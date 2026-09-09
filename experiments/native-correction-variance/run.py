"""One fixed synthetic RAW variance-transfer run; root executes after source review."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("correction_process", ROOT/"experiments/m193c-output-grid/bounded-process.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")

assert sys.argv[1:] == [], "one fixed allocation; no parameter sweep"
build = HERE/"build-2"
receipt = json.loads((build/"invocation.json").read_text(encoding="utf-8"))
for entry in receipt["source_files"]:
    assert m.binding(ROOT/entry["path"]) == {k: entry[k] for k in ("bytes", "sha256")}, "compiled source changed"
artifacts = json.loads((build/"executables.json").read_text(encoding="utf-8"))
held = artifacts["cli-tests"]
exe = ROOT/held["path"]
assert m.binding(exe) == {k: held[k] for k in ("bytes", "sha256")}
smoke = json.loads((HERE/"smoke-1/process.json").read_text(encoding="utf-8"))
spent = smoke["job_accounting"]["total_cpu_100ns"]/1e7
assert smoke["exit_code"] == 0 and smoke["error"] is None
out = HERE/"run-1"
out.mkdir()
fields = {"RAYON_NUM_THREADS":"2", "STREHL_FULLRES_GATHER":"1",
          "STREHL_DIRECT_PLANES":"rounded", "STREHL_PROBE_GATHER":"green",
          "STREHL_WARP_WRITEBACK":"parallel", "STREHL_DEFECT":"off",
          "STREHL_CORRECTION_VARIANCE_OUT":str(out/"measurement.json")}
env, removed = m.clean_environment(fields.items())
argv = [str(exe), "--exact",
        "merge_cmd::gatefloor::native_correction_variance::correction_variance_transfer",
        "--ignored", "--nocapture", "--test-threads=1"]
sources = {p.name:m.binding(p) for p in (HERE/"run.py", HERE/"design.md", HERE/"independent-review.md", HERE/"charter.md")}
save(out/"invocation.json", dict(command=argv, overrides=fields, removed_environment=removed,
    executable=held, build=m.binding(build/"invocation.json"), source_revision=receipt["revision"],
    protocol=sources, prior_child_cpu_seconds=spent))
api = m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
result = m.run(argv, env, ROOT, out/"transfer.log", api=api, wall_seconds=120,
    cpu_seconds=120-spent, log_bytes=4<<20, committed_bytes=2<<30)
save(out/"process.json", result)
print(json.dumps({k:result[k] for k in ("exit_code","error","wall_seconds")}), flush=True)
assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"], "preserve failure; no automatic extension"
assert "1 passed" in (out/"transfer.log").read_text(encoding="utf-8")
measurement = json.loads((out/"measurement.json").read_text(encoding="utf-8"))
assert len(measurement["rows"]) == 32
for entry in receipt["source_files"]:
    assert m.binding(ROOT/entry["path"]) == {k: entry[k] for k in ("bytes", "sha256")}
cpu = spent + result["job_accounting"]["total_cpu_100ns"]/1e7
retained = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
assert cpu <= 120 and retained <= 256<<20
save(out/"completion.json", dict(status=measurement["decision"]["status"],
    measurement=m.binding(out/"measurement.json"), aggregate_child_cpu_seconds=cpu,
    wall_seconds=result["wall_seconds"], peak_job_commit_bytes=result["job_memory"]["peak_job_memory_used_bytes"],
    retained_bytes_before_completion=retained, scope="fixed software transfer only; no native photograph or SOTA claim"))
print(json.dumps(measurement["decision"],indent=2),flush=True)
