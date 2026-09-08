"""Exact AREA8 feature export and ONE offline private CPU LightGlue commission."""
import time
START=time.monotonic()
import argparse
from decimal import Decimal,ROUND_CEILING
import hashlib
from pathlib import Path
import sys
import traceback
import types

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
MIB=1<<20
VERSION="m193c-sift-lightglue-commission-v1"
COMPLETE="COMPLETE_SIFT_EXPORT_AND_PRIVATE_LIGHTGLUE_COMMISSION_ONLY"
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
ACQUISITION=dict(cpu_seconds=20,wall_seconds=120,file_bytes=64*MIB,metadata_bytes=MIB)
A4_SHA="2fda937bbf9e37f16bd3bc2fa8de5d5348d0d253432e22fa9366dbf9f798a7d6"
COMMIT="eb42fee2d71449efb0aa5c10549752b5d75384d8"
ASSET_NAMES=dict(matcher="lightglue.py",rootsift_reference="sift.py",license="license.txt",readme="readme.md",checkpoint="sift-lightglue.pth")


def need(ok,message):
    if not ok:raise ValueError(message)


def setup(args):
    path=HERE/"area-four-run.py"
    with path.open("rb") as stream:raw=stream.read(4*MIB+1)
    need(len(raw)==27409 and hashlib.sha256(raw).hexdigest()==A4_SHA,"immutable latest controller")
    a4=types.ModuleType("m193c_export_area4_history");a4.__file__=str(path);sys.modules[a4.__name__]=a4
    exec(compile(raw,str(path),"exec"),a4.__dict__)
    path=HERE/"refusal-trace-run.py"
    raw=path.read_bytes();need(hashlib.sha256(raw).hexdigest()==a4.PINS[path.name],"immutable trace utility")
    t=types.ModuleType("m193c_export_trace");t.__file__=str(path);sys.modules[t.__name__]=t
    exec(compile(raw,str(path),"exec"),t.__dict__)
    n=t.load_bytes(HERE/"native-derivative-run.py",dict(bytes=44451,sha256=a4.PINS["native-derivative-run.py"]),"m193c_export_native")
    raw=t.raw(args.plan);need(t.digest(raw)["sha256"]==args.sha256,"external plan SHA")
    plan=n.strict(raw)
    n.closed(plan,"schema source_bindings area4_baseline acquisition_receipt prior_work preparation_allowance python_executable commands".split(),"eight-key commission plan")
    need(plan["schema"]=="m193c-sift-lightglue-commission-plan-v1" and plan["preparation_allowance"]==ALLOWANCE,"fixed source version/allowance")
    for path in (SELF,HERE/"sift-lightglue-adapter.py",HERE/"sift-lightglue-commission-preregister.md",HERE/"area-four-run.py",*(HERE/x for x in a4.PINS)):
        expected=plan["source_bindings"][n.relative(path)]
        need(t.digest(t.raw(path))==expected and (path.name not in a4.PINS or expected["sha256"]==a4.PINS[path.name]),"complete executed source pin")
    def load(name,label):return t.load_bytes(HERE/name,plan["source_bindings"][n.relative(HERE/name)],"m193c_export_"+label)
    d=load("direct-pair-run.py","direct");c=load("coverage-sensor-white-run.py","coverage")
    f=load("factor-eight-prototype.py","representation");precise=load("real-precise-run.py","precise")
    s=load("sift-lightglue-adapter.py","adapter")
    need(all(plan["source_bindings"][n.relative(path)]["sha256"]==sha for path,sha in c.PINS.items()),"frozen numerical pins")
    output=Path(args.output).resolve()
    need(Path.cwd().resolve()==ROOT and output.is_relative_to(HERE) and not output.exists(),"fresh owned output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions)=={"faulthandler","pycache_prefix"} and sys._xoptions["faulthandler"] is True
         and not Path(sys._xoptions["pycache_prefix"]).exists()
         and Path(sys._xoptions["pycache_prefix"]).resolve().is_relative_to(output.parent if args.worker else output),"exact fresh cache/options")
    n.closed(plan["commands"],("parent","worker"),"commands")
    need(t.replace(plan["commands"]["worker" if args.worker else "parent"],args.sha256,args.request_sha256)==sys.orig_argv,"exact original argv")
    t.START=START
    return a4,t,d,c,n,f,precise,s,plan,output,dict(path=str(Path(args.plan).resolve()),**t.digest(raw))


