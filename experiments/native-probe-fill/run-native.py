"""Compare the held scalar binary and exact parallel candidate on fixed native inputs."""
from pathlib import Path
import importlib.util,json,sys,subprocess,hashlib,time
import numpy as np
import tifffile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
PROFILE=ROOT/"experiments/native-pyramid-profile"
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
m=module("probe_fill_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
host=module("probe_fill_host",ROOT/"experiments/M-PHASE0-PIPE/measure.py")
def ref(p):return dict(path=str(p),**m.binding(p))
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2,allow_nan=False);f.write("\n")
assert sys.argv[1:] in ([], ["--transfer-109"], ["--green-probe-109"], ["--parallel-writeback-109"], ["--direct-planes-109"]), "only fixed109 follow-ups are supported"
direct=sys.argv[1:]==["--direct-planes-109"]
writeback=sys.argv[1:]==["--parallel-writeback-109"]
green=sys.argv[1:]==["--green-probe-109"]
transfer=bool(sys.argv[1:])
plan_path=HERE/"transfer-plan-109.json" if transfer else PROFILE/"native-plan-1.json"
plan=json.loads(plan_path.read_text(encoding="utf-8"))
baseline=(json.loads((HERE/"transfer-109/results.json").read_text(encoding="utf-8"))["renders"][0] if green or writeback or direct else None) if transfer else json.loads((PROFILE/"native/results.json").read_text(encoding="utf-8"))["renders"][0]
arms=("old","candidate","candidate","old","serial-control") if writeback else (("old","candidate","candidate","old","rgb-control") if green else (("old","candidate","candidate","old") if transfer else ("old","candidate","candidate","old","scalar-control")))
old=ROOT/"experiments/native-green-probe/build-2/strehl.exe" if writeback else (HERE/"build-1/strehl.exe" if green else PROFILE/"build-1/strehl.exe")
new=ROOT/"experiments/native-parallel-writeback/build-1/strehl.exe" if writeback else (ROOT/"experiments/native-green-probe/build-2/strehl.exe" if green else HERE/"build-1/strehl.exe")
if direct:
    arms=("old","candidate","candidate","old","off-control")
    old=ROOT/"experiments/native-parallel-writeback/build-1/strehl.exe"
    new=ROOT/"experiments/native-direct-planes/build-1/strehl.exe"
for exe in (old,new):
    built=json.loads((exe.parent/"executables.json").read_text(encoding="utf-8"))
    assert ref(exe)["sha256"]==built["strehl"]["sha256"]
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
out=ROOT/"experiments/native-parallel-writeback/native" if writeback else (ROOT/"experiments/native-green-probe/native" if green else HERE/("transfer-109" if transfer else "native"));
if direct:out=ROOT/"experiments/native-direct-planes/native"
out.mkdir()
limits=plan["limits"]
revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
save(out/"execution.json",dict(revision=revision,source=ref(Path(__file__)),plan=ref(plan_path),old=ref(old),candidate=ref(new),baseline_file=None if baseline is None else baseline["file"],baseline_decoded=None if baseline is None else baseline["decoded"],mode_order=list(arms)))
for item in plan["inputs"]:
    p=Path(item["path"]);s=p.stat()
    assert s.st_size==item["bytes"] and s.st_mtime_ns==item["mtime_ns"]
records=[]
for i,arm in enumerate(arms):
    if transfer:
        expected=plan["source_map"];actual=ref(Path(expected["path"]))
        assert actual["bytes"]==expected["bytes"] and actual["sha256"]==expected["sha256"], "held map changed"
    label=f"{i+1}-{arm}";tiff=out/(label+".tiff");profile=out/(label+"-profile.json")
    exe=old if arm=="old" else new
    args=[str(tiff) if x=="PER_RUN_NATIVE_TIFF" else x for x in plan["planned_render"]["command"]]
    fields=list(plan["planned_render"]["environment_overrides"].items())+[("STREHL_PYRAMID_PROFILE","on"),("STREHL_PYRAMID_PROFILE_OUTPUT",str(profile))]
    if direct and arm!="old":fields.append(("STREHL_DIRECT_PLANES","off" if arm=="off-control" else "rounded"))
    if arm=="scalar-control":fields.append(("STREHL_PROBE_FILL","serial"))
    if arm=="rgb-control":fields.append(("STREHL_PROBE_GATHER","rgb"))
    if arm=="serial-control":fields.append(("STREHL_WARP_WRITEBACK","serial"))
    env,removed=m.clean_environment(fields);argv=[str(exe),*args]
    save(out/(label+"-invocation.json"),dict(command=argv,environment_overrides=dict(fields),removed_environment=removed))
    before=host.system_times();start=time.perf_counter()
    r=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=limits["native_child_wall_seconds"],cpu_seconds=limits["native_child_cpu_seconds"],log_bytes=limits["native_log_bytes"],committed_bytes=limits["native_child_committed_bytes"])
    elapsed=time.perf_counter()-start;busy,seconds=host.busy_between(before,host.system_times())
    r["host"]=dict(interval_wall_seconds=elapsed,busy_fraction=busy,all_core_busy_seconds=seconds,scope="whole machine including this job; not exclusive competing process accounting")
    save(out/(label+"-process.json"),r)
    print(json.dumps(dict(label=label,exit_code=r["exit_code"],error=r["error"],wall_seconds=r["wall_seconds"],host_busy_fraction=busy)),flush=True)
    assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
    file=ref(tiff)
    with tifffile.TiffFile(tiff) as tf:
        assert len(tf.pages)==1
        pixels=tf.asarray();assert pixels.shape==(4688,7032,3) and pixels.dtype==np.uint16 and pixels.min()<pixels.max()
        decoded=dict(shape=list(pixels.shape),dtype=str(pixels.dtype),bytes=pixels.nbytes,sha256=hashlib.sha256(pixels.tobytes(order="C")).hexdigest())
    del pixels
    if baseline is None:
        assert i==0 and arm=="old";baseline=dict(file=file,decoded=decoded)
    assert file["sha256"]==baseline["file"]["sha256"] and decoded["sha256"]==baseline["decoded"]["sha256"],"full native output changed"
    row=dict(label=label,arm=arm,file=file,decoded=decoded,process_wall_seconds=r["wall_seconds"],job_cpu_seconds=r["job_accounting"]["total_cpu_100ns"]/1e7,peak_job_commit_bytes=r["job_memory"]["peak_job_memory_used_bytes"],host=r["host"],profile=json.loads(profile.read_text(encoding="utf-8")))
    records.append(row);save(out/(label+"-output.json"),row)
    assert sum(x["file"]["bytes"] for x in records)<=limits["retained_native_output_bytes"]
save(out/"results.json",dict(scope=plan["scope"],renders=records,all_whole_tiffs_match_original=True,all_decoded_pixels_match_original=True,alignment=plan.get("alignment_note","reuses prior lane-owned direct map; standalone solve1.297s previously measured")))
print(json.dumps(dict(status="NATIVE_COMPARISON_COMPLETE",renders=len(records),all_tiffs_equal=True)),flush=True)

