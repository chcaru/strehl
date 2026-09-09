"""Saved common-TIFF verification2 only; source review and root release precede execution.
The pinned original controller is a definition library. No original main, build,
fixture producer, product invocation, or scientific function is called here.
"""
import time
START=time.monotonic()
from pathlib import Path
import ast,copy,hashlib,json,math,os,stat,sys,types
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
KIB=1024;MIB=1<<20
ORIGINAL=HERE/"run-stage.py"
ORIGINAL_PIN=(29852,"25d9b11cd0b99c1720ff460a4237209eaa9c6a36a8ffa8ade50afa608f41cb05")
FREEZE_PIN=(21903,"e30fa632be7cd66900e250d5c1abf5b748f729d19ff1494d8bb9518cb292de0f")
OLD_RELEASE_PIN=(27201,"aa060f5f69df6f37f24bf0dc50005377cf227aca7a9ea35eb3d1300d4ebb84a2")
EXTRAS=("independent-controls-2.py","independent-controls-2-spec.md","run-verification-2.py",
        "verification-2-contract.md","prepare-verification-2.py","capture-verification-2.py",
        "verification-2-decision.md","verification-2-source-review.md")
FAILURE_PINS={
 "verify-1/result.json":(65536,"85738ee79f68460cde0fc4b6118b4a4752be0dfe9e0d639b41c2a80a81cfe6b7"),
 "verify-1/child-00.json":(2712,"2bc170ab76cdfd99f1dfc376f01031001befe68785f5b8a15b363ff3043f489a"),
 "verify-1/child-00.log":(5871,"6a59e078697cb267fcc839b4aaff8ad4ec1eb62c38c385fb22b644763a77acec"),
 "verify-1/parent-tail.json":(606,"c8b4abf09c85164589658a4f4bbbf97b8ec1ce8fe9742c7ca49bb1cc1bbaa371"),
 "verify-1/check/result.json":(5871,"6a59e078697cb267fcc839b4aaff8ad4ec1eb62c38c385fb22b644763a77acec"),
 "work/verify-external-1-outer.json":(1595,"5ec49e5536c87c8f590d1487bc5a635ff79ec99d17b3e67afef3e305fd949363"),
 "work/verify-external-1-stdout.bin":(454,"64fc53575b64ef937b90d719773a6ccf1a901239f33c07c9009ce862d490f0ce"),
 "work/verify-external-1-stderr.bin":(0,"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
 "work/verify-external-1-exit.txt":(2,"4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865")}
SAME_FIELDS=("inputs","executable","fixtures","run_bundle","prerequisites")
P=A=None
original_authority=None
history_state=None

def need(value,message):
    if not value:raise ValueError(message)

def buffer(path,cap,empty=False):
    """Bounded initial metadata reader; separate full path/handle identities."""
    p=Path(os.path.abspath(path))
    for q in (p,*p.parents):
        s=q.lstat()
        need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain metadata ancestry")
    before=p.stat()
    need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,"declared metadata extent")
    with p.open("rb") as stream:
        opened=os.fstat(stream.fileno());raw=stream.read(cap+1);after=os.fstat(stream.fileno())
    final=p.stat()
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0))
    full=lambda s:shared(s)+(s.st_ctime_ns,)
    need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
         and len(raw)==before.st_size and len(raw)<=cap,"same metadata buffer")
    return raw

def strict(raw):
    def pairs(rows):
        out={}
        for key,value in rows:
            need(key not in out,"duplicate metadata key");out[key]=value
        return out
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,"nonfinite metadata"))
    def finite(v):
        if type(v) is float:need(math.isfinite(v),"nonfinite metadata")
        elif type(v) is dict:
            for x in v.values():finite(x)
        elif type(v) is list:
            for x in v:finite(x)
    finite(value);return value

