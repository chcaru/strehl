"""Private false/true/restored-false SIFT upscale experiment. Source-only until release.
No real input population, real feature loop, graph solve or product output exists here.
"""
import time
START=time.monotonic()
import argparse
from decimal import Decimal
import hashlib
from pathlib import Path
import sys
import traceback
import types

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/"experiments/m193c-output-grid"
SELF=Path(__file__).resolve()
MIB=1<<20
PINS={"direct-pair-run.py":"fbf89076ae3e8069ab717796818a6c0a2417637cd29973d533ceefdd1fd82782",
      "factor-eight-run.py":"3699b85aceed462edb8a5641a3847e5a3676a0166cff7a03f630fa670dff6082",
      "factor-eight-prototype.py":"86111beb318f270c4532d4a5299d8b6a14413845c5eb384790f3e8d21d959d6f"}
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
KWARGS=dict(nfeatures=2048,nOctaveLayers=3,contrastThreshold=0.01,edgeThreshold=12,sigma=1.6)
IDS=("cached-repeated-block-null","explicit-false-reproduction","precise-true-observation",
     "restored-false-reproduction","precise-native-rotation-positive",
     "precise-two-pixel-map-destroyer","precise-observer-null")
COMPLETE="COMPLETE_PRIVATE_PRECISE_UPSCALE_CONTROL_ONLY"


def need(ok,message):
    if not ok: raise ValueError(message)


def setup(args):
    p=HERE/"direct-pair-run.py"; raw=p.read_bytes()
    need(len(raw)==24373 and hashlib.sha256(raw).hexdigest()==PINS[p.name],"held direct helper")
    d=types.ModuleType("m193c_precise_direct"); d.__file__=str(p); sys.modules[d.__name__]=d
    exec(compile(raw,str(p),"exec"),d.__dict__)
    cp=HERE/"coverage-sensor-white-run.py"; raw=cp.read_bytes()
    need(d.digest(raw)["sha256"]==d.PINS[cp.name],"held coverage helper")
    c=d.load(cp,d.digest(raw),"m193c_precise_coverage")
    raw=c.raw_read(args.plan,4*MIB); need(d.digest(raw)["sha256"]==args.sha256,"external precise plan SHA")
    plan=c.strict(raw)
    need(set(plan)==set("schema source_bindings factor_eight_baseline prior_work preparation_allowance python_executable commands".split())
         and plan["schema"]=="m193c-precise-upscale-plan-v1","closed precise-upscale plan")
    pins=dict(d.PINS,**PINS)
    for p in (SELF,HERE/"precise-upscale-preregister.md",*(HERE/x for x in pins)):
        ref=plan["source_bindings"][p.relative_to(ROOT).as_posix()]
        need(d.digest(c.raw_read(p,4*MIB))==ref and (p.name not in pins or ref["sha256"]==pins[p.name]),"exact source closure")
    need(all(plan["source_bindings"][p.relative_to(ROOT).as_posix()]["sha256"]==sha for p,sha in c.PINS.items()),"frozen numerical pins")
    def bound(name,module):
        return d.load(HERE/name,plan["source_bindings"][(HERE/name).relative_to(ROOT).as_posix()],module)
    n=bound("native-derivative-run.py","m193c_precise_util")
    f=bound("factor-eight-prototype.py","m193c_precise_representation")
    h=bound("factor-eight-run.py","m193c_precise_factor")
    output=Path(args.output).resolve()
    need(Path.cwd().resolve()==ROOT and output.is_relative_to(HERE) and not output.exists(),"fresh owned output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions)=={"faulthandler","pycache_prefix"}
         and sys._xoptions["faulthandler"] is True and not Path(sys._xoptions["pycache_prefix"]).exists()
         and Path(sys._xoptions["pycache_prefix"]).resolve().is_relative_to(output.parent if args.worker else output),"exact fresh cache/options")
    need(set(plan["commands"])=={"parent","worker"} and
         d.replace(plan["commands"]["worker" if args.worker else "parent"],args.sha256,args.request_sha256)==sys.orig_argv,"exact original argv")
    return d,c,n,f,h,plan,output,dict(path=str(Path(args.plan).resolve()),**d.digest(raw))


