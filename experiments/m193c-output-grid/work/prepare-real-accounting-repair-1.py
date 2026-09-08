"""Metadata-only preparation of one explicit operational replacement; no scientific imports."""
from pathlib import Path
from decimal import Decimal,ROUND_CEILING
import argparse
import hashlib
import json
import os
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/"experiments/m193c-output-grid";SELF=Path(__file__).resolve()
START=time.monotonic();PYTHON=Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=1048576,metadata_bytes=1048576)
CAPS=dict(cpu_seconds=100,wall_seconds=180,file_bytes=8*1048576,metadata_bytes=8*1048576)
COUNTS=(487,1024,1024,1024,1024,1024,1024,910,734);SEEN={}
def need(ok,message):
    if not ok:raise ValueError(message)
def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_file_attributes)
def strict(data):
    def object_(items):
        result={}
        for key,value in items:
            need(key not in result,"duplicate JSON key");result[key]=value
        return result
    def bad(value):raise ValueError("nonfinite JSON constant")
    return json.loads(data,object_pairs_hook=object_,parse_constant=bad)
def ref(path,sha256=None,empty=False):
    path=(ROOT/path).resolve()
    need(path.is_relative_to(ROOT) or path==PYTHON,"owned metadata or exact Python")
    need(path==PYTHON or path.suffix.lower() in (".json",".lock",".md",".py",".rs",".toml",".tsv",".txt",".log"),"no images/model/runtime libraries")
    before=path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and not before.st_file_attributes&0x400 and (0 if empty else 1)<=before.st_size<=32*1048576,"bounded regular metadata")
    digest=hashlib.sha256();count=0
    with path.open("rb") as stream:
        opened=os.fstat(stream.fileno());need((opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino),"opened metadata identity")
        while data:=stream.read(1048576):
            count+=len(data);need(count<=32*1048576,"bounded complete metadata");digest.update(data)
    need(identity(path.stat(follow_symlinks=False))==identity(before) and count==before.st_size,"stable metadata read")
    value=dict(path=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),bytes=count,sha256=digest.hexdigest())
    need(sha256 is None or value["sha256"]==sha256,"released exact digest")
    need(SEEN.setdefault(str(path),(value,identity(before)))==(value,identity(before)),"same repeated metadata identity")
    return value
def checked(value):
    actual=ref(value["path"],value["sha256"]);need(actual["bytes"]==value["bytes"],"released exact extent");return actual
def raw(value):
    path=ROOT/value["path"]
    with path.open("rb") as stream:data=stream.read(value["bytes"]+1)
    need(len(data)==value["bytes"] and hashlib.sha256(data).hexdigest()==value["sha256"],"same held metadata bytes")
    return data
def read(path,digest=None):
    value=ref(path,digest);need(value["bytes"]<=4*1048576,"bounded JSON");return value,strict(raw(value))
def same(a,b):return (ROOT/a["path"]).resolve()==(ROOT/b["path"]).resolve() and all(a[k]==b[k] for k in ("bytes","sha256"))
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def create(path,data):
    need(not path.exists() and path.parent.is_dir(),"fresh metadata destination")
    with path.open("xb") as stream:
        need(stream.write(data)==len(data),"complete metadata write");stream.flush();os.fsync(stream.fileno())
    value=ref(path);need(value["bytes"]==len(data) and value["sha256"]==hashlib.sha256(data).hexdigest(),"actual metadata readback");return value