def reference(path,raw):
    return dict(path=Path(path).relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def held(path,pin):
    raw=buffer(path,pin[0],empty=pin[0]==0)
    need((len(raw),hashlib.sha256(raw).hexdigest())==pin,"literal held metadata/source identity")
    return raw,reference(path,raw)

def namespaces():
    """Two namespaces, one reverse-proven schema literal; neither original entry runs."""
    global P,A,original_authority
    raw,_=held(ORIGINAL,ORIGINAL_PIN)
    tree=ast.parse(raw,str(ORIGINAL));patched=copy.deepcopy(tree)
    mains=[n for n in patched.body if isinstance(n,ast.FunctionDef) and n.name=="main"]
    need(len(mains)==1,"one held controller main")
    targets=[n for n in ast.walk(mains[0]) if isinstance(n,ast.Constant)
             and n.value=="common-tiff-stack-independent-verification-v1"]
    need(len(targets)==1,"one exact checker-schema seam")
    targets[0].value="common-tiff-stack-independent-verification-v2"
    reverse=copy.deepcopy(patched)
    reverted=[n for n in ast.walk(reverse) if isinstance(n,ast.Constant)
              and n.value=="common-tiff-stack-independent-verification-v2"]
    need(len(reverted)==1,"one reversal operand");reverted[0].value="common-tiff-stack-independent-verification-v1"
    need(ast.dump(reverse,include_attributes=False)==ast.dump(tree,include_attributes=False),"whole original AST restored")
    P=types.ModuleType("common_tiff_original_producer_definitions");P.__file__=str(ORIGINAL)
    A=types.ModuleType("common_tiff_saved_verification2_definitions");A.__file__=str(ORIGINAL)
    exec(compile(tree,str(ORIGINAL),"exec"),P.__dict__)
    exec(compile(patched,str(ORIGINAL),"exec"),A.__dict__)
    # Original producer namespace remains in its original source/schema/path gauge.
    P.START=START
    A.START=START;A.SELF=SELF
    A.SCHEMA="common-tiff-stack-stage-release-v2"
    A.RESULT="common-tiff-stack-owned-stage-v2"
    A.TAIL="common-tiff-stack-parent-tail-v2"
    A.CONTROLS=HERE/"independent-controls-2.py"
    A.OUTPUTS=dict(A.OUTPUTS);A.OUTPUTS["verify"]=HERE/"verify-2"
    A.REQUIRED=tuple(A.REQUIRED)+EXTRAS
    original_authority=A.authority
    A.authority=authority
    A.prerequisites=prerequisites
    A.fixture_read=P.fixture_read

def history():
    freeze_raw,freeze_ref=held(HERE/"work/source-freeze-3.json",FREEZE_PIN)
    old_raw,old_ref=held(HERE/"work/verify-release-1.json",OLD_RELEASE_PIN)
    freeze=strict(freeze_raw);old=strict(old_raw)
    need(set(freeze)=={"schema","source_bindings"} and freeze["schema"]=="common-tiff-stack-root-source-freeze-v1"
         and type(freeze["source_bindings"]) is dict and len(freeze["source_bindings"])==156,"held original156 freeze")
    need(set(old)=={"schema","stage","source_bindings","inputs","command","children","executable","fixtures","run_bundle","prerequisites"}
         and old["schema"]==P.SCHEMA and old["stage"]=="verify"
         and old["source_bindings"]==freeze["source_bindings"],"original verification1 source map")
    raw={};refs={}
    for name,pin in FAILURE_PINS.items():raw[name],refs[name]=held(HERE/name,pin)
    check=strict(raw["verify-1/check/result.json"]);child=strict(raw["verify-1/child-00.json"])
    parent=strict(raw["verify-1/result.json"]);tail=strict(raw["verify-1/parent-tail.json"])
    outer=strict(raw["work/verify-external-1-outer.json"])
    need(raw["verify-1/child-00.log"]==raw["verify-1/check/result.json"] and raw["work/verify-external-1-exit.txt"]==b"1\n"
         and raw["work/verify-external-1-stderr.bin"]==b"","exact original negative transport")
    need(check["status"]==parent["status"]=="REFUSED" and check["software_integration_complete"] is False
         and check["independent_controls"]==[] and len(check["cases"])==12
         and all(x["status"]=="SAVED_CASE_REJECTED" and x["error"]["message"]=="actual incomplete/manifest associations"
                 for x in check["cases"]),"preserved original pre-science rejection")
    need(type(child["exit_code"]) is int and child["exit_code"]==1 and child["error"] is None
         and child["cleanup_errors"]==[] and child["direct_exit_observed"] is True
         and child["pipe_eof_observed"] is True and child["post_exit_drain"]["completed"] is True
         and child["terminal_job_accounting"] is True and child["job_accounting"]["active_processes"]==0
         and child["termination"]["attempted"] is False,"old expected-zero failure had a clean negative child")
    need(type(outer["exit_code"]) is int and outer["exit_code"]==1 and outer["timeout_terminated"] is False
         and tail["cpu_accounting_complete"] is True and tail["live_child_cpu_seconds"]==0,"old actual terminal accounting")
    summary=dict(original_freeze=freeze_ref,original_verify_release=old_ref,failed_verification_refs=refs,
                 old_status="REFUSED",old_rejected_case_count=12,old_scientific_control_count=0,
                 old_measured_parent_cpu_seconds=tail["actual_parent_cpu_sample"],
                 old_measured_child_cpu_seconds=tail["completed_child_cpu_seconds"],
                 old_measured_whole_wall_seconds=outer["elapsed_wall_seconds"],
                 prior_verification_reserved=dict(cpu_seconds=60,wall_seconds=120,file_bytes=16*MIB),
                 current_verification_reserved=dict(cpu_seconds=60,wall_seconds=120,file_bytes=16*MIB),
                 verification_pair_reserved=dict(cpu_seconds=120,wall_seconds=240,file_bytes=32*MIB),
                 additional_metadata_reserved=dict(cpu_seconds=5,active_wall_seconds=7.5),
                 cumulative_metadata_reserved=dict(cpu_seconds=35,active_wall_seconds=52.5,file_bytes=8*MIB),
                 scope="Actual old failure remains refused; full entered reservations retained without refund. Current process work is reported separately.")
    return old,summary

def authority(args):
    global history_state
    need(Path(os.path.abspath(args.release))==HERE/"work/verify-release-2.json","fixed new release path")
    new_raw=buffer(args.release,MIB)
    need(hashlib.sha256(new_raw).hexdigest()==args.release_sha256,"new actual release SHA")
    new=strict(new_raw);old,summary=history()
    need(set(new)==set(old) and new["schema"]==A.SCHEMA and new["stage"]=="verify","saved-only ten-key release")
    producer=old["source_bindings"];sources=new["source_bindings"]
    extra_keys={(HERE/name).relative_to(ROOT).as_posix() for name in EXTRAS}
    need(type(sources) is dict and not(set(producer)&extra_keys) and set(sources)==set(producer)|extra_keys
         and len(sources)==164 and {k:sources[k] for k in producer}==producer,"original156 plus exact eight unchanged extension")
    need(all(new[k]==old[k] for k in SAME_FIELDS),"same original binary/input/fixture/render/prerequisite authority")
    freeze_path=HERE/"work/verification-source-freeze-2.json";freeze_raw=buffer(freeze_path,MIB);freeze=strict(freeze_raw)
    need(set(freeze)=={"schema","producer_release","source_bindings"}
         and freeze["schema"]=="common-tiff-stack-verification-source-freeze-v2"
         and freeze["producer_release"]==summary["original_verify_release"] and freeze["source_bindings"]==sources,"exact separate verification freeze")
    # Existing authority authenticates all current pins, argv, caps, and freshness.
    returned=original_authority(args)
    release,ref,output,budget,result=returned
    need(release==new,"unchanged new release between authority reads")
    P.d=A.d;history_state=(old,summary)
    summary["verification_freeze"]=reference(freeze_path,freeze_raw)
    summary["added_sources"]=[dict(path=k,**sources[k]) for k in sorted(extra_keys)]
    result["verification_history"]=summary
    result["source_bindings"]=sources
    return returned

def prerequisites(release,budget):
    need(history_state is not None and release["stage"]=="verify","saved-only authority completed")
    old,_=history_state
    need(all(release[k]==old[k] for k in SAME_FIELDS),"original prerequisite fields remain literal")
    # Prior body uses the original SELF, schemas, paths, producer156 source map,
    # and original fixture source/spec. Budget still accounts all current work.
    return P.prerequisites(old,budget)

def main():
    namespaces()
    return A.main()

if __name__=="__main__":raise SystemExit(main())
