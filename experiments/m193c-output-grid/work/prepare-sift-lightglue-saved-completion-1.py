"""Metadata-only fresh plan preparation. No subject import, image/model read or fit."""
from pathlib import Path
from decimal import Decimal,ROUND_CEILING
import argparse
import hashlib
import json
import os
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/"experiments/m193c-output-grid"
SELF=Path(__file__).resolve();START=time.monotonic()
PYTHON=Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=1048576,metadata_bytes=1048576)
SEEN={}
def need(ok,message):
    if not ok:raise ValueError(message)
def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_file_attributes)
def ref(path,sha256=None,empty=False):
    path=(ROOT/path).resolve()
    need(path.is_relative_to(ROOT) or path==PYTHON,"owned metadata or actual Python")
    need(path==PYTHON or path.suffix.lower() in (".json",".lock",".md",".py",".rs",".toml",".tsv",".txt",".log"),"metadata/source-only payload types")
    before=path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and not before.st_file_attributes&0x400 and (0 if empty else 1)<=before.st_size<=32*1048576,"plain bounded metadata file")
    digest=hashlib.sha256();count=0
    with path.open("rb") as stream:
        opened=os.fstat(stream.fileno());need((opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino),"opened metadata identity")
        while data:=stream.read(1048576):
            count+=len(data);need(count<=32*1048576,"file extent grew");digest.update(data)
    need(identity(path.stat(follow_symlinks=False))==identity(before) and count==before.st_size,"same immutable metadata file")
    value=dict(path=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),bytes=count,sha256=digest.hexdigest())
    need(sha256 is None or value["sha256"]==sha256,"root released metadata digest")
    need(SEEN.setdefault(str(path),(value,identity(before)))==(value,identity(before)),"same repeated metadata")
    return value
def raw(ref_):
    data=(ROOT/ref_["path"]).read_bytes()
    need(len(data)==ref_["bytes"] and hashlib.sha256(data).hexdigest()==ref_["sha256"],"same-byte released record")
    return data
def read(path,sha256=None):
    value=ref(path,sha256);need(value["bytes"]<=4*1048576,"bounded JSON metadata")
    return value,json.loads(raw(value))
def same(a,b):
    return (ROOT/a["path"]).resolve()==(ROOT/b["path"]).resolve() and all(a[k]==b[k] for k in ("bytes","sha256"))
def checked(value):
    actual=ref(value["path"],value["sha256"]);need(actual["bytes"]==value["bytes"],"root extent");return actual
def encoded(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def create(path,data):
    need(not path.exists() and path.parent.is_dir(),"fresh metadata destination")
    with path.open("xb") as stream:
        need(stream.write(data)==len(data),"complete metadata write");stream.flush();os.fsync(stream.fileno())
    value=ref(path);need(value["bytes"]==len(data) and value["sha256"]==hashlib.sha256(data).hexdigest(),"metadata readback")
    return value

p=argparse.ArgumentParser()
p.add_argument("--audit",nargs=2,required=True);p.add_argument("--audit-outer",nargs=2,required=True);p.add_argument("--audit-stderr",nargs=2,required=True)
p.add_argument("--source",nargs=2,action="append",required=True)
args=p.parse_args()
need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON,"actual metadata-only Python/cwd")
planpath=HERE/"sift-lightglue-saved-completion-plan-1.json"
priorpath=HERE/"work/sift-lightglue-saved-completion-prior-work-1.json"
output=HERE/"sift-lightglue-saved-completion-1"
need(not planpath.exists() and not priorpath.exists() and not output.exists(),"fresh attempt only")
auditref,audit=read(*args.audit);outerref,auditouter=read(*args.audit_outer);stderrref=ref(*args.audit_stderr,empty=True)
need(audit["schema"]=="m193c-saved-sift-lightglue-commission-prefix-audit-v3" and
     audit["status"]=="PASS_SAVED_SIFT_LIGHTGLUE_COMMISSION_PREFIX_AUDIT" and
     audit["saved_prefix_verified"] is True and audit["subject_complete"] is False and
     audit["admission_allowed"] is False and audit["cpu_accounting_complete"] is False and audit["parent_result_missing"] is True,
     "exact independently eligible failed prefix, never ordinary complete admission")
need(audit["cpu_reservation_seconds"]==300 and audit["missing_parent_publication_cpu_allowance_seconds"]==2,"accepted conservative CPU policy")
need(set(audit["external"])==set("plan worker_result outer console exit".split()),"five exact surviving refs")
prefix={key:checked(value) for key,value in audit["external"].items()};prefix["audit"]=auditref
oldref,old=read(prefix["plan"]["path"],prefix["plan"]["sha256"])
workerref,worker=read(prefix["worker_result"]["path"],prefix["worker_result"]["sha256"])
need(same(workerref,audit["worker_result"]) and old["schema"]=="m193c-sift-lightglue-commission-plan-v1" and
     worker["status"]=="REFUSED" and worker["assembly"] is None and worker["counters"]["registrar_calls"]==0,"actual untouched stopped commission")
