"""Versioned whole-record comparison repair; immutable private controller reused.
SOURCE ONLY until reviewed exact release. No experiment runs during generation/import.
"""
import time
START=time.monotonic()
from copy import deepcopy
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
BASE_SHA="bdb52e2a87992709d2479237ed2f275ce6a0e223667b55c3fc6a2c316d0f0547"
PINS={"direct-pair-run.py":"fbf89076ae3e8069ab717796818a6c0a2417637cd29973d533ceefdd1fd82782",
      "factor-eight-run.py":"3699b85aceed462edb8a5641a3847e5a3676a0166cff7a03f630fa670dff6082",
      "factor-eight-prototype.py":"86111beb318f270c4532d4a5299d8b6a14413845c5eb384790f3e8d21d959d6f",
      "precise-upscale-run.py":BASE_SHA}
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
KWARGS=dict(nfeatures=2048,nOctaveLayers=3,contrastThreshold=0.01,edgeThreshold=12,sigma=1.6)
IDS=("cached-repeated-block-null","explicit-false-reproduction","precise-true-observation",
     "restored-false-reproduction","precise-native-rotation-positive",
     "precise-two-pixel-map-destroyer","precise-observer-null")
VERSION="m193c-precise-upscale-canonical-v1"
METHOD="ENTIRE records: immutable n.json_bytes; exact serialized byte equality; no omitted fields or tolerance"
BASE_AUTHORITY=None


def need(ok,message):
    if not ok: raise ValueError(message)


def compare(n,label,left,right):
    a,z=n.json_bytes(left),n.json_bytes(right)
    return dict(label=label,method=METHOD,equal=a==z,
                left=dict(bytes=len(a),sha256=hashlib.sha256(a).hexdigest()),
                right=dict(bytes=len(z),sha256=hashlib.sha256(z).hexdigest()))


def commission(n,cached,cached_ref,result,b,output):
    cases=[]; row=dict(id="whole-record-comparator",passed=False,evidence=dict(cached_control=cached_ref,cases=cases))
    try:
        mixed=deepcopy(cached); changed=0
        for side in ("reference_q8","source_q8"):
            rows=mixed["site_evidence"]["sides"][side]["exact_locations_shared_between_splits"]
            need(rows and all(type(x) is list and len(x)==2 for x in rows),"actual nonempty cached shared sites")
            mixed["site_evidence"]["sides"][side]["exact_locations_shared_between_splits"]=[tuple(x) for x in rows]
            changed+=len(rows)
        need(mixed!=cached and changed>0,"placebo actually changes Python tuple/list equality")
        null=compare(n,"actual-tuple-list-null",mixed,cached); cases.append(dict(expected_equal=True,comparison=null))
        need(null["equal"],"canonical tuple/list null")
        fault=deepcopy(mixed)
        need(fault["landmarks"] and len(fault["landmarks"][0]["reference_q8"])==2,"actual cached landmark exists")
        original=fault["landmarks"][0]["reference_q8"][0]; fault["landmarks"][0]["reference_q8"][0]+=1
        negative=compare(n,"actual-landmark-plus-one-q8",fault,cached); cases.append(dict(expected_equal=False,comparison=negative))
        need(not negative["equal"],"one-Q8 landmark mutation rejected")
        fault["landmarks"][0]["reference_q8"][0]=original
        restored=compare(n,"landmark-restored",fault,cached); cases.append(dict(expected_equal=True,comparison=restored))
        need(restored["equal"],"landmark restoration")
        original=fault["transform"]["tx"]; fault["transform"]["tx"]+=1
        negative=compare(n,"actual-map-tx-plus-one-q32",fault,cached); cases.append(dict(expected_equal=False,comparison=negative))
        need(not negative["equal"],"one-Q32 map-field mutation rejected")
        fault["transform"]["tx"]=original
        restored=compare(n,"map-restored",fault,cached); cases.append(dict(expected_equal=True,comparison=restored))
        need(restored["equal"],"map restoration")
        row["evidence"].update(tuple_converted_shared_coordinates=changed,python_equality=False)
        row["passed"]=True
    except BaseException:
        row["evidence"]["exception"]=traceback.format_exc(); raise
    finally:
        result["comparison_controls"].append(row); b.save(output/"control-whole-record-comparator.json",row)

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
    need(set(plan)==set("schema source_bindings failed_attempt prior_work preparation_allowance python_executable commands".split())
         and plan["schema"]=="m193c-precise-upscale-canonical-plan-v1","closed precise-upscale plan")
    pins=dict(d.PINS,**PINS)
    for p in (SELF,HERE/"precise-upscale-canonical-preregister.md",*(HERE/x for x in pins)):
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
    original_publish=c.publish
    def tagged_publish(n,path,result,*positional,**keywords):
        result["implementation_version"]=VERSION
        result["comparison_method"]=METHOD
        return original_publish(n,path,result,*positional,**keywords)
    c.publish=tagged_publish
    return d,c,n,f,h,plan,output,dict(path=str(Path(args.plan).resolve()),**d.digest(raw))


