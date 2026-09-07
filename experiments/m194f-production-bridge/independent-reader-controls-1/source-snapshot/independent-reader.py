"""Independent bounded classic-TIFF reader and M194f delivered-value oracles."""
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


def read_tiff(path, kind, expected_shape, expected_sha=None):
    """Read actual referenced strips; return native u16 pixels and own evidence."""
    require(kind in ("rgb", "gray"), "unknown image kind")
    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    require(8 <= len(raw) <= LIMIT, "bounded TIFF size")
    file_sha = digest(raw)
    require(expected_sha is None or expected_sha == file_sha, "external TIFF SHA mismatch")
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
    channels = 3 if kind == "rgb" else 1
    require(1 <= width <= 128 and 1 <= height <= 128, "bounded dimensions")
    shape = (height, width, 3) if channels == 3 else (height, width)
    require(tuple(expected_shape) == shape, "expected TIFF dimensions/channels")
    require(scalar(277, 1) == channels, "sample count")
    require(numbers(258) == (16,) * channels, "bits per sample")
    require(numbers(339, (1,) * channels) == (1,) * channels, "unsigned sample format")
    require(scalar(259) == 1, "compression")
    require(scalar(262) == (2 if channels == 3 else 1), "photometric")
    for tag, label in ((274, "orientation"), (284, "planar config"), (317, "predictor")):
        require(scalar(tag, 1) == 1, label)
    for tag in (282, 283):
        if tag in tags:
            require(tags[tag]["value"] == (1, 1), "measurement resolution")
    require(scalar(296, 1) == 1, "resolution unit")
    if channels == 3:
        require(tags.get(270, {}).get("value") == DESCRIPTION, "CameraLinear description")
        require(tags.get(305, {}).get("value") == SOFTWARE, "measurement software")
    else:
        require(270 not in tags and 305 not in tags, "unexpected Gray description/software")
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
    pixels = np.frombuffer(b"".join(payloads), dtype=endian + "u2").astype(np.uint16).reshape(shape)
    pixel_sha = digest(pixels.astype("<u2").tobytes())
    evidence = dict(path=str(path.resolve()), bytes=len(raw), sha256=file_sha,
                    pixel_sha256=pixel_sha, shape=list(shape), kind=kind,
                    endian=endian, strip_count=len(offsets), tags=tags)
    return pixels, evidence


def oracle(scene, x, y):
    x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    if scene == "constant":
        rgb = np.stack((np.full_like(x, 2000), np.full_like(x, 3000), np.full_like(x, 2500)), -1)
    else:
        require(scene == "affine", "unknown oracle scene")
        rgb = np.stack((2000 + 80*x, 3000 + 100*y, 2500 + 40*x + 60*y), -1)
    return rgb * np.array([.75*float(np.float32(4/3)), 1, .6*float(np.float32(5/3))])


def quantize(dn):
    return np.floor(np.clip(np.asarray(dn)/RANGE, 0, 1)*65535 + .5).astype(np.uint16)


def coordinate_check(pixels, scene, expected=None):
    require(pixels.shape == (32, 48, 3), "private RGB shape")
    y, x = np.mgrid[14:18, 14:34]
    if expected is None:
        expected = oracle(scene, x + 6, y + 10)
    actual = pixels[14:18, 14:34].astype(float)*RANGE/65535
    delta = np.abs(actual - expected)
    require(delta.shape == (4, 20, 3) and np.isfinite(delta).all(), "oracle samples")
    require(float(delta.max()) <= .25, f"coordinate/value error {float(delta.max())} DN")
    return dict(sites=80, max_abs_dn=float(delta.max()), per_channel_max_dn=delta.max((0, 1)).tolist())


def mutation_check(original, changed):
    require(original.shape == changed.shape == (32, 48, 3), "mutation shape")
    old, new = int(original[16, 23, 1]), int(changed[16, 23, 1])
    increase = (new-old)*RANGE/65535
    require(0 < old < 65535 and 0 < new < 65535, "mutation clipping")
    require(increase > 63.5, f"green mutation unpowered {increase} DN")
    return dict(native_xy=[29, 26], output_xy=[23, 16], increase_dn=increase)


def rank_oracle(values=(100, 200, 200, 400, 500), targets=(99, 100, 200, 201, 300, 400, 500, 501)):
    below = np.array([sum(v < t for v in values) for t in targets], dtype=np.uint32)
    seen = np.full(len(targets), len(values), dtype=np.uint32)
    code = np.floor((1-2*np.abs(below.astype(float)/seen-.5))*1000 + .5).astype(np.uint16)
    return tuple(np.tile(a, (8, 2)) for a in (below, seen, code))


def rank_check(pixels, below, seen, unseen_index=None):
    expected_below, expected_seen, expected = rank_oracle()
    if unseen_index is not None:
        require(type(unseen_index) is int and 0 <= unseen_index < 128, "unseen index")
        expected_seen.flat[unseen_index] = 0
        expected.flat[unseen_index] = 65535
    require(pixels.shape == (8, 16), "rank image shape")
    require(np.array_equal(np.asarray(below).reshape(8, 16), expected_below), "actual strict-below counts")
    require(np.array_equal(np.asarray(seen).reshape(8, 16), expected_seen), "actual seen counts")
    require(np.array_equal(pixels, expected), "actual rank/sentinel pixels")
    return dict(samples=128, codes=np.unique(pixels).tolist(), unseen_index=unseen_index)


def genuine_confidence_check(pixels, expected_shape):
    require(pixels.shape == tuple(expected_shape), "genuine confidence quad shape")
    require(set(np.unique(pixels)).issubset({0, 400, 800}), "genuine confidence code/coverage")
    return dict(shape=list(pixels.shape), codes=np.unique(pixels).tolist())
