"""Fixed original/repaired checked-sampler stages; SOURCE ONLY until root release.
Reuses held M194h owned-process/read/scan/accounting definitions, no old science.
"""
import time
START=time.monotonic()
from pathlib import Path
import argparse,hashlib,json,math,os,re,shutil,stat,sys,types
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
KIB=1024;MIB=1<<20;GIB=1<<30
BASE=ROOT/"experiments/m194h-pedestal-causality/build-and-run.py"
BASE_SHA="b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410"
REUSED=ROOT/"experiments/common-tiff-stack/run-stage.py"
REUSED_SHA="25d9b11cd0b99c1720ff460a4237209eaa9c6a36a8ffa8ade50afa608f41cb05"
BUILD_PROCESS=HERE/"bounded-build-process.py"
BUILD_SHA="bdd7ff3328de37789ac212cf5f4d868ad3580939827c4a7ca10a669c2ddc995c"
TEST_SOURCE=ROOT/"crates/strehl-core/tests/sampler-boundary.rs"
TEST_SPEC=HERE/"independent-test-spec.md"
TEST_NAME="sampler_boundary_public_contract"
ALIGN=ROOT/"crates/strehl-core/src/align.rs"
ORIGINAL_ALIGN_SHA="6d33f0e24f21d4370ccd8df0bf618e54a5ad615b838bc265469b4f85051c2786"
SCHEMA="sampler-boundary-stage-release-v1"
RESULT="sampler-boundary-owned-stage-v1"
EXTERNAL="sampler-boundary-stage-external-v1"
TAIL="sampler-boundary-parent-tail-v1"
STAGES={"regression":dict(cpu_seconds=30,wall_seconds=60,committed_bytes=512*MIB,file_bytes=16*MIB,scratch_bytes=0),
        "build":dict(cpu_seconds=600,wall_seconds=300,committed_bytes=3*GIB,file_bytes=128*MIB,scratch_bytes=4*GIB),
        "test":dict(cpu_seconds=30,wall_seconds=60,committed_bytes=512*MIB,file_bytes=16*MIB,scratch_bytes=0)}
VARIANTS=("baseline","repaired")
REQUIRED=("charter.md","run-stage.py","bounded-build-process.py","run-stage-contract.md","independent-test-spec.md",
          "prepare-release.py","capture-stage.py","source-review.md")
TAIL_CPU=2;TAIL_WALL=3
TARGET=None;OUTPUTS={};d=None

def need(value,message):
    if not value:raise ValueError(message)

def bootstrap(path,cap):
    path=Path(os.path.abspath(path))
    for p in (path,*path.parents):
        if p.exists():
            s=p.lstat()
            need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"bootstrap plain ancestry")
    before=path.stat();need(stat.S_ISREG(before.st_mode) and 0<before.st_size<=cap,"bootstrap bounded source")
    with path.open("rb") as stream:
        opened=os.fstat(stream.fileno());raw=stream.read(cap+1);after=os.fstat(stream.fileno())
    final=path.stat()
    full=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
    need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
         and len(raw)==before.st_size and len(raw)<=cap,"bootstrap same source bytes")
    return raw

def load_base():
    global d
    raw=bootstrap(BASE,128*KIB)
    need(hashlib.sha256(raw).hexdigest()==BASE_SHA,"held M194h primitive source")
    d=types.ModuleType("common_tiff_held_m194h_primitives");d.__file__=str(BASE)
    exec(compile(raw,str(BASE),"exec"),d.__dict__)
    # Only globals consumed by the listed reused non-scientific primitives change.
    d.START=START;d.HERE=HERE;d.SELF=SELF;d.TARGET=TARGET;d.STAGES=STAGES;d.OUTPUTS=OUTPUTS
    d.BUILD_PROCESS=BUILD_PROCESS;d.BUILD_PROCESS_SHA=BUILD_SHA
    d.FIXED_ENV={"RAYON_NUM_THREADS":"2"}
    return d

def file_ref(path,cap,expected=None,check=lambda:None):
    return d.read(path,cap,expected,keep=False,check=check)[1]

def source_check(sources,budget):
    for key in sources:d.source_bytes(ROOT/key,sources,budget.check)
    return d.source_closure(sources,budget.check)

def input_check(release,budget):
    inputs=release["inputs"]
    need(type(inputs) is list and 1<=len(inputs)<=128,"bounded released input roles")
    seen=set();total=0
    for ref in inputs:
        need(type(ref) is dict and set(ref)=={"path","bytes","sha256"} and type(ref["bytes"]) is int
             and 0<ref["bytes"]<=64*MIB,"positive released input")
        p=d.lexical(ROOT/ref["path"]);need(p not in seen,"unique released input")
        seen.add(p);total+=ref["bytes"];file_ref(p,64*MIB,ref,budget.check)
    need(total<=256*MIB and d.lexical(sys.executable) in seen,"input aggregate/current Python")
    if release["stage"]=="build":
        tools={d.lexical(shutil.which(name) or "") for name in ("cargo","rustc")}
        need(len(tools)==2 and tools<=seen,"actual resolved Cargo/rustc bindings")
    return inputs

