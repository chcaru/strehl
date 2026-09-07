"""Separate recorded build stamps from unchanged M194b default plan/pixel behavior.

Reader correction only: preserve original-entry-1/result.json's whole-plan
assumption failure and reread its already-rendered TIFF. No subprocess/render.
"""
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
C = runpy.run_path(str(HERE / "consumer-run.py"))
result_path = HERE / "original-entry-1/result.json"
r = C["load"](result_path)
assert not r["passed"] and not r["checks"]["plan_identical"]
assert all(value for key, value in r["checks"].items() if key != "plan_identical")
before = C["sources"]()
assert before == r["sources_before"] == r["sources_after"]
assert C["sha"](r["receipt_path"]) == r["receipt_sha256"]
assert C["sha"](r["baseline_receipt"]) == r["baseline_receipt_sha256"]
a = C["load"](r["receipt_path"])
b = C["load"](r["baseline_receipt"])
assert C["sha"](a["output"]["path"]) == a["output"]["sha256"] == b["output"]["sha256"]
assert C["sha"](b["output"]["path"]) == b["output"]["sha256"]
differences = {key: dict(current=a["plan"].get(key), baseline=b["plan"].get(key))
               for key in a["plan"].keys() | b["plan"].keys() if a["plan"].get(key) != b["plan"].get(key)}
expected = {"software": {"current": "strehl 0.0.0 (5f55c9ee7dc1-dirty)",
                         "baseline": "strehl 0.0.0 (444eb759be03-dirty)"}}
assert differences == expected
checks = dict(r["checks"])
del checks["plan_identical"]
checks["all_plan_fields_other_than_build_stamp_identical"] = differences == expected
checks["receipt_and_actual_tiff_bindings_rechecked"] = True
checks["sources_unchanged"] = before == C["sources"]()
record = dict(schema="m194d-original-entry-recheck-v1", passed=all(checks.values()),
              original_result=str(result_path), original_result_sha256=C["sha"](result_path),
              original_whole_plan_failure_preserved=True, no_rerender=True,
              driver_sha256=C["sha"](__file__), differences=differences,
              scope="Original unselected entry default pixels; recorded executable build stamp is permitted to identify the new build.",
              checks=checks, output=a["output"], build_record=r["build_record"], build_sha256=r["build_sha256"])
out = HERE / "original-entry-1/recheck.json"
C["write_new"](out, record)
print(json.dumps({"passed": record["passed"], "record": str(out), "sha256": C["sha"](out)}))
