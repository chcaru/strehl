"""Run independent probe-fill and existing gate-floor regressions in the built binary."""
from pathlib import Path
import importlib.util,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
p=ROOT/"experiments/m193c-output-grid/bounded-process.py"
spec=importlib.util.spec_from_file_location("probe_fill_controls",p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2);f.write("\n")
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
out=HERE/"controls-1";out.mkdir()
exe=HERE/"build-1/cli-tests.exe"
assert m.binding(exe)["sha256"]==json.loads((HERE/"build-1/executables.json").read_text(encoding="utf-8"))["cli-tests"]["sha256"]
fields=[("RAYON_NUM_THREADS","8"),("STREHL_PYRAMID_PROFILE","off")]
env,removed=m.clean_environment(fields)
argv=[str(exe),"merge_cmd::gatefloor::","--nocapture","--test-threads=1"]
save(out/"invocation.json",dict(command=argv,source=m.binding(Path(__file__)),executable=m.binding(exe),environment_overrides=dict(fields),removed_environment=removed,revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()))
r=m.run(argv,env,ROOT,out/"tests.log",api=api,wall_seconds=60,cpu_seconds=180,log_bytes=2<<20,committed_bytes=2<<30)
save(out/"process.json",r)
print(json.dumps(dict(exit_code=r["exit_code"],error=r["error"],wall_seconds=r["wall_seconds"])),flush=True)
assert r["exit_code"]==0 and r["error"] is None and not r["cleanup_errors"]
log=(out/"tests.log").read_text(encoding="utf-8",errors="replace")
assert "720 whole-buffer comparisons" in log and "independent_fill_mode_parser ... ok" in log
print(log,flush=True)

