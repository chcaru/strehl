"""Seven fixed M194h scanner controls. SOURCE ONLY until independent release."""
import time
START=time.monotonic()
import argparse
import ast
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import traceback
import types

SELF=Path(__file__).resolve()
ROOT=SELF.parents[3]
DRIVER=SELF.parent.parent/"build-and-run.py"
OUT=SELF.parent/"scan-regression-1"
IDS=("stable","scratch-deletion","strict-deletion","oversize","reparse-bit","permission-onerror","restored")
KEEP=b"0123456789abcdef"
RACE=b"0123456789abcdef0123456789abcdef"
CAP=32768
ROWS=[]
SOURCES={}

def need(ok,message):
    if not ok:raise ValueError(message)

def check():
    need(time.process_time()<=9 and time.monotonic()-START<=18,"metadata live allowance")

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
def shared(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)

def read(path,cap,expected=None):
    path=Path(path)
    for part in (path,*path.parents):
        s=part.lstat()
        need(not s.st_file_attributes&0x400 and not stat.S_ISLNK(s.st_mode),"plain read ancestry")
    before=path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=cap,"bounded plain read")
    with path.open("rb") as stream:
        opened=os.fstat(stream.fileno());raw=stream.read(cap+1);after=os.fstat(stream.fileno())
    need(shared(before)==shared(opened) and identity(opened)==identity(after)
         and identity(before)==identity(path.stat()) and len(raw)==before.st_size,"same-buffer read")
    digest=sha(raw)
    if expected is not None:need(digest==expected,"source digest")
    return raw,dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=digest)

def publish(name,value):
    raw=encode(value);need(len(raw)<=CAP,"metadata receipt capacity")
    stage=OUT/"publication-stage.json";target=OUT/name
    with stage.open("wb") as stream:
        need(stream.write(raw)==len(raw),"short receipt write");stream.flush();os.fsync(stream.fileno())
    got,_=read(stage,CAP);need(got==raw,"receipt stage bytes")
    os.replace(stage,target)
    got,ref=read(target,CAP);need(got==raw,"receipt final bytes")
    return ref

def progress():
    return publish("progress.json",dict(schema="m194h-scan-control-progress-v1",rows=ROWS,sources=SOURCES))

def fixed_write(path,raw):
    need(path.parent==OUT/"fixture" and path.name in ("keep.bin","race.bin"),"fixed fixture path")
    with path.open("xb") as stream:
        need(stream.write(raw)==len(raw),"fixture full write");stream.flush();os.fsync(stream.fileno())
    need(read(path,32)[0]==raw,"fixture written identity")

def fixture_hashes(fixture):
    return {name:read(fixture/name,32)[1] for name in ("keep.bin","race.bin")}

def selected(raw):
    tree=ast.parse(raw,filename=str(DRIVER))
    names=("need","lexical","owned","scan")
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    need(tuple(node.name for node in nodes)==names,"closed scanner AST selection")
    module=ast.Module(body=nodes,type_ignores=[])
    namespace=dict(Path=Path,os=os,stat=stat,ROOT=ROOT)
    exec(compile(module,str(DRIVER),"exec"),namespace)
    return namespace,sha(ast.dump(module,include_attributes=False).encode())

def row(case,action):
    check();record=dict(id=case,passed=False);ROWS.append(record);progress()
    try:
        record["observation"]=action();record["passed"]=True
    except Exception as exc:
        record["error"]=dict(type=type(exc).__name__,text=str(exc)[:2048])
        raise
    finally:progress()

def rejected(action,kind,fragment):
    try:action()
    except Exception as exc:
        need(type(exc) is kind and fragment in str(exc),"expected exact refusal")
        return dict(type=type(exc).__name__,text=str(exc)[:2048])
    raise ValueError("destroyer did not refuse")

