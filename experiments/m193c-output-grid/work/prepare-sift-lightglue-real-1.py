"""Metadata-only conditional real-arm preparation. Never import a scientific subject."""
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
for prefix in ("prefix","completion"):
    for part in ("audit","outer","stderr"):p.add_argument("--"+prefix+"-"+part,nargs=2,required=True)
p.add_argument("--source",nargs=2,action="append",required=True);args=p.parse_args()
need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON,"actual metadata Python/cwd")
planpath=HERE/"sift-lightglue-real-plan-1.json";priorpath=HERE/"work/sift-lightglue-real-prior-work-1.json";output=HERE/"sift-lightglue-real-1"
need(not planpath.exists() and not priorpath.exists() and not output.exists(),"fresh conditional attempt")
audits={};bundles={};outerrefs=[];audit_sources=[]
for prefix in ("prefix","completion"):
    auditref,audit=read(*getattr(args,prefix+"_audit"));outerref,outer=read(*getattr(args,prefix+"_outer"))
    stderr=ref(*getattr(args,prefix+"_stderr"),empty=True)
    fields=("plan","worker_result","outer","console","exit") if prefix=="prefix" else ("plan","result","outer","console","exit")
    need(set(audit["external"])==set(fields),"closed actual audited inputs")
    refs={key:checked(value) for key,value in audit["external"].items()};refs["audit"]=auditref
    source=checked(audit["audit_source"]);argv=[str(PYTHON),"-B",str((ROOT/source["path"]).resolve())]
    for key in fields:argv+=["--"+key.replace("_","-")+"-sha256",refs[key]["sha256"]]
    need(outer["command"]==argv and outer["exit_code"]==0 and outer["stderr_bytes"]==stderr["bytes"]==0 and
         outer["stdout_bytes"]==auditref["bytes"],"actual audited output/outer/empty stderr association")
    need(outer["elapsed_wall_seconds"]<=audit["audit_timing"]["wall_seconds"]+audit["audit_publication_allowance"]["wall_seconds"],
         "audit publication tail within charged work")
    audits[prefix]=audit;bundles["commission_prefix" if prefix=="prefix" else "saved_completion"]=refs
    outerrefs.append(outerref);audit_sources.append(source)
prefix=audits["prefix"];done=audits["completion"]
need(prefix["schema"]=="m193c-saved-sift-lightglue-commission-prefix-audit-v3" and
     prefix["status"]=="PASS_SAVED_SIFT_LIGHTGLUE_COMMISSION_PREFIX_AUDIT" and prefix["saved_prefix_verified"] is True and
     all(prefix[k] is False for k in ("subject_complete","admission_allowed","cpu_accounting_complete")),"eligible retained prefix only")
need(done["schema"]=="m193c-saved-sift-lightglue-saved-completion-audit-v2" and
     done["status"]=="PASS_SAVED_PRIVATE_LIGHTGLUE_COMPLETION_OUTCOME_AUDIT" and done["audit_version"]=="v2-one-runtime-conjunct" and
     all(done[k] is True for k in ("subject_complete","combined_private_prerequisite_eligible","new_run_cpu_accounting_complete")) and
     all(done[k] is False for k in ("admission_allowed","cpu_accounting_complete","original_commission_complete")) and
     done["refused_control"] is None and done["old_run_status"]=="REFUSED","actual independent private checks passed")
prefixrefs=bundles["commission_prefix"];donerefs=bundles["saved_completion"]
_,oldplan=read(prefixrefs["plan"]["path"],prefixrefs["plan"]["sha256"])
_,old=read(prefixrefs["worker_result"]["path"],prefixrefs["worker_result"]["sha256"])
_,doneplan=read(donerefs["plan"]["path"],donerefs["plan"]["sha256"])
_,parent=read(donerefs["result"]["path"],donerefs["result"]["sha256"])
need(all(same(done["commission_prefix"][k],prefixrefs[k]) and same(doneplan["commission_prefix"][k],prefixrefs[k]) for k in prefixrefs),
     "same two-part private prerequisite")
need(old["status"]=="REFUSED" and old["counters"]["registrar_calls"]==0 and len(old["exports"])==11 and
     parent["status"]=="COMPLETE_SAVED_PRIVATE_LIGHTGLUE_CHECKS_ONLY" and parent["new_run_cpu_accounting_complete"] is True and
     parent["cpu_accounting_complete"] is False and same(parent["worker_result"],done["worker_result"]),"actual separately completed private attempt")
workerref=checked(done["worker_result"]);worker=strict(raw(workerref))
need(worker["counters"]==dict(images=0,extractions=0,normalizations=0,model_forwards=0,registrar_calls=5) and
     all(row["passed"] is True for row in worker["controls"]) and len(worker["controls"])==5,"fixed five private fits")
for ordinal,value in enumerate(old["exports"]):
    export=checked(value);record=strict(raw(export));expected=1024 if ordinal<2 else COUNTS[ordinal-2]
    need(record["core"]["count"]==expected and record["descriptors"]["shape"]==[expected,128],"actual exact-count storage population")
    # Export metadata only here; no u8/key/f32 payload or runtime/checkpoint is opened by preparation.
