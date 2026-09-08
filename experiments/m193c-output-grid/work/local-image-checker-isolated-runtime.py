"""SOURCE-ONLY CANDIDATE: isolated, no-data NumPy import registry capture.
Run only after independent review and exact grant release. No subject import.
"""
import time
START = time.monotonic()
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys
import traceback
import types

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "experiments/m193c-output-grid/work"
SELF = Path(__file__).resolve()
PYTHON = Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
PYROOT = PYTHON.parent
PACKAGE = PYROOT / "Lib/site-packages"
KIB = 1024
MIB = 1 << 20
SCHEMA = "m193c-isolated-numpy-import-capture-v1"
STATUS = "COMPLETE_NO_DATA_IMPORT_CAPTURE_ONLY"
FINAL = WORK / "local-image-checker-import-capture-1.json"
PROGRESS = WORK / "local-image-checker-import-capture-1-progress.json"
STAGE = WORK / "local-image-checker-import-capture-1-stage.json"
GRANT = WORK / "local-image-checker-import-capture-grant-1.json"
EMPTY = hashlib.sha256(b"").hexdigest()
PLAN = dict(path="experiments/m193c-output-grid/local-image-probe-plan-1.json",
            bytes=476283, sha256="337ee76493feb15f14982d14fdb6b6148bc76ba108a9c0d77ba51ca25a6e66c1")
FAILED = {
 "result": (".json",168790,"9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f"),
 "outer": ("-outer.json",2138,"bb583734d952afe54e225bc14c225ac30a7bb8f9944cfc6843eb6ef42a4ed684"),
 "stdout": ("-stdout.bin",168790,"9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f"),
 "stderr": ("-stderr.bin",0,EMPTY),
 "exit": ("-exit.txt",2,"4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865")}
PRIOR = dict(cpu_seconds=1588.443678,wall_seconds=1601.9278447999966,
             file_bytes=4140565273,metadata_bytes=149304339)
CAPS = dict(cpu_seconds=1660,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=168*MIB)
def allowance(cpu,wall,mib):
 return dict(cpu_seconds=cpu,wall_seconds=wall,file_bytes=mib*MIB,metadata_bytes=mib*MIB)
RESOURCES = dict(preparation_before_capture=allowance(5,10,1),capture=allowance(15,25,2),
 preparation_before_audit=allowance(5,10,1),audit=allowance(25,30,3),
 independent_and_external=allowance(10,15,1))
THREADS = ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS")
POLICY = dict(flags=["-I","-S","-B"],package_path=str(PACKAGE),
 inspection_helpers_preloaded=True,site_processing=False,dependent_native_dll_closure=False,
 cache_bytes_verified=False,max_aliases=4096,max_files=2048,max_registry_bytes=MIB,
 max_hashed_bytes=128*MIB,thread_settings={k:"1" for k in THREADS})
REQUIRED = ("local-image-checker-isolated-runtime.py",
 "local-image-checker-import-capture-preregister.md",
 "local-image-checker-import-capture-ledger.json",
 "independent-local-image-checker-import-capture-source-review.md",
 "local-image-checker-import-capture-launch.py",
 "independent-local-image-checker-import-capture-launch-review.md",
 "local-image-checker-import-capture-prepare.py",
 "local-image-checker-import-capture-preparation.md",
 "independent-local-image-checker-import-capture-preparation-review.md")
SEEN = {}
HASHED_BYTES = 0
PHASES = []
WRITES = 0
PROGRESS_REF = None
RESULT = dict(schema=SCHEMA,status="INCOMPLETE_NO_DATA_IMPORT_CAPTURE",
 subject_complete=False,saved_data_checks_complete=False,dependent_native_dll_closure=False)
AUTHORITY = {}
FILE_TABLE = {}
READ_SCOPE = {}
REGISTRY_PROGRESS = {}
REGISTRY_OBJECTS = {}

def need(value,message):
 if not value: raise ValueError(message)

