"""M194h source-bound build/component/render driver. No work on import.
SOURCE ONLY until the root's exact independently reviewed release.
"""
import time
START=time.monotonic()
import argparse
import ast
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import shutil
import subprocess
import sys
import traceback
import types

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
KIB=1024;MIB=1<<20;GIB=1<<30
SCHEMA="m194h-owned-stage-release-v1"
FEATURE="m194h-pedestal-causality"
TARGET=ROOT/"target/m194h-pedestal-causality-1"
PROCESS=ROOT/"experiments/m193c-output-grid/bounded-process.py"
HARNESS=ROOT/"experiments/m12-scorecard/m12-harness.py"
PROCESS_SHA="47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b"
CORE_TEST="pyramid::m194h::controls::fixed_threshold_null_and_observer_controls"
CLI_TEST="merge_cmd::known_scene_benchmark::noise_pupil_bridge::pedestal_causality::m194h_fixed_pedestal_case"
STAGES={
 "build":dict(cpu_seconds=300,wall_seconds=240,committed_bytes=8*GIB,file_bytes=128*MIB,scratch_bytes=4*GIB),
 "components":dict(cpu_seconds=60,wall_seconds=60,committed_bytes=GIB,file_bytes=2*MIB,scratch_bytes=0),
 "render":dict(cpu_seconds=120,wall_seconds=180,committed_bytes=GIB,file_bytes=16*MIB,scratch_bytes=0)}
OUTPUTS={k:HERE/(k+"-1" if k!="render" else "subject-1") for k in STAGES}
FIXED_ENV={"RAYON_NUM_THREADS":"2","STREHL_PYRAMID_WORKERS":"2","STREHL_DEFECT":"off","STREHL_FIX_CA":"off","STREHL_FULLRES_GATHER":"1"}
JOB_NAMES=("kernel32","ntdll","CREATE_SUSPENDED","JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE",
 "JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS","JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS",
 "IO_COUNTERS","JOBOBJECT_BASIC_LIMIT_INFORMATION","JOBOBJECT_EXTENDED_LIMIT_INFORMATION",
 "JOBOBJECT_BASIC_ACCOUNTING_INFORMATION","create_process_job","assign_process_to_job","job_accounting","job_memory")
JOB_SIGNATURES=tuple(f"{a}.{b}.{c}" for a,b in (
 ("kernel32","CloseHandle"),("kernel32","CreateJobObjectW"),("kernel32","AssignProcessToJobObject"),
 ("kernel32","SetInformationJobObject"),("kernel32","QueryInformationJobObject"),("ntdll","NtResumeProcess"))
 for c in ("argtypes","restype"))
TERMINAL_CAP=64*KIB
TAIL_CPU=2;TAIL_WALL=3;CLEANUP_WALL=12
CASE_CAPS={"plan.json":128*KIB,"trace.bin":128*KIB,"trace.json":16*KIB,"output.tif":512*KIB,
 "result.json":32*KIB,"result-stage.json":32*KIB,"failure.json":8*KIB}
REQUIRED=(".gitattributes","build-and-run.py","build-and-execution-contract.md","resource-ledger.json",
 "experiment-decision.md","core-hook.rs","component-controls.rs","production-bridge.rs","preregister.md",
 "independent-verification-design.md","independent-verify.py")

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def finite(value):return type(value) in (int,float) and math.isfinite(value) and value>=0
def strict(raw):
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,"duplicate JSON key");result[key]=value
        return result
    result=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:need(False,"nonfinite JSON"))
    def visit(value):
        if type(value) is float:need(math.isfinite(value),"nonfinite JSON")
        elif type(value) is list:
            for item in value:visit(item)
        elif type(value) is dict:
            for item in value.values():visit(item)
    visit(result);return result
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def lexical(path):
    path=Path(os.path.abspath(path))
    need(len(str(path))<=384 and str(path).isascii(),"declared ASCII path width")
    for part in (path,*path.parents):
        if part.exists():
            s=part.lstat()
            need(not s.st_file_attributes&0x400 and not stat.S_ISLNK(s.st_mode),"reparse/symlink path")
    return path
def owned(path):
    path=lexical(path)
    need(path.is_relative_to(ROOT),"repository-owned path")
    need(path.resolve()==path,"canonical path")
    return path
