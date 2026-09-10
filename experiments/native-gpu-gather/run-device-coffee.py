"""One105-frame output comparison; no speed comparison against the older binary."""
from pathlib import Path
import importlib.util,json,sys,hashlib,re,shutil
import numpy as np
import tifffile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);v=importlib.util.module_from_spec(s);sys.modules[name]=v;s.loader.exec_module(v);return v
m=module("coffee_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
host=module("coffee_host",ROOT/"experiments/M-PHASE0-PIPE/measure.py")
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def ref(p):return dict(path=str(p),**m.binding(p))
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2,allow_nan=False);f.write("\n")
def banner(p):
    v=[s.split(":",1)[1].strip() for s in p.read_text(encoding="utf-8").splitlines() if s.startswith("build ")];assert len(v)==1;return v[0]
def value(v):
    if isinstance(v,bytes):return dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest())
    if isinstance(v,(tuple,list,np.ndarray)):return [value(x) for x in v]
    return v.item() if isinstance(v,np.generic) else v
def tags(page):return {str(t.code):dict(name=t.name,dtype=int(t.dtype),count=t.count,value=value(t.value)) for t in page.tags.values()}
def masked_hash(p,start,count):
    h=hashlib.sha256();offset=0
    with p.open("rb") as f:
        while raw:=f.read(1<<20):
            block=bytearray(raw);a=max(start-offset,0);b=min(start+count-offset,len(block))
            if b>a:block[a:b]=bytes(b-a)
            h.update(block);offset+=len(block)
    return h.hexdigest()
assert sys.argv[1:]==[],"one fixed render"
build=HERE/"build-native-6";receipt=read(build/"invocation.json");held=read(build/"executables.json");exe=ROOT/held["strehl"]["path"]
control=HERE/"run-device-4";gates=[control/"completion.json"]
assert read(gates[0])["status"]=="GUARD_DEVICE_AND_IMAGE_CONTROLS_PASS"
for stem,name,status in [("guard","device-guard-results.json","DEVICE_GUARD_CONTROLS_PASS"),("descriptors","device-descriptor-results.json","DEVICE_DESCRIPTOR_CONTROLS_PASS"),("images","results.json","EIGHTEEN_GPU_GATHER_CONTROLS_PASS")]:
    inv=control/(stem+"-invocation.json");done=control/(stem+"-completion.json");result=control/name;gates.extend([inv,done,result])
    assert read(inv)["build"]==m.binding(build/"invocation.json") and read(inv)["executable"]==held["cli-tests"]
    assert read(done)["exit_code"]==0 and read(done)["error"] is None and read(done)["measurement"]==m.binding(result)
    assert read(result)["status"]==status
images=read(control/"results.json");coords=read(control/"device-descriptor-results.json")
assert images["schedule"]=="Device256"
gather_hash="a7dce2107ce7713ac4d9cd961dd44e303bd69b37c2d2ca7029f20aa1f131de9d"
assert images["compilation"]["original_sha256"]=="41658a89bd9b17c73b0f452b48bde689679e4ecc50774872ebfff0171cdb6560" and images["compilation"]["submitted_sha256"]==gather_hash
prior109=HERE/"device-native-109-1";gates.extend([prior109/"results.json",prior109/"execution.json"])
assert read(gates[-1])["build"]==ref(build/"invocation.json") and read(gates[-1])["executable"]==held["strehl"]
r109=read(gates[-2]);assert r109["all_tiffs_exact"] and [r["arm"] for r in r109["renders"]]==["cpu","gpu","gpu","cpu"] and all(r["exact"] for r in r109["renders"])
old=ROOT/"experiments/native-product-comparison/run-1";plan=read(old/"plan.json");inv=read(old/"native-invocation.json");anchor=read(old/"native-output.json")
assert m.binding(old/"plan.json")["sha256"]=="e5acdda4c6aa75e52225d843efd0008f91795444f43e846cb635645da1ac8643"
assert m.binding(old/"native-invocation.json")["sha256"]=="b109cf8963ce4481749f15fec3f9312dff54d67782f5ca3a84779bb7c1916924"
assert m.binding(old/"native-output.json")["sha256"]=="391ce9963416303ef139bdef9a9ab7648e714ae3c1c97d827b860427888683b3"
baseline=Path(anchor["output"]["path"]);warp=Path(plan["map"]["path"]);inputs=[i for i in plan["inputs"] if Path(i["path"]).suffix.lower()==".arw"]
assert len(inputs)==105 and [Path(i["path"]).stem for i in inputs]==[f"DSC{i:05d}" for i in range(16,121)]
rawdir=Path(inputs[0]["path"]).parent;stamp_log=HERE/"device-native-112-1/2-gpu-rounded-on-device.log"
stamp=banner(stamp_log);assert stamp=="strehl 0.0.0 (36b91f0e5ced)" and len(stamp)==len(anchor["tags"]["Software"])
protocol=[ref(p) for p in gates+[Path(__file__),HERE/"execution-coffee.md",old/"plan.json",old/"native-invocation.json",old/"native-output.json",old/"native.log",stamp_log]]
def check():
    for i in receipt["source_files"]+protocol:assert m.binding(ROOT/i["path"])=={k:i[k] for k in ("bytes","sha256")},"source/protocol changed"
    assert m.binding(exe)=={k:held["strehl"][k] for k in ("bytes","sha256")}
    assert sorted(p for p in rawdir.iterdir() if p.is_file() and p.suffix.lower()==".arw")==sorted(Path(i["path"]) for i in inputs),"ARW population changed"
    for i in inputs:
        s=Path(i["path"]).stat();assert (s.st_size,s.st_mtime_ns)==(i["bytes"],i["mtime_ns"]),"original metadata changed"
    assert m.binding(warp)["sha256"]=="b21b247944c257ab0fd3c767c879b9abf4a5fb1112dded97c87990a7d537274c"
    assert ref(baseline)==anchor["output"],"held baseline changed"