def encoded(value):
 return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()

def clock():
 return dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)

def guard():
 v=clock()
 need(v["cpu_seconds"]<=14 and v["wall_seconds"]<=23.5,"capture operation limit including terminal reserve")

def closed(value,keys):
 need(type(value) is dict and set(value)==set(keys),"closed fields: "+",".join(keys))

def strict(raw):
 def pairs(items):
  out={}
  for k,v in items:
   need(k not in out,"duplicate JSON key");out[k]=v
  return out
 def walk(v):
  if type(v) is float:need(math.isfinite(v),"finite JSON")
  elif type(v) is dict:
   for x in v.values():walk(x)
  elif type(v) is list:
   for x in v:walk(x)
 v=json.loads(raw,object_pairs_hook=pairs,
  parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
 walk(v);return v

def lexical(value):
 need(type(value) is str and 0<len(value)<=2048,"bounded path spelling")
 p=Path(value);need(".." not in p.parts,"no parent traversal in declared path")
 return Path(os.path.abspath(str(ROOT/p)))

def resolved(value):
 p=lexical(value)
 # Check every lexical component before resolution can hide a reparse ancestor.
 for q in [*reversed(p.parents),p]:
  s=q.lstat()
  need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&1024,
   "no lexical reparse component")
  if q!=p:need(stat.S_ISDIR(s.st_mode),"directory ancestry")
 actual=p.resolve(strict=True);need(actual==p,"unchanged canonical path after checked resolution")
 return actual

def identity(s):
 return tuple(int(getattr(s,k,0)) for k in
  ("st_dev","st_ino","st_size","st_mtime_ns","st_file_attributes","st_nlink"))

def plain(s,p):
 need(stat.S_ISREG(s.st_mode) and not getattr(s,"st_file_attributes",0)&1024
  and s.st_nlink>=1 and (not p.is_relative_to(ROOT) or s.st_nlink==1),"plain scoped file")

def pin_check(r,positive=False,preflight=False):
 closed(r,("path","bytes","sha256"))
 need(type(r["bytes"]) is int and (r["bytes"]>0 if positive else r["bytes"]>=0)
  and type(r["sha256"]) is str and len(r["sha256"])==64
  and all(c in "0123456789abcdef" for c in r["sha256"]),"typed extent/hash")
 p=lexical(r["path"]) if preflight else resolved(r["path"])
 need(r["bytes"]!=0 or r["sha256"]==EMPTY,"empty file hash")
 return p

def fileref(p,n,h):
 return dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),bytes=n,sha256=h)

def read(r,cap,keep=True):
 global HASHED_BYTES
 guard();p=pin_check(r);need(r["bytes"]<=cap,"prevalidated read extent")
 before=p.lstat();plain(before,p);need(before.st_size==r["bytes"],"bound extent before read")
 need(HASHED_BYTES+r["bytes"]<=128*MIB,"whole capture read bound")
 h=hashlib.sha256();parts=[];count=0
 with p.open("rb") as f:
  first=os.fstat(f.fileno());plain(first,p);need(identity(first)==identity(before),"opened same file")
  while count<r["bytes"]:
   guard();chunk=f.read(min(MIB,r["bytes"]-count));need(chunk,"short read")
   count+=len(chunk);HASHED_BYTES+=len(chunk);h.update(chunk)
   if keep:parts.append(chunk)
  need(f.read(1)==b"","no trailing bytes");last=os.fstat(f.fileno())
 after=p.lstat();plain(after,p)
 need(identity(first)==identity(last)==identity(after),"stable before/open/post file")
 need(h.hexdigest()==r["sha256"],"bound file SHA256")
 current=dict(file=fileref(p,count,h.hexdigest()),identity=list(identity(after)))
 need(p not in SEEN or SEEN[p]==current,"same file identity across capture phases")
 SEEN[p]=current
 return b"".join(parts),current

