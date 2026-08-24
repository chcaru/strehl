"""Is PIL truncating the 16-bit render to 8 bits?

x9_montage printed `(4688, 7032, 3) uint8` for a file the tool says is
"16-bit RGB", and 7032*4688*3*2 = 197,796,096 bytes against a 197,797,874 byte
file -- so the bytes on disk are 16-bit and the array in memory was not.

If that is right, every per-crop number in that run measured 8-bit quantisation
and not the kernel, and the region selection was made on truncated data. Worth
five minutes to find out before any of it is reported.
"""

import pathlib
import struct
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
Image.MAX_IMAGE_PIXELS = None

P = pathlib.Path(r"C:\dev\strehl-out\M95-montage\bee3-catmull-rom.tif")

# --- read the TIFF IFD by hand; no library gets to have an opinion here ---
b = P.open("rb").read(4096)
endian = "<" if b[:2] == b"II" else ">"
(magic,) = struct.unpack(endian + "H", b[2:4])
(ifd_off,) = struct.unpack(endian + "I", b[4:8])
print(f"byte order {b[:2]!r}  magic {magic}  first IFD at {ifd_off}")

with P.open("rb") as f:
    f.seek(ifd_off)
    (n,) = struct.unpack(endian + "H", f.read(2))
    tags = {}
    for _ in range(n):
        tag, typ, cnt = struct.unpack(endian + "HHI", f.read(8))
        val = f.read(4)
        if typ == 3 and cnt == 1:
            (v,) = struct.unpack(endian + "H", val[:2])
        elif typ == 4 and cnt == 1:
            (v,) = struct.unpack(endian + "I", val)
        else:
            (v,) = struct.unpack(endian + "I", val)
        tags[tag] = (typ, cnt, v)

NAMES = {256: "ImageWidth", 257: "ImageLength", 258: "BitsPerSample",
         259: "Compression", 262: "Photometric", 277: "SamplesPerPixel",
         339: "SampleFormat"}
for t, name in NAMES.items():
    if t in tags:
        print(f"  {name:16s} = {tags[t][2]}   (type {tags[t][0]}, count {tags[t][1]})")

bps = tags.get(258, (0, 0, None))
if bps[1] > 1:
    with P.open("rb") as f:
        f.seek(bps[2])
        vals = struct.unpack(endian + "H" * bps[1], f.read(2 * bps[1]))
    print(f"  BitsPerSample (array) = {vals}")
    bits = vals[0]
else:
    bits = bps[2]
print(f"\nON DISK: {bits} bits per sample")

im = Image.open(P)
a = np.asarray(im)
print(f"PIL     : mode={im.mode!r} -> numpy {a.dtype}, max={a.max()}")

if bits == 16 and a.dtype == np.uint8:
    print("\nCONFIRMED: PIL truncates this file to 8 bits. Every number x9_montage")
    print("printed from a PIL array measured quantisation, not the kernel.")

# --- a reader that does not truncate ---
ok = []
try:
    import tifffile
    t = tifffile.imread(str(P))
    print(f"\ntifffile: numpy {t.dtype} {t.shape}, max={t.max()}")
    ok.append(("tifffile", t.dtype))
except ImportError:
    print("\ntifffile: NOT INSTALLED")
except Exception as e:  # noqa: BLE001
    print(f"\ntifffile: FAILED {e!r}")

# --- and a floor: raw memmap straight off the strip, no library at all ---
try:
    with P.open("rb") as f:
        f.seek(ifd_off)
        (n,) = struct.unpack(endian + "H", f.read(2))
        strip_off = None
        for _ in range(n):
            tag, typ, cnt = struct.unpack(endian + "HHI", f.read(8))
            val = f.read(4)
            if tag == 273 and cnt == 1:
                (strip_off,) = struct.unpack(endian + "I", val)
    if strip_off is not None:
        w, h = tags[256][2], tags[257][2]
        spp = tags[277][2]
        mm = np.memmap(P, dtype=(endian + "u2"), mode="r", offset=strip_off,
                       shape=(h, w, spp))
        print(f"memmap  : numpy {mm.dtype} {mm.shape}, "
              f"max={int(mm[::37, ::37].max())}, strip at {strip_off}")
        ok.append(("memmap", mm.dtype))
    else:
        print("memmap  : single StripOffsets not found (multi-strip file)")
except Exception as e:  # noqa: BLE001
    print(f"memmap  : FAILED {e!r}")

print(f"\nnon-truncating readers available: {ok}")
print("END OF BITDEPTH PROBE")
