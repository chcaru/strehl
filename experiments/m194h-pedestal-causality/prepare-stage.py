"""Root's fixed M194h metadata constructor. No build, test or image computation.
Corrected invocation per stage, cumulative including first refusal <=40 CPU/80 wall/8 MiB.
"""
from pathlib import Path
import hashlib,json,os,re,shutil,sys,time
START=time.monotonic()
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORK=HERE/"work"
PY=Path(r"C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe")
FEATURE="m194h-pedestal-causality"
CORE_TEST="pyramid::m194h::controls::fixed_threshold_null_and_observer_controls"
CLI_TEST="merge_cmd::known_scene_benchmark::noise_pupil_bridge::pedestal_causality::m194h_fixed_pedestal_case"
def live():
    check(time.process_time()<=9 and time.monotonic()-START<=18,"fixed preparation slice")
def check(ok,message):
    if not ok:raise ValueError(message)
def encoded(v):return (json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def read(p,cap=64<<20):
    live();p=Path(p);check(p.stat().st_size<=cap,"bounded input")
    initial=p.stat()
    with p.open("rb") as f:
        before=os.fstat(f.fileno());b=f.read(cap+1);after=os.fstat(f.fileno())
    final=p.stat()
    identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
    check(len(b)<=cap and identity(initial)==identity(final) and identity(before)==identity(after) and identity(initial)[:4]+identity(initial)[5:]==identity(before)[:4]+identity(before)[5:] and len(b)==before.st_size,"stable input")
    live()
    return b
def buffer_ref(p):
    p=Path(p).resolve();b=read(p)
    return b,dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def ref(p):return buffer_ref(p)[1]
def write(p,v):
    live()
    b=encoded(v);check(len(b)<=1<<20 and not p.exists(),"fresh bounded metadata")
    with p.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
    check(read(p)==b,"metadata readback")
    return ref(p)
def verify(r):
    b,observed=buffer_ref(ROOT/r["path"])
    check(type(r) is dict and set(r)=={"path","bytes","sha256"} and type(r["bytes"]) is int,"typed retained FileRef")
    check((ROOT/r["path"]).resolve()==(ROOT/observed["path"]).resolve() and all(r[k]==observed[k] for k in ("bytes","sha256")),"exact retained FileRef")
    return json.loads(b)
def freeze_sources():
    paths={ROOT/"Cargo.toml",ROOT/"Cargo.lock"}
    for base,dirs,files in os.walk(ROOT/"crates"):
        dirs[:]=[d for d in dirs if d not in ("target",".git")]
        for n in files:
            if n.endswith(".rs") or n=="Cargo.toml":paths.add((Path(base)/n).resolve())
    pending=[(p,ROOT/"crates"/p.relative_to(ROOT).parts[1]) for p in paths if p.suffix==".rs"]
    seen=set()
    while pending:
        p,crate=pending.pop()
        if (p,crate) in seen:continue
        seen.add((p,crate));s=read(p,4<<20).decode("utf8")
        names=re.findall(r'^\s*include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)',s,re.M)
        targets=[(crate/n.lstrip("/")).resolve() for n in names]
        targets += [(p.parent/n).resolve() for n in re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]',s,re.M)]
        for q in targets:
            check(q.is_relative_to(ROOT),"owned compiled include")
            paths.add(q);pending.append((q,crate))
        for n in re.findall(r'include_(?:str|bytes)!\(\s*"([^"]+)"\s*\)',s):
            q=(p.parent/n).resolve();check(q.is_relative_to(ROOT),"owned literal input");paths.add(q)
    for p in HERE.iterdir():
        if p.is_file() and (p.suffix in (".rs",".py",".md",".json") or p.name==".gitattributes"):paths.add(p)
    for n in ("independent-build-run-review.md","independent-root-wrapper-review.md","independent-verify.py","independent-verification-design.md",".gitattributes"):
        check(HERE/n in paths and (HERE/n).is_file(),"required final source "+n)
    for n in ("experiments/m193c-output-grid/bounded-process.py","experiments/m12-scorecard/m12-harness.py",
              "experiments/m194g-larger-pupil/independent-quality-result-check.py",
              "experiments/m194g-larger-pupil/work/pedestal-sparse-error-causal-proposal.md"):
        paths.add(ROOT/n)
    out={}
    for p in sorted(paths):
        r=ref(p);check(0<r["bytes"]<=4<<20,"positive source extent")
        out[r["path"]]={k:r[k] for k in ("bytes","sha256")}
    check(sum(v["bytes"] for v in out.values())<=16<<20,"source aggregate")
    return out
def bundle(stage):
    base=HERE/("subject-1" if stage=="render" else stage+"-1")
    stem=WORK/(stage+"-external-1")
    out={k:ref(p) for k,p in (
        ("result",base/"result.json"),("tail",base/"parent-tail.json"),
        ("outer",Path(str(stem)+"-outer.json")),("stdout",Path(str(stem)+"-stdout.bin")),
        ("stderr",Path(str(stem)+"-stderr.bin")),("exit",Path(str(stem)+"-exit.txt")))}
    value=verify(out["result"]);outer=verify(out["outer"])
    check(value["status"]=="COMPLETE_STAGE_UNVERIFIED" and outer["exit_code"]==0 and not outer["timeout_terminated"],"successful actual prerequisite")
    return out
def main():
    stage=sys.argv[1];check(stage in ("build","components","render"),"fixed stage")
    check(Path.cwd().resolve()==ROOT and Path(sys.executable).resolve()==PY and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"fixed metadata process")
    WORK.mkdir(exist_ok=True)
    history=json.loads(read(WORK/"build-preparation-1.json"))
    check(history["status"]=="REFUSED" and history["charged_cpu_seconds"]==10 and history["charged_wall_seconds"]==20,"retained first preparation refusal")
    prior=[]
    for s in ("build","components","render"):
        p=WORK/(s+"-preparation-2.json")
        if p.exists() and s!=stage:prior.append(json.loads(read(p)))
    check(len(prior)==("build","components","render").index(stage),"once-only ordered preparation")
    check(all(r["status"]=="PASS_METADATA_PREPARATION" for r in prior),"successful previous preparation")
    sources=freeze_sources()
    closure=WORK/"source-freeze-1.json"
    if stage=="build":write(closure,dict(schema="m194h-root-source-freeze-v1",source_bindings=sources,scope="Exact working bytes used by the owned build; immutable through these three stages."))
    else:check(json.loads(read(closure))["source_bindings"]==sources,"held source unchanged")
    target=ROOT/"target/m194h-pedestal-causality-1"
    inputs=[ref(PY)]
    binaries={};prerequisites={}
    if stage=="build":
        check(not target.exists() and not (HERE/"build-1").exists(),"fresh build")
        inputs += [ref(Path(shutil.which(n))) for n in ("cargo","rustc")]
        base=["cargo","test"]
        children=[base+["-p","strehl-core","--lib","--features",FEATURE,"--target-dir",str(target),"--no-run","--message-format=json-render-diagnostics","--locked","--offline"],
          base+["-p","strehl-cli","--bin","strehl","--features",FEATURE,"--target-dir",str(target),"--no-run","--message-format=json-render-diagnostics","--locked","--offline"],
          [str(HERE/"build-1/core-tests.exe"),"--list"],[str(HERE/"build-1/cli-tests.exe"),"--list"]]
    else:
        prerequisites["build"]=bundle("build")
        built=verify(prerequisites["build"]["result"])
        for k in ("core","cli"):
            original=built["artifacts"][k]["binary"];observed=ref(ROOT/original["path"])
            check(all(original[f]==observed[f] for f in ("bytes","sha256")),"built binary unchanged")
            binaries[k]=observed
        key="core" if stage=="components" else "cli";test=CORE_TEST if stage=="components" else CLI_TEST
        command=[str((ROOT/binaries[key]["path"]).resolve()),"--exact",test,"--ignored","--test-threads=1","--nocapture"]
        children=[command] if stage=="components" else [command for _ in range(12)]
        if stage=="render":prerequisites["components"]=bundle("components")
    subject=None
    if stage=="render":
        dev=json.loads(read(HERE/"development-bindings.json"))
        cases=[]
        for i in range(12):
            seed,arm,obs=(743,("H","P","P0")[i//3],("off","on","placebo")[i%3]) if i<9 else (None,("H","P","P0")[i-9],"off")
            cases.append(dict(ordinal=i,seed=seed,arm=arm,observation=obs,output_directory=f"experiments/m194h-pedestal-causality/subject-1/case-{i:02}"))
        grant=dict(schema="m194h-pedestal-causality-release-v1",source_bindings=sources,
            noise_admission=dev["noise_admission"],matrix_index=dev["matrix"],quality_verification=dev["quality_verification"],
            binary=binaries["cli"],commands=[children[0]],cases=cases)
        for k in ("noise_admission","matrix_index","quality_verification"):verify(grant[k]);inputs.append(grant[k])
        subject=write(WORK/"subject-release-1.json",grant)
    path=WORK/(stage+"-release-1.json")
    command=[str(PY),"-I","-S","-B",str(HERE/"build-and-run.py"),"--release",str(path),"--release-sha256","ACTUAL_RELEASE_SHA256"]
    release=dict(schema="m194h-owned-stage-release-v1",stage=stage,source_bindings=sources,inputs=inputs,command=command,
                 children=children,binaries=binaries,subject_grant=subject,prerequisites=prerequisites)
    rr=write(path,release)
    check(freeze_sources()==sources,"source closure unchanged through preparation")
    cpu=history["charged_cpu_seconds"]+sum(r["charged_cpu_seconds"] for r in prior)+10
    wall=history["charged_wall_seconds"]+sum(r["charged_wall_seconds"] for r in prior)+20
    size=sum(p.stat().st_size for p in WORK.iterdir() if p.is_file())
    check(cpu<=40 and wall<=80 and size+(64<<10)<=8<<20,"cumulative metadata envelope")
    result=dict(schema="m194h-root-preparation-v1",stage=stage,release=rr,source_freeze=ref(closure),source_files=len(sources),
      source_bytes=sum(v["bytes"] for v in sources.values()),charged_cpu_seconds=10,
      charged_wall_seconds=20,actual_parent_cpu_sample=time.process_time(),actual_wall_sample=time.monotonic()-START,cumulative_cpu_seconds=cpu,cumulative_wall_seconds=wall,work_file_bytes=size,
      status="PASS_METADATA_PREPARATION",scope="Full 10 CPU/20 wall slice charged per invocation before work, including failures; live9/18 guard reserves1/2 for terminal publication. No scientific execution.")
    publish_receipt(result)
    print(json.dumps(result))
def publish_receipt(value):
    raw=encoded(value);check(len(raw)<=64<<10,"bounded preparation receipt")
    temp=WORK/(sys.argv[1]+"-preparation-stage-2.json")
    with temp.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(temp,WORK/(sys.argv[1]+"-preparation-2.json"))
if __name__=="__main__":
    stage=sys.argv[1]
    check(stage in ("build","components","render"),"stage")
    WORK.mkdir(exist_ok=True)
    receipt=WORK/(stage+"-preparation-2.json")
    check(not receipt.exists(),"fresh preparation")
    initial=dict(schema="m194h-root-preparation-v1",stage=stage,status="INITIAL_INCOMPLETE",
       charged_cpu_seconds=10,charged_wall_seconds=20,scope="Full prospective slice retained before ordinary preparation; no retry.")
    with receipt.open("xb") as f:f.write(encoded(initial));f.flush();os.fsync(f.fileno())
    try:main()
    except BaseException as e:
        initial.update(status="REFUSED",error=str(e)[:2000],actual_parent_cpu_sample=time.process_time(),actual_wall_sample=time.monotonic()-START)
        publish_receipt(initial)
        raise