def authority(a4,t,d,n,plan,files):
    refs=plan["area4_baseline"];n.closed(refs,"plan result outer console exit audit".split(),"actual AREA4 baseline")
    old,parent,outer,audit=(t.read(files,refs[k]) for k in ("plan","result","outer","audit"))
    need(old["schema"]=="m193c-area-four-plan-v1" and all(plan["source_bindings"].get(k)==v for k,v in old["source_bindings"].items()),"preserved all old source bindings")
    rows,fixtures,schedule,area8_pairs,old_prior=a4.authority(t,d,n,old,files)
    need(parent["schema"]=="m193c-area-four-diagnostic-run-v1" and parent["status"]==a4.COMPLETE
         and parent["error"] is None and parent["finalization_errors"]==[] and parent["sources_unchanged"] is True
         and parent["source_bindings"]==old["source_bindings"] and parent["prior_work"]==old_prior and t.same(files,parent["plan"],refs["plan"]),"actual complete AREA4 parent")
    need(type(outer["exit_code"]) is int and outer["exit_code"]==0 and outer["admissible_parent_exit"] is True
         and parent["command"]==outer["command"]==t.replace(old["commands"]["parent"],refs["plan"]["sha256"])
         and outer["plan_sha256"]==refs["plan"]["sha256"] and t.checked_raw(files,refs["exit"],64).strip()==b"0","actual AREA4 outer/exit")
    final=n.strict(t.checked_raw(files,refs["console"]).splitlines()[-1])
    need(final["status"]==parent["status"] and final["cpu_accounting_complete"] is True and final["error"] is None and final["finalization_errors"]==[]
         and Path(final["result"]).resolve()==files.path(refs["result"],Path(refs["result"]["path"]).is_absolute()),"actual final accounting")
    need(audit["schema"]=="m193c-saved-area-four-audit-v1" and audit["status"]=="PASS_SAVED_AREA_FOUR_OUTCOME_AUDIT"
         and audit["subject_complete"] is True and audit["refused_control"] is None and audit["cpu_accounting_complete"] is True
         and audit["worker_status"]==parent["status"] and audit["actual_final_work"]==final["work_through_final_checks"],"independent actual AREA4 audit")
    for key in ("plan","result","outer","console","exit"):need(t.same(files,audit["external"][key],refs[key]),"actual audit association")
    need(t.same(files,audit["worker_result"],parent["worker_result"]),"audited actual worker")
    n.successful_process(parent["child"],parent["child"]["command"])
    worker=t.read(files,parent["worker_result"])
    need(worker["status"]==a4.COMPLETE and worker["schema"]=="m193c-area-four-diagnostic-worker-v1" and worker["error"] is None
         and worker["finalization_errors"]==[] and worker["sources_unchanged"] is True and worker["source_bindings"]==old["source_bindings"]
         and len(worker["controls"])==14 and all(x["passed"] for x in worker["controls"])
         and len(worker["features"])==9 and len(worker["pairs"])==23 and worker["unvisited"]==[]
         and all(x["status"]=="REGISTRATION_REFUSED" for x in worker["pairs"]),"complete latest charged population")
    trace=t.read(files,old["trace_baseline"]["plan"])
    real_parent=t.read(files,trace["real_baseline"]["result"]);real_plan=t.read(files,trace["real_baseline"]["plan"])
    real_worker=t.read(files,real_parent["worker_result"])
    private_parent=t.read(files,real_plan["private_baseline"]["result"]);private_worker=t.read(files,private_parent["worker_result"])
    arm_ref=private_worker["arms"][1];arm=t.read(files,arm_ref);private_ref=arm["feature_record"];private=t.read(files,private_ref)
    need(arm["name"]=="precise-true" and arm["outcome"]["status"]=="RETURNED" and len(real_worker["features"])==9,"actual AREA8 precise export population")
    cached=[t.read(files,x) for x in real_worker["features"]]
    need(all(row["original_index"]==value["original_index"] and t.same(files,row["tiff"],value["tiff"]) and value["status"]=="RETURNED"
             for row,value in zip(rows,cached,strict=True)),"exact cached nine feature associations")
    intake_refs=plan["acquisition_receipt"];n.closed(intake_refs,"plan result outer console exit audit".split(),"independently audited acquisition bundle")
    receipt=t.read(files,intake_refs["result"])
    intake_outer=t.read(files,intake_refs["outer"]);intake_audit=t.read(files,intake_refs["audit"])
    need(receipt["schema"]=="m193c-lightglue-acquisition-v1" and receipt["status"]=="COMPLETE_SOURCE_AND_CHECKPOINT_ACQUISITION_ONLY"
         and receipt["source_commit"]==COMMIT and receipt["reservation"]==ACQUISITION and receipt["errors"]==[],"completed separately charged acquisition")
    # Final receipt field closure is deliberately part of this new source, never inferred from asset paths.
    n.closed(receipt,"schema status plan source_commit asset_release_id assets prior_work reservation charged_work timing command source errors inventory child upstream_checkpoint_digest model_imports image_payloads_opened checkpoint_parses observed_work_plus_final_receipt_reserve metadata_accounting final_tail_allowance timing_scope".split(),"acquisition receipt")
    expected_base=dict(final["work_through_final_checks"])
    wall=Decimal(str(parent["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"]))
    need(wall==Decimal(audit["next_wall_seconds"]),"actual AREA4 conservative outer wall")
    expected_base["wall_seconds"]=float(wall.quantize(Decimal("0.000001"),rounding=ROUND_CEILING))
    need(receipt["prior_work"]==expected_base,"acquisition starts at complete latest cost")
    need(all(Decimal(str(receipt["charged_work"][k]))==Decimal(str(expected_base[k]))+ACQUISITION[k] for k in ALLOWANCE),"full nonrefundable acquisition reservation")
    assets={}
    need(len(receipt["assets"])==5 and {x["id"] for x in receipt["assets"]}==set(ASSET_NAMES),"five exact acquired assets")
    for asset in receipt["assets"]:
        ref={k:asset[k] for k in ("path","sha256","bytes")}
        path=files.verify(ref,64*MIB,Path(ref["path"]).is_absolute())
        need(path==HERE/"lightglue-acquisition-1"/ASSET_NAMES[asset["id"]],"fixed separately acquired asset path")
        assets[asset["id"]]=ref
    need(assets["checkpoint"]["bytes"]==47632573,"official SIFT checkpoint extent")
    for name in ("matcher","rootsift_reference","license","readme"):
        path=files.path(assets[name],Path(assets[name]["path"]).is_absolute())
        need(plan["source_bindings"][n.relative(path)]=={k:assets[name][k] for k in ("bytes","sha256")},"acquired source in current closure")
    files.verify(receipt["source"],4*MIB,Path(receipt["source"]["path"]).is_absolute())
    need(t.same(files,receipt["plan"],intake_refs["plan"]),"actual intake plan association")
    acquisition_plan=t.read(files,intake_refs["plan"])
    need(acquisition_plan["schema"]=="m193c-lightglue-acquisition-plan-v1" and acquisition_plan["source_commit"]==COMMIT
         and receipt["asset_release_id"]==131252238 and receipt["upstream_checkpoint_digest"] is None
         and receipt["model_imports"]==receipt["image_payloads_opened"]==receipt["checkpoint_parses"]==0
         and receipt["command"]==t.replace(acquisition_plan["commands"]["parent"],receipt["plan"]["sha256"])
         and all(plan["source_bindings"].get(k)==v for k,v in acquisition_plan["source_bindings"].items()),"actual acquisition plan/source preservation")
    n.successful_process(receipt["child"],t.replace(acquisition_plan["commands"]["worker"],receipt["plan"]["sha256"]))
    need(plan["source_bindings"][n.relative(files.path(receipt["source"],Path(receipt["source"]["path"]).is_absolute()))]
         =={k:receipt["source"][k] for k in ("bytes","sha256")},"actual acquisition source bound")
    need(all(receipt["observed_work_plus_final_receipt_reserve"][k]<=ACQUISITION[k] for k in ALLOWANCE),"acquisition remained within its full charged reservation")
    need(type(intake_outer["exit_code"]) is int and intake_outer["exit_code"]==0 and intake_outer["admissible_parent_exit"] is True
         and intake_outer["command"]==receipt["command"] and intake_outer["plan_sha256"]==intake_refs["plan"]["sha256"]
         and t.checked_raw(files,intake_refs["exit"],64).strip()==b"0","actual intake outer/exit")
    intake_final=n.strict(t.checked_raw(files,intake_refs["console"]).splitlines()[-1])
    need(intake_final["status"]==receipt["status"] and intake_final["errors"]==[] and intake_final["charged_work"]==receipt["charged_work"]
         and Path(intake_final["result"]).resolve()==files.path(intake_refs["result"],Path(intake_refs["result"]["path"]).is_absolute()),"actual intake final stdout")
    need(intake_audit["schema"]=="m193c-saved-lightglue-acquisition-audit-v1" and intake_audit["status"]=="PASS_SAVED_LIGHTGLUE_ACQUISITION_OUTCOME_AUDIT"
         and intake_audit["subject_complete"] is True and intake_audit["admission_allowed"] is True
         and intake_audit["cpu_accounting_complete"] is True,"independently admitted complete acquisition")
    for key in ("plan","result","outer","console","exit"):need(t.same(files,intake_audit["external"][key],intake_refs[key]),"intake audit exact external association")
    need(any(t.same(files,intake_audit["worker_result"],item) for item in receipt["inventory"]),"audited intake worker in actual saved inventory")
    intake_worker=t.read(files,intake_audit["worker_result"])
    need(intake_worker["status"]==receipt["status"] and intake_worker["command"]==receipt["child"]["command"]
         and t.same(files,intake_worker["plan"],intake_refs["plan"]) and all(x["passed"] is True for x in intake_worker["controls"]),"actual admitted intake worker")
    base=intake_audit["actual_final_work"];n.closed(base,ALLOWANCE,"complete audited acquisition carry")
    need(all(Decimal(str(base[k]))>=Decimal(str(receipt["charged_work"][k])) for k in ALLOWANCE)
         and Decimal(intake_audit["next_wall_seconds"])==Decimal(str(base["wall_seconds"])),"complete audit/tail work never refunded")
    prior=t.read(files,plan["prior_work"]);n.closed(prior,ALLOWANCE,"new complete prior")
    expected=dict(base)
    expected["wall_seconds"]=Decimal(intake_audit["next_wall_seconds"]).quantize(Decimal("0.000001"),rounding=ROUND_CEILING)
    need(all(Decimal(str(prior[k]))==Decimal(str(expected[k]))+ALLOWANCE[k] for k in ALLOWANCE),"audited acquisition carry plus new preparation; conservative microsecond wall")
    return dict(rows=rows,fixtures=fixtures,pairs=schedule,private_ref=private_ref,private=private,
        real_refs=real_worker["features"],cached=cached,assets=assets,prior=prior)


