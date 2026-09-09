"""Compile the fixed core-only NCC experiment through the existing bounded builder."""
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("sinc_build",ROOT/"experiments/m194h-pedestal-causality/bounded-build-process.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

def ref(path):
    return dict(path=str(path.relative_to(ROOT)),**m.binding(path))
def save(path,value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write("\n")

assert sys.argv[1:] in ([], ["--diagnostic"])
out=HERE/("build-2" if sys.argv[1:] else "build-1");out.mkdir()
files=["crates/strehl-core/Cargo.toml","crates/strehl-core/src/align.rs","crates/strehl-core/src/lib.rs","Cargo.lock"]
files += ["experiments/alignment-sinc-peak/"+name for name in
          ("implementation.rs","consumer-tests.rs","independent-controls.rs","design.md","charter.md","build.py")]
sources=[ref(ROOT/p) for p in files]
env,removed=m.clean_environment([("RAYON_NUM_THREADS","2"),("CARGO_INCREMENTAL","0")])
argv=["cargo","test","-p","strehl-core","--lib","--no-run","--release",
      "--features","alignment-sinc-peak","--jobs","2","--target-dir",str(ROOT/"target/native-pyramid-profile"),
      "--message-format=json-render-diagnostics","--locked","--offline"]
save(out/"invocation.json",dict(command=argv,source_files=sources,
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    environment_overrides={"RAYON_NUM_THREADS":"2","CARGO_INCREMENTAL":"0"},removed_environment=removed,
    scope="core-only compile; no test or original image execution"))
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
r=m.run(argv,env,ROOT,out/"compile.log",api=api,wall_seconds=600,cpu_seconds=1800,log_bytes=16<<20,committed_bytes=4<<30)
save(out/"build-result.json",r)
print(json.dumps({k:r[k] for k in ("exit_code","error","wall_seconds")}),flush=True)
assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
log=(out/"compile.log").read_text(encoding="utf-8",errors="replace")
assert "Compiling strehl-core" in log
found=[]
for line in log.splitlines():
    try: obj=json.loads(line)
    except ValueError: continue
    if obj.get("reason")=="compiler-artifact" and obj.get("executable") and obj.get("target",{}).get("name")=="strehl_core":
        found.append(obj["executable"])
assert len(found)==1
exe=out/"core-tests.exe";shutil.copyfile(found[0],exe)
for held in sources:
    assert ref(ROOT/held["path"])==held,"source changed during build"
save(out/"executable.json",ref(exe))
print(json.dumps(ref(exe)),flush=True)
