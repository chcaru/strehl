from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


for _name in (
    "RAYON_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_name] = "6"
os.environ["PYTHONIOENCODING"] = "utf-8"


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
BASELINE = ROOT / "experiments" / "SCORECARD-BASELINE"
BASELINE_OUT = BASELINE / "out"
BASELINE_WORK = BASELINE / "work"
OUT = LANE / "out"
RENDERS = OUT / "renders"
PRIVATE_CACHE = LANE / "work" / "cache"
BINARY = BASELINE_WORK / "bin" / "strehl.exe"

BINARY_SHA256 = "814eb719608cc0f085fbd49e7529eb6fa4e50031070f5f57af4fc2812cee4363"
BINARY_VERSION = "strehl 0.0.0 (4b60b1ba9f56)"
CONTROL_NAME = "m2-second-first16"
CONTROL_SHA256 = "3d46f11413e5cf37bdeb730eb6faf66c266ac52107e1b5af1e032052080d16bc"
COMMON_SHAPE = (4608, 6912)
NATIVE_SHAPE = (4688, 7032)
THREAD_ENV = {
    "RAYON_NUM_THREADS": "6",
    "OMP_NUM_THREADS": "6",
    "OPENBLAS_NUM_THREADS": "6",
    "MKL_NUM_THREADS": "6",
    "NUMEXPR_NUM_THREADS": "6",
}

ARMS = (
    "m1-bright-a12",
    "m1-bright-b12",
    "m1-second-a12",
    "m1-second-b12",
    "m2-bright-first16",
    "m2-bright-second16",
    "m2-second-first16",
    "m2-second-second16",
)

PROTECTED = (
    "docs/STATUS.md",
    "docs/proposals/2026-09-sota-scorecard.md",
    "docs/research/M8-overshoot.md",
    "experiments/M8-overshoot",
    "experiments/M-COVER-BORDER",
    "experiments/SCORECARD-BASELINE",
)

DEFAULTS = {
    "limit": None,
    "limit_meaning": "all files in exact frozen input directory",
    "merge": "pyramid (omitted shipping default)",
    "pyramid_bands": 7,
    "pyramid_gate": 2.0,
    "pyramid_exponent_coarsest": 2.0,
    "pyramid_sharpen_per_octave": 1.4,
    "pyramid_select": "soft",
    "pyramid_base": "mean",
    "srgb_transfer_curve": False,
    "linear_srgb": True,
    "demosaic": "Malvar-He-Cutler full resolution",
    "binned": False,
    "fix_ca": "omitted; gear-matched profile default",
    "exposure_stops": 0.0,
    "auto_exposure": False,
    "estimator_gate": "omitted and inapplicable to pyramid",
    "focus": "omitted and inapplicable to pyramid",
    "flat_roi": None,
    "detail_roi": None,
    "index_map": None,
    "n_eff_map": None,
    "confidence_map": None,
    "photometric": "omitted; pyramid banner says photometric gain not applied",
    "target_n_eff": None,
    "stats": False,
    "stats_placebo": False,
    "confidence_tail": 0.05,
    "resampler": "catmull-rom",
    "cover_control": "scale (omitted shipping default)",
    "cover_test": "crop (explicit)",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path, block: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(block):
            digest.update(chunk)
    return digest.hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def snapshot_files(paths: list[Path]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(set(paths), key=lambda item: str(item).lower()):
        if not path.is_file():
            raise RuntimeError(f"frozen dependency missing: {path}")
        stat = path.stat()
        rows[relative(path)] = {
            "bytes": stat.st_size,
            "sha256": sha256(path),
        }
    return rows


def frozen_dependency_paths() -> list[Path]:
    tracked_text = subprocess.run(
        ["git", "ls-files", "--", "experiments/SCORECARD-BASELINE"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    tracked = [ROOT / line for line in tracked_text.splitlines() if line]
    ignored = [
        BINARY,
        BASELINE_WORK / "source" / "crates" / "strehl-cli" / "src" / "main.rs",
        BASELINE_WORK / "source" / "crates" / "strehl-cli" / "src" / "align_cmd.rs",
        BASELINE_WORK / "source" / "crates" / "strehl-cli" / "src" / "merge_cmd.rs",
        BASELINE_WORK / "source" / "crates" / "strehl-core" / "src" / "pyramid.rs",
    ]
    ignored.extend((BASELINE_WORK / "cache").glob("*.warpmap.txt"))
    ignored.extend((BASELINE_WORK / "input-cache").glob("*.npy"))
    ignored.extend((BASELINE_WORK / "inputs").glob("*/*.ARW"))
    ignored.extend((BASELINE_OUT / "renders").glob("*.tiff"))
    return tracked + ignored


def metadata_rows(path: Path) -> list[dict[str, Any]]:
    if path.is_file():
        stat = path.stat()
        return [{"path": relative(path), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}]
    if not path.exists():
        return []
    rows = []
    for item in sorted(path.rglob("*"), key=lambda value: str(value).lower()):
        if item.is_file():
            stat = item.stat()
            rows.append(
                {
                    "path": relative(item),
                    "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
    return rows


def protected_fingerprint() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in PROTECTED:
        diff = subprocess.run(
            ["git", "--no-pager", "diff", "--binary", "--", name],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout
        status = subprocess.run(
            ["git", "--no-pager", "status", "--porcelain=v1", "--untracked-files=all", "--", name],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout
        rows = metadata_rows(ROOT / name)
        result[name] = {
            "diff_sha256": hash_text(diff),
            "status": status.splitlines(),
            "status_sha256": hash_text(status),
            "metadata_count": len(rows),
            "metadata_sha256": hash_text(json.dumps(rows, sort_keys=True)),
        }
    return result


def baseline_cache_paths() -> list[Path]:
    paths = sorted((BASELINE_WORK / "cache").glob("*.warpmap.txt"))
    if len(paths) != 8:
        raise RuntimeError(f"expected eight frozen cache files, found {len(paths)}")
    return paths


def copy_private_cache() -> None:
    PRIVATE_CACHE.mkdir(parents=True, exist_ok=True)
    expected_names = {path.name for path in baseline_cache_paths()}
    existing_names = {path.name for path in PRIVATE_CACHE.glob("*") if path.is_file()}
    unexpected = sorted(existing_names - expected_names)
    if unexpected:
        raise RuntimeError(f"unexpected private-cache files: {unexpected}")
    for source in baseline_cache_paths():
        destination = PRIVATE_CACHE / source.name
        if destination.exists():
            if sha256(destination) != sha256(source):
                raise RuntimeError(f"private cache differs and will not be overwritten: {destination}")
        else:
            shutil.copy2(source, destination)


def cache_snapshot(root: Path) -> dict[str, dict[str, Any]]:
    paths = sorted(path for path in root.glob("*.warpmap.txt") if path.is_file())
    return {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in paths
    }


def recognized_strehl_env() -> list[str]:
    source = BASELINE_WORK / "source"
    names: set[str] = set()
    pattern = re.compile(r"STREHL_[A-Z0-9_]+")
    for path in source.rglob("*.rs"):
        names.update(pattern.findall(path.read_text(encoding="utf-8", errors="replace")))
    return sorted(names)


def effective_environment() -> dict[str, Any]:
    names = recognized_strehl_env()
    strehl = {name: None for name in names}
    strehl["STREHL_CACHE_DIR"] = str(PRIVATE_CACHE.resolve())
    return {
        "thread_cap": 6,
        "variables": {
            **THREAD_ENV,
            "PYTHONIOENCODING": "utf-8",
            "STREHL_CACHE_DIR": str(PRIVATE_CACHE.resolve()),
        },
        "all_other_recognized_strehl_variables": strehl,
        "ambient_strehl_names_cleared": sorted(
            name for name in os.environ if name.startswith("STREHL_")
        ),
    }


def render_env() -> dict[str, str]:
    env = dict(os.environ)
    for name in list(env):
        if name.startswith("STREHL_"):
            env.pop(name)
    env.update(THREAD_ENV)
    env["PYTHONIOENCODING"] = "utf-8"
    env["STREHL_CACHE_DIR"] = str(PRIVATE_CACHE.resolve())
    return env


def validate_inputs_against_manifest() -> dict[str, Any]:
    manifest = read_json(BASELINE_OUT / "INPUT-MANIFEST.json")
    expected = {
        Path(row["path"]).name.lower(): {
            "bytes": int(row["size"]),
            "sha256": row["sha256"],
        }
        for row in manifest["used_files"]
    }
    checked = []
    for directory in sorted((BASELINE_WORK / "inputs").iterdir()):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.ARW")):
            want = expected.get(path.name.lower())
            if want is None:
                raise RuntimeError(f"{path} is absent from frozen INPUT-MANIFEST")
            got = {"bytes": path.stat().st_size, "sha256": sha256(path)}
            if got != want:
                raise RuntimeError(f"{path} differs from frozen INPUT-MANIFEST")
            checked.append(relative(path))
    if len(checked) != 112:
        raise RuntimeError(f"expected 112 arm-file instances, found {len(checked)}")
    return {
        "instances": len(checked),
        "unique_capture_hashes": len({row["sha256"] for row in expected.values()}),
        "all_match_frozen_input_manifest": True,
    }


def command_for(name: str, output: Path, cover: str | None) -> list[str]:
    command = [
        str(BINARY.resolve()),
        "stack",
        str((BASELINE_WORK / "inputs" / name).resolve()),
        "--out",
        str(output.resolve()),
        "--linear-srgb",
        "--demosaic",
    ]
    if cover is not None:
        command.extend(["--cover", cover])
    return command


def preflight() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    if any(RENDERS.glob("*.tiff")):
        raise RuntimeError("render TIFF exists before preregistration freeze")
    if sha256(BINARY) != BINARY_SHA256:
        raise RuntimeError("frozen binary hash mismatch")
    version = subprocess.run(
        [str(BINARY), "--version"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if version != BINARY_VERSION:
        raise RuntimeError(f"frozen binary version mismatch: {version!r}")
    copy_private_cache()
    baseline_cache = cache_snapshot(BASELINE_WORK / "cache")
    private_cache = cache_snapshot(PRIVATE_CACHE)
    if private_cache != baseline_cache:
        raise RuntimeError("private cache is not a byte copy of the frozen cache")
    input_validation = validate_inputs_against_manifest()
    frozen = snapshot_files(frozen_dependency_paths())
    payload = {
        "phase": "A_Q1_Q2_ONLY",
        "created_utc": utc_now(),
        "git_head_observed": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip(),
        "binary": {
            "path": str(BINARY.resolve()),
            "bytes": BINARY.stat().st_size,
            "sha256": BINARY_SHA256,
            "version": version,
        },
        "arms": list(ARMS),
        "input_validation": input_validation,
        "baseline_cache": baseline_cache,
        "private_cache": private_cache,
        "frozen_dependencies": frozen,
        "protected_paths": protected_fingerprint(),
        "environment": effective_environment(),
        "defaults": DEFAULTS,
        "control": {
            "arm": CONTROL_NAME,
            "required_sha256": CONTROL_SHA256,
            "command": command_for(
                CONTROL_NAME, RENDERS / f"control-scale-{CONTROL_NAME}.tiff", None
            ),
        },
        "crop_command_templates": {
            name: command_for(name, RENDERS / f"{name}.tiff", "crop") for name in ARMS
        },
    }
    write_json(OUT / "PREFLIGHT.json", payload)
    print(
        f"preflight passed: {len(frozen)} frozen files hashed, "
        f"{len(private_cache)} cache files copied"
    )
    return 0


def selected_banners(text: str) -> list[str]:
    prefixes = (
        "build",
        "merge backend",
        "lateral CA",
        "defect map",
        "frames",
        "bands",
        "selection",
        "noise gate",
        "exponent",
        "per-band exp",
        "base band",
        "not applied",
        "alignment",
        "  held-out err",
        "  coverage",
        "memory plan",
        "folded",
        "wrote",
    )
    return [
        line
        for line in text.splitlines()
        if any(line.lstrip().lower().startswith(prefix.strip().lower()) for prefix in prefixes)
    ]


def parse_alignment(text: str) -> dict[str, Any]:
    line = next(
        (line for line in text.splitlines() if line.lstrip().startswith("alignment")),
        None,
    )
    if line is None:
        raise RuntimeError("alignment banner missing")
    match = re.search(
        r"reference frame\s+(\d+),\s+(\d+)\s+placed\s+/\s+(\d+)\s+refused",
        line,
    )
    if match is None:
        raise RuntimeError(f"alignment banner unparseable: {line}")
    held = next(
        (line for line in text.splitlines() if line.lstrip().startswith("held-out err")),
        None,
    )
    resampler_match = re.search(r"resampler:\s*([A-Za-z0-9-]+)", held or "")
    return {
        "banner": line,
        "reference_frame": int(match.group(1)),
        "placed": int(match.group(2)),
        "refused": int(match.group(3)),
        "held_out_banner": held,
        "resampler": resampler_match.group(1).lower() if resampler_match else None,
    }


def coverage_banner(text: str) -> str:
    line = next(
        (
            line
            for line in text.splitlines()
            if re.match(r"^\s*coverage\s+:", line)
        ),
        None,
    )
    if line is None:
        raise RuntimeError("coverage fit banner missing")
    return line


def parse_scale_coverage(text: str) -> dict[str, Any]:
    line = coverage_banner(text)
    match = re.search(r"field of view scaled to\s+([0-9.]+)", line)
    if match is None:
        raise RuntimeError(f"Scale coverage banner unparseable: {line}")
    return {"banner": line, "k_printed": match.group(1), "k": float(match.group(1))}


def parse_crop_coverage(text: str) -> dict[str, Any]:
    line = coverage_banner(text)
    match = re.search(
        r"--\s*(\d+)\s+x\s+(\d+)\s+plane px at\s+\((\d+),\s*(\d+)\)"
        r"\s+of\s+(\d+)\s+x\s+(\d+).*?\(k=([0-9.]+)\)",
        line,
    )
    if match is None:
        raise RuntimeError(f"Crop coverage banner unparseable: {line}")
    return {
        "banner": line,
        "rect_plane": {
            "width": int(match.group(1)),
            "height": int(match.group(2)),
            "x": int(match.group(3)),
            "y": int(match.group(4)),
        },
        "full_plane": {"width": int(match.group(5)), "height": int(match.group(6))},
        "k_printed": match.group(7),
        "k": float(match.group(7)),
    }


def inspect_tiff(path: Path) -> dict[str, Any]:
    import tifffile

    with tifffile.TiffFile(path) as tiff:
        page = tiff.pages[0]
        shape = list(page.shape)
        dtype = str(page.dtype)
    return {
        "output": str(path.resolve()),
        "shape": shape,
        "dtype": dtype,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def run_render(name: str, output: Path, log: Path, cover: str | None) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"{output} exists; refusing implicit overwrite")
    command = command_for(name, output, cover)
    env = render_env()
    cache_before = cache_snapshot(PRIVATE_CACHE)
    clock = time.perf_counter()
    process = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    elapsed = time.perf_counter() - clock
    combined = process.stdout + ("\n" + process.stderr if process.stderr else "")
    log.write_text(
        "$ " + subprocess.list2cmdline(command) + "\n\n" + combined,
        encoding="utf-8",
    )
    cache_after = cache_snapshot(PRIVATE_CACHE)
    record: dict[str, Any] = {
        "name": name,
        "cover_argument": cover,
        "command": command,
        "environment": {
            **THREAD_ENV,
            "PYTHONIOENCODING": "utf-8",
            "STREHL_CACHE_DIR": str(PRIVATE_CACHE.resolve()),
            "other_STREHL_variables": "unset",
        },
        "defaults": DEFAULTS,
        "started_utc": utc_now(),
        "wall_seconds_diagnostic_only": elapsed,
        "returncode": process.returncode,
        "log": str(log.resolve()),
        "selected_banner_lines": selected_banners(combined),
        "cache_before": cache_before,
        "cache_after": cache_after,
        "cache_unchanged": cache_before == cache_after,
    }
    if process.returncode == 0 and output.exists():
        record.update(inspect_tiff(output))
        record["alignment"] = parse_alignment(combined)
        record["coverage"] = (
            parse_crop_coverage(combined) if cover == "crop" else parse_scale_coverage(combined)
        )
    if process.returncode != 0:
        record["stderr_tail"] = process.stderr[-4000:]
    return record


def recover_existing_render(
    name: str,
    output: Path,
    log: Path,
    cover: str,
    preflight_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not output.is_file() or not log.is_file():
        raise RuntimeError(f"{name}: cannot recover an incomplete render pair")
    command = command_for(name, output, cover)
    text = log.read_text(encoding="utf-8")
    expected_first = "$ " + subprocess.list2cmdline(command)
    if text.splitlines()[0] != expected_first:
        raise RuntimeError(f"{name}: existing log command differs from preregistration")
    combined = text.split("\n\n", 1)[1] if "\n\n" in text else text
    total_match = re.search(r"^total\s*:\s*([0-9.]+)\s+s", combined, re.MULTILINE)
    cache_after = cache_snapshot(PRIVATE_CACHE)
    if cache_after != preflight_cache:
        raise RuntimeError(f"{name}: private cache moved during the interrupted render")
    record: dict[str, Any] = {
        "name": name,
        "cover_argument": cover,
        "command": command,
        "environment": {
            **THREAD_ENV,
            "PYTHONIOENCODING": "utf-8",
            "STREHL_CACHE_DIR": str(PRIVATE_CACHE.resolve()),
            "other_STREHL_variables": "unset",
        },
        "defaults": DEFAULTS,
        "started_utc": datetime.fromtimestamp(
            output.stat().st_ctime, timezone.utc
        ).isoformat(),
        "wall_seconds_diagnostic_only": (
            float(total_match.group(1)) if total_match else None
        ),
        "wall_seconds_source": "recovered binary total banner after parser failure",
        "returncode": 0,
        "log": str(log.resolve()),
        "selected_banner_lines": selected_banners(combined),
        "cache_before": preflight_cache,
        "cache_after": cache_after,
        "cache_unchanged": cache_after == preflight_cache,
        "record_recovered_without_rerender": True,
        "recovery_reason": (
            "AMENDMENT-1: binary completed before the original coverage parser raised"
        ),
    }
    record.update(inspect_tiff(output))
    record["alignment"] = parse_alignment(combined)
    record["coverage"] = parse_crop_coverage(combined)
    return record


def baseline_log(name: str) -> str:
    return (BASELINE_OUT / f"{name}.log").read_text(encoding="utf-8")


def same_solve_assertions(name: str, crop: dict[str, Any]) -> dict[str, Any]:
    scale_alignment = parse_alignment(baseline_log(name))
    scale_coverage = parse_scale_coverage(baseline_log(name))
    crop_alignment = crop["alignment"]
    checks = {
        "reference_frame": crop_alignment["reference_frame"]
        == scale_alignment["reference_frame"],
        "placed": crop_alignment["placed"] == scale_alignment["placed"],
        "refused": crop_alignment["refused"] == scale_alignment["refused"],
        "resampler": crop_alignment["resampler"] == scale_alignment["resampler"],
        "coverage_k_printed": crop["coverage"]["k_printed"]
        == scale_coverage["k_printed"],
    }
    return {
        "scale_alignment": scale_alignment,
        "scale_coverage": scale_coverage,
        "checks": checks,
        "all_match": all(checks.values()),
    }


def render() -> int:
    pre = read_json(OUT / "PREFLIGHT.json")
    if sha256(BINARY) != BINARY_SHA256:
        raise RuntimeError("frozen binary moved after preflight")
    if cache_snapshot(PRIVATE_CACHE) != pre["private_cache"]:
        raise RuntimeError("private cache moved after preflight")
    manifest_path = OUT / "RENDER-MANIFEST.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        manifest["resumed_utc"] = utc_now()
    else:
        manifest = {
            "phase": "A_Q1_Q2_ONLY",
            "started_utc": utc_now(),
            "control_required_before_crop": True,
            "control": None,
            "crop_records": [],
            "crop_interpretable": False,
        }
    control_output = RENDERS / f"control-scale-{CONTROL_NAME}.tiff"
    if manifest.get("control") is not None:
        control = manifest["control"]
        if not control_output.is_file() or sha256(control_output) != CONTROL_SHA256:
            raise RuntimeError("existing Scale control no longer matches its frozen hash")
    else:
        control = run_render(
            CONTROL_NAME,
            control_output,
            OUT / f"control-scale-{CONTROL_NAME}.log",
            None,
        )
        control["required_sha256"] = CONTROL_SHA256
        control["hash_matches"] = control.get("sha256") == CONTROL_SHA256
    manifest["control"] = control
    write_json(manifest_path, manifest)
    print(
        f"control {CONTROL_NAME}: rc={control['returncode']} "
        f"sha256={control.get('sha256')}"
    )
    if control["returncode"] != 0 or not control["hash_matches"]:
        manifest["stop_reason"] = "Scale control failed or hash mismatched; Crop not rendered"
        write_json(manifest_path, manifest)
        return 2
    existing = {record["name"]: record for record in manifest["crop_records"]}
    for name in ARMS:
        output = RENDERS / f"{name}.tiff"
        log = OUT / f"{name}.log"
        if name in existing:
            record = existing[name]
            if not output.is_file() or record.get("sha256") != sha256(output):
                raise RuntimeError(f"{name}: manifested output moved")
            continue
        if output.exists():
            record = recover_existing_render(
                name, output, log, "crop", pre["private_cache"]
            )
        else:
            record = run_render(name, output, log, "crop")
        if record["returncode"] == 0:
            record["same_solve_as_frozen_scale"] = same_solve_assertions(name, record)
            rect = record["coverage"]["rect_plane"]
            expected_shape = [2 * rect["height"], 2 * rect["width"], 3]
            record["expected_shape_from_crop_rect"] = expected_shape
            record["shape_matches_crop_rect"] = record["shape"] == expected_shape
        manifest["crop_records"].append(record)
        existing[name] = record
        write_json(manifest_path, manifest)
        print(f"{name}: rc={record['returncode']} shape={record.get('shape')}")
        if record["returncode"] != 0:
            return record["returncode"]
        if not record["cache_unchanged"]:
            raise RuntimeError(f"{name}: private cache changed")
        if not record["same_solve_as_frozen_scale"]["all_match"]:
            raise RuntimeError(f"{name}: solve or coverage k differs from frozen Scale")
        if not record["shape_matches_crop_rect"]:
            raise RuntimeError(f"{name}: TIFF dimensions disagree with Crop rectangle")
    manifest["crop_interpretable"] = True
    manifest["completed_utc"] = utc_now()
    write_json(manifest_path, manifest)
    return 0


def scale_residuals() -> dict[str, dict[str, Any]]:
    data = read_json(BASELINE_OUT / "MEASUREMENTS.json")
    return {
        "m1-bright-a12": data["m1"][0]["geometry_a"],
        "m1-bright-b12": data["m1"][0]["geometry_b"],
        "m1-second-a12": data["m1"][1]["geometry_a"],
        "m1-second-b12": data["m1"][1]["geometry_b"],
        "m2-bright-first16": data["m2"][0]["arms"][0]["geometry"],
        "m2-bright-second16": data["m2"][0]["arms"][1]["geometry"],
        "m2-second-first16": data["m2"][1]["arms"][0]["geometry"],
        "m2-second-second16": data["m2"][1]["arms"][1]["geometry"],
    }


def site_family(name: str, sites: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    if name.startswith("m1-"):
        return "m1.sites", sites["m1"]["sites"]
    if name.startswith("m2-bright-"):
        return "m2.bright_sites", sites["m2"]["bright_sites"]
    return "m2.second_sites", sites["m2"]["second_sites"]


def derive_q2(render_manifest: dict[str, Any]) -> dict[str, Any]:
    sites = read_json(BASELINE_OUT / "SITE-MANIFEST.json")
    input_y, input_x, common_h, common_w = [int(v) for v in sites["input_crop"]]
    rows = []
    for record in render_manifest["crop_records"]:
        name = record["name"]
        rect = record["coverage"]["rect_plane"]
        crop_y = 2 * int(rect["y"])
        crop_x = 2 * int(rect["x"])
        crop_h = 2 * int(rect["height"])
        crop_w = 2 * int(rect["width"])
        shape = record["shape"]
        map_exact = shape == [crop_h, crop_w, 3]
        intersection_h = max(
            0,
            min(crop_y + crop_h, input_y + common_h) - max(crop_y, input_y),
        )
        intersection_w = max(
            0,
            min(crop_x + crop_w, input_x + common_w) - max(crop_x, input_x),
        )
        retained = (intersection_h * intersection_w) / (common_h * common_w)
        family_name, family_sites = site_family(name, sites)
        survived = 0
        for site in family_sites:
            sy0 = input_y + int(site["y"])
            sx0 = input_x + int(site["x"])
            sy1 = sy0 + int(site["height"])
            sx1 = sx0 + int(site["width"])
            survived += (
                crop_y <= sy0
                and crop_x <= sx0
                and sy1 <= crop_y + crop_h
                and sx1 <= crop_x + crop_w
            )
        center_y = crop_y + (crop_h - common_h) // 2 if crop_h >= common_h else None
        center_x = crop_x + (crop_w - common_w) // 2 if crop_w >= common_w else None
        rows.append(
            {
                "name": name,
                "output_shape": shape,
                "native_shape_hwc": [NATIVE_SHAPE[0], NATIVE_SHAPE[1], 3],
                "native_dimensions_match": shape
                == [NATIVE_SHAPE[0], NATIVE_SHAPE[1], 3],
                "large_enough_for_common_shape": shape[0] >= common_h
                and shape[1] >= common_w,
                "crop_rect_plane_xywh": [
                    rect["x"],
                    rect["y"],
                    rect["width"],
                    rect["height"],
                ],
                "crop_rect_fullres_yxhw": [crop_y, crop_x, crop_h, crop_w],
                "exact_integer_scene_mapping_established": map_exact,
                "frozen_common_input_crop_yxhw": [input_y, input_x, common_h, common_w],
                "common_overlap_retained_fraction": retained,
                "common_overlap_retained_percent": 100.0 * retained,
                "contains_entire_frozen_common_overlap": retained == 1.0,
                "output_luma_center_crop_scene_origin_yx": [center_y, center_x],
                "center_crop_origin_equals_frozen_input_crop": [center_y, center_x]
                == [input_y, input_x],
                "site_family": family_name,
                "sites_preregistered": len(family_sites),
                "sites_survived": survived,
                "site_survival_percent": 100.0 * survived / len(family_sites),
            }
        )
    groups = {
        "m1-bright": ("m1-bright-a12", "m1-bright-b12"),
        "m1-second": ("m1-second-a12", "m1-second-b12"),
        "m2-bright": ("m2-bright-first16", "m2-bright-second16"),
        "m2-second": ("m2-second-first16", "m2-second-second16"),
    }
    by_name = {row["name"]: row for row in rows}
    attrition = {}
    for group, names in groups.items():
        survival = [by_name[name]["site_survival_percent"] for name in names]
        attrition[group] = {
            "arms": list(names),
            "survival_percent": survival,
            "differential_attrition_percentage_points": max(survival) - min(survival),
        }
    return {
        "status": "DERIVED_FROM_VERIFIED_INTEGER_CROP_MAPPING",
        "native_active_array_shape_hxw": list(NATIVE_SHAPE),
        "native_active_output_width_x_height": [NATIVE_SHAPE[1], NATIVE_SHAPE[0]],
        "frozen_common_shape_hxw": list(COMMON_SHAPE),
        "site_manifest_input_crop_yxhw": sites["input_crop"],
        "rows": rows,
        "attrition_groups": attrition,
        "all_outputs_large_enough_for_common_shape": all(
            row["large_enough_for_common_shape"] for row in rows
        ),
        "all_outputs_native_size": all(row["native_dimensions_match"] for row in rows),
        "all_common_overlap_retained_at_least_99_percent": all(
            row["common_overlap_retained_percent"] >= 99.0 for row in rows
        ),
        "all_sites_survive_at_least_80_percent": all(
            row["site_survival_percent"] >= 80.0 for row in rows
        ),
        "all_differential_attrition_at_most_2pp": all(
            row["differential_attrition_percentage_points"] <= 2.0
            for row in attrition.values()
        ),
    }


def measure() -> int:
    render_manifest = read_json(OUT / "RENDER-MANIFEST.json")
    if not render_manifest.get("crop_interpretable"):
        raise RuntimeError("Crop is not interpretable because render control did not clear")
    sys.path.insert(0, str(BASELINE))
    import audit_geometry
    import cv2
    import measure as frozen_measure
    import numpy as np

    cv2.setNumThreads(6)
    commissioning = audit_geometry.commission()
    write_json(
        OUT / "GEOMETRY-COMMISSION.json",
        {
            "called_before_real_values": True,
            "opencv_threads": cv2.getNumThreads(),
            "commissioning": commissioning,
        },
    )
    if not commissioning["commissioned"]:
        raise RuntimeError("inherited ECC estimator did not commission")

    crop_residuals: dict[str, dict[str, Any]] = {}
    for name, reference_name in audit_geometry.PAIRS.items():
        try:
            reference = np.load(
                BASELINE_WORK / "input-cache" / reference_name, mmap_mode="r"
            )
            moving = frozen_measure.output_luma(RENDERS / f"{name}.tiff")
            geometry = frozen_measure.geometry(reference, moving)
            geometry.pop("aligned", None)
            crop_residuals[name] = {"status": "MEASURED", **geometry}
        except Exception as error:
            crop_residuals[name] = {
                "status": "MEASURED_EXCEPTION",
                "exception_type": type(error).__name__,
                "exception": str(error),
            }

    audit_geometry.OUT = OUT
    audit_geometry.WORK = BASELINE_WORK
    audit_exception = None
    try:
        audit_geometry.main()
    except Exception as error:
        audit_exception = {"type": type(error).__name__, "message": str(error)}

    crop_audit_path = OUT / "GEOMETRY-AUDIT.json"
    crop_audit = read_json(crop_audit_path) if crop_audit_path.exists() else None
    scale_audit = read_json(BASELINE_OUT / "GEOMETRY-AUDIT.json")
    scale_rows = {row["render"]: row for row in scale_audit["rows"]}
    crop_rows = (
        {row["render"]: row for row in crop_audit["rows"]}
        if crop_audit and "rows" in crop_audit
        else {}
    )
    old_residuals = scale_residuals()
    rows = []
    for name in ARMS:
        crop_ecc = crop_rows.get(name)
        crop_residual = crop_residuals[name]
        crop_all_geometry_pass = bool(
            crop_ecc
            and crop_ecc["scorecard_scale_pass"]
            and crop_ecc["scorecard_rotation_pass"]
            and crop_residual.get("scorecard_geometry_pass")
        )
        rows.append(
            {
                "arm": name,
                "scale_existing_ecc": scale_rows[name],
                "scale_existing_non_translation": old_residuals[name],
                "crop_ecc": crop_ecc,
                "crop_non_translation": crop_residual,
                "crop_all_geometry_clauses_pass": crop_all_geometry_pass,
            }
        )
    result = {
        "status": "MEASURED_POST_SCORE_REJECTION_ONLY",
        "estimator": (
            "Frozen whole-image downsampled affine ECC; post-score rejection-only, "
            "not literal discrete landmarks"
        ),
        "commissioned_before_real_values": True,
        "commissioning": commissioning,
        "audit_geometry_main_called_unchanged": True,
        "audit_geometry_rebindings": {
            "OUT": str(OUT.resolve()),
            "WORK": str(BASELINE_WORK.resolve()),
        },
        "audit_exception": audit_exception,
        "rows": rows,
        "all_crop_geometry_clauses_pass": all(
            row["crop_all_geometry_clauses_pass"] for row in rows
        ),
    }
    write_json(OUT / "Q1-RESULTS.json", result)
    write_json(OUT / "Q2-GEOMETRY.json", derive_q2(render_manifest))
    return 0 if audit_exception is None else 3


def finalize() -> int:
    pre = read_json(OUT / "PREFLIGHT.json")
    frozen_after = snapshot_files(frozen_dependency_paths())
    protected_after = protected_fingerprint()
    result = {
        "checked_utc": utc_now(),
        "frozen_dependencies_before": pre["frozen_dependencies"],
        "frozen_dependencies_after": frozen_after,
        "frozen_dependencies_unchanged": frozen_after == pre["frozen_dependencies"],
        "baseline_cache_before": pre["baseline_cache"],
        "baseline_cache_after": cache_snapshot(BASELINE_WORK / "cache"),
        "baseline_cache_unchanged": cache_snapshot(BASELINE_WORK / "cache")
        == pre["baseline_cache"],
        "private_cache_before": pre["private_cache"],
        "private_cache_after": cache_snapshot(PRIVATE_CACHE),
        "private_cache_unchanged": cache_snapshot(PRIVATE_CACHE) == pre["private_cache"],
        "protected_paths_before": pre["protected_paths"],
        "protected_paths_after": protected_after,
        "protected_paths_unchanged": protected_after == pre["protected_paths"],
    }
    result["all_read_only_guards_pass"] = all(
        (
            result["frozen_dependencies_unchanged"],
            result["baseline_cache_unchanged"],
            result["private_cache_unchanged"],
            result["protected_paths_unchanged"],
        )
    )
    write_json(OUT / "PROVENANCE-AUDIT.json", result)
    if not result["all_read_only_guards_pass"]:
        raise RuntimeError("a frozen or protected path changed since preflight")
    print("provenance audit passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase", choices=("preflight", "render", "measure", "finalize", "all")
    )
    args = parser.parse_args()
    if args.phase == "preflight":
        return preflight()
    if args.phase == "render":
        return render()
    if args.phase == "measure":
        return measure()
    if args.phase == "finalize":
        return finalize()
    code = render()
    if code:
        return code
    code = measure()
    if code:
        return code
    return finalize()


if __name__ == "__main__":
    raise SystemExit(main())
