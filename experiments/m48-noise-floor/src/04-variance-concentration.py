"""M48 step 4 - variance concentration, done correctly. Supersedes step 3's
`var_frac_top` / `rms_excised` fields, which are WRONG.

**The defect in step 3, stated plainly.** `03-sigma-distribution.py` called
`np.sort(var)` on a 2-D per-plane variance map. `np.sort` defaults to
`axis=-1`, so it sorted each ROW independently; the following `np.cumsum`
then flattened that row-wise-sorted array. Every "top q of pixels" quantity in
`data/sigma-distribution.json` is therefore computed over the tail of the last
rows rather than over the tail of the sensor, and reads almost exactly
proportional to `q` -- which is the tell, since the same file's percentiles show
a p99 sigma four times the median. This is AGENTS.md rule 23's general form
("any separable filter applied to an array with a non-spatial axis will touch
that axis unless you stop it") in its simplest costume: a reduction with a
default axis. Step 3's `rms_sd` / `mean_sd` / `median_sd` / percentiles / max
are unaffected -- those reductions all flatten by default and are correct.

**The question this is answering.** Step 2 found the pooled RMS
`sqrt(mean_px(var))` sits 6-15% above the mean pixel `mean_px(sd)`, with the gap
growing in ISO, and the working explanation was the hot-pixel tail. Jensen's
inequality gives `rms >= mean` for ANY spread of per-pixel sigma, so the gap
alone is not evidence of a tail. The discriminating measurement is where the
variance actually lives:

  - the fraction of total temporal variance carried by the worst q of pixels;
  - the pooled RMS after those pixels are excised;
  - the excision fraction at which the pooled RMS finally meets the mean pixel.

The excision is an ORACLE and is deliberately generous to the tail hypothesis:
pixels are ranked by their sigma at this very ISO, so it removes the worst
pixels a defect map could not have known about. If even the oracle fails to
close the gap, the tail hypothesis is refuted for good.

Reference rates: M22's recurrent hot-pixel map is 11,393 px = 0.0346% of the
sensor; M4 section 9 finds 17 pixels sensor-wide above black+50 DN at ISO 2000.

No gain is assumed. Sigma is in DN.
"""

import glob
import json
import os

import numpy as np
import rawpy

ROOT = r"D:\macro-dark-frames"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

PLANES = (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1))
EXCISE_Q = (0.000346, 0.001, 0.005, 0.01, 0.05, 0.10, 0.20)


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def temporal_var(files):
    s = ss = None
    n = 0
    for f in files:
        # Rule 32: copy inside the `with`, on the same line.
        with rawpy.imread(f) as rr:
            a = rr.raw_image_visible.astype(np.float64)
        if s is None:
            s = np.zeros_like(a)
            ss = np.zeros_like(a)
        s += a
        ss += a * a
        n += 1
    var = (ss - s * s / n) / (n - 1)
    np.clip(var, 0, None, out=var)
    return var, n


def plane_stats(var2d):
    """`var2d` is one plane's per-pixel temporal variance."""
    var = np.sort(var2d, axis=None)  # axis=None: flat, ascending. The fix.
    npx = var.size
    csum = np.cumsum(var)
    total = float(csum[-1])
    rms = float(np.sqrt(total / npx))
    mean_sd = float(np.sqrt(var).mean())

    frac, excised = {}, {}
    for q in EXCISE_Q:
        k = max(1, int(round(q * npx)))
        keep = npx - k
        frac[f"{q}"] = float((total - csum[keep - 1]) / total)
        excised[f"{q}"] = float(np.sqrt(csum[keep - 1] / keep))

    # The excision fraction at which the oracle-excised pooled RMS finally meets
    # the mean pixel. `csum[j-1]/j` is the mean variance of the j smallest, which
    # is monotone non-decreasing in j, so a binary search is exact.
    target = mean_sd * mean_sd
    lo, hi = 1, npx
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if csum[mid - 1] / mid <= target:
            lo = mid
        else:
            hi = mid - 1
    meet_q = float((npx - lo) / npx)

    return dict(
        n_px=int(npx),
        rms_sd=rms,
        mean_sd=mean_sd,
        median_sd=float(np.sqrt(var[npx // 2])),
        var_frac_top=frac,
        rms_excised=excised,
        excise_q_to_reach_mean_sd=meet_q,
    )


def main():
    rows = []
    print(
        f"{'ISO':>5} {'rms':>7} {'mean':>7} {'gap%':>6} | "
        f"{'top.0346%':>9} {'top1%':>7} {'top5%':>7} (share of variance) | "
        f"{'exc.0346%':>9} {'exc5%':>7} {'exc20%':>7} (rms/full) | {'q to meet mean':>14}"
    )
    for d in sorted(glob.glob(os.path.join(ROOT, "*MSDCF"))):
        fs = sorted(glob.glob(os.path.join(d, "*.ARW")))[2:]
        iso = iso_of(fs[0])
        var, n = temporal_var(fs)
        per_plane = {
            name: plane_stats(np.ascontiguousarray(var[dy::2, dx::2]))
            for name, dy, dx in PLANES
        }
        del var

        names = [p for p, _, _ in PLANES]
        avg = lambda k: sum(per_plane[p][k] for p in names) / 4  # noqa: E731
        rms4, mean4 = avg("rms_sd"), avg("mean_sd")
        frac4 = {
            f"{q}": sum(per_plane[p]["var_frac_top"][f"{q}"] for p in names) / 4
            for q in EXCISE_Q
        }
        exc4 = {
            f"{q}": sum(per_plane[p]["rms_excised"][f"{q}"] for p in names) / 4
            for q in EXCISE_Q
        }
        meet4 = avg("excise_q_to_reach_mean_sd")

        rows.append(
            dict(
                dir=os.path.basename(d),
                iso=iso,
                n=n,
                planes=per_plane,
                rms_sd4=rms4,
                mean_sd4=mean4,
                median_sd4=avg("median_sd"),
                var_frac_top4=frac4,
                rms_excised4=exc4,
                excise_q_to_reach_mean_sd4=meet4,
            )
        )
        print(
            f"{iso:>5} {rms4:7.4f} {mean4:7.4f} {100 * (rms4 / mean4 - 1):6.2f} | "
            f"{100 * frac4['0.000346']:8.3f}% {100 * frac4['0.01']:6.2f}% "
            f"{100 * frac4['0.05']:6.2f}% | "
            f"{exc4['0.000346'] / rms4:9.5f} {exc4['0.05'] / rms4:7.5f} "
            f"{exc4['0.2'] / rms4:7.5f} | {100 * meet4:13.2f}%"
        )

    rows.sort(key=lambda r: r["iso"])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "variance-concentration.json"), "w") as fh:
        json.dump(
            dict(
                supersedes=(
                    "data/sigma-distribution.json fields 'var_frac_top', "
                    "'var_frac_top4', 'rms_excised', 'rms_excised4' -- those were "
                    "computed with np.sort on a 2-D array (default axis=-1) and "
                    "are wrong. All other fields of that file are correct."
                ),
                rows=rows,
            ),
            fh,
            indent=1,
        )
    print(f"\nwrote {os.path.join(OUT, 'variance-concentration.json')}")


if __name__ == "__main__":
    main()
