"""Run independent controls, then the one fixed generated NCC comparison."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("sinc_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def read(p): return json.loads(p.read_text(encoding="utf-8"))
def save(p,value):
    with p.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write("\n")
assert sys.argv[1:] in ([], ["--compensated"])
repair = bool(sys.argv[1:])
build=HERE/("build-3" if repair else "build-1");held=read(build/"executable.json");exe=ROOT/held["path"]
receipt=read(build/"invocation.json")
def check():
    assert m.binding(exe)=={k:held[k] for k in ("bytes","sha256")}
    for item in receipt["source_files"]:
        assert m.binding(ROOT/item["path"])=={k:item[k] for k in ("bytes","sha256")},"compiled source changed"
check()
out=HERE/("compensated-1" if repair else "run-1");out.mkdir()
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
save(out/"execution.json",dict(build=m.binding(build/"invocation.json"),executable=held,
    runner=m.binding(HERE/"run.py"),revision=receipt["revision"],scope="no original captures; fixed generated source"))
cpu=0.0;steps=[]
if repair:
    for prior in (HERE/"run-1/literal-process.json", HERE/"diagnostic-1/process.json"):
        previous=read(prior)
        assert previous["exit_code"]==101 and previous["error"] is None and previous["terminal_job_accounting"]
        cpu+=previous["job_accounting"]["total_cpu_100ns"]/1e7
    save(out/"prior-cost.json",dict(aggregate_child_cpu_seconds=cpu, scope="same original120CPU allocation"))
for name,test,output_env in [
    ("literal","align::sinc_peak_diagnostic::tests::sinc_peak_literal_controls","STREHL_SINC_PEAK_OUT"),
    ("consumer","align::sinc_peak_diagnostic::consumer_tests::alignment_sinc_peak_fixed_consumer","STREHL_SINC_PEAK_CONSUMER_OUT")]:
    target=out/(name+".json")
    fields={"RAYON_NUM_THREADS":"2",output_env:str(target)}
    env,removed=m.clean_environment(fields.items())
    argv=[str(exe),"--exact",test,"--ignored","--nocapture","--test-threads=1"]
    save(out/(name+"-invocation.json"),dict(command=argv,environment_overrides=fields,removed_environment=removed))
    r=m.run(argv,env,ROOT,out/(name+".log"),api=api,wall_seconds=120,cpu_seconds=120-cpu,
        log_bytes=4<<20,committed_bytes=2<<30,check=check)
    save(out/(name+"-process.json"),r)
    print(json.dumps(dict(name=name,**{k:r[k] for k in ("exit_code","error","wall_seconds")})),flush=True)
    assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"],"preserve failed finite control; no automatic retry"
    assert "1 passed" in (out/(name+".log")).read_text(encoding="utf-8")
    cpu+=r["job_accounting"]["total_cpu_100ns"]/1e7
    record=read(target)
    if name=="literal": assert record["status"]=="PASS" and record["positive_count"]==9
    else: assert len(record["rows"])==48 and len(record["blocks"])==8 and len(record["timing"])==2
    steps.append(dict(name=name,result=m.binding(target),cpu_seconds=r["job_accounting"]["total_cpu_100ns"]/1e7,
        wall_seconds=r["wall_seconds"],peak_job_commit_bytes=r["job_memory"]["peak_job_memory_used_bytes"]))
record=read(out/"consumer.json")
retained=sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
assert cpu<=120 and retained<=256<<20
save(out/"completion.json",dict(status=record["status"],proceed_to_raw_ladder=record["proceed_to_raw_ladder"],
    steps=steps,aggregate_child_cpu_seconds=cpu,retained_bytes_before_completion=retained,
    scope="generated actual NCC calls only; no automatic RAW ladder or SOTA claim"))
print(json.dumps(dict(status=record["status"],proceed=record["proceed_to_raw_ladder"],blocks=record["blocks"],
    timing=record["timing"],failures=record["failures"],inconclusive=record["inconclusive"]),indent=2),flush=True)
