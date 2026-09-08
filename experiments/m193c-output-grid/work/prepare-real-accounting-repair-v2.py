"""Metadata-only preparation for the surgical second operational attempt."""
import time
START=time.monotonic()
import argparse,ast,hashlib,json,math,os,stat,sys
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/"experiments/m193c-output-grid";SELF=Path(__file__).resolve()
PYTHON=Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe");SEEN={}
MIB=1<<20
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
CAPS=dict(cpu_seconds=100,wall_seconds=180,file_bytes=8*MIB,metadata_bytes=8*MIB)
EMPTY="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
EMPTY_PATHS=("experiments/m193c-output-grid/work/independent-sift-lightglue-real-prefix-audit-stderr.txt",
             "experiments/m193c-output-grid/work/independent-real-accounting-repair-audit-stderr.txt")
# Definitions only; never execute the frozen preparer's top-level release body.
OLD_PREPARER=HERE/"work/prepare-real-accounting-repair-1.py"
OLD_PIN=dict(bytes=14898,sha256="8b47379258c0b18225d8ba21933d912ea3c9fc086de0d0887b0b81cbb2758021")
def need(ok,message):
    if not ok:raise ValueError(message)
def load_helpers():
    with OLD_PREPARER.open("rb") as stream:data=stream.read(OLD_PIN["bytes"]+1)
    need(dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())==OLD_PIN,"held metadata helper source")
    names=("identity","strict","ref","checked","raw","read","same","encoded","create","predicted")
    nodes=[x for x in ast.parse(data).body if isinstance(x,ast.FunctionDef) and x.name in names]
    need(tuple(x.name for x in nodes)==names,"closed unchanged metadata helper selection")
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(OLD_PREPARER),"exec"),globals())
def empty_ref(name):
    need(name in EMPTY_PATHS,"exact known diagnostic role")
    path=ROOT/name
    def ident(info):return(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,getattr(info,"st_file_attributes",0),info.st_nlink)
    for p in (path,*path.parents):
        info=p.lstat();need(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,"owned diagnostic reparse")
    before=path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and before.st_size==0 and before.st_nlink==1,"owned exact empty diagnostic")
    with path.open("rb") as stream:
        opened=os.fstat(stream.fileno());data=stream.read(1);after_handle=os.fstat(stream.fileno())
    need(data==b"" and ident(before)==ident(opened)==ident(after_handle)==ident(path.stat(follow_symlinks=False)),"same-handle diagnostic identity")
    return dict(path=name,bytes=0,sha256=EMPTY),ident(before)
def positive_namespace(sources,evidence):
    need(type(sources) is dict and sources,"positive source map")
    for name,value in sources.items():
        need(type(name) is str and type(value) is dict and set(value)=={"bytes","sha256"} and type(value["bytes"]) is int
             and value["bytes"]>=1 and type(value["sha256"]) is str and len(value["sha256"])==64 and
             all(c in "0123456789abcdef" for c in value["sha256"]),"positive source extent before release")
    need(type(evidence) is dict and set(evidence)==set(EMPTY_PATHS) and
         all(type(v) is dict and set(v)=={"bytes","sha256"} and type(v["bytes"]) is int and
             v==dict(bytes=0,sha256=EMPTY) for v in evidence.values()),"exact two diagnostic entries")
    need(not set(sources)&set(evidence),"source/evidence disjoint")
def typed_work(value):
    need(type(value) is dict and set(value)==set(ALLOWANCE),"closed work")
    for key,v in value.items():
        need(type(v) in ((int,float) if key.endswith("seconds") else (int,)) and math.isfinite(v) and v>=0,"finite nonnegative work")
