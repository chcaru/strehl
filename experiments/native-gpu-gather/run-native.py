"""Fixed native GPU acceptance, then separately requested same-binary timing."""
from pathlib import Path
import importlib.util,json,sys,hashlib,subprocess,shutil
import numpy as np
import tifffile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
m=module("gpu_native_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
host=module("gpu_native_host",ROOT/"experiments/M-PHASE0-PIPE/measure.py")
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2,allow_nan=False);f.write("\n")
def ref(p):return dict(path=str(p),**m.binding(p))
assert sys.argv[1:] in ([],["--timing-109"]),"two fixed allocations only"
timing=bool(sys.argv[1:])
controls=json.loads((HERE/"run-4/results.json").read_text(encoding="utf-8"))
assert controls["status"]=="EIGHTEEN_GPU_GATHER_CONTROLS_PASS"
assert controls["compilation"]["max_storage_buffer_binding_size"]>=395592192
if timing:
    acceptance=json.loads((HERE/"native-112-2/results.json").read_text(encoding="utf-8"))
    assert acceptance["all_tiffs_exact"] and len(acceptance["renders"])==3
plan_path=ROOT/("experiments/native-probe-fill/transfer-plan-109.json" if timing else "experiments/native-pyramid-profile/native-plan-1.json")
plan=json.loads(plan_path.read_text(encoding="utf-8"))
expected_plan="3eb75cb702755104623047a38a1a2c13c270681aec7fd1d8a810e0b824f3be59" if timing else "947b7fba499cf493d19c1c73f1374693256517983909b84e262d4312958ccf29"
assert m.binding(plan_path)["sha256"]==expected_plan
whole="84f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851" if timing else "ba96c63dd56f2729ba2ed25fedc19b291a4a78f9992f6823ce501a1df2a8bdc6"
decoded="1bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1" if timing else "d5fd6969b77fc94334995dea771e434f65f2b3cf782e1d683ca2872639595a1a"
arms=[("cpu","rounded","off","parallel"),("gpu","rounded","off","parallel"),("gpu","rounded","off","parallel"),("cpu","rounded","off","parallel")] if timing else [
    ("cpu","rounded","off","parallel"),("gpu","rounded","off","serial"),("gpu","rounded","on","parallel")]
build=HERE/"build-native-2";receipt=json.loads((build/"invocation.json").read_text(encoding="utf-8"))
held=json.loads((build/"executables.json").read_text(encoding="utf-8"))["strehl"];exe=ROOT/held["path"]
assert m.binding(exe)=={k:held[k] for k in ("bytes","sha256")}
def check_sources():
    for item in receipt["source_files"]:
        assert m.binding(ROOT/item["path"])=={k:item[k] for k in ("bytes","sha256")},"compiled source changed"
def check_inputs():
    for item in plan["inputs"]:
        p=Path(item["path"]);s=p.stat()
        assert (s.st_size,s.st_mtime_ns)==(item["bytes"],item["mtime_ns"]),"original changed"
