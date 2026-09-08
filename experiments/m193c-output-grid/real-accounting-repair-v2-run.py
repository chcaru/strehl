"""Surgical v2 source/evidence split and latest-refusal authority; no new scientific body."""
import time
START=time.monotonic()
import ast,copy,hashlib,json,os,stat,sys,types
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
MIB=1<<20;KIB=1024
BASE_PIN=dict(bytes=29315,sha256="7ca656b0a689116f892e66108cbb8b843c8ab0efcf0bccb89bec8155c5ab724c")
SUPPORT_PIN=dict(bytes=22268,sha256="295e5d5e5289cff1f0657e697016c6c98f657fa14178b20567090ce64d4aaba0")
AUDIT_PIN=dict(bytes=16641,sha256="7a86134c6e2e570194caac609824e8e54f1a86c5c7bff0ad02e1af470aa16447")
AUDIT_OUTER_PIN=dict(bytes=1026,sha256="8c6f40cbe643e8b13c8504eba2874f983c1e16d249bcc69fd38ec5a82727375c")
EMPTY="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
EMPTY_PATHS=("experiments/m193c-output-grid/work/independent-sift-lightglue-real-prefix-audit-stderr.txt",
             "experiments/m193c-output-grid/work/independent-real-accounting-repair-audit-stderr.txt")
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(raw):return dict(bytes=len(raw),sha256=sha(raw))
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def path_of(ref):return (ROOT/ref["path"]).resolve()
def same(a,b):return path_of(a)==path_of(b) and all(a[k]==b[k] for k in ("bytes","sha256"))
def held(path,expected):
    with Path(path).open("rb") as stream:raw=stream.read(expected["bytes"]+1)
    need(pin(raw)==expected,"exact held source buffer");return raw
def module(raw,path,name):
    value=types.ModuleType(name);value.__file__=str(path);sys.modules[name]=value
    exec(compile(raw,str(path),"exec"),value.__dict__);return value

def empty_identity(name,bound):
    need(name in EMPTY_PATHS and type(bound) is dict and set(bound)=={"bytes","sha256"} and type(bound["bytes"]) is int and bound==dict(bytes=0,sha256=EMPTY),"exact allowed empty diagnostic")
    path=ROOT/name
    need(path.relative_to(ROOT).as_posix()==name,"canonical empty diagnostic path")
    for component in (path,*path.parents):
        info=component.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,
             "empty diagnostic lexical reparse")
    before=path.stat(follow_symlinks=False)
    def ident(info):return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,getattr(info,"st_file_attributes",0),info.st_nlink)
    need(stat.S_ISREG(before.st_mode) and before.st_size==0 and before.st_nlink==1,"exact empty diagnostic extent")
    with path.open("rb") as stream:
        opened=os.fstat(stream.fileno());raw=stream.read(1);after_handle=os.fstat(stream.fileno())
    after=path.stat(follow_symlinks=False)
    need(raw==b"" and ident(before)==ident(opened)==ident(after_handle)==ident(after),"same-handle empty diagnostic identity")
    return dict(path=name,bytes=0,sha256=EMPTY,metadata=list(ident(after)))

def namespaces(sources,evidence):
    need(type(sources) is dict and sources,"nonempty positive source namespace")
    for name,bound in sources.items():
        need(type(name) is str and type(bound) is dict and set(bound)=={"bytes","sha256"} and
             type(bound["bytes"]) is int and bound["bytes"]>=1 and type(bound["sha256"]) is str and
             len(bound["sha256"])==64 and all(c in "0123456789abcdef" for c in bound["sha256"]),
             "positive source extent and digest")
    need(type(evidence) is dict and set(evidence)==set(EMPTY_PATHS) and
         all(type(value) is dict and set(value)=={"bytes","sha256"} and type(value["bytes"]) is int and value==dict(bytes=0,sha256=EMPTY) for value in evidence.values()),"closed two-empty diagnostic namespace")
    need(not set(sources)&set(evidence),"source/evidence disjoint")

