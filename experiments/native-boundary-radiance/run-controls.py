"""Run the fixed independent optical-operator control through the existing process helper."""
from pathlib import Path
import importlib.util,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
p=ROOT/"experiments/m193c-output-grid/bounded-process.py"
spec=importlib.util.spec_from_file_location("boundary_controls_process",p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2);f.write("\n")
assert len(sys.argv)==1,"fixed operator controls only"
out=HERE/"controls-1";out.mkdir()
exe=HERE/"build-1/cli-tests.exe"
built=json.loads((exe.parent/"executables.json").read_text(encoding="utf-8"))
assert m.binding(exe)["sha256"]==built["cli-tests"]["sha256"]
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
fields=[("RAYON_NUM_THREADS","2"),("STREHL_PYRAMID_PROFILE","off")]
env,removed=m.clean_environment(fields)
argv=[str(exe),"merge_cmd::native_boundary_radiance::independent_tests::independent_boundary_radiance_controls","--exact","--nocapture","--test-threads=1"]
save(out/"invocation.json",dict(command=argv,executable=m.binding(exe),environment_overrides=dict(fields),removed_environment=removed,revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),scope="independent affine/moment operator controls, no scored image or native RAW"))
result=m.run(argv,env,ROOT,out/"controls.log",api=api,wall_seconds=60,cpu_seconds=180,log_bytes=2<<20,committed_bytes=1<<30)
save(out/"process.json",result)
print(json.dumps(dict(exit_code=result["exit_code"],error=result["error"],wall_seconds=result["wall_seconds"])),flush=True)
assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"]
log=(out/"controls.log").read_text(encoding="utf-8")
assert "1 passed; 0 failed; 0 ignored" in log and "BOUNDARY_RADIANCE_INDEPENDENT:" in log,"control filter did not complete its declared test"
save(out/"results.json",dict(status="INDEPENDENT_OPERATOR_CONTROLS_PASS",scope="operator only; no production-hook, image-quality or physical calibration acceptance",log=m.binding(out/"controls.log")))
