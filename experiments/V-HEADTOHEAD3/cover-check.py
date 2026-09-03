"""Independent checker for the V-HEADTOHEAD3 cover-mode outcome.

This file deliberately does not import the author cover implementation or its
results.  Mid-ranks use ``numpy.unique``, registration uses scikit-image phase
correlation, geometry diagnostics use scikit-image resize, and spectra use a
weighted real FFT.  Outcome sites come only from the separately frozen record.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence


def _cap_threads() -> None:
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        try:
            current = int(os.environ.get(name, "8"))
        except ValueError:
            current = 8
        os.environ[name] = str(min(max(current, 1), 8))


_cap_threads()

import numpy as np
import tifffile
from skimage.filters import gaussian
from skimage.registration import phase_cross_correlation
from skimage.transform import resize


BANDS = (
    (0.02, 0.05),
    (0.05, 0.10),
    (0.10, 0.20),
    (0.20, 0.25),
)
BAND_NAMES = tuple(f"{lo:.2f}-{hi:.2f}" for lo, hi in BANDS)
UNLICENSED = "UNLICENSED_GT_0.25"
SIDE = 512
BORDER = 256
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260917
SCALE_GRID = np.arange(0.94, 1.0801, 0.005)
PROVENANCE_SCHEMA = "V-HEADTOHEAD3-COVER-RENDER-1"
EXPECTED_EXE = Path(r"C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe")
EXPECTED_EXE_SHA256 = (
    "2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7"
)
EXPECTED_SOURCE = Path(r"D:\personal\macro\113MSDCF")
EXPECTED_SCALE_SHA256 = (
    "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F"
)


class StopOutcome(RuntimeError):
    """A preregistered stop rather than a competitive result."""


def hash_file(path: Path, chunk: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest().upper()


def source_manifest(source: Path = EXPECTED_SOURCE) -> dict[str, Any]:
    entries = []
    paths = sorted(
        (
            path
            for path in source.rglob("*")
            if path.is_file() and path.suffix.lower() in {".arw", ".xmp"}
        ),
        key=lambda value: value.relative_to(source).as_posix().lower(),
    )
    for path in paths:
        entries.append(
            {
                "path": path.relative_to(source).as_posix(),
                "size": path.stat().st_size,
                "sha256": hash_file(path),
            }
        )
    counts = {
        suffix: sum(Path(row["path"]).suffix.lower() == suffix for row in entries)
        for suffix in (".arw", ".xmp")
    }
    canonical = json.dumps(
        entries,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "digest": hashlib.sha256(canonical).hexdigest().upper(),
        "counts": counts,
        "entries": entries,
    }


def expected_argv(mode: str, output: Path) -> list[str]:
    result = [
        str(EXPECTED_EXE),
        "stack",
        str(EXPECTED_SOURCE),
        "-o",
        str(output.resolve()),
        "--srgb",
    ]
    if mode == "crop":
        result.extend(("--cover", "crop"))
    elif mode != "scale":
        raise ValueError(f"unknown cover mode {mode!r}")
    return result


def parse_render_log(log: str, mode: str) -> dict[str, Any]:
    alignment = re.search(
        r"(\d+)\s+placed\s*/\s*(\d+)\s+refused",
        log,
        re.IGNORECASE,
    )
    if alignment is None:
        raise ValueError("render log has no placed/refused record")
    result: dict[str, Any] = {
        "mode": mode,
        "placed": int(alignment.group(1)),
        "refused": int(alignment.group(2)),
    }
    if mode == "scale":
        found = re.search(
            r"field of view scaled to\s+([0-9.]+)",
            log,
            re.IGNORECASE,
        )
        if found is None:
            raise ValueError("scale coverage banner absent")
        result.update({"k": float(found.group(1)), "unity_scale": False})
    elif mode == "crop":
        found = re.search(
            r"CROPPED to the region EVERY frame covers\s*--\s*"
            r"(\d+)\s*x\s*(\d+)\s*plane px.*?"
            r"at\s*\((\d+),\s*(\d+)\)\s*of\s*(\d+)\s*x\s*(\d+).*?"
            r"UNITY SCALE.*?\(k=([0-9.]+)\)",
            log,
            re.IGNORECASE | re.DOTALL,
        )
        if found is None:
            raise ValueError("unity-scale crop banner absent")
        result.update(
            {
                "plane_dimensions": [int(found.group(2)), int(found.group(1))],
                "plane_origin": [int(found.group(4)), int(found.group(3))],
                "full_plane_dimensions": [
                    int(found.group(6)),
                    int(found.group(5)),
                ],
                "k": float(found.group(7)),
                "unity_scale": True,
            }
        )
    else:
        raise ValueError(f"unknown cover mode {mode!r}")
    return result


def validate_provenance_payload(
    payload: dict[str, Any],
    crop_path: Path,
    scale_path: Path,
    pmax_path: Path,
    frozen: dict[str, Any],
    *,
    verify_live_source: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema") != PROVENANCE_SCHEMA:
        errors.append("schema")
    executable = payload.get("executable", {})
    if executable.get("path") != str(EXPECTED_EXE):
        errors.append("executable path")
    if (
        executable.get("sha256") != EXPECTED_EXE_SHA256
        or hash_file(EXPECTED_EXE) != EXPECTED_EXE_SHA256
    ):
        errors.append("executable hash")
    source = payload.get("source", {})
    pre = source.get("pre", {})
    post = source.get("post", {})
    if (
        source.get("path") != str(EXPECTED_SOURCE)
        or pre.get("digest") != post.get("digest")
        or pre.get("counts") != {".arw": 63, ".xmp": 63}
        or post.get("counts") != {".arw": 63, ".xmp": 63}
    ):
        errors.append("source pre/post manifest")
    if verify_live_source:
        live = source_manifest()
        if live.get("digest") != pre.get("digest") or live.get(
            "counts"
        ) != pre.get("counts"):
            errors.append("live source manifest")
    frozen_pmax = str(frozen.get("PMAX_SHA256", "")).upper()
    frozen_scale = str(frozen.get("SCALE_SHA256", "")).upper()
    frozen_subject = str(frozen.get("SUBJECT", ""))
    if (
        not frozen_pmax
        or hash_file(pmax_path) != frozen_pmax
        or payload.get("comparators", {}).get(frozen_subject) != frozen_pmax
    ):
        errors.append("comparator hash")
    environment = payload.get("environment", {})
    effective = environment.get("effective_strehl", {})
    if set(effective) != {"STREHL_CACHE_DIR"}:
        errors.append("inherited STREHL environment")
    try:
        Path(str(effective.get("STREHL_CACHE_DIR", ""))).resolve().relative_to(
            (Path(__file__).resolve().parent / "out").resolve()
        )
    except (ValueError, OSError):
        errors.append("private cache")
    if environment.get("rayon_num_threads") != 8:
        errors.append("render thread cap")
    if environment.get("numeric_thread_caps") != {
        "OMP_NUM_THREADS": 8,
        "OPENBLAS_NUM_THREADS": 8,
        "MKL_NUM_THREADS": 8,
        "NUMEXPR_NUM_THREADS": 8,
    }:
        errors.append("numerical thread caps")
    arms = payload.get("arms", {})
    for mode, live_path in (("scale", scale_path), ("crop", crop_path)):
        arm = arms.get(mode, {})
        if arm.get("path") != str(live_path.resolve()):
            errors.append(f"{mode} path")
        if arm.get("argv") != expected_argv(mode, live_path):
            errors.append(f"{mode} argument vector")
        if arm.get("exit_code") != 0:
            errors.append(f"{mode} exit")
        if not live_path.is_file() or arm.get("sha256") != hash_file(live_path):
            errors.append(f"{mode} live hash")
        try:
            facts = parse_render_log(str(arm.get("log", "")), mode)
        except ValueError:
            errors.append(f"{mode} log")
            continue
        if facts != arm.get("facts"):
            errors.append(f"{mode} parsed facts")
        if facts["placed"] != 63 or facts["refused"] != 0:
            errors.append(f"{mode} placement")
        if mode == "crop" and not facts["unity_scale"]:
            errors.append("crop not unity scale")
    scale = arms.get("scale", {})
    crop = arms.get("crop", {})
    if (
        frozen_scale != EXPECTED_SCALE_SHA256
        or scale.get("sha256") != frozen_scale
        or hash_file(scale_path) != EXPECTED_SCALE_SHA256
    ):
        errors.append("scale byte identity")
    if scale.get("sha256") == crop.get("sha256"):
        errors.append("no crop intervention")
    if errors:
        raise StopOutcome("invalid render provenance: " + ", ".join(errors))
    return payload


def validate_provenance(
    provenance_path: Path,
    crop_path: Path,
    scale_path: Path,
    pmax_path: Path,
    frozen: dict[str, Any],
) -> dict[str, Any]:
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    return validate_provenance_payload(
        payload,
        crop_path,
        scale_path,
        pmax_path,
        frozen,
        verify_live_source=True,
    )


class Record:
    def __init__(self) -> None:
        self.controls = 0
        self.control_failures = 0
        self.plants = 0
        self.plant_failures = 0

    def control(self, name: str, passed: bool, reading: str) -> None:
        self.controls += 1
        if not passed:
            self.control_failures += 1
        print(f"CONTROL {'GREEN' if passed else 'FAIL ':5s} {name}: {reading}")

    def plant(self, name: str, went_red: bool, reading: str) -> None:
        self.plants += 1
        if not went_red:
            self.plant_failures += 1
        print(f"PLANT   {'RED' if went_red else 'MISS':5s} {name}: {reading}")

    def finish(self) -> int:
        ok = self.control_failures == 0 and self.plant_failures == 0
        print(
            "COMMISSION "
            f"{'GREEN' if ok else 'FAILED'}: "
            f"{self.controls - self.control_failures}/{self.controls} controls GREEN; "
            f"{self.plants - self.plant_failures}/{self.plants} plants RED"
        )
        return 0 if ok else 1


def ranks(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a)
    _, inverse, counts = np.unique(
        x.ravel(), return_inverse=True, return_counts=True
    )
    ends = np.cumsum(counts, dtype=np.int64)
    starts = ends - counts
    average_one_based = (starts + 1 + ends) / 2.0
    n = x.size
    return ((average_one_based[inverse] - (n + 1) / 2.0) / n).reshape(x.shape)


def _frequency_radius(shape: tuple[int, int]) -> np.ndarray:
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.rfftfreq(shape[1])[None, :]
    return np.sqrt(fy * fy + fx * fx)


def _weighted_power(field: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    q = np.asarray(field, np.float64)
    q = q - np.mean(q)
    variance = float(np.mean(q * q))
    if not variance > 0.0:
        raise ValueError("constant checker crop")
    window = np.hanning(q.shape[0])[:, None] * np.hanning(q.shape[1])[None, :]
    power = np.abs(np.fft.rfft2(q * window)) ** 2
    if q.shape[1] % 2 == 0:
        power[:, 1:-1] *= 2.0
    else:
        power[:, 1:] *= 2.0
    denominator = q.size * float(np.sum(window * window)) * variance
    return power, _frequency_radius(q.shape), denominator


def rank_energy(a: np.ndarray, native_scale: float = 1.0) -> tuple[float | None, ...]:
    """Four independent Q bands in PMax-native physical frequencies.

    ``native_scale`` is arm pixels per PMax pixel.  A mapped edge above the
    licensed native Nyquist cap is represented by ``None`` and is never summed.
    """

    if not native_scale > 0.0:
        raise ValueError("native scale must be positive")
    power, radius, denominator = _weighted_power(ranks(np.asarray(a)))
    result: list[float | None] = []
    for lo, hi in BANDS:
        mapped_lo = lo / native_scale
        mapped_hi = hi / native_scale
        if mapped_hi > 0.25:
            result.append(None)
            continue
        mask = (radius >= mapped_lo) & (radius < mapped_hi)
        result.append(float(np.sum(power[mask], dtype=np.float64) / denominator))
    return tuple(result)


def raw_energy(a: np.ndarray, native_scale: float = 1.0) -> tuple[float | None, ...]:
    power, radius, denominator = _weighted_power(np.asarray(a, np.float64))
    result: list[float | None] = []
    for lo, hi in BANDS:
        mapped_lo = lo / native_scale
        mapped_hi = hi / native_scale
        if mapped_hi > 0.25:
            result.append(None)
        else:
            mask = (radius >= mapped_lo) & (radius < mapped_hi)
            result.append(
                float(np.sum(power[mask], dtype=np.float64) / denominator)
            )
    return tuple(result)


def correlation(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, np.float64).ravel()
    y = np.asarray(b, np.float64).ravel()
    x -= np.mean(x)
    y -= np.mean(y)
    denominator = math.sqrt(float(x @ x) * float(y @ y))
    return float((x @ y) / denominator) if denominator else float("nan")


def correction(reference: np.ndarray, moving: np.ndarray) -> tuple[int, int]:
    shift, _, _ = phase_cross_correlation(
        reference,
        moving,
        upsample_factor=1,
        normalization="phase",
    )
    return int(round(float(shift[0]))), int(round(float(shift[1])))


def shifted_overlap(
    reference: np.ndarray,
    moving: np.ndarray,
    shift: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Overlap after shifting ``moving`` by ``shift`` into reference space."""

    dy, dx = shift
    ry = max(0, dy)
    rx = max(0, dx)
    my = max(0, -dy)
    mx = max(0, -dx)
    height = min(reference.shape[0] - ry, moving.shape[0] - my)
    width = min(reference.shape[1] - rx, moving.shape[1] - mx)
    if height <= 0 or width <= 0:
        return reference[:0, :0], moving[:0, :0]
    return (
        reference[ry : ry + height, rx : rx + width],
        moving[my : my + height, mx : mx + width],
    )


