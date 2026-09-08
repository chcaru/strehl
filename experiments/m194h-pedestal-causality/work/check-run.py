"""One owned invocation of the held independent M194h saved-output checker.
Reuses the reviewed driver's generic process/Job/accounting functions. No retries.
"""
import time
START=time.monotonic()
from pathlib import Path
import hashlib,json,sys,types,os,traceback
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/"experiments/m194h-pedestal-causality"
LIMITS=dict(cpu_seconds=60,wall_seconds=120,committed_bytes=1<<30,file_bytes=16<<20,scratch_bytes=0)
def need(v,s):
 if not v:raise ValueError(s)
def read(p,cap):
 need(p.stat().st_size<=cap,"bounded input")
 with p.open("rb") as f:
  s=os.fstat(f.fileno());b=f.read(cap+1);e=os.fstat(f.fileno())
 ident=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
 need(len(b)<=cap and ident(s)==ident(e)==ident(p.stat()) and len(b)==s.st_size,"same input bytes")
 return b
def main():
 need(sys.argv[1::2][0:2]==["--release","--release-sha256"] and len(sys.argv)==5,"exact wrapper arguments")
 release_path=Path(sys.argv[2]).resolve()
 raw=read(release_path,1<<20);need(hashlib.sha256(raw).hexdigest()==sys.argv[4],"held independent release")
 release=json.loads(raw);need(set(release)=={"schema","source_bindings","render","subject_grant","command"} and release["schema"]=="m194h-independent-check-release-v1","exact independent release")
 sources=release["source_bindings"]
 def bound(p):
  b=read(p,4<<20);key=p.relative_to(ROOT).as_posix()
  need(sources[key]==dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()),"held current source")
  return b
 bound(Path(__file__).resolve())
 path=HERE/"build-and-run.py";driver=types.ModuleType("m194h_reused_owned_driver");driver.__file__=str(path)
 exec(compile(bound(path),str(path),"exec"),driver.__dict__)
 driver.START=START
 output=HERE/"independent-run-1";need(not output.exists(),"fresh checker wrapper")
 output.mkdir()
 budget=driver.Budget("components",output);budget.stage="checker";budget.caps=LIMITS
 # The scientific checker output is in a sibling directory, included in the same byte budget.
 original_check=budget.check
 def check(force=False):
  original_check(force)
  a=driver.scan(output,16<<20);b=driver.scan(HERE/"independent-check-1",16<<20)
  need(a["bytes"]+b["bytes"]+(192<<10)<=16<<20,"combined independent artifact cap")
 budget.check=check
 original_limits=budget.limits
 def limits(i):
  v=original_limits(i);v["log_bytes"]=1<<20;return v
 budget.limits=limits
 result=dict(schema="m194h-independent-wrapper-v1",status="INITIAL_INCOMPLETE",release=dict(path=str(release_path),bytes=len(raw),sha256=sys.argv[4]),invocation=sys.orig_argv,children=[],artifacts={},error=None,finalization_errors=[],limits=LIMITS)
 driver.atomic(output/"result.json",result)
 try:
  for key in sources:driver.source_bytes(ROOT/key,sources,budget.check)
  checker=HERE/"independent-verify.py";pin=sources[checker.relative_to(ROOT).as_posix()]
  command=[sys.argv[4] if x=="ACTUAL_RELEASE_SHA256" else pin["sha256"] if x=="ACTUAL_SOURCE_SHA256" else x for x in release["command"]]
  expected=[str(Path(sys.executable)),"-I","-B",str(checker),"--release",str(release_path),"--release-sha256",sys.argv[4],"--source-sha256",pin["sha256"],"--output",str(HERE/"independent-check-1")]
  need(command==expected,"exact checker child command")
  process,api=driver.load_process(sources)
  env=driver.clean_env()
  for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):env[name]="2"
  driver.child_call(process,api,command,env,0,output,budget,result)
  final_path=HERE/"independent-check-1/result.json"
  finalraw,finalref=driver.read(final_path,1<<20,check=budget.check);final=driver.strict(finalraw)
  lograw,_=driver.read(output/"child-00.log",1<<20,check=budget.check)
  need(lograw==finalraw and final["status"]=="PASS_INDEPENDENT_SAVED_CONSUMER_CHECK_ONLY" and final["independent_complete"] is True and final["error"] is None,"exact checker final/log and complete disposition")
  for key in sources:driver.source_bytes(ROOT/key,sources,budget.check)
  driver.read(release_path,1<<20,result["release"],keep=False,check=budget.check)
  result["artifacts"]["independent_result"]=finalref
  result["status"]="COMPLETE_INDEPENDENT_WRAPPER_UNVERIFIED"
 except BaseException:
  result["status"]="REFUSED";result["error"]=driver.error_value()
 finally:
  result["work"]=budget.work()
  try:
   terminal=driver.atomic(output/"result.json",result)
   tail=dict(schema="m194h-independent-wrapper-tail-v1",result=terminal,
     parent_cpu_sample=time.process_time(),completed_child_cpu_seconds=budget.completed_cpu,
     live_child_cpu_seconds=budget.live_cpu,whole_wall_sample=time.monotonic()-START,
     cpu_accounting_complete=budget.complete and budget.accounting_error is None,final_external_allowance=dict(cpu_seconds=2,wall_seconds=3))
   need(tail["parent_cpu_sample"]+budget.completed_cpu+budget.live_cpu+2<=60 and tail["whole_wall_sample"]+3<=120,"whole independent envelope plus tail")
   tr=driver.write_new(output/"parent-tail.json",driver.encoded(tail),8192)
   advertisement=dict(status=result["status"],result=terminal,tail=tr)
  except BaseException:
   result["status"]="REFUSED";result["finalization_errors"].append(driver.error_value())
   try:terminal=driver.atomic(output/"result.json",result)
   except BaseException:terminal=None
   advertisement=dict(status="REFUSED",result=terminal,error="wrapper finalization failed")
  advertisement_bytes=driver.encoded(advertisement)
  need(len(advertisement_bytes)<=8192,"bounded wrapper stdout")
  need(sys.stdout.buffer.write(advertisement_bytes)==len(advertisement_bytes),"complete wrapper stdout")
  sys.stdout.buffer.flush()
 return 0 if result["status"]=="COMPLETE_INDEPENDENT_WRAPPER_UNVERIFIED" else 1
if __name__=="__main__":raise SystemExit(main())
