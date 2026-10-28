"""Bounded developed-RGB comparator inputs. Importing performs no image/file work."""
from pathlib import Path
from dataclasses import dataclass, field
import hashlib
import json
import math
import struct

import cv2
import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "outputs/raw-quality-2026-10-26"
EXPORT = BASE / "weevil-107-tiff-export/receipt.json"
ORDER = BASE / "weevil-107-baseline/input-order.json"
MAP = BASE / "weevil-107-ca-off-alignment.txt"
PINS = ((EXPORT, "461ecb3a8e44a82005ed6883718aa85276a74a2ebfca31fb0628809c4ba315a0"),
        (ORDER, "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f"),
        (MAP, "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"))
ICC_SHA = "238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b"
MAX_TILE_PIXELS = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_ref(path):
    path = Path(path).resolve(strict=True)
    require(path.suffix.lower() != ".arw", "developed-image bridge cannot read RAW")
    first = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    final = path.stat()
    require((first.st_size, first.st_mtime_ns) == (final.st_size, final.st_mtime_ns), "file changed during hashing")
    return dict(path=str(path), bytes=final.st_size, mtime_ns=final.st_mtime_ns, sha256=digest.hexdigest())


@dataclass
class Context:
    paths: tuple
    maps: tuple
    frames: tuple
    bindings: list
    stats: tuple
    metadata: dict
    width: int = 6896
    height: int = 4596
    source_width: int = 7032
    source_height: int = 4688
    crop_offset: tuple = (68.0, 46.0)
    center: tuple = (3516.0, 2344.0)
    icc: bytes | None = None
    headers_checked: bool = False
    gather_calls: int = 0
    gathered_pixels_per_source: int = 0
    header_records: list = field(default_factory=list)


def load_manifest():
    """Pin three small manifests; no TIFF payload hash or RAW decode."""
    bindings = []
    for path, expected in PINS:
        binding = file_ref(path)
        require(binding["sha256"] == expected, "frozen manifest/map changed")
        bindings.append(binding)
    export = json.loads(EXPORT.read_text(encoding="utf-8"))
    order = json.loads(ORDER.read_text(encoding="utf-8"))
    require(export["status"] == "299_UNALIGNED_NATIVE_RGB16_DEVELOPED"
            and export["input_content_and_metadata_unchanged"] and export["golden"]["status"] == "EXACT"
            and export["active_wh"] == [7032, 4688] and len(export["frames"]) == len(order) == 299,
            "complete developed export required")
    frames = tuple(export["frames"])
    paths, stats = [], []
    for index, (record, original) in enumerate(zip(frames, order)):
        path = Path(record["output"]).resolve(strict=True)
        require(record["ordinal"] == index and original["index"] == index
                and record["input"] == original and record["output_wh"] == [7032, 4688]
                and record["raw_active_xywh"] == [0, 0, 7032, 4688]
                and record["input_wb_bits"] == export["wb_bits"]
                and path.parent == (BASE / "weevil-107-tiff-export/frames").resolve()
                and path.name == f"DSC{index + 1:05d}.tiff", "source ordinal/development/path mismatch")
        stat = path.stat()
        require(stat.st_size == record["output_bytes"], "TIFF byte count changed")
        paths.append(path)
        stats.append((stat.st_size, stat.st_mtime_ns))
    require(len(set(paths)) == 299, "duplicate developed inputs")
    transforms = {}
    headers = {}
    for line in MAP.read_text(encoding="utf-8").splitlines():
        row = line.split("#", 1)[0].split()
        if not row:
            continue
        if row[0].isdigit():
            index = int(row[0])
            require(row[1] == "placed" and len(row) == 6 and index not in transforms, "complete placed map required")
            values = tuple(struct.unpack("<d", int(v, 16).to_bytes(8, "little"))[0] for v in row[2:])
            require(all(math.isfinite(v) for v in values) and values[0] ** 2 + values[1] ** 2 > 0, "finite invertible similarity")
            transforms[index] = values
        else:
            headers[row[0]] = row[1:]
    require(set(transforms) == set(range(299)) and headers["reference"] == ["149"]
            and headers["plane"] == ["3516x2344"] and headers["resampler"] == ["catmull-rom"]
            and headers["frames"] == headers["end"] == ["299"], "held map gauge")
    metadata = dict(source_count=299, source_order=list(range(299)), reference=149,
         output_wh=[6896, 4596], source_wh=[7032, 4688], crop_offset=[68, 46], native_center=[3516, 2344],
         wb_bits=export["wb_bits"], tone_bits=export["tone_bits"], xyz_to_cam_bits=export["xyz_to_cam_bits"],
         levels=export["levels"], source_scope=export["scope"], source_export_executable_sha256=export["executable_sha256"],
         map_f64_bits=[[f"{struct.unpack('<Q', struct.pack('<d', v))[0]:016x}" for v in transforms[i]] for i in range(299)],
         resampler="OpenCV INTER_CUBIC in developed encoded RGB, float32; distinct from native Catmull-Rom",
         quantization="clip to0..65535 then floor(value+0.5) to uint16 after bounded float32 remap",
         channels="RGB; caller must use RGB2GRAY or explicitly reverse to upstream BGR",
         no_RAW_reads=True, aligned_full_frame_volume=False, max_tile_pixels=MAX_TILE_PIXELS)
    return Context(tuple(paths), tuple(transforms[i] for i in range(299)), frames, bindings, tuple(stats), metadata)


