from __future__ import annotations

import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Iterable

import numpy as np
import tifffile


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SUBJECT = Path(
    r"D:\personal\macro\requests\misc-diagnostic"
    r"\high-res-calibration-slide-cpl\tilted-sw10-cpl"
)
WARP_MAP = Path(
    r"D:\strehl-out\cover-default-slide-v2"
    r"\warpmaps\tilted-sw10.warpmap.txt"
)
DECODER = Path(r"D:\strehl-out\cover-default\target\release\strehl.exe")
COMPARATOR = Path(r"C:\dev\macro\focus-stack\dist\focus-stack.exe")
CHECKER = ROOT / "checker.py"

EXPECTED = {
    "subject": "tilted-sw10-cpl",
    "frames": 92,
    "width": 3516,
    "height": 2344,
    "reference": 46,
    "reference_file": "DSC00062.ARW",
    "stack_digest": "3c8796d7fd1acf46",
    "source_inventory_sha256": (
        "500753BD7F5F11C06882A9A3D2DECE82A07CE0BB93F52CADC13CD8A4E624B759"
    ),
    "warp_map_sha256": (
        "DB982BEDAE1172EB51D5787F4C6746C1FD552E33077CCAFAD5469BC96D6B10D1"
    ),
    "decoder_sha256": (
        "1AC423529D5AAD88B7141801E47DCD612FCA8061558578A88592DB715CE81A0F"
    ),
    "comparator_sha256": (
        "0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D"
    ),
    "checker_sha256": (
        "B66C9465D5F644D66646A14722475987F187E32B02ED3B687997C18CE1670B89"
    ),
    "crop": {"x": 62, "y": 41, "width": 3392, "height": 2262},
}

# IEC 61966-2-1 linear sRGB/BT.709 D65 to ITU-R BT.2020 D65.
SRGB_TO_REC2020 = np.array(
    [
        [0.6274038959346991, 0.3292830383778841, 0.04331306568741707],
        [0.06909728935823203, 0.9195403950754587, 0.01136231556630915],
        [0.01639143887515027, 0.08801330787722583, 0.8955952532476241],
    ],
    dtype=np.float64,
)

COMPARATOR_OPTIONS = [
    "--no-align",
    "--no-transform",
    "--no-whitebalance",
    "--no-contrast",
    "--nocrop",
    "--input-colorspace=linear-rec2020",
    "--internal-colorspace=linear",
    "--output-colorspace=linear-rec2020",
    "--output-bitdepth=16",
    "--hdr-preserve=off",
    "--threads=6",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def byte_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def pixel_sha256(image: np.ndarray) -> str:
    h = hashlib.sha256()
    h.update(str(image.dtype).encode("ascii"))
    h.update(struct.pack("<I", image.ndim))
    h.update(struct.pack("<" + "Q" * image.ndim, *image.shape))
    h.update(np.ascontiguousarray(image).tobytes())
    return h.hexdigest().upper()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".new")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)


def assert_hash(path: Path, expected: str) -> None:
    got = sha256(path)
    if got != expected:
        raise RuntimeError(f"{path}: SHA-256 {got}, expected {expected}")


def _s15f16(value: float) -> bytes:
    scaled = int(round(value * 65536.0))
    if not -(1 << 31) <= scaled < (1 << 31):
        raise ValueError(value)
    return struct.pack(">i", scaled)


def _xyz_tag(values: Iterable[float]) -> bytes:
    return b"XYZ " + b"\0" * 4 + b"".join(_s15f16(v) for v in values)


def _curve_identity_tag() -> bytes:
    return b"curv" + b"\0" * 4 + struct.pack(">I", 0)


def _desc_tag(text: str) -> bytes:
    ascii_text = text.encode("ascii") + b"\0"
    return (
        b"desc"
        + b"\0" * 4
        + struct.pack(">I", len(ascii_text))
        + ascii_text
        + struct.pack(">II", 0, 0)
        + struct.pack(">HB", 0, 0)
        + b"\0" * 67
    )


def _text_tag(text: str) -> bytes:
    return b"text" + b"\0" * 4 + text.encode("ascii") + b"\0"


