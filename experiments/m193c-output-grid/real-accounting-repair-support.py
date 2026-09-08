"""Operational accounting repair; immutable science stays in the held real runner."""
import ast,copy,hashlib,json,math,os,time,types
from contextlib import contextmanager
from pathlib import Path
KIB=1024;MIB=1<<20
OPERATIONAL_BYTES=128*KIB
EXTENSION=dict(cpu_seconds=120,wall_seconds=0,file_bytes=0,metadata_bytes=0)
OLD_GLOBAL=dict(cpu_seconds=1200,wall_seconds=1800,file_bytes=4<<30,metadata_bytes=128*MIB)
NEW_GLOBAL=dict(OLD_GLOBAL,cpu_seconds=1320)
ATTEMPT=dict(cpu_seconds=100,wall_seconds=180,file_bytes=8*MIB,metadata_bytes=8*MIB)
PROBE_PIN=dict(bytes=13921,sha256="aaa98419c7141eba44be2e0df746d26a36938f9232e85e2075aba6bdb9a52cfe")
OLD_PIN=dict(bytes=51374,sha256="038a7d649932553891e16018efe1a5d6b6ad313a8073471c4dc8b6a19ce3a420")
CONTROL_IDS=("joint-cpu-refusal","exact-boundary-positive","restored-live-refusal")
def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def load(path,expected,name):
    raw=Path(path).read_bytes();need(dict(bytes=len(raw),sha256=sha(raw))==expected,"held operational dependency")
    module=types.ModuleType(name);module.__file__=str(path)
    import sys
    sys.modules[name]=module;exec(compile(raw,str(path),"exec"),module.__dict__);return module