def authority(d,c,n,f,h,plan,files):
    refs=plan["factor_eight_baseline"]; n.closed(refs,"plan result outer console exit audit".split(),"factor-eight evidence")
    for ref in refs.values(): files.verify(ref,4*MIB,Path(ref["path"]).is_absolute())
    old,parent,outer,audit=(d.read(files,refs[k]) for k in ("plan","result","outer","audit"))
    need(old["schema"]=="m193c-factor-eight-plan-v1" and
         all(plan["source_bindings"].get(k)==v for k,v in old["source_bindings"].items()),"unchanged exercised source closure")
    _,fixtures,_,_,old_prior=h.authority(d,c,n,old,files)
    need(parent["schema"]=="m193c-factor-eight-run-v1" and parent["status"]=="REFUSED" and
         parent["finalization_errors"]==[] and parent["sources_unchanged"] is True and parent["prior_work"]==old_prior and
         parent["source_bindings"]==old["source_bindings"] and d.same(files,parent["plan"],refs["plan"]),"actual failed factor-eight parent")
    need(type(outer["exit_code"]) is int and outer["exit_code"]==1 and outer["admissible_parent_exit"] is False and
         outer["command"]==parent["command"]==d.replace(old["commands"]["parent"],refs["plan"]["sha256"]) and
         outer["plan_sha256"]==refs["plan"]["sha256"] and c.checked_raw(n,files,refs["exit"],64).strip()==b"1","actual failed parent argv/exit")
    final=n.strict(c.checked_raw(n,files,refs["console"],4*MIB).splitlines()[-1])
    need(final["status"]=="REFUSED" and final["cpu_accounting_complete"] is True and final["finalization_errors"]==[] and
         Path(final["result"]).resolve()==files.path(refs["result"],Path(refs["result"]["path"]).is_absolute()),"actual final accounting")
    need(audit["schema"]=="m193c-saved-factor-eight-audit-v1" and audit["status"]=="PASS_SAVED_FACTOR_EIGHT_OUTCOME_AUDIT"
         and audit["subject_complete"] is False and audit["cpu_accounting_complete"] is True and
         audit["actual_final_work"]==final["work_through_final_checks"] and audit["subject_branch"]=="NAMED_CONTROL_FAILED_ZERO_REAL_DECODES"
         and audit["refused_control"]=="native-rotation-positive","independent actual failed-positive audit")
    for k in ("plan","result","outer","console","exit"):
        need(d.same(files,audit["external"][k],refs[k]),"audit actual association")
    need(d.same(files,audit["worker_result"],parent["worker_result"]),"audit actual worker association")
    worker=d.read(files,parent["worker_result"])
    need(worker["schema"]=="m193c-factor-eight-worker-v1" and worker["status"]=="REFUSED" and
         worker["finalization_errors"]==[] and worker["sources_unchanged"] is True and
         worker["real_decode_attempts"]==worker["real_decodes_completed"]==0 and worker["features"]==worker["pairs"]==[] and
         worker["unvisited"]==list(range(23)) and worker["graph"] is None,"actual no real input visited")
    expected=d.CONTROL_IDS+f.CONTROL_IDS[:3]
    need(tuple(x["id"] for x in worker["controls"])==expected and
         all(x["passed"] is True for x in worker["controls"][:-1]) and worker["controls"][-1]["passed"] is False,"actual failure at fixed positive")
    cached=worker["controls"][-1]
    need(cached["evidence"]["outcome"]["status"]=="RETURNED" and not f.literal_corner_pass(cached["evidence"]["outcome"]["transform"]),"returned but wrong known map")
    worker_dir=files.path(parent["worker_result"],Path(parent["worker_result"]["path"]).is_absolute()).parent
    cached_ref=files.bind(worker_dir/"control-native-rotation-positive.json",4*MIB,True)
    need(d.read(files,cached_ref)==cached,"actual cached positive record")
    feature_ref=cached["evidence"]["features"]; features=d.read(files,feature_ref)
    need(features["schema"]=="m193c-factor-eight-private-features-v1" and any(d.same(files,features["fixture"],x) for x in fixtures),"actual private feature/fixture association")
    prior=d.read(files,plan["prior_work"])
    need(plan["preparation_allowance"]==ALLOWANCE,"fixed nonrefundable preparation")
    base=dict(final["work_through_final_checks"])
    base["wall_seconds"]=Decimal(str(parent["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"]))
    need(base["wall_seconds"]==Decimal(audit["next_wall_seconds"]),"actual outer/audit wall carry")
    need(all(Decimal(str(prior[k]))==Decimal(str(base[k]))+ALLOWANCE[k] for k in ALLOWANCE),"actual failed run plus preparation; no refund")
    return dict(cached_control=cached_ref,cached_features=feature_ref,fixture=features["fixture"]),prior


