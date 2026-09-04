"""External LibRaw check that M130 Crop copies integer samples exactly."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rawpy
import tifffile

import artifact_io


HERE = Path(__file__).resolve().parent
DEFAULT_FREEZE_ARTIFACT = HERE / "freeze.json"
HOLD_RE = re.compile(
    r"^freeze `(?P<id>[^`]+)` HOLDS: (?P<sha>[0-9A-F]{64}) "
    r"\((?P<bytes>\d+) bytes, (?P<detail>.+)\) -- reproduced twice$"
)


@dataclass(frozen=True)
class Diff:
    samples: int
    differing: int
    fraction_differing: float
    max_abs_dn: int
    rms_dn: float


def sha256(path: Path) -> str:
    return artifact_io.sha256_file(path)


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(array))).hexdigest().upper()


def stats(reference: np.ndarray, candidate: np.ndarray) -> Diff:
    if reference.shape != candidate.shape:
        raise ValueError(f"shape mismatch: {reference.shape} != {candidate.shape}")
    delta = candidate.astype(np.int32) - reference.astype(np.int32)
    absolute = np.abs(delta)
    differing = int(np.count_nonzero(delta))
    return Diff(
        samples=delta.size,
        differing=differing,
        fraction_differing=differing / delta.size,
        max_abs_dn=int(absolute.max(initial=0)),
        rms_dn=float(np.sqrt(np.mean(delta.astype(np.float64) ** 2))),
    )


def encode(
    raw: np.ndarray,
    *,
    black: int,
    white: int,
    gains: np.ndarray,
) -> np.ndarray:
    """Independently reproduce the default binned linear RGB16 arithmetic."""

    if raw.ndim != 2 or raw.shape[0] % 2 or raw.shape[1] % 2:
        raise ValueError(f"visible mosaic must have even HxW dimensions, got {raw.shape}")
    source = raw.astype(np.float32)
    floor = np.float32(black)

    def plane(view: np.ndarray) -> np.ndarray:
        return np.maximum(
            np.subtract(view, floor, dtype=np.float32),
            np.float32(0.0),
        )

    red = plane(source[0::2, 0::2])
    green_1 = plane(source[0::2, 1::2])
    green_2 = plane(source[1::2, 0::2])
    blue = plane(source[1::2, 1::2])
    green = np.multiply(
        np.add(green_1, green_2, dtype=np.float32),
        np.float32(0.5),
        dtype=np.float32,
    )
    scale = np.float32(65535.0)
    sensor_range = np.float32(white - black)
    encoded: list[np.ndarray] = []
    for values, gain in zip((red, green, blue), gains, strict=True):
        values = np.multiply(values, np.float32(gain), dtype=np.float32)
        values = np.divide(values, sensor_range, dtype=np.float32)
        values = np.minimum(values, np.float32(1.0))
        values = np.multiply(values, scale, dtype=np.float32)
        values = np.add(values, np.float32(0.5), dtype=np.float32)
        encoded.append(values.astype(np.uint16))
    return np.stack(encoded, axis=-1)


def read_rgb16(path: Path) -> np.ndarray:
    image = np.asarray(tifffile.imread(path))
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint16:
        raise ValueError(f"{path}: expected uint16 HxWx3, got {image.shape} {image.dtype}")
    return image


def emit(result: dict[str, Any], output: Path | None) -> dict[str, Any]:
    if output is not None:
        result = artifact_io.write_artifact(output, result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def command_commission(_: argparse.Namespace) -> int:
    fixture = np.arange(12 * 14, dtype=np.uint16).reshape(12, 14) + 512
    encoded = encode(
        fixture,
        black=512,
        white=15360,
        gains=np.asarray([2.861328125, 1.0, 1.482421875], dtype=np.float32),
    )
    exact = asdict(stats(encoded, encoded.copy()))
    mutation = encoded.copy()
    mutation[1, 2, 1] ^= np.uint16(0x8000)
    changed = asdict(stats(encoded, mutation))
    scene = np.arange(40 * 50 * 3, dtype=np.uint16).reshape(40, 50, 3)
    correct = scene[4:34, 5:45]
    wrong = scene[4:34, 6:46]
    origin = asdict(stats(correct, wrong))
    checks = {
        "exact_null": exact["differing"] == 0 and exact["max_abs_dn"] == 0,
        "single_pixel_mutation": changed["differing"] == 1
        and changed["max_abs_dn"] == 32768,
        "origin_plant_fires": origin["fraction_differing"] > 0.95,
    }
    result = {
        "schema": "m130-crop-early-exactness-commission-v1",
        "milestone": "M130",
        "command": "commission",
        "checks": checks,
        "exact_null": exact,
        "single_pixel_mutation": changed,
        "origin_plant": origin,
        "pass": all(checks.values()),
    }
    emit(result, getattr(_, "output", None))
    return 0 if result["pass"] else 1


def command_measure(args: argparse.Namespace) -> int:
    with rawpy.imread(str(args.raw)) as first:
        raw_first = np.array(first.raw_image_visible, copy=True)
        pattern = first.raw_pattern.tolist()
        color_desc = first.color_desc.decode("ascii")
        black_levels = [int(v) for v in first.black_level_per_channel]
        wb = np.asarray(first.camera_whitebalance, dtype=np.float32)
    with rawpy.imread(str(args.raw)) as second:
        raw_second = np.array(second.raw_image_visible, copy=True)
    if not np.array_equal(raw_first, raw_second):
        raise ValueError("two independent LibRaw contexts decoded different mosaics")
    if pattern != [[0, 1], [3, 2]] or color_desc != "RGBG":
        raise ValueError(
            f"unexpected CFA metadata: pattern={pattern}, color_desc={color_desc!r}"
        )
    if len(set(black_levels)) != 1 or black_levels[0] != args.black:
        raise ValueError(
            f"LibRaw black levels {black_levels} do not match --black {args.black}"
        )
    gains = np.asarray([wb[0] / wb[1], 1.0, wb[2] / wb[1]], dtype=np.float32)
    expected = encode(
        raw_first,
        black=args.black,
        white=args.white,
        gains=gains,
    )
    direct = read_rgb16(args.direct)
    crop = read_rgb16(args.crop)
    scale = read_rgb16(args.scale)
    expected_height, expected_width, _ = expected.shape
    if direct.shape[0] != expected_height or direct.shape[1] < expected_width:
        raise ValueError(
            f"direct {direct.shape} does not cover external overlap {expected.shape}"
        )
    if scale.shape[0] != expected_height or scale.shape[1] < expected_width:
        raise ValueError(
            f"scale {scale.shape} does not cover external overlap {expected.shape}"
        )
    x, y = args.origin
    height, width, _ = crop.shape
    if y + height > expected_height or x + width > expected_width:
        raise ValueError(
            f"crop origin {(x, y)} and shape {crop.shape} exceed {expected.shape}"
        )
    external_crop = expected[y : y + height, x : x + width]
    wrong_external_crop = expected[y : y + height, x + 1 : x + 1 + width]
    if wrong_external_crop.shape != external_crop.shape:
        raise ValueError("the one-pixel origin plant does not fit")
    direct_overlap = direct[:, :expected_width]
    scale_overlap = scale[:, :expected_width]
    direct_window = direct[y : y + height, x : x + width]

    comparisons: dict[str, dict[str, Any]] = {
        "external_to_direct_overlap": asdict(stats(expected, direct_overlap)),
        "external_to_crop": asdict(stats(external_crop, crop)),
        "direct_window_to_crop": asdict(stats(direct_window, crop)),
        "wrong_origin_to_crop": asdict(stats(wrong_external_crop, crop)),
        "external_to_scale_overlap": asdict(stats(expected, scale_overlap)),
    }
    exact_names = (
        "external_to_direct_overlap",
        "external_to_crop",
        "direct_window_to_crop",
    )
    checks = {
        "external_direct_exact": comparisons["external_to_direct_overlap"]["differing"]
        == 0,
        "external_crop_exact": comparisons["external_to_crop"]["differing"] == 0,
        "direct_crop_exact": comparisons["direct_window_to_crop"]["differing"] == 0,
        "wrong_origin_fires": comparisons["wrong_origin_to_crop"][
            "fraction_differing"
        ]
        > 0.01,
        "scale_is_nonidentity": comparisons["external_to_scale_overlap"][
            "fraction_differing"
        ]
        > 0.01,
        "all_exact_max_zero": all(
            comparisons[name]["max_abs_dn"] == 0 for name in exact_names
        ),
    }
    result = {
        "schema": "m130-crop-early-exactness-v1",
        "milestone": "M130",
        "command": "measure",
        "analysis_status": "regenerated from the hashed RAW and TIFF inputs",
        "render_production_status": (
            "manual command, not regenerated by exactness.py; commands and "
            "binary hashes are recorded in docs/research/M130-crop-early.md"
        ),
        "instrument": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__)),
        },
        "raw": {
            "path": str(args.raw.resolve()),
            "sha256": sha256(args.raw),
            "bytes": args.raw.stat().st_size,
            "visible_shape": list(raw_first.shape),
            "visible_sha256": array_sha256(raw_first),
            "pattern": pattern,
            "color_desc": color_desc,
            "black_levels": black_levels,
            "camera_whitebalance": [float(v) for v in wb],
            "gains": [float(v) for v in gains],
        },
        "expected": {
            "shape": list(expected.shape),
            "sha256": array_sha256(expected),
            "black": args.black,
            "white": args.white,
        },
        "files": {
            name: {
                "path": str(path.resolve()),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "shape": list(read_rgb16(path).shape),
            }
            for name, path in (
                ("direct", args.direct),
                ("crop", args.crop),
                ("scale", args.scale),
            )
        },
        "crop_origin_plane_px": [x, y],
        "comparisons": comparisons,
        "checks": checks,
        "pass": all(checks.values()),
    }
    emit(result, args.output)
    return 0 if result["pass"] else 1


def registry_rows(path: Path) -> list[dict[str, str]]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    rows = list(csv.DictReader(io.StringIO("\n".join(lines)), delimiter="\t"))
    if not rows:
        raise ValueError(f"{path}: byte-freeze registry has no rows")
    if any(None in row or None in row.values() for row in rows):
        raise ValueError(f"{path}: malformed tab-separated byte-freeze row")
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate byte-freeze identifier")
    return rows


def cargo_summary(output: str) -> dict[str, int]:
    matches = re.findall(
        r"test result: ok\. (?P<passed>\d+) passed; (?P<failed>\d+) failed; "
        r"(?P<ignored>\d+) ignored; (?P<measured>\d+) measured; "
        r"(?P<filtered>\d+) filtered out",
        output,
    )
    if not matches:
        raise ValueError("byte-freeze harness did not print a passing test summary")
    passed, failed, ignored, measured, filtered = (int(value) for value in matches[-1])
    return {
        "passed": passed,
        "failed": failed,
        "ignored": ignored,
        "measured": measured,
        "filtered_out": filtered,
    }


def git_head(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def command_record_freeze(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    captures = args.captures.resolve()
    registry_path = repo / "crates" / "strehl-cli" / "tests" / "byte-freezes.tsv"
    harness_path = repo / "crates" / "strehl-cli" / "tests" / "byte-freeze.rs"
    rows = registry_rows(registry_path)

    capture_manifests: dict[str, dict[str, Any]] = {}
    capture_states: dict[str, list[dict[str, int | str]]] = {}
    for row in rows:
        key = f"{row['stack']}-first-{row['limit']}"
        stack = captures / row["stack"]
        if key not in capture_manifests:
            manifest = artifact_io.frame_manifest(
                stack,
                capture_identifier=key,
                limit=int(row["limit"]),
            )
            got_range = (
                f"{Path(manifest['first_frame']).stem}.."
                f"{Path(manifest['last_frame']).stem}"
            )
            if got_range != row["frames"]:
                raise ValueError(
                    f"{row['id']}: registry range {row['frames']} != capture {got_range}"
                )
            capture_manifests[key] = manifest
            capture_states[key] = artifact_io.path_state(stack)

    default_manifest = artifact_io.frame_manifest(
        args.default_stack,
        capture_identifier=args.default_capture_identifier,
        limit=args.default_limit,
    )
    default_state = artifact_io.path_state(args.default_stack)

    sidecars: dict[str, dict[str, Any]] = {}
    fixture_dir = registry_path.parent / "data"
    for row in rows:
        name = row["env_warpmap"]
        if name != "unset" and name not in sidecars:
            sidecars[name] = artifact_io.file_record(fixture_dir / name)

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("STREHL_")
    }
    environment["STREHL_FREEZE_REQUIRE"] = "1"
    environment["STREHL_CAPTURES"] = str(captures)
    environment["CARGO_TARGET_DIR"] = str(args.cargo_target.resolve())
    command = [
        "cargo",
        "test",
        "-p",
        "strehl-cli",
        "--test",
        "byte-freeze",
        "the_frozen_renders_still_produce_their_recorded_bytes",
        "--",
        "--nocapture",
    ]
    completed = subprocess.run(
        command,
        cwd=repo,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = completed.stdout + completed.stderr
    print(output, file=sys.stderr, end="" if output.endswith("\n") else "\n")
    if completed.returncode != 0:
        raise RuntimeError(
            f"byte-freeze harness exited {completed.returncode}; no artifact written"
        )

    exercised: list[dict[str, Any]] = []
    for line in output.splitlines():
        match = HOLD_RE.match(line.strip())
        if match is None:
            continue
        exercised.append(
            {
                "id": match.group("id"),
                "sha256": match.group("sha"),
                "bytes": int(match.group("bytes")),
                "reported_detail": match.group("detail"),
                "exercised_passes": 2,
                "status": "HOLDS",
            }
        )
    expected_ids = [row["id"] for row in rows]
    exercised_ids = [row["id"] for row in exercised]
    if exercised_ids != expected_ids:
        raise ValueError(
            "harness rows differ from registry rows: "
            f"expected {expected_ids}, got {exercised_ids}"
        )
    by_id = {row["id"]: row for row in rows}
    for row in exercised:
        registered = by_id[row["id"]]
        if row["sha256"] != registered["sha256"]:
            raise ValueError(f"{row['id']}: harness and registry SHA-256 differ")
        if row["bytes"] != int(registered["bytes"]):
            raise ValueError(f"{row['id']}: harness and registry byte counts differ")
        row.update(
            {
                "stack": registered["stack"],
                "frame_range": registered["frames"],
                "limit": int(registered["limit"]),
                "merge": registered["merge"],
                "gate": registered["gate"],
                "alignment_mode": registered["alignment_mode"],
                "capture_manifest": (
                    f"{registered['stack']}-first-{registered['limit']}"
                ),
            }
        )

    unchanged = True
    for key in capture_manifests:
        stack = captures / by_id[next(
            row_id
            for row_id in expected_ids
            if f"{by_id[row_id]['stack']}-first-{by_id[row_id]['limit']}" == key
        )]["stack"]
        unchanged &= capture_states[key] == artifact_io.path_state(stack)
    unchanged &= default_state == artifact_io.path_state(args.default_stack)
    if not unchanged:
        raise RuntimeError("a read-only capture directory changed during the harness run")

    before = read_rgb16(args.default_before)
    after = read_rgb16(args.default_after)
    default_diff = asdict(stats(before, after))
    if default_diff["differing"] != 0:
        raise ValueError("before/after default renders are not byte-exact as arrays")

    summary = cargo_summary(output)
    artifact = {
        "schema": "m130-crop-early-freeze-v1",
        "milestone": "M130",
        "generation": {
            "source": "regenerated by exactness.py record-freeze",
            "repository_head": git_head(repo),
            "command": command,
            "cwd": str(repo),
            "environment": {
                "STREHL_FREEZE_REQUIRE": "1",
                "STREHL_CAPTURES": str(captures),
                "CARGO_TARGET_DIR": str(args.cargo_target.resolve()),
            },
            "exit_code": completed.returncode,
            "cargo_summary": summary,
            "harness_output_sha256": artifact_io.sha256_text(output),
        },
        "instruments": {
            "exactness_py": artifact_io.file_record(Path(__file__)),
            "artifact_io_py": artifact_io.file_record(HERE / "artifact_io.py"),
            "registry": artifact_io.file_record(registry_path),
            "harness": artifact_io.file_record(harness_path),
        },
        "input_provenance": {
            "capture_manifests": capture_manifests,
            "default_capture": default_manifest,
            "sidecars": sidecars,
            "read_only_directories_unchanged_during_run": unchanged,
        },
        "freeze_rows": exercised,
        "default_cover_pair": {
            "production_status": (
                "manual command, not regenerated by record-freeze; exact render "
                "commands and binary hashes are in docs/research/M130-crop-early.md"
            ),
            "analysis_status": (
                "hashes, dimensions, and sample differences regenerated by "
                "exactness.py record-freeze"
            ),
            "before": {
                **artifact_io.file_record(args.default_before),
                "shape": list(before.shape),
                "dtype": str(before.dtype),
            },
            "after": {
                **artifact_io.file_record(args.default_after),
                "shape": list(after.shape),
                "dtype": str(after.dtype),
            },
            "comparison": {
                "samples": default_diff["samples"],
                "differing_samples": default_diff["differing"],
                "fraction_differing": default_diff["fraction_differing"],
                "max_dn": default_diff["max_abs_dn"],
                "rms_dn": default_diff["rms_dn"],
            },
        },
        "verdict": {
            "all_registry_rows_exercised_twice": all(
                row["exercised_passes"] == 2 for row in exercised
            ),
            "default_cover_byte_exact": default_diff["differing"] == 0,
            "pass": True,
        },
    }
    sealed = artifact_io.write_artifact(args.output, artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output.resolve()),
                "self_sha256": sealed["integrity"]["self_sha256"],
                "rows": len(exercised),
                "default_differing_samples": default_diff["differing"],
                "pass": sealed["verdict"]["pass"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_verify_freeze(args: argparse.Namespace) -> int:
    artifact = artifact_io.read_verified_artifact(args.input.resolve())
    artifact_io.require_keys(
        artifact,
        ("schema", "freeze_rows", "default_cover_pair", "verdict"),
        where=str(args.input),
    )
    if artifact["schema"] != "m130-crop-early-freeze-v1":
        raise ValueError(f"{args.input}: unsupported schema {artifact['schema']!r}")
    if not artifact["freeze_rows"]:
        raise ValueError(f"{args.input}: no exercised byte-freeze rows")
    if not artifact["verdict"].get("all_registry_rows_exercised_twice"):
        raise ValueError(f"{args.input}: not every registry row was exercised twice")
    if artifact["default_cover_pair"]["comparison"]["differing_samples"] != 0:
        raise ValueError(f"{args.input}: default before/after pair differs")
    print(
        json.dumps(
            {
                "artifact": str(args.input.resolve()),
                "self_sha256": artifact["integrity"]["self_sha256"],
                "rows": len(artifact["freeze_rows"]),
                "default_differing_samples": 0,
                "pass": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest="command", required=True)
    commission = commands.add_parser("commission")
    commission.add_argument("--output", type=Path)
    commission.set_defaults(function=command_commission)
    measure = commands.add_parser("measure")
    measure.add_argument("--raw", type=Path, required=True)
    measure.add_argument("--direct", type=Path, required=True)
    measure.add_argument("--crop", type=Path, required=True)
    measure.add_argument("--scale", type=Path, required=True)
    measure.add_argument("--origin", type=int, nargs=2, required=True, metavar=("X", "Y"))
    measure.add_argument("--black", type=int, default=512)
    measure.add_argument("--white", type=int, default=15360)
    measure.add_argument("--output", type=Path)
    measure.set_defaults(function=command_measure)
    freeze = commands.add_parser("record-freeze")
    freeze.add_argument("--repo", type=Path, required=True)
    freeze.add_argument("--captures", type=Path, required=True)
    freeze.add_argument("--default-stack", type=Path, required=True)
    freeze.add_argument("--default-capture-identifier", required=True)
    freeze.add_argument("--default-limit", type=int, required=True)
    freeze.add_argument("--default-before", type=Path, required=True)
    freeze.add_argument("--default-after", type=Path, required=True)
    freeze.add_argument("--cargo-target", type=Path, required=True)
    freeze.add_argument("--output", type=Path, default=DEFAULT_FREEZE_ARTIFACT)
    freeze.set_defaults(function=command_record_freeze)
    verify = commands.add_parser("verify-freeze")
    verify.add_argument("--input", type=Path, default=DEFAULT_FREEZE_ARTIFACT)
    verify.set_defaults(function=command_verify_freeze)
    return p


def main() -> int:
    args = parser().parse_args()
    return int(args.function(args))


if __name__ == "__main__":
    raise SystemExit(main())
