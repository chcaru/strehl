"""Fixed 23 direct pairs after the observed reference65/source104 refusal.
Source-only until root pins the complete plan and exact commands. No graph solve.
"""
import time
START = time.monotonic()
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
import types

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "experiments/m193c-output-grid"
SELF = Path(__file__).resolve()
MIB = 1 << 20
CAPS = dict(cpu_seconds=300, wall_seconds=480, file_bytes=8*MIB, metadata_bytes=8*MIB)
ORIGINAL = (0,13,26,39,52,65,78,91,104)
PINS = {
 "coverage-sensor-white-run.py":"16f9e944673aa58b81727fabddadc7192a082cef149e950cd7dda24f217e51cf",
 "native-derivative-run.py":"94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a",
 "bounded-process.py":"47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b"}
CODE = "UNMEASURED_INPUT_REGISTRATION_INADEQUATE"
OLD_MESSAGE = CODE+": too few total mutual landmarks"
CONTROL_IDS=("geometry-0","geometry-2","observer-null","identity","complementary-refusal","association-destroyer-restored","blob-sha-refusal-restored")

def need(ok, message):
    if not ok: raise ValueError(message)

def digest(raw):
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def load(path, expected, name):
    need(path.stat().st_size <= 4*MIB, "bounded executable source")
    raw = path.read_bytes()
    need(digest(raw) == expected, "exact executed source bytes")
    module = types.ModuleType(name); module.__file__ = str(path); sys.modules[name] = module
    exec(compile(raw,str(path),"exec"),module.__dict__)
    return module

def replace(command, sha, request=None):
    return [sha if x=="ACTUAL_PLAN_SHA256" else request if x=="ACTUAL_REQUEST_SHA256" else x for x in command]

def setup(args):
    cp = HERE/"coverage-sensor-white-run.py"
    raw = cp.read_bytes(); need(digest(raw)["sha256"]==PINS[cp.name], "held utility pin")
    c = load(cp,digest(raw),"m193c_pair_coverage")
    raw = c.raw_read(args.plan,4*MIB); need(digest(raw)["sha256"]==args.sha256,"external plan SHA")
    plan = c.strict(raw)
    need(set(plan)==set("schema source_bindings coverage prior_work python_executable commands".split()) and
         plan["schema"]=="m193c-direct-pair-plan-v1", "closed pair plan")
    need(all(plan["source_bindings"][p.relative_to(ROOT).as_posix()]["sha256"]==pin for p,pin in c.PINS.items()),"frozen numerical/dependency pins")
    for p in (SELF,HERE/"direct-pair-preregister.md",*(HERE/x for x in PINS)):
        key=p.relative_to(ROOT).as_posix(); expected=plan["source_bindings"][key]
        need(digest(c.raw_read(p,4*MIB))==expected and (p.name not in PINS or expected["sha256"]==PINS[p.name]),"source closure")
    n=load(HERE/"native-derivative-run.py",plan["source_bindings"]["experiments/m193c-output-grid/native-derivative-run.py"],"m193c_pair_util")
    output=Path(args.output).resolve()
    need(Path.cwd().resolve()==ROOT and output.is_relative_to(HERE) and not output.exists(),"fresh owned output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions)=={"faulthandler","pycache_prefix"} and
         sys._xoptions["faulthandler"] is True and not Path(sys._xoptions["pycache_prefix"]).exists() and
         Path(sys._xoptions["pycache_prefix"]).resolve().is_relative_to(output.parent if args.worker else output),"fresh exact cache/options")
    need(set(plan["commands"])=={"parent","worker"} and
         replace(plan["commands"]["worker" if args.worker else "parent"],args.sha256,args.request_sha256)==sys.orig_argv,"exact original argv")
    return c,n,plan,output,dict(path=str(Path(args.plan).resolve()),**digest(raw))