def _sf32_tag(values: Iterable[float]) -> bytes:
    return b"sf32" + b"\0" * 4 + b"".join(_s15f16(v) for v in values)


def linear_rec2020_icc() -> bytes:
    """Build a deterministic ICC v2 matrix/shaper profile with identity TRCs."""
    d50 = (0.9642956764295677, 1.0, 0.8251046025104605)
    colorants = {
        b"rXYZ": (0.6735154631882762, 0.27905900514112053, -0.00193242713400435),
        b"gXYZ": (0.1656972637039047, 0.6753180057491098, 0.02997782679282918),
        b"bXYZ": (0.12508294953738716, 0.04562298910976963, 0.7970592028516356),
    }
    chad = (
        1.0479297925449969,
        0.02294687060160967,
        -0.05019226628920519,
        0.0296278087700558,
        0.9904344267538798,
        -0.01707379906341879,
        -0.00924304064620451,
        0.01505519149029814,
        0.7518742814281372,
    )
    payloads: dict[bytes, bytes] = {
        b"desc": _desc_tag("M8 Linear Rec.2020 D65"),
        b"cprt": _text_tag("M8 comparative controlled instrument"),
        b"wtpt": _xyz_tag(d50),
        b"rXYZ": _xyz_tag(colorants[b"rXYZ"]),
        b"gXYZ": _xyz_tag(colorants[b"gXYZ"]),
        b"bXYZ": _xyz_tag(colorants[b"bXYZ"]),
        b"TRC0": _curve_identity_tag(),
        b"chad": _sf32_tag(chad),
    }
    tag_payload = {
        b"desc": b"desc",
        b"cprt": b"cprt",
        b"wtpt": b"wtpt",
        b"rXYZ": b"rXYZ",
        b"gXYZ": b"gXYZ",
        b"bXYZ": b"bXYZ",
        b"rTRC": b"TRC0",
        b"gTRC": b"TRC0",
        b"bTRC": b"TRC0",
        b"chad": b"chad",
    }
    tags = list(tag_payload)
    offset = 128 + 4 + 12 * len(tags)
    offsets: dict[bytes, tuple[int, int]] = {}
    body = bytearray()
    for key, payload in payloads.items():
        while (offset + len(body)) % 4:
            body.append(0)
        start = offset + len(body)
        body.extend(payload)
        offsets[key] = (start, len(payload))
    size = offset + len(body)
    header = bytearray(128)
    struct.pack_into(">I", header, 0, size)
    header[4:8] = b"M8  "
    struct.pack_into(">I", header, 8, 0x02400000)
    header[12:16] = b"mntr"
    header[16:20] = b"RGB "
    header[20:24] = b"XYZ "
    struct.pack_into(">6H", header, 24, 2026, 9, 2, 0, 0, 0)
    header[36:40] = b"acsp"
    header[40:44] = b"MSFT"
    header[48:52] = b"M8  "
    header[52:56] = b"R202"
    struct.pack_into(">I", header, 64, 1)
    header[68:80] = _xyz_tag(d50)[8:]
    header[80:84] = b"M8  "
    table = bytearray(struct.pack(">I", len(tags)))
    for signature in tags:
        start, length = offsets[tag_payload[signature]]
        table.extend(signature + struct.pack(">II", start, length))
    return bytes(header + table + body)


def write_icc(path: Path) -> dict:
    data = linear_rec2020_icc()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": str(path.resolve()), "sha256": byte_sha256(data), "bytes": len(data)}


def write_rgb16(path: Path, image: np.ndarray, icc: bytes, description: str) -> None:
    if image.dtype != np.uint16 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"expected uint16 HxWx3, got {image.dtype} {image.shape}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(
        path,
        np.ascontiguousarray(image),
        photometric="rgb",
        compression=None,
        metadata=None,
        description=description,
        extratags=[
            (274, "H", 1, 1, False),
            (34675, "B", len(icc), icc, False),
        ],
    )


def read_rgb16(path: Path) -> np.ndarray:
    image = np.asarray(tifffile.imread(path))
    if image.dtype != np.uint16 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"{path}: expected uint16 HxWx3, got {image.dtype} {image.shape}")
    return image