def check_headers(ctx):
    """Inspect every TIFF header/memmap layout only; no full pixel-array decode."""
    records, common_icc = [], None
    for index, path in enumerate(ctx.paths):
        _check_stat(ctx, index)
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            require(len(tif.pages) == 1 and page.shape == (4688, 7032, 3)
                    and page.dtype == np.dtype("uint16") and int(page.compression) == 1
                    and int(page.photometric) == 2 and int(page.planarconfig) == 1, "RGB16 uncompressed contiguous layout required")
            icc = bytes(page.tags[34675].value)
            require(hashlib.sha256(icc).hexdigest() == ICC_SHA, "source ICC changed")
            if common_icc is None:
                common_icc = icc
            require(icc == common_icc, "literal source ICC mismatch")
            record = dict(index=index, path=str(path), shape=list(page.shape), dtype=str(page.dtype),
                          compression=int(page.compression), planarconfig=int(page.planarconfig),
                          dataoffsets=list(page.dataoffsets), databytecounts=list(page.databytecounts), icc_sha256=ICC_SHA)
        mm = tifffile.memmap(path, mode="r")
        try:
            require(mm.shape == (4688, 7032, 3) and mm.dtype == np.uint16 and mm.flags.c_contiguous,
                    "read-only direct TIFF memory mapping required")
            record["memmap_strides"] = list(mm.strides)
        finally:
            mm._mmap.close()
        corners = []
        for x, y in ((0, 0), (ctx.width - 1, 0), (ctx.width - 1, ctx.height - 1), (0, ctx.height - 1)):
            sx, sy = _coordinates((x, y, 1, 1), ctx.maps[index], ctx.center, ctx.crop_offset)
            corners.append((float(sx[0, 0]), float(sy[0, 0])))
        x_min, x_max = min(p[0] for p in corners), max(p[0] for p in corners)
        y_min, y_max = min(p[1] for p in corners), max(p[1] for p in corners)
        require(x_min >= 1.5 and y_min >= 1.5 and x_max <= ctx.source_width - 2.5
                and y_max <= ctx.source_height - 2.5, "full delivered canvas exceeds cubic source support")
        record["full_canvas_source_support"] = dict(corners=corners, x_min=x_min, x_max=x_max,
             y_min=y_min, y_max=y_max, covered=True, scope="Affine extrema at four delivered-canvas corners; f32 remap coordinates.")
        records.append(record)
        _check_stat(ctx, index)
    ctx.icc, ctx.headers_checked, ctx.header_records = common_icc, True, records
    return dict(status="ALL299_RGB16_HEADERS_VERIFIED", headers=records, full_payload_hashes_checked=False,
                dependencies=dict(numpy=np.__version__, opencv=cv2.__version__, tifffile=tifffile.__version__))


