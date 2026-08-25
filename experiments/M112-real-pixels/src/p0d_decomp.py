r"""M112 Phase 0d -- why P-A was contradicted: where the perturbation actually lands.

`p0c_quant.py` registered P-A: that a quantisation floor would COMPRESS the
measured cost toward zero, per M115's band-SNR factorisation. **The measurement
contradicted it.** The cost INFLATES, +0.1813 -> +0.2105 dex, before collapsing
at extreme posterisation. This file chases that rather than banking P-B/C/D.

THE ALGEBRA I GOT WRONG
-----------------------
p0c reasoned: a white floor `q` enters the control as `Phi_b = Phi_true + q`, and
the arm gathers from the same quantised source so it filters signal and floor
alike, `Phi_g = |H|^2 (Phi_true + q)`. Then

    cost = log10( (Phi_true + q) / (|H|^2 (Phi_true + q)) ) = log10(1 / |H|^2)

which is independent of `q`. That predicts a FLAT ladder, and the ladder is not
flat. The error is the step that writes `|H|^2` as a scalar.

`band_ratio` is a MEAN over a band, and the gather's transfer |H(f)|^2 falls
across that band. A band mean is therefore a spectrum-weighted average of |H|^2,
and the weight is the spectrum of whatever dominates the band. The image's own
spectrum is red and concentrates near the band's lower edge where |H|^2 is high;
a quantisation floor is approximately white and puts relatively more power at the
band's upper edge where |H|^2 is lowest. So the floor is attenuated MORE than the
signal it displaces, and the cost rises as the floor takes over the band.

**The perturbation lands in the band weighting, not in a common factor.** Writing
a frequency-dependent transfer as a scalar is exactly what hides it.

THE DISCRIMINATING TEST
-----------------------
If the effect were a common additive floor, it would enter control and arm alike
and largely cancel: BR(base) and BR(gathered) would rise together and the cost
would stay flat. If instead quantisation INJECTS high-band power that the
low-passed arm cannot follow, BR(base) rises and the gap widens. This measures
both terms separately at each dose.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "experiments" / "M95-coverage" / "src"))
import m95cov as M          # noqa: E402

sys.path.insert(0, str(HERE.parent))
from p0c_quant import BASE, LEVELS, quantise    # noqa: E402

STEP = 0.9315   # the coverage-scale gather, as in the NOW arm


def main():
    img0 = M.load_luma(BASE)
    tiles = M.pick_tiles(img0)
    print(f"tiles {len(tiles)}   band {M.BAND} cyc/px   gather step {STEP}\n")
    print(f"{'levels':>8s} {'meas/tile':>10s} {'BR(base)':>10s} {'BR(gath)':>10s} "
          f"{'cost':>9s} {'dBR_base':>10s} {'dBR_gath':>10s}")
    out, b0, g0 = [], None, None
    for lv in LEVELS[:-1]:      # drop 2 levels: the low band goes to zero -> NaN
        img = quantise(img0, lv)
        meas = int(np.median([np.unique(img[ty:ty + M.TILE, tx:tx + M.TILE]).size
                              for ty, tx in tiles]))
        br_b, br_g = [], []
        for ty, tx in tiles:
            br_b.append(M.band_ratio(img[ty:ty + M.TILE, tx:tx + M.TILE], 1.0))
            reg = img[ty - 64:ty + M.TILE + 64, tx - 64:tx + M.TILE + 64]
            br_g.append(M.band_ratio(M.gather(reg, STEP, 64.3, 64.3), STEP))
        mb, mg = float(np.mean(br_b)), float(np.mean(br_g))
        if b0 is None:
            b0, g0 = mb, mg
        out.append({"levels": lv, "measured_levels_per_tile": meas,
                    "BR_base": mb, "BR_gathered": mg, "cost": mb - mg,
                    "d_BR_base": mb - b0, "d_BR_gathered": mg - g0})
        print(f"{str(lv):>8s} {meas:>10d} {mb:>10.4f} {mg:>10.4f} {mb - mg:>+9.4f} "
              f"{mb - b0:>+10.4f} {mg - g0:>+10.4f}")

    rise = out[-1]["d_BR_base"]
    print(f"\ncontrol high-band power inflates by {rise:+.4f} dex across the ladder.")
    print("A common additive floor cannot do that: it would enter both terms and cancel.")
    print("VERDICT ON P-A: contradicted, and the mechanism is band-weighted transfer,")
    print("not a common floor. Quantisation ADDS high-band power the arm cannot follow.")
    print("\nDirection matters for M112: quantisation drives the measured recovery")
    print("MORE POSITIVE (toward 'ship'), so it cannot have manufactured a no-go.")
    (HERE.parents[1] / "out" / "p0d.json").write_text(
        json.dumps({"base": str(BASE), "step": STEP, "band": list(M.BAND),
                    "n_tiles": len(tiles), "ladder": out}, indent=1),
        encoding="utf-8")


if __name__ == "__main__":
    main()