def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
def read(path,cap,expected=None,keep=True,check=lambda:None):
    path=lexical(path);before=path.stat()
    need(stat.S_ISREG(before.st_mode) and 0<=before.st_size<=cap,"plain bounded file")
    h=hashlib.sha256();parts=[];size=0
    with path.open("rb") as stream:
        need(identity(before)==identity(os.fstat(stream.fileno())),"open file identity")
        while True:
            check();raw=stream.read(min(MIB,cap-size+1))
            if not raw:break
            size+=len(raw);need(size<=cap,"bounded file changed extent");h.update(raw)
            if keep:parts.append(raw)
        after=os.fstat(stream.fileno())
    need(identity(before)==identity(after)==identity(path.stat()) and size==before.st_size,"stable file identity")
    ref=dict(path=str(path),bytes=size,sha256=h.hexdigest())
    if expected is not None:
        need(type(expected) is dict and set(expected)=={"path","bytes","sha256"},"typed FileRef")
        need(type(expected["bytes"]) is int and type(expected["sha256"]) is str,"typed FileRef values")
        need(lexical(ROOT/expected["path"])==path and size==expected["bytes"] and ref["sha256"]==expected["sha256"],"FileRef identity")
    return (b"".join(parts) if keep else None),ref
def source_ref(path):return owned(path).relative_to(ROOT).as_posix()
def ref_binding(ref):return {k:ref[k] for k in ("bytes","sha256")}
def source_bytes(path,bindings,check=lambda:None):
    key=source_ref(path);pin=bindings[key]
    data,ref=read(path,4*MIB,dict(path=key,**pin),check=check)
    need(ref["bytes"]>0,"positive source");return data
def write_new(path,data,cap):
    path=owned(path);need(len(data)<=cap and not path.exists() and path.parent.is_dir(),"fresh bounded write")
    with path.open("xb") as stream:
        need(stream.write(data)==len(data),"short write");stream.flush();os.fsync(stream.fileno())
    observed,ref=read(path,cap);need(observed==data,"write readback")
    return ref
def atomic(path,value,cap=TERMINAL_CAP):
    data=encoded(value);need(len(data)<=cap,"terminal encoding capacity")
    data=data.rstrip(b"\n")+b" "*(cap-len(data))+b"\n"
    stage=path.with_name("result-stage.json")
    # Only this owned reserved stage can be replaced; no retry loop.
    if stage.exists():need(stage.stat().st_size<=cap,"terminal stage extent")
    with stage.open("wb") as stream:
        need(stream.write(data)==len(data),"short terminal write");stream.flush();os.fsync(stream.fileno())
    got,_=read(stage,cap);need(got==data,"terminal stage readback")
    os.replace(stage,path)
    got,ref=read(path,cap);need(got==data,"canonical terminal readback");return ref
def error_value():
    text=traceback.format_exc();return dict(text=text[-6000:],utf8_bytes=len(text.encode()),sha256=sha(text.encode()),truncated=len(text)>6000)
def job_cpu(value):
    need(type(value) is dict,"Job accounting record")
    keys=("total_user_100ns","total_kernel_100ns","total_cpu_100ns","active_processes")
    need(all(type(value.get(k)) is int and value[k]>=0 for k in keys),"typed Job accounting")
    need(value["total_cpu_100ns"]==value["total_user_100ns"]+value["total_kernel_100ns"],"Job CPU components")
    return value["total_cpu_100ns"]/1e7
def clean_env():
    blocked={"RUSTFLAGS","CARGO_ENCODED_RUSTFLAGS","CARGO_TARGET_DIR","RUSTC_WRAPPER","RUSTC_WORKSPACE_WRAPPER","RUSTC"}
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(("STREHL_","M194H_","RAYON_","OMP_","OPENBLAS_","MKL_","NUMEXPR_")) and k.upper() not in blocked}
    env.update(FIXED_ENV);env["CARGO_NET_OFFLINE"]="true";return env
def scan(root,limit):
    if not root.exists():return dict(files=0,bytes=0)
    total=count=0
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in dirs:owned(Path(directory)/name)
        for name in files:
            p=owned(Path(directory)/name);s=p.stat()
            need(stat.S_ISREG(s.st_mode),"plain output file");count+=1;total+=s.st_size
            need(total<=limit,"file family capacity")
    return dict(files=count,bytes=total)

def admit_work(work,caps,cpu_reserve=TAIL_CPU,wall_reserve=TAIL_WALL):
    need(all(finite(work[k]) for k in ("cpu_seconds","wall_seconds")),"typed work")
    need(work["cpu_seconds"]<=caps["cpu_seconds"]-cpu_reserve,"reserved stage CPU")
    need(work["wall_seconds"]<=caps["wall_seconds"]-wall_reserve,"reserved stage wall")

