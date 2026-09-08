"""One fixed AREA4+precise diagnostic; source-only until reviewed exact release."""
import time
START=time.monotonic()
import argparse
from decimal import Decimal, ROUND_CEILING
import hashlib
from pathlib import Path
import sys
import traceback
import types

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
MIB=1<<20
VERSION="m193c-area-four-diagnostic-v1"
COMPLETE="COMPLETE_AREA_FOUR_DIAGNOSTIC_ONLY"
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
PINS={
 "refusal-trace-run.py":"05162ef398426ea7ec9ac434ec3ab637bc2cd7e02331ef93f9534357ffd50268",
 "direct-pair-run.py":"fbf89076ae3e8069ab717796818a6c0a2417637cd29973d533ceefdd1fd82782",
 "native-derivative-run.py":"94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a",
 "coverage-sensor-white-run.py":"16f9e944673aa58b81727fabddadc7192a082cef149e950cd7dda24f217e51cf",
 "real-precise-run.py":"7f71fa2414f72bd994ff1701d7ae8c39d49005a11f0fb60027622e780c43efa6",
 "factor-eight-prototype.py":"86111beb318f270c4532d4a5299d8b6a14413845c5eb384790f3e8d21d959d6f",
 "bounded-process.py":"47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b"}


def need(ok,message):
    if not ok: raise ValueError(message)


def setup(args):
    path=HERE/"refusal-trace-run.py"
    with path.open("rb") as stream: raw=stream.read(4*MIB+1)
    need(len(raw)<=4*MIB and hashlib.sha256(raw).hexdigest()==PINS[path.name],"immutable trace utilities")
    t=types.ModuleType("m193c_area4_trace_helpers");t.__file__=str(path);sys.modules[t.__name__]=t
    exec(compile(raw,str(path),"exec"),t.__dict__)
    raw=t.raw(args.plan);need(t.digest(raw)["sha256"]==args.sha256,"external plan SHA")
    n=t.load_bytes(HERE/"native-derivative-run.py",dict(sha256=PINS["native-derivative-run.py"],bytes=44451),"m193c_area4_native")
    plan=n.strict(raw)
    n.closed(plan,"schema source_bindings trace_baseline prior_work preparation_allowance python_executable commands".split(),"AREA4 plan")
    need(plan["schema"]=="m193c-area-four-plan-v1" and plan["preparation_allowance"]==ALLOWANCE,"versioned fixed arm/allowance")
    for path in (SELF,HERE/"area-four-prototype.py",HERE/"area-four-preregister.md",*(HERE/x for x in PINS)):
        expected=plan["source_bindings"][n.relative(path)]
        need(t.digest(t.raw(path))==expected and (path.name not in PINS or expected["sha256"]==PINS[path.name]),"executed source closure")
    def load(name,label):return t.load_bytes(HERE/name,plan["source_bindings"][n.relative(HERE/name)],"m193c_area4_"+label)
    d=load("direct-pair-run.py","direct");c=load("coverage-sensor-white-run.py","coverage")
    f=load("area-four-prototype.py","representation");q=load("factor-eight-prototype.py","literal_helpers")
    precise=load("real-precise-run.py","factory_helpers")
    need(all(plan["source_bindings"][n.relative(path)]["sha256"]==sha for path,sha in c.PINS.items()),"frozen numerical/runtime pins")
    output=Path(args.output).resolve()
    need(Path.cwd().resolve()==ROOT and output.is_relative_to(HERE) and not output.exists(),"fresh owned output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions)=={"faulthandler","pycache_prefix"} and sys._xoptions["faulthandler"] is True
         and not Path(sys._xoptions["pycache_prefix"]).exists()
         and Path(sys._xoptions["pycache_prefix"]).resolve().is_relative_to(output.parent if args.worker else output),"exact fresh cache/options")
    n.closed(plan["commands"],("parent","worker"),"commands")
    need(t.replace(plan["commands"]["worker" if args.worker else "parent"],args.sha256,args.request_sha256)==sys.orig_argv,"exact original argv")
    t.START=START
    return t,d,c,n,f,q,precise,plan,output,dict(path=str(Path(args.plan).resolve()),**t.digest(raw))


