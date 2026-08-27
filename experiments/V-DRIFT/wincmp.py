"""Compare a full-stack solve against isolated local solves of the same frames.

The distinction this makes is the one the whole hypothesis turns on.

A merge combines, at any output pixel, the frames in which that pixel is in
focus -- a contiguous run of neighbouring indices. What can destroy detail is
therefore *relative* misregistration between frames that are CLOSE together in
the stack. A slowly-accumulating error in absolute placement moves neighbouring
frames together, as a smooth low-frequency warp: it displaces the output
slightly but does not blur it, because the frames being combined are still
right with respect to each other.

So the accumulation hypothesis needs more than "absolute error grows with
depth". It needs local relative geometry to be wrong at depth. That is what
this measures: for every pair of frames within a window, separated by `sep`
indices, how much do the full solve and an isolated local solve disagree about
the map between them?

  disagreement at small sep, growing with stack position  -> accumulation is
      reaching into local geometry and can blur the merge
  disagreement flat, or confined to large sep             -> the long path
      costs absolute placement only, which the merge does not see
"""

import argparse
import json
import os
import statistics
import sys

from wm import WarpMap


def rel_between(wm, i, j):
    r = wm.a[j] / wm.a[i]
    s = wm.b[j] - r * wm.b[i]
    return r, s


def disagreement(full, win, gi, gj, li, lj):
    """Corner error between the two solves' opinion of the map gi->gj."""
    r1, s1 = rel_between(full, gi, gj)
    r2, s2 = rel_between(win, li, lj)
    da, db = r1 - r2, s1 - s2
    w, h = full.width / 2.0, full.height / 2.0
    cs = [complex(-w, -h), complex(w, -h), complex(-w, h), complex(w, h)]
    return max(abs(da * c + db) for c in cs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("full_wm")
    ap.add_argument("windows_jsonl")
    ap.add_argument("--seps", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32])
    a = ap.parse_args()

    full = WarpMap(a.full_wm)
    print(f"full solve: {full.name}, {len(full.placed())} frames, spans {full.spans}")
    print(f"  heldout {full.heldout_px:.3f} px, cycle floor {full.cycle_floor_px:.3f} px")
    print()
    print("Median disagreement (plane px) between the full solve and an isolated")
    print("local solve, for frame pairs separated by `sep` indices inside each window.")
    print()
    hdr = f"{'window (global frames)':<28}{'cycle':>7}" + "".join(f"{'sep' + str(s):>9}" for s in a.seps)
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for line in open(a.windows_jsonl):
        rec = json.loads(line)
        if rec.get("rc") != 0 or not os.path.exists(rec["warpmap"]):
            continue
        win = WarpMap(rec["warpmap"])
        start, count = rec["window_start"], rec["window_count"]
        cells, detail = [], {}
        for sep in a.seps:
            vals = []
            for li in range(0, count - sep):
                lj = li + sep
                gi, gj = start + li, start + lj
                if gi in full.a and gj in full.a and li in win.a and lj in win.a:
                    vals.append(disagreement(full, win, gi, gj, li, lj))
            if vals:
                cells.append(f"{statistics.median(vals):>9.3f}")
                detail[sep] = statistics.median(vals)
            else:
                cells.append(f"{'-':>9}")
        label = f"{start}-{start + count - 1}"
        print(f"{label:<28}{rec['cycle_floor']:>7.3f}" + "".join(cells))
        rows.append((start, rec["cycle_floor"], detail))

    print()
    print("Reading: sep=1..8 is the range a merge actually combines. If those columns")
    print("are flat across windows, the full solve's LOCAL geometry is as good at the")
    print("far end as at the near end, and accumulation is not reaching the merge.")

    for sep in a.seps:
        vals = [d.get(sep) for _, _, d in rows if d.get(sep) is not None]
        if len(vals) >= 2:
            lo, hi = min(vals), max(vals)
            print(f"  sep {sep:<3} across windows: min {lo:.3f}  max {hi:.3f}  "
                  f"ratio {hi / lo if lo > 0 else float('inf'):.2f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