def metadata_controls(output):
    directory=output/"metadata-controls";directory.mkdir()
    rows=[]
    progress=directory/"progress.json"
    def retain():atomic(progress,dict(schema="m194h-driver-metadata-controls-v1",rows=rows),8*KIB)
    def test(name,call,error=None):
        row=dict(id=name,passed=False,error=None);rows.append(row);retain()
        try:
            call()
            need(error is None,"fault did not reject")
            row["passed"]=True
        except ValueError as exc:
            row["error"]=str(exc);row["passed"]=error is not None and str(exc)==error
            if not row["passed"]:raise
        finally:retain()
    actual=dict(total_user_100ns=900000000,total_kernel_100ns=50000000,total_cpu_100ns=950000000,active_processes=0)
    test("typed-job-positive",lambda:need(job_cpu(actual)==95,"positive Job value"))
    for name,key,value,error in (
        ("wrong-total","total_cpu_100ns",950000001,"Job CPU components"),
        ("negative-user","total_user_100ns",-1,"typed Job accounting"),
        ("bool-active","active_processes",False,"typed Job accounting")):
        fault=dict(actual);fault[key]=value
        test(name,lambda fault=fault:job_cpu(fault),error)
    caps=dict(cpu_seconds=100,wall_seconds=10)
    test("combined-cpu-positive",lambda:admit_work(dict(cpu_seconds=4+95,wall_seconds=1),caps,0,0))
    test("combined-cpu-overrun",lambda:admit_work(dict(cpu_seconds=6+95,wall_seconds=1),caps,0,0),"reserved stage CPU")
    test("json-finite-overflow",lambda:strict(b'{"v":1e999}'),"nonfinite JSON")
    test("json-duplicate",lambda:strict(b'{"v":1,"v":2}'),"duplicate JSON key")
    slot=directory/"publication.json"
    original=atomic(slot,dict(status="POSITIVE_METADATA_FIXTURE"),8*KIB)
    test("terminal-overflow-preserves-prior",lambda:atomic(slot,dict(status="REFUSED",detail="x"*(9*KIB)),8*KIB),"terminal encoding capacity")
    _,after=read(slot,8*KIB)
    need(after==original,"overflow left original canonical unchanged")
    refused=atomic(slot,dict(status="REFUSED_METADATA_FIXTURE"),8*KIB)
    restored=atomic(slot,dict(status="POSITIVE_METADATA_FIXTURE"),8*KIB)
    need(restored==original,"restored actual slot identity")
    test("same-slot-restoration",lambda:need(restored==original,"restored actual slot identity"))
    value=dict(schema="m194h-driver-metadata-controls-v1",status="PASS_METADATA_SEAMS_ONLY",rows=rows,
               fixture=dict(original=original,refused_bytes_sha256=refused["sha256"],restored=restored),
               scope="Injected arithmetic/Job records and actual bounded metadata writes; no OS/process or scientific commissioning.")
    return write_new(directory/"result.json",encoded(value),16*KIB)

class Budget:
    def __init__(self,stage,output):
        self.stage=stage;self.caps=STAGES[stage];self.output=output
        self.completed_cpu=0.;self.live_cpu=0.;self.complete=True;self.accounting_error=None
        self.last_scan=0.;self.inventory=None;self.scratch=None
    def observe(self,value):
        try:
            cpu=job_cpu(value);need(cpu>=self.live_cpu,"monotone live Job CPU");self.live_cpu=cpu
        except Exception as exc:self.accounting_error=repr(exc)
        return value
    def work(self):
        parent=time.process_time()
        return dict(parent_cpu_seconds=parent,completed_child_cpu_seconds=self.completed_cpu,
                    live_child_cpu_seconds=self.live_cpu,cpu_seconds=parent+self.completed_cpu+self.live_cpu,
                    wall_seconds=time.monotonic()-START,cpu_accounting_complete=self.complete and self.accounting_error is None)
    def check(self,force=False):
        need(self.accounting_error is None,"live Job accounting invalid")
        w=self.work()
        admit_work(w,self.caps)
        if force or time.monotonic()-self.last_scan>=.25:
            self.inventory=scan(self.output,self.caps["file_bytes"]-3*TERMINAL_CAP)
            if self.stage=="build":self.scratch=scan(TARGET,self.caps["scratch_bytes"])
            self.last_scan=time.monotonic()
    def limits(self,index):
        self.check(True);w=self.work()
        wall=min(20 if self.stage=="render" else 10 if self.stage=="build" and index>=2 else self.caps["wall_seconds"],
                 self.caps["wall_seconds"]-w["wall_seconds"]-TAIL_WALL-CLEANUP_WALL)
        cpu=min(20 if self.stage=="render" else self.caps["cpu_seconds"],
                self.caps["cpu_seconds"]-w["cpu_seconds"]-TAIL_CPU)
        need(wall>0 and cpu>0,"remaining stage launch envelope")
        return dict(wall_seconds=wall,cpu_seconds=cpu,log_bytes=16*MIB if self.stage=="build" and index<2 else 64*KIB,
                    committed_bytes=self.caps["committed_bytes"])

