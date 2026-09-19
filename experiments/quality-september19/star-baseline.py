"""One current native star-sand baseline; original captures are read only."""
from pathlib import Path
import importlib.util,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location("bounded",ROOT/"experiments/m193c-output-grid/bounded-process.py")
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def save(p,v):
 with p.open("x",encoding="utf-8") as f:json.dump(v,f,indent=2);f.write("\n")
def ref(p):return dict(path=str(p),**m.binding(p))
rawdir=Path("D:/personal/macro/requests/misc-diagnostic/star-sand-cpl")
files=sorted(rawdir.glob("*.ARW"));assert [p.stem for p in files]==[f"DSC{i:05d}" for i in range(16,275)]
inputs=[dict(path=str(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in files]
exe=ROOT/"experiments/native-gpu-gather/build-native-6/strehl.exe"
assert m.binding(exe)["sha256"]=="2fd0a1615989e262fbba61e0a1587a9b8f20ff4913d3969510e967ce9d9219d7"
out=HERE/"star-baseline-1";out.mkdir();warp=out/"star.warpmap.txt";tiff=out/"star.tiff"
fields=dict(RAYON_NUM_THREADS="8",STREHL_PYRAMID_WORKERS="8",STREHL_ALIGN="1",STREHL_WARPMAP=str(warp),STREHL_FULLRES_GATHER="1",STREHL_DIRECT_PLANES="rounded",STREHL_PROBE_GATHER="green",STREHL_WARP_WRITEBACK="parallel",STREHL_GPU_GATHER="on",STREHL_GPU_SCHEDULE="device",STREHL_GPU_GATHER_LOG="off",STREHL_DEFECT="off")
env,removed=m.clean_environment(fields.items());api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
commands=[("align",[str(exe),"align",str(rawdir),"--out",str(warp),"--threads","8","--resampler","catmull-rom"]), ("render",[str(exe),"stack",str(rawdir),"--merge","pyramid","--pyramid-bands","7","--pyramid-gate","2","--pyramid-exponent","2","--pyramid-sharpen","1.4","--pyramid-select","soft","--pyramid-base","mean","--srgb","--demosaic","--resampler","catmull-rom","--cover","crop","--out",str(tiff)])]
save(out/"invocation.json",dict(inputs=inputs,executable=ref(exe),runner=ref(Path(__file__)),commands=commands,environment=fields,removed_environment=removed,scope="new259 RAW baseline; output image inspection, no speed or quality claim"))
for label,argv in commands:
 r=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=600,cpu_seconds=3600,log_bytes=4<<20,committed_bytes=16<<30)
 save(out/(label+"-process.json"),r)
 print(json.dumps(dict(stage=label,exit_code=r["exit_code"],error=r["error"],wall_seconds=r["wall_seconds"])),flush=True)
 assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
 for i in inputs:
  stat=Path(i["path"]).stat();assert(stat.st_size,stat.st_mtime_ns)==(i["bytes"],i["mtime_ns"])
 assert m.binding(exe)["sha256"]=="2fd0a1615989e262fbba61e0a1587a9b8f20ff4913d3969510e967ce9d9219d7"
 assert sum(p.stat().st_size for p in out.iterdir() if p.is_file())<=512<<20
save(out/"completion.json",dict(status="BASELINE_RENDERED",map=ref(warp),image=ref(tiff),original_metadata_unchanged=True))
