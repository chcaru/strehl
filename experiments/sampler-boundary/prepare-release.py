"""Root metadata-only release/freeze constructor for four fixed sampler stages."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,time,os,stat,zipfile,re
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORK=HERE/"work"
ALIGN="crates/strehl-core/src/align.rs"
ORIGINAL="6d33f0e24f21d4370ccd8df0bf618e54a5ad615b838bc265469b4f85051c2786"
REPAIRED="e5003cf05a2805a0a6a72b6f59f2724bcc8873ebbcc8bbb95a69120bda7a24a1"
STAGES=("build","test","regression")
VARIANTS=("baseline","repaired")
TEST="crates/strehl-core/tests/sampler-boundary.rs"
SPEC="experiments/sampler-boundary/independent-test-spec.md"

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
def same_owned_ref(a,b):
 # Relative and absolute Windows spellings may identify the same owned file.
 # Keep location, extent and digest; equal content in a different file is not identity.
 def owned_name(v):
  need(type(v) is dict and set(v)=={"path","bytes","sha256"} and type(v["path"]) is str
       and type(v["bytes"]) is int and v["bytes"]>0 and type(v["sha256"]) is str
       and re.fullmatch("[0-9a-f]{64}",v["sha256"]),"typed positive file reference")
  text=str(Path(os.path.abspath(ROOT/v["path"])))
  if re.match(r"^\\\\\?\\[A-Za-z]:\\",text):text=text[4:]
  p=Path(text)
  need(p.is_relative_to(ROOT),"owned compared reference")
  return p
 return owned_name(a)==owned_name(b) and a["bytes"]==b["bytes"] and a["sha256"]==b["sha256"]

def source_map():
 old=json.loads(raw(ROOT/"experiments/common-tiff-stack/work/verification-source-freeze-2.json"))["source_bindings"]
 paths={ROOT/k for k in old}
 paths.update(p for p in (ROOT/"crates").rglob("*") if p.is_file() and (p.suffix==".rs" or p.name=="Cargo.toml") and "target" not in p.relative_to(ROOT/"crates").parts)
 paths.update(HERE/n for n in ("charter.md","run-stage.py","bounded-build-process.py","run-stage-contract.md","independent-test-spec.md",
                            "prepare-release.py","capture-stage.py","source-review.md","repair.patch","repair-rationale.md","independent-repair-source-review.md","independent-test-source-review.md"))
 out={p.relative_to(ROOT).as_posix():binding(p) for p in sorted(paths)}
 need(len(out)<=512 and sum(v["bytes"] for v in out.values())<=16<<20,"source family cap")
 return out

def bundle(stage,variant):
 label=variant+"-"+stage
 stem=WORK/(label+"-external-1")
 paths={"result":HERE/(label+"-1/result.json"),"tail":HERE/(label+"-1/parent-tail.json"),
        "outer":Path(str(stem)+"-outer.json"),"stdout":Path(str(stem)+"-stdout.bin"),
        "stderr":Path(str(stem)+"-stderr.bin"),"exit":Path(str(stem)+"-exit.txt")}
 buffers={k:read_bound(p,empty=(k=="stderr")) for k,p in paths.items()}
 refs={k:ref(p,empty=(k=="stderr"),b=buffers[k]) for k,p in paths.items()}
 r=json.loads(buffers["result"]);o=json.loads(buffers["outer"])
 need(r["schema"]=="sampler-boundary-owned-stage-v1" and r["stage"]==stage and r["variant"]==variant
      and r["status"]=="COMPLETE_STAGE_UNVERIFIED" and r["error"] is None and not r["finalization_errors"],"completed prior operational stage")
 need(o["schema"]=="sampler-boundary-stage-external-v1" and o["exit_code"]==0
      and o["timeout_terminated"] is False and buffers["exit"]==b"0\n","actual prior controller exit")
 old=json.loads(raw(ROOT/r["release"]["path"]))
 need(same_owned_ref(ref(ROOT/r["release"]["path"]),r["release"]),"exact prior release")
 return refs,r,old

def archive_sources(variant,sources,prior):
 # Immutable exact as-run source buffers, not a replacement live source tree.
 selected=sources if variant=="baseline" else {k:v for k,v in sources.items() if prior.get(k)!=v}
 need(variant=="baseline" or set(selected)=={ALIGN},"repair archive contains only reviewed sampler delta")
 path=WORK/(variant+"-source-1.zip")
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
 started=time.monotonic();cpu_started=time.process_time()
 a=argparse.ArgumentParser();a.add_argument("variant",choices=VARIANTS);a.add_argument("stage",choices=STAGES)
 args=a.parse_args();stage=args.stage;variant=args.variant;label=variant+"-"+stage
 need(stage!="regression" or variant=="repaired","regression is repaired-only")
 WORK.mkdir(exist_ok=True)
 freeze=WORK/(variant+"-source-freeze-1.json");current=source_map();prior_sources={}
 need(current[ALIGN]["sha256"]==(ORIGINAL if variant=="baseline" else REPAIRED),"exact independently reviewed sampler bytes")
 prereq={};exe=None;archived=None
 if stage=="build":
  need(not freeze.exists() and not (HERE/(label+"-1")).exists(),"new source freeze/build")
  if variant=="repaired":
   prereq["baseline"],baseline,old=bundle("test","baseline");prior_sources=old["source_bindings"]
   need({k for k in prior_sources if current.get(k)!=prior_sources[k]}=={ALIGN}
        and set(current)==set(prior_sources),"only reviewed align.rs source delta")
   observation=baseline["artifacts"]["test_observation"]
   need(same_owned_ref(ref(ROOT/observation["path"]),observation),"exact actual baseline observation")
   actual=json.loads(raw(ROOT/observation["path"],128<<10))
   need(actual["variant"]=="baseline" and actual["actual_exit_code"]==101 and actual["test_passed"] is False
        and actual["population_complete"] is True and actual["rows"]==344 and actual["failed"]>0
        and actual["exercised_public_boundary_failure"] is True,"preserved actual original assertion failure")
  archived=archive_sources(variant,current,prior_sources)
  write(freeze,{"schema":"sampler-boundary-root-source-freeze-v1","variant":variant,"source_bindings":current,"archive":archived})
 else:
  held=json.loads(raw(freeze));need(held["variant"]==variant and held["source_bindings"]==current,"unchanged frozen source bytes")
  prereq["build"],built,old=bundle("build",variant)
  need(old["source_bindings"]==current,"same sources as actual fresh build")
  exe=built["artifacts"]["unit_executable" if stage=="regression" else "executable"]
  if stage=="regression":
   prereq["test"],tested,prior_test=bundle("test","repaired")
   need(prior_test["source_bindings"]==current and tested["test_disposition"]["test_passed"] is True
        and tested["test_disposition"]["rows"]==344 and tested["test_disposition"]["failed"]==0,"actual repaired344-row prerequisite")
  need(same_owned_ref(ref(ROOT/exe["path"]),exe),"actual built executable before release")
 sources=current
 py=str(Path(sys.executable));controller=str(HERE/"run-stage.py");release=WORK/(label+"-release-1.json")
 command=(["cargo","test","-p","strehl-core","--lib","--test","sampler-boundary","--no-run","--jobs","2","--target-dir",
           str(ROOT/("target/sampler-boundary-"+variant+"-1")),"--message-format=json-render-diagnostics","--locked","--offline"]
          if stage=="build" else [str(HERE/(variant+"-build-1/sampler-boundary-tests.exe")),"--exact",
                                  "sampler_boundary_public_contract","--nocapture","--test-threads=1"])
 if stage=="regression":
  names=[
   "align::tests::catmull_rom_reproduces_the_samples_at_integer_positions",
   "align::tests::clamped_catmull_rom_stays_inside_the_exact_support16_hull",
   "align::tests::clamped_catmull_rom_is_bit_identical_until_catmull_leaves_the_hull",
   "align::tests::clamped_catmull_rom_preserves_integer_samples_and_constant_planes_exactly",
   "align::tests::clamped_catmull_rom_has_catmull_support_and_checked_domain",
   "align::tests::a_widened_clamp_makes_the_hull_guard_fail",
   "align::tests::a_gather_under_the_identity_is_the_identity",
   "align::tests::lanczos3_is_interpolating_and_preserves_dc",
   "align::tests::lanczos3_support_matches_its_reach",
   "align::tests::lanczos2_is_interpolating_and_costs_no_extra_border",
   "warpmap::gather_tests::gather_marks_uncovered_pixels_instead_of_clamping",
   "warpmap::gather_tests::gather_refuses_a_geometry_mismatch",
   "warpmap::gather_tests::gather_refuses_a_refused_frame",
  ]
  command=[str(ROOT/exe["path"]),"--exact","--nocapture","--test-threads=1",*names]
 inputs=[ref(sys.executable)]
 if stage=="build":inputs += [ref(shutil.which(n)) for n in ("cargo","rustc")]
 prediction={"spec":dict(path=SPEC,**sources[SPEC]),"test_source":dict(path=TEST,**sources[TEST]),"expected_exit_code":101 if variant=="baseline" else 0}
 value={"schema":"sampler-boundary-stage-release-v1","stage":stage,"variant":variant,"source_bindings":sources,"inputs":inputs,
        "command":[py,"-I","-S","-B",controller,"--release",str(release),"--release-sha256","ACTUAL_RELEASE_SHA256"],
        "children":[dict(command=command,expected_exit_code=0 if stage=="build" else prediction["expected_exit_code"])],
        "executable":exe,"prerequisites":prereq,"prediction":prediction}
 need(not (HERE/(label+"-1")).exists(),"unvisited target stage")
 result=write(release,value)
 need(sum(p.stat().st_size for p in WORK.iterdir() if p.is_file())<=8<<20,"aggregate sampler metadata/archive cap")
 cpu=time.process_time()-cpu_started;wall=time.monotonic()-started
 need(cpu+1<=5 and wall+2<=7.5,"fixed5CPU/7.5activewall metadata slice with final allowance")
 record={"stage":stage,"variant":variant,"release":result,"sources":len(sources),"source_bytes":sum(v["bytes"] for v in sources.values()),
         "archive":archived,"metadata_only":True,"parent_cpu_sample":cpu,"active_wall_sample":wall,
         "charged_cpu_seconds":5,"charged_active_wall_seconds":7.5,
         "scope":"Five fixed metadata slices total25CPU/37.5activewall/8MiB; no product/test launch. Samples plus1CPU/2wall final allowance must fit each slice."}
 write(WORK/(label+"-preparation-1.json"),record)
 print(json.dumps(record),flush=True)
if __name__=="__main__":main()
