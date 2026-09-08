"""M192e five-private-child startup attribution. Source only until exact release."""
import time
START=time.monotonic()
import argparse,ast,copy,hashlib,importlib.util,json,os,sys
from pathlib import Path
import durable as d
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SAMPLER=ROOT/"experiments/m192c-sampler/sampler.py";CHILD=SAMPLER.with_name("child.py")
HARNESS=ROOT/"experiments/m12-scorecard/m12-harness.py"
SAVED=ROOT/"experiments/m193c-output-grid/sift-lightglue-saved-completion-run.py"
PROCESS=SAVED.with_name("bounded-process.py");PUBLICATION=SAVED.with_name("saved-completion-publication.py")
SPEC=HERE/"startup-attribution-preregister-2.md"
ARMS=("off","on","placebo","before-popen-delay","after-resume-delay")
BASELINE_CAPS=dict(plan=65536,result=65536,outer=16384,verification=16384,diagnosis=16384,independent_review=16384)
LIMITS=dict(phase_cpu_seconds=20,phase_wall_seconds=30,source_bytes=1<<20,output_bytes=3<<20,
            audit_cpu_seconds=10,audit_wall_seconds=20,audit_file_bytes=1<<20)
COMPLETE="COMPLETE_PRIVATE_STARTUP_OBSERVATIONS_ONLY"
MONITOR_CALLS={"h.system_times":"startup-system-times","h.memory_status":"startup-memory-status",
    "k32.CreateJobObjectW":"startup-create-job","(folder / 'stdout.log').open":"startup-stdout-open",
    "(folder / 'stderr.log').open":"startup-stderr-open","subprocess.Popen":"startup-popen",
    "h.assign_process_to_job":"assignment-helper"}
ASSIGN_CALLS={"kernel32.AssignProcessToJobObject":"startup-assign-job","ntdll.NtResumeProcess":"startup-resume"}
def sha(data):return hashlib.sha256(data).hexdigest().upper()
def load(ref,name):
    raw,_=d.bytes_binding(ref["path"],expected=ref)
    spec=importlib.util.spec_from_loader(name,loader=None);module=importlib.util.module_from_spec(spec)
    module.__file__=ref["path"];sys.modules[name]=module
    exec(compile(raw,ref["path"],"exec"),module.__dict__);return module
def same(a,b):
    d.ref_shape(a);d.ref_shape(b)
    return d.lexical_path(a["path"])==d.lexical_path(b["path"]) and a["bytes"]==b["bytes"] and a["sha256"].upper()==b["sha256"].upper()
