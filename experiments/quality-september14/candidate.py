"""One quadratic-map photograph, through the unchanged baseline renderer."""
from pathlib import Path
import importlib.util,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location("bounded",ROOT/"experiments/m193c-output-grid/bounded-process.py")
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def save(p,v):
 with p.open("x",encoding="utf-8") as f:json.dump(v,f,indent=2);f.write("\n")
def ref(p):return dict(path=str(p),**m.binding(p))
base=HERE/"baseline-1";b=read(base/"invocation.json");bh=read(base/"completion.json")
control=ROOT/"experiments/alignment-quadratic-peak/run-1/completion.json"
assert read(control)["proceed_to_raw_comparison"] is True
build=ROOT/"experiments/alignment-quadratic-peak/build-cli-1";held=read(build/"executables.json")
aligner=ROOT/held["strehl"]["path"];test=ROOT/held["cli-tests"]["path"]
renderer=Path(b["executable"]["path"]);assert ref(renderer)==b["executable"]
for x in read(ROOT/"experiments/alignment-quadratic-peak/cli-source.json"):
 assert m.binding(ROOT/x["path"])=={k:x[k] for k in ("bytes","sha256")}
assert ref(Path(bh["image"]["path"]))==bh["image"] and ref(Path(bh["map"]["path"]))==bh["map"]
out=HERE/"quadratic-1";out.mkdir();warp=out/"printer.warpmap.txt";tiff=out/"printer.tiff"
fields=dict(b["environment"]);fields["STREHL_WARPMAP"]=str(warp)
env,removed=m.clean_environment(fields.items());api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
a=list(b["commands"][0][1]);a[0]=str(aligner);a[a.index("--out")+1]=str(warp);a += ["--peak-refinement","quadratic"]
r=list(b["commands"][1][1]);r[r.index("--out")+1]=str(tiff)
commands=[("cli-control",[str(test),"--exact","tests::quadratic_peak_refinement_is_explicit_and_keeps_the_automatic_cache_separate","--nocapture"]),("align",a),("render",r)]
save(out/"invocation.json",dict(inputs=b["inputs"],aligner=ref(aligner),renderer=ref(renderer),control=ref(control),commands=commands,environment=fields,removed_environment=removed,baseline=ref(base/"invocation.json"),runner=ref(Path(__file__)),scope="only alignment peak method changes; same held renderer/preset; native integer crop intersection, no fitted image registration"))
for label,argv in commands:
 result=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=600,cpu_seconds=3600,log_bytes=4<<20,committed_bytes=16<<30)
 save(out/(label+"-process.json"),result)
 print(json.dumps(dict(stage=label,exit_code=result["exit_code"],error=result["error"],wall_seconds=result["wall_seconds"])),flush=True)
 assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"]
 if label=="cli-control":assert "1 passed" in (out/(label+".log")).read_text()
 for i in b["inputs"]:
  st=Path(i["path"]).stat();assert(st.st_size,st.st_mtime_ns)==(i["bytes"],i["mtime_ns"])
 assert ref(renderer)==b["executable"]
 assert sum(p.stat().st_size for p in out.iterdir() if p.is_file())<=512<<20
save(out/"completion.json",dict(status="CANDIDATE_RENDERED",map=ref(warp),image=ref(tiff),original_metadata_unchanged=True))