def make_budget(n,old,output,prior,worker,grant,started,*,control=False):
    """Reuse the executed comparison's exact optimization, then explicit grant/liveness seams."""
    need(grant["previous_cumulative_limits"]==OLD_GLOBAL and grant["additional_authorized_work"]==EXTENSION
         and grant["new_cumulative_limits"]==NEW_GLOBAL and grant["attempt_caps"]==ATTEMPT,
         "separate explicit one-attempt CPU authorization")
    probe=load(old.HERE/"work/accounting-callback-comparison.py",PROBE_PIN,"m193c_accounting_probe_definition")
    source=(old.HERE/"sift-lightglue-real-run.py").read_bytes()
    need(dict(bytes=len(source),sha256=sha(source))==OLD_PIN,"old real source remains immutable")
    original=probe.select(source,probe.OLD_NAMES);tree=probe.optimized(original)
    optimized_sha=probe.digest_ast(tree)
    # These two extra replacements implement the reviewed resource grant only.
    # They are separate from the previously tested three optimization changes.
    class Grant(ast.NodeTransformer):
        def __init__(self):self.changed=0
        def visit_Constant(self,node):
            if type(node.value) is int and node.value==1200:
                self.changed+=1;return ast.Name(id="AUTHORIZED_CPU_CEILING",ctx=ast.Load())
            return node
    replace=Grant();tree=replace.visit(tree);need(replace.changed==2,"two explicit factory global CPU references")
    namespace=dict(Path=Path,time=time,contextmanager=contextmanager,START=started,AUTHORIZED_CPU_CEILING=NEW_GLOBAL["cpu_seconds"])
    exec(compile(ast.fix_missing_locations(tree),str(Path(__file__).resolve()),"exec"),namespace)
    class AuthorizedBase(n.Budget):
        def work(self):
            value=super().work()
            injected=getattr(self,"injected_parent_cpu",None)
            if injected is not None:
                need(getattr(self,"control_scope",False),"injected accounting confined to explicit control")
                value["cpu_seconds"]=self.prior["cpu_seconds"]+injected+self.child_cpu
            if getattr(self,"extent_uncertain",False):
                for key in ("file_bytes","metadata_bytes"):value[key]=self.prior[key]+ATTEMPT[key]
            return value
        def check(self,force=False):
            now=time.monotonic()
            if force or now-self.last_scan>=.2:self.scan()
            value=self.work()
            for key,maximum in NEW_GLOBAL.items():
                need(value[key]<=maximum,"complete authorized "+key+" bound")
    proxy=types.SimpleNamespace(**vars(n));proxy.Budget=AuthorizedBase
    budget=namespace["budget_for"](proxy,output,prior,worker)
    old_families=dict(namespace["FAMILIES"])
    namespace["FAMILIES"]={**old_families,"operational":OPERATIONAL_BYTES}
    need(sum(namespace["FAMILIES"].values())==8217472<=ATTEMPT["file_bytes"],"new concrete family ledger within unchanged8MiB")
    ParentClass=type(budget)
    class Budget(ParentClass):
        def check(self,force=False,terminal=None):
            if self.transport_depth:
                now=time.monotonic()
                if force or now-self.last_scan>=.2:self.scan()
                value=self.work();totals=self.totals()
                for key in ("file_bytes","metadata_bytes"):
                    need(value[key]<=NEW_GLOBAL[key] and value[key]-self.prior[key]<=ATTEMPT[key],"transport extent cap")
                need(all(totals[k]<=cap for k,cap in self.families.items()),"transport family cap")
                return
            need(self.job_accounting_error is None,"invalid live Job accounting")
            return super().check(force,terminal)
        def reserve(self,path,size,family,terminal):
            path=Path(path).resolve()
            if self.transport_depth:
                allowed=self.transport_slots.get(str(path))
                need(allowed is not None and allowed[0]==family and 0<size<=allowed[1],
                     "only declared bounded transport slots")
            return super().reserve(path,size,family,terminal)
        @contextmanager
        def terminal(self):
            # The inherited science uses this only for its bounded guard-exit receipt.
            outer=self.transport_depth==0
            if outer:
                self.transport_entries+=1;self.transport_start=(time.process_time(),time.monotonic())
            self.transport_depth+=1;previous=self.terminal_mode;self.terminal_mode=True
            try:yield
            finally:
                self.terminal_mode=previous;self.transport_depth-=1
                if outer:
                    self.transport_cpu+=time.process_time()-self.transport_start[0]
                    self.transport_wall+=time.monotonic()-self.transport_start[1];self.transport_start=None
        def admit_terminal(self):
            previous=self.transport_depth;self.transport_depth=0
            try:
                self.check(True,terminal=True)
                stats=self.transport_cost()
                need(stats["cpu_seconds"]<=2 and stats["wall_seconds"]<=3,"bounded publication transport allowance")
            finally:self.transport_depth=previous
        def register_transport(self,path,family,maximum):
            path=Path(path).resolve();need(path.is_relative_to(self.output),"owned terminal slot")
            key=str(path);value=(family,maximum)
            need(key not in self.transport_slots or self.transport_slots[key]==value,"fixed terminal slot reservation")
            self.reserve(path,maximum,family,True);self.transport_slots[key]=value
        def observe_job(self,accounting):
            """Called immediately after the unchanged actual Job query; never invents CPU."""
            self.job_observations+=1
            self.latest_job_accounting=accounting
            if type(accounting) is dict and type(accounting.get("total_cpu_100ns")) is int and accounting["total_cpu_100ns"]>=0:
                current=accounting["total_cpu_100ns"]/1e7
                if current>=self.child_cpu:self.child_cpu=current
                else:self.job_accounting_error="nonmonotone actual Job CPU"
            else:self.job_accounting_error="missing typed actual Job CPU"
        def transport_cost(self):
            active=(0.,0.) if self.transport_start is None else (time.process_time()-self.transport_start[0],time.monotonic()-self.transport_start[1])
            return dict(entries=self.transport_entries,cpu_seconds=self.transport_cpu+active[0],wall_seconds=self.transport_wall+active[1],
                        allowance=dict(cpu_seconds=2,wall_seconds=3),scope="actual transport intervals; no scientific admission after cap failure")
        def transport_summary(self):
            return dict(reserved_slots={Path(p).relative_to(self.output).as_posix():[family,size]
                                       for p,(family,size) in sorted(self.transport_slots.items())},
                        live_job_queries=self.job_observations,latest_job_accounting=self.latest_job_accounting,
                        job_accounting_error=self.job_accounting_error,transport_cost=self.transport_cost())
    budget.__class__=Budget
    budget.transport_depth=0;budget.transport_slots={};budget.control_scope=control
    budget.injected_parent_cpu=None;budget.job_observations=0
    budget.latest_job_accounting=None;budget.job_accounting_error=None
    budget.transport_entries=0;budget.transport_start=None;budget.transport_cpu=0.;budget.transport_wall=0.;budget.extent_uncertain=False
    budget.families=namespace["FAMILIES"];budget.metadata_families=namespace["META"]
    budget.optimized_ast_sha256=optimized_sha;budget.granted_ast_sha256=probe.digest_ast(tree)
    budget.grant=grant
    return budget