def main():
    load_helpers()
    p=argparse.ArgumentParser();p.add_argument("--source",nargs=2,action="append",required=True);args=p.parse_args()
    need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON,"exact metadata invocation")
    planpath=HERE/"real-accounting-repair-plan-2.json";priorpath=HERE/"work/real-accounting-repair-prior-work-2.json"
    grantpath=HERE/"work/real-accounting-repair-resource-authorization-2.json";output=HERE/"real-accounting-repair-2"
    need(all(not path.exists() for path in (planpath,priorpath,grantpath,output)),"fresh output2 only")
    oldref,old=read(HERE/"real-accounting-repair-plan-1.json","cdd83fa172486607ed8fd77798369327a6498a9f64d10950757a97f943462b32")
    need(old["schema"]=="m193c-real-accounting-repair-plan-v1" and len(old["source_bindings"])==296,"exact failed plan1")
    ar,audit=read(HERE/"work/independent-real-accounting-repair-audit.json","7a86134c6e2e570194caac609824e8e54f1a86c5c7bff0ad02e1af470aa16447")
    or_,outer=read(HERE/"work/independent-real-accounting-repair-audit-outer.json","8c6f40cbe643e8b13c8504eba2874f983c1e16d249bcc69fd38ec5a82727375c")
    need(audit["schema"]=="m193c-saved-real-accounting-repair-audit-v1" and
         audit["status"]=="PASS_SAVED_REAL_ACCOUNTING_REPAIR_OUTCOME_AUDIT" and
         all(audit[k] is False for k in ("subject_complete","diagnostic_observations_verified","verified_worker_scientific_population",
                                       "admission_allowed","cpu_accounting_complete")) and
         audit["new_run_cpu_accounting_complete"] is True and audit["worker_result"] is None,"audited parent-only prelaunch refusal")
    need(set(audit["external"])=={"plan","result","outer","console","exit"},"closed actual failed references")
    failed={key:checked(value) for key,value in audit["external"].items()};failed["audit"]=ar
    need(same(oldref,failed["plan"]),"exact failed plan association")
    parent=strict(raw(failed["result"]))
    need(parent["status"]=="REFUSED" and parent["active_phase"]=="authority" and parent["child_launch_entered"] is False
         and parent["worker_result"] is None and all(v==0 for v in parent["counters"].values())
         and parent["error"]["traceback_suffix"].endswith("ValueError: typed FileRef\n"),"zero-science namespace failure")
    asource=checked(audit["audit_source"]);aledger=checked(audit["audit_family"]["ledger"]);progress=checked(audit["audit_progress"])
    argv=[str(PYTHON),"-B",str((ROOT/asource["path"]).resolve()),"--source-sha256",asource["sha256"],"--ledger-sha256",aledger["sha256"]]
    for key in ("plan","result","outer","console","exit"):argv+=["--"+key+"-sha256",failed[key]["sha256"]]
    need(outer["command"]==argv and outer["exit_code"]==0 and outer["stdout_bytes"]==ar["bytes"] and outer["stderr_bytes"]==0
         and outer["elapsed_wall_seconds"]<=audit["audit_timing"]["wall_seconds"]+audit["audit_publication_allowance"]["wall_seconds"],
         "actual audit command/result/empty stderr/tail")
    empties={key:value for key,value in old["source_bindings"].items() if value["bytes"]==0}
    need(empties=={EMPTY_PATHS[0]:dict(bytes=0,sha256=EMPTY)},"exact historical namespace exclusion")
    sources={key:value for key,value in old["source_bindings"].items() if value["bytes"]>=1}
    need(len(sources)==295,"all295 positive historical bindings")
    evidence={};empty_seen={}
    for name in EMPTY_PATHS:
        value,identity_=empty_ref(name);evidence[name]={key:value[key] for key in ("bytes","sha256")};empty_seen[name]=identity_
    for name,expected in sources.items():
        actual=ref(name,expected["sha256"])
        need(actual["bytes"]==expected["bytes"],"all positive old extents unchanged")
    # No empty=True intake. Positive evidence may remain in the historical source
    # closure; only the two explicitly named zero diagnostics have a separate lane.
    extras=[oldref,ar,or_,asource,aledger,progress,*failed.values()]
    for path,digest in [*args.source,(str(SELF),None),*[(r["path"],r["sha256"]) for r in extras]]:
        value=ref(path,digest)
        binding={key:value[key] for key in ("bytes","sha256")}
        need(sources.setdefault(value["path"],binding)==binding,"positive source additions cannot replace historical bytes")
    replacement={}
    for key,name in (("runner","real-accounting-repair-v2-run.py"),("support","real-accounting-repair-v2-support.py"),("spec","real-accounting-repair-v2-preregister.md")):
        relative=(HERE/name).relative_to(ROOT).as_posix();need(relative in sources,"held new replacement supplied")
        replacement[key]=dict(path=relative,**sources[relative])
    for name in ("work/independent-real-accounting-repair-v2-source-review.md",
                 "work/independent-real-accounting-repair-v2-preparation-review.md",
                 "work/independent-real-accounting-repair-v2-audit.py",
                 "work/independent-real-accounting-repair-v2-auditor-source-review.md"):
        need((HERE/name).relative_to(ROOT).as_posix() in sources,"independent source/preparation/auditor closure")
    positive_namespace(sources,evidence)
    # Powered release-only metadata cases, before any output exists.
    controls=[]
    for label,bad_sources,bad_evidence,error in (
        ("zero-source",{**sources,EMPTY_PATHS[0]:dict(bytes=0,sha256=EMPTY)},evidence,"positive source extent before release"),
        ("false-zero-diagnostic",sources,{**evidence,EMPTY_PATHS[0]:dict(bytes=False,sha256=EMPTY)},"exact two diagnostic entries"),
        ("unexpected-empty",sources,{**evidence,"unexpected-empty":dict(bytes=0,sha256=EMPTY)},"exact two diagnostic entries")):
        observed=None
        try:positive_namespace(bad_sources,bad_evidence)
        except ValueError as exc:observed=str(exc)
        need(observed==error,"powered release namespace: "+label);controls.append(dict(id=label,passed=True,error=observed))
    positive_namespace(sources,evidence)
    base=dict(audit["actual_final_work"]);typed_work(base)
    need(base==dict(cpu_seconds=1292.771803,wall_seconds=1193.6198098999992,file_bytes=4059662381,metadata_bytes=68401447)
         and Decimal(audit["next_wall_seconds"])==Decimal(str(base["wall_seconds"])),"all audited costs retained")
    prior={key:float(Decimal(str(base[key])).quantize(Decimal(".000001"),rounding=ROUND_CEILING)+ALLOWANCE[key])
        if key.endswith("seconds") else base[key]+ALLOWANCE[key] for key in ALLOWANCE};typed_work(prior)
    oldlimits=dict(cpu_seconds=1320,wall_seconds=1800,file_bytes=4<<30,metadata_bytes=128*MIB)
    newlimits=dict(oldlimits,cpu_seconds=1440)
    need(prior["cpu_seconds"]+CAPS["cpu_seconds"]>oldlimits["cpu_seconds"] and
         all(Decimal(str(prior[key]))+CAPS[key]<=newlimits[key] for key in CAPS),"finite extension needed; whole attempt fits")
    python=checked(old["python_executable"])
    grant=dict(schema="m193c-real-accounting-repair-resource-authorization-v2",
        status="AUTHORIZED_SINGLE_FRESH_OPERATIONAL_REPLACEMENT",previous_cumulative_limits=oldlimits,
        additional_authorized_work=dict(cpu_seconds=120,wall_seconds=0,file_bytes=0,metadata_bytes=0),
        new_cumulative_limits=newlimits,preparation_allowance=ALLOWANCE,attempt_caps=CAPS,previous_charged_work=base,
        previous_ceiling_disposition="RETIRED_NOT_RESET",new_output=output.relative_to(ROOT).as_posix(),
        failed_prefix_audit=old["failed_real_baseline"]["audit"],callback_result=old["callback_baseline"]["result"],
        replacement_sources=replacement,failed_repair_audit=ar,evidence_bindings=evidence)
    grantraw=encoded(grant);grantref=predicted(grantpath,grantraw);priorraw=encoded(prior);priorref=predicted(priorpath,priorraw)
    script=str(HERE/"real-accounting-repair-v2-run.py");prefix=[str(PYTHON),"-B","-X","faulthandler","-X"]
    parent_argv=prefix+["pycache_prefix="+str(output/"parent-cache"),script,"--plan",str(planpath),
        "--sha256","ACTUAL_PLAN_SHA256","--output",str(output)]
    worker_argv=prefix+["pycache_prefix="+str(output/"worker-cache"),script,"--plan",str(planpath),
        "--sha256","ACTUAL_PLAN_SHA256","--output",str(output/"worker"),"--worker","--request",str(output/"request.json"),
        "--request-sha256","ACTUAL_REQUEST_SHA256"]
    plan=dict(schema="m193c-real-accounting-repair-plan-v2",source_bindings=sources,private_baseline=old["private_baseline"],
        failed_real_baseline=old["failed_real_baseline"],callback_baseline=old["callback_baseline"],resource_authorization=grantref,
        prior_work=priorref,preparation_allowance=ALLOWANCE,python_executable=python,
        commands=dict(parent=parent_argv,worker=worker_argv),failed_repair_baseline=failed,evidence_bindings=evidence)
    need(len(plan)==12 and len(grant)==15,"closed v2 release schemas")
    positive_namespace(plan["source_bindings"],plan["evidence_bindings"])
    planraw=encoded(plan)
    need(len(planraw)<=256*1024 and len(grantraw)<=16*1024 and len(priorraw)<=4096,"fixed release extents")
    newbytes=sum(v["bytes"] for k,v in sources.items() if k not in old["source_bindings"])
    ledger=dict(newly_bound_source_and_metadata_bytes=newbytes,plan_capacity=256*1024,prior_capacity=4096,
        authorization_capacity=16384,outer_console_exit_capacity=8192,continuation_capacity=16384,
        prospective_independent_audit_family_capacity=384*1024)
    need(sum(ledger.values())<=MIB,"whole preparation family reserved")
    for path,(value,before) in SEEN.items():
        need(identity(Path(path).stat(follow_symlinks=False))==before,"all positive metadata unchanged before release")
    for name,before in empty_seen.items():need(empty_ref(name)[1]==before,"both empty diagnostics unchanged before release")
    need(time.process_time()<20 and time.monotonic()-START<30,"full fixed metadata preparation allowance")
    # One last explicit predicate before the FIRST write, so the original defect
    # cannot be deferred until the subject's immutable source reader.
    positive_namespace(sources,evidence)
    need(create(grantpath,grantraw)==grantref and create(priorpath,priorraw)==priorref,"actual fixed authority/prior writes")
    planref=create(planpath,planraw)
    need(time.process_time()<20 and time.monotonic()-START<30,"fixed preparation through publication")
    print(json.dumps(dict(status="PREPARED_SURGICAL_SOURCE_EVIDENCE_REPAIR_METADATA_ONLY",plan=planref,prior_work=priorref,
        resource_authorization=grantref,source_count=len(sources),preserved_positive_sources=295,empty_diagnostics=len(evidence),
        preparation_capacity_ledger=ledger,preparation_capacity_bytes=sum(ledger.values()),namespace_controls=controls,
        sampled_preparation_work=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START),
        images_opened=0,feature_payloads_opened=0,checkpoint_reads=0,model_imports=0,registrar_calls=0,
        prior_accounting_scope="all charged failures retained;1320 retired without reset;1440 explicit cumulative CPU maximum"),allow_nan=False))
if __name__=="__main__":main()
