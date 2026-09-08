"""Source-only metadata preparer; no collector/numerical imports or runtime walk."""
import time
START=time.monotonic()
import argparse,hashlib,json,math,os,stat,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/"experiments/m193c-output-grid/work"
SELF=Path(__file__).resolve();PY=Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
KIB=1024;MIB=1<<20;EMPTY=hashlib.sha256(b"").hexdigest()
GRANT=WORK/"local-image-checker-import-capture-grant-1.json"
RECEIPT=WORK/"local-image-checker-import-capture-preparation-1.json"
CONTROLS=WORK/"local-image-checker-import-capture-preparation-controls-1.json"
FAILURE=WORK/"local-image-checker-import-capture-preparation-1-failure.json"
STAGE=WORK/"local-image-checker-import-capture-preparation-1-stage.json"
PLAN=dict(path="experiments/m193c-output-grid/local-image-probe-plan-1.json",bytes=476283,
 sha256="337ee76493feb15f14982d14fdb6b6148bc76ba108a9c0d77ba51ca25a6e66c1")
PRIOR=dict(cpu_seconds=1588.443678,wall_seconds=1601.9278447999966,file_bytes=4140565273,metadata_bytes=149304339)
CAPS=dict(cpu_seconds=1660,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=168*MIB)
def allocation(cpu,wall,mib):return dict(cpu_seconds=cpu,wall_seconds=wall,file_bytes=mib*MIB,metadata_bytes=mib*MIB)
RESOURCES=dict(preparation_before_capture=allocation(5,10,1),capture=allocation(15,25,2),
 preparation_before_audit=allocation(5,10,1),audit=allocation(25,30,3),independent_and_external=allocation(10,15,1))
POLICY=dict(flags=["-I","-S","-B"],package_path=str(PY.parent/"Lib/site-packages"),
 inspection_helpers_preloaded=True,site_processing=False,dependent_native_dll_closure=False,
 cache_bytes_verified=False,max_aliases=4096,max_files=2048,max_registry_bytes=MIB,
 max_hashed_bytes=128*MIB,thread_settings={k:"1" for k in
 ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS")})
FAILED={
 "result":(".json",168790,"9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f"),
 "outer":("-outer.json",2138,"bb583734d952afe54e225bc14c225ac30a7bb8f9944cfc6843eb6ef42a4ed684"),
 "stdout":("-stdout.bin",168790,"9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f"),
 "stderr":("-stderr.bin",0,EMPTY),
 "exit":("-exit.txt",2,"4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865")}
REQUIRED=("local-image-checker-isolated-runtime.py","local-image-checker-bootstrap-closure-design.md",
 "local-image-checker-import-capture-preregister.md","local-image-checker-import-capture-ledger.json",
 "independent-local-image-checker-import-capture-source-review.md","local-image-checker-import-capture-launch.py",
 "independent-local-image-checker-import-capture-launch-review.md","local-image-checker-import-capture-prepare.py",
 "local-image-checker-import-capture-preparation.md","independent-local-image-checker-import-capture-preparation-review.md")
SEEN={};ROWS=[];WRITES=0;OBSERVED={};OWNED=False

def need(v,m):
 if not v:raise ValueError(m)
def encode(v):return (json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sampled():return dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
def guard():
 s=sampled();OBSERVED.update(s)
 need(s["cpu_seconds"]<=4 and s["wall_seconds"]<=9,"current preparation ordinary CPU/wall envelope")
def closed(v,keys):need(type(v) is dict and set(v)==set(keys),"closed metadata fields")
def parse(raw):
 def pairs(items):
  out={}
  for k,v in items:need(k not in out,"duplicate JSON key");out[k]=v
  return out
 def walk(v):
  if type(v) is float:need(math.isfinite(v),"finite JSON")
  elif type(v) is dict:
   for x in v.values():walk(x)
  elif type(v) is list:
   for x in v:walk(x)
 v=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
 walk(v);return v
def path(value):
 need(type(value) is str and 0<len(value)<=2048,"bounded path")
 p=Path(value);need(".." not in p.parts,"no parent traversal")
 p=Path(os.path.abspath(str(ROOT/p)))
 for q in [*reversed(p.parents),p]:
  s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&1024,"no lexical reparse component")
  if q!=p:need(stat.S_ISDIR(s.st_mode),"directory ancestry")
 need(p.resolve(strict=True)==p,"same checked canonical path")
 return p
def identity(s):
 return tuple(int(getattr(s,k,0)) for k in ("st_dev","st_ino","st_size","st_mtime_ns","st_file_attributes","st_nlink"))
def plain(s,p):
 need(stat.S_ISREG(s.st_mode) and not getattr(s,"st_file_attributes",0)&1024
  and s.st_nlink>=1 and (not p.is_relative_to(ROOT) or s.st_nlink==1),"plain scoped file")
def pin(v,positive=False):
 closed(v,("path","bytes","sha256"))
 need(type(v["bytes"]) is int and (v["bytes"]>0 if positive else v["bytes"]>=0)
  and type(v["sha256"]) is str and len(v["sha256"])==64
  and all(c in "0123456789abcdef" for c in v["sha256"]),"positive source FileRef" if positive else "typed FileRef")
 need(v["bytes"]!=0 or v["sha256"]==EMPTY,"canonical empty hash")
 return path(v["path"])
def ref(p,raw):
 return dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),bytes=len(raw),sha256=digest(raw))
