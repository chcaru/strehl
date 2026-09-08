"""One explicitly authorized operational replacement; unchanged held real-pair science."""
import time
START=time.monotonic()
import argparse,hashlib,json,math,os,sys,traceback,types
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
SPEC=HERE/"real-accounting-repair-preregister.md";SUPPORT=HERE/"real-accounting-repair-support.py"
MIB=1<<20;KIB=1024
VERSION="m193c-real-accounting-repair-v1"
COMPLETE="COMPLETE_FIXED_REAL_LIGHTGLUE_DIAGNOSTIC_ONLY"
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
OLD_PIN=dict(bytes=51374,sha256="038a7d649932553891e16018efe1a5d6b6ad313a8073471c4dc8b6a19ce3a420")
PREFIX_PIN=dict(bytes=11333,sha256="4f8b48d9edf19fdac45c38aaf3bab85364e853a721827d4415d4d7dcb91cc66f")
CALLBACK_PIN=dict(bytes=10240,sha256="b42293535eed7fcd9545a451804da23fcfa6d7735d0639f10b92e7a06c899bb0")
KEYS="schema source_bindings private_baseline failed_real_baseline callback_baseline resource_authorization prior_work preparation_allowance python_executable commands".split()
def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(raw):return dict(bytes=len(raw),sha256=sha(raw))
def readraw(path,cap=4*MIB):
    with Path(path).open("rb") as stream:raw=stream.read(cap+1)
    need(0<len(raw)<=cap,"bounded source/plan read");return raw
def path_of(ref):return (ROOT/ref["path"]).resolve()
def same(a,b):return path_of(a)==path_of(b) and all(a[k]==b[k] for k in ("bytes","sha256"))
def load(path,expected,name):
    raw=readraw(path);need(pin(raw)==expected,"held module source")
    module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
    exec(compile(raw,str(path),"exec"),module.__dict__);return module
def setup(args):
    old=load(HERE/"sift-lightglue-real-run.py",OLD_PIN,"m193c_immutable_real_science")
    c=load(HERE/"sift-lightglue-saved-completion-run.py",old.PIN_HELPER,"m193c_repair_saved_helpers")
    utility=HERE/"native-derivative-run.py";raw=readraw(utility)
    need(sha(raw)==c.PINS[utility.name],"immutable reader")
    n=load(utility,pin(raw),"m193c_repair_reader")
    data=readraw(args.plan);need(sha(data)==args.sha256,"actual new plan SHA")
    plan=n.strict(data);n.closed(plan,KEYS,"new closed operational plan")
    need(plan["schema"]=="m193c-real-accounting-repair-plan-v1" and plan["preparation_allowance"]==ALLOWANCE,
         "operational version and fixed preparation")
    expected=[SELF,SPEC,SUPPORT,HERE/"sift-lightglue-real-run.py",HERE/"sift-lightglue-real-codec.py",
              HERE/"sift-lightglue-saved-completion-run.py",HERE/"saved-completion-publication.py",c.REFERENCE,c.HARNESS,
              HERE/"work/accounting-callback-comparison.py",*[HERE/x for x in c.PINS if x!="reference.py"]]
    for path in expected:
        held=plan["source_bindings"][n.relative(path)]
        need(pin(readraw(path))==held and (path.name not in c.PINS or held["sha256"]==c.PINS[path.name]),
             "complete executed source closure")
    need(plan["source_bindings"][n.relative(HERE/"sift-lightglue-real-run.py")]==OLD_PIN and
         plan["source_bindings"][n.relative(HERE/"sift-lightglue-saved-completion-run.py")]==old.PIN_HELPER and
         plan["source_bindings"][n.relative(HERE/"saved-completion-publication.py")]==old.PIN_PUBLISHER,"immutable science/helpers")
    support=load(SUPPORT,plan["source_bindings"][n.relative(SUPPORT)],"m193c_repair_support")
    pub=load(HERE/"saved-completion-publication.py",old.PIN_PUBLISHER,"m193c_repair_publication")
    codec=load(HERE/"sift-lightglue-real-codec.py",plan["source_bindings"][n.relative(HERE/"sift-lightglue-real-codec.py")],"m193c_repair_codec")
    output=Path(args.output).resolve()
    need(Path.cwd().resolve()==ROOT and output.is_relative_to(HERE) and not output.exists(),"owned fresh output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions)=={"faulthandler","pycache_prefix"} and sys._xoptions["faulthandler"] is True,
         "exact Python options")
    cache=Path(sys._xoptions["pycache_prefix"]).resolve()
    need(not cache.exists() and cache.is_relative_to(output.parent if args.worker else output),"fresh owned cache")
    n.closed(plan["commands"],("parent","worker"),"commands")
    need(old.command(plan["commands"]["worker" if args.worker else "parent"],args.sha256,args.request_sha256)==sys.orig_argv,
         "exact actual command")
    grant_bytes=readraw(path_of(plan["resource_authorization"]),MIB)
    need(pin(grant_bytes)=={k:plan["resource_authorization"][k] for k in ("bytes","sha256")},"exact new resource authorization")
    grant=n.strict(grant_bytes)
    return old,c,n,support,pub,codec,plan,output,dict(path=str(Path(args.plan).resolve()),**pin(data)),grant