def setup(args):
    plan,ref=d.json_binding(args.plan,65536,expected_sha256=args.plan_sha256)
    d.need(set(plan)=={"schema","source_bindings","rehearsal_baseline","python","output_directory","commands","resource_limits"}
        and plan["schema"]=="m192e-startup-attribution-plan-v1" and plan["resource_limits"]==LIMITS,"closed fixed startup plan")
    d.need(set(plan["commands"])=={"parent","worker"},"two exact commands")
    expected=[args.plan_sha256 if x=="ACTUAL_PLAN_SHA256" else x for x in plan["commands"]["worker" if args.worker else "parent"]]
    d.need(expected==sys.orig_argv and sys.dont_write_bytecode and Path.cwd().resolve()==ROOT and os.name=="nt","exact held invocation")
    sources={}
    d.need(type(plan["source_bindings"]) is list and len(plan["source_bindings"])<=64,"bounded source count")
    for source in plan["source_bindings"]:
        d.ref_shape(source);d.need(source["bytes"]>0,"positive source extent")
        p=d.lexical_path(source["path"]);d.need(str(p) not in sources,"unique source")
        sources[str(p)]=source
    required=(Path(__file__).resolve(),SPEC,HERE/"durable.py",SAMPLER,CHILD,HARNESS,SAVED,PROCESS,PUBLICATION)
    d.need(all(str(p) in sources for p in required) and sum(r["bytes"] for r in sources.values())<=LIMITS["source_bytes"],"bounded whole source closure before hashing")
    python=plan["python"];d.ref_shape(python)
    d.need(d.lexical_path(python["path"])==Path(sys.executable).resolve() and 0<python["bytes"]<=16*(1<<20),"current Python identity and bounded extent before hashing")
    base=plan["rehearsal_baseline"]
    d.need(type(base) is dict and set(base)==set(BASELINE_CAPS),"six existing baseline refs")
    for role,r in base.items():
        d.ref_shape(r);d.need(0<r["bytes"]<=BASELINE_CAPS[role],"bounded baseline role before hashing")
    for r in (*sources.values(),python,*base.values()):
        d.need(time.process_time()<5 and time.monotonic()-START<5,"bounded setup prefix")
        d.bytes_binding(r["path"],r["bytes"],expected=r)
    review=HERE/"independent-rehearsal-1-read.md"
    d.need(d.lexical_path(base["independent_review"]["path"])==review and
        base["independent_review"]["bytes"]==9509 and base["independent_review"]["sha256"].upper()==
        "4D19117D757FD6E814AEBA1CBB747F3E53F9B376C2B4D540D6662809B4387FF8","actual independent failed-integration read")
    inherited=d.read_ref(base["plan"],BASELINE_CAPS["plan"])
    old_sources={str(d.lexical_path(r["path"])):r for r in inherited["source_bindings"]}
    for p in (SAMPLER,HARNESS,HERE/"durable.py",SAVED,PROCESS,PUBLICATION):
        d.need(sources[str(p)]["bytes"]==old_sources[str(p)]["bytes"] and
            sources[str(p)]["sha256"].upper()==old_sources[str(p)]["sha256"].upper(),"same actually rehearsed immutable helpers")
    old=d.read_ref(base["verification"],BASELINE_CAPS["verification"])
    d.need(old["schema"]=="m192e-terminal-verification-v1" and old["status"]=="PASS_BOUND_TERMINAL_REHEARSAL_ONLY"
        and old["integration_pass"] is False and old["sampling_all_pass"] is False and old["output_nonperturbation"] is True
        and same(old["plan"],base["plan"])
        and same(old["parent"],base["result"])
        and same(old["outer"],base["outer"]),"preserved actual failed integration")
    out=d.lexical_path(plan["output_directory"],missing=True)
    d.need(out.parent==HERE and out.name.startswith("startup-attribution-") and
        (out.is_dir() if args.worker else not out.exists()),"fresh literal output scope")
    return plan,ref,sources,out
class Budget:
    def __init__(self,out):
        self.output=out;self.child_cpu=0.;self.accounting_error=None;self.extents={};self.last_scan=0.;self.observed=0
    def observe(self,value):
        keys=("total_user_100ns","total_kernel_100ns","total_cpu_100ns","active_processes")
        if type(value) is dict and all(type(value.get(k)) is int and value[k]>=0 for k in keys) and value["total_cpu_100ns"]==value["total_user_100ns"]+value["total_kernel_100ns"]:
            now=value["total_cpu_100ns"]/1e7
            if now>=self.child_cpu:self.child_cpu=now
            else:self.accounting_error="decreasing Job CPU"
        else:self.accounting_error="invalid Job CPU components or sum"
    def check(self,force=False,terminal=False):
        if not terminal:
            d.need(time.monotonic()-START<=28 and time.process_time()+self.child_cpu<=19 and self.accounting_error is None,
                "ordinary startup phase bound")
        now=time.monotonic()
        if force or now-self.last_scan>=.1:
            count=0
            for base,dirs,names in os.walk(self.output,followlinks=False):
                for name in dirs+names:d.lexical_path(Path(base)/name)
                for name in names:count+=(Path(base)/name).stat().st_size
            self.observed=count;self.last_scan=now
            if not terminal:d.need(count<=LIMITS["output_bytes"],"observed startup output bound")
    def reserve(self,path,size,family,terminal=False):
        p=Path(path).resolve();d.need(p.is_relative_to(self.output) and 0<size<=384*1024,"owned bounded write")
        self.extents[str(p)]=max(self.extents.get(str(p),0),size)
        d.need(sum(self.extents.values())<=LIMITS["output_bytes"],"reserved output bound")
        self.check(terminal=terminal)
    def save(self,path,value,cap=64*1024,terminal=False,replace=False):
        raw=d.encode(value);d.need(len(raw)<=cap,"bounded metadata record")
        self.reserve(path,len(raw),"metadata",terminal)
        path.parent.mkdir(parents=True,exist_ok=True)
        d.need(replace or not path.exists(),"fresh metadata record")
        with path.open("wb" if replace else "xb") as stream:
            d.need(stream.write(raw)==len(raw),"whole metadata write");stream.flush();os.fsync(stream.fileno())
        actual,ref=d.json_binding(path,cap);d.need(actual==value,"same-byte metadata readback");return ref
