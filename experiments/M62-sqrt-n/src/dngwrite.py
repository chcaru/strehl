"""Minimal uncompressed CFA DNG writer.

The shipped CLI only accepts `.arw`, and `rawler` selects a decoder from file
CONTENT rather than from the extension. So a synthetic burst is written as an
uncompressed DNG carrying a `.arw` name, and the DNG decoder picks it up.

Nothing here is read from `rawler` (LGPL-2.1, link-only). TIFF/DNG tag numbers
and field types are uncopyrightable facts; the layout below was written from
the public TIFF 6.0 and DNG 1.4 field definitions.

Layout emitted, in file order:

    header (8 B) | IFD0 | IFD0 external values | Exif IFD | Exif external |
    image strip

IFD0 carries the raw CFA plane directly (`NewSubfileType = 0`). No thumbnail
and no SubIFD: a reader that needs one will fail loudly on decode, which is
exactly the signal wanted.
"""

from __future__ import annotations

import struct

import numpy as np

BYTE, ASCII, SHORT, LONG, RATIONAL, UNDEFINED, SRATIONAL = 1, 2, 3, 4, 5, 7, 10

_SCALAR_FMT = {BYTE: "B", SHORT: "H", LONG: "I"}
_TYPE_SIZE = {BYTE: 1, ASCII: 1, SHORT: 2, LONG: 4, RATIONAL: 8, UNDEFINED: 1, SRATIONAL: 8}


def _encode(typ, values):
    """Return (bytes, count) for one IFD entry's payload."""
    if typ == ASCII:
        blob = values.encode("ascii") + b"\x00"
        return blob, len(blob)
    if typ == UNDEFINED:
        blob = bytes(values)
        return blob, len(blob)
    if typ in (RATIONAL, SRATIONAL):
        fmt = "<ii" if typ == SRATIONAL else "<II"
        blob = b"".join(struct.pack(fmt, n, d) for n, d in values)
        return blob, len(values)
    fmt = "<" + _SCALAR_FMT[typ]
    blob = b"".join(struct.pack(fmt, int(v)) for v in values)
    return blob, len(values)


class _Ifd:
    def __init__(self):
        self.entries = []  # (tag, typ, blob, count)

    def add(self, tag, typ, values):
        blob, count = _encode(typ, values)
        self.entries.append([tag, typ, blob, count])

    def add_pointer(self, tag):
        """A LONG entry whose value is patched later. Returns its index."""
        self.entries.append([tag, LONG, b"\x00\x00\x00\x00", 1])
        return len(self.entries) - 1

    def set_pointer(self, idx, offset):
        self.entries[idx][2] = struct.pack("<I", int(offset))

    def sort(self):
        self.entries.sort(key=lambda e: e[0])

    def dir_size(self):
        return 2 + 12 * len(self.entries) + 4

    def ext_size(self):
        return sum(len(e[2]) for e in self.entries if len(e[2]) > 4)

    def serialise(self, base, next_ifd=0):
        """Serialise at absolute offset `base`. External values follow the dir."""
        ext_at = base + self.dir_size()
        head = struct.pack("<H", len(self.entries))
        ext = b""
        for tag, typ, blob, count in self.entries:
            if len(blob) <= 4:
                payload = blob + b"\x00" * (4 - len(blob))
            else:
                payload = struct.pack("<I", ext_at + len(ext))
                ext += blob
                if len(blob) % 2:  # keep word alignment
                    ext += b"\x00"
            head += struct.pack("<HHI", tag, typ, count) + payload
        head += struct.pack("<I", next_ifd)
        return head + ext


def _srational(x, den=1000000):
    return (int(round(x * den)), den)