def budget_for(n,output,prior):
    class Budget(n.Budget):
        complete=True
        def check(self,force=False):
            super().check(force)
            need(all(self.work()[k]-self.prior[k]<=v for k,v in CAPS.items()),"direct-pair local cap")
        def limits(self,metadata_cap=MIB):
            result=super().limits(metadata_cap); work=self.work()
            for key in ("cpu_seconds","wall_seconds"):
                result[key]=min(result[key],CAPS[key]-(work[key]-self.prior[key]))
            result["log_bytes"]=min(result["log_bytes"],CAPS["file_bytes"]-(work["file_bytes"]-self.prior["file_bytes"]))
            need(all(x>0 for x in result.values()),"remaining pair child budget")
            return result
        def save(self,path,value,cap=4*MIB):
            raw=n.json_bytes(value); self.check(True)
            need(sum(self.extents.values())+len(raw)<=8*MIB,"pair metadata preallocation")
            super().save(path,value,cap)
    return Budget(output,prior,START,0.0)

def read(files,ref):
    return files.read(ref,absolute=Path(ref["path"]).is_absolute())

def same(files,a,b):
    return files.path(a,Path(a["path"]).is_absolute())==files.path(b,Path(b["path"]).is_absolute()) and all(a[k]==b[k] for k in ("sha256","bytes"))

def authority(c,n,plan,files):
    refs=plan["coverage"]; n.closed(refs,"result release outer console exit audit".split(),"coverage evidence")
    for ref in refs.values(): files.verify(ref,4*MIB,Path(ref["path"]).is_absolute())
    previous, result, outer, audit=(read(files,refs[k]) for k in ("release","result","outer","audit"))
    need(previous["schema"]=="m193c-sensor-white-coverage-release-v1" and
         result["schema"]=="m193c-sensor-white-coverage-run-v1" and result["status"]=="REFUSED" and
         result["finalization_errors"]==[] and same(files,result["execution_release"],refs["release"]),"actual coverage refusal")
    need(type(outer["exit_code"]) is int and outer["exit_code"]==1 and outer["admissible_parent_exit"] is False and
         result["command"]==outer["command"] and outer["release_sha256"]==refs["release"]["sha256"],"actual coverage parent/outer")
    need(c.checked_raw(n,files,refs["exit"],64).strip()==b"1","actual coverage exit")
    final=n.strict(c.checked_raw(n,files,refs["console"],4*MIB).splitlines()[-1]); accounting=final["work_through_final_checks"]
    need(final["status"]=="REFUSED" and Path(final["result"]).resolve()==files.path(refs["result"]) and
         final["finalization_errors"]==[] and accounting["cpu_accounting_complete"] is True,"actual final coverage accounting")
    need(audit["schema"]=="m193c-saved-sensor-white-coverage-audit-v1" and audit["status"]=="PASS_SAVED_COVERAGE_OUTCOME_AUDIT" and
         audit["subject_complete"] is False and audit["worker_status"]=="REGISTRAR_REFUSED","independent refusal audit")
    for k in ("result","release","outer","console","exit"):
        need(same(files,audit["external"][k],refs[k]),"audit actual association")
    need(result["sources_before"]==result["sources_after"]==previous["source_bindings"] and
         result["inputs_before"]==result["inputs_after"]==previous["inputs"] and
         all(plan["source_bindings"].get(k)==v for k,v in previous["source_bindings"].items()),"preserved exercised source closure")
    prior=read(files,plan["prior_work"])
    need(audit["actual_final_accounting"]==accounting,"audit actual final accounting")
    base=dict(accounting["work_observed_or_lower_bound"],wall_seconds=audit["next_wall_seconds"])
    addition=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
    need(all(Decimal(str(prior[k]))==Decimal(str(base[k]))+addition[k] for k in addition) and
         Decimal(audit["next_wall_seconds"])==Decimal(str(result["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"])),
         "exact root carry plus nonrefundable preparation; no snapshot refund")
    worker=read(files,result["worker_result"]); refused=worker["first_refusal"]
    need(worker["status"]=="REGISTRAR_REFUSED" and worker["finalization_errors"]==[] and
         [r["id"] for r in worker["controls"]]==list(c.CONTROL_IDS) and all(r["passed"] is True for r in worker["controls"]),"eight actual controls")
    need(refused["failure_phase"]=="register_to_reference" and refused["message"]==OLD_MESSAGE and
         refused["ordered_groups_complete"] is True and refused["constructor_index"]==1 and
         refused["ordered_groups"][0]["original_indices"]==[65] and refused["failing_input"]["original_indices"]==[104] and
         len(refused["unvisited_inputs"])==7,"literal old ordered pair and unvisited prefix")
    rows=result["admitted_inputs"]
    need(len(rows)==9 and [(r["ordinal"],r["original_index"]) for r in rows]==list(enumerate(ORIGINAL)),"nine actual input admissions")
    need(len(worker["fixtures"])==5,"five existing small fixture refs")
    return rows,worker["fixtures"],refused,prior

