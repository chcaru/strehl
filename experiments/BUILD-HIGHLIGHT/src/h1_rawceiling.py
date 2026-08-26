"""Where do foam's RAW channels actually run out?

WHY THIS EXISTS. The whole fix hinges on a threshold, and my brief warns in
capital letters that "a threshold expressed as a fraction of a nominal maximum
is a trap when the real maximum is lower". `clip.rs` says the container maximum
is 16383 and `Levels::white` is 15360; `clip_highlights` triggers on the former.
If foam's sensels never reach 16383 then the shipped trigger is structurally
incapable of firing on this subject, and no amount of tuning downstream of it
matters. So: measure, per CFA plane, on real frames, with an INDEPENDENT decoder
(rawpy/LibRaw, not strehl's own rawler path) so the number is not the pipeline
marking its own homework.

AGENTS rule 32: `raw_image_visible` is a view into LibRaw's buffer. Copy inside
the `with`.

AGENTS rule 7: statistics are taken on the ACTIVE AREA only. rawpy's
`raw_image_visible` is already the visible frame, which is the active area; its
shape is asserted against the geometry `strehl probe` reports.
"""

import sys
from pathlib import Path

import numpy as np
import rawpy

# `strehl probe D:\personal\macro\foam` on this tree, 2026-08-26:
#   levels: black 512, white 15360 ; active area 7032 x 4688 ; wb [2.680664, 1, 1.5253906]
BLACK = 512.0
WHITE = 15360.0
CONTAINER = 16383.0
#
# NOTE, measured not assumed: LibRaw's visible frame is 4688 x 7028, four
# columns narrower than the 7032 rawler reports. That is a decoder difference in
# where the active area's right edge is placed, it is 0.06% of the width, and it
# cannot manufacture or hide a saturation ceiling. Recorded rather than silenced.
ACTIVE = (4688, 7028)

# RGGB: plane -> (row offset, col offset)
PLANES = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}


def one(path):
    with rawpy.imread(str(path)) as r:
        v = r.raw_image_visible.astype(np.float64)  # copy on the same line
    assert v.shape == ACTIVE, f"{path.name}: shape {v.shape}, expected {ACTIVE}"
    out = {}
    for name, (dy, dx) in PLANES.items():
        p = v[dy::2, dx::2]
        out[name] = {
            "max": float(p.max()),
            "p99.99": float(np.percentile(p, 99.99)),
            "at_container": float((p >= CONTAINER).mean()),
            "at_white": float((p >= WHITE).mean()),
        }
    return out


def main():
    stack = Path(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    frames = sorted(stack.glob("*.ARW"))
    assert frames, f"no ARW under {stack}"
    step = max(1, len(frames) // limit)
    picked = frames[::step][:limit]
    print(f"stack {stack}  ({len(frames)} frames, sampling {len(picked)} evenly)")
    print(f"black {BLACK:.0f}  white {WHITE:.0f}  container {CONTAINER:.0f}")
    print()
    print(f"  {'frame':<14} {'plane':>5} {'max DN':>8} {'p99.99':>9} "
          f"{'>=16383':>10} {'>=15360':>10} {'max/cont':>9}")
    agg = {k: 0.0 for k in PLANES}
    agg_container = {k: 0.0 for k in PLANES}
    for f in picked:
        st = one(f)
        for name in PLANES:
            s = st[name]
            agg[name] = max(agg[name], s["max"])
            agg_container[name] += s["at_container"]
            print(f"  {f.name:<14} {name:>5} {s['max']:8.0f} {s['p99.99']:9.1f} "
                  f"{s['at_container'] * 100:9.4f}% {s['at_white'] * 100:9.4f}% "
                  f"{s['max'] / CONTAINER:9.4f}")
    print()
    print("  ACROSS THE SAMPLED FRAMES")
    for name in PLANES:
        print(f"    {name:>3}: max {agg[name]:8.0f}   "
              f"= {agg[name] / CONTAINER * 100:6.2f}% of container, "
              f"{agg[name] / WHITE * 100:6.2f}% of Levels::white   "
              f"mean fraction at container {agg_container[name] / len(picked) * 100:.4f}%")
    print()
    gmax = max(agg["G1"], agg["G2"])
    if gmax >= CONTAINER:
        print("  VERDICT: green DOES reach the container maximum. `clip_highlights`'s")
        print("           trigger is reachable per-frame.")
    else:
        print("  VERDICT: green NEVER reaches the container maximum on these frames.")
        print("           A trigger written as `v >= CONTAINER_MAX_DN` cannot fire here,")
        print("           per frame OR after any average. The real ceiling is lower.")


if __name__ == "__main__":
    main()