def selected_function(path,name,globals_,mapping,pin):
    raw,_=d.bytes_binding(path,expected=pin);tree=ast.parse(raw,str(path))
    original=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    node=copy.deepcopy(original);counts={key:0 for key in mapping}
    startup_end=min((n.lineno for n in ast.walk(original) if isinstance(n,ast.While)),default=10**9)
    class Rewriter(ast.NodeTransformer):
        def visit_Call(self,call):
            call=self.generic_visit(call);key=ast.unparse(call.func)
            if key in mapping and (name!="monitor" or call.lineno<startup_end):
                counts[key]+=1
                if key=="h.assign_process_to_job":
                    call.func=ast.Attribute(value=ast.Name(id="probe",ctx=ast.Load()),attr="assign",ctx=ast.Load())
                else:
                    call.args=[ast.Constant(mapping[key]),call.func,*call.args]
                    call.func=ast.Attribute(value=ast.Name(id="probe",ctx=ast.Load()),attr="call",ctx=ast.Load())
            return call
    node=Rewriter().visit(node)
    d.need(all(v==1 for v in counts.values()),"exact closed startup call replacements")
    reverse_counts={key:0 for key in mapping}
    class Unwrapper(ast.NodeTransformer):
        def visit_Call(self,call):
            call=self.generic_visit(call);key=ast.unparse(call.func)
            if key=="probe.call":
                d.need(len(call.args)>=2 and isinstance(call.args[0],ast.Constant),"closed reverse wrapper shape")
                target=ast.unparse(call.args[1])
                d.need(target in mapping and mapping[target]==call.args[0].value,"same reverse call and label")
                reverse_counts[target]+=1;call.func=call.args[1];call.args=call.args[2:]
            elif key=="probe.assign":
                d.need("h.assign_process_to_job" in mapping,"closed reverse assignment")
                reverse_counts["h.assign_process_to_job"]+=1
                call.func=ast.parse("h.assign_process_to_job",mode="eval").body
            return call
    restored=Unwrapper().visit(copy.deepcopy(node))
    original_dump=ast.dump(original,include_attributes=False)
    restored_dump=ast.dump(restored,include_attributes=False)
    d.need(reverse_counts==counts and restored_dump==original_dump,"complete original AST restored byte for byte")
    module=ast.Module(body=[ast.ImportFrom(module="__future__",names=[ast.alias(name="annotations")],level=0),node],type_ignores=[])
    ast.fix_missing_locations(module);scope=dict(globals_)
    exec(compile(module,str(path),"exec"),scope)
    return scope[name],dict(original_ast_sha256=sha(original_dump.encode()),
        restored_ast_sha256=sha(restored_dump.encode()),reverse_replacement_counts=reverse_counts,
        changed_ast_sha256=sha(ast.dump(node,include_attributes=False).encode()),replacement_counts=counts,
        scope="Only named call wrapping; original start, interval, missed arithmetic and admission expressions remain literal.")
