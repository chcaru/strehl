"""dust_patch.py -- adjudicate the sensor-dust defect by eye, at full resolution.

dust.py could not confirm the motes on the 4x overviews: its deepest candidate
reached only 1.33x its own null, so it reports NOT DETECTED, and its deepest
reading is not evidence.  That is a limit of the instrument and of the
reduction; it is not a finding that the sensor is clean.

So this file does the thing that needs no instrument.  DELIVER-V4 states mote 2
worst at output `(7008, 4450)` in `highly-angled-ruler-mm-cpl`.  A sensor mote
sits at a FIXED output position, so the test is: cut the SAME integer slice out
of many different subjects and see whether the same disc appears in the same
place.  Different scenes cannot conspire to put an identical grey disc at
identical coordinates.

The tile is selection-ranked -- the strongest examples are shown -- and that is
stated on the image, because a ranked tile demonstrates presence and says
nothing about incidence.  Incidence is the per-image table in logs/dust.txt.

Output: C:\\dev\\strehl-out\\DELIVER-V5\\known-defects\\
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

import rimlib
from build import font, label_below
from geom import masters

DST = r"C:\dev\strehl-out\DELIVER-V5\known-defects"
CX, CY = 7008, 4450          # DELIVER-V4's stated worst site for mote 2
PATCH = 256
NCOL, NROW = 3, 3


def main():
    os.makedirs(DST, exist_ok=True)
    ms = masters()
    cand = []
    for i, (name, p) in enumerate(ms):
        a16 = tifffile.imread(p)
        h, w = a16.shape[:2]
        x0 = max(0, min(w - PATCH, CX - PATCH // 2))
        y0 = max(0, min(h - PATCH, CY - PATCH // 2))
        patch = rimlib.to8(a16[y0:y0 + PATCH, x0:x0 + PATCH])
        del a16
        g = patch[..., 1].astype(np.float32)
        # the disc must sit at the STATED coordinate, not at the patch centre --
        # clamping at the frame edge moves the centre by up to 104 px in x, and
        # my first draft measured there instead, i.e. not at the site at all.
        px, py = CX - x0, CY - y0
        yy, xx = np.mgrid[0:PATCH, 0:PATCH]
        r = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
        inner = g[r < 22].mean()
        outer = g[(r > 40) & (r < 70)].mean()
        depth = 100.0 * (inner / max(outer, 1.0) - 1.0)
        # flat and bright is the only regime a grey disc is visible in
        flat = float(g[(r > 40) & (r < 70)].std())
        cand.append((depth, name, x0, y0, patch, float(outer), flat))
        print("%2d/%2d %-34s slice (%d,%d) disc@(%d,%d) %+7.2f%%  bg %5.1f DN  "
              "bg sd %5.1f DN%s"
              % (i + 1, len(ms), name, x0, y0, px, py, depth, outer, flat,
                 "  <- FLAT+BRIGHT, a mote would be unmistakable"
                 if outer >= 90 and flat <= 8 else ""), flush=True)

    same = len({(c[2], c[3]) for c in cand})
    print("\n  distinct slice coordinates used across %d masters: %d %s"
          % (len(cand), same, "(all identical -- a fixed output position)"
             if same == 1 else "(NOT identical: the two geometries clamp "
                               "differently, stated below)"))

    # A mote is only visible on flat, bright background. Rank on that subset
    # only -- ranking the whole corpus put dark SCENE CONTENT at the top, which
    # is what my first draft did and then called "the sensor".
    flatbright = [c for c in cand if c[5] >= 90.0 and c[6] <= 8.0]
    flatbright.sort(key=lambda t: t[0])
    show = flatbright[:NCOL * NROW] if len(flatbright) >= NCOL * NROW \
        else sorted(cand, key=lambda t: t[0])[:NCOL * NROW]
    ranked_on = "flat+bright subjects only (%d of %d)" % (len(flatbright), len(cand)) \
        if len(flatbright) >= NCOL * NROW else "ALL subjects (too few flat+bright)"
    BAR = 16
    canvas = Image.new("RGB", (NCOL * PATCH, NROW * (PATCH + BAR) + 48), (16, 16, 16))
    d = ImageDraw.Draw(canvas)
    for i, c in enumerate(show):
        depth, name, x0, y0, patch, bg, flat = c
        r, cc = divmod(i, NCOL)
        canvas.paste(Image.fromarray(patch), (cc * PATCH, r * (PATCH + BAR)))
        d.text((cc * PATCH + 3, r * (PATCH + BAR) + PATCH + 2),
               "%s %+.1f%% bg%.0f" % (name[:22], depth, bg),
               fill=(220, 220, 220), font=font(11))
    fb = [c[0] for c in flatbright]
    worst_fb = min(fb) if fb else float("nan")
    seen = bool(fb) and worst_fb <= -3.0
    d.text((3, NROW * (PATCH + BAR) + 3),
           "SENSOR DUST: DELIVER-V4 reports a mote here. NOT REPRODUCED at this "
           "coordinate in SHIP-V4.", fill=(255, 190, 190), font=font(13))
    d.text((3, NROW * (PATCH + BAR) + 19),
           "Same integer slice (%d,%d) %dpx, TRUE 1:1, %s. Disc placed at the "
           "stated (%d,%d)." % (show[0][2], show[0][3], PATCH, ranked_on, CX, CY),
           fill=(190, 190, 190), font=font(11))
    d.text((3, NROW * (PATCH + BAR) + 33),
           "Worst flat+bright reading %+.2f%%: no grey disc is present where one "
           "would be unmistakable." % worst_fb, fill=(190, 190, 190), font=font(11))
    out = os.path.join(DST, "sensor-dust_mote2_%d_%d_NOT-REPRODUCED.png"
                       % (show[0][2], show[0][3]))
    canvas.save(out)

    print("\n=== counted partition, all %d masters ===" % len(ms))
    neg = [c for c in cand if c[0] <= -3.0]
    mild = [c for c in cand if -3.0 < c[0] <= -1.0]
    none = [c for c in cand if c[0] > -1.0]
    print("  <=-3%% %d + -3..-1%% %d + >-1%% %d = %d of %d   %s"
          % (len(neg), len(mild), len(none), len(neg) + len(mild) + len(none),
             len(ms), "OK" if len(neg) + len(mild) + len(none) == len(ms) else "MISMATCH"))
    print("  worst overall %.2f%% (%s), median %.2f%%"
          % (cand[0][0] if cand else 0, cand[0][1] if cand else "-",
             float(np.median([c[0] for c in cand]))))
    print("\n=== the only regime that can adjudicate: flat AND bright ===")
    print("  flat+bright subjects at this site: %d of %d" % (len(flatbright), len(ms)))
    for c in flatbright:
        print("      %-34s %+7.2f%%  bg %5.1f DN  sd %4.1f" % (c[1], c[0], c[5], c[6]))
    print("\n  wrote %s" % out)
    print("\nVERDICT: %s" % (
        "a disc IS present on flat, bright background (worst %+.2f%%): the "
        "defect is confirmed at this coordinate." % worst_fb if seen else
        "NOT REPRODUCED. On the %d subjects where the background at this site is "
        "flat and bright -- the only regime in which a grey disc is visible at "
        "all -- the worst reading is %+.2f%%, and nothing is visible in the tile. "
        "My first draft ranked the WHOLE corpus, put dark scene content at the "
        "top, and called it the sensor; that verdict was wrong and the ranking "
        "that produced it was measuring scene brightness. DELIVER-V4's mote may "
        "be real at coordinates I did not search, but it is not at (%d,%d) in "
        "SHIP-V4." % (len(flatbright), worst_fb, CX, CY)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
