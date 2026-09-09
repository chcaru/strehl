"""Additive saved-fixture authority. No I/O or subject runs at module import."""
from pathlib import Path
import ast,copy,hashlib,json,math,os,re,stat,types

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/"experiments/common-tiff-dimensions"
KIB=1024;MIB=1<<20
HISTORY={
  "build": {
    "result": {
      "path": "experiments/common-tiff-dimensions/build-2/result.json",
      "bytes": 262144,
      "sha256": "7f35c05c7eeffbe026dbd7b9b67267982a03abd442df7024984efe5ca9e14532"
    },
    "tail": {
      "path": "experiments/common-tiff-dimensions/build-2/parent-tail.json",
      "bytes": 619,
      "sha256": "dc6e78b55d81b090843020447c5a136477d8a508fe1b5e4f86e39ddee0ebe9fd"
    },
    "outer": {
      "path": "experiments/common-tiff-dimensions/work/build-external-2-outer.json",
      "bytes": 1625,
      "sha256": "f79ef43e385726d71040143ed26c2293c7e84413480e96a3b4afea02c08f2244"
    },
    "stdout": {
      "path": "experiments/common-tiff-dimensions/work/build-external-2-stdout.bin",
      "bytes": 481,
      "sha256": "8ae4833c5c843baeb1e658ca2040cee0c376663183302e5b26aba6242a58bf7c"
    },
    "stderr": {
      "path": "experiments/common-tiff-dimensions/work/build-external-2-stderr.bin",
      "bytes": 0,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    "exit": {
      "path": "experiments/common-tiff-dimensions/work/build-external-2-exit.txt",
      "bytes": 2,
      "sha256": "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
    }
  },
  "prepare": {
    "result": {
      "path": "experiments/common-tiff-dimensions/prepare-1/result.json",
      "bytes": 262144,
      "sha256": "8411594fbca4f81d3574e369a2089c2b3cf5d77b4580da8d827d218f5499c1f5"
    },
    "tail": {
      "path": "experiments/common-tiff-dimensions/prepare-1/parent-tail.json",
      "bytes": 619,
      "sha256": "67acd7438b0e46a9b19a0436187910c3c8aad14e23fde03169189879609a45bd"
    },
    "outer": {
      "path": "experiments/common-tiff-dimensions/work/prepare-external-1-outer.json",
      "bytes": 1634,
      "sha256": "65f109dd5e47252e503ed84cf993cbc8dadf7d59da21493ccadb087f23cfdf9b"
    },
    "stdout": {
      "path": "experiments/common-tiff-dimensions/work/prepare-external-1-stdout.bin",
      "bytes": 467,
      "sha256": "696f8e97d5bb765e4c3d4592b7100ad700ba33d5c1f8bb4fbcb9aebca032b975"
    },
    "stderr": {
      "path": "experiments/common-tiff-dimensions/work/prepare-external-1-stderr.bin",
      "bytes": 0,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    "exit": {
      "path": "experiments/common-tiff-dimensions/work/prepare-external-1-exit.txt",
      "bytes": 2,
      "sha256": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865"
    }
  },
  "build_release": {
    "path": "experiments/common-tiff-dimensions/work/build-release-2.json",
    "bytes": 28414,
    "sha256": "e6a6610d81854b14689cea52fd7faeff9467639cd1b98ad06ccc2b69671efdb5"
  },
  "prepare_release": {
    "path": "experiments/common-tiff-dimensions/work/prepare-release-1.json",
    "bytes": 29563,
    "sha256": "ce63754d0ec95f0c1b6636a45f3289daa8deb813bab16f16c0177eb1fcb11aa6"
  },
  "producer_freeze": {
    "path": "experiments/common-tiff-dimensions/work/source-freeze-2.json",
    "bytes": 28634,
    "sha256": "f3778c80df31b6cde6e253797cf497ca2cdfced85f8507ae126ba03ce8563708"
  },
  "prepare_child": {
    "path": "experiments/common-tiff-dimensions/prepare-1/child-00.json",
    "bytes": 2293,
    "sha256": "3aee4d40f23c980989772c46cefcbb967dfae9ffe5090a508285002114870380"
  },
  "prepare_log": {
    "path": "experiments/common-tiff-dimensions/prepare-1/child-00.log",
    "bytes": 6382,
    "sha256": "b040b37644f5cc3413ac8d4c7e798194402c173d07c7c8fe692bfeb6be93f144"
  },
  "index": {
    "path": "experiments/common-tiff-dimensions/prepare-1/fixtures/index.json",
    "bytes": 40481,
    "sha256": "d07f356bdd7b2286b88404a337afd831319130e979b9adc27222d5ad71b1bf98"
  },
  "original_controller": {
    "path": "experiments/common-tiff-dimensions/run-stage.py",
    "bytes": 33546,
    "sha256": "442226bd08b128f8bb97460fab6f8ab6280fd0950d1912313b87d583b7a33940"
  },
  "original_checker": {
    "path": "experiments/common-tiff-dimensions/independent-controls.py",
    "bytes": 65751,
    "sha256": "8fefa5e31c614595367f644b314ece77da6bf5d4ec54c4edde80816a0e8cee47"
  },
  "original_spec": {
    "path": "experiments/common-tiff-dimensions/independent-spec.md",
    "bytes": 19270,
    "sha256": "055b66302e3f73d3d62226c25cef939f74dd664149e1a7d005991ce09286489b"
  }
}
EXTRAS=("run-recovery-stage.py","recovery-authority.py","prepare-recovery-release.py",
        "capture-recovery-stage.py","recovery-contract.md","recoverydesign.md",
        "recovery-controls.py","recovery-spec.md","recovery-checker.py","recovery-source-review.md")
COMPILED={"files":118,"canonical_sha256":"ee02f4b41cfc5cc5c1d501c72d9980f2131fba9b891e6b9aca9412e119ff72a8"}
INDEX=HERE/"prepare-1/fixtures/index.json"
EXE=HERE/"build-2/strehl-common-input.exe"
EXE_REF={"path":"experiments/common-tiff-dimensions/build-2/strehl-common-input.exe","bytes":3201536,
         "sha256":"172a52135ebee5853169cd3cd8bd8e9c97b4dc6ad5a886c20bfd57ea0a4a0684"}
FIXTURE_AST_SHA='6fdf3945d43620706246caae9e962209ae3386e9e2b85315baed018d102c90c7'
LEGACY_ASSOCIATIONS=[{'left': {'bytes': 2905, 'path': '\\\\?\\C:\\dev\\blog\\death-of-software\\projects\\strehl\\experiments\\common-tiff-stack\\prepare-1\\fixtures\\case-00.json', 'sha256': '7c764e065a46e33da556ff98daf67f2c027abdbec833da63b742d82620ffd837'}, 'right': {'bytes': 2905, 'path': 'C:\\dev\\blog\\death-of-software\\projects\\strehl\\experiments\\common-tiff-stack\\prepare-1\\fixtures\\case-00.json', 'sha256': '7c764e065a46e33da556ff98daf67f2c027abdbec833da63b742d82620ffd837'}, 'matched': True}, {'left': {'bytes': 74807, 'path': '\\\\?\\C:\\dev\\blog\\death-of-software\\projects\\strehl\\experiments\\common-tiff-stack\\render-1\\case-00\\output.tiff', 'sha256': '1e6c9f9bd3146c0c8f7314c422e26c842eb45ba25d76d12adae8f8d690842f7e'}, 'right': {'bytes': 74807, 'path': 'experiments/common-tiff-stack/render-1/case-00/output.tiff', 'sha256': '1e6c9f9bd3146c0c8f7314c422e26c842eb45ba25d76d12adae8f8d690842f7e'}, 'matched': True}]
ADMISSION_SCHEMA="common-tiff-dimensions-saved-fixture-admission-v1"
FAILURE_SHA="c7ca5efa219aefb6d3517658d1d8a1539d831b22187e180ce4bc31c7ff21518b"
RESERVATIONS={
 "prior_builds":{"cpu_seconds":1200,"wall_seconds":600,"retained":True},
 "failed_prepare":{"cpu_seconds":30,"wall_seconds":60,"file_bytes":34*MIB,"retained":True},
 "saved_admission":{"cpu_seconds":10,"wall_seconds":20,"read_bytes":64*MIB,"file_bytes":2*MIB},
 "private_recovery_controls":{"cpu_seconds":5,"wall_seconds":10,"read_bytes":4*MIB,"write_bytes":2*MIB},
 "recovery_metadata_constructors":{"invocations":4,"cpu_seconds":40,"wall_seconds":80,"family_bytes":32*MIB},
 "recovery_control_capture":{"cpu_seconds":5,"overhead_wall_seconds":10,"full_outer_wall_seconds":20,"read_bytes":1*MIB,"write_bytes":1*MIB},
 "unvisited_render":{"cpu_seconds":180,"wall_seconds":240,"file_bytes":128*MIB},
 "unvisited_verify":{"cpu_seconds":60,"wall_seconds":120,"file_bytes":19*MIB},
 "scope":"All earlier metadata, scanner-control, wrapper, review and failed-stage reservations remain with their original records. No whole-program sum or refund is inferred."}

def need(v,message):
    if not v:raise ValueError(message)

def encoded(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def exact(a,b):return encoded(a)==encoded(b)
def map_sha(value):return digest(encoded(value))

def strict(raw):
    def pairs(rows):
        out={}
        for k,v in rows:
            need(k not in out,"duplicate metadata key");out[k]=v
        return out
    v=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,"nonfinite metadata"))
    def finite(x):
        if type(x) is float:need(math.isfinite(x),"nonfinite metadata")
        elif type(x) is dict:
            for y in x.values():finite(y)
        elif type(x) is list:
            for y in x:finite(y)
    finite(v);return v

def ref_shape(ref,empty=False):
    return (type(ref) is dict and set(ref)=={"path","bytes","sha256"}
            and type(ref["path"]) is str and type(ref["bytes"]) is int
            and (0 if empty else 1)<=ref["bytes"]<=64*MIB
            and type(ref["sha256"]) is str and re.fullmatch("[0-9a-f]{64}",ref["sha256"]) is not None)

def association_path(name):
    need(type(name) is str and 0<len(name)<=32768 and "\0" not in name,"typed association path")
    if name.startswith("\\\\?\\"):
        name=name[4:]
        need(re.match(r"^[A-Za-z]:\\",name) is not None,"supported verbatim local-drive path")
    need(not name.startswith(("\\\\","//","\\")),"no device or UNC association")
    local=name.replace("/","\\")
    drive=len(local)>=2 and local[1]==":"
    if drive:
        need(re.match(r"^[A-Za-z]:\\",local) is not None,"absolute local-drive association")
        components=local[3:].split("\\")
    else:components=local.split("\\")
    need(all(part and part not in (".","..") and not part.endswith(("."," "))
             and not any(c in part for c in ':<>"|?*') for part in components),
         "canonical association components")
    p=Path(name);p=p if p.is_absolute() else ROOT/p
    need(p.is_relative_to(ROOT),"repository association containment")
    for q in (p,*p.parents):
        s=q.lstat()
        need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain association ancestry")
    resolved=p.resolve(strict=True)
    need(resolved.is_relative_to(ROOT),"resolved repository association containment")
    return resolved

def legacy_same_ref(a,b):
    return (ref_shape(a) and ref_shape(b)
            and association_path(a["path"])==association_path(b["path"])
            and a["bytes"]==b["bytes"] and a["sha256"]==b["sha256"])

def read_bound(path,cap,expected=None,empty=False):
    p=Path(os.path.abspath(path))
    for q in (p,*p.parents):
        s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain source ancestry")
    before=p.stat();need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,"bounded source extent")
    with p.open("rb") as f:
        opened=os.fstat(f.fileno());raw=f.read(cap+1);after=os.fstat(f.fileno())
    final=p.stat()
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0))
    full=lambda s:shared(s)+(s.st_ctime_ns,)
    need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
         and len(raw)==before.st_size and len(raw)<=cap,"same authenticated source buffer")
    try:name=p.relative_to(ROOT).as_posix()
    except ValueError:name=str(p)
    ref=dict(path=name,bytes=len(raw),sha256=digest(raw))
    if expected is not None:
        need(ref_shape(expected,empty) and exact(ref,expected),"literal held file identity")
    return raw,ref

