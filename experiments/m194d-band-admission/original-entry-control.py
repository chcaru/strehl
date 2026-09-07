"""Render the preregistered original M194b default entry using a new pinned CLI."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C = runpy.run_path(str(HERE / "consumer-run.py"))
BASELINE = ROOT / "experiments/m194c-probe-layout/candidate-2/run/run-index.json"
BASELINE_SHA = "71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab"
TEST = "merge_cmd::known_scene_benchmark::m194b_known_scene_consumer"


def bound(path, digest):
    path = Path(path)
    if C["sha"](path) != digest:
        raise ValueError(f"external binding changed: {path}")
    return C["load"](path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-record", required=True, type=Path)
    parser.add_argument("--build-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build = bound(args.build_record, args.build_sha256)
    assert build["schema"] == "m194d-consumer-build-v1" and build["pass"]
    before = C["sources"]()
    assert before == build["sources_after"] == build["sources_before"]
    for item in [build["test_executable"], build["compiler_artifact"]]:
        path = Path(item["path"])
        assert C["sha"](path) == item["sha256"] and path.stat().st_size == item["bytes"]
    baseline = bound(BASELINE, BASELINE_SHA)
    case = next(c for c in baseline["cases"] if c["scene"] == "plane" and not c["noise_enabled"])
    arm = next(a for a in case["arms"] if a["name"] == "full9")
    original_receipt_path = BASELINE.parent / arm["receipt_path"]
    original = bound(original_receipt_path, arm["receipt_sha256"])
    original_output = original["output"]
    assert C["sha"](original_output["path"]) == original_output["sha256"]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    plan, receipt, image = out / "plan.json", out / "receipt.json", out / "output.tiff"
    env = C["controlled_env"]()
    env.update(STREHL_M194B_MANIFEST=case["manifest_path"],
               STREHL_M194B_MANIFEST_SHA256=case["manifest_sha256"],
               STREHL_M194B_PLAN=str(plan))
    assert not any(k.startswith("STREHL_M194D") for k in env)
    commands = []
    for mode in ["plan", "render"]:
        env["STREHL_M194B_MODE"] = mode
        if mode == "render":
            env.update(STREHL_M194B_PLAN_SHA256=C["sha"](plan),
                       STREHL_M194B_SUBSET="all", STREHL_M194B_OUTPUT=str(image),
                       STREHL_M194B_RECEIPT=str(receipt))
        command = [build["test_executable"]["path"], "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
        started = datetime.now(timezone.utc).isoformat()
        process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
        ended = datetime.now(timezone.utc).isoformat()
        raw = process.stdout + process.stderr
        log = out / (mode + "-command.log")
        log.write_bytes(raw)
        record = dict(command=command, started_utc=started, ended_utc=ended,
                      exit_code=process.returncode, log=str(log), log_sha256=C["sha"](log),
                      environment={k: v for k, v in env.items() if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"},
                      passed=process.returncode == 0 and b"1 passed; 0 failed" in raw)
        C["write_new"](out / (mode + "-command.json"), record)
        commands.append(record)
        if not record["passed"]:
            raise RuntimeError("original entry failed; preserved " + str(log))
    actual = C["load"](receipt)
    checks = dict(original_plan_schema=C["load"](plan)["schema"] == "m194b-consumer-plan-v1",
                  original_receipt_schema=actual["schema"] == "m194b-consumer-receipt-v1",
                  plan_identical=actual["plan"] == original["plan"],
                  whole_tiff_identical=C["sha"](image) == original_output["sha256"],
                  decoded_pixel_hash_identical=actual["output"]["pixel_sha256_le"] == original_output["pixel_sha256_le"],
                  output_metadata_identical=all(actual["output"][key] == original_output[key]
                      for key in ["bytes", "width", "height", "channels", "sample_type", "software"]),
                  unselected_admission_environment=not any(k.startswith("STREHL_M194D") for k in env),
                  each_original_frame_decoded_once=actual["decode_counts"] == [1] * 9,
                  sources_unchanged=before == C["sources"](),
                  baseline_tiff_unchanged=C["sha"](original_output["path"]) == original_output["sha256"])
    result = dict(schema="m194d-original-entry-control-v1", checks=checks, passed=all(checks.values()),
                  build_record=str(args.build_record.resolve()), build_sha256=args.build_sha256,
                  driver_sha256=C["sha"](__file__), baseline_index=str(BASELINE), baseline_index_sha256=BASELINE_SHA,
                  baseline_receipt=str(original_receipt_path), baseline_receipt_sha256=arm["receipt_sha256"],
                  commands=commands, receipt_path=str(receipt), receipt_sha256=C["sha"](receipt),
                  output=actual["output"], sources_before=before, sources_after=C["sources"]())
    C["write_new"](out / "result.json", result)
    print(json.dumps({"passed": result["passed"], "checks": checks, "result": str(out / "result.json")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
