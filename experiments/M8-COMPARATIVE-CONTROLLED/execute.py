from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from common import (
    CHECKER,
    COMPARATOR,
    EXPECTED,
    ROOT,
    atomic_json,
    bounded_environment,
    byte_sha256,
    canonicalize_with_icc,
    comparator_command,
    linear_rec2020_icc,
    pixel_sha256,
    read_rgb16,
    sha256,
    tiff_tags,
)
from identity_adapter import build_state, final_output, summarize


OUTPUT = ROOT / "output"
STATE = ROOT / "checker-state"


def load_admitted_inputs() -> tuple[dict, list[Path], dict]:
    controls_path = ROOT / "controls" / "PASS.json"
    manifest_path = ROOT / "prepared-manifest.json"
    if not controls_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("controls PASS and prepared manifest are both required")
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if controls.get("status") != "PASS" or manifest.get("status") != "PREPARED":
        raise RuntimeError("controls or preparation is not admitted")
    if sha256(COMPARATOR) != EXPECTED["comparator_sha256"]:
        raise RuntimeError("comparator binary changed")
    if sha256(CHECKER) != EXPECTED["checker_sha256"]:
        raise RuntimeError("commissioned checker changed")
    inputs = []
    errors = []
    icc_hash = controls["icc"]["sha256"]
    for row in manifest["frames"]:
        path = Path(row["prepared_path"])
        inputs.append(path)
        if not path.is_file():
            errors.append(f"missing {path}")
            continue
        image = read_rgb16(path)
        tags = tiff_tags(path)
        if sha256(path) != row["prepared"]["file_sha256"]:
            errors.append(f"file hash changed: {path.name}")
        if pixel_sha256(image) != row["prepared"]["pixel_sha256"]:
            errors.append(f"pixel hash changed: {path.name}")
        if list(image.shape) != [
            EXPECTED["crop"]["height"],
            EXPECTED["crop"]["width"],
            3,
        ]:
            errors.append(f"shape changed: {path.name}")
        if tags["orientation"] != 1 or tags["icc_sha256"] != icc_hash:
            errors.append(f"orientation/profile changed: {path.name}")
    if len(inputs) != EXPECTED["frames"]:
        errors.append(f"input count {len(inputs)}, expected {EXPECTED['frames']}")
    admission = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "frames": len(inputs),
        "icc_sha256": icc_hash,
    }
    atomic_json(ROOT / "prelaunch-admission.json", admission)
    if errors:
        raise RuntimeError("prelaunch admission failed: " + "; ".join(errors[:5]))
    return manifest, inputs, controls


