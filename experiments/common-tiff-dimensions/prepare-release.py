"""Root metadata-only release constructor; never launches a product or checker."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,time,os,stat,zipfile,io
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORK=HERE/"work"
BUILD_ATTEMPT=2
BASE_FREEZE_SHA="7b37fe67c8cee38e655d461ee9c5b498b60808b834d2b97d61ee3be9a76b6de4"
NEW_SOURCES=("scratch-scan.py","scratch-scan-draft-1.py","scratch-scan-rationale.md",
             "scratch-scan-controls.py","scratch-scan-spec.md","scratch-control-capture.py","scratch-scan-source-review.md",
             "build2-source-addendum.md","build2-source-review.md")
CHANGED_SOURCES=("run-stage.py","bounded-build-process.py","prepare-release.py",
                 "capture-stage.py","run-stage-contract.md","independent-controls.py","independent-spec.md")
RESERVATIONS={
 "failed_build_1":{"cpu_seconds":600,"wall_seconds":300,"retained":True},
 "fresh_build_2":{"cpu_seconds":600,"wall_seconds":300,"invocations":1},
 "unchanged_prepare_render_verify":{"cpu_seconds":270,"wall_seconds":420},
 "stage_total":{"cpu_seconds":1470,"wall_seconds":1020},
 "metadata_constructors":{"prior_invocations":1,"fresh_invocations":4,"cpu_seconds":50,"wall_seconds":100,"family_bytes":32<<20},
 "failed_build_review":{"cpu_seconds":10,"wall_seconds":20,"read_bytes":64<<20,"write_bytes":2<<20},
 "scratch_controls":{"cpu_seconds":5,"wall_seconds":10,"read_bytes":1<<20,"write_bytes":1<<20,"groups":16,"dispatcher_calls":17},
 "scratch_wrapper":{"cpu_seconds":5,"wall_seconds":10,"read_bytes":1<<20,"write_bytes":1<<20},
 "scratch_combined_outer_wall_seconds":20,
 "scope":"Nonrefundable explicit reservations only. Earlier source-preparation/formatter records remain; no whole-session numeric aggregate is inferred."}
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
def source_map(old):
 paths={ROOT/k for k in old}
 paths.update(p for p in (ROOT/"crates").rglob("*") if p.is_file() and (p.suffix==".rs" or p.name=="Cargo.toml") and "target" not in p.relative_to(ROOT/"crates").parts)
 paths.update(HERE/n for n in NEW_SOURCES)
 need(len(paths)<=512,"source path population before content reads")
 extents=[p.stat().st_size for p in paths]
 need(all(0<n<=4<<20 for n in extents) and sum(extents)<=16<<20,"declared source extents before content reads")
 out={p.relative_to(ROOT).as_posix():binding(p) for p in sorted(paths)}
 need(len(out)<=512 and sum(v["bytes"] for v in out.values())<=16<<20,"source family cap")
 allowed_new={(HERE/n).relative_to(ROOT).as_posix() for n in NEW_SOURCES}
 allowed_changed={(HERE/n).relative_to(ROOT).as_posix() for n in CHANGED_SOURCES}
 need(set(old)<=set(out) and set(out)-set(old)<=allowed_new,"no removed or undeclared new source")
 need({k for k in old if out[k]!=old[k]}<=allowed_changed,"only declared operational/path source changes")
 return out

def base_sources():
 path=WORK/"source-freeze-1.json";b=raw(path,64<<10)
 need(hashlib.sha256(b).hexdigest()==BASE_FREEZE_SHA,"exact preserved source1 freeze")
 value=json.loads(b)
 need(set(value)=={"schema","source_bindings","archive"} and value["schema"]=="common-tiff-dimensions-root-source-freeze-v1"
      and len(value["source_bindings"])==181,"original181 source authority")
 archive=value["archive"]
 need(archive["path"]=="experiments/common-tiff-dimensions/work/source-1.zip","exact preserved archive path")
 archive_raw=raw(ROOT/archive["path"],16<<20)
 need(ref(ROOT/archive["path"],b=archive_raw)==archive,"same-buffer preserved source1 archive")
 return value,ref(path,b=b),archive_raw

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
def archive_sources(sources,base,base_ref,base_raw):
 # Retain source1; archive only changed/new bytes, then reconstruct every current buffer.
 prior=base["source_bindings"]
 selected={k:v for k,v in sources.items() if k not in prior or prior[k]!=v}
 need(selected and set(prior)<=set(sources),"nonempty extension without source removal")
 path=WORK/"source-2-delta.zip"
 with zipfile.ZipFile(path,"x",compression=zipfile.ZIP_STORED) as z:
  for k,pin in selected.items():
   b=raw(ROOT/k,4<<20)
   need(dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())==pin,"archived delta equals held buffer")
   z.writestr(k,b)
 delta_raw=raw(path,16<<20)
 with zipfile.ZipFile(io.BytesIO(base_raw),"r") as old,zipfile.ZipFile(io.BytesIO(delta_raw),"r") as delta:
  need(len(old.namelist())==len(prior) and set(old.namelist())==set(prior)
       and delta.namelist()==list(selected),"exact unique base/delta archive inventories")
  for k,pin in prior.items():
   b=old.read(k)
   need(dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())==pin,"every preserved archive buffer")
  for k,pin in sources.items():
   b=(delta if k in selected else old).read(k)
   need(dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())==pin,"every composed current source buffer")
 return {"schema":"common-tiff-dimensions-root-source-freeze-v2","source_bindings":sources,
         "base_freeze":base_ref,"base_archive":base["archive"],"delta_archive":ref(path,b=delta_raw),
         "changed_or_new":list(selected),"scope":"Exact current source is delta when named, otherwise preserved source1. No old byte buffer is overwritten."}

def main():
 started=time.monotonic();cpu_started=time.process_time();a=argparse.ArgumentParser();a.add_argument("stage",choices=STAGES);args=a.parse_args();stage=args.stage
 WORK.mkdir(exist_ok=True)
 freeze=WORK/"source-freeze-2.json";base,base_ref,base_raw=base_sources();current=source_map(base["source_bindings"])
 if stage=="build":
  need(not freeze.exists() and not (HERE/"build-2").exists() and not (ROOT/"target/common-tiff-dimensions-2").exists(),"fresh source2/build2/target2")
  composed=archive_sources(current,base,base_ref,base_raw)
  write(freeze,composed)
 else:
  frozen=json.loads(raw(freeze))
  need(frozen["schema"]=="common-tiff-dimensions-root-source-freeze-v2" and frozen["source_bindings"]==current
       and frozen["base_freeze"]==base_ref and frozen["base_archive"]==base["archive"],"unchanged compositional source2 authority")
  need(ref(ROOT/frozen["delta_archive"]["path"])==frozen["delta_archive"],"unchanged source2 delta archive")
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
  commands=[["cargo","build","-p","strehl-cli","--bin","strehl-common-input","--jobs","2","--target-dir",str(ROOT/"target/common-tiff-dimensions-2"),"--message-format=json-render-diagnostics","--locked","--offline"]]
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
 record={"stage":stage,"build_attempt":BUILD_ATTEMPT,"source_freeze":ref(freeze),"reservations":RESERVATIONS,"release":result,"sources":len(sources),"source_bytes":sum(v["bytes"] for v in sources.values()),"metadata_only":True,"parent_cpu_sample":cpu,"active_wall_sample":wall,"charged_cpu_seconds":10,"charged_active_wall_seconds":20,"scope":"Four fresh metadata slices plus the retained build1 slice total50CPU/100wall/32MiB; no product/checker. Samples plus1CPU/2wall final allowance fit each fresh10CPU/20wall slice; prior work is not reset."}
 write(WORK/(stage+"-preparation-"+str(attempt(stage))+".json"),record)
 print(json.dumps(record),flush=True)
if __name__=="__main__":main()