def namespace(values,empty=False,cap=256*MIB,maximum=8192):
 need(type(values) is dict and 0<len(values)<=maximum,"finite namespace")
 out={};total=0
 for key,pin in values.items():
  closed(pin,("bytes","sha256"));r=dict(path=key,**pin);p=pin_check(r,not empty,preflight=True)
  need((pin["bytes"]==0)==empty and p not in out,"unique typed canonical-spelling namespace role")
  out[p]=r;total+=pin["bytes"]
 need(total<=cap,"aggregate namespace extent before payload reads")
 return out

def write_exact(p,raw,cap):
 global WRITES
 need(len(raw)<=cap and WRITES<12,"bounded publication write count/extent")
 WRITES+=1
 with p.open("xb") as f:
  need(f.write(raw)==len(raw),"complete raw write");f.flush();os.fsync(f.fileno())
 before=p.lstat();plain(before,p)
 with p.open("rb") as f:
  first=os.fstat(f.fileno());need(identity(first)==identity(before),"publication opened identity")
  observed=f.read(len(raw)+1);last=os.fstat(f.fileno())
 need(observed==raw and identity(first)==identity(last)==identity(p.lstat()),"publication same-byte readback")
 return fileref(p,len(raw),sha(observed))

def remember(phase,summary):
 global PROGRESS_REF
 need(len(PHASES)<8,"finite phase count")
 row=dict(phase=phase,summary=summary);need(len(encoded(row))<=8*KIB,"bounded phase detail")
 PHASES.append(row)
 raw=encoded(dict(schema=SCHEMA,status="INCOMPLETE_NO_DATA_IMPORT_CAPTURE",phases=PHASES,
  sampled_work=clock(),registry_progress=REGISTRY_PROGRESS))
 need(len(raw)<=64*KIB,"progress preallocation")
 raw=raw.rstrip(b"\n").ljust(64*KIB-1,b" ")+b"\n"
 write_exact(STAGE,raw,64*KIB);stage_identity=identity(STAGE.lstat());os.replace(STAGE,PROGRESS)
 need(identity(PROGRESS.lstat())==stage_identity,"same staged object after progress replacement")
 PROGRESS_REF=fileref(PROGRESS,len(raw),sha(raw))

def profile_predicate(flags,paths):
 expected_flags=dict(isolated=1,ignore_environment=1,no_site=1,no_user_site=1,safe_path=True)
 need(type(flags) is dict and flags==expected_flags and all(type(flags[k]) is type(v) for k,v in expected_flags.items()),
  "typed isolated no-site flags")
 need(paths==[str(PYROOT/"python312.zip"),str(PYROOT/"DLLs"),str(PYROOT/"Lib"),str(PYROOT)],
  "exact original isolated search path")

def startup():
 need(Path.cwd().resolve()==ROOT and resolved(sys.executable)==PYTHON,"fixed cwd/interpreter")
 need(sys.flags.isolated==1 and sys.flags.ignore_environment==1 and sys.flags.no_site==1
  and sys.flags.no_user_site==1 and sys.flags.safe_path is True and sys.dont_write_bytecode
  and not sys._xoptions,"exact isolated no-site no-bytecode profile")
 need(sys.prefix==sys.base_prefix==str(PYROOT) and sys.exec_prefix==sys.base_exec_prefix==str(PYROOT),
  "fixed nonvirtual interpreter prefixes")
 need("site" not in sys.modules and "sitecustomize" not in sys.modules
  and "usercustomize" not in sys.modules,"no site-processing modules")
 profile_predicate({k:getattr(sys.flags,k) for k in ("isolated","ignore_environment","no_site","no_user_site","safe_path")},list(sys.path))
 configs=[]
 for p in (PYROOT/"python312._pth",PYROOT/"python._pth",PYROOT/"pyvenv.cfg",PYROOT.parent/"pyvenv.cfg"):
  # Exact finite existence witnesses; an alternate startup configuration is a refusal.
  try:s=p.lstat()
  except FileNotFoundError:configs.append(dict(path=str(p),exists=False));continue
  plain(s,p);configs.append(dict(path=str(p),exists=True,identity=list(identity(s))))
  RESULT["startup_configurations"]=configs
  need(False,"unexpected interpreter path configuration")
 return dict(flags={k:getattr(sys.flags,k) for k in ("isolated","ignore_environment","no_site","no_user_site","safe_path")},
  dont_write_bytecode=sys.dont_write_bytecode,orig_argv=list(sys.orig_argv),executable=str(PYTHON),
  version=sys.version,prefix=sys.prefix,base_prefix=sys.base_prefix,initial_sys_path=list(sys.path),
  configurations=configs,cache_policy="B prevents writes only; reported cache paths retained without executed-cache byte closure")