def prepare_transport(b,pub,out,worker):
    (out/"operational").mkdir(exist_ok=True)
    for name in pub.NAMES:b.register_transport(out/name,"terminal",64*KIB)
    if worker:
        b.register_transport(out/"metadata/manifest/population.json","metadata",48*KIB)
        b.register_transport(out/"metadata/state/import-guard-final.json","metadata",2048)
    else:
        b.register_transport(out/"operational/child-terminal.json","operational",16*KIB)
    b.register_transport(out/"operational/accounting-final.json","operational",8192)

def write_slot(pub,b,path,value,maximum=16*KIB):
    raw=encoded(value);need(len(raw)<=maximum,"fixed transport payload size")
    raw+=b" "*(maximum-len(raw))
    with b.terminal():
        ref=pub.Writer(b,Path(path).parent,"operational").write(path,raw,replace=True,terminal=True)
    return ref

@contextmanager
def live_job_accounting(api,b):
    original=api.job_accounting
    def observe(job):
        value=original(job);b.observe_job(value);return value
    api.job_accounting=observe
    try:yield
    finally:
        api.job_accounting=original
        need(api.job_accounting is original,"actual Job observer restoration")

def capture_child(pub,b,path,observed,*,injected=False):
    """Durable exact observation precedes every new admission assertion."""
    need(injected==b.control_scope,"control/actual Job receipt scopes agree")
    accounting=observed.get("job_accounting")
    b.observe_job(accounting)
    b.complete=(observed.get("terminal_job_accounting") is True and
                type(accounting) is dict and accounting.get("active_processes")==0
                and b.job_accounting_error is None)
    value=dict(schema="m193c-durable-child-terminal-v1",
               measurement_scope="INJECTED_ACCOUNTING_SEAM" if injected else "ACTUAL_OWNED_JOB_RETURN",
               observation=observed,live_job_queries=b.job_observations,
               latest_job_accounting=b.latest_job_accounting,
               job_accounting_error=b.job_accounting_error,
               parent_and_child_work=b.work(),new_run_cpu_accounting_complete=b.complete)
    ref=write_slot(pub,b,path,value)
    # Deliberately outside the durable write and transport context.
    b.admit_terminal()
    return ref

def refresh_recovery(publisher,b,links):
    """Keep the old durable emergency until the complete replacement is fsynced."""
    value=dict(publisher.default,**links,status="REFUSED",publication_phase="BOUND_RECOVERY_REFUSAL")
    need(len(encoded(value))<=min(publisher.size,16*KIB),"bounded refreshed recovery object")
    raw=publisher.pack(value)
    with b.terminal():
        publisher.writer.write(publisher.paths["publication-stage.json"],raw,replace=True,terminal=True)
        publisher.writer.replace(publisher.paths["publication-stage.json"],publisher.paths["emergency-refusal.json"])
    need(publisher.paths["emergency-refusal.json"].read_bytes()==raw,"bound fallback exact readback")
    publisher.default=value;publisher.default_raw=raw
    return dict(path=str(publisher.paths["emergency-refusal.json"]),bytes=len(raw),sha256=sha(raw))

