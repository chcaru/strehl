"""Execute the two fixed current product workflows with existing process tools."""
from pathlib import Path
import importlib.util,json,subprocess,sys,hashlib
import numpy as np
import tifffile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
m=module("product_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
def ref(p):return dict(path=str(p.resolve()),**m.binding(p))
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def save(p,v):
    with p.open("x",encoding="utf-8") as f:json.dump(v,f,indent=2,allow_nan=False);f.write("\n")
assert sys.argv[1:] in ([],["--fork-memory-40g"]),"fixed original allocation or one declared resource amendment only"
amended=bool(sys.argv[1:])
commit_cap=(40 if amended else 16)<<30
assert read(ROOT/"experiments/native-direct-planes/score-detail-1/decision.json")["rounded_exact_pass"] is True
rawdir=Path("D:/personal/macro/coffee-bean");tiffdir=Path("D:/edited/macro/coffee-bean")
raw=sorted([p for p in rawdir.iterdir() if p.is_file() and p.suffix.lower()==".arw"])
tiffs=sorted([p for p in tiffdir.iterdir() if p.is_file() and p.suffix.lower()==".tif"])
expected=[f"DSC{i:05d}" for i in range(16,121)]
assert [p.stem for p in raw]==[p.stem for p in tiffs]==expected
def metadata(p):
    s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
inputs=[metadata(p) for p in raw+tiffs]
native=ROOT/"experiments/native-direct-planes/build-1/strehl.exe"
fork=ROOT/"experiments/M175-fork-arm/bin/focus-stack.exe"
warp=ROOT/"experiments/M-PHASE0-PHASE/out/canon/coffee-bean.warpmap.txt"
assert m.binding(native)["sha256"]=="95e5c82d8940e87dc2e5e790a71aea4f5def69b03abbf1478a93b80087ca0236"
assert m.binding(fork)["sha256"]=="691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac"
assert m.binding(warp)["sha256"]=="b21b247944c257ab0fd3c767c879b9abf4a5fb1112dded97c87990a7d537274c"
original=HERE/"run-1"
if amended:
    prior=read(original/"plan.json")
    failure=read(original/"fork-process.json")
    assert failure["error"]=="ValueError('child committed-memory bound')"
    assert prior["inputs"]==inputs
    assert ref(native)==prior["native"] and ref(fork)==prior["fork"] and ref(warp)==prior["map"]
    assert [ref(p) for p in sorted(fork.parent.glob("*.dll"))]==prior["dlls"]
    saved_native=read(original/"native-output.json")
    assert ref(Path(saved_native["output"]["path"]))==saved_native["output"]
    host=module("product_host_memory",ROOT/"experiments/M-PHASE0-PIPE/measure.py")
    total_memory,available_memory=host.memory_status()
    assert available_memory>=48<<30,"amended run needs at least48GiB currently available RAM"
out=HERE/("fork-2" if amended else "run-1");out.mkdir()
noutput=out/"native-coffee-bean.tiff";foutput=out/"fork-coffee-bean.tiff"
nargs=[str(native),"stack",str(rawdir),"--merge","pyramid","--pyramid-bands","7","--pyramid-gate","2","--pyramid-exponent","2","--pyramid-sharpen","1.4","--pyramid-select","soft","--pyramid-base","mean","--srgb","--demosaic","--resampler","catmull-rom","--cover","crop","--out",str(noutput)]
nfields=[("RAYON_NUM_THREADS","8"),("STREHL_PYRAMID_WORKERS","8"),("STREHL_ALIGN","1"),("STREHL_WARPMAP",str(warp)),("STREHL_DIRECT_PLANES","rounded"),("STREHL_PROBE_GATHER","green"),("STREHL_WARP_WRITEBACK","parallel"),("STREHL_FULLRES_GATHER","1"),("STREHL_DEFECT","off")]
fargs=[str(fork),"--output="+str(foutput),"--reference=52","--threads=8","--batchsize=8","--consistency=2","--denoise=1","--input-colorspace=linear-rec2020","--output-colorspace=srgb","--output-bitdepth=16","--verbose"]+[str(p) for p in tiffs]
plans=[dict(label="native",command=nargs,fields=nfields,output=str(noutput)),dict(label="fork",command=fargs,fields=[],output=str(foutput))]
if amended:
    old_args=prior["plans"][1]["command"]
    assert len(old_args)==len(fargs)
    differences=[(a,b) for a,b in zip(old_args,fargs) if a!=b]
    assert differences==[(old_args[1],fargs[1])] and old_args[1].startswith("--output=") and fargs[1].startswith("--output=")
    plans=plans[1:]
save(out/"plan.json",dict(schema="native-product-comparison-v1",revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),runner=ref(Path(__file__)),native=ref(native),fork=ref(fork),dlls=[ref(p) for p in sorted(fork.parent.glob("*.dll"))],map=ref(warp),inputs=inputs,plans=plans,limits=dict(wall_seconds=600,cpu_seconds=3600,peak_job_commit_bytes=commit_cap,log_bytes=4<<20,retained_primary_output_bytes=512<<20),scope="RAW direct versus existing developed LinearRec2020 TIFF workflow; native reuses map while fork aligns; upstream development time unavailable; no speed ranking or common-linear quality claim"))
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
def run(label,argv,fields,wall,cpu,commit):
    env,removed=m.clean_environment(fields)
    save(out/(label+"-invocation.json"),dict(command=argv,environment_overrides=dict(fields),removed_environment=removed))
    result=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=wall,cpu_seconds=cpu,log_bytes=4<<20,committed_bytes=commit)
    save(out/(label+"-process.json"),result)
    print(json.dumps(dict(label=label,exit_code=result["exit_code"],error=result["error"],wall_seconds=result["wall_seconds"])),flush=True)
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"],"preserve failure; fixed allocation stops"
    return result
