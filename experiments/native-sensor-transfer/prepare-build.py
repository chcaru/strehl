"""Root metadata-only constructor for the two fixed fresh native diagnostic builds.
No candidate import, compiler, RAW hash/decode or numerical control is executed.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,stat,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORK=HERE/"work"
START=time.monotonic()
READ=0
WRITE=0
MIB=1<<20
def need(v,s):
    if not v:raise ValueError(s)
def check():
    need(time.process_time()+1<=30 and time.monotonic()-START+2<=60,"metadata slice plus publication reserve")
    need(READ<=128*MIB and WRITE<=24*MIB,"metadata read/write allocation")
def read(p,cap=4*MIB,empty=False):
    global READ
    p=Path(os.path.abspath(p))
    for q in (p,*p.parents):
        s=q.lstat()
        need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain source ancestry")
    before=p.stat()
    need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,"bounded source extent")
    check();need(READ+before.st_size+1<=128*MIB,"read reservation")
    with p.open("rb") as f:
        opened=os.fstat(f.fileno());b=f.read(before.st_size+1);after=os.fstat(f.fileno())
    READ+=len(b)
    final=p.stat()
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0))
    full=lambda s:shared(s)+(s.st_ctime_ns,)
    need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
         and len(b)==before.st_size,"same authenticated source bytes")
    check();return b
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def ref(p,b):
    p=Path(os.path.abspath(p))
    return dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),**pin(b))
def publish(p,value):
    global WRITE
    b=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
    need(len(b)<=MIB and WRITE+len(b)<=24*MIB,"metadata publication extent")
    with p.open("xb") as f:need(f.write(b)==len(b),"full fresh metadata write")
    WRITE+=len(b)
    need(read(p,MIB)==b,"metadata readback");return ref(p,b)
def sources():
    paths={ROOT/"Cargo.toml",ROOT/"Cargo.lock",ROOT/"crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt"}
    for base,dirs,files in os.walk(ROOT/"crates"):
        dirs[:]=[n for n in dirs if n not in ("target",".git")]
        for name in files:
            if name.endswith(".rs") or name=="Cargo.toml":paths.add((Path(base)/name).resolve())
    pending=[(p,ROOT/"crates"/p.relative_to(ROOT).parts[1]) for p in paths if p.suffix==".rs"]
    buffers={};seen=set()
    while pending:
        p,crate=pending.pop()
        if (p,crate) in seen:continue
        seen.add((p,crate));b=buffers.setdefault(p,read(p));text=b.decode("utf8")
        names=re.findall(r'^\s*include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)',text,re.M)
        targets=[(crate/n.lstrip("/")).resolve() for n in names]
        targets += [(p.parent/n).resolve() for n in re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]',text,re.M)]
        for target in targets:
            need(target.is_relative_to(ROOT),"repository literal include")
            paths.add(target);pending.append((target,crate))
    local=("run-stage.py","bounded-build-process.py","capture-stage.py","run-stage-contract.md","run-stage-source-review.md",
           "charter.md","scope-amendment-2.md","scope-amendment-3.md","source/implementation-contract.md",
           "source/native-adapter.rs","source/core-hook.rs","producer-source-review.md","prepare-build.py","input-bindings-1.json")
    paths.update(HERE/n for n in local)
    paths.update(ROOT/n for n in ("experiments/m194h-pedestal-causality/build-and-run.py",
        "experiments/m193c-output-grid/bounded-process.py","experiments/m12-scorecard/m12-harness.py",
        "experiments/common-tiff-dimensions/scratch-scan.py"))
    need(len(paths)<=512,"bounded source population")
    for p in paths:
        if p not in buffers:buffers[p]=read(p)
    out={p.relative_to(ROOT).as_posix():pin(buffers[p]) for p in sorted(paths)}
    need(sum(v["bytes"] for v in out.values())<=16*MIB,"source aggregate")
    return out,buffers
def bundle(stage):
    attempt=3 if stage=="build-on" else 1
    output=HERE/(stage+"-"+str(attempt));stem=WORK/(stage+"-external-"+str(attempt)+"-")
    paths={"result":output/"result.json","tail":output/"parent-tail.json",
           "outer":Path(str(stem)+"outer.json"),"stdout":Path(str(stem)+"stdout.bin"),
           "stderr":Path(str(stem)+"stderr.bin"),"exit":Path(str(stem)+"exit.txt")}
    data={k:read(p,256<<10,empty=k=="stderr") for k,p in paths.items()}
    value={k:ref(paths[k],b) for k,b in data.items()}
    result=json.loads(data["result"]);outer=json.loads(data["outer"])
    need(result["status"]=="COMPLETE_STAGE_UNVERIFIED" and result["error"] is None
         and not result["finalization_errors"],"completed previous build")
    need(outer["exit_code"]==0 and outer["timeout_terminated"] is False and data["exit"]==b"0\n","actual prior zero exit")
    return value,result
def main():
    global WRITE,READ
    parser=argparse.ArgumentParser();parser.add_argument("stage",choices=("build-on","build-off"));args=parser.parse_args();stage=args.stage
    need(os.name=="nt" and Path.cwd().resolve()==ROOT,"fixed Windows repository")
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"isolated metadata-only constructor")
    WORK.mkdir(exist_ok=True)
    attempt=3 if stage=="build-on" else 1
    release=WORK/(stage+"-release-"+str(attempt)+".json")
    target=ROOT/("target/native-sensor-transfer-"+stage.removeprefix("build-")+"-"+str(attempt))
    need(not release.exists() and not target.exists() and not (HERE/(stage+"-"+str(attempt))).exists(),"fresh fixed stage")
    current,buffers=sources();freeze=WORK/"build-source-freeze-3.json";archive=WORK/"build-source-3.zip"
    if stage=="build-on":
        need(not freeze.exists() and not archive.exists(),"fresh source preservation")
        need(WRITE+17*MIB<=24*MIB,"reserve full bounded stored archive before creation")
        with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_STORED) as z:
            for k in current:z.writestr(k,buffers[ROOT/k])
        WRITE+=archive.stat().st_size;check()
        archive_raw=read(archive,17*MIB)
        with zipfile.ZipFile(archive,"r") as z:
            need(z.namelist()==list(current),"exact archive names")
            for k,p in current.items():
                size=z.getinfo(k).file_size
                need(size==p["bytes"] and READ+size<=128*MIB,"reserve exact archived member before inflate")
                member=z.read(k);READ+=len(member);check()
                need(pin(member)==p,"exact retained source buffer")
        freeze_ref=publish(freeze,dict(schema="native-sensor-transfer-build-source-freeze-v1",source_bindings=current,archive=ref(archive,archive_raw)))
    else:
        held=read(freeze,MIB);fv=json.loads(held);freeze_ref=ref(freeze,held)
        need(fv["schema"]=="native-sensor-transfer-build-source-freeze-v1" and fv["source_bindings"]==current,"unchanged build source")
        ar=read(ROOT/fv["archive"]["path"],17*MIB);need(ref(ROOT/fv["archive"]["path"],ar)==fv["archive"],"unchanged source archive")
    prior={};binaries={}
    if stage=="build-off":
        prior["build-on"],value=bundle("build-on");binaries["feature_on"]=value["artifacts"]["executable"]
    py=str(Path(sys.executable))
    inputs=[ref(py,read(py,64*MIB))]
    for name in ("cargo","rustc"):
        actual=shutil.which(name);need(actual,"actual compiler launcher path")
        inputs.append(ref(actual,read(actual,64*MIB)))
    binding=read(HERE/"input-bindings-1.json",16<<10)
    need(pin(binding)==dict(bytes=7119,sha256="ab4017907d5ff243ca36883a9e5ff7335717c4f7da4678b01eacab98b3d98b4a"),"held original identity receipt")
    originals=json.loads(binding)["originals"]
    command=["cargo","test","-p","strehl-cli","--bin","strehl","--no-run"]
    if stage=="build-on":command+=["--features","native-sensor-transfer"]
    command+=["--jobs","2","--target-dir",str(target),"--message-format=json-render-diagnostics","--locked","--offline"]
    value=dict(schema="native-sensor-transfer-stage-release-v1",stage=stage,source_bindings=current,inputs=inputs,originals=originals,
       command=[py,"-I","-S","-B",str(HERE/"run-stage.py"),"--release",str(release),"--release-sha256","ACTUAL_RELEASE_SHA256"],
       children=[dict(command=command,expected_exit_code=0)],binaries=binaries,reader_release=None,prerequisites=prior)
    released=publish(release,value);check()
    record=dict(schema="native-sensor-transfer-build-preparation-v1",stage=stage,release=released,source_freeze=freeze_ref,
        source_files=len(current),source_bytes=sum(v["bytes"] for v in current.values()),
        invocation=sys.orig_argv,cpu_sample=time.process_time(),active_wall_sample=time.monotonic()-START,
        read_bytes_sample=READ,write_bytes_sample=WRITE,
        allocation=dict(cpu_seconds=30,wall_seconds=60,read_bytes=128*MIB,write_bytes=24*MIB,publication_reserve_cpu_seconds=1,publication_reserve_wall_seconds=2),
        scope="Metadata and source/tool identity only. No RAW payload read/decode, product, compiler, control or checker invocation.")
    receipt=publish(WORK/(stage+"-preparation-"+str(attempt)+".json"),record)
    print(json.dumps(dict(release=released,preparation=receipt,source_files=len(current))),flush=True)
if __name__=="__main__":main()