def original_plan_predicate(value):
 pin_check(value,True,preflight=True)
 need(value==PLAN,"original plan immutable")

def authority(args):
 global AUTHORITY,READ_SCOPE
 need(resolved(args.grant)==GRANT,"fresh fixed capture grant")
 n=GRANT.stat().st_size;need(0<n<=256*KIB,"finite grant before read")
 raw,gr=read(dict(path=str(GRANT),bytes=n,sha256=args.grant_sha256),256*KIB)
 grant=strict(raw)
 closed(grant,("schema","original_plan","failed_audit2","source_bindings","python_executable",
  "startup_policy","prior_work","resources","cumulative_limits","command"))
 need(grant["schema"]=="m193c-isolated-numpy-import-grant-v1","capture grant schema")
 original_plan_predicate(grant["original_plan"])
 need(grant["startup_policy"]==POLICY and grant["prior_work"]==PRIOR
  and grant["resources"]==RESOURCES and grant["cumulative_limits"]==CAPS,"explicit finite phase grant")
 need(all(PRIOR[k]+sum(v[k] for v in RESOURCES.values())<=CAPS[k] for k in PRIOR),"whole phase fits amended cumulative limits")
 sources=namespace(grant["source_bindings"],cap=256*KIB,maximum=32)
 need(all(p.is_relative_to(WORK) for p in sources) and all(WORK/n in sources for n in REQUIRED),
  "complete new source/protocol/review closure")
 need(sources[SELF]["sha256"]==args.self_sha256,"actual held capture source")
 expected=[str(PYTHON),"-I","-S","-B",str(SELF),"--grant",str(GRANT),
  "--grant-sha256","ACTUAL_CAPTURE_GRANT_SHA256","--self-sha256",args.self_sha256]
 need(grant["command"]==expected and sys.orig_argv==[
  args.grant_sha256 if v=="ACTUAL_CAPTURE_GRANT_SHA256" else v for v in expected],"exact actual capture argv")
 planraw,_=read(PLAN,640*KIB);plan=strict(planraw)
 need(plan["schema"]=="m193c-local-image-probe-plan-v1"
  and grant["python_executable"]==plan["python_executable"],"old pinned Python identity")
 maps=[namespace(plan[n],empty=n=="runtime_empty_bindings",cap=256*MIB)
  for n in ("source_bindings","runtime_bindings","runtime_empty_bindings")]
 need(sum(len(m) for m in maps)==len(set().union(*(set(m) for m in maps))),"disjoint canonical-spelling original namespaces; actual reads check ancestry")
 combined={p:r for m in maps for p,r in m.items()}
 need(not sources.keys()&combined.keys(),"new source namespace cannot revise original files")
 READ_SCOPE={**combined,**sources}
 for r in sources.values():read(r,256*KIB,False)
 read(grant["python_executable"],MIB,False)
 closed(grant["failed_audit2"],tuple(FAILED))
 previous={}
 for role,(suffix,n,h) in FAILED.items():
  r=dict(path="experiments/m193c-output-grid/work/independent-local-image-probe-audit-2"+suffix,bytes=n,sha256=h)
  pin_check(grant["failed_audit2"][role])
  need(grant["failed_audit2"][role]==r,"exact failed second audit evidence")
  previous[role]=read(r,256*KIB)[0]
 old=strict(previous["result"]);outer=strict(previous["outer"])
 need(old["status"]=="INCOMPLETE_INDEPENDENT_AUDIT" and old["subject_complete"] is False
  and old["scientific_contract_verified"] is False and "private" not in old
  and old["actual_final_work"]==PRIOR,"retained second audit refusal and full charges")
 need(previous["stdout"]==previous["result"] and previous["stderr"]==b"" and previous["exit"]==b"1\n"
  and outer["exit_code"]==1 and outer["stdout_bytes"]==len(previous["stdout"])
  and outer["stderr_bytes"]==0,"actual failed raw transport/outer")
 AUTHORITY=dict(grant=gr["file"],original_plan=PLAN,failed_audit2=grant["failed_audit2"],
  prior_work=PRIOR,resources=RESOURCES,cumulative_limits=CAPS)
 return plan

