"""Independent M8 source-support hull checker.

The producer supplies only source-plane values, exact placement coefficients,
and raw gathered f32 values.  This file reconstructs coordinates, validity,
discrete support, hulls, tolerances, and verdicts without importing Strehl.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np
import tifffile


MAGIC = b"M8SITE01"
VERSION = 2
HEADER = struct.Struct("<8s9I6d2fI")
KERNELS = {0: "catmull-rom", 1: "bilinear"}
SITE_NAMES = {(0, 0): "R", (1, 0): "G1", (0, 1): "G2", (1, 1): "B"}
SITE_CHANNEL = {(0, 0): 0, (1, 0): 1, (0, 1): 1, (1, 1): 2}
CHUNK_ROWS = 64
U16_QUANT_TOL = 0.5 / 65535.0
R_VIOLATION_DTYPE = np.dtype(
    [
        ("y", "<u2"),
        ("x", "<u2"),
        ("direction", "i1"),
        ("value", "<f4"),
        ("lo", "<f4"),
        ("hi", "<f4"),
        ("tau", "<f4"),
        ("signed_excess", "<f4"),
    ]
)
O_VIOLATION_DTYPE = np.dtype(
    [
        ("y", "<u2"),
        ("x", "<u2"),
        ("channel", "u1"),
        ("direction", "i1"),
        ("encoded", "<u2"),
        ("lo", "<f4"),
        ("hi", "<f4"),
        ("tolerance", "<f4"),
        ("signed_excess", "<f4"),
    ]
)


@dataclass(frozen=True)
class Block:
    path: Path
    kernel: int
    src_w: int
    src_h: int
    dst_w: int
    dst_h: int
    site_x: int
    site_y: int
    channel: int
    a_re: float
    a_im: float
    b_re: float
    b_im: float
    cx: float
    cy: float
    value_range: float
    site_gain: float
    frame: str
    source_offset: int
    trace_offset: int

    @property
    def site(self) -> str:
        return SITE_NAMES[(self.site_x, self.site_y)]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def read_block(path: Path) -> Block:
    with path.open("rb") as f:
        raw = f.read(HEADER.size)
        if len(raw) != HEADER.size:
            raise ValueError(f"{path}: truncated M8 header")
        (
            magic,
            version,
            kernel,
            src_w,
            src_h,
            dst_w,
            dst_h,
            site_x,
            site_y,
            channel,
            a_re,
            a_im,
            b_re,
            b_im,
            cx,
            cy,
            value_range,
            site_gain,
            frame_len,
        ) = HEADER.unpack(raw)
        if magic != MAGIC or version != VERSION:
            raise ValueError(f"{path}: unsupported M8 protocol {magic!r} v{version}")
        if kernel not in KERNELS:
            raise ValueError(f"{path}: unknown kernel {kernel}")
        if (site_x, site_y) not in SITE_NAMES:
            raise ValueError(f"{path}: invalid CFA site {(site_x, site_y)}")
        if SITE_CHANNEL[(site_x, site_y)] != channel:
            raise ValueError(
                f"{path}: site {(site_x, site_y)} says channel {channel}, "
                f"expected {SITE_CHANNEL[(site_x, site_y)]}"
            )
        frame_raw = f.read(frame_len)
        if len(frame_raw) != frame_len:
            raise ValueError(f"{path}: truncated frame path")
        frame = frame_raw.decode("utf-8")
        source_offset = HEADER.size + frame_len
        trace_offset = source_offset + 4 * src_w * src_h
        expected = trace_offset + 4 * dst_w * dst_h
        actual = path.stat().st_size
        if actual != expected:
            raise ValueError(f"{path}: expected {expected} bytes, found {actual}")
        if not (math.isfinite(value_range) and value_range > 0.0):
            raise ValueError(f"{path}: invalid linear range {value_range}")
        if not (math.isfinite(site_gain) and site_gain > 0.0):
            raise ValueError(f"{path}: invalid site gain {site_gain}")
    return Block(
        path,
        kernel,
        src_w,
        src_h,
        dst_w,
        dst_h,
        site_x,
        site_y,
        channel,
        a_re,
        a_im,
        b_re,
        b_im,
        cx,
        cy,
        value_range,
        site_gain,
        frame,
        source_offset,
        trace_offset,
    )


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".new")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_meta(state: Path) -> dict | None:
    path = state / "meta.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def initialise_state(state: Path, capture: str, b: Block) -> dict:
    state.mkdir(parents=True, exist_ok=True)
    shape = (3, b.dst_h, b.dst_w)
    lo = np.lib.format.open_memmap(
        state / "o-lo.npy", mode="w+", dtype="<f4", shape=shape
    )
    hi = np.lib.format.open_memmap(
        state / "o-hi.npy", mode="w+", dtype="<f4", shape=shape
    )
    tau = np.lib.format.open_memmap(
        state / "o-tau.npy", mode="w+", dtype="<f4", shape=shape
    )
    lo[:] = np.float32(np.inf)
    hi[:] = np.float32(-np.inf)
    tau[:] = np.float32(0.0)
    lo.flush()
    hi.flush()
    tau.flush()
    del lo, hi, tau
    meta = {
        "protocol": VERSION,
        "capture": capture,
        "width": b.dst_w,
        "height": b.dst_h,
        "source_width": b.src_w,
        "source_height": b.src_h,
        "range": b.value_range,
        "output_gains": [None, None, None],
        "sites": {},
    }
    atomic_json(state / "meta.json", meta)
    return meta


def validate_state(meta: dict, capture: str, b: Block) -> None:
    expected = {
        "capture": capture,
        "width": b.dst_w,
        "height": b.dst_h,
        "source_width": b.src_w,
        "source_height": b.src_h,
    }
    for key, value in expected.items():
        if meta.get(key) != value:
            raise ValueError(
                f"state {key}={meta.get(key)!r}, block requires {value!r}"
            )
    if np.float32(meta["range"]).tobytes() != np.float32(b.value_range).tobytes():
        raise ValueError(f"state range {meta['range']} != block range {b.value_range}")


def row_coordinates(b: Block, y0: int, y1: int) -> tuple[np.ndarray, np.ndarray]:
    ox = 0.5 * b.site_x
    oy = 0.5 * b.site_y
    x = np.arange(b.dst_w, dtype=np.float64)[None, :] + ox
    y = np.arange(y0, y1, dtype=np.float64)[:, None] + oy
    xr = x - b.cx
    yr = y - b.cy
    sx = 2.0 * (b.a_re * xr - b.a_im * yr + b.b_re + b.cx)
    sy = 2.0 * (b.a_re * yr + b.a_im * xr + b.b_im + b.cy)
    return sx, sy


def support_spec(kernel: int) -> tuple[float, tuple[int, ...]]:
    if kernel == 0:
        return 2.0, (-1, 0, 1, 2)
    if kernel == 1:
        return 1.0, (0, 1)
    raise AssertionError(kernel)


def exact_support(
    source: np.ndarray, b: Block, sx: np.ndarray, sy: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    support, offsets = support_spec(b.kernel)
    valid = (
        (sx >= support - 0.5)
        & (sy >= support - 0.5)
        & (sx <= b.src_w - 0.5 - support)
        & (sy <= b.src_h - 0.5 - support)
    )
    ix = np.floor(sx).astype(np.intp)
    iy = np.floor(sy).astype(np.intp)
    low_index = 1 if b.kernel == 0 else 0
    high_x = b.src_w - (3 if b.kernel == 0 else 2)
    high_y = b.src_h - (3 if b.kernel == 0 else 2)
    np.clip(ix, low_index, high_x, out=ix)
    np.clip(iy, low_index, high_y, out=iy)
    lo = np.full(sx.shape, np.float32(np.inf), dtype=np.float32)
    hi = np.full(sx.shape, np.float32(-np.inf), dtype=np.float32)
    for dy in offsets:
        for dx in offsets:
            values = np.asarray(source[iy + dy, ix + dx], dtype=np.float32)
            np.minimum(lo, values, out=lo)
            np.maximum(hi, values, out=hi)
    return valid, lo, hi


def tau_r(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    z = np.maximum(np.float32(1.0), np.maximum(np.abs(lo), np.abs(hi)))
    z = np.asarray(z, dtype=np.float32)
    ulp = np.nextafter(z, np.float32(np.inf)) - z
    return np.asarray(np.float32(8.0) * ulp, dtype=np.float32)


def is_integer_identity(b: Block) -> bool:
    return (
        b.a_re == 1.0
        and b.a_im == 0.0
        and b.b_re == 0.0
        and b.b_im == 0.0
    )


def violation_rows(
    y0: int,
    value: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    tau: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> np.ndarray:
    mask = lower | upper
    yy, xx = np.nonzero(mask)
    out = np.empty(len(xx), dtype=R_VIOLATION_DTYPE)
    out["y"] = yy + y0
    out["x"] = xx
    out["direction"] = np.where(upper[mask], 1, -1)
    out["value"] = value[mask]
    out["lo"] = lo[mask]
    out["hi"] = hi[mask]
    out["tau"] = tau[mask]
    out["signed_excess"] = np.where(
        upper[mask], value[mask] - hi[mask], value[mask] - lo[mask]
    )
    return out


def consume(block_path: Path, state: Path, capture: str) -> dict:
    b = read_block(block_path)
    meta = load_meta(state)
    if meta is None:
        meta = initialise_state(state, capture, b)
    validate_state(meta, capture, b)
    frame_name = Path(b.frame).name
    site_key = f"{frame_name}|{b.site}"
    if site_key in meta["sites"]:
        raise RuntimeError(f"{site_key}: duplicate trace block")
    if meta["output_gains"][b.channel] is None:
        meta["output_gains"][b.channel] = b.site_gain
    output_gain = float(meta["output_gains"][b.channel])

    source = np.memmap(
        block_path,
        mode="r",
        dtype="<f4",
        offset=b.source_offset,
        shape=(b.src_h, b.src_w),
    )
    trace = np.memmap(
        block_path,
        mode="r",
        dtype="<f4",
        offset=b.trace_offset,
        shape=(b.dst_h, b.dst_w),
    )
    o_lo = np.load(state / "o-lo.npy", mmap_mode="r+")
    o_hi = np.load(state / "o-hi.npy", mmap_mode="r+")
    o_tau = np.load(state / "o-tau.npy", mmap_mode="r+")

    denominator = lower_count = upper_count = 0
    max_upper = 0.0
    min_lower = 0.0
    coverage_mismatch = 0
    copy_denominator = copy_violations = 0
    copy_max_abs = 0.0
    violation_parts: list[np.ndarray] = []
    output_scale = np.float32(output_gain / b.site_gain / b.value_range)

    for y0 in range(0, b.dst_h, CHUNK_ROWS):
        y1 = min(b.dst_h, y0 + CHUNK_ROWS)
        sx, sy = row_coordinates(b, y0, y1)
        valid, lo, hi = exact_support(source, b, sx, sy)
        values = np.asarray(trace[y0:y1], dtype=np.float32)
        finite = np.isfinite(values)
        mismatch = finite ^ valid
        coverage_mismatch += int(np.count_nonzero(mismatch))
        if np.any(mismatch):
            yy, xx = np.argwhere(mismatch)[0]
            raise RuntimeError(
                f"{site_key}: independently reconstructed validity differs from "
                f"trace at ({int(xx)},{int(yy + y0)})"
            )
        tau = tau_r(lo, hi)
        lower = valid & (values < lo - tau)
        upper = valid & (values > hi + tau)
        denominator += int(np.count_nonzero(valid))
        lower_count += int(np.count_nonzero(lower))
        upper_count += int(np.count_nonzero(upper))
        if np.any(upper):
            max_upper = max(
                max_upper, float(np.max(values[upper] - hi[upper], initial=0.0))
            )
        if np.any(lower):
            min_lower = min(
                min_lower, float(np.min(values[lower] - lo[lower], initial=0.0))
            )
        if np.any(lower | upper):
            violation_parts.append(
                violation_rows(y0, values, lo, hi, tau, lower, upper)
            )

        if is_integer_identity(b):
            xi = np.rint(sx).astype(np.intp)
            yi = np.rint(sy).astype(np.intp)
            xi = np.clip(xi, 0, b.src_w - 1)
            yi = np.clip(yi, 0, b.src_h - 1)
            copied = np.asarray(source[yi, xi], dtype=np.float32)
            copy_tau = tau_r(copied, copied)
            delta = np.abs(values - copied)
            copy_denominator += int(np.count_nonzero(valid))
            copy_violations += int(np.count_nonzero(valid & (delta > copy_tau)))
            if np.any(valid):
                copy_max_abs = max(copy_max_abs, float(np.max(delta[valid], initial=0.0)))

        lo_norm = np.asarray(lo * output_scale, dtype=np.float32)
        hi_norm = np.asarray(hi * output_scale, dtype=np.float32)
        tau_norm = np.asarray(tau * output_scale, dtype=np.float32)
        lo_view = o_lo[b.channel, y0:y1]
        hi_view = o_hi[b.channel, y0:y1]
        tau_view = o_tau[b.channel, y0:y1]
        np.minimum(lo_view, np.where(valid, lo_norm, np.float32(np.inf)), out=lo_view)
        np.maximum(
            hi_view, np.where(valid, hi_norm, np.float32(-np.inf)), out=hi_view
        )
        np.maximum(
            tau_view, np.where(valid, tau_norm, np.float32(0.0)), out=tau_view
        )

    o_lo.flush()
    o_hi.flush()
    o_tau.flush()
    violations = (
        np.concatenate(violation_parts)
        if violation_parts
        else np.empty(0, dtype=R_VIOLATION_DTYPE)
    )
    violation_dir = state / "r-violations"
    violation_dir.mkdir(exist_ok=True)
    violation_path = violation_dir / f"{Path(frame_name).stem}-{b.site}.npy"
    np.save(violation_path, violations, allow_pickle=False)
    summary = {
        "frame": frame_name,
        "frame_path": b.frame,
        "site": b.site,
        "channel": b.channel,
        "site_gain": b.site_gain,
        "output_gain": output_gain,
        "output_scale": float(output_scale),
        "kernel": KERNELS[b.kernel],
        "denominator": denominator,
        "violations": lower_count + upper_count,
        "lower_violations": lower_count,
        "upper_violations": upper_count,
        "fraction": (lower_count + upper_count) / denominator if denominator else None,
        "max_upper_signed_excess": max_upper,
        "min_lower_signed_excess": min_lower,
        "max_abs_signed_excess": max(max_upper, abs(min_lower)),
        "coverage_mismatches": coverage_mismatch,
        "copy_denominator": copy_denominator,
        "copy_violations": copy_violations,
        "copy_max_abs": copy_max_abs,
        "violations_file": str(violation_path.resolve()),
        "violations_sha256": sha256(violation_path),
    }
    meta["sites"][site_key] = summary
    atomic_json(state / "meta.json", meta)
    del source, trace, o_lo, o_hi, o_tau
    print(json.dumps(summary, sort_keys=True))
    return summary


def aggregate_r(state: Path) -> dict:
    meta = load_meta(state)
    if meta is None or not meta["sites"]:
        raise RuntimeError(f"{state}: no consumed sites")
    rows = list(meta["sites"].values())
    denominator = sum(r["denominator"] for r in rows)
    violations = sum(r["violations"] for r in rows)
    lower = sum(r["lower_violations"] for r in rows)
    upper = sum(r["upper_violations"] for r in rows)
    copy_denominator = sum(r["copy_denominator"] for r in rows)
    copy_violations = sum(r["copy_violations"] for r in rows)
    frames: dict[str, list[str]] = {}
    for r in rows:
        frames.setdefault(r["frame"], []).append(r["site"])
    payload = {
        "capture": meta["capture"],
        "frames": len(frames),
        "sites": len(rows),
        "frame_sites": {k: sorted(v) for k, v in sorted(frames.items())},
        "denominator": denominator,
        "violations": violations,
        "lower_violations": lower,
        "upper_violations": upper,
        "fraction": violations / denominator,
        "percent": 100.0 * violations / denominator,
        "max_upper_signed_excess": max(r["max_upper_signed_excess"] for r in rows),
        "min_lower_signed_excess": min(r["min_lower_signed_excess"] for r in rows),
        "max_abs_signed_excess": max(r["max_abs_signed_excess"] for r in rows),
        "coverage_mismatches": sum(r["coverage_mismatches"] for r in rows),
        "copy_denominator": copy_denominator,
        "copy_violations": copy_violations,
        "copy_fraction": (
            copy_violations / copy_denominator if copy_denominator else None
        ),
        "copy_max_abs": max(r["copy_max_abs"] for r in rows),
        "violation_manifests": [
            {
                "frame": r["frame"],
                "site": r["site"],
                "count": r["violations"],
                "path": r["violations_file"],
                "sha256": r["violations_sha256"],
            }
            for r in rows
            if r["violations"]
        ],
    }
    atomic_json(state / "m8-r.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def o_violation_rows(
    y0: int,
    channel: int,
    encoded: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    tolerance: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> np.ndarray:
    mask = lower | upper
    yy, xx = np.nonzero(mask)
    values = encoded.astype(np.float64) / 65535.0
    out = np.empty(len(xx), dtype=O_VIOLATION_DTYPE)
    out["y"] = yy + y0
    out["x"] = xx
    out["channel"] = channel
    out["direction"] = np.where(upper[mask], 1, -1)
    out["encoded"] = encoded[mask]
    out["lo"] = lo[mask]
    out["hi"] = hi[mask]
    out["tolerance"] = tolerance[mask]
    out["signed_excess"] = np.where(
        upper[mask], values[mask] - hi[mask], values[mask] - lo[mask]
    )
    return out


def final_output(state: Path, tiff_path: Path) -> dict:
    meta = load_meta(state)
    if meta is None:
        raise RuntimeError(f"{state}: no state")
    image = np.asarray(tifffile.imread(tiff_path))
    expected = (meta["height"], meta["width"], 3)
    if image.shape != expected or image.dtype != np.uint16:
        raise ValueError(
            f"{tiff_path}: expected uint16 {expected}, got {image.dtype} {image.shape}"
        )
    if any(g is None for g in meta["output_gains"]):
        raise RuntimeError(
            f"{meta['capture']}: final output gains are incomplete: "
            f"{meta['output_gains']}"
        )
    lo_all = np.load(state / "o-lo.npy", mmap_mode="r")
    hi_all = np.load(state / "o-hi.npy", mmap_mode="r")
    tau_all = np.load(state / "o-tau.npy", mmap_mode="r")
    denominator = lower_count = upper_count = 0
    unbracketed = 0
    max_upper = 0.0
    min_lower = 0.0
    parts: list[np.ndarray] = []
    for channel in range(3):
        for y0 in range(0, meta["height"], CHUNK_ROWS):
            y1 = min(meta["height"], y0 + CHUNK_ROWS)
            lo = np.asarray(lo_all[channel, y0:y1], dtype=np.float64)
            hi = np.asarray(hi_all[channel, y0:y1], dtype=np.float64)
            tau = np.asarray(tau_all[channel, y0:y1], dtype=np.float64)
            bracketed = np.isfinite(lo) & np.isfinite(hi)
            unbracketed += int(np.count_nonzero(~bracketed))
            encoded = np.asarray(image[y0:y1, :, channel], dtype=np.uint16)
            values = encoded.astype(np.float64) / 65535.0
            tolerance = tau + U16_QUANT_TOL
            lower = bracketed & (values < lo - tolerance)
            upper = bracketed & (values > hi + tolerance)
            denominator += int(np.count_nonzero(bracketed))
            lower_count += int(np.count_nonzero(lower))
            upper_count += int(np.count_nonzero(upper))
            if np.any(upper):
                max_upper = max(
                    max_upper, float(np.max(values[upper] - hi[upper], initial=0.0))
                )
            if np.any(lower):
                min_lower = min(
                    min_lower, float(np.min(values[lower] - lo[lower], initial=0.0))
                )
            if np.any(lower | upper):
                parts.append(
                    o_violation_rows(
                        y0,
                        channel,
                        encoded,
                        lo,
                        hi,
                        tolerance,
                        lower,
                        upper,
                    )
                )
    if unbracketed:
        raise RuntimeError(
            f"{meta['capture']}: {unbracketed} output samples have no valid-frame hull"
        )
    violations = (
        np.concatenate(parts)
        if parts
        else np.empty(0, dtype=O_VIOLATION_DTYPE)
    )
    violation_path = state / "m8-o-violations.npy"
    np.save(violation_path, violations, allow_pickle=False)
    count = lower_count + upper_count
    payload = {
        "capture": meta["capture"],
        "tiff": str(tiff_path.resolve()),
        "tiff_sha256": sha256(tiff_path),
        "denominator": denominator,
        "violations": count,
        "lower_violations": lower_count,
        "upper_violations": upper_count,
        "fraction": count / denominator,
        "percent": 100.0 * count / denominator,
        "max_upper_signed_excess_linear": max_upper,
        "min_lower_signed_excess_linear": min_lower,
        "max_abs_signed_excess_linear": max(max_upper, abs(min_lower)),
        "max_abs_signed_excess_u16_lsb": max(max_upper, abs(min_lower)) * 65535.0,
        "quantisation_tolerance": U16_QUANT_TOL,
        "unbracketed_samples": unbracketed,
        "violations_file": str(violation_path.resolve()),
        "violations_sha256": sha256(violation_path),
        "clamping_caveat": (
            "Final clamping can erase M8-O evidence; a zero M8-O count is not "
            "a pass without the pre-clamp M8-R census."
        ),
    }
    atomic_json(state / "m8-o.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def commission_assert(root: Path) -> dict:
    arms = {}
    for name in [
        "catmull-hard-step",
        "copy-null",
        "bilinear-null",
        "explicit-hi-lo-plant",
    ]:
        arms[name] = json.loads(
            (root / name / "m8-r.json").read_text(encoding="utf-8")
        )
    checks = {
        "catmull_red": arms["catmull-hard-step"]["violations"] >= 1,
        "copy_green": arms["copy-null"]["violations"] == 0,
        "copy_exact": arms["copy-null"]["copy_violations"] == 0
        and arms["copy-null"]["copy_denominator"] > 0,
        "bilinear_green": arms["bilinear-null"]["violations"] == 0,
        "hi_lo_both_found": arms["explicit-hi-lo-plant"]["violations"] == 2
        and arms["explicit-hi-lo-plant"]["upper_violations"] == 1
        and arms["explicit-hi-lo-plant"]["lower_violations"] == 1,
    }
    payload = {"checks": checks, "arms": arms, "passed": all(checks.values())}
    atomic_json(root / "commission.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload["passed"]:
        return 1
    return 0


def independence() -> int:
    path = Path(__file__).resolve()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    forbidden = sorted(x for x in imports if x.lower().startswith("strehl"))
    payload = {
        "checker": str(path),
        "sha256": sha256(path),
        "imports": sorted(imports),
        "forbidden_strehl_imports": forbidden,
        "independent": not forbidden,
        "coordinate_reconstruction_function": "row_coordinates",
        "support_reconstruction_function": "exact_support",
        "tolerance_function": "tau_r",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not forbidden else 1


def iter_blocks(path: Path) -> Iterator[Path]:
    yield from sorted(path.glob("*.m8site"))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("consume")
    p.add_argument("--block", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--capture", required=True)

    p = sub.add_parser("finalize-r")
    p.add_argument("--state", type=Path, required=True)

    p = sub.add_parser("final")
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--tiff", type=Path, required=True)

    p = sub.add_parser("commission-assert")
    p.add_argument("--root", type=Path, required=True)

    sub.add_parser("independence")

    args = ap.parse_args()
    if args.command == "consume":
        consume(args.block, args.state, args.capture)
        return 0
    if args.command == "finalize-r":
        aggregate_r(args.state)
        return 0
    if args.command == "final":
        final_output(args.state, args.tiff)
        return 0
    if args.command == "commission-assert":
        return commission_assert(args.root)
    if args.command == "independence":
        return independence()
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
