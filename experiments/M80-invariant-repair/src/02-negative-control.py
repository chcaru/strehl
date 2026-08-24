"""Byte-confirmed red/restore/green control for M80's noise-null test."""

from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "crates" / "strehl-cli" / "src" / "merge_cmd.rs"
WORK = HERE.parent / "control-work"
BACKUP = WORK / "merge_cmd.rs.backup"
OUT = HERE.parent / "out" / "02-negative-control.log"
TARGET = HERE.parent / "target-m80-control"
MARKER = b"M80_NEGATIVE_CONTROL"
ANCHOR = (
    b"    let (scale_for_detail_left, scale_for_detail_right) = "
    b"(scale_right, scale_left); // M80_CROSS_FITTED_SCALES"
)
REPLACEMENT = (
    b"    let (scale_for_detail_left, scale_for_detail_right) = "
    b"(1.0, 1.0); // M80_NEGATIVE_CONTROL"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_test() -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(TARGET)
    return subprocess.run(
        [
            "cargo",
            "test",
            "--manifest-path",
            str(ROOT / "Cargo.toml"),
            "-p",
            "strehl-cli",
            "--bin",
            "strehl",
            "selection_noise_null_is_not_a_retention_target_across_frame_counts",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if BACKUP.exists():
        raise RuntimeError(f"refusing to overwrite stale backup: {BACKUP}")
    original = SOURCE.read_bytes()
    if original.count(ANCHOR) != 1:
        raise RuntimeError(
            f"plant anchor count is {original.count(ANCHOR)}, expected exactly 1"
        )
    BACKUP.write_bytes(original)
    lines = [
        f"MEASURED: backup bytes={len(original)} sha256={sha256(original)}",
    ]
    red: subprocess.CompletedProcess[str] | None = None
    restored_ok = False
    try:
        planted = original.replace(ANCHOR, REPLACEMENT)
        if planted.count(MARKER) != 1 or planted.count(REPLACEMENT) != 1:
            raise RuntimeError("constructed plant does not contain one exact replacement")
        SOURCE.write_bytes(planted)
        reread = SOURCE.read_bytes()
        exact = reread == planted and reread.count(REPLACEMENT) == 1
        lines.append(
            "MEASURED: planted bytes "
            f"sha256={sha256(reread)} marker_count={reread.count(MARKER)} "
            f"exact_fragment_count={reread.count(REPLACEMENT)} exact_match={exact}"
        )
        if not exact:
            raise RuntimeError("read-back bytes do not match the constructed plant")
        red = run_test()
        lines.append(f"MEASURED: planted cargo exit={red.returncode}")
        lines.append("--- planted cargo output ---")
        lines.append(red.stdout.rstrip())
        lines.append("--- end planted cargo output ---")
    finally:
        restored = BACKUP.read_bytes()
        SOURCE.write_bytes(restored)
        os.utime(SOURCE, None)
        BACKUP.unlink()
        restored_bytes = SOURCE.read_bytes()
        restored_ok = restored_bytes == original
        lines.append(
            "MEASURED: restored bytes "
            f"sha256={sha256(restored_bytes)} exact_match={restored_ok} "
            f"backup_removed={not BACKUP.exists()}"
        )

    green = run_test()
    lines.append(f"MEASURED: restored cargo exit={green.returncode}")
    lines.append("--- restored cargo output ---")
    lines.append(green.stdout.rstrip())
    lines.append("--- end restored cargo output ---")

    red_output = "" if red is None else red.stdout
    red_ok = (
        red is not None
        and red.returncode != 0
        and "noise null N=22" in red_output
        and (
            "selector target must be NOT-MEASURABLE" in red_output
            or "STRUCTURE must read 1" in red_output
        )
        and "Compiling strehl-cli" in red_output
    )
    green_ok = (
        restored_ok
        and green.returncode == 0
        and (
            "selection_noise_null_is_not_a_retention_target_across_frame_counts ... ok"
            in green.stdout
        )
        and "Compiling strehl-cli" in green.stdout
    )
    lines.append(f"MEASURED: red control pass={red_ok}")
    lines.append(f"MEASURED: restored green pass={green_ok}")
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text, end="")
    if not red_ok or not green_ok:
        raise SystemExit("M80 negative control failed")


if __name__ == "__main__":
    main()
