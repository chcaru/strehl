"""One fixed two-frame RAW inspection with existing bounded child processes."""
from pathlib import Path
import importlib.util,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);sys.modules[name]=obj;spec.loader.exec_module(obj);return obj
m=module("followup_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
author=module("followup_inspection",HERE/"inspect.py")
def ref(path):return dict(path=str(path.resolve()),**m.binding(path))
def save(path,value):
    with path.open("x",encoding="utf-8") as f:json.dump(value,f,indent=2,allow_nan=False);f.write("\n")
assert sys.argv[1:]==[],"one fixed allocation"
author.fixed()
inputs=[author.input_path(i)[1] for i in author.INDICES]
source_paths=[HERE/"inspect.py",HERE/"run.py",HERE/"charter.md",HERE/"independent-review.md",
    ROOT/"experiments/native-background-stroke/inspect.py",ROOT/"experiments/native-background-stroke/sampler.py",
    ROOT/"experiments/M-PHASE0-PHASE/src/clib.py"]
sources=[ref(p) for p in source_paths]
helper=ROOT/"experiments/m12-scorecard/m12-harness.py"
api=m.load_job_api(m.binding(helper))
out=HERE/"run-1";out.mkdir();(out/"secondary").mkdir()
save(out/"plan.json",dict(revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    sources=sources,inputs=inputs,python=ref(Path(sys.executable)),secondary_executable=ref(author.SECONDARY),
    helpers=[ref(helper),ref(ROOT/"experiments/m193c-output-grid/bounded-process.py")],
    limits=dict(per_child_wall_seconds=30,per_child_cpu_seconds=30,per_child_commit_bytes=1<<30,
                aggregate_cpu_seconds=60,retained_bytes=32<<20),scope="two existing originals only; no new build or render"))
records=[]
def run(label,argv):
    spent=sum(v["cpu_seconds"] for v in records);assert spent<60
    fields=dict(OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",RAYON_NUM_THREADS="2")
    env,removed=m.clean_environment(fields.items())
    save(out/(label+"-invocation.json"),dict(command=argv,overrides=fields,removed_environment=removed))
    result=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=30,
        cpu_seconds=min(30,60-spent),log_bytes=1<<20,committed_bytes=1<<30)
    save(out/(label+"-process.json"),result)
    print(json.dumps(dict(label=label,exit_code=result["exit_code"],error=result["error"],wall_seconds=result["wall_seconds"])),flush=True)
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"],"preserve failure; no retry"
    records.append(dict(label=label,cpu_seconds=result["job_accounting"]["total_cpu_100ns"]/1e7,
        wall_seconds=result["wall_seconds"],peak_job_commit_bytes=result["job_memory"]["peak_job_memory_used_bytes"]))
    assert sum(r["cpu_seconds"] for r in records)<=60
    assert sum(p.stat().st_size for p in out.rglob("*") if p.is_file())<=32<<20
py=[sys.executable,"-I","-B",str(HERE/"inspect.py")]
for index in author.INDICES:
    raw,_=author.input_path(index)
    run(f"secondary-{index}",[str(author.SECONDARY),str(raw),str(out/"secondary"),f"frame-{index}","0","6000","512","704"])
    run(f"primary-{index}",py+["primary","--index",str(index),"--out",str(out)])
run("analysis",py+["analyze","--out",str(out)])
assert [author.input_path(i)[1] for i in author.INDICES]==inputs,"original metadata changed"
for held in sources:assert ref(Path(held["path"]))==held,"inspection source changed"
save(out/"completion.json",dict(status="COMPLETE_PENDING_INDEPENDENT_INTERPRETATION",steps=records,
    aggregate_cpu_seconds=sum(r["cpu_seconds"] for r in records),original_metadata_unchanged=True,result=ref(out/"result.json")))
print(json.dumps(dict(status="complete",aggregate_cpu_seconds=sum(r["cpu_seconds"] for r in records))),flush=True)