def producer_sources():
    raw,_=read_bound(ROOT/HISTORY["producer_freeze"]["path"],64*KIB,HISTORY["producer_freeze"])
    v=strict(raw)
    need(v["schema"]=="common-tiff-dimensions-root-source-freeze-v2"
         and type(v["source_bindings"]) is dict and len(v["source_bindings"])==190,"literal original190 source map")
    return v["source_bindings"]

def extension(producer,current):
    extras={(HERE/name).relative_to(ROOT).as_posix() for name in EXTRAS}
    need(type(producer) is dict and len(producer)==190 and type(current) is dict
         and set(current)==set(producer)|extras and not set(producer)&extras,"original190 plus closed ten-source extension")
    need(all(exact(current[k],v) for k,v in producer.items()),"unchanged original190 source identities")
    total=0
    for k,v in current.items():
        need(type(k) is str and not Path(k).is_absolute() and ".." not in Path(k).parts
             and type(v) is dict and set(v)=={"bytes","sha256"}
             and type(v["bytes"]) is int and 0<v["bytes"]<=4*MIB
             and type(v["sha256"]) is str and re.fullmatch("[0-9a-f]{64}",v["sha256"]) is not None,"positive bounded source extension")
        total+=v["bytes"]
    need(total<=16*MIB,"source extension aggregate")
    return True