def authority(old,c,n,s,plan,files,grant,output,worker):
    failed=plan["failed_real_baseline"];n.closed(failed,("plan","result","outer","console","exit","audit"),"failed attempt references")
    need({k:failed["audit"][k] for k in ("bytes","sha256")}==PREFIX_PIN,"exact independently read failed-prefix audit")
    audit,previous,parent,outer=(c.read(files,failed[k]) for k in ("audit","plan","result","outer"))
    need(audit["schema"]=="m193c-saved-sift-lightglue-real-prefix-audit-v1" and
         audit["status"]=="PASS_SAVED_REAL_LIGHTGLUE_METADATA_PREFIX_AUDIT" and audit["saved_metadata_prefix_verified"] is True,
         "independently verified metadata prefix only")
    need(all(audit[k] is False for k in ("subject_complete","diagnostic_observations_verified","admission_allowed",
         "cpu_accounting_complete","new_run_cpu_accounting_complete","model_runtime_verified","model_state_verified","guard_restoration_verified")),
         "prior incomplete science/CPU remains incomplete")
    need(set(audit["external"])==set(failed)-{"audit"} and all(same(audit["external"][k],failed[k]) for k in audit["external"]),
         "failed actual outer/console/exit association")
    need(parent["status"]=="REFUSED" and outer["exit_code"]==1 and outer["plan_sha256"]==failed["plan"]["sha256"] and
         outer["command"]==old.command(previous["commands"]["parent"],failed["plan"]["sha256"]) and
         c.checked(files,failed["exit"],64).strip()==b"1","original refusal and actual command remain")
    c.checked(files,failed["console"],MIB);c.read(files,audit["worker_result"])
    need(previous["schema"]=="m193c-sift-lightglue-real-plan-v1","old plan remains old schema")
    # Crucially, invoke historical authority on its unchanged seven-key old plan.
    saved,pa,private,da,_=old.authority(c,n,previous,files)
    need(set(plan["private_baseline"])==set(previous["private_baseline"]) and
         all(set(plan["private_baseline"][kind])==set(refs) and
             all(same(plan["private_baseline"][kind][key],ref) for key,ref in refs.items())
             for kind,refs in previous["private_baseline"].items()),"same admitted private prerequisites")
    need(all(plan["source_bindings"].get(k)==v for k,v in previous["source_bindings"].items()),"entire historical source closure preserved")
    callback=plan["callback_baseline"];n.closed(callback,("source","protocol","review","result","outer","console","exit"),"actual callback references")
    need({k:callback["result"][k] for k in ("bytes","sha256")}==CALLBACK_PIN,"actual once-only callback result")
    probe,po=(c.read(files,callback[k]) for k in ("result","outer"))
    need(probe["schema"]=="m193c-accounting-callback-comparison-v1" and probe["status"]=="PASS_CALLBACK_EQUIVALENCE_AND_POWER_ONLY" and
         probe["sources_unchanged"] is True and probe["scientific_calls"]==0 and probe["error"] is None,"bounded accounting comparison only")
    ids=("hash","cadence","local-cpu","global-cpu","publication-cpu","local-wall","global-wall","publication-wall",
         "worker-soft-wall","family","prewrite-family","prewrite-metadata","joint-parent-child")
    need(tuple(row["id"] for row in probe["cases"])==ids and
         all(row["passed"] is True and row["whole_intrinsic_equal"] is True and row["old_sha256"]==row["candidate_sha256"] for row in probe["cases"]),
         "all thirteen whole intrinsic results unchanged")
    h=probe["cases"][0]
    need(h["old_counts"]==dict(checks=1,family=585,scans=1,totals=9) and
         h["candidate_counts"]==dict(checks=1,family=33,scans=1,totals=1),"actual exercised callback reduction")
    need(len(probe["owned_source_bindings"])==3 and all(same(probe["owned_source_bindings"][i],callback[k])
         for i,k in enumerate(("source","protocol","review"))),"all three actual comparison owned source bindings")
    for key in ("source","protocol","review"):c.checked(files,callback[key],MIB)
    need(po["exit_code"]==0 and c.checked(files,callback["exit"],64).strip()==b"0" and
         po["command"]==[str(path_of(plan["python_executable"])),"-B",str(path_of(callback["source"])),"--output",str(path_of(callback["result"]).parent)],
         "actual once-only callback command/exit")
    line=n.strict(c.checked(files,callback["console"],MIB))
    need(line["status"]==probe["status"] and Path(line["path"]).resolve()==path_of(callback["result"]) and
         line["sha256"]==callback["result"]["sha256"],"actual callback stdout binds exact saved result")
    n.closed(grant,("schema","status","previous_cumulative_limits","additional_authorized_work","new_cumulative_limits",
        "preparation_allowance","attempt_caps","previous_charged_work","previous_ceiling_disposition","new_output",
        "failed_prefix_audit","callback_result","replacement_sources"),"explicit separate resource authorization")
    need(grant["schema"]=="m193c-real-accounting-repair-resource-authorization-v1" and
         grant["status"]=="AUTHORIZED_SINGLE_FRESH_OPERATIONAL_REPLACEMENT" and grant["previous_ceiling_disposition"]=="RETIRED_NOT_RESET" and
         grant["previous_cumulative_limits"]==s.OLD_GLOBAL and grant["additional_authorized_work"]==s.EXTENSION and
         grant["new_cumulative_limits"]==s.NEW_GLOBAL and grant["preparation_allowance"]==ALLOWANCE and grant["attempt_caps"]==s.ATTEMPT,
         "explicit1320 cumulative ceiling, old1200 retired and unchanged local science envelope")
    need(Path(grant["new_output"]).resolve()==(output.parent if worker else output) and same(grant["failed_prefix_audit"],failed["audit"]) and
         same(grant["callback_result"],callback["result"]),"authorization exact attempt and evidence")
    n.closed(grant["replacement_sources"],("runner","support","spec"),"authorized replacement source identities")
    for key,path in (("runner",SELF),("support",SUPPORT),("spec",SPEC)):
        ref=grant["replacement_sources"][key]
        need(path_of(ref)==path and {k:ref[k] for k in ("bytes","sha256")}==plan["source_bindings"][n.relative(path)],
             "authorized exact replacement bytes")
        c.checked(files,ref,MIB)
    c.checked(files,plan["resource_authorization"],MIB)
    base=audit["actual_final_work"];prior=c.read(files,plan["prior_work"])
    c.typed_prior(n,base);c.typed_prior(n,prior)
    need(grant["previous_charged_work"]==base and Decimal(audit["next_wall_seconds"])==Decimal(str(base["wall_seconds"])),
         "all previous spent reservations retained without reset")
    for key in ALLOWANCE:
        value=Decimal(str(base[key]))
        if key.endswith("seconds"):value=value.quantize(Decimal(".000001"),rounding=ROUND_CEILING)
        need(Decimal(str(prior[key]))==value+ALLOWANCE[key],"conservative microsecond ceiling plus full preparation")
    need(all(Decimal(str(prior[k]))+s.ATTEMPT[k]<=s.NEW_GLOBAL[k] for k in ALLOWANCE),"entire one-attempt maximum fits authorized cumulative envelope")
    return saved,pa,private,da,prior,audit,probe

