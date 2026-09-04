from __future__ import annotations

import importlib.util
import json
import shutil
import struct
import sys
from pathlib import Path

import numpy as np

from common import CHECKER, ROOT, atomic_json, read_rgb16, sha256


MAGIC = b"M8SITE01"
VERSION = 2
HEADER = struct.Struct("<8s9I6d2fI")
CHANNEL_SITES = [(0, 0), (1, 0), (1, 1)]


def load_checker():
    spec = importlib.util.spec_from_file_location("m8_commissioned_checker", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {CHECKER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_identity_block(
    path: Path, frame: Path, image: np.ndarray, channel: int
) -> None:
    """Encode one-pixel identity support as a 2x2-equal bilinear support."""
    height, width, _ = image.shape
    site_x, site_y = CHANNEL_SITES[channel]
    # The unchanged checker maps destination coordinates to 2*x+0.5, 2*y+0.5.
    # Every source sample is repeated 2x2, so its independently reconstructed
    # bilinear support contains one prepared value and nothing else.
    b_re = 0.25 - 0.5 * site_x
    b_im = 0.25 - 0.5 * site_y
    source = np.repeat(
        np.repeat(
            image[..., channel].astype(np.float32) / np.float32(65535.0),
            2,
            axis=0,
        ),
        2,
        axis=1,
    )
    trace = image[..., channel].astype(np.float32) / np.float32(65535.0)
    frame_bytes = str(frame.resolve()).encode("utf-8")
    header = HEADER.pack(
        MAGIC,
        VERSION,
        1,
        2 * width,
        2 * height,
        width,
        height,
        site_x,
        site_y,
        channel,
        1.0,
        0.0,
        b_re,
        b_im,
        width * 0.5,
        height * 0.5,
        1.0,
        1.0,
        len(frame_bytes),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(header)
        f.write(frame_bytes)
        f.write(np.ascontiguousarray(source, dtype="<f4").tobytes())
        f.write(np.ascontiguousarray(trace, dtype="<f4").tobytes())


def build_state(
    frames: list[Path],
    state: Path,
    capture: str,
    block_dir: Path | None = None,
) -> dict:
    checker = load_checker()
    if state.exists():
        shutil.rmtree(state)
    state.mkdir(parents=True)
    blocks = block_dir or (state.parent / "blocks")
    blocks.mkdir(parents=True, exist_ok=True)
    rows = []
    for ordinal, frame in enumerate(frames):
        image = read_rgb16(frame)
        for channel in range(3):
            block = blocks / f"{ordinal:03d}-c{channel}.m8site"
            write_identity_block(block, frame, image, channel)
            rows.append(checker.consume(block, state, capture))
            block.unlink()
    aggregate = checker.aggregate_r(state)
    payload = {
        "capture": capture,
        "frames": len(frames),
        "sites": len(rows),
        "adapter": (
            "Each prepared RGB sample is repeated into a 2x2 source cell. "
            "The unchanged checker independently reconstructs bilinear support "
            "at phase (0.5,0.5), whose four values are equal. The resulting "
            "hull is exactly the one prepared sample."
        ),
        "checker": str(CHECKER.resolve()),
        "checker_sha256": sha256(CHECKER),
        "m8_r": aggregate,
    }
    atomic_json(state / "adapter.json", payload)
    return payload


def final_output(state: Path, output: Path) -> dict:
    checker = load_checker()
    return checker.final_output(state, output)


def summarize(state: Path, output: Path, destination: Path) -> dict:
    meta = json.loads((state / "meta.json").read_text(encoding="utf-8"))
    result = json.loads((state / "m8-o.json").read_text(encoding="utf-8"))
    image = read_rgb16(output)
    lo = np.load(state / "o-lo.npy", mmap_mode="r")
    hi = np.load(state / "o-hi.npy", mmap_mode="r")
    violations = np.load(state / "m8-o-violations.npy", mmap_mode="r")
    signed = np.asarray(violations["signed_excess"], dtype=np.float64)
    excess = np.abs(signed)
    spans = []
    zero_span_violations = 0
    for row in violations:
        span = float(row["hi"]) - float(row["lo"])
        if span > 0.0:
            spans.append(abs(float(row["signed_excess"])) / span)
        else:
            zero_span_violations += 1
    zero_span = 0
    finite = 0
    for channel in range(3):
        channel_lo = np.asarray(lo[channel])
        channel_hi = np.asarray(hi[channel])
        mask = np.isfinite(channel_lo) & np.isfinite(channel_hi)
        finite += int(np.count_nonzero(mask))
        zero_span += int(np.count_nonzero(mask & (channel_hi == channel_lo)))
    all_samples = int(image.shape[0] * image.shape[1] * image.shape[2])

    def quantiles(values: np.ndarray | list[float]) -> dict:
        array = np.asarray(values, dtype=np.float64)
        if array.size == 0:
            return {"median": None, "p99": None, "max": None}
        return {
            "median": float(np.quantile(array, 0.5)),
            "p99": float(np.quantile(array, 0.99)),
            "max": float(np.max(array)),
        }

    payload = {
        "capture": meta["capture"],
        "output": str(output.resolve()),
        "all_output_samples": all_samples,
        "valid_source_hull_samples": finite,
        "lower_violations": int(result["lower_violations"]),
        "upper_violations": int(result["upper_violations"]),
        "total_violations": int(result["violations"]),
        "rate_all_output": result["violations"] / all_samples,
        "rate_valid_hull": result["violations"] / finite,
        "percent_all_output": 100.0 * result["violations"] / all_samples,
        "percent_valid_hull": 100.0 * result["violations"] / finite,
        "min_lower_signed_excess_linear": result[
            "min_lower_signed_excess_linear"
        ],
        "max_upper_signed_excess_linear": result[
            "max_upper_signed_excess_linear"
        ],
        "excess_linear": quantiles(excess),
        "excess_dn": quantiles(excess * 65535.0),
        "excess_over_hull_span": quantiles(spans),
        "zero_span_hull_samples": zero_span,
        "zero_span_violations": zero_span_violations,
        "sign_balance": {
            "lower_fraction": (
                result["lower_violations"] / result["violations"]
                if result["violations"]
                else None
            ),
            "upper_fraction": (
                result["upper_violations"] / result["violations"]
                if result["violations"]
                else None
            ),
        },
        "rail_occupancy": {
            "zero": [int(np.count_nonzero(image[..., c] == 0)) for c in range(3)],
            "full": [
                int(np.count_nonzero(image[..., c] == 65535)) for c in range(3)
            ],
        },
        "violations_file": result["violations_file"],
        "violations_sha256": result["violations_sha256"],
        "licensed_claim": (
            "M8-O can establish invention after the declared prepared-input "
            "boundary. It cannot name the inventor."
        ),
        "benchmark_scope": (
            "Controlled merge audit, not a default-settings product benchmark."
        ),
    }
    atomic_json(destination, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload
