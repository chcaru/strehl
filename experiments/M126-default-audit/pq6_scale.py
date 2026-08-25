"""M126/PQ6 correction -- the 64x64 tile SD in pq6.py is biased LOW, and the
crate said so before I measured it.

merge.rs:1957-1968 (fact 313): "A sample standard deviation taken over a region
only a few supports across is biased low, because the mean it subtracts is
itself correlated with the samples. At 192 x 192 this measured 0.01366 -- 10%
under the truth -- and it drifted with plane size."

The combined support is 43x43. pq6.py used TILE = 64: **1.5 supports across**,
far smaller than the 192 that already read 10% low. So pq6.py's ratios are not
evidence about the constant; they are a re-measurement of a documented bias.

This sweeps region size and looks for the drift fact 313 predicts. The crate's
own synthetic ladder is the comparison, measured with the same estimator:

    192^2 -> 0.01366    384^2 -> 0.015277 +/- 0.000223    512^2 -> 0.015214 +/- 0.000075

If the real-data ladder tracks the synthetic ladder, the constant's domain
matches its application domain and PQ6 is refuted. If the real ladder converges
somewhere else, the gap is the answer.
"""

import json
from pathlib import Path

import numpy as np

import score
from pq6 import ROOT, SUBJECTS, FOCUS_NOISE_SD, RAYLEIGH_MEAN, load_focus

# The crate's own synthetic ladder, merge.rs:1962-1966 / fact 313.
CRATE_LADDER = {192: 0.01366, 384: 0.015277, 512: 0.015214}
SIZES = [64, 128, 192, 256, 384, 512]


def region_stats(resp: np.ndarray, struct: np.ndarray, size: int, frac: float):
    """Per-region mean and SD of `resp` over the flattest `frac` of regions,
    where flatness is judged from the RENDER's structure field, never from the
    response being measured."""
    hh, ww = resp.shape[0] // size, resp.shape[1] // size
    rb = resp[: hh * size, : ww * size].reshape(hh, size, ww, size)
    sb = struct[: hh * size, : ww * size].reshape(hh, size, ww, size)

    m1 = rb.mean(axis=(1, 3))
    m2 = (rb.astype(np.float64) ** 2).mean(axis=(1, 3))
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    smean = sb.mean(axis=(1, 3))

    cut = float(np.quantile(smean, frac))
    keep = smean <= cut
    return m1[keep], sd[keep], int(keep.sum())


def main() -> None:
    out = {"crate_ladder": CRATE_LADDER, "FOCUS_NOISE_SD": FOCUS_NOISE_SD,
           "sizes": SIZES, "subjects": {}}

    print(f"{'subject':>14} {'size':>5} {'n':>4} {'sd_p50':>9} {'ratio':>7} "
          f"{'mean/rayl':>9}   crate_synthetic")
    for s in SUBJECTS:
        resp = load_focus(ROOT / f"dump-{s}")
        g = score.green(ROOT / f"{s}.tif")
        st = score.structure(g)
        out["subjects"][s] = {}
        for size in SIZES:
            means, sds, n = region_stats(resp, st, size, score.FLAT_FRAC)
            if n == 0:
                continue
            med = float(np.median(sds))
            rec = {
                "n_regions": n,
                "sd_median": med,
                "sd_p05": float(np.quantile(sds, 0.05)),
                "ratio_median": med / FOCUS_NOISE_SD,
                "mean_over_rayleigh": float(np.median(means) / RAYLEIGH_MEAN),
            }
            out["subjects"][s][str(size)] = rec
            crate = CRATE_LADDER.get(size)
            ctxt = f"{crate:.5f}" if crate else "--"
            print(f"{s:>14} {size:>5} {n:>4} {med:>9.5f} {rec['ratio_median']:>7.3f} "
                  f"{rec['mean_over_rayleigh']:>9.3f}   {ctxt}")
        print()

    # Does the real ladder drift the way fact 313 says a biased one must?
    out["drift"] = {}
    for s in SUBJECTS:
        d = out["subjects"][s]
        if "64" in d and "512" in d:
            out["drift"][s] = d["512"]["sd_median"] / d["64"]["sd_median"]
    print("drift 64 -> 512 (fact 313 predicts > 1 if the small tile is biased low):")
    for s, v in out["drift"].items():
        print(f"  {s:>14}  {v:.3f}x")

    (ROOT / "pq6_scale.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'pq6_scale.json'}")


if __name__ == "__main__":
    main()
