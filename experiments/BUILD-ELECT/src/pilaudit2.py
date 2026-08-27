"""Loader audit v2: the reference-free test, and the case it cannot answer.

ORCH's correction is right and my own artifact carried the harmful phrasing: the
v1 script printed the banner "is any BUILD-ELECT magnitude 256x wrong?", which
names a repair that does not work. Corrected there and recorded here rather than
quietly deleted.

The corrected audit question is `len(np.unique(arr))` -- thousands of distinct
values from a 16-bit master read properly, a couple of hundred at most through
PIL -- and its stated virtue is that it needs **no reference image and no
knowledge of what the number should be**.

That virtue is real for the case ORCH had. It is exactly what makes the test
unable to answer the case THIS lane had, and I want that on the record before
anyone runs it and trusts the answer:

  An 8-bit file read correctly ALSO returns a low unique count.

So a low count means "this array has coarse tonal resolution", which is not the
same proposition as "this array was truncated". The two differ in whether a
better read exists. On a genuinely 8-bit source the prescribed remedy -- re-run
from tifffile -- has nothing to re-read, and a lane applying the rule
mechanically would go looking for a 16-bit original that does not exist.

  What property of the input decides whether this check can see anything?
  The BIT DEPTH OF THE SOURCE -- which is the one thing the test does not read.

Distinguishing them requires the container's own declaration: IHDR for PNG,
BitsPerSample for TIFF. Both are parsed here from raw bytes with no imaging
library in the path, so the reader cannot be the thing under test.

This script also closes section 21.6's open item. Section 21 measured at an
address derived by ASSUMING ORCH's 1:1 asset is the 800x800 tile at origin
(2864,864), and never reproduced ORCH's +22 exactly. ORCH's own notice quotes a
master width of 7032 where this lane recorded 7040, which is enough to move an
assumed origin. So the origin is now MEASURED by integer-shift cross-correlation
rather than assumed, and section 21's clipping census is re-run at 16 bits at
whatever origin that finds -- on the master, not on the 8-bit derivative.
"""
import os
import struct
import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
SHIP = r"C:\dev\strehl-out\SHIP-V2"
MASTER = os.path.join(SHIP, "flower-bud-alone-cpl--SHIP-V2.tiff")
ASSET = (r"C:\dev\strehl-out\VIEW-SHIP\assets"
         r"\flower-bud-alone-cpl--SHIP-V2--1to1.png")

ASSUMED = (2864, 864)
SEARCH = 40
PATCH = 192
REGION = (20, 220, 350, 560)


def png_ihdr(path):
    with open(path, "rb") as f:
        head = f.read(33)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{path}: not a PNG"
    assert head[12:16] == b"IHDR", f"{path}: first chunk {head[12:16]!r}"
    w, h = struct.unpack(">II", head[16:24])
    return w, h, head[24]


def tiff_bits(path):
    """BitsPerSample straight out of the IFD, no imaging library."""
    with open(path, "rb") as f:
        b = f.read(8)
        end = "<" if b[:2] == b"II" else ">"
        off = struct.unpack(end + "I", b[4:8])[0]
        f.seek(off)
        n = struct.unpack(end + "H", f.read(2))[0]
        for _ in range(n):
            e = f.read(12)
            tag, typ, cnt = struct.unpack(end + "HHI", e[:8])
            if tag == 258:
                if cnt == 1:
                    return [struct.unpack(end + "H", e[8:10])[0]]
                p = struct.unpack(end + "I", e[8:12])[0]
                here = f.tell()
                f.seek(p)
                v = list(struct.unpack(end + "H" * cnt, f.read(2 * cnt)))
                f.seek(here)
                return v
    return None