def _check_stat(ctx, index):
    stat = ctx.paths[index].stat()
    require((stat.st_size, stat.st_mtime_ns) == ctx.stats[index], "developed source metadata changed")


def hash_inputs(ctx):
    """One full sequential59GB identity sweep, root-scheduled before full work."""
    rows = []
    for index, path in enumerate(ctx.paths):
        _check_stat(ctx, index)
        binding = file_ref(path)
        record = ctx.frames[index]
        require(binding["sha256"] == record["output_sha256"] and binding["bytes"] == record["output_bytes"],
                "developed source content differs from frozen export")
        rows.append(binding)
    return rows


def verify_inputs(ctx, rows):
    """One full after sweep; never called implicitly for each tile."""
    after = hash_inputs(ctx)
    require(after == rows, "input bytes/metadata changed during comparison")
    for expected in ctx.bindings:
        require(file_ref(expected["path"]) == expected, "manifest/map changed during comparison")
    return dict(input_bytes_and_metadata_unchanged=True, sources=after, bindings=ctx.bindings)


def _coordinates(rect, transform, center, offset):
    x, y, w, h = rect
    ar, ai, br, bi = transform
    # f64 retained geometric map, then explicit f32 remap coordinates. The
    # existing CPU fullres route uses this center, without the research +0.5.
    xx = np.arange(x, x + w, dtype=np.float64)[None, :] + offset[0] - center[0]
    yy = np.arange(y, y + h, dtype=np.float64)[:, None] + offset[1] - center[1]
    sx = (center[0] + ar * xx - ai * yy + 2 * br).astype(np.float32)
    sy = (center[1] + ai * xx + ar * yy + 2 * bi).astype(np.float32)
    return sx, sy