def authority(t,d,n,plan,files):
    refs=plan["trace_baseline"];n.closed(refs,"plan result outer console exit audit".split(),"actual trace baseline")
    old,parent,outer,audit=(t.read(files,refs[k]) for k in ("plan","result","outer","audit"))
    need(old["schema"]=="m193c-refusal-trace-plan-v1" and all(plan["source_bindings"].get(k)==v for k,v in old["source_bindings"].items()),"preserved trace source closure")
    # Execute only the immutable historical metadata authority with its ORIGINAL plan/carry.
    coarse_pairs,private_arms,old_prior=t.authority(n,old,files)
    need(parent["schema"]=="m193c-refusal-trace-run-v1" and parent["status"]=="COMPLETE_SAVED_REFUSAL_TRACE_ONLY"
         and parent["error"] is None and parent["finalization_errors"]==[] and parent["sources_unchanged"] is True
         and parent["source_bindings"]==old["source_bindings"] and parent["prior_work"]==old_prior and t.same(files,parent["plan"],refs["plan"]),"actual completed trace parent")
    need(type(outer["exit_code"]) is int and outer["exit_code"]==0 and outer["admissible_parent_exit"] is True
         and parent["command"]==outer["command"]==t.replace(old["commands"]["parent"],refs["plan"]["sha256"])
         and outer["plan_sha256"]==refs["plan"]["sha256"] and t.checked_raw(files,refs["exit"],64).strip()==b"0","actual trace outer/exit")
    final=n.strict(t.checked_raw(files,refs["console"]).splitlines()[-1])
    need(final["status"]==parent["status"] and final["cpu_accounting_complete"] is True and final["error"] is None and final["finalization_errors"]==[]
         and Path(final["result"]).resolve()==files.path(refs["result"],Path(refs["result"]["path"]).is_absolute()),"actual trace final accounting")
    need(audit["schema"]=="m193c-saved-refusal-trace-audit-v1" and audit["status"]=="PASS_SAVED_REFUSAL_TRACE_OUTCOME_AUDIT"
         and audit["subject_complete"] is True and audit["refused_control"] is None and audit["cpu_accounting_complete"] is True
         and audit["worker_status"]==parent["status"] and audit["actual_final_work"]==final["work_through_final_checks"],"actual independent completed trace audit")
    for key in ("plan","result","outer","console","exit"):need(t.same(files,audit["external"][key],refs[key]),"trace audit association")
    need(t.same(files,audit["worker_result"],parent["worker_result"]),"audited trace worker")
    n.successful_process(parent["child"],parent["child"]["command"])
    worker=t.read(files,parent["worker_result"])
    need(worker["schema"]=="m193c-refusal-trace-worker-v1" and worker["status"]==parent["status"] and worker["error"] is None and worker["finalization_errors"]==[]
         and worker["sources_unchanged"] is True and worker["source_bindings"]==old["source_bindings"] and t.same(files,worker["plan"],refs["plan"])
         and worker["registrar_replay_attempts"]==77 and len(worker["pairs"])==23 and worker["unvisited"]==[]
         and tuple(x["id"] for x in worker["controls"])==t.IDS and all(x["passed"] is True for x in worker["controls"]+worker["pairs"]),"actual complete trace population")
    for index,row in enumerate(worker["pairs"]):
        record=t.read(files,row["record"])
        need(record["passed"] is True and record["pair"]==coarse_pairs[index]["record"]["pair"]
             and t.same(files,record["input"],coarse_pairs[index]["ref"]),"trace of exact cached coarse pair")
    # Read the actual real request bound by its completed parent; do not reconstruct input authority from a path convention.
    real_parent=t.read(files,old["real_baseline"]["result"])
    request=t.read(files,real_parent["request"])
    need(request["schema"]=="m193c-factor-eight-request-v1" and t.same(files,request["plan"],old["real_baseline"]["plan"]),"actual real request association")
    rows,fixtures,schedule=request["rows"],request["fixtures"],request["pairs"]
    need(len(rows)==9 and [(row["ordinal"],row["original_index"]) for row in rows]==list(enumerate(d.ORIGINAL))
         and schedule==d.pair_plan(rows)==[x["record"]["pair"] for x in coarse_pairs] and len(fixtures)==5,"exact9 images/23 directions/5 private fixtures")
    private_features=t.read(files,private_arms[1]["record"]["feature_record"])
    need(any(t.same(files,private_features["fixture"],ref) for ref in fixtures),"same known native private fixture")
    real_worker=t.read(files,real_parent["worker_result"])
    need(len(real_worker["features"])==9,"actual cached feature population")
    for row,ref in zip(rows,real_worker["features"],strict=True):
        feature=t.read(files,ref)
        need(feature["original_index"]==row["original_index"] and t.same(files,feature["tiff"],row["tiff"]),"exact cached real TIFF association")
    prior=t.read(files,plan["prior_work"])
    base=dict(final["work_through_final_checks"])
    exact_wall=Decimal(str(parent["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"]))
    need(exact_wall==Decimal(audit["next_wall_seconds"]),"actual conservative trace outer wall")
    base["wall_seconds"]=exact_wall.quantize(Decimal("0.000001"),rounding=ROUND_CEILING)
    need(all(Decimal(str(prior[k]))==Decimal(str(base[k]))+ALLOWANCE[k] for k in ALLOWANCE),"complete trace cost plus preparation; upward microsecond wall ceiling")
    return rows,fixtures,schedule,coarse_pairs,prior