def load_process(bindings):
    data=source_bytes(PROCESS,bindings);need(sha(data)==PROCESS_SHA,"immutable owned process source")
    module=types.ModuleType("m194h_owned_process");module.__file__=str(PROCESS)
    exec(compile(data,str(PROCESS),"exec"),module.__dict__)
    tree=ast.parse(source_bytes(HARNESS,bindings),str(HARNESS));nodes=[];seen=set();names=set(JOB_NAMES+JOB_SIGNATURES)
    for node in tree.body:
        if isinstance(node,ast.ImportFrom) and node.module=="__future__":nodes.append(node);continue
        name=node.name if isinstance(node,(ast.FunctionDef,ast.ClassDef)) else None
        if isinstance(node,ast.Assign) and len(node.targets)==1:
            target=node.targets[0]
            name=target.id if isinstance(target,ast.Name) else ast.unparse(target) if isinstance(target,ast.Attribute) else None
        if name in names:
            need(name not in seen,"unique Job declaration");seen.add(name);nodes.append(node)
    need(seen==names,"closed Job AST dependency selection")
    api=types.ModuleType("m194h_owned_job");api.__dict__.update(ctypes=ctypes,wt=wt,subprocess=subprocess)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HARNESS),"exec"),api.__dict__)
    return module,api

def source_closure(bindings,check):
    paths={ROOT/"Cargo.toml",ROOT/"Cargo.lock",ROOT/"crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt"}
    for base,dirs,files in os.walk(ROOT/"crates"):
        dirs[:]=[d for d in dirs if d not in ("target",".git")]
        for name in files:
            if name.endswith(".rs") or name=="Cargo.toml":paths.add(owned(Path(base)/name))
    pending=[(p,ROOT/"crates"/p.relative_to(ROOT).parts[1]) for p in paths if p.suffix==".rs"]
    seen=set()
    while pending:
        path,crate=pending.pop()
        if (path,crate) in seen:continue
        seen.add((path,crate));text=source_bytes(path,bindings,check).decode("utf8")
        names=re.findall(r'^\s*include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)',text,re.M)
        targets=[owned(crate/name.lstrip("/")) for name in names]
        targets += [owned(path.parent/name) for name in re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]',text,re.M)]
        for p in targets:paths.add(p);pending.append((p,crate))
    need(all(source_ref(p) in bindings for p in paths),"complete current compiled source closure")
    return dict(files=len(paths),canonical_sha256=sha(encoded({source_ref(p):bindings[source_ref(p)] for p in sorted(paths)})))
def expected_children(stage,binaries):
    if stage=="build":
        prefix=["cargo","test"]
        return [prefix+["-p","strehl-core","--lib","--features",FEATURE,"--target-dir",str(TARGET),"--no-run","--message-format=json-render-diagnostics","--locked","--offline"],
                prefix+["-p","strehl-cli","--bin","strehl","--features",FEATURE,"--target-dir",str(TARGET),"--no-run","--message-format=json-render-diagnostics","--locked","--offline"],
                [str(OUTPUTS["build"]/"core-tests.exe"),"--list"],
                [str(OUTPUTS["build"]/"cli-tests.exe"),"--list"]]
    test=CORE_TEST if stage=="components" else CLI_TEST
    key="core" if stage=="components" else "cli"
    command=[str(owned(ROOT/binaries[key]["path"])),"--exact",test,"--ignored","--test-threads=1","--nocapture"]
    return [command] if stage=="components" else [command for _ in range(12)]