def pair_plan(rows):
    edges={(i,i+d) for d in (1,2,4) for i in range(9-d)}|{tuple(sorted((5,j))) for j in range(9) if j!=5}
    need(len(edges)==23 and len(edges)<=25 and (5,8) in edges,"fixed23 pair union")
    return [dict(id=f"pair-{i}-{j}",reference=5 if 5 in (i,j) else i,source=(j if i==5 else i) if 5 in (i,j) else j,
                 local_span=j-i,star=5 in (i,j),reference_original=ORIGINAL[5 if 5 in (i,j) else i],
                 source_original=ORIGINAL[(j if i==5 else i) if 5 in (i,j) else j]) for i,j in sorted(edges)]

def decode_blob(c,n,files,ref,v1):
    p=files.path(ref,Path(ref["path"]).is_absolute())
    need(p.is_relative_to(HERE) and p.suffix==".tiff" and 0<ref["bytes"]<=197798267,"bounded owned TIFF")
    before=n.metadata(p)
    with p.open("rb") as stream:
        opened=os.fstat(stream.fileno()); need((opened.st_dev,opened.st_ino)==(before["device"],before["file_id"]),"opened TIFF identity")
        blob=stream.read(ref["bytes"]+1)
    need(n.metadata(p)==before and digest(blob)=={k:ref[k] for k in ("sha256","bytes")},"authenticated same TIFF blob")
    files.retained[str(p)]={k:ref[k] for k in ("sha256","bytes")}; files.budget.check()
    return v1.decode_input_tiff(blob)

def observe_pair(v1,ref,src,mode="count"):
    original=v1.match_features; captured=[]
    def observed(a,b):
        rows=original(a,b)
        if mode=="count": captured.extend(rows)
        return rows
    result=dict(status="REGISTRATION_REFUSED",transform=None,metrics=None,guard=None,error=None,landmarks=[],heldout_bbox_q8=None)
    try:
        if mode!="off": v1.match_features=observed
        try:
            transform,metrics,guard=v1.register_to_reference(ref,src)
            result.update(status="RETURNED",transform=transform.as_dict(),metrics=metrics,guard=guard)
        except v1.ContractError as exc:
            if exc.code!=CODE: raise
            result["error"]=dict(type=type(exc).__name__,code=exc.code,message=str(exc),traceback=traceback.format_exc())
    finally: v1.match_features=original
    held=[]
    for i,m in enumerate(captured):
        residual=None if result["transform"] is None else v1.residual_squared_q40(m,transform)
        accepted=None if residual is None else residual<=v1.inlier_threshold_squared()
        row=dict(reference_q8=[m.reference_x_q8,m.reference_y_q8],source_q8=[m.source_x_q8,m.source_y_q8],
                 split="holdout" if i%2 else "calibration",digest=m.digest.hex(),inlier=accepted)
        result["landmarks"].append(row)
        if i%2 and accepted: held.append(row)
    if held:
        result["heldout_bbox_q8"]={side:[min(r[side][0] for r in held),min(r[side][1] for r in held),
                                             max(r[side][0] for r in held),max(r[side][1] for r in held)] for side in ("reference_q8","source_q8")}
    return result