if amended:
    save(out/"amendment.json",dict(memory_before=dict(total_bytes=total_memory,available_bytes=available_memory),charter=ref(HERE/"resource-amendment.md"),original_plan=ref(original/"plan.json"),failed_process=ref(original/"fork-process.json"),retained_native=ref(original/"native-output.json"),changes=["output path","committed memory cap16GiBto40GiB"],same_remaining_argv=True))
else:run("map-check",[str(native),"align",str(rawdir),"--check",str(warp)],[],15,15,1<<30)
records=[]
for plan in plans:
    for i in inputs:
        s=Path(i["path"]).stat();assert s.st_size==i["bytes"] and s.st_mtime_ns==i["mtime_ns"]
    assert m.binding(warp)["sha256"]=="b21b247944c257ab0fd3c767c879b9abf4a5fb1112dded97c87990a7d537274c"
    r=run(plan["label"],plan["command"],plan["fields"],600,3600,commit_cap)
    p=Path(plan["output"]);assert p.stat().st_size<=512<<20
    with tifffile.TiffFile(p) as tf:
        assert len(tf.pages)==1
        pix=tf.asarray();assert pix.ndim==3 and pix.shape[2]==3 and pix.dtype==np.uint16 and int(pix.min())<int(pix.max())
        decoded=dict(shape=list(pix.shape),dtype=str(pix.dtype),bytes=pix.nbytes,sha256=hashlib.sha256(pix.tobytes(order="C")).hexdigest())
        tags={k:str(tf.pages[0].tags[k].value) for k in ("Software","PhotometricInterpretation") if k in tf.pages[0].tags}
        icc=tf.pages[0].tags.get(34675)
        tags["icc_profile"]=None if icc is None else dict(bytes=len(icc.value),sha256=hashlib.sha256(icc.value).hexdigest())
    del pix
    record=dict(label=plan["label"],output=ref(p),decoded=decoded,tags=tags,process_wall_seconds=r["wall_seconds"],job_cpu_seconds=r["job_accounting"]["total_cpu_100ns"]/1e7,peak_job_commit_bytes=r["job_memory"]["peak_job_memory_used_bytes"])
    save(out/(plan["label"]+"-output.json"),record);records.append(record)
    assert sum(x["output"]["bytes"] for x in records)+(saved_native["output"]["bytes"] if amended else 0)<=512<<20
save(out/"results.json",dict(status="FORK_RESTART_COMPLETE_UNREVIEWED" if amended else "TWO_WORKFLOWS_COMPLETE_UNREVIEWED",outputs=records,plan=ref(out/"plan.json"),scope="actual viewing outputs; no ground-truth/competitive-speed score"))