def _registration_score(
    reference: np.ndarray,
    moving: np.ndarray,
) -> tuple[float, tuple[int, int]]:
    shape = (
        max(reference.shape[0], moving.shape[0]),
        max(reference.shape[1], moving.shape[1]),
    )
    a = np.zeros(shape, np.float64)
    b = np.zeros(shape, np.float64)
    a[: reference.shape[0], : reference.shape[1]] = reference
    b[: moving.shape[0], : moving.shape[1]] = moving
    shift = correction(a, b)
    aa, bb = shifted_overlap(reference, moving, shift)
    minimum = min(reference.size, moving.size)
    fraction = aa.size / minimum
    if aa.size == 0 or fraction < 0.45:
        return float("-inf"), shift
    return correlation(aa, bb) * math.sqrt(fraction), shift


def _scale_score(
    arm_ranks: np.ndarray,
    pmax_ranks: np.ndarray,
    scale: float,
) -> tuple[float, tuple[int, int]]:
    shape = (
        max(8, int(round(pmax_ranks.shape[0] * scale))),
        max(8, int(round(pmax_ranks.shape[1] * scale))),
    )
    moving = resize(
        pmax_ranks,
        shape,
        order=1,
        mode="reflect",
        anti_aliasing=False,
        preserve_range=True,
    )
    return _registration_score(arm_ranks, moving)


