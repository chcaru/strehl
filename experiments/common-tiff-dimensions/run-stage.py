"""Fixed common-TIFF dimension stages; SOURCE ONLY until a separately pinned root release.
Reuses held M194h accounting/read/scan/Job primitives, never its science or main.
"""
import time
START=time.monotonic()
from pathlib import Path
import argparse,hashlib,json,math,os,re,shutil,stat,sys,types

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
MIB=1<<20;KIB=1024;GIB=1<<30
BASE=ROOT/"experiments/m194h-pedestal-causality/build-and-run.py"
BASE_SHA="b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410"
BUILD_PROCESS=HERE/"bounded-build-process.py"
BUILD_SHA="97cf2d4a587c95a111a738330a66a24d9b003debb69ee0346cecd3c9955151d9"
TARGET=ROOT/"target/common-tiff-dimensions-1"
EXE=HERE/"build-1/strehl-common-input.exe"
CONTROLS=HERE/"independent-controls.py"
FIXTURES=HERE/"prepare-1/fixtures"
INDEX=FIXTURES/"index.json"
RUN_BUNDLE=HERE/"render-bundle-1.json"
OUTPUTS={s:HERE/(s+"-1") for s in ("build","prepare","render","verify")}
STAGES={
    "build":dict(cpu_seconds=600,wall_seconds=300,committed_bytes=3*GIB,file_bytes=128*MIB,scratch_bytes=4*GIB),
    "prepare":dict(cpu_seconds=30,wall_seconds=60,committed_bytes=GIB,file_bytes=34*MIB,scratch_bytes=0),
    "render":dict(cpu_seconds=180,wall_seconds=240,committed_bytes=GIB,file_bytes=128*MIB,scratch_bytes=0),
    "verify":dict(cpu_seconds=60,wall_seconds=120,committed_bytes=GIB,file_bytes=19*MIB,scratch_bytes=0)}
SCHEMA="common-tiff-dimensions-stage-release-v1"
RESULT="common-tiff-dimensions-owned-stage-v1"
EXTERNAL="common-tiff-dimensions-stage-external-v1"
TAIL="common-tiff-dimensions-parent-tail-v1"
REQUIRED=("run-stage.py","bounded-build-process.py","run-stage-contract.md",
          "charter.md","implementation-contract.md","independent-controls.py","independent-spec.md")
CASE_IDS=("mean-two-min","mean-five-odd","mean-eight-max","odd-address","odd-offset",
          "odd-noisy-off","odd-noisy-on","odd-noisy-placebo","legacy-constant",
          "count-zero","count-one","count-nine","width-low","width-high","height-low",
          "height-high","width-u32-overflow","legacy-count-two","legacy-odd",
          "duplicate-input","wrong-profile","wrong-proxy-variance","last-geometry","last-file-hash")
OBSERVERS=("off","off","off","on","on","off","on","placebo","off")+("off",)*15
FOLDS=(2,5,8,5,5,5,5,5,3)+(0,)*13+(4,4)
KINDS=("mean-two","mean-five","mean-eight","odd-address","odd-offset","odd-noisy","odd-noisy","odd-noisy","legacy",
       "mean-five","mean-five","mean-eight","mean-five","mean-five","mean-five","mean-five","mean-five",
       "legacy","odd-address","mean-five","mean-five","odd-noisy","mean-five","mean-five")
VERSIONS=tuple(1 if i in (8,17,18) else 2 for i in range(24))
SET_COUNTS={"mean-two":2,"mean-five":5,"mean-eight":8,"odd-address":5,"odd-offset":5,"odd-noisy":5,"count-nine-extra":1}
SET_GRIDS={"mean-two":(64,64),"mean-five":(129,97),"mean-eight":(512,512),"odd-address":(129,97),
           "odd-offset":(129,97),"odd-noisy":(129,97),"legacy":(128,96)}