def read(v,cap):
 guard();p=pin(v);need(v["bytes"]<=cap,"prevalidated read extent")
 before=p.lstat();plain(before,p);need(before.st_size==v["bytes"],"bound pre-open extent")
 with p.open("rb") as f:
  first=os.fstat(f.fileno());need(identity(first)==identity(before),"opened exact object")
  raw=f.read(v["bytes"]+1);last=os.fstat(f.fileno())
 named=p.lstat();plain(named,p)
 need(identity(first)==identity(last)==identity(named) and len(raw)==v["bytes"],"stable same-buffer read")
 need(digest(raw)==v["sha256"],"bound file SHA256")
 value=dict(file=ref(p,raw),identity=list(identity(named)))
 need(p not in SEEN or SEEN[p]==value,"same held bytes and identity")
 SEEN[p]=value;return raw
def bind(p,cap):
 p=path(str(p));s=p.lstat();plain(s,p);need(0<s.st_size<=cap,"positive bounded source")
 # Read and bind one buffer; no separately parsed unbound metadata.
 with p.open("rb") as f:
  a=os.fstat(f.fileno());need(identity(a)==identity(s),"bind opened identity")
  raw=f.read(s.st_size+1);b=os.fstat(f.fileno())
 c=p.lstat();plain(c,p)
 need(identity(a)==identity(b)==identity(c) and len(raw)==s.st_size,"bind stable bytes")
 r=ref(p,raw);SEEN[p]=dict(file=r,identity=list(identity(c)));return r
def write(p,value,cap):
 global WRITES
 raw=encode(value);need(len(raw)<=cap and WRITES<8,"finite metadata publication")
 WRITES+=1
 with p.open("xb") as f:
  need(f.write(raw)==len(raw),"full metadata write");f.flush();os.fsync(f.fileno())
 s=p.lstat();plain(s,p)
 with p.open("rb") as f:
  a=os.fstat(f.fileno());need(identity(a)==identity(s),"published opened identity")
  observed=f.read(len(raw)+1);b=os.fstat(f.fileno())
 need(observed==raw and identity(a)==identity(b)==identity(p.lstat()),"published same-byte readback")
 return ref(p,observed)
def default_or_failure(value,initial=False):
 target=FAILURE if initial else STAGE
 r=write(target,value,16*KIB)
 if not initial:
  old_identity=identity(STAGE.lstat());os.replace(STAGE,FAILURE)
  need(identity(FAILURE.lstat())==old_identity,"same atomic failure object")
  r["path"]=FAILURE.relative_to(ROOT).as_posix()
 return r
def original_plan(v):
 pin(v,True);need(v==PLAN,"original plan immutable")
def sources_predicate(values):
 need(type(values) is list and 1<=len(values)<=32,"finite source list")
 paths=[];total=0
 for r in values:
  p=pin(r,True);need(p.is_relative_to(WORK) and p.suffix in (".py",".md",".json"),"new source metadata only")
  paths.append(p);total+=r["bytes"]
 need(len(paths)==len(set(paths)),"unique source identity")
 need(total<=256*KIB,"whole source closure extent")
 return paths
