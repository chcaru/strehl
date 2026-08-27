"""Print the header and tag list of an embedded ICC profile.

The point is one number: the tone response curve.  If the profile strehl
embeds declares gamma 1.0, then a colour-managed consumer (Zerene) that honours
it will not apply an sRGB decode to data that is already linear.  If the
profile is absent or declares the sRGB curve, the consumer will linearise
already-linear data and the tone confound this lane exists to remove comes back
in through the reader instead of through Lightroom.

Reads only the ICC structure, which is a published open specification
(ICC.1:2010).  Nothing here inspects any application's code.
"""
import struct
import sys

import tifffile


def read_profile(path):
    with tifffile.TiffFile(path) as tf:
        for t in tf.pages[0].tags:
            if t.name == "InterColorProfile":
                return bytes(t.value)
    return None


def main():
    for path in sys.argv[1:]:
        print("=" * 90)
        print(path)
        b = read_profile(path)
        if b is None:
            print("  NO EMBEDDED ICC PROFILE")
            continue
        size, = struct.unpack(">I", b[0:4])
        cmm = b[4:8].decode("latin1")
        ver = b[8:12]
        cls = b[12:16].decode("latin1")
        space = b[16:20].decode("latin1")
        pcs = b[20:24].decode("latin1")
        desc_sig = b[36:40].decode("latin1")
        print(f"  size {size} (tag says) / {len(b)} (actual)  cmm '{cmm}' "
              f"version {ver[0]}.{ver[1] >> 4}.{ver[1] & 15}")
        print(f"  class '{cls}'  data space '{space}'  PCS '{pcs}'  "
              f"magic '{desc_sig}'")
        ntags, = struct.unpack(">I", b[128:132])
        print(f"  {ntags} tags:")
        for i in range(ntags):
            off = 132 + 12 * i
            sig = b[off:off + 4].decode("latin1")
            o, n = struct.unpack(">II", b[off + 4:off + 12])
            body = b[o:o + n]
            typ = body[0:4].decode("latin1") if n >= 4 else "?"
            extra = ""
            if typ == "curv" and n >= 12:
                cnt, = struct.unpack(">I", body[8:12])
                if cnt == 0:
                    extra = "  -> identity (gamma 1.0)"
                elif cnt == 1:
                    g, = struct.unpack(">H", body[12:14])
                    extra = f"  -> gamma {g / 256.0:.4f}"
                else:
                    extra = f"  -> {cnt}-entry sampled curve"
            elif typ == "para" and n >= 12:
                ft, = struct.unpack(">H", body[8:10])
                extra = f"  -> parametric function type {ft}"
            elif typ in ("desc", "mluc", "text") and n >= 16:
                extra = "  -> " + body[8:min(n, 96)].decode(
                    "latin1", "replace").replace("\x00", "").strip()
            print(f"    {sig}  type {typ}  {n:5d} bytes{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
