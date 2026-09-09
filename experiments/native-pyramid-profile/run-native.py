"""Execute the fixed native profile plan using existing process/host facilities."""
from pathlib import Path
import importlib.util,json,sys,subprocess,hashlib,time
import numpy as np
import tifffile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
m=module("native_profile_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
host=module("native_profile_host",ROOT/"experiments/M-PHASE0-PIPE/measure.py")
def ref(p):return dict(path=str(p),**m.binding(p))
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2,allow_nan=False);f.write("\n")
plan=json.loads((HERE/"native-plan-1.json").read_text())
assert json.loads((HERE/"independent-controls-1.json").read_text())["status"]=="SAVED_CONTROLS_PASS"
exe=HERE/"build-1/strehl.exe"
built=json.loads((HERE/"build-1/executables.json").read_text())
assert ref(exe)["sha256"]==built["strehl"]["sha256"]
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
out=HERE/"native";out.mkdir()
limits=plan["limits"]
revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
save(out/"execution.json",dict(revision=revision,source=ref(Path(__file__)),plan=ref(HERE/"native-plan-1.json"),executable=ref(exe),physical_memory_bytes=host.memory_status()[0],logical_cpu_count=host.LOGICAL_CPUS))
for item in plan["inputs"]:
    p=Path(item["path"]);s=p.stat()
    assert s.st_size==item["bytes"] and s.st_mtime_ns==item["mtime_ns"],"input metadata changed since fixed selection"
def run(label,args,fields):
    env,removed=m.clean_environment(fields)
    argv=[str(exe),*args]
    save(out/(label+"-invocation.json"),dict(command=argv,environment_overrides=dict(fields),removed_environment=removed))
    before=host.system_times();started=time.perf_counter()
    result=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=limits["native_child_wall_seconds"],cpu_seconds=limits["native_child_cpu_seconds"],log_bytes=limits["native_log_bytes"],committed_bytes=limits["native_child_committed_bytes"])
    elapsed=time.perf_counter()-started;after=host.system_times()
    busy,seconds=host.busy_between(before,after)
    result["host"]=dict(interval_wall_seconds=elapsed,busy_fraction=busy,all_core_busy_seconds=seconds,scope="Whole-machine sampling enclosing child helper, not exclusive competing-process accounting.")
    save(out/(label+"-process.json"),result)
    print(json.dumps(dict(label=label,exit_code=result["exit_code"],error=result["error"],wall_seconds=result["wall_seconds"],host_busy_fraction=busy)),flush=True)
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"],"owned native invocation failed; retain evidence"
    return result
align=run("align",plan["planned_alignment"]["command"],[("RAYON_NUM_THREADS","8")])
warp=Path(plan["planned_alignment"]["command"][-1])
assert warp.is_file()
save(out/"alignment-map.json",ref(warp))
records=[]
for i,mode in enumerate(plan["planned_render"]["modes"]):
    label=f"{i+1}-{mode}";tiff=out/(label+".tiff")
    args=[str(tiff) if x=="PER_RUN_NATIVE_TIFF" else x for x in plan["planned_render"]["command"]]
    fields=list(plan["planned_render"]["environment_overrides"].items())+[("STREHL_PYRAMID_PROFILE",mode)]
    profile=out/(label+"-profile.json")
    if mode!="off":fields.append(("STREHL_PYRAMID_PROFILE_OUTPUT",str(profile)))
    result=run(label,args,fields)
    # Read each completed entire TIFF after the timed product process.
    file_ref=ref(tiff)
    with tifffile.TiffFile(tiff) as tf:
        assert len(tf.pages)==1,"expected one complete native image"
        pixels=tf.asarray()
        assert pixels.shape==(4688,7032,3) and pixels.dtype==np.uint16
        assert pixels.min()<pixels.max(),"degenerate output"
        decoded=dict(shape=list(pixels.shape),dtype=str(pixels.dtype),bytes=pixels.nbytes,minimum=int(pixels.min()),maximum=int(pixels.max()),sha256=hashlib.sha256(pixels.tobytes(order="C")).hexdigest())
    del pixels
    row=dict(label=label,mode=mode,file=file_ref,decoded=decoded,process_wall_seconds=result["wall_seconds"],job_cpu_seconds=result["job_accounting"]["total_cpu_100ns"]/1e7,peak_job_commit_bytes=result["job_memory"]["peak_job_memory_used_bytes"],host=result["host"],profile=json.loads(profile.read_text()) if mode!="off" else None)
    records.append(row);save(out/(label+"-output.json"),row)
    assert len({x["file"]["sha256"] for x in records})==1 and len({x["decoded"]["sha256"] for x in records})==1,"observer perturbed native output"
    assert sum(x["file"]["bytes"] for x in records)<=limits["retained_native_output_bytes"]
save(out/"results.json",dict(scope=plan["scope"],alignment_process_wall_seconds=align["wall_seconds"],renders=records,all_whole_tiff_bytes_equal=True,all_decoded_pixels_equal=True))
print(json.dumps(dict(status="NATIVE_PROFILE_COMPLETE",renders=len(records),all_tiff_bytes_equal=True)),flush=True)

