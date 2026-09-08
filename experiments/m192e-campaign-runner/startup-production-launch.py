"""Prospective owned launch and terminal GetProcessTimes receipt; no launch on import."""
import time
START=time.monotonic()
import argparse,ctypes,importlib.util,json,os,subprocess,sys
from pathlib import Path
import durable as d
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SAVED=ROOT/"experiments/m193c-output-grid/sift-lightglue-saved-completion-run.py"
HARNESS=ROOT/"experiments/m12-scorecard/m12-harness.py"
SIZE=8192
def load(ref,name):
    raw,_=d.bytes_binding(ref["path"],expected=ref)
    spec=importlib.util.spec_from_loader(name,loader=None);module=importlib.util.module_from_spec(spec)
    module.__file__=ref["path"];sys.modules[name]=module
    exec(compile(raw,ref["path"],"exec"),module.__dict__);return module
def write(path,value):
    raw=d.encode(value);d.need(len(raw)<=SIZE,"fixed outer receipt capacity")
    raw+=b" "*(SIZE-len(raw));stage=path.with_name("receipt-stage.json")
    with stage.open("wb") as stream:
        d.need(stream.write(raw)==len(raw),"complete outer receipt write");stream.flush();os.fsync(stream.fileno())
    os.replace(stage,path)
    value_,ref=d.json_binding(path,SIZE);d.need(value_==value,"same-byte outer receipt")
    return ref
def times(api,process):
    values=[api.wt.FILETIME() for _ in range(4)]
    function=api.kernel32.GetProcessTimes
    function.argtypes=[api.wt.HANDLE,*([ctypes.POINTER(api.wt.FILETIME)]*4)];function.restype=api.wt.BOOL
    d.need(bool(function(api.wt.HANDLE(int(process._handle)),*[ctypes.byref(v) for v in values])),"actual owned GetProcessTimes")
    numbers=[(int(v.dwHighDateTime)<<32)|int(v.dwLowDateTime) for v in values]
    return dict(created_100ns=numbers[0],exited_100ns=numbers[1],kernel_cpu_100ns=numbers[2],user_cpu_100ns=numbers[3])
