"""Exact and geometric audit for the cover-mode default decision.

This deliberately contains no sharpness statistic.  It compares serialized
integers, evaluates similarity geometry from serialized f64 bit patterns, and
profiles absolute green-channel levels in fixed border annuli.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import tifffile


PROFILE_EDGES = (0, 2, 4, 8, 16, 32, 64, 96, 128, 160, 192, 256, 320, 384, 448, 512, 640, 768)


@dataclass(frozen=True)
class DiffStats:
    samples: int
    differing: int
    fraction_differing: float
    max_abs_dn: int
    rms_dn: float
    mean_abs_dn: float


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def diff_stats(reference: np.ndarray, candidate: np.ndarray) -> DiffStats:
    if reference.shape != candidate.shape:
        raise ValueError(f"shape mismatch: {reference.shape} != {candidate.shape}")
    d = candidate.astype(np.int64) - reference.astype(np.int64)
    ad = np.abs(d)
    differing = int(np.count_nonzero(d))
    return DiffStats(
        samples=d.size,
        differing=differing,
        fraction_differing=differing / d.size,
        max_abs_dn=int(ad.max(initial=0)),
        rms_dn=float(np.sqrt(np.mean(d.astype(np.float64) ** 2))),
        mean_abs_dn=float(np.mean(ad)),
    )


def read_tiff(path: Path) -> np.ndarray:
    a = np.asarray(tifffile.imread(path))
    if a.ndim != 3 or a.shape[2] < 3 or not np.issubdtype(a.dtype, np.integer):
        raise ValueError(f"{path}: expected integer HxWx>=3 TIFF, got {a.shape} {a.dtype}")
    return a


def command_compare(args: argparse.Namespace) -> int:
    reference = read_tiff(args.reference)
    candidate = read_tiff(args.candidate)
    h, w = candidate.shape[:2]
    x, y = args.origin
    window = reference[y : y + h, x : x + w, : candidate.shape[2]]
    if window.shape != candidate.shape:
        raise ValueError(
            f"window at ({x},{y}) has {window.shape}; candidate has {candidate.shape}"
        )
    payload = {
        "reference": str(args.reference.resolve()),
        "reference_sha256": sha256(args.reference),
        "candidate": str(args.candidate.resolve()),
        "candidate_sha256": sha256(args.candidate),
        "reference_shape": list(reference.shape),
        "candidate_shape": list(candidate.shape),
        "origin_xy": [x, y],
        **asdict(diff_stats(window, candidate)),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def f64_bits(raw: str) -> float:
    return struct.unpack(">d", bytes.fromhex(raw))[0]


@dataclass(frozen=True)
class WarpGeometry:
    path: Path
    frames: int
    width: int
    height: int
    reference: int
    placed: tuple[tuple[complex, complex], ...]


def parse_warpmap(path: Path) -> WarpGeometry:
    frames = width = height = reference = None
    placed: list[tuple[complex, complex]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == "frames":
            frames = int(fields[1])
        elif fields[0] == "plane":
            width, height = (int(x) for x in fields[1].split("x"))
        elif fields[0] == "reference":
            reference = int(fields[1])
        elif len(fields) >= 6 and fields[0].isdigit() and fields[1] == "placed":
            a = complex(f64_bits(fields[2]), f64_bits(fields[3]))
            b = complex(f64_bits(fields[4]), f64_bits(fields[5]))
            placed.append((a, b))
    if None in (frames, width, height, reference):
        raise ValueError(f"{path}: incomplete warpmap header")
    if not placed:
        raise ValueError(f"{path}: no placed frames")
    return WarpGeometry(path, frames, width, height, reference, tuple(placed))


def corners_are_covered(
    placed: Iterable[tuple[complex, complex]],
    width: int,
    height: int,
    margin: float,
    k: float,
) -> bool:
    cx, cy = width * 0.5, height * 0.5
    corners = ((0.0, 0.0), (width - 1.0, 0.0), (0.0, height - 1.0), (width - 1.0, height - 1.0))
    for a, b in placed:
        for x, y in corners:
            q = a * (k * complex(x - cx, y - cy)) + b
            sx, sy = q.real + cx, q.imag + cy
            if not (
                sx >= margin
                and sy >= margin
                and sx <= width - 1.0 - margin
                and sy <= height - 1.0 - margin
            ):
                return False
    return True


def cover_scale(
    placed: Iterable[tuple[complex, complex]],
    width: int,
    height: int,
    margin: float = 3.0,
) -> float:
    placed = tuple(placed)
    if not placed:
        raise ValueError("cover scale requires at least one placement")
    if corners_are_covered(placed, width, height, margin, 1.0):
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if corners_are_covered(placed, width, height, margin, mid):
            lo = mid
        else:
            hi = mid
    if lo <= 0.0:
        raise ValueError("no positive cover scale")
    return lo


def cover_rect(width: int, height: int, k: float) -> tuple[int, int, int, int]:
    def axis(n: int) -> tuple[int, int]:
        lo = 0.5 * n * (1.0 - k)
        hi = lo + k * (n - 1.0)
        x0 = max(0, math.ceil(lo))
        x1 = max(x0, min(n - 1, math.floor(hi)))
        return x0, x1 - x0 + 1

    x, w = axis(width)
    y, h = axis(height)
    return x, y, w, h


def command_cover_scale(args: argparse.Namespace) -> int:
    rows = []
    for path in args.warpmaps:
        geom = parse_warpmap(path)
        k = cover_scale(geom.placed, geom.width, geom.height, args.margin)
        x, y, w, h = cover_rect(geom.width, geom.height, k)
        rows.append(
            {
                "path": str(path.resolve()),
                "sha256": sha256(path),
                "frames": geom.frames,
                "placed": len(geom.placed),
                "reference": geom.reference,
                "plane": [geom.width, geom.height],
                "margin_px": args.margin,
                "k": k,
                "upsample_fraction": 1.0 / k - 1.0,
                "upsample_percent": 100.0 * (1.0 / k - 1.0),
                "crop_rect_xywh": [x, y, w, h],
                "retained_pixel_fraction": (w * h) / (geom.width * geom.height),
            }
        )
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


def distance_from_border(height: int, width: int) -> np.ndarray:
    y = np.minimum(np.arange(height), np.arange(height)[::-1])
    x = np.minimum(np.arange(width), np.arange(width)[::-1])
    return np.minimum(y[:, None], x[None, :])


def border_rows(
    bands7: np.ndarray,
    bands2: np.ndarray,
    threshold: float,
    deep_start: int,
) -> tuple[list[dict[str, float | int]], int | None, float]:
    if bands7.shape != bands2.shape:
        raise ValueError(f"shape mismatch: {bands7.shape} != {bands2.shape}")
    if bands7.ndim != 2:
        raise ValueError(f"border profile expects two 2-D planes, got {bands7.shape}")
    dist = distance_from_border(*bands7.shape)
    deep = dist >= deep_start
    if not np.any(deep):
        raise ValueError(f"no pixels reach deep-start={deep_start} in {bands7.shape}")
    deep_ratio = float(np.mean(bands7[deep], dtype=np.float64) / np.mean(bands2[deep], dtype=np.float64))
    max_distance = int(dist.max())
    edges = [x for x in PROFILE_EDGES if x <= max_distance]
    if not edges or edges[0] != 0:
        edges.insert(0, 0)
    rows: list[dict[str, float | int]] = []
    for i, lo in enumerate(edges):
        hi = edges[i + 1] if i + 1 < len(edges) else max_distance + 1
        mask = (dist >= lo) & (dist < hi)
        if not np.any(mask):
            continue
        mean7 = float(np.mean(bands7[mask], dtype=np.float64))
        mean2 = float(np.mean(bands2[mask], dtype=np.float64))
        ratio = mean7 / mean2
        rows.append(
            {
                "lo": lo,
                "hi": hi,
                "samples": int(np.count_nonzero(mask)),
                "mean_bands7": mean7,
                "mean_bands2": mean2,
                "ratio": ratio,
                "normalised_effect": ratio / deep_ratio - 1.0,
            }
        )
    safe = None
    for row in rows:
        candidate = int(row["lo"])
        if candidate < 8:
            continue
        tail = [r for r in rows if int(r["lo"]) >= candidate]
        if tail and all(abs(float(r["normalised_effect"])) <= threshold for r in tail):
            safe = candidate
            break
    return rows, safe, deep_ratio


def command_border(args: argparse.Namespace) -> int:
    a = read_tiff(args.bands7)
    b = read_tiff(args.bands2)
    rows, safe, deep_ratio = border_rows(
        a[..., 1].astype(np.float64),
        b[..., 1].astype(np.float64),
        args.threshold,
        args.deep_start,
    )
    payload = {
        "bands7": str(args.bands7.resolve()),
        "bands7_sha256": sha256(args.bands7),
        "bands2": str(args.bands2.resolve()),
        "bands2_sha256": sha256(args.bands2),
        "shape": list(a.shape),
        "threshold": args.threshold,
        "deep_start": args.deep_start,
        "deep_ratio": deep_ratio,
        "safe_inset_px": safe,
        "rows": rows,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def identity_closed_form(width: int, height: int, margin: float) -> float:
    candidates = [1.0]
    for n in (width, height):
        c = n * 0.5
        candidates.extend(((c - margin) / c, (n - 1.0 - margin - c) / (n - 1.0 - c)))
    return min(candidates)


def command_commission(_: argparse.Namespace) -> int:
    shape = (48, 64, 3)
    y, x, c = np.indices(shape)
    base = (1000 + 17 * x + 31 * y + 101 * c).astype(np.uint16)
    n = base.size

    defect = base.copy()
    defect[7, 11, 2] += 4096
    bad = diff_stats(base, defect)
    assert bad.max_abs_dn == 4096
    assert bad.differing == 1
    assert bad.fraction_differing == 1.0 / n
    assert abs(bad.rms_dn - 4096.0 / math.sqrt(n)) < 1e-12

    improved = base.copy()
    improved[7, 11, 2] += 1024
    better = diff_stats(base, improved)
    restored = diff_stats(base, base.copy())
    assert better.max_abs_dn < bad.max_abs_dn
    assert better.rms_dn < bad.rms_dn
    assert restored.max_abs_dn == 0 and restored.rms_dn == 0 and restored.differing == 0

    full = np.arange(30 * 40 * 3, dtype=np.uint16).reshape(30, 40, 3)
    crop = full[5:25, 7:31].copy()
    right = diff_stats(full[5:25, 7:31], crop)
    origin_mutants = {}
    for name, (dx, dy) in {
        "left": (-1, 0),
        "right": (1, 0),
        "up": (0, -1),
        "down": (0, 1),
    }.items():
        got = diff_stats(full[5 + dy : 25 + dy, 7 + dx : 31 + dx], crop)
        assert got.differing > 0 and got.max_abs_dn > 0 and got.rms_dn > right.rms_dn
        origin_mutants[name] = asdict(got)
    assert right.differing == 0

    yy, xx = np.indices((96, 128))
    border_base = (10000.0 + xx + 2.0 * yy).astype(np.float64)
    dist = distance_from_border(*border_base.shape)
    planted = border_base.copy()
    planted[dist < 16] *= 1.02
    rows, safe, deep = border_rows(planted, border_base, 0.001, 32)
    assert safe == 16
    outer = next(r for r in rows if r["lo"] == 0)
    assert abs(float(outer["normalised_effect"]) - 0.02) < 1e-12
    small = border_base.copy()
    small[dist < 16] *= 1.0005
    _, small_safe, _ = border_rows(small, border_base, 0.001, 32)
    _, null_safe, null_deep = border_rows(border_base, border_base, 0.001, 32)
    assert small_safe == 8 and null_safe == 8
    assert abs(null_deep - 1.0) < 1e-15

    width, height, margin = 3516, 2344, 3.0
    identity = ((complex(1.0, 0.0), complex(0.0, 0.0)),)
    k = cover_scale(identity, width, height, margin)
    expected = identity_closed_form(width, height, margin)
    assert abs(k - expected) <= 2e-15
    k_better = cover_scale(identity, width, height, 0.0)
    assert k_better == 1.0 and k_better > k

    print(
        json.dumps(
            {
                "status": "COMMISSIONED",
                "known_defect": asdict(bad),
                "improved_defect": asdict(better),
                "restored": asdict(restored),
                "correct_origin": asdict(right),
                "origin_mutants": origin_mutants,
                "border_2pct_safe_inset_px": safe,
                "border_0_05pct_safe_inset_px": small_safe,
                "border_null_safe_inset_px": null_safe,
                "identity_k": k,
                "identity_closed_form_k": expected,
                "identity_zero_margin_improvement_k": k_better,
                "border_deep_ratio": deep,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("commission")
    q.set_defaults(run=command_commission)

    q = sub.add_parser("compare")
    q.add_argument("reference", type=Path)
    q.add_argument("candidate", type=Path)
    q.add_argument("--origin", nargs=2, type=int, metavar=("X", "Y"), default=(0, 0))
    q.set_defaults(run=command_compare)

    q = sub.add_parser("cover-scale")
    q.add_argument("warpmaps", nargs="+", type=Path)
    q.add_argument("--margin", type=float, default=3.0)
    q.set_defaults(run=command_cover_scale)

    q = sub.add_parser("border")
    q.add_argument("bands7", type=Path)
    q.add_argument("bands2", type=Path)
    q.add_argument("--threshold", type=float, default=0.001)
    q.add_argument("--deep-start", type=int, default=768)
    q.set_defaults(run=command_border)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