def source_evidence_controls(n,old,c,files,plan,pub,b,output):
    sources,evidence=plan["source_bindings"],plan["evidence_bindings"]
    namespaces(sources,evidence);n.binding_map(sources,files)
    before=[empty_identity(name,evidence[name]) for name in EMPTY_PATHS]
    unchanged=sha(encoded(dict(sources=sources,evidence=evidence)))
    rows=[dict(id="actual-positive-sources-and-two-empty-evidence",passed=True,
               source_count=len(sources),empty_count=len(before))]
    def rejected(name,operation,expected):
        error=None
        try:operation()
        except ValueError as exc:error=str(exc)
        need(error==expected,"powered namespace refusal: "+name)
        rows.append(dict(id=name,passed=True,error=error))
    # This calls the unchanged production source reader with the actual known
    # empty diagnostic, reproducing the precise failed-run boundary.
    rejected("empty-as-source",lambda:n.binding_map({EMPTY_PATHS[0]:evidence[EMPTY_PATHS[0]]},files),"typed FileRef")
    bad=dict(evidence);bad["experiments/m193c-output-grid/work/unexpected-empty.txt"]=dict(bytes=0,sha256=EMPTY)
    rejected("unexpected-empty-role",lambda:namespaces(sources,bad),"closed two-empty diagnostic namespace")
    rejected("nonzero-diagnostic-declaration",lambda:empty_identity(EMPTY_PATHS[0],dict(bytes=1,sha256=EMPTY)),"exact allowed empty diagnostic")
    rejected("wrong-empty-digest",lambda:empty_identity(EMPTY_PATHS[0],dict(bytes=0,sha256="0"*64)),"exact allowed empty diagnostic")
    bad=dict(evidence);bad[EMPTY_PATHS[0]]=dict(bytes=False,sha256=EMPTY)
    rejected("false-zero-diagnostic",lambda:namespaces(sources,bad),"closed two-empty diagnostic namespace")
    bad_sources=dict(sources);bad_sources[EMPTY_PATHS[0]]=evidence[EMPTY_PATHS[0]]
    rejected("source-intake-zero",lambda:namespaces(bad_sources,evidence),"positive source extent and digest")
    namespaces(sources,evidence)
    # The actual positive entry, not a fabricated subject file, passes the same
    # original reader again after all faults; no source bytes are mutated.
    runner=n.relative(SELF);n.binding_map({runner:sources[runner]},files)
    after=[empty_identity(name,evidence[name]) for name in EMPTY_PATHS]
    need(after==before and sha(encoded(dict(sources=sources,evidence=evidence)))==unchanged,"restored exact namespace/empty identities")
    rows.append(dict(id="restored-positive-placebo",passed=True,namespace_sha256=unchanged))
    original=files.recheck
    def recheck():
        original()
        need([empty_identity(name,evidence[name]) for name in EMPTY_PATHS]==before,"retained empty evidence changed")
    files.recheck=recheck
    value=dict(schema="m193c-positive-source-empty-evidence-controls-v1",status="PASS_METADATA_NAMESPACE_ONLY",
        rows=rows,empty_witnesses=before,source_namespace_sha256=sha(encoded(sources)),
        evidence_namespace_sha256=sha(encoded(evidence)),scope="metadata only; no source/content edits or scientific calls")
    return old.save(pub,b,files,output,"metadata/controller/source-evidence-controls.json",value,cap=4096)

