"""M126/PQ6 -- pool by the crate's OWN commissioning criterion.

merge.rs:2063-2072 checks the pure-noise response MEAN against the closed-form
Rayleigh mean and refuses the measurement unless the ratio is inside 0.97-1.03:

    "A silent rescale ... moves this by three orders of magnitude while leaving
     the standard deviation looking plausible."

That check is a *structure detector* when it is pointed at real data. Under pure
sensor noise the mean must land on the Rayleigh mean; scene structure can only
push it up. And it is near-orthogonal to the quantity being tested, because for
a mean-of-Rayleigh field the mean is invariant to the effective sample count
while the SD scales as 1/sqrt(n_eff).

So: keep only the regions the crate itself would accept as pure noise, and read
the SD off those. POST-HOC -- this selector was not in PREREG-PQ6.md (d3ed787),
which selected by the render's structure quantile. Both are reported.
"""

import json
from pathlib import Path

import numpy as np

import score
from pq6 import ROOT, SUBJECTS, FOCUS_NOISE_SD, RAYLEIGH_MEAN, load_focus

# merge.rs:2069 -- the crate's own tolerance on the structural mean check.
CRATE_LO, CRATE_HI = 0.97, 1.03
SIZES = [128, 192, 256, 384, 512]


def regions(resp: np.ndarray, size: int):
    hh, ww = resp.shape[0] // size, resp.shape[1] // size
    b = resp[: hh * size, : ww * size].reshape(hh, size, ww, size)
    m1 = b.mean(axis=(1, 3))
    m2 = (b.astype(np.float64) ** 2).mean(axis=(1, 3))
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    return m1.ravel(), sd.ravel()


def main() -> None:
    out = {"criterion": [CRATE_LO, CRATE_HI], "FOCUS_NOISE_SD": FOCUS_NOISE_SD,
           "by_size": {}, "per_subject": {}}

    print(f"regions passing the crate's own 0.97-1.03 mean check\n")
    print(f"{'size':>5} {'kept':>6} {'of':>6} {'sd_median':>10} {'ratio':>7} "
          f"{'sd_p25':>9} {'sd_p75':>9}")
    for size in SIZES:
        keep_sd, tot = [], 0
        for s in SUBJECTS:
            resp = load_focus(ROOT / f"dump-{s}")
            m, sd = regions(resp, size)
            r = m / RAYLEIGH_MEAN
            ok = (r >= CRATE_LO) & (r <= CRATE_HI)
            keep_sd.append(sd[ok])
            tot += ok.size
            out["per_subject"].setdefault(s, {})[str(size)] = {
                "kept": int(ok.sum()), "of": int(ok.size),
                "sd_median": float(np.median(sd[ok])) if ok.any() else None,
            }
        allsd = np.concatenate(keep_sd)
        if allsd.size == 0:
            print(f"{size:>5} {0:>6} {tot:>6}   (no region passes)")
            continue
        med = float(np.median(allsd))
        out["by_size"][str(size)] = {
            "kept": int(allsd.size), "of": tot,
            "sd_median": med, "ratio": med / FOCUS_NOISE_SD,
            "sd_p25": float(np.quantile(allsd, 0.25)),
            "sd_p75": float(np.quantile(allsd, 0.75)),
        }
        print(f"{size:>5} {allsd.size:>6} {tot:>6} {med:>10.5f} "
              f"{med / FOCUS_NOISE_SD:>7.3f} {np.quantile(allsd, 0.25):>9.5f} "
              f"{np.quantile(allsd, 0.75):>9.5f}")

    print("\nper-subject, region size 256 (kept / of, sd_median):")
    for s in SUBJECTS:
        r = out["per_subject"][s]["256"]
        sdm = f"{r['sd_median']:.5f}" if r["sd_median"] else "--"
        print(f"  {s:>14}  {r['kept']:>3} / {r['of']:<3}  {sdm}")

    (ROOT / "pq6_pooled.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'pq6_pooled.json'}")


if __name__ == "__main__":
    main()