missing=(ROOT/prefix["worker_result"]["path"]).parent.parent/"result.json"
need(Path(audit["parent_result_expected_path"]).resolve()==missing.resolve() and not missing.exists(),"actual missing parent receipt")
_,oldouter=read(prefix["outer"]["path"],prefix["outer"]["sha256"])
need(oldouter["exit_code"]==1 and oldouter["plan_sha256"]==prefix["plan"]["sha256"] and raw(prefix["exit"]).strip()==b"1","actual old failed outer and exit")
audit_source=checked(audit["audit_source"]);python=checked(old["python_executable"])
need((ROOT/python["path"]).resolve()==PYTHON,"inherited actual Python")
audit_command=[str(PYTHON),"-B",str((ROOT/audit_source["path"]).resolve())]
for key in ("plan","worker_result","outer","console","exit"):
    audit_command.extend(["--"+key.replace("_","-")+"-sha256",prefix[key]["sha256"]])
need(auditouter["command"]==audit_command and auditouter["exit_code"]==0 and
     auditouter["stderr_bytes"]==stderrref["bytes"]==0 and auditouter["stdout_bytes"]==auditref["bytes"],
     "actual successful prefix audit launcher/output/empty stderr")
need(auditouter["elapsed_wall_seconds"]<=audit["audit_timing"]["wall_seconds"]+audit["audit_publication_allowance"]["wall_seconds"],
     "audit final publication fits charged tail")
base=dict(audit["actual_final_work"]);need(set(base)==set(ALLOWANCE),"four conservative charged work fields")
need(all(type(base[k]) in (int,float) and Decimal(str(base[k])).is_finite() and base[k]>=0 for k in ("cpu_seconds","wall_seconds")) and
     all(type(base[k]) is int and base[k]>=0 for k in ("file_bytes","metadata_bytes")),"finite nonnegative typed carry")
next_wall=Decimal(audit["next_wall_seconds"])
need(next_wall.is_finite() and next_wall>=0 and next_wall==Decimal(str(base["wall_seconds"])),"audit wall string agrees with charged work")
for key in ("cpu_seconds","wall_seconds"):base[key]=Decimal(str(base[key])).quantize(Decimal(".000001"),rounding=ROUND_CEILING)
prior={k:float(Decimal(str(base[k]))+ALLOWANCE[k]) if k.endswith("seconds") else base[k]+ALLOWANCE[k] for k in ALLOWANCE}
need(all(Decimal(str(prior[k]))==Decimal(str(base[k]))+ALLOWANCE[k] for k in ALLOWANCE),"exact representable carried charge plus prep")
need(prior["cpu_seconds"]+60<=1200 and prior["wall_seconds"]+120<=1800 and
     prior["file_bytes"]+8*1048576<=4<<30 and prior["metadata_bytes"]+8*1048576<=128*1048576,
     "full tighter attempt fits remaining global envelope before release")
priorraw=encoded(prior);priorref=dict(path=priorpath.relative_to(ROOT).as_posix(),bytes=len(priorraw),sha256=hashlib.sha256(priorraw).hexdigest())
sources=dict(old["source_bindings"])
for name,pin in [*args.source,(str(SELF),None),(audit_source["path"],audit_source["sha256"]),(outerref["path"],outerref["sha256"])]:
    value=ref(name,pin);binding={k:value[k] for k in ("bytes","sha256")}
    need(sources.setdefault(value["path"],binding)==binding,"never modify an old source binding")
required=("sift-lightglue-saved-completion-run.py","saved-completion-publication.py","sift-lightglue-saved-completion-preregister.md",
          "work/independent-sift-lightglue-saved-completion-source-review.md","work/independent-sift-lightglue-saved-completion-audit.py",
          "work/independent-sift-lightglue-saved-completion-plan-preparation-read.md")
need(all((HERE/name).relative_to(ROOT).as_posix() in sources for name in required),"new source/review/auditor closure")
for name,pin in sources.items():
    actual=ref(name,pin["sha256"]);need(actual["bytes"]==pin["bytes"],"entire inherited/new source closure")
base_command=[str(PYTHON),"-B","-X","faulthandler","-X"]
script=str(HERE/"sift-lightglue-saved-completion-run.py")
parent=base_command+["pycache_prefix="+str(output/"parent-cache"),script,"--plan",str(planpath),"--sha256","ACTUAL_PLAN_SHA256","--output",str(output)]
worker_command=base_command+["pycache_prefix="+str(output/"worker-cache"),script,"--plan",str(planpath),"--sha256","ACTUAL_PLAN_SHA256",
                           "--output",str(output/"worker"),"--worker","--request",str(output/"request.json"),"--request-sha256","ACTUAL_REQUEST_SHA256"]
plan=dict(schema="m193c-sift-lightglue-saved-completion-plan-v1",source_bindings=sources,commission_prefix=prefix,prior_work=priorref,
          preparation_allowance=ALLOWANCE,python_executable=python,commands=dict(parent=parent,worker=worker_command))
planraw=encoded(plan);need(len(planraw)<=256*1024 and len(priorraw)<=4096,"compact metadata plan")
for path,(value,before) in SEEN.items():need(identity(Path(path).stat(follow_symlinks=False))==before,"pre-write metadata unchanged")
need(time.monotonic()-START<30 and time.process_time()<20,"bounded metadata preparation")
need(create(priorpath,priorraw)==priorref,"actual prior file")
planref=create(planpath,planraw)
print(json.dumps(dict(status="PREPARED_METADATA_AND_OPAQUE_HASHES_ONLY",plan=planref,prior_work=priorref,source_count=len(sources),
    checked_metadata_files=len(SEEN),image_payloads_opened=0,checkpoint_reads=0,model_imports=0,registrar_calls=0,
    prior_accounting_scope="conservative audited reservation, not complete measured CPU"),allow_nan=False))
