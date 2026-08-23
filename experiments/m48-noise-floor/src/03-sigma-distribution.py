"""M48 step 3 - is the pooled RMS inflated by a sparse hot tail, or by a broad
population?

Step 2 established that M4's table is the POOLED RMS,
`rms_sd = sqrt(mean_pixels(var))`, and that `mean_sd = mean_pixels(sd)` is 11-15%
lower with the gap growing in ISO. The working explanation was "the hot-pixel
tail inflates the RMS", which -- if true -- would argue for re-basing the
constants on a typical pixel, because M22 already carries a recurrent hot-pixel
map (11,393 px = 0.0346% of the sensor) and M29 treats static defects as a
separate concern.

That explanation is a hypothesis and this script exists to kill it. Jensen's
inequality guarantees rms >= mean for ANY spread of per-pixel sigma, sparse or
not, so the gap on its own is not evidence of a tail.

The discriminating measurement is variance CONCENTRATION:

  - what fraction of the total temporal variance is carried by the top q of
    pixels, for q at and above M22's hot-pixel rate;
  - what the pooled RMS becomes once those pixels are excised.

The excision is deliberately generous to the tail hypothesis: pixels are ranked
by their sigma AT THIS ISO and the worst are removed, which is an oracle no
runtime defect map can be. If even the oracle excision fails to bring the pooled
RMS down to the mean pixel, the tail hypothesis is refuted and the gap is a
property of the whole population.

Also emitted, because they cost nothing on the same pass:

  - per-plane rms_sd, extending step 2's verification of M4 section 8.1 from the
    published 4-plane mean to all four published plane columns;
  - percentiles of the per-pixel sigma, so the shape of the population is on the
    record rather than inferred from two moments;
  - the count of pixels whose 20 samples are all identical (sd exactly 0), which
    is a quantisation tell at low ISO.

No gain is assumed anywhere. Sigma is in DN.
"""

import glob
import json
import os

import numpy as np
import rawpy

ROOT = r"D:\macro-dark-frames"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# M4 section 8.1 per-plane, as published. Step 2 verified the mean column only.
M4_PLANES = {
    50: (1.0079, 1.0054, 1.0120, 0.9211),
    100: (1.0048, 1.0042, 1.0105, 0.9185),
    200: (1.7709, 1.7782, 1.7929, 1.6246),
    250: (2.1927, 2.2104, 2.2284, 2.0201),
    400: (1.2130, 1.2266, 1.2403, 1.1146),
    500: (1.4940, 1.4949, 1.5105, 1.3724),
    640: (1.8308, 1.8438, 1.8657, 1.6914),
    800: (2.2752, 2.2872, 2.3138, 2.1100),
    1000: (2.8376, 2.8582, 2.8920, 2.6463),
    1600: (4.4369, 4.4702, 4.5407, 4.1739),
    2000: (5.5866, 5.6165, 5.6883, 5.2406),
}

PLANES = (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1))

# M22's recurrent hot-pixel rate is 0.0346%; the others bracket it by decades.
EXCISE_Q = (0.000346, 0.001, 0.005, 0.01, 0.05)
PCTS = (0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9, 99.99)


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def temporal_var(files):
    """Per-pixel temporal variance over `files`, float64 sum / sum-of-squares."""
    s = ss = None
    n = 0
    for f in files:
        # Rule 32: raw_image_visible is a view into LibRaw's buffer. Copy inside
        # the `with`, on the same line.
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


def plane_stats(var):
    """Every statistic this milestone needs, from one plane's variance map."""
    npx = var.size
    sd = np.sqrt(var)
    total_var = float(var.sum())
    var_sorted = np.sort(var)  # ascending
    csum = np.cumsum(var_sorted)

    concentration = {}
    excised_rms = {}
    for q in EXCISE_Q:
        k = max(1, int(round(q * npx)))  # this many pixels removed from the top
        keep = npx - k
        concentration[f"{q}"] = float((total_var - csum[keep - 1]) / total_var)
        excised_rms[f"{q}"] = float(np.sqrt(csum[keep - 1] / keep))

    return dict(
        n_px=int(npx),
        rms_sd=float(np.sqrt(var.mean())),
        mean_sd=float(sd.mean()),
        median_sd=float(np.median(sd)),
        max_sd=float(sd.max()),
        zero_sd_px=int((var == 0.0).sum()),
        pct=[float(x) for x in np.percentile(sd, PCTS)],
        # fraction of TOTAL VARIANCE carried by the worst q of pixels
        var_frac_top=concentration,
        # pooled RMS after an oracle excision of the worst q of pixels
        rms_excised=excised_rms,
    )


def main():
    rows = []
    for d in sorted(glob.glob(os.path.join(ROOT, "*MSDCF"))):
        fs = sorted(glob.glob(os.path.join(d, "*.ARW")))[2:]
        iso = iso_of(fs[0])
        var, n = temporal_var(fs)
        per_plane = {}
        for name, dy, dx in PLANES:
            per_plane[name] = plane_stats(np.ascontiguousarray(var[dy::2, dx::2]))
        del var

        mean4 = {
            k: sum(per_plane[p][k] for p, _, _ in PLANES) / 4
            for k in ("rms_sd", "mean_sd", "median_sd")
        }
        # Plane-averaged concentration and excised RMS, same convention as step 2.
        conc4 = {
            q: sum(per_plane[p]["var_frac_top"][q] for p, _, _ in PLANES) / 4
            for q in (f"{q}" for q in EXCISE_Q)
        }
        exc4 = {
            q: sum(per_plane[p]["rms_excised"][q] for p, _, _ in PLANES) / 4
            for q in (f"{q}" for q in EXCISE_Q)
        }
        m4 = M4_PLANES[iso]
        m4_ratio = [
            per_plane[p]["rms_sd"] / m for p, m in zip(("R", "G1", "G2", "B"), m4)
        ]

        rows.append(
            dict(
                dir=os.path.basename(d),
                iso=iso,
                n=n,
                planes=per_plane,
                mean4=mean4,
                var_frac_top4=conc4,
                rms_excised4=exc4,
                m4_planes=list(m4),
                m4_plane_ratio=m4_ratio,
            )
        )
        print(
            f"ISO {iso:>5}  rms={mean4['rms_sd']:7.4f} mean={mean4['mean_sd']:7.4f} "
            f"med={mean4['median_sd']:7.4f} | mean/rms={mean4['mean_sd'] / mean4['rms_sd']:.4f} "
            f"| top0.0346% carries {100 * conc4['0.000346']:5.2f}% of var, "
            f"excised rms={exc4['0.000346']:7.4f} "
            f"| per-plane M4 ratio {min(m4_ratio):.4f}-{max(m4_ratio):.4f}"
        )

    rows.sort(key=lambda r: r["iso"])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "sigma-distribution.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nwrote {os.path.join(OUT, 'sigma-distribution.json')}")


if __name__ == "__main__":
    main()
