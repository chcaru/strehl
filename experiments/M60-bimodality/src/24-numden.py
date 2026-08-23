"""M60 / 24 -- report the NUMERATOR and the DENOMINATOR separately.

AGENTS rule 39 / discipline 338: a ratio must be publishable as its two parts,
so a reader can check that the denominator is not doing the work.  12-analyse.py
already keeps prom, denom and z separate internally; this prints them per cell so
the report can quote real-cell numbers rather than plant numbers.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cells import CELLS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
CUR = os.path.join(DATA, "curves")
NUL = os.path.join(DATA, "null")


def main():
    import importlib
    A = importlib.import_module("12-analyse")
    print("=" * 78)
    print("numerator and denominator, separately, on the REAL cells")
    print("  prom = f(k2) - f(kd)  DN      denom = sqrt(sig_f(k2)^2 + sig_f(kd)^2)  DN")
    print("=" * 78)
    rows = []
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        p = os.path.join(CUR, "%s__%s.npz" % (stack, name))
        pn = os.path.join(NUL, "%s__%s.npz" % (stack, name))
        if not (os.path.exists(p) and os.path.exists(pn)):
            continue
        d = np.load(p, allow_pickle=True)
        dn = np.load(pn, allow_pickle=True)
        band = d["lab"] == 0
        re = A.detect(np.ascontiguousarray(d["F"][:, band]),
                      np.maximum(np.ascontiguousarray(d["S"][:, band]), 1e-6))
        nu = A.detect(np.ascontiguousarray(dn["F"][:, band]),
                      np.maximum(np.ascontiguousarray(dn["S"][:, band]), 1e-6))
        zst = float(np.percentile(nu["z"], 99))
        rows.append(dict(cell=name, cls=cls, zstar=zst,
                         prom=float(np.median(re["prom"])),
                         denom=float(np.median(re["denom"])),
                         z=float(np.median(re["z"])),
                         z_p90=float(np.percentile(re["z"], 90)),
                         prom_null=float(np.median(nu["prom"])),
                         z_null=float(np.median(nu["z"]))))
        r = rows[-1]
        print("  %-18s %-8s prom %7.2f DN  denom %6.3f DN  z med %6.2f  z p90 %7.2f"
              "  | z* %5.2f | null prom %6.2f DN  null z %5.2f"
              % (name, cls, r["prom"], r["denom"], r["z"], r["z_p90"],
                 r["zstar"], r["prom_null"], r["z_null"]))
    print()
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r for r in rows if r["cls"] == cls]
        print("  %-9s n=%2d  prom med %7.2f DN (%.2f-%.2f)  denom med %6.3f DN"
              "  z med %6.2f (%.2f-%.2f)  z* %5.2f-%5.2f"
              % (cls, len(v),
                 np.median([r["prom"] for r in v]),
                 min(r["prom"] for r in v), max(r["prom"] for r in v),
                 np.median([r["denom"] for r in v]),
                 np.median([r["z"] for r in v]),
                 min(r["z"] for r in v), max(r["z"] for r in v),
                 min(r["zstar"] for r in v), max(r["zstar"] for r in v)))
    print()
    print("  Read the prom column, not just z: if the denominators were doing the")
    print("  work the classes would separate on denom and not on prom.")

    # P5 predicts lobe height proportional to the edge contrast dI, so the
    # numerator should track band contrast and NOT the class label.
    ap = os.path.join(DATA, "20-audit.json")
    if os.path.exists(ap):
        from scipy.stats import spearmanr
        with open(ap, encoding="utf-8") as fh:
            tex = {t["cell"]: t for t in json.load(fh)["texture"]}
        print()
        print("=" * 78)
        print("does the numerator track EDGE CONTRAST rather than the class label?")
        print("  P5: a defocus side-lobe has height proportional to the step dI")
        print("=" * 78)
        xs, ys, cs = [], [], []
        for r in rows:
            t = tex.get(r["cell"])
            if not t:
                continue
            xs.append(t["band_peak"]); ys.append(r["prom"]); cs.append(r["cls"])
        xs, ys = np.array(xs), np.array(ys)
        rho, p = spearmanr(xs, ys)
        print("  Spearman(prom, band peak focus response) over %d cells = %+.3f  p=%.3g"
              % (len(xs), rho, p))
        for cls in ("occ", "occ_flat", "ctl"):
            m = np.array([c == cls for c in cs])
            print("  %-9s n=%2d  prom / band-peak median %.4f"
                  % (cls, m.sum(), np.median(ys[m] / xs[m])))
        print()
        print("  If prom/band-peak is the same for occ and occ_flat, the extra raw")
        print("  prominence at occ cells is their extra edge contrast, not depth.")

    with open(os.path.join(DATA, "24-numden.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print("\nwrote data/24-numden.json")


if __name__ == "__main__":
    main()