class Probe:
    def __init__(self,arm,sampler,sources):
        self.arm=arm;self.rows=[];self.child_pid=None;self.popen_argv=None;self.popen_flags=None
        self.assign,self.assign_ast=selected_function(HARNESS,"assign_process_to_job",dict(sampler.h.__dict__,probe=self),ASSIGN_CALLS,sources[str(HARNESS)])
    def delay(self,name):
        begin=time.perf_counter_ns();cpu=time.thread_time_ns()
        row=dict(phase=name,start_ns=begin,thread_cpu_start_ns=cpu,requested_delay_ms=150,scope="INJECTED_OBSERVER_DELAY")
        self.rows.append(row)
        try:time.sleep(.150)
        finally:row.update(end_ns=time.perf_counter_ns(),thread_cpu_end_ns=time.thread_time_ns())
    def call(self,name,function,*args,**kwargs):
        if name=="startup-popen" and self.arm=="before-popen-delay":self.delay("before-popen-delay")
        row=dict(phase=name,start_ns=time.perf_counter_ns(),thread_cpu_start_ns=time.thread_time_ns(),
                 error=None,scope="ACTUAL_STARTUP_CALL")
        self.rows.append(row);d.need(len(self.rows)<=12,"fixed startup phase rows")
        try:
            value=function(*args,**kwargs)
            if name=="startup-popen":
                self.child_pid=value.pid;self.popen_argv=args[0];self.popen_flags=kwargs["creationflags"]
                row["returned_pid"]=value.pid
            elif name in ("startup-create-job","startup-assign-job","startup-resume"):
                row["native_result"]=int(value) if value is not None else None
            return value
        except BaseException as exc:
            row["error"]=dict(type=type(exc).__name__,message=str(exc)[-512:]);raise
        finally:
            row.update(end_ns=time.perf_counter_ns(),thread_cpu_end_ns=time.thread_time_ns())
            if name=="startup-resume" and row.get("native_result")==0 and self.arm=="after-resume-delay":
                self.delay("after-resume-delay")
def intrinsic(folder,output,raw):
    refs={name:d.binding(folder/(name+".log")) for name in ("stdout","stderr")}
    data,_=d.bytes_binding(output,8192)
    d.need(data==b"M192c deterministic synthetic output\nnull\n"+bytes(range(256))*16,"actual known null output")
    d.need(all(r["bytes"]<=8192 for r in refs.values()),"bounded null logs")
    result=dict(returncode=raw["returncode"],stdout=dict(bytes=refs["stdout"]["bytes"],sha256=refs["stdout"]["sha256"]),
        stderr=dict(bytes=refs["stderr"]["bytes"],sha256=refs["stderr"]["sha256"]),
        output=dict(bytes=len(data),sha256=sha(data)))
    return result,refs
def finish(result,pub,budget,planref,sources):
    def admission():
        budget.check(True,terminal=True)
        d.need(budget.accounting_error is None and time.process_time()+budget.child_cpu+.25<=20 and
            time.monotonic()-START+.5<=30 and budget.observed<=LIMITS["output_bytes"],"whole phase plus fixed publication reserve")
    result["publication_allowance"]=dict(cpu_seconds=.25,wall_seconds=.5)
    result["complete_process_cpu_accounting"]=False;result["actual_outer_exit_required"]=True
    try:
        for ref in sources.values():d.bytes_binding(ref["path"],ref["bytes"],expected=ref)
        admission()
    except BaseException as exc:result.update(status="REFUSED",final_error=dict(type=type(exc).__name__,message=str(exc)[-1024:]))
    result["accounting_sample"]=dict(parent_or_worker_process_cpu_seconds=time.process_time(),latest_owned_job_cpu_seconds=budget.child_cpu,
        wall_seconds=time.monotonic()-START,accounting_error=budget.accounting_error,observed_file_bytes=budget.observed)
    published=pub.publish(result,late=admission if result["status"]!= "REFUSED" else lambda:None,
        emit=lambda ref:print(json.dumps(dict(status=result["status"],plan=planref,result=ref),allow_nan=False),flush=True),
        after=admission if result["status"]!="REFUSED" else lambda:None)
    return 0 if published["passed"] else 1