def private(d,c,n,f,h,files,b,v1,inputs,result,output):
    cached=d.read(files,inputs["cached_control"]); saved=d.read(files,inputs["cached_features"])
    def record(name,ok,evidence):
        row=dict(id=name,passed=bool(ok),evidence=evidence); result["controls"].append(row)
        b.save(output/("control-"+name+".json"),row); need(ok,"precise control: "+name)
    active=IDS[0]
    counts=result["counters"]
    def fit(a,z,mode="count"):
        counts["matcher_calls"]+=1; need(counts["matcher_calls"]<=5,"five private matcher calls maximum")
        return h.qualify(f,d.observe_pair(v1,a,z,mode))
    def arm(name,precise,coarse_ref,coarse_src,receipts):
        original=v1.cv2.SIFT_create
        value=dict(schema="m193c-private-precise-arm-v1",name=name,enable_precise_upscale=precise,constructor_calls=[],factory_restored=False,
                   feature_record=None,outcome=None,error=None)
        constructed=[]
        def factory(*args,**kwargs):
            need(args==() and kwargs==KWARGS and all(type(kwargs[k]) is type(v) for k,v in KWARGS.items()),"exact frozen SIFT constructor arguments")
            actual=dict(kwargs,enable_precise_upscale=precise)
            value["constructor_calls"].append(actual); counts["factory_calls"]+=1
            need(counts["factory_calls"]<=6 and len(value["constructor_calls"])<=2,"six total/two per-arm SIFT factories")
            return original(**actual)
        try:
            v1.cv2.SIFT_create=factory
            try:
                for rgb in (coarse_ref,coarse_src):
                    counts["feature_extraction_attempts"]+=1
                    need(counts["feature_extraction_attempts"]<=6,"six private feature extractions maximum")
                    coarse=v1.extract_features(rgb); native=f.lifted(v1.np,v1,coarse)
                    constructed.append((coarse,native))
            finally:
                v1.cv2.SIFT_create=original
                value["factory_restored"]=v1.cv2.SIFT_create is original
            need(len(value["constructor_calls"])==2 and value["factory_restored"],"two exact constructors and factory restoration")
            features=dict(schema="m193c-factor-eight-private-features-v1",fixture=inputs["fixture"],qualification=dict(h.QUALIFIER),reference=None,source=None)
            for side,(coarse,native),receipt in zip(("reference","source"),constructed,receipts,strict=True):
                features[side]=dict(representation=receipt,count=len(coarse.keys),coarse_coordinates_q8=coarse.coordinates_q8.tolist(),
                    native_coordinates_q8=native.coordinates_q8.tolist(),descriptors_sha256=hashlib.sha256(coarse.descriptors.astype("<i2").tobytes()).hexdigest(),
                    keys_sha256=hashlib.sha256(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in coarse.keys])).hexdigest())
            p=output/(name+"-features.json"); b.save(p,features); value["feature_record"]=files.bind(p,4*MIB,True)
            value["outcome"]=fit(constructed[0][1],constructed[1][1])
            return value,features,(constructed[0][1],constructed[1][1])
        except BaseException:
            value["error"]=traceback.format_exc(); raise
        finally:
            p=output/(name+"-arm.json"); b.save(p,value)
            result["arms"].append(files.bind(p,4*MIB,True))
    try:
        counts["private_decode_attempts"]+=1
        original=d.decode_blob(c,n,files,inputs["fixture"],v1)
        need(original.shape==(288,384,3),"same private fixture shape")
        native=v1.np.repeat(v1.np.repeat(original,8,axis=0),8,axis=1)
        rotated=v1.np.ascontiguousarray(v1.np.rot90(native,k=1))
        coarse_ref,ref_receipt=f.representation(v1.np,native); coarse_src,src_receipt=f.representation(v1.np,rotated)
        del native,rotated
        need(v1.np.array_equal(coarse_ref,original) and v1.np.array_equal(coarse_src,v1.np.rot90(original,k=1)),"actual private block-repeat null")
        del original
        record(active,ref_receipt==saved["reference"]["representation"] and src_receipt==saved["source"]["representation"],
               dict(fixture=inputs["fixture"],reference=ref_receipt,source=src_receipt,cached_features=inputs["cached_features"]))
        active=IDS[1]
        baseline,baseline_features,_=arm("explicit-false",False,coarse_ref,coarse_src,(ref_receipt,src_receipt))
        record(active,baseline_features==saved and d.signature(baseline["outcome"])==d.signature(cached["evidence"]["outcome"])
               and baseline["outcome"]==cached["evidence"]["outcome"],dict(arm=result["arms"][-1],cached_control=inputs["cached_control"],cached_features=inputs["cached_features"]))
        active=IDS[2]
        treatment,true_features,true_pair=arm("precise-true",True,coarse_ref,coarse_src,(ref_receipt,src_receipt))
        record(active,treatment["outcome"]["status"] in ("RETURNED","REGISTRATION_REFUSED") and treatment["factory_restored"],
               dict(arm=result["arms"][-1],scope="Completed fixed observation; this does not admit its map"))
        active=IDS[3]
        restored,restored_features,_=arm("restored-false",False,coarse_ref,coarse_src,(ref_receipt,src_receipt))
        record(active,restored_features==baseline_features==saved and restored["outcome"]==baseline["outcome"]
               and d.signature(restored["outcome"])==d.signature(cached["evidence"]["outcome"]),dict(arm=result["arms"][-1],baseline_arm=result["arms"][0]))
        del coarse_ref,coarse_src
        active=IDS[4]; got=treatment["outcome"]
        errors=[] if got["transform"] is None else f.corner_errors(got["transform"])
        record(active,got["status"]=="RETURNED" and len(got["landmarks"])>=24 and f.literal_corner_pass(got["transform"]),
               dict(arm=result["arms"][1],corner_errors=errors,literal_truth_q32=f.rotation_truth(),qualification=dict(h.QUALIFIER)))
        active=IDS[5]; bad=dict(got["transform"]); bad["tx"]+=2*f.Q32
        record(active,not f.literal_corner_pass(bad),dict(baseline=got["transform"],mutated=bad,corner_errors=f.corner_errors(bad),qualification=dict(h.QUALIFIER)))
        active=IDS[6]
        off=fit(*true_pair,mode="off"); placebo=fit(*true_pair,mode="placebo")
        hashes={label:hashlib.sha256(n.json_bytes(d.signature(value))).hexdigest() for label,value in (("off",off),("count",got),("placebo",placebo))}
        record(active,len(set(hashes.values()))==1 and d.signature(off)==d.signature(got)==d.signature(placebo) and len(got["landmarks"])>=24,
               dict(canonical_signature_sha256=hashes,off=off,count_arm=result["arms"][1],placebo=placebo))
        need(tuple(x["id"] for x in result["controls"])==IDS and counts==dict(private_decode_attempts=1,feature_extraction_attempts=6,factory_calls=6,matcher_calls=5),"complete fixed private population")
    except BaseException:
        if not result["controls"] or result["controls"][-1]["id"]!=active:
            row=dict(id=active,passed=False,evidence=dict(exception=traceback.format_exc(),arms=list(result["arms"])))
            result["controls"].append(row); b.save(output/("control-"+active+".json"),row)
        raise


