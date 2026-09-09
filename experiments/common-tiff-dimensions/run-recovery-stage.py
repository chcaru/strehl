"""Additive saved-fixture admission/render/verify. No build or generator entrypoint."""
import time
START=time.monotonic()
from pathlib import Path
import argparse,ast,copy,hashlib,json,math,os,stat,sys,types
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve();KIB=1024;MIB=1<<20
H=P=A=None
ORIGINAL_AUTHORITY=ORIGINAL_CHILDREN=None
OLD=CURRENT=CONTEXT=None
FIXTURE_READER=PROOF=None
READ_BYTES=0;READ_CAP=None
RESULT_CONTEXT=None

def need(v,message):
    if not v:raise ValueError(message)

def bootstrap(path,cap):
    global READ_BYTES
    p=Path(os.path.abspath(path))
    for q in (p,*p.parents):
        s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain bootstrap ancestry")
    before=p.stat();need(stat.S_ISREG(before.st_mode) and 0<before.st_size<=cap,"bounded bootstrap")
    need(READ_CAP is None or READ_BYTES+before.st_size+1<=READ_CAP,"bounded admission bootstrap read")
    with p.open("rb") as f:
        opened=os.fstat(f.fileno());raw=f.read(before.st_size+1);after=os.fstat(f.fileno())
    final=p.stat()
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0))
    full=lambda s:shared(s)+(s.st_ctime_ns,)
    need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
         and len(raw)==before.st_size and len(raw)<=cap,"same bootstrap bytes")
    READ_BYTES+=len(raw)+1
    return raw

def metered_reader(original):
    def read(path,cap,*args,**kwargs):
        global READ_BYTES
        if READ_CAP is None:return original(path,cap,*args,**kwargs)
        extent=Path(path).stat().st_size
        need(type(extent) is int and 0<=extent<=cap,"bounded admission read preextent")
        need(READ_BYTES+extent+1<=READ_CAP,"64MiB admission content-read allowance")
        READ_BYTES+=extent+1
        if RESULT_CONTEXT is not None:
            RESULT_CONTEXT["read_accounting"]=dict(charged_bytes_sample=READ_BYTES,final_read_allowance=MIB,cap=READ_CAP,scope="Content reads including bootstrap and publication readbacks; final sample has a separate1MiB read tail.")
        return original(path,min(cap,extent),*args,**kwargs)
    return read

def history_read(ref,budget,cap=None):
    return P.d.read(ROOT/ref["path"],ref["bytes"] if cap is None else cap,ref,check=budget.check)[0]