def tiff_tags(path: Path) -> dict:
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        orientation = int(page.tags[274].value) if 274 in page.tags else 1
        icc = bytes(page.tags[34675].value) if 34675 in page.tags else None
        compression = str(page.compression.name)
        photometric = str(page.photometric.name)
        return {
            "shape": list(page.shape),
            "dtype": str(page.dtype),
            "orientation": orientation,
            "icc_sha256": byte_sha256(icc) if icc is not None else None,
            "icc_bytes": len(icc) if icc is not None else 0,
            "compression": compression,
            "photometric": photometric,
        }


def image_census(image: np.ndarray) -> dict:
    return {
        "minimum": [int(image[..., c].min()) for c in range(3)],
        "maximum": [int(image[..., c].max()) for c in range(3)],
        "zero": [int(np.count_nonzero(image[..., c] == 0)) for c in range(3)],
        "full": [int(np.count_nonzero(image[..., c] == 65535)) for c in range(3)],
    }


def canonicalize_with_icc(source: Path, destination: Path, icc: bytes) -> dict:
    image = read_rgb16(source)
    before = pixel_sha256(image)
    write_rgb16(
        destination,
        image,
        icc,
        "M8 controlled comparator output; linear Rec.2020 D65; identity TRCs",
    )
    after_image = read_rgb16(destination)
    after = pixel_sha256(after_image)
    if before != after or not np.array_equal(image, after_image):
        raise RuntimeError("metadata-only canonicalization changed sample values")
    return {
        "direct_path": str(source.resolve()),
        "direct_sha256": sha256(source),
        "canonical_path": str(destination.resolve()),
        "canonical_sha256": sha256(destination),
        "pixel_sha256": before,
        "pixel_array_unchanged": True,
        "direct_tags": tiff_tags(source),
        "canonical_tags": tiff_tags(destination),
        "census": image_census(image),
    }


def f64_from_bits(text: str) -> float:
    return struct.unpack(">d", bytes.fromhex(text))[0]


def parse_warp_map(path: Path = WARP_MAP) -> dict:
    assert_hash(path, EXPECTED["warp_map_sha256"])
    header: dict[str, str] = {}
    placements = []
    saw_end = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        key = fields[0]
        if key == "placed" or (len(fields) > 1 and fields[1] == "placed"):
            idx = int(fields[0])
            bits = fields[2:6]
            placements.append(
                {
                    "index": idx,
                    "bits": bits,
                    "a_re": f64_from_bits(bits[0]),
                    "a_im": f64_from_bits(bits[1]),
                    "b_re": f64_from_bits(bits[2]),
                    "b_im": f64_from_bits(bits[3]),
                }
            )
        elif key == "end":
            saw_end = True
            if int(fields[1]) != EXPECTED["frames"]:
                raise RuntimeError("warp map end count changed")
        elif len(fields) >= 2:
            header[key] = fields[1]
    required = {
        "stack-name": EXPECTED["subject"],
        "stack-digest": EXPECTED["stack_digest"],
        "frames": str(EXPECTED["frames"]),
        "plane": f"{EXPECTED['width']}x{EXPECTED['height']}",
        "reference": str(EXPECTED["reference"]),
        "resampler": "catmull-rom",
    }
    for key, want in required.items():
        if header.get(key) != want:
            raise RuntimeError(f"warp map {key}={header.get(key)!r}, expected {want!r}")
    if not saw_end or [p["index"] for p in placements] != list(range(EXPECTED["frames"])):
        raise RuntimeError("warp map placements are incomplete or out of order")
    return {"header": header, "placements": placements}


def comparator_command(inputs: list[Path], output: Path) -> list[str]:
    return [
        str(COMPARATOR),
        *COMPARATOR_OPTIONS,
        f"--output={output}",
        *[str(path) for path in inputs],
    ]


def bounded_environment() -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("STREHL_"):
            del env[key]
    for key in [
        "RAYON_NUM_THREADS",
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "BLIS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ]:
        env[key] = "6"
    env["PYTHONIOENCODING"] = "utf-8"
    return env

