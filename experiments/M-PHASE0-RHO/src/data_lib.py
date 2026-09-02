"""Read-only RAW and calibration helpers for M-PHASE0-RHO."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Iterable

import numpy as np
import rawpy

import rho_lib as R


MACRO_ROOT = Path(r"D:\personal\macro")
REQUEST_ROOT = MACRO_ROOT / "requests"
FLAT_ROOT = MACRO_ROOT / "flat-fields" / "flat-fields"

ACTIVE_SHAPE = (4688, 7028)
RAW_PATTERN = ((0, 1), (3, 2))
BLACK_LEVEL = 512.0
WHITE_LEVEL = 16383.0
CAMERA_MODEL = "ILCE-7CM2"

GQ_SIZE = 1024
ROI_CENTRES = (
    (1200, 1200),
    (1200, 3514),
    (1200, 5828),
    (3488, 1200),
    (3488, 3514),
    (3488, 5828),
)

EXIF_TAGS = (
    "-Make",
    "-Model",
    "-ISO",
    "-ExposureTime",
    "-FNumber",
    "-FocalLength",
    "-DateTimeOriginal",
    "-ImageWidth",
    "-ImageHeight",
    "-FileSize",
    "-FileName",
    "-Directory",
    "-SonyRawFileType",
)


def exif_records(roots: Iterable[str | Path]) -> list[dict]:
    """Read EXIF metadata without modifying or demosaicing the source files."""
    tool = shutil.which("exiftool")
    if not tool:
        fallback = Path(
            r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe"
        )
        if not fallback.exists():
            raise RuntimeError("exiftool is required for the metadata inventory")
        tool = str(fallback)
    args = [
        tool,
        "-json",
        "-n",
        "-ext",
        "ARW",
        "-r",
        *EXIF_TAGS,
        *(str(Path(p)) for p in roots),
    ]
    proc = subprocess.run(
        args,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"exiftool failed with {proc.returncode}: {proc.stderr.strip()}"
        )
    records = json.loads(proc.stdout)
    return sorted(records, key=lambda x: x["SourceFile"].lower())


def load_active(path: str | Path) -> tuple[np.ndarray, dict]:
    """Copy the visible undemosaiced mosaic and validate its sensor contract."""
    with rawpy.imread(str(path)) as raw:
        active = np.array(raw.raw_image_visible, copy=True)
        pattern = (
            None if raw.raw_pattern is None else tuple(map(tuple, raw.raw_pattern))
        )
        meta = {
            "shape": list(active.shape),
            "dtype": str(active.dtype),
            "raw_pattern": None
            if pattern is None
            else [[int(x) for x in row] for row in pattern],
            "color_desc": bytes(raw.color_desc)
            .decode("ascii", "replace")
            .rstrip("\x00"),
            "black_levels": [float(x) for x in raw.black_level_per_channel],
            "white_level": float(raw.white_level),
        }
    if active.shape != ACTIVE_SHAPE:
        raise ValueError(f"unexpected active shape {active.shape} for {path}")
    if pattern != RAW_PATTERN:
        raise ValueError(f"unexpected CFA pattern {pattern} for {path}")
    if any(abs(x - BLACK_LEVEL) > 1e-9 for x in meta["black_levels"]):
        raise ValueError(f"unexpected black levels for {path}: {meta['black_levels']}")
    return active, meta


def load_gq_patches(
    path: str | Path,
    centres: Iterable[tuple[int, int]] = ROI_CENTRES,
    size: int = GQ_SIZE,
) -> tuple[list[np.ndarray], dict]:
    active, meta = load_active(path)
    patches = [
        R.extract_gq(active, int(rc), int(cc), int(size)).astype(np.float32)
        - BLACK_LEVEL
        for rc, cc in centres
    ]
    return patches, meta


def group_records(
    records: Iterable[dict], **fields: float | int | str
) -> list[dict]:
    out = []
    for row in records:
        if all(row.get(key) == value for key, value in fields.items()):
            out.append(row)
    return sorted(
        out,
        key=lambda x: (x.get("DateTimeOriginal", ""), x.get("FileName", "")),
    )


def lowpass_gq(patch: np.ndarray, cutoff: float = 0.02) -> np.ndarray:
    """Smooth illumination below a sensor-frequency cutoff."""
    a = np.asarray(patch, dtype=float)
    fx, fy = R.gq_frequency_grid(a.shape[0])
    radius = np.hypot(fx, fy)
    transfer = 1.0 / (1.0 + np.power(radius / float(cutoff), 8.0))
    return np.fft.ifft2(np.fft.fft2(a) * transfer).real


def response_map(patch: np.ndarray, cutoff: float = 0.02) -> np.ndarray:
    smooth = lowpass_gq(patch, cutoff=cutoff)
    if float(np.percentile(smooth, 1)) <= 0.0:
        raise ValueError("flat-field illumination is not positive")
    gain = np.asarray(patch, dtype=float) / smooth
    gain /= float(np.median(gain))
    return gain.astype(np.float32)


def build_calibration_maps(
    flat_records: list[dict],
    dark_records: list[dict],
    flat_exposure: float = 0.05,
    dark_exposure: float = 1.0,
    centres: Iterable[tuple[int, int]] = ROI_CENTRES,
    size: int = GQ_SIZE,
) -> tuple[dict, dict]:
    """Build split flat-response maps and a matched master-dark map."""
    centres = tuple(centres)
    flats = group_records(
        flat_records, ISO=100, ExposureTime=float(flat_exposure)
    )
    darks = group_records(
        dark_records, ISO=100, ExposureTime=float(dark_exposure)
    )
    if len(flats) != 40:
        raise ValueError(f"expected 40 flat frames, found {len(flats)}")
    if len(darks) != 22:
        raise ValueError(f"expected 22 dark frames, found {len(darks)}")

    flat_a = [np.zeros((size, size), dtype=np.float64) for _ in centres]
    flat_b = [np.zeros((size, size), dtype=np.float64) for _ in centres]
    for i, row in enumerate(flats):
        patches, _ = load_gq_patches(row["SourceFile"], centres, size)
        target = flat_a if i < len(flats) // 2 else flat_b
        for acc, patch in zip(target, patches):
            acc += patch
    flat_a = [x / (len(flats) // 2) for x in flat_a]
    flat_b = [x / (len(flats) // 2) for x in flat_b]

    dark_a = [np.zeros((size, size), dtype=np.float64) for _ in centres]
    dark_b = [np.zeros((size, size), dtype=np.float64) for _ in centres]
    split = len(darks) // 2
    for i, row in enumerate(darks):
        patches, _ = load_gq_patches(row["SourceFile"], centres, size)
        target = dark_a if i < split else dark_b
        for acc, patch in zip(target, patches):
            acc += patch
    dark_a = [x / split for x in dark_a]
    dark_b = [x / (len(darks) - split) for x in dark_b]
    dark = [(a + b) / 2.0 for a, b in zip(dark_a, dark_b)]

    gain_a = [response_map(f - d) for f, d in zip(flat_a, dark)]
    gain_b = [response_map(f - d) for f, d in zip(flat_b, dark)]
    rows = []
    for i, (ga, gb, da, db) in enumerate(
        zip(gain_a, gain_b, dark_a, dark_b)
    ):
        xa = (ga - 1.0).ravel()
        xb = (gb - 1.0).ravel()
        corr = float(np.corrcoef(xa, xb)[0, 1])
        rows.append(
            {
                "roi": i,
                "centre": list(centres[i]),
                "gain_split_correlation": corr,
                "gain_a_rms": float(np.std(xa)),
                "gain_b_rms": float(np.std(xb)),
                "gain_split_rms": float(np.std(xa - xb) / np.sqrt(2.0)),
                "dark_split_rms_dn": float(
                    np.std(np.asarray(da) - np.asarray(db)) / np.sqrt(2.0)
                ),
            }
        )

    maps = {
        "gain_a": gain_a,
        "gain_b": gain_b,
        "dark": [x.astype(np.float32) for x in dark],
        "dark_a": [x.astype(np.float32) for x in dark_a],
        "dark_b": [x.astype(np.float32) for x in dark_b],
    }
    summary = {
        "flat_exposure": flat_exposure,
        "dark_exposure": dark_exposure,
        "flat_frames": len(flats),
        "dark_frames": len(darks),
        "cutoff_sensor_cyc_px": 0.02,
        "rois": rows,
        "median_gain_split_correlation": float(
            np.median([x["gain_split_correlation"] for x in rows])
        ),
    }
    return maps, summary


def calibrate_patch(
    patch: np.ndarray,
    roi_index: int,
    maps: dict,
    response_split: str | None,
) -> np.ndarray:
    signal = np.asarray(patch, dtype=float) - np.asarray(
        maps["dark"][roi_index], dtype=float
    )
    if response_split is None:
        return signal
    if response_split not in ("a", "b"):
        raise ValueError(f"unknown response split {response_split!r}")
    gain = np.asarray(maps[f"gain_{response_split}"][roi_index], dtype=float)
    return signal / gain
