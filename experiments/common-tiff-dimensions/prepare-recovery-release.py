"""Four metadata-only additive release constructors. Never launch or decode fixtures."""
import time
START=time.monotonic();CPU=time.process_time()
from pathlib import Path
import argparse,ast,hashlib,io,json,os,re,stat,sys,types,zipfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;WORK=HERE/"work"
SELF=Path(__file__).resolve();KIB=1024;MIB=1<<20
AUTHORITY_SHA="45df35ca1ad6b47b3cea305f7f8519f76dee40d5625b7a647622ac5c822b1e3b"
H=None;CURRENT=None
STAGES=("controls","recovery","render","verify")
FREEZE=WORK/"recovery-source-freeze-1.json"
DELTA=WORK/"recovery-source-delta-1.zip"
CONTROL_BUNDLE=WORK/"recovery-controls-bundle-1.json"
READ=0

def need(value,message):
    if not value:raise ValueError(message)

def check():
    need(time.process_time()-CPU+1<=10 and time.monotonic()-START+2<=20,"one10CPU/20wall metadata slot including final allowance")

def encoded(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def read_bound(path,cap,expected=None,empty=False):
    global READ
    check();path=Path(os.path.abspath(path))
    for p in (path,*path.parents):
        s=p.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain metadata ancestry")
    before=path.stat();need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,"bounded metadata read")
    READ+=before.st_size+1;need(READ<=128*MIB,"finite metadata constructor read allowance")
    with path.open("rb") as f:
        first=os.fstat(f.fileno());raw=f.read(before.st_size+1);last=os.fstat(f.fileno())
    after=path.stat()
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0))
    full=lambda s:shared(s)+(s.st_ctime_ns,)
    need(full(before)==full(after) and full(first)==full(last) and shared(before)==shared(first)
         and len(raw)==before.st_size,"same metadata read buffer")
    try:name=path.relative_to(ROOT).as_posix()
    except ValueError:name=str(path)
    ref=dict(path=name,bytes=len(raw),sha256=digest(raw))
    if expected is not None:
        need(type(expected) is dict and set(expected)=={"path","bytes","sha256"}
             and type(expected["bytes"]) is int and expected["bytes"]==len(raw)
             and type(expected["sha256"]) is str and expected["sha256"]==ref["sha256"]
             and type(expected["path"]) is str and
             Path(os.path.abspath(ROOT/expected["path"]))==path,"literal retained metadata identity")
    return raw,ref

def write(path,value,cap=128*KIB,replace=False,transport=False):
    global READ
    if not transport:check()
    raw=encoded(value);need(len(raw)<=cap,"finite metadata publication")
    stage=Path(str(path)+".stage") if replace else path
    with stage.open("xb") as f:
        need(f.write(raw)==len(raw),"whole metadata write");f.flush();os.fsync(f.fileno())
    # Final transport still uses bounded same-byte readback, independently of admission.
    if transport:
        READ+=len(raw)+1;need(READ<=128*MIB,"terminal read within constructor allowance")
        with stage.open("rb") as f:observed=f.read(len(raw)+1)
        need(observed==raw,"whole terminal readback")
    else:need(read_bound(stage,cap)[0]==raw,"whole metadata readback")
    if replace:os.replace(stage,path)
    return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=digest(raw))

def load_authority():
    global H
    raw,_=read_bound(HERE/"recovery-authority.py",32*KIB)
    need(digest(raw)==AUTHORITY_SHA,"held recovery authority source")
    H=types.ModuleType("common_tiff_recovery_constructor_authority");H.__file__=str(HERE/"recovery-authority.py")
    exec(compile(raw,H.__file__,"exec"),H.__dict__)
    H.read_bound=read_bound

def current_sources(old):
    paths={key:ROOT/key for key in old}
    paths.update({(HERE/name).relative_to(ROOT).as_posix():HERE/name for name in H.EXTRAS})
    extents={key:p.stat().st_size for key,p in paths.items()}
    need(len(paths)==200 and all(type(n) is int and 0<n<=4*MIB for n in extents.values())
         and sum(extents.values())<=16*MIB,"closed200 source preextent bounds")
    values={key:read_bound(path,extents[key])[1] for key,path in sorted(paths.items())}
    result={key:dict(bytes=r["bytes"],sha256=r["sha256"]) for key,r in values.items()}
    H.extension(old,result)
    need(sum(v["bytes"] for k,v in result.items() if k not in old)<=256*KIB,"closed new-source aggregate for normal admission read bound")
    return result