def main():
    p=argparse.ArgumentParser();p.add_argument("--plan",type=Path,required=True);p.add_argument("--plan-sha256",required=True)
    args=p.parse_args()
    d.need(os.name=="nt" and sys.dont_write_bytecode and Path.cwd().resolve()==ROOT,"exact Windows launch environment")
    plan,planref=d.json_binding(args.plan,expected_sha256=args.plan_sha256)
    d.need(plan["schema"]=="m192e-startup-production-plan-v1","held rehearsal plan")
    output=d.lexical_path(plan["output_directory"],missing=True)
    directory=output.with_name(output.name+"-outer")
    d.need(output.parent==HERE and not output.exists() and not directory.exists(),"fresh paired output roots")
    sources={str(d.lexical_path(r["path"])):r for r in plan["source_bindings"]}
    for path in (Path(__file__).resolve(),HERE/"startup-production-run.py",HERE/"durable.py",SAVED,HARNESS):d.check_ref(sources[str(path)])
    d.need(d.check_ref(plan["python"])["path"]==str(Path(sys.executable).resolve()),"same held Python")
    saved=load(sources[str(SAVED)],"m192e_outer_pure_job_selector")
    ref=sources[str(HARNESS)]
    api=saved.selected(HARNESS,dict(bytes=ref["bytes"],sha256=ref["sha256"].lower()),saved.JOB_NAMES+saved.JOB_SIGNATURES)
    command=[str(Path(sys.executable).resolve()),"-B",str(HERE/"startup-production-run.py"),"--plan",str(args.plan.resolve()),"--plan-sha256",args.plan_sha256]
    directory.mkdir()
    stdout=directory/"stdout.log";stderr=directory/"stderr.log";receipt=directory/"outer.json"
    result=dict(schema="m192e-outer-run-v1",status="REFUSED",phase="INITIAL_INCOMPLETE",
        source=sources[str(Path(__file__).resolve())],plan=planref,command=command,
        process_id=None,exit_code=None,process_times_before=None,process_times_after=None,
        terminal_cpu_accounting=False,elapsed_wall_seconds=None,job_accounting=None,
        termination_attempted=False,error=None,cleanup_errors=[],stdout=None,stderr=None,
        wrapper_scope="separate owned launcher; parent600CPU/240wall plus held worker Job is the subject scope")
    write(receipt,result)
    job=process=None;launched=None
    try:
        job=api.create_process_job()
        with stdout.open("xb") as out,stderr.open("xb") as err:
            launched=time.monotonic()
            process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                creationflags=api.CREATE_SUSPENDED|subprocess.CREATE_NO_WINDOW)
            result["process_id"]=process.pid
            result["process_times_before"]=times(api,process)
            api.assign_process_to_job(job,process)
            while process.poll() is None:
                d.need(time.monotonic()-launched<=240,"parent whole240 wall")
                d.need(stdout.stat().st_size<=d.MIB and stderr.stat().st_size<=d.MIB,"observed bounded outer logs")
                d.need(time.process_time()<=5 and time.monotonic()-START<=255,"separate wrapper envelope")
                time.sleep(.025)
            result["exit_code"]=process.wait()
            # Same retained Popen handle; never close it or look up by PID first.
            after=times(api,process);result["process_times_after"]=after
            d.need(after["created_100ns"]==result["process_times_before"]["created_100ns"] and after["exited_100ns"]>0,
                   "same creation identity after actual wait")
            result["terminal_cpu_accounting"]=True
            result["elapsed_wall_seconds"]=time.monotonic()-launched
            result["job_accounting"]=api.job_accounting(job)
            d.need(result["job_accounting"]["active_processes"]==0,"complete owned outer tree")
            out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
        d.need(result["exit_code"]==0 and result["elapsed_wall_seconds"]<=240,"actual zero exit inside whole wall bound")
        result["status"]="COMPLETE_OUTER_CAPTURE_ONLY";result["phase"]="TERMINAL_CAPTURE"
    except BaseException as exc:
        result["error"]=dict(type=type(exc).__name__,message=str(exc)[-1024:])
    finally:
        if job is not None:
            try:
                observed=api.job_accounting(job)
                if observed["active_processes"]:
                    result["termination_attempted"]=True
                    fn=api.kernel32.TerminateJobObject;fn.argtypes=[api.wt.HANDLE,api.wt.UINT];fn.restype=api.wt.BOOL
                    d.need(bool(fn(job,0xE192E000)),"terminate only owned outer Job")
                    deadline=time.monotonic()+5
                    while observed["active_processes"] and time.monotonic()<deadline:
                        time.sleep(.025);observed=api.job_accounting(job)
                result["job_accounting"]=observed
                if observed["active_processes"]:result["cleanup_errors"].append("owned Job still active")
            except BaseException as exc:result["cleanup_errors"].append(str(exc)[-512:])
        if process is not None:
            try:
                if process.poll() is None:process.kill() # Only own direct child if assignment failed.
                result["exit_code"]=process.wait(timeout=5)
                after=times(api,process)
                d.need(after["created_100ns"]==result["process_times_before"]["created_100ns"] and after["exited_100ns"]>0,"terminal retained-handle identity")
                result["process_times_after"]=after;result["terminal_cpu_accounting"]=True
            except BaseException as exc:result["cleanup_errors"].append(str(exc)[-512:])
            finally:process._handle.Close()
        if job is not None:api.kernel32.CloseHandle(job)
        if launched is not None:result["elapsed_wall_seconds"]=time.monotonic()-launched
    for key,path in (("stdout",stdout),("stderr",stderr)):
        if path.exists():result[key]=d.binding(path)
    result["wrapper_sample"]=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START,
        publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),
        scope="wrapper only through final receipt preparation; excludes its last receipt/stdout write")
    if (result["cleanup_errors"] or result["termination_attempted"] or not result["terminal_cpu_accounting"]
        or result["elapsed_wall_seconds"] is None or result["elapsed_wall_seconds"]>240
        or result["wrapper_sample"]["cpu_seconds"]+.25>5 or result["wrapper_sample"]["wall_seconds"]+.5>255
        or any(result[k] is None or result[k]["bytes"]>d.MIB for k in ("stdout","stderr"))):
        result["status"]="REFUSED"
    for ref in (result["source"],planref):d.check_ref(ref)
    actual=write(receipt,result)
    print(json.dumps(dict(status=result["status"],result=actual),allow_nan=False),flush=True)
    return 0 if result["status"]=="COMPLETE_OUTER_CAPTURE_ONLY" else 1
if __name__=="__main__":raise SystemExit(main())
