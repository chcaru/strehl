"""Run M164 on the three authorized burned historical render pairs.

This command is intentionally closed over cb, 113, and 113-sharp. It stages
read-only D: inputs before TIFF decoding, verifies every byte hash, uses a
geometry-aware identity baseline, and writes a durable RUNNING/PASS/FAIL JSON
artifact. A scientific veto is a successful run result, not a process error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
import scipy
import tifffile
from scipy import ndimage
from scipy.stats import rankdata

import transfer_veto as veto


HERE = Path(__file__).resolve().parent
TRANSFER_VETO_PATH = HERE / "transfer_veto.py"
TRANSFER_VETO_SHA256 = (
    "E6C44578CA5913E4BB7FA966BBF1CD945F0AB084E2EEB8754B75435CD86E853B"
)
Q = 1.0 / 65535.0
SITE_SIDE = 512
SITE_CENTRES = (
    (1024, 1024),
    (1024, 2680),
    (1024, 4336),
    (1024, 5992),
    (2336, 1024),
    (2336, 2680),
    (2336, 4336),
    (2336, 5992),
    (3648, 1024),
    (3648, 2680),
    (3648, 4336),
    (3648, 5992),
)
ADAPTERS = (("bilinear", 1), ("cubic", 3))
MAX_RAIL_FRACTION = 0.001
MIN_ELIGIBLE_SITES = 8


@dataclass(frozen=True)
class ImageSpec:
    path: Path
    sha256: str
    byte_count: int
    shape: tuple[int, int, int]
    dtype: str
    icc_sha256: str
    encoding: str
    stage_name: str | None = None


@dataclass(frozen=True)
class PairSpec:
    key: str
    strehl: ImageSpec
    comparator: ImageSpec
    label: str


STREHL_COFFEE = ImageSpec(
    path=Path(r"C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff"),
    sha256="F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC",
    byte_count=197801290,
    shape=(4688, 7032, 3),
    dtype="uint16",
    icc_sha256="238AD2596316306A72025BB245CF3C8CD72F1090C8D95AF2F38DC090E84ECE5B",
    encoding="strehl-srgb-u16",
)
STREHL_113 = ImageSpec(
    path=Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff"),
    sha256="4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
    byte_count=197801290,
    shape=(4688, 7032, 3),
    dtype="uint16",
    icc_sha256="238AD2596316306A72025BB245CF3C8CD72F1090C8D95AF2F38DC090E84ECE5B",
    encoding="strehl-srgb-u16",
)
COFFEE_FORK = ImageSpec(
    path=Path(r"C:\dev\macro\out\coffee-bean\stack.tif"),
    sha256="8636C20D73CA0CB1F57DB89BF8553ABC166E0FBC517E5C62A07C74DEE509066E",
    byte_count=393326272,
    shape=(4672, 7008, 3),
    dtype="float32",
    icc_sha256="E7C043EEA23BA669BDFF26708A157C3C6C7A2A0E522774A6A61632FD1F489BC5",
    encoding="linear-rec2020-f32",
)
ZERENE_113 = ImageSpec(
    path=Path(r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"),
    sha256="B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0",
    byte_count=196453660,
    shape=(4672, 7008, 3),
    dtype="uint16",
    icc_sha256="DED327B844C2DBE4907E83AB9BA098397D1AE229A0BC58C039C32119A0216A26",
    encoding="linear-adobergb-u16",
    stage_name="113-pmax0.tif",
)
ZERENE_113_SHARP = ImageSpec(
    path=Path(r"D:\edited\macro\test\2026-05-07-21.31.06 ZS PMax.tif"),
    sha256="4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E",
    byte_count=196453660,
    shape=(4672, 7008, 3),
    dtype="uint16",
    icc_sha256="DED327B844C2DBE4907E83AB9BA098397D1AE229A0BC58C039C32119A0216A26",
    encoding="linear-adobergb-u16",
    stage_name="113-pmax40.tif",
)
PAIRS = (
    PairSpec("cb", STREHL_COFFEE, COFFEE_FORK, "DELIVER-V6 versus focus-stack fork"),
    PairSpec("113", STREHL_113, ZERENE_113, "DELIVER-V6 versus Zerene PMax0"),
    PairSpec(
        "113-sharp",
        STREHL_113,
        ZERENE_113_SHARP,
        "DELIVER-V6 versus Zerene PMax40",
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".next")
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def require_owned_path(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ValueError(f"{label} must be absolute: {path}")
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(HERE):
        raise ValueError(f"{label} must remain under {HERE}: {resolved}")
    if resolved.drive.upper() == "D:":
        raise ValueError(f"{label} may not be written on D:: {resolved}")
    return resolved


def inspect_tiff(path: Path, spec: ImageSpec) -> dict[str, Any]:
    with tifffile.TiffFile(path) as tiff:
        page = tiff.pages[0]
        icc_tag = page.tags.get("InterColorProfile")
        if icc_tag is None:
            raise RuntimeError(f"missing ICC profile: {path}")
        icc = bytes(icc_tag.value)
        observed = {
            "shape": tuple(page.shape),
            "dtype": str(page.dtype),
            "icc_sha256": sha256_bytes(icc),
            "photometric": int(page.photometric),
            "compression": int(page.compression),
        }
    if observed["shape"] != spec.shape:
        raise RuntimeError(
            f"unexpected TIFF shape for {path}: {observed['shape']} != {spec.shape}"
        )
    if observed["dtype"] != spec.dtype:
        raise RuntimeError(
            f"unexpected TIFF dtype for {path}: {observed['dtype']} != {spec.dtype}"
        )
    if observed["icc_sha256"] != spec.icc_sha256:
        raise RuntimeError(f"ICC hash mismatch: {path}")
    return {
        **observed,
        "shape": list(observed["shape"]),
    }


def materialize(spec: ImageSpec, stage_dir: Path) -> tuple[Path, dict[str, Any]]:
    if not spec.path.is_file():
        raise FileNotFoundError(spec.path)
    source_size = spec.path.stat().st_size
    if source_size != spec.byte_count:
        raise RuntimeError(
            f"byte count mismatch for {spec.path}: {source_size} != {spec.byte_count}"
        )

    if spec.stage_name is None:
        actual_hash = sha256_file(spec.path)
        if actual_hash != spec.sha256:
            raise RuntimeError(f"source hash mismatch: {spec.path}")
        working = spec.path
        staged = False
    else:
        stage_dir.mkdir(parents=True, exist_ok=True)
        working = stage_dir / spec.stage_name
        if working.exists() and (
            working.stat().st_size != spec.byte_count
            or sha256_file(working) != spec.sha256
        ):
            working.unlink()
        if not working.exists():
            partial = working.with_name(working.stem + ".copying" + working.suffix)
            if partial.exists():
                partial.unlink()
            shutil.copyfile(spec.path, partial)
            if partial.stat().st_size != spec.byte_count:
                raise RuntimeError(f"staged byte count mismatch: {partial}")
            if sha256_file(partial) != spec.sha256:
                raise RuntimeError(f"staged hash mismatch: {partial}")
            os.replace(partial, working)
        if sha256_file(working) != spec.sha256:
            raise RuntimeError(f"staged hash mismatch after placement: {working}")
        staged = True

    header = inspect_tiff(working, spec)
    return working, {
        "source_path": str(spec.path),
        "working_path": str(working),
        "staged_copy": staged,
        "bytes": spec.byte_count,
        "sha256": spec.sha256,
        "encoding": spec.encoding,
        "header": header,
    }


@dataclass(frozen=True)
class Geometry:
    center_y: float
    center_x: float
    a: float
    b: float
    tx: float
    ty: float
    tile_count: int
    snr_tile_count: int
    inlier_tile_count: int
    residual_rms_px: float
    residual_max_px: float
    median_snr: float

    @property
    def scale(self) -> float:
        return math.hypot(self.a, self.b)

    @property
    def rotation_deg(self) -> float:
        return math.degrees(math.atan2(self.b, self.a))

    def point_arrays(
        self, y: np.ndarray, x: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        xx = x - self.center_x
        yy = y - self.center_y
        target_x = self.a * xx - self.b * yy + self.center_x + self.tx
        target_y = self.b * xx + self.a * yy + self.center_y + self.ty
        return target_y, target_x

    def as_dict(self) -> dict[str, Any]:
        return {
            "mapping": (
                "strehl = scale*rotation(comparator - comparator_center) "
                "+ comparator_center + translation"
            ),
            "scale": self.scale,
            "rotation_deg": self.rotation_deg,
            "translation_x_px": self.tx,
            "translation_y_px": self.ty,
            "tiles_evaluated": self.tile_count,
            "tiles_passing_snr_gt_10": self.snr_tile_count,
            "similarity_inlier_tiles": self.inlier_tile_count,
            "residual_rms_px": self.residual_rms_px,
            "residual_max_px": self.residual_max_px,
            "median_snr_all_tiles": self.median_snr,
        }


def raw_green(path: Path) -> np.ndarray:
    image = tifffile.memmap(path, mode="r")
    green = np.ascontiguousarray(image[:, :, 1], dtype=np.float32)
    if np.issubdtype(image.dtype, np.integer):
        green /= np.iinfo(image.dtype).max
    del image
    return green


def box_average(image: np.ndarray, factor: int) -> np.ndarray:
    height = (image.shape[0] // factor) * factor
    width = (image.shape[1] // factor) * factor
    return image[:height, :width].reshape(
        height // factor, factor, width // factor, factor
    ).mean(axis=(1, 3))


def phase_prepare(tile: np.ndarray) -> np.ndarray | None:
    values = np.asarray(tile, np.float32)
    median = float(np.median(values))
    values = np.log1p(
        np.maximum(values - values.min(), 0.0) / (abs(median) + 1.0e-6)
    )
    values -= values.mean()
    standard_deviation = float(values.std())
    if standard_deviation < 1.0e-6:
        return None
    window = np.hanning(values.shape[0])[:, None] * np.hanning(values.shape[1])[None, :]
    return (values / standard_deviation) * window


def phase_displacement(first: np.ndarray, second: np.ndarray) -> tuple[int, int, float]:
    first_fft = np.fft.rfft2(first)
    second_fft = np.fft.rfft2(second)
    cross = first_fft * np.conj(second_fft)
    cross /= np.abs(cross) + 1.0e-12
    correlation = np.fft.irfft2(cross, s=first.shape)
    index = int(np.argmax(correlation))
    dy, dx = np.unravel_index(index, correlation.shape)
    peak = float(correlation.flat[index])
    standard_deviation = float(correlation.std())
    if dy > first.shape[0] // 2:
        dy -= first.shape[0]
    if dx > first.shape[1] // 2:
        dx -= first.shape[1]
    snr = peak / standard_deviation if standard_deviation > 0 else 0.0
    return int(dy), int(dx), float(snr)


def fit_geometry(comparator_path: Path, strehl_path: Path) -> Geometry:
    reference_green = raw_green(comparator_path)
    target_green = raw_green(strehl_path)

    reduction = 8
    reference_small = box_average(reference_green, reduction)
    target_small = box_average(target_green, reduction)
    height = min(reference_small.shape[0], target_small.shape[0])
    width = min(reference_small.shape[1], target_small.shape[1])
    prepared_target = phase_prepare(target_small[:height, :width])
    prepared_reference = phase_prepare(reference_small[:height, :width])
    if prepared_target is None or prepared_reference is None:
        raise RuntimeError("full-frame phase preparation failed")
    gross_dy, gross_dx, _ = phase_displacement(prepared_target, prepared_reference)
    gross_dy *= reduction
    gross_dx *= reduction

    tile_size = 512
    ys = np.linspace(300, reference_green.shape[0] - 300 - tile_size, 8).astype(int)
    xs = np.linspace(300, reference_green.shape[1] - 300 - tile_size, 11).astype(int)
    rows: list[tuple[float, float, float, float, float]] = []
    for y in ys:
        for x in xs:
            target_y = y + gross_dy
            target_x = x + gross_dx
            if (
                target_y < 0
                or target_x < 0
                or target_y + tile_size > target_green.shape[0]
                or target_x + tile_size > target_green.shape[1]
            ):
                continue
            reference_tile = reference_green[y : y + tile_size, x : x + tile_size]
            target_tile = target_green[
                target_y : target_y + tile_size,
                target_x : target_x + tile_size,
            ]
            prepared_reference = phase_prepare(reference_tile)
            prepared_target = phase_prepare(target_tile)
            if prepared_reference is None or prepared_target is None:
                continue
            dy, dx, snr = phase_displacement(prepared_target, prepared_reference)
            rows.append((y + tile_size / 2, x + tile_size / 2, dy, dx, snr))

    reference_shape = reference_green.shape
    del reference_green, target_green
    measured = np.asarray(rows, dtype=np.float64)
    if measured.shape[0] < 12:
        raise RuntimeError(f"only {measured.shape[0]} geometry tiles were measurable")
    kept = measured[measured[:, 4] > 10.0]
    if kept.shape[0] < 8:
        raise RuntimeError(f"only {kept.shape[0]} geometry tiles passed SNR > 10")

    center_y = reference_shape[0] / 2
    center_x = reference_shape[1] / 2
    centered_y = kept[:, 0] - center_y
    centered_x = kept[:, 1] - center_x
    residual_dy = kept[:, 2]
    residual_dx = kept[:, 3]
    design = np.zeros((2 * kept.shape[0], 4), dtype=np.float64)
    rhs = np.zeros(2 * kept.shape[0], dtype=np.float64)
    design[0::2, 0] = centered_x
    design[0::2, 1] = -centered_y
    design[0::2, 2] = 1.0
    design[1::2, 0] = centered_y
    design[1::2, 1] = centered_x
    design[1::2, 3] = 1.0
    rhs[0::2] = residual_dx
    rhs[1::2] = residual_dy

    def fit(indices: np.ndarray) -> np.ndarray:
        equations = np.ravel(np.column_stack((2 * indices, 2 * indices + 1)))
        solution, *_ = np.linalg.lstsq(design[equations], rhs[equations], rcond=None)
        return solution

    def radial_residual(solution: np.ndarray) -> np.ndarray:
        component = (design @ solution - rhs).reshape(-1, 2)
        return np.sqrt(np.sum(component * component, axis=1))

    best_inliers: np.ndarray | None = None
    best_score: tuple[int, float] | None = None
    threshold = 12.0
    for first in range(kept.shape[0] - 1):
        for second in range(first + 1, kept.shape[0]):
            candidate = fit(np.asarray([first, second]))
            residual_radius = radial_residual(candidate)
            inliers = np.flatnonzero(residual_radius <= threshold)
            if inliers.size < 4:
                continue
            score = (int(inliers.size), -float(np.median(residual_radius[inliers])))
            if best_score is None or score > best_score:
                best_score = score
                best_inliers = inliers
    if best_inliers is None or best_inliers.size < 6:
        raise RuntimeError("robust similarity found fewer than six inliers")
    for _ in range(4):
        solution = fit(best_inliers)
        revised = np.flatnonzero(radial_residual(solution) <= threshold)
        if np.array_equal(revised, best_inliers):
            break
        best_inliers = revised
    solution = fit(best_inliers)
    delta_a, b, local_tx, local_ty = solution
    component_residual = (design @ solution - rhs).reshape(-1, 2)
    inlier_residual = component_residual[best_inliers]
    return Geometry(
        center_y=center_y,
        center_x=center_x,
        a=1.0 + float(delta_a),
        b=float(b),
        tx=float(local_tx + gross_dx),
        ty=float(local_ty + gross_dy),
        tile_count=int(measured.shape[0]),
        snr_tile_count=int(kept.shape[0]),
        inlier_tile_count=int(best_inliers.size),
        residual_rms_px=float(np.sqrt(np.mean(inlier_residual**2))),
        residual_max_px=float(np.max(np.abs(inlier_residual))),
        median_snr=float(np.median(measured[:, 4])),
    )


def parse_strehl_tone(path: Path) -> dict[str, float]:
    with tifffile.TiffFile(path) as tiff:
        description_tag = tiff.pages[0].tags.get("ImageDescription")
        if description_tag is None:
            raise RuntimeError(f"tone metadata missing: {path}")
        description = str(description_tag.value)
    match = re.search(
        r"Tone rendering: black ([0-9]+(?:\.[0-9]+)?), "
        r"white ([0-9]+(?:\.[0-9]+)?).*?"
        r"display-space contrast ([0-9]+(?:\.[0-9]+)?)",
        description,
    )
    if match is None:
        raise RuntimeError(f"tone metadata could not be parsed: {path}")
    return {
        "black": float(match.group(1)),
        "white": float(match.group(2)),
        "contrast": float(match.group(3)),
        "toe": 0.004,
    }


def inverse_s_curve(values: np.ndarray, strength: float) -> np.ndarray:
    output = np.asarray(values, dtype=np.float64)
    estimate = output.copy()
    for _ in range(8):
        smooth = estimate * estimate * (3.0 - 2.0 * estimate)
        function = estimate + strength * (smooth - estimate) - output
        derivative = 1.0 + strength * (
            6.0 * estimate - 6.0 * estimate**2 - 1.0
        )
        estimate -= function / np.maximum(derivative, 1.0e-6)
        estimate = np.clip(estimate, 0.0, 1.0)
    return estimate


def srgb_inverse(values: np.ndarray) -> np.ndarray:
    return np.where(
        values <= 0.04045,
        values / 12.92,
        ((values + 0.055) / 1.055) ** 2.4,
    )


def tone_gain(luminance: np.ndarray, tone: dict[str, float]) -> np.ndarray:
    luminance = np.maximum(luminance, 0.0)
    scale = 1.0 / (tone["white"] - tone["black"])
    y = (luminance - tone["black"]) * scale
    soft = 0.5 * (y + np.sqrt(y * y + tone["toe"] ** 2))
    gain = np.full_like(luminance, scale)
    positive = luminance > 1.0e-12
    gain[positive] = np.minimum(soft[positive] / luminance[positive], scale)
    gain[~positive] = 0.0
    return gain


def inverse_strehl_render(rgb: np.ndarray, tone: dict[str, float]) -> np.ndarray:
    display = inverse_s_curve(rgb, tone["contrast"])
    placed = srgb_inverse(display)
    placed_luminance = (
        0.2126 * placed[..., 0]
        + 0.7152 * placed[..., 1]
        + 0.0722 * placed[..., 2]
    )
    scale = 1.0 / (tone["white"] - tone["black"])
    upper = np.maximum(
        placed_luminance / max(scale, 1.0e-12), tone["white"] * 2.0
    )
    lower = np.zeros_like(placed_luminance)
    for _ in range(32):
        middle = 0.5 * (lower + upper)
        developed = middle * tone_gain(middle, tone)
        choose_upper = developed >= placed_luminance
        upper = np.where(choose_upper, middle, upper)
        lower = np.where(choose_upper, lower, middle)
    source_luminance = 0.5 * (lower + upper)
    gain = tone_gain(source_luminance, tone)
    return placed / np.maximum(gain[..., None], 1.0e-12)


def rail_fraction(raw: np.ndarray) -> float:
    if np.issubdtype(raw.dtype, np.integer):
        info = np.iinfo(raw.dtype)
        return float(np.mean((raw == info.min) | (raw == info.max)))
    return float(np.mean((raw <= 0.0) | (raw >= 1.0)))


def decode_luminance(
    raw: np.ndarray, encoding: str, tone: dict[str, float] | None
) -> np.ndarray:
    if encoding == "strehl-srgb-u16":
        if tone is None:
            raise RuntimeError("strehl tone metadata was not supplied")
        rgb = raw.astype(np.float64) / 65535.0
        linear = inverse_strehl_render(rgb, tone)
        return (
            0.2126 * linear[..., 0]
            + 0.7152 * linear[..., 1]
            + 0.0722 * linear[..., 2]
        )
    if encoding == "linear-adobergb-u16":
        linear = raw.astype(np.float64) / 65535.0
        return (
            0.297344975 * linear[..., 0]
            + 0.627363566 * linear[..., 1]
            + 0.075291458 * linear[..., 2]
        )
    if encoding == "linear-rec2020-f32":
        linear = raw.astype(np.float64)
        return (
            0.2627 * linear[..., 0]
            + 0.6780 * linear[..., 1]
            + 0.0593 * linear[..., 2]
        )
    raise ValueError(f"unsupported encoding: {encoding}")


def read_crop(path: Path, centre: tuple[int, int], side: int) -> np.ndarray:
    cy, cx = centre
    y0 = int(cy - side // 2)
    x0 = int(cx - side // 2)
    image = tifffile.memmap(path, mode="r")
    if y0 < 0 or x0 < 0 or y0 + side > image.shape[0] or x0 + side > image.shape[1]:
        del image
        raise RuntimeError(f"crop out of bounds at {centre}: {path}")
    crop = np.asarray(image[y0 : y0 + side, x0 : x0 + side, :]).copy()
    del image
    return crop


def map_strehl_to_comparator(
    strehl_path: Path,
    strehl_encoding: str,
    tone: dict[str, float],
    geometry: Geometry,
    centre: tuple[int, int],
    side: int,
    order: int,
    correction: tuple[int, int] = (0, 0),
) -> tuple[np.ndarray, float]:
    cy, cx = centre
    y0 = cy - side // 2
    x0 = cx - side // 2
    correction_y, correction_x = correction
    output_y, output_x = np.meshgrid(
        np.arange(y0, y0 + side, dtype=np.float64) - correction_y,
        np.arange(x0, x0 + side, dtype=np.float64) - correction_x,
        indexing="ij",
    )
    source_y, source_x = geometry.point_arrays(output_y, output_x)
    padding = 4 if order > 1 else 2
    sy0 = int(math.floor(float(np.min(source_y)))) - padding
    sx0 = int(math.floor(float(np.min(source_x)))) - padding
    sy1 = int(math.ceil(float(np.max(source_y)))) + padding + 1
    sx1 = int(math.ceil(float(np.max(source_x)))) + padding + 1

    image = tifffile.memmap(strehl_path, mode="r")
    if sy0 < 0 or sx0 < 0 or sy1 > image.shape[0] or sx1 > image.shape[1]:
        del image
        raise RuntimeError(f"mapped crop out of bounds at {centre}: {strehl_path}")
    raw = np.asarray(image[sy0:sy1, sx0:sx1, :]).copy()
    del image
    rails = rail_fraction(raw)
    luminance = decode_luminance(raw, strehl_encoding, tone)
    coordinates = np.asarray((source_y - sy0, source_x - sx0))
    mapped = ndimage.map_coordinates(
        luminance,
        coordinates,
        order=order,
        mode="reflect",
        prefilter=order > 1,
    )
    return np.asarray(mapped, dtype=np.float64), rails


def registration_field(values: np.ndarray) -> np.ndarray:
    prepared = phase_prepare(values)
    if prepared is None:
        raise RuntimeError("registration field is degenerate")
    return prepared


def phase_correction(
    reference: np.ndarray, moving: np.ndarray, max_shift: int
) -> tuple[int, int, float]:
    if reference.shape != moving.shape:
        raise ValueError("phase correction requires equal shapes")
    a = registration_field(reference)
    b = registration_field(moving)
    fa = np.fft.fft2(a)
    fb = np.fft.fft2(b)
    cross = fa * np.conj(fb)
    cross /= np.abs(cross) + np.finfo(np.float64).eps
    correlation = np.fft.ifft2(cross).real
    allowed_y = np.minimum(
        np.arange(reference.shape[0]),
        reference.shape[0] - np.arange(reference.shape[0]),
    )
    allowed_x = np.minimum(
        np.arange(reference.shape[1]),
        reference.shape[1] - np.arange(reference.shape[1]),
    )
    allowed = (allowed_y[:, None] <= max_shift) & (
        allowed_x[None, :] <= max_shift
    )
    correlation = np.where(allowed, correlation, -np.inf)
    iy, ix = np.unravel_index(np.argmax(correlation), correlation.shape)
    dy = int(iy - reference.shape[0] if iy > reference.shape[0] // 2 else iy)
    dx = int(ix - reference.shape[1] if ix > reference.shape[1] // 2 else ix)
    return dy, dx, float(correlation[iy, ix])


def midrank_field(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    count = array.size
    ranks = rankdata(array.ravel(), method="average").reshape(array.shape)
    return (ranks - (count + 1.0) / 2.0) / count


def pearson(first: np.ndarray, second: np.ndarray) -> float:
    a = np.asarray(first, dtype=np.float64).ravel()
    b = np.asarray(second, dtype=np.float64).ravel()
    a -= np.mean(a)
    b -= np.mean(b)
    denominator = math.sqrt(float(np.dot(a, a) * np.dot(b, b)))
    return float(np.dot(a, b) / denominator) if denominator > 0 else float("nan")


def rank_correlation(first: np.ndarray, second: np.ndarray) -> float:
    a = midrank_field(first[::4, ::4])
    b = midrank_field(second[::4, ::4])
    return pearson(a, b)


def null_correlation_gate(
    first: np.ndarray, second: np.ndarray, seed: int
) -> tuple[float, list[float]]:
    a = midrank_field(first[::4, ::4])
    b = midrank_field(second[::4, ::4])
    rng = np.random.default_rng(seed)
    values: list[float] = []
    while len(values) < 64:
        dy = int(rng.integers(16, a.shape[0] - 16))
        dx = int(rng.integers(16, a.shape[1] - 16))
        if rng.integers(2):
            dy = -dy
        if rng.integers(2):
            dx = -dx
        values.append(pearson(a, np.roll(b, (dy, dx), axis=(0, 1))))
    return float(np.quantile(values, 0.999)), values


def normalize_pair(
    baseline: np.ndarray, *others: np.ndarray
) -> tuple[list[np.ndarray], dict[str, float]]:
    minimum = float(np.min(baseline))
    maximum = float(np.max(baseline))
    if not maximum > minimum:
        raise RuntimeError("mapped strehl baseline is constant")
    scale = 0.8 / (maximum - minimum)
    offset = 0.1 - scale * minimum

    def quantize(values: np.ndarray) -> np.ndarray:
        transformed = np.asarray(values, dtype=np.float64) * scale + offset
        if not np.all(np.isfinite(transformed)):
            raise RuntimeError("normalization produced non-finite values")
        return np.rint(transformed / Q) * Q

    return [quantize(baseline), *(quantize(value) for value in others)], {
        "source_minimum": minimum,
        "source_maximum": maximum,
        "scale": scale,
        "offset": offset,
        "quantization_step": Q,
    }


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "status": result["status"],
        "fired": bool(result["fired"]),
        "difference_rms_lsb": result.get("difference_rms_lsb"),
    }
    if "families" not in result:
        if "reason" in result:
            record["reason"] = result["reason"]
        return record
    record["selected_family"] = result["selected_family"]
    record["firing_families"] = result["firing_families"]
    record["families"] = {
        family["family"]: {
            key: family[key]
            for key in (
                "fired",
                "difference_rms_lsb",
                "kernel_effect_rms_lsb",
                "residual_rms_lsb",
                "residual_over_difference",
                "informative_tiles",
                "tile_q90",
                "fold_disagreement",
            )
        }
        for family in result["families"]
    }
    return record


def require_valid(result: dict[str, Any], context: str) -> None:
    if result["status"] == "INSTRUMENT_INVALID":
        raise RuntimeError(f"{context}: {result.get('reason', 'instrument invalid')}")


def selected_metric(record: dict[str, Any], key: str) -> float | None:
    family_name = record.get("selected_family")
    if family_name is None:
        return None
    value = record["families"][family_name].get(key)
    return None if value is None else float(value)


def metric_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"trials": len(records), "fires": 0}
    summary["fires"] = sum(bool(record["fired"]) for record in records)
    metrics: dict[str, Any] = {}
    for key in (
        "difference_rms_lsb",
        "kernel_effect_rms_lsb",
        "residual_rms_lsb",
        "residual_over_difference",
        "tile_q90",
        "fold_disagreement",
    ):
        values: list[float] = []
        for record in records:
            value = (
                record.get(key)
                if key == "difference_rms_lsb"
                else selected_metric(record, key)
            )
            if value is not None and np.isfinite(value):
                values.append(float(value))
        if values:
            metrics[key] = {
                "minimum": float(np.min(values)),
                "median": float(np.median(values)),
                "maximum": float(np.max(values)),
            }
    summary["selected_metrics"] = metrics
    return summary


def local_disk(image: np.ndarray, amplitude_lsb: float = 32.0) -> np.ndarray:
    yy, xx = np.meshgrid(
        np.arange(image.shape[0]), np.arange(image.shape[1]), indexing="ij"
    )
    radius = np.sqrt(
        (yy - (image.shape[0] * 0.37)) ** 2
        + (xx - (image.shape[1] * 0.61)) ** 2
    )
    support = 54.0
    envelope = np.where(
        radius < support,
        0.5 * (1.0 + np.cos(np.pi * radius / support)),
        0.0,
    )
    return np.rint((image + amplitude_lsb * Q * envelope) / Q) * Q


def shift_roundtrip(image: np.ndarray, displacement: float = 0.05) -> np.ndarray:
    shifted = ndimage.shift(
        image,
        (displacement, displacement),
        order=1,
        mode="reflect",
        prefilter=False,
    )
    restored = ndimage.shift(
        shifted,
        (-displacement, -displacement),
        order=1,
        mode="reflect",
        prefilter=False,
    )
    return np.rint(restored / Q) * Q


def adapter_controls(
    baseline: np.ndarray, alternate: np.ndarray
) -> dict[str, Any]:
    prepared = veto.prepare_transfer_veto(baseline, Q)
    identity = compact_result(prepared.evaluate(baseline))
    disturbance = compact_result(prepared.evaluate(local_disk(baseline)))
    blurred = np.rint(
        ndimage.gaussian_filter(baseline, sigma=0.4, mode="reflect") / Q
    ) * Q
    blur = compact_result(prepared.evaluate(blurred))
    lowpass = ndimage.gaussian_filter(baseline, sigma=1.0, mode="reflect")
    sharpened = np.rint((baseline + 0.02 * (baseline - lowpass)) / Q) * Q
    sharpening = compact_result(prepared.evaluate(sharpened))
    resampling = compact_result(prepared.evaluate(shift_roundtrip(baseline)))
    adapter_forward = compact_result(prepared.evaluate(alternate))
    adapter_reverse_raw = veto.evaluate_transfer_veto(alternate, baseline, Q)
    adapter_reverse = compact_result(adapter_reverse_raw)
    for name, result in (
        ("identity", identity),
        ("disturbance", disturbance),
        ("blur", blur),
        ("sharpening", sharpening),
        ("resampling", resampling),
        ("adapter-forward", adapter_forward),
        ("adapter-reverse", adapter_reverse),
    ):
        require_valid(result, f"control {name}")
    passed = (
        identity["status"] == "IDENTITY_EQUIVALENT"
        and not identity["fired"]
        and disturbance["status"] == "NOT_VETOED"
        and not disturbance["fired"]
        and float(disturbance["difference_rms_lsb"]) >= 0.5
        and blur["fired"]
        and sharpening["fired"]
        and resampling["fired"]
    )
    if not passed:
        raise RuntimeError("adapter control battery did not pass")
    return {
        "passed": True,
        "identity": identity,
        "movable_local_disturbance": disturbance,
        "gaussian_blur_sigma_0_4": blur,
        "unsharp_radius_1_amount_0_02": sharpening,
        "bilinear_shift_roundtrip_0_05": resampling,
        "adapter_choice_bilinear_to_cubic": adapter_forward,
        "adapter_choice_cubic_to_bilinear": adapter_reverse,
    }


def evaluate_pair(
    pair: PairSpec,
    strehl_path: Path,
    comparator_path: Path,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    geometry = fit_geometry(comparator_path, strehl_path)
    tone = parse_strehl_tone(strehl_path)
    comparator_image = tifffile.memmap(comparator_path, mode="r")
    comparator_shape = comparator_image.shape
    del comparator_image
    if comparator_shape[:2] != pair.comparator.shape[:2]:
        raise RuntimeError(f"{pair.key}: comparator shape changed after validation")

    sites: list[dict[str, Any]] = []
    controls: dict[str, Any] | None = None
    for site_index, centre in enumerate(SITE_CENTRES):
        site: dict[str, Any] = {
            "site": site_index,
            "centre_comparator_yx": list(centre),
            "eligible": False,
        }
        try:
            comparator_raw = read_crop(comparator_path, centre, SITE_SIDE)
            comparator_rails = rail_fraction(comparator_raw)
            comparator = decode_luminance(
                comparator_raw, pair.comparator.encoding, None
            )
            preliminary, strehl_rails = map_strehl_to_comparator(
                strehl_path,
                pair.strehl.encoding,
                tone,
                geometry,
                centre,
                SITE_SIDE,
                order=1,
            )
            correction = phase_correction(comparator, preliminary, max_shift=32)
            if max(abs(correction[0]), abs(correction[1])) >= 32:
                site["reason"] = "LOCAL_CORRECTION_AT_SEARCH_BOUNDARY"
                site["registration"] = {
                    "local_correction_yx": [correction[0], correction[1]],
                    "phase_peak": correction[2],
                }
                sites.append(site)
                continue
            corrected: dict[str, np.ndarray] = {}
            adapter_rails: dict[str, float] = {}
            for adapter_name, order in ADAPTERS:
                mapped, mapped_rails = map_strehl_to_comparator(
                    strehl_path,
                    pair.strehl.encoding,
                    tone,
                    geometry,
                    centre,
                    SITE_SIDE,
                    order=order,
                    correction=(correction[0], correction[1]),
                )
                corrected[adapter_name] = mapped
                adapter_rails[adapter_name] = mapped_rails

            correlation_before = rank_correlation(comparator, preliminary)
            correlation_after = rank_correlation(
                comparator, corrected["bilinear"]
            )
            null_gate, nulls = null_correlation_gate(
                comparator,
                corrected["bilinear"],
                seed=164000 + site_index,
            )
            site["registration"] = {
                "local_correction_yx": [correction[0], correction[1]],
                "phase_peak": correction[2],
                "rank_correlation_before": correlation_before,
                "rank_correlation_after": correlation_after,
                "rank_null_q999": null_gate,
                "rank_null_minimum": float(np.min(nulls)),
                "rank_null_median": float(np.median(nulls)),
                "rank_null_maximum": float(np.max(nulls)),
            }
            site["rail_fraction"] = {
                "comparator": comparator_rails,
                **{f"strehl_{name}": value for name, value in adapter_rails.items()},
            }
            if comparator_rails > MAX_RAIL_FRACTION:
                site["reason"] = "COMPARATOR_RAIL_FRACTION"
                sites.append(site)
                continue
            if max(adapter_rails.values()) > MAX_RAIL_FRACTION:
                site["reason"] = "STREHL_RAIL_FRACTION"
                sites.append(site)
                continue
            if not np.isfinite(correlation_after) or correlation_after <= null_gate:
                site["reason"] = "REGISTRATION_NULL"
                sites.append(site)
                continue
            if correlation_after + 1.0e-12 < correlation_before:
                site["reason"] = "REGISTRATION_DID_NOT_IMPROVE"
                sites.append(site)
                continue

            normalized, normalization = normalize_pair(
                corrected["bilinear"],
                corrected["cubic"],
                comparator,
            )
            normalized_strehl = {
                "bilinear": normalized[0],
                "cubic": normalized[1],
            }
            normalized_comparator = normalized[2]
            prepared_comparator = veto.prepare_transfer_veto(
                normalized_comparator, Q
            )
            adapter_results: dict[str, Any] = {}
            for adapter_name, _ in ADAPTERS:
                strehl_values = normalized_strehl[adapter_name]
                forward_raw = veto.evaluate_transfer_veto(
                    strehl_values, normalized_comparator, Q
                )
                reverse_raw = prepared_comparator.evaluate(strehl_values)
                require_valid(
                    forward_raw, f"{pair.key} site {site_index} {adapter_name} forward"
                )
                require_valid(
                    reverse_raw, f"{pair.key} site {site_index} {adapter_name} reverse"
                )
                adapter_results[adapter_name] = {
                    "comparator_from_strehl": compact_result(forward_raw),
                    "strehl_from_comparator": compact_result(reverse_raw),
                }

            robust_forward = all(
                adapter_results[name]["comparator_from_strehl"]["fired"]
                for name, _ in ADAPTERS
            )
            robust_reverse = all(
                adapter_results[name]["strehl_from_comparator"]["fired"]
                for name, _ in ADAPTERS
            )
            site.update(
                {
                    "eligible": True,
                    "reason": None,
                    "normalization": normalization,
                    "adapters": adapter_results,
                    "robust_fire_comparator_from_strehl": robust_forward,
                    "robust_fire_strehl_from_comparator": robust_reverse,
                }
            )
            if controls is None:
                controls = adapter_controls(
                    normalized_strehl["bilinear"],
                    normalized_strehl["cubic"],
                )
                controls["site"] = site_index
            sites.append(site)
        except Exception as error:
            raise RuntimeError(
                f"{pair.key} site {site_index} failed: "
                f"{type(error).__name__}: {error}"
            ) from error

    eligible = [site for site in sites if site["eligible"]]
    if len(eligible) < MIN_ELIGIBLE_SITES:
        reasons = [site.get("reason") for site in sites if not site["eligible"]]
        raise RuntimeError(
            f"{pair.key}: only {len(eligible)}/{len(sites)} sites eligible; "
            f"reasons={reasons}"
        )
    if controls is None or not controls["passed"]:
        raise RuntimeError(f"{pair.key}: no passing adapter control site")

    forward_count = sum(
        bool(site["robust_fire_comparator_from_strehl"]) for site in eligible
    )
    reverse_count = sum(
        bool(site["robust_fire_strehl_from_comparator"]) for site in eligible
    )
    if forward_count == len(eligible) or reverse_count == len(eligible):
        verdict = "INADMISSIBLE_COMMON_TRANSFER"
        fired = True
    elif forward_count == 0 and reverse_count == 0:
        verdict = "NOT_VETOED"
        fired = False
    else:
        verdict = "MIXED_SITE_EVIDENCE"
        fired = False

    residuals: dict[str, Any] = {}
    for adapter_name, _ in ADAPTERS:
        for direction in ("comparator_from_strehl", "strehl_from_comparator"):
            records = [
                site["adapters"][adapter_name][direction] for site in eligible
            ]
            residuals[f"{adapter_name}.{direction}"] = metric_summary(records)

    return {
        "pair": pair.key,
        "label": pair.label,
        "holdout_status": "BURNED-OK",
        "fired": fired,
        "verdict": verdict,
        "pair_rule": (
            "fire only when every eligible fixed site (minimum 8) fires in "
            "one direction under both bilinear and cubic geometry adapters"
        ),
        "fixed_sites": len(SITE_CENTRES),
        "eligible_sites": len(eligible),
        "excluded_sites": len(sites) - len(eligible),
        "robust_fire_sites_comparator_from_strehl": forward_count,
        "robust_fire_sites_strehl_from_comparator": reverse_count,
        "geometry": geometry.as_dict(),
        "tone_inversion": tone,
        "adapter_controls": controls,
        "residual_statistics": residuals,
        "provenance": provenance,
        "sites": sites,
    }


def run_real(output: Path, stage_dir: Path) -> dict[str, Any]:
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        if os.environ.get(variable) != "1":
            raise RuntimeError(f"{variable} must equal 1")
    if sha256_file(TRANSFER_VETO_PATH) != TRANSFER_VETO_SHA256:
        raise RuntimeError("transfer_veto.py hash mismatch")
    if tuple(pair.key for pair in PAIRS) != ("cb", "113", "113-sharp"):
        raise RuntimeError("authorized pair set changed")
    if any("119" in pair.key for pair in PAIRS):
        raise RuntimeError("forbidden 119 pair entered the run set")

    materialized: dict[ImageSpec, tuple[Path, dict[str, Any]]] = {}
    for pair in PAIRS:
        for spec in (pair.strehl, pair.comparator):
            if spec not in materialized:
                materialized[spec] = materialize(spec, stage_dir)

    pair_results = []
    for pair in PAIRS:
        strehl_path, strehl_provenance = materialized[pair.strehl]
        comparator_path, comparator_provenance = materialized[pair.comparator]
        pair_results.append(
            evaluate_pair(
                pair,
                strehl_path,
                comparator_path,
                {
                    "strehl": strehl_provenance,
                    "comparator": comparator_provenance,
                },
            )
        )

    verdicts = [result["verdict"] for result in pair_results]
    if "INADMISSIBLE_COMMON_TRANSFER" in verdicts:
        historical = "NO"
    elif all(verdict == "NOT_VETOED" for verdict in verdicts):
        historical = "YES_WITHIN_M164_SCOPE"
    else:
        historical = "PARTIAL"
    return {
        "status": "PASS",
        "completed_at": utc_now(),
        "scientific_result": {
            "historical_comparisons_admissible": historical,
            "interpretation": (
                "This is an admissibility result only. It does not rank either "
                "renderer and a NOT_VETOED result excludes only M164's frozen families."
            ),
        },
        "pairs": pair_results,
    }


def self_test() -> None:
    if tuple(pair.key for pair in PAIRS) != ("cb", "113", "113-sharp"):
        raise AssertionError("pair whitelist changed")
    if any("119" in pair.key.lower() for pair in PAIRS):
        raise AssertionError("119 entered the pair whitelist")
    if sha256_file(TRANSFER_VETO_PATH) != TRANSFER_VETO_SHA256:
        raise AssertionError("transfer-veto source hash changed")

    rng = np.random.default_rng(164)
    source = rng.normal(size=(512, 512))
    source = ndimage.gaussian_filter(source, 0.7, mode="reflect")
    source -= source.min()
    source /= source.max()
    source = np.rint((0.1 + 0.8 * source) / Q) * Q
    controls = adapter_controls(source, source.copy())
    if not controls["passed"]:
        raise AssertionError("synthetic adapter controls failed")

    planted = np.roll(source, (7, -5), axis=(0, 1))
    correction = phase_correction(source, planted, max_shift=16)
    if correction[:2] != (-7, 5):
        raise AssertionError(f"phase correction sign failed: {correction[:2]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--stage-dir", type=Path)
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.self_test:
        try:
            self_test()
            print("M164 real-pair runner self-test: PASS")
            return 0
        except BaseException as error:
            print(
                f"M164 real-pair runner self-test: FAIL: "
                f"{type(error).__name__}: {error}",
                file=sys.stderr,
            )
            return 2
    if arguments.output is None or arguments.stage_dir is None:
        parser.error("--output and --stage-dir are required unless --self-test is used")

    output = require_owned_path(arguments.output, "output")
    stage_dir = require_owned_path(arguments.stage_dir, "stage directory")
    running = {
        "status": "RUNNING",
        "started_at": utc_now(),
        "command": [sys.executable, *sys.argv],
        "authorized_pairs": ["cb", "113", "113-sharp"],
        "forbidden_pairs": ["all 119MSDCF pairs"],
        "thread_environment": {
            variable: os.environ.get(variable)
            for variable in (
                "OPENBLAS_NUM_THREADS",
                "OMP_NUM_THREADS",
                "MKL_NUM_THREADS",
            )
        },
        "runtime": {
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "tifffile": tifffile.__version__,
        },
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "transfer_veto_sha256": sha256_file(TRANSFER_VETO_PATH),
    }
    atomic_json(output, running)
    try:
        result = {**running, **run_real(output, stage_dir)}
        atomic_json(output, result)
        print(f"M164 real-pair run: PASS; verdict written to {output}")
        for pair in result["pairs"]:
            print(
                f"{pair['pair']}: {pair['verdict']} "
                f"forward={pair['robust_fire_sites_comparator_from_strehl']}/"
                f"{pair['eligible_sites']} reverse="
                f"{pair['robust_fire_sites_strehl_from_comparator']}/"
                f"{pair['eligible_sites']}"
            )
        return 0
    except BaseException as error:
        failure = {
            **running,
            "status": "FAIL",
            "completed_at": utc_now(),
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }
        try:
            atomic_json(output, failure)
        finally:
            print(
                f"M164 real-pair run: FAIL: {type(error).__name__}: {error}; "
                f"verdict written to {output}",
                file=sys.stderr,
            )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
