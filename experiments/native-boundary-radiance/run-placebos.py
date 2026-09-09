"""Exactly two colour no-treatment outputs or one fixed displaced-boundary output."""
from pathlib import Path
import argparse, importlib.util, json, sys
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
helper=ROOT/"experiments/m193c-output-grid/bounded-process.py"
spec=importlib.util.spec_from_file_location("boundary_placebo_process",helper)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2);f.write("\n")
def ref(p):
    p=p.resolve();return dict(path=p.relative_to(ROOT).as_posix(),**m.binding(p))
def check_ref(r):
    p=ROOT/r["path"];assert m.binding(p)=={k:r[k] for k in ("sha256","bytes")},str(p)
    return p
parser=argparse.ArgumentParser();parser.add_argument("--case",choices=("color","displaced"),required=True)
args=parser.parse_args()
exe=HERE/"build-2/cli-tests.exe";built=read(exe.parent/"executables.json")
assert m.binding(exe)=={k:built["cli-tests"][k] for k in ("sha256","bytes")}
build=read(exe.parent/"invocation.json")
assert build["revision"]=="7ef4e4a6f6c265f45128cee08d71cec20ae2f695","unexpected build2 revision"
sources=build["source_files"]+[ref(Path(__file__)),ref(helper),ref(ROOT/"experiments/m12-scorecard/m12-harness.py")]
for r in sources:check_ref(r)
prerequisites={"controls":ref(HERE/"controls-1/results.json")}
assert read(HERE/"controls-1/results.json")["status"]=="INDEPENDENT_OPERATOR_CONTROLS_PASS"
if args.case=="displaced":
    decision=HERE/"score-flat-1/decision.json"
    assert read(decision)["proceed_to_textured"] is True,"flat decision did not authorize textured work"
    matrix_path=HERE/"run-textured-1/run-index.json";matrix=read(matrix_path)
    assert matrix["schema"]=="native-boundary-radiance-fixed-pairs-v1" and matrix["status"]=="COMPLETE_UNSCORED"
    expected={(s,mode) for s in (None,701,709,719,727,733,739,743,751) for mode in ("off","apply")}
    assert len(matrix["rows"])==18 and {(r["seed"],r["mode"]) for r in matrix["rows"]}==expected
    assert all(r["scene"]=="textured" for r in matrix["rows"])
    for row in matrix["rows"]:
        for key in ("output","receipt","process","log"):check_ref(row[key])
        assert read(ROOT/row["receipt"]["path"])["executable_sha256"]==m.binding(exe)["sha256"]
    prerequisites.update(flat_decision=ref(decision),completed_textured=ref(matrix_path))
out=HERE/("run-"+args.case+"-1");out.mkdir()
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
fixed=[("RAYON_NUM_THREADS","2"),("STREHL_DEFECT","off"),("STREHL_FIX_CA","off"),("STREHL_FULLRES_GATHER","1"),("STREHL_PYRAMID_WORKERS","2")]
plan=dict(schema="native-boundary-radiance-placebos-v1",case=args.case,primary_tiffs=2 if args.case=="color" else 1,
    maximum_program_primary_tiffs=39,executable=ref(exe),build_invocation=ref(exe.parent/"invocation.json"),
    source_bindings=sources,prerequisites=prerequisites,
    failing_inputs=["colour off/no-treatment whole TIFF differs","no-treatment marker absent","displaced model is unchanged or all fits abstain"],
    quality_authority="independent fixed scorer; this runner does not inspect truth or score quality")
save(out/"plan.json",plan)
def invoke(stem,test,fields):
    env,removed=m.clean_environment(fixed+fields)
    argv=[str(exe),test,"--exact","--ignored","--nocapture","--test-threads=1"]
    save(out/(stem+"-invocation.json"),dict(command=argv,environment_overrides=dict(fixed+fields),removed_environment=removed))
    result=m.run(argv,env,ROOT,out/(stem+".log"),api=api,wall_seconds=120,cpu_seconds=180,log_bytes=2<<20,committed_bytes=1<<30)
    save(out/(stem+"-process.json"),result)
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"],result
    log=(out/(stem+".log")).read_text(encoding="utf-8")
    assert "1 passed; 0 failed; 0 ignored" in log,"incorrect test population"
    diagnostics=[json.loads(line.split("boundary radiance: ",1)[1]) for line in log.splitlines() if line.startswith("boundary radiance: ")]
    print(json.dumps(dict(case=args.case,step=stem,wall_seconds=result["wall_seconds"])),flush=True)
    return diagnostics
