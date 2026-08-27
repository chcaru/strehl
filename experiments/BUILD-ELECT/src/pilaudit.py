"""Loader audit: did any BUILD-ELECT magnitude come through PIL from a 16-bit file?

ORCH measured that Pillow returns uint8 from the 16-bit SHIP-V2 masters with no
exception, no warning and no flag -- the loss lives in the difference between
the array and the file, and nothing in the array records it. A monotone
truncation preserves shape claims and destroys magnitude claims.

A grep says every .tiff in this lane is read with tifffile and the only two
PIL.Image.open calls read a .png and a .jpg. That is an argument about source
text. This measures the three things the argument assumes:

  1. tifffile really does return uint16 from the masters this lane measured.
  2. PIL really would have truncated them -- so the hazard is live in THIS
     environment and the tifffile choice is load-bearing rather than lucky.
  3. ORCH's 1:1 asset, the one input this lane DOES read through PIL, is
     genuinely 8-bit at source.

(3) is the one that matters, because section 21's clipping census -- 0.00% of
ORCH's region at >= 250 -- was read through PIL. If that asset were 16 bits, the
census counted truncated values against an 8-bit ceiling and means nothing.

The PNG depth is parsed straight out of the IHDR bytes with no imaging library
in the path, so the reader cannot be the thing under test. IHDR is fixed-layout:
8-byte signature, 4-byte length, 4-byte type, then width, height, bit depth.

Note on direction, stated before the run: 16->8 truncation maps 65535 to 255 and
also maps 65280..65535 to 255, so it can only ever CREATE apparent clipping,
never hide it. A clipping census that found none is therefore conservative under
the hazard. That is a reason the conclusion would survive, which by tonight's
notice is exactly when to measure rather than reason.
"""
import os
import struct
import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
SHIP = r"C:\dev\strehl-out\SHIP-V2"
ASSET = (r"C:\dev\strehl-out\VIEW-SHIP\assets"
         r"\flower-bud-alone-cpl--SHIP-V2--1to1.png")

TIFFS = [
    ("ORCH master (sec 21 census ref)",
     os.path.join(SHIP, "flower-bud-alone-cpl--SHIP-V2.tiff")),
    ("g2.0 LINEAR default arm", os.path.join(OUT, "fb-noflags.tiff")),
    ("n=1 pyramid arm", os.path.join(OUT, "one-fb-pyramid.tiff")),
]


def png_depth(path):
    """Bit depth and colour type from IHDR, no imaging library involved."""
    with open(path, "rb") as f:
        head = f.read(33)
    sig = head[:8]
    assert sig == b"\x89PNG\r\n\x1a\n", f"{path}: not a PNG (sig {sig!r})"
    assert head[12:16] == b"IHDR", f"{path}: first chunk is {head[12:16]!r}"
    w, h = struct.unpack(">II", head[16:24])
    return w, h, head[24], head[25]


def main():
    print("=" * 78)
    print("LOADER AUDIT -- was any BUILD-ELECT magnitude read through PIL?")
    print("=" * 78)
    print("  NOTE: this banner used to read '256x wrong', which was ORCH's")
    print("  original framing and is retracted. The loss is QUANTISATION, not")
    print("  scale: 10440 distinct values become 57 and multiplying by 256")
    print("  restores the scale and none of the information. Affected numbers")
    print("  must be RE-READ, never rescaled. See pilaudit2.py.")

    print("\n  [1] tifffile vs PIL on the 16-bit masters this lane measured")
    print(f"    {'file':<34} {'tifffile':>18} {'PIL':>14}")
    n_hazard = 0
    for name, p in TIFFS:
        if not os.path.exists(p):
            print(f"    {name:<34} {'MISSING -- not a pass':>33}")
            continue
        a = tifffile.imread(p)
        with Image.open(p) as im:
            b = np.asarray(im)
        ta = f"{a.dtype} max {int(a.max())}"
        tb = f"{b.dtype} max {int(b.max())}"
        print(f"    {name:<34} {ta:>18} {tb:>14}")
        assert a.dtype == np.uint16, f"{p}: tifffile gave {a.dtype}"
        if b.dtype == np.uint8:
            n_hazard += 1
        del a, b

    if n_hazard == 0:
        print("\n    PIL did NOT truncate here. The hazard did not reproduce in")
        print("    this environment, so this audit has NOT been shown capable of")
        print("    catching it and its clean result on (3) carries less weight.")
    else:
        print(f"\n    PIL truncated {n_hazard}/{len(TIFFS)} to uint8 with no error.")
        print("    The hazard is live here, so choosing tifffile is load-bearing")
        print("    and this audit has been shown able to see the failure it")
        print("    is looking for.")

    print("\n  [2] ORCH's 1:1 asset -- the ONE input this lane reads via PIL")
    if not os.path.exists(ASSET):
        print("    MISSING -- section 21's clipping census cannot be audited")
        return 1
    w, h, depth, ctype = png_depth(ASSET)
    print(f"    IHDR (parsed from raw bytes) : {w} x {h}, "
          f"bit depth {depth}, colour type {ctype}")
    with Image.open(ASSET) as im:
        arr = np.asarray(im.convert("RGB"))
    print(f"    PIL returns                  : {arr.dtype}, max {int(arr.max())}")
    if depth == 8:
        print("\n    Source is 8 bits per sample. PIL returning uint8 is not a")
        print("    truncation, it is the file. Section 21's clipping census -- "
              "0.00%")
        print("    of the region at >= 250 -- was measured against a real 255")
        print("    ceiling and STANDS.")
        rc = 0
    else:
        print(f"\n    Source is {depth} bits. PIL truncated it. Section 21's")
        print("    clipping census counted truncated values against an 8-bit")
        print("    ceiling and MUST BE WITHDRAWN.")
        rc = 1

    print("\n  [3] does the census conclusion depend on the answer to [2]?")
    top = int((arr >= 250).sum())
    print(f"    samples >= 250 in the asset : {top}")
    print("    16->8 truncation maps 65280..65535 to 255, so it can only ADD")
    print("    apparent clipping. A census that found none is conservative")
    print("    either way -- but that is the argument, and [2] is the")
    print("    measurement, and they now agree.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