def fit_geometry_arrays(
    arm: np.ndarray,
    pmax: np.ndarray,
    scales: np.ndarray = SCALE_GRID,
    sample_step: int = 1,
) -> dict[str, Any]:
    arm_ranks = ranks(np.asarray(arm)[::sample_step, ::sample_step])
    pmax_ranks = ranks(np.asarray(pmax)[::sample_step, ::sample_step])
    coarse = [_scale_score(arm_ranks, pmax_ranks, float(s)) for s in scales]
    coarse_index = int(np.argmax([row[0] for row in coarse]))
    coarse_interior = 0 < coarse_index < len(scales) - 1
    centre = float(scales[coarse_index])
    fine_scales = np.arange(centre - 0.006, centre + 0.0061, 0.001)
    fine = [_scale_score(arm_ranks, pmax_ranks, float(s)) for s in fine_scales]
    fine_index = int(np.argmax([row[0] for row in fine]))
    score, shift = fine[fine_index]
    return {
        "scale": float(fine_scales[fine_index]),
        "translation": [
            float(shift[0] * sample_step),
            float(shift[1] * sample_step),
        ],
        "score": float(score),
        "coarse_interior": coarse_interior,
        "fine_interior": 0 < fine_index < len(fine_scales) - 1,
        "sample_step": int(sample_step),
    }


def fit_geometry(arm: np.ndarray, pmax: np.ndarray) -> dict[str, Any]:
    step = max(1, int(math.ceil(max(*arm.shape, *pmax.shape) / 768)))
    return fit_geometry_arrays(arm, pmax, sample_step=step)


def crop_bounds(
    shape: tuple[int, int],
    centre: Sequence[float],
    side: int,
) -> tuple[int, int, int, int] | None:
    y, x = map(float, centre)
    y0 = int(round(y - side / 2.0))
    x0 = int(round(x - side / 2.0))
    y1 = y0 + side
    x1 = x0 + side
    if y0 < 0 or x0 < 0 or y1 > shape[0] or x1 > shape[1]:
        return None
    return y0, x0, y1, x1


def centred(
    a: np.ndarray,
    centre: Sequence[float],
    side: int,
) -> np.ndarray | None:
    bounds = crop_bounds(a.shape, centre, side)
    if bounds is None:
        return None
    y0, x0, y1, x1 = bounds
    return np.asarray(a[y0:y1, x0:x1])


def border_clearance(
    shape: tuple[int, int],
    centre: Sequence[float],
    side: int,
) -> int:
    bounds = crop_bounds(shape, centre, side)
    if bounds is None:
        return -1
    y0, x0, y1, x1 = bounds
    return int(min(y0, x0, shape[0] - y1, shape[1] - x1))


def rail_fraction(a: np.ndarray) -> float:
    if np.issubdtype(a.dtype, np.integer):
        info = np.iinfo(a.dtype)
        return float(np.mean((a == info.min) | (a == info.max)))
    return float(np.mean((a == 0.0) | (a == 1.0)))


def map_site(
    arm: np.ndarray,
    pmax: np.ndarray,
    centre: Sequence[int],
    geometry: dict[str, Any],
    required_border: int = 0,
) -> dict[str, Any]:
    scale = float(geometry["scale"])
    translation = np.asarray(geometry["translation"], np.float64)
    pcentre = np.asarray(centre, np.float64)
    predicted = scale * pcentre + translation
    diagnostic_side = SIDE + 128
    pdiag = centred(pmax, pcentre, diagnostic_side)
    arm_diagnostic_side = int(round(diagnostic_side * scale))
    adiag = centred(arm, predicted, arm_diagnostic_side)
    if pdiag is None or adiag is None:
        return {"reason": "bounds"}
    resized_pmax = resize(
        ranks(pdiag),
        adiag.shape,
        order=1,
        mode="reflect",
        anti_aliasing=False,
        preserve_range=True,
    )
    arm_diag_ranks = ranks(adiag)
    local = correction(arm_diag_ranks, resized_pmax)
    if max(abs(local[0]), abs(local[1])) > int(round(64 * max(scale, 1.0))):
        return {"reason": "registration"}
    final_centre = predicted + np.asarray(local, np.float64)
    arm_side = int(round(SIDE * scale))
    pmax_crop = centred(pmax, pcentre, SIDE)
    arm_crop = centred(arm, final_centre, arm_side)
    if pmax_crop is None or arm_crop is None:
        return {"reason": "bounds"}
    clearance = border_clearance(arm.shape, final_centre, arm_side)
    if clearance < required_border:
        return {
            "reason": "border",
            "border_clearance": clearance,
        }
    aa, bb = shifted_overlap(arm_diag_ranks, resized_pmax, local)
    fixed_correlation = correlation(aa[::4, ::4], bb[::4, ::4])
    if not np.isfinite(fixed_correlation) or fixed_correlation <= 0.0:
        return {"reason": "registration"}
    if rail_fraction(pmax_crop) > 0.01 or rail_fraction(arm_crop) > 0.01:
        return {"reason": "rail"}
    return {
        "reason": None,
        "arm": arm_crop,
        "pmax": pmax_crop,
        "centre": final_centre.tolist(),
        "local_correction": list(local),
        "correlation": fixed_correlation,
        "border_clearance": clearance,
    }


