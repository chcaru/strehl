"""Plant an invalid B6 ROI, prove registration fails, then restore and pass."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
SPEC = HERE / "spec_v1.py"
VALIDATOR = HERE / "validate_heldout.py"
MARKER = b"M78B_NEGATIVE_CONTROL"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_plant(original: bytes) -> bytes:
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    anchor = newline.join((
        b"        out.append((x, y, side, side))",
        b"    return out",
        b"",
        b"",
        b"def roi_padded_bounds",
    ))
    replacement = newline.join((
        b"        out.append((x, y, side, side))",
        b"    out[-1] = (916, 2402, 512, 512)  # " + MARKER,
        b"    return out",
        b"",
        b"",
        b"def roi_padded_bounds",
    ))
    if original.count(anchor) != 1:
        raise RuntimeError(
            f"plant anchor count is {original.count(anchor)}, expected exactly 1")
    planted = original.replace(anchor, replacement)
    if planted.count(MARKER) != 1 or planted.count(replacement) != 1:
        raise RuntimeError("constructed plant bytes do not contain one exact replacement")
    return planted


def run_validator(json_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--json", str(json_path)],
        cwd=EXPERIMENT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log",
        type=Path,
        default=EXPERIMENT / "out" / "m78b_negative_control.log",
    )
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    backup_path = EXPERIMENT / "out" / "m78b_spec_v1_backup.py"
    invalid_json = EXPERIMENT / "out" / "m78b_negative_control_invalid.json"
    valid_json = EXPERIMENT / "out" / "m78b_heldout_geometry.json"
    lines: list[str] = []

    def record(text: str) -> None:
        lines.append(text)
        print(text)

    original = SPEC.read_bytes()
    if backup_path.exists():
        raise RuntimeError(f"refusing to overwrite stale backup: {backup_path}")
    backup_path.write_bytes(original)
    record(f"MEASURED: backup bytes={len(original)} sha256={sha256(original)}")

    negative_ok = False
    try:
        planted = build_plant(original)
        SPEC.write_bytes(planted)
        reread = SPEC.read_bytes()
        exact_fragment = (
            b"    out[-1] = (916, 2402, 512, 512)  # "
            + MARKER
        )
        fragment_count = reread.count(exact_fragment)
        exact_match = reread == planted and fragment_count == 1
        record(
            "MEASURED: planted bytes "
            f"sha256={sha256(reread)} marker_count={reread.count(MARKER)} "
            f"exact_fragment_count={fragment_count} exact_match={exact_match}")
        if not exact_match:
            raise RuntimeError("read-back bytes did not match the constructed plant")

        negative = run_validator(invalid_json)
        record(f"MEASURED: planted validator exit={negative.returncode}")
        record("--- planted validator output ---")
        record(negative.stdout.rstrip())
        record("--- end planted validator output ---")
        required = (
            "roi_index=3",
            "roi=(916, 2402, 512, 512)",
            "y1=2946",
            "required_raw_extent=(5892, 2920)",
            "visible_raw_shape=(4688, 7028)",
            "ROI bounds checks: 0/24",
            "substrate NOT VALID",
        )
        missing = [text for text in required if text not in negative.stdout]
        negative_ok = negative.returncode != 0 and not missing
        record(
            f"MEASURED: planted failure nonzero={negative.returncode != 0} "
            f"missing_required_diagnostics={missing} pass={negative_ok}")
    finally:
        restored = backup_path.read_bytes()
        SPEC.write_bytes(restored)
        backup_path.unlink()
        restored_ok = SPEC.read_bytes() == original
        record(
            "MEASURED: restored bytes "
            f"sha256={sha256(SPEC.read_bytes())} exact_match={restored_ok} "
            f"backup_removed={not backup_path.exists()}")

    green = run_validator(valid_json)
    record(f"MEASURED: restored validator exit={green.returncode}")
    record("--- restored validator output ---")
    record(green.stdout.rstrip())
    record("--- end restored validator output ---")
    green_required = ("ROI bounds checks: 24/24", "substrate VALID")
    green_missing = [text for text in green_required if text not in green.stdout]
    green_ok = green.returncode == 0 and not green_missing
    record(
        f"MEASURED: restored green missing_required_diagnostics={green_missing} "
        f"pass={green_ok}")
    overall = negative_ok and restored_ok and green_ok
    record(f"DERIVED: M78b negative control pass={overall}")
    args.log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
