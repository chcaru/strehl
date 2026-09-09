"""Run four tiny controls through the existing bounded process helper."""
from pathlib import Path
import importlib.util,json,sys,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
p=ROOT/"experiments/m193c-output-grid/bounded-process.py"
spec=importlib.util.spec_from_file_location("phase_controls_process",p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def ref(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2);f.write("\n")
job=ROOT/"experiments/m12-scorecard/m12-harness.py"
api=m.load_job_api({k:v for k,v in ref(job).items() if k!="path"})
out=HERE/"controls-1";out.mkdir()
exe=HERE/"build-1/cli-tests.exe"
revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
for label,mode,delay in [("off","off",False),("on","on",False),("placebo","placebo",False),("delay","on",True)]:
    fields=[("RAYON_NUM_THREADS","4"),("STREHL_PYRAMID_PROFILE",mode)]
    if delay:fields.append(("STREHL_PYRAMID_PROFILE_DELAY","1"))
    env,removed=m.clean_environment(fields)
    argv=[str(exe),"merge_cmd::native_pyramid_profile::tests::phase_timer_smoke","--exact","--ignored","--nocapture","--test-threads=1"]
    save(out/f"{label}-invocation.json",dict(command=argv,environment_overrides=dict(fields),removed_environment=removed,executable=ref(exe),revision=revision))
    r=m.run(argv,env,ROOT,out/f"{label}.log",api=api,wall_seconds=30,cpu_seconds=60,log_bytes=1<<20,committed_bytes=1<<30)
    save(out/f"{label}-process.json",r)
    print(json.dumps(dict(label=label,exit_code=r["exit_code"],error=r["error"],wall_seconds=r["wall_seconds"])),flush=True)
    assert r["exit_code"]==0 and r["error"] is None
baseline=HERE/"smoke-off"
pairs=[]
for label in ("on","placebo","delay"):
    files=[]
    for name in ("output.f32","output.tiff"):
        a=baseline/name;b=HERE/f"smoke-{label}"/name
        assert a.read_bytes()==b.read_bytes(),f"observer changed output: {label}/{name}"
        files.append(dict(name=name,baseline=ref(a),observed=ref(b),byte_equal=True))
    pairs.append(dict(label=label,files=files))
save(out/"byte-equality.json",dict(pairs=pairs,scope="tiny actual output identity; independent phase checker still required"))
print(json.dumps(dict(status="CONTROLS_EXECUTED",byte_pairs_equal=6)),flush=True)