def text(value):
 need(value is None or type(value) is str and len(value)<=2048,"bounded module metadata string")
 return value

def loader_identity(loader):
 if loader is None:return None
 if isinstance(loader,type):return text("class:"+loader.__module__+"."+loader.__qualname__)
 kind=type(loader);return text("instance:"+kind.__module__+"."+kind.__qualname__)

def aliases():
 values=list(sys.modules.items())
 need(len(values)<=4096 and all(type(k) is str and len(k)<=256 for k,v in values),"complete bounded module population")
 rows=[];objects=[]
 for name,module in sorted(values):
  if module is None:
   rows.append([name,"none",None,None,None,None,None]);objects.append([name,id(module)]);continue
  need(type(module) is types.ModuleType,"literal Python module entry")
  d=vars(module);spec=d.get("__spec__")
  origin=None if spec is None else text(spec.origin)
  loader=None if spec is None else loader_identity(spec.loader)
  reported=text(d.get("__file__"));cached=text(d.get("__cached__"))
  rows.append([name,"file" if reported else ("builtin" if origin=="built-in" else "frozen" if origin=="frozen" else "no-file"),
   reported,origin,text(loader),cached,None if spec is None else text(spec.cached)])
  objects.append([name,id(module)])
 return rows,objects

def inspect_registry(label):
 # All inspection imports are top-level. Catch any lazy additions made while examining specs/caches.
 rows,objects=aliases();before=sha(encoded(rows))
 REGISTRY_PROGRESS.update(phase=label,aliases=len(rows),processed=0,unresolved=0)
 file_rows=[];unresolved=[]
 for row in rows:
  guard();name,kind,reported,origin,loader,cached,spec_cached=row
  idx=None
  if reported:
   p=resolved(reported)
   if p.suffix.lower() in (".pyc",".pyo"):
    try:p=resolved(importlib.util.source_from_cache(str(p)))
    except ValueError:
     unresolved.append(dict(name=name,path=str(p),reason="cache-source-conversion"));p=None
   if p is not None:
    pin=READ_SCOPE.get(p)
    if pin is None:unresolved.append(dict(name=name,path=str(p),reason="outside-original-plus-new-source-authority"))
    else:
     if p not in FILE_TABLE:
      need(len(FILE_TABLE)<2048,"finite full file table")
      _,witness=read(pin,128*MIB,False);FILE_TABLE[p]=witness
     idx=str(p)
  file_rows.append([name,kind,idx,reported,origin,loader,cached,spec_cached])
  REGISTRY_PROGRESS.update(processed=len(file_rows),unresolved=len(unresolved))
 rows_after,objects_after=aliases()
 stable=rows_after==rows and objects_after==objects
 record=dict(label=label,layout=["name","kind","canonical_file","reported_file","spec_origin","loader_type","cached","spec_cached"],
  rows=file_rows,canonical_metadata_sha256=before,stable_during_inspection=stable,unresolved=unresolved)
 REGISTRY_OBJECTS[label]=objects
 RESULT.setdefault("registries",[]).append(record)
 extent=len(encoded(dict(registries=RESULT["registries"],files=list(FILE_TABLE.values()))))
 if extent>MIB:
  RESULT["registry_overflow"]=dict(bytes=extent,sha256=sha(encoded(record)),label=label,complete_record_retained=False)
  RESULT["registries"].pop()
  need(False,"whole registry serialization bound; retained prefix is incomplete")
 need(stable,"registry inspection cannot hide newly loaded or rebound entries")
 # Do not stop on the first undeclared alias; retain the entire bounded discrepancy list.
 need(not unresolved,"complete registry has undeclared module files")
 return record