def controls(values):
 before=digest(encode(values))
 def source_fault(kind):
  v=parse(encode(values))
  if kind=="zero":v[0].update(bytes=0,sha256=EMPTY)
  elif kind=="bool":v[0].update(bytes=False,sha256=EMPTY)
  elif kind=="duplicate":v[-1]=dict(v[0])
  sources_predicate(v)
 def plan_fault():
  v=dict(PLAN);v["bytes"]+=1;original_plan(v)
 def hash_fault():
  v=dict(next(r for r in values if path(r["path"])==SELF))
  v["sha256"]=("0" if v["sha256"][0]!="0" else "1")+v["sha256"][1:]
  read(v,256*KIB)
 cases=[("positive",lambda:source_fault(None),None),("wrong-plan",plan_fault,"original plan immutable"),
  ("zero-source",lambda:source_fault("zero"),"positive source FileRef"),
  ("bool-extent",lambda:source_fault("bool"),"positive source FileRef"),
  ("duplicate-source",lambda:source_fault("duplicate"),"unique source identity"),
  ("wrong-source-hash",hash_fault,"bound file SHA256")]
 for name,call,expected in cases:
  row=dict(name=name,passed=False);ROWS.append(row);err=None
  try:call()
  except ValueError as exc:err=str(exc)
  row.update(rejection=err,passed=err==expected);need(row["passed"],"metadata control "+name)
 restored=parse(encode(values));sources_predicate(restored)
 need(digest(encode(values))==before==digest(encode(restored)),"whole source restoration")
 ROWS.append(dict(name="restored",passed=True,rejection=None))
 return dict(schema="m193c-isolated-import-preparation-controls-v1",rows=ROWS,
  original_sha256=before,restored_sha256=digest(encode(restored)),scope="metadata/source-byte predicates only; no collector/runtime import")
