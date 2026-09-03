from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from common import OUT, ROOT, SCORECARD, SOURCE_COMMIT, WORK, sha256, write_json


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    log: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "$ " + subprocess.list2cmdline(command) + "\n\n"
            + process.stdout
            + ("\n[stderr]\n" + process.stderr if process.stderr else ""),
            encoding="utf-8",
        )
    if process.returncode:
        raise RuntimeError(
            f"{subprocess.list2cmdline(command)} failed rc={process.returncode}\n"
            f"{process.stderr[-4000:]}"
        )
    return process


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source = WORK / "source"
    target = WORK / "target"
    binary_dir = WORK / "bin"
    if source.exists():
        shutil.rmtree(source)
    if target.exists():
        shutil.rmtree(target)
    source.mkdir(parents=True)
    binary_dir.mkdir(parents=True, exist_ok=True)

    archive = WORK / "source.tar"
    run(
        [
            "git",
            "--no-pager",
            "archive",
            "--format=tar",
            f"--output={archive}",
            SOURCE_COMMIT,
        ],
        cwd=ROOT,
        log=OUT / "freeze-archive.log",
    )
    run(["tar", "-xf", str(archive), "-C", str(source)], log=OUT / "freeze-extract.log")
    archive.unlink()

    env = os.environ.copy()
    env.update(
        {
            "CARGO_BUILD_JOBS": "8",
            "RAYON_NUM_THREADS": "8",
            "STREHL_BUILD_ID": SOURCE_COMMIT[:12],
            "CARGO_TERM_COLOR": "never",
        }
    )
    run(
        [
            "cargo",
            "build",
            "--release",
            "--jobs",
            "8",
            "--manifest-path",
            str(source / "Cargo.toml"),
            "--target-dir",
            str(target),
        ],
        cwd=source,
        env=env,
        log=OUT / "freeze-build.log",
    )
    built = target / "release" / "strehl.exe"
    if not built.exists():
        raise RuntimeError(f"build succeeded but {built} is absent")
    binary = binary_dir / "strehl.exe"
    shutil.copy2(built, binary)
    version = run([str(binary), "--version"]).stdout.strip()
    help_text = run([str(binary), "stack", "--help"]).stdout

    power = run(["powercfg", "/GETACTIVESCHEME"]).stdout.strip()
    cargo = run(["cargo", "--version"]).stdout.strip()
    rustc = run(["rustc", "--version"]).stdout.strip()
    run_manifest = {
        "scorecard": {
            "path": str(SCORECARD.relative_to(ROOT)),
            "sha256": sha256(SCORECARD),
            "version": "v1.1",
        },
        "source": {
            "commit": SOURCE_COMMIT,
            "archive_command": f"git archive --format=tar {SOURCE_COMMIT}",
            "working_tree_source_used": False,
        },
        "binary": {
            "runtime_path": str(binary),
            "sha256": sha256(binary),
            "version": version,
            "build_command": (
                "cargo build --release --jobs 8 "
                f"--manifest-path {source / 'Cargo.toml'} --target-dir {target}"
            ),
            "build_id_override": SOURCE_COMMIT[:12],
        },
        "host": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": sys.version,
            "power_plan": power,
            "cargo": cargo,
            "rustc": rustc,
        },
        "thread_cap": {
            "exploratory_max": 8,
            "cargo_jobs": 8,
            "rayon_threads": 8,
            "quality_pyramid_workers_override": None,
        },
        "quality_product_arm": {
            "input": "original ARW subsets",
            "command_flags": ["--linear-srgb", "--demosaic"],
            "merge": "shipping default inferred by CLI",
            "alignment": "shipping default",
            "cover": "shipping default scale",
            "cache_root": str(WORK / "cache"),
            "purpose": "native-RAW product diagnostic, not the absent common-TIFF arm",
        },
        "capability_preflight": {
            "stack_help_mentions_prophoto": "prophoto" in help_text.lower(),
            "stack_help_mentions_tiff_input": (
                "tiff input" in help_text.lower() or "directory of tiff" in help_text.lower()
            ),
            "stack_help_mentions_linear_srgb": "--linear-srgb" in help_text,
            "stack_help_mentions_depth_output": "depth map" in help_text.lower(),
            "stack_help_mentions_confidence_map": "--confidence-map" in help_text,
            "stack_help_mentions_n_eff_map": "--n-eff-map" in help_text,
        },
        "timing": {
            "m11_m12_run": False,
            "reason": "quiet machine-wide window not yet available",
            "requested_window_minutes": [90, 120],
        },
    }
    write_json(OUT / "RUN-MANIFEST.json", run_manifest)
    print(f"frozen {version}")
    print(f"binary sha256 {run_manifest['binary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