def member(z,key,pin):
    global READ
    item=z.getinfo(key);need(item.file_size==pin["bytes"],"archive member preextent")
    READ+=item.file_size+1;need(READ<=128*MIB,"inflated archive bytes within constructor allowance")
    b=z.read(key);need(H.exact(dict(bytes=len(b),sha256=digest(b)),pin),"exact inflated archive member")
    return b

def composed_old_sources(old):
    raw,_=read_bound(ROOT/H.HISTORY["producer_freeze"]["path"],64*KIB,H.HISTORY["producer_freeze"])
    frozen=H.strict(raw)
    base_raw,_=read_bound(ROOT/frozen["base_freeze"]["path"],64*KIB,frozen["base_freeze"])
    base=H.strict(base_raw)
    old_raw,_=read_bound(ROOT/frozen["base_archive"]["path"],16*MIB,frozen["base_archive"])
    delta_raw,_=read_bound(ROOT/frozen["delta_archive"]["path"],16*MIB,frozen["delta_archive"])
    need(H.exact(base["archive"],frozen["base_archive"]),"literal original archive association")
    with zipfile.ZipFile(io.BytesIO(old_raw)) as original,zipfile.ZipFile(io.BytesIO(delta_raw)) as delta:
        need(len(original.namelist())==len(base["source_bindings"])==181
             and set(original.namelist())==set(base["source_bindings"])
             and len(delta.namelist())==len(set(delta.namelist()))
             and delta.namelist()==frozen["changed_or_new"],"unique original compositional inventories")
        for key,pin in base["source_bindings"].items():
            item=original.getinfo(key);need(item.file_size==pin["bytes"],"original zip preextent")
            member(original,key,pin)
        for key,pin in old.items():
            z=delta if key in frozen["changed_or_new"] else original
            item=z.getinfo(key);need(item.file_size==pin["bytes"],"composed source preextent")
            member(z,key,pin)
    return frozen

def compiled_closure(sources):
    # Same finite source selection as the held reader, no Rust/import execution.
    paths={ROOT/"Cargo.toml",ROOT/"Cargo.lock",ROOT/"crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt"}
    def onerror(e):raise e
    for base,dirs,files in os.walk(ROOT/"crates",onerror=onerror):
        dirs[:]=[d for d in dirs if d not in ("target",".git")]
        for name in files:
            if name.endswith(".rs") or name=="Cargo.toml":paths.add(Path(base)/name)
    pending=[(p,ROOT/"crates"/p.relative_to(ROOT).parts[1]) for p in paths if p.suffix==".rs"]
    seen=set()
    while pending:
        p,crate=pending.pop()
        if (p,crate) in seen:continue
        seen.add((p,crate));key=p.relative_to(ROOT).as_posix()
        need(key in sources,"compiled source admitted")
        raw,_=read_bound(p,4*MIB,dict(path=key,**sources[key]))
        text=raw.decode("utf8")
        names=re.findall(r'^\s*include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)',text,re.M)
        targets=[Path(os.path.abspath(crate/name.lstrip("/"))) for name in names]
        targets += [Path(os.path.abspath(p.parent/name)) for name in re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]',text,re.M)]
        for q in targets:paths.add(q);pending.append((q,crate))
    closure={p.relative_to(ROOT).as_posix():sources[p.relative_to(ROOT).as_posix()] for p in sorted(paths)}
    value=dict(files=len(paths),canonical_sha256=digest(encoded(closure)))
    need(H.exact(value,H.COMPILED),"fresh current compiled118 equals actual successful build")
    return value

