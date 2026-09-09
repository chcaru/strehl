"""Root metadata-only release constructor; never launches a product or checker."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,time,os,stat
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORK=HERE/"work"
BUILD_ATTEMPT=3
def attempt(stage):return BUILD_ATTEMPT if stage=="build" else 1
STAGES=("build","prepare","render","verify")
def need(v,s):
 if not v:raise ValueError(s)
def read_bound(p,cap=64<<20,empty=False):
 p=Path(os.path.abspath(p))
 for q in (p,*p.parents):
  s=q.lstat()
  need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,"plain source ancestry")
 before=p.stat()
 need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,"bounded declared extent")
 with p.open("rb") as stream:
  opened=os.fstat(stream.fileno());b=stream.read(cap+1);after=os.fstat(stream.fileno())
 final=p.stat()
 shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0))
 full=lambda s:shared(s)+(s.st_ctime_ns,)
 need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
      and len(b)==before.st_size and len(b)<=cap,"same authenticated buffer")
 return b
def raw(p,cap=64<<20):return read_bound(p,cap)
def binding(p):
 b=raw(p);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def ref(p,empty=False,b=None):
 p=Path(os.path.abspath(p));b=read_bound(p,empty=empty) if b is None else b
 try:name=p.relative_to(ROOT).as_posix()
 except ValueError:name=str(p)
 return dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,value):
 b=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
 need(len(b)<=1<<20,"metadata output cap")
 with p.open("xb") as f:f.write(b)
 return ref(p)
def source_map():
 old=json.loads(raw(ROOT/"experiments/m194h-pedestal-causality/work/source-freeze-3.json"))["source_bindings"]
 paths={ROOT/k for k in old}
 paths.update(p for p in (ROOT/"crates").rglob("*") if p.is_file() and (p.suffix==".rs" or p.name=="Cargo.toml") and "target" not in p.relative_to(ROOT/"crates").parts)
 paths.update(HERE/n for n in ("root-decision.md","source-contract.md","independent-controls-spec.md","independent-controls.py","bounded-build-process.py","run-stage.py","run-stage-contract.md","prepare-release.py","capture-stage.py","source-review.md","independent-product-source-review.md","independent-controls-ledger.json"))
 out={p.relative_to(ROOT).as_posix():binding(p) for p in sorted(paths)}
 need(len(out)<=512 and sum(v["bytes"] for v in out.values())<=16<<20,"source family cap")
 return out
def bundle(stage):
 stem=WORK/(stage+"-external-"+str(attempt(stage)))
 paths={"result":HERE/(stage+"-"+str(attempt(stage))+"/result.json"),"tail":HERE/(stage+"-"+str(attempt(stage))+"/parent-tail.json"),
        "outer":Path(str(stem)+"-outer.json"),"stdout":Path(str(stem)+"-stdout.bin"),
        "stderr":Path(str(stem)+"-stderr.bin"),"exit":Path(str(stem)+"-exit.txt")}
 buffers={k:read_bound(p,empty=(k=="stderr")) for k,p in paths.items()}
 b={k:ref(p,empty=(k=="stderr"),b=buffers[k]) for k,p in paths.items()}
 r=json.loads(buffers["result"]);o=json.loads(buffers["outer"])
 need(r["status"]=="COMPLETE_STAGE_UNVERIFIED" and r["error"] is None and not r["finalization_errors"],"completed prerequisite")
 need(o["exit_code"]==0 and o["timeout_terminated"] is False and buffers["exit"]==b"0\n","actual prior exit")
 return b,r
def main():
 started=time.monotonic();cpu_started=time.process_time()
 need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"isolated metadata-only constructor")
 need(sys.argv==[str(Path(__file__).resolve())],"exact no-argument constructor")
 old_path=WORK/"verify-release-1.json";old_raw=raw(old_path)
 need(len(old_raw)==27201 and hashlib.sha256(old_raw).hexdigest()=="aa060f5f69df6f37f24bf0dc50005377cf227aca7a9ea35eb3d1300d4ebb84a2","held original producer release")
 old=json.loads(old_raw);producer=old["source_bindings"]
 need(source_map()==producer,"all original producer sources unchanged")
 extras=("independent-controls-2.py","independent-controls-2-spec.md","run-verification-2.py","verification-2-contract.md","prepare-verification-2.py","capture-verification-2.py","verification-2-decision.md","verification-2-source-review.md")
 sources=dict(producer)
 for name in extras:
  key=(HERE/name).relative_to(ROOT).as_posix()
  need(key not in sources,"strictly added audit source")
  sources[key]=binding(HERE/name)
 need(len(sources)==164 and sum(v["bytes"] for v in sources.values())<=16<<20,"bounded exact audit closure")
 freeze=WORK/"verification-source-freeze-2.json";release=WORK/"verify-release-2.json"
 need(not freeze.exists() and not release.exists() and not (HERE/"verify-2").exists(),"fresh once-only saved verification")
 prereq={};results={}
 for previous in ("build","prepare","render"):
  prereq[previous],results[previous]=bundle(previous)
  rr=json.loads(raw(ROOT/results[previous]["release"]["path"]))
  need(rr["source_bindings"]==producer,"unchanged producer map in every prior stage")
 exe=results["build"]["artifacts"]["executable"];fixtures=results["prepare"]["artifacts"]["fixture_index"]
 rb=old["run_bundle"];need(ref(HERE/"render-bundle-1.json")==rb,"same exact saved render bundle")
 py=str(Path(sys.executable));controller=str(HERE/"run-verification-2.py");controls=str(HERE/"independent-controls-2.py")
 controlsha=sources["experiments/common-tiff-stack/independent-controls-2.py"]["sha256"]
 child=[py,"-I","-S","-B",controls,"verify","--fixtures",str(HERE/"prepare-1/fixtures/index.json"),"--fixtures-sha256",fixtures["sha256"],"--run-bundle",str(HERE/"render-bundle-1.json"),"--run-bundle-sha256",rb["sha256"],"--output",str(HERE/"verify-2/check"),"--source-sha256",controlsha]
 inputs=[ref(sys.executable),ref(ROOT/"experiments/M165-common-input/linear-prophoto-d50-v1.icc")]
 need(inputs==old["inputs"],"same held input authority")
 write(freeze,{"schema":"common-tiff-stack-verification-source-freeze-v2","producer_release":ref(old_path),"source_bindings":sources})
 value={"schema":"common-tiff-stack-stage-release-v2","stage":"verify","source_bindings":sources,"inputs":inputs,
 "command":[py,"-I","-S","-B",controller,"--release",str(release),"--release-sha256","ACTUAL_RELEASE_SHA256"],
 "children":[dict(command=child,expected_exit_code=0)],"executable":exe,"fixtures":fixtures,"run_bundle":rb,"prerequisites":prereq}
 result=write(release,value)
 cpu=time.process_time()-cpu_started;wall=time.monotonic()-started
 need(cpu+1<=5 and wall+2<=7.5,"fixed additional 5CPU/7.5activewall metadata slice")
 record={"stage":"verify","attempt":2,"release":result,"sources":len(sources),"source_bytes":sum(v["bytes"] for v in sources.values()),"metadata_only":True,"parent_cpu_sample":cpu,"active_wall_sample":wall,"charged_cpu_seconds":5,"charged_active_wall_seconds":7.5,"scope":"One separate saved-verifier metadata slice; six old slices retained. Cumulative35CPU/52.5activewall, existing8MiB cap. No product or checker executed."}
 write(WORK/"verify-preparation-2.json",record)
 print(json.dumps(record),flush=True)
if __name__=="__main__":main()