def worker(a4,t,d,c,n,f,precise,s,plan,plan_ref,args,output,b,files,result,inputs):
    raw=t.raw(args.request,MIB);need(t.digest(raw)["sha256"]==args.request_sha256,"actual worker request SHA")
    request=n.strict(raw);ref=dict(path=str(Path(args.request).resolve()),**t.digest(raw));result["request"]=ref;files.verify(ref,MIB,True)
    n.closed(request,"schema plan rows private_ref real_refs assets prior_work".split(),"exact commission request")
    need(request["schema"]=="m193c-sift-lightglue-commission-request-v1" and request["plan"]==plan_ref
         and request["rows"]==inputs["rows"] and request["private_ref"]==inputs["private_ref"]
         and request["real_refs"]==inputs["real_refs"] and request["assets"]==inputs["assets"],"bound requested export population/assets")
    n.closed(request["prior_work"],ALLOWANCE,"request carry")
    need(all((n.number(request["prior_work"][k]) if k.endswith("seconds") else n.integer(request["prior_work"][k]))
         and request["prior_work"][k]>=result["prior_work"][k] for k in ALLOWANCE),"typed at-least-plan request carry")
    def save(name,value):
        path=output/(name+".json");b.save(path,value);return files.bind(path,4*MIB,True)
    def control(name,passed,evidence):
        value=dict(id=name,passed=bool(passed),evidence=evidence);ref=save("control-"+name,value)
        result["controls"].append(dict(id=name,passed=bool(passed),record=ref));need(passed,"commission control: "+name)
    consumer=d.load(c.CONSUMER,plan["source_bindings"][n.relative(c.CONSUMER)],"m193c_export_consumer");v1=consumer.v1;np=v1.np
    result["extractor_runtime_before"]=c.runtime(consumer)
    need(result["extractor_runtime_before"]==c.strict(c.raw_read(c.CONTRACT,MIB))["reference_environment"],"frozen extractor runtime")
    need(not precise.FACTORY_ACTIVE and precise.OBSERVATIONS=={"private":[],"real":[]},"fresh scoped factories")
    result["active_phase"]="private-fixture"
    fixture=inputs["private"]["fixture"];result["counters"]["private_decodes"]+=1
    original=d.decode_blob(c,n,files,fixture,v1);need(original.shape==(288,384,3),"same private base fixture")
    native=np.repeat(np.repeat(original,8,axis=0),8,axis=1);del original
    rotated=np.ascontiguousarray(np.rot90(native,k=1))
    cr,rr=f.representation(np,native);cs,rs=f.representation(np,rotated);del native,rotated
    result["representation_attempts"].append(save("private-representation-before-extraction",dict(fixture=fixture,reference=rr,source=rs)))
    private_features=[];private_records=[]
    for i,(coarse,receipt,side) in enumerate(((cr,rr,"reference"),(cs,rs,"source"))):
        result["active_phase"]="private-extraction-"+side;result["counters"]["feature_extractions"]+=1
        witness=precise.new_witness("private",i)
        feature=precise.precise_call(v1,witness,lambda:v1.extract_features(coarse))
        lifted=f.lifted(np,v1,feature);actual=a4.feature_record(n,feature,lifted,receipt)
        private_features.append(lifted);private_records.append(actual)
    del cr,cs,coarse,feature
    whole=dict(schema=inputs["private"]["schema"],fixture=fixture,qualification=inputs["private"]["qualification"],
        reference=private_records[0],source=private_records[1])
    comparison=t.compare(n,"entire-private-AREA8-precise-features",whole,inputs["private"])
    control("private-cache-reproduction",comparison["equal"],dict(canonical_comparisons=[comparison],actual=save("private-reproduced-features",whole)))
    private_data=[]
    for i,side in enumerate(("reference","source")):
        result["active_phase"]="private-export-"+side
        cached=inputs["private"][side];expected={k:cached[k] for k in ("count","coarse_coordinates_q8","native_coordinates_q8","descriptors_sha256","keys_sha256")}
        size=cached["representation"]["coarse_shape"][:2][::-1]
        record,data,blobs=s.export(np,n,b,files,"private-"+side,private_features[i],expected,size,dict(cache=inputs["private_ref"],side=side,representation=cached["representation"]))
        result["exports"].append(save("private-"+side,record));private_data.append(data)
        if i==0:
            progress=result["serializer_fault_prefixes"]
            evidence=s.serializer_controls(np,n,private_features[i],expected,size,blobs,
                lambda rows:progress.append(save("export-fault-prefix-"+str(len(rows)),rows)))
            control("serializer-readback-observer-destroyers-restored",True,dict(**evidence,actual_fault_prefixes=progress))
    del private_features
    for row,cached,cache_ref in zip(inputs["rows"],inputs["cached"],inputs["real_refs"],strict=True):
        i=row["ordinal"];result["active_phase"]="real-feature-export-"+str(i)
        result["counters"]["real_decode_attempts"]+=1;rgb=d.decode_blob(c,n,files,row["tiff"],v1)
        try:
            need(rgb.shape==(4688,7032,3),"unchanged real native dimensions")
            coarse,receipt=f.representation(np,rgb)
        finally:del rgb
        result["counters"]["real_decodes_completed"]+=1;result["counters"]["feature_extractions"]+=1
        witness=precise.new_witness("real",i);receipt["precise_factory"]=witness
        result["representation_attempts"].append(save("real-representation-before-extraction-"+str(i),dict(tiff=row["tiff"],representation=receipt)))
        try:feature,receipt=precise.precise_call(v1,witness,lambda:f.extract_coarse(np,v1,coarse,receipt))
        finally:del coarse
        actual=dict(original_index=row["original_index"],tiff=row["tiff"],status="RETURNED",error=None,representation=receipt,
            count=len(feature.keys),coordinates_q8=feature.coordinates_q8.tolist(),
            descriptors_sha256=hashlib.sha256(feature.descriptors.astype("<i2").tobytes()).hexdigest(),
            keys_sha256=hashlib.sha256(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in feature.keys])).hexdigest())
        comparison=t.compare(n,"entire-real-AREA8-precise-feature-"+str(i),actual,cached)
        control("real-cache-reproduction-"+str(i),comparison["equal"],dict(canonical_comparisons=[comparison],actual=save("real-reproduced-"+str(i),actual),cache=cache_ref))
        expected=dict(count=actual["count"],coarse_coordinates_q8=receipt["coarse_coordinates_q8"],
            native_coordinates_q8=actual["coordinates_q8"],descriptors_sha256=actual["descriptors_sha256"],keys_sha256=actual["keys_sha256"])
        record,_,_=s.export(np,n,b,files,"real-"+str(i),feature,expected,[879,586],dict(cache=cache_ref,tiff=row["tiff"],representation=receipt))
        result["exports"].append(save("real-"+str(i),record));result["unvisited_real_exports"]=list(range(i+1,9));del feature
    result["extractor_runtime_after"]=c.runtime(consumer)
    need(result["extractor_runtime_after"]==result["extractor_runtime_before"],"stable extractor runtime")
    result["export_admission"]="ALL_ELEVEN_CACHED_FEATURES_REPRODUCED_AND_READ_BACK"
    result["active_phase"]="offline-runtime-load"
    model_witness=dict(blocked_imports=[],import_guard_restored=False,model_load_completed=False)
    result["model_loading"]=model_witness
    with s.import_guard(model_witness):
        begin=time.monotonic();cpu=time.process_time()
        import torch
        assets=inputs["assets"]
        matcher=t.checked_raw(files,assets["matcher"]);sift=t.checked_raw(files,assets["rootsift_reference"])
        checkpoint=files.verify(assets["checkpoint"],64*MIB,Path(assets["checkpoint"]["path"]).is_absolute())
        model,rootsift=s.load_model(torch,matcher,files.path(assets["matcher"],Path(assets["matcher"]["path"]).is_absolute()),
            sift,files.path(assets["rootsift_reference"],Path(assets["rootsift_reference"]["path"]).is_absolute()),checkpoint,model_witness)
        model_witness.update(model_load_completed=True,load_wall_seconds=time.monotonic()-begin,load_cpu_seconds=time.process_time()-cpu)
        result["runtime_before"]=save("runtime-before",s.runtime_snapshot(torch,np,n,files))
        result["active_phase"]="model-input-controls"
        evidence=[s.input_controls(torch,rootsift,data) for data in private_data]
        tensor_inputs={"image0":s.model_input(torch,rootsift,private_data[0]),"image1":s.model_input(torch,rootsift,private_data[1])}
        result["model_inputs"]=save("private-model-inputs",{k:s.tensor_witness(v) for k,v in tensor_inputs.items()})
        normalized=[]
        for i,side in enumerate(("image0","image1")):
            tensor=tensor_inputs[side]["descriptors"];data=tensor.detach().cpu().numpy().astype("<f4",copy=False).tobytes()
            ref=s.write_blob(n,b,files,output/(side+"-rootsift.f32"),data,cap=512*1024)
            need(t.checked_raw(files,ref,512*1024)==data,"actual normalized descriptor payload readback")
            normalized.append(dict(side=side,source_export=result["exports"][i],file=ref,dtype="<f4",shape=list(tensor.shape),
                tensor_sha256=s.sha(data),scope="actual copied RootSIFT input values before single forward"))
        result["normalized_private_descriptors"]=save("private-rootsift-payloads",dict(schema="m193c-private-rootsift-payloads-v1",sides=normalized))
        first=private_data[0]["descriptors"][0]
        wrong=torch.nn.functional.normalize(torch.from_numpy(first.copy()).to(dtype=torch.float32),p=2,dim=-1,eps=1e-6)
        correct=tensor_inputs["image0"]["descriptors"][0,0]
        difference=float((wrong-correct).abs().max())
        wrong_record=dict(schema="m193c-private-rootsift-wrong-normalization-v1",side="image0",row_index=0,
            rule="L2_ONLY_OMITS_L1_CLAMP_SQRT",eps=1e-6,componentwise_absolute_bound=2**-15,
            row_has_variation=len(set(int(x) for x in first))>1,wrong_float32_values=wrong.tolist(),
            actual_correct_payload=result["normalized_private_descriptors"],max_abs_difference_from_actual_correct_float32=difference,
            scope="fixed first private reference row; no row search, extra model input construction or forward; independent f64 audit remains required")
        result["normalization_destroyer"]=save("private-wrong-normalization",wrong_record)
        control("private-model-input-observer",wrong_record["row_has_variation"] and difference>2**-15,
            dict(scope="tensor construction only; no inference",sides=evidence,wrong_normalization=result["normalization_destroyer"]))
        result["active_phase"]="one-private-forward";b.check(True);result["counters"]["private_model_forwards"]+=1
        begin=time.monotonic();cpu=time.process_time()
        with torch.inference_mode():prediction=model(tensor_inputs)
        result["inference_timing"]=dict(wall_seconds=time.monotonic()-begin,cpu_seconds=time.process_time()-cpu)
        raw_output=s.output_record(torch,prediction,len(private_data[0]["keys"]),len(private_data[1]["keys"]))
        result["learned_output"]=save("private-learned-output",raw_output)
        after={k:s.tensor_witness(v) for k,v in tensor_inputs.items()}
        need(after==t.read(files,result["model_inputs"]),"model input tensors unchanged after actual forward")
        result["runtime_after"]=save("runtime-after",s.runtime_snapshot(torch,np,n,files))
        need(not torch.cuda.is_initialized(),"CPU-only no CUDA runtime initialization")
        del model,prediction,tensor_inputs
    result["active_phase"]="private-known-geometry"
    output_record=raw_output["output"];pairs=output_record["matches"];scores=output_record["scores"]
    matches,landmarks=s.assemble(v1,*private_data,pairs,scores)
    raw_landmarks=[dict(reference_q8=private_data[0]["native"][i].tolist(),source_q8=private_data[1]["native"][j].tolist()) for i,j in pairs]
    truths=dict(uncapped=s.truth_rows(raw_landmarks),capped=s.truth_rows(landmarks),
        population_relation="SAME_ROWS_NO_INDEPENDENT_CORROBORATION" if len(pairs)<=256 else "UNCAPPED_AND_HASH_CAPPED_POPULATIONS")
    need(truths["uncapped"]["count"]==len(pairs) and truths["capped"]["count"]==min(256,len(pairs)),"actual uncapped/capped truth populations")
    result["assembly"]=save("private-assembled-matches",dict(landmarks=landmarks,truth=truths,qualification=dict(s.QUALIFIER),
        association_rule="LightGlue fixed mutual learned confidence >0.1; original descriptor/coordinate hash order and cap256; alternating split"))
    def fit(values,mode="count"):
        result["counters"]["registrar_calls"]+=1;need(result["counters"]["registrar_calls"]<=5,"five saved-match registrar maximum")
        return s.registrar(v1,d,values,mode)
    baseline=fit(matches)
    control("private-learned-known-geometry",baseline["status"]=="RETURNED" and f.literal_corner_pass(baseline["transform"])
        and truths["uncapped"]["passes"] and truths["capped"]["passes"],
        dict(outcome=baseline,corner_errors=[] if baseline["transform"] is None else f.corner_errors(baseline["transform"]),assembly=result["assembly"]))
    shifted=dict(baseline["transform"]);shifted["tx"]+=2*(1<<32)
    control("native-two-pixel-map-destroyer",not f.literal_corner_pass(shifted),dict(transform=shifted,corner_errors=f.corner_errors(shifted),qualification=dict(s.QUALIFIER)))
    off=fit(matches,"off");placebo=fit(matches,"placebo")
    comparisons=[t.compare(n,"registrar-observer-"+name,d.signature(baseline),d.signature(value)) for name,value in (("off",off),("placebo",placebo))]
    control("saved-match-registrar-observer",all(x["equal"] for x in comparisons),dict(canonical_comparisons=comparisons,off=off,placebo=placebo))
    permutation=list(range(len(matches)))
    for split in (0,1):
        ids=list(range(split,len(matches),2))
        ranked=sorted(ids,key=lambda i:hashlib.sha256(b"M193C-LG-ASSOCIATION-FAULT\0"+matches[i].digest).digest())
        for at,other in zip(ids,ranked,strict=True):permutation[at]=other
    bad=[v1.Match(m.reference_x_q8,m.reference_y_q8,matches[permutation[i]].source_x_q8,matches[permutation[i]].source_y_q8,m.digest) for i,m in enumerate(matches)]
    changed=any((a.source_x_q8,a.source_y_q8)!=(z.source_x_q8,z.source_y_q8) for a,z in zip(matches,bad,strict=True))
    badrows=[dict(reference_q8=[m.reference_x_q8,m.reference_y_q8],source_q8=[m.source_x_q8,m.source_y_q8]) for m in bad]
    badtruth=s.truth_rows(badrows);badfit=fit(bad)
    control("within-split-association-destroyer",changed and not badtruth["passes"] and (badfit["status"]!="RETURNED" or not f.literal_corner_pass(badfit["transform"])),
        dict(permutation=permutation,actual_pairing_changed=changed,truth=badtruth,outcome=badfit,
            scope="active labelled saved-pairing fault; preserved original row order/digest/split, not rematched data"))
    restored=fit(matches);comparison=t.compare(n,"entire-restored-learned-registrar-outcome",restored,baseline)
    control("private-restored",comparison["equal"] and restored["status"]=="RETURNED" and f.literal_corner_pass(restored["transform"]),
        dict(canonical_comparisons=[comparison],outcome=restored))
    result["active_phase"]="complete"