def freeze_sources(old,current,stage):
    if stage=="controls":
        need(not FREEZE.exists() and not DELTA.exists(),"fresh additive source freeze")
        composed_old_sources(old)
        keys=sorted(set(current)-set(old));need(len(keys)==10,"ten new operational sources only")
        with zipfile.ZipFile(DELTA,"x",compression=zipfile.ZIP_STORED) as z:
            for key in keys:
                raw,_=read_bound(ROOT/key,4*MIB,dict(path=key,**current[key]));z.writestr(key,raw)
        raw,ref=read_bound(DELTA,4*MIB)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            need(z.namelist()==keys,"unique exact additive archive")
            for key in keys:
                need(z.getinfo(key).file_size==current[key]["bytes"],"new zip preextent")
                member(z,key,current[key])
        value=dict(schema="common-tiff-dimensions-recovery-source-freeze-v1",
                   producer_freeze=H.HISTORY["producer_freeze"],source_bindings=current,delta_archive=ref)
        write(FREEZE,value)
    else:
        raw,_=read_bound(FREEZE,128*KIB);value=H.strict(raw)
        need(set(value)=={"schema","producer_freeze","source_bindings","delta_archive"}
             and value["schema"]=="common-tiff-dimensions-recovery-source-freeze-v1"
             and H.exact(value["source_bindings"],current)
             and H.exact(value["producer_freeze"],H.HISTORY["producer_freeze"]),"unchanged additive freeze")
        read_bound(ROOT/value["delta_archive"]["path"],4*MIB,value["delta_archive"])
    return read_bound(FREEZE,128*KIB)[1]

def historical_metadata(old):
    saved={}
    for stage in ("build","prepare"):
        buffers={role:read_bound(ROOT/r["path"],r["bytes"],r,empty=r["bytes"]==0)[0]
                 for role,r in H.HISTORY[stage].items()}
        result,outer,tail=(H.strict(buffers[k]) for k in ("result","outer","tail"))
        need(result["schema"]=="common-tiff-dimensions-owned-stage-v1" and result["stage"]==stage
             and H.exact(result["compiled_source_closure"],H.COMPILED),"literal historical stage/compiled closure")
        need(result["status"]==("COMPLETE_STAGE_UNVERIFIED" if stage=="build" else "REFUSED")
             and outer["exit_code"]==(0 if stage=="build" else 1)
             and outer["timeout_terminated"] is False,"preserved historical dispositions")
        rr=H.HISTORY[stage+"_release"];release=H.strict(read_bound(ROOT/rr["path"],64*KIB,rr)[0])
        need(H.exact(release["source_bindings"],old) and H.legacy_same_ref(result["release"],rr),
             "historical original190 authority")
        saved[stage]=(result,release)
    child=H.strict(read_bound(ROOT/H.HISTORY["prepare_child"]["path"],32*KIB,H.HISTORY["prepare_child"])[0])
    advert=H.strict(read_bound(ROOT/H.HISTORY["prepare_log"]["path"],32*KIB,H.HISTORY["prepare_log"])[0])
    H.admit_saved_prepare(saved["prepare"][0],child,advert,
      H.strict(read_bound(ROOT/H.HISTORY["prepare"]["tail"]["path"],8*KIB,H.HISTORY["prepare"]["tail"])[0]),
      H.strict(read_bound(ROOT/H.HISTORY["prepare"]["outer"]["path"],64*KIB,H.HISTORY["prepare"]["outer"])[0]),
      b"1\n",H.HISTORY["index"],saved["prepare"][1]["children"][0]["command"])
    return saved

