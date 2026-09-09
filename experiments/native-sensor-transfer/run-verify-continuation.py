"""Fixed native Crop transfer stages. Source preparation is not execution authority.
Reuses held M194h process/accounting primitives and the commissioned scratch shim.
"""
import time
START=time.monotonic()
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,stat,sys,types

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
OLD_SELF=HERE/"run-stage.py"
NATIVE_SELF=HERE/"run-native-continuation.py"
OLD_RUNNER_SHA='6b3fc325a1d10a25885a2f2c8d42114732733a9282d02ad7edb7bb9f26e02d62'
PUBLICATION=HERE/"native-publication-scan.py"
PUBLICATION_SHA='1b12816c6b727a8fc28fc62b254c290e900b5d3090b863199136f62a11414b24'
ACTIVE_NATIVE=[None]
HISTORY={'freeze': {'path': 'experiments/native-sensor-transfer/work/execution-source-freeze-1.json', 'bytes': 21318, 'sha256': 'ac5063c60da834a39e8f5e9ac627b481d8451e0af4f295ebeebadbb2aa0e6bbb'}, 'archive': {'path': 'experiments/native-sensor-transfer/work/native-partial-archive-1.json', 'bytes': 427, 'sha256': 'd4fb465812acfbde224c96e6e8e3e3ed038bd102e059f4ecf3777fc1239e1d9b'}, 'failed_result': {'path': 'experiments/native-sensor-transfer/native-1/result.json', 'bytes': 262144, 'sha256': '5f53ec740b061226f55c2f328e3b8a727a489b7db5e6ad1cbfc0cea232dfb3da'}, 'failed_tail': {'path': 'experiments/native-sensor-transfer/native-1/parent-tail.json', 'bytes': 620, 'sha256': '569cefc2e6fdfd72a77905c469da876ed501e085ed01472a49d8f886521f02aa'}, 'failed_outer': {'path': 'experiments/native-sensor-transfer/work/native-external-1-outer.json', 'bytes': 1630, 'sha256': 'b98959b4ba0b22f16851f3e6616a067a954f7b80bc34d5eeede4d79fa11f18a3'}, 'failed_stdout': {'path': 'experiments/native-sensor-transfer/work/native-external-1-stdout.bin', 'bytes': 465, 'sha256': 'cdeb7e9c3d4f71f56a3017db1f8a89aa3ffe34e92f808baa63c3715b67d4451f'}, 'failed_stderr': {'path': 'experiments/native-sensor-transfer/work/native-external-1-stderr.bin', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'failed_exit': {'path': 'experiments/native-sensor-transfer/work/native-external-1-exit.txt', 'bytes': 2, 'sha256': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865'}, 'child0': {'path': 'experiments/native-sensor-transfer/native-1/child-00.json', 'bytes': 2161, 'sha256': 'c2036081780d6d775ce02cd724b0c4e44b2ef7705845b17cb1226a9ee71f3b2e'}, 'child1': {'path': 'experiments/native-sensor-transfer/native-1/child-01.json', 'bytes': 1992, 'sha256': '2f88424ae436f51c15c44175e654a51042c81efb56f48858f2f425d598f92a98'}, 'traversal0': {'path': 'experiments/native-sensor-transfer/native-run-0/result.json', 'bytes': 5215, 'sha256': '60290553394183040dfc03c03cc59feb9a53b17850899499650eaa7adfef8d8f'}}

MIB=1<<20;KIB=1024;GIB=1<<30
BASE=ROOT/"experiments/m194h-pedestal-causality/build-and-run.py"
BASE_SHA="b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410"
BUILD_PROCESS=HERE/"bounded-build-process.py"
BUILD_SHA="0a17f2779b6b76d9f495bc88743fc0d13b291f16e49e59535442b01b0018027a"
SCRATCH=HERE/"scratch-scan.py"
SCRATCH_SHA="b53c57e56855578c803c29594da34e0a69423c9113608932d823184c4b79c2a4"
STAGES={
    "build-on":dict(cpu_seconds=600,wall_seconds=300,committed_bytes=3*GIB,file_bytes=128*MIB,scratch_bytes=4*GIB),
    "build-off":dict(cpu_seconds=600,wall_seconds=300,committed_bytes=3*GIB,file_bytes=128*MIB,scratch_bytes=4*GIB),
    "controls":dict(cpu_seconds=120,wall_seconds=180,committed_bytes=GIB,file_bytes=64*MIB,scratch_bytes=0),
    "native":dict(cpu_seconds=1800,wall_seconds=1200,committed_bytes=2*GIB,file_bytes=256*MIB,scratch_bytes=0),
    "verify":dict(cpu_seconds=1200,wall_seconds=900,committed_bytes=GIB,file_bytes=96*MIB,scratch_bytes=0)}
OUTPUTS={s:HERE/(s+("-4" if s=="build-on" else "-3" if s=="native" else "-2" if s=="verify" else "-1")) for s in STAGES}
TARGETS={s:ROOT/("target/native-sensor-transfer-"+s.removeprefix("build-")+("-4" if s=="build-on" else "-1")) for s in ("build-on","build-off")}
EXES={s:OUTPUTS["build-"+s.removeprefix("feature_")]/"cli-tests.exe" for s in ("feature_on","feature_off")}
READER=HERE/"verify-recovery.py"
INPUT_BINDINGS={"path":"experiments/native-sensor-transfer/input-bindings-1.json","bytes":7119,
                "sha256":"ab4017907d5ff243ca36883a9e5ff7335717c4f7da4678b01eacab98b3d98b4a"}
READER_CAPS={"controls":dict(cpu_seconds=100,wall_seconds=150,memory_bytes=GIB,write_bytes=62*MIB),
             "verify":dict(cpu_seconds=1000,wall_seconds=850,memory_bytes=GIB,write_bytes=64*MIB)}
READER_ENV={"OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1"}
BUILD_ENV_PREFIXES=("CARGO_BUILD_","CARGO_TARGET_","CARGO_PROFILE_","CARGO_UNSTABLE_")
BUILD_ENV_KEYS=("RUSTC_BOOTSTRAP","RUSTFLAGS","CARGO_ENCODED_RUSTFLAGS","RUSTDOCFLAGS","CARGO_ENCODED_RUSTDOCFLAGS","RUSTC","RUSTC_WRAPPER","RUSTC_WORKSPACE_WRAPPER")
TEST="merge_cmd::native_sensor_transfer::fixed_native_sensor_transfer_pair"
SCHEMA="native-sensor-transfer-continuation-release-v1"
RESULT="native-sensor-transfer-owned-stage-v1"
TAIL="native-sensor-transfer-parent-tail-v1"
EXTERNAL="native-sensor-transfer-stage-external-v1"
READER_SCHEMA="native-sensor-transfer-reader-recovery-release-v1"
REQUIRED=("run-stage.py","bounded-build-process.py","capture-stage.py","run-stage-contract.md",
          "run-stage-source-review.md","charter.md","scope-amendment-2.md","scope-amendment-3.md",
          "source/implementation-contract.md","source/native-adapter.rs","source/core-hook.rs",
          "producer-source-review.md")
PREREQUISITES={"build-on":(),"build-off":("build-on",),
               "controls":("build-on","build-off"),"native":("build-on","build-off","controls"),
               "verify":("build-on","build-off","controls","native")}
ORIGINALS=tuple("D:/personal/macro/requests/10-paper-iso-var/DSC%05d.ARW"%i for i in range(235,240))+tuple(
    "D:/personal/macro/requests/6-11-extended-dark-frames/DSC%05d.ARW"%i for i in range(872,894))
COUNTS=(5,22,5,5,2,2,2,5,2)
OBSERVERS=("on","on","off","placebo","on","off","placebo","absent","absent")
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

def file_ref(path,cap,expected=None,check=lambda:None):
    return d.read(path,cap,expected,keep=False,check=check)[1]

def source_check(sources,budget):
    for key in sources:d.source_bytes(ROOT/key,sources,budget.check)
    return d.source_closure(sources,budget.check)

def load_base():
    global d
    raw=bootstrap(BASE,128*KIB)
    need(hashlib.sha256(raw).hexdigest()==BASE_SHA,"held M194h primitive source")
    d=types.ModuleType("native_sensor_held_m194h_primitives");d.__file__=str(BASE)
    exec(compile(raw,str(BASE),"exec"),d.__dict__)
    d.START=START;d.HERE=HERE;d.SELF=SELF;d.STAGES=STAGES.copy();d.OUTPUTS=OUTPUTS
    d.BUILD_PROCESS=BUILD_PROCESS;d.BUILD_PROCESS_SHA=BUILD_SHA
    d.FIXED_ENV={"RAYON_NUM_THREADS":"4"}
    d.TERMINAL_CAP=STAGE_RESULT_CAP
    return d

def source_map(sources):
    need(type(sources) is dict and 1<=len(sources)<=512,"bounded source map")
    resolved=set();total=0
    for key,pin in sources.items():
        need(type(key) is str and type(pin) is dict and set(pin)=={"bytes","sha256"},"source shape")
        need(type(pin["bytes"]) is int and 0<pin["bytes"]<=4*MIB and type(pin["sha256"]) is str
             and re.fullmatch("[0-9a-f]{64}",pin["sha256"]),"positive source extent/hash")
        p=d.owned(ROOT/key);need(d.source_ref(p)==key and p not in resolved,"canonical unique source")
        resolved.add(p);total+=pin["bytes"]
    need(total<=16*MIB,"source aggregate")

def build_configuration(env):
    need(env.get("CARGO_INCREMENTAL")=="0","fixed nonincremental native builds")
    need(not any(k.upper().startswith(BUILD_ENV_PREFIXES) or k.upper() in BUILD_ENV_KEYS for k in env),
         "no inherited build/target/profile/unstable compiler flag overrides")
    supplied=env.get("CARGO_HOME")
    need(supplied is None or type(supplied) is str and bool(supplied),"nonempty supplied Cargo home")
    home=d.lexical(supplied if supplied is not None else Path.home()/".cargo")
    paths=[]
    for base in (*(p/".cargo" for p in (ROOT,*ROOT.parents)),home):
        for name in ("config","config.toml"):
            candidate=base/name
            if candidate not in paths:paths.append(candidate)
    need(len(paths)==14,"fixed applicable Cargo configuration population")
    records=[]
    for candidate in paths:
        # lstat also detects present dangling/reparse configuration entries.
        try:candidate.lstat()
        except FileNotFoundError:records.append(dict(path=str(candidate),absent=True))
        else:raise ValueError(f"unexpected Cargo configuration source: {candidate}")
    return dict(cargo_home_environment=supplied,cargo_home_selected=str(home),cargo_incremental=env["CARGO_INCREMENTAL"],
                selection="explicit CARGO_HOME" if supplied is not None else "default user home/.cargo",
                candidates=records,environment_overrides="removed; no extra rustflags/profile/target/unstable keys",
                scope="Fixed absent configuration ruling and exact argv; no hermetic compiler/dependency claim")

def build_command(stage):
    command=["cargo","test","-p","strehl-cli","--bin","strehl","--no-run"]
    if stage=="build-on":command+=["--features","native-sensor-transfer"]
    return command+["--jobs","2","--target-dir",str(TARGETS[stage]),
                    "--message-format=json-render-diagnostics","--locked","--offline"]

def reader_command(mode,ref):
    return [str(Path(sys.executable)),"-I","-S","-B",str(READER),"--mode",mode,
            "--release",str(d.owned(ROOT/ref["path"])),"--release-sha256",ref["sha256"]]

def native_inventory(scanner,output):
    def scan(path,limit,*,tolerate_disappearance=False):
        if d.lexical(path)!=output or tolerate_disappearance:
            return scanner(path,limit,tolerate_disappearance=tolerate_disappearance)
        records=[];total=files=0
        for directory in (output,HERE/"native-1",HERE/"native-2",HERE/"native-attempt-1-partial",*(HERE/f"native-run-{i}" for i in range(9))):
            entry=scanner(directory,limit-total)
            total+=entry["bytes"];files+=entry["files"]
            records.append(dict(path=d.source_ref(directory),sample=entry))
        return dict(bytes=total,files=files,members=records,
                    scope="Non-atomic census of current/prior parent, archived partial and all nine producer directories; only the active named publication uses conservative final substitution")
    return scan

def authority(args):
    need(os.name=="nt" and Path.cwd().resolve()==ROOT,"Windows repository cwd")
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"isolated stdlib controller")
    load_base()
    path=d.owned(args.release);raw,ref=d.read(path,MIB)
    need(ref["sha256"]==args.release_sha256,"actual release SHA")
    release=d.strict(raw)
    keys={"schema","stage","source_bindings","inputs","originals","command","children","binaries","reader_release","prerequisites","recovery"}
    need(type(release) is dict and set(release)==keys and release["schema"]==SCHEMA,"closed eleven-key continuation release")
    stage=release["stage"];need(stage=="verify","verify retry only; no native/build/control replay")
    expected=[str(Path(sys.executable)),"-I","-S","-B",str(SELF),"--release",str(path),"--release-sha256",args.release_sha256]
    command=[args.release_sha256 if x=="ACTUAL_RELEASE_SHA256" else x for x in release["command"]]
    need(command==sys.orig_argv==expected and len(d.encoded(command))<=4*KIB,"exact controller argv")
    sources=release["source_bindings"];source_map(sources)
    mandatory=[HERE/name for name in REQUIRED]+[BASE,d.PROCESS,d.HARNESS,SCRATCH,ROOT/INPUT_BINDINGS["path"],SELF,NATIVE_SELF,PUBLICATION,HERE/"capture-verify-continuation.py",HERE/"capture-native-continuation.py",HERE/"prepare-native-continuation.py",HERE/"publication-race-controls.py"]
    if stage in ("controls","verify"):mandatory.append(READER)
    need(all(d.source_ref(p) in sources for p in mandatory),"mandatory stage source closure")
    need(sources[d.source_ref(BASE)]["sha256"]==BASE_SHA
         and sources[d.source_ref(BUILD_PROCESS)]["sha256"]==BUILD_SHA,"fixed reused source pins")
    d.source_bytes(SELF,sources)
    compile_stage=stage.startswith("build-")
    if compile_stage:
        d.TARGET=TARGETS[stage];d.STAGES["build"]=STAGES[stage]
        shim_raw=d.source_bytes(SCRATCH,sources)
        need(hashlib.sha256(shim_raw).hexdigest()==SCRATCH_SHA,"held scratch-only shim source")
        shim=types.ModuleType("native_sensor_scratch_scan");shim.__file__=str(SCRATCH)
        exec(compile(shim_raw,str(SCRATCH),"exec"),shim.__dict__)
        d.scan=shim.make_scanner(d,d.TARGET)
    output=OUTPUTS[stage];need(not output.exists(),"fresh once-only stage output")
    if stage=="native":
        need((HERE/"native-run-0").is_dir() and all(not (HERE/f"native-run-{i}").exists() for i in range(1,9)),"reuse zero and eight fresh native directories")
        publication_raw=d.source_bytes(PUBLICATION,sources)
        need(hashlib.sha256(publication_raw).hexdigest()==PUBLICATION_SHA,"held publication adapter")
        publication=types.ModuleType("native_publication");publication.__file__=str(PUBLICATION)
        exec(compile(publication_raw,str(PUBLICATION),"exec"),publication.__dict__)
        d.scan=native_inventory(publication.make_scanner(d,ACTIVE_NATIVE,HERE),output)
    output.mkdir()
    budget=d.Budget("build" if compile_stage else stage,output);budget.source_bindings=sources
    original_limits=budget.limits
    def limits(index):
        value=original_limits(index)
        value["log_bytes"]=16*MIB if compile_stage else MIB if stage=="native" else 128*KIB
        if stage in READER_CAPS:
            value["cpu_seconds"]=min(value["cpu_seconds"],READER_CAPS[stage]["cpu_seconds"])
            value["wall_seconds"]=min(value["wall_seconds"],READER_CAPS[stage]["wall_seconds"])
        return value
    budget.limits=limits
    result=dict(schema=RESULT,status="INITIAL_INCOMPLETE",stage=stage,release=ref,invocation=sys.orig_argv,
                children=[],artifacts={},prerequisites={},work=None,error=None,finalization_errors=[],
                limits=STAGES[stage],tail_allowance=dict(cpu_seconds=TAIL_CPU,wall_seconds=TAIL_WALL),
                scope="Parent CPU sample plus each owned child Job once; stage completion is operational, not physical model acceptance.")
    d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
    return release,ref,output,budget,result

def originals_check(originals):
    raw,_=d.read(ROOT/INPUT_BINDINGS["path"],16*KIB,INPUT_BINDINGS)
    held=d.strict(raw)
    need(held["schema"]=="native-sensor-transfer-input-bindings-v1"
         and held["status"]=="INPUT_IDENTITIES_HELD_UNDECODED" and held["error"] is None
         and originals==held["originals"],"exact once-held original identities")
    need(type(originals) is list and len(originals)==27,"fixed 27 original FileRefs")
    total=0
    for ref,expected in zip(originals,ORIGINALS):
        need(type(ref) is dict and set(ref)=={"path","bytes","sha256"} and type(ref["path"]) is str
             and type(ref["bytes"]) is int and 0<ref["bytes"]<=64*MIB
             and type(ref["sha256"]) is str and re.fullmatch("[0-9a-f]{64}",ref["sha256"]),"typed original FileRef")
        path=d.lexical(ref["path"]);need(path==d.lexical(expected),"fixed original order/path")
        st=path.stat();need(stat.S_ISREG(st.st_mode) and st.st_size==ref["bytes"],"original metadata extent")
        total+=ref["bytes"]
    need(total==926855168,"fixed original encoded aggregate")
    return dict(files=27,bytes=total,scope="Metadata extent/path check only; parent does not hash RAW payloads")

def input_check(release,budget):
    inputs=release["inputs"]
    need(type(inputs) is list and 1<=len(inputs)<=128,"bounded tool input roles")
    seen=set();total=0
    for ref in inputs:
        need(type(ref) is dict and set(ref)=={"path","bytes","sha256"} and type(ref["bytes"]) is int
             and 0<ref["bytes"]<=64*MIB,"positive released tool")
        p=d.lexical(ROOT/ref["path"]);need(p not in seen,"unique released tool")
        seen.add(p);total+=ref["bytes"]
    need(total<=256*MIB and d.lexical(sys.executable) in seen,"tool aggregate/current Python")
    if release["stage"].startswith("build-"):
        tools={d.lexical(shutil.which(name) or "") for name in ("cargo","rustc")}
        need(len(tools)==2 and tools<=seen,"actual resolved Cargo/rustc bindings")
    need(not seen.intersection(d.lexical(p) for p in ORIGINALS),"RAW originals are not repeated tool hashes")
    for ref in inputs:file_ref(ROOT/ref["path"],64*MIB,ref,budget.check)
    return inputs

def prerequisites(release,budget,closure):
    stage=release["stage"];bundles=release["prerequisites"]
    need(type(bundles) is dict and set(bundles)==set(PREREQUISITES[stage]),"fixed prerequisite stage order")
    prior={key:bundle_read(bundles[key],key,budget,release["source_bindings"]) for key in PREREQUISITES[stage]}
    for key,value in prior.items():
        need(value["compiled_source_closure"]==closure,"current compiled source closure equals each actual prerequisite")
    binaries=release["binaries"]
    names=() if stage=="build-on" else ("feature_on",) if stage=="build-off" else ("feature_on","feature_off")
    need(type(binaries) is dict and set(binaries)==set(names),"fixed available binary roles")
    for name in names:
        build="build-"+name.removeprefix("feature_");ref=binaries[name]
        need(d.same_ref(ref,prior[build]["artifacts"]["executable"])
             and d.lexical(ROOT/ref["path"])==EXES[name],"exact prior copied executable")
        file_ref(EXES[name],64*MIB,ref,budget.check)
    if stage in ("controls","verify"):
        ref=release["reader_release"]
        need(type(ref) is dict and d.lexical(ROOT/ref["path"])==HERE/"work"/"verify-recovery-reader-release-2.json","fixed reader release")
        raw,_=d.read(ROOT/ref["path"],MIB,ref,check=budget.check);reader=d.strict(raw)
        need(type(reader) is dict and set(reader)=={"schema","mode","source_bindings","originals","builds","native","controls","output","limits","command"}
             and reader["schema"]==READER_SCHEMA and reader["mode"]==stage,"closed reader release")
        need(reader["source_bindings"]==release["source_bindings"] and reader["originals"]==release["originals"],"current reader source/original authority")
        need(reader["builds"]=={"feature_on":bundles["build-on"],"feature_off":bundles["build-off"]},"reader actual build bundles")
        need(reader["native"]==dict(failed=release["recovery"]["failed_native"],resumed=bundles["native"])
             and reader["controls"]==(bundles["controls"] if stage=="verify" else None),"reader actual completed dependencies")
        need(d.lexical(reader["output"])==OUTPUTS[stage]/"check","fixed reader output")
        limits=reader["limits"]
        need(type(limits) is dict and set(limits)=={"cpu_seconds","wall_seconds","memory_bytes","read_bytes","write_bytes"}
             and all(type(limits[k]) is int and limits[k]>0 for k in limits),"typed positive reader limits")
        need(all(limits[k]<=maximum for k,maximum in READER_CAPS[stage].items()),"reader fits fixed stage suballocation")
        need([ref["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in reader["command"]]==reader_command(stage,ref),"reader exact argv")
    else:need(release["reader_release"] is None,"no premature reader release")
    return prior

def exact_children(release):
    stage=release["stage"]
    if stage.startswith("build-"):commands=[build_command(stage)]
    elif stage in ("controls","verify"):commands=[reader_command(stage,release["reader_release"])]
    else:
        commands=[[str(EXES["feature_on" if i<7 else "feature_off"]),"--ignored","--exact",TEST,
                   "--nocapture","--test-threads=1"] for i in range(1,9)]
    expected=[dict(command=c,expected_exit_code=0) for c in commands]
    need(type(release["children"]) is list and len(release["children"])==len(expected)
         and all(type(c) is dict and set(c)=={"command","expected_exit_code"}
                 and type(c["expected_exit_code"]) is int and type(c["command"]) is list
                 and all(type(x) is str for x in c["command"]) and len(d.encoded(c["command"]))<=4*KIB
                 for c in release["children"]),"typed bounded child schedule")
    need(release["children"]==expected,"fixed exact child schedule")
    return expected

def compiled_binary(stage,output,budget):
    raw,_=d.read(output/"child-00.log",16*MIB,check=budget.check)
    need(b"Compiling strehl-core" in raw and b"Compiling strehl-cli" in raw,"actual core and CLI Compiling lines")
    messages=[];finished=[]
    for line in raw.splitlines():
        if not line.startswith(b"{"):continue
        v=d.strict(line)
        if v.get("reason")=="build-finished":finished.append(v)
        if v.get("reason")=="compiler-artifact" and v.get("executable") and v.get("target",{}).get("name")=="strehl":
            messages.append(v)
    need(len(finished)==1 and set(finished[0])=={"reason","success"} and finished[0]["success"] is True,"actual successful Cargo build-finished")
    need(len(messages)==1,"unique test executable compiler artifact");v=messages[0]
    need(v["fresh"] is False and v["profile"]["test"] is True and v["target"]["kind"]==["bin"]
         and Path(v["target"]["src_path"]).resolve()==ROOT/"crates/strehl-cli/src/main.rs"
         and Path(v["manifest_path"]).resolve()==ROOT/"crates/strehl-cli/Cargo.toml"
         and v["features"]==(["native-sensor-transfer"] if stage=="build-on" else []),"fresh exact feature test executable")
    need(len(d.encoded(v))<=16*KIB,"bounded compiler message")
    origin=d.owned(v["executable"]);need(origin.is_relative_to(TARGETS[stage]),"new target artifact")
    data,original=d.read(origin,64*MIB,check=budget.check)
    copied=d.write_new(OUTPUTS[stage]/"cli-tests.exe",data,64*MIB)
    need(d.ref_binding(original)==d.ref_binding(copied),"copied actual executable bytes")
    return dict(executable=copied,compiled_original=original,compiler_message=v,build_finished=finished[0])

def capture_traversal(index,budget):
    path=HERE/f"native-run-{index}"/"result.json"
    raw,ref=d.read(path,64*KIB,check=budget.check);v=d.strict(raw)
    need(v["schema"]=="native-sensor-transfer-traversal-v1" and v["status"]=="COMPLETE_NATIVE_CROP_TRAVERSAL"
         and type(v["invocation"]) is int and v["invocation"]==index
         and v["feature"] is (index<7) and v["observer"]==OBSERVERS[index],"fixed completed traversal identity")
    need(type(v["native_decodes"]) is int and v["native_decodes"]==COUNTS[index]
         and type(v["folds"]) is int and v["folds"]==2*COUNTS[index]
         and len(v["frames"])==2*COUNTS[index] and len(v["outputs"])==2,"complete paired traversal population")
    return dict(invocation=index,result=ref)


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
    need(outer["command"]==result["invocation"],"prior invocation")
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
    need(old["schema"]==(SCHEMA if stage=="native" else "native-sensor-transfer-stage-release-v1") and old["stage"]==stage,"historical release stage")
    historical=old["source_bindings"];source_map(historical)
    historical_self=NATIVE_SELF if stage=="native" else OLD_SELF
    need(d.same_ref(outer["source"],dict(path=d.source_ref(historical_self),**historical[d.source_ref(historical_self)])),"historical own runner association")
    d.source_bytes(historical_self,historical,budget.check)
    # Unrelated later checker files need not equal the historical build map.
    # The caller compares actual current compiled closure to the retained build closure.
    need([result["release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in old["command"]]==result["invocation"],"prior release argv")
    for k,cap in caps.items():file_ref(ROOT/bundle[k]["path"],cap,bundle[k],budget.check)
    return result

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

def admit_recovery(release,budget,closure):
    recovery=release["recovery"]
    need(type(recovery) is dict and set(recovery)=={"failed_native","relocation","reused0"},"closed recovery")
    expected={k:HISTORY["failed_"+k] for k in ("result","tail","outer","stdout","stderr","exit")}
    need(recovery["failed_native"]==expected and recovery["relocation"]==HISTORY["archive"]
         and recovery["reused0"]==dict(child=HISTORY["child0"],result=HISTORY["traversal0"]),"exact saved recovery refs")
    caps=dict(result=256*KIB,tail=8*KIB,outer=64*KIB,stdout=8*KIB,stderr=32*KIB,exit=KIB)
    raw={k:d.read(ROOT/r["path"],caps[k],r,check=budget.check)[0] for k,r in expected.items()}
    old=d.strict(raw["result"]);outer=d.strict(raw["outer"]);tail=d.strict(raw["tail"]);advert=d.strict(raw["stdout"])
    need(old["schema"]==RESULT and old["stage"]=="native" and old["status"]=="REFUSED" and old["error"] is not None,"historical parent remains refused")
    need(outer["schema"]==EXTERNAL and outer["exit_code"]==1 and outer["timeout_terminated"] is False
         and raw["exit"]==b"1\n" and outer["command"]==old["invocation"],"actual refused parent transport")
    for k in ("stdout","stderr","exit"):need(d.same_ref(outer[k],expected[k]),"historical raw association")
    need(advert["status"]=="REFUSED" and d.same_ref(advert["result"],expected["result"])
         and d.same_ref(advert["tail"],expected["tail"]) and raw["stdout"]==d.encoded(advert)
         and d.same_ref(tail["result"],expected["result"]),"historical terminal association")
    before,_=d.read(ROOT/old["release"]["path"],MIB,old["release"],check=budget.check);prior=d.strict(before)
    frozen_raw,_=d.read(ROOT/HISTORY["freeze"]["path"],MIB,HISTORY["freeze"],check=budget.check);frozen=d.strict(frozen_raw)
    original=frozen["source_bindings"]
    need(len(original)==150 and prior["source_bindings"]==original and all(release["source_bindings"].get(k)==v for k,v in original.items()),"unchanged original 150 source bindings")
    need(hashlib.sha256(d.source_bytes(OLD_SELF,original,budget.check)).hexdigest()==OLD_RUNNER_SHA,"historical runner unchanged")
    need(prior["schema"]=="native-sensor-transfer-stage-release-v1" and prior["stage"]=="native"
         and [old["release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in prior["command"]]==old["invocation"]
         and d.same_ref(outer["source"],dict(path=d.source_ref(OLD_SELF),**original[d.source_ref(OLD_SELF)])),"historical release/runner identity")
    need(old["compiled_source_closure"]==closure and prior["binaries"]==release["binaries"]
         and prior["originals"]==release["originals"],"same compiled closure/executables/originals")
    need(len(old["children"])==2 and d.same_ref(old["children"][0],HISTORY["child0"])
         and d.same_ref(old["children"][1],HISTORY["child1"]),"actual completed and interrupted children")
    childraw,_=d.read(ROOT/HISTORY["child0"]["path"],32*KIB,HISTORY["child0"],check=budget.check);child=d.strict(childraw)
    need(child["error"] is None and child["cleanup_errors"]==[] and child["exit_code"]==0
         and child["direct_exit_observed"] is True and child["pipe_eof_observed"] is True
         and child["post_exit_drain"]["completed"] is True and child["terminal_job_accounting"] is True
         and child["job_accounting"]["active_processes"]==0 and child["termination"]["attempted"] is False
         and child["command"]==prior["children"][0]["command"],"saved zero clean actual child")
    d.job_cpu(child["job_accounting"])
    file_ref(HERE/"native-1/child-00.log",MIB,child["log"],budget.check)
    d.read(ROOT/HISTORY["child1"]["path"],32*KIB,HISTORY["child1"],check=budget.check)
    saved=old["artifacts"]["traversals"];captured=capture_traversal(0,budget)
    need(type(saved) is list and len(saved)==1 and all(type(row) is dict and set(row)=={"invocation","result"}
         and type(row["invocation"]) is int and row["invocation"]==0
         and d.same_ref(row["result"],HISTORY["traversal0"]) for row in (saved[0],captured)),"saved complete zero traversal")
    moved_raw,_=d.read(ROOT/HISTORY["archive"]["path"],64*KIB,HISTORY["archive"],check=budget.check);moved=d.strict(moved_raw)
    need(moved["content_hashes_preserved"] is True and moved["partial_population_excluded"] is True
         and moved["files"]==130 and moved["bytes"]==48620310
         and d.lexical(moved["from"])==HERE/"native-run-1"
         and d.lexical(moved["to"])==HERE/"native-attempt-1-partial"
         and (HERE/"native-attempt-1-partial").is_dir(),"exact preserved incomplete tree receipt")
    return dict(**recovery,original_source_freeze=HISTORY["freeze"],reused_invocations=[0],new_invocations=list(range(1,9)),
                prior_parent_status="REFUSED",scope="Child zero reused once. Fresh parent CPU/Job totals include only eight new children; all failed native-attempt costs remain separately charged. Archived incomplete frames are excluded.")

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--release",required=True);parser.add_argument("--release-sha256",required=True)
    args=parser.parse_args();release=release_ref=output=budget=result=None
    try:
        release,release_ref,output,budget,result=authority(args)
        stage=release["stage"];sources=release["source_bindings"]
        result["compiled_source_closure"]=source_check(sources,budget)
        input_check(release,budget);result["originals"]=release["originals"]
        result["original_metadata"]=originals_check(release["originals"])
        prerequisites(release,budget,result["compiled_source_closure"])
        result["recovery"]=admit_recovery(release,budget,result["compiled_source_closure"])
        if stage=="native":result["artifacts"]["traversals"]=[capture_traversal(0,budget)]
        result["prerequisites"]=release["prerequisites"];schedule=exact_children(release)
        env={k:v for k,v in d.clean_env().items()
             if not k.upper().startswith(("NATIVE_SENSOR_TRANSFER_",*BUILD_ENV_PREFIXES))
             and k.upper() not in BUILD_ENV_KEYS}
        need(not any(k.upper().startswith(("STREHL_","M194H_","NATIVE_SENSOR_TRANSFER_")) for k in env),"no native/experiment overrides")
        if stage.startswith("build-"):env["CARGO_INCREMENTAL"]="0"
        result["environment"]={k:env.get(k) for k in ("RAYON_NUM_THREADS","CARGO_NET_OFFLINE","RUSTUP_TOOLCHAIN","RUSTUP_HOME","CARGO_HOME","CARGO_INCREMENTAL")}
        need(len(d.encoded(result["environment"]))<=8*KIB,"bounded observed environment")
        result["environment_scope"]="Four Rayon threads; per-traversal pyramid/selector fields below. Offline compiler; observed inherited toolchain search is not hermetic."
        compile_stage=stage.startswith("build-")
        if compile_stage:
            need(not TARGETS[stage].exists(),"fresh target scratch")
            result["build_configuration"]=build_configuration(env)
        process,api=d.load_process(sources,compile_stage)
        result["operations"]=[];d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
        for i,child in enumerate(schedule):
            invocation=i+1 if stage=="native" else i
            child_env=env.copy()
            if stage in ("controls","verify"):child_env.update(READER_ENV)
            if stage=="native":
                need(not (HERE/f"native-run-{invocation}").exists(),"fresh native invocation directory")
                name="feature_on" if invocation<7 else "feature_off"
                file_ref(EXES[name],64*MIB,release["binaries"][name],budget.check)
                child_env.update(STREHL_PYRAMID_WORKERS="4",NATIVE_SENSOR_TRANSFER_INVOCATION=str(invocation))
            invocation_env={k:child_env[k] for k in ("RAYON_NUM_THREADS","STREHL_PYRAMID_WORKERS","NATIVE_SENSOR_TRANSFER_INVOCATION","CARGO_INCREMENTAL",*READER_ENV) if k in child_env}
            result["operations"].append(dict(ordinal=i,invocation=invocation,expected_exit_code=0,status="ATTEMPTED",environment=invocation_env))
            d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
            if stage=="native":ACTIVE_NATIVE[0]=invocation
            try:record=child_call(process,api,child["command"],child_env,0,i,output,budget,result)
            finally:ACTIVE_NATIVE[0]=None
            budget.check(True)
            result["operations"][-1]["status"]="EXPECTED_PROCESS_DISPOSITION"
            if compile_stage:result["artifacts"].update(compiled_binary(stage,output,budget))
            elif stage=="native":
                result["artifacts"].setdefault("traversals",[]).append(capture_traversal(invocation,budget))
                file_ref(EXES[name],64*MIB,release["binaries"][name],budget.check)
            else:
                final_raw,final_ref=d.read(output/"check/result.json",128*KIB,check=budget.check)
                log,_=d.read(output/"child-00.log",128*KIB,record["log"],check=budget.check)
                need(log==final_raw,"independent reader raw final association")
                final_value=d.strict(final_raw)
                expected_status="PASS_PRIVATE_CONTROLS_PENDING_ACTUAL" if stage=="controls" else "PASS_CONDITIONAL_NATIVE_DIAGNOSTIC"
                need(final_value["schema"]=="native-sensor-transfer-independent-result-v1"
                     and final_value["status"]==expected_status and final_value["physical_model_pass"] is None,
                     "actual independent software disposition without physical-model promotion")
                if stage=="verify":need(final_value["software_associations_complete"] is True,"complete saved software associations")
                result["artifacts"]["independent_result"]=final_ref
            d.atomic(output/"result.json",result,STAGE_RESULT_CAP)
        if stage=="native":need(len(result["artifacts"]["traversals"])==9,"complete fixed native population")
        if compile_stage:
            need(build_configuration(env)==result["build_configuration"],"unchanged final Cargo config absence/search root")
        need(source_check(sources,budget)==result["compiled_source_closure"],"unchanged final compiled closure")
        input_check(release,budget);originals_check(release["originals"])
        for name,ref in release["binaries"].items():file_ref(EXES[name],64*MIB,ref,budget.check)
        if release["reader_release"] is not None:
            ref=release["reader_release"];d.read(ROOT/ref["path"],MIB,ref,check=budget.check)
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