def render() -> dict:
    manifest, inputs, controls = load_admitted_inputs()
    OUTPUT.mkdir(exist_ok=True)
    direct = OUTPUT / "focus-stack-direct.tif"
    canonical = OUTPUT / "focus-stack-canonical.tif"
    direct.unlink(missing_ok=True)
    canonical.unlink(missing_ok=True)
    help_run = subprocess.run(
        [str(COMPARATOR), "--help"],
        cwd=OUTPUT,
        env=bounded_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    help_text = help_run.stdout + help_run.stderr
    help_path = ROOT / "focus-stack-help.txt"
    help_path.write_text(help_text, encoding="utf-8")
    control_help_hash = controls["command"]["help_sha256"]
    help_hash = byte_sha256(help_text.encode("utf-8"))
    if help_hash != control_help_hash:
        raise RuntimeError("focus-stack help text changed since controls")
    command = comparator_command(inputs, direct)
    run = subprocess.run(
        command,
        cwd=OUTPUT,
        env=bounded_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout_path = ROOT / "focus-stack.stdout.txt"
    stderr_path = ROOT / "focus-stack.stderr.txt"
    stdout_path.write_text(run.stdout, encoding="utf-8")
    stderr_path.write_text(run.stderr, encoding="utf-8")
    command_record = {
        "command": command,
        "cwd": str(OUTPUT.resolve()),
        "binary": str(COMPARATOR),
        "binary_sha256": sha256(COMPARATOR),
        "help_path": str(help_path.resolve()),
        "help_sha256": help_hash,
        "returncode": run.returncode,
        "stdout_path": str(stdout_path.resolve()),
        "stdout_sha256": sha256(stdout_path),
        "stderr_path": str(stderr_path.resolve()),
        "stderr_sha256": sha256(stderr_path),
        "prepared_manifest_sha256": sha256(ROOT / "prepared-manifest.json"),
    }
    atomic_json(ROOT / "focus-stack-command.json", command_record)
    if run.returncode != 0 or not direct.is_file():
        raise RuntimeError(f"focus-stack subject render failed: {run.returncode}")
    canonical_record = canonicalize_with_icc(
        direct, canonical, linear_rec2020_icc()
    )
    direct_tags = canonical_record["direct_tags"]
    canonical_tags = canonical_record["canonical_tags"]
    errors = []
    expected_shape = [
        EXPECTED["crop"]["height"],
        EXPECTED["crop"]["width"],
        3,
    ]
    if canonical_tags["shape"] != expected_shape:
        errors.append(
            f"output shape {canonical_tags['shape']}, expected {expected_shape}"
        )
    if canonical_tags["dtype"] != "uint16":
        errors.append(f"output dtype {canonical_tags['dtype']}, expected uint16")
    if canonical_tags["orientation"] != 1:
        errors.append(f"output orientation {canonical_tags['orientation']}")
    if canonical_tags["compression"] != "NONE":
        errors.append(f"canonical compression {canonical_tags['compression']}")
    if canonical_tags["icc_sha256"] != controls["icc"]["sha256"]:
        errors.append("canonical output ICC differs from commissioned input ICC")
    if not canonical_record["pixel_array_unchanged"]:
        errors.append("ICC canonicalization changed samples")
    # For this CLI there is no adjusted-plane export. Admission therefore rests
    # on the documented true bypass plus the full-size, same-N pixel witness.
    if controls["green"]["pass"] is not True:
        errors.append("same-build same-N output-grid witness did not pass")
    admission = {
        "status": "PASS" if not errors else "UNMEASURED",
        "errors": errors,
        "boundary": (
            "The 92 canonical prepared TIFF arrays. Comparator placement is "
            "identity by --no-align true bypass, commissioned on the same "
            "binary, options, dimensions, source count, and output path."
        ),
        "default_product_claim": False,
        "direct_tags": direct_tags,
        "canonical_tags": canonical_tags,
        "canonicalization": canonical_record,
        "command": command_record,
    }
    atomic_json(ROOT / "subject-admission.json", admission)
    if errors:
        raise RuntimeError("subject admission failed: " + "; ".join(errors))
    print(json.dumps({"status": "RENDERED_AND_ADMITTED"}, indent=2))
    return admission


def measure() -> dict:
    admission_path = ROOT / "subject-admission.json"
    if not admission_path.is_file():
        raise RuntimeError("subject has not passed admission")
    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    if admission.get("status") != "PASS":
        raise RuntimeError("subject admission is not PASS")
    manifest, inputs, _ = load_admitted_inputs()
    canonical = OUTPUT / "focus-stack-canonical.tif"
    if not canonical.is_file():
        raise RuntimeError("canonical output missing")
    build = build_state(inputs, STATE, EXPECTED["subject"], ROOT / "work" / "blocks")
    result = final_output(STATE, canonical)
    summary = summarize(STATE, canonical, ROOT / "m8-summary.json")
    payload = {
        "status": "MEASURED",
        "candidate_only": True,
        "scoreable": False,
        "subject": EXPECTED["subject"],
        "frames": EXPECTED["frames"],
        "prepared_manifest_sha256": sha256(ROOT / "prepared-manifest.json"),
        "admission_sha256": sha256(admission_path),
        "adapter": build,
        "checker_result": result,
        "summary": summary,
    }
    atomic_json(ROOT / "result.json", payload)
    print(json.dumps({"status": "MEASURED", "result": str(ROOT / "result.json")}, indent=2))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["render", "measure", "all"])
    args = parser.parse_args()
    if args.operation in {"render", "all"}:
        render()
    if args.operation in {"measure", "all"}:
        measure()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        atomic_json(
            ROOT / "UNMEASURED.json",
            {"status": "UNMEASURED", "error": f"{type(error).__name__}: {error}"},
        )
        raise
