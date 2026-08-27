"""P42 -- where does sensor quad (3434, 2305) land in a delivered master?

Three coordinates are in circulation for one mote and they do not agree:

    BUILD-DEFECT (me) : quad (3434, 2305)
    V-EYES           : (7008, 4450) on highly-angled-ruler-mm-cpl
    a third lane     : 6776_4322 in a filename

If the lanes have been measuring different places then the -13.28% / -0.78%
disagreement dissolves and nobody is wrong. So this program does not argue
about coordinate conventions; it looks at the delivered master and reports
where the dark disc actually is.

WHAT MY COORDINATE IS, stated so it can be checked rather than believed:

  `DustQuad.px/py` index the grid produced by `strehl_core::defect_map::quad_mean`,
  which averages each 2x2 CFA quad of the ACTIVE AREA. So (3434, 2305) is a
  CFA-QUAD coordinate, in active-area coordinates, PRE-WARP:

      photosite = (2 * 3434, 2 * 2305) = (6868, 4610), active-area relative

  The active-area origin is (0, 0) on every stack in this corpus (measured,
  P39), so photosite coordinates are also raw-buffer coordinates. A delivered
  master is 7032 x 4688 -- one output pixel per photosite, verified below from
  the file size -- so an UNWARPED master would show the mote at (6868, 4610).

  The master is not unwarped. The aligner applies a per-frame similarity, so
  the mote's master coordinate is its sensor coordinate pushed through the
  reference frame's warp. That displacement is what this program measures.

IT IS ALLOWED TO FIND NOTHING. The search window is +/- SEARCH_RADIUS around
the predicted point and a candidate must clear DEPTH_FLOOR. If no pixel in the
window is that dark, it prints that and returns no coordinate.
"""

import os
import sys

import numpy as np
import tifffile

MASTERS = r"C:\dev\strehl-out\acceptance\SHIP-V4"

# Quad coordinate from the shipping embedded map.
QUAD = (3434, 2305)
# Predicted master pixel if the warp were the identity.
PRED = (2 * QUAD[0], 2 * QUAD[1])

# The other two coordinates in circulation, checked at the same time.
OTHERS = {"V-EYES (7008,4450)": (7008, 4450), "third lane 6776_4322": (6776, 4322)}

# Half-width of the search, in master pixels. 400 px is far larger than any
# alignment displacement measured on this corpus (232.7 px corner-to-corner on
# the deepest bracket) so a miss is a real miss, not a window that was too
# small.
SEARCH_RADIUS = 400
# Background support, in master pixels. 64 quads = 128 photosites = 128 master
# pixels, matching ValidateParams::hp_radius so the depths are comparable.
BG_RADIUS = 128
CORE_RADIUS = 16
DEPTH_FLOOR = 0.010