def qualify(f,q,outcome):
    outcome["qualification"]=dict(f.QUALIFIER)
    if "landmarks" in outcome:outcome["site_evidence"]=q.site_evidence(outcome["landmarks"])
    return outcome


def feature_record(n,coarse,native,receipt):
    return dict(representation=receipt,count=len(coarse.keys),coarse_coordinates_q8=coarse.coordinates_q8.tolist(),
        native_coordinates_q8=native.coordinates_q8.tolist(),descriptors_sha256=hashlib.sha256(coarse.descriptors.astype("<i2").tobytes()).hexdigest(),
        keys_sha256=hashlib.sha256(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in coarse.keys])).hexdigest())


def additive_controls(t,d,c,n,f,q,precise,files,v1,fixtures,rows,save):
    np=v1.np;active=None
    def record(name,ok,evidence):
        row=dict(id=name,passed=bool(ok),evidence=evidence);rows.append(row);save(name,row);need(ok,"AREA4 control: "+name)
    def call(a,z,mode="count"):return qualify(f,q,d.observe_pair(v1,a,z,mode))
    def corners(got):return [] if got["transform"] is None else q.corner_errors(got["transform"])
    try:
        active="area4-half-ties";sums=(7,8,9,23,24,25);blocks=[]
        for total in sums:
            block=np.full((16,3),total//16,dtype=np.uint16);block[:total%16]+=1;blocks.append(block.reshape(4,4,3))
        blocks.append(np.full((4,4,3),65535,dtype=np.uint16))
        actual=f.area4(np,np.concatenate(blocks,axis=1));expected=[[[x]*3 for x in (0,0,1,1,2,2,65535)]]
        record(active,actual.tolist()==expected,dict(input_channel_sums=list(sums)+[16*65535],actual=actual.tolist(),expected=expected))
        del blocks,block,actual
        active="repeated-block-null"
        known=c.strict(c.raw_read(c.FIXTURES,MIB))["synthetic_overlap"]["sources"]
        fixture=next(ref for ref in fixtures if ref["sha256"]==known[0]["source_sha256"])
        original=d.decode_blob(c,n,files,fixture,v1);need(original.shape==(288,384,3),"unchanged original private fixture")
        native=np.repeat(np.repeat(original,8,axis=0),8,axis=1)
        rotated=np.ascontiguousarray(np.rot90(native,k=1))
        coarse_ref,receipt_ref=f.representation(np,native);coarse_src,receipt_src=f.representation(np,rotated)
        del native,rotated
        expected_ref=np.repeat(np.repeat(original,2,axis=0),2,axis=1)
        expected_src=np.ascontiguousarray(np.rot90(expected_ref,k=1))
        hashes={k:hashlib.sha256(v.astype("<u2",copy=False).tobytes()).hexdigest() for k,v in
            (("expected_reference",expected_ref),("coarse_reference",coarse_ref),("expected_rotation",expected_src),("coarse_source",coarse_src))}
        record(active,coarse_ref.shape==(576,768,3) and coarse_src.shape==(768,576,3)
            and np.array_equal(coarse_ref,expected_ref) and np.array_equal(coarse_src,expected_src),
            dict(fixture=fixture,native_repeat_factor=8,expected_coarse_repeat_factor=2,reference=receipt_ref,source=receipt_src,actual_sha256=hashes))
        del original,expected_ref,expected_src
        active="native-rotation-positive"
        wr=precise.new_witness("private",0);cr=precise.precise_call(v1,wr,lambda:v1.extract_features(coarse_ref))
        ws=precise.new_witness("private",1);cs=precise.precise_call(v1,ws,lambda:v1.extract_features(coarse_src))
        del coarse_ref,coarse_src
        ref=f.lifted(np,v1,cr);src=f.lifted(np,v1,cs)
        saved_features=dict(schema="m193c-area-four-private-diagnostic-features-v1",fixture=fixture,qualification=dict(f.QUALIFIER),
            reference=feature_record(n,cr,ref,receipt_ref),source=feature_record(n,cs,src,receipt_src))
        feature_path=files.budget.output/"rotation-feature-record.json";files.budget.save(feature_path,saved_features)
        feature_ref=files.bind(feature_path,4*MIB,True)
        positive=call(ref,src)
        record(active,positive["status"]=="RETURNED" and len(positive["landmarks"])>=24 and q.literal_corner_pass(positive["transform"]),
            dict(features=feature_ref,outcome=positive,corner_errors=corners(positive),literal_truth_q32=q.rotation_truth(),precise_factories=list(precise.OBSERVATIONS["private"])))
        active="native-two-pixel-map-destroyer"
        bad=dict(positive["transform"]);bad["tx"]+=2*q.Q32
        record(active,not q.literal_corner_pass(bad),dict(baseline=positive["transform"],mutated=bad,qualification=dict(f.QUALIFIER),
            corner_errors=q.corner_errors(bad),added_native_px=2))
        active="centre-offset-destroyer"
        missing=call(f.lifted(np,v1,cr,omit_centre=True),f.lifted(np,v1,cs,omit_centre=True))
        missing["qualification"].update(coordinate_gauge="active faulty coordinates; q_fault=4*q_coarse+0",
            expected_ordinary_coordinate_gauge=f.QUALIFIER["coordinate_gauge"],active_defect="omitted +384 Q8 on both endpoints")
        record(active,missing["status"]=="RETURNED" and not q.literal_corner_pass(missing["transform"]),
            dict(features=feature_ref,outcome=missing,corner_errors=corners(missing),active_omission_q8=384))
        active="native-rotation-restored"
        restored_ref=f.lifted(np,v1,cr);restored_src=f.lifted(np,v1,cs)
        restored_features=dict(schema="m193c-area-four-private-diagnostic-features-v1",fixture=fixture,qualification=dict(f.QUALIFIER),
            reference=feature_record(n,cr,restored_ref,receipt_ref),source=feature_record(n,cs,restored_src,receipt_src))
        restored=call(restored_ref,restored_src)
        comparisons=[t.compare(n,"entire-restored-private-features",restored_features,saved_features),t.compare(n,"entire-restored-outcome",restored,positive)]
        record(active,all(x["equal"] for x in comparisons) and restored["status"]=="RETURNED" and q.literal_corner_pass(restored["transform"]),
            dict(outcome=restored,corner_errors=corners(restored),canonical_comparisons=comparisons))
        active="rotation-observer-null"
        off=call(ref,src,"off");placebo=call(ref,src,"placebo")
        comparisons=[t.compare(n,"observer-count-vs-"+name,d.signature(restored),d.signature(got)) for name,got in (("off",off),("placebo",placebo))]
        record(active,all(x["equal"] for x in comparisons) and len(restored["landmarks"])>=24,
            dict(canonical_comparisons=comparisons,off=off,count=restored,placebo=placebo))
    except BaseException:
        if active is not None and (not rows or rows[-1]["id"]!=active):
            row=dict(id=active,passed=False,evidence=dict(exception=traceback.format_exc()));rows.append(row);save(active,row)
        raise
    need(tuple(row["id"] for row in rows)==d.CONTROL_IDS+f.CONTROL_IDS,"fourteen fixed complete controls")


def worker(t,d,c,n,f,q,precise,plan,plan_ref,args,output,b,files,result,rows,fixtures,schedule,coarse_pairs):
    raw=t.raw(args.request,MIB);need(t.digest(raw)["sha256"]==args.request_sha256,"actual worker request SHA")
    request=n.strict(raw);result["request"]=dict(path=str(Path(args.request).resolve()),**t.digest(raw));files.verify(result["request"],MIB,True)
    n.closed(request,"schema plan rows fixtures pairs area8_pair_refs prior_work".split(),"AREA4 request")
    need(request["schema"]=="m193c-area-four-diagnostic-request-v1" and request["plan"]==plan_ref and request["rows"]==rows
         and request["fixtures"]==fixtures and request["pairs"]==schedule and request["area8_pair_refs"]==[x["ref"] for x in coarse_pairs],"exact requested population")
    n.closed(request["prior_work"],ALLOWANCE,"request carried work")
    need(all((n.number(request["prior_work"][k]) if k.endswith("seconds") else n.integer(request["prior_work"][k]))
        and request["prior_work"][k]>=result["prior_work"][k] for k in ALLOWANCE),"typed at-least-plan request carry")
    b.save(output/"pair-plan.json",dict(rows=rows,pairs=schedule,area8_pair_refs=request["area8_pair_refs"]))
    consumer=d.load(c.CONSUMER,plan["source_bindings"][n.relative(c.CONSUMER)],"m193c_area4_consumer")
    v1=consumer.v1;result["runtime_before"]=c.runtime(consumer)
    need(result["runtime_before"]==c.strict(c.raw_read(c.CONTRACT,MIB))["reference_environment"],"frozen numerical runtime")
    def save_control(name,row):
        path=output/("control-"+name+".json");b.save(path,row);result["control_records"].append(files.bind(path,4*MIB,True))
    need(not precise.FACTORY_ACTIVE and precise.OBSERVATIONS=={"private":[],"real":[]},"fresh scoped precision helper")
    d.controls(c,n,files,v1,fixtures,result["controls"],save_control)
    need(not precise.FACTORY_ACTIVE and precise.OBSERVATIONS=={"private":[],"real":[]},"legacy controls use unchanged default constructor")
    additive_controls(t,d,c,n,f,q,precise,files,v1,fixtures,result["controls"],save_control)
    b.save(output/"controls.json",result["controls"])
    features=[]
    for row in rows:
        record=dict(schema="m193c-area-four-diagnostic-feature-v1",original_index=row["original_index"],tiff=row["tiff"],
            status="FEATURE_UNAVAILABLE",error=None,representation=None,qualification=dict(f.QUALIFIER))
        try:
            result["real_decode_attempts"]+=1;rgb=d.decode_blob(c,n,files,row["tiff"],v1)
            try:
                need(rgb.shape==(4688,7032,3),"admitted native image shape")
                coarse,receipt=f.representation(v1.np,rgb);record["representation"]=receipt
                need(coarse.shape==(1172,1758,3),"fixed AREA4 coarse image shape")
            finally:del rgb
            result["real_decodes_completed"]+=1
            witness=precise.new_witness("real",row["ordinal"]);receipt["precise_factory"]=witness
            try:feature,receipt=precise.precise_call(v1,witness,lambda:f.extract_coarse(v1.np,v1,coarse,receipt))
            finally:del coarse
            record.update(status="RETURNED",count=len(feature.keys),coordinates_q8=feature.coordinates_q8.tolist(),representation=receipt,
                descriptors_sha256=hashlib.sha256(feature.descriptors.astype("<i2").tobytes()).hexdigest(),
                keys_sha256=hashlib.sha256(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in feature.keys])).hexdigest())
        except v1.ContractError as exc:
            if exc.code!=d.CODE:raise
            feature=None;record["error"]=dict(type=type(exc).__name__,code=exc.code,message=str(exc),traceback=traceback.format_exc())
        features.append(feature);path=output/f"feature-{row['ordinal']}.json";b.save(path,record);result["features"].append(files.bind(path,4*MIB,True))
    observations=[]
    for index,pair in enumerate(schedule):
        a,z=features[pair["reference"]],features[pair["source"]]
        outcome=d.observe_pair(v1,a,z) if a is not None and z is not None else dict(status="FEATURE_UNAVAILABLE",unavailable=[i for i in (pair["reference"],pair["source"]) if features[i] is None])
        record=dict(schema="m193c-area-four-diagnostic-pair-v1",pair=pair,area8_precise_baseline=coarse_pairs[index]["ref"],outcome=qualify(f,q,outcome))
        path=output/(pair["id"]+".json");b.save(path,record)
        result["pairs"].append(dict(pair=pair,record=files.bind(path,4*MIB,True),status=outcome["status"]))
        observations.append(record);result["unvisited"]=list(range(index+1,23))
    result["graph"]=d.graph(observations)
    result["graph"].update(scope="Diagnostic direct-pair topology only; no support, placement, overlap or quality admission",qualification=dict(f.QUALIFIER))
    result["development_outcome"]="ZERO_RETURNED_EDGES_AT_FIXED_AREA4" if not result["graph"]["edges"] else "RETURNED_EDGES_REQUIRE_INDEPENDENT_GEOMETRY_AND_CONSUMER_QUALIFICATION"
    result["runtime_after"]=c.runtime(consumer);need(result["runtime_after"]==result["runtime_before"],"stable runtime")