def _normalise_site(row: Any, label: str | None = None) -> dict[str, Any]:
    if isinstance(row, dict):
        centre = row.get("centre", row.get("pmax_centre"))
        actual_label = row.get("label", row.get("stratum", label))
        site_id = row.get("id")
    else:
        centre = row
        actual_label = label
        site_id = None
    if (
        not isinstance(centre, (list, tuple))
        or len(centre) != 2
        or any(isinstance(value, bool) for value in centre)
    ):
        raise ValueError(f"invalid frozen centre: {centre!r}")
    y, x = (int(centre[0]), int(centre[1]))
    actual_label = str(actual_label).lower() if actual_label is not None else ""
    if actual_label.startswith("detail"):
        actual_label = "detail"
    elif actual_label.startswith("flat"):
        actual_label = "flat"
    else:
        raise ValueError(f"invalid frozen stratum: {actual_label!r}")
    result: dict[str, Any] = {"centre": [y, x], "label": actual_label}
    if site_id is not None:
        result["id"] = str(site_id)
    return result


def normalise_sites(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, dict) and "sites" in document:
        rows = [_normalise_site(row) for row in document["sites"]]
    elif isinstance(document, dict) and (
        "detail" in document or "flat" in document
    ):
        rows = []
        for label in ("detail", "flat"):
            rows.extend(_normalise_site(row, label) for row in document.get(label, []))
    elif isinstance(document, (list, tuple)):
        rows = [_normalise_site(row) for row in document]
    else:
        raise ValueError("frozen record must contain sites or detail/flat lists")
    centres = [tuple(row["centre"]) for row in rows]
    if len(set(centres)) != len(centres):
        raise ValueError("duplicate frozen PMax centre")
    return rows


def site_digest(sites: Sequence[dict[str, Any]]) -> str:
    canonical = [
        {"centre": list(map(int, row["centre"])), "label": str(row["label"])}
        for row in sites
    ]
    payload = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def validate_site_digest(
    sites: Sequence[dict[str, Any]],
    expected: str,
) -> str:
    actual = site_digest(sites)
    if not expected or actual != str(expected).upper():
        raise ValueError(f"frozen site digest mismatch: {actual} != {expected}")
    return actual


def _module_from_spec(spec: str) -> ModuleType:
    path = Path(spec)
    if path.is_file():
        module_spec = importlib.util.spec_from_file_location("cover_frozen_sites", path)
        if module_spec is None or module_spec.loader is None:
            raise ValueError(f"cannot load frozen module {path}")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module
    return importlib.import_module(spec)


def load_frozen(spec: str) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    path = Path(spec)
    metadata: dict[str, Any]
    if path.suffix.lower() == ".json":
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("frozen JSON root must be an object")
        metadata = dict(document)
        site_document = document
        expected = document.get("site_digest", document.get("digest"))
    else:
        module = _module_from_spec(spec)
        metadata = {
            name: getattr(module, name)
            for name in (
                "PMAX_SHA256",
                "SCALE_SHA256",
                "SUBJECT",
                "SITE_DIGEST",
                "AUTHOR_GEOMETRY",
            )
            if hasattr(module, name)
        }
        site_document = None
        for name in ("COVER_FROZEN", "FROZEN_SITES", "SITES"):
            if hasattr(module, name):
                site_document = getattr(module, name)
                break
        if site_document is None and (
            hasattr(module, "DETAIL_SITES") or hasattr(module, "FLAT_SITES")
        ):
            site_document = {
                "detail": getattr(module, "DETAIL_SITES", ()),
                "flat": getattr(module, "FLAT_SITES", ()),
            }
        if site_document is None:
            raise ValueError("frozen module exports no supported site record")
        expected = getattr(module, "SITE_DIGEST", None)
        if isinstance(site_document, dict):
            expected = site_document.get(
                "site_digest", site_document.get("digest", expected)
            )
            metadata.update(site_document)
    sites = normalise_sites(site_document)
    if expected is None:
        raise ValueError("frozen record has no site digest")
    digest = validate_site_digest(sites, str(expected))
    return sites, digest, metadata


def coverage_gate(sites: Sequence[dict[str, Any]]) -> tuple[bool, dict[str, int]]:
    counts = collections.Counter(str(site["label"]) for site in sites)
    result = {"detail": counts["detail"], "flat": counts["flat"]}
    return result["detail"] >= 12 and result["flat"] >= 6, result


def competitive_class(low: float, high: float) -> str:
    if low > 1.05:
        return "LEADS"
    if high < 1.0 / 1.05:
        return "TRAILS"
    return "UNRESOLVED"


def bootstrap_rows(rows: Sequence[dict[str, Any]], seed: int) -> list[dict[str, Any] | str]:
    if not rows:
        raise ValueError("empty bootstrap stratum")
    result: list[dict[str, Any] | str] = []
    rng = np.random.default_rng(seed)
    for band in range(len(BANDS)):
        if any(row["logs"][band] is None for row in rows):
            result.append(UNLICENSED)
            continue
        values = np.asarray([row["logs"][band] for row in rows], np.float64)
        indices = rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))
        means = np.mean(values[indices], axis=1)
        summaries = []
        for column in range(3):
            low, high = np.quantile(means[:, column], [0.025, 0.975])
            summaries.append(
                {
                    "point": float(np.exp(np.mean(values[:, column]))),
                    "ci_low": float(np.exp(low)),
                    "ci_high": float(np.exp(high)),
                }
            )
        summaries[0]["class"] = competitive_class(
            summaries[0]["ci_low"], summaries[0]["ci_high"]
        )
        summaries[1]["class"] = competitive_class(
            summaries[1]["ci_low"], summaries[1]["ci_high"]
        )
        result.append(
            {
                "n": len(values),
                "scale_over_pmax": summaries[0],
                "crop_over_pmax": summaries[1],
                "crop_over_scale": summaries[2],
            }
        )
    return result


def cover_verdict(
    scale_class: str,
    crop_class: str,
    g_low: float,
    g_high: float,
    quadrant_effects: Sequence[float],
    loo_reversal: bool,
) -> str:
    guards = (
        len(quadrant_effects) == 4
        and all(value > 1.0 for value in quadrant_effects)
        and not loo_reversal
    )
    if g_high < 0.98:
        return "CROP_DEGRADES"
    if g_low >= 0.98 and g_high <= 1.02:
        return "COVER_NOT_CAUSE"
    if (
        scale_class == "TRAILS"
        and crop_class != "TRAILS"
        and g_low > 1.02
        and guards
    ):
        return "RECOVERED_BY_CROP"
    if (
        scale_class == "TRAILS"
        and crop_class == "TRAILS"
        and g_low > 1.02
        and guards
    ):
        return "PARTIAL_RECOVERY"
    return "UNRESOLVED"