def authority(d,c,n,f,h,plan,files):
    refs=plan["failed_attempt"]; n.closed(refs,"plan result outer console exit audit".split(),"failed precise attempt")
    for ref in refs.values(): files.verify(ref,4*MIB,Path(ref["path"]).is_absolute())
    old,parent,outer,audit=(d.read(files,refs[k]) for k in ("plan","result","outer","audit"))
    need(old["schema"]=="m193c-precise-upscale-plan-v1" and
         all(plan["source_bindings"].get(k)==v for k,v in old["source_bindings"].items()),"all failed-attempt source bindings preserved")
    # The captured old function sees its original globals/constants. No old plan
    # or historical prior is rewritten to make the new attempt fit its schema.
    inputs,old_prior=BASE_AUTHORITY(d,c,n,f,h,old,files)
    need(parent["schema"]=="m193c-precise-upscale-run-v1" and parent["status"]=="REFUSED" and
         parent["finalization_errors"]==[] and parent["sources_unchanged"] is True and parent["prior_work"]==old_prior and
         parent["source_bindings"]==old["source_bindings"] and d.same(files,parent["plan"],refs["plan"]),"actual precise parent refusal")
    need(type(outer["exit_code"]) is int and outer["exit_code"]==1 and outer["admissible_parent_exit"] is False and
         outer["command"]==parent["command"]==d.replace(old["commands"]["parent"],refs["plan"]["sha256"]) and
         outer["plan_sha256"]==refs["plan"]["sha256"] and c.checked_raw(n,files,refs["exit"],64).strip()==b"1","actual failed precise argv/exit")
    final=n.strict(c.checked_raw(n,files,refs["console"],4*MIB).splitlines()[-1])
    need(final["status"]=="REFUSED" and final["cpu_accounting_complete"] is True and final["finalization_errors"]==[] and
         Path(final["result"]).resolve()==files.path(refs["result"],Path(refs["result"]["path"]).is_absolute()),"actual final precise accounting")
    need(audit["schema"]=="m193c-saved-precise-upscale-audit-v1" and audit["status"]=="PASS_SAVED_PRECISE_UPSCALE_OUTCOME_AUDIT" and
         audit["subject_complete"] is False and audit["refused_control"]=="explicit-false-reproduction" and
         audit["cpu_accounting_complete"] is True and audit["actual_final_work"]==final["work_through_final_checks"],"independent precise refusal audit")
    for k in ("plan","result","outer","console","exit"):
        need(d.same(files,audit["external"][k],refs[k]),"audit actual precise association")
    need(d.same(files,audit["worker_result"],parent["worker_result"]),"audited actual precise worker")
    worker=d.read(files,parent["worker_result"])
    need(worker["schema"]=="m193c-precise-upscale-worker-v1" and worker["status"]=="REFUSED" and
         worker["sources_unchanged"] is True and worker["finalization_errors"]==[] and len(worker["arms"])==1 and
         [(x["id"],x["passed"]) for x in worker["controls"]]==[(IDS[0],True),(IDS[1],False)] and
         worker["counters"]==dict(private_decode_attempts=1,feature_extraction_attempts=2,factory_calls=2,matcher_calls=1),"actual first-false stop only")
    arm=d.read(files,worker["arms"][0]); features=d.read(files,arm["feature_record"])
    cached=d.read(files,inputs["cached_control"]); saved=d.read(files,inputs["cached_features"])
    checks=[compare(n,"saved-failed-features-vs-original",features,saved),
            compare(n,"saved-failed-outcome-vs-original",arm["outcome"],cached["evidence"]["outcome"])]
    need(all(x["equal"] for x in checks) and arm["name"]=="explicit-false" and arm["enable_precise_upscale"] is False and
         arm["factory_restored"] is True and arm["error"] is None,"saved failed-attempt records reproduce cache canonically")
    prior=d.read(files,plan["prior_work"]); need(plan["preparation_allowance"]==ALLOWANCE,"fixed next preparation allowance")
    base=dict(final["work_through_final_checks"])
    base["wall_seconds"]=Decimal(str(parent["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"]))
    need(base["wall_seconds"]==Decimal(audit["next_wall_seconds"]),"actual precise outer wall")
    need(all(Decimal(str(prior[k]))==Decimal(str(base[k]))+ALLOWANCE[k] for k in ALLOWANCE),"failed precise cost plus preparation; no refund")
    return dict(inputs,failed_arm=worker["arms"][0],failed_features=arm["feature_record"],saved_authority_comparisons=checks),prior