def operation_controls(n,old,pub,parent,grant,root,started):
    """The real finalizer/publisher path, explicit injected counters, zero child launches."""
    root.mkdir();rows=[]
    # All control I/O is separately charged to the actual outer budget.
    def charge(path,size):
        parent.reserve(path,size,"operational",False)
    def actual_writer(path,raw):
        charge(path,len(raw))
        with path.open("wb") as stream:
            need(stream.write(raw)==len(raw),"complete operational control evidence")
            stream.flush();os.fsync(stream.fileno())
    for index,(name,parent_final,passed) in enumerate((
            ("joint-cpu-refusal",6,False),("exact-boundary-positive",5,True),("restored-live-refusal",6,False))):
        parent.check(True);folder=root/name
        row=dict(id=name,passed=False,measurement_scope="INJECTED_ACCOUNTING_SEAM",expected_admission=passed)
        rows.append(row)
        try:
            folder.mkdir()
            # A private bookkeeping budget with zero prior is labelled and never used by science.
            control=make_budget(n,old,folder,dict(cpu_seconds=0.,wall_seconds=0.,file_bytes=0,metadata_bytes=0),
                                False,grant,time.monotonic(),control=True)
            for filename in pub.NAMES:control.register_transport(folder/filename,"terminal",2048)
            child_path=folder/"child-terminal.json"
            control.register_transport(child_path,"operational",16*KIB)
            for filename in pub.NAMES:charge(folder/filename,2048)
            charge(child_path,16*KIB)
            publisher=pub.Publisher(pub.Writer(control,folder,"terminal"),
                dict(schema="m193c-accounting-control-v1",id=name,measurement_scope="INJECTED_ACCOUNTING_SEAM"),2048)
            control.injected_parent_cpu=1.
            limits=control.limits();need(limits["cpu_seconds"]==95,"actual inherited child allowance95")
            control.injected_parent_cpu=float(parent_final)
            observed=dict(command=["INJECTED_ACCOUNTING_NO_PROCESS"],exit_code=0,error=None,
                          job_accounting=dict(total_cpu_100ns=950000000,active_processes=0),
                          terminal_job_accounting=True)
            error=None
            try:receipt=capture_child(pub,control,child_path,observed,injected=True)
            except ValueError as exc:
                error=str(exc);receipt=dict(path=str(child_path),bytes=child_path.stat().st_size,sha256=sha(child_path.read_bytes()))
            actual=json.loads(child_path.read_bytes())
            need(actual["observation"]==observed and actual["parent_and_child_work"]["cpu_seconds"]==95+parent_final,
                 "exact declared Joint CPU evidence survived admission")
            need((error is None)==passed and (passed or error=="local cap"),"powered combined CPU admission")
            value=dict(schema="m193c-accounting-control-v1",id=name,
                       status="COMPLETE_CONTROL_ONLY" if passed else "REFUSED",
                       measurement_scope="INJECTED_ACCOUNTING_SEAM",child_terminal=receipt,error=error)
            refresh_recovery(publisher,control,dict(child_terminal=receipt,error=error))
            actual_value=dict(value,padding="x"*4096) if index==0 else value
            with control.terminal():
                publication=publisher.publish(actual_value,late=control.admit_terminal if passed else lambda:None)
            if index==0:
                actual,_=publisher.actual()
                need(publication["error"]["phase"]=="ENCODING" and actual["child_terminal"]==receipt and actual["error"] is not None,
                     "powered encoding refusal preserves refreshed exact child binding")
            need(publication["passed"]==passed and (passed or publication["canonical_refusal_verified"] is True),
                 "actual terminal transport remains available after joint cap refusal")
            if index==2:
                # The live update is also on the exact pre-operation check path.
                count=0
                try:control.check()
                except ValueError as exc:need(str(exc)=="local cap","live combined refusal")
                else:count+=1
                need(count==0,"next scientific operation remains unvisited")
                # Retain the refusal bytes before restoring this same publisher.
                refusal_copy=folder/"refused-canonical.json"
                refused_raw=(folder/"result.json").read_bytes();actual_writer(refusal_copy,refused_raw)
                publication=dict(publication,canonical=dict(path=str(refusal_copy),bytes=len(refused_raw),sha256=sha(refused_raw)),
                                 original_canonical_path=str(folder/"result.json"))
                control.injected_parent_cpu=5.
                control.admit_terminal()
                with control.terminal():
                    restored=publisher.publish(dict(schema="m193c-accounting-control-v1",id=name,
                        status="COMPLETE_RESTORATION_CONTROL_ONLY",measurement_scope="INJECTED_ACCOUNTING_SEAM",
                        restored_parent_cpu=5,child_cpu=95,combined_cpu=100,preceding_failure_child=receipt),
                        late=control.admit_terminal)
                need(restored["passed"] is True,"same-instance restored accounting/publication")
                row["restoration"]=restored
            row.update(passed=True,child_terminal=receipt,combined_cpu=95+parent_final,
                       child_allowed_cpu=limits["cpu_seconds"],error=error,publication=publication)
        except BaseException as exc:
            row["failure"]=dict(type=type(exc).__name__,message=str(exc));raise
        finally:
            for path in folder.iterdir() if folder.exists() else ():
                if path.is_file():charge(path,path.stat().st_size)
            raw=encoded(dict(schema="m193c-accounting-control-prefix-v1",rows=rows))
            need(len(raw)<=8192,"bounded operational control prefix")
            actual_writer(root/"controls.json",raw)
    parent.check(True)
    return dict(path=str(root/"controls.json"),bytes=(root/"controls.json").stat().st_size,
                sha256=sha((root/"controls.json").read_bytes()))


