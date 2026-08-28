"""V-MOTE P7 -- the before/after evidence, from ONE pinned build.

Arm OFF: STREHL_DEFECT unset (the shipping default).
Arm ON : STREHL_DEFECT=on.
Both:    C:\\dev\\strehl-pin-vmote\\strehl.exe, sha256
         0F4ACD7E2D592FE3F8980BA6077100BCBF253879CE53A42F0AC81EFFFA3CFCDA,
         `stack D:\\personal\\macro\\flower-bud-alone-cpl -o <out> --srgb`.

Prints a whole-image diff first.  An env var that is accepted and silently
ignored produces a byte-identical pair, and THAT is the failure mode this
project has already shipped once (STREHL_SOFT_GATE).  A difference is the only
proof the knob was read.
"""
import os, sys
import numpy as np
import tifffile
from PIL import Image

AB = r"C:\dev\strehl-out\V-MOTE\ab"
DST = r"C:\dev\strehl-out\V-MOTE\crops"
SITE_P = (6868, 4610)
SITE_M = (7008, 4450)
from vm_master import vm_depth


def main():
    off = tifffile.imread(os.path.join(AB, "flower-bud-alone-cpl_OFF.tiff"))
    on = tifffile.imread(os.path.join(AB, "flower-bud-alone-cpl_ON.tiff"))
    print("OFF %s %s   ON %s %s" % (off.shape, off.dtype, on.shape, on.dtype))
    assert off.shape == on.shape
    d = on.astype(np.int32) - off.astype(np.int32)
    nz = np.count_nonzero(d)
    print("whole-image diff: %d of %d samples differ (%.4f%%), max |delta| %d DN16, "
          "mean |delta| over changed %.1f DN16"
          % (nz, d.size, 100.0 * nz / d.size, int(np.abs(d).max()),
             float(np.abs(d)[d != 0].mean()) if nz else 0.0))
    if nz == 0:
        print("  !! BYTE-IDENTICAL -- STREHL_DEFECT was accepted and IGNORED. Everything below is void.")
        return 1
    # where did it change
    ys, xs = np.nonzero(np.abs(d).max(axis=2))
    print("  changed-sample bounding box: x %d..%d  y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))
    for tag, cx, cy in (("mote2", SITE_P[0], SITE_P[1]), ("mote1", 6404, 238)):
        m = np.abs(d[max(0, cy-120):cy+120, max(0, cx-120):cx+120]).max()
        print("  max |delta| within 120 px of %s (%d,%d): %d DN16" % (tag, cx, cy, m))

    print("\ndepth at the site, same statistic as vm_master.py (core r<=16, quad fit 90..160):")
    for tag, a in (("OFF", off), ("ON ", on)):
        g = a[..., 1].astype(np.float64)
        for name, (cx, cy) in (("BUILD-DEFECT (6868,4610)", SITE_P),
                               ("V-EYES       (7008,4450)", SITE_M),
                               ("mote centre  (6878,4620)", (6878, 4620))):
            print("  %s  %s  %+0.3f%%" % (tag, name, vm_depth(g, cx, cy)[0]))

    print("\n1:1 crops, no resampling:")
    CW = 400
    h, w = off.shape[:2]
    x0, y0 = w - CW, h - CW
    # ONE stretch window, taken from the OFF arm, used for BOTH so the pair is comparable
    g = off[y0:y0+CW, x0:x0+CW, 1].astype(np.float64)
    lo, hi = np.percentile(g, 0.5), np.percentile(g, 99.5)
    for tag, a in (("OFF", off), ("ON", on)):
        crop = a[y0:y0+CW, x0:x0+CW, :].astype(np.float64)
        rgb = np.clip((crop - lo) / max(hi - lo, 1), 0, 1)
        p = os.path.join(DST, "20-AB-flower-bud-alone-cpl-%s-corner400.png" % tag)
        Image.fromarray((rgb*255+0.5).astype(np.uint8)).save(p)
        print("  %s  slice x0=%d y0=%d %dx%d  SHARED stretch [%.0f,%.0f] DN16"
              % (os.path.basename(p), x0, y0, CW, CW, lo, hi))
    # the difference itself, so the correction's footprint is visible
    dg = d[y0:y0+CW, x0:x0+CW, 1].astype(np.float64)
    p = os.path.join(DST, "21-AB-flower-bud-alone-cpl-DIFF-corner400.png")
    Image.fromarray((np.clip(dg / max(np.abs(dg).max(), 1), 0, 1)*255+0.5).astype(np.uint8)).save(p)
    print("  %s  ON minus OFF, green, stretch [0, %d] DN16"
          % (os.path.basename(p), int(np.abs(dg).max())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