def private(d,c,n,f,h,files,b,v1,inputs,result,output):
    cached=d.read(files,inputs["cached_control"]); saved=d.read(files,inputs["cached_features"])
    def record(name,ok,evidence):
        row=dict(id=name,passed=bool(ok),evidence=evidence); result["controls"].append(row)
        b.save(output/("control-"+name+".json"),row); need(ok,"precise control: "+name)
    active=None
    result["comparison_controls"]=[]
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
        commission(n,cached["evidence"]["outcome"],inputs["cached_control"],result,b,output)
        active=IDS[0]
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
        comparisons=[compare(n,"entire-feature-record",baseline_features,saved),
                     compare(n,"entire-frozen-signature",d.signature(baseline["outcome"]),d.signature(cached["evidence"]["outcome"])),
                     compare(n,"entire-outcome-record",baseline["outcome"],cached["evidence"]["outcome"])]
        record(active,all(x["equal"] for x in comparisons),dict(arm=result["arms"][-1],cached_control=inputs["cached_control"],
               cached_features=inputs["cached_features"],canonical_comparisons=comparisons))
        active=IDS[2]
        treatment,true_features,true_pair=arm("precise-true",True,coarse_ref,coarse_src,(ref_receipt,src_receipt))
        record(active,treatment["outcome"]["status"] in ("RETURNED","REGISTRATION_REFUSED") and treatment["factory_restored"],
               dict(arm=result["arms"][-1],scope="Completed fixed observation; this does not admit its map"))
        active=IDS[3]
        restored,restored_features,_=arm("restored-false",False,coarse_ref,coarse_src,(ref_receipt,src_receipt))
        comparisons=[compare(n,"entire-restored-features-vs-fresh-false",restored_features,baseline_features),
                     compare(n,"entire-restored-features-vs-cache",restored_features,saved),
                     compare(n,"entire-restored-outcome-vs-fresh-false",restored["outcome"],baseline["outcome"]),
                     compare(n,"entire-restored-outcome-vs-cache",restored["outcome"],cached["evidence"]["outcome"]),
                     compare(n,"entire-restored-signature-vs-cache",d.signature(restored["outcome"]),d.signature(cached["evidence"]["outcome"]))]
        record(active,all(x["equal"] for x in comparisons),dict(arm=result["arms"][-1],baseline_arm=result["arms"][0],canonical_comparisons=comparisons))
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
        need([(x["id"],x["passed"]) for x in result["comparison_controls"]]==[("whole-record-comparator",True)],"commissioned whole-record comparator")
        need(tuple(x["id"] for x in result["controls"])==IDS and counts==dict(private_decode_attempts=1,feature_extraction_attempts=6,factory_calls=6,matcher_calls=5),"complete fixed private population")
    except BaseException:
        if active is not None and (not result["controls"] or result["controls"][-1]["id"]!=active):
            row=dict(id=active,passed=False,evidence=dict(exception=traceback.format_exc(),arms=list(result["arms"])))
            result["controls"].append(row); b.save(output/("control-"+active+".json"),row)
        raise


def main():
    global BASE_AUTHORITY
    path=HERE/"precise-upscale-run.py"; raw=path.read_bytes()
    need(len(raw)==21313 and hashlib.sha256(raw).hexdigest()==BASE_SHA,"immutable precise controller")
    base=types.ModuleType("m193c_canonical_precise_controller"); base.__file__=str(path); sys.modules[base.__name__]=base
    exec(compile(raw,str(path),"exec"),base.__dict__)
    BASE_AUTHORITY=base.authority
    # Fixed adapter seams only. The controller's limits, status, result schemas,
    # IDs, numerical constants and old authority globals remain unchanged.
    base.setup=setup; base.authority=authority; base.private=private; base.START=START
    return base.main()


if __name__=="__main__": raise SystemExit(main())