LEGACY={
    "index":{"path":"experiments/common-tiff-stack/prepare-1/fixtures/index.json","bytes":19328,"sha256":"5c16e7cd7cd6a29377579f643b1b31515ffb99a1f5ad0a5ef32c362de6adeab8"},
    "report":{"path":"experiments/common-tiff-stack/render-1/case-00/report.json","bytes":11635,"sha256":"abc69a25319da0ddb6ce2e9a036d8b37c0e1bcd4c67a9c186e6a647f088b5f9a"},
    "output":{"path":"experiments/common-tiff-stack/render-1/case-00/output.tiff","bytes":74807,"sha256":"1e6c9f9bd3146c0c8f7314c422e26c842eb45ba25d76d12adae8f8d690842f7e"}}
STAGE_RESULT_CAP=256*KIB
TAIL_CPU=2;TAIL_WALL=3
d=None

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
    d.TERMINAL_CAP=STAGE_RESULT_CAP
    return d

def file_ref(path,cap,expected=None,check=lambda:None):
    return d.read(path,cap,expected,keep=False,check=check)[1]

def source_check(sources,budget):
    for key in sources:d.source_bytes(ROOT/key,sources,budget.check)
    return d.source_closure(sources,budget.check)

def build_command():
    return ["cargo","build","-p","strehl-cli","--bin","strehl-common-input","--jobs","2","--target-dir",str(TARGET),
            "--message-format=json-render-diagnostics","--locked","--offline"]

def python_command(sources,mode,index_ref=None,bundle_ref=None):
    command=[str(Path(sys.executable)),"-I","-S","-B",str(CONTROLS),mode]
    if mode=="prepare":command+=["--output",str(FIXTURES)]
    else:command+=["--fixtures",str(INDEX),"--fixtures-sha256",index_ref["sha256"],
                  "--run-bundle",str(RUN_BUNDLE),"--run-bundle-sha256",bundle_ref["sha256"],
                  "--output",str(OUTPUTS["verify"]/"check")]
    return command+["--source-sha256",sources[d.source_ref(CONTROLS)]["sha256"]]

def authority(args):
    need(os.name=="nt" and Path.cwd().resolve()==ROOT,"Windows repository cwd")
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"isolated stdlib controller")
    load_base()
    path=d.owned(args.release);raw,ref=d.read(path,MIB)
    need(ref["sha256"]==args.release_sha256,"actual release SHA")
    release=d.strict(raw)
    keys={"schema","stage","source_bindings","inputs","command","children","executable","fixtures","run_bundle","prerequisites"}
    need(type(release) is dict and set(release)==keys and release["schema"]==SCHEMA,"closed ten-key release")
    stage=release["stage"];need(stage in OUTPUTS,"fixed stage")
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
         and all(d.source_ref(p) in sources for p in (BASE,d.PROCESS,d.HARNESS)),"mandatory primitive/control source closure")
    need(sources[d.source_ref(BASE)]["sha256"]==BASE_SHA and sources[d.source_ref(BUILD_PROCESS)]["sha256"]==BUILD_SHA,"fixed reused source pins")
    d.source_bytes(SELF,sources)
    output=OUTPUTS[stage];need(not output.exists(),"fresh once-only stage output")
    output.mkdir()
    budget=d.Budget(stage,output);budget.source_bindings=sources
    original_limits=budget.limits
    def limits(index):
        v=original_limits(index)
        if stage in ("prepare","render","verify"):
            cpu,wall={"prepare":(20,40),"render":(20,20),"verify":(45,90)}[stage]
            v["wall_seconds"]=min(wall,v["wall_seconds"]);v["cpu_seconds"]=min(cpu,v["cpu_seconds"])
        v["log_bytes"]=16*MIB if stage=="build" else MIB if stage=="verify" else 256*KIB
        return v
    budget.limits=limits
    result=dict(schema=RESULT,status="INITIAL_INCOMPLETE",stage=stage,release=ref,invocation=sys.orig_argv,
                children=[],artifacts={},prerequisites={},work=None,error=None,finalization_errors=[],
                limits=STAGES[stage],tail_allowance=dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),
                scope="Parent CPU plus each owned child Job once; expected refusal is a clean process disposition, not a scientific pass.")
    d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
    return release,ref,output,budget,result

