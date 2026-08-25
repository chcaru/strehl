"""O6 -- the flat control fired. Decompose the floor before interpreting anything.

o5 measured D = +1.3343 / +2.8310 / +2.7989 % on the detail ROIs and +1.6251 %
on ROI-FLAT. The flat control was pre-registered to read |D| < 1 %. It did not.
ROI-FLAT has contrast 1.18 -- there is no detail there to elect well or badly --
so a positive D there is a FLOOR that is not election error, and it is larger
than the whole reading on ROI-LOWDRIFT.

Control N0 could not have caught this. It ran on a synthetic ramp built from ONE
source frame, so every synthetic frame sat at the same exposure level. On the
real capture the level varies frame to frame, and the two rules treat level
differently:

    elector  box(|g|) / box(sigma)      <- divides by a level-dependent sigma
    oracle   box(g^2) - noise           <- does not

A rule that divides by sigma prefers frames at LOWER signal level, because sigma
grows with level. A rule that does not, prefers frames with more absolute
gradient energy, which grows with level. On a featureless field that is a
systematic disagreement with nothing to do with focus.

This script decomposes the floor by swapping one ingredient at a time. All four
variants are scored by the SAME evaluator on G2, so only the SELECTION rule
changes between arms:

    E       box(|g|) / box(sigma)          the product's rule
    E_raw   box(|g|)                       product's rule, divisor removed
    O       box(g^2) - noise               the oracle
    O_div   (box(g^2) - noise) / box(sigma)^2   oracle, divisor added

If the floor is the divisor, D(E vs O_div) collapses on ROI-FLAT while
D(E_raw vs O) does not -- and the reverse if it is magnitude-vs-energy.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import o2lib as O  # noqa: E402
from o3_commission import CUBE, OUTD  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROIS = ["ROI-FLAT", "ROI-LOWDRIFT", "ROI-MIDDRIFT", "ROI-HIGHDRIFT"]


def variants(img, noise):
    """All four selection scores from one shared Sobel/box pass."""
    mag, e = O.sobel_mag2(img)
    bm = O.box_mean(mag)
    be = O.box_mean(e)
    bs = np.maximum(O.box_mean(np.maximum(noise.sigma(img[1:-1, 1:-1]), O.EPS)), O.EPS)
    nz = O.box_mean(O.conv3(noise.var(img), O.NOISE_K))
    return {"E": bm / bs, "E_raw": bm, "O": be - nz, "O_div": (be - nz) / (bs * bs)}


def main() -> int:
    meta = json.load(open(os.path.join(CUBE, "cube_meta.json"), encoding="utf-8"))
    n, black = meta["n"], meta["black"]

    f1 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g1.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    f2 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g2.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    noise, _ = O.fit_noise(f1.reshape(-1, f1.shape[-1]), f2.reshape(-1, f2.shape[-1]), black)
    del f1, f2
    print(f"noise model: {noise}")

    print("\nframe-to-frame LEVEL variation, the thing N0 could not see:")
    lv = {nm: np.array([r[nm][0] for r in meta["levels"]]) for nm in ROIS}
    for nm in ROIS:
        a = lv[nm]
        print(f"  {nm:14s} mean {a.mean():8.1f} DN  min {a.min():8.1f}  max {a.max():8.1f}"
              f"  spread {100.0*(a.max()-a.min())/a.mean():6.2f} %")

    res = {"levels": {nm: dict(mean=float(lv[nm].mean()), min=float(lv[nm].min()),
                               max=float(lv[nm].max())) for nm in ROIS}, "rois": {}}

    for nm in ROIS:
        print("\n" + "=" * 74)
        print(nm)
        g1 = np.load(os.path.join(CUBE, f"{nm}.g1.npy"), mmap_mode="r")
        g2 = np.load(os.path.join(CUBE, f"{nm}.g2.npy"), mmap_mode="r")

        best, arg = {}, {}
        for f in range(n):
            v = variants(g1[f].astype(np.float64), noise)
            for k, s in v.items():
                if k not in best:
                    best[k] = s.copy()
                    arg[k] = np.zeros(s.shape, dtype=np.int32)
                else:
                    m = s > best[k]
                    best[k][m] = s[m]
                    arg[k][m] = f
        del best

        ev = {k: np.zeros(arg["E"].shape, dtype=np.float64) for k in arg}
        for f in range(n):
            s = O.oracle_score(g2[f].astype(np.float64), noise)
            for k, idxmap in arg.items():
                m = idxmap == f
                if m.any():
                    ev[k][m] = s[m]

        row = {}
        for sel, ref, lab in (("E", "O", "D(E vs O)      headline"),
                              ("E_raw", "O", "D(E_raw vs O)  divisor off elector"),
                              ("E", "O_div", "D(E vs O_div)  divisor on oracle"),
                              ("E_raw", "O_div", "D(E_raw vs O_div)")):
            d = (1.0 - float(ev[sel].mean()) / float(ev[ref].mean())) * 100.0
            row[f"{sel}|{ref}"] = d
            print(f"  {lab:34s} = {d:+8.4f} %")
        agree = float(np.mean(arg["E"] == arg["O"])) * 100.0
        agree_div = float(np.mean(arg["E"] == arg["O_div"])) * 100.0
        print(f"  elector == oracle          {agree:.4f} %")
        print(f"  elector == oracle+divisor  {agree_div:.4f} %")
        row["agree_pct"] = agree
        row["agree_div_pct"] = agree_div
        res["rois"][nm] = row
        del g1, g2, ev, arg

    print("\n" + "=" * 74)
    print("DECOMPOSITION on the flat control (no detail, so any D is floor):")
    fl = res["rois"]["ROI-FLAT"]
    print(f"  headline floor            {fl['E|O']:+.4f} %")
    print(f"  with divisor on oracle    {fl['E|O_div']:+.4f} %")
    print(f"  with divisor off elector  {fl['E_raw|O']:+.4f} %")
    drop = abs(fl["E|O"]) - abs(fl["E|O_div"])
    print(f"  -> giving the oracle the same divisor moves the floor by {drop:+.4f} pp")
    res["floor_explained_by_divisor_pp"] = drop

    print("\nELECTION ERROR IN EQUIVALENT FRAMES (floor-subtracted, P1r yardstick):")
    o5 = json.load(open(os.path.join(OUTD, "o5_deficit.json"), encoding="utf-8"))
    floor = o5["rois"]["ROI-FLAT"]["D_pct"]
    eq = {}
    for nm in ROIS:
        if nm == "ROI-FLAT":
            continue
        d = o5["rois"][nm]["D_pct"]
        s1 = o5["rois"][nm]["one_frame_sens_pct"]
        e = (d - floor) / s1
        eq[nm] = dict(D_pct=d, floor_pct=floor, excess_pct=d - floor,
                      one_frame_pct=s1, equiv_frames=e)
        print(f"  {nm:14s} D {d:+.4f} % - floor {floor:+.4f} % = {d-floor:+.4f} %"
              f"  /  {s1:.4f} % per frame  =  {e:+.4f} frames")
    res["equiv_frames"] = eq
    with open(os.path.join(OUTD, "o6_decompose.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"\nwrote {os.path.join(OUTD, 'o6_decompose.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