def controls(namespace):
    fixture=OUT/"fixture";fixture.mkdir()
    fixed_write(fixture/"keep.bin",KEEP);fixed_write(fixture/"race.bin",RACE)
    before=fixture_hashes(fixture);scanner=namespace["scan"]
    original_walk=os.walk;original_lstat=Path.lstat
    baseline={}
    def stable():
        value=scanner(fixture,48)
        need(value["files"]==2 and value["bytes"]==48 and value["initial_absent"] is False
             and value["observed_disappearances"]==0 and value["disappearance_samples"]==[]
             and value["tolerate_disappearance"] is False,"stable real fixture")
        baseline.update(value);return dict(scan=value,fixture=before)
    row(IDS[0],stable)
    def deletion(tolerant):
        reached=dict(enumerated=False,removed=False)
        def disappearing_walk(top,**kwargs):
            for directory,dirs,files in original_walk(top,**kwargs):
                if Path(directory)==fixture:
                    need(sorted(files)==["keep.bin","race.bin"],"real enumeration fixture")
                    reached["enumerated"]=True
                    need(read(fixture/"race.bin",32)[0]==RACE,"race bytes before deletion")
                    (fixture/"race.bin").unlink();reached["removed"]=True
                yield directory,dirs,files
        namespace["os"]=types.SimpleNamespace(path=os.path,walk=disappearing_walk)
        try:
            if tolerant:
                value=scanner(fixture,48,tolerate_disappearance=True)
                sample=value["disappearance_samples"]
                need(value["files"]==1 and value["bytes"]==16 and value["initial_absent"] is False
                     and value["observed_disappearances"]==1 and value["tolerate_disappearance"] is True
                     and len(sample)==1 and sample[0]==dict(operation="file-inspection",
                         path=str(fixture/"race.bin"),path_truncated=False),"actual scratch disappearance")
            else:
                value=rejected(lambda:scanner(fixture,48),FileNotFoundError,"file-inspection")
                need(str(fixture/"race.bin") in value["text"],"strict refusal path")
            need(all(reached.values()) and not (fixture/"race.bin").exists(),"deletion branch exercised")
            return dict(policy="scratch" if tolerant else "retained-strict",reached=reached,actual=value)
        finally:
            namespace["os"]=os
            if not (fixture/"race.bin").exists():fixed_write(fixture/"race.bin",RACE)
    row(IDS[1],lambda:deletion(True))
    row(IDS[2],lambda:deletion(False))
    def oversize():
        sizes=[read(fixture/name,32)[1]["bytes"] for name in ("keep.bin","race.bin")]
        need(sum(sizes)==48 and sum(sizes)>47,"oversize fixture power")
        return dict(actual_bytes=sum(sizes),limit=47,tolerate_disappearance=True,
                    refusal=rejected(lambda:scanner(fixture,47,tolerate_disappearance=True),
                                     ValueError,"file family capacity"))
    row(IDS[3],oversize)
    def reparse():
        reached=[False];target=fixture/"race.bin"
        def injected_lstat(path,*args,**kwargs):
            value=original_lstat(path,*args,**kwargs)
            if path==target:
                reached[0]=True
                return types.SimpleNamespace(st_mode=value.st_mode,
                                             st_file_attributes=value.st_file_attributes|0x400)
            return value
        Path.lstat=injected_lstat
        try:
            failure=rejected(lambda:scanner(fixture,48,tolerate_disappearance=True),
                             ValueError,"reparse/symlink path")
            need(reached[0] and str(target) in failure["text"],"reparse predicate reached")
            return dict(scope="Injected lstat reparse attribute on an actual ordinary fixture; no native junction.",
                        reached=True,refusal=failure)
        finally:Path.lstat=original_lstat
    row(IDS[4],reparse)
    def permission():
        reached=[False]
        def denied_walk(top,**kwargs):
            need(callable(kwargs.get("onerror")),"actual onerror callback supplied")
            reached[0]=True
            kwargs["onerror"](PermissionError(errno.EACCES,"fixed permission fixture",str(fixture)))
            raise ValueError("onerror swallowed PermissionError")
            yield
        namespace["os"]=types.SimpleNamespace(path=os.path,walk=denied_walk)
        try:
            failure=rejected(lambda:scanner(fixture,48,tolerate_disappearance=True),
                             PermissionError,"scan walk")
            need(reached[0] and str(fixture) in failure["text"],"permission callback reached")
            return dict(scope="Injected PermissionError delivered through the actual walk onerror callback; no ACL edit.",
                        reached=True,refusal=failure)
        finally:namespace["os"]=os
    row(IDS[5],permission)
    def restored():
        need(namespace["os"] is os and os.walk is original_walk and Path.lstat is original_lstat,
             "all scoped observation seams restored")
        after=fixture_hashes(fixture)
        need(after==before,"actual fixture hashes restored")
        value=scanner(fixture,48)
        need(value==baseline,"whole scan outcome restored")
        return dict(scan=value,fixture=after,full_outcome_equal=True,scope="Restoration, no performance claim.")
    row(IDS[6],restored)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--driver-sha256",required=True);parser.add_argument("--self-sha256",required=True)
    args=parser.parse_args()
    need(not OUT.exists(),"fresh fixed output")
    OUT.mkdir()
    publish("result.json",dict(schema="m194h-scan-regression-v1",status="INITIAL_INCOMPLETE",passed=False))
    value=dict(schema="m194h-scan-regression-v1",status="REFUSED",passed=False,rows=ROWS,sources=SOURCES,
               scope="Metadata scanner regression only; no compile, process, numerical, image, or corpus operation.",
               command=[sys.executable,*sys.orig_argv[1:]],
               resource_reservation=dict(cpu_seconds=10,wall_seconds=20,file_bytes=1<<20),
               publication_allowance=dict(cpu_seconds=1,wall_seconds=2))
    try:
        raw,SOURCES["driver"]=read(DRIVER,128<<10,args.driver_sha256)
        _,SOURCES["self"]=read(SELF,16<<10,args.self_sha256)
        namespace,value["selected_ast_sha256"]=selected(raw);progress()
        controls(namespace)
        need(tuple(item["id"] for item in ROWS)==IDS and all(item["passed"] for item in ROWS),"all seven visited")
        read(DRIVER,128<<10,args.driver_sha256);read(SELF,16<<10,args.self_sha256)
        check();value.update(status="PASS_METADATA_SCAN_REGRESSION_ONLY",passed=True)
    except Exception:
        text=traceback.format_exc()
        value["error"]=dict(text=text[-4096:],utf8_bytes=len(text.encode()),sha256=sha(text.encode()),truncated=len(text)>4096)
    value["actual_prepublication"]=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
    final=publish("result.json",value)
    advertisement=encode(dict(result=final,status=value["status"],passed=value["passed"]))
    need(len(advertisement)<=8192 and sys.stdout.buffer.write(advertisement)==len(advertisement),"full bounded stdout")
    sys.stdout.buffer.flush()
    return 0 if value["passed"] else 1

if __name__=="__main__":raise SystemExit(main())