rows=[]
if args.case=="color":
    manifest=ROOT/"experiments/m194b-known-scene/producer-output-1/color/noise-off/manifest.json"
    assert m.binding(manifest)["sha256"]=="21fffbadd35149150f98634ff3394c2e4ef6bb0a879ab5fcdebd0336f35fac51"
    for ordinal,mode in enumerate(("off","no-treatment")):
        stem="case-%02d"%ordinal;output=out/(stem+".tif");receipt=out/(stem+"-receipt.json");consumer_plan=out/(stem+"-consumer-plan.json")
        name="m194b_known_scene_consumer" if mode=="off" else "m194b_boundary_radiance_no_treatment_consumer"
        test="merge_cmd::known_scene_benchmark::"+name
        fields={"MANIFEST":str(manifest),"MANIFEST_SHA256":m.binding(manifest)["sha256"],"PLAN":str(consumer_plan),"MODE":"plan"}
        assert not invoke(stem+"-plan",test,[("STREHL_M194B_"+k,v) for k,v in fields.items()])
        planned=read(consumer_plan)
        assert planned["schema"]==("m194b-consumer-plan-v1" if mode=="off" else "native-boundary-radiance-colour-no-treatment-plan-v1")
        fields.update(MODE="render",PLAN_SHA256=m.binding(consumer_plan)["sha256"],SUBSET="all",OUTPUT=str(output),RECEIPT=str(receipt))
        diagnostics=invoke(stem,test,[("STREHL_M194B_"+k,v) for k,v in fields.items()])
        got=read(receipt)
        assert got["schema"]==("m194b-consumer-receipt-v1" if mode=="off" else "native-boundary-radiance-colour-no-treatment-receipt-v1")
        assert got["decode_counts"]==[1]*9 and got["frame_subset_original"]==list(range(9))
        assert got["output"]["sha256"]==m.binding(output)["sha256"] and got["plan_sha256"]==m.binding(consumer_plan)["sha256"]
        assert diagnostics==([] if mode=="off" else [{"configuration":"no-treatment","accepted":0}])
        rows.append(dict(ordinal=ordinal,scene="color",seed=None,mode=mode,output=ref(output),receipt=ref(receipt),
            consumer_plan=ref(consumer_plan),process=ref(out/(stem+"-process.json")),log=ref(out/(stem+".log")),
            plan_process=ref(out/(stem+"-plan-process.json")),diagnostics=diagnostics,manifest=ref(manifest),source_bindings=sources))
    assert (out/"case-00.tif").read_bytes()==(out/"case-01.tif").read_bytes(),"colour no-treatment changed whole TIFF"
    outcome={"whole_tiff_identity":True,"explicit_no_treatment_observed":True}
else:
    admission=ROOT/"experiments/m194g-larger-pupil/independent-noise-files-1/noise-admission.json"
    assert m.binding(admission)["sha256"]=="088272bfbeca6d00a816a5de72eeaf7aac8f8ca6e0ef68941ab236655fa298e7"
    output=out/"case-00.tif";receipt=out/"case-00-receipt.json"
    fields=dict(MODE="displaced",SCENE="textured",SEED="noise-off",NOISE_ADMISSION=str(admission),
        NOISE_ADMISSION_SHA256=m.binding(admission)["sha256"],OUTPUT=str(output),RECEIPT=str(receipt))
    test="merge_cmd::known_scene_benchmark::noise_pupil_bridge::boundary_radiance_bridge::m194g_boundary_radiance_consumer"
    diagnostics=invoke("case-00",test,[("STREHL_BOUNDARY_BRIDGE_"+k,v) for k,v in fields.items()])
    got=read(receipt)
    assert got["schema"]=="native-boundary-radiance-consumer-v1" and got["inputs_unchanged"] is True
    assert got["mode"]=="displaced" and got["scene"]=="textured" and got["seed"] is None
    assert got["decode_counts"]==[1]*5 and got["geometry"]["model_offset"]==146 and got["geometry"]["true_offset"]==142
    assert got["output"]["width"]==300 and got["output"]["height"]==226
    assert got["output"]["sha256"]==m.binding(output)["sha256"] and got["executable_sha256"]==m.binding(exe)["sha256"]
    assert len(diagnostics)==1 and diagnostics[0]["boundary_offset"]==146 and diagnostics[0]["accepted"]>0
    rows.append(dict(ordinal=0,scene="textured",seed=None,mode="displaced",output=ref(output),receipt=ref(receipt),
        process=ref(out/"case-00-process.json"),log=ref(out/"case-00.log"),diagnostics=diagnostics,
        source_bindings=sources,consumer_wall_seconds=got["consumer_wall_seconds"]))
    outcome={"fixed_displaced_model_exercised":True,"quality":"UNSCORED"}
for r in sources:check_ref(r)
check_ref(plan["executable"])
save(out/"run-index.json",dict(schema="native-boundary-radiance-placebos-v1",case=args.case,
    status="COMPLETE_UNSCORED",rows=rows,plan=ref(out/"plan.json"),source_bindings=sources,outcome=outcome))
