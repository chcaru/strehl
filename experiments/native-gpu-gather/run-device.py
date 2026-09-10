"""Fixed device descriptor commissioning, then unchanged18 image controls."""
from pathlib import Path
import importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("device_gather_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2,allow_nan=False);f.write("\n")
assert sys.argv[1:]==[],"one fixed allocation"
build=HERE/"build-native-6"
receipt=json.loads((build/"invocation.json").read_text(encoding="utf-8"))
def check_sources():
    for e in receipt["source_files"]:
        assert m.binding(ROOT/e["path"])=={k:e[k] for k in ("bytes","sha256")},"compiled source changed"
check_sources()
held=json.loads((build/"executables.json").read_text(encoding="utf-8"))["cli-tests"]
exe=ROOT/held["path"];assert m.binding(exe)=={k:held[k] for k in ("bytes","sha256")}
out=HERE/"run-device-4";out.mkdir()
fields={"RAYON_NUM_THREADS":"2","STREHL_FULLRES_GATHER":"1","STREHL_PROBE_GATHER":"green",
    "STREHL_WARP_WRITEBACK":"parallel","STREHL_DEFECT":"off",
    "STREHL_GPU_SCHEDULE":"device","STREHL_GPU_GATHER_OUTPUT":str(out)}
env,removed=m.clean_environment(fields.items())
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
protocol={p.name:m.binding(p) for p in (Path(__file__),HERE/"execution-6.md",HERE/"independent-design-device.md",HERE/"independent-design-device-guard.md",HERE/"device-guard-review.md",HERE/"independent-design.md")}
records=[]
for stem,test,filename,status in [
    ("guard","independent_gpu_device_guard_controls","device-guard-results.json","DEVICE_GUARD_CONTROLS_PASS"),
    ("descriptors","independent_gpu_device_descriptor_controls","device-descriptor-results.json","DEVICE_DESCRIPTOR_CONTROLS_PASS"),
    ("images","independent_gpu_gather_controls","results.json","EIGHTEEN_GPU_GATHER_CONTROLS_PASS")]:
    argv=[str(exe),"--exact","merge_cmd::tests::native_gpu_gather_controls::"+test,"--ignored","--nocapture","--test-threads=1"]
    save(out/(stem+"-invocation.json"),dict(command=argv,overrides=fields,removed_environment=removed,executable=held,
        build=m.binding(build/"invocation.json"),source_revision=receipt["revision"],protocol=protocol))
    r=m.run(argv,env,ROOT,out/(stem+".log"),api=api,wall_seconds=120,cpu_seconds=120,log_bytes=4<<20,committed_bytes=4<<30)
    save(out/(stem+"-process.json"),r)
    row=dict(test=test,exit_code=r["exit_code"],error=r["error"],wall_seconds=r["wall_seconds"],
        child_cpu_seconds=r["job_accounting"]["total_cpu_100ns"]/1e7,
        peak_job_commit_bytes=r["job_memory"]["peak_job_memory_used_bytes"])
    if (out/filename).exists():row["measurement"]=m.binding(out/filename)
    save(out/(stem+"-completion.json"),row);records.append(row)
    print(json.dumps(row),flush=True)
    check_sources()
    assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"],"preserve failure; later process refused"
    measurement=json.loads((out/filename).read_text(encoding="utf-8"))
    assert measurement["status"]==status
    compilation=measurement["compilation" if stem=="images" else "gather_compilation"]
    assert compilation["original_sha256"]=="41658a89bd9b17c73b0f452b48bde689679e4ecc50774872ebfff0171cdb6560","protected original f32 image shader changed"
    assert compilation["submitted_sha256"]=="a7dce2107ce7713ac4d9cd961dd44e303bd69b37c2d2ca7029f20aa1f131de9d","protected strict f32 image shader changed"
    assert "1 passed" in (out/(stem+".log")).read_text(encoding="utf-8")
assert sum(r["child_cpu_seconds"] for r in records)<=360
assert sum(f.stat().st_size for f in out.rglob("*") if f.is_file())<=256<<20
save(out/"completion.json",dict(status="GUARD_DEVICE_AND_IMAGE_CONTROLS_PASS",processes=records))
print("GUARD_DEVICE_AND_IMAGE_CONTROLS_PASS",flush=True)