def _schema_ok(payload: dict[str, Any]) -> bool:
    bands = payload.get("bands")
    if not isinstance(bands, dict):
        return False
    if set(bands) != set(BAND_NAMES) | {"gt_0.25"}:
        return False
    if bands.get("gt_0.25") != UNLICENSED:
        return False
    for name in BAND_NAMES:
        value = bands[name]
        if value == UNLICENSED:
            continue
        if not isinstance(value, dict):
            return False
    return True


def green(path: Path) -> np.ndarray:
    image = tifffile.memmap(path)
    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[-1] >= 2:
        return image[:, :, 1]
    if image.ndim == 3 and image.shape[0] >= 2:
        return image[1]
    raise ValueError(f"unsupported TIFF shape {image.shape} for {path}")


def _logs(
    scale_energy: tuple[float | None, ...],
    crop_energy: tuple[float | None, ...],
    pmax_energy: tuple[float | None, ...],
) -> list[tuple[float, float, float] | None]:
    result: list[tuple[float, float, float] | None] = []
    for qs, qc, qp in zip(scale_energy, crop_energy, pmax_energy):
        if qs is None or qc is None or qp is None:
            result.append(None)
            continue
        if min(qs, qc, qp) <= 0.0:
            raise ValueError("zero rank energy in licensed band")
        ds = math.log(qs / qp)
        dc = math.log(qc / qp)
        result.append((ds, dc, dc - ds))
    return result


def _primary_guards(rows: Sequence[dict[str, Any]], pmax_shape: tuple[int, int]) -> tuple[list[float], bool]:
    effects: list[float] = []
    for qy in range(2):
        for qx in range(2):
            selected = [
                row
                for row in rows
                if (row["centre"][0] >= pmax_shape[0] / 2.0) == bool(qy)
                and (row["centre"][1] >= pmax_shape[1] / 2.0) == bool(qx)
                and row["logs"][2] is not None
            ]
            if selected:
                effects.append(
                    float(
                        np.exp(
                            np.mean([row["logs"][2][2] for row in selected])
                        )
                    )
                )
    loo_reversal = False
    if len(rows) > 1:
        for index in range(len(rows)):
            remaining = [
                row["logs"][2][2]
                for i, row in enumerate(rows)
                if i != index and row["logs"][2] is not None
            ]
            if remaining and float(np.exp(np.mean(remaining))) <= 1.0:
                loo_reversal = True
                break
    return effects, loo_reversal


def run_outcome(
    crop_path: Path,
    scale_path: Path,
    pmax_path: Path,
    frozen_spec: str,
    provenance_path: Path,
) -> dict[str, Any]:
    sites, digest, metadata = load_frozen(frozen_spec)
    validate_provenance(
        provenance_path,
        crop_path,
        scale_path,
        pmax_path,
        metadata,
    )
    pmax = green(pmax_path)
    scale_arm = green(scale_path)
    crop_arm = green(crop_path)
    scale_geometry = fit_geometry(scale_arm, pmax)
    crop_geometry = fit_geometry(crop_arm, pmax)
    for name, geometry in (
        ("scale", scale_geometry),
        ("crop", crop_geometry),
    ):
        if not geometry["coarse_interior"] or not geometry["fine_interior"]:
            raise StopOutcome(f"{name} geometry optimum is not interior")

    reasons = {"scale": collections.Counter(), "crop": collections.Counter()}
    retained: list[dict[str, Any]] = []
    crop_clearances: list[int] = []
    for site in sites:
        centre = site["centre"]
        scale_row = map_site(scale_arm, pmax, centre, scale_geometry)
        crop_row = map_site(
            crop_arm,
            pmax,
            centre,
            crop_geometry,
            required_border=BORDER,
        )
        reasons["scale"][scale_row["reason"] or "eligible"] += 1
        reasons["crop"][crop_row["reason"] or "eligible"] += 1
        if scale_row["reason"] is not None or crop_row["reason"] is not None:
            continue
        pmax_crop = centred(pmax, centre, SIDE)
        if pmax_crop is None:
            continue
        pmax_energy = rank_energy(pmax_crop)
        scale_energy = rank_energy(
            scale_row["arm"], float(scale_geometry["scale"])
        )
        crop_energy = rank_energy(crop_row["arm"], float(crop_geometry["scale"]))
        retained.append(
            {
                "centre": centre,
                "label": site["label"],
                "logs": _logs(scale_energy, crop_energy, pmax_energy),
            }
        )
        crop_clearances.append(int(crop_row["border_clearance"]))

    coverage_ok, retained_counts = coverage_gate(retained)
    if not coverage_ok:
        raise StopOutcome(
            "coverage gate failed: "
            f"{retained_counts['detail']} detail, {retained_counts['flat']} flat"
        )
    if not crop_clearances or min(crop_clearances) < BORDER:
        raise StopOutcome("crop border-clearance gate failed")
    detail = [row for row in retained if row["label"] == "detail"]
    flat = [row for row in retained if row["label"] == "flat"]
    detail_summary = bootstrap_rows(detail, BOOTSTRAP_SEED)
    flat_summary = bootstrap_rows(flat, BOOTSTRAP_SEED + 1)
    band_payload: dict[str, Any] = {}
    for index, name in enumerate(BAND_NAMES):
        if detail_summary[index] == UNLICENSED or flat_summary[index] == UNLICENSED:
            band_payload[name] = UNLICENSED
        else:
            band_payload[name] = {
                "detail": detail_summary[index],
                "flat": flat_summary[index],
            }
    band_payload["gt_0.25"] = UNLICENSED

    primary = detail_summary[2]
    if primary == UNLICENSED:
        verdict = UNLICENSED
        quadrants: list[float] = []
        loo_reversal = False
    else:
        quadrants, loo_reversal = _primary_guards(detail, pmax.shape)
        verdict = cover_verdict(
            primary["scale_over_pmax"]["class"],
            primary["crop_over_pmax"]["class"],
            primary["crop_over_scale"]["ci_low"],
            primary["crop_over_scale"]["ci_high"],
            quadrants,
            loo_reversal,
        )
    payload = {
        "status": "GREEN",
        "site_digest": digest,
        "geometry": {
            "scale": scale_geometry,
            "crop": crop_geometry,
        },
        "coverage": {
            "frozen": collections.Counter(site["label"] for site in sites),
            "retained": retained_counts,
            "loss_reasons": {
                name: dict(counter) for name, counter in reasons.items()
            },
            "minimum_crop_border": min(crop_clearances),
        },
        "bands": band_payload,
        "primary": {
            "verdict": verdict,
            "quadrant_effects": quadrants,
            "loo_reversal": loo_reversal,
        },
    }
    if not _schema_ok(payload):
        raise RuntimeError("internal capped-output schema failure")
    return payload


