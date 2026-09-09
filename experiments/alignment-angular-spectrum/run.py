"""Single bounded execution of the fixed angular-spectrum falsifier."""
from pathlib import Path
import importlib.util,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
helper=ROOT/"experiments/m193c-output-grid/bounded-process.py"
spec=importlib.util.spec_from_file_location("angular_bounded_process",helper);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),**m.binding(p))
def save(p,x):
 with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2);f.write("\n")
assert len(sys.argv)==1
out=HERE/"execution-1";out.mkdir()
sources=[ref(HERE/p) for p in ("operator.py","experiment.py","independent-controls.py","design.md","independent-review.md","charter.md","run.py")]
fields=[(k,"1") for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS")]
env,removed=m.clean_environment(fields)
argv=[sys.executable,"-I","-B",str(HERE/"experiment.py"),"--output-dir",str(HERE/"run-1")]
save(out/"invocation.json",dict(command=argv,revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),sources=sources,environment_overrides=dict(fields),removed_environment=removed,scope="one fixed analytic-image falsifier, independent controls first, no native decode"))
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
result=m.run(argv,env,ROOT,out/"run.log",api=api,wall_seconds=90,cpu_seconds=60,log_bytes=2<<20,committed_bytes=512<<20)
save(out/"process.json",result)
print(json.dumps(dict(exit_code=result["exit_code"],error=result["error"],wall_seconds=result["wall_seconds"])),flush=True)
for r in sources:assert m.binding(ROOT/r["path"])=={k:r[k] for k in ("sha256","bytes")}
assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"]
saved=json.loads((HERE/"run-1/results.json").read_text(encoding="utf-8"))
assert saved["status"]=="COMPLETE_UNINTERPRETED" and len(saved["rows"])==70
save(out/"completion.json",dict(status="COMPLETE_UNINTERPRETED",results=ref(HERE/"run-1/results.json"),controls=ref(HERE/"run-1/controls.json"),process=ref(out/"process.json")))

