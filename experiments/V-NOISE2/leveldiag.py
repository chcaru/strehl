"""leveldiag -- is A1 repairable?  MEASURE the level dependence, do not assume it.

fullhp's noise correction subtracts FLAT-tile band power from DETAIL-tile band
power.  That assumes (A1) the two populations carry the same noise power.  The
first run MEASURED their luma levels as 10315.7 and 6302.0 -- a ratio of 0.611 --
so A1 is false, and the direction is the flattering one: FLAT tiles are darker,
shot noise in CONTRAST units grows as the level falls, so F over-states the
noise in DETAIL tiles and S = D - F over-subtracts.  It over-subtracts more from
the noisier arm, which is `enfuse`.

Rather than assume a noise model, fit one.  If band power varies with tile level
as L^p, then the FLAT population's own scatter measures p, and the correction to
the DETAIL population's level is F * (L_D / L_F)^p.

    p = 0   noise power independent of level  (A1 as originally assumed)
    p = -1  shot-noise limited, in contrast units
    p = -2  fixed additive noise, in contrast units

This prints p with a bootstrap CI, the level spread available to fit it, and how
far apart the three corrections put the answer -- so the sensitivity is a
measured band rather than an argued one.  It also reports the overlap between
the two populations' level distributions, because if it is large enough the
whole assumption can be sidestepped by level-matching instead of modelling.

    python leveldiag.py [key=119]
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
from h2h2b import Comp, T                                        # noqa: E402

import hd2                                                       # noqa: E402
from fullhp import W, bandpower                                  # noqa: E402


def collect(comp, cells, t=T):
    lv, bp = [], []
    for (y, x) in cells:
        c, nc = comp.crop(int(y), int(x), t)
        if c is None or nc:
            continue
        b = bandpower(c)
        if b is None or not np.isfinite(b) or b <= 0:
            continue
        lv.append(float(c.mean()))
        bp.append(b)
    return np.array(lv), np.array(bp)


def fit_p(lv, bp, nboot=2000, rng=None):
    rng = rng or np.random.default_rng(3)
    x, y = np.log(lv), np.log(bp)
    p = float(np.polyfit(x, y, 1)[0])
    bs = []
    for _ in range(nboot):
        i = rng.integers(0, len(x), len(x))
        if np.ptp(x[i]) <= 0:
            continue
        bs.append(np.polyfit(x[i], y[i], 1)[0])
    return p, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    arm = os.path.join(hd2.ROOT, key, "arms")
    z = np.load(os.path.join(hd2.ROOT, key, "census.npz"))
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    FLAT = [tuple(cells[i]) for i in flat]

    print("=" * 96)
    print(f"LEVELDIAG -- measuring the level dependence A1 assumes away, {key}")
    print("=" * 96)
    out = {}
    for name, fn in (("strehl", "strehl-full.tiff"),
                     ("enfuse", "coh-enfuse-full.tif")):
        C = Comp(dict(path=os.path.join(arm, fn), weights=W))
        lvF, bpF = collect(C, FLAT)
        lvD, bpD = collect(C, DET)
        p, lo, hi = fit_p(lvF, bpF)
        out[name] = (np.median(lvD), np.median(lvF), np.median(bpD),
                     np.median(bpF), p, lo, hi)
        print(f"\n  {name}")
        print(f"    FLAT   n={len(lvF):3d} level median {np.median(lvF):8.1f} "
              f"range [{lvF.min():.0f}, {lvF.max():.0f}]  "
              f"log-range {np.log(lvF.max()/lvF.min()):.2f}")
        print(f"    DETAIL n={len(lvD):3d} level median {np.median(lvD):8.1f} "
              f"range [{lvD.min():.0f}, {lvD.max():.0f}]")
        print(f"    fitted p (band power ~ L^p, over FLAT tiles): "
              f"{p:+.3f} [{lo:+.3f}, {hi:+.3f}] 95% CI")
        ov_lo = max(lvF.min(), lvD.min())
        ov_hi = min(lvF.max(), lvD.max())
        nF = int(((lvF >= ov_lo) & (lvF <= ov_hi)).sum())
        nD = int(((lvD >= ov_lo) & (lvD <= ov_hi)).sum())
        print(f"    level overlap [{ov_lo:.0f}, {ov_hi:.0f}]: "
              f"{nF}/{len(lvF)} FLAT and {nD}/{len(lvD)} DETAIL tiles inside it")
        for pp, lab in ((0.0, "p=0  (A1 as assumed)"), (p, "p=fitted"),
                        (-1.0, "p=-1 (shot-limited)"), (-2.0, "p=-2 (additive)")):
            Fc = np.median(bpF) * (np.median(lvD) / np.median(lvF)) ** pp
            S = np.median(bpD) - Fc
            print(f"      {lab:24s} F->{Fc:.4e}  S={S:.4e}"
                  + ("   NEGATIVE -- estimator destroyed" if S <= 0 else ""))

    print()
    print("=" * 96)
    print("  What it does to the ANSWER (enfuse detail amplitude / strehl's):")
    for pp, lab in ((0.0, "p=0  (A1 as assumed)"), (out['strehl'][4], "p=fitted(strehl)"),
                    (-1.0, "p=-1 (shot-limited)"), (-2.0, "p=-2 (additive)")):
        vals = {}
        for name in ("strehl", "enfuse"):
            lD, lF, bD, bF = out[name][:4]
            vals[name] = bD - bF * (lD / lF) ** pp
        if vals["strehl"] > 0 and vals["enfuse"] > 0:
            r = np.sqrt(vals["enfuse"] / vals["strehl"])
            print(f"    {lab:24s} ratio {r:.3f}")
        else:
            print(f"    {lab:24s} UNDEFINED (a scene term went non-positive)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