def main():
    p=argparse.ArgumentParser()
    for name in ("plan","sha256","output"): p.add_argument("--"+name,required=True)
    p.add_argument("--worker",action="store_true"); p.add_argument("--request"); p.add_argument("--request-sha256"); args=p.parse_args()
    need(args.worker==(args.request is not None and args.request_sha256 is not None),"worker-only request")
    d,c,n,f,h,plan,output,plan_ref=setup(args)
    raw=c.raw_read(n.repo_path(plan["prior_work"]["path"]),MIB)
    need(d.digest(raw)=={k:plan["prior_work"][k] for k in ("sha256","bytes")},"actual prior carry")
    prior=n.strict(raw); b=d.budget_for(n,output,prior); b.started=START
    files=n.Files(b); output.mkdir()
    result=dict(schema="m193c-precise-upscale-worker-v1" if args.worker else "m193c-precise-upscale-run-v1",status="REFUSED",
        command=sys.orig_argv,plan=plan_ref,request=None,prior_work=prior,source_bindings=plan["source_bindings"],sources_unchanged=False,
        controls=[],arms=[],counters=dict(private_decode_attempts=0,feature_extraction_attempts=0,factory_calls=0,matcher_calls=0),
        scope="PRIVATE FIXTURE ONLY; no real image population or product admission",qualification=dict(h.QUALIFIER),
        child=None,worker_result=None,runtime_before=None,runtime_after=None,error=None,finalization_errors=[],work=None)
    try:
        files.verify(plan_ref,4*MIB,True); n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True)==Path(sys.executable).resolve(),"actual Python pin")
        inputs,actual_prior=authority(d,c,n,f,h,plan,files); need(actual_prior==prior,"same new prior carry")
        if args.worker:
            raw=c.raw_read(args.request,MIB); need(d.digest(raw)["sha256"]==args.request_sha256,"actual worker request")
            request=n.strict(raw); result["request"]=dict(path=str(Path(args.request).resolve()),**d.digest(raw)); files.verify(result["request"],MIB,True)
            n.closed(request,"schema plan inputs prior_work".split(),"private worker request")
            need(request["schema"]=="m193c-precise-upscale-request-v1" and request["plan"]==plan_ref and request["inputs"]==inputs and
                 all(request["prior_work"][k]>=prior[k] for k in prior),"same private request and carried setup work")
            consumer=d.load(c.CONSUMER,plan["source_bindings"][c.CONSUMER.relative_to(ROOT).as_posix()],"m193c_precise_consumer")
            result["runtime_before"]=c.runtime(consumer)
            need(result["runtime_before"]==c.strict(c.raw_read(c.CONTRACT,MIB))["reference_environment"],"frozen runtime")
            private(d,c,n,f,h,files,b,consumer.v1,inputs,result,output)
            result["runtime_after"]=c.runtime(consumer); need(result["runtime_after"]==result["runtime_before"],"stable runtime")
        else:
            request=dict(schema="m193c-precise-upscale-request-v1",plan=plan_ref,inputs=inputs,prior_work=b.work())
            b.save(output/"request.json",request); ref=files.bind(output/"request.json",MIB,True); result["request"]=ref
            command=d.replace(plan["commands"]["worker"],args.sha256,ref["sha256"])
            need(command[command.index("--output")+1]==str(output/"worker") and command[command.index("--request")+1]==str(output/"request.json"),"actual worker paths")
            process,api=n.load_process(plan,files); env,removed=process.clean_environment()
            removed += [k for k in env if k.upper().startswith("PYTHON")]
            env={k:v for k,v in env.items() if not k.upper().startswith("PYTHON")}; env.update(dict.fromkeys(c.THREADS,"2"))
            result["environment"]={k:env[k] for k in c.THREADS}; result["removed_environment"]=sorted(set(removed)); b.complete=False
            observed=process.run(command,env,ROOT,output/"worker.log",api=api,check=b.check,**b.limits())
            result["child"]=observed; account=observed.get("job_accounting")
            if type(account) is dict and n.integer(account.get("total_cpu_100ns")):
                b.child_cpu=account["total_cpu_100ns"]/1e7; b.complete=observed.get("terminal_job_accounting") is True and account.get("active_processes")==0
            if (output/"worker/result.json").exists(): result["worker_result"]=files.bind(output/"worker/result.json",4*MIB,True)
            n.successful_process(observed,command); child=d.read(files,result["worker_result"])
            need(child["status"]==COMPLETE and child["error"] is None and child["finalization_errors"]==[] and child["sources_unchanged"] is True and
                 child["command"]==command and child["request"]==ref and child["plan"]==plan_ref and
                 tuple(x["id"] for x in child["controls"])==IDS and all(x["passed"] is True for x in child["controls"]) and
                 child["counters"]==dict(private_decode_attempts=1,feature_extraction_attempts=6,factory_calls=6,matcher_calls=5),"actual complete private worker")
        result["status"]=COMPLETE
    except BaseException: result["error"]=traceback.format_exc()
    def final():
        files.recheck(); b.check(True); result["sources_unchanged"]=True
        need(result["status"]!=COMPLETE or b.complete,"complete terminal CPU required")
    try: final()
    except BaseException: result["finalization_errors"].append(traceback.format_exc()); result["status"]="REFUSED"
    result["work"]=dict(cpu_accounting_complete=b.complete,global_work=b.work(),new_extent_bytes=sum(b.extents.values()),snapshot_bytes=0,
        scope="worker sub-observation; parent Job owns setup and child work" if args.worker else "authoritative parent plus terminal Job")
    return 0 if c.publish(n,output/"result.json",result,b.save,final,
        lambda:dict(status=result["status"],result=str(output/"result.json"),work_through_final_checks=b.work(),cpu_accounting_complete=b.complete,
                    error=result["error"],finalization_errors=result["finalization_errors"]),lambda:b.check(True)) else 1


if __name__=="__main__": raise SystemExit(main())