def worker(args,plan,planref,sources,out):
    b=Budget(out);publication=load(sources[str(PUBLICATION)],"m192e_startup_worker_publication")
    folder=out/"worker";folder.mkdir()
    pub=publication.Publisher(publication.Writer(b,folder,"terminal"),dict(schema="m192e-startup-worker-v1",plan=planref),size=32768)
    result=dict(schema="m192e-startup-worker-v1",status="REFUSED",plan=planref,arms=[],unvisited=list(ARMS),active=None,error=None)
    try:
        s=load(sources[str(SAMPLER)],"m192e_startup_sampler")
        baseline=None
        for arm in ARMS:
            b.check(True);result["active"]=arm
            area=out/"arms"/arm;area.mkdir(parents=True);monitor_folder=area/"monitor"
            output=area/"null-output.bin";child_receipt=area/"child-receipt.json"
            command=[plan["python"]["path"],"-B",str(CHILD),"--mode","null","--output",str(output),"--receipt",str(child_receipt)]
            probe=None;construction=None;raw=None;error=None;start=time.monotonic()
            try:
                if arm=="off":function=s.monitor
                else:
                    probe=Probe(arm,s,sources)
                    function,construction=selected_function(SAMPLER,"monitor",dict(s.__dict__,probe=probe),MONITOR_CALLS,sources[str(SAMPLER)])
                raw=function(argv=command,env=os.environ.copy(),folder=monitor_folder,mode="on")
            except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc)[-1024:])
            finally:
                startup=dict(arm=arm,mode="OFF" if probe is None else "ON_LABEL_PLACEBO" if arm=="placebo" else "ON",
                    phases=[] if probe is None else probe.rows,child_pid=None if probe is None else probe.child_pid,
                    actual_popen_argv=None if probe is None else probe.popen_argv,
                    actual_popen_flags=None if probe is None else probe.popen_flags,monitor_ast=construction,
                    assignment_ast=None if probe is None else probe.assign_ast,error=error,
                    baseline_query_added=False,old_sampling_origin_changed=False)
                startref=b.save(area/"startup.json",startup,8192,terminal=True)
            record=dict(arm=arm,command=command,startup=startref,wall_seconds=time.monotonic()-start,error=error,
                        passed=False,raw=None,intrinsic=None,first_observation_interval_ms=None)
            if raw is not None:
                record["raw"]=b.save(area/"monitor.json",raw,384*1024)
                actual,logs=intrinsic(monitor_folder,output,raw);record.update(intrinsic=actual,logs=logs,output=d.binding(output),
                    child_receipt=d.binding(child_receipt),sampling_pass=raw["sampling_pass"],coverage=raw["coverage"],
                    maximum_interval_ms=raw["max_interval_ms_including_final"],dropped=raw["trace"]["dropped"])
                observed=raw["trace"]["observations"]
                d.need(observed and observed[0]["poll"]==0 and all(v==0 for v in raw["trace"]["dropped"].values()),"complete private trace")
                record["first_observation_interval_ms"]=(observed[0]["observed_ns"]-raw["start_ns"])/1e6
                child_rows=d.read_json(child_receipt,8192)
                d.need(type(child_rows) is list and len(child_rows)==2 and child_rows[0]["event"]=="start" and
                    child_rows[-1]["event"]=="end" and child_rows[0]["mode"]=="null" and
                    child_rows[0]["pid"]==child_rows[-1]["pid"] and
                    any(r["pid"]==child_rows[0]["pid"] for r in raw["processes"]),"actual private child identity witnessed")
                expected_phases=["startup-system-times","startup-memory-status","startup-create-job","startup-stdout-open",
                    "startup-stderr-open","startup-popen","startup-assign-job","startup-resume"]
                if probe is not None:
                    actual_phases=[r["phase"] for r in probe.rows if r["scope"]=="ACTUAL_STARTUP_CALL"]
                    d.need(actual_phases==expected_phases and probe.popen_argv==command and
                        probe.popen_flags==s.h.CREATE_SUSPENDED and probe.child_pid==child_rows[0]["pid"] and
                        all(r.get("error") is None for r in probe.rows),"all actual startup seams exercised")
                common=(raw["returncode"]==0 and raw["job_accounting"]["active_processes"]==0 and raw["argv"]==command)
                if baseline is None:baseline=actual
                record["intrinsic_matches_off"]=actual==baseline
                if arm in ("off","on","placebo"):record["passed"]=common and actual==baseline and raw["sampling_pass"]
                else:
                    delay=next(row for row in probe.rows if row["phase"]==arm)
                    elapsed=(delay["end_ns"]-delay["start_ns"])/1e6
                    popen=next(row for row in probe.rows if row["phase"]=="startup-popen")
                    resume=next(row for row in probe.rows if row["phase"]=="startup-resume")
                    positioned=(delay["end_ns"]<=popen["start_ns"]<child_rows[0]["qpc_ns"] if arm=="before-popen-delay" else
                        resume["end_ns"]<=delay["start_ns"]<delay["end_ns"]<=observed[0]["observed_ns"] and
                        resume["start_ns"]<=child_rows[0]["qpc_ns"]<=delay["end_ns"])
                    record.update(injected_phase_ms=elapsed,positioned=positioned,
                        passed=common and actual==baseline and elapsed>=140 and positioned and
                            raw["max_interval_ms_including_final"]>=140 and raw["sampling_pass"] is False)
            ref=b.save(area/"record.json",record,16384,terminal=True);result["arms"].append(ref)
            result["unvisited"].remove(arm);result["active"]=None
            b.save(out/"progress.json",result,32768,terminal=True,replace=(out/"progress.json").exists())
            d.need(error is None,"operational arm failure stops fixed suffix")
        values=[d.read_ref(ref,16384) for ref in result["arms"]]
        result.update(status=COMPLETE,all_five_pass=all(row["passed"] for row in values),
            intrinsic_all_identical=all(row.get("intrinsic_matches_off") for row in values),
            scope="Private startup attribution only; unchanged old sampling clock/gates; no production, RAW, TIFF or full campaign.")
    except BaseException as exc:result["error"]=dict(type=type(exc).__name__,message=str(exc)[-1024:])
    return finish(result,pub,b,planref,sources)
