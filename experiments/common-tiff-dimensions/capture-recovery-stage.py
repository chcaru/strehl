"""Direct capture for additive controls/admission/render/verify; no build or generator."""
import time
START=time.monotonic();CPU=time.process_time()
from pathlib import Path
import argparse,hashlib,json,os,stat,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;WORK=HERE/"work"
SELF=Path(__file__).resolve();KIB=1024;MIB=1<<20
STAGES=("controls","recovery","render","verify")
READ=0;WRITTEN=0

def need(v,label):
    if not v:raise ValueError(label)
def encoded(v):return (json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def read_bound(path,cap,empty=False):
    global READ
    path=Path(os.path.abspath(path))
    for p in (path,*path.parents):
        s=p.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain capture ancestry")
    before=path.stat();need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,"bounded capture bytes")
    READ+=before.st_size+1;need(READ<=MIB,"finite capture read allowance")
    with path.open("rb") as f:
        first=os.fstat(f.fileno());raw=f.read(before.st_size+1);last=os.fstat(f.fileno())
    after=path.stat()
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0))
    full=lambda s:shared(s)+(s.st_ctime_ns,)
    need(full(before)==full(after) and full(first)==full(last) and shared(before)==shared(first)
         and len(raw)==before.st_size,"same capture byte buffer")
    return raw
def ref(path,cap=MIB,empty=False,raw=None):
    path=Path(os.path.abspath(path));raw=read_bound(path,cap,empty) if raw is None else raw
    return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(path,raw,cap):
    global WRITTEN
    WRITTEN+=len(raw);need(WRITTEN<=MIB,"finite capture write allowance")
    need(len(raw)<=cap,"bounded capture publication")
    with path.open("xb") as f:need(f.write(raw)==len(raw),"whole capture write");f.flush();os.fsync(f.fileno())
    need(read_bound(path,cap,empty=not raw)==raw,"capture publication readback")
    return ref(path,cap,empty=not raw,raw=raw)
def strict(raw):
    def pairs(rows):
        d={}
        for k,v in rows:need(k not in d,"duplicate capture JSON key");d[k]=v
        return d
    def bad(v):raise ValueError("nonfinite capture JSON")
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)

