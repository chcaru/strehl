from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import tifffile

from common import OUT, ROOT, WORK, read_json, sha256, write_json


BEE = Path(r"D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light")
GROUPS = {
    "m1-bright-a12": list(range(336, 348)),
    "m1-bright-b12": list(range(348, 360)),
    "m1-second-a12": list(range(592, 604)),
    "m1-second-b12": list(range(604, 616)),
    "m2-bright-first16": list(range(328, 344)),
    "m2-bright-second16": list(range(344, 360)),
    "m2-second-first16": list(range(584, 600)),
    "m2-second-second16": list(range(600, 616)),
}
REQUIRED_COMMITTED = (
    "experiments/SCORECARD-BASELINE/out/INPUT-MANIFEST.json",
    "experiments/SCORECARD-BASELINE/out/SITE-MANIFEST.json",
    "experiments/SCORECARD-BASELINE/out/RUN-MANIFEST.json",
    "experiments/SCORECARD-BASELINE/out/commission.json",
)


def require_prerender_commit() -> str:
    for relative in REQUIRED_COMMITTED:
        process = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if process.returncode:
            raise RuntimeError(f"{relative} is not committed; refusing first score render")
    status = subprocess.run(
        [
            "git",
            "--no-pager",
            "status",
            "--porcelain",
            "--",
            "experiments/SCORECARD-BASELINE",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    if status.strip():
        raise RuntimeError(
            "SCORECARD-BASELINE has uncommitted pre-render changes; refusing render:\n" + status
        )
    return subprocess.run(
        [
            "git",
            "--no-pager",
            "log",
            "-1",
            "--format=%H",
            "--",
            "experiments/SCORECARD-BASELINE/out/RUN-MANIFEST.json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def materialize_group(name: str, numbers: list[int]) -> tuple[Path, str]:
    directory = WORK / "inputs" / name
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    mode = "symlink"
    for number in numbers:
        source = BEE / f"DSC{number:05d}.ARW"
        destination = directory / source.name
        try:
            os.symlink(source, destination)
        except OSError:
            mode = "copy"
            shutil.copy2(source, destination)
    return directory, mode


def selected_log_lines(text: str) -> list[str]:
    prefixes = (
        "build",
        "backend",
        "camera",
        "frames",
        "geometry",
        "alignment",
        "  held-out",
        "  coverage",
        "memory",
        "folded",
        "timings",
        "output",
    )
    return [
        line
        for line in text.splitlines()
        if any(line.lstrip().lower().startswith(prefix.strip().lower()) for prefix in prefixes)
    ]


def main() -> int:
    prereg_commit = require_prerender_commit()
    run_manifest = read_json(OUT / "RUN-MANIFEST.json")
    binary = Path(run_manifest["binary"]["runtime_path"])
    if not binary.exists() or sha256(binary) != run_manifest["binary"]["sha256"]:
        raise RuntimeError("frozen binary is absent or its hash moved")

    outputs = OUT / "renders"
    outputs.mkdir(parents=True, exist_ok=True)
    cache = WORK / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "RAYON_NUM_THREADS": "8",
            "OMP_NUM_THREADS": "8",
            "OPENBLAS_NUM_THREADS": "8",
            "MKL_NUM_THREADS": "8",
            "NUMEXPR_NUM_THREADS": "8",
            "STREHL_CACHE_DIR": str(cache),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    env.pop("STREHL_PYRAMID_WORKERS", None)

    records = []
    for name, numbers in GROUPS.items():
        directory, materialization = materialize_group(name, numbers)
        output = outputs / f"{name}.tiff"
        log = OUT / f"{name}.log"
        if output.exists():
            raise RuntimeError(f"{output} already exists; refusing an implicit re-render")
        command = [
            str(binary),
            "stack",
            str(directory),
            "--out",
            str(output),
            "--linear-srgb",
            "--demosaic",
        ]
        started = datetime.now(timezone.utc).isoformat()
        clock = time.perf_counter()
        process = subprocess.run(command, env=env, text=True, capture_output=True)
        elapsed = time.perf_counter() - clock
        combined = process.stdout + ("\n" + process.stderr if process.stderr else "")
        log.write_text(
            "$ " + subprocess.list2cmdline(command) + "\n\n" + combined,
            encoding="utf-8",
        )
        record = {
            "name": name,
            "frames": numbers,
            "input_directory": str(directory),
            "materialization": materialization,
            "command": command,
            "started_utc": started,
            "wall_seconds_diagnostic_only": elapsed,
            "returncode": process.returncode,
            "log": str(log),
            "selected_banner_lines": selected_log_lines(combined),
        }
        if process.returncode == 0 and output.exists():
            with tifffile.TiffFile(output) as tiff:
                page = tiff.pages[0]
                record["shape"] = list(page.shape)
                record["dtype"] = str(page.dtype)
            record.update(
                {
                    "output": str(output),
                    "size": output.stat().st_size,
                    "sha256": sha256(output),
                }
            )
        records.append(record)
        write_json(
            OUT / "RENDER-MANIFEST.json",
            {
                "prerender_commit": prereg_commit,
                "timings_are_score_values": False,
                "reason": "quality renders ran under shared-machine contention",
                "records": records,
            },
        )
        print(f"{name}: rc={process.returncode} elapsed={elapsed:.1f}s")
        if process.returncode:
            print(combined[-4000:], file=sys.stderr)
            return process.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