def main():
 global OWNED
 result=dict(schema="m193c-isolated-import-preparation-v1",status="INITIAL_INCOMPLETE",rows=ROWS)
 try:
  need(not any(p.exists() for p in (GRANT,RECEIPT,CONTROLS,FAILURE,STAGE)),"fresh preparation artifacts")
  OWNED=True;default_or_failure(result,True)
  ap=argparse.ArgumentParser();ap.add_argument("--source",action="append",required=True)
  ap.add_argument("--self-sha256",required=True);args=ap.parse_args()
  need(Path.cwd().resolve()==ROOT and path(sys.executable)==PY and sys.flags.isolated==1
   and sys.flags.no_site==1 and sys.dont_write_bytecode and not sys._xoptions,"metadata-only isolated preparation profile")
  need(1<=len(args.source)<=32 and all(len(x)<=2048 for x in args.source),"bounded source argv")
  listed=[path(x) for x in args.source]
  need(len(listed)==len(set(listed)) and set(WORK/n for n in REQUIRED)<=set(listed),"exact required unique source closure")
  # First inspect all extents; no source is hashed until aggregate is known to fit.
  total=0
  for p in listed:
   s=p.lstat();plain(s,p);need(p.is_relative_to(WORK) and p.suffix in (".py",".md",".json") and 0<s.st_size<=256*KIB,"positive source metadata extent")
   total+=s.st_size
  need(total<=256*KIB,"source aggregate preflight")
  values=[]
  for p in sorted(listed):guard();values.append(bind(p,256*KIB))
  sources_predicate(values)
  need(next(r for r in values if path(r["path"])==SELF)["sha256"]==args.self_sha256,"held preparer SELF")
  original_plan(PLAN);plan=parse(read(PLAN,640*KIB))
  need(plan["schema"]=="m193c-local-image-probe-plan-v1","fixed original plan schema")
  oldkeys={str(Path(os.path.abspath(str(ROOT/k)))) for space in
   ("source_bindings","runtime_bindings","runtime_empty_bindings") for k in plan[space]}
  need(not oldkeys&{str(p) for p in listed},"no mutation of original namespace")
  python=plan["python_executable"];need(pin(python,True)==PY,"old pinned interpreter");read(python,MIB)
  failed_refs={};data={}
  for role,(suffix,n,h) in FAILED.items():
   r=dict(path="experiments/m193c-output-grid/work/independent-local-image-probe-audit-2"+suffix,bytes=n,sha256=h)
   failed_refs[role]=r;data[role]=read(r,256*KIB)
  old=parse(data["result"]);outer=parse(data["outer"])
  need(old["status"]=="INCOMPLETE_INDEPENDENT_AUDIT" and old["actual_final_work"]==PRIOR
   and old["subject_complete"] is False and old["scientific_contract_verified"] is False and "private" not in old,"retained failed audit/carry")
  need(data["stdout"]==data["result"] and data["stderr"]==b"" and data["exit"]==b"1\n"
   and outer["exit_code"]==1 and outer["stdout_bytes"]==len(data["stdout"]) and outer["stderr_bytes"]==0,"actual failed audit transport")
  need(all(PRIOR[k]+sum(v[k] for v in RESOURCES.values())<=CAPS[k] for k in PRIOR),"full prospective phase fits amended caps")
  control=controls(values);control_ref=write(CONTROLS,control,32*KIB)
  mapping={r["path"]:{k:r[k] for k in ("bytes","sha256")} for r in values}
  collector=next(r for r in values if path(r["path"])==WORK/"local-image-checker-isolated-runtime.py")
  command=[str(PY),"-I","-S","-B",str(WORK/"local-image-checker-isolated-runtime.py"),
   "--grant",str(GRANT),"--grant-sha256","ACTUAL_CAPTURE_GRANT_SHA256","--self-sha256",collector["sha256"]]
  grant=dict(schema="m193c-isolated-numpy-import-grant-v1",original_plan=PLAN,
   failed_audit2=failed_refs,source_bindings=mapping,python_executable=python,startup_policy=POLICY,
   prior_work=PRIOR,resources=RESOURCES,cumulative_limits=CAPS,command=command)
  for r in values:read(r,256*KIB)
  for p,w in SEEN.items():
   s=p.lstat();plain(s,p);need(list(identity(s))==w["identity"],"final held metadata identity")
  guard();grant_ref=write(GRANT,grant,256*KIB)
  result.update(status="COMPLETE_CAPTURE_METADATA_PREPARATION_ONLY",grant=grant_ref,controls=control_ref,
   original_plan=PLAN,failed_audit2=failed_refs,sources=values,command=list(sys.orig_argv),
   source=next(r for r in values if path(r["path"])==SELF),prior_work=PRIOR,
   charged_preparation=RESOURCES["preparation_before_capture"],
   sampled_work=sampled(),publication_allowance=dict(cpu_seconds=1,wall_seconds=1),
   cpu_accounting_complete=False,source_only_scope="No subject/collector/numerical import or runtime walk",
   admission_rule="Root must verify actual preparation outer/exit/receipt/grant before capture release")
  receipt_ref=write(RECEIPT,result,32*KIB)
  console=encode(dict(schema=result["schema"],status=result["status"],receipt=receipt_ref,grant=grant_ref))
  need(len(console)<=8*KIB and sys.stdout.buffer.write(console)==len(console),"bounded full raw console")
  sys.stdout.buffer.flush();return 0
 except BaseException:
  raw=traceback.format_exc().encode()
  result=dict(schema="m193c-isolated-import-preparation-v1",status="REFUSED_CAPTURE_METADATA_PREPARATION",
   grant=result.get("grant"),controls=result.get("controls"),rows=ROWS,sampled_work=sampled(),
   last_guard_sample=OBSERVED,cpu_accounting_complete=False,
   charged_preparation=RESOURCES["preparation_before_capture"],publication_allowance=dict(cpu_seconds=1,wall_seconds=1),
   error=dict(bytes=len(raw),sha256=digest(raw),suffix=raw[-2048:].decode("utf-8","replace"),truncated=len(raw)>2048))
  need(len(encode(result))<=16*KIB,"compact failure receipt extent")
  if OWNED:
   try:default_or_failure(result)
   except BaseException:pass
  return 1
if __name__=="__main__":raise SystemExit(main())