def main():
    parser=argparse.ArgumentParser()
    for name in ("plan","sha256","output"):parser.add_argument("--"+name,required=True)
    parser.add_argument("--worker",action="store_true");parser.add_argument("--request");parser.add_argument("--request-sha256")
    args=parser.parse_args();need(args.worker==(args.request is not None and args.request_sha256 is not None),"worker-only request")
    t,d,c,n,f,q,precise,plan,output,plan_ref=setup(args)
    raw=t.raw(n.repo_path(plan["prior_work"]["path"]),MIB)
    need(t.digest(raw)=={k:plan["prior_work"][k] for k in ("sha256","bytes")},"actual prior carry")
    prior=n.strict(raw);b=t.budget_for(n,output,prior);files=n.Files(b);output.mkdir()
    result=dict(schema="m193c-area-four-diagnostic-worker-v1" if args.worker else "m193c-area-four-diagnostic-run-v1",implementation_version=VERSION,
        status="REFUSED",command=sys.orig_argv,plan=plan_ref,request=None,prior_work=prior,source_bindings=plan["source_bindings"],sources_unchanged=False,
        controls=[],control_records=[],features=[],pairs=[],unvisited=list(range(23)),graph=None,development_outcome=None,child=None,worker_result=None,
        real_decode_attempts=0,real_decodes_completed=0,runtime_before=None,runtime_after=None,qualification=dict(f.QUALIFIER),
        precise_factory_observations=precise.OBSERVATIONS,error=None,finalization_errors=[],work=None,
        fixed_maximum_calls=dict(legacy_feature_extractions=5,private_precise_extractions=2,real_precise_extractions=9,legacy_matcher_calls=6,private_matcher_calls=5,real_matcher_calls=23))
    try:
        files.verify(plan_ref,4*MIB,True);n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True)==Path(sys.executable).resolve(),"actual Python pin")
        rows,fixtures,schedule,coarse_pairs,actual_prior=authority(t,d,n,plan,files);need(actual_prior==prior,"same new prior carry")
        if args.worker:worker(t,d,c,n,f,q,precise,plan,plan_ref,args,output,b,files,result,rows,fixtures,schedule,coarse_pairs)
        else:
            request=dict(schema="m193c-area-four-diagnostic-request-v1",plan=plan_ref,rows=rows,fixtures=fixtures,pairs=schedule,
                area8_pair_refs=[x["ref"] for x in coarse_pairs],prior_work=b.work())
            b.save(output/"request.json",request);ref=files.bind(output/"request.json",MIB,True);result["request"]=ref
            command=t.replace(plan["commands"]["worker"],args.sha256,ref["sha256"])
            need(command[command.index("--output")+1]==str(output/"worker") and command[command.index("--request")+1]==str(output/"request.json"),"actual worker paths")
            process,api=n.load_process(plan,files);env,removed=process.clean_environment()
            removed += [key for key in env if key.upper().startswith("PYTHON")];env={k:v for k,v in env.items() if not k.upper().startswith("PYTHON")};env.update(dict.fromkeys(c.THREADS,"2"))
            result["environment"]={key:env[key] for key in c.THREADS};result["removed_environment"]=sorted(set(removed));b.complete=False
            observed=process.run(command,env,ROOT,output/"worker.log",api=api,check=b.check,**b.limits());result["child"]=observed
            account=observed.get("job_accounting")
            if type(account) is dict and n.integer(account.get("total_cpu_100ns")):
                b.child_cpu=account["total_cpu_100ns"]/1e7;b.complete=observed.get("terminal_job_accounting") is True and account.get("active_processes")==0
            if (output/"worker/result.json").exists():result["worker_result"]=files.bind(output/"worker/result.json",4*MIB,True)
            n.successful_process(observed,command);child=t.read(files,result["worker_result"])
            need(child["schema"]=="m193c-area-four-diagnostic-worker-v1" and child["implementation_version"]==VERSION and child["status"]==COMPLETE
                 and child["error"] is None and child["finalization_errors"]==[] and child["sources_unchanged"] is True and child["command"]==command
                 and child["request"]==ref and child["plan"]==plan_ref and len(child["features"])==9 and len(child["pairs"])==23 and child["unvisited"]==[]
                 and child["real_decode_attempts"]==child["real_decodes_completed"]==9 and len(child["control_records"])==14
                 and tuple(x["id"] for x in child["controls"])==d.CONTROL_IDS+f.CONTROL_IDS and all(x["passed"] is True for x in child["controls"]),"actual complete AREA4 worker")
            # Parent keeps compact control indices; the worker and individual records retain complete evidence.
            result["controls"]=[dict(id=row["id"],passed=row["passed"],record=ref) for row,ref in zip(child["controls"],child["control_records"],strict=True)]
            for key in ("control_records","features","pairs","unvisited","graph","development_outcome","real_decode_attempts","real_decodes_completed","runtime_before","runtime_after","precise_factory_observations"):
                result[key]=child[key]
        result["status"]=COMPLETE
    except BaseException:result["error"]=traceback.format_exc()
    def final():
        files.recheck();b.check(True);result["sources_unchanged"]=True
        need(not precise.FACTORY_ACTIVE,"no factory wrapper survives finalization")
        if result["status"]==COMPLETE:
            need(b.complete,"complete terminal CPU required")
            observations=result["precise_factory_observations"]
            need(len(observations["private"])==2 and len(observations["real"])==9,"exact true extraction population")
            need(all(x["restored"] is True and len(x["calls"])==1 and x["error"] is None for x in observations["private"]),"two completed private true factories")
            need(all(x["restored"] is True and len(x["calls"])<=1 for x in observations["real"]),"bounded restored real factories")
    try:final()
    except BaseException:result["finalization_errors"].append(traceback.format_exc());result["status"]="REFUSED"
    result["work"]=dict(cpu_accounting_complete=b.complete,global_work=b.work(),new_extent_bytes=sum(b.extents.values()),snapshot_bytes=0,
        scope="worker sub-observation; parent Job owns all setup and worker work" if args.worker else "authoritative parent plus terminal Job")
    return 0 if c.publish(n,output/"result.json",result,b.save,final,
        lambda:dict(status=result["status"],result=str(output/"result.json"),work_through_final_checks=b.work(),cpu_accounting_complete=b.complete,
                    error=result["error"],finalization_errors=result["finalization_errors"]),lambda:b.check(True)) else 1


if __name__=="__main__":raise SystemExit(main())
