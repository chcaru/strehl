"""One bounded constructor-only example build/run; no fixed controls are replaced."""
from pathlib import Path
import importlib.util,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
PROCESS=ROOT/"experiments/m193c-output-grid/bounded-process.py"
BUILD=ROOT/"experiments/m194h-pedestal-causality/bounded-build-process.py"
spec=importlib.util.spec_from_file_location("gpu_preflight_process",PROCESS)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
spec=importlib.util.spec_from_file_location("gpu_preflight_build",BUILD)
b=importlib.util.module_from_spec(spec);sys.modules[spec.name]=b;spec.loader.exec_module(b)
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2,allow_nan=False);f.write("\n")
def ref(p):return dict(path=str(p.relative_to(ROOT)),**m.binding(p))
assert sys.argv[1:]==[],"one fixed preflight allocation"
prior=HERE/"build-native-5/invocation.json";job=ROOT/"experiments/m12-scorecard/m12-harness.py"
example=ROOT/"crates/strehl-cli/examples/native-gpu-preflight.rs"
paths=[ROOT/e["path"] for e in json.loads(prior.read_text(encoding="utf-8"))["source_files"]]
paths=list(dict.fromkeys(paths+[example,Path(__file__).resolve(),prior,PROCESS,BUILD,job]))
sources=[ref(p) for p in paths] # Bind current contents; prior hashes are not reused.
def check_sources():
    for e in sources:assert m.binding(ROOT/e["path"])=={k:e[k] for k in ("bytes","sha256")},e["path"]+" changed"
def retained():return sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
out=HERE/"preflight-1";out.mkdir()
fields={"RAYON_NUM_THREADS":"2","CARGO_INCREMENTAL":"0"}
env,removed=m.clean_environment(fields.items());api=m.load_job_api(m.binding(job))
argv=["cargo","test","-p","strehl-cli","--example","native-gpu-preflight","--no-run","--release",
    "--features","native-pyramid-profile,native-gpu-gather,native-direct-planes","--jobs","2",
    "--target-dir",str(ROOT/"target/native-pyramid-profile"),"--message-format=json-render-diagnostics","--locked","--offline"]
save(out/"invocation.json",dict(command=argv,source_files=sources,environment_overrides=fields,
    removed_environment=removed,revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    scope="current-content bindings from prior build path list; constructor only, no fixed controls or images"))
stage="compile"
try:
    check_sources()
    r=b.run(argv,env,ROOT,out/"compile.log",api=api,wall_seconds=180,cpu_seconds=600,log_bytes=16<<20,committed_bytes=4<<30)
    save(out/"compile-process.json",r);check_sources()
    assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"],"compile failed"
    log=(out/"compile.log").read_text(encoding="utf-8",errors="replace");artifacts=[]
    assert "Compiling strehl-cli" in log,"fresh CLI example compilation required"
    for line in log.splitlines():
        try:a=json.loads(line)
        except ValueError:continue
        if a.get("reason")=="compiler-artifact" and a.get("target",{}).get("name")=="native-gpu-preflight" and a.get("executable"):
            assert "example" in a["target"]["kind"] and a["profile"]["test"] and a.get("fresh") is False,"fresh example test required"
            artifacts.append(a)
    assert len(artifacts)==1,"one compiled example required"
    built=Path(artifacts[0]["executable"]).resolve();assert built.is_relative_to(ROOT/"target/native-pyramid-profile")
    assert retained()+built.stat().st_size<=256<<20,"retained preflight bound"
    exe=out/"native-gpu-preflight.exe";shutil.copyfile(built,exe);held=ref(exe)
    assert m.binding(built)==m.binding(exe),"copied executable differs"
    save(out/"executable.json",dict(executable=held,cargo_artifact=artifacts[0]))
    stage="runtime";check_sources();assert m.binding(exe)=={k:held[k] for k in ("bytes","sha256")}
    run_argv=[str(exe),"--exact","coordinate_pipeline_preflight","--nocapture","--test-threads=1"]
    save(out/"run-invocation.json",dict(command=run_argv,executable=held,source_files=sources,
        environment_overrides=fields,removed_environment=removed))
    r=m.run(run_argv,env,ROOT,out/"run.log",api=api,wall_seconds=30,cpu_seconds=30,log_bytes=2<<20,committed_bytes=1<<30)
    save(out/"run-process.json",r);check_sources()
    assert m.binding(exe)=={k:held[k] for k in ("bytes","sha256")},"runtime executable changed"
    assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"],"pipeline preflight failed"
    log=(out/"run.log").read_text(encoding="utf-8");assert "1 passed; 0 failed" in log,"preflight test did not pass"
    lines=[line[line.index('{'):] for line in log.splitlines() if '{' in line]
    assert len(lines)==1,"one preflight JSON record required"
    result=json.loads(lines[0]);save(out/"pipeline.json",result)
    assert result["status"]=="COORDINATE_PIPELINE_READY" and result["coordinate_compilation"] and result["hardware"]
    assert result["gather_compilation"]["original_sha256"]=="41658a89bd9b17c73b0f452b48bde689679e4ecc50774872ebfff0171cdb6560"
    assert result["gather_compilation"]["submitted_sha256"]=="a7dce2107ce7713ac4d9cd961dd44e303bd69b37c2d2ca7029f20aa1f131de9d"
    assert retained()<=256<<20,"retained preflight bound"
    save(out/"completion.json",dict(status="COORDINATE_PIPELINE_READY",executable=held,pipeline=m.binding(out/"pipeline.json")))
    print("COORDINATE_PIPELINE_READY",flush=True)
except BaseException as error:
    save(out/"failure.json",dict(status="PREFLIGHT_FAILED",stage=stage,error=repr(error)))
    raise
