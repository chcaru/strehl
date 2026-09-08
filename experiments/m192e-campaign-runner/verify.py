"""M192e retained-artifact integration checker; never starts recorded commands.

Reuses the unchanged M192d independent TIFF/monitor readers, not their controls
or main. This authored checker is not a replacement for independent review.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import durable as d

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
READER=ROOT/"experiments/m192d-production-rehearsal/independent-verify.py"
BINDINGS=ROOT/"experiments/m192b-verifier/verify.py"
PROTOCOL=ROOT/"experiments/M192-m12-certify/protocol.json"
SCHEDULE=("off","on","placebo")
CONTROL_IDS=("actual-metadata-roundtrip","partial-stage-recovery",
    "trace-overflow-terminal-refusal","before-replace-recovery",
    "same-instance-restored-placebo","resealed-campaign-identity",
    "resealed-run-identity","resealed-generation-chain")

def read_ref(ref,cap=d.RECORD_BYTES):
    return d.read_ref(ref,cap)

def same_ref(a,b):
    return (d.lexical_path(a["path"])==d.lexical_path(b["path"])
            and a["bytes"]==b["bytes"] and a["sha256"].upper()==b["sha256"].upper())

def at(ref,path):
    d.need(d.lexical_path(ref["path"])==d.lexical_path(path),"literal artifact path")


def job_cpu(value):
    keys=("total_user_100ns","total_kernel_100ns","total_cpu_100ns","active_processes")
    d.need(type(value) is dict and all(type(value.get(k)) is int and value[k]>=0 for k in keys),
        "typed nonnegative Job counters")
    d.need(value["total_cpu_100ns"]==value["total_user_100ns"]+value["total_kernel_100ns"],
        "Job total equals user plus kernel")
    return value["total_cpu_100ns"]/1e7

def job_counter_controls(actual):
    original=d.sha(d.encode(actual));positive=job_cpu(actual);rows=[]
    for name,field,value in (("wrong-total","total_cpu_100ns",actual["total_cpu_100ns"]+1),
        ("negative-user","total_user_100ns",-1),("bool-active","active_processes",False)):
        bad=copy.deepcopy(actual);bad[field]=value;error=None
        try:job_cpu(bad)
        except ValueError as exc:error=str(exc)
        d.need(error is not None,"powered Job counter rejection")
        rows.append(dict(id=name,changed=bad,expected_error=error))
    d.need(d.sha(d.encode(actual))==original and job_cpu(actual)==positive,"unchanged restored Job counter witness")
    return dict(positive_cpu_seconds=positive,original_sha256=original,rows=rows,restored=True)

def load_bound(path,name,sources):
    ref=sources[str(path.resolve())];d.check_ref(ref)
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    d.check_ref(ref)
    return module

def invocation_check(value,plan,plan_ref,out,protocol,domain,index,mode,input_ref):
    rid="native-n33-w8-"+mode
    d.need(value["schema"]=="m192e-invocation-v1" and
           value["campaign_id"]==plan["campaign_id"] and value["run_id"]==rid and
           type(value["sequence"]) is int and value["sequence"]==index and value["mode"]==mode
           and value["sampler_mode"]=="on" and value["limit"]==33 and value["workers"]==8,
           "invocation literal population")
    expected=[plan["binary"]["path"],"stack",protocol["inputs"]["33"],"--limit","33",
        "--out",str(out/"work"/"outputs"/(rid+".tiff")),*protocol["configuration"]["arguments_after_output"]]
    d.need(value["argv"]==expected,"complete invocation argv")
    active=dict(STREHL_PYRAMID_WORKERS="8",STREHL_WARPMAP=str(out/"work"/"sidecars"/"n33.warpmap.txt"),
        STREHL_CACHE_DIR=str(out/"work"/"cache"/"native"/"n33"),
        TEMP=str(out/"work"/"monitor"/rid/"temp"),TMP=str(out/"work"/"monitor"/rid/"temp"))
    removed=value["cleared_present_variables"]
    d.need(type(removed) is list and removed==sorted(set(removed)) and
        all(type(k) is str and k.upper().startswith(("STREHL_","RAYON_","OMP_","OPENBLAS_","MKL_","NUMEXPR_"))
            for k in removed),"declared cleared variables")
    d.need(value["environment_domain"]==sorted(domain) and
           set(value["environment"])==set(domain)|set(active)|set(removed) and
           all(value["environment"][k]==active.get(k) for k in value["environment"]),
           "complete environment values/domain")
    d.need(value["actual_monitor_folder"]==str(out/"work"/"monitor"/rid),"actual monitor folder")
    d.need(same_ref(value["source_plan"],plan_ref) and same_ref(value["input_binding"],input_ref)
           and same_ref(value["binary"],plan["binary"]),"invocation evidence association")
    at(value["sidecar"],out/"work"/"sidecars"/"n33.warpmap.txt")
    d.need(value["sidecar"]["bytes"]==plan["sidecar"]["bytes"] and
           value["sidecar"]["sha256"].upper()==plan["sidecar"]["sha256"].upper(),"actual sidecar copy")

def recovered(directory,campaign,rid,size):
    identity=dict(campaign_id=campaign,run_id=rid)
    rows=[];errors=[]
    for i in range(2):
        path=directory/f"slot-{i}.json"
        try:
            v,ref=d.json_binding(path,size)
            d.need(ref["bytes"]==size and set(v)=={"schema","identity","sequence","status",
                "previous_sha256","payload_sha256","payload"} and v["schema"]=="m192e-checkpoint-v1"
                and v["identity"]==identity and v["status"]=="INCOMPLETE","checkpoint envelope")
            q=v["sequence"];previous=v["previous_sha256"]
            d.need(type(q) is int and q>=-1 and type(previous) is str and len(previous)==64
                and all(c in "0123456789ABCDEF" for c in previous),"checkpoint sequence/digest")
            d.need(v["payload_sha256"]==d.sha(d.encode(v["payload"])),"checkpoint payload identity")
            d.need(q not in (-1,0) or previous=="0"*64,"initial chain origin")
            d.need(q!=-1 or v["payload"] is None,"unwritten checkpoint payload")
            rows.append((q,v,ref))
        except Exception as exc:errors.append(dict(path=str(path),error=repr(exc)))
    d.need(rows,"readable checkpoint generation")
    rows.sort(key=lambda row:row[0])
    if len(rows)==2 and rows[0][0]>=0:
        d.need(rows[1][0]==rows[0][0]+1 and rows[1][1]["previous_sha256"]==rows[0][2]["sha256"],
               "successive linked generations")
    return rows,errors

def checkpoint_check(record,adapter,raw,out,campaign,mode):
    rid="native-n33-w8-"+mode
    d.need(adapter["mode"]==mode and adapter["checkpoint_every_observations"]==100
           and adapter["restored"] is True and adapter["latest_telemetry"] is None,"adapter restoration")
    expected=0 if mode=="off" else raw["sample_count"]//100
    d.need(adapter["calls"]==(0 if mode=="off" else raw["sample_count"])
           and adapter["telemetry_calls"]==(0 if mode=="off" else (raw["sample_count"]+9)//10)
           and adapter["checkpoint_count"]==expected and record["checkpoint_count"]==expected,
           "actual callback/checkpoint census")
    d.need(mode=="off" or expected>0,"production checkpoint path exercised")
    d.need(record["checkpoint_exercised"] is True,"retained exercised disposition")
    rows,errors=recovered(out/"records"/rid/"trace",campaign,rid,d.SLOT_BYTES)
    receipt=record["trace_recovery"]
    d.need(not errors and receipt["errors"]==[] and receipt["status"]=="RECOVERABLE_INCOMPLETE"
           and receipt["may_resume"] is False and receipt["may_certify"] is False,
           "recovery is not completion authority")
    d.need(receipt["sequence"]==rows[-1][0]==expected-1 and
           same_ref(receipt["latest"],rows[-1][2]) and len(receipt["generations"])==len(rows)
           and all(same_ref(x,y[2]) for x,y in zip(receipt["generations"],rows)),"bound generation selection")
    for seq,value,ref in rows:
        if seq<0:continue
        payload=value["payload"];trace=payload["trace"]
        count=(seq+1)*100
        d.need(set(payload)=={"trace","latest_telemetry","telemetry_calls","last_observation","retained_scope",
            "placebo_label"} and payload["placebo_label"] is (mode=="placebo"),"checkpoint payload fields")
        observations=trace["observations"]
        d.need(len(observations)+trace["dropped"]["observations"]==count and
            len(observations)<=1000 and observations[-1]["poll"]==count-1 and
            observations[-1]["observed_ns"]==payload["last_observation"] and
            trace["enabled"] is True and trace["placebo"] is False,"actual persisted sampler prefix")
        d.need(payload["telemetry_calls"]==(count+9)//10 and
            payload["latest_telemetry"]["end_ns"]<=payload["last_observation"],"latest completed telemetry")
        final_obs={x["poll"]:x for x in raw["trace"]["observations"]}
        for observation in observations:
            if observation["poll"] in final_obs:
                d.need(observation==final_obs[observation["poll"]],"overlapping persisted/final observation identity")
        d.need(len(trace["events"])<=4096 and len(trace["incidents"])<=32
            and all(n>=0 for n in trace["dropped"].values()),"bounded prefix tails")
    return dict(checkpoint_count=expected,last_sequence=rows[-1][0],
                recovered_status=receipt["status"],full_history_retained=False)

def terminal_strings(stack,destination):
    return [f"frames          : 33 from {stack}","coverage mode   : scale -- as asked, --cover",
        "alignment       : ON (sidecar-override)","33 placed / 0 refused","folded          : 33 / 33 frames",
        "8 execution threads","memory plan     : 4 canonical chunks, 1 reusable frame worker, 1 retained + 1 scratch accumulator",
        "camera RGB -> LINEAR sRGB","Malvar-He-Cutler demosaic","wrote           : "+str(destination),"total           :"]


def final_tail(plan_ref,out,role,command,log_ref):
    """Canonical success alone is insufficient; bind a later tail and log line."""
    raw,_=d.bytes_binding(log_ref["path"],d.MIB,expected=log_ref)
    adverts=[]
    for line in raw.splitlines():
        try:value=d.parse_json(line)
        except (ValueError,UnicodeError):continue
        if type(value) is dict and value.get("schema")=="m192e-terminal-advertisement-v1" and value.get("role")==role:
            adverts.append(value)
    d.need(len(adverts)==1,"one actual terminal advertisement")
    advert=adverts[0]
    d.need(advert["status"]=="COMPLETE_REHEARSAL_EVIDENCE_ONLY" and
        advert["complete_cpu_accounting"] is False and advert["outer_exit_required"] is True and
        same_ref(advert["plan"],plan_ref),"advertised completion remains conditional")
    at(advert["canonical"],out/role/"result.json");at(advert["tail"],out/role/"terminal-tail.json")
    canonical=read_ref(advert["canonical"],64*1024);tail=read_ref(advert["tail"],8192)
    d.need(tail["schema"]=="m192e-publication-tail-v1" and tail["role"]==role and
        tail["status"]=="COMPLETE_REHEARSAL_EVIDENCE_ONLY" and tail["phase"]=="AFTER_CANONICAL_PUBLICATION" and
        same_ref(tail["plan"],plan_ref) and same_ref(tail["canonical"],advert["canonical"]) and
        tail["complete_cpu_accounting"] is False and tail["outer_exit_required"] is True and
        type(tail["process_id"]) is int and tail["process_id"]>0 and tail["process_id"]==advert["process_id"],
        "bound post-publication tail")
    d.need(canonical["status"]=="COMPLETE_REHEARSAL_EVIDENCE_ONLY" and canonical["command"]==command and
        canonical["terminal_tail_path"]==str(out/role/"terminal-tail.json") and
        canonical["complete_cpu_accounting"] is False and canonical["outer_exit_required"] is True,
        "exact terminal command and conditional accounting")
    for sample in (tail["sample"],advert["sample_after_tail"]):
        d.need(all(type(sample[k]) in (int,float) and sample[k]>=0 for k in
            ("process_cpu_seconds","latest_owned_job_cpu_seconds","combined_cpu_seconds","wall_seconds")) and
            sample["combined_cpu_seconds"]==sample["process_cpu_seconds"]+sample["latest_owned_job_cpu_seconds"] and
            sample["accounting_error"] is None,"typed publication accounting sample")
    d.need(all(advert["sample_after_tail"][k]>=tail["sample"][k] for k in
        ("process_cpu_seconds","latest_owned_job_cpu_seconds","combined_cpu_seconds","wall_seconds")) and
        0<=tail["publication"]["cpu_seconds"]<=2 and 0<=tail["publication"]["wall_seconds"]<=3 and
        advert["sample_after_tail"]["wall_seconds"]<=(240 if role=="parent" else 210),
        "bounded ordered publication samples")
    return canonical,tail,advert

def verify_outer(plan_path,plan_sha256,outer_path,outer_sha256):
    plan,plan_ref=d.json_binding(plan_path,expected_sha256=plan_sha256)
    outer,outer_ref=d.json_binding(outer_path,8192,expected_sha256=outer_sha256)
    out=d.lexical_path(plan["output_directory"]);directory=out.with_name(out.name+"-outer")
    at(outer_ref,directory/"outer.json")
    command=[plan["python"]["path"],"-B",str(HERE/"run.py"),"--plan",str(Path(plan_path).resolve()),
        "--plan-sha256",plan_sha256]
    d.need(outer["schema"]=="m192e-outer-run-v1" and outer["status"]=="COMPLETE_OUTER_CAPTURE_ONLY" and
        outer["phase"]=="TERMINAL_CAPTURE" and outer["command"]==command and same_ref(outer["plan"],plan_ref) and
        outer["exit_code"]==0 and outer["terminal_cpu_accounting"] is True and
        outer["termination_attempted"] is False and outer["cleanup_errors"]==[] and outer["error"] is None,
        "actual complete owned outer receipt")
    sources={str(d.lexical_path(r["path"])):r for r in plan["source_bindings"]}
    d.need(same_ref(outer["source"],sources[str(HERE/"launch.py")]),"held outer helper")
    d.check_ref(outer["source"])
    for stream in ("stdout","stderr"):
        at(outer[stream],directory/(stream+".log"));d.need(d.check_ref(outer[stream])["bytes"]<=d.MIB,"outer log extent")
    parent,ptail,padvert=final_tail(plan_ref,out,"parent",command,outer["stdout"])
    d.need(outer["process_id"]==ptail["process_id"],"same actual owned parent")
    fields={"created_100ns","exited_100ns","kernel_cpu_100ns","user_cpu_100ns"}
    before,after=outer["process_times_before"],outer["process_times_after"]
    for value in (before,after):
        d.need(type(value) is dict and set(value)==fields and
            all(type(v) is int and v>=0 for v in value.values()),"actual process-time field types")
    d.need(before["created_100ns"]==after["created_100ns"]>0 and
        after["exited_100ns"]>=after["created_100ns"] and
        after["kernel_cpu_100ns"]>=before["kernel_cpu_100ns"] and
        after["user_cpu_100ns"]>=before["user_cpu_100ns"],"same retained handle creation and terminal clocks")
    parent_cpu=(after["kernel_cpu_100ns"]+after["user_cpu_100ns"])/1e7
    d.need(parent_cpu>=padvert["sample_after_tail"]["process_cpu_seconds"],"terminal parent CPU includes publication")
    at(parent["child"],out/"child.json");child=read_ref(parent["child"],128*1024)
    worker_command=command+["--worker"]
    d.need(child["command"]==worker_command and child["terminal_job_accounting"] is True and child["exit_code"]==0 and
        child["error"] is None and child["cleanup_errors"]==[] and child["termination"]["attempted"] is False and
        child["job_accounting"]["active_processes"]==0,"natural complete bound worker Job")
    child_cpu=job_cpu(child["job_accounting"])
    d.need(child_cpu==ptail["sample"]["latest_owned_job_cpu_seconds"]==
        padvert["sample_after_tail"]["latest_owned_job_cpu_seconds"],"parent sample uses exact terminal child Job")
    worker,wtail,wadvert=final_tail(plan_ref,out,"worker",worker_command,child["log"])
    d.need(same_ref(parent["worker"],wadvert["canonical"]) and
        wtail["sample"]["process_cpu_seconds"]<=wadvert["sample_after_tail"]["process_cpu_seconds"]<=child_cpu,
        "worker terminal evidence belongs to parent-owned Job")
    d.need(parent_cpu+child_cpu<=600 and 0<=outer["elapsed_wall_seconds"]<=240 and
        outer["elapsed_wall_seconds"]>=padvert["sample_after_tail"]["wall_seconds"],
        "whole subject CPU/wall including terminal publication and exit")
    d.need(outer["job_accounting"]["active_processes"]==0 and
        job_cpu(outer["job_accounting"])<=600,"complete whole outer Job cross-bound")
    wrapper=outer["wrapper_sample"]
    d.need(wrapper["publication_allowance"]==dict(cpu_seconds=.25,wall_seconds=.5) and
        0<=wrapper["cpu_seconds"]+.25<=5 and 0<=wrapper["wall_seconds"]+.5<=255,
        "separate wrapper sampled work plus explicit tail allowance")
    verification=verify_worker(plan_path,plan_sha256,out/"worker"/"result.json")
    at(parent["verification"],out/"verification.json")
    retained=read_ref(parent["verification"],128*1024)
    d.need(retained==verification,"whole retained worker verification identity")
    # Both fresh roots count. The sibling contains only bounded outer evidence.
    totals={k:0 for k in d.FAMILIES};budget=d.Budget(out,1)
    for root in (out,directory):
        for base,dirs,names in os.walk(root,followlinks=False):
            for name in dirs+names:d.lexical_path(Path(base)/name)
            for name in names:
                path=Path(base)/name
                family=budget.family(path) if root==out else ("logs" if name.endswith(".log") else "metadata")
                totals[family]+=path.stat().st_size
    d.need(all(totals[k]<=d.FAMILIES[k] for k in totals) and sum(totals.values())<=d.TOTAL,
        "whole paired-root output family bounds")
    return dict(schema="m192e-terminal-verification-v1",status="PASS_BOUND_TERMINAL_REHEARSAL_ONLY",
        plan=plan_ref,outer=outer_ref,parent=padvert["canonical"],worker=wadvert["canonical"],
        parent_terminal_cpu_seconds=parent_cpu,worker_terminal_job_cpu_seconds=child_cpu,
        combined_terminal_cpu_seconds=parent_cpu+child_cpu,whole_parent_wall_seconds=outer["elapsed_wall_seconds"],
        wrapper_sample=wrapper,actual_family_bytes=totals,complete_subject_cpu_accounting=True,
        job_counter_controls=job_counter_controls(child["job_accounting"]),
        output_nonperturbation=verification["output_nonperturbation"],sampling_all_pass=verification["sampling_all_pass"],
        integration_pass=verification["integration_pass"],full_campaign_certificate=False,independent_review_required=True,
        scope="Parent terminal GetProcessTimes plus worker terminal Job CPU; outer Job is a cross-bound, never added again. Wrapper work is separate sampled work with declared tail. No campaign or timing-transition certification.")

def verify_worker(plan_path,plan_sha256,worker_path):
    plan_ref=d.binding(plan_path);d.need(plan_ref["sha256"]==plan_sha256.upper(),"released plan")
    plan=read_ref(plan_ref);out=d.lexical_path(plan["output_directory"])
    d.need(plan["schema"]=="m192e-rehearsal-plan-v1" and out.parent==HERE,"plan/output identity")
    sources={str(d.lexical_path(r["path"])):r for r in plan["source_bindings"]}
    for ref in plan["source_bindings"]:d.check_ref(ref)
    for ref in plan["baseline"].values():d.check_ref(ref)
    for key in ("python","binary","sidecar"):d.check_ref(plan[key])
    prior=load_bound(READER,"m192e_prior_independent_reader",sources)
    binding_reader=load_bound(BINDINGS,"m192e_prior_binding_reader",sources)
    domain=d.environment_domain(sources[str((ROOT/"scripts/check-defaults.py").resolve())],binding_reader)
    protocol=read_ref(sources[str(PROTOCOL)])
    cached=read_ref(plan["baseline"]["record"])
    at(d.binding(worker_path),out/"worker"/"result.json")
    worker_ref=d.binding(worker_path);worker=read_ref(worker_ref,64*1024)
    d.need(worker["schema"]=="m192e-worker-v1" and worker["status"]=="COMPLETE_REHEARSAL_EVIDENCE_ONLY"
        and worker["campaign_id"]==plan["campaign_id"] and worker["unvisited"]==[] and worker["active"] is None
        and worker["error"] is None and worker["full_campaign_certificate"] is False
        and len(worker["completed"])==3,"complete fixed worker")
    child=d.read_json(out/"child.json",128*1024)
    worker_command=[plan["python"]["path"],"-B",str(HERE/"run.py"),"--plan",str(Path(plan_path).resolve()),
        "--plan-sha256",plan_sha256,"--worker"]
    d.need(child["command"]==worker_command and child["exit_code"]==0 and child["terminal_job_accounting"] is True and
        child["job_accounting"]["active_processes"]==0 and child["error"] is None and child["cleanup_errors"]==[] and
        child["termination"]["attempted"] is False,"worker exit required before artifact verification")
    job_cpu(child["job_accounting"])
    _,_,advert=final_tail(plan_ref,out,"worker",worker_command,child["log"])
    d.need(same_ref(advert["canonical"],worker_ref),"actual worker stdout/canonical association")
    before,after=(read_ref(worker[key]) for key in ("inputs_before","inputs_after"))
    expected=read_ref(plan["baseline"]["inputs"])
    d.need(before==after and len(before)==len(expected)==33,"selected inputs preserved")
    # The worker's actual before/after hashes prove reads; this checker opens no RAW.
    for a,b in zip(before,expected):
        d.need(d.lexical_path(a["path"])==d.lexical_path(b["path"]) and a["bytes"]==b["bytes"]
            and a["mtime_ns"]==b["mtime_ns"] and a["sha256"]==b["sha256"].upper(),"same frozen input identity")
    old_before,old_after=(read_ref(worker[key]) for key in ("preserved_before","preserved_after"))
    manifest=read_ref(plan["baseline"]["preserved"])
    d.need(old_before==old_after and old_before["schema"]=="m192e-old-output-preservation-v1"
        and len(old_before["rows"])==7,"seven old outputs preservation")
    old_review=read_ref(plan["baseline"]["independent_review"])
    for i,(row,declared) in enumerate(zip(old_before["rows"],manifest["rows"])):
        d.need(row["index"]==declared["index"]==i and same_ref(row["record"],declared["record"])
            and same_ref(row["output"],declared["output"]),"bound old record/output set")
        old=read_ref(row["record"])
        d.need(row["output"]["sha256"]==old["tiff"]["output_sha256"]==old_review["rows"][i]["output_sha256"],
               "unchanged independently reviewed output")
    controls=read_ref(worker["controls"],128*1024)
    d.need([x["id"] for x in controls]==list(CONTROL_IDS) and all(x["passed"] is True for x in controls),
           "all new storage controls")
    overflow=controls[2]["publication"]
    d.need(overflow["canonical_refusal_verified"] is True and overflow["passed"] is False,
           "actual overflow disposition")
    refusal=read_ref(controls[2]["retained_refusal"],4096)
    d.need(refusal["status"]=="REFUSED" and refusal["reason"]=="TRACE_OVERFLOW" and
           controls[2]["retained_refusal"]["sha256"].upper()==overflow["canonical"]["sha256"].upper(),
           "durable exact overflow refusal before restored publication")
    d.need(controls[4]["publication"]["passed"] is True,"same publisher restoration")
    for row in controls[5:]:
        d.need(row["expected_error"] and row["restored_recovery"]["sequence"]==1,"powered re-sealed association fault")
        for witness in row["injected_generation_witnesses"]:
            raw=d.encode(witness["value"]);raw+=b" "*(witness["fixed_extent"]-len(raw))
            d.need(len(raw)==witness["mutated"]["bytes"]==16384 and d.sha(raw)==witness["mutated"]["sha256"],
                   "retained full injected generation before restoration")
    reports=[];invocations=[]
    for index,(mode,ref) in enumerate(zip(SCHEDULE,worker["completed"])):
        rid="native-n33-w8-"+mode;folder=out/"records"/rid
        at(ref,folder/"record.json");record=read_ref(ref,64*1024)
        d.need(record["schema"]=="m192e-record-v1" and record["campaign_id"]==plan["campaign_id"]
            and record["run_id"]==rid and record["sequence"]==index and record["mode"]==mode,"record population")
        at(record["invocation"],folder/"invocation.json");inv=read_ref(record["invocation"],64*1024)
        invocation_check(inv,plan,plan_ref,out,protocol,domain,index,mode,worker["inputs_before"]);invocations.append(inv)
        at(record["monitor"],folder/"monitor.json");raw=read_ref(record["monitor"])
        d.need(raw["argv"]==inv["argv"] and raw["mode"]=="on" and raw["returncode"]==0 and
               raw["job_accounting"]["active_processes"]==0 and raw["job_accounting"]["total_terminated_processes"]==0,
               "natural original sampler invocation")
        trace=prior.check_record(raw);telemetry=prior.check_telemetry(raw)
        d.need(raw["trace"]["enabled"] is True and record["natural_complete"] is True,"actual production trace")
        for stream in ("stdout","stderr"):
            origin=out/"work"/"monitor"/rid/(stream+".log")
            at(record["log_origins"][stream],origin);at(record["logs"][stream],out/"logs"/(rid+"."+stream+".log"))
            original_ref=d.check_ref(record["log_origins"][stream]);archived=d.check_ref(record["logs"][stream])
            d.need(original_ref["bytes"]==archived["bytes"]<=2*d.MIB and original_ref["sha256"]==archived["sha256"],
                   "bounded archived actual log")
        stderr=Path(record["logs"]["stderr"]["path"]).read_text(encoding="utf-8")
        destination=out/"work"/"outputs"/(rid+".tiff")
        markers={x:x in stderr for x in terminal_strings(protocol["inputs"]["33"],destination)}
        d.need(record["terminal_markers"]==markers and all(markers.values()),"actual terminal markers")
        at(record["output"],destination);d.check_ref(record["output"])
        image=prior.tiff(destination)
        d.need(image["shape"]==[4688,7032,3] and image["output_bytes"]==record["output"]["bytes"] and
               all(image[k]==record["tiff"][k]==cached["tiff"][k] for k in ("output_sha256","pixel_sha256"))
               and record["identity_matches"] is True,"whole native TIFF/pixel nonperturbation")
        at(record["adapter"],folder/"adapter.json");adapter=read_ref(record["adapter"],4096)
        checkpoint=checkpoint_check(record,adapter,raw,out,plan["campaign_id"],mode)
        d.need(record["sampling_pass"] is raw["sampling_pass"] and record["coverage"]==raw["coverage"]
            and record["max_interval_ms_including_final"]==raw["max_interval_ms_including_final"]
            and record["dropped"]==raw["trace"]["dropped"] and
            record["full_trace_retained"] is all(x==0 for x in raw["trace"]["dropped"].values()),"sampling/drop disposition")
        reports.append(dict(mode=mode,record=ref,output_sha256=image["output_sha256"],pixel_sha256=image["pixel_sha256"],
            sampling_pass=raw["sampling_pass"],max_interval_ms_including_final=raw["max_interval_ms_including_final"],
            final_interval_ms=raw["final_interval_ms"],coverage=raw["coverage"],dropped=record["dropped"],
            retained_gap_lower_bound_ms=trace["reconstructed_retained_max_interval_ms"],
            retained_max_reproduced=trace["complete_max_reproduced"],telemetry_snapshots=telemetry["snapshots"],
            checkpoint=checkpoint))
    # New invocation integration seam only. All fixtures are copies of actual
    # current-run metadata; old verifier/sampler/TIFF controls are not repeated.
    powered=[]
    mutations=(
        ("campaign",lambda x:x.__setitem__("campaign_id","00000000-0000-0000-0000-000000000000")),
        ("run",lambda x:x.__setitem__("run_id","native-n33-w8-WRONG")),
        ("argv",lambda x:x["argv"].__setitem__(4,"32")),
        ("worker",lambda x:x.__setitem__("workers",7)),
        ("environment",lambda x:x["environment"].__setitem__("STREHL_PYRAMID_WORKERS","7")),
        ("origin",lambda x:x.__setitem__("actual_monitor_folder",str(out/"work"/"WRONG"))))
    positive=invocations[0];unchanged=d.sha(d.encode(positive))
    for name,mutate in mutations:
        bad=copy.deepcopy(positive);mutate(bad);error=None
        try:invocation_check(bad,plan,plan_ref,out,protocol,domain,0,"off",worker["inputs_before"])
        except ValueError as exc:error=str(exc)
        d.need(error is not None and d.sha(d.encode(positive))==unchanged,"powered invocation binding rejection")
        powered.append(dict(id=name,expected_error=error,changed=bad,original_sha256=unchanged))
    invocation_check(positive,plan,plan_ref,out,protocol,domain,0,"off",worker["inputs_before"])
    all_sampling=all(r["sampling_pass"] for r in reports)
    d.need(worker["output_nonperturbation"] is True and worker["sampling_all_pass"] is all_sampling
        and worker["integration_pass"] is all_sampling,"complete rehearsal reduction")
    for ref in plan["source_bindings"]:d.check_ref(ref)
    return dict(schema="m192e-rehearsal-verification-v1",status="PASS_REHEARSAL_BINDINGS_ONLY",
        plan=plan_ref,worker=worker_ref,rows=reports,new_invocation_controls=powered,
        output_nonperturbation=True,sampling_all_pass=all_sampling,integration_pass=all_sampling,
        old_outputs_preserved=7,raw_payloads_opened_by_checker=0,full_campaign_certificate=False,
        independent_review_required=True,
        interpretation="Identity and sampling integration only; bounded tails and recoverable INCOMPLETE snapshots do not certify a campaign or isolate timing-transition causes.")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--plan",required=True,type=Path);parser.add_argument("--plan-sha256",required=True)
    parser.add_argument("--worker-result",type=Path);parser.add_argument("--outer",type=Path)
    parser.add_argument("--outer-sha256")
    args=parser.parse_args()
    d.need((args.outer is None)==(args.outer_sha256 is None) and
        ((args.worker_result is not None)!=(args.outer is not None)),"one explicit verification scope")
    result=(verify_outer(args.plan,args.plan_sha256,args.outer,args.outer_sha256) if args.outer is not None else
        verify_worker(args.plan,args.plan_sha256,args.worker_result))
    print(json.dumps(result,sort_keys=True,allow_nan=False))
if __name__=="__main__":main()
