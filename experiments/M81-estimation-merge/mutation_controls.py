"""Plant and verify M81's two required source mutations, then restore bytes."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = REPO / "crates" / "strehl-core" / "src" / "calibration.rs"
BACKUP = HERE / "calibration.rs.mutation-backup"
LOG = HERE / "mutation-controls.log"

MUTATIONS = (
    (
        "spectral-clip",
        b"let sum: f64 = signal.iter().copied().sum();",
        b"let sum: f64 = signal.iter().copied().map(|s| s.max(0.0)).sum();",
        "summing_before_clipping_returns_zero_on_the_noise_plant",
    ),
    (
        "reverse-cumulative",
        b"cumulative += count;",
        b"cumulative = cumulative.saturating_sub(count);",
        "admission_histogram_solves_the_measured_monotone_ladder",
    ),
)


def run() -> None:
    original = SOURCE.read_bytes()
    BACKUP.write_bytes(original)
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(HERE / "target-dev")
    records = []
    try:
        for name, old, planted, test in MUTATIONS:
            if original.count(old) != 1:
                raise RuntimeError(f"{name}: expected one source match, found {original.count(old)}")
            modified = original.replace(old, planted)
            SOURCE.write_bytes(modified)
            readback = SOURCE.read_bytes()
            if readback.count(planted) != 1 or old in readback:
                raise RuntimeError(f"{name}: planted bytes failed read-back")
            command = [
                "cargo",
                "test",
                "-p",
                "strehl-core",
                f"calibration::tests::{test}",
                "--",
                "--exact",
            ]
            proc = subprocess.run(
                command,
                cwd=REPO,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            records.append(
                "\n".join(
                    [
                        f"CONTROL={name}",
                        f"PLANTED_READBACK=PASS bytes={planted.decode('ascii')}",
                        f"COMMAND={' '.join(command)}",
                        f"EXIT={proc.returncode}",
                        proc.stdout,
                        proc.stderr,
                    ]
                )
            )
            if "running 1 test" not in proc.stdout or "running 0 tests" in proc.stdout:
                raise RuntimeError(f"{name}: cargo did not execute exactly one test")
            if proc.returncode == 0:
                raise RuntimeError(f"{name}: planted mutation did not make its test fail")
            SOURCE.write_bytes(original)
            if SOURCE.read_bytes() != original:
                raise RuntimeError(f"{name}: source did not restore byte-for-byte")
    finally:
        SOURCE.write_bytes(original)
        if BACKUP.exists():
            BACKUP.unlink()
        LOG.write_text("\n\n".join(records) + "\n", encoding="utf-8")
    if SOURCE.read_bytes() != original:
        raise RuntimeError("source differs after mutation controls")
    print("mutation controls: 2/2 planted, read back, rejected, and restored")


if __name__ == "__main__":
    run()