def make_fixture_reader(producer,raw):
    tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="fixture_read"]
    need(len(nodes)==1,"one held fixture reader")
    original=nodes[0];candidate=copy.deepcopy(original);hits=[]
    for n in ast.walk(candidate):
        if (isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="same_ref"
            and isinstance(n.func.value,ast.Name) and n.func.value.id=="d"
            and len(n.args)==2 and isinstance(n.args[0],ast.Subscript)
            and isinstance(n.args[0].value,ast.Name) and n.args[0].value.id=="old"):
            role=n.args[0].slice.value if isinstance(n.args[0].slice,ast.Constant) else None
            need(role in ("manifest","output") and ast.dump(n.args[1],include_attributes=False)==
                 ast.dump(ast.parse(f'legacy["{role}"]',mode="eval").body,include_attributes=False),"exact legacy association operands")
            hits.append(role);n.func=ast.Name(id="legacy_same_ref",ctx=ast.Load())
    need(hits==["manifest","output"],"exact two ordered legacy callsites")
    reverse=copy.deepcopy(candidate)
    for n in ast.walk(reverse):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="legacy_same_ref":
            n.func=ast.Attribute(value=ast.Name(id="d",ctx=ast.Load()),attr="same_ref",ctx=ast.Load())
    need(ast.dump(reverse,include_attributes=False)==ast.dump(original,include_attributes=False),"whole fixture AST reversed")
    visits=[]
    def observed(a,b):
        value=legacy_same_ref(a,b)
        visits.append(dict(left=a,right=b,matched=value))
        need(len(visits)<=2,"two current-invocation legacy observations")
        return value
    namespace=dict(producer.__dict__);namespace["legacy_same_ref"]=observed
    module=ast.fix_missing_locations(ast.Module(body=[candidate],type_ignores=[]))
    exec(compile(module,str(ROOT/HISTORY["original_controller"]["path"]),"exec"),namespace)
    proof=dict(scope="Exact two visits for the current fixture-read invocation; admission retains its own immutable copy.",replaced_calls=2,original_ast_sha256=digest(ast.dump(original,include_attributes=False).encode()),
               reverse_ast_sha256=digest(ast.dump(reverse,include_attributes=False).encode()),visits=visits)
    return namespace["fixture_read"],proof