def write_cfa_dng(
    path,
    cfa: np.ndarray,
    *,
    black: int = 512,
    white: int = 15360,
    iso: int = 160,
    exposure_s: float = 1.0,
    make: str = "SONY",
    model: str = "ILCE-7CM2",
    unique_model: str = "SONY ILCE-7CM2",
    wb=(2.861, 1.0, 1.482),
):
    """Write `cfa` (uint16, RGGB, even dimensions) as an uncompressed CFA DNG."""
    assert cfa.dtype == np.uint16, cfa.dtype
    h, w = cfa.shape
    assert h % 2 == 0 and w % 2 == 0, (h, w)

    ifd0 = _Ifd()
    ifd0.add(254, LONG, [0])  # NewSubfileType: full-resolution image
    ifd0.add(256, LONG, [w])  # ImageWidth
    ifd0.add(257, LONG, [h])  # ImageLength
    ifd0.add(258, SHORT, [16])  # BitsPerSample
    ifd0.add(259, SHORT, [1])  # Compression: none
    ifd0.add(262, SHORT, [32803])  # PhotometricInterpretation: CFA
    ifd0.add(271, ASCII, make)
    ifd0.add(272, ASCII, model)
    strip_off = ifd0.add_pointer(273)  # StripOffsets
    ifd0.add(274, SHORT, [1])  # Orientation
    ifd0.add(277, SHORT, [1])  # SamplesPerPixel
    ifd0.add(278, LONG, [h])  # RowsPerStrip: one strip
    ifd0.add(279, LONG, [w * h * 2])  # StripByteCounts
    ifd0.add(284, SHORT, [1])  # PlanarConfiguration
    ifd0.add(305, ASCII, "strehl-M62-sqrt-n synthetic burst")
    ifd0.add(33421, SHORT, [2, 2])  # CFARepeatPatternDim
    ifd0.add(33422, BYTE, [0, 1, 1, 2])  # CFAPattern: RGGB
    exif_ptr = ifd0.add_pointer(34665)  # ExifIFD
    ifd0.add(50706, BYTE, [1, 4, 0, 0])  # DNGVersion
    ifd0.add(50707, BYTE, [1, 1, 0, 0])  # DNGBackwardVersion
    ifd0.add(50708, ASCII, unique_model)  # UniqueCameraModel
    ifd0.add(50710, BYTE, [0, 1, 2])  # CFAPlaneColor: RGB
    ifd0.add(50711, SHORT, [1])  # CFALayout: rectangular
    ifd0.add(50713, SHORT, [1, 1])  # BlackLevelRepeatDim
    ifd0.add(50714, SHORT, [black])  # BlackLevel
    ifd0.add(50717, LONG, [white])  # WhiteLevel
    # A plausible daylight matrix. Nothing measured here consumes it; a valid
    # DNG is required to carry one.
    cm = [0.7328, -0.2011, -0.0326, -0.4938, 1.2337, 0.2848, -0.0982, 0.1502, 0.5591]
    ifd0.add(50721, SRATIONAL, [_srational(v) for v in cm])  # ColorMatrix1
    ifd0.add(50728, RATIONAL, [(int(round(1e6 / g)), 1000000) for g in wb])  # AsShotNeutral
    ifd0.add(50778, SHORT, [21])  # CalibrationIlluminant1: D65
    ifd0.add(50829, LONG, [0, 0, h, w])  # ActiveArea: whole frame
    ifd0.sort()

    exif = _Ifd()
    exif.add(33434, RATIONAL, [(int(round(exposure_s * 1000)), 1000)])  # ExposureTime
    exif.add(33437, RATIONAL, [(56, 10)])  # FNumber
    exif.add(34855, SHORT, [iso])  # ISOSpeedRatings
    exif.add(36864, UNDEFINED, b"0230")  # ExifVersion
    exif.add(37386, RATIONAL, [(200, 1)])  # FocalLength
    exif.sort()

    # Offsets are resolved by serialising once to MEASURE, then again to emit.
    # Computing the length from `ext_size()` under-counts the per-blob odd-length
    # pad byte, which silently lands the Exif IFD inside IFD0's value block: the
    # file still decodes, and ISO comes back UNKNOWN.
    ifd0_at = 8
    ifd0_len = len(ifd0.serialise(ifd0_at))
    exif_at = ifd0_at + ifd0_len + (ifd0_len % 2)
    exif_len = len(exif.serialise(exif_at))
    image_at = exif_at + exif_len + (exif_len % 2)

    ifd0.set_pointer(exif_ptr, exif_at)
    ifd0.set_pointer(strip_off, image_at)

    ifd0_bytes = ifd0.serialise(ifd0_at)
    assert len(ifd0_bytes) == ifd0_len, (len(ifd0_bytes), ifd0_len)
    ifd0_bytes += b"\x00" * (exif_at - ifd0_at - len(ifd0_bytes))
    exif_bytes = exif.serialise(exif_at)
    assert len(exif_bytes) == exif_len, (len(exif_bytes), exif_len)
    exif_bytes += b"\x00" * (image_at - exif_at - len(exif_bytes))

    with open(path, "wb") as fh:
        fh.write(struct.pack("<2sHI", b"II", 42, ifd0_at))
        fh.write(ifd0_bytes)
        fh.write(exif_bytes)
        fh.write(np.ascontiguousarray(cfa).tobytes())
