"""POPCHECK -- are the two arms read on the SAME tiles, and are the dropped
tiles a biased subset?

fullhp.py's reading prints '86 matched / 24 dropped' for BOTH arms.  Equal
COUNTS are not equal SETS, and the verdict assumes the arms are compared on the
same scene.  Two questions, both answerable and neither answered by the counts:

  Q1  Are the 86 surviving DETAIL tiles the same cells in both arms?  If the
      arms drop different tiles they are being read on different scenes and the
      ratio is not a like-for-like comparison.

  Q2  Are the 24 dropped tiles a biased subset -- specifically, are they the
      brightest or the most detailed?  A drop rule that removes the highest-
      detail tiles measures a different question than the one asked.  The rule
      drops a DETAIL tile when fewer than KMIN FLAT tiles lie within LOGTOL of
      its level, so the drops are expected at the EXTREMES of the level range,
      where FLAT tiles run out.  That is a prediction, so it is testable.

Neither question can flatter the project: a failure on Q1 invalidates the
reading and a failure on Q2 bounds it.
"""
import sys
import json
import os
import numpy as np
import fullhp as F
import hd2


def keepmask(lvD, lvF, bpF):
    """Which DETAIL tiles survive level-matching.  scene_matched() returns only
    the count, so the mask is recomputed here from the same predicate."""
    return np.array([F.noise_at(L, lvF, bpF) is not None for L in lvD], bool)


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    arm = os.path.join(hd2.ROOT, key, "arms")
    sp = os.path.join(arm, "strehl-full.tiff")
    ep = os.path.join(arm, "coh-enfuse-full.tif")
    with open(os.path.join(hd2.ROOT, key, "geom-full.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    s = float(g["strehl-full_vs_enfuse-full"]["scale"])
    BAND_C = (F.BAND[0] * s, F.BAND[1] * s)
    z = np.load(os.path.join(hd2.ROOT, key, "census.npz"))
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    FLAT = [tuple(cells[i]) for i in flat]

    S = F.Comp(dict(path=sp, weights=F.W))
    E = F.Comp(dict(path=ep, weights=F.W))
    lvS, bpS = F.tiles(S, DET, F.BAND)
    lvF, bpF = F.tiles(S, FLAT, F.BAND)
    P = F.Placer(S, E, s)
    elv, ebp = F.tiles(E, DET, BAND_C, placer=P)
    elvF, ebpF = F.tiles(E, FLAT, BAND_C, placer=P)

    keepS = keepmask(lvS, lvF, bpF)
    keepE = keepmask(elv, elvF, ebpF)
    kS, kE = set(np.flatnonzero(keepS)), set(np.flatnonzero(keepE))

    print("=" * 96)
    print(f"POPCHECK -- tile population identity and drop bias, {key}")
    print("=" * 96)
    print(f"\nQ1  same tiles in both arms?")
    print(f"    strehl keeps {len(kS)}, enfuse keeps {len(kE)}, "
          f"intersection {len(kS & kE)}")
    only_s, only_e = sorted(kS - kE), sorted(kE - kS)
    print(f"    kept by strehl only: {len(only_s)} {only_s[:10]}")
    print(f"    kept by enfuse only: {len(only_e)} {only_e[:10]}")
    q1 = (kS == kE)
    print(f"    -> {'IDENTICAL populations' if q1 else 'POPULATIONS DIFFER'}")
    if not q1:
        both = np.array(sorted(kS & kE), int)
        sS = np.array([bpS[i] - F.noise_at(lvS[i], lvF, bpF) for i in both])
        sE = np.array([ebp[i] - F.noise_at(elv[i], elvF, ebpF) for i in both])
        r = F.ratio_of(float(np.median(sS)), float(np.median(sE)))
        print(f"    re-read on the {len(both)} tiles BOTH arms keep: "
              f"ratio {r:.4f}  (as-run 1.003)")

    print(f"\nQ2  are the {len(lvS) - len(kS)} dropped tiles a biased subset?")
    drop = np.flatnonzero(~keepS)
    keep = np.flatnonzero(keepS)
    lo, hi = float(np.min(lvF)), float(np.max(lvF))
    print(f"    FLAT tile level range {lo:.0f} .. {hi:.0f}  "
          f"(a DETAIL tile needs >= {F.KMIN} FLAT within {F.LOGTOL} in log)")
    print(f"    {'set':10s} {'n':>4s} {'median level':>13s} "
          f"{'min':>8s} {'max':>8s} {'median bp':>12s}")
    for lab, idx in (("kept", keep), ("dropped", drop)):
        if len(idx) == 0:
            continue
        print(f"    {lab:10s} {len(idx):4d} {np.median(lvS[idx]):13.0f} "
              f"{np.min(lvS[idx]):8.0f} {np.max(lvS[idx]):8.0f} "
              f"{np.median(bpS[idx]):12.4e}")
    if len(drop):
        out = int(np.sum((lvS[drop] > hi) | (lvS[drop] < lo)))
        print(f"    dropped tiles outside the FLAT level range entirely: "
              f"{out}/{len(drop)}")
        above = int(np.sum(lvS[drop] > np.median(lvS)))
        print(f"    dropped tiles above the median DETAIL level: "
              f"{above}/{len(drop)}")
        bk, bd = bpS[keep], bpS[drop]
        rng = np.random.default_rng(0)
        d = float(np.median(bd) - np.median(bk))
        pool = np.concatenate([bk, bd])
        null = np.empty(4000)
        for i in range(4000):
            p = rng.permutation(pool)
            null[i] = np.median(p[:len(bd)]) - np.median(p[len(bd):])
        pv = float(np.mean(np.abs(null) >= abs(d)))
        print(f"    median bp(dropped) - median bp(kept) = {d:+.4e}  "
              f"permutation p = {pv:.3f}")
        print(f"    -> {'NO detectable detail bias in the drop rule' if pv > 0.05 else 'DROP RULE IS DETAIL-BIASED'}")
        if pv <= 0.05:
            print(f"    NOTE: a biased drop is only a DIFFERENTIAL problem if "
                  f"the arms drop different tiles.  Q1 says they do not, so "
                  f"this")
            print(f"    restricts what the reading DESCRIBES (the level-"
                  f"matchable 86) without biasing the ratio between arms.")

    print(f"\nQ3  how much does the reading move with the drop rule's own "
          f"parameters?")
    print(f"    If the verdict depends on LOGTOL/KMIN it is an artifact of the "
          f"matching rule, not of the images.")
    print(f"    {'LOGTOL':>7s} {'KMIN':>5s} {'n kept':>7s} "
          f"{'S strehl':>11s} {'S enfuse':>11s} {'ratio':>7s}")
    base = (F.LOGTOL, F.KMIN)

    def matched(lvD, bpD, lvFF, bpFF, tol):
        """Recomputed here rather than via scene_matched(), because noise_at's
        `bw=LOGTOL` default is bound at def time and would ignore the sweep."""
        out = []
        for L, b in zip(lvD, bpD):
            n = F.noise_at(L, lvFF, bpFF, bw=tol)
            if n is not None:
                out.append(b - n)
        return np.array(out)

    try:
        for tol, kmin in ((0.10, 3), (0.15, 3), (0.25, 3), (0.40, 3),
                          (0.15, 2), (0.15, 5), (0.15, 8)):
            F.KMIN = kmin
            dS = matched(lvS, bpS, lvF, bpF, tol)
            dE = matched(elv, ebp, elvF, ebpF, tol)
            nS, nE = len(dS), len(dE)
            if nS == 0 or nE == 0 or nS != nE:
                print(f"    {tol:7.2f} {kmin:5d} {nS:3d}/{nE:<3d} "
                      f"{'':>11s} {'':>11s}  unequal n -- not comparable")
                continue
            sS, sE = float(np.median(dS)), float(np.median(dE))
            print(f"    {tol:7.2f} {kmin:5d} {nS:7d} {sS:11.4e} {sE:11.4e} "
                  f"{F.ratio_of(sS, sE):7.3f}"
                  f"{'   <- as run' if (tol, kmin) == base else ''}")
    finally:
        F.LOGTOL, F.KMIN = base
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
