"""Fixed saved-CFA off/apply comparison through the new optical prototype bridge."""
from pathlib import Path
import argparse, importlib.util, json, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
SEEDS=(None,701,709,719,727,733,739,743,751)
p=ROOT/"experiments/m193c-output-grid/bounded-process.py"
spec=importlib.util.spec_from_file_location("boundary_matrix_process",p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def ref(p):
    p=p.resolve();return dict(path=p.relative_to(ROOT).as_posix(),**m.binding(p))
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2);f.write("\n")
def read(p):return json.loads(p.read_text(encoding="utf-8"))
parser=argparse.ArgumentParser()
parser.add_argument("--scene",choices=("flat","textured"),required=True)
args=parser.parse_args()
if args.scene=="textured":
    decision=read(HERE/"score-flat-1/decision.json")
    assert decision["proceed_to_textured"] is True,"flat control did not authorize textured population"
out=HERE/("run-"+args.scene+"-1");out.mkdir()
exe=HERE/"build-2/cli-tests.exe"
built=read(exe.parent/"executables.json")
assert m.binding(exe)["sha256"]==built["cli-tests"]["sha256"]
old=read(ROOT/"experiments/m194g-larger-pupil/production-matrix-1/run-index.json")
baselines={(r["scene"],r["seed"]):r["tiff"] for r in old["entries"] if r["admission"]=="hard-floor" and r["subset"]=="all-five"}
assert set(k[1] for k in baselines if k[0]==args.scene)==set(SEEDS)
admission=ROOT/"experiments/m194g-larger-pupil/independent-noise-files-1/noise-admission.json"
assert m.binding(admission)["sha256"]=="088272bfbeca6d00a816a5de72eeaf7aac8f8ca6e0ef68941ab236655fa298e7"
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
test="merge_cmd::known_scene_benchmark::noise_pupil_bridge::boundary_radiance_bridge::m194g_boundary_radiance_consumer"
save(out/"plan.json",dict(schema="native-boundary-radiance-fixed-pairs-v1",scene=args.scene,runner=ref(Path(__file__)),saved_baseline_index=ref(ROOT/"experiments/m194g-larger-pupil/production-matrix-1/run-index.json"),seeds=SEEDS,modes=["off","apply"],cases=18,maximum_program_primary_tiffs=39,executable=ref(exe),source_revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),noise_admission=ref(admission),controls=ref(HERE/"controls-1/results.json"),timing_scope="one observation per output; not a performance benchmark",failing_inputs=["off bytes differ from saved current HardFloor output","consumer skips,duplicates or reorders original CFA observations","all candidate fits abstain; no evidence of treatment"],quality_authority="independent scorer, fixed flat-first policy"))
rows=[];started=time.monotonic()
for ordinal,(seed,mode) in enumerate((s,mode) for s in SEEDS for mode in ("off","apply")):
    stem=out/("case-%02d"%ordinal)
    output=stem.with_suffix(".tif");receipt=out/(stem.name+"-receipt.json")
    fields=[("RAYON_NUM_THREADS","2"),("STREHL_DEFECT","off"),("STREHL_FIX_CA","off"),("STREHL_FULLRES_GATHER","1"),("STREHL_PYRAMID_WORKERS","2")]
    values=dict(MODE=mode,SCENE=args.scene,SEED="noise-off" if seed is None else str(seed),NOISE_ADMISSION=str(admission),NOISE_ADMISSION_SHA256=m.binding(admission)["sha256"],OUTPUT=str(output),RECEIPT=str(receipt))
    fields.extend(("STREHL_BOUNDARY_BRIDGE_"+k,v) for k,v in values.items())
    env,removed=m.clean_environment(fields)
    argv=[str(exe),test,"--exact","--ignored","--nocapture","--test-threads=1"]
    save(out/(stem.name+"-invocation.json"),dict(command=argv,environment_overrides=dict(fields),removed_environment=removed))
    result=m.run(argv,env,ROOT,stem.with_suffix(".log"),api=api,wall_seconds=120,cpu_seconds=180,log_bytes=2<<20,committed_bytes=1<<30)
    save(out/(stem.name+"-process.json"),result)
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"],(ordinal,result["error"])
    log=stem.with_suffix(".log").read_text(encoding="utf-8")
    assert "1 passed; 0 failed; 0 ignored" in log,"incorrect test population"
    got=read(receipt)
    assert got["schema"]=="native-boundary-radiance-consumer-v1" and got["inputs_unchanged"] is True
    assert got["mode"]==mode and got["scene"]==args.scene and got["seed"]==seed
    assert got["decode_counts"]==[1]*5 and got["output"]["width"]==300 and got["output"]["height"]==226
    assert got["output"]["sha256"]==m.binding(output)["sha256"] and got["executable_sha256"]==m.binding(exe)["sha256"]
    diagnostic=[json.loads(line.split("boundary radiance: ",1)[1]) for line in log.splitlines() if line.startswith("boundary radiance: ")]
    if mode=="off":
        assert not diagnostic
        saved=baselines[(args.scene,seed)]
        saved_path=ROOT/saved["path"]
        assert m.binding(saved_path)=={k:saved[k] for k in ("sha256","bytes")}
        assert output.read_bytes()==saved_path.read_bytes(),"fresh off render differs from saved HardFloor output"
    else:
        assert len(diagnostic)==1 and diagnostic[0]["accepted"]>0,"candidate did not exercise treatment"
    row=dict(ordinal=ordinal,scene=args.scene,seed=seed,mode=mode,output=ref(output),receipt=ref(receipt),process=ref(out/(stem.name+"-process.json")),log=ref(stem.with_suffix(".log")),diagnostics=diagnostic,baseline_identity=mode=="off",consumer_wall_seconds=got["consumer_wall_seconds"])
    save(out/(stem.name+"-result.json"),row);rows.append(row)
    print(json.dumps(dict(case=ordinal,scene=args.scene,seed=seed,mode=mode,wall_seconds=result["wall_seconds"],accepted=diagnostic[0]["accepted"] if diagnostic else None)),flush=True)
    assert time.monotonic()-started<900,"fixed scene wall ceiling"
save(out/"run-index.json",dict(schema="native-boundary-radiance-fixed-pairs-v1",rows=rows,status="COMPLETE_UNSCORED",baseline_identity_count=sum(r["baseline_identity"] for r in rows),plan=ref(out/"plan.json")))