def signature(record):
 return sha(encoded(dict(layout=record["layout"],rows=record["rows"],unresolved=record["unresolved"])))


# Audit3 selects these exact unchanged definitions into a private globals mapping,
# not a new sys.modules alias. All imports below must be preloaded before capture.
AUDIT_SHARED_DEFINITIONS=("need","encoded","sha","closed","strict","lexical","resolved",
 "identity","plain","pin_check","fileref","read","namespace","profile_predicate","text",
 "loader_identity","aliases","inspect_registry","signature","normalized_registry","final_recheck")
AUDIT_IMPORTS=("time","argparse","ast","hashlib","importlib.util","json","math","os",
 "pathlib.Path","stat","sys","traceback","types")
API_SOURCE=WORK/"local-image-checker-isolated-runtime.py"

def shared_profile():
 raw,witness=read(READ_SCOPE[API_SOURCE],256*KIB)
 tree=ast.parse(raw);nodes={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
 need(all(n in nodes for n in AUDIT_SHARED_DEFINITIONS),"exact declared shared inspector definitions")
 body=ast.Module(body=[nodes[n] for n in AUDIT_SHARED_DEFINITIONS],type_ignores=[])
 return dict(schema="m193c-isolated-runtime-shared-profile-v1",source=witness["file"],
  definitions=list(AUDIT_SHARED_DEFINITIONS),definition_ast_sha256=sha(ast.dump(body,include_attributes=False).encode()),
  preloaded_imports=list(AUDIT_IMPORTS),entry_normalization="Only __main__ canonical/reported source paths become CURRENT_ENTRY; exact source remains separately granted",
  binding_scope="Private definition namespace, no additional sys.modules helper alias; caller supplies guard, clock and explicit mutable reader/registry state")

def normalized_registry(record,entry_source):
 entry=resolved(str(entry_source));need(entry in FILE_TABLE,"current entry source was actually authenticated")
 rows=strict(encoded(record["rows"]));found=0
 for row in rows:
  if row[0]=="__main__":
   need(row[1]=="file" and row[2]==str(entry) and resolved(row[3])==entry
    and row[4] is None and row[6] is None and row[7] is None,"exact current script entry metadata")
   row[2]=row[3]="CURRENT_ENTRY";found+=1
 need(found==1,"one explicit current entry alias")
 return dict(layout=record["layout"],rows=rows,unresolved=record["unresolved"])

def metadata_controls(record):
 # Copied metadata/source-pin faults commission the actual predicates; no extra import/process.
 base=signature(record);progress=dict(scope="Injected metadata only, not physical startup causality",
  rows=[],original_sha256=base)
 RESULT["metadata_controls"]=progress
 def validate(v):
  need(v["layout"]==record["layout"] and type(v["rows"]) is list and len(v["rows"])==len(record["rows"]),
   "complete registry shape")
  need(signature(v)==base,"exact full alias registry identity")
 def registry_fault(kind):
  v=strict(encoded(record))
  if kind=="missing":v["rows"].pop()
  elif kind=="rebound":v["rows"][0][0]+="-fault"
  validate(v)
 def profile_fault(kind):
  flags=dict(RESULT["startup"]["flags"]);paths=list(RESULT["startup"]["initial_sys_path"])
  if kind=="flag":flags["no_site"]=0
  elif kind=="path":paths.append(str(PACKAGE))
  profile_predicate(flags,paths)
 def source_fault(kind):
  r=dict(READ_SCOPE[SELF])
  if kind=="empty":r.update(bytes=0,sha256=EMPTY);pin_check(r,True)
  elif kind=="bool":r.update(bytes=False,sha256=EMPTY);pin_check(r)
  elif kind=="hash":
   r["sha256"]=("0" if r["sha256"][0]!="0" else "1")+r["sha256"][1:]
   read(r,256*KIB,False)
 def plan_fault():
  value=dict(PLAN);value["bytes"]+=1;original_plan_predicate(value)
 cases=[("positive-registry",lambda:registry_fault(None),None),
  ("missing-alias",lambda:registry_fault("missing"),"complete registry shape"),
  ("rebound-alias",lambda:registry_fault("rebound"),"exact full alias registry identity"),
  ("wrong-no-site-flag",lambda:profile_fault("flag"),"typed isolated no-site flags"),
  ("extra-search-path",lambda:profile_fault("path"),"exact original isolated search path"),
  ("zero-positive-source",lambda:source_fault("empty"),"typed extent/hash"),
  ("bool-empty-extent",lambda:source_fault("bool"),"typed extent/hash"),
  ("wrong-source-hash",lambda:source_fault("hash"),"bound file SHA256"),
  ("changed-original-plan-reference",plan_fault,"original plan immutable")]
 for name,call,expected in cases:
  row=dict(name=name,passed=False);progress["rows"].append(row);rejected=None
  try:call()
  except ValueError as exc:rejected=str(exc)
  row.update(rejection=rejected,passed=rejected==expected)
  need(row["passed"],"powered metadata control: "+name)
 restored=strict(encoded(record));validate(restored);profile_fault(None)
 need(signature(record)==base==signature(restored),"whole original/copy restoration")
 progress["rows"].append(dict(name="restored",passed=True,rejection=None))
 progress["restored_sha256"]=signature(restored)
 return progress

def final_recheck():
 for p,witness in SEEN.items():
  guard();s=p.lstat();plain(s,p)
  need(list(identity(s))==witness["identity"],"final file identity unchanged")
 # This final stat check is an identity witness, not another full content hash.
 return dict(files=len(SEEN),scope="same full metadata identity after earlier authenticated content reads")

def main():
 global RESULT
 parser=argparse.ArgumentParser()
 parser.add_argument("--grant",required=True);parser.add_argument("--grant-sha256",required=True)
 parser.add_argument("--self-sha256",required=True)
 code=1;owned=False
 try:
  need(not any(p.exists() for p in (FINAL,PROGRESS,STAGE)),"fresh capture artifacts")
  owned=True
  remember("initial",dict(scope="No subject/image/array operations; default incomplete"))
  args=parser.parse_args()
  RESULT["startup"]=startup()
  authority(args);RESULT["authority"]=AUTHORITY
  remember("authority",dict(grant=AUTHORITY["grant"]))
  RESULT["shared_inspector_profile"]=shared_profile()
  before=inspect_registry("before-numpy")
  before["entry_normalized_sha256"]=sha(encoded(normalized_registry(before,SELF)))
  RESULT["metadata_controls"]=metadata_controls(before)
  remember("pre-import",dict(aliases=len(before["rows"]),files=len(FILE_TABLE)))
  for k in THREADS:os.environ[k]="1"
  need(str(PACKAGE) not in sys.path,"single explicit package path addition")
  sys.path.append(str(PACKAGE))
  RESULT["numpy_import_attempted"]=True
  t=clock()
  # The only numerical-package action in this stage; no saved data is opened.
  import numpy as np
  ended=clock()
  RESULT["numpy_import_timing"]={k:ended[k]-t[k] for k in t}
  RESULT["numpy_version"]=np.__version__
  # Exact module bytes are pinned by the original manifest; record actual version without guessing it.
  post=inspect_registry("after-numpy")
  post["entry_normalized_sha256"]=sha(encoded(normalized_registry(post,SELF)))
  RESULT["search_path_after_import"]=list(sys.path)
  need(sys.path==RESULT["startup"]["initial_sys_path"]+[str(PACKAGE)],"no import-time search path widening")
  need("site" not in sys.modules and "sitecustomize" not in sys.modules and "usercustomize" not in sys.modules,
   "no site processing during NumPy import")
  RESULT["thread_settings"]={k:os.environ.get(k) for k in THREADS}
  need(RESULT["thread_settings"]=={k:"1" for k in THREADS},"fixed non-PYTHON thread settings")
  RESULT["final_identity_recheck"]=final_recheck()
  last,last_objects=aliases()
  need(sha(encoded(last))==post["canonical_metadata_sha256"] and last_objects==REGISTRY_OBJECTS["after-numpy"],
   "full post-import registry remains unchanged")
  remember("capture-complete",dict(aliases=len(post["rows"]),files=len(FILE_TABLE)))
  last,last_objects=aliases()
  need(sha(encoded(last))==post["canonical_metadata_sha256"] and last_objects==REGISTRY_OBJECTS["after-numpy"],
   "final publication helpers preserve the post-import registry")
  RESULT["status"]=STATUS;RESULT["capture_complete"]=True;code=0
 except BaseException:
  raw=traceback.format_exc().encode()
  RESULT.update(status="INCOMPLETE_NO_DATA_IMPORT_CAPTURE",capture_complete=False,error=dict(bytes=len(raw),sha256=sha(raw),
   suffix=raw[-4096:].decode("utf-8","replace"),truncated=len(raw)>4096))
 finally:
  if not owned:return 1
  RESULT.update(authority=AUTHORITY,phases=PHASES,registry_progress=REGISTRY_PROGRESS,
   files=list(FILE_TABLE.values()),hashed_bytes=HASHED_BYTES,sampled_work=clock(),
   cpu_accounting_complete=False,publication_allowance=dict(cpu_seconds=1,wall_seconds=1.5),
   source_scope="Original module-source file authority only; cached bytecode and dependent native DLL closure unverified",
   admission_rule="Require exact actual outer exit0, final/console association, independent capture review and separate audit grant")
  try:
   guard_final=clock()
   need(guard_final["cpu_seconds"]<=15 and guard_final["wall_seconds"]<=25,"capture terminal envelope")
   raw=encoded(RESULT)
   if len(raw)>1152*KIB:
    # Preserve a bounded refusal even if a complete registry exceeds its retained lane.
    code=1
    RESULT=dict(schema=SCHEMA,status="INCOMPLETE_NO_DATA_IMPORT_CAPTURE",capture_complete=False,
     subject_complete=False,saved_data_checks_complete=False,cpu_accounting_complete=False,
     authority_grant=AUTHORITY.get("grant"),progress=PROGRESS_REF,sampled_work=clock(),
     oversized_record=dict(bytes=len(raw),sha256=sha(raw),complete_record_retained=False),
     registry_progress=REGISTRY_PROGRESS,error="FINAL_METADATA_EXTENT",publication_allowance=dict(cpu_seconds=1,wall_seconds=1.5))
    raw=encoded(RESULT);need(len(raw)<=16*KIB,"bounded compact terminal refusal")
   r=write_exact(FINAL,raw,1152*KIB)
   console=encoded(dict(schema=SCHEMA,status=RESULT["status"],result=r,
    capture_complete=RESULT.get("capture_complete",False),exit_code=code))
   need(len(console)<=8*KIB,"bounded raw console")
   need(sys.stdout.buffer.write(console)==len(console),"full raw console write");sys.stdout.buffer.flush()
  except BaseException:
   code=1
   try:remember("terminal-publication-refusal",dict(error=traceback.format_exc()[-2048:]))
   except BaseException:pass
 return code

if __name__=="__main__":
 raise SystemExit(main())

