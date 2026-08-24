"""M72 step 6 -- where each covariance is generated.  Prediction declared first.

C2 and O5 together show two distinct ISO signatures in the same sweep.  From
ISO 100 to ISO 2000, rho falls to:

    R-G2  1.23      G2-B  0.84      G1-B  0.82        <- barely moves
    G1-G2 0.34      R-B   0.36      within-plane 0.26-0.36  <- falls ~3x

The pairs that barely move are exactly the four ORTHOGONAL NEAREST
NEIGHBOURS at |Delta| = 1: R-G1 (0,1), R-G2 (1,0), G2-B (0,1), G1-B (1,0).
The pairs that fall steeply are everything at |Delta| >= sqrt(2): the two
diagonals and every within-plane pair.  That split is by DISTANCE and it is
not the split F3 found in the field, which was about magnitude.

WHY THIS WOULD BE A MECHANISM STATEMENT

02 fits var(ISO) = alpha G^2 + delta and does the same for cov.  The alpha
G^2 term is noise referred to the ELECTRON domain, upstream of the
conversion gain; the delta term is fixed in DN^2 and is generated
DOWNSTREAM of it, in the late analog chain or the ADC.  05 measured the
variance's own split: upstream fraction 0.6933 for the greens.

rho = cov/var is flat with ISO if and only if the covariance has the SAME
upstream/downstream split as the variance it normalises.  So:

    flat  ->  upstream fraction ~= 0.69, the variance's own value
    steep ->  upstream fraction << 0.69

05 already found 0.2488 for G1-G2, which is steep and consistent.  The test
is whether the FLAT pairs come out near the variance's 0.69.

PREDICTION, DECLARED BEFORE RUNNING, AND IT CAN FAIL

  P1  The three flat pairs with non-zero rho -- R-G2, G2-B, G1-B -- have
      covariance upstream fractions consistent with the green variance's
      0.6933, and the steep pairs G1-G2 and R-B and all eight within-plane
      series do not.  I will call the split established only if EVERY flat
      pair exceeds EVERY steep series, with no overlap.

  P2  Rank correlation between the upstream fraction and the ISO ratio
      across all thirteen series must be strong and positive.  A weak or
      negative rank correlation means the alpha/delta split is not what
      drives the ISO behaviour and P1 passed by coincidence.

  CONSEQUENCE IF P1 FAILS: the two ISO signatures are reported as a
  measured, unexplained structure and NO generation location is claimed for
  either group.  The report says the mechanism is unidentified.  This is a
  real possibility: the fits are three-parameter over eleven points with a
  dual-gain break, and R-G1 is so close to zero that its ratio is
  meaningless -- which is why it is excluded from P1 by name, here, before
  the numbers are seen.

  WHAT THIS CANNOT DO, either way: locating a covariance upstream of the
  conversion gain does not name the circuit.  Upstream in a DARK frame means
  the electron domain at or before the sense node.  It does not distinguish
  a shared floating diffusion from correlated dark current from anything
  else generated there, and this milestone has no instrument that can.

Run: python 06-mechanism-split.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

spec2 = importlib.util.spec_from_file_location("m72c", HERE / "02-criteria.py")
m72c = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(m72c)

FLAT = ["R-G2", "G2-B", "G1-B"]
STEEP = ["G1-G2", "R-B"]
SHEP = 1.0 / 12.0


def main() -> int:
    sweep = json.loads((DATA / "01-green-correlation.json").read_text(encoding="utf-8"))
    groups = sorted(sweep["groups"], key=lambda q: q["iso"])
    isos = np.array([q["iso"] for q in groups], float)
    g = np.array([m72c.gain(i) for i in isos])
    md = np.array([m72c.mode(i) for i in isos])
    g0 = m72c.gain(100.0)

    def upstream(cov: np.ndarray) -> tuple[float, float, dict]:
        fit = m72c.jackknife_fit(g, md, cov)
        up = fit["alpha_low"] * g0 ** 2
        return up / (up + fit["delta"]), fit["alpha_low_se"] * g0 ** 2, fit

    def var_of(plane: str, q: dict) -> float:
        pair, which = {"R": ("R-G1", "var_a"), "G1": ("G1-G2", "var_a"),
                       "G2": ("G1-G2", "var_b"), "B": ("R-B", "var_b")}[plane]
        return q["arms"]["k6"]["pairs"][pair][which]

    print("=" * 78)
    print("M72 step 6 -- upstream fraction of every covariance series")
    print("=" * 78)
    print("\n  var(ISO) = alpha G^2 + delta.  Upstream fraction = alpha G(100)^2")
    print("  over the total at base ISO.  Green VARIANCE reference = 0.6933.\n")
    print(f"  {'series':>12} {'|Delta|':>8} {'rho@100':>9} {'rho@2000':>9} "
          f"{'ratio':>7} {'upstream':>9} {'group':>7}")

    rows = []
    for name in ("R-G1", "R-G2", "G2-B", "G1-B", "G1-G2", "R-B"):
        cov = np.array([q["arms"]["k6"]["pairs"][name]["cov"] for q in groups])
        r0 = groups[1]["arms"]["k6"]["pairs"][name]["rho_shep"]
        r1 = groups[-1]["arms"]["k6"]["pairs"][name]["rho_shep"]
        frac, _, _ = upstream(cov)
        grp = "flat" if name in FLAT else ("steep" if name in STEEP else "zero")
        dist = "1" if name in ("R-G1", "R-G2", "G2-B", "G1-B") else "sqrt2"
        rows.append((name, grp, r1 / r0 if abs(r0) > 1e-3 else float("nan"), frac))
        print(f"  {name:>12} {dist:>8} {r0:+9.5f} {r1:+9.5f} "
              f"{(r1 / r0 if abs(r0) > 1e-3 else float('nan')):7.3f} {frac:9.4f} {grp:>7}")

    for plane in ("R", "G1", "G2", "B"):
        for kind in ("same_row", "same_col"):
            rho = np.array([q["arms"]["k6"]["within"][plane][kind] for q in groups])
            var = np.array([var_of(plane, q) for q in groups])
            cov = rho * (var - SHEP)
            frac, _, _ = upstream(cov)
            name = f"{plane} {kind[5:]}"
            rows.append((name, "steep", rho[-1] / rho[1], frac))
            print(f"  {name:>12} {'2':>8} {rho[1]:+9.5f} {rho[-1]:+9.5f} "
                  f"{rho[-1] / rho[1]:7.3f} {frac:9.4f} {'steep':>7}")

    flat = [f for n, gr, _, f in rows if gr == "flat"]
    steep = [f for n, gr, _, f in rows if gr == "steep"]
    print(f"\n  flat  pairs  upstream {min(flat):.4f} to {max(flat):.4f}   n={len(flat)}")
    print(f"  steep series upstream {min(steep):.4f} to {max(steep):.4f}   n={len(steep)}")
    print(f"  green VARIANCE upstream 0.6933")

    p1 = min(flat) > max(steep)
    print(f"\n  P1  every flat pair above every steep series: "
          f"{min(flat):.4f} > {max(steep):.4f}  {'PASS' if p1 else 'FAIL'}")

    use = [(r, f) for n, gr, r, f in rows if gr != "zero" and np.isfinite(r)]
    rr = np.array([a for a, _ in use])
    ff = np.array([b for _, b in use])
    ra = rr.argsort().argsort().astype(float)
    fa = ff.argsort().argsort().astype(float)
    rank = float(np.corrcoef(ra, fa)[0, 1])
    p2 = rank > 0.5
    print(f"  P2  Spearman(ISO ratio, upstream fraction) over {len(use)} series "
          f"= {rank:+.4f}  {'PASS' if p2 else 'FAIL'}")

    print("\n" + "=" * 78)
    if p1 and p2:
        print("BOTH PRE-REGISTERED PREDICTIONS MET.")
        print("The two ISO signatures are an upstream/downstream split, and it")
        print("is ordered by DISTANCE: the orthogonal nearest neighbours at")
        print("|Delta|=1 carry a covariance generated in the electron domain,")
        print("upstream of the conversion gain; everything at |Delta| >= sqrt(2),")
        print("including BOTH diagonals and every within-plane pair, carries a")
        print("covariance generated downstream of it.")
        print("")
        print("This does NOT name a circuit.  It says where in the chain the")
        print("noise is generated, which is the most the instrument supports.")
    else:
        print("PREDICTION NOT MET.  Consequence as declared: the two ISO")
        print("signatures are reported as measured and unexplained, and NO")
        print("generation location is claimed for either group.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