def child_call(process,api,command,env,expected_exit,index,output,budget,result):
    compile_case=budget.stage=="build" and index==0
    need((getattr(process,"BUILD_ONLY",False) is True)==compile_case,"build-only process dispatch")
    limits=budget.limits(index);original=api.job_accounting
    budget.live_cpu=0.;budget.complete=False
    def observed(job):return budget.observe(original(job))
    api.job_accounting=observed
    try:record=process.run(command,env,ROOT,output/f"child-{index:02}.log",api=api,check=budget.check,**limits)
    finally:api.job_accounting=original
    # Receipt is durable before an expected exit or resource assertion can refuse.
    record_ref=d.write_new(output/f"child-{index:02}.json",d.encoded(record),32*KIB)
    result["children"].append(record_ref);d.atomic(output/"result.json",result)
    if record["job_accounting"] is not None:
        cpu=d.job_cpu(record["job_accounting"]);need(cpu>=budget.live_cpu,"terminal Job monotonicity")
        budget.completed_cpu+=cpu;budget.live_cpu=0.
    budget.complete=record["terminal_job_accounting"] is True
    need(budget.complete and record["job_accounting"]["active_processes"]==0,"complete child Job accounting")
    budget.check(True)
    need(record["error"] is None and not record["cleanup_errors"] and type(record["exit_code"]) is int
         and record["exit_code"]==expected_exit and record["direct_exit_observed"] is True
         and record["pipe_eof_observed"] is True and record["post_exit_drain"]["completed"] is True,"expected clean child terminal")
    need(record["termination"]["attempted"] is False,"failure cleanup cannot admit an expected refusal")
    if compile_case:d.admit_compile_cleanup(record)
    else:need("compile_cleanup" not in record,"strict policy for every nonbuild child")
    file_ref(output/f"child-{index:02}.log",limits["log_bytes"],record["log"],budget.check)
    return record

def output_path(stage,variant):return HERE/f"{variant}-{stage}-1"
def executable_path(variant):return output_path("build",variant)/"sampler-boundary-tests.exe"
def unit_executable_path(variant):return output_path("build",variant)/"core-unit-tests.exe"
def target_path(variant):return ROOT/f"target/sampler-boundary-{variant}-1"

def build_command(variant):
    return ["cargo","test","-p","strehl-core","--lib","--test","sampler-boundary","--no-run","--jobs","2",
            "--target-dir",str(target_path(variant)),"--message-format=json-render-diagnostics","--locked","--offline"]

def test_command(variant):
    return [str(executable_path(variant)),"--exact",TEST_NAME,"--nocapture","--test-threads=1"]

def authority(args):
    global TARGET,OUTPUTS
    need(os.name=="nt" and Path.cwd().resolve()==ROOT,"Windows repository cwd")
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"isolated stdlib controller")
    # Bootstrap metadata determines only one of five literal destinations.
    raw=bootstrap(args.release,MIB);need(hashlib.sha256(raw).hexdigest()==args.release_sha256,"release bootstrap SHA")
    provisional=json.loads(raw);stage=provisional.get("stage");variant=provisional.get("variant")
    need(stage in STAGES and variant in VARIANTS and (stage!="regression" or variant=="repaired"),"fixed sampler stage/variant")
    TARGET=target_path(variant);OUTPUTS={s:output_path(s,variant) for s in STAGES}
    load_base()
    path=d.owned(args.release);raw,ref=d.read(path,MIB)
    need(ref["sha256"]==args.release_sha256,"actual release SHA")
    release=d.strict(raw)
    keys={"schema","stage","variant","source_bindings","inputs","command","children","executable","prerequisites","prediction"}
    need(type(release) is dict and set(release)==keys and release["schema"]==SCHEMA
         and release["stage"]==stage and release["variant"]==variant,"closed ten-key release")
    need(path==HERE/"work"/f"{variant}-{stage}-release-1.json","fixed fresh release path")
    expected=[str(Path(sys.executable)),"-I","-S","-B",str(SELF),"--release",str(path),"--release-sha256",args.release_sha256]
    command=[args.release_sha256 if x=="ACTUAL_RELEASE_SHA256" else x for x in release["command"]]
    need(command==sys.orig_argv==expected and len(d.encoded(command))<=4*KIB,"exact controller argv")
    sources=release["source_bindings"];need(type(sources) is dict and 1<=len(sources)<=512,"bounded source map")
    resolved=set();total=0
    for key,pin in sources.items():
        need(type(key) is str and type(pin) is dict and set(pin)=={"bytes","sha256"},"source shape")
        need(type(pin["bytes"]) is int and 0<pin["bytes"]<=4*MIB and type(pin["sha256"]) is str
             and re.fullmatch("[0-9a-f]{64}",pin["sha256"]),"source extent/hash")
        p=d.owned(ROOT/key);need(d.source_ref(p)==key and p not in resolved,"canonical unique source")
        resolved.add(p);total+=pin["bytes"]
    need(total<=16*MIB,"source aggregate")
    need(all(d.source_ref(HERE/name) in sources for name in REQUIRED)
         and all(d.source_ref(p) in sources for p in (BASE,REUSED,d.PROCESS,d.HARNESS,TEST_SOURCE,ALIGN)),"mandatory source closure")
    for p,sha in ((BASE,BASE_SHA),(REUSED,REUSED_SHA),(BUILD_PROCESS,BUILD_SHA)):
        need(sources[d.source_ref(p)]["sha256"]==sha,"fixed reused source pin")
    pred=release["prediction"]
    need(type(pred) is dict and set(pred)=={"spec","test_source","expected_exit_code"}
         and type(pred["expected_exit_code"]) is int
         and pred["expected_exit_code"]==(101 if variant=="baseline" else 0),"source-predicted test disposition")
    for key,p in (("spec",TEST_SPEC),("test_source",TEST_SOURCE)):
        need(d.same_ref(pred[key],dict(path=d.source_ref(p),**sources[d.source_ref(p)])),"prediction source/spec association")
    align=sources[d.source_ref(ALIGN)]
    need((align["sha256"]==ORIGINAL_ALIGN_SHA)==(variant=="baseline"),"original versus repaired compiled sampler source")
    d.source_bytes(SELF,sources)
    output=OUTPUTS[stage];need(not output.exists(),"fresh once-only stage output");output.mkdir()
    budget=d.Budget(stage,output);budget.source_bindings=sources
    original_limits=budget.limits
    def limits(index):
        v=original_limits(index);v["log_bytes"]=16*MIB if stage=="build" else MIB
        return v
    budget.limits=limits
    result=dict(schema=RESULT,status="INITIAL_INCOMPLETE",stage=stage,variant=variant,release=ref,invocation=sys.orig_argv,
                children=[],artifacts={},prerequisites={},prediction=pred,work=None,error=None,finalization_errors=[],
                limits=STAGES[stage],tail_allowance=dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),
                scope="Bounded public sampler test path; an expected baseline failure is retained evidence, not a passing test or quality result.")
    d.atomic(output/"result.json",result)
    return release,ref,output,budget,result

