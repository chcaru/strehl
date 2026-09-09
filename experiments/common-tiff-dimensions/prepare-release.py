"""Root metadata-only release constructor; never launches a product or checker."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,time,os,stat,zipfile
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORK=HERE/"work"
BUILD_ATTEMPT=1
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
 b=raw(p,4<<20);return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
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
 old=json.loads(raw(ROOT/"experiments/common-tiff-stack/work/verification-source-freeze-2.json"))["source_bindings"]
 paths={ROOT/k for k in old}
 paths.update(p for p in (ROOT/"crates").rglob("*") if p.is_file() and (p.suffix==".rs" or p.name=="Cargo.toml") and "target" not in p.relative_to(ROOT/"crates").parts)
 paths.update(HERE/n for n in ("charter.md","implementation-contract.md","independent-spec.md","independent-controls.py","bounded-build-process.py","run-stage.py","run-stage-contract.md","prepare-release.py","capture-stage.py","source-review.md","root-source-review.md","draft.patch","patch-source-handoff.md","stage-layout-construction.md","independent-spec-draft-1.md","product-layout-construction.md"))
 need(len(paths)<=512,"source path population before content reads")
 extents=[p.stat().st_size for p in paths]
 need(all(0<n<=4<<20 for n in extents) and sum(extents)<=16<<20,"declared source extents before content reads")
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
def archive_sources(sources):
 # Immutable exact as-run source buffers, not a replacement live source tree.
 selected=sources
 path=WORK/"source-1.zip"
 with zipfile.ZipFile(path,"x",compression=zipfile.ZIP_STORED) as z:
  for k,pin in selected.items():
   b=raw(ROOT/k,4<<20)
   need(dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())==pin,"archived source equals held buffer")
   z.writestr(k,b)
 with zipfile.ZipFile(path,"r") as z:
  need(z.namelist()==list(selected),"exact archive inventory")
  for k,pin in selected.items():
   b=z.read(k)
   need(dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())==pin,"every archive buffer read back")
 return ref(path)

def main():
 started=time.monotonic();cpu_started=time.process_time();a=argparse.ArgumentParser();a.add_argument("stage",choices=STAGES);args=a.parse_args();stage=args.stage
 WORK.mkdir(exist_ok=True)
 freeze=WORK/"source-freeze-1.json";current=source_map()
 if stage=="build":
  need(not freeze.exists() and not (HERE/"build-1").exists(),"new initial freeze/build")
  archive=archive_sources(current)
  write(freeze,{"schema":"common-tiff-dimensions-root-source-freeze-v1","source_bindings":current,"archive":archive})
 else:
  need(json.loads(raw(freeze))["source_bindings"]==current,"unchanged frozen source bytes")
 sources=current
 prereq={};results={}
 for previous in STAGES[:STAGES.index(stage)]:
  prereq[previous],results[previous]=bundle(previous)
  rr=json.loads(raw(ROOT/results[previous]["release"]["path"]))
  need(rr["source_bindings"]==sources,"same prior producer sources")
 exe=None if stage=="build" else results["build"]["artifacts"]["executable"]
 fixtures=results["prepare"]["artifacts"]["fixture_index"] if stage in ("render","verify") else None
 rb=None
 if stage=="verify":rb=write(HERE/"render-bundle-1.json",prereq["render"])
 py=str(Path(sys.executable));controller=str(HERE/"run-stage.py");release=WORK/(stage+"-release-"+str(attempt(stage))+".json")
 controls=str(HERE/"independent-controls.py");controlsha=sources["experiments/common-tiff-dimensions/independent-controls.py"]["sha256"]
 if stage=="build":
  commands=[["cargo","build","-p","strehl-cli","--bin","strehl-common-input","--jobs","2","--target-dir",str(ROOT/"target/common-tiff-dimensions-1"),"--message-format=json-render-diagnostics","--locked","--offline"]]
 elif stage=="prepare":
  commands=[[py,"-I","-S","-B",controls,"prepare","--output",str(HERE/"prepare-1/fixtures"),"--source-sha256",controlsha]]
 elif stage=="render":
  rows=json.loads(raw(ROOT/fixtures["path"]))["cases"]
  commands=[[str(ROOT/exe["path"]) if x=="ACTUAL_BINARY_PATH" else x for x in row["command"]] for row in rows]
  need(len(commands)==24,"fixed case count")
 else:
  commands=[[py,"-I","-S","-B",controls,"verify","--fixtures",str(HERE/"prepare-1/fixtures/index.json"),"--fixtures-sha256",fixtures["sha256"],"--run-bundle",str(HERE/"render-bundle-1.json"),"--run-bundle-sha256",rb["sha256"],"--output",str(HERE/"verify-1/check"),"--source-sha256",controlsha]]
 inputs=[ref(sys.executable),ref(ROOT/"experiments/M165-common-input/linear-prophoto-d50-v1.icc")]
 if stage=="build":inputs += [ref(shutil.which(n)) for n in ("cargo","rustc")]
 value={"schema":"common-tiff-dimensions-stage-release-v1","stage":stage,"source_bindings":sources,"inputs":inputs,
 "command":[py,"-I","-S","-B",controller,"--release",str(release),"--release-sha256","ACTUAL_RELEASE_SHA256"],
 "children":[dict(command=c,expected_exit_code=1 if stage=="render" and i>=9 else 0) for i,c in enumerate(commands)],
 "executable":exe,"fixtures":fixtures,"run_bundle":rb,"prerequisites":prereq}
 need(not (HERE/(stage+"-"+str(attempt(stage)))).exists(),"unvisited target stage")
 result=write(release,value)
 cpu=time.process_time()-cpu_started;wall=time.monotonic()-started
 need(cpu+1<=10 and wall+2<=20,"fixed10CPU/20activewall metadata slice including final allowance")
 need(sum(p.stat().st_size for p in WORK.iterdir() if p.is_file())<=32<<20,"32MiB metadata/archive family")
 record={"stage":stage,"release":result,"sources":len(sources),"source_bytes":sum(v["bytes"] for v in sources.values()),"metadata_only":True,"parent_cpu_sample":cpu,"active_wall_sample":wall,"charged_cpu_seconds":10,"charged_active_wall_seconds":20,"scope":"Four fixed metadata construction slices total40CPU/80activewall/32MiB; no product/checker. Samples plus1CPU/2wall final allowance must fit each slice."}
 write(WORK/(stage+"-preparation-"+str(attempt(stage))+".json"),record)
 print(json.dumps(record),flush=True)
if __name__=="__main__":main()