def signature(value):
    error=value["error"]
    return {k:value[k] for k in ("status","transform","metrics","guard")}|dict(error=None if error is None else {k:error[k] for k in ("type","code","message")})

def controls(c,n,files,v1,fixtures,rows,save):
    def record(name,ok,evidence):
        row=dict(id=name,passed=bool(ok),evidence=evidence); rows.append(row)
        save(name,row); need(ok,"pair control: "+name)
    known=c.strict(c.raw_read(c.FIXTURES,MIB))["synthetic_overlap"]["sources"]
    feats=[v1.extract_features(decode_blob(c,n,files,f,v1)) for f in fixtures]
    by={f["sha256"]:i for i,f in enumerate(fixtures)}; reference=by[known[0]["source_sha256"]]
    results=[]
    def accepts(got,expected):
        return got["transform"]==expected["source_to_reference_q32"] and dict(got["metrics"] or {},reference=False)==expected["registration"] and got["guard"]==expected["valid_center_guard_q8"]
    for expected in known[1:]:
        index=by[expected["source_sha256"]]
        got=observe_pair(v1,feats[reference],feats[index]); results.append(got)
        record("geometry-"+str(index),accepts(got,expected),signature(got))
    first=by[known[1]["source_sha256"]]
    off=observe_pair(v1,feats[reference],feats[first],"off"); placebo=observe_pair(v1,feats[reference],feats[first],"placebo")
    hashes={name:hashlib.sha256(n.json_bytes(signature(value))).hexdigest() for name,value in (("off",off),("count",results[0]),("placebo",placebo))}
    record("observer-null",len(set(hashes.values()))==1 and signature(off)==signature(placebo)==signature(results[0]) and len(results[0]["landmarks"])==256,
           dict(off=signature(off),count=signature(results[0]),placebo=signature(placebo),canonical_signature_sha256=hashes))
    identity=observe_pair(v1,feats[3],feats[3]); bad=observe_pair(v1,feats[4],feats[3])
    record("identity",identity["transform"]==v1.IDENTITY_Q32.as_dict() and identity["metrics"]["heldout_rms_reference_px"]=="0.000000000",signature(identity))
    record("complementary-refusal",bad["status"]=="REGISTRATION_REFUSED" and bad["error"]["code"]==CODE,signature(bad))
    record("association-destroyer-restored",not accepts(results[0],known[2]) and not accepts(results[1],known[1]) and accepts(results[0],known[1]),
           dict(first=results[0]["transform"],wrong=known[2]["source_to_reference_q32"],restored=known[1]["source_to_reference_q32"]))
    forged=dict(fixtures[0],sha256="0"*64); error=None; calls=[]; original_decoder=v1.decode_input_tiff
    def counted(blob):
        calls.append(1); return original_decoder(blob)
    try:
        v1.decode_input_tiff=counted
        try: decode_blob(c,n,files,forged,v1)
        except ValueError as exc: error=str(exc)
        refused_calls=len(calls); restored=decode_blob(c,n,files,fixtures[0],v1).shape
    finally: v1.decode_input_tiff=original_decoder
    record("blob-sha-refusal-restored",error=="authenticated same TIFF blob" and refused_calls==0 and len(calls)==1 and restored==(288,384,3),
           dict(exception=error,refused_decoder_calls=refused_calls,restored_decoder_calls=len(calls)-refused_calls))
    need(tuple(r["id"] for r in rows)==CONTROL_IDS,"seven complete pair controls")
    return rows

