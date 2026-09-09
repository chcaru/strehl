"""Two tiny smoke invocations, using existing bounded process helpers."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def ref(p):
    b=p.read_bytes()
    return dict(path=str(p.relative_to(ROOT)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
    return m
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2);f.write("\n")
build=load("signed_build",ROOT/"experiments/m194h-pedestal-causality/bounded-build-process.py")
process=load("signed_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
job=ROOT/"experiments/m12-scorecard/m12-harness.py"
api=build.load_job_api({k:v for k,v in ref(job).items() if k!="path"})
out=HERE/"build-1";out.mkdir()
env,removed=build.clean_environment([("RAYON_NUM_THREADS","4"),("CARGO_INCREMENTAL","0")])
target=ROOT/"target/native-signed-black"
command=["cargo","test","-p","strehl-cli","--bin","strehl","--no-run","--features","native-signed-black","--jobs","2","--target-dir",str(target),"--message-format=json-render-diagnostics","--locked","--offline"]
revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
save(out/"invocation.json",dict(revision=revision,command=command,environment_overrides={"RAYON_NUM_THREADS":"4","CARGO_INCREMENTAL":"0"},removed_environment=removed,sources=[ref(ROOT/p) for p in ["crates/strehl-cli/Cargo.toml","crates/strehl-cli/src/merge_cmd.rs","experiments/native-signed-black/implementation.rs","experiments/native-signed-black/run-smoke.py"]],scope="debug smoke, no native performance claim"))
result=build.run(command,env,ROOT,out/"compile.log",api=api,wall_seconds=300,cpu_seconds=600,log_bytes=16<<20,committed_bytes=3<<30)
save(out/"build-result.json",result)
assert result["exit_code"]==0 and result["error"] is None,result
raw=(out/"compile.log").read_text(encoding="utf-8",errors="replace")
assert "Compiling strehl-cli" in raw,"actual CLI compilation required"
executables=[]
for line in raw.splitlines():
    try:item=json.loads(line)
    except ValueError:continue
    if item.get("reason")=="compiler-artifact" and item.get("executable") and item.get("target",{}).get("name")=="strehl":executables.append(item["executable"])
assert len(executables)==1,executables
exe=out/"cli-tests.exe";shutil.copyfile(executables[0],exe)
save(out/"executable.json",ref(exe))
print(json.dumps({"build_exit":0,"build_wall_seconds":result["wall_seconds"],"compiled_cli":True}),flush=True)
for arm,value in [("clamped","0"),("signed","1")]:
    env2,removed2=process.clean_environment([("RAYON_NUM_THREADS","4"),("STREHL_SIGNED_BLACK",value)])
    argv=[str(exe),"merge_cmd::native_signed_black::tests::signed_cfa_whole_path_smoke","--exact","--ignored","--nocapture","--test-threads=1"]
    save(out/f"smoke-{arm}-invocation.json",dict(command=argv,environment_overrides={"RAYON_NUM_THREADS":"4","STREHL_SIGNED_BLACK":value},removed_environment=removed2,executable=ref(exe),revision=revision))
    r=process.run(argv,env2,ROOT,out/f"smoke-{arm}.log",api=api,wall_seconds=60,cpu_seconds=120,log_bytes=1<<20,committed_bytes=1<<30)
    save(out/f"smoke-{arm}-process.json",r)
    assert r["exit_code"]==0 and r["error"] is None,r
    print(json.dumps({"arm":arm,"exit":0,"wall_seconds":r["wall_seconds"]}),flush=True)
pairs=[]
for label in ("negative","nonnegative"):
    a=HERE/"smoke-clamped"/f"{label}.tiff";b=HERE/"smoke-signed"/f"{label}.tiff"
    same=a.read_bytes()==b.read_bytes()
    assert same,f"constant writer bytes changed: {label}"
    pairs.append(dict(case=label,whole_tiff_equal=same,clamped=ref(a),signed=ref(b)))
save(out/"paired-writer-check.json",dict(pairs=pairs,scope="constant zero and positive companion; no image quality claim"))
print(json.dumps({"smoke":"PASS","whole_tiff_pairs_equal":2}),flush=True)