def bundle_read(bundle,stage,budget,sources):
    caps={"result":STAGE_RESULT_CAP,"tail":8*KIB,"outer":64*KIB,"stdout":8*KIB,"stderr":32*KIB,"exit":KIB}
    need(type(bundle) is dict and set(bundle)==set(caps),"six actual prior roles")
    raw={k:d.read(ROOT/bundle[k]["path"],cap,bundle[k],check=budget.check)[0] for k,cap in caps.items()}
    v={k:d.strict(raw[k]) for k in ("result","tail","outer","stdout")}
    result,tail,outer,advert=(v[k] for k in ("result","tail","outer","stdout"))
    need(d.lexical(ROOT/bundle["result"]["path"])==OUTPUTS[stage]/"result.json"
         and d.lexical(ROOT/bundle["tail"]["path"])==OUTPUTS[stage]/"parent-tail.json","fixed previous paths")
    need(result["schema"]==RESULT and result["stage"]==stage and result["status"]=="COMPLETE_STAGE_UNVERIFIED"
         and result["error"] is None and not result["finalization_errors"],"completed prior stage")
    outer_keys={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds",
                "stdout","stderr","exit","stdout_bytes","stderr_bytes","scope"}
    need(set(outer)==outer_keys and outer["schema"]==EXTERNAL and type(outer["exit_code"]) is int
         and outer["exit_code"]==0 and outer["timeout_terminated"] is False and raw["exit"].strip()==b"0","actual prior exit")
    need(outer["command"]==result["invocation"] and d.same_ref(outer["source"],dict(path=d.source_ref(SELF),**sources[d.source_ref(SELF)])),"prior invocation/source")
    for k in ("stdout","stderr","exit"):need(d.same_ref(outer[k],bundle[k]),"actual outer byte association")
    need(type(outer["stdout_bytes"]) is int and outer["stdout_bytes"]==len(raw["stdout"])
         and type(outer["stderr_bytes"]) is int and outer["stderr_bytes"]==len(raw["stderr"]),"actual stream extents")
    need(set(advert)=={"status","result","tail"} and advert["status"]==result["status"]
         and d.same_ref(advert["result"],bundle["result"]) and d.same_ref(advert["tail"],bundle["tail"])
         and raw["stdout"]==d.encoded(advert),"exact actual prior advertisement")
    need(tail["schema"]==TAIL and d.same_ref(tail["result"],bundle["result"])
         and tail["cpu_accounting_complete"] is True and tail["live_child_cpu_seconds"]==0
         and tail["final_external_allowance"]==dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),"prior terminal accounting")
    need(all(d.finite(tail[k]) for k in ("actual_parent_cpu_sample","whole_wall_sample","completed_child_cpu_seconds")),"prior finite timing")
    need(d.finite(outer["elapsed_wall_seconds"]) and outer["elapsed_wall_seconds"]<=STAGES[stage]["wall_seconds"]
         and outer["elapsed_wall_seconds"]<=tail["whole_wall_sample"]+TAIL_WALL,"actual whole prior wall")
    need(tail["actual_parent_cpu_sample"]+tail["completed_child_cpu_seconds"]+TAIL_CPU<=STAGES[stage]["cpu_seconds"]
         and result["work"]["cpu_accounting_complete"] is True,"prior CPU plus finite tail")
    oldraw,_=d.read(ROOT/result["release"]["path"],MIB,result["release"],check=budget.check);old=d.strict(oldraw)
    need(old["schema"]==SCHEMA and old["stage"]==stage and old["source_bindings"]==sources,"same frozen maps across stages")
    need([result["release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in old["command"]]==result["invocation"],"prior release argv")
    for k,cap in caps.items():file_ref(ROOT/bundle[k]["path"],cap,bundle[k],budget.check)
    return result

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

def fixture_read(ref,budget):
    need(type(ref) is dict and d.lexical(ROOT/ref["path"])==INDEX,"fixed fixture index")
    raw,_=d.read(INDEX,256*KIB,ref,check=budget.check);value=d.strict(raw)
    need(set(value)=={"schema","source","spec","profile","recipe","recipe_sha256","legacy","generated_files","cases"}
         and value["schema"]=="common-tiff-dimensions-independent-fixtures-v1","fixed fixture schema")
    for role,path in (("source",CONTROLS),("spec",HERE/"independent-spec.md")):
        need(d.same_ref(value[role],dict(path=d.source_ref(path),**budget.source_bindings[d.source_ref(path)])),"fixture exact source/spec")
    profile=ROOT/"experiments/M165-common-input/linear-prophoto-d50-v1.icc"
    need(d.lexical(ROOT/value["profile"]["path"])==profile and type(value["profile"]["bytes"]) is int
         and value["profile"]["bytes"]==548 and value["profile"]["sha256"]=="16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef","fixed existing profile authority")
    file_ref(profile,548,value["profile"],budget.check)
    legacy=value["legacy"]
    need(type(legacy) is dict and set(legacy)=={"index","report","manifest","output"},"closed legacy evidence")
    for role,expected in LEGACY.items():
        need(d.same_ref(legacy[role],expected),"literal held legacy identity")
        file_ref(ROOT/expected["path"],256*KIB,expected,budget.check)
    oldraw,_=d.read(ROOT/legacy["report"]["path"],64*KIB,legacy["report"],check=budget.check)
    old=d.strict(oldraw)
    need(old["schema"]=="common-tiff-stack-result-v1" and old["status"]=="COMPLETE"
         and old["subject_complete"] is True and d.same_ref(old["manifest"],legacy["manifest"])
         and d.same_ref(old["output"],legacy["output"]),"held legacy manifest/output association")
    file_ref(ROOT/legacy["manifest"]["path"],64*KIB,legacy["manifest"],budget.check)
    rows=value["cases"];generated=value["generated_files"]
    need(type(rows) is list and len(rows)==24 and type(generated) is list and len(generated)==58,"fixed fixture population")
    actual={};total=0
    for f in generated:
        p=d.owned(ROOT/f["path"]);need(p.parent==FIXTURES and p!=INDEX and p not in actual,"owned actual fixture files")
        cap=1638400 if p.suffix==".tiff" else 64*KIB
        need(type(f["bytes"]) is int and 0<f["bytes"]<=cap,"fixture extent")
        file_ref(p,cap,f,budget.check);actual[p]=f;total+=f["bytes"]
    expected_names={"recipe.json","last-geometry.tiff","last-file-hash.tiff"}
    expected_names.update(f"{kind}-{frame}.tiff" for kind,count in SET_COUNTS.items() for frame in range(count))
    expected_names.update(f"case-{i:02}.json" for i in range(24))
    need(set(actual)=={FIXTURES/name for name in expected_names},"exact 58 generated fixture paths")
    need(total+ref["bytes"]<=32*MIB,"actual fixture family extent")
    recipe=FIXTURES/"recipe.json"
    need(recipe in actual and d.same_ref(value["recipe"],actual[recipe]),"actual generated recipe")
    recipe_raw,_=d.read(recipe,64*KIB,value["recipe"],check=budget.check)
    need(d.sha(recipe_raw.rstrip(b"\n"))==value["recipe_sha256"],"recipe canonical byte association")
    expected_keys={"ordinal","id","fixture_kind","version","observer","expected_exit_code","expected_folded_frames","manifest","command","output_path","report_path"}
    for i,row in enumerate(rows):
        case=OUTPUTS["render"]/f"case-{i:02}";manifest=FIXTURES/f"case-{i:02}.json"
        need(set(row)==expected_keys and type(row["ordinal"]) is int and row["ordinal"]==i
             and row["id"]==CASE_IDS[i] and row["fixture_kind"]==KINDS[i] and row["observer"]==OBSERVERS[i]
             and type(row["version"]) is int and row["version"]==VERSIONS[i]
             and type(row["expected_exit_code"]) is int and row["expected_exit_code"]==(0 if i<9 else 1)
             and type(row["expected_folded_frames"]) is int and row["expected_folded_frames"]==FOLDS[i],"fixed case identities")
        need(d.lexical(ROOT/row["manifest"]["path"])==manifest and manifest in actual
             and d.same_ref(row["manifest"],actual[manifest]),"bound actual case manifest")
        need(d.lexical(ROOT/row["output_path"])==case/"output.tiff" and d.lexical(ROOT/row["report_path"])==case/"report.json","fixed case output paths")
        expected=["ACTUAL_BINARY_PATH","--stack-manifest",str(manifest),"--manifest-sha256",row["manifest"]["sha256"],
                  "--report",str(case/"report.json"),"--observer",OBSERVERS[i]]
        need(row["command"]==expected,"exact case command template")
    # Authenticate generated actual bytes, not the intentionally false hash in
    # last-file-hash's product manifest. Its refusal is the product's task.
    return value


def prerequisites(release,budget):
    stage=release["stage"];expected={"build":(),"prepare":("build",),"render":("build","prepare"),"verify":("build","prepare","render")}[stage]
    need(type(release["prerequisites"]) is dict and set(release["prerequisites"])==set(expected),"exact prior stages")
    prior={k:bundle_read(release["prerequisites"][k],k,budget,release["source_bindings"]) for k in expected}
    if stage=="build":need(release["executable"] is None,"no executable before build")
    else:
        need(d.same_ref(release["executable"],prior["build"]["artifacts"]["executable"])
             and d.lexical(ROOT/release["executable"]["path"])==EXE,"actual fresh compiled executable")
        file_ref(EXE,64*MIB,release["executable"],budget.check)
    fixtures=None
    if stage in ("render","verify"):
        need(d.same_ref(release["fixtures"],prior["prepare"]["artifacts"]["fixture_index"]),"exact prepared fixtures")
        fixtures=fixture_read(release["fixtures"],budget)
    else:need(release["fixtures"] is None,"no premature fixture identity")
    if stage=="verify":
        raw,_=d.read(RUN_BUNDLE,64*KIB,release["run_bundle"],check=budget.check)
        need(d.strict(raw)==release["prerequisites"]["render"]
             and d.lexical(ROOT/release["run_bundle"]["path"])==RUN_BUNDLE,"exact external render bundle for independent checker")
    else:need(release["run_bundle"] is None,"no premature saved-render bundle")
    return prior,fixtures

def exact_children(release,fixtures):
    stage=release["stage"]
    if stage=="build":commands=[build_command()]
    elif stage=="prepare":commands=[python_command(release["source_bindings"],"prepare")]
    elif stage=="verify":commands=[python_command(release["source_bindings"],"verify",release["fixtures"],release["run_bundle"])]
    else:commands=[[str(EXE) if x=="ACTUAL_BINARY_PATH" else x for x in row["command"]] for row in fixtures["cases"]]
    exits=[0 if i<9 else 1 for i in range(24)] if stage=="render" else [0]
    expected=[dict(command=c,expected_exit_code=e) for c,e in zip(commands,exits)]
    need(type(release["children"]) is list and len(release["children"])==len(expected)
         and all(type(c) is dict and set(c)=={"command","expected_exit_code"}
                 and type(c["expected_exit_code"]) is int and type(c["command"]) is list
                 and all(type(x) is str for x in c["command"]) and len(d.encoded(c["command"]))<=4*KIB
                 for c in release["children"]),"typed bounded child schedule")
    need(release["children"]==expected,"fixed command and expected-exit schedule")
    return expected

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
    result["children"].append(record_ref);d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
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

def compiled_binary(output,budget):
    raw,_=d.read(output/"child-00.log",16*MIB,check=budget.check)
    need(b"Compiling strehl-cli" in raw,"actual Compiling line")
    messages=[];finished=[]
    for line in raw.splitlines():
        if not line.startswith(b"{"):continue
        v=d.strict(line)
        if v.get("reason")=="build-finished":finished.append(v)
        if v.get("reason")=="compiler-artifact" and v.get("executable") and v.get("target",{}).get("name")=="strehl-common-input":
            messages.append(v)
    need(len(finished)==1 and set(finished[0])=={"reason","success"} and finished[0]["success"] is True,"actual successful Cargo build-finished record")
    need(len(messages)==1,"unique actual bin compiler artifact");v=messages[0]
    source=ROOT/"crates/strehl-cli/src/bin/strehl-common-input.rs"
    need(v["fresh"] is False and v["profile"]["test"] is False and v["target"]["kind"]==["bin"]
         and Path(v["target"]["src_path"]).resolve()==source
         and Path(v["manifest_path"]).resolve()==ROOT/"crates/strehl-cli/Cargo.toml"
         and "m194h-pedestal-causality" not in v["features"],"fresh default common-input binary")
    need(len(d.encoded(v))<=16*KIB,"bounded compiler message")
    origin=d.owned(v["executable"]);need(origin.is_relative_to(TARGET),"new target artifact")
    data,original=d.read(origin,64*MIB,check=budget.check)
    copied=d.write_new(EXE,data,64*MIB);need(d.ref_binding(original)==d.ref_binding(copied),"copied actual executable bytes")
    return dict(executable=copied,compiled_original=original,compiler_message=v,build_finished=finished[0])

def capture_case(row,record,budget):
    directory=OUTPUTS["render"]/f"case-{row['ordinal']:02}"
    v1=row["version"]==1
    width,height=SET_GRIDS[row["fixture_kind"]]
    tiff_cap=128*KIB if v1 else 6*width*height+64*KIB
    report_cap=64*KIB if v1 else 192*KIB
    caps={"output.tiff":tiff_cap,"output.tiff-stage":tiff_cap,"report.json":report_cap,
          "report.incomplete.json":4*KIB,"report.stage.json":report_cap,
          **{f"report.frame-{i}.json":16*KIB for i in range(3 if v1 else 8)}}
    refs={}
    for path in directory.iterdir():
        need(path.is_file() and path.name in caps,"closed product case artifacts")
        refs[path.name]=file_ref(path,caps[path.name],check=budget.check)
    need("report.json" in refs,"retained actual final product report")
    report_raw,_=d.read(directory/"report.json",report_cap,refs["report.json"],check=budget.check)
    log_raw,_=d.read(OUTPUTS["render"]/f"child-{row['ordinal']:02}.log",256*KIB,record["log"],check=budget.check)
    need(log_raw==report_raw,"actual product raw stdout/report identity")
    # Scientific semantics/pixels belong to the independent saved checker.
    if row["expected_exit_code"]==0:need("output.tiff" in refs,"successful actual TIFF exists")
    else:need("output.tiff" not in refs,"registered refusal cannot leave an admitted TIFF")
    return dict(ordinal=row["ordinal"],id=row["id"],expected_exit_code=row["expected_exit_code"],
                expected_folded_frames=row["expected_folded_frames"],artifacts=refs)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--release",required=True);parser.add_argument("--release-sha256",required=True)
    args=parser.parse_args();release=release_ref=output=budget=result=None
    try:
        release,release_ref,output,budget,result=authority(args)
        sources=release["source_bindings"];result["compiled_source_closure"]=source_check(sources,budget)
        input_check(release,budget);prior,fixtures=prerequisites(release,budget)
        result["prerequisites"]=release["prerequisites"];schedule=exact_children(release,fixtures)
        env=d.clean_env()
        need(not any(k.upper().startswith(("STREHL_","M194H_")) for k in env),"no old native/experiment overrides")
        result["environment"]={k:env.get(k) for k in ("RAYON_NUM_THREADS","CARGO_NET_OFFLINE","RUSTUP_TOOLCHAIN","RUSTUP_HOME","CARGO_HOME")}
        need(len(d.encoded(result["environment"]))<=8*KIB,"bounded observed environment")
        result["environment_scope"]="two Rayon threads, offline compiler; inherited toolchain search observed, not hermetic"
        if release["stage"]=="build":need(not TARGET.exists(),"fresh target scratch")
        process,api=d.load_process(sources,release["stage"]=="build")
        result["operations"]=[];d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
        for i,child in enumerate(schedule):
            if release["stage"]=="render":
                directory=OUTPUTS["render"]/f"case-{i:02}";need(not directory.exists(),"fresh product case")
                directory.mkdir();file_ref(EXE,64*MIB,release["executable"],budget.check)
                fixture_read(release["fixtures"],budget)
            result["operations"].append(dict(ordinal=i,expected_exit_code=child["expected_exit_code"],status="ATTEMPTED"))
            d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
            record=child_call(process,api,child["command"],env,child["expected_exit_code"],i,output,budget,result)
            result["operations"][-1]["status"]="EXPECTED_PROCESS_DISPOSITION"
            if release["stage"]=="build":result["artifacts"].update(compiled_binary(output,budget))
            elif release["stage"]=="prepare":
                index_ref=file_ref(INDEX,MIB,check=budget.check);fixture_read(index_ref,budget)
                result["artifacts"]["fixture_index"]=index_ref
                log,_=d.read(output/"child-00.log",256*KIB,record["log"],check=budget.check);advert=d.strict(log)
                need(advert["schema"]=="common-tiff-dimensions-independent-preparation-v1" and advert["status"]=="PREPARED_UNRUN_FIXTURES"
                     and advert["cases"]==24 and advert["generated_files"]==59 and d.same_ref(advert["index"],index_ref),"actual prepared-index advertisement")
            elif release["stage"]=="render":
                result["artifacts"].setdefault("cases",[]).append(capture_case(fixtures["cases"][i],record,budget))
                file_ref(EXE,64*MIB,release["executable"],budget.check);fixture_read(release["fixtures"],budget)
            else:
                final=output/"check/result.json";final_raw,final_ref=d.read(final,MIB,check=budget.check)
                log,_=d.read(output/"child-00.log",MIB,record["log"],check=budget.check)
                need(log==final_raw,"independent checker raw final association")
                final_value=d.strict(final_raw)
                need(final_value["schema"]=="common-tiff-dimensions-independent-verification-v1"
                     and final_value["status"]=="PASS_COMMON_RGB_DIMENSIONS_SOFTWARE_INTEGRATION"
                     and final_value["software_integration_complete"] is True,"actual independent success disposition")
                result["artifacts"]["independent_result"]=final_ref
            d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
        if release["stage"]=="render":need(len(result["artifacts"]["cases"])==24,"complete fixed 24-case population")
        need(source_check(sources,budget)==result["compiled_source_closure"],"unchanged final compiled closure")
        input_check(release,budget)
        if release["executable"] is not None:file_ref(EXE,64*MIB,release["executable"],budget.check)
        if release["fixtures"] is not None:fixture_read(release["fixtures"],budget)
        d.read(args.release,MIB,release_ref,check=budget.check)
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
                terminal=d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
                tail=dict(schema=TAIL,result=terminal,actual_parent_cpu_sample=time.process_time(),
                          whole_wall_sample=time.monotonic()-START,completed_child_cpu_seconds=budget.completed_cpu,
                          live_child_cpu_seconds=budget.live_cpu,cpu_accounting_complete=budget.complete and budget.accounting_error is None,
                          final_external_allowance=dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),
                          scope="Sample after canonical publication; actual external exit/whole wall and charged tail are required.")
                need(tail["actual_parent_cpu_sample"]+budget.completed_cpu+budget.live_cpu+TAIL_CPU<=budget.caps["cpu_seconds"]
                     and tail["whole_wall_sample"]+TAIL_WALL<=budget.caps["wall_seconds"],"final sampled envelope plus finite tail")
                tail_ref=d.write_new(output/"parent-tail.json",d.encoded(tail),8*KIB)
                advertised=dict(status=result["status"],result=terminal,tail=tail_ref)
            except BaseException:
                result["status"]="REFUSED";result["finalization_errors"].append(d.error_value())
                try:terminal=d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
                except BaseException:terminal=None
                advertised=dict(status="REFUSED",result=terminal,error="terminal/tail refusal")
        else:advertised=result
        raw=d.encoded(advertised) if d is not None else (json.dumps(advertised,sort_keys=True,separators=(",",":"))+"\n").encode()
        need(len(raw)<=8*KIB,"bounded raw stdout");need(sys.stdout.buffer.write(raw)==len(raw),"full raw stdout");sys.stdout.buffer.flush()
    return 0 if result["status"]=="COMPLETE_STAGE_UNVERIFIED" else 1

if __name__=="__main__":raise SystemExit(main())
