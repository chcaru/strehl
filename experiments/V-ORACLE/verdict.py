#!/usr/bin/env python3
"""The verdict table: (a) capture gap or (b) merge defect, per region.

The two verdicts are distinguished by two INDEPENDENT numbers, and the script
prints both so a reader can see when they disagree.

  1. IS THERE A SHARPER SOURCE FRAME?   ratio = src_signal / mrg_signal.
     ratio <= 1 means the merge already delivers at least as much resolvable
     structure as the sharpest single frame in the bracket.  There is nothing
     to recover, so the merge cannot be the cause.

  2. WAS FOCUS EVER CAPTURED THERE AT ALL?   rise_end.
     rise_end = (V[k*] - V[end]) / (V[k*] - floor) at the nearer bracket end.
     ~1 means the through-focus curve rose to a peak inside the bracket and
     fell away again, so the sweep contained best focus for that tile.
     ~0 means the curve is still AT its maximum on the boundary frame, so the
     sweep ran out before focus did and the frame that would have been sharp
     there was never taken.

  A region that is blurred in the output with ratio<=1 AND rise_end~0 is a
  CAPTURE GAP: no frame was sharp there, and the merge gave back everything
  that was captured.
  A region that is blurred with ratio>>1 is a MERGE DEFECT: the information
  existed in a frame and did not reach the output.

The band is not chosen.  All five are printed, and the verdict is required to
be the same in every band that carries signal; a verdict that appears in one
band only is reported as such rather than promoted.

Usage:  python verdict.py <subject> [--mode point|box]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402
from sites import FLOWERS_SITES, CROP  # noqa: E402

TS = 128


def end_rise(curve):
    k = int(np.argmax(curve))
    floor = float(np.quantile(curve, 0.25))
    pk = float(curve[k])
    if pk - floor <= 0:
        return float("nan"), k
    end = 0 if k <= len(curve) - 1 - k else len(curve) - 1
    return (pk - float(curve[end])) / (pk - floor), k


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--mode", default="point", choices=["point", "box"])
    ap.add_argument("--variant", default="",
                    help="suffix appended to the stage A/B npz stem.  Used ONLY "
                         "by commission_verdict.py to feed this decision rule "
                         "mutated inputs whose correct conclusion is known in "
                         "advance.  Empty means the real measurement.")
    ap.add_argument("--bands", default="1,2,3",
                    help="which bands the (a)/(b) rule may use.  Default 1,2,3. "
                         "ORCH correction #5 binds every lane to name the band "
                         "and the subject's qualification at it; flowers-cpl is "
                         "NOT in V-LINEAR-BANDS.md, and bandfreq.py shows band 1 "
                         "reaches 0.283 cyc/green-px, above the 0.17 floor of "
                         "the corpus boundary range under the less favourable "
                         "grid reading.  '2,3' re-runs the verdict on only the "
                         "bands that are safe under BOTH grid conventions.")
    args = ap.parse_args()
    SIG = tuple(int(x) for x in args.bands.split(","))

    A = np.load(os.path.join(ora.OUT, "stageA",
                             args.subject + args.variant + ".npz"))
    B = np.load(os.path.join(ora.OUT, "stageB",
                             args.subject + args.variant + ".npz"))
    nr, nc = int(A["nr"]), int(A["nc"])
    con, var_k, ks = A["contrast"], A["var_k"], A["frames"]
    mrg = B[f"{args.mode}_sig"]
    K = len(ks)

    print(f"=== {args.subject} :: VERDICT TABLE ({args.mode} sampling) ===")
    print(f"grid {nr}x{nc} tiles of {TS} green px = {2 * TS} master px; "
          f"{K} of {int(A['nframes'])} frames\n")
    hdr = (f"{'site':<5}{'eye':<10}{'tile':<9}" +
           "".join(f"{'b' + str(b) + ' ratio':>11}" for b in range(ora.NBAND)) +
           "".join(f"{'b' + str(b) + ' rise':>10}" for b in range(ora.NBAND)))
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for i, (my, mx, note) in enumerate(FLOWERS_SITES if
                                       args.subject == "flowers-cpl" else []):
        gy0, gx0 = my / 2.0, mx / 2.0
        gy1, gx1 = gy0 + CROP / 2.0, gx0 + CROP / 2.0
        rr = [r for r in range(nr) if gy0 <= (r + 0.5) * TS <= gy1]
        cc = [c for c in range(nc) if gx0 <= (c + 0.5) * TS <= gx1]
        # the tile inside the crop with the MOST resolvable structure at band 2:
        # picking the best tile is adverse to a capture-gap verdict, because it
        # gives the source arm its strongest possible showing at that site.
        sub = con[2][np.ix_(rr, cc)]
        j = int(np.argmax(sub))
        R, C = rr[j // len(cc)], cc[j % len(cc)]
        ratios, rises = [], []
        for b in range(ora.NBAND):
            ratios.append(con[b, R, C] / max(mrg[b, R, C], 1e-9))
            rises.append(end_rise(var_k[:, b, R, C].astype(float))[0])
        eye = "SHARP" if "SHARP" in note else "BLURRED"
        rows.append((i, eye, R, C, ratios, rises))
        print(f"{i:<5}{eye:<10}r{R:02d}c{C:02d}   " +
              "".join(f"{x:11.3f}" for x in ratios) +
              "".join(f"{x:10.2f}" for x in rises))

    print("\nratio = best source frame signal / merge signal, both "
          "noise-corrected.\nrise  = fraction of the through-focus peak that "
          "has decayed by the nearer\n        bracket end.  ~0 = the sweep "
          "ended while the tile was still at its\n        sharpest, i.e. best "
          "focus for that tile was never captured.\n")

    for i, eye, R, C, ratios, rises in rows:
        sig = [b for b in SIG if np.isfinite(ratios[b])]
        beats = [b for b in sig if ratios[b] > 1.25]
        stuck = [b for b in sig if np.isfinite(rises[b]) and rises[b] < 0.10]
        if beats:
            v = (f"(b) MERGE DEFECT -- source beats merge by "
                 f"{max(ratios[b] for b in beats):.2f}x in band(s) {beats}")
        elif len(stuck) == len(sig):
            v = ("(a) CAPTURE GAP -- no frame sharper than the merge, and the "
                 "focus curve is still at its peak on the boundary frame in "
                 "every signal band")
        else:
            v = ("(a) merge not beaten, but the focus curve DID turn over "
                 f"inside the bracket in band(s) "
                 f"{[b for b in sig if b not in stuck]}: focus was captured "
                 "and the merge still matched or beat every frame")
        print(f"  site {i} ({eye:7s}) tile r{R:02d}c{C:02d}: {v}")

    # ---- corpus-level summary for this subject, over every tile ------------
    print(f"\n=== whole-frame summary, all {nr * nc} tiles, "
          f"partitioned so the counts sum ===")
    for b in (1, 2, 3):
        det = con[b] >= np.nanquantile(con[b], 0.90)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = con[b] / np.maximum(mrg[b], 1e-9)
        fin = np.isfinite(ratio)
        n_det_bad = int((det & fin & (ratio > 1.25)).sum())
        n_det_ok = int((det & fin & (ratio <= 1.25)).sum())
        n_det_nan = int((det & ~fin).sum())
        n_other = int((~det).sum())
        tot = n_det_bad + n_det_ok + n_det_nan + n_other
        assert tot == nr * nc, f"{tot} != {nr * nc}"
        worst = ratio[det & fin].max() if (det & fin).any() else float("nan")
        print(f"  band {b}: detail tiles where source beats merge by >1.25x: "
              f"{n_det_bad:4d}  ({100.0 * n_det_bad / (nr * nc):5.2f}% of all "
              f"tiles, {100.0 * n_det_bad / max(det.sum(), 1):5.2f}% of detail "
              f"tiles); worst ratio {worst:.2f}x")
        print(f"          detail-and-merge-not-beaten {n_det_ok:4d} | "
              f"detail-but-unmeasurable {n_det_nan:4d} | "
              f"below detail threshold {n_other:4d} | TOTAL {tot} == {nr * nc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