def bundle(stage):
    paths={"result":HERE/f"{stage}-1/result.json","tail":HERE/f"{stage}-1/parent-tail.json"}
    paths.update({k:WORK/f"{stage}-recovery-external-1-{s}" for k,s in
                  (("outer","outer.json"),("stdout","stdout.bin"),("stderr","stderr.bin"),("exit","exit.txt"))})
    caps={"result":256*KIB,"tail":8*KIB,"outer":64*KIB,"stdout":8*KIB,"stderr":32*KIB,"exit":KIB}
    actual={k:read_bound(p,caps[k],empty=k=="stderr") for k,p in paths.items()}
    refs={k:r for k,(_,r) in actual.items()};raw={k:b for k,(b,_) in actual.items()}
    result,tail,outer,advert=(H.strict(raw[k]) for k in ("result","tail","outer","stdout"))
    need(result["schema"]=="common-tiff-dimensions-owned-stage-v2" and result["stage"]==stage
         and result["status"]=="COMPLETE_STAGE_UNVERIFIED" and result["error"] is None
         and result["finalization_errors"]==[],"genuine completed recovery prerequisite")
    need(outer["schema"]=="common-tiff-dimensions-stage-external-v2" and type(outer["exit_code"]) is int
         and outer["exit_code"]==0 and outer["timeout_terminated"] is False and raw["exit"]==b"0\n",
         "actual completed recovery outer")
    need(H.legacy_same_ref(outer["source"],dict(path=SELF.with_name("run-recovery-stage.py").relative_to(ROOT).as_posix(),
                                              **CURRENT[SELF.with_name("run-recovery-stage.py").relative_to(ROOT).as_posix()])),
         "current executed recovery source")
    for role in ("stdout","stderr","exit"):need(H.exact(outer[role],refs[role]),"recovery raw outer association")
    need(raw["stdout"]==encoded(advert) and set(advert)=={"status","result","tail"}
         and advert["status"]==result["status"] and H.legacy_same_ref(advert["result"],refs["result"])
         and H.legacy_same_ref(advert["tail"],refs["tail"]),"complete raw advertisement")
    rr=result["release"];release=H.strict(read_bound(ROOT/rr["path"],128*KIB,rr)[0])
    need(release["schema"]=="common-tiff-dimensions-stage-release-v2" and release["stage"]==stage
         and H.exact(release["source_bindings"],CURRENT)
         and result["invocation"]==outer["command"]==
             [rr["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in release["command"]],
         "same execution namespace and command")
    need(tail["schema"]=="common-tiff-dimensions-parent-tail-v2" and H.legacy_same_ref(tail["result"],refs["result"])
         and tail["cpu_accounting_complete"] is True and tail["live_child_cpu_seconds"]==0
         and tail["final_external_allowance"]==dict(cpu_seconds=2,wall_seconds=3),"complete recovery accounting")
    cpu,wall=(10,20) if stage=="recovery" else (180,240)
    need(all(type(tail[k]) in (int,float) and 0<=tail[k]<1e9 for k in
             ("actual_parent_cpu_sample","completed_child_cpu_seconds","whole_wall_sample"))
         and tail["actual_parent_cpu_sample"]+tail["completed_child_cpu_seconds"]+2<=cpu
         and type(outer["elapsed_wall_seconds"]) in (int,float) and 0<=outer["elapsed_wall_seconds"]<=wall
         and outer["elapsed_wall_seconds"]<=tail["whole_wall_sample"]+3
         and H.exact(result["compiled_source_closure"],H.COMPILED),"finite actual recovery prerequisite")
    return refs,result

def controls_bundle():
    paths={"result":WORK/"recovery-controls-1/result.json"}
    paths.update({k:WORK/f"controls-recovery-external-1-{s}" for k,s in
                  (("outer","outer.json"),("stdout","stdout.bin"),("stderr","stderr.bin"),("exit","exit.txt"))})
    caps={"result":128*KIB,"outer":64*KIB,"stdout":128*KIB,"stderr":16*KIB,"exit":KIB}
    actual={k:read_bound(p,caps[k],empty=k=="stderr") for k,p in paths.items()}
    refs={k:r for k,(_,r) in actual.items()};raw={k:b for k,(b,_) in actual.items()}
    value=H.strict(raw["result"]);outer=H.strict(raw["outer"])
    need(raw["result"]==raw["stdout"] and raw["stderr"]==b"" and raw["exit"]==b"0\n"
         and value["status"]=="PASS_FIXED_RECOVERY_METADATA_CONTROLS" and value["controls_complete"] is True
         and value["groups"]==value["completed_groups"]==40 and outer["exit_code"]==0
         and outer["timeout_terminated"] is False and 0<=outer["elapsed_wall_seconds"]<=10,
         "saved actual independent controls")
    source=HERE/"recovery-controls.py";key=source.relative_to(ROOT).as_posix()
    controlraw,_=read_bound(source,128*KIB,dict(path=key,**CURRENT[key]))
    tree=ast.parse(controlraw);decl=[n for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=="IDS" for t in n.targets)]
    need(len(decl)==1,"one fixed controls population")
    ids=ast.literal_eval(decl[0].value)
    need(type(ids) is tuple and len(ids)==len(set(ids))==40 and type(value["rows"]) is list
         and len(value["rows"])==40 and [r["id"] for r in value["rows"]]==list(ids)
         and all(set(r)=={"id","passed","details"} and r["passed"] is True for r in value["rows"])
         and value["error"] is None,"complete actual fixed40 controls")
    command=[str(Path(sys.executable)),"-I","-S","-B",str(source),"--source-sha256",CURRENT[key]["sha256"],
             "--output",str(WORK/"recovery-controls-1")]
    need(value["schema"]=="common-tiff-dimensions-recovery-controls-v1"
         and H.legacy_same_ref(value["source"],dict(path=key,**CURRENT[key]))
         and value["invocation"]==outer["command"]==command
         and outer["schema"]=="common-tiff-dimensions-recovery-controls-external-v1"
         and H.legacy_same_ref(outer["source"],value["source"]),"actual controls source and command")
    ca=outer["capture_accounting"]
    need(set(ca)=={"parent_cpu_sample","whole_wall_sample","publication_allowance","reserved","admitted","error","scope"}
         and ca["admitted"] is True and ca["error"] is None
         and H.exact(ca["publication_allowance"],dict(cpu_seconds=1,wall_seconds=2))
         and H.exact(ca["reserved"],dict(cpu_seconds=5,overhead_wall_seconds=10,whole_wall_seconds=20))
         and type(ca["parent_cpu_sample"]) in (int,float) and 0<=ca["parent_cpu_sample"]+1<=5
         and type(ca["whole_wall_sample"]) in (int,float)
         and outer["elapsed_wall_seconds"]<=ca["whole_wall_sample"] and ca["whole_wall_sample"]+2<=20
         and ca["whole_wall_sample"]-outer["elapsed_wall_seconds"]+2<=10,"bounded controls capture")
    for role in ("stdout","stderr","exit"):need(H.exact(outer[role],refs[role]),"control raw outer association")
    return refs

def main():
    global CURRENT
    parser=argparse.ArgumentParser();parser.add_argument("stage",choices=STAGES);args=parser.parse_args();stage=args.stage
    need(os.name=="nt" and Path.cwd().resolve()==ROOT and sys.flags.isolated and sys.flags.no_site
         and sys.dont_write_bytecode,"isolated Windows metadata constructor")
    need(WORK.is_dir(),"existing work directory")
    receipt=WORK/f"{stage}-recovery-preparation-1.json";release=WORK/f"{stage}-recovery-release-1.json"
    need(not receipt.exists() and not release.exists(),"fresh once-only metadata slot")
    record=dict(schema="common-tiff-dimensions-recovery-preparation-v1",status="INITIAL_INCOMPLETE",stage=stage,
        charged_cpu_seconds=10,charged_wall_seconds=20,release=None,error=None,
        scope="One nonrefundable metadata constructor slot; no compile, generator, controls, product or numerical execution.")
    write(receipt,record)
    code=1
    try:
        load_authority();old=H.producer_sources();CURRENT=current_sources(old);closure=compiled_closure(CURRENT)
        frozen_ref=freeze_sources(old,CURRENT,stage);prior=historical_metadata(old)
        # No binary/TIFF payload reads here: exact already-verified references are carried.
        py=str(Path(sys.executable));inputs=[read_bound(py,MIB)[1],
            read_bound(ROOT/"experiments/M165-common-input/linear-prophoto-d50-v1.icc",16*KIB)[1],
            H.HISTORY["producer_freeze"],frozen_ref]
        if stage=="controls":
            source=HERE/"recovery-controls.py";sha=CURRENT[source.relative_to(ROOT).as_posix()]["sha256"]
            command=[py,"-I","-S","-B",str(source),"--source-sha256",sha,"--output",str(WORK/"recovery-controls-1")]
            value=dict(schema="common-tiff-dimensions-recovery-controls-release-v1",source_bindings=CURRENT,inputs=inputs,command=command)
            need(not (WORK/"recovery-controls-1").exists(),"unvisited controls")
        else:
            if stage=="recovery":
                cb=controls_bundle();cb_ref=write(CONTROL_BUNDLE,cb,16*KIB)
            else:
                raw,cb_ref=read_bound(CONTROL_BUNDLE,16*KIB);cb=H.strict(raw)
                need(H.exact(cb,controls_bundle()),"same actual control bundle")
            inputs.append(cb_ref)
            prereq=dict(build=H.HISTORY["build"],prepare=H.HISTORY["prepare"])
            if stage in ("render","verify"):
                recovered,recovered_result=bundle("recovery");prereq["recovery"]=recovered
            index=H.strict(read_bound(ROOT/H.HISTORY["index"]["path"],64*KIB,H.HISTORY["index"])[0])
            commands=[];rb=None
            if stage=="render":
                commands=[[str(H.EXE) if x=="ACTUAL_BINARY_PATH" else x for x in row["command"]] for row in index["cases"]]
                need(len(commands)==24,"fixed original24 commands")
            if stage=="verify":
                rendered,_=bundle("render");prereq["render"]=rendered
                rb=write(HERE/"render-bundle-1.json",rendered,64*KIB)
                source=HERE/"recovery-checker.py";sha=CURRENT[source.relative_to(ROOT).as_posix()]["sha256"]
                commands=[[py,"-I","-S","-B",str(source),"verify","--fixtures",str(H.INDEX),
                    "--fixtures-sha256",H.HISTORY["index"]["sha256"],"--run-bundle",str(HERE/"render-bundle-1.json"),
                    "--run-bundle-sha256",rb["sha256"],"--output",str(HERE/"verify-1/check"),"--source-sha256",sha]]
            command=[py,"-I","-S","-B",str(HERE/"run-recovery-stage.py"),"--release",str(release),
                     "--release-sha256","ACTUAL_RELEASE_SHA256"]
            value=dict(schema="common-tiff-dimensions-stage-release-v2",stage=stage,source_bindings=CURRENT,inputs=inputs,
                command=command,children=[dict(command=c,expected_exit_code=1 if stage=="render" and i>=9 else 0)
                                         for i,c in enumerate(commands)],
                executable=H.EXE_REF,fixtures=H.HISTORY["index"],run_bundle=rb,prerequisites=prereq)
            need(not (HERE/f"{stage}-1").exists(),"fresh unvisited recovery stage")
        released=write(release,value)
        need(H.exact(current_sources(old),CURRENT),"all200 source buffers stable after construction")
        check();need(READ+128*KIB+1<=128*MIB,"constructor final read reserve")
        need(sum(p.stat().st_size for p in WORK.rglob("*") if p.is_file())<=32*MIB,"retained32MiB metadata family")
        record.update(status="PREPARED_UNRUN_RELEASE",release=released,source_freeze=frozen_ref,
            source_entries=len(CURRENT),compiled_source_closure=closure,reservations=H.RESERVATIONS,
            actual_parent_cpu_sample=time.process_time()-CPU,whole_wall_sample=time.monotonic()-START,
            read_bytes_sample=READ,final_read_allowance=128*KIB+1,final_allowance=dict(cpu_seconds=1,wall_seconds=2))
        code=0
    except Exception as e:
        record.update(status="REFUSED",error=dict(type=type(e).__name__,message=str(e)[:2048]),
                      actual_parent_cpu_sample=time.process_time()-CPU,whole_wall_sample=time.monotonic()-START)
    # One bounded final transport; a refused constructor never authorizes a child.
    write(receipt,record,128*KIB,replace=True,transport=True)
    out=encoded(record);need(len(out)<=128*KIB,"metadata stdout bound")
    need(sys.stdout.buffer.write(out)==len(out),"whole metadata stdout");sys.stdout.buffer.flush()
    return code
if __name__=="__main__":raise SystemExit(main())