def exact_children(release):
    stage=release["stage"];variant=release["variant"]
    command=build_command(variant) if stage=="build" else test_command(variant) if stage=="test" else regression_command(variant)
    expected=[dict(command=command,expected_exit_code=0 if stage=="build" else release["prediction"]["expected_exit_code"])]
    children=release["children"]
    need(type(children) is list and len(children)==1 and type(children[0]) is dict
         and set(children[0])=={"command","expected_exit_code"} and type(children[0]["expected_exit_code"]) is int
         and type(children[0]["command"]) is list and all(type(x) is str for x in children[0]["command"])
         and len(d.encoded(children[0]["command"]))<=4*KIB and children==expected,"one exact released child")
    return expected

def bundle_read(bundle,stage,variant,budget,sources):
    caps={"result":64*KIB,"tail":8*KIB,"outer":64*KIB,"stdout":8*KIB,"stderr":32*KIB,"exit":KIB}
    need(type(bundle) is dict and set(bundle)==set(caps),"six actual prior roles")
    raw={k:d.read(ROOT/bundle[k]["path"],cap,bundle[k],check=budget.check)[0] for k,cap in caps.items()}
    values={k:d.strict(raw[k]) for k in ("result","tail","outer","stdout")}
    result,tail,outer,advert=(values[k] for k in ("result","tail","outer","stdout"))
    need(d.lexical(ROOT/bundle["result"]["path"])==output_path(stage,variant)/"result.json"
         and d.lexical(ROOT/bundle["tail"]["path"])==output_path(stage,variant)/"parent-tail.json","fixed previous sampler paths")
    need(result["schema"]==RESULT and result["stage"]==stage and result["variant"]==variant
         and result["status"]=="COMPLETE_STAGE_UNVERIFIED" and result["error"] is None
         and not result["finalization_errors"],"completed prior operational stage")
    need(set(outer)=={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds",
                      "stdout","stderr","exit","stdout_bytes","stderr_bytes","scope"}
         and outer["schema"]==EXTERNAL and type(outer["exit_code"]) is int and outer["exit_code"]==0
         and outer["timeout_terminated"] is False and raw["exit"]==b"0\n","actual prior parent exit")
    need(outer["command"]==result["invocation"]
         and d.same_ref(outer["source"],dict(path=d.source_ref(SELF),**sources[d.source_ref(SELF)])),"prior command/controller source")
    for k in ("stdout","stderr","exit"):need(d.same_ref(outer[k],bundle[k]),"actual outer bytes")
    need(type(outer["stdout_bytes"]) is int and outer["stdout_bytes"]==len(raw["stdout"])
         and type(outer["stderr_bytes"]) is int and outer["stderr_bytes"]==len(raw["stderr"]),"actual stream extents")
    need(set(advert)=={"status","result","tail"} and advert["status"]==result["status"]
         and d.same_ref(advert["result"],bundle["result"]) and d.same_ref(advert["tail"],bundle["tail"])
         and raw["stdout"]==d.encoded(advert),"exact prior raw advertisement")
    need(tail["schema"]==TAIL and d.same_ref(tail["result"],bundle["result"])
         and tail["cpu_accounting_complete"] is True and tail["live_child_cpu_seconds"]==0
         and tail["final_external_allowance"]==dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),"prior final Job accounting")
    need(all(d.finite(tail[k]) for k in ("actual_parent_cpu_sample","whole_wall_sample","completed_child_cpu_seconds")),"prior finite times")
    need(d.finite(outer["elapsed_wall_seconds"]) and outer["elapsed_wall_seconds"]<=STAGES[stage]["wall_seconds"]
         and outer["elapsed_wall_seconds"]<=tail["whole_wall_sample"]+TAIL_WALL,"prior external whole wall")
    need(tail["actual_parent_cpu_sample"]+tail["completed_child_cpu_seconds"]+TAIL_CPU<=STAGES[stage]["cpu_seconds"]
         and result["work"]["cpu_accounting_complete"] is True,"prior CPU plus finite tail")
    oldraw,_=d.read(ROOT/result["release"]["path"],MIB,result["release"],check=budget.check);old=d.strict(oldraw)
    need(old["schema"]==SCHEMA and old["stage"]==stage and old["variant"]==variant
         and old["source_bindings"]==sources,"same frozen source map in linked prior stage")
    need([result["release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in old["command"]]==result["invocation"],"prior release invocation")
    for k,cap in caps.items():file_ref(ROOT/bundle[k]["path"],cap,bundle[k],budget.check)
    return result,old

def prerequisites(release,budget):
    stage=release["stage"];variant=release["variant"];sources=release["source_bindings"]
    expected={"build","test"} if stage=="regression" else {"build"} if stage=="test" else {"baseline"} if variant=="repaired" else set()
    need(type(release["prerequisites"]) is dict and set(release["prerequisites"])==expected,"exact prior sampler stages")
    prior={}
    if stage in ("test","regression"):
        built,old=bundle_read(release["prerequisites"]["build"],"build",variant,budget,sources)
        need(old["prediction"]==release["prediction"],"same reviewed test prediction")
        exe=executable_path(variant) if stage=="test" else unit_executable_path(variant)
        key="executable" if stage=="test" else "unit_executable"
        need(d.same_ref(release["executable"],built["artifacts"][key])
             and d.lexical(ROOT/release["executable"]["path"])==exe,"actual fresh test executable")
        file_ref(exe,32*MIB,release["executable"],budget.check);prior["build"]=built
        if stage=="regression":
            tested,previous=bundle_read(release["prerequisites"]["test"],"test",variant,budget,sources)
            observation=tested["artifacts"]["test_observation"]
            raw,_=d.read(ROOT/observation["path"],128*KIB,observation,check=budget.check);value=d.strict(raw)
            need(value["variant"]=="repaired" and value["actual_exit_code"]==0 and value["test_passed"] is True
                 and value["population_complete"] is True and value["rows"]==344 and value["failed"]==0,
                 "same-source repaired public contract passed before regressions")
            prior["test"]=tested
    else:
        need(release["executable"] is None,"no executable before fresh build")
        if variant=="repaired":
            bundle=release["prerequisites"]["baseline"]
            raw,_=d.read(ROOT/bundle["result"]["path"],64*KIB,bundle["result"],check=budget.check);r=d.strict(raw)
            raw,_=d.read(ROOT/r["release"]["path"],MIB,r["release"],check=budget.check);original=d.strict(raw)
            before=original["source_bindings"]
            baseline,original=bundle_read(bundle,"test","baseline",budget,before)
            changed={k for k in before if k not in sources or before[k]!=sources[k]}
            need(set(sources)==set(before) and changed=={d.source_ref(ALIGN)} and before[d.source_ref(ALIGN)]["sha256"]==ORIGINAL_ALIGN_SHA,
                 "only compiled align.rs changes in original source authorities")
            need(original["prediction"]["test_source"]==release["prediction"]["test_source"]
                 and original["prediction"]["spec"]==release["prediction"]["spec"],"unchanged independent tests and control spec")
            observation_ref=baseline["artifacts"]["test_observation"]
            raw,_=d.read(ROOT/observation_ref["path"],128*KIB,observation_ref,check=budget.check);observation=d.strict(raw)
            need(observation["variant"]=="baseline" and observation["test_passed"] is False
                 and observation["actual_exit_code"]==101 and observation["population_complete"] is True
                 and observation["rows"]==344 and observation["failed"]>0
                 and observation["exercised_public_boundary_failure"] is True,"actual original public assertion failure preserved")
            prior["baseline"]=baseline
    return prior

def compiled_binary(output,variant,budget):
    raw,_=d.read(output/"child-00.log",16*MIB,check=budget.check)
    need(b"Compiling strehl-core" in raw,"actual Compiling strehl-core line")
    artifacts=[];finished=[]
    for line in raw.splitlines():
        if not line.startswith(b"{"):continue
        value=d.strict(line)
        if value.get("reason")=="build-finished":finished.append(value)
        if value.get("reason")=="compiler-artifact" and value.get("executable"):
            artifacts.append(value)
    need(len(finished)==1 and set(finished[0])=={"reason","success"} and finished[0]["success"] is True,"actual successful test build-finished")
    need(len(artifacts)==2,"exact integration plus library test artifacts")
    result={"build_finished":finished[0],"compiler_messages":{}}
    for name,kind,source,destination,key in (("sampler-boundary","test",TEST_SOURCE,executable_path(variant),"executable"),
            ("strehl_core","lib",ROOT/"crates/strehl-core/src/lib.rs",unit_executable_path(variant),"unit_executable")):
        rows=[v for v in artifacts if v.get("target",{}).get("name")==name]
        need(len(rows)==1,"unique actual named test artifact");v=rows[0]
        need(v["fresh"] is False and v["profile"]["test"] is True and v["target"]["kind"]==[kind]
             and Path(v["target"]["src_path"]).resolve()==source
             and Path(v["manifest_path"]).resolve()==ROOT/"crates/strehl-core/Cargo.toml"
             and v["features"]==[],"fresh default-feature test executable")
        need(len(d.encoded(v))<=16*KIB,"bounded Cargo artifact")
        origin=d.owned(v["executable"]);need(origin.is_relative_to(target_path(variant)),"fresh variant target artifact")
        data,original=d.read(origin,32*MIB,check=budget.check)
        copied=d.write_new(destination,data,32*MIB)
        need(d.ref_binding(original)==d.ref_binding(copied),"copied actual test executable bytes")
        result[key]=copied;result[key+"_compiled_original"]=original;result["compiler_messages"][name]=v
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--release",required=True);parser.add_argument("--release-sha256",required=True)
    args=parser.parse_args();release=release_ref=output=budget=result=None
    try:
        release,release_ref,output,budget,result=authority(args)
        stage=release["stage"];variant=release["variant"];sources=release["source_bindings"]
        result["compiled_source_closure"]=source_check(sources,budget)
        input_check(release,budget);prior=prerequisites(release,budget)
        result["prerequisites"]=release["prerequisites"];schedule=exact_children(release)
        env={k:v for k,v in d.clean_env().items() if not k.upper().startswith(("SAMPLER_BOUNDARY_","RUST_TEST_"))}
        env["RUST_BACKTRACE"]="0";env["RUST_LIB_BACKTRACE"]="0"
        need(not any(k.upper().startswith(("STREHL_","M194H_","SAMPLER_BOUNDARY_")) for k in env),"no unrelated experiment override")
        result["environment"]={k:env.get(k) for k in ("RAYON_NUM_THREADS","CARGO_NET_OFFLINE","RUSTUP_TOOLCHAIN","RUSTUP_HOME","CARGO_HOME","RUST_BACKTRACE","RUST_LIB_BACKTRACE")}
        need(len(d.encoded(result["environment"]))<=8*KIB,"bounded observed toolchain environment")
        result["environment_scope"]="two Cargo jobs and two Rayon threads; inherited toolchain location is bound/observed, not hermetic"
        if stage=="build":need(not TARGET.exists(),"fresh target scratch")
        else:file_ref(ROOT/release["executable"]["path"],32*MIB,release["executable"],budget.check)
        process,api=d.load_process(sources,stage=="build")
        result["operations"]=[dict(ordinal=0,expected_exit_code=schedule[0]["expected_exit_code"],status="ATTEMPTED")]
        d.atomic(output/"result.json",result)
        child=schedule[0]
        record=child_call(process,api,child["command"],env,child["expected_exit_code"],0,output,budget,result)
        result["operations"][0]["status"]="EXPECTED_PROCESS_DISPOSITION"
        if stage=="build":result["artifacts"].update(compiled_binary(output,variant,budget))
        else:
            observation,summary=(test_transcript(output,variant,record,budget) if stage=="test"
                                 else regression_transcript(output,variant,record,budget))
            result["artifacts"]["test_observation" if stage=="test" else "regression_observation"]=observation
            result["test_disposition"]=summary
            file_ref(ROOT/release["executable"]["path"],32*MIB,release["executable"],budget.check)
        d.atomic(output/"result.json",result)
        need(source_check(sources,budget)==result["compiled_source_closure"],"unchanged final compiled source closure")
        input_check(release,budget);d.read(args.release,MIB,release_ref,check=budget.check)
        budget.check(True)
        result["inventory_sample"]=budget.inventory;result["scratch_sample"]=budget.scratch
        result["status"]="COMPLETE_STAGE_UNVERIFIED"
    except BaseException:
        if result is None:result=dict(schema=RESULT,status="REFUSED_BEFORE_OUTPUT",invocation=sys.orig_argv,children=[])
        result["status"]="REFUSED";result["error"]=d.error_value() if d is not None else dict(message="bootstrap/authority refusal")
    finally:
        if output is not None:
            result["work"]=budget.work()
            try:
                terminal=d.atomic(output/"result.json",result)
                tail=dict(schema=TAIL,result=terminal,actual_parent_cpu_sample=time.process_time(),
                          whole_wall_sample=time.monotonic()-START,completed_child_cpu_seconds=budget.completed_cpu,
                          live_child_cpu_seconds=budget.live_cpu,cpu_accounting_complete=budget.complete and budget.accounting_error is None,
                          final_external_allowance=dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),
                          scope="Sample after canonical publication; actual external exit/whole wall and reserved tail are required.")
                need(tail["actual_parent_cpu_sample"]+budget.completed_cpu+budget.live_cpu+TAIL_CPU<=budget.caps["cpu_seconds"]
                     and tail["whole_wall_sample"]+TAIL_WALL<=budget.caps["wall_seconds"],"final sampled envelope plus tail")
                tail_ref=d.write_new(output/"parent-tail.json",d.encoded(tail),8*KIB)
                advertised=dict(status=result["status"],result=terminal,tail=tail_ref)
            except BaseException:
                result["status"]="REFUSED";result["finalization_errors"].append(d.error_value())
                try:terminal=d.atomic(output/"result.json",result)
                except BaseException:terminal=None
                advertised=dict(status="REFUSED",result=terminal,error="terminal/tail refusal")
        else:advertised=result
        raw=d.encoded(advertised) if d is not None else (json.dumps(advertised,sort_keys=True,separators=(",",":"))+"\n").encode()
        need(len(raw)<=8*KIB,"bounded raw stdout");need(sys.stdout.buffer.write(raw)==len(raw),"full raw stdout");sys.stdout.buffer.flush()
    return 0 if result["status"]=="COMPLETE_STAGE_UNVERIFIED" else 1

GROUPS={"support":6,"boundary":126,"null":18,"nonfinite":36,"tiny":48,"unchecked":60,
        "constructor":4,"unchecked-tiny":20,"lanczos-commission":18,"cubic-limiter":6,"gather":2}
ROW_KEYS={"ordinal","id","group","kernel","api","x_f64_bits","y_f64_bits","actual_kind",
          "actual_f32_bits","oracle_kind","oracle_f32_bits","oracle_f64_bits","tolerance_code_units","exercised","passed"}

def expected_row_ids():
    kernels=("nearest","bilinear","catmull-rom","clamped-catmull-rom","lanczos2","lanczos3")
    boundary=("low-corner","low-x","low-y","interior-quarter","interior-half","last-integer",
              "high-x-quarter","high-x-half","high-y-quarter","high-y-half","high-corner-quarter","high-corner-half",
              "exact-upper-corner","just-low-x","just-low-y","just-high-x","just-high-y",
              "distant-low-x","distant-low-y","distant-high-x","distant-high-y")
    unchecked=("high-x-quarter","high-y-quarter","endpoint-x","endpoint-y","endpoint-corner",
               "far-high-x","far-high-y","far-high-corner","far-low-corner","interior-quarter")
    ids=[]
    for k in kernels:
        ids.append(k+"-support-literal")
        ids.extend(k+"-boundary-"+site for site in boundary)
        ids.extend(k+"-null-"+site for site in ("low","interior","upper"))
        ids.extend(k+"-nonfinite-"+kind+"-"+axis for kind in ("nan","positive-infinity","negative-infinity") for axis in ("x","y"))
        ids.extend(k+"-tiny-"+size for size in ("1x1","1x7","7x1","2x2","3x3","4x4","5x5","6x6"))
        ids.extend(k+"-unchecked-"+site for site in unchecked)
    for k in ("bilinear","catmull-rom","clamped-catmull-rom","lanczos2","lanczos3"):
        sizes=("1x7","7x1") if k=="bilinear" else ("1x7","7x1","2x7","7x2","4x7","7x4") if k=="lanczos3" else ("1x7","7x1","2x7","7x2")
        ids.extend(k+"-unchecked-tiny-"+size for size in sizes)
    ids.extend("plane-constructor-"+site for site in ("empty-both","empty-width","empty-height","short-data"))
    for k in ("lanczos2","lanczos3"):
        ids.extend(k+"-lanczos-commission-"+axis+"-"+phase for phase in ("quarter","half") for axis in ("x","y","corner"))
        ids.extend(k+"-lanczos-commission-"+site for site in ("wrong-translation","wrong-phase","restored"))
    ids.extend("clamped-catmull-rom-cubic-limiter-"+site for site in ("below","inside","above","affine-low","affine-interior","affine-upper"))
    ids.extend(("bilinear-gather-requested-map","bilinear-gather-opposite-direction-rejected"))
    need(len(ids)==344 and len(set(ids))==344,"fixed source-derived identity census")
    return ids

def test_transcript(output,variant,record,budget):
    raw,log_ref=d.read(output/"child-00.log",MIB,record["log"],check=budget.check)
    markers=[];offset=0
    kinds=("BEGIN","ROW","GATHER","SUMMARY")
    for line in raw.splitlines(keepends=True):
        body=line.rstrip(b"\r\n")
        if body.startswith(b"SAMPLER_BOUNDARY_"):
            found=[kind for kind in kinds if body.startswith(("SAMPLER_BOUNDARY_"+kind+" ").encode())]
            need(len(found)==1,"known sampler transcript marker")
            kind=found[0];prefix=("SAMPLER_BOUNDARY_"+kind+" ").encode()
            need(len(body)<=256*KIB,"bounded transcript marker")
            markers.append((kind,d.strict(body[len(prefix):]),offset,len(line)))
        offset+=len(line)
    need([m[0] for m in markers]==["BEGIN"]+["ROW"]*344+["GATHER","SUMMARY"],"complete ordered 347-marker transcript")
    begin=markers[0][1];rows=[m[1] for m in markers[1:345]];gather=markers[345][1];summary=markers[346][1]
    need(begin==dict(schema="sampler-boundary-begin-v1",expected_rows=344,width=128,height=96,
                     gauge="integer sample centres; scalar plane sample pitch"),"fixed test BEGIN")
    need([r.get("id") for r in rows]==expected_row_ids(),"exact fixed ordered row identities")
    ids=set();groups={k:0 for k in GROUPS};failed=[];boundary_failure=False
    for i,row in enumerate(rows):
        need(type(row) is dict and set(row)==ROW_KEYS and type(row["ordinal"]) is int and row["ordinal"]==i,"exact row ordinal/shape")
        need(type(row["id"]) is str and re.fullmatch("[a-z0-9-]{1,128}",row["id"])
             and row["id"] not in ids and row["group"] in GROUPS,"unique bounded row/group identity")
        ids.add(row["id"]);groups[row["group"]]+=1
        need(row["kernel"] in ("nearest","bilinear","catmull-rom","clamped-catmull-rom","lanczos2","lanczos3","none")
             and row["api"] in ("sample","sample_checked","metadata-or-consumer","sample_checked-pair",
                                 "sample_checked-destroyer","sample_checked-raw-and-limited","sample-endpoint-and-far-high"),"row kernel/API identity")
        for key,bits,nullable in (("x_f64_bits",64,False),("y_f64_bits",64,False),("actual_f32_bits",32,True),
                                  ("oracle_f32_bits",32,True),("oracle_f64_bits",64,True)):
            value=row[key];need((nullable and value is None) or (type(value) is int and 0<=value<(1<<bits)),"typed IEEE row payload")
        need(row["actual_kind"] in ("finite","nonfinite","refused","panic","true","false")
             and row["oracle_kind"] in ("literal","translated-stencil","true","refused","must-differ","literal-support-hull","in-hull-bit-identity","effective-fallback-endpoint")
             and d.finite(row["tolerance_code_units"]) and type(row["exercised"]) is bool and type(row["passed"]) is bool
             and (not row["passed"] or row["exercised"]),"typed row disposition")
        need((row["actual_f32_bits"] is not None)==(row["actual_kind"] in ("finite","nonfinite")),"actual-kind payload association")
        if not row["passed"]:
            failed.append({k:row[k] for k in ("ordinal","id","group","kernel","api","actual_kind","exercised")})
            boundary_failure|=row["group"]=="boundary" and row["api"]=="sample_checked" and row["exercised"] and row["actual_kind"]=="finite"
    need(groups==GROUPS and len(ids)==344,"fixed complete row group population")
    need(set(summary)=={"schema","rows","failed","passed","population_complete","groups"}
         and summary["schema"]=="sampler-boundary-summary-v1" and summary["population_complete"] is True
         and all(type(summary[k]) is int for k in ("rows","failed","passed"))
         and summary["rows"]==344 and summary["failed"]==len(failed) and summary["passed"]==344-len(failed)
         and summary["groups"]==groups and all(type(v) is int for v in summary["groups"].values()),"actual summary matches all retained rows")
    gather_keys={"schema","width","height","map","sampler","status","returned_count","expected_count","observed_count",
                 "mask_mismatches","value_mismatches","refusal_nan_mismatches","wrong_direction_mask_mismatches",
                 "wrong_direction_value_mismatches","max_abs_error","mask_nibble_lsb_first_hex",
                 "expected_mask_nibble_lsb_first_hex","row_major_f32_bits_hex"}
    need(set(gather)==gather_keys and gather["schema"]=="sampler-boundary-gather-v1"
         and type(gather["width"]) is int and type(gather["height"]) is int
         and gather["width"]==128 and gather["height"]==96 and gather["sampler"]=="bilinear"
         and gather["map"]=="source=(reference.x+0.25,reference.y+0.25)","fixed public gather operands")
    for key,extent in (("mask_nibble_lsb_first_hex",3072),("expected_mask_nibble_lsb_first_hex",3072),("row_major_f32_bits_hex",98304)):
        need(type(gather[key]) is str and len(gather[key])==extent and re.fullmatch("[0-9a-f]+",gather[key]),"complete gathered mask/value bit arrays")
    for key in ("expected_count","observed_count","mask_mismatches","value_mismatches","refusal_nan_mismatches",
                "wrong_direction_mask_mismatches","wrong_direction_value_mismatches"):
        need(type(gather[key]) is int and 0<=gather[key]<=12288,"typed gathered census")
    need(gather["returned_count"] is None or type(gather["returned_count"]) is int and 0<=gather["returned_count"]<=12288,"typed gather return count")
    need(type(gather["status"]) is str and len(gather["status"])<=64 and d.finite(gather["max_abs_error"]),"bounded gather status/error")
    terminal=raw[markers[-1][2]+markers[-1][3]:]
    if variant=="baseline":
        need(record["exit_code"]==101 and failed and boundary_failure,"source-predicted exercised public boundary failure")
        message=f"fixed sampler boundary contract: {len(failed)} failed of 344 rows; full transcript retained".encode()
        need(message in terminal and b"test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out;" in terminal,
             "actual final aggregate assertion and failed single-test harness")
    else:
        need(record["exit_code"]==0 and not failed
             and b"test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;" in terminal,"actual repaired single-test pass")
    value=dict(schema="sampler-boundary-test-observation-v1",variant=variant,raw_log=log_ref,actual_exit_code=record["exit_code"],
               rows=344,failed=len(failed),passed=344-len(failed),population_complete=True,groups=groups,
               test_passed=not failed,exercised_public_boundary_failure=boundary_failure,failed_rows=failed,
               begin=begin,summary=summary,
               gather_record=dict(byte_offset=markers[345][2],bytes=markers[345][3],
                                  sha256=d.sha(raw[markers[345][2]:markers[345][2]+markers[345][3]])),
               scope="Transport/population and authored assertion disposition only. Full bit arrays/rows remain in raw log; no sampler oracle is recomputed here.")
    ref=d.write_new(output/"test-observation.json",d.encoded(value),128*KIB)
    return ref,{k:value[k] for k in ("actual_exit_code","rows","failed","passed","population_complete","test_passed","exercised_public_boundary_failure")}


REGRESSION_TESTS=(
 "align::tests::catmull_rom_reproduces_the_samples_at_integer_positions",
 "align::tests::clamped_catmull_rom_stays_inside_the_exact_support16_hull",
 "align::tests::clamped_catmull_rom_is_bit_identical_until_catmull_leaves_the_hull",
 "align::tests::clamped_catmull_rom_preserves_integer_samples_and_constant_planes_exactly",
 "align::tests::clamped_catmull_rom_has_catmull_support_and_checked_domain",
 "align::tests::a_widened_clamp_makes_the_hull_guard_fail",
 "align::tests::a_gather_under_the_identity_is_the_identity",
 "align::tests::lanczos3_is_interpolating_and_preserves_dc",
 "align::tests::lanczos3_support_matches_its_reach",
 "align::tests::lanczos2_is_interpolating_and_costs_no_extra_border",
 "warpmap::gather_tests::gather_marks_uncovered_pixels_instead_of_clamping",
 "warpmap::gather_tests::gather_refuses_a_geometry_mismatch",
 "warpmap::gather_tests::gather_refuses_a_refused_frame")

def regression_command(variant):
    need(variant=="repaired","repaired-only unit regression commission")
    return [str(unit_executable_path(variant)),"--exact","--nocapture","--test-threads=1",*REGRESSION_TESTS]

def regression_transcript(output,variant,record,budget):
    need(variant=="repaired" and record["exit_code"]==0,"repaired regression actual exit")
    raw,log_ref=d.read(output/"child-00.log",MIB,record["log"],check=budget.check)
    text=raw.decode("utf-8")
    need(re.findall(r"(?m)^running ([0-9]+) tests?\r?$",text)==["13"],"actual thirteen-test harness invocation")
    rows=re.findall(r"(?m)^test ([a-zA-Z0-9_:]+) \.\.\. (ok|FAILED|ignored)\r?$",text)
    need(len(rows)==13 and len({r[0] for r in rows})==13 and {r[0] for r in rows}==set(REGRESSION_TESTS)
         and all(r[1]=="ok" for r in rows),"all thirteen exact regression names passed, no executed extras")
    summaries=re.findall(r"(?m)^test result: ok\. 13 passed; 0 failed; 0 ignored; 0 measured; ([0-9]+) filtered out;[^\r\n]*\r?$",text)
    need(len(summaries)==1,"exact complete regression harness summary")
    value=dict(schema="sampler-boundary-regression-observation-v1",variant=variant,raw_log=log_ref,actual_exit_code=0,
               tests=13,passed=13,failed=0,ignored=0,filtered_unvisited=int(summaries[0]),population_complete=True,
               test_passed=True,observed_order=[r[0] for r in rows],requested_order=list(REGRESSION_TESTS),
               scope="One exact-name OR-filter libtest invocation; other core tests are filtered/unvisited. This is regression evidence, not image quality.")
    ref=d.write_new(output/"regression-observation.json",d.encoded(value),32*KIB)
    return ref,{k:value[k] for k in ("actual_exit_code","tests","passed","failed","ignored","filtered_unvisited","population_complete","test_passed")}
if __name__=="__main__":raise SystemExit(main())
