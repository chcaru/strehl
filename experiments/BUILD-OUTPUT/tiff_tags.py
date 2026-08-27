"""Read a TIFF's IFD out of the raw bytes and say what the file actually claims.

WHY THIS PARSES BYTES INSTEAD OF ASKING A LIBRARY

Two independent reasons, both learned the hard way in this tree.

1. PIL mis-reads this tool's 16-bit TIFFs (AGENTS environment note), and
   `tifffile` -- which does read them correctly -- normalises what it hands
   back: it will report a resolution of `(1, 1)` whether the tag says `1/1`
   or the tag is absent entirely. For the question "is tag 282 PRESENT",
   a normaliser is exactly the wrong instrument, because the state this
   milestone had to distinguish is *absent* from *present and equal to the
   library's default*.
2. The ICC embedding technote specifies TIFF type UNDEFINED (7) for tag
   34675, and `[u8]` encodes as BYTE (1) by default. No high-level reader
   reports the field type, so the only way to check that claim is to read
   the twelve-byte IFD entry.

So this reads the header, walks the IFD, and prints the tag id, the TIFF
type code, the count and the value for every tag in the file. Nothing is
interpreted except where interpretation is stated.

Usage:  python tiff_tags.py <file.tiff> [more.tiff ...]
"""

import struct
import sys

TYPE_NAME = {
    1: "BYTE", 2: "ASCII", 3: "SHORT", 4: "LONG", 5: "RATIONAL",
    6: "SBYTE", 7: "UNDEFINED", 8: "SSHORT", 9: "SLONG", 10: "SRATIONAL",
    11: "FLOAT", 12: "DOUBLE", 16: "LONG8", 17: "SLONG8", 18: "IFD8",
}
TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4,
             10: 8, 11: 4, 12: 8, 16: 8, 17: 8, 18: 8}

TAG_NAME = {
    256: "ImageWidth", 257: "ImageLength", 258: "BitsPerSample",
    259: "Compression", 262: "PhotometricInterpretation",
    270: "ImageDescription", 273: "StripOffsets", 277: "SamplesPerPixel",
    278: "RowsPerStrip", 279: "StripByteCounts", 282: "XResolution",
    283: "YResolution", 284: "PlanarConfiguration", 296: "ResolutionUnit",
    305: "Software", 339: "SampleFormat", 34675: "ICCProfile",
}
RESUNIT = {1: "none", 2: "inch", 3: "centimetre"}


def read_ifd(buf):
    """Return (endian_char, [(tag, typ, count, raw_value_or_offset_bytes)])."""
    if buf[:2] == b"II":
        e = "<"
    elif buf[:2] == b"MM":
        e = ">"
    else:
        raise SystemExit("not a TIFF: bad byte order mark %r" % buf[:2])
    magic, = struct.unpack(e + "H", buf[2:4])
    if magic == 42:
        off, = struct.unpack(e + "I", buf[4:8])
        big = False
    elif magic == 43:
        # BigTIFF. The crate writes it above 4 GB, and a master can reach it.
        offsize, pad = struct.unpack(e + "HH", buf[4:8])
        if offsize != 8 or pad != 0:
            raise SystemExit("unsupported BigTIFF header")
        off, = struct.unpack(e + "Q", buf[8:16])
        big = True
    else:
        raise SystemExit("not a TIFF: magic %d" % magic)

    if big:
        n, = struct.unpack(e + "Q", buf[off:off + 8])
        entries, p, esize = [], off + 8, 20
    else:
        n, = struct.unpack(e + "H", buf[off:off + 2])
        entries, p, esize = [], off + 2, 12

    for _ in range(n):
        if big:
            tag, typ, cnt = struct.unpack(e + "HHQ", buf[p:p + 12])
            inline = buf[p + 12:p + 20]
            room = 8
        else:
            tag, typ, cnt = struct.unpack(e + "HHI", buf[p:p + 8])
            inline = buf[p + 8:p + 12]
            room = 4
        nbytes = cnt * TYPE_SIZE.get(typ, 0)
        if nbytes and nbytes <= room:
            data = inline[:nbytes]
        elif nbytes:
            vo, = struct.unpack(e + ("Q" if big else "I"), inline)
            data = buf[vo:vo + nbytes]
        else:
            data = b""
        entries.append((tag, typ, cnt, data))
        p += esize
    return e, entries