def live_controls(n,old,pub,parent,grant,root):
    """Powered injected query wrapper only: never an actual Windows Job observation."""
    root.mkdir();rows=[]
    def fixture(name,prior_cpu=0):
        folder=root/name;folder.mkdir()
        b=make_budget(n,old,folder,dict(cpu_seconds=prior_cpu,wall_seconds=0.,file_bytes=0,metadata_bytes=0),
                      False,grant,time.monotonic(),control=True)
        b.injected_parent_cpu=1.;return b
    records=[dict(total_cpu_100ns=10000000,active_processes=1),
             dict(total_cpu_100ns=20000000,active_processes=0)]
    intrinsic=[]
    for mode in ("off","on","placebo"):
        b=fixture(mode);queries=[]
        def query(job):
            need(job=="INJECTED_JOB_TOKEN","labelled fake Job query")
            value=records[len(queries)];queries.append(value);return value
        api=types.SimpleNamespace(job_accounting=query)
        values=[]
        if mode=="off":
            values=[api.job_accounting("INJECTED_JOB_TOKEN") for _ in records]
        else:
            with live_job_accounting(api,b):
                for index in range(len(records)):
                    value=api.job_accounting("INJECTED_JOB_TOKEN");values.append(value)
                    need(value is records[index] and b.child_cpu==index+1 and b.job_observations==index+1,
                         "actual wrapper delegates once, retains identity and updates each counter")
                    if mode=="on":need(sha(encoded(value))==sha(encoded(records[index])),"observer exact content")
        need(api.job_accounting is query and len(queries)==2,"normal wrapper restoration/once delegation")
        digest=sha(encoded(values));intrinsic.append(digest)
        rows.append(dict(id="live-wrapper-"+mode,passed=True,intrinsic_sha256=digest,queries=len(queries),
                         observed_queries=b.job_observations,restored=True))
    need(len(set(intrinsic))==1,"whole injected query off/on/placebo equality")
    for name,values in (("decreasing",[dict(total_cpu_100ns=20000000),dict(total_cpu_100ns=10000000)]),
                        ("malformed",[dict(total_cpu_100ns="10000000")])):
        b=fixture(name);calls=[]
        def query(job):
            value=values[len(calls)];calls.append(value);return value
        api=types.SimpleNamespace(job_accounting=query);next_operations=0;error=None
        try:
            with live_job_accounting(api,b):
                for _ in values:api.job_accounting("INJECTED_JOB_TOKEN")
                b.check();next_operations+=1
        except ValueError as exc:error=str(exc)
        need(error=="invalid live Job accounting" and next_operations==0 and api.job_accounting is query,
             "invalid query blocks next operation and restores wrapper on exception")
        rows.append(dict(id="live-wrapper-"+name,passed=True,error=error,queries=len(calls),
                         next_operations=next_operations,restored=True,retained_accounting_error=b.job_accounting_error))
    b=fixture("explicit-new-ceiling",1222);b.injected_parent_cpu=97.;b.admit_terminal()
    positive=b.work()["cpu_seconds"];b.injected_parent_cpu=99.;error=None
    try:b.admit_terminal()
    except ValueError as exc:error=str(exc)
    need(positive==1319 and error=="complete authorized cpu_seconds bound","retired1200 replaced only by explicit1320")
    rows.append(dict(id="authorized-cumulative-ceiling",passed=True,admitted_cpu=positive,
                     refused_cpu=b.work()["cpu_seconds"],error=error,retired_ceiling=1200,new_ceiling=1320))
    value=dict(schema="m193c-injected-live-accounting-controls-v1",
               scope="INJECTED_QUERY_AND_ACCOUNTING_SEAMS_NOT_WINDOWS_PROCESS_BOUNDARY",rows=rows)
    path=root/"live-controls.json";parent.register_transport(path,"operational",8192)
    ref=write_slot(pub,parent,path,value,8192);parent.check(True);return ref