def box_smooth(a, r):
    """Separable box mean, edge-normalised."""
    pad = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(pad, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    y0, x0 = np.arange(h)[:, None], np.arange(w)[None, :]
    y1, x1 = y0 + 2 * r + 1, x0 + 2 * r + 1
    s = c[y1, x1] - c[y0, x1] - c[y1, x0] + c[y0, x0]
    return s / float((2 * r + 1) ** 2)


def disc_mean(a, cy, cx, r):
    y0, y1 = max(0, cy - r), min(a.shape[0], cy + r + 1)
    x0, x1 = max(0, cx - r), min(a.shape[1], cx + r + 1)
    sub = a[y0:y1, x0:x1]
    yy, xx = np.ogrid[y0:y1, x0:x1]
    m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    return float(sub[m].mean())


def main():
    names = sys.argv[1:] or ["highly-angled-ruler-mm-cpl", "coffee-bean", "bee-3-cpl"]
    for name in names:
        path = os.path.join(MASTERS, f"{name}--SHIP-V4.tiff")
        if not os.path.exists(path):
            print(f"{name}: no master at {path}")
            continue
        img = tifffile.imread(path)
        h, w = img.shape[0], img.shape[1]
        print(f"\n=== {name} ===")
        print(f"master        : {w} x {h} x {img.shape[2]} {img.dtype}")
        print(f"quad {QUAD} -> photosite {PRED} -> predicted master pixel {PRED}")
        if w != 7032 or h != 4688:
            print(f"  NOTE: master is {w}x{h}, not the 7032x4688 the map assumes")

        # Luma. Dust attenuates all channels alike, so a plain mean is fine and
        # avoids arguing about weights.
        lum = img.astype(np.float32).mean(axis=2)
        del img

        y0 = max(0, PRED[1] - SEARCH_RADIUS - BG_RADIUS)
        y1 = min(h, PRED[1] + SEARCH_RADIUS + BG_RADIUS + 1)
        x0 = max(0, PRED[0] - SEARCH_RADIUS - BG_RADIUS)
        x1 = min(w, PRED[0] + SEARCH_RADIUS + BG_RADIUS + 1)
        crop = lum[y0:y1, x0:x1]
        bg = box_smooth(crop, BG_RADIUS)
        res = np.where(bg > 1.0, crop / np.maximum(bg, 1e-6) - 1.0, 0.0)
        # Suppress the frame-edge band: the box mean is truncated there and its
        # residual is a border artifact, not a mote. Measured on the flats: the
        # 40 deepest "blobs" with an 8 px border were all frame edge.
        inner = res[BG_RADIUS:-BG_RADIUS or None, BG_RADIUS:-BG_RADIUS or None]
        sd = float(inner.std())
        print(f"residual sd   : {100 * sd:.3f}% over the {inner.shape} search box")

        # Smooth at the mote scale before hunting a minimum, or the deepest
        # pixel is simply the noisiest one.
        sm = box_smooth(res, CORE_RADIUS)
        sm[:BG_RADIUS, :] = 0
        sm[-BG_RADIUS:, :] = 0
        sm[:, :BG_RADIUS] = 0
        sm[:, -BG_RADIUS:] = 0
        j = int(np.argmin(sm))
        cy, cx = divmod(j, sm.shape[1])
        depth = float(sm[cy, cx])
        my, mx = cy + y0, cx + x0
        if -depth < DEPTH_FLOOR:
            print(
                f"NOTHING FOUND: deepest point in +/-{SEARCH_RADIUS}px is "
                f"{100 * depth:+.3f}%, above the {-100 * DEPTH_FLOOR:.1f}% floor"
            )
        else:
            print(
                f"deepest       : master ({mx}, {my})  {100 * depth:+.3f}%  "
                f"displaced ({mx - PRED[0]:+d}, {my - PRED[1]:+d}) from prediction"
            )

        print("  reading each circulating coordinate at r=%d:" % CORE_RADIUS)
        probes = {f"BUILD-DEFECT {PRED}": PRED}
        probes.update(OTHERS)
        for label, (px, py) in probes.items():
            if not (x0 <= px < x1 and y0 <= py < y1):
                print(f"    {label:26} outside the search box (+/-{SEARCH_RADIUS}px)")
                continue
            near_edge = px < BG_RADIUS or py < BG_RADIUS or px >= w - BG_RADIUS or py >= h - BG_RADIUS
            d = disc_mean(res, py - y0, px - x0, CORE_RADIUS)
            flag = "  [within %dpx of the frame edge: background box is truncated]" % BG_RADIUS
            print(
                f"    {label:26} {100 * d:+7.3f}%   ({d / sd:+5.2f} sd of local residual)"
                f"{flag if near_edge else ''}"
            )

        # Print, then TEST. The master-domain residual is dominated by subject
        # structure at this corner, so a reading is only evidence if it clears
        # the local scatter. Gate on it rather than tabling it.
        best = min(disc_mean(res, py - y0, px - x0, CORE_RADIUS)
                   for (px, py) in probes.values()
                   if x0 <= px < x1 and y0 <= py < y1)
        if abs(best) < 3.0 * sd:
            print(
                f"  VERDICT: UNDERPOWERED. The deepest circulating coordinate reads "
                f"{100 * best:+.3f}%, which is {abs(best) / sd:.2f} sd of a residual "
                f"whose sd is {100 * sd:.3f}%. This master cannot decide whether a "
                f"~3.5% mote is present; it decides nothing in either direction."
            )
        else:
            print(
                f"  VERDICT: DETECTED at {100 * best:+.3f}% = {abs(best) / sd:.2f} sd."
            )


if __name__ == "__main__":
    main()