def job_cpu(record):
    need(type(record) is dict,"Job accounting object")
    for name in ("total_user_100ns","total_kernel_100ns","total_cpu_100ns","active_processes"):
        need(type(record.get(name)) is int and record[name]>=0,"typed nonnegative Job component")
    need(record["total_user_100ns"]+record["total_kernel_100ns"]==record["total_cpu_100ns"],"exact Job component total")
    return record["total_cpu_100ns"]/1e7

def admit_saved_prepare(parent,child,advert,tail,outer,exit_raw,index_ref,expected_command):
    need(parent.get("schema")=="common-tiff-dimensions-owned-stage-v1" and parent.get("stage")=="prepare"
         and parent.get("status")=="REFUSED" and parent.get("artifacts")=={} and parent.get("finalization_errors")==[]
         and type(parent.get("error")) is dict and parent["error"].get("sha256")==FAILURE_SHA,
         "exact refused preparation parent")
    need(type(expected_command) is list and expected_command and all(type(x) is str for x in expected_command)
         and exact(child.get("command"),expected_command),"exact original generator command")
    cpu=job_cpu(child.get("job_accounting"))
    need(type(child.get("exit_code")) is int and child["exit_code"]==0
         and child.get("error") is None and child.get("cleanup_errors")==[]
         and child.get("direct_exit_observed") is True and child.get("pipe_eof_observed") is True
         and child.get("post_exit_drain",{}).get("completed") is True
         and child.get("terminal_job_accounting") is True and child["job_accounting"]["active_processes"]==0
         and child.get("termination",{}).get("attempted") is False and "compile_cleanup" not in child,
         "clean successful saved generator child")
    need(advert.get("schema")=="common-tiff-dimensions-independent-preparation-v1"
         and advert.get("status")=="PREPARED_UNRUN_FIXTURES" and type(advert.get("cases")) is int and advert["cases"]==24
         and type(advert.get("generated_files")) is int and advert["generated_files"]==59
         and type(advert.get("file_bytes")) is int and advert["file_bytes"]==16025258
         and legacy_same_ref(advert.get("index"),index_ref),"saved generator advertisement")
    need(type(outer.get("exit_code")) is int and outer["exit_code"]==1 and outer.get("timeout_terminated") is False
         and exit_raw==b"1\n","refused preparation external disposition")
    need(tail.get("cpu_accounting_complete") is True and tail.get("live_child_cpu_seconds")==0
         and type(tail.get("live_child_cpu_seconds")) in (int,float)
         and tail.get("completed_child_cpu_seconds")==cpu
         and exact(tail.get("final_external_allowance"),{"cpu_seconds":2,"wall_seconds":3}),"saved preparation terminal accounting")
    for value in (tail.get("actual_parent_cpu_sample"),tail.get("whole_wall_sample"),outer.get("elapsed_wall_seconds")):
        need(type(value) in (int,float) and math.isfinite(value) and value>=0,"finite saved preparation accounting")
    need(tail["actual_parent_cpu_sample"]+cpu+2<=30
         and outer["elapsed_wall_seconds"]<=min(60,tail["whole_wall_sample"]+3),"saved preparation reserved envelope")
    return dict(original_parent_status="REFUSED",original_parent_complete=False,generator_child_exit_code=0,
                generator_child_cpu_seconds=cpu,saved_prefix_eligible=True)