def graph(pairs):
    edges=[(p["pair"]["reference"],p["pair"]["source"]) for p in pairs if p["outcome"]["status"]=="RETURNED"]
    def reachable(start,excluded=None):
        seen={start}; pending=[start]
        while pending:
            at=pending.pop()
            for edge in edges:
                if edge==excluded or at not in edge: continue
                to=edge[1] if edge[0]==at else edge[0]
                if to not in seen: seen.add(to); pending.append(to)
        return sorted(seen)
    bridges=[e for e in edges if e[1] not in reachable(e[0],e)]
    return dict(anchor_local=4,anchor_original=52,reference_local=5,reference_original=65,
                edges=edges,bridges=bridges,nodes=[dict(local=i,original=ORIGINAL[i],component=reachable(i),
                anchor_connected=4 in reachable(i),degree=sum(i in e for e in edges),
                cycle_participation=any(i in e and e not in bridges for e in edges)) for i in range(9)],
                scope="Direct support only; no placement solve or overlap/quality admission")

def main():
    p=argparse.ArgumentParser(); p.add_argument("--plan",required=True); p.add_argument("--sha256",required=True); p.add_argument("--output",required=True)
    p.add_argument("--worker",action="store_true"); p.add_argument("--request"); p.add_argument("--request-sha256"); args=p.parse_args()
    need(args.worker==(args.request is not None and args.request_sha256 is not None),"worker-only request")
    c,n,plan,output,plan_ref=setup(args)
    raw_prior=c.raw_read(n.repo_path(plan["prior_work"]["path"]),MIB)
    need(digest(raw_prior)=={k:plan["prior_work"][k] for k in ("sha256","bytes")},"actual prior carry")
    prior=n.strict(raw_prior)
    b=budget_for(n,output,prior); files=n.Files(b); output.mkdir()
    result=dict(schema="m193c-direct-pair-worker-v1" if args.worker else "m193c-direct-pair-run-v1",status="REFUSED",command=sys.orig_argv,
                plan=plan_ref,request=None,prior_work=prior,source_bindings=plan["source_bindings"],sources_unchanged=False,
                controls=[],features=[],pairs=[],unvisited=list(range(23)),graph=None,child=None,worker_result=None,
                runtime_before=None,runtime_after=None,error=None,finalization_errors=[],work=None)
    try:
        files.verify(plan_ref,4*MIB,True)
        n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True)==Path(sys.executable).resolve(),"actual Python pin")
        rows,fixtures,old,actual_prior=authority(c,n,plan,files); need(actual_prior==prior,"same prior carry")
        schedule=pair_plan(rows)
        if not args.worker:
            b.save(output/"pair-plan.json",dict(rows=rows,pairs=schedule,old_refusal=old))
            request=dict(schema="m193c-direct-pair-request-v1",plan=plan_ref,pairs=schedule,rows=rows,fixtures=fixtures,prior_work=b.work())
            b.save(output/"request.json",request); ref=files.bind(output/"request.json",MIB,True); result["request"]=ref
            command=replace(plan["commands"]["worker"],args.sha256,ref["sha256"])
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
            n.successful_process(observed,command); child=read(files,result["worker_result"])
            need(child["status"]=="COMPLETE_DIRECT_PAIR_SUPPORT_ONLY" and child["error"] is None and child["finalization_errors"]==[] and
                 child["command"]==command and child["request"]==ref and child["plan"]==plan_ref and len(child["pairs"])==23 and
                 child["unvisited"]==[] and tuple(x["id"] for x in child["controls"])==CONTROL_IDS and
                 all(x["passed"] is True for x in child["controls"]),"actual complete pair worker")
            result["unvisited"]=[]; result["graph"]=child["graph"]
        else:
            raw=c.raw_read(args.request,MIB); need(digest(raw)["sha256"]==args.request_sha256,"actual worker request")
            request=n.strict(raw); result["request"]=dict(path=str(Path(args.request).resolve()),**digest(raw))
            files.verify(result["request"],MIB,True)
            need(request["schema"]=="m193c-direct-pair-request-v1" and request["plan"]==plan_ref and request["rows"]==rows and
                 request["pairs"]==schedule and request["fixtures"]==fixtures and
                 all(request["prior_work"][k]>=prior[k] for k in prior),"exact requested population and carried setup work")
            # Metadata plan exists before any private or real TIFF bytes are opened.
            b.save(output/"pair-plan.json",dict(rows=rows,pairs=schedule))
            consumer=load(c.CONSUMER,plan["source_bindings"][c.CONSUMER.relative_to(ROOT).as_posix()],"m193c_pair_consumer")
            v1=consumer.v1; result["runtime_before"]=c.runtime(consumer)
            need(result["runtime_before"]==c.strict(c.raw_read(c.CONTRACT,MIB))["reference_environment"],"frozen runtime")
            controls(c,n,files,v1,fixtures,result["controls"],lambda name,row:b.save(output/("control-"+name+".json"),row))
            b.save(output/"controls.json",result["controls"])
            features=[]
            for row in rows:
                record=dict(original_index=row["original_index"],tiff=row["tiff"],status="FEATURE_UNAVAILABLE",error=None)
                try:
                    rgb=decode_blob(c,n,files,row["tiff"],v1); need(rgb.shape==(4688,7032,3),"admitted native shape")
                    try: feature=v1.extract_features(rgb)
                    finally: del rgb
                    record.update(status="RETURNED",count=len(feature.keys),coordinates_q8=feature.coordinates_q8.tolist(),
                                  descriptors_sha256=hashlib.sha256(feature.descriptors.astype("<i2").tobytes()).hexdigest(),
                                  keys_sha256=hashlib.sha256(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in feature.keys])).hexdigest())
                except v1.ContractError as exc:
                    if exc.code!=CODE: raise
                    feature=None; record["error"]=dict(code=exc.code,message=str(exc),traceback=traceback.format_exc())
                features.append(feature); result["features"].append(record); b.save(output/f"feature-{row['ordinal']}.json",record)
            for ordinal,pair in enumerate(schedule):
                a,z=features[pair["reference"]],features[pair["source"]]
                outcome=observe_pair(v1,a,z) if a is not None and z is not None else dict(status="FEATURE_UNAVAILABLE",unavailable=[i for i in (pair["reference"],pair["source"]) if features[i] is None])
                record=dict(pair=pair,outcome=outcome); result["pairs"].append(record); result["unvisited"]=list(range(ordinal+1,23))
                b.save(output/(pair["id"]+".json"),record)
            result["graph"]=graph(result["pairs"])
            result["historical_pair_reproduced"]=any(p["pair"]["reference"]==5 and p["pair"]["source"]==8 and (p["outcome"].get("error") or {}).get("message")==OLD_MESSAGE for p in result["pairs"])
            result["graph"]["interpretation_eligible"]=result["historical_pair_reproduced"]
            result["graph"]["eligibility_reason"]="historical ordered refusal reproduced" if result["historical_pair_reproduced"] else "STOP: resolve changed historical pair outcome before topology interpretation"
            result["runtime_after"]=c.runtime(consumer); need(result["runtime_after"]==result["runtime_before"],"stable runtime")
        result["status"]="COMPLETE_DIRECT_PAIR_SUPPORT_ONLY"
    except BaseException: result["error"]=traceback.format_exc()
    def final():
        files.recheck(); b.check(True); result["sources_unchanged"]=True
        need(result["status"]!="COMPLETE_DIRECT_PAIR_SUPPORT_ONLY" or b.complete,"complete terminal CPU required")
    try: final()
    except BaseException: result["finalization_errors"].append(traceback.format_exc()); result["status"]="REFUSED"
    result["work"]=dict(cpu_accounting_complete=b.complete,global_work=b.work(),new_extent_bytes=sum(b.extents.values()),snapshot_bytes=0,
                       scope="worker sub-observation; parent Job deducts setup work" if args.worker else "authoritative parent plus terminal Job")
    return 0 if c.publish(n,output/"result.json",result,b.save,final,
        lambda:dict(status=result["status"],result=str(output/"result.json"),work_through_final_checks=b.work(),cpu_accounting_complete=b.complete,
                    error=result["error"],finalization_errors=result["finalization_errors"]),lambda:b.check(True)) else 1

if __name__=="__main__": raise SystemExit(main())
