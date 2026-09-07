"""Independent bounded RGB16 classic-TIFF reader for the larger native fixture."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct

import numpy as np

DESCRIPTION = (
    "Linear camera-native RGB (sensor primaries), NO colour matrix, no transfer curve. "
    "THIS IS NOT sRGB -- do not treat it as such. This is the measurement output. "
    "White balance: as-shot per-channel gains, green = 1, applied AFTER black subtraction "
    "and normalisation by (white - black), and AFTER the noise model, which is calibrated "
    "in raw DN before any gain."
)
SOFTWARE = "strehl 0.0.0"
RANGE = 14848.0
LIMIT = 1_048_576


class Refusal(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Refusal(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_rgb_tiff(path, expected_shape, expected_sha, budget):
    """Read actual referenced strips; return native u16 pixels and own evidence."""
    budget.check()
    require(type(expected_shape) in (tuple, list) and len(expected_shape) == 3
            and all(type(x) is int for x in expected_shape)
            and 1 <= expected_shape[0] <= 240 and 1 <= expected_shape[1] <= 320
            and expected_shape[2] == 3, "typed native-bounded expected RGB shape")
    require(type(expected_sha) is str and len(expected_sha) == 64
            and all(c in "0123456789abcdef" for c in expected_sha), "external TIFF SHA required")
    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    require(8 <= len(raw) <= LIMIT, "bounded TIFF size")
    file_sha = digest(raw)
    require(expected_sha == file_sha, "external TIFF SHA mismatch")
    require(raw[:2] in (b"II", b"MM"), "TIFF byte order")
    endian = "<" if raw[:2] == b"II" else ">"

    def unpack(fmt, at):
        size = struct.calcsize(endian + fmt)
        require(0 <= at <= len(raw) - size, "out-of-file TIFF field")
        return struct.unpack_from(endian + fmt, raw, at)

    require(unpack("H", 2)[0] == 42, "classic TIFF magic")
    ifd = unpack("I", 4)[0]
    require(ifd >= 8, "IFD overlaps header")
    n = unpack("H", ifd)[0]
    require(1 <= n <= 64, "bounded IFD entries")
    ifd_end = ifd + 2 + 12 * n + 4
    require(ifd_end <= len(raw), "truncated IFD")
    require(unpack("I", ifd_end - 4)[0] == 0, "multiple IFDs forbidden")
    occupied = [(0, 8, "header"), (ifd, ifd_end, "IFD")]
    allowed = {256, 257, 258, 259, 262, 270, 273, 274, 277, 278, 279,
               282, 283, 284, 296, 305, 317, 339}
    tags = {}
    for i in range(n):
        entry = ifd + 2 + 12 * i
        tag, typ, count = unpack("HHI", entry)
        require(tag in allowed, f"unknown or forbidden tag {tag}")
        require(tag not in tags, f"duplicate tag {tag}")
        require(typ in (2, 3, 4, 5) and 1 <= count <= 4096, "unsupported type/count")
        require((typ == 2) == (tag in (270, 305)), "wrong ASCII tag type")
        require((typ == 5) == (tag in (282, 283)), "wrong rational tag type")
        if tag in (258, 259, 262, 274, 277, 284, 296, 317, 339):
            require(typ == 3, "SHORT tag type")
        size = {2: 1, 3: 2, 4: 4, 5: 8}[typ] * count
        at = entry + 8 if size <= 4 else unpack("I", entry + 8)[0]
        require(0 <= at <= len(raw) - size, "tag payload outside file")
        if size > 4:
            occupied.append((at, at + size, f"tag{tag}"))
        if typ == 2:
            value = raw[at:at + size]
            require(value.endswith(b"\0") and b"\0" not in value[:-1], "ASCII termination")
            try:
                value = value[:-1].decode("ascii")
            except UnicodeDecodeError as error:
                raise Refusal("non-ASCII tag") from error
        elif typ == 5:
            require(count == 1, "resolution count")
            value = unpack("II", at)
        else:
            value = unpack(("H" if typ == 3 else "I") * count, at)
        tags[tag] = dict(type=typ, count=count, value=value)

    def numbers(tag, default=None):
        if tag not in tags:
            require(default is not None, f"missing tag {tag}")
            return tuple(default)
        require(tags[tag]["type"] in (3, 4), f"noninteger tag {tag}")
        return tags[tag]["value"]

    def scalar(tag, default=None):
        values = numbers(tag, None if default is None else (default,))
        require(len(values) == 1, f"nonscalar tag {tag}")
        return values[0]

    width, height = scalar(256), scalar(257)
    channels = 3
    require(1 <= width <= 320 and 1 <= height <= 240, "bounded native dimensions")
    shape = (height, width, 3)
    require(tuple(expected_shape) == shape, "expected TIFF dimensions/channels")
    require(scalar(277, 1) == channels, "sample count")
    require(numbers(258) == (16,) * channels, "bits per sample")
    require(numbers(339, (1,) * channels) == (1,) * channels, "unsigned sample format")
    require(scalar(259) == 1, "compression")
    require(scalar(262) == 2, "RGB photometric")
    for tag, label in ((274, "orientation"), (284, "planar config"), (317, "predictor")):
        require(scalar(tag, 1) == 1, label)
    for tag in (282, 283):
        if tag in tags:
            require(tags[tag]["value"] == (1, 1), "measurement resolution")
    require(scalar(296, 1) == 1, "resolution unit")
    require(tags.get(270, {}).get("value") == DESCRIPTION, "CameraLinear description")
    require(tags.get(305, {}).get("value") == SOFTWARE, "measurement software")
    rows = scalar(278)
    require(rows > 0, "zero rows per strip")
    offsets, counts = numbers(273), numbers(279)
    require(len(offsets) == len(counts) == math.ceil(height / rows), "strip count")
    payloads = []
    for i, (offset, count) in enumerate(zip(offsets, counts, strict=True)):
        expected = min(rows, height - i * rows) * width * channels * 2
        require(count == expected, "strip byte count")
        require(8 <= offset <= len(raw) - count, "strip outside file")
        occupied.append((offset, offset + count, f"strip{i}"))
        payloads.append(raw[offset:offset + count])
    occupied.sort()
    require(all(a[1] <= b[0] for a, b in zip(occupied, occupied[1:])), "referenced regions overlap")
    require(occupied[-1][1] == len(raw), "unreferenced trailing bytes")
    # Both wire-backed and returned arrays count while simultaneously live.
    # The separately bounded Python byte buffers are not claimed as process RSS.
    budget.check_allocation(shape, endian + "u2")
    wire = np.frombuffer(b"".join(payloads), dtype=endian + "u2").reshape(shape)
    budget.watch(wire, "RGB TIFF wire payload")
    budget.check_allocation(shape, "<u2")
    pixels = np.array(wire, dtype="<u2", copy=True, order="C")
    budget.watch(pixels, "RGB TIFF decoded pixels")
    pixel_sha = digest(pixels.tobytes(order="C"))
    evidence = dict(path=str(path.resolve()), bytes=len(raw), sha256=file_sha,
                    pixel_sha256=pixel_sha, shape=list(shape), kind="rgb",
                    endian=endian, strip_count=len(offsets), tags=tags)
    budget.check()
    return pixels, evidence