p=argparse.ArgumentParser()
p.add_argument("--source",nargs=2,action="append",required=True)
args=p.parse_args()
need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON,"actual metadata Python/cwd")
planpath=HERE/"real-accounting-repair-plan-1.json"
priorpath=HERE/"work/real-accounting-repair-prior-work-1.json"
grantpath=HERE/"work/real-accounting-repair-resource-authorization-1.json"
output=HERE/"real-accounting-repair-1"
need(all(not x.exists() for x in (planpath,priorpath,grantpath,output)),"one fresh operational replacement")
oldref,oldplan=read(HERE/"sift-lightglue-real-plan-1.json","63de01efe856d3760ea3b0b5d15ac056a3ec2e868fdd74eb908e3df616174184")
need(set(oldplan)=={"schema","source_bindings","private_baseline","prior_work","preparation_allowance","python_executable","commands"},"closed frozen predecessor plan")
# These immutable observations, not rerun subjects, define this release.
ar,audit=read(HERE/"work/independent-sift-lightglue-real-prefix-audit.json","4f8b48d9edf19fdac45c38aaf3bab85364e853a721827d4415d4d7dcb91cc66f")
or_,outer=read(HERE/"work/independent-sift-lightglue-real-prefix-audit-outer.json","4e84cbca51eed44567bb043f7b078d4388a924a15e38f58d1a4de2de1cf93c0d")
er=ref(HERE/"work/independent-sift-lightglue-real-prefix-audit-stderr.txt","e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",empty=True)
need(audit["schema"]=="m193c-saved-sift-lightglue-real-prefix-audit-v1" and
     audit["status"]=="PASS_SAVED_REAL_LIGHTGLUE_METADATA_PREFIX_AUDIT" and audit["saved_metadata_prefix_verified"] is True,"actual narrow prefix PASS")
need(all(audit[k] is False for k in ("subject_complete","admission_allowed","cpu_accounting_complete","new_run_cpu_accounting_complete",
     "model_runtime_verified","model_state_verified","guard_restoration_verified","scientific_call_counters_retained","diagnostic_observations_verified")) and
     audit["scientific_call_counts"] is None and audit["real_pair_observations"]==0,"failed scientific scope remains unchanged")
need(set(audit["external"])=={"plan","result","outer","console","exit"},"closed failed subject refs")
failed={k:checked(v) for k,v in audit["external"].items()};failed["audit"]=ar
need(same(failed["plan"],oldref),"same frozen failed subject")
asource=checked(audit["audit_source"]);aledger=checked(audit["audit_family"]["ledger"])
argv=[str(PYTHON),"-B",str((ROOT/asource["path"]).resolve()),"--source-sha256",asource["sha256"],"--ledger-sha256",aledger["sha256"]]
for k in ("plan","result","outer","console","exit"):argv += ["--"+k+"-sha256",failed[k]["sha256"]]
need(outer["command"]==argv and outer["exit_code"]==0 and outer["stdout_bytes"]==ar["bytes"] and outer["stderr_bytes"]==er["bytes"]==0,"actual prefix command/exit/output")
need(outer["elapsed_wall_seconds"]<=audit["audit_timing"]["wall_seconds"]+audit["audit_publication_allowance"]["wall_seconds"],"actual prefix publication within charged tail")
progress=checked(audit["progress"])
cb={}
fixed={
 "source":("accounting-callback-comparison.py","aaa98419c7141eba44be2e0df746d26a36938f9232e85e2075aba6bdb9a52cfe"),
 "protocol":("accounting-callback-preregister.md","2b889ac71635cb4393a82845692ccae8691d7faf2018dc59440bf84a01bfe1d2"),
 "review":("independent-accounting-callback-source-review.md","1d95cc56a9dc35e26b5cb2faace8f0676deb9d483d2c2be8723e0cf5c5c8da4e"),
 "result":("accounting-callback-comparison-1/result.json","b42293535eed7fcd9545a451804da23fcfa6d7735d0639f10b92e7a06c899bb0")}