ADMISSION_KEYS={"schema","status","old_prepare_status","subject_complete","producer_freeze",
 "producer_source_map_sha256","execution_source_map_sha256","compiled_source_closure","build","failed_prepare",
 "generator_child","generator_stdout","index","files","file_bytes","fixture_read_proof","controls","scope"}

def admission_association(value,index_ref,producer_freeze,producer_map,current_map,expected_files):
    extension(producer_map,current_map)
    need(type(value) is dict and set(value)==ADMISSION_KEYS and value["schema"]==ADMISSION_SCHEMA
         and value["status"]=="SAVED_FIXTURES_ADMITTED" and value["old_prepare_status"]=="REFUSED"
         and value["subject_complete"] is False,"genuine saved-fixture admission disposition")
    need(exact(value["producer_freeze"],producer_freeze) and exact(producer_freeze,HISTORY["producer_freeze"])
         and value["producer_source_map_sha256"]==map_sha(producer_map)
         and value["execution_source_map_sha256"]==map_sha(current_map)
         and exact(value["compiled_source_closure"],COMPILED),"original and execution source provenance")
    need(exact(value["build"],HISTORY["build"]) and exact(value["failed_prepare"],HISTORY["prepare"])
         and exact(value["generator_child"],HISTORY["prepare_child"])
         and exact(value["generator_stdout"],HISTORY["prepare_log"]),"exact preserved build and failed preparation")
    need(exact(value["index"],index_ref) and exact(index_ref,HISTORY["index"])
         and type(expected_files) is list and len(expected_files)==59
         and all(ref_shape(ref) for ref in expected_files) and exact(value["files"],expected_files)
         and type(value["file_bytes"]) is int and value["file_bytes"]==sum(ref["bytes"] for ref in expected_files)==16025258,
         "exact saved59 fixture identity population")
    p=value["fixture_read_proof"]
    need(type(p) is dict and set(p)=={"scope","replaced_calls","original_ast_sha256","reverse_ast_sha256","visits"}
         and type(p.get("replaced_calls")) is int and p["replaced_calls"]==2
         and p["original_ast_sha256"]==p["reverse_ast_sha256"]==FIXTURE_AST_SHA
         and exact(p["visits"],LEGACY_ASSOCIATIONS),"actual ordered two-callsite fixture proof")
    need(type(value["controls"]) is dict and set(value["controls"])=={"result","outer","stdout","stderr","exit"}
         and all(ref_shape(v,empty=(k=="stderr")) for k,v in value["controls"].items()),"complete recovery control evidence refs")
    return True