def compact_error():
    full=traceback.format_exc();suffix=full[-12000:]
    value=dict(type=sys.exc_info()[0].__name__,traceback_suffix=suffix,full_traceback_characters=len(full),
               full_traceback_utf8_sha256=sha(full.encode()),truncated=len(full)>len(suffix))
    while len(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True).encode())>4096:
        suffix=suffix[len(suffix)//2:];value.update(traceback_suffix=suffix,truncated=True)
    return value

def merge_child_ledger(b,output,child):
    """Import authenticated monotone reservations; no filesystem writes or CPU admission."""
    ledger=child.get("charged_path_extents")
    if ledger is None:
        need(child.get("status")=="REFUSED","missing child ledger cannot admit success")
        b.extent_uncertain=True
        return
    need(type(ledger) is dict and len(ledger)<=512,"bounded child reservation ledger")
    for name,size in ledger.items():
        path=(output/"worker"/name).resolve()
        need(type(name) is str and path.is_relative_to(output/"worker") and
             path.relative_to(output/"worker").as_posix()==name and type(size) is int and 0<size<=MIB,
             "authenticated canonical owned child ledger entry")
        family=b.family(path);need(family in b.families,"declared child family")
        b.overrides[str(path)]=family;b.extents[str(path)]=max(b.extents.get(str(path),0),size)
    used={key:0 for key in b.metadata_families}
    for path,size in b.extents.items():
        family=b.overrides[path] if path in b.overrides else b.family(path)
        if family=="metadata":
            parts=Path(path).relative_to(output).parts
            if parts[0]=="worker":parts=parts[1:]
            sub=parts[1] if parts[0]=="metadata" and len(parts)>2 else "controller"
            need(sub in used,"declared child metadata subfamily");used[sub]+=size
    need(all(used[k]<=v for k,v in b.metadata_families.items()),"combined monotone metadata subfamilies")
    with b.terminal():b.check(True)

def main():
    parser=argparse.ArgumentParser()
    for key in ("plan","sha256","output"):parser.add_argument("--"+key,required=True)
    parser.add_argument("--worker",action="store_true");parser.add_argument("--request");parser.add_argument("--request-sha256")
    args=parser.parse_args();need(args.worker==(args.request is not None and args.request_sha256 is not None),"worker-only request")
    old,c,n,s,pub,codec,plan,output,plan_ref,grant=setup(args)
    prior_bytes=readraw(path_of(plan["prior_work"]),MIB)
    need(pin(prior_bytes)=={k:plan["prior_work"][k] for k in ("bytes","sha256")},"exact prior")
    planned=n.strict(prior_bytes);c.typed_prior(n,planned);prior=planned;request_ref=None
    if args.worker:
        data=readraw(args.request,MIB);need(sha(data)==args.request_sha256,"actual worker request digest")
        request=n.strict(data);n.closed(request,("schema","plan","prior_work"),"worker request")
        need(request["schema"]=="m193c-real-accounting-repair-request-v1" and same(request["plan"],plan_ref),"exact replacement request")
        c.typed_prior(n,request["prior_work"])
        need(all(Decimal(str(request["prior_work"][k]))>=Decimal(str(planned[k])) for k in ALLOWANCE),"monotone request carry")
        prior=request["prior_work"];request_ref=dict(path=str(Path(args.request).resolve()),**pin(data))
    output.mkdir();b=s.make_budget(n,old,output,prior,args.worker,grant,START);files=n.Files(b)
    result=dict(schema="m193c-real-accounting-repair-worker-v1" if args.worker else "m193c-real-accounting-repair-run-v1",
        implementation_version=VERSION,scientific_implementation_version=old.VERSION,status="REFUSED",plan=plan_ref,request=request_ref,
        command=sys.orig_argv,prior_work=prior,private_baseline=plan["private_baseline"],failed_real_baseline=plan["failed_real_baseline"],
        callback_baseline=plan["callback_baseline"],resource_authorization=plan["resource_authorization"],
        old_run_status="REFUSED",original_commission_complete=False,previous_real_run_status="REFUSED",
        cpu_accounting_complete=False,new_run_cpu_accounting_complete=False,sources_unchanged=False,
        counters=dict(images=0,extractions=0,normalizations=0,model_forwards=0,registrar_calls=0),
        active_phase="authority",controls=[],control_records=[],codec_controls=[],publication_controls=None,
        publication_control_prefixes=[],publication_control_summary=[],pairs=[],predictions=[],fits=[],
        unvisited=[list(x) for x in old.PAIRS],runtime_before=None,runtime_after=None,saved_feature_checks=0,
        inference_observer_nonperturbation="UNTESTED_CURRENT_PROCESS",qualification=old.QUALIFIER,error=None,worker_result=None,
        child_observation=None,accounting_controls=None,live_accounting_controls=None,child_launch_entered=False)
    publisher=pub.Publisher(pub.Writer(b,output,"terminal"),dict(schema=result["schema"],implementation_version=VERSION,
        scientific_implementation_version=old.VERSION,plan=plan_ref,request=request_ref,prior_work=prior,
        resource_authorization=plan["resource_authorization"],cpu_accounting_complete=False,new_run_cpu_accounting_complete=False,
        old_run_status="REFUSED",previous_real_run_status="REFUSED",original_commission_complete=False,qualification=old.QUALIFIER))
    s.prepare_transport(b,pub,output,args.worker)
    saved=None;observed=None;child=None;child_ledger_retained=False
    job_path=output/"operational/child-terminal.json"
    if not args.worker:
        result["child_observation"]=s.write_slot(pub,b,job_path,dict(schema="m193c-durable-child-terminal-v1",
            measurement_scope="UNOBSERVED_CHILD_TERMINAL",observation=None,new_run_cpu_accounting_complete=False))
    try:
        files.verify(plan_ref,MIB,True);n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True)==Path(sys.executable).resolve(),"same held Python")
        saved,pa,private,da,derived,audit,probe=authority(old,c,n,s,plan,files,grant,output,args.worker)
        need(derived==planned and b.optimized_ast_sha256==probe["candidate_ast"],"exact derived prior and executed optimization AST")
        result["accounting_implementation"]=dict(optimized_ast_sha256=b.optimized_ast_sha256,authorized_ast_sha256=b.granted_ast_sha256,
             old_cumulative_cpu_limit=1200,new_cumulative_cpu_limit=1320,old_ceiling_disposition="RETIRED_NOT_RESET",
             previous_charged_work=audit["actual_final_work"],optimization_effect="COUNTER_REDUCTION_VERIFIED; failed96s attribution unmeasured")
        if args.worker:
            files.verify(request_ref,MIB,True);result["active_phase"]="publication-controls";observations=[]
            def progress(rows):
                result["publication_control_summary"]=[dict(id=row["id"],passed=row["passed"],error=row.get("error")) for row in rows]
                ref=old.save(pub,b,files,output,"publication-progress-"+str(len(rows))+".json",
                    dict(schema="m193c-publication-progress-v1",ordinal=len(rows),row=rows[-1],earlier=result["publication_control_prefixes"].copy()),
                    "publication",cap=24*KIB)
                result["publication_control_prefixes"].append(ref)
            controls=pub.commission(b,output/"publication-controls",observations,progress)
            result["publication_controls"]=old.save(pub,b,files,output,"publication-control-result.json",
                dict(schema=controls["schema"],passed=controls["passed"],scope=controls["scope"],controls=result["publication_control_prefixes"]),
                "publication",cap=8192)
            # No override or transformation of science, normalization, matching, fitting, observations or codecs.
            old.science(c,n,pub,codec,plan,files,b,output,result,saved,pa,private,da)
            need(c.read(files,result["import_guard_final"])["import_guard_restored"] is True,"actual final import guard restored")
        else:
            result["active_phase"]="operational-controls"
            result["accounting_controls"]=s.operation_controls(n,old,pub,b,grant,output/"operational/accounting-controls",START)
            result["live_accounting_controls"]=s.live_controls(n,old,pub,b,grant,output/"operational/live-controls")
            result["active_phase"]="request"
            request=dict(schema="m193c-real-accounting-repair-request-v1",plan=plan_ref,prior_work=b.work())
            request_ref=old.save(pub,b,files,output,"request.json",request,cap=2048);result["request"]=request_ref
            argv=old.command(plan["commands"]["worker"],args.sha256,request_ref["sha256"])
            need(argv[argv.index("--output")+1]==str(output/"worker") and argv[argv.index("--request")+1]==str(output/"request.json"),
                 "fixed worker output/request paths")
            for name in pub.NAMES:b.reserve(output/"worker"/name,64*KIB,"terminal",True)
            for group in ("normal","capacity","oversized","late-before-stdout","restored-placebo","stdout-after-escape","emergency-fallback"):
                for name in pub.NAMES:b.reserve(output/"worker/publication-controls"/group/name,4096,"publication",True)
            b.reserve(output/"worker/operational/accounting-final.json",8192,"operational",True)
            b.reserve(output/"worker.log",MIB,"log",True)
            process=load(HERE/"bounded-process.py",plan["source_bindings"][n.relative(HERE/"bounded-process.py")],"m193c_repair_process")
            api=c.selected(c.HARNESS,plan["source_bindings"][n.relative(c.HARNESS)],c.JOB_NAMES+c.JOB_SIGNATURES)
            env,removed=process.clean_environment();removed+=[k for k in env if k.upper().startswith("PYTHON")]
            env={k:value for k,value in env.items() if not k.upper().startswith("PYTHON")};env["CUDA_VISIBLE_DEVICES"]=""
            result["environment_removed"]=sorted(set(removed));result["active_phase"]="worker"
            limits=b.limits()
            result["child_launch_entered"]=True;b.complete=False
            # Query wrapper is active for normal polling AND final/termination observations.
            try:
                with s.live_job_accounting(api,b):
                    observed=process.run(argv,env,ROOT,output/"worker.log",api=api,check=b.check,**limits)
            finally:
                if observed is not None:
                    try:s.capture_child(pub,b,job_path,observed)
                    finally:
                        # Even cap rejection above cannot discard the already durable exact Job record.
                        with b.terminal():
                            result["child_observation"]=files.bind(job_path,16*KIB,True)
                            retained_job=c.read(files,result["child_observation"])
                            result["child_receipt_observed"]=retained_job.get("observation") is not None
                            child_path=output/"worker/result.json"
                            if child_path.exists():
                                result["worker_result"]=files.bind(child_path,64*KIB,True)
                                child=c.read(files,result["worker_result"])
                                need(same(child["plan"],plan_ref) and same(child["request"],request_ref),"retained child exact request association")
                                merge_child_ledger(b,output,child);child_ledger_retained=not b.extent_uncertain
                                result["worker_status"]=child.get("status");result["worker_active_phase"]=child.get("active_phase")
            n.successful_process(observed,argv)
            need(result["worker_result"] is not None and child["schema"]=="m193c-real-accounting-repair-worker-v1" and
                 child["implementation_version"]==VERSION and child["scientific_implementation_version"]==old.VERSION and
                 child["status"]==COMPLETE and child["error"] is None and child["new_run_cpu_accounting_complete"] is True and
                 child["sources_unchanged"] is True and child["command"]==argv,"actual complete replacement worker")
            for key in ("counters","saved_feature_checks","inference_observer_nonperturbation","development_outcome"):
                result[key]=child[key]
            result["unvisited"]=[];result["active_phase"]="complete"
        # These remain ordinary admission work; terminal transport does not authorize more science or hashing.
        files.recheck();b.check(True)
        if not args.worker and saved:
            result["runtime_final"]=old.save(pub,b,files,output,"runtime/parent-final.json",
                old.runtime(c,n,None,files,plan,saved),"runtime",cap=8*KIB)
        need(b.complete and b.job_accounting_error is None,"new run complete observed accounting")
        b.admit_terminal()
        result["sources_unchanged"]=True;result["new_run_cpu_accounting_complete"]=True;result["status"]=COMPLETE
    except BaseException:
        result["status"]="REFUSED";result["error"]=compact_error()
        if not args.worker and result["child_launch_entered"] and not child_ledger_retained:b.extent_uncertain=True
    # Only predeclared small transport files are writable here. Cap failures never resume science.
    with b.terminal():
        try:
            if args.worker:
                population={key:result[key] for key in ("pairs","predictions","fits","unvisited","controls","control_records","codec_controls")}
                result["population"]=old.save(pub,b,files,output,"metadata/manifest/population.json",population,cap=48*KIB,terminal=True)
                for key in ("pairs","predictions","fits","control_records"):result[key]=dict(count=len(result[key]),record=result["population"])
            b.check(True);result["new_run_cpu_accounting_complete"]=b.complete
            result["work"]=dict(conservative_global_work=b.work(),new_charged_extent_bytes=sum(b.extents.values()),local_caps=s.ATTEMPT,
                family_limits=b.families,metadata_subfamily_limits=b.metadata_families,new_run_cpu_accounting_complete=b.complete,
                prior_cpu_accounting_complete=False,extent_scope="full local8MiB charged because child ledger unavailable" if b.extent_uncertain else
                "monotone reserved path maxima; actual inventory is separate",extent_accounting_complete=not b.extent_uncertain)
            result["charged_path_extents"]={Path(path).relative_to(output).as_posix():size for path,size in sorted(b.extents.items())}
            accounting=dict(schema="m193c-real-accounting-repair-final-accounting-v1",status=result["status"],
                conservative_global_work=b.work(),new_run_cpu_accounting_complete=b.complete,prior_cpu_accounting_complete=False,
                transport=b.transport_summary(),child_observation=result["child_observation"],worker_result=result["worker_result"],
                measurement_scope="CURRENT_PROCESS_PLUS_LATEST_OBSERVED_OWNED_JOB_CPU; historical CPU gap remains")
            result["accounting_final"]=s.write_slot(pub,b,output/"operational/accounting-final.json",accounting,8192)
        except BaseException:
            result["status"]="REFUSED";result["accounting_finalization_error"]=compact_error()
        try:
            need(len(pub.encoded(result))<=60*KIB,"whole terminal record60KiB preflight")
        except BaseException:
            result["status"]="REFUSED";result["terminal_shape_error"]=compact_error()
        try:
            s.refresh_recovery(publisher,b,dict(request=result["request"],child_observation=result["child_observation"],
                worker_result=result["worker_result"],accounting_final=result.get("accounting_final"),
                error=result.get("terminal_shape_error") or result.get("error"),
                new_run_cpu_accounting_complete=b.complete,charged_extent_fallback="FULL_LOCAL8MIB_IF_DETAILED_LEDGER_UNAVAILABLE"))
        except BaseException:
            result["status"]="REFUSED";result["recovery_refresh_error"]=compact_error()
        def admit():
            if result["status"]==COMPLETE:b.admit_terminal()
            else:b.check(True)
        def emit(receipt):
            sys.stdout.write(json.dumps(dict(status=result["status"],result=receipt,cpu_accounting_complete=False,
                new_run_cpu_accounting_complete=b.complete,conservative_work_through_publication=b.work()),allow_nan=False)+"\n");sys.stdout.flush()
        published=publisher.publish(result,late=admit,emit=emit,after=admit)
    tail=dict(schema="m193c-real-accounting-repair-publication-tail-v1",
        status=result["status"] if published["passed"] else "REFUSED" if published.get("canonical_refusal_verified") is True else "REFUSAL_PUBLICATION_UNVERIFIED",
        publication={key:published.get(key) for key in ("passed","canonical","canonical_refusal_verified","first_positive","phase")},
        publication_error_type=(published.get("error") or {}).get("type"),child_observation=result["child_observation"],
        worker_result=result["worker_result"],accounting_final=result.get("accounting_final"),
        transport=b.transport_cost(),conservative_work_through_transport_exit=b.work(),
        timing_scope="measured through last transport exit; excludes this final bounded stderr write")
    tail_bytes=s.encoded(tail);need(len(tail_bytes)<=4096,"bounded actual transport tail")
    sys.stderr.write(tail_bytes.decode());sys.stderr.flush()
    return 0 if published["passed"] else 1

if __name__=="__main__":raise SystemExit(main())
