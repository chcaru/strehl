"""Run exactly one fixed native GPU gather controls after source freeze."""
from pathlib import Path
import importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("gpu_gather_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def save(path,value):
    with path.open("x",encoding="utf-8") as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write("\n")
assert sys.argv[1:]==[],"one fixed allocation, no sweep"
build=HERE/"build-4"
receipt=json.loads((build/"invocation.json").read_text(encoding="utf-8"))
def check_sources():
    for e in receipt["source_files"]:
        assert m.binding(ROOT/e["path"])=={k:e[k] for k in ("bytes","sha256")},"compiled source changed"
check_sources()
held=json.loads((build/"executables.json").read_text(encoding="utf-8"))["cli-tests"]
exe=ROOT/held["path"];assert m.binding(exe)=={k:held[k] for k in ("bytes","sha256")}
out=HERE/"run-2";out.mkdir()
fields={"RAYON_NUM_THREADS":"2","STREHL_FULLRES_GATHER":"1",
        "STREHL_PROBE_GATHER":"green","STREHL_WARP_WRITEBACK":"parallel",
        "STREHL_DEFECT":"off","STREHL_GPU_GATHER_OUTPUT":str(out)}
env,removed=m.clean_environment(fields.items())
argv=[str(exe),"--exact","merge_cmd::tests::native_gpu_gather_controls::independent_gpu_gather_controls",
      "--ignored","--nocapture","--test-threads=1"]
protocol={p.name:m.binding(p) for p in (HERE/"run.py",HERE/"independent-design.md",HERE/"independent-review.md",HERE/"charter.md",HERE/"execution-1.md")}
save(out/"invocation.json",dict(command=argv,overrides=fields,removed_environment=removed,
    executable=held,build=m.binding(build/"invocation.json"),source_revision=receipt["revision"],protocol=protocol))
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
r=m.run(argv,env,ROOT,out/"consumer.log",api=api,wall_seconds=120,cpu_seconds=120,
        log_bytes=4<<20,committed_bytes=4<<30)
save(out/"process.json",r)
print(json.dumps({k:r[k] for k in ("exit_code","error","wall_seconds")}),flush=True)
check_sources()
cpu=r["job_accounting"]["total_cpu_100ns"]/1e7
retained=sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
assert cpu<=120 and retained<=256<<20
record=dict(exit_code=r["exit_code"],error=r["error"],aggregate_child_cpu_seconds=cpu,
    wall_seconds=r["wall_seconds"],peak_job_commit_bytes=r["job_memory"]["peak_job_memory_used_bytes"],
    terminal_job_accounting=r["terminal_job_accounting"],cleanup_errors=r["cleanup_errors"],
    retained_bytes_before_completion=retained,scope="18 primary generated-code cases plus fixed quantizer/descriptor controls; no RAW photograph/SOTA or speed claim")
if (out/"results.json").exists():record["measurement"]=m.binding(out/"results.json")
save(out/"completion.json",record)
assert r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
assert r["exit_code"]==0,"preserve failed candidate; no automatic repeat"
assert "1 passed" in (out/"consumer.log").read_text(encoding="utf-8")
print(json.dumps(record),flush=True)