def main():
    print("=" * 78)
    print("LOADER AUDIT v2 -- quantisation is not a scale error")
    print("=" * 78)

    print("\n  [1] the reference-free test, run on this lane's inputs")
    print(f"    {'array':<40} {'dtype':>8} {'distinct':>9}")
    m = tifffile.imread(MASTER)
    print(f"    {'master via tifffile':<40} {str(m.dtype):>8} "
          f"{len(np.unique(m)):>9}")
    with Image.open(MASTER) as im:
        mp = np.asarray(im)
    print(f"    {'master via PIL':<40} {str(mp.dtype):>8} "
          f"{len(np.unique(mp)):>9}")
    with Image.open(ASSET) as im:
        av = np.asarray(im.convert("RGB"))
    print(f"    {'ORCH 1:1 asset via PIL':<40} {str(av.dtype):>8} "
          f"{len(np.unique(av)):>9}")
    del mp

    print("\n  [2] can the test tell those last two apart?")
    print("    Both are uint8 with a low distinct count. One is a truncation")
    print("    with a 16-bit original on disk; the other is the file. The")
    print("    counts do not separate them. The containers do:")
    w, h, depth = png_ihdr(ASSET)
    bps = tiff_bits(MASTER)
    print(f"      asset  IHDR          : {w} x {h}, bit depth {depth}")
    print(f"      master BitsPerSample : {bps}")
    print("    So: the master must be read with tifffile and IS; the asset has")
    print("    no better read to fall back to, and 'rerun from tifffile' is")
    print("    not an available remedy there.")

    print("\n  [3] where is the asset actually IN the master?")
    print(f"    master shape {m.shape}, assumed origin {ASSUMED}")
    g = m[:, :, 1].astype(np.float32)
    ag = av[:, :, 1].astype(np.float32)
    r0, c0 = PATCH, PATCH
    pa = ag[r0:r0 + PATCH, c0:c0 + PATCH]
    pa = pa - pa.mean()
    pn = float(np.sqrt((pa * pa).sum()))
    best, bxy = -2.0, None
    for dy in range(-SEARCH, SEARCH + 1):
        for dx in range(-SEARCH, SEARCH + 1):
            y = ASSUMED[1] + r0 + dy
            x = ASSUMED[0] + c0 + dx
            q = g[y:y + PATCH, x:x + PATCH]
            if q.shape != pa.shape:
                continue
            q = q - q.mean()
            d = float(np.sqrt((q * q).sum()))
            if d <= 0:
                continue
            r = float((pa * q).sum()) / (pn * d)
            if r > best:
                best, bxy = r, (ASSUMED[0] + dx, ASSUMED[1] + dy)
    if bxy is None or best < 0.5:
        print(f"    CORRELATION FAILED (best {best:.3f}). Refusing to quote an")
        print("    origin. Section 21's address stays assumed and flagged.")
        return 1
    print(f"    measured origin : {bxy}   peak correlation {best:.4f}")
    dx = bxy[0] - ASSUMED[0]
    dy = bxy[1] - ASSUMED[1]
    print(f"    offset from assumed : ({dx:+d}, {dy:+d})")
    if (dx, dy) == (0, 0):
        print("    Section 21's assumed address was RIGHT. The unreproduced")
        print("    +22 is not an address error and stays open.")
    else:
        print("    Section 21 measured at the WRONG address by that offset.")

    print("\n  [4] section 21's clipping census, re-run at 16 bits on the master")
    y0, y1, x0, x1 = REGION
    reg = m[bxy[1] + y0:bxy[1] + y1, bxy[0] + x0:bxy[0] + x1, :3]
    print(f"    region {reg.shape[1]} x {reg.shape[0]} at "
          f"({bxy[0]+x0},{bxy[1]+y0}), 16-bit")
    for i, ch in enumerate("RGB"):
        c = reg[:, :, i]
        print(f"      {ch}: max {int(c.max()):>6}  "
              f"distinct {len(np.unique(c)):>6}  "
              f"at 65535 {int((c == 65535).sum()):>6}  "
              f"ge 64000 {int((c >= 64000).sum()):>6}")
    n = reg.shape[0] * reg.shape[1]
    top = int((reg.max(axis=2) >= 65535).sum())
    print(f"    pixels with any channel at full scale : {top} of {n} "
          f"({100.0*top/n:.4f}%)")
    print("    Section 21 asked this of the 8-bit derivative. Asked of the")
    print("    16-bit master, at a measured rather than assumed address, the")
    print("    answer is the one that can actually support the claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