def show_value(e, tag, typ, cnt, data):
    if typ == 2:
        s = data.rstrip(b"\0").decode("utf-8", "replace")
        return ("%r" % s) if len(s) <= 110 else ("%r... (%d chars)" % (s[:110], len(s)))
    if typ == 3:
        v = struct.unpack(e + "H" * cnt, data)
        if tag == 296:
            return "%s  (%s)" % (v, RESUNIT.get(v[0], "UNKNOWN"))
        return str(v)
    if typ in (4, 9):
        return str(struct.unpack(e + ("I" if typ == 4 else "i") * cnt, data)[:8])
    if typ in (5, 10):
        out = []
        for i in range(min(cnt, 4)):
            a, b = struct.unpack(e + ("II" if typ == 5 else "ii"),
                                 data[i * 8:i * 8 + 8])
            out.append("%d/%d = %s" % (a, b, (a / b) if b else "inf"))
        return "; ".join(out)
    if typ in (1, 7):
        return "%d bytes, first16=%s" % (cnt, data[:16].hex())
    return repr(data[:16])


def icc_summary(blob):
    """Everything about an ICC profile that a wrong profile would get wrong."""
    if len(blob) < 132:
        return ["  ICC: TRUNCATED (%d bytes)" % len(blob)]
    size, = struct.unpack(">I", blob[0:4])
    ver, = struct.unpack(">I", blob[8:12])
    lines = [
        "  ICC size field %d vs actual %d  %s" % (
            size, len(blob), "OK" if size == len(blob) else "*** MISMATCH ***"),
        "  ICC version 0x%08x (v%d.%d.%d)  class %r  data %r  pcs %r  sig %r" % (
            ver, ver >> 24, (ver >> 20) & 0xF, (ver >> 16) & 0xF,
            blob[12:16].decode("latin1"), blob[16:20].decode("latin1"),
            blob[20:24].decode("latin1"), blob[36:40].decode("latin1")),
        "  ICC created %s" % (struct.unpack(">6H", blob[24:36]),),
    ]
    n, = struct.unpack(">I", blob[128:132])
    lines.append("  ICC tags (%d):" % n)
    for i in range(n):
        sig, off, sz = struct.unpack(">4sII", blob[132 + 12 * i:144 + 12 * i])
        sig = sig.decode("latin1")
        extra = ""
        body = blob[off:off + sz]
        if sig in ("rXYZ", "gXYZ", "bXYZ", "wtpt") and sz >= 20:
            xyz = struct.unpack(">3i", body[8:20])
            extra = "  = (%.6f, %.6f, %.6f)" % tuple(v / 65536.0 for v in xyz)
        if sig.endswith("TRC") and sz >= 12:
            cnt, = struct.unpack(">I", body[8:12])
            if cnt == 0:
                extra = "  = curv count 0  -> IDENTITY (gamma 1.0)"
            elif cnt == 1:
                g, = struct.unpack(">H", body[12:14])
                extra = "  = curv gamma %.4f" % (g / 256.0)
            else:
                pts = struct.unpack(">%dH" % cnt, body[12:12 + 2 * cnt])
                mid = pts[cnt // 2] / 65535.0
                extra = ("  = curv %d points, f(0)=%.5f f(0.5)=%.5f f(1)=%.5f"
                         % (cnt, pts[0] / 65535.0, mid, pts[-1] / 65535.0))
        if sig in ("desc", "cprt") and sz > 12:
            txt = body[12:12 + min(sz - 12, 90)]
            extra = "  = %r" % txt.split(b"\0")[0].decode("latin1", "replace")
        lines.append("    %-4s off %-7d size %-6d%s" % (sig, off, sz, extra))
    return lines


def main(paths):
    for path in paths:
        with open(path, "rb") as fh:
            buf = fh.read()
        print("=" * 100)
        print("%s   (%d bytes)" % (path, len(buf)))
        e, entries = read_ifd(buf)
        seen = set()
        for tag, typ, cnt, data in entries:
            seen.add(tag)
            print("  %-6d %-26s %-10s count %-8d %s" % (
                tag, TAG_NAME.get(tag, "?"), TYPE_NAME.get(typ, "type%d" % typ),
                cnt, show_value(e, tag, typ, cnt, data)))
            if tag == 34675:
                for line in icc_summary(data):
                    print(line)
        for tag in (282, 283, 296, 34675, 305, 270):
            if tag not in seen:
                print("  ABSENT: %d %s" % (tag, TAG_NAME[tag]))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1:]))