def normalise(x: np.ndarray) -> np.ndarray:
    y = np.asarray(x, np.float64)
    return (y - np.min(y)) / (np.max(y) - np.min(y))


def fixture(n: int = 320, seed: int = 1709) -> np.ndarray:
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    phase = np.exp(2j * np.pi * rng.random((n, n)))
    texture = np.fft.ifft2(phase / np.maximum(radius, 1.0 / n)).real
    texture = (texture - np.mean(texture)) / np.std(texture)
    yy, xx = np.mgrid[:n, :n]
    signal = (
        0.24 * texture
        + 0.42 * np.sin(2.0 * np.pi * 0.035 * xx + 0.1)
        + 0.34 * np.sin(2.0 * np.pi * 0.075 * yy + 0.7)
        + 0.44 * np.sin(2.0 * np.pi * 0.15 * (0.8 * xx + 0.6 * yy) + 1.1)
        + 0.25 * np.sin(2.0 * np.pi * 0.225 * xx + 0.4)
        + 0.30 * (xx > 0.37 * n)
        - 0.18 * (yy > 0.64 * n)
    )
    return normalise(signal)


def _tone_transforms(x: np.ndarray) -> dict[str, np.ndarray]:
    z = normalise(x)
    return {
        "affine": 0.17 + 2.3 * z,
        "gamma3": z**3,
        "logistic12": 1.0 / (1.0 + np.exp(-12.0 * (z - 0.5))),
    }


def commission_bins(rec: Record) -> None:
    probes = (0.03125, 0.078125, 0.15625, 0.234375)
    membership = [
        [index for index, (lo, hi) in enumerate(BANDS) if lo <= f < hi]
        for f in probes
    ]
    rec.control(
        "four fixed bins",
        membership == [[0], [1], [2], [3]],
        f"memberships={membership}",
    )
    rejected = not any(lo <= 0.28125 < hi for lo, hi in BANDS)
    rec.control("0.28125 cap rejection", rejected, f"rejected={rejected}")
    mutant_bands = BANDS + ((0.25, 0.30),)
    mutant_accepts = any(lo <= 0.28125 < hi for lo, hi in mutant_bands)
    rec.plant(
        "uncapped fifth bin",
        mutant_accepts and rejected,
        f"mutant accepts 0.28125={mutant_accepts}",
    )


def commission_tone(rec: Record, x: np.ndarray) -> None:
    base = np.asarray(rank_energy(x), np.float64)
    moves = {
        name: float(
            np.max(np.abs(np.asarray(rank_energy(value), np.float64) - base))
        )
        for name, value in _tone_transforms(x).items()
    }
    worst = max(moves.values())
    rec.control(
        "strict affine/gamma/logistic invariance",
        worst <= 1e-12,
        ", ".join(f"{name}={move:.3e}" for name, move in moves.items()),
    )
    raw_base = np.asarray(raw_energy(x), np.float64)
    raw_moves = {
        name: float(
            np.max(
                np.abs(
                    np.asarray(raw_energy(value), np.float64) / raw_base - 1.0
                )
            )
        )
        for name, value in _tone_transforms(x).items()
    }
    potency = max(raw_moves.values())
    rec.plant(
        "raw-power substitution",
        worst <= 1e-12 and potency >= 0.05,
        f"ordinal move={worst:.3e}, raw relative move={potency:.3f}",
    )


def commission_identity_blur_usm(rec: Record, x: np.ndarray) -> None:
    base = np.asarray(rank_energy(x), np.float64)
    identity = np.asarray(rank_energy(np.array(x, copy=True)), np.float64)
    blurred_image = gaussian(x, sigma=1.2, mode="reflect", preserve_range=True)
    blurred = np.asarray(rank_energy(blurred_image), np.float64)
    lowpass = gaussian(x, sigma=1.0, mode="reflect", preserve_range=True)
    sharpened_image = x + 1.4 * (x - lowpass)
    sharpened = np.asarray(rank_energy(sharpened_image), np.float64)
    rec.control(
        "identity parity",
        np.array_equal(base, identity),
        f"max delta={float(np.max(np.abs(base - identity))):.3e}",
    )
    blur_ratio = float(blurred[2] / base[2])
    usm_ratio = float(sharpened[2] / base[2])
    rec.control(
        "blur degradation 0.10-0.20",
        blur_ratio < 0.95,
        f"ratio={blur_ratio:.4f}",
    )
    rec.control(
        "independent USM improvement 0.10-0.20",
        usm_ratio > 1.05,
        f"ratio={usm_ratio:.4f}",
    )
    disabled_blur = float(np.asarray(rank_energy(x))[2] / base[2])
    disabled_usm = float(np.asarray(rank_energy(x))[2] / base[2])
    rec.plant(
        "disabled blur",
        not (disabled_blur < 0.95),
        f"mutant ratio={disabled_blur:.4f}",
    )
    rec.plant(
        "disabled USM",
        not (disabled_usm > 1.05),
        f"mutant ratio={disabled_usm:.4f}",
    )


def commission_registration(rec: Record) -> None:
    source = fixture(192, seed=181)
    planted = (7, -5)
    moving = np.roll(source, planted, axis=(0, 1))
    recovered = correction(ranks(source), ranks(moving))
    expected = (-planted[0], -planted[1])
    a, b = shifted_overlap(source, moving, recovered)
    rec.control(
        "known translation and correction sign",
        recovered == expected and np.array_equal(a, b),
        f"expected={expected}, recovered={recovered}",
    )
    wrong = (-recovered[0], -recovered[1])
    wa, wb = shifted_overlap(source, moving, wrong)
    na, nb = shifted_overlap(source, moving, (0, 0))
    rec.plant(
        "wrong registration sign",
        not np.array_equal(wa, wb),
        f"wrong={wrong}, equality={np.array_equal(wa, wb)}",
    )
    rec.plant(
        "registration no-op",
        not np.array_equal(na, nb),
        f"equality={np.array_equal(na, nb)}",
    )


def commission_scale(rec: Record) -> None:
    pmax = fixture(320, seed=991)
    truth = 1.035
    enlarged = resize(
        pmax,
        (int(round(pmax.shape[0] * truth)), int(round(pmax.shape[1] * truth))),
        order=1,
        mode="reflect",
        anti_aliasing=False,
        preserve_range=True,
    )
    origin = (11, 17)
    arm = enlarged[origin[0] : -13, origin[1] : -7]
    result = fit_geometry_arrays(arm, pmax)
    translation = np.asarray(result["translation"])
    expected_translation = -np.asarray(origin, np.float64)
    rec.control(
        "known scale and crop translation",
        result["coarse_interior"]
        and result["fine_interior"]
        and abs(result["scale"] - truth) <= 0.003
        and float(np.max(np.abs(translation - expected_translation))) <= 3.0,
        f"scale={result['scale']:.4f}, translation={translation.tolist()}, "
        f"expected={expected_translation.tolist()}",
    )
    dimension_scale = 0.5 * (
        arm.shape[0] / pmax.shape[0] + arm.shape[1] / pmax.shape[1]
    )
    rec.plant(
        "dimension-assumed scale",
        abs(dimension_scale - truth) > 0.01
        and abs(result["scale"] - truth) <= 0.003,
        f"dimension={dimension_scale:.4f}, fitted={result['scale']:.4f}",
    )


