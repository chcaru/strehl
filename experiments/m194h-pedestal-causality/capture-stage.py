"""Root external record for one fixed M194h stage. Does not retry.
The inner controller owns and bounds its child Jobs; this outer record owns only
the directly launched Python controller. No complete parent CPU claim.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def buffer_ref(p):
 assert p.stat().st_size<=1<<20,"bounded external input"
 identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
 initial=p.stat()
 with p.open("rb") as f:
  before=os.fstat(f.fileno());b=f.read((1<<20)+1);after=os.fstat(f.fileno())
 assert len(b)<=1<<20 and identity(initial)==identity(p.stat()) and identity(before)==identity(after) and identity(initial)[:4]+identity(initial)[5:]==identity(before)[:4]+identity(before)[5:] and len(b)==before.st_size,"stable external input"
 return b,dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def ref(p):return buffer_ref(p)[1]
def main():
 stage=sys.argv[1]
 assert stage in ("build","components","render")
 assert Path.cwd().resolve()==ROOT
 release=HERE/"work"/(stage+"-release-"+("3" if stage=="build" else "1")+".json")
 raw,r=buffer_ref(release);grant=json.loads(raw)
 assert grant["schema"]=="m194h-owned-stage-release-v1" and grant["stage"]==stage,"fixed stage schema"
 prepraw,_=buffer_ref(HERE/"work"/(stage+"-preparation-4.json"))
 prep=json.loads(prepraw)
 assert prep["status"]=="PASS_METADATA_PREPARATION" and prep["release"]==r,"prepared actual release"
 own=ref(Path(__file__).resolve())
 assert {k:own[k] for k in ("bytes","sha256")}==grant["source_bindings"][own["path"]],"held capture source"
 command=[r["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in grant["command"]]
 source=ref(HERE/"build-and-run.py")
 assert {k:source[k] for k in ("bytes","sha256")}==grant["source_bindings"][source["path"]]
 stem=HERE/"work"/(stage+"-external-"+("3" if stage=="build" else "1"))
 paths={k:Path(str(stem)+suffix) for k,suffix in (("stdout","-stdout.bin"),("stderr","-stderr.bin"),("exit","-exit.txt"),("outer","-outer.json"))}
 assert all(not p.exists() for p in paths.values())
 timeout={"build":240,"components":60,"render":180}[stage]
 timedout=False;exit_code=None;failure=None;proc=None
 with paths["stdout"].open("xb") as out,paths["stderr"].open("xb") as err:
  start=time.monotonic()
  try:
   proc=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
   while proc.poll() is None:
    if time.monotonic()-start>=timeout:
     timedout=True;raise TimeoutError("external whole-wall bound")
    if paths["stdout"].stat().st_size>8192 or paths["stderr"].stat().st_size>32768:
     raise ValueError("external stream cap")
    time.sleep(.05)
   exit_code=proc.returncode
  except BaseException as exc:
   failure=str(exc)[:1000]
   if proc is not None:
    try:
     if proc.poll() is None:proc.kill()
     exit_code=proc.wait(timeout=10)
    except BaseException as cleanup:failure+="; cleanup: "+str(cleanup)[:1000]
  wall=time.monotonic()-start
  out.flush();os.fsync(out.fileno());err.flush();os.fsync(err.fileno())
 with paths["exit"].open("xb") as f:
  f.write((str(exit_code)+"\n").encode());f.flush();os.fsync(f.fileno())
 outer=dict(schema="m194h-stage-external-v1",command=command,source=source,exit_code=exit_code,
  timeout_terminated=timedout,elapsed_wall_seconds=wall,stdout=ref(paths["stdout"]),stderr=ref(paths["stderr"]),exit=ref(paths["exit"]),
  stdout_bytes=paths["stdout"].stat().st_size,stderr_bytes=paths["stderr"].stat().st_size,
  scope="Complete directly launched controller interval and actual exit when observed; raw streams. Inner controller owns child Jobs. No complete parent CPU inference from wall. Failure="+str(failure))
 raw=(json.dumps(outer,indent=2)+"\n").encode()
 with paths["outer"].open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
 print(json.dumps(dict(exit_code=exit_code,elapsed_wall_seconds=wall,timeout_terminated=timedout,artifacts={k:ref(p) for k,p in paths.items()})),flush=True)
 assert paths["stdout"].stat().st_size<=8192 and paths["stderr"].stat().st_size<=32768 and len(raw)<=65536,"external cap; actual evidence retained"
 return exit_code if exit_code is not None and failure is None else 1
if __name__=="__main__":raise SystemExit(main())