for key,(path,digest) in fixed.items():cb[key]=ref(HERE/"work"/path,digest)
for key in ("outer","console","exit"):cb[key]=ref(HERE/"work"/("accounting-callback-comparison-1-"+key+(".json" if key=="outer" else ".txt")))
result=strict(raw(cb["result"]));cout=strict(raw(cb["outer"]));console=strict(raw(cb["console"]))
need(result["schema"]=="m193c-accounting-callback-comparison-v1" and result["status"]=="PASS_CALLBACK_EQUIVALENCE_AND_POWER_ONLY" and result["sources_unchanged"] is True and result["error"] is None and result["scientific_calls"]==0,"actual bounded callback-only PASS")
need(len(result["cases"])==13 and len({v["id"] for v in result["cases"]})==13 and all(v["passed"] is True and v["whole_intrinsic_equal"] is True and v["old_sha256"]==v["candidate_sha256"] for v in result["cases"]),"thirteen retained intrinsic comparison cases")
need(len(result["owned_source_bindings"])==3 and all(same(actual,cb[key]) for actual,key in zip(result["owned_source_bindings"],("source","protocol","review"))),"actual probe owned-source bindings")
# Explicit grouping: do not hide a command assertion behind a conditional expression.
need(cout["command"]==[str(PYTHON),"-B",str((ROOT/cb["source"]["path"]).resolve()),"--output",str((HERE/"work/accounting-callback-comparison-1").resolve())] and cout["exit_code"]==0 and raw(cb["exit"]).strip()==b"0","callback actual command/exit")
need(console["status"]==result["status"] and Path(console["path"]).resolve()==(ROOT/cb["result"]["path"]).resolve() and console["sha256"]==cb["result"]["sha256"],"callback actual console/result association")
need(cout["elapsed_wall_seconds"]<=20 and result["actual_controller_work"]["cpu_seconds"]<=10,"callback fits full already charged reservation")
need(audit["other_work_reserved"]["cpu_seconds"]==10 and audit["other_work_reserved"]["wall_seconds"]==20,"probe not charged twice or refunded")
base=dict(audit["actual_final_work"])
need(base==dict(cpu_seconds=1170.209303,wall_seconds=1162.3484670000043,file_bytes=4058327085,metadata_bytes=67066151),"exact independently accepted conservative carry")
need(Decimal(audit["next_wall_seconds"])==Decimal(str(base["wall_seconds"])),"exact next-wall carry")
prior={k:float(Decimal(str(base[k])).quantize(Decimal(".000001"),rounding=ROUND_CEILING)+ALLOWANCE[k]) if k.endswith("seconds") else base[k]+ALLOWANCE[k] for k in ALLOWANCE}
oldlimits=dict(cpu_seconds=1200,wall_seconds=1800,file_bytes=4<<30,metadata_bytes=128*1048576)
newlimits=dict(oldlimits,cpu_seconds=1320)
need(prior["cpu_seconds"]+CAPS["cpu_seconds"]>oldlimits["cpu_seconds"] and all(prior[k]+CAPS[k]<=newlimits[k] for k in CAPS),"explicit finite extension needed and complete new attempt affordable")
sources=dict(oldplan["source_bindings"])
extra=[ar,or_,er,asource,aledger,progress,*cb.values()]
for path,digest in [*args.source,(str(SELF),None),*[(v["path"],v["sha256"]) for v in extra]]:
    value=ref(path,digest,empty=True);binding={k:value[k] for k in ("bytes","sha256")}
    need(sources.setdefault(value["path"],binding)==binding,"predecessor sources immutable")
replacement={}
for key,name in (("runner","real-accounting-repair-run.py"),("support","real-accounting-repair-support.py"),("spec","real-accounting-repair-preregister.md")):
    keypath=(HERE/name).relative_to(ROOT).as_posix();need(keypath in sources,"reviewed replacement source supplied")
    replacement[key]=dict(path=keypath,**sources[keypath])
for name in ("work/independent-real-accounting-repair-source-review.md","work/independent-real-accounting-repair-preparation-review.md"):
    need((HERE/name).relative_to(ROOT).as_posix() in sources,"independent source/preparation reviews supplied")
for name,expected in sources.items():
    actual=ref(name,expected["sha256"],empty=True);need(actual["bytes"]==expected["bytes"],"all old/new source extents exact")
