"""Root external capture of one owned stage; no retry or science implementation."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time,os,stat
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def need(v,s):
 if not v:raise ValueError(s)
def read_bound(p,cap=64<<20,empty=False):
 p=Path(os.path.abspath(p))
 for q in (p,*p.parents):
  s=q.lstat()
  need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain source ancestry")
 before=p.stat()
 need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,"bounded declared extent")
 with p.open("rb") as stream:
  opened=os.fstat(stream.fileno());b=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
 final=p.stat()
 shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0))
 full=lambda s:shared(s)+(s.st_ctime_ns,)
 need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
      and len(b)==before.st_size and len(b)<=cap,"same authenticated buffer")
 return b
def ref(p,empty=False,cap=64<<20):
 b=read_bound(p,cap,empty);return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 a=argparse.ArgumentParser();a.add_argument("stage",choices=("build-on","build-off","controls","native","verify"));args=a.parse_args();stage=args.stage;attempt=2 if stage=="build-on" else 1
 work=HERE/"work";release=work/(stage+"-release-"+str(attempt)+".json");b=read_bound(release,1<<20)
 r=json.loads(b);assert r["schema"]=="native-sensor-transfer-stage-release-v1" and r["stage"]==stage
 sha=hashlib.sha256(b).hexdigest()
 source=HERE/"run-stage.py";pin=ref(source)
 assert {k:pin[k] for k in ("bytes","sha256")}==r["source_bindings"][pin["path"]]
 own=ref(Path(__file__).resolve());assert {k:own[k] for k in ("bytes","sha256")}==r["source_bindings"][own["path"]]
 command=[sha if x=="ACTUAL_RELEASE_SHA256" else x for x in r["command"]]
 assert command==[sys.executable,"-I","-S","-B",str(source),"--release",str(release),"--release-sha256",sha]
 paths={k:work/(stage+"-external-"+str(attempt)+"-"+suffix) for k,suffix in [("stdout","stdout.bin"),("stderr","stderr.bin"),("exit","exit.txt"),("outer","outer.json")]}
 assert all(not p.exists() for p in paths.values()) and not (HERE/(stage+"-"+str(attempt))).exists()
 timedout=False
 with paths["stdout"].open("xb") as out,paths["stderr"].open("xb") as err:
  start=time.monotonic();p=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
  try:code=p.wait(timeout={"build-on":300,"build-off":300,"controls":180,"native":1200,"verify":900}[stage])
  except subprocess.TimeoutExpired:timedout=True;p.kill();code=p.wait(timeout=15)
  wall=time.monotonic()-start
  out.flush();os.fsync(out.fileno());err.flush();os.fsync(err.fileno())
 with paths["exit"].open("xb") as f:f.write((str(code)+"\n").encode())
 value=dict(schema="native-sensor-transfer-stage-external-v1",command=command,source=pin,exit_code=code,
 timeout_terminated=timedout,elapsed_wall_seconds=wall,stdout=ref(paths["stdout"],empty=True,cap=8<<10),stderr=ref(paths["stderr"],empty=True,cap=32<<10),exit=ref(paths["exit"]),
 stdout_bytes=paths["stdout"].stat().st_size,stderr_bytes=paths["stderr"].stat().st_size,
 scope="Complete directly launched controller interval and actual exit; controller owns descendant Jobs. Raw controller stdout/stderr. No whole CPU inference from wall.")
 raw=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
 need(len(raw)<=64<<10,"bounded outer before publication")
 with paths["outer"].open("xb") as f:need(f.write(raw)==len(raw),"full outer write")
 print(json.dumps(dict(stage=stage,exit_code=code,whole_wall_seconds=wall,timeout_terminated=timedout,outer=ref(paths["outer"]))),flush=True)
 assert len(raw)<=64<<10 and value["stdout_bytes"]<=8<<10 and value["stderr_bytes"]<=32<<10
 return code
if __name__=="__main__":raise SystemExit(main())
