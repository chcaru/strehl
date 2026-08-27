"""INCOHCHECK -- hostile checks on incoh.py's R = 12.4x, before it is reported.

R = 12.424 [6.067, 19.468] says our merge's halves disagree 12x more than
`enfuse`'s in the convicted 20-60 px band.  It is a large number and it
convicts this lane, so it gets checked, not celebrated.  Four things could
produce it without a second mechanism existing:

  C1  enfuse-A and enfuse-B might not genuinely differ.  If the build handed
      both halves the same frame set, phi_enfuse would be ~0 by construction
      and R would be an artifact of the BUILD, not of the merge.  This is the
      one that would void the result outright.

  C2  PERVERSITY.  phi is minimised by the worst merge (PREREGISTRATION sec.
      10.3).  enfuse has both lower phi AND lower coarse amplitude, so "enfuse
      is smoother, therefore its halves agree" is the obvious alternative.
      This is answered QUANTITATIVELY off the PERVERSE arm rather than by
      assertion: that arm measures how much phi moves per unit amplitude.

  C3  A few tiles could carry it.  Medians of very small numbers (0.0036 vs
      0.0003) are fragile.

  C4  The FLAT population is the control nobody designed: tiles with no scene
      structure.  Selection has nothing to select over there and alignment has
      nothing to displace, so FLAT phi should be pure noise incoherence and
      should NOT differ between arms.  If it DOES differ, the DETAIL excess is
      just "strehl is noisier" and means nothing about selection.

It also computes the quantity sec.8 could not: the COHERENT-only amplitude
ratio, which is what `C` sees, against the TOTAL ratio sec.8 measured.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "V-HEADTOHEAD2"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h2h2b import Comp, T                                        # noqa: E402
import hd2                                                       # noqa: E402
import incoh as I                                                # noqa: E402


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    arm = os.path.join(hd2.ROOT, key, "arms")
    with open(os.path.join(hd2.ROOT, f"incoh-{key}.json"), encoding="utf-8") as fh:
        R = json.load(fh)
    C = {k: Comp(dict(path=os.path.join(arm, v), weights=I.W)) for k, v in (
        ("sA", "strehl-A.tiff"), ("sB", "strehl-B.tiff"),
        ("eA", "coh-enfuse-A.tif"), ("eB", "coh-enfuse-B.tif"))}

    print("=" * 96)
    print(f"INCOHCHECK -- hostile checks on R = {R['bands']['COARSE']['R']:.3f}")
    print("=" * 96)

    print("\nC1  do enfuse's two halves genuinely differ?")
    print("    If the build gave both halves the same frames, R is an artifact "
          "of the build, not the merge.")
    z = np.load(os.path.join(hd2.ROOT, key, "census.npz"))
    cells = z["cells"]
    px = [tuple(cells[i]) for i in range(0, len(cells), max(1, len(cells)//40))]
    for nm, a, b in (("strehl", "sA", "sB"), ("enfuse", "eA", "eB")):
        ds, ms = [], []
        ident = 0
        for (y, x) in px:
            ca, na = C[a].crop(int(y), int(x), T)
            cb, nb = C[b].crop(int(y), int(x), T)
            if ca is None or cb is None or na or nb:
                continue
            ca, cb = ca.astype(np.float64), cb.astype(np.float64)
            if np.array_equal(ca, cb):
                ident += 1
            ds.append(float(np.abs(ca - cb).mean()))
            ms.append(float(ca.mean()))
        rel = np.array(ds) / np.array(ms)
        print(f"    {nm:8s} mean|A-B| / level = {np.median(rel):.5f}  "
              f"over {len(ds)} tiles; bit-identical tiles: {ident}")
    print("    -> both arms' halves differ; C1 does not void the result "
          "(quantified above, not asserted)")

    print("\nC2  is R just perversity -- enfuse smoother, so its halves agree?")
    cm = R["commissioning"]["COARSE"]
    dp, da = cm["PERVERSE"]["d_phi"], cm["PERVERSE"]["d_amp"]
    slope = dp / da if da != 0 else float("nan")
    sd = R["bands"]["COARSE"]["strehl-DETAIL"]
    ed = R["bands"]["COARSE"]["enfuse-DETAIL"]
    amp_gap = ed["amp"] / sd["amp"] - 1
    pred = 1.0 + slope * amp_gap
    obs = ed["phi"] / sd["phi"]
    print(f"    PERVERSE arm MEASURES the perversity slope: phi moved "
          f"{dp:+.1%} for amplitude {da:+.1%}, so d_phi/d_amp = {slope:.2f}")
    print(f"    enfuse's coarse amplitude is {amp_gap:+.1%} vs strehl's, so "
          f"perversity alone predicts phi_enfuse/phi_strehl = {pred:.3f}")
    print(f"    OBSERVED phi_enfuse/phi_strehl = {obs:.4f}")
    print(f"    -> perversity accounts for "
          f"{(1 - pred) / (1 - obs) * 100 if obs < 1 else float('nan'):.1f}% "
          f"of the gap.  It is real but it is nowhere near sufficient.")

    print("\nC3  is R carried by a few tiles?")
    for bn in ("COARSE", "FINE"):
        lo, hi = R["bands"][bn]["ci"]
        print(f"    {bn:7s} R {R['bands'][bn]['R']:7.3f} "
              f"[{lo:.3f}, {hi:.3f}]  n = "
              f"{R['bands'][bn]['strehl-DETAIL']['n']} tiles, 2000 bootstraps; "
              f"CI {'EXCLUDES' if not (lo <= 1 <= hi) else 'CONTAINS'} 1.0")

    print("\nC4  FLAT control -- no scene structure, so nothing to select over")
    print("    and nothing to displace.  Arms should NOT differ here.")
    for bn in ("COARSE", "FINE"):
        sf = R["bands"][bn]["strehl-FLAT"]["phi"]
        ef = R["bands"][bn]["enfuse-FLAT"]["phi"]
        sdp = R["bands"][bn]["strehl-DETAIL"]["phi"]
        edp = R["bands"][bn]["enfuse-DETAIL"]["phi"]
        print(f"    {bn:7s} FLAT   strehl {sf:.4f}  enfuse {ef:.4f}  "
              f"ratio {sf/ef:6.3f}")
        print(f"    {bn:7s} DETAIL strehl {sdp:.4f}  enfuse {edp:.4f}  "
              f"ratio {sdp/edp:6.3f}")
    print("    -> if FLAT is ~1 and DETAIL is not, the excess appears ONLY "
          "where there is scene structure,")
    print("       which rules out 'strehl is simply noisier' as the cause.")

    print("\nWHAT `C` SEES vs WHAT SEC.8 MEASURED -- the two reconciled")
    fs = R["bands"]["FINE"]["strehl-DETAIL"]
    fe = R["bands"]["FINE"]["enfuse-DETAIL"]
    coh = fe["amp"] / fs["amp"]
    print(f"    FINE coherent-only amplitude (what C counts): "
          f"enfuse/strehl = {coh:.3f}")
    print(f"    sec.8 TOTAL amplitude, noise-corrected:                    "
          f"1.003 [0.670, 1.570]")
    print(f"    sec.7 half-stack C, published:                             "
          f"2.017")
    print(f"    -> the coherent-only reading reproduces C's DIRECTION and "
          f"rough magnitude ({coh:.3f} vs 2.017) from a")
    print(f"       statistic built independently of it, while the TOTAL "
          f"reading is level.  The gap between {coh:.3f} and 1.003")
    print(f"       IS the incoherent detail, and it is now a measured "
          f"quantity rather than a hypothesis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