def parent(args,plan,planref,sources,out):
    out.mkdir();b=Budget(out);publication=load(sources[str(PUBLICATION)],"m192e_startup_parent_publication")
    folder=out/"parent";folder.mkdir()
    pub=publication.Publisher(publication.Writer(b,folder,"terminal"),dict(schema="m192e-startup-parent-v1",plan=planref),size=32768)
    result=dict(schema="m192e-startup-parent-v1",status="REFUSED",plan=planref,child=None,worker=None,error=None)
    try:
        utility=load(sources[str(SAVED)],"m192e_startup_job_selector")
        href=sources[str(HARNESS)]
        api=utility.selected(HARNESS,dict(bytes=href["bytes"],sha256=href["sha256"].lower()),utility.JOB_NAMES+utility.JOB_SIGNATURES)
        process=load(sources[str(PROCESS)],"m192e_startup_bounded_process")
        command=[args.plan_sha256 if x=="ACTUAL_PLAN_SHA256" else x for x in plan["commands"]["worker"]]
        child_path=out/"child.json"
        result["child"]=b.save(child_path,dict(status="UNOBSERVED",terminal_job_accounting=False),65536,terminal=True)
        remaining=30-(time.monotonic()-START)-12-2
        d.need(remaining>=8,"eight-second child envelope plus separate12 cleanup and2 publication")
        query=api.job_accounting
        def live(job):
            value=query(job);before=d.encode(value);b.observe(value)
            d.need(d.encode(value)==before,"live accounting observer preserves exact returned content");return value
        api.job_accounting=live
        try:
            child=process.run(command,os.environ.copy(),ROOT,out/"worker.log",api=api,wall_seconds=min(12,remaining),
                cpu_seconds=20-time.process_time()-2,log_bytes=128*1024,committed_bytes=1024*(1<<20),check=b.check)
        finally:api.job_accounting=query
        # Capture exact observed terminal before any acceptance check can refuse.
        result["child"]=b.save(child_path,child,65536,terminal=True,replace=True)
        worker_path=out/"worker"/"result.json"
        if worker_path.exists():result["worker"]=d.binding(worker_path)
        d.need(child["error"] is None and not child["cleanup_errors"] and child["exit_code"]==0 and
            child["terminal_job_accounting"] is True and not child["termination"]["attempted"],"natural actual worker tree")
        value=d.read_ref(result["worker"],32768)
        d.need(value["status"]==COMPLETE and value["unvisited"]==[] and len(value["arms"])==5,"complete fixed private population")
        result.update(status=COMPLETE,arms=value["arms"],all_five_pass=value["all_five_pass"],
            intrinsic_all_identical=value["intrinsic_all_identical"],terminal_job_accounting=True)
    except BaseException as exc:result["error"]=dict(type=type(exc).__name__,message=str(exc)[-1024:])
    return finish(result,pub,b,planref,sources)
def main():
    p=argparse.ArgumentParser();p.add_argument("--plan",required=True,type=Path);p.add_argument("--plan-sha256",required=True)
    p.add_argument("--worker",action="store_true");args=p.parse_args()
    plan,ref,sources,out=setup(args)
    return worker(args,plan,ref,sources,out) if args.worker else parent(args,plan,ref,sources,out)
if __name__=="__main__":raise SystemExit(main())