need(sum(COUNTS)*128*4==4236800 and sum((204,64,64,208,24,12))*1024==589824,"exact metadata and normalization byte ledger")
base=dict(done["actual_final_work"]);need(set(base)==set(ALLOWANCE),"closed conservative work")
need(all(type(base[k]) in (int,float) and Decimal(str(base[k])).is_finite() and base[k]>=0 for k in ("cpu_seconds","wall_seconds")) and
     all(type(base[k]) is int and base[k]>=0 for k in ("file_bytes","metadata_bytes")),"finite nonnegative work fields")
need(Decimal(done["next_wall_seconds"])==Decimal(str(base["wall_seconds"])),"exact audit next-wall agreement")
for key in ("cpu_seconds","wall_seconds"):base[key]=Decimal(str(base[key])).quantize(Decimal(".000001"),rounding=ROUND_CEILING)
prior={k:float(Decimal(str(base[k]))+ALLOWANCE[k]) if k.endswith("seconds") else base[k]+ALLOWANCE[k] for k in ALLOWANCE}
need(all(Decimal(str(prior[k]))==Decimal(str(base[k]))+ALLOWANCE[k] for k in ALLOWANCE),"no downward binary-roundtrip carry")
need(all(prior[k]+CAPS[k]<=limit for k,limit in dict(cpu_seconds=1200,wall_seconds=1800,file_bytes=4<<30,metadata_bytes=128*1048576).items()),
     "entire fixed100CPU/180wall/8MiB arm affordable before preparation")
sources=dict(doneplan["source_bindings"])
need(all(sources.get(k)==v for k,v in oldplan["source_bindings"].items()),"entire historical closure preserved")
for name,digest in [*args.source,(str(SELF),None),*[(ref_["path"],ref_["sha256"]) for ref_ in outerrefs+audit_sources]]:
    value=ref(name,digest);binding={k:value[k] for k in ("bytes","sha256")}
    need(sources.setdefault(value["path"],binding)==binding,"old source binding cannot change")
required=("sift-lightglue-real-run.py","sift-lightglue-real-codec.py","sift-lightglue-real-preregister.md",
          "work/sift-lightglue-real-arm-design.md","work/sift-lightglue-real-arm-design-v2.md",
          "work/independent-sift-lightglue-real-source-review.md","work/independent-sift-lightglue-real-plan-preparation-read.md",
          "work/independent-sift-lightglue-real-audit.py","work/independent-sift-lightglue-real-auditor-source-read.md")
need(all((HERE/name).relative_to(ROOT).as_posix() in sources for name in required),"held new source and independent review closure")
for name,expected in sources.items():
    actual=ref(name,expected["sha256"]);need(actual["bytes"]==expected["bytes"],"all old/new sources exact")
python=checked(doneplan["python_executable"]);need((ROOT/python["path"]).resolve()==PYTHON,"inherited actual Python")
priorraw=encoded(prior);priorref=dict(path=priorpath.relative_to(ROOT).as_posix(),bytes=len(priorraw),sha256=hashlib.sha256(priorraw).hexdigest())
prefix_command=[str(PYTHON),"-B","-X","faulthandler","-X"];script=str(HERE/"sift-lightglue-real-run.py")
parent_command=prefix_command+["pycache_prefix="+str(output/"parent-cache"),script,"--plan",str(planpath),
                              "--sha256","ACTUAL_PLAN_SHA256","--output",str(output)]
worker_command=prefix_command+["pycache_prefix="+str(output/"worker-cache"),script,"--plan",str(planpath),
    "--sha256","ACTUAL_PLAN_SHA256","--output",str(output/"worker"),"--worker","--request",str(output/"request.json"),
    "--request-sha256","ACTUAL_REQUEST_SHA256"]
plan=dict(schema="m193c-sift-lightglue-real-plan-v1",source_bindings=sources,private_baseline=bundles,
          prior_work=priorref,preparation_allowance=ALLOWANCE,python_executable=python,commands=dict(parent=parent_command,worker=worker_command))
planraw=encoded(plan);need(len(planraw)<=256*1024 and len(priorraw)<=4096,"bounded metadata outputs")
for path,(value,before) in SEEN.items():need(identity(Path(path).stat(follow_symlinks=False))==before,"all metadata unchanged before write")
need(time.monotonic()-START<30 and time.process_time()<20,"fixed metadata preparation allowance")
need(create(priorpath,priorraw)==priorref,"actual prior identity");planref=create(planpath,planraw)
print(json.dumps(dict(status="PREPARED_CONDITIONAL_REAL_METADATA_ONLY",plan=planref,prior_work=priorref,source_count=len(sources),
    checked_metadata_files=len(SEEN),images_opened=0,feature_payloads_opened=0,checkpoint_reads=0,model_imports=0,registrar_calls=0,
    prior_accounting_scope="conservative audited charges; original commission REFUSED and historical CPU incomplete"),allow_nan=False))