check();existing=list(HERE.glob("*native*/*.tiff"));retained=sum(p.stat().st_size for p in existing)
assert len(existing)==20 and retained==3955965340 and retained+anchor["output"]["bytes"]<=4<<30
assert shutil.disk_usage(ROOT).free>=anchor["output"]["bytes"]+(256<<20)
out=HERE/"device-native-coffee-1";out.mkdir();tiff=out/"gpu-coffee-bean.tiff"
argv=list(inv["command"]);argv[0]=str(exe);argv[argv.index("--out")+1]=str(tiff)
fields=dict(inv["environment_overrides"]);fields.update(STREHL_GPU_GATHER="on",STREHL_GPU_SCHEDULE="device",STREHL_GPU_GATHER_LOG="on")
env,removed=m.clean_environment(fields.items());api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
save(out/"invocation.json",dict(command=argv,environment_overrides=fields,removed_environment=removed,protocol=protocol,build=ref(build/"invocation.json"),executable=held["strehl"],map=ref(warp),inputs=inputs,baseline=anchor,retained_before=retained))
try:
    check();before=host.system_times()
    r=m.run(argv,env,ROOT,out/"render.log",api=api,wall_seconds=180,cpu_seconds=900,log_bytes=2<<20,committed_bytes=8<<30)
    busy,seconds=host.busy_between(before,host.system_times());r["host"]=dict(busy_fraction=busy,all_core_busy_seconds=seconds)
    save(out/"process.json",r);check()
    assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
    log=(out/"render.log").read_text(encoding="utf-8");rgb=log.count("GPU gather completed RGB");green=log.count("GPU gather completed green-only");device=log.count("GPU device coordinates completed")
    route=dict(rgb=rgb,green=green,device=device,numeric_calls=len(re.findall(r"GPU gather (?:RGB|green-only) Device256:",log)),fallback="fallback Parallel256" in log,cpu="remains CPU" in log)
    route_ok=rgb==green==105 and device==210 and route["numeric_calls"]==210 and not route["fallback"] and not route["cpu"] and gather_hash in log and coords["coordinate_compilation"]["submitted_sha256"] in log
    oldlog=(old/"native.log").read_text(encoding="utf-8");prefixes=("lateral CA ","iso ","levels ","noise model ","defect map ","analysis domain ","output domain ","tone ")
    settings={p:[s for s in log.splitlines() if s.startswith(p)]==[s for s in oldlog.splitlines() if s.startswith(p)] for p in prefixes}
    with tifffile.TiffFile(baseline) as a,tifffile.TiffFile(tiff) as b:
        assert len(a.pages)==len(b.pages)==1;at=tags(a.pages[0]);bt=tags(b.pages[0]);software=(a.pages[0].tags[305],b.pages[0].tags[305])
        offsets=[(s.valueoffset,s.count) for s in software];pix=b.asarray();payload=dict(shape=list(pix.shape),dtype=str(pix.dtype),bytes=pix.nbytes,sha256=hashlib.sha256(pix.tobytes(order="C")).hexdigest());del pix
    diffs={k:dict(old=at.get(k),new=bt.get(k)) for k in sorted(set(at)|set(bt)) if at.get(k)!=bt.get(k)};structural={k:dict(old=at.get(k),new=bt.get(k)) for k in ("273","279","324","325") if k in at or k in bt}
    stamp_ok=bt["305"]["value"]==banner(out/"render.log")==stamp;masked=[masked_hash(p,*o) for p,o in zip((baseline,tiff),offsets)]
    new=ref(tiff);all_bytes=sum(p.stat().st_size for p in HERE.glob("*native*/*.tiff"))
    exact=payload==anchor["decoded"] and payload["shape"]==[4524,6784,3] and payload["dtype"]=="uint16"
    metadata_only=set(diffs)=={"305"} and offsets[0]==offsets[1] and masked[0]==masked[1] and new["bytes"]==anchor["output"]["bytes"] and stamp_ok
    passed=exact and metadata_only and route_ok and all(settings.values()) and all_bytes<=4<<30
    save(out/"results.json",dict(status="COFFEE_DEVICE_PIXELS_EXACT_SOFTWARE_ONLY" if passed else "COFFEE_REJECT",file=new,baseline=anchor["output"],decoded=payload,decoded_exact=exact,tag_differences=diffs,structural_tags=structural,software_storage=offsets,software_masked_hashes=masked,metadata_only_change=metadata_only,route=route,route_pass=route_ok,settings_match=settings,all_native_tiff_bytes=all_bytes,process=ref(out/"process.json"),scope="one deep-stack output identity check; no comparative105 speed claim"))
    assert passed,"retained105 output mismatch; no extra arm"
except BaseException as e:
    save(out/"failure.json",dict(status="COFFEE_FAILED",error=repr(e)));raise
