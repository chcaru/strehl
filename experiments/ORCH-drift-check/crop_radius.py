"""Where do M110's crops sit in normalised image radius?

M107's lateral-CA fit spans r = 0.208-0.788 with both outer annuli empty, and
`support_r_max = Some(0.788)` is declared but NOT enforced. So any crop past
r = 0.788 is being corrected by extrapolated model shape, not by data.

This asks a decision-relevant question: is the CA that is most visible by eye
sitting inside the fitted support, or outside it?
"""
import math
import pathlib
import struct

TIF = pathlib.Path(r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif")

# M110's crop centres, read from its ZOOM filenames.
CROPS = {
    "bee-3-cpl hairs": (300, 4200),
    "bee-3-cpl specular": (900, 2620),
    "bee-3-cpl wing": (900, 60),
    "wrapped-text-1 text": (4850, 1750),
}


def tiff_dims(path):
    """Minimal TIFF header walk -- ImageWidth (256) / ImageLength (257)."""
    with open(path, "rb") as fh:
        head = fh.read(8)
        endian = "<" if head[:2] == b"II" else ">"
        magic = struct.unpack(endian + "H", head[2:4])[0]
        big = magic == 43
        if big:
            off = struct.unpack(endian + "Q", fh.read(16)[8:16])[0]
        else:
            off = struct.unpack(endian + "I", head[4:8])[0]
        fh.seek(off)
        if big:
            n = struct.unpack(endian + "Q", fh.read(8))[0]
            esz, cnt_fmt = 20, "Q"
        else:
            n = struct.unpack(endian + "H", fh.read(2))[0]
            esz, cnt_fmt = 12, "I"
        w = h = None
        for _ in range(n):
            e = fh.read(esz)
            tag, typ = struct.unpack(endian + "HH", e[:4])
            if big:
                val = struct.unpack(endian + "Q", e[12:20])[0]
            else:
                val = struct.unpack(endian + "I", e[8:12])[0]
                if typ == 3:  # SHORT stored in the high half on big-endian
                    val = struct.unpack(endian + "H", e[8:10])[0]
            if tag == 256:
                w = val
            elif tag == 257:
                h = val
        return w, h


W, H = tiff_dims(TIF)
cx, cy = W / 2.0, H / 2.0
r_corner = math.hypot(cx, cy)

print("render: %s" % TIF)
print("dims  : %d x %d" % (W, H))
print("centre: (%.1f, %.1f)   corner radius: %.1f px" % (cx, cy, r_corner))
print()
print("%-24s %10s %10s   %s" % ("crop", "r_px", "r_norm", "vs support 0.788"))
for name, (x, y) in CROPS.items():
    r = math.hypot(x - cx, y - cy)
    rn = r / r_corner
    verdict = "INSIDE fit" if rn <= 0.788 else "*** OUTSIDE -- EXTRAPOLATED ***"
    print("%-24s %10.1f %10.4f   %s" % (name, r, rn, verdict))

print()
print("fit support measured by M107: r = 0.208 .. 0.788 (both outer annuli empty)")