def authority(old,c,n,s,plan,files,grant,output,worker):
    refs=plan["failed_repair_baseline"];n.closed(refs,("plan","result","outer","console","exit","audit"),"failed repair six references")
    need({k:refs["audit"][k] for k in ("bytes","sha256")}==AUDIT_PIN,"actual once-only repair1 audit")
    audit,previous,parent,outer=(c.read(files,refs[k]) for k in ("audit","plan","result","outer"))
    need(audit["schema"]=="m193c-saved-real-accounting-repair-audit-v1" and
         audit["status"]=="PASS_SAVED_REAL_ACCOUNTING_REPAIR_OUTCOME_AUDIT" and
         all(audit[k] is False for k in ("subject_complete","diagnostic_observations_verified",
             "verified_worker_scientific_population","admission_allowed","cpu_accounting_complete")) and
         audit["new_run_cpu_accounting_complete"] is True and audit["worker_result"] is None,
         "failed prelaunch audit with legitimate parent-only accounting; historical gap retained")
    need(set(audit["external"])==set(refs)-{"audit"} and all(same(audit["external"][k],refs[k]) for k in audit["external"]),
         "actual failed repair result/outer/console/exit")
    need(previous["schema"]=="m193c-real-accounting-repair-plan-v1" and parent["status"]=="REFUSED"
         and parent["active_phase"]=="authority" and parent["child_launch_entered"] is False
         and parent["worker_result"] is None and all(v==0 for v in parent["counters"].values())
         and parent["error"]["type"]=="ValueError" and "n.binding_map" in parent["error"]["traceback_suffix"]
         and parent["error"]["traceback_suffix"].endswith("ValueError: typed FileRef\n"),
         "actual zero-science source-namespace failure")
    need(outer["exit_code"]==1 and outer["plan_sha256"]==refs["plan"]["sha256"] and
         outer["command"]==old.command(previous["commands"]["parent"],refs["plan"]["sha256"]) and
         c.checked(files,refs["exit"],64).strip()==b"1","actual refused command and exit")
    c.checked(files,refs["console"],MIB)
    for key in ("private_baseline","failed_real_baseline","callback_baseline"):
        need(plan[key]==previous[key],"unchanged inherited prerequisite bundle")
    old_sources=previous["source_bindings"]
    empties={key:value for key,value in old_sources.items() if value["bytes"]==0}
    need(len(old_sources)==296 and empties=={EMPTY_PATHS[0]:dict(bytes=0,sha256=EMPTY)},"exact one source-namespace defect")
    positives={key:value for key,value in old_sources.items() if value["bytes"]>=1}
    need(len(positives)==295 and all(plan["source_bindings"].get(key)==value for key,value in positives.items()) and
         EMPTY_PATHS[0] not in plan["source_bindings"],"all295 positive bindings preserved without reclassifying sources")
    namespaces(plan["source_bindings"],plan["evidence_bindings"])
    for name,bound in plan["evidence_bindings"].items():empty_identity(name,bound)
    audit_outer_path=HERE/"work/independent-real-accounting-repair-audit-outer.json"
    need(plan["source_bindings"].get(n.relative(audit_outer_path))==AUDIT_OUTER_PIN,"held actual audit1 outer")
    audit_outer=c.read(files,dict(path=n.relative(audit_outer_path),**AUDIT_OUTER_PIN))
    command=[str(path_of(plan["python_executable"])),"-B",str(path_of(audit["audit_source"])),
             "--source-sha256",audit["audit_source"]["sha256"],"--ledger-sha256",audit["audit_family"]["ledger"]["sha256"]]
    for key in ("plan","result","outer","console","exit"):command+=["--"+key+"-sha256",refs[key]["sha256"]]
    need(audit_outer["command"]==command and audit_outer["exit_code"]==0 and
         audit_outer["stdout_bytes"]==refs["audit"]["bytes"] and audit_outer["stderr_bytes"]==0 and
         audit_outer["elapsed_wall_seconds"]<=audit["audit_timing"]["wall_seconds"]+audit["audit_publication_allowance"]["wall_seconds"],
         "actual independently audited refusal publication tail")
    for ref in (audit["audit_source"],audit["audit_family"]["ledger"],audit["audit_progress"]):c.checked(files,ref,MIB)
    # Do not send the known-invalid296-entry source map to the frozen main.
    # Its historical authority takes the EXACT old plan/grant and has no binding_map.
    history=module(held(HERE/"real-accounting-repair-run.py",BASE_PIN),HERE/"real-accounting-repair-run.py","m193c_v2_historical_authority")
    historical_support=module(held(HERE/"real-accounting-repair-support.py",SUPPORT_PIN),HERE/"real-accounting-repair-support.py","m193c_v2_historical_grant")
    oldgrant=c.read(files,previous["resource_authorization"])
    oldoutput=Path(old.command(previous["commands"]["parent"],refs["plan"]["sha256"])[-1])
    saved,pa,private,da,oldprior,older_audit,probe=history.authority(old,c,n,historical_support,previous,files,oldgrant,oldoutput,False)
    n.closed(grant,("schema","status","previous_cumulative_limits","additional_authorized_work","new_cumulative_limits",
        "preparation_allowance","attempt_caps","previous_charged_work","previous_ceiling_disposition","new_output",
        "failed_prefix_audit","callback_result","replacement_sources","failed_repair_audit","evidence_bindings"),"explicit next finite grant")
    need(grant["schema"]=="m193c-real-accounting-repair-resource-authorization-v2" and
         grant["status"]=="AUTHORIZED_SINGLE_FRESH_OPERATIONAL_REPLACEMENT" and
         grant["previous_ceiling_disposition"]=="RETIRED_NOT_RESET" and grant["previous_cumulative_limits"]==s.OLD_GLOBAL==oldgrant["new_cumulative_limits"]
         and grant["additional_authorized_work"]==s.EXTENSION and grant["new_cumulative_limits"]==s.NEW_GLOBAL
         and grant["preparation_allowance"]==ALLOWANCE and grant["attempt_caps"]==s.ATTEMPT,
         "explicit1320-to1440 grant; no retired charge reset or local threshold increase")
    need(same(grant["failed_repair_audit"],refs["audit"]) and same(grant["failed_prefix_audit"],plan["failed_real_baseline"]["audit"])
         and same(grant["callback_result"],plan["callback_baseline"]["result"]) and grant["evidence_bindings"]==plan["evidence_bindings"]
         and Path(grant["new_output"]).resolve()==(output.parent if worker else output),"latest failed attempt and exact output/evidence grant")
    n.closed(grant["replacement_sources"],("runner","support","spec"),"new exact source authorization")
    for key,path in (("runner",SELF),("support",HERE/"real-accounting-repair-v2-support.py"),("spec",HERE/"real-accounting-repair-v2-preregister.md")):
        ref=grant["replacement_sources"][key]
        need(path_of(ref)==path and {k:ref[k] for k in ("bytes","sha256")}==plan["source_bindings"][n.relative(path)],"new replacement pin")
        c.checked(files,ref,MIB)
    base=audit["actual_final_work"];prior=c.read(files,plan["prior_work"])
    c.typed_prior(n,base);c.typed_prior(n,prior)
    need(base==dict(cpu_seconds=1292.771803,wall_seconds=1193.6198098999992,file_bytes=4059662381,metadata_bytes=68401447)
         and grant["previous_charged_work"]==base and Decimal(audit["next_wall_seconds"])==Decimal(str(base["wall_seconds"])),
         "all failed-attempt conservative charges remain")
    for key in ALLOWANCE:
        value=Decimal(str(base[key]))
        if key.endswith("seconds"):value=value.quantize(Decimal(".000001"),rounding=ROUND_CEILING)
        need(Decimal(str(prior[key]))==value+ALLOWANCE[key],"upward microsecond carry plus full preparation")
    need(all(Decimal(str(prior[k]))+s.ATTEMPT[k]<=s.NEW_GLOBAL[k] for k in ALLOWANCE),"entire single attempt fits explicit grant")
    c.checked(files,plan["resource_authorization"],MIB)
    return saved,pa,private,da,prior,audit,probe

