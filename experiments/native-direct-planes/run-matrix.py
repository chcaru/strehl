"""Fixed saved M194b off/rounded/float comparison using existing bounded processes."""
from pathlib import Path
import argparse,importlib.util,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
SEEDS=(None,701,709,719,727,733,739,743,751)
p=ROOT/"experiments/m193c-output-grid/bounded-process.py"
spec=importlib.util.spec_from_file_location("direct_matrix_process",p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def ref(p):
    p=p.resolve();return dict(path=p.relative_to(ROOT).as_posix(),**m.binding(p))
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2,allow_nan=False);f.write("\n")
def read(p):return json.loads(p.read_text(encoding="utf-8"))
parser=argparse.ArgumentParser();parser.add_argument("--scene",choices=("flat","detail"),required=True);args=parser.parse_args()
flat_decision=None
if args.scene=="detail":
    flat_decision=HERE/"score-flat-1/decision.json"
    decision=read(flat_decision)
    modes=("off","rounded","float") if decision["proceed_to_precision_detail"] else ("off","rounded")
else:modes=("off","rounded","float")
controls=HERE/"controls-1/results.json";assert read(controls)["status"]=="TWELVE_DIRECT_PLANES_CONTROLS_PASS"
producer=ROOT/"experiments/m194b-known-scene/producer-output-1/producer-result.json"
assert m.binding(producer)["sha256"]=="544d47dbc0fdebcf220094ca53434ca49abfee62f55febec27b36f58c24087cc"
prod=read(producer);assert prod["commission_sha256"]=="0a8eb43a53d8f44a6e803f531fd2e83d12b7a59e280440e730dc6ea6523b50d5"
manifests={r["path"]:r["sha256"] for r in prod["manifests"]}
exe=HERE/"build-2/cli-tests.exe";assert m.binding(exe)["sha256"]==read(exe.parent/"executables.json")["cli-tests"]["sha256"]
out=HERE/("run-"+args.scene+"-1");out.mkdir()
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
test="merge_cmd::known_scene_benchmark::m194b_direct_planes_consumer"
cpu_used=0.0
if args.scene=="detail":cpu_used=read(HERE/"run-flat-1/run-index.json")["aggregate_child_cpu_seconds"]
save(out/"allocation.json",dict(scene=args.scene,modes=modes,runner=ref(Path(__file__)),producer=ref(producer),executable=ref(exe),controls=ref(controls),source_revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),primary_ceiling=33,observer_placebos=1,aggregate_cpu_seconds_limit=60,peak_job_commit_limit=1<<30,timing_scope="tiny saved inputs only; no native throughput claim"))
def invoke(stem,scene,seed,mode,observer=True):
    global cpu_used
    relative=f"{scene}/"+("noise-off" if seed is None else f"seed-{seed}")+"/manifest.json"
    manifest=producer.parent/relative;assert m.binding(manifest)["sha256"]==manifests[relative]
    plan=out/(stem+"-plan.json");receipt=out/(stem+"-receipt.json");output=out/(stem+".tif")
    common=[("RAYON_NUM_THREADS","2"),("STREHL_DEFECT","off"),("STREHL_FIX_CA","off"),("STREHL_FULLRES_GATHER","1"),("STREHL_PYRAMID_WORKERS","2"),("STREHL_DIRECT_PLANES",mode)]
    values=dict(MANIFEST=str(manifest),MANIFEST_SHA256=manifests[relative],PLAN=str(plan),SUBSET="all",DIRECT_OBSERVER="on" if observer else "off")
    processes=[]
    for action in ("plan","render"):
        v=dict(values,MODE=action)
        if action=="render":v.update(PLAN_SHA256=m.binding(plan)["sha256"],OUTPUT=str(output),RECEIPT=str(receipt))
        fields=common+[("STREHL_M194B_"+k,x) for k,x in v.items()]
        env,removed=m.clean_environment(fields);argv=[str(exe),test,"--exact","--ignored","--nocapture","--test-threads=1"]
        label=stem+"-"+action
        save(out/(label+"-invocation.json"),dict(command=argv,environment_overrides=dict(fields),removed_environment=removed))
        assert cpu_used<60,"fixed population child CPU budget exhausted"
        result=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=60,cpu_seconds=60-cpu_used,log_bytes=2<<20,committed_bytes=1<<30)
        save(out/(label+"-process.json"),result)
        assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"],(label,result["error"])
        assert "1 passed; 0 failed; 0 ignored" in (out/(label+".log")).read_text(encoding="utf-8")
        cpu_used+=result["job_accounting"]["total_cpu_100ns"]/1e7
        assert cpu_used<=60
        processes.append(ref(out/(label+"-process.json")))
    got=read(receipt)
    assert got["schema"]=="native-direct-planes-consumer-receipt-v1" and got["direct_planes_mode"]==mode
    assert got["manifest_sha256"]==manifests[relative] and got["plan_sha256"]==m.binding(plan)["sha256"] and got["plan"]==read(plan)
    assert got["frame_subset_original"]==list(range(9)) and got["decode_counts"]==[1]*9
    assert got["output"]["sha256"]==m.binding(output)["sha256"] and (got["output"]["width"],got["output"]["height"])==(284,212)
    evidence=got["direct_planes_evidence"];assert evidence["observer_enabled"]==observer
    if observer:
        assert evidence["input_captures"]==9 and evidence["collapsed_captures"]==1
        assert (evidence["actual_direct_calls"]>0)==(mode!="off") and (evidence["probe_direct_calls"]>0)==(mode!="off")
    row=dict(scene=scene,seed=seed,mode=mode,manifest=ref(manifest),plan=ref(plan),receipt=ref(receipt),output=ref(output),processes=processes)
    save(out/(stem+"-result.json"),row)
    print(json.dumps(dict(scene=scene,seed=seed,mode=mode,observer=observer,aggregate_child_cpu_seconds=cpu_used)),flush=True)
    return row
rows=[];placebo=None
population=[("flat",s) for s in SEEDS] if args.scene=="flat" else [("plane",None),("color",None)]
for scene,seed in population:
    for mode in modes:
        row=invoke("case-%02d"%len(rows),scene,seed,mode);rows.append(row)
        if args.scene=="flat" and seed is None and mode=="off":
            placebo=invoke("observer-placebo",scene,seed,mode,False)
            assert (ROOT/placebo["output"]["path"]).read_bytes()==(ROOT/row["output"]["path"]).read_bytes(),"observer changed output"
            assert read(ROOT/placebo["receipt"]["path"])["output"]["pixel_sha256_le"]==read(ROOT/row["receipt"]["path"])["output"]["pixel_sha256_le"]
result=dict(schema="native-direct-planes-fixed-pairs-v1",status="COMPLETE_UNSCORED",scene=args.scene,rows=rows,controls=ref(controls),producer=ref(producer),allocation=ref(out/"allocation.json"),aggregate_child_cpu_seconds=cpu_used)
if placebo is not None:result["observer_placebo"]=placebo
if flat_decision is not None:result["flat_decision"]=ref(flat_decision)
save(out/"run-index.json",result)
