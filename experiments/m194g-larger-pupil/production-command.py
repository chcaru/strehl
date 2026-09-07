"""Parent-observed bounded launches of the separately compiled M194g bridge.

Standard-library plumbing only. No compile, source import or child executes
merely by importing this module. Root must release the exact command first.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import traceback

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREFIX="merge_cmd::known_scene_benchmark::noise_pupil_bridge"
TEST=PREFIX+"::m194g_noise_production_bridge"
PRIVATE=PREFIX+"::private_controls"
ENV_PREFIX="STREHL_M194G_BRIDGE_"
LOG_LIMIT=16<<20
CHILD_WALL=240.0
EXPECTED_TESTS={TEST,PRIVATE+"::m194g_private_production_outputs"} | {
    PRIVATE+"::"+name for name in (
        "m194g_private_source_rails_and_fault","m194g_private_bounded_json_paths_aliases",
        "m194g_private_settings_geometry","m194g_private_manifest_schema_tuple_controls",
        "m194g_private_ledger_changed_input","m194g_private_actual_plan_controls")}
REMOVED=("STREHL_GATE_FLOOR","STREHL_GATE_FLOOR_SCALE","STREHL_WHITE_FLOOR",
         "RUSTFLAGS","CARGO_ENCODED_RUSTFLAGS","CARGO_TARGET_DIR")


def need(ok,message):
    if not ok: raise ValueError(message)


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()


def strict(raw):
    def pairs(items):
        value={}
        for key,item in items:
            need(key not in value,"duplicate JSON key")
            value[key]=item
        return value
    def finite(value):
        if type(value) is float: need(math.isfinite(value),"nonfinite JSON number")
        elif type(value) is dict:
            for v in value.values(): finite(v)
        elif type(value) is list:
            for v in value: finite(v)
    value=json.loads(raw,object_pairs_hook=pairs,
                     parse_constant=lambda _:need(False,"nonfinite JSON token"))
    finite(value)
    return value


def digest(path):
    h=hashlib.sha256(); count=0
    with Path(path).open("rb") as stream:
        while raw:=stream.read(1<<20): h.update(raw); count+=len(raw)
    return dict(sha256=h.hexdigest(),bytes=count)


def ref(path):
    path=Path(path).resolve(strict=True)
    need(path.is_relative_to(ROOT) and path.is_file(),"file outside repository")
    value=digest(path)
    need(value["bytes"]>0,"empty FileRef")
    return dict(path=path.relative_to(ROOT).as_posix(),**value)


def relative(name,base=ROOT):
    need(type(name) is str and name and ":" not in name and "\\" not in name
         and not name.startswith("/") and all(p not in ("", ".", "..") for p in name.split("/")),
         "noncanonical contained reference")
    base=Path(base).resolve()
    target=(base/name).resolve(strict=True)
    need(target.is_relative_to(base) and target.is_file(),"reference outside base")
    return target


def checked_ref(value,base=ROOT,maximum=None):
    need(type(value) is dict and set(value)=={"path","sha256","bytes"},"FileRef keys")
    need(type(value["bytes"]) is int and value["bytes"]>0 and type(value["sha256"]) is str
         and re.fullmatch("[0-9a-f]{64}",value["sha256"]) is not None,"FileRef types")
    need(maximum is None or value["bytes"]<=maximum,"FileRef bounded extent")
    path=relative(value["path"],base)
    need(digest(path)=={k:value[k] for k in ("sha256","bytes")},"bound file changed")
    return path


def read_json(value,base=ROOT,maximum=4<<20):
    path=checked_ref(value,base,maximum)
    with path.open("rb") as stream: raw=stream.read(maximum+1)
    need(len(raw)==value["bytes"] and hashlib.sha256(raw).hexdigest()==value["sha256"],"JSON bytes changed")
    return strict(raw),path


class Metadata:
    def __init__(self,root):
        self.root=Path(root).resolve()
        need(self.root.is_relative_to(ROOT),"metadata output outside repository")
        self.root.mkdir(parents=True,exist_ok=False)
        self.bytes=0
        self.files={}

    def reserve(self,count):
        need(type(count) is int and count>=0 and self.bytes+count<=64<<20,"64MiB controller metadata/log ceiling")

    def new_path(self,name):
        path=(self.root/name).resolve()
        need(path.is_relative_to(self.root) and not path.exists(),"fresh contained output required")
        path.parent.mkdir(parents=True,exist_ok=True)
        return path

    def write(self,name,raw):
        self.reserve(len(raw)); path=self.new_path(name)
        try:
            with path.open("xb") as stream: written=stream.write(raw)
            need(written==len(raw),"short controller write")
        finally:
            self.bytes+=path.stat().st_size if path.exists() else 0
        value=ref(path); self.files[value["path"]]={k:value[k] for k in ("sha256","bytes")}
        return value

    def json(self,name,value): return self.write(name,canonical(value))

    def adopt(self,value,*,tiff=False):
        path=checked_ref(value)
        need(path.is_relative_to(self.root),"child output outside owned output")
        wanted={k:value[k] for k in ("sha256","bytes")}
        if value["path"] not in self.files:
            if not tiff:
                self.reserve(value["bytes"]); self.bytes+=value["bytes"]
            self.files[value["path"]]=wanted
        else: need(self.files[value["path"]]==wanted,"child output changed before adoption")

    def finish(self):
        need(self.bytes<=64<<20,"controller metadata ceiling")
        for path,wanted in self.files.items(): need(digest(ROOT/path)==wanted,"controller output changed")


def environment(fields):
    values={k:v for k,v in os.environ.items() if not k.upper().startswith("STREHL_")
            and k.upper() not in {*REMOVED,"RAYON_NUM_THREADS"}}
    values.update(STREHL_DEFECT="off",STREHL_FIX_CA="off",STREHL_FULLRES_GATHER="1",
                  STREHL_PYRAMID_WORKERS="2",RAYON_NUM_THREADS="2")
    values.update({ENV_PREFIX+k:str(v) for k,v in fields.items()})
    relevant={k:v for k,v in values.items() if k.startswith("STREHL_") or k=="RAYON_NUM_THREADS"}
    for name in {*REMOVED,*[k for k in os.environ if k.upper().startswith("STREHL_")]}:
        if name not in relevant: relevant[name]=None
    return values,relevant


def summary(raw,passed,ignored=0):
    lines=[x for x in raw.decode("utf8","replace").splitlines() if x.startswith("test result:")]
    pattern=rf"test result: ok\. {passed} passed; 0 failed; {ignored} ignored; 0 measured; [0-9]+ filtered out; finished in [0-9.]+s"
    return len(lines)==1 and re.fullmatch(pattern,lines[0]) is not None


def output_binding(output,actual):
    name=output["path"]
    need(type(name) is str,"receipt output path type")
    if name.startswith("\\\\?\\"):
        need(re.match(r"^[A-Za-z]:\\",name[4:]) is not None,"unsupported extended output path")
        name=name[4:]
    path=Path(name)
    need(path.is_absolute() and path.resolve()==checked_ref(actual),"receipt actual output path association")
    need(type(output["bytes"]) is int and output["bytes"]==actual["bytes"]
         and output["sha256"]==actual["sha256"],"receipt actual output byte/hash association")


def live_child(command,env,log,metadata,*,wall_limit=CHILD_WALL,log_limit=LOG_LIMIT):
    """Only this Popen child's timeout/overflow can trigger its termination.

    A bounded queue drains stdout/stderr concurrently; the on-disk log never
    exceeds its limit. This reports operational refusal, not a dead-process
    inference. Private tests may supply the registered smaller timeout.
    """
    need(not log.exists(),"fresh log required")
    events=queue.Queue(maxsize=8); stop=threading.Event()
    started=time.monotonic(); process=None; failure=None; code=None
    def pump(stream):
        try:
            while not stop.is_set():
                raw=os.read(stream.fileno(),65536)
                if not raw: break
                while not stop.is_set():
                    try: events.put(("data",raw),timeout=.05); break
                    except queue.Full: pass
        except Exception as exc:
            while not stop.is_set():
                try: events.put(("error",repr(exc)),timeout=.05); break
                except queue.Full: pass
        finally:
            while not stop.is_set():
                try: events.put(("eof",None),timeout=.05); break
                except queue.Full: pass
    size=0; worker=None; eof=False
    try:
        with log.open("xb") as output:
            process=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0)
            worker=threading.Thread(target=pump,args=(process.stdout,),daemon=True)
            worker.start()
            while not eof or process.poll() is None:
                need(time.monotonic()-started<=wall_limit,"child wall allowance exceeded")
                try: kind,value=events.get(timeout=.02)
                except queue.Empty: continue
                if kind=="eof": eof=True; continue
                if kind=="error": raise RuntimeError("child log pump: "+value)
                remaining=log_limit-size
                kept=value[:remaining]
                metadata.reserve(len(kept))
                written=output.write(kept)
                metadata.bytes+=written; size+=written
                need(written==len(kept),"short child log write")
                need(len(value)<=remaining,"child log allowance exceeded")
            code=process.wait(timeout=1)
    except Exception as exc:
        failure=repr(exc)
    finally:
        if log.exists():
            actual_size=log.stat().st_size
            metadata.bytes+=max(0,actual_size-size)
            size=actual_size
        if process is not None:
            if process.poll() is None:
                try: process.kill()
                except Exception as exc: failure=(failure or "")+"; own-child kill: "+repr(exc)
            try: code=process.wait(timeout=5)
            except Exception as exc: failure=(failure or "")+"; own-child wait: "+repr(exc)
        stop.set()
        if worker is not None:
            worker.join(timeout=1)
            if worker.is_alive(): failure=(failure or "")+"; log worker did not terminate"
        if process is not None and process.stdout is not None and (worker is None or not worker.is_alive()):
            process.stdout.close()
        if time.monotonic()-started>wall_limit and failure is None:
            failure="child wall allowance exceeded through final observation"
    return dict(exit_code=code,wall_seconds=time.monotonic()-started,error=failure,
                started_monotonic=started,log_bytes=size)


class Build:
    def __init__(self,build_ref):
        self.ref=build_ref
        self.record,self.path=read_json(build_ref)
        b=self.record
        need(b["schema"]=="m194g-bridge-build-v1" and b["status"]=="COMPLETE_COMPILED_TESTS_ONLY"
             and b["error"] is None and b["finalization_errors"]==[] and b["rebuilt_cli"] is True
             and type(b["exit_code"]) is int and b["exit_code"]==0,"complete actual build required")
        need(type(b["sources_before"]) is dict and b["sources_before"] and b["sources_before"]==b["sources_after"],
             "compiled source closure")
        self.sources=b["sources_before"]
        self.executable=checked_ref(b["test_executable"])
        original=checked_ref(b["compiler_artifact"])
        need(digest(self.executable)==digest(original),"compiler/copied executable bytes differ")
        message=b["compiler_artifact_message"]
        need(message["reason"]=="compiler-artifact" and message["profile"]["test"] is True
             and message["target"]["name"]=="strehl" and Path(message["executable"]).resolve()==original,
             "compiler artifact association")
        listing=checked_ref(b["test_listing"],maximum=1<<20).read_text(encoding="utf8")
        names=[line[:-6] for line in listing.splitlines() if line.endswith(": test") and PREFIX in line]
        need(len(names)==8 and set(names)==EXPECTED_TESTS,"actual exact eight bridge test names")
        driver=checked_ref(b["driver"],maximum=1<<20)
        need(driver==HERE/"bridge-build.py","actual build driver required")
        raw=driver.read_bytes()
        need(len(raw)==b["driver"]["bytes"] and hashlib.sha256(raw).hexdigest()==b["driver"]["sha256"],
             "actually executed build helper bytes changed")
        module_spec=importlib.util.spec_from_loader("m194g_pinned_build_source",loader=None,origin=str(driver))
        self.driver=importlib.util.module_from_spec(module_spec); self.driver.__file__=str(driver)
        exec(compile(raw,str(driver),"exec"),self.driver.__dict__)
        self.finish()

    def finish(self):
        need(ref(self.path)==self.ref,"build result changed")
        need(self.driver.sources()==self.sources,"actual compiled include/source set changed")
        for key in ("driver","compiler_artifact","test_executable","test_listing","compiler_log","execution_release"):
            checked_ref(self.record[key])


def launch(build,command,env,relevant,metadata,name,ordinal,phase,*,passed=1,ignored=0,precheck=None):
    need(type(ordinal) is int and ordinal>=0 and phase in ("plan","render","private-controls","private-outputs"),"launch identity")
    need(command[0]==str(build.executable),"launch actual copied executable")
    log=metadata.new_path(name+".log")
    record=dict(schema="m194g-production-launch-v1" if phase in ("plan","render") else "m194g-private-production-launch-v1",
                status="FAILED_CHILD",ordinal=ordinal,phase=phase,command=command,environment=relevant,
                executable=build.record["test_executable"],started_utc=datetime.now(timezone.utc).isoformat(),
                ended_utc=None,wall_seconds=None,exit_code=None,log=None,error=None)
    try:
        build.finish()
        if precheck: precheck()
        observation=live_child(command,env,log,metadata)
        record.update({k:observation[k] for k in ("wall_seconds","exit_code","error")})
        need(observation["error"] is None,"bounded child failure: "+str(observation["error"]))
        need(type(observation["exit_code"]) is int and observation["exit_code"]==0,"actual nonzero child exit")
        raw=log.read_bytes()
        need(summary(raw,passed,ignored),"actual child test count/summary")
        build.finish()
        if precheck: precheck()
        record["status"]="COMPLETE_CHILD_EXIT_ZERO"
    except Exception:
        if record["error"] is None: record["error"]=traceback.format_exc()
    record["ended_utc"]=datetime.now(timezone.utc).isoformat()
    if log.exists() and log.stat().st_size:
        record["log"]=ref(log)
        metadata.files[record["log"]["path"]]={k:record["log"][k] for k in ("sha256","bytes")}
    launch_ref=metadata.json(name+"-launch.json",record)
    return record,launch_ref


def invoke(build,metadata,*,kind,ordinal=0,scene=None,seed=None,subset="all",admission="hard-floor",observer="off",
           noise_admission=None,plan=None,stem="child",precheck=None):
    """Return actual launch and emitted file references; never assign quality."""
    if kind in ("private-controls","private-outputs"):
        private=metadata.new_path(stem+"-outputs")
        fields=dict(PRIVATE_OUTPUT=str(private))
        command=([str(build.executable),PRIVATE,"--test-threads=1","--nocapture"] if kind=="private-controls" else
                 [str(build.executable),"--exact",PRIVATE+"::m194g_private_production_outputs","--ignored","--test-threads=1","--nocapture"])
        env,relevant=environment(fields)
        record,launch_ref=launch(build,command,env,relevant,metadata,stem,ordinal,kind,
                                 passed=6 if kind=="private-controls" else 1,ignored=1 if kind=="private-controls" else 0,precheck=precheck)
        return dict(launch=launch_ref,record=record,private_output=str(private))
    need(kind in ("plan","render"),"bridge command kind")
    checked_ref(noise_admission)
    need(scene in ("flat","textured") and (seed is None or type(seed) is int and seed in (701,709,719,727,733,739,743,751)),"registered scene/seed")
    need(subset in ("all","first","last") and admission in ("hard-floor","floor-pedestal-v1")
         and observer in ("off","count","placebo"),"registered settings")
    need(subset=="all" or (scene=="textured" and seed is None and admission=="hard-floor"),"endpoint settings")
    if kind=="plan": target=metadata.new_path(stem+"-plan.json")
    else:
        target=checked_ref(plan)
        receipt=metadata.new_path(stem+"-receipt.json")
        image=metadata.new_path(stem+".tif")
    fields=dict(MODE=kind,NOISE_ADMISSION=str(ROOT/noise_admission["path"]),NOISE_ADMISSION_SHA256=noise_admission["sha256"],
                SCENE=scene,SEED="noise-off" if seed is None else str(seed),SUBSET=subset,ADMISSION=admission,OBSERVER=observer,PLAN=str(target))
    if kind=="render": fields.update(PLAN_SHA256=plan["sha256"],OUTPUT=str(image),RECEIPT=str(receipt))
    env,relevant=environment(fields)
    command=[str(build.executable),"--exact",TEST,"--ignored","--test-threads=1","--nocapture"]
    record,launch_ref=launch(build,command,env,relevant,metadata,stem+"-"+kind,ordinal,kind,precheck=precheck)
    result=dict(record=record,launch=launch_ref,log=record["log"],plan=None,receipt=None,tiff=None,error=None)
    try:
        if target.exists() and target.stat().st_size: result["plan"]=ref(target)
        if record["status"]=="COMPLETE_CHILD_EXIT_ZERO":
            need(target.is_file(),"successful bridge plan absent")
            if kind=="render":
                result.update(receipt=ref(receipt),tiff=ref(image))
                metadata.adopt(result["receipt"])
                metadata.adopt(result["tiff"],tiff=True)
                value,_=read_json(result["receipt"],maximum=1<<20)
                need(value["schema"]=="m194g-noise-consumer-receipt-v1" and value["status"]=="COMPLETE_RGB_UNVERIFIED"
                     and value["plan_sha256"]==plan["sha256"] and value["inputs_unchanged"] is True,"bridge actual receipt completion")
                need(canonical(value["plan"])==canonical(read_json(plan)[0]),"bridge receipt/plan association")
                output_binding(value["output"],result["tiff"])
            else:
                metadata.adopt(result["plan"])
                value,_=read_json(result["plan"],maximum=1<<20)
                need(value["schema"]=="m194g-noise-consumer-plan-v1","bridge actual plan schema")
    except Exception:
        result["error"]=traceback.format_exc()
    return result


def authorize(args,scope,required=()):
    release_ref=ref(args.release)
    need(release_ref["sha256"]==args.release_sha256,"external execution release differs")
    release,_=read_json(release_ref)
    need(set(release)=={"schema","scope","source_bindings","inputs","commands"}
         and release["schema"]=="m194g-numerical-execution-release-v1" and release["scope"]==scope,
         "production execution release schema/scope")
    allowed=[[args.release_sha256 if x=="ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in cmd]
             for cmd in release["commands"]]
    need(list(sys.orig_argv) in allowed,"actual original production argv not released")
    own=Path(__file__).resolve().relative_to(ROOT).as_posix()
    required={own,"experiments/m194g-larger-pupil/bridge-build.py",*required}
    need(type(release["source_bindings"]) is dict and required<=set(release["source_bindings"]),"actual controller dependency omitted")
    def recheck():
        need(ref(args.release)==release_ref,"production release changed")
        for name,value in release["source_bindings"].items(): checked_ref(dict(path=name,**value))
        for value in release["inputs"]: checked_ref(value)
    recheck()
    return release,release_ref,recheck


def publish(metadata,name,result,recheck,*,failure_status):
    """No positive result survives a known post-write failure."""
    target=metadata.root/name
    try:
        recheck(); metadata.finish()
        result_ref=metadata.json(name,result)
        recheck(); metadata.finish()
        return result_ref
    except Exception as original:
        if result.get("error") is None: result["error"]=traceback.format_exc()
        result["status"]=failure_status
        result.setdefault("finalization_errors",[]).append(repr(original))
        if target.exists():
            try: target.rename(target.with_name(target.name+".rejected"))
            except Exception as secondary: original.add_note("retaining first publication failed: "+repr(secondary))
        try:
            metadata.json(name,result)
        except Exception as secondary: original.add_note("refusal persistence failed: "+repr(secondary))
        print(canonical(result).decode(),file=sys.stderr,flush=True)
        raise original


LAUNCH_CONTROL_IDS=("actual-build-and-list", "build-source-omission-refused", "build-artifact-mismatch-refused",
                    "build-list-omission-refused", "build-metadata-restored", "environment-overrides-cleared", "environment-restored",
                    "output-association-valid", "output-association-stale", "output-association-restored",
                    "actual-zero-exit", "actual-nonzero-exit", "zero-tests-refused",
                    "duplicate-summary-refused", "exact-log-limit", "log-overflow-refused", "actual-timeout-refused",
                    "fresh-output-refused", "changed-source-refused", "restored-source", "preserved-prior-failure",
                    "wrong-executable-command-refused", "final-build-and-list")


def launcher_controls(build,metadata,recheck,result):
    """Actual local Python children are explicitly ineligible as bridge evidence."""
    checks=result["checks"]
    def add(name,ok,evidence):
        checks.append(dict(name=name,**{"pass":bool(ok)},evidence=evidence))
        result["check_count"]=len(checks)
        need(ok,"launcher control failed: "+name)
    build.finish(); add("actual-build-and-list",True,dict(build=build.ref,listing=build.record["test_listing"]))
    def build_reject(name,value,message):
        value_ref=metadata.json("private-build/"+name+".json",value)
        try: Build(value_ref)
        except ValueError as exc: add(name,message in str(exc),dict(error=str(exc),build=value_ref))
        else: add(name,False,dict(build=value_ref))
    import copy
    omitted=copy.deepcopy(build.record)
    first=next(iter(omitted["sources_before"]))
    del omitted["sources_before"][first]; del omitted["sources_after"][first]
    build_reject("build-source-omission-refused",omitted,"actual compiled include/source set changed")
    small=metadata.write("private-build/different-artifact.bin",b"private non-executable association control")
    changed=copy.deepcopy(build.record); changed["test_executable"]=small
    build_reject("build-artifact-mismatch-refused",changed,"compiler/copied executable bytes differ")
    listing=checked_ref(build.record["test_listing"]).read_text(encoding="utf8").splitlines()
    dropped=False; kept=[]
    for line in listing:
        if PREFIX in line and line.endswith(": test") and not dropped: dropped=True; continue
        kept.append(line)
    need(dropped,"private listing fault had no bridge test")
    changed=copy.deepcopy(build.record)
    changed["test_listing"]=metadata.write("private-build/missing-test-list.log",("\n".join(kept)+"\n").encode())
    build_reject("build-list-omission-refused",changed,"actual exact eight bridge test names")
    restored_build=metadata.json("private-build/restored.json",build.record)
    Build(restored_build); add("build-metadata-restored",True,{"build":restored_build})
    baseline=environment({"OBSERVER":"off"})
    poison={"STREHL_GATE_FLOOR":"white","STREHL_GATE_FLOOR_SCALE":"99","STREHL_PRIVATE_POISON":"on","RUSTFLAGS":"--cfg forbidden"}
    old={k:os.environ.get(k) for k in poison}
    try:
        os.environ.update(poison)
        cleaned,relevant=environment({"OBSERVER":"off"})
        add("environment-overrides-cleared",all(k not in cleaned and relevant[k] is None for k in poison)
            and cleaned["STREHL_FULLRES_GATHER"]=="1" and cleaned["RAYON_NUM_THREADS"]=="2",
            {"planted":poison,"recorded_removed":{k:relevant[k] for k in poison}})
    finally:
        for key,value in old.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value
    add("environment-restored",environment({"OBSERVER":"off"})==baseline,{})
    descriptor=dict(path=str(ROOT/small["path"]),sha256=small["sha256"],bytes=small["bytes"])
    output_binding(descriptor,small); add("output-association-valid",True,{"private_file":small})
    try: output_binding({**descriptor,"sha256":"0"*64},small)
    except ValueError as exc: add("output-association-stale","byte/hash association" in str(exc),{"error":str(exc)})
    else: add("output-association-stale",False,{})
    output_binding(descriptor,small); add("output-association-restored",True,{"private_file":small})
    watched=metadata.new_path("private-child/watched.txt"); watched.write_bytes(b"original")
    metadata.bytes+=8; metadata.files[watched.relative_to(ROOT).as_posix()]=digest(watched)
    source=metadata.write("private-child/child.py",b'''import pathlib,sys,time
mode=sys.argv[1]
summary=b"\\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\\n"
if mode=="zero": sys.stdout.buffer.write(summary)
elif mode=="nonzero": sys.stdout.buffer.write(summary); sys.exit(7)
elif mode=="zero-tests": print("test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out; finished in 0.01s")
elif mode=="duplicate": sys.stdout.buffer.write(summary+summary)
elif mode=="limit": sys.stdout.buffer.write(b"x"*((16<<20)-len(summary))+summary)
elif mode=="overflow": sys.stdout.buffer.write(b"x"*((16<<20)+1)); sys.stdout.flush(); time.sleep(.2)
elif mode=="timeout": print("healthy private timeout fixture",flush=True); time.sleep(5)
elif mode=="change": pathlib.Path(sys.argv[2]).write_bytes(b"changed!"); sys.stdout.buffer.write(summary)
else: raise ValueError(mode)
''')
    python=Path(sys.executable).resolve()
    python_binding=digest(python)
    class PrivateBuild:
        executable=python
        # Private launch schema names this absolute interpreter observation;
        # it cannot enter the repository-only production matrix schema.
        record={"test_executable":{"path":str(python),**python_binding}}
        def finish(self):
            need(digest(python)==python_binding,"private interpreter changed")
            need(watched.read_bytes()==b"original","private watched source changed")
            checked_ref(source)
    fake=PrivateBuild()
    env,relevant=environment({})
    def command(mode): return [str(python),str(ROOT/source["path"]),mode,str(watched)]
    def run(mode,name):
        return launch(fake,command(mode),env,relevant,metadata,"private-child/"+name,0,"private-controls",passed=1,precheck=recheck)
    zero,zero_ref=run("zero","zero")
    add("actual-zero-exit",zero["status"]=="COMPLETE_CHILD_EXIT_ZERO" and zero["exit_code"]==0,{"launch":zero_ref})
    bad,bad_ref=run("nonzero","nonzero")
    add("actual-nonzero-exit",bad["status"]=="FAILED_CHILD" and bad["exit_code"]==7,{"launch":bad_ref})
    for mode,name in (("zero-tests","zero-tests-refused"),("duplicate","duplicate-summary-refused")):
        row,rr=run(mode,mode)
        add(name,row["status"]=="FAILED_CHILD" and row["exit_code"]==0 and "test count/summary" in row["error"],{"launch":rr})
    row,rr=run("limit","limit")
    add("exact-log-limit",row["status"]=="COMPLETE_CHILD_EXIT_ZERO" and row["log"]["bytes"]==LOG_LIMIT,{"launch":rr})
    row,rr=run("overflow","overflow")
    add("log-overflow-refused",row["status"]=="FAILED_CHILD" and "log allowance exceeded" in row["error"]
        and row["log"]["bytes"]==LOG_LIMIT,{"launch":rr})
    timeout_log=metadata.new_path("private-child/timeout.log")
    observed=live_child(command("timeout"),env,timeout_log,metadata,wall_limit=.2)
    timeout_ref=ref(timeout_log) if timeout_log.stat().st_size else None
    if timeout_ref: metadata.files[timeout_ref["path"]]={k:timeout_ref[k] for k in ("sha256","bytes")}
    add("actual-timeout-refused",observed["error"] is not None and "wall allowance exceeded" in observed["error"],
        dict(observation=observed,log=timeout_ref,private_wall_allowance=.2))
    try: run("zero","zero")
    except ValueError as exc: add("fresh-output-refused","fresh contained output" in str(exc),{"error":str(exc)})
    else: add("fresh-output-refused",False,{})
    try:
        changed,changed_ref=run("change","change")
        add("changed-source-refused",changed["status"]=="FAILED_CHILD" and changed["exit_code"]==0
            and "watched source changed" in changed["error"],{"launch":changed_ref})
    finally:
        metadata.reserve(8); watched.write_bytes(b"original"); metadata.bytes+=8
    restored,restored_ref=run("zero","restored")
    add("restored-source",restored["status"]=="COMPLETE_CHILD_EXIT_ZERO",{"launch":restored_ref})
    stored,_=read_json(bad_ref)
    add("preserved-prior-failure",stored["status"]=="FAILED_CHILD" and stored["exit_code"]==7,{"launch":bad_ref})
    try: launch(fake,[str(python)+"-wrong"],env,relevant,metadata,"private-child/wrong",0,"private-controls")
    except ValueError as exc: add("wrong-executable-command-refused","actual copied executable" in str(exc),{"error":str(exc)})
    else: add("wrong-executable-command-refused",False,{})
    build.finish(); add("final-build-and-list",True,{"build":build.ref})
    need(tuple(x["name"] for x in checks)==LAUNCH_CONTROL_IDS,"complete launcher control population")
    result["status"]="PASS_PRIVATE_LAUNCHER_CONTROLS_ONLY"
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--release",type=Path,required=True); parser.add_argument("--release-sha256",required=True)
    parser.add_argument("--build",type=Path,required=True); parser.add_argument("--build-sha256",required=True)
    parser.add_argument("--kind",choices=("launcher-controls","private-controls","private-outputs","plan","render"),required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--noise-admission",type=Path); parser.add_argument("--noise-admission-sha256")
    parser.add_argument("--scene",choices=("flat","textured")); parser.add_argument("--seed",default="noise-off")
    parser.add_argument("--subset",choices=("all","first","last"),default="all")
    parser.add_argument("--admission",choices=("hard-floor","floor-pedestal-v1"),default="hard-floor")
    parser.add_argument("--observer",choices=("off","count","placebo"),default="off")
    parser.add_argument("--plan",type=Path); parser.add_argument("--plan-sha256")
    args=parser.parse_args()
    release,release_ref,recheck=authorize(args,"production-"+args.kind)
    metadata=Metadata(args.output)
    result=dict(schema="m194g-production-command-v1",status="UNCOMMISSIONED_PRODUCTION_COMMAND",
                ref_root="repository",kind=args.kind,execution_release=release_ref,invocation=list(sys.orig_argv),
                build=ref(args.build),sources_before=release["source_bindings"],sources_after=None,
                inputs_before={r["path"]:{k:r[k] for k in ("sha256","bytes")} for r in release["inputs"]},inputs_after=None,
                child=None,controls=None,error=None,finalization_errors=[],work=None)
    try:
        need(result["build"]["sha256"]==args.build_sha256 and result["build"] in release["inputs"],"external released build pin")
        build=Build(result["build"])
        if args.kind=="launcher-controls":
            result["controls"]=dict(schema="m194g-production-launcher-controls-v1",status="UNCOMMISSIONED_LAUNCHER_CONTROLS",
                                    fixture_only=True,check_count=0,checks=[])
            launcher_controls(build,metadata,recheck,result["controls"])
        else:
            noise=ref(args.noise_admission) if args.noise_admission else None
            saved_plan=ref(args.plan) if args.plan else None
            if noise: need(noise["sha256"]==args.noise_admission_sha256 and noise in release["inputs"],"released noise admission pin")
            if saved_plan: need(saved_plan["sha256"]==args.plan_sha256 and saved_plan in release["inputs"],"released plan pin")
            child=invoke(build,metadata,kind=args.kind,scene=args.scene,seed=None if args.seed=="noise-off" else int(args.seed),
                         subset=args.subset,admission=args.admission,observer=args.observer,noise_admission=noise,plan=saved_plan,precheck=recheck)
            result["child"]=child
            need(child["record"]["status"]=="COMPLETE_CHILD_EXIT_ZERO","production child refused")
            need(child.get("error") is None,"production child artifact validation: "+str(child.get("error")))
            if args.kind.startswith("private-"):
                for path in sorted(Path(child["private_output"]).rglob("*")):
                    if path.is_file(): metadata.adopt(ref(path),tiff=path.suffix.lower() in (".tif",".tiff"))
        result["status"]="COMPLETE_PRODUCTION_COMMAND_UNVERIFIED"
    except Exception: result["error"]=traceback.format_exc()
    try:
        result["sources_after"]={name:digest(ROOT/name) for name in result["sources_before"]}
        result["inputs_after"]={name:digest(ROOT/name) for name in result["inputs_before"]}
        need(canonical(result["sources_before"])==canonical(result["sources_after"])
             and canonical(result["inputs_before"])==canonical(result["inputs_after"]),"final production closure")
    except Exception:
        result["status"]="UNCOMMISSIONED_PRODUCTION_COMMAND"
        result["finalization_errors"].append(traceback.format_exc())
    result["work"]=dict(metadata_and_log_bytes=metadata.bytes,metadata_and_log_limit=64<<20,
                        per_child_wall_seconds=CHILD_WALL,per_child_log_bytes=LOG_LIMIT,
                        scope="operational launch/output bounds, no performance or memory quality claim")
    publish(metadata,"result.json",result,recheck,failure_status="UNCOMMISSIONED_PRODUCTION_COMMAND")
    print(canonical(dict(status=result["status"],result=ref(metadata.root/"result.json"))).decode(),flush=True)
    return 0 if result["status"]=="COMPLETE_PRODUCTION_COMMAND_UNVERIFIED" else 1


if __name__=="__main__": raise SystemExit(main())