def authority(args):
    need(os.name=="nt" and Path.cwd().resolve()==ROOT,"Windows repository cwd")
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"isolated stdlib controller")
    path=owned(args.release);raw,ref=read(path,MIB)
    need(ref["bytes"]>0 and ref["sha256"]==args.release_sha256,"actual release SHA")
    release=strict(raw)
    need(set(release)=={"schema","stage","source_bindings","inputs","command","children","binaries","subject_grant","prerequisites"} and release["schema"]==SCHEMA,"closed stage release")
    stage=release["stage"];need(stage in STAGES,"stage")
    command=[args.release_sha256 if x=="ACTUAL_RELEASE_SHA256" else x for x in release["command"]]
    expected=[str(Path(sys.executable)),"-I","-S","-B",str(SELF),"--release",str(path),"--release-sha256",args.release_sha256]
    need(command==sys.orig_argv==expected and len(encoded(command))<=4*KIB,"exact controller command")
    sources=release["source_bindings"]
    need(type(sources) is dict and sources,"source bindings")
    total=0;resolved=set()
    for key,pin in sources.items():
        need(type(key) is str and type(pin) is dict and set(pin)=={"bytes","sha256"},"source shape")
        need(type(pin["bytes"]) is int and 0<pin["bytes"]<=4*MIB and re.fullmatch("[0-9a-f]{64}",pin["sha256"]),"positive source bounds")
        p=owned(ROOT/key);need(source_ref(p)==key and p not in resolved,"unique canonical source")
        total+=pin["bytes"];resolved.add(p)
    need(total<=16*MIB,"source aggregate")
    need(all(source_ref(HERE/name) in sources for name in REQUIRED) and all(source_ref(p) in sources for p in (PROCESS,HARNESS)),"mandatory source closure")
    output=OUTPUTS[stage];need(not output.exists(),"fresh stage output")
    output.mkdir()
    budget=Budget(stage,output)
    result=dict(schema="m194h-owned-stage-v1",status="INITIAL_INCOMPLETE",stage=stage,release=ref,invocation=sys.orig_argv,
                children=[],artifacts={},prerequisites={},work=None,error=None,finalization_errors=[],
                accounting_scope="parent process CPU plus each owned child Job once; final parent publication is externally bounded",
                limits=STAGES[stage],tail_allowance=dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL))
    atomic(output/"result.json",result)
    return release,ref,output,budget,result

def same_ref(a,b):
    return (type(a) is dict and type(b) is dict and set(a)==set(b)=={"path","bytes","sha256"}
            and type(a["bytes"]) is int and type(b["bytes"]) is int
            and lexical(ROOT/a["path"])==lexical(ROOT/b["path"]) and ref_binding(a)==ref_binding(b))
def stage_bundle(bundle,stage,budget,sources):
    roles={"result":TERMINAL_CAP,"tail":8*KIB,"outer":64*KIB,"stdout":8*KIB,"stderr":32*KIB,"exit":KIB}
    need(type(bundle) is dict and set(bundle)==set(roles),"closed prerequisite bundle")
    values={};buffers={}
    for key,cap in roles.items():
        r=bundle[key];raw,_=read(ROOT/r["path"],cap,r,check=budget.check);buffers[key]=raw
        if key in ("result","tail","outer","stdout"):values[key]=strict(raw)
    result,tail,outer,advertisement=(values[k] for k in ("result","tail","outer","stdout"))
    need(lexical(ROOT/bundle["result"]["path"])==OUTPUTS[stage]/"result.json"
         and lexical(ROOT/bundle["tail"]["path"])==OUTPUTS[stage]/"parent-tail.json","fixed prior stage terminal paths")
    need(set(outer)=={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds","stdout","stderr","exit","stdout_bytes","stderr_bytes","scope"}
         and outer["schema"]=="m194h-stage-external-v1","external schema")
    need(type(outer["exit_code"]) is int and outer["exit_code"]==0 and outer["timeout_terminated"] is False
         and buffers["exit"].strip()==b"0","actual prior exit")
    need(outer["command"]==result["invocation"],"actual prior command")
    need(same_ref(outer["source"],dict(path=source_ref(SELF),**sources[source_ref(SELF)])),"prior executed source")
    for key in ("stdout","stderr","exit"):need(same_ref(outer[key],bundle[key]),"external raw association")
    need(type(outer["stdout_bytes"]) is int and type(outer["stderr_bytes"]) is int
         and outer["stdout_bytes"]==len(buffers["stdout"]) and outer["stderr_bytes"]==len(buffers["stderr"]),"raw extents")
    need(result["schema"]=="m194h-owned-stage-v1" and result["stage"]==stage
         and result["status"]=="COMPLETE_STAGE_UNVERIFIED" and result["error"] is None
         and not result["finalization_errors"],"complete prior stage")
    need(set(advertisement)=={"status","result","tail"} and advertisement["status"]==result["status"]
         and same_ref(advertisement["result"],bundle["result"]) and same_ref(advertisement["tail"],bundle["tail"])
         and buffers["stdout"]==encoded(advertisement),"exact raw prior advertisement")
    need(tail["schema"]=="m194h-parent-publication-tail-v1" and same_ref(tail["result"],bundle["result"])
         and tail["cpu_accounting_complete"] is True and tail["live_child_cpu_seconds"]==0
         and tail["final_external_allowance"]==dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),"prior tail scope")
    for key in ("actual_parent_cpu_sample","whole_wall_sample","completed_child_cpu_seconds"):
        need(finite(tail[key]),"finite prior timing")
    need(finite(outer["elapsed_wall_seconds"]) and outer["elapsed_wall_seconds"]<=tail["whole_wall_sample"]+TAIL_WALL
         and outer["elapsed_wall_seconds"]<=STAGES[stage]["wall_seconds"],"actual prior whole wall")
    need(tail["actual_parent_cpu_sample"]+tail["completed_child_cpu_seconds"]+TAIL_CPU<=STAGES[stage]["cpu_seconds"],"prior complete sampled CPU plus tail")
    need(result["work"]["cpu_accounting_complete"] is True,"prior complete Job accounting")
    for key,cap in roles.items():read(ROOT/bundle[key]["path"],cap,bundle[key],keep=False,check=budget.check)
    return bundle

