"""Solve local windows at different positions in a deep stack.

This is the experiment that separates the two things that both look like
"deep stacks are worse":

  accumulation  the full-stack solve's error at frame i grows with how far i is
                from the reference, because per-step errors compound along the
                path. Local geometry near the far end would then be WRONG in
                the full solve while a local solve of those same frames gets it
                right.

  difficulty    the far end of the stack is simply harder to register -- more
                defocus between neighbours, more breathing, fewer usable tiles.
                A local solve of those frames is then just as bad as the full
                solve's opinion of them, and no amount of solver work helps.

Each window is solved on its own, in isolation, with the same span ladder. Two
quantities come out per window:

  its own cycle floor / refusal rate -> how hard those frames are, on their own
  its disagreement with the full solve -> what the long path cost

If difficulty is flat across positions but disagreement grows towards the ends,
that is accumulation. If difficulty itself grows towards the ends, the deep
stack is harder, not mis-solved.

Frames are copied because D: is read-only and this box cannot make symlinks
without administrator rights. Each window is deleted after it is solved, so
peak disk is one window, not all of them.
"""

import argparse
import json
import os
import shutil
import sys

from sweep import OUT, check_binary, solve

SCRATCH = os.path.join(OUT, "win")


def build_window(srcdir, start, count, label):
    frames = sorted(f for f in os.listdir(srcdir) if f.lower().endswith(".arw"))
    chosen = frames[start:start + count]
    if len(chosen) < count:
        raise SystemExit(f"window {label}: wanted {count} frames from {start}, got {len(chosen)}")
    dest = os.path.join(SCRATCH, label)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    for f in chosen:
        shutil.copy2(os.path.join(srcdir, f), os.path.join(dest, f))
    return dest, chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outfile")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--count", type=int, default=63)
    ap.add_argument("--starts", type=int, nargs="+", required=True)
    ap.add_argument("--keep", action="store_true", help="do not delete the copied frames")
    a = ap.parse_args()

    sha = check_binary()
    print(f"strehl SHA-256 {sha[:16]}... OK")
    os.makedirs(SCRATCH, exist_ok=True)
    path = os.path.join(OUT, a.outfile)

    print(f"{'window':<28}{'heldout':>9}{'cycle':>8}{'drift':>9}{'ref%':>7}{'wall':>8}")
    print("-" * 69)
    with open(path, "a", encoding="utf-8") as fh:
        for start in a.starts:
            label = f"{a.subject}-win{start:03d}n{a.count}"
            dest, chosen = build_window(a.dir, start, a.count, label)
            try:
                r = solve(label, dest, None, None, "window")
                r["window_start"] = start
                r["window_count"] = a.count
                r["first_frame"] = chosen[0]
                r["last_frame"] = chosen[-1]
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                ho = f"{r['heldout']:.3f}" if r.get("heldout") else "-"
                cy = f"{r['cycle_floor']:.3f}" if r.get("cycle_floor") else "-"
                dr = f"{r['drift']:.1f}" if r.get("drift") else "-"
                rf = f"{r['refused_pct']:.1f}" if r.get("refused_pct") is not None else "-"
                print(f"{label:<28}{ho:>9}{cy:>8}{dr:>9}{rf:>7}{r['wall_s']:>8.1f}")
            finally:
                if not a.keep:
                    shutil.rmtree(dest, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
