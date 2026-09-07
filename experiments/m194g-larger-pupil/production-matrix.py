"""Fixed38 parent-observed bridge outputs; never computes quality or noise."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
C=None
SEEDS=(None,701,709,719,727,733,739,743,751)


def population():
    result=[]
    for scene_number,scene in enumerate(("flat","textured")):
        for state_number,seed in enumerate(SEEDS):
            state=scene_number*9+state_number
            modes=("hard-floor","floor-pedestal-v1") if state%2==0 else ("floor-pedestal-v1","hard-floor")
            for mode in modes:
                result.append(dict(ordinal=len(result),scene=scene,noise_enabled=seed is not None,seed=seed,
                                   admission=mode,subset="all-five",original_indices=[0,1,2,3,4]))
    for index in (0,4):
        result.append(dict(ordinal=len(result),scene="textured",noise_enabled=False,seed=None,
                           admission="hard-floor",subset=f"endpoint-{index}",original_indices=[index]))
    C.need(len(result)==38 and len({(r["scene"],r["seed"],r["admission"],r["subset"]) for r in result})==38,
           "literal unique38 population")
    return result


def gates(noise_ref,bridge_ref,instrument_ref,build_ref):
    noise,_=C.read_json(noise_ref)
    C.need(set(noise)=={"schema","status","ref_root","manifest","generation_result","independent_read","float_commission","noise_commission"}
           and noise["schema"]=="m194g-software-noise-admission-v1" and noise["status"]=="PASS_SOFTWARE_NOISE_FILES_ONLY"
           and noise["ref_root"]=="repository","actual noise-file admission required")
    for key in ("manifest","generation_result","independent_read","float_commission","noise_commission"):
        C.checked_ref(noise[key])
    bridge,_=C.read_json(bridge_ref)
    refs=("build","private_tests","private_outputs","intended_outputs","independent_read","execution_release")
    C.need(set(bridge)=={"schema","status","ref_root",*refs,"sources_before","sources_after","inputs_before","inputs_after","error","finalization_errors"}
           and bridge["schema"]=="m194g-production-bridge-commission-v1" and bridge["status"]=="PASS_PRODUCTION_BRIDGE_ONLY"
           and bridge["ref_root"]=="repository" and bridge["error"] is None and bridge["finalization_errors"]==[],
           "complete independently commissioned bridge required")
    C.need(C.canonical(bridge["build"])==C.canonical(build_ref),"same compiled bridge required")
    for key in refs: C.checked_ref(bridge[key])
    for stem in ("sources","inputs"):
        C.need(type(bridge[stem+"_before"]) is dict and bridge[stem+"_before"]
               and C.canonical(bridge[stem+"_before"])==C.canonical(bridge[stem+"_after"]),"bridge stable closure")
        for name,value in bridge[stem+"_before"].items(): C.checked_ref(dict(path=name,**value))
    instrument,_=C.read_json(instrument_ref)
    C.need(set(instrument)=={"schema","status","checks","sources_before","sources_after","runtime","work","error",
                             "finalization_errors","execution_release","invocation","fixture","artifacts"}
           and instrument["schema"]=="m194g-quality-instruments-v1" and instrument["status"]=="PASS_QUALITY_INSTRUMENTS_ONLY"
           and instrument["error"] is None and instrument["finalization_errors"]==[],"actual quality instruments required")
    checks=instrument["checks"]
    C.need(type(checks) is list and len(checks)==69 and len({x["id"] for x in checks})==69
           and all(set(x)=={"id","passed","details"} and type(x["id"]) is str and x["passed"] is True for x in checks),
           "all69 actual instrument checks")
    C.need(type(instrument["sources_before"]) is dict and instrument["sources_before"]
           and C.canonical(instrument["sources_before"])==C.canonical(instrument["sources_after"]),"instrument source closure")
    for name,value in instrument["sources_before"].items(): C.checked_ref(dict(path=name,**value))


def actual_plan(value,row,noise_ref,build):
    C.need(value["schema"]=="m194g-noise-consumer-plan-v1" and value["noise_admission_sha256"]==noise_ref["sha256"],"plan/noise association")
    selected=value["selected"]
    subset={"all-five":"all","endpoint-0":"first","endpoint-4":"last"}[row["subset"]]
    expected=dict(scene=row["scene"],noise_enabled=row["noise_enabled"],seed=row["seed"],subset=subset)
    C.need(C.canonical({k:selected[k] for k in expected})==C.canonical(expected),"actual planned tuple")
    C.need([f["index"] for f in selected["frames"]]==row["original_indices"]
           and all(type(f["index"]) is int for f in selected["frames"]),"actual original frame list")
    geometry=value["geometry"]
    C.need(geometry["reference_coordinate_gauge"]==2 and type(geometry["reference_coordinate_gauge"]) is int,
           "actual coordinate gauge")
    for local,original in enumerate(row["original_indices"]):
        expected_place=dict(original_index=original,local_index=local,probe_seed_index=local,
                            quad_similarity=dict(a_re=1.0,a_im=0.0,b_re=0.0,b_im=0.0))
        C.need(C.canonical(geometry["placements"][local])==C.canonical(expected_place),"actual placement/probe index")
    C.need(len(geometry["placements"])==len(row["original_indices"])
           and geometry["reference_local_index"]==(2 if row["subset"]=="all-five" else 0),"local reference index")
    config=value["config"]
    wanted="HardFloor" if row["admission"]=="hard-floor" else "FloorPedestalV1"
    C.need(config["admission"]==wanted and config["bands"]==3 and config["space"]=="CameraLinear"
           and config["confidence"] is False and config["exposure_stops"]==0 and config["floor_scale"]=="unset"
           and config["gate_floor_enabled"] is True and value["observer"]["mode"]=="off","actual fixed production configuration")
    C.need(value["build"]["sha256"]==build.record["test_executable"]["sha256"]
           and value["build"]["bytes"]==build.record["test_executable"]["bytes"],"actual plan executable")
    return {k:geometry[k] for k in ("full_native","full_quad","crop_quad","canonical_native_offset","output_native",
                                   "reference_coordinate_gauge","level_sizes")}


def floor_log(ref,count):
    text=C.checked_ref(ref,maximum=C.LOG_LIMIT).read_text(encoding="utf8",errors="strict")
    lines=re.findall(r"^measured floor  : ([^\r\n]*)$",text,re.M)
    contributions=re.findall(r"THE FLOOR THE GATE ACTUALLY USED, averaged over ([0-9]+) warped",text)
    C.need(len(lines)==len(contributions)==1 and int(contributions[0])==count,"actual measured floor/banner count")
    numbers=lines[0].split()
    C.need(1<=len(numbers)<=2 and all(re.fullmatch(r"[0-9]+\.[0-9]{4}",x) is not None for x in numbers),
           "actual finite nonempty measured floor prefix")


def main():
    global C
    parser=argparse.ArgumentParser()
    for field in ("release","build","noise-admission","bridge-commission","instrument-commission"):
        parser.add_argument("--"+field,type=Path,required=True)
        parser.add_argument("--"+field+"-sha256",required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    # Parse only the externally pinned release before executing the dependency.
    with args.release.open("rb") as stream: release_raw=stream.read((4<<20)+1)
    if len(release_raw)>4<<20 or hashlib.sha256(release_raw).hexdigest()!=args.release_sha256:
        raise ValueError("matrix bootstrap release bytes differ")
    bootstrap=json.loads(release_raw)
    command_path=HERE/"production-command.py"
    name=command_path.relative_to(ROOT).as_posix()
    wanted=bootstrap["source_bindings"][name]
    with command_path.open("rb") as stream: raw=stream.read((1<<20)+1)
    if len(raw)>1<<20 or dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))!=wanted:
        raise ValueError("matrix executed command dependency differs")
    spec=importlib.util.spec_from_loader("m194g_production_command",loader=None,origin=str(command_path))
    C=importlib.util.module_from_spec(spec); C.__file__=str(command_path)
    exec(compile(raw,str(command_path),"exec"),C.__dict__)
    extra=[Path(__file__).resolve().relative_to(ROOT).as_posix(),
           "experiments/m194g-larger-pupil/next-quality-matrix-design.md",
           "experiments/m194g-larger-pupil/next-production-controller-design.md"]
    release,release_ref,source_check=C.authorize(args,"quality-production-matrix",extra)
    metadata=C.Metadata(args.output)
    inputs={key:C.ref(getattr(args,key)) for key in ("build","noise_admission","bridge_commission","instrument_commission")}
    result=dict(schema="m194g-production-matrix-v1",status="UNCOMMISSIONED_PRODUCTION_MATRIX",ref_root="repository",
                **{k:inputs[k] for k in ("noise_admission","bridge_commission","instrument_commission")},
                execution_release=release_ref,invocation=list(sys.orig_argv),sources_before=release["source_bindings"],sources_after=None,
                inputs_before={r["path"]:{k:r[k] for k in ("sha256","bytes")} for r in release["inputs"]},inputs_after=None,
                entries=[],work=dict(completed_plans=[],failed_launch=None),error=None,finalization_errors=[])
    build=None
    def recheck():
        source_check()
        if build: build.finish()
        gates(inputs["noise_admission"],inputs["bridge_commission"],inputs["instrument_commission"],inputs["build"])
    try:
        for key,value in inputs.items():
            C.need(value["sha256"]==getattr(args,key+"_sha256") and value in release["inputs"],"released matrix input "+key)
        build=C.Build(inputs["build"])
        recheck()
        rows=population()
        planned=[]
        for row in rows:
            stem=f"case-{row['ordinal']:02d}"
            plan_path=metadata.root/(stem+"-plan.json")
            fields=dict(MODE="plan",NOISE_ADMISSION=str(ROOT/inputs["noise_admission"]["path"]),
                        NOISE_ADMISSION_SHA256=inputs["noise_admission"]["sha256"],SCENE=row["scene"],
                        SEED="noise-off" if row["seed"] is None else str(row["seed"]),
                        SUBSET={"all-five":"all","endpoint-0":"first","endpoint-4":"last"}[row["subset"]],
                        ADMISSION=row["admission"],OBSERVER="off",PLAN=str(plan_path))
            render_fields=dict(fields,MODE="render",PLAN_SHA256="ACTUAL_SAME_CASE_PLAN_SHA256",
                               OUTPUT=str(metadata.root/(stem+".tif")),RECEIPT=str(metadata.root/(stem+"-receipt.json")))
            planned.append(dict(**row,stem=stem,command=[str(build.executable),"--exact",C.TEST,"--ignored","--test-threads=1","--nocapture"],
                                plan_path=str(plan_path),plan_environment=C.environment(fields)[1],
                                render_environment=C.environment(render_fields)[1],
                                render_paths=dict(plan_sha256="ACTUAL_SAME_CASE_PLAN_SHA256",output=str(metadata.root/(stem+".tif")),
                                                  receipt=str(metadata.root/(stem+"-receipt.json"))),observer="off"))
        metadata.json("planned-38-commands.json",dict(schema="m194g-predeclared-matrix-commands-v1",plan_commands=38,render_commands=38,rows=planned))
        plans=[]; common=None
        for row,registered in zip(rows,planned):
            child=C.invoke(build,metadata,kind="plan",ordinal=row["ordinal"],scene=row["scene"],seed=row["seed"],
                           subset={"all-five":"all","endpoint-0":"first","endpoint-4":"last"}[row["subset"]],
                           admission=row["admission"],noise_admission=inputs["noise_admission"],stem=registered["stem"],precheck=recheck)
            result["work"]["failed_launch"]=child["launch"]
            C.need(child["record"]["status"]=="COMPLETE_CHILD_EXIT_ZERO","matrix plan child failed")
            C.need(child.get("error") is None,"matrix plan artifact validation: "+str(child.get("error")))
            C.need(C.canonical(child["record"]["command"])==C.canonical(registered["command"])
                   and C.canonical(child["record"]["environment"])==C.canonical(registered["plan_environment"]),
                   "actual plan launch differs from predeclared command/environment")
            value,_=C.read_json(child["plan"])
            geometry=actual_plan(value,row,inputs["noise_admission"],build)
            if common is None: common=geometry
            C.need(C.canonical(geometry)==C.canonical(common),"all38 plans share exact output geometry")
            plans.append(child)
            result["work"]["completed_plans"].append(dict(plan=child["plan"],launch=child["launch"]))
            result["work"]["failed_launch"]=None
        C.need(len(plans)==38,"all38 plans must precede pixels")
        metadata.json("resolved-38-plans.json",dict(schema="m194g-resolved-matrix-plans-v1",geometry=common,
                                                    plans=result["work"]["completed_plans"]))
        unique=set()
        for row,registered,plan_child in zip(rows,planned,plans):
            child=C.invoke(build,metadata,kind="render",ordinal=row["ordinal"],scene=row["scene"],seed=row["seed"],
                           subset={"all-five":"all","endpoint-0":"first","endpoint-4":"last"}[row["subset"]],
                           admission=row["admission"],noise_admission=inputs["noise_admission"],plan=plan_child["plan"],
                           stem=registered["stem"],precheck=recheck)
            result["work"]["failed_launch"]=child["launch"]
            C.need(child["record"]["status"]=="COMPLETE_CHILD_EXIT_ZERO","matrix render child failed")
            C.need(child.get("error") is None,"matrix render artifact validation: "+str(child.get("error")))
            expected_environment={k:(plan_child["plan"]["sha256"] if v=="ACTUAL_SAME_CASE_PLAN_SHA256" else v)
                                  for k,v in registered["render_environment"].items()}
            C.need(C.canonical(child["record"]["command"])==C.canonical(registered["command"])
                   and C.canonical(child["record"]["environment"])==C.canonical(expected_environment),
                   "actual render launch differs from predeclared command/environment")
            floor_log(child["log"],len(row["original_indices"]))
            entry=dict(**row,plan=plan_child["plan"],plan_launch=plan_child["launch"],receipt=child["receipt"],
                       tiff=child["tiff"],log=child["log"],launch=child["launch"])
            for key in ("plan","plan_launch","receipt","tiff","log","launch"):
                path=C.checked_ref(entry[key]); stat=path.stat(); identity=(stat.st_dev,stat.st_ino)
                C.need(stat.st_ino!=0 and identity not in unique,"distinct matrix output identities")
                unique.add(identity)
            result["entries"].append(entry)
            result["work"]["failed_launch"]=None
        C.need(len(result["entries"])==38,"complete38 output population")
        result["status"]="COMPLETE_38_RGB_OUTPUTS_UNSCORED"
    except Exception: result["error"]=traceback.format_exc()
    try:
        result["sources_after"]={name:C.digest(ROOT/name) for name in result["sources_before"]}
        result["inputs_after"]={name:C.digest(ROOT/name) for name in result["inputs_before"]}
        C.need(C.canonical(result["sources_before"])==C.canonical(result["sources_after"])
               and C.canonical(result["inputs_before"])==C.canonical(result["inputs_after"]),"matrix final closure")
    except Exception:
        result["status"]="UNCOMMISSIONED_PRODUCTION_MATRIX"
        result["finalization_errors"].append(traceback.format_exc())
    result["work"].update(metadata_and_log_bytes=metadata.bytes,metadata_and_log_limit=64<<20,
                          per_child_wall_seconds=240,per_child_log_bytes=16<<20)
    C.publish(metadata,"run-index.json",result,recheck,failure_status="UNCOMMISSIONED_PRODUCTION_MATRIX")
    print(C.canonical(dict(status=result["status"],entries=len(result["entries"]),result=C.ref(metadata.root/"run-index.json"))).decode(),flush=True)
    return 0 if result["status"]=="COMPLETE_38_RGB_OUTPUTS_UNSCORED" else 1


if __name__=="__main__": raise SystemExit(main())