def prerequisites(release,budget):
    stage=release["stage"];prior=release["prerequisites"]
    expected=() if stage=="build" else ("build",) if stage=="components" else ("build","components")
    need(type(prior) is dict and set(prior)==set(expected),"stage prerequisite roles")
    for key in expected:stage_bundle(prior[key],key,budget,release["source_bindings"])
    need(type(release["inputs"]) is list and len(release["inputs"])<=64,"bounded input roles")
    need(all(type(r) is dict and set(r)=={"path","bytes","sha256"} and type(r["bytes"]) is int and 0<=r["bytes"]<=64*MIB for r in release["inputs"]) and sum(r["bytes"] for r in release["inputs"])<=128*MIB,"typed bounded input aggregate")
    need(any(lexical(ROOT/r["path"])==lexical(sys.executable) for r in release["inputs"]),"bound current Python executable")
    for r in release["inputs"]:read(ROOT/r["path"],64*MIB,r,keep=False,check=budget.check)
    if stage=="build":
        tool_paths={lexical(shutil.which(name) or "") for name in ("cargo","rustc")}
        need(len(tool_paths)==2 and tool_paths<={lexical(ROOT/r["path"]) for r in release["inputs"]},"bound resolved cargo/rustc commands")
    binaries=release["binaries"]
    need(type(binaries) is dict and set(binaries)==(set() if stage=="build" else {"core","cli"}),"binary roles")
    for r in binaries.values():read(ROOT/r["path"],32*MIB,r,keep=False,check=budget.check)
    if stage=="render":
        r=release["subject_grant"];raw,_=read(ROOT/r["path"],MIB,r,check=budget.check);g=strict(raw)
        need(set(g)=={"schema","source_bindings","noise_admission","matrix_index","quality_verification","binary","commands","cases"}
             and g["schema"]=="m194h-pedestal-causality-release-v1","exact science grant")
        need(g["binary"]==binaries["cli"] and g["source_bindings"]==release["source_bindings"],"same science source/binary")
        need(g["commands"]==[release["children"][0]] and len(g["cases"])==12,"science invocation/population")
        for i,c in enumerate(g["cases"]):
            seed,arm,obs=(743,("H","P","P0")[i//3],("off","on","placebo")[i%3]) if i<9 else (None,("H","P","P0")[i-9],"off")
            need(c==dict(ordinal=i,seed=seed,arm=arm,observation=obs,output_directory=f"experiments/m194h-pedestal-causality/subject-1/case-{i:02}"),"fixed case")
    else:need(release["subject_grant"] is None,"no science grant before render")
    return prior

def compile_artifact(log,index,output,budget):
    raw,_=read(log,16*MIB,check=budget.check)
    crate="strehl-core" if index==0 else "strehl-cli";name="strehl_core" if index==0 else "strehl"
    source=ROOT/f"crates/{crate}/src"/("lib.rs" if index==0 else "main.rs")
    need(("Compiling "+crate).encode() in raw,"fresh Compiling evidence")
    messages=[]
    for line in raw.splitlines():
        if line.startswith(b"{"):
            m=strict(line)
            if m.get("reason")=="compiler-artifact" and m.get("executable") and m.get("target",{}).get("name")==name:
                if Path(m["target"]["src_path"]).resolve()==source:
                    messages.append(m)
    need(len(messages)==1,"unique compiled test artifact");m=messages[0]
    need(len(encoded(m))<=8*KIB,"bounded compiler artifact record")
    need(m["profile"]["test"] is True and m["fresh"] is False and FEATURE in m["features"],"feature-enabled rebuilt artifact")
    need(Path(m["manifest_path"]).resolve()==ROOT/f"crates/{crate}/Cargo.toml","artifact manifest")
    origin=owned(m["executable"]);need(origin.is_relative_to(TARGET),"fresh target artifact")
    data,ref=read(origin,32*MIB,check=budget.check)
    copied=write_new(output/("core-tests.exe" if index==0 else "cli-tests.exe"),data,32*MIB)
    need(ref_binding(ref)==ref_binding(copied),"copied compiler bytes")
    return dict(compiler_message=m,original=ref,binary=copied)
def case_result(output,index,budget):
    directory=output/f"case-{index:02}";need(directory.is_dir(),"actual case directory")
    observed={}
    for p in directory.iterdir():
        need(p.is_file() and p.name in CASE_CAPS,"closed case files")
        _,r=read(p,CASE_CAPS[p.name],keep=False,check=budget.check);observed[p.name]=r
    need({"plan.json","trace.bin","trace.json","output.tif","result.json"}<=set(observed),"complete case artifacts")
    raw,_=read(directory/"result.json",32*KIB,observed["result.json"],check=budget.check);value=strict(raw)
    need(value["schema"]=="m194h-pedestal-case-v1" and value["status"]=="COMPLETE_CASE_UNVERIFIED"
         and value["science_complete"] is True and value["case"]["ordinal"]==index,"actual complete case")
    need(ref_binding(observed["output.tif"])=={k:value["output"][k] for k in ("bytes","sha256")},"actual output association")
    return dict(case=index,result=observed["result.json"],output=observed["output.tif"],trace=observed["trace.json"])

def child_call(process,api,command,env,index,output,budget,result):
    limits=budget.limits(index);old=api.job_accounting
    budget.live_cpu=0.;budget.complete=False
    def observed(job):return budget.observe(old(job))
    api.job_accounting=observed
    try:
        record=process.run(command,env,ROOT,output/f"child-{index:02}.log",api=api,check=budget.check,**limits)
    finally:api.job_accounting=old
    # A fixed terminal record is durable BEFORE any admission/cap assertion.
    ref=write_new(output/f"child-{index:02}.json",encoded(record),32*KIB)
    result["children"].append(ref)
    atomic(output/"result.json",result)
    if record["job_accounting"] is not None:
        terminal_cpu=job_cpu(record["job_accounting"])
        need(terminal_cpu>=budget.live_cpu,"terminal Job monotonicity")
        budget.completed_cpu+=terminal_cpu;budget.live_cpu=0.
    budget.complete=record["terminal_job_accounting"] is True
    need(budget.complete and record["job_accounting"]["active_processes"]==0,"complete child accounting")
    budget.check(True)
    need(record["error"] is None and not record["cleanup_errors"] and record["exit_code"]==0
         and record["direct_exit_observed"] and record["pipe_eof_observed"]
         and record["post_exit_drain"]["completed"],"owned child successful terminal")
    return record

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--release",required=True);parser.add_argument("--release-sha256",required=True);args=parser.parse_args()
    output=budget=result=release=None
    try:
        release,ref,output,budget,result=authority(args)
        sources=release["source_bindings"]
        for key in sources:source_bytes(ROOT/key,sources,budget.check)
        ledger=strict(source_bytes(HERE/"resource-ledger.json",sources,budget.check))
        need(ledger["stage_limits"]==STAGES,"fixed resource ledger")
        result["compiled_source_closure"]=source_closure(sources,budget.check)
        result["prerequisites"]=prerequisites(release,budget)
        need(release["children"]==expected_children(release["stage"],release["binaries"]),"exact child schedule")
        env=clean_env();result["environment"]={k:env.get(k) for k in (*FIXED_ENV,"CARGO_NET_OFFLINE","RUSTUP_TOOLCHAIN","RUSTUP_HOME","CARGO_HOME")}
        need(all(v is None or type(v) is str and len(v)<=1024 for v in result["environment"].values()) and len(encoded(result["environment"]))<=8*KIB,"bounded environment witness")
        result["environment_scope"]="fixed product settings; offline compiler; inherited toolchain search is observed, not hermetic"
        if release["stage"]=="build":need(not TARGET.exists(),"fresh build scratch")
        result["metadata_controls"]=metadata_controls(output)
        budget.check(True)
        process,api=load_process(sources)
        outputs=[]
        for index,command in enumerate(release["children"]):
            actual_env=dict(env)
            if release["stage"]=="render":
                grant=release["subject_grant"]
                actual_env.update(M194H_GRANT=str(owned(ROOT/grant["path"])),M194H_GRANT_SHA256=grant["sha256"],M194H_CASE=str(index))
            child_call(process,api,command,actual_env,index,output,budget,result)
            if release["stage"]=="build":
                if index<2:result["artifacts"][("core","cli")[index]]=compile_artifact(output/f"child-{index:02}.log",index,output,budget)
                else:
                    raw,_=read(output/f"child-{index:02}.log",64*KIB,check=budget.check)
                    expected=CORE_TEST if index==2 else CLI_TEST
                    need((expected+": test").encode() in raw.splitlines(),"actual expected test listing")
            elif release["stage"]=="render":outputs.append(case_result(output,index,budget))
            else:
                raw,_=read(output/"child-00.log",64*KIB,check=budget.check)
                need(b"test result: ok. 1 passed; 0 failed; 0 ignored;" in raw and b"M194H_COMPONENT_COMPLETE 26-merges 130-frame-folds plus-one-rejected-entry" in raw,"exact component test completed")
            result["artifacts"]["cases"]=outputs
            atomic(output/"result.json",result)
        if release["stage"]=="render":
            need(len(outputs)==12,"all fixed cases retained")
            for first in (0,3,6):
                need(len({outputs[i]["output"]["sha256"] for i in range(first,first+3)})==1,"actual observer whole-file nonperturbation")
        for key in sources:source_bytes(ROOT/key,sources,budget.check)
        read(args.release,MIB,ref,check=budget.check)
        budget.check(True)
        result["work"]=budget.work();result["inventory_sample"]=budget.inventory;result["scratch_sample"]=budget.scratch
        result["status"]="COMPLETE_STAGE_UNVERIFIED"
    except Exception:
        if result is None:result=dict(schema="m194h-owned-stage-v1",status="REFUSED_BEFORE_OUTPUT",invocation=sys.orig_argv,children=[])
        result["status"]="REFUSED";result["error"]=error_value()
    finally:
        if output is not None:
            result["work"]=budget.work()
            result["publication_started"]=dict(parent_cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
            try:
                terminal=atomic(output/"result.json",result)
                tail=dict(schema="m194h-parent-publication-tail-v1",result=terminal,
                          actual_parent_cpu_sample=time.process_time(),whole_wall_sample=time.monotonic()-START,
                          completed_child_cpu_seconds=budget.completed_cpu,live_child_cpu_seconds=budget.live_cpu,
                          cpu_accounting_complete=budget.complete and budget.accounting_error is None,
                          final_external_allowance=dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),
                          scope="sample after canonical publication; independently retained outer exit/wall and charged tail required")
                need(tail["actual_parent_cpu_sample"]+budget.completed_cpu+budget.live_cpu+TAIL_CPU<=budget.caps["cpu_seconds"],"final CPU tail envelope")
                need(tail["whole_wall_sample"]+TAIL_WALL<=budget.caps["wall_seconds"],"final wall tail envelope")
                tailref=write_new(output/"parent-tail.json",encoded(tail),8*KIB)
                advertised=dict(status=result["status"],result=terminal,tail=tailref)
            except Exception:
                result["status"]="REFUSED";result["finalization_errors"].append(error_value())
                try:terminal=atomic(output/"result.json",result)
                except Exception:terminal=None
                advertised=dict(status="REFUSED",result=terminal,error="terminal/tail failure; no admission")
        else:advertised=result
        raw=encoded(advertised)
        need(len(raw)<=8*KIB,"bounded stdout")
        need(sys.stdout.buffer.write(raw)==len(raw),"full raw stdout");sys.stdout.buffer.flush()
    return 0 if result["status"]=="COMPLETE_STAGE_UNVERIFIED" else 1

if __name__=="__main__":raise SystemExit(main())