check_sources();check_inputs()
map_path=Path(plan["planned_render"]["environment_overrides"]["STREHL_WARPMAP"])
expected_map="c29cab9c6f944f4d03c4402998e54aad4d4221cc450ac4bef42a453de848434d" if timing else "1bc98923196b82699eb62b35bbed7c2b9c7e37b5f4cec9140703c6155050dddc"
assert m.binding(map_path)["sha256"]==expected_map
assert shutil.disk_usage(ROOT).free >= (len(arms)*197798267+(512<<20))
out=HERE/("native-109-1" if timing else "native-112-2");out.mkdir()
save(out/"execution.json",dict(source=ref(Path(__file__)),protocol=ref(HERE/"execution-4.md"),
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    build=ref(build/"invocation.json"),executable=held,plan=ref(plan_path),map=ref(map_path),arms=arms,
    expected_whole=whole,expected_decoded=decoded,scope="fixed native consumer identity; timing excludes saved alignment solve"))
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
records=[]
for index,(arm,direct,log_mode,schedule) in enumerate(arms):
    label=f"{index+1}-{arm}-{direct}-{log_mode}-{schedule}";tiff=out/(label+".tiff");profile=out/(label+"-profile.json")
    fields=dict(plan["planned_render"]["environment_overrides"])
    fields.update(STREHL_PYRAMID_PROFILE="on",STREHL_PYRAMID_PROFILE_OUTPUT=str(profile),
        STREHL_GPU_GATHER="on" if arm=="gpu" else "off",STREHL_GPU_GATHER_LOG=log_mode,STREHL_GPU_SCHEDULE=schedule,
        STREHL_DIRECT_PLANES=direct,STREHL_FULLRES_GATHER="1",STREHL_PROBE_GATHER="green",STREHL_WARP_WRITEBACK="parallel",STREHL_DEFECT="off")
    env,removed=m.clean_environment(fields.items())
    argv=[str(exe),*[str(tiff) if x=="PER_RUN_NATIVE_TIFF" else x for x in plan["planned_render"]["command"]]]
    save(out/(label+"-invocation.json"),dict(command=argv,environment_overrides=fields,removed_environment=removed))
    before=host.system_times()
    r=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=180,cpu_seconds=900,log_bytes=2<<20,committed_bytes=8<<30)
    busy,seconds=host.busy_between(before,host.system_times())
    r["host"]=dict(busy_fraction=busy,all_core_busy_seconds=seconds,scope="whole machine, including this job")
    save(out/(label+"-process.json"),r)
    print(json.dumps(dict(label=label,exit_code=r["exit_code"],error=r["error"],wall_seconds=r["wall_seconds"])),flush=True)
    check_sources();check_inputs()
    assert m.binding(map_path)["sha256"]==expected_map
    assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
    text=(out/(label+".log")).read_text(encoding="utf-8",errors="replace")
    rgb=text.count("GPU gather completed RGB");green=text.count("GPU gather completed green-only")
    if arm=="gpu":
        assert rgb>0 and green>0 and "remains CPU" not in text,"requested GPU route not established"
        if log_mode=="on":assert controls["compilation"]["submitted_sha256"] in text,"different strict shader"
        if log_mode=="placebo":assert "CALL PLACEBO" in text and "INITIALIZATION PLACEBO" in text
    else:assert rgb==green==0,"CPU arm entered GPU"
    file=ref(tiff)
    with tifffile.TiffFile(tiff) as tf:
        assert len(tf.pages)==1
        pixels=tf.asarray();assert pixels.shape==(4688,7032,3) and pixels.dtype==np.uint16 and pixels.min()<pixels.max()
        payload=dict(shape=list(pixels.shape),dtype=str(pixels.dtype),bytes=pixels.nbytes,sha256=hashlib.sha256(pixels.tobytes(order="C")).hexdigest())
    del pixels
    exact=file["sha256"]==whole and payload["sha256"]==decoded
    row=dict(label=label,arm=arm,direct=direct,log_mode=log_mode,schedule=schedule,file=file,decoded=payload,exact=exact,
        gpu_rgb_calls=rgb,gpu_green_calls=green,wall_seconds=r["wall_seconds"],
        cpu_seconds=r["job_accounting"]["total_cpu_100ns"]/1e7,peak_job_commit_bytes=r["job_memory"]["peak_job_memory_used_bytes"],
        host=r["host"],profile=json.loads(profile.read_text(encoding="utf-8")))
    records.append(row);save(out/(label+"-output.json"),row)
    assert exact,"preserved full native TIFF mismatch; do not start later arms"
    assert sum(x["file"]["bytes"] for x in records)<=2<<30
save(out/"results.json",dict(all_tiffs_exact=True,renders=records,scope="full native TIFF identity; complete process cost includes GPU startup/transfers/writer, saved alignment solve excluded"))
print(json.dumps(dict(status="NATIVE_GPU_COMPARISON_COMPLETE",renders=len(records),all_tiffs_exact=True)),flush=True)