CONTROL_IDS=("private-cache-reproduction","serializer-readback-observer-destroyers-restored",
    *(f"real-cache-reproduction-{i}" for i in range(9)),"private-model-input-observer","private-learned-known-geometry",
    "native-two-pixel-map-destroyer","saved-match-registrar-observer","within-split-association-destroyer","private-restored")


def main():
    parser=argparse.ArgumentParser()
    for name in ("plan","sha256","output"):parser.add_argument("--"+name,required=True)
    parser.add_argument("--worker",action="store_true");parser.add_argument("--request");parser.add_argument("--request-sha256")
    args=parser.parse_args();need(args.worker==(args.request is not None and args.request_sha256 is not None),"worker-only request")
    a4,t,d,c,n,f,precise,s,plan,output,plan_ref=setup(args)
    raw=t.raw(n.repo_path(plan["prior_work"]["path"]),MIB)
    need(t.digest(raw)=={k:plan["prior_work"][k] for k in ("sha256","bytes")},"actual prior carry")
    prior=n.strict(raw);b=t.budget_for(n,output,prior);files=n.Files(b);output.mkdir()
    result=dict(schema="m193c-sift-lightglue-commission-worker-v1" if args.worker else "m193c-sift-lightglue-commission-run-v1",
        implementation_version=VERSION,status="REFUSED",command=sys.orig_argv,plan=plan_ref,request=None,prior_work=prior,
        source_bindings=plan["source_bindings"],sources_unchanged=False,acquisition_receipt=plan["acquisition_receipt"],
        controls=[],exports=[],serializer_fault_prefixes=[],representation_attempts=[],unvisited_real_exports=list(range(9)),export_admission="NOT_ADMITTED",
        active_phase="authority",counters=dict(private_decodes=0,real_decode_attempts=0,real_decodes_completed=0,
            feature_extractions=0,private_model_forwards=0,real_model_forwards=0,registrar_calls=0),
        fixed_maximum_calls=dict(private_decodes=1,real_decodes=9,feature_extractions=11,private_model_forwards=1,real_model_forwards=0,registrar_calls=5,
            post_extraction_serializer_modes=3,private_model_input_constructions=8,wrong_normalization_rows=1),
        model_loading=None,model_inputs=None,normalized_private_descriptors=None,normalization_destroyer=None,learned_output=None,assembly=None,inference_timing=None,
        inference_observer_nonperturbation="UNTESTED_ONE_FORWARD",
        extractor_runtime_before=None,extractor_runtime_after=None,runtime_before=None,runtime_after=None,
        precise_factory_observations=precise.OBSERVATIONS,child=None,worker_result=None,qualification=dict(s.QUALIFIER),
        error=None,finalization_errors=[],work=None)
    try:
        files.verify(plan_ref,4*MIB,True);n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True)==Path(sys.executable).resolve(),"actual Python pin")
        inputs=authority(a4,t,d,n,plan,files);need(inputs["prior"]==prior,"same carry")
        if args.worker:worker(a4,t,d,c,n,f,precise,s,plan,plan_ref,args,output,b,files,result,inputs)
        else:
            request=dict(schema="m193c-sift-lightglue-commission-request-v1",plan=plan_ref,rows=inputs["rows"],
                private_ref=inputs["private_ref"],real_refs=inputs["real_refs"],assets=inputs["assets"],prior_work=b.work())
            b.save(output/"request.json",request);ref=files.bind(output/"request.json",MIB,True);result["request"]=ref
            command=t.replace(plan["commands"]["worker"],args.sha256,ref["sha256"])
            need(command[command.index("--output")+1]==str(output/"worker") and command[command.index("--request")+1]==str(output/"request.json"),"actual worker paths")
            process,api=n.load_process(plan,files);env,removed=process.clean_environment()
            removed += [key for key in env if key.upper().startswith("PYTHON")]
            env={k:v for k,v in env.items() if not k.upper().startswith("PYTHON")};env.update(dict.fromkeys(c.THREADS,"2"))
            env["CUDA_VISIBLE_DEVICES"]=""
            result["environment"]={key:env[key] for key in (*c.THREADS,"CUDA_VISIBLE_DEVICES")};result["removed_environment"]=sorted(set(removed));b.complete=False
            observed=process.run(command,env,ROOT,output/"worker.log",api=api,check=b.check,**b.limits());result["child"]=observed
            account=observed.get("job_accounting")
            if type(account) is dict and n.integer(account.get("total_cpu_100ns")):
                b.child_cpu=account["total_cpu_100ns"]/1e7;b.complete=observed.get("terminal_job_accounting") is True and account.get("active_processes")==0
            if (output/"worker/result.json").exists():result["worker_result"]=files.bind(output/"worker/result.json",4*MIB,True)
            n.successful_process(observed,command);child=t.read(files,result["worker_result"])
            need(child["schema"]=="m193c-sift-lightglue-commission-worker-v1" and child["implementation_version"]==VERSION and child["status"]==COMPLETE
                 and child["error"] is None and child["finalization_errors"]==[] and child["sources_unchanged"] is True
                 and child["command"]==command and child["request"]==ref and child["plan"]==plan_ref
                 and child["source_bindings"]==plan["source_bindings"],"actual complete commissioning worker")
            for key in ("controls","exports","serializer_fault_prefixes","representation_attempts","unvisited_real_exports","export_admission","active_phase","counters","model_loading","model_inputs","normalized_private_descriptors","normalization_destroyer",
                "learned_output","assembly","inference_timing","extractor_runtime_before","extractor_runtime_after","runtime_before","runtime_after","precise_factory_observations"):
                result[key]=child[key]
            # Parent rechecks the saved evidence without interpreting exports as image or model input.
            for ref in result["exports"]+[x["record"] for x in result["controls"]]+[result["runtime_before"],result["runtime_after"],result["model_inputs"],result["normalized_private_descriptors"],result["normalization_destroyer"],result["learned_output"],result["assembly"]]:
                value=t.read(files,ref)
                for witness in value.get("empty_runtime_files",[]):s.retain_empty_runtime(n,witness["path"],witness)
        result["status"]=COMPLETE
    except BaseException:result["error"]=traceback.format_exc()
    def final():
        files.recheck();s.check_empty_runtime(n);b.check(True);result["sources_unchanged"]=True
        need(not precise.FACTORY_ACTIVE,"factory restoration survives publication")
        if result["status"]==COMPLETE:
            need(b.complete and result["unvisited_real_exports"]==[] and len(result["exports"])==11
                 and result["export_admission"]=="ALL_ELEVEN_CACHED_FEATURES_REPRODUCED_AND_READ_BACK"
                 and tuple(x["id"] for x in result["controls"])==CONTROL_IDS and all(x["passed"] is True for x in result["controls"]),"complete exact export/control population")
            need(result["counters"]==dict(private_decodes=1,real_decode_attempts=9,real_decodes_completed=9,feature_extractions=11,
                 private_model_forwards=1,real_model_forwards=0,registrar_calls=5),"actual bounded call population")
            observations=result["precise_factory_observations"]
            need(len(observations["private"])==2 and len(observations["real"])==9
                 and all(x["restored"] is True and x["error"] is None and len(x["calls"])==1 for x in observations["private"]+observations["real"]),"eleven exact explicit-true factories")
            need(result["model_loading"]["import_guard_restored"] is True and result["model_loading"]["complete_parameter_coverage"] is True
                 and result["inference_observer_nonperturbation"]=="UNTESTED_ONE_FORWARD","honest one-forward/runtime scope")
    try:final()
    except BaseException:result["finalization_errors"].append(traceback.format_exc());result["status"]="REFUSED"
    result["work"]=dict(cpu_accounting_complete=b.complete,global_work=b.work(),new_extent_bytes=sum(b.extents.values()),snapshot_bytes=0,
        scope="worker sub-observation; parent Job owns complete actual CPU" if args.worker else "authoritative parent plus terminal Job",
        local_caps=dict(cpu_seconds=300,wall_seconds=480,file_bytes=8*MIB,metadata_bytes=8*MIB))
    return 0 if c.publish(n,output/"result.json",result,b.save,final,
        lambda:dict(status=result["status"],result=str(output/"result.json"),work_through_final_checks=b.work(),cpu_accounting_complete=b.complete,
                    error=result["error"],finalization_errors=result["finalization_errors"]),lambda:b.check(True)) else 1


if __name__=="__main__":raise SystemExit(main())