def main():
    global WRITTEN
    parser=argparse.ArgumentParser();parser.add_argument("stage",choices=STAGES)
    parser.add_argument("--release-sha256",required=True);args=parser.parse_args();stage=args.stage
    need(os.name=="nt" and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
         and Path.cwd().resolve()==ROOT,"isolated Windows capture")
    release=WORK/f"{stage}-recovery-release-1.json";raw=read_bound(release,128*KIB);r=strict(raw)
    sha=hashlib.sha256(raw).hexdigest();need(sha==args.release_sha256,"actual constructed release identity")
    if stage=="controls":
        need(set(r)=={"schema","source_bindings","inputs","command"}
             and r["schema"]=="common-tiff-dimensions-recovery-controls-release-v1","closed controls release")
        source=HERE/"recovery-controls.py";output=WORK/"recovery-controls-1"
    else:
        need(set(r)=={"schema","stage","source_bindings","inputs","command","children","executable","fixtures","run_bundle","prerequisites"}
             and r["schema"]=="common-tiff-dimensions-stage-release-v2" and r["stage"]==stage,"closed recovery stage release")
        source=HERE/"run-recovery-stage.py";output=HERE/f"{stage}-1"
    sources=r["source_bindings"]
    own=ref(SELF,32*KIB);pin=ref(source,128*KIB)
    for v in (own,pin):
        need({k:v[k] for k in ("bytes","sha256")}==sources[v["path"]],"actual capture and child source")
    frozen=strict(read_bound(WORK/"recovery-source-freeze-1.json",128*KIB))
    need(frozen["schema"]=="common-tiff-dimensions-recovery-source-freeze-v1"
         and encoded(frozen["source_bindings"])==encoded(sources),"same frozen recovery namespace")
    receipt=strict(read_bound(WORK/f"{stage}-recovery-preparation-1.json",128*KIB))
    need(receipt["schema"]=="common-tiff-dimensions-recovery-preparation-v1"
         and receipt["status"]=="PREPARED_UNRUN_RELEASE" and receipt["stage"]==stage
         and receipt["error"] is None and receipt["release"]==ref(release,128*KIB,raw=raw)
         and receipt["charged_cpu_seconds"]==10 and receipt["charged_wall_seconds"]==20,
         "actual completed once-only metadata constructor")
    if stage=="controls":
        expected=[sys.executable,"-I","-S","-B",str(source),"--source-sha256",pin["sha256"],"--output",str(output)]
    else:expected=[sys.executable,"-I","-S","-B",str(source),"--release",str(release),"--release-sha256",sha]
    command=[sha if x=="ACTUAL_RELEASE_SHA256" else x for x in r["command"]]
    need(command==expected,"exact reviewed child command")
    need(read_bound(release,128*KIB)==raw,"release stable after source checks")
    paths={k:WORK/f"{stage}-recovery-external-1-{suffix}" for k,suffix in
           (("stdout","stdout.bin"),("stderr","stderr.bin"),("exit","exit.txt"),("outer","outer.json"))}
    need(not output.exists() and all(not p.exists() for p in paths.values()),"fresh once-only captured stage")
    maxwall={"controls":10,"recovery":20,"render":240,"verify":120}[stage]
    outcap=128*KIB if stage=="controls" else 8*KIB;errcap=16*KIB if stage=="controls" else 32*KIB
    timedout=False;code=None;failure=None;p=None;childwall=0.0
    with paths["stdout"].open("xb") as out,paths["stderr"].open("xb") as err:
        childstart=time.monotonic()
        cleanup_deadline=min(childstart+15,START+18) if stage=="controls" else childstart+maxwall+5
        try:
            p=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
            while p.poll() is None:
                now=time.monotonic()
                if now-childstart>=maxwall:
                    timedout=True;p.kill();break
                if paths["stdout"].stat().st_size>outcap or paths["stderr"].stat().st_size>errcap:
                    failure="raw stream extent exceeded";p.kill();break
                time.sleep(.02)
            code=p.wait(timeout=max(.001,cleanup_deadline-time.monotonic()))
        except Exception as e:
            failure=type(e).__name__+": "+str(e)[:512]
            if p is not None:
                try:
                    if p.poll() is None:p.kill()
                    # The second path has no renewed5s allowance.
                    if time.monotonic()<cleanup_deadline:
                        code=p.wait(timeout=cleanup_deadline-time.monotonic())
                    else:code=p.poll()
                except Exception as final:failure+="; cleanup: "+type(final).__name__+": "+str(final)[:256]
        finally:
            childwall=time.monotonic()-childstart
            out.flush();os.fsync(out.fileno());err.flush();os.fsync(err.fileno())
    # Exact streams and metadata share one1MiB read/write lane. Admission retains the smaller stream caps.
    streams={k:read_bound(paths[k],256*KIB,empty=True) for k in ("stdout","stderr")}
    WRITTEN+=sum(len(b) for b in streams.values());need(WRITTEN<=MIB,"actual redirected raw write allowance")
    if len(streams["stdout"])>outcap or len(streams["stderr"])>errcap:failure="raw stream extent exceeded"
    exitraw=(str(code)+"\n").encode() if code is not None else b"NOT_STARTED_OR_UNCOLLECTED\n"
    exitref=write(paths["exit"],exitraw,KIB)
    value=dict(schema="common-tiff-dimensions-recovery-controls-external-v1" if stage=="controls"
               else "common-tiff-dimensions-stage-external-v2",
        command=command,source=pin,exit_code=code,timeout_terminated=timedout,elapsed_wall_seconds=childwall,
        stdout=ref(paths["stdout"],raw=streams["stdout"]),stderr=ref(paths["stderr"],raw=streams["stderr"]),
        exit=exitref,stdout_bytes=len(streams["stdout"]),stderr_bytes=len(streams["stderr"]),
        scope="Actual directly launched child interval and exit; raw streams. Recovery controller owns descendant Jobs. No CPU inferred from wall.")
    if stage=="controls":
        cpu=time.process_time()-CPU;wall=time.monotonic()-START
        admitted=failure is None and code==0 and not timedout and childwall<=10 and cpu+1<=5 and wall+2<=20 and wall-childwall+2<=10
        value["capture_accounting"]=dict(parent_cpu_sample=cpu,whole_wall_sample=wall,
          publication_allowance=dict(cpu_seconds=1,wall_seconds=2),
          reserved=dict(cpu_seconds=5,overhead_wall_seconds=10,whole_wall_seconds=20),
          admitted=admitted,error=failure,
          scope="Wrapper samples plus reserved publication; actual complete wrapper interval is retained separately by root external capture.")
    else:admitted=failure is None and code==0 and not timedout and childwall<=maxwall
    outer=write(paths["outer"],encoded(value),64*KIB)
    advertised=encoded(dict(stage=stage,exit_code=code,timeout_terminated=timedout,child_wall_seconds=childwall,outer=outer))
    WRITTEN+=len(advertised);need(WRITTEN<=MIB,"capture advertisement write charge")
    need(len(advertised)<=8*KIB and sys.stdout.buffer.write(advertised)==len(advertised),"whole capture advertisement")
    sys.stdout.buffer.flush()
    if stage=="controls":
        need(time.process_time()-CPU<=5 and time.monotonic()-START<=20,"actual capture publication within reserved phase")
    return 0 if admitted else 1

if __name__=="__main__":raise SystemExit(main())