python=checked(oldplan["python_executable"])
need((ROOT/python["path"]).resolve()==PYTHON,"exact inherited Python")
grant=dict(schema="m193c-real-accounting-repair-resource-authorization-v1",status="AUTHORIZED_SINGLE_FRESH_OPERATIONAL_REPLACEMENT",
    previous_cumulative_limits=oldlimits,additional_authorized_work=dict(cpu_seconds=120,wall_seconds=0,file_bytes=0,metadata_bytes=0),
    new_cumulative_limits=newlimits,preparation_allowance=ALLOWANCE,attempt_caps=CAPS,previous_charged_work=base,
    previous_ceiling_disposition="RETIRED_NOT_RESET",new_output=output.relative_to(ROOT).as_posix(),failed_prefix_audit=ar,callback_result=cb["result"],replacement_sources=replacement)
def predicted(path,data):return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
grantraw=encoded(grant);grantref=predicted(grantpath,grantraw);priorraw=encoded(prior);priorref=predicted(priorpath,priorraw)
script=str(HERE/"real-accounting-repair-run.py");prefix_command=[str(PYTHON),"-B","-X","faulthandler","-X"]
parent_command=prefix_command+["pycache_prefix="+str(output/"parent-cache"),script,"--plan",str(planpath),"--sha256","ACTUAL_PLAN_SHA256","--output",str(output)]
worker_command=prefix_command+["pycache_prefix="+str(output/"worker-cache"),script,"--plan",str(planpath),"--sha256","ACTUAL_PLAN_SHA256","--output",str(output/"worker"),"--worker","--request",str(output/"request.json"),"--request-sha256","ACTUAL_REQUEST_SHA256"]
plan=dict(schema="m193c-real-accounting-repair-plan-v1",source_bindings=sources,private_baseline=oldplan["private_baseline"],prior_work=priorref,
    preparation_allowance=ALLOWANCE,python_executable=python,commands=dict(parent=parent_command,worker=worker_command),
    failed_real_baseline=failed,callback_baseline=cb,resource_authorization=grantref)
planraw=encoded(plan);need(len(planraw)<=256*1024 and len(priorraw)<=4096 and len(grantraw)<=16384,"bounded fresh release metadata")
# Conservative capacity, not write traffic: old already-held evidence added to
# this closure is charged again here rather than silently omitted.
new_sources={name:value["bytes"] for name,value in sources.items() if name not in oldplan["source_bindings"]}
preparation_ledger=dict(newly_bound_source_and_metadata_bytes=sum(new_sources.values()),
    plan_capacity=256*1024,prior_capacity=4096,authorization_capacity=16384,
    outer_console_exit_capacity=8192,continuation_capacity=16384,
    prospective_independent_audit_family_capacity=384*1024)
need(sum(preparation_ledger.values())<=ALLOWANCE["file_bytes"]==ALLOWANCE["metadata_bytes"],
    "complete preparation sources/reviews/releases/outer/future-audit capacity")
for path,(value,before) in SEEN.items():need(identity(Path(path).stat(follow_symlinks=False))==before,"all metadata stable before release")
need(time.monotonic()-START<30 and time.process_time()<20,"fixed metadata preparation allowance")
need(create(grantpath,grantraw)==grantref and create(priorpath,priorraw)==priorref,"actual authority/prior bytes")
planref=create(planpath,planraw)
finished_work=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
need(finished_work["cpu_seconds"]<20 and finished_work["wall_seconds"]<30,"actual complete preparation before stdout")
print(json.dumps(dict(status="PREPARED_SINGLE_OPERATIONAL_REPLACEMENT_METADATA_ONLY",plan=planref,prior_work=priorref,resource_authorization=grantref,
    preparation_capacity_ledger=preparation_ledger,preparation_capacity_bytes=sum(preparation_ledger.values()),
    sampled_preparation_work=finished_work,source_count=len(sources),checked_metadata_files=len(SEEN),images_opened=0,feature_payloads_opened=0,checkpoint_reads=0,model_imports=0,registrar_calls=0,
    prior_accounting_scope="conservative audited charges retained; explicit120CPU extension beyond retired1200; historicalCPU incomplete"),allow_nan=False))
