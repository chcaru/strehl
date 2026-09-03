"""Decode the registered real captures once and freeze block sufficient stats.

No verdict is computed here.  All files are read-only inputs; every generated
cache and inventory lands below this lane's ``out`` directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
CACHE = OUT / "cache"
sys.path.insert(0, str(HERE))
import astiglib as A  # noqa: E402


REQUESTS = Path(r"D:\personal\macro\requests")
LINEAR_WHITE = 15360
CLIP_FLOOR = LINEAR_WHITE - 16


@dataclass(frozen=True)
class Stack:
    name: str
    path: str
    role: str
    setup: str
    step_width: int
    aperture: float
    expected_frames: int


STACKS = (
    Stack(
        "grid1-sw1",
        str(REQUESTS / "30-calibration-grid" / "calibration-grid-1-sw1-cpl"),
        "grid",
        "grid1",
        1,
        5.6,
        91,
    ),
    Stack(
        "grid1-sw4",
        str(REQUESTS / "30-calibration-grid" / "calibration-grid-1-sw4-cpl"),
        "grid",
        "grid1",
        4,
        5.6,
        55,
    ),
    Stack(
        "grid1-sw10",
        str(REQUESTS / "30-calibration-grid" / "calibration-grid-1-sw10-cpl"),
        "grid",
        "grid1",
        10,
        5.6,
        23,
    ),
    Stack(
        "grid2-sw4",
        str(REQUESTS / "30-calibration-grid" / "calibration-grid-2-sw4-cpl"),
        "grid",
        "grid2",
        4,
        5.6,
        46,
    ),
    Stack(
        "grid2-sw10",
        str(REQUESTS / "30-calibration-grid" / "calibration-grid-2-sw10-cpl"),
        "grid",
        "grid2",
        10,
        5.6,
        27,
    ),
    Stack(
        "fabric-f5.6",
        str(REQUESTS / "7-aperture-pairs" / "fabric-weave-f5.6-sw5-cpl"),
        "aperture",
        "fabric",
        5,
        5.6,
        210,
    ),
    Stack(
        "fabric-f8",
        str(REQUESTS / "7-aperture-pairs" / "fabric-weave-f8-sw5-cpl"),
        "aperture",
        "fabric",
        5,
        8.0,
        150,
    ),
    Stack(
        "fabric-f11",
        str(REQUESTS / "7-aperture-pairs" / "fabric-weave-f11-sw5-cpl"),
        "aperture",
        "fabric",
        5,
        11.0,
        109,
    ),
    Stack(
        "fabric-f14",
        str(REQUESTS / "7-aperture-pairs" / "fabric-weave-f14-sw5-cpl"),
        "aperture",
        "fabric",
        5,
        14.0,
        83,
    ),
    Stack(
        "fabric-f18",
        str(REQUESTS / "7-aperture-pairs" / "fabric-weave-f18-sw5-cpl"),
        "aperture",
        "fabric",
        5,
        18.0,
        71,
    ),
    Stack(
        "razor-flat-f8",
        str(
            REQUESTS
            / "19-razor-edge"
            / "horizontal-flat"
            / "razor-edge-horizontal-flat-sw4-f8-cpl"
        ),
        "flat-control",
        "razor",
        4,
        8.0,
        50,
    ),
)


VARIANTS = {
    "primary": {"tile_size": 192, "block_grid": 4, "channel": "luma", "xshift": 0},
    "tile128": {"tile_size": 128, "block_grid": 4, "channel": "luma", "xshift": 0},
    "tile256": {"tile_size": 256, "block_grid": 4, "channel": "luma", "xshift": 0},
    "g1": {"tile_size": 192, "block_grid": 4, "channel": "g1", "xshift": 0},
    "g2": {"tile_size": 192, "block_grid": 4, "channel": "g2", "xshift": 0},
    "block3": {"tile_size": 192, "block_grid": 3, "channel": "luma", "xshift": 0},
    "block5": {"tile_size": 192, "block_grid": 5, "channel": "luma", "xshift": 0},
    "xminus2": {"tile_size": 192, "block_grid": 4, "channel": "luma", "xshift": -2},
    "xplus2": {"tile_size": 192, "block_grid": 4, "channel": "luma", "xshift": 2},
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_snapshot(stacks: tuple[Stack, ...]) -> dict:
    records = []
    for stack in stacks:
        path = Path(stack.path)
        files = sorted(path.glob("*.ARW"))
        records.append(
            {
                "stack": stack.name,
                "path": stack.path,
                "count": len(files),
                "bytes": int(sum(p.stat().st_size for p in files)),
                "newest_mtime_ns": max((p.stat().st_mtime_ns for p in files), default=0),
            }
        )
    return {"records": records}


def centres_for(stack: Stack, height: int, width: int, tile_size: int) -> list[dict]:
    if stack.role == "flat-control":
        # Fixed from M128's reported silhouette near green row 1112: this point
        # is 588 rows below it, on the texture-poor dark background.
        return [
            {
                "sector": "centre",
                "radius": 0.0,
                "cy": 1700,
                "cx": width // 2,
            }
        ]
    return A.fixed_tile_centres(height, width, tile_size)


def green_patch(
    visible: np.ndarray,
    centre: dict,
    tile_size: int,
    channel: str,
    black: tuple[float, float],
    xshift: int,
) -> tuple[np.ndarray, float]:
    half = tile_size // 2
    cy = int(centre["cy"])
    cx = int(centre["cx"]) + xshift
    y0, y1 = cy - half, cy + half
    x0, x1 = cx - half, cx + half
    raw = visible[2 * y0 : 2 * y1, 2 * x0 : 2 * x1]
    if raw.shape != (2 * tile_size, 2 * tile_size):
        raise ValueError(f"tile outside visible array: {raw.shape}")
    # Copy/convert while rawpy's owner is alive (AGENTS rule 32).
    g1 = np.array(raw[0::2, 1::2], dtype=np.float64, copy=True) - black[0]
    g2 = np.array(raw[1::2, 0::2], dtype=np.float64, copy=True) - black[1]
    clipped = float(
        np.mean(
            np.logical_or(
                raw[0::2, 1::2] >= CLIP_FLOOR,
                raw[1::2, 0::2] >= CLIP_FLOOR,
            )
        )
    )
    if channel == "luma":
        return (g1 + g2) / 2.0, clipped
    if channel == "g1":
        return g1, clipped
    if channel == "g2":
        return g2, clipped
    raise ValueError(f"unknown channel {channel}")


def frame_job(args) -> tuple[dict, dict, dict]:
    path_text, stack_dict = args
    stack = Stack(**stack_dict)
    path = Path(path_text)
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible
        pattern = (
            None if raw.raw_pattern is None else np.array(raw.raw_pattern, copy=True).tolist()
        )
        desc = bytes(raw.color_desc).decode("ascii", "replace").rstrip("\x00")
        metadata = {
            "shape": list(visible.shape),
            "dtype": str(visible.dtype),
            "pattern": pattern,
            "color_desc": desc,
            "black_levels": [float(x) for x in raw.black_level_per_channel],
            "container_white": float(raw.white_level),
        }
        if metadata != {
            "shape": [4688, 7028],
            "dtype": "uint16",
            "pattern": [[0, 1], [3, 2]],
            "color_desc": "RGBG",
            "black_levels": [512.0, 512.0, 512.0, 512.0],
            "container_white": 16383.0,
        }:
            raise ValueError(f"{path}: loader contract changed: {metadata}")
        height, width = visible.shape[0] // 2, visible.shape[1] // 2
        by_variant = {}
        clip_by_variant = {}
        wanted = ("primary",) if stack.role == "flat-control" else tuple(VARIANTS)
        for name in wanted:
            cfg = VARIANTS[name]
            centres = centres_for(stack, height, width, cfg["tile_size"])
            stats = []
            clips = []
            for centre in centres:
                patch, clipped = green_patch(
                    visible,
                    centre,
                    cfg["tile_size"],
                    cfg["channel"],
                    (metadata["black_levels"][1], metadata["black_levels"][3]),
                    cfg["xshift"],
                )
                stats.append(
                    A.frame_sufficient_stats(
                        patch,
                        block_grid=cfg["block_grid"],
                    )
                )
                clips.append(clipped)
            by_variant[name] = np.stack(stats)
            clip_by_variant[name] = np.asarray(clips)
    return by_variant, clip_by_variant, metadata


def inventory_for(stack: Stack, files: list[Path]) -> dict:
    picks = sorted({0, len(files) // 2, len(files) - 1})
    return {
        **asdict(stack),
        "files": [
            {
                "name": p.name,
                "bytes": p.stat().st_size,
                "mtime_ns": p.stat().st_mtime_ns,
            }
            for p in files
        ],
        "anchor_sha256": {files[i].name: file_sha256(files[i]) for i in picks},
    }


def run_stack(stack: Stack, workers: int) -> dict:
    path = Path(stack.path)
    files = sorted(path.glob("*.ARW"))
    if len(files) != stack.expected_frames:
        raise ValueError(
            f"{stack.name}: expected {stack.expected_frames} frames, found {len(files)}"
        )
    print(f"\n{stack.name}: {len(files)} frames, {workers} workers")
    start = time.perf_counter()
    collected = {}
    clipped = {}
    metadata_first = None
    jobs = [(str(p), asdict(stack)) for p in files]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for index, (stats, clips, metadata) in enumerate(
            pool.map(frame_job, jobs, chunksize=1)
        ):
            if metadata_first is None:
                metadata_first = metadata
            elif metadata != metadata_first:
                raise ValueError(f"{stack.name}: metadata changed at frame {index}")
            for name, value in stats.items():
                collected.setdefault(name, []).append(value)
                clipped.setdefault(name, []).append(clips[name])
            if (index + 1) % 10 == 0 or index + 1 == len(files):
                print(f"  {index + 1}/{len(files)}", flush=True)
    arrays = {}
    for name, rows in collected.items():
        arrays[f"stats__{name}"] = np.stack(rows)
        arrays[f"clip__{name}"] = np.stack(clipped[name])
        cfg = VARIANTS[name]
        centres = centres_for(
            stack,
            metadata_first["shape"][0] // 2,
            metadata_first["shape"][1] // 2,
            cfg["tile_size"],
        )
        arrays[f"centres__{name}"] = np.asarray(
            [
                (
                    float(c["cy"]),
                    float(c["cx"] + cfg["xshift"]),
                    float(c["radius"]),
                    float(
                        {
                            "centre": 0,
                            "left": 1,
                            "right": 2,
                            "top": 3,
                            "bottom": 4,
                        }[c["sector"]]
                    ),
                )
                for c in centres
            ],
            dtype=np.float64,
        )
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / f"{stack.name}.npz"
    np.savez_compressed(target, **arrays)
    elapsed = time.perf_counter() - start
    print(f"  wrote {target.name}, {target.stat().st_size} bytes, {elapsed:.1f}s")
    return {
        "stack": asdict(stack),
        "metadata": metadata_first,
        "cache": str(target.relative_to(ROOT)),
        "cache_bytes": target.stat().st_size,
        "cache_sha256": file_sha256(target),
        "elapsed_seconds": elapsed,
        "inventory": inventory_for(stack, files),
    }


def select_stacks(which: str) -> tuple[Stack, ...]:
    if which == "all":
        return STACKS
    if which == "grid":
        return tuple(s for s in STACKS if s.role == "grid")
    if which == "aperture":
        return tuple(s for s in STACKS if s.role == "aperture")
    if which == "control":
        return tuple(s for s in STACKS if s.role == "flat-control")
    names = {x.strip() for x in which.split(",")}
    selected = tuple(s for s in STACKS if s.name in names)
    if names != {s.name for s in selected}:
        raise ValueError(f"unknown stack(s): {sorted(names - {s.name for s in selected})}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stacks",
        default="all",
        help="all, grid, aperture, control, or comma-separated stack names",
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    stacks = select_stacks(args.stacks)
    before = capture_snapshot(stacks)
    records = [run_stack(stack, args.workers) for stack in stacks]
    after = capture_snapshot(stacks)
    if before != after:
        raise RuntimeError("read-only capture snapshot changed during decode")
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "capture-inventory.json"
    existing = {}
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
    by_name = {
        row["stack"]["name"]: row
        for row in existing.get("records", [])
    }
    by_name.update({row["stack"]["name"]: row for row in records})
    result = {
        "schema_version": 1,
        "role": "real RAW extraction; no focus-split verdict",
        "invocation": (
            "OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1; "
            "PYTHONIOENCODING=utf-8; "
            f"python experiments\\M-PHASE0-ASTIG\\src\\real_measure.py "
            f"--stacks {args.stacks} --workers {args.workers}"
        ),
        "source_sha256": {
            "real_measure.py": file_sha256(Path(__file__)),
            "astiglib.py": file_sha256(HERE / "astiglib.py"),
        },
        "capture_snapshot_unchanged": True,
        "records": [by_name[k] for k in sorted(by_name)],
    }
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {target}")


if __name__ == "__main__":
    main()
