"""Build only the small saved-RGB example, using existing bounded processes."""
from pathlib import Path
import importlib.util,sys,json,shutil
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location("bounded",ROOT/"experiments/m193c-output-grid/bounded-process.py")
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def save(p,v):
    with p.open("x",encoding="utf-8") as f: json.dump(v,f,indent=2);f.write("\n")
def ref(p):return dict(path=str(p),**m.binding(p))
out=HERE/"patch-render-build-2";out.mkdir()
sources=[ref(ROOT/p) for p in ["crates/strehl-cli/src/image_out.rs","crates/strehl-cli/examples/saved-rgb-render.rs","crates/strehl-core/src/color.rs","crates/strehl-core/src/highlight.rs", "crates/strehl-cli/Cargo.toml","Cargo.lock"]]
argv=["cargo","build","-p","strehl-cli","--example","saved-rgb-render","--release",
      "--features","native-pyramid-profile,native-gpu-gather,native-direct-planes",
      "--target-dir",str(ROOT/"target/native-pyramid-profile"),"--jobs","2","--locked","--offline","--message-format=json-render-diagnostics"]
env,removed=m.clean_environment([("RAYON_NUM_THREADS","8"),("CARGO_INCREMENTAL","0")])
save(out/"invocation.json",dict(command=argv,source_files=sources,removed_environment=removed,scope="saved-patch developer only; no RAW or full CLI replay"))
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
r=m.run(argv,env,ROOT,out/"compile.log",api=api,wall_seconds=600,cpu_seconds=1800,log_bytes=16<<20,committed_bytes=8<<30)
save(out/"build-result.json",r)
print(json.dumps({k:r[k] for k in ("exit_code","error","wall_seconds")}),flush=True)
assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
log=(out/"compile.log").read_text(encoding="utf-8",errors="replace");assert "Compiling strehl-cli" in log
found=[]
for line in log.splitlines():
    try: a=json.loads(line)
    except ValueError:continue
    if a.get("reason")=="compiler-artifact" and a.get("executable") and a.get("target",{}).get("name")=="saved-rgb-render":found.append(a["executable"])
assert len(found)==1
exe=out/"saved-rgb-render.exe";shutil.copyfile(found[0],exe)
for record in sources:assert ref(Path(record["path"]))==record
save(out/"executable.json",ref(exe));print(json.dumps(ref(exe)),flush=True)