def failure_history(budget):
    raw={k:history_read(ref,budget) for k,ref in H.HISTORY["prepare"].items()}
    parent,tail,outer,advert=(P.d.strict(raw[k]) for k in ("result","tail","outer","stdout"))
    child=P.d.strict(history_read(H.HISTORY["prepare_child"],budget))
    log=history_read(H.HISTORY["prepare_log"],budget);generated=P.d.strict(log)
    release=P.d.strict(history_read(H.HISTORY["prepare_release"],budget))
    need(release["schema"]==P.SCHEMA and release["stage"]=="prepare"
         and H.exact(release["source_bindings"],OLD),"original preparation authority")
    need(P.d.same_ref(parent["release"],H.HISTORY["prepare_release"])
         and parent["invocation"]==outer["command"]==
         [H.HISTORY["prepare_release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in release["command"]],
         "original failed preparation argv")
    need(len(parent["children"])==1 and P.d.same_ref(parent["children"][0],H.HISTORY["prepare_child"])
         and P.d.same_ref(child["log"],H.HISTORY["prepare_log"])
         and child["log_bytes"]==len(log) and len(release["children"])==1
         and child["command"]==release["children"][0]["command"]
         and release["children"][0]["expected_exit_code"]==0,"original one generator child and stdout")
    need(H.exact(parent["prerequisites"],{"build":H.HISTORY["build"]})
         and H.exact(parent["compiled_source_closure"],H.COMPILED),"original build and compiled closure")
    need(set(outer)=={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds",
                     "stdout","stderr","exit","stdout_bytes","stderr_bytes","scope"}
         and outer["schema"]==P.EXTERNAL and P.d.same_ref(outer["source"],H.HISTORY["original_controller"]),
         "original failed outer/source")
    for role in ("stdout","stderr","exit"):
        need(P.d.same_ref(outer[role],H.HISTORY["prepare"][role]),"failed raw stream identity")
    need(outer["stdout_bytes"]==len(raw["stdout"]) and outer["stderr_bytes"]==len(raw["stderr"])
         and raw["stderr"]==b"" and raw["stdout"]==P.d.encoded(advert)
         and set(advert)=={"status","result","tail"} and advert["status"]=="REFUSED"
         and P.d.same_ref(advert["result"],H.HISTORY["prepare"]["result"])
         and P.d.same_ref(advert["tail"],H.HISTORY["prepare"]["tail"])
         and tail["schema"]==P.TAIL and P.d.same_ref(tail["result"],H.HISTORY["prepare"]["result"]),
         "actual failed preparation advertisement/tail")
    return H.admit_saved_prepare(parent,child,generated,tail,outer,raw["exit"],H.HISTORY["index"],release["children"][0]["command"])

def controls_read(bundle,budget):
    caps={"result":128*KIB,"outer":64*KIB,"stdout":128*KIB,"stderr":16*KIB,"exit":KIB}
    need(type(bundle) is dict and set(bundle)==set(caps),"five fixed recovery control evidence refs")
    raw={k:A.d.read(ROOT/bundle[k]["path"],cap,bundle[k],check=budget.check)[0] for k,cap in caps.items()}
    value,outer=(A.d.strict(raw[k]) for k in ("result","outer"))
    need(A.d.lexical(ROOT/bundle["result"]["path"])==HERE/"work/recovery-controls-1/result.json"
         and raw["result"]==raw["stdout"] and raw["stderr"]==b"" and raw["exit"]==b"0\n",
         "actual control output/stream identity")
    need(value["schema"]=="common-tiff-dimensions-recovery-controls-v1"
         and value["status"]=="PASS_FIXED_RECOVERY_METADATA_CONTROLS"
         and value["controls_complete"] is True and type(value["groups"]) is int and value["groups"]==40
         and type(value["completed_groups"]) is int and value["completed_groups"]==40
         and value["error"] is None,"actual recovery control pass")
    source=A.d.source_bytes(HERE/"recovery-controls.py",CURRENT,budget.check)
    tree=ast.parse(source);decl=[x for x in tree.body if isinstance(x,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=="IDS" for t in x.targets)]
    need(len(decl)==1,"one literal independent control population")
    ids=ast.literal_eval(decl[0].value)
    need(type(ids) is tuple and len(ids)==40 and len(set(ids))==40
         and type(value["rows"]) is list and len(value["rows"])==40
         and [r["id"] for r in value["rows"]]==list(ids)
         and all(set(r)=={"id","passed","details"} and r["passed"] is True for r in value["rows"]),
         "all fixed independent controls visited")
    need(P.d.same_ref(value["source"],dict(path="experiments/common-tiff-dimensions/recovery-controls.py",
                                        **CURRENT["experiments/common-tiff-dimensions/recovery-controls.py"]))
         and value["publication_allowance"]==dict(cpu_seconds=1,wall_seconds=2)
         and value["full_reserved_allowance"]==dict(cpu_seconds=5,wall_seconds=10,read_bytes=4*MIB,write_bytes=2*MIB)
         and all(A.d.finite(value["own_work"][k]) for k in ("cpu_seconds","wall_seconds"))
         and value["own_work"]["cpu_seconds"]+1<=5 and value["own_work"]["wall_seconds"]+2<=10,
         "actual bounded independent controls")
    need(outer["schema"]=="common-tiff-dimensions-recovery-controls-external-v1"
         and type(outer["exit_code"]) is int and outer["exit_code"]==0 and outer["timeout_terminated"] is False
         and 0<=outer["elapsed_wall_seconds"]<=10
         and P.d.same_ref(outer["source"],dict(path="experiments/common-tiff-dimensions/recovery-controls.py",
                                            **CURRENT["experiments/common-tiff-dimensions/recovery-controls.py"])),
         "actual recovery controls external disposition")
    expected=[str(Path(sys.executable)),"-I","-S","-B",str(HERE/"recovery-controls.py"),
              "--source-sha256",CURRENT["experiments/common-tiff-dimensions/recovery-controls.py"]["sha256"],
              "--output",str(HERE/"work/recovery-controls-1")]
    need(outer["command"]==value["invocation"]==expected,"exact independent control command")
    need(set(outer)=={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds",
         "stdout","stderr","exit","stdout_bytes","stderr_bytes","scope","capture_accounting"},"closed controls outer")
    capture=outer["capture_accounting"]
    need(set(capture)=={"parent_cpu_sample","whole_wall_sample","publication_allowance","reserved","admitted","error","scope"}
         and capture["admitted"] is True and capture["error"] is None
         and H.exact(capture["publication_allowance"],dict(cpu_seconds=1,wall_seconds=2))
         and H.exact(capture["reserved"],dict(cpu_seconds=5,overhead_wall_seconds=10,whole_wall_seconds=20))
         and all(A.d.finite(capture[k]) for k in ("parent_cpu_sample","whole_wall_sample"))
         and capture["parent_cpu_sample"]+1<=5 and capture["whole_wall_sample"]>=outer["elapsed_wall_seconds"]
         and capture["whole_wall_sample"]+2<=20
         and capture["whole_wall_sample"]-outer["elapsed_wall_seconds"]+2<=10,"bounded controls capture")
    for role in ("stdout","stderr","exit"):need(P.d.same_ref(outer[role],bundle[role]),"control external raw refs")
    need(outer["stdout_bytes"]==len(raw["stdout"]) and outer["stderr_bytes"]==len(raw["stderr"]),"control raw extents")
    return value

def fixture_read(ref,budget):
    PROOF["visits"].clear()
    value=FIXTURE_READER(ref,types.SimpleNamespace(source_bindings=OLD,check=budget.check))
    need(len(PROOF["visits"])==2 and all(row["matched"] is True for row in PROOF["visits"]),"both actual legacy associations visited")
    return value

def get_controls_bundle(release,budget):
    path=HERE/"work/recovery-controls-bundle-1.json"
    found=[r for r in release["inputs"] if A.d.lexical(ROOT/r["path"])==path]
    need(len(found)==1,"one explicit recovery control bundle input")
    raw=A.d.read(path,16*KIB,found[0],check=budget.check)[0]
    value=A.d.strict(raw);controls_read(value,budget);return value

def prerequisites(release,budget):
    stage=release["stage"]
    need(H.exact(RESULT_CONTEXT["compiled_source_closure"],H.COMPILED),"current compiled118 identity equals successful build")
    keys={"recovery":{"build","prepare"},"render":{"build","prepare","recovery"},"verify":{"build","prepare","recovery","render"}}[stage]
    need(type(release["prerequisites"]) is dict and set(release["prerequisites"])==keys,"versioned exact prerequisite roles")
    need(H.exact(release["prerequisites"]["build"],H.HISTORY["build"])
         and H.exact(release["prerequisites"]["prepare"],H.HISTORY["prepare"]),"literal historical bundles preserved")
    build=P.bundle_read(release["prerequisites"]["build"],"build",budget,OLD)
    need(H.exact(build["compiled_source_closure"],H.COMPILED)
         and H.legacy_same_ref(build["artifacts"]["executable"],H.EXE_REF)
         and H.legacy_same_ref(release["executable"],H.EXE_REF),"unchanged actual compiled118 binary")
    A.file_ref(A.EXE,64*MIB,release["executable"],budget.check)
    old_disposition=failure_history(budget)
    need(H.exact(release["fixtures"],H.HISTORY["index"]),"fixed original prepared index")
    index=fixture_read(release["fixtures"],budget)
    controls=get_controls_bundle(release,budget)
    prior={"build":build,"prepare":old_disposition}
    files=[H.HISTORY["index"],*index["generated_files"]]
    if stage=="recovery":
        need(release["run_bundle"] is None,"no render bundle at admission")
        value=dict(schema=H.ADMISSION_SCHEMA,status="SAVED_FIXTURES_ADMITTED",old_prepare_status="REFUSED",subject_complete=False,
          producer_freeze=H.HISTORY["producer_freeze"],producer_source_map_sha256=H.map_sha(OLD),
          execution_source_map_sha256=H.map_sha(CURRENT),compiled_source_closure=H.COMPILED,
          build=H.HISTORY["build"],failed_prepare=H.HISTORY["prepare"],
          generator_child=H.HISTORY["prepare_child"],generator_stdout=H.HISTORY["prepare_log"],
          index=H.HISTORY["index"],files=files,file_bytes=sum(r["bytes"] for r in files),
          fixture_read_proof=copy.deepcopy(PROOF),controls=controls,
          scope="Saved fixture bytes admitted only with this recovery stage's complete parent/tail/outer; original prepare stays REFUSED. No pixel or software-integration claim.")
        H.admission_association(value,H.HISTORY["index"],H.HISTORY["producer_freeze"],OLD,CURRENT,files)
        ref=A.d.write_new(A.OUTPUTS["recovery"]/"admission.json",A.d.encoded(value),128*KIB)
        RESULT_CONTEXT["artifacts"].update(admission=ref,fixture_index=H.HISTORY["index"])
    else:
        recovered=A.bundle_read(release["prerequisites"]["recovery"],"recovery",budget,CURRENT)
        ref=recovered["artifacts"]["admission"]
        need(A.d.lexical(ROOT/ref["path"])==A.OUTPUTS["recovery"]/"admission.json","fixed genuine admission receipt")
        value=A.d.strict(A.d.read(ROOT/ref["path"],128*KIB,ref,check=budget.check)[0])
        H.admission_association(value,H.HISTORY["index"],H.HISTORY["producer_freeze"],OLD,CURRENT,files)
        need(H.exact(value["controls"],controls),"same exact actual controls")
        prior["recovery"]=recovered
        if stage=="verify":
            prior["render"]=A.bundle_read(release["prerequisites"]["render"],"render",budget,CURRENT)
            raw=A.d.read(A.RUN_BUNDLE,64*KIB,release["run_bundle"],check=budget.check)[0]
            need(A.d.lexical(ROOT/release["run_bundle"]["path"])==A.RUN_BUNDLE
                 and H.exact(A.d.strict(raw),release["prerequisites"]["render"]),"actual current render bundle")
        else:need(release["run_bundle"] is None,"no premature render bundle")
    RESULT_CONTEXT["recovery_history"]=dict(original_prepare_status="REFUSED",compiled_source_closure=H.COMPILED,
        producer_freeze=H.HISTORY["producer_freeze"],producer_source_map_sha256=H.map_sha(OLD),
        execution_source_map_sha256=H.map_sha(CURRENT),reservations=H.RESERVATIONS)
    return prior,index

def exact_children(release,index):
    if release["stage"]=="recovery":
        need(release["children"]==[],"saved admission launches no child");return []
    return ORIGINAL_CHILDREN(release,index)

def authority(args):
    global OLD,CURRENT,READ_CAP,FIXTURE_READER,PROOF,RESULT_CONTEXT
    stage=CONTEXT["stage"]
    need(stage in ("recovery","render","verify"),"no build or generator recovery entrypoint")
    need(Path(os.path.abspath(args.release))==HERE/f"work/{stage}-recovery-release-1.json","fixed recovery release path")
    OLD=H.producer_sources();CURRENT=CONTEXT["source_bindings"];H.extension(OLD,CURRENT)
    freeze_path=HERE/"work/recovery-source-freeze-1.json"
    frozen_raw,_=H.read_bound(freeze_path,MIB);frozen=H.strict(frozen_raw)
    need(set(frozen)=={"schema","producer_freeze","source_bindings","delta_archive"}
         and frozen["schema"]=="common-tiff-dimensions-recovery-source-freeze-v1"
         and H.exact(frozen["producer_freeze"],H.HISTORY["producer_freeze"])
         and H.exact(frozen["source_bindings"],CURRENT),"explicit additive recovery freeze")
    returned=ORIGINAL_AUTHORITY(args)
    release,ref,output,budget,result=returned
    RESULT_CONTEXT=result
    need(H.exact(release,CONTEXT),"same exact recovery release bytes")
    READ_CAP=64*MIB if stage=="recovery" else None
    need(READ_CAP is None or READ_BYTES<=READ_CAP,"bounded admission bootstrap reads")
    P.load_base()
    original_check=budget.check
    def check(terminal=False):
        if terminal and READ_CAP is not None:need(READ_BYTES+MIB<=READ_CAP,"admission final read reserve")
        return original_check(terminal)
    budget.check=check
    FIXTURE_READER,PROOF=H.make_fixture_reader(P,ORIGINAL_RAW)
    original_load=A.d.load_process
    def load(sources,compile_only=False):
        need(not compile_only,"no compiler helper in recovery")
        return (None,None) if stage=="recovery" else original_load(sources,False)
    A.d.load_process=load
    return returned

def setup(args):
    global H,P,A,ORIGINAL_AUTHORITY,ORIGINAL_CHILDREN,CONTEXT,ORIGINAL_RAW,READ_CAP
    raw=bootstrap(args.release,MIB)
    need(hashlib.sha256(raw).hexdigest()==args.release_sha256,"actual new release hash")
    provisional=json.loads(raw)
    READ_CAP=64*MIB if type(provisional) is dict and provisional.get("stage")=="recovery" else None
    need(type(provisional) is dict and type(provisional.get("source_bindings")) is dict,"bounded source-bearing release")
    key="experiments/common-tiff-dimensions/recovery-authority.py";pin=provisional["source_bindings"][key]
    need(type(pin) is dict and type(pin.get("bytes")) is int and 0<pin["bytes"]<=32*KIB,"bounded authority source pin")
    source=bootstrap(ROOT/key,32*KIB)
    need(len(source)==pin["bytes"] and hashlib.sha256(source).hexdigest()==pin["sha256"],"authenticated authority source")
    H=types.ModuleType("common_tiff_recovery_authority");H.__file__=str(ROOT/key)
    exec(compile(source,str(ROOT/key),"exec"),H.__dict__)
    CONTEXT=H.strict(raw)
    H.read_bound=metered_reader(H.read_bound)
    ORIGINAL_RAW,_=H.read_bound(ROOT/H.HISTORY["original_controller"]["path"],128*KIB,H.HISTORY["original_controller"])
    for label in ("P","A"):
        module=types.ModuleType("common_tiff_original_provenance" if label=="P" else "common_tiff_recovery_execution")
        module.__file__=str(ROOT/H.HISTORY["original_controller"]["path"])
        exec(compile(ORIGINAL_RAW,module.__file__,"exec"),module.__dict__)
        if label=="P":P=module
        else:A=module
    for module in (P,A):
        module.bootstrap=metered_reader(module.bootstrap)
        original_load=module.load_base
        def load_base(original_load=original_load,module=module):
            d=original_load();d.read=metered_reader(d.read);return d
        module.load_base=load_base
    P.START=START;A.START=START;A.SELF=SELF
    A.SCHEMA="common-tiff-dimensions-stage-release-v2";A.RESULT="common-tiff-dimensions-owned-stage-v2"
    A.TAIL="common-tiff-dimensions-parent-tail-v2";A.EXTERNAL="common-tiff-dimensions-stage-external-v2"
    A.CONTROLS=HERE/"recovery-checker.py"
    A.OUTPUTS={"recovery":HERE/"recovery-1","render":HERE/"render-1","verify":HERE/"verify-1"}
    A.STAGES={k:v for k,v in A.STAGES.items() if k in ("render","verify")}
    A.STAGES["recovery"]=dict(cpu_seconds=10,wall_seconds=20,committed_bytes=1<<30,file_bytes=2*MIB,scratch_bytes=0)
    A.REQUIRED=tuple(A.REQUIRED)+H.EXTRAS
    ORIGINAL_AUTHORITY=A.authority;ORIGINAL_CHILDREN=A.exact_children
    A.authority=authority;A.prerequisites=prerequisites;A.fixture_read=fixture_read;A.exact_children=exact_children

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--release",required=True);parser.add_argument("--release-sha256",required=True)
    args=parser.parse_args()
    setup(args)
    return A.main()

if __name__=="__main__":raise SystemExit(main())