def commission_crop_origin(rec: Record) -> None:
    image = np.arange(180 * 220, dtype=np.int64).reshape(180, 220)
    origin = (23, 31)
    emitted = image[origin[0] : origin[0] + 120, origin[1] : origin[1] + 140]
    pmax_centre = np.asarray((83, 101))
    emitted_centre = pmax_centre - np.asarray(origin)
    expected = centred(image, pmax_centre, 48)
    actual = centred(emitted, emitted_centre, 48)
    rec.control(
        "exact centred-crop mapping",
        expected is not None and actual is not None and np.array_equal(expected, actual),
        f"origin={origin}, mapped={emitted_centre.tolist()}",
    )
    for name, delta in (
        ("origin y-1", (-1, 0)),
        ("origin y+1", (1, 0)),
        ("origin x-1", (0, -1)),
        ("origin x+1", (0, 1)),
    ):
        mutant_centre = pmax_centre - (
            np.asarray(origin) + np.asarray(delta)
        )
        mutant = centred(emitted, mutant_centre, 48)
        rec.plant(
            name,
            mutant is not None and not np.array_equal(expected, mutant),
            f"mutant mapped={mutant_centre.tolist()}",
        )


def commission_freeze_and_coverage(rec: Record) -> None:
    sites = [
        {"centre": [600 + 20 * i, 700 + 17 * i], "label": "detail"}
        for i in range(12)
    ] + [
        {"centre": [900 + 20 * i, 1100 + 17 * i], "label": "flat"}
        for i in range(6)
    ]
    digest = site_digest(sites)
    actual = validate_site_digest(sites, digest)
    ok, counts = coverage_gate(sites)
    rec.control(
        "frozen digest and coverage gates",
        actual == digest and ok,
        f"digest={digest[:12]}, counts={counts}",
    )
    reselected = [dict(row) for row in sites]
    reselected[0] = {"centre": [reselected[0]["centre"][0] + 1, reselected[0]["centre"][1]], "label": "detail"}
    try:
        validate_site_digest(reselected, digest)
        reselection_rejected = False
    except ValueError:
        reselection_rejected = True
    rec.plant(
        "post-treatment site reselection",
        reselection_rejected,
        f"replacement rejected={reselection_rejected}",
    )
    changed_digest = ("0" if digest[0] != "0" else "1") + digest[1:]
    try:
        validate_site_digest(sites, changed_digest)
        digest_rejected = False
    except ValueError:
        digest_rejected = True
    rec.plant(
        "frozen digest mutation",
        digest_rejected,
        f"mutated digest rejected={digest_rejected}",
    )
    near_edge = (290, 600)
    side = 80
    clearance = border_clearance((1200, 1200), near_edge, side)
    proper = clearance >= BORDER
    bounds_only = clearance >= 0
    rec.control(
        "256-pixel border gate",
        not proper and bounds_only,
        f"clearance={clearance}, proper={proper}",
    )
    rec.plant(
        "omitted border gate",
        bounds_only and not proper,
        "bounds-only mutant admits the rejected site",
    )


def commission_schema(rec: Record, x: np.ndarray) -> None:
    licensed = rank_energy(x, 1.0)
    capped = rank_energy(x, 0.95)
    payload = {
        "bands": {
            **{
                name: ({"q": licensed[index]} if licensed[index] is not None else UNLICENSED)
                for index, name in enumerate(BAND_NAMES)
            },
            "gt_0.25": UNLICENSED,
        }
    }
    rec.control(
        "capped four-band schema",
        _schema_ok(payload)
        and capped[3] is None
        and rank_energy(x, 1.0 - 2e-12)[3] is None,
        f"schema={_schema_ok(payload)}, corrected-final={capped[3]}",
    )
    mutant = json.loads(json.dumps(payload))
    mutant["bands"]["gt_0.25"] = 1.28125
    rec.plant(
        "numeric above-cap schema",
        not _schema_ok(mutant),
        f"mutant accepted={_schema_ok(mutant)}",
    )