def _sample_rgb(source, sx, sy):
    require(source.dtype == np.uint16 and source.ndim == 3 and source.shape[2] == 3,
            "RGB uint16 source required")
    require(sx.shape == sy.shape and sx.dtype == sy.dtype == np.float32
            and np.isfinite(sx).all() and np.isfinite(sy).all(), "finite f32 coordinates")
    height, width, _ = source.shape
    require(float(sx.min()) >= 1.5 and float(sy.min()) >= 1.5
            and float(sx.max()) <= width - 2.5 and float(sy.max()) <= height - 2.5,
            "source interpolation footprint outside held common support")
    x0, y0 = math.floor(float(sx.min())) - 1, math.floor(float(sy.min())) - 1
    x1, y1 = math.floor(float(sx.max())) + 3, math.floor(float(sy.max())) + 3
    roi = np.array(source[y0:y1, x0:x1], dtype=np.float32, copy=True, order="C")
    # Integer ROI subtraction follows global f32 coordinate formation, so
    # changing tile boundaries does not change the nominal fractional phase.
    result = cv2.remap(roi, sx - np.float32(x0), sy - np.float32(y0), cv2.INTER_CUBIC,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    require(np.isfinite(result).all(), "nonfinite developed interpolation")
    np.clip(result, 0, 65535, out=result)
    np.add(result, np.float32(.5), out=result)
    np.floor(result, out=result)
    return result.astype(np.uint16)


def gather_tile(ctx, rect_xywh):
    """All299 ordered RGB16 inputs for one bounded in-canvas consumer region."""
    require(ctx.headers_checked, "check_headers must precede gathering")
    require(len(rect_xywh) == 4 and all(type(v) is int for v in rect_xywh), "integer xywh rectangle")
    x, y, w, h = rect_xywh
    require(w > 0 and h > 0 and w * h <= MAX_TILE_PIXELS and x >= 0 and y >= 0
            and x + w <= ctx.width and y + h <= ctx.height, "bounded in-canvas tile required")
    result = np.empty((299, h, w, 3), dtype=np.uint16)
    for index, path in enumerate(ctx.paths):
        _check_stat(ctx, index)
        sx, sy = _coordinates(rect_xywh, ctx.maps[index], ctx.center, ctx.crop_offset)
        source = tifffile.memmap(path, mode="r")
        try:
            result[index] = _sample_rgb(source, sx, sy)
        finally:
            source._mmap.close()
        _check_stat(ctx, index)
    ctx.gather_calls += 1
    ctx.gathered_pixels_per_source += w * h
    return result


def coordinate_controls():
    """Pure generated check of the actual remap path; root alone executes it."""
    yy, xx = np.mgrid[:96, :128]
    source = np.stack((1000 + 101 * xx + 37 * yy,
                       2000 + 19 * xx + 83 * yy,
                       3000 + 53 * xx + 11 * yy), axis=-1).astype(np.uint16)
    rect, center, offset = (40, 32, 24, 16), (64.0, 48.0), (0.0, 0.0)
    sx, sy = _coordinates(rect, (1.0, 0.0, 0.0, 0.0), center, offset)
    ident = _sample_rgb(source, sx, sy)
    identity_exact = np.array_equal(ident, source[32:48, 40:64])
    sx, sy = _coordinates((4, 4, 24, 16), (1.0, 0.0, 0.0, 0.0), center, (68.0, 46.0))
    cropped = _sample_rgb(source, sx, sy)
    crop_offset_exact = np.array_equal(cropped, source[50:66, 72:96])
    sx, sy = _coordinates(rect, (1.0, 0.0, 1.0, -.5), center, offset)
    translated = _sample_rgb(source, sx, sy)
    translation_exact = np.array_equal(translated, source[31:47, 42:66])
    transform = (1.25, .125, 1.5, -1.0)
    sx, sy = _coordinates(rect, transform, center, offset)
    expected_x = np.empty(sx.shape, np.float32)
    expected_y = np.empty(sy.shape, np.float32)
    for v in range(rect[3]):
        for u in range(rect[2]):
            dx, dy = rect[0] + u - 64.0, rect[1] + v - 48.0
            expected_x[v, u] = 64.0 + 1.25 * dx - .125 * dy + 3.0
            expected_y[v, u] = 48.0 + .125 * dx + 1.25 * dy - 2.0
    coordinates_exact = np.array_equal(sx, expected_x) and np.array_equal(sy, expected_y)
    good = _sample_rgb(source, sx, sy)
    bx, by = _coordinates(rect, transform, (64.5, 48.5), offset)
    wrong_center = _sample_rgb(source, bx, by)
    phase_foil_diff = int(np.count_nonzero(good != wrong_center))
    rgb_gray = cv2.cvtColor(good, cv2.COLOR_RGB2GRAY)
    wrong_gray = cv2.cvtColor(good, cv2.COLOR_BGR2GRAY)
    channel_foil_diff = int(np.count_nonzero(rgb_gray != wrong_gray))
    pieces = []
    for tile_rect in ((40, 32, 12, 16), (52, 32, 12, 16)):
        a, b = _coordinates(tile_rect, transform, center, offset)
        pieces.append(_sample_rgb(source, a, b))
    partition_exact = np.array_equal(good, np.concatenate(pieces, axis=1))
    require(identity_exact and crop_offset_exact and translation_exact and coordinates_exact and partition_exact
            and phase_foil_diff > 0 and channel_foil_diff > 0, "input bridge coordinate/channel control failed")
    return dict(status="INPUT_BRIDGE_COORDINATES_VERIFIED", identity_exact=identity_exact,
         native_crop_offset_exact=crop_offset_exact,
         integer_translation_exact=translation_exact, geometric_coordinates_exact=coordinates_exact,
         tile_partition_exact=partition_exact, wrong_half_pixel_center_differing_samples=phase_foil_diff,
         wrong_BGR_gray_differing_pixels=channel_foil_diff, interpolation="cv2.INTER_CUBIC",
         native_Catmull_pixel_parity_claim=False, actual_input_reads=0)