def adapted():
    path=HERE/"real-accounting-repair-run.py";raw=held(path,BASE_PIN);tree=ast.parse(raw)
    strings={
        "real-accounting-repair-preregister.md":("real-accounting-repair-v2-preregister.md",1),
        "real-accounting-repair-support.py":("real-accounting-repair-v2-support.py",1),
        "m193c-real-accounting-repair-v1":("m193c-real-accounting-repair-v2",1),
        "m193c-real-accounting-repair-plan-v1":("m193c-real-accounting-repair-plan-v2",1),
        "m193c-real-accounting-repair-request-v1":("m193c-real-accounting-repair-request-v2",2),
        "m193c-real-accounting-repair-worker-v1":("m193c-real-accounting-repair-worker-v2",2),
        "m193c-real-accounting-repair-run-v1":("m193c-real-accounting-repair-run-v2",1),
        "m193c-real-accounting-repair-final-accounting-v1":("m193c-real-accounting-repair-final-accounting-v2",1),
        "m193c-real-accounting-repair-publication-tail-v1":("m193c-real-accounting-repair-publication-tail-v2",1),
        "schema source_bindings private_baseline failed_real_baseline callback_baseline resource_authorization prior_work preparation_allowance python_executable commands":
            ("schema source_bindings private_baseline failed_real_baseline callback_baseline resource_authorization prior_work preparation_allowance python_executable commands failed_repair_baseline evidence_bindings",1)}
    class Adapter(ast.NodeTransformer):
        def __init__(self):self.counts={};self.bindings=0;self.ceilings=0
        def visit_Constant(self,node):
            if type(node.value) is str and node.value in strings:
                self.counts[node.value]=self.counts.get(node.value,0)+1
                return ast.copy_location(ast.Constant(strings[node.value][0]),node)
            return node
        def visit_keyword(self,node):
            if node.arg in ("old_cumulative_cpu_limit","new_cumulative_cpu_limit"):
                need(isinstance(node.value,ast.Constant) and node.value.value=={"old_cumulative_cpu_limit":1200,"new_cumulative_cpu_limit":1320}[node.arg],"fixed reporting ceiling seam")
                self.ceilings+=1;node.value=ast.Constant({"old_cumulative_cpu_limit":1320,"new_cumulative_cpu_limit":1440}[node.arg])
            return self.generic_visit(node)
        def visit_Expr(self,node):
            if ast.dump(node,include_attributes=False)==ast.dump(ast.parse('n.binding_map(plan["source_bindings"],files)').body[0],include_attributes=False):
                self.bindings+=1
                return ast.copy_location(ast.parse('result["source_evidence_controls"]=source_evidence_controls(n,old,c,files,plan,pub,b,output)').body[0],node)
            return self.generic_visit(node)
    change=Adapter();tree=change.visit(tree)
    need(change.counts=={k:v[1] for k,v in strings.items()} and change.bindings==1 and change.ceilings==2,"closed surgical main AST edits")
    value=types.ModuleType("m193c_v2_fixed_main");value.__file__=str(SELF);sys.modules[value.__name__]=value
    exec(compile(ast.fix_missing_locations(tree),str(SELF),"exec"),value.__dict__)
    value.START=START;value.authority=authority;value.source_evidence_controls=source_evidence_controls
    return value

if __name__=="__main__":raise SystemExit(adapted().main())