def commission_provenance(rec: Record) -> None:
    scale_path = Path(
        r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff"
    )
    crop_path = Path(
        r"D:\edited\macro\test\2026-05-07-21.31.06 ZS PMax.tif"
    )
    pmax_path = Path(
        r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"
    )
    pmax_hash = hash_file(pmax_path)
    digest = "A" * 64
    scale_log = (
        "alignment       : ON, 63 placed / 0 refused\n"
        "coverage        : field of view scaled to 0.9970 so that EVERY frame covers"
    )
    crop_log = (
        "alignment       : ON, 63 placed / 0 refused\n"
        "coverage        : CROPPED to the region EVERY frame covers -- "
        "3490 x 2320 plane px at (13, 12) of 3516 x 2344, "
        "emitted at UNITY SCALE. dropped and NOT upsampled (k=0.9926)"
    )
    payload: dict[str, Any] = {
        "schema": PROVENANCE_SCHEMA,
        "executable": {
            "path": str(EXPECTED_EXE),
            "sha256": EXPECTED_EXE_SHA256,
        },
        "source": {
            "path": str(EXPECTED_SOURCE),
            "pre": {
                "digest": digest,
                "counts": {".arw": 63, ".xmp": 63},
            },
            "post": {
                "digest": digest,
                "counts": {".arw": 63, ".xmp": 63},
            },
        },
        "comparators": {
            "113": pmax_hash,
            "113-sharp": hash_file(crop_path),
        },
        "environment": {
            "effective_strehl": {
                "STREHL_CACHE_DIR": str(
                    (Path(__file__).resolve().parent / "out" / "cache").resolve()
                )
            },
            "rayon_num_threads": 8,
            "numeric_thread_caps": {
                "OMP_NUM_THREADS": 8,
                "OPENBLAS_NUM_THREADS": 8,
                "MKL_NUM_THREADS": 8,
                "NUMEXPR_NUM_THREADS": 8,
            },
        },
        "arms": {
            "scale": {
                "path": str(scale_path.resolve()),
                "argv": expected_argv("scale", scale_path),
                "exit_code": 0,
                "sha256": EXPECTED_SCALE_SHA256,
                "facts": parse_render_log(scale_log, "scale"),
                "log": scale_log,
            },
            "crop": {
                "path": str(crop_path.resolve()),
                "argv": expected_argv("crop", crop_path),
                "exit_code": 0,
                "sha256": hash_file(crop_path),
                "facts": parse_render_log(crop_log, "crop"),
                "log": crop_log,
            },
        },
    }
    frozen = {
        "PMAX_SHA256": pmax_hash,
        "SCALE_SHA256": EXPECTED_SCALE_SHA256,
        "SUBJECT": "113",
    }

    def accepted(document: dict[str, Any], record: dict[str, Any] = frozen) -> bool:
        try:
            validate_provenance_payload(
                document,
                crop_path,
                scale_path,
                pmax_path,
                record,
                verify_live_source=False,
            )
            return True
        except StopOutcome:
            return False

    rec.control(
        "live-file-bound provenance null",
        accepted(payload),
        "frozen executable/scale/comparator files accepted",
    )

    def mutant(change: Any) -> bool:
        document = json.loads(json.dumps(payload))
        change(document)
        return not accepted(document)

    mutations = (
        (
            "changed executable hash",
            lambda d: d["executable"].__setitem__("sha256", "0" * 64),
        ),
        (
            "changed comparator hash",
            lambda d: d["comparators"].__setitem__("113", "0" * 64),
        ),
        (
            "swapped comparator labels",
            lambda d: d.__setitem__(
                "comparators",
                {
                    "113": d["comparators"]["113-sharp"],
                    "113-sharp": d["comparators"]["113"],
                },
            ),
        ),
        (
            "extra render flag",
            lambda d: d["arms"]["crop"]["argv"].append("--auto-exposure"),
        ),
        (
            "inherited STREHL environment",
            lambda d: d["environment"]["effective_strehl"].__setitem__(
                "STREHL_COVER", "scale"
            ),
        ),
        (
            "excess numerical threads",
            lambda d: d["environment"]["numeric_thread_caps"].__setitem__(
                "OMP_NUM_THREADS", 99
            ),
        ),
        (
            "changed source post-manifest",
            lambda d: d["source"]["post"].__setitem__("digest", "B" * 64),
        ),
        (
            "non-identical scale control",
            lambda d: d["arms"]["scale"].__setitem__("sha256", "0" * 64),
        ),
        (
            "placement refusal",
            lambda d: d["arms"]["crop"].__setitem__(
                "log", d["arms"]["crop"]["log"].replace(
                    "63 placed / 0 refused", "62 placed / 1 refused"
                )
            ),
        ),
        (
            "no crop intervention",
            lambda d: d["arms"]["crop"].__setitem__(
                "sha256", d["arms"]["scale"]["sha256"]
            ),
        ),
    )
    for name, change in mutations:
        rec.plant(name, mutant(change), "production provenance gate rejected mutant")
    swapped = {
        "PMAX_SHA256": hash_file(crop_path),
        "SCALE_SHA256": EXPECTED_SCALE_SHA256,
        "SUBJECT": "113-sharp",
    }
    rec.plant(
        "swapped frozen comparator",
        not accepted(payload, swapped),
        "live PMax rejected against incompatible frozen identity",
    )
    wrong_scale = dict(frozen)
    wrong_scale["SCALE_SHA256"] = "0" * 64
    rec.plant(
        "changed frozen scale identity",
        not accepted(payload, wrong_scale),
        "frozen scale identity is bound to the live scale control",
    )


def commission_verdicts(rec: Record) -> None:
    fixtures = (
        (
            "RECOVERED_BY_CROP",
            ("TRAILS", "UNRESOLVED", 1.03, 1.08, [1.01] * 4, False),
        ),
        (
            "PARTIAL_RECOVERY",
            ("TRAILS", "TRAILS", 1.03, 1.07, [1.01] * 4, False),
        ),
        (
            "COVER_NOT_CAUSE",
            ("TRAILS", "TRAILS", 0.99, 1.01, [0.99] * 4, True),
        ),
        (
            "CROP_DEGRADES",
            ("UNRESOLVED", "TRAILS", 0.91, 0.97, [0.95] * 4, False),
        ),
        (
            "UNRESOLVED",
            ("TRAILS", "UNRESOLVED", 1.03, 1.08, [1.01, 1.01, 0.99, 1.01], False),
        ),
    )
    for expected, arguments in fixtures:
        actual = cover_verdict(*arguments)
        rec.control(
            f"literal verdict {expected}",
            actual == expected,
            f"actual={actual}",
        )


def commission() -> int:
    rec = Record()
    caps = {
        name: int(os.environ[name])
        for name in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        )
    }
    rec.control(
        "maximum eight numerical threads",
        all(1 <= value <= 8 for value in caps.values()),
        str(caps),
    )
    x = fixture()
    commission_bins(rec)
    commission_tone(rec, x)
    commission_identity_blur_usm(rec, x)
    commission_registration(rec)
    commission_scale(rec)
    commission_crop_origin(rec)
    commission_freeze_and_coverage(rec)
    commission_schema(rec, x)
    commission_provenance(rec)
    commission_verdicts(rec)
    return rec.finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commission", action="store_true")
    parser.add_argument("--crop", type=Path)
    parser.add_argument("--scale", type=Path)
    parser.add_argument("--pmax", type=Path)
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--frozen-sites")
    parser.add_argument("frozen", nargs="?")
    args = parser.parse_args(argv)
    if args.commission:
        if any(
            (
                args.crop,
                args.scale,
                args.pmax,
                args.provenance,
                args.frozen_sites,
                args.frozen,
            )
        ):
            parser.error("--commission does not accept outcome inputs")
        return commission()
    frozen_spec = args.frozen_sites or args.frozen
    if args.frozen_sites and args.frozen:
        parser.error("give frozen sites once, as --frozen-sites or a positional path")
    if (
        args.crop is None
        or args.scale is None
        or args.pmax is None
        or args.provenance is None
        or not frozen_spec
    ):
        parser.error(
            "outcome mode requires --crop, --scale, --pmax, --provenance "
            "and frozen sites"
        )
    try:
        payload = run_outcome(
            args.crop,
            args.scale,
            args.pmax,
            frozen_spec,
            args.provenance,
        )
        code = 0
    except StopOutcome as exc:
        payload = {
            "status": "STOP",
            "reason": str(exc),
            "bands": {
                **{name: UNLICENSED for name in BAND_NAMES},
                "gt_0.25": UNLICENSED,
            },
        }
        code = 2
    except Exception as exc:
        payload = {
            "status": "ERROR",
            "reason": f"{type(exc).__name__}: {exc}",
            "bands": {
                **{name: UNLICENSED for name in BAND_NAMES},
                "gt_0.25": UNLICENSED,
            },
        }
        code = 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    sys.exit(main())
