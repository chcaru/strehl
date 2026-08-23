"""The scale centre, and whether one fixed centre explains the translation.

M3 measured the similarity's scale centre at sensor **(-22, -113) px** — not the
image centre — on a shallow stack under a fixed reference. If in-camera focus
bracketing really is pure magnification about a fixed optical point, then across
a 105-frame sweep the whole translation should be predicted by

    B_j = (1 - A_j) * c

for a single complex constant `c`. That is strategy `S5`. This script fits `c`
and reports how much worse the constrained model is than a free per-frame `B`,
which is the registered falsifier 3 for candidate (c).
"""

import numpy as np

from m10_lib import RHO, corner_err, read_edges, relative, solve_poly

CASES = {
    "coffee-bean": ("data/coffee-bean-edges.csv", 105),
    "109MSDCF": ("data/shallow-109-edges.csv", 22),
    "119MSDCF": ("data/shallow-119-edges.csv", 33),
}
# The plane is a CFA quad plane, so one plane px is two sensor px.
PLANE_W, PLANE_H = 3516, 2344


def resid(sol, edges):
    v = [corner_err(relative(sol[e.i], sol[e.j]), e.t()) for e in edges if e.ok]
    return float(np.median(v)), float(np.percentile(v, 90))


def main():
    print("=" * 88)
    print("S5  IS THE TRANSLATION PURE MAGNIFICATION ABOUT ONE FIXED CENTRE?")
    print("  B_j = (1 - A_j) * c, one complex c for the whole stack.")
    print("  Centres are plane px from the plane centre, and the sensor")
    print("  equivalent, which is what M3 quoted: M3 measured (-22, -113) px.")
    print("=" * 88)
    for case, (path, n) in CASES.items():
        print(f"\n{case}")
        for cfg in ["m10", "wide64"]:
            rows = [e for e in read_edges(path, cfg=cfg) if e.ok]
            med = np.median([e.span for e in rows])
            del med
            band = [e for e in rows if e.span >= 8] or rows
            for deg in (4, 6):
                s5, c = solve_poly(band, n, deg, scheme="unit",
                                   fixed_centre=True)
                s4, _ = solve_poly(band, n, deg, scheme="unit",
                                   bdeg=min(deg, 4))
                free, _ = solve_poly(band, n, deg, scheme="unit")
                m5, p5 = resid(s5, band)
                m4, p4 = resid(s4, band)
                mf, pf = resid(free, band)
                print(f"  cfg={cfg:<7} deg={deg}  centre = "
                      f"({c.real:+8.1f}, {c.imag:+8.1f}) plane px = "
                      f"({2 * c.real:+9.1f}, {2 * c.imag:+9.1f}) sensor px")
                print(f"    training residual, plane px   median / p90")
                print(f"      S5 one fixed centre  {m5:>8.3f} {p5:>8.3f}")
                print(f"      S4 polynomial B      {m4:>8.3f} {p4:>8.3f}")
                print(f"      free per-frame B     {mf:>8.3f} {pf:>8.3f}")
                print(f"      S5 / free ratio      {m5 / max(mf, 1e-9):>8.3f}"
                      "   (falsifier 3 trips above 3.0)")
    print()
    print("  rho = %.2f plane px; plane is %d x %d." % (RHO, PLANE_W, PLANE_H))


if __name__ == "__main__":
    raise SystemExit(main())
