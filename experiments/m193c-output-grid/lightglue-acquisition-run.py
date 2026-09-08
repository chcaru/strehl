"""Bounded, opaque official SIFT-LightGlue intake. Never imports staged assets."""
import time
START=time.monotonic()
import argparse
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
from pathlib import Path
import sys
import types
import urllib.request
import urllib.parse
import ssl

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
MIB=1<<20
COMMIT="eb42fee2d71449efb0aa5c10549752b5d75384d8"
PREFIX="https://raw.githubusercontent.com/cvg/LightGlue/"+COMMIT+"/"
RESERVATION=dict(cpu_seconds=20,wall_seconds=120,file_bytes=64*MIB,metadata_bytes=MIB)
PRIOR=dict(cpu_seconds=639.9375,wall_seconds=757.919086,file_bytes=3969447612,metadata_bytes=44246966)
COMPLETE="COMPLETE_SOURCE_AND_CHECKPOINT_ACQUISITION_ONLY"
ASSETS=[
 dict(id="matcher",url=PREFIX+"lightglue/lightglue.py",name="lightglue.py",expected_bytes=None,max_bytes=MIB,kind="text"),
 dict(id="rootsift_reference",url=PREFIX+"lightglue/sift.py",name="sift.py",expected_bytes=None,max_bytes=MIB,kind="text"),
 dict(id="license",url=PREFIX+"LICENSE",name="license.txt",expected_bytes=None,max_bytes=MIB,kind="text"),
 dict(id="readme",url=PREFIX+"README.md",name="readme.md",expected_bytes=None,max_bytes=MIB,kind="text"),
 dict(id="checkpoint",url="https://github.com/cvg/LightGlue/releases/download/v0.1_arxiv/sift_lightglue.pth",name="sift-lightglue.pth",expected_bytes=47632573,max_bytes=47632573,kind="checkpoint")]
HOSTS={"raw.githubusercontent.com","github.com","release-assets.githubusercontent.com","objects.githubusercontent.com"}
PINS={"bounded-process.py":"47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b"}
AUDIT_SHA="02c97674a2128fc1d31ba687aa0fe3e98648e5a0604783ad4006166b29814adc"
PLAN_SHA="7c83db049cc869b2428b7e0aa321ece23b91c0b05c6143c3414591479afa41d6"

def need(ok,message):
    if not ok: raise ValueError(message)

def strict(raw):
    def pairs(rows):
        d={}
        for k,v in rows:
            need(k not in d,"duplicate JSON key");d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:need(False,"nonfinite JSON"))

def rawjson(value): return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf8")

def ref(path,limit=64*MIB):
    p=Path(path).resolve();need(p.is_relative_to(ROOT) or p==Path(sys.executable).resolve(),"owned metadata or exact Python")
    a=p.stat();need(0<=a.st_size<=limit,"bounded input extent")
    h=hashlib.sha256();size=0
    with p.open("rb") as stream:
        while b:=stream.read(MIB):
            h.update(b);size+=len(b);need(size<=limit,"bounded input read")
    z=p.stat();need((a.st_size,a.st_mtime_ns,a.st_ino)==(z.st_size,z.st_mtime_ns,z.st_ino) and size==a.st_size,"stable input")
    return dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),bytes=size,sha256=h.hexdigest())

def checkref(value):
    actual=ref(ROOT/value["path"])
    need(set(value)=={"path","bytes","sha256"} and actual["bytes"]==value["bytes"] and actual["sha256"]==value["sha256"],"exact file reference identity/extent/hash")
    return actual

def readref(value):
    checkref(value);p=ROOT/value["path"];b=p.read_bytes()
    need(len(b)==value["bytes"] and hashlib.sha256(b).hexdigest()==value["sha256"],"same JSON bytes")
    return strict(b)

def save(path,value,limit=256*1024):
    b=rawjson(value);need(len(b)<=limit,"metadata prewrite cap")
    with Path(path).open("xb") as stream:need(stream.write(b)==len(b),"complete metadata write")
    return ref(path)

def urlcheck(url):
    p=urllib.parse.urlsplit(url)
    need(p.scheme=="https" and p.hostname in HOSTS and p.port in (None,443)
         and p.username is None and p.password is None and not p.fragment,"HTTPS exact allowlist, no credentials/fragment")
    return url

def bytecheck(current,chunk,maximum):
    need(0<=current<=maximum and 0<=chunk<=maximum-current,"payload prewrite byte cap")

def prefixcheck(first,kind):
    need(bool(first),"nonempty HTTP body")
    low=first.lstrip().lower()
    need(not low.startswith((b"<!doctype",b"<html",b'{"',b'["')),"not HTML/JSON error body")
    if kind=="checkpoint":need(first.startswith((b"PK\x03\x04",b"\x80\x02",b"\x80\x03",b"\x80\x04",b"\x80\x05")),"opaque supported torch container prefix")

def controls():
    rows=[]
    def reject(name,fn):
        failed=False
        try:fn()
        except ValueError:failed=True
        rows.append(dict(id=name,passed=failed));need(failed,"negative control "+name)
    for i,u in enumerate(("http://github.com/a","https://evil.example/a","https://github.com.evil.example/a","https://user:secret@github.com/a","https://github.com:444/a","https://github.com/a#fragment")):
        reject("forbidden-url-"+str(i),lambda u=u:urlcheck(u))
    for u in (x["url"] for x in ASSETS):urlcheck(u)
    urlcheck("https://release-assets.githubusercontent.com/a?token=opaque")
    reject("prewrite-overrun",lambda:bytecheck(7,2,8))
    bytecheck(7,1,8)
    reject("checkpoint-json",lambda:prefixcheck(b'{"message":"error"}',"checkpoint"))
    reject("checkpoint-html",lambda:prefixcheck(b"<html>error","checkpoint"))
    reject("checkpoint-random",lambda:prefixcheck(b"not a checkpoint","checkpoint"))
    prefixcheck(b"PK\x03\x04opaque","checkpoint")
    reject("duplicate-plan-key",lambda:strict(b'{"x":1,"x":2}'))
    return rows

def baseline():
    oldpath=HERE/"area-four-plan-1.json";oldref=ref(oldpath);need(oldref["sha256"]==PLAN_SHA,"held AREA4 plan")
    old=readref(oldref)
    ar=ref(HERE/"work/independent-area-four-1-audit.json");need(ar["sha256"]==AUDIT_SHA,"held AREA4 audit")
    audit=readref(ar)
    need(audit["schema"]=="m193c-saved-area-four-audit-v1" and audit["status"]=="PASS_SAVED_AREA_FOUR_OUTCOME_AUDIT"
         and audit["subject_complete"] is True and audit["refused_control"] is None and audit["cpu_accounting_complete"] is True,"complete independently audited AREA4")
    external={k:checkref(v) for k,v in audit["external"].items()}
    need(set(external)=={"plan","result","outer","console","exit"} and external["plan"]==oldref,"exact audited baseline")
    parent=readref(external["result"]);outer=readref(external["outer"])
    console=(ROOT/external["console"]["path"]).read_bytes().splitlines()[-1];final=strict(console)
    need(parent["status"]==final["status"]=="COMPLETE_AREA_FOUR_DIAGNOSTIC_ONLY" and outer["exit_code"]==0
         and (ROOT/external["exit"]["path"]).read_bytes().strip()==b"0" and parent["source_bindings"]==old["source_bindings"]
         and final["work_through_final_checks"]==audit["actual_final_work"] and parent["error"] is None
         and final["cpu_accounting_complete"] is True and not parent["finalization_errors"],"actual AREA4 closure")
    base=dict(audit["actual_final_work"])
    wall=Decimal(str(parent["prior_work"]["wall_seconds"]))+Decimal(str(outer["elapsed_wall_seconds"]))
    need(wall==Decimal(audit["next_wall_seconds"]),"independent outer wall carry")
    base["wall_seconds"]=float(wall.quantize(Decimal("0.000001"),rounding=ROUND_CEILING))
    need(base==PRIOR and len(old["source_bindings"])==210,"held prior and all210 historical sources")
    external["audit"]=ar
    return old,external

def prepare(args):
    need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode,"root cwd and no bytecode")
    old,external=baseline();bindings=dict(old["source_bindings"])
    additions=[SELF,HERE/"lightglue-acquisition-preregister.md"]
    additions.extend(ROOT/x for x in args.source)
    need(len(additions)==len(set(additions)),"distinct new source paths")
    for p in additions:
        r=ref(p);v={k:r[k] for k in ("bytes","sha256")}
        need(bindings.setdefault(r["path"],v)==v,"no source replacement")
    for p,v in bindings.items():need(ref(ROOT/p)==dict(path=p,**v),"complete held source closure")
    need(all((HERE/x).relative_to(ROOT).as_posix() in bindings for x in
        ("work/independent-lightglue-acquisition-source-review.md","work/independent-lightglue-acquisition-audit.py")),"held independent review and prospective audit")
    path=HERE/"lightglue-acquisition-plan-1.json";out=HERE/"lightglue-acquisition-1"
    need(not out.exists() and not path.exists(),"fresh intake plan/output")
    python=checkref(old["python_executable"]);base=[python["path"],"-B","-X","faulthandler",str(SELF)]
    parent=base+["--plan",str(path),"--sha256","ACTUAL_PLAN_SHA256","--output",str(out)]
    worker=parent+["--worker"]
    plan=dict(schema="m193c-lightglue-acquisition-plan-v1",source_bindings=bindings,area4_baseline=external,
        prior_work=PRIOR,reservation=RESERVATION,assets=ASSETS,source_commit=COMMIT,asset_release_id=131252238,
        upstream_checkpoint_digest=None,upstream_digest_observation="Official v0.1_arxiv release asset metadata reports digest:null; local hash is an integrity pin, not an independent publisher digest.",
        python_executable=python,commands=dict(parent=parent,worker=worker),
        held_metadata=[dict(path=k,**bindings[k]) for k in sorted(bindings) if k not in old["source_bindings"]],
        preparation_timing=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START))
    need(plan["preparation_timing"]["cpu_seconds"]<2 and plan["preparation_timing"]["wall_seconds"]<5,"metadata preparation headroom")
    checks=controls();prepared=rawjson(plan)
    need(len(prepared)<=256*1024 and sum(x["bytes"] for x in plan["held_metadata"])+len(prepared)+524*1024<MIB,"held metadata and final/audit/outer/log reserves")
    receipt=save(path,plan)
    print(json.dumps(dict(status="PREPARED_METADATA_ONLY",plan=receipt,source_count=len(bindings),controls=checks,image_payloads_opened=0)))

def setup(args):
    need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and sys._xoptions=={"faulthandler":True},"exact root/runtime options")
    pr=ref(args.plan);need(pr["sha256"]==args.sha256,"external plan SHA");plan=readref(pr)
    need(set(plan)==set("schema source_bindings area4_baseline prior_work reservation assets source_commit asset_release_id upstream_checkpoint_digest upstream_digest_observation python_executable commands held_metadata preparation_timing".split()),"closed plan schema")
    need(set(plan["commands"])=={"parent","worker"} and set(plan["preparation_timing"])=={"cpu_seconds","wall_seconds"},"closed command/timing schema")
    need(plan["schema"]=="m193c-lightglue-acquisition-plan-v1" and plan["assets"]==ASSETS
         and plan["reservation"]==RESERVATION and plan["prior_work"]==PRIOR and plan["source_commit"]==COMMIT
         and plan["asset_release_id"]==131252238 and plan["upstream_checkpoint_digest"] is None,"frozen intake specification")
    expected=[args.sha256 if x=="ACTUAL_PLAN_SHA256" else x for x in plan["commands"]["worker" if args.worker else "parent"]]
    need(expected==sys.orig_argv,"exact executed argv")
    checkref(plan["python_executable"])
    for p,v in plan["source_bindings"].items():need(ref(ROOT/p)==dict(path=p,**v),"all sources unchanged")
    old,external=baseline();need(plan["area4_baseline"]==external and all(plan["source_bindings"].get(k)==v for k,v in old["source_bindings"].items()),"preserved fullAREA4 ancestry")
    need(plan["held_metadata"]==[dict(path=k,**v) for k,v in plan["source_bindings"].items() if k not in old["source_bindings"]],"exact new binding metadata delta")
    out=Path(args.output).resolve();need(out==HERE/"lightglue-acquisition-1","exact owned output")
    return plan,pr,out

class Redirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,attempt):self.attempt=attempt;self.count=0
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        self.count+=1;need(self.count<=4,"redirect cap");urlcheck(newurl)
        self.attempt["redirects"].append(dict(status=code,from_url=req.full_url,to_url=newurl))
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def prewrite(out,plan,pr,extra,checkpoint=False):
    # The concurrently written log is charged at its full cap, never its transient extent.
    entries=[p for p in out.rglob("*") if p.is_file() and p.name!="worker.log"]
    payload=sum(p.stat().st_size for p in entries)
    metadata=sum(p.stat().st_size for p in entries if p.name!="sift-lightglue.pth")
    held=sum(x["bytes"] for x in plan["held_metadata"])+pr["bytes"]
    reserve=(256+196+8+64)*1024
    bytecheck(payload+held+reserve,extra,RESERVATION["file_bytes"])
    bytecheck(metadata+held+reserve,0 if checkpoint else extra,RESERVATION["metadata_bytes"])

def worker(args,plan,pr,out):
    need(out.is_dir() and not any(out.glob("attempt-*")),"fresh worker prefix")
    def saved(path,value):
        prewrite(out,plan,pr,len(rawjson(value)))
        return save(path,value)
    rows=controls();saved(out/"controls.json",rows)
    # No environment proxies, cookies, authentication handlers, retries or alternate URLs.
    for index,asset in enumerate(ASSETS):
        attempt=dict(id=asset["id"],url=asset["url"],redirects=[],status="STARTED",bytes=0,sha256=None,error=None)
        saved(out/("attempt-"+str(index)+"-start.json"),attempt)
        path=out/asset["name"];h=hashlib.sha256();size=0
        try:
            remaining=100-(time.monotonic()-START);need(remaining>0,"network phase deadline")
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),Redirect(attempt),
                urllib.request.HTTPSHandler(context=ssl.create_default_context()))
            request=urllib.request.Request(urlcheck(asset["url"]),headers={"User-Agent":"strehl-research-bounded-intake/1","Accept-Encoding":"identity"})
            with opener.open(request,timeout=min(10,remaining)) as response:
                attempt["final_url"]=urlcheck(response.url)
                attempt["http_status"]=response.status
                attempt["content_type"]=response.headers.get("Content-Type","")
                attempt["content_length"]=response.headers.get("Content-Length")
                need(response.status==200 and response.headers.get("Content-Encoding","identity")=="identity","HTTP200 identity encoding")
                mime=attempt["content_type"].split(";")[0].strip().lower()
                need(mime not in ("application/json","text/html"),"not HTTP error content type")
                if asset["kind"]=="checkpoint":need(mime in ("application/octet-stream","binary/octet-stream","application/x-pytorch"),"checkpoint binary content type")
                length=attempt["content_length"]
                if length is not None:
                    need(length.isascii() and length.isdecimal(),"declared numeric length")
                    bytecheck(0,int(length),asset["max_bytes"])
                    need(asset["expected_bytes"] is None or int(length)==asset["expected_bytes"],"expected checkpoint header extent")
                with path.open("xb",buffering=0) as stream:
                    pending=b"";validated=False
                    while True:
                        need(time.monotonic()-START<100 and time.process_time()<12,"network phase wall/CPU")
                        b=response.read1(65536 if validated else 64-len(pending))
                        if not validated:
                            pending+=b
                            if len(pending)<64 and b:continue
                            prefixcheck(pending,asset["kind"]);b=pending;validated=True
                        if not b:break
                        bytecheck(size,len(b),asset["max_bytes"])
                        prewrite(out,plan,pr,len(b),asset["kind"]=="checkpoint")
                        written=stream.write(b)
                        size+=written;h.update(b[:written])
                        need(written==len(b),"full payload write")
                need(size>0 and (length is None or size==int(length)) and
                     (asset["expected_bytes"] is None or size==asset["expected_bytes"]),"complete expected body")
                if asset["kind"]=="text":path.read_text(encoding="utf8")
                attempt["status"]="COMPLETE_OPAQUE_ASSET"
        except Exception as exc:
            attempt["error"]=repr(exc);attempt["status"]="REFUSED_ASSET"
        finally:
            actual=ref(path) if path.exists() else dict(bytes=0,sha256=hashlib.sha256(b"").hexdigest())
            attempt["bytes"]=actual["bytes"];attempt["sha256"]=actual["sha256"]
            attempt["path"]=path.relative_to(ROOT).as_posix()
            attempt["elapsed_wall_seconds"]=time.monotonic()-START
            saved(out/("attempt-"+str(index)+"-final.json"),attempt)
        if attempt["error"] is not None:raise ValueError("retained asset refusal: "+asset["id"])
    saved(out/"worker-result.json",dict(status=COMPLETE,plan=pr,controls=rows,command=sys.orig_argv,
        timing=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)))
    print(COMPLETE)

def parent(args,plan,pr,out):
    need(not out.exists(),"fresh parent output");out.mkdir()
    source=ref(SELF);errors=[];child=None;assets=[]
    result=dict(schema="m193c-lightglue-acquisition-v1",status="REFUSED_ACQUISITION",plan=pr,source_commit=COMMIT,
        asset_release_id=131252238,assets=assets,prior_work=PRIOR,reservation=RESERVATION,charged_work=None,
        timing=None,command=sys.orig_argv,source=source,errors=errors,inventory=[],child=None,
        upstream_checkpoint_digest=None,model_imports=0,image_payloads_opened=0,checkpoint_parses=0)
    try:
        controls()
        p=HERE/"bounded-process.py";raw=p.read_bytes()
        need(hashlib.sha256(raw).hexdigest()==PINS[p.name],"pinned process controller")
        b=types.ModuleType("m193c_intake_process");b.__file__=str(p);sys.modules[b.__name__]=b
        exec(compile(raw,str(p),"exec"),b.__dict__)
        api=b.load_job_api(plan["source_bindings"]["experiments/m12-scorecard/m12-harness.py"])
        command=[args.sha256 if x=="ACTUAL_PLAN_SHA256" else x for x in plan["commands"]["worker"]]
        env,_=b.clean_environment();env["PYTHONDONTWRITEBYTECODE"]="1"
        child=b.run(command,env,str(ROOT),out/"worker.log",api=api,wall_seconds=110,cpu_seconds=15,log_bytes=65536,committed_bytes=512*MIB)
        result["child"]=child
        need(child["exit_code"]==0 and child["error"] is None and not child["cleanup_errors"] and child["terminal_job_accounting"]
             and child["job_accounting"]["active_processes"]==0 and not child["termination"]["attempted"],"successful bounded complete worker")
        wr=readref(ref(out/"worker-result.json"))
        need(wr["status"]==COMPLETE and wr["plan"]==pr and wr["command"]==command and all(x["passed"] for x in wr["controls"]),"successful worker receipt")
        for index,asset in enumerate(ASSETS):
            row=readref(ref(out/("attempt-"+str(index)+"-final.json")))
            actual=ref(out/asset["name"])
            need(row["status"]=="COMPLETE_OPAQUE_ASSET" and row["error"] is None and
                {k:row[k] for k in ("path","bytes","sha256")}==actual and row["url"]==asset["url"],"complete rehashed opaque asset")
            assets.append(dict(id=asset["id"],url=asset["url"],final_url=row["final_url"],**actual,expected_bytes=asset["expected_bytes"]))
        for p,v in plan["source_bindings"].items():need(ref(ROOT/p)==dict(path=p,**v),"source closure unchanged after intake")
        result["status"]=COMPLETE
    except Exception as exc:errors.append(repr(exc))
    finally:
        # Retain every partial file, start/final attempt and failed bounded-child observation.
        inventory=[ref(p) for p in sorted(out.rglob("*")) if p.is_file()]
        result["inventory"]=inventory
        payload=sum(x["bytes"] for x in inventory)
        metadata=sum(x["bytes"] for x in inventory if not x["path"].endswith(".pth"))
        childcpu=0 if child is None or child["job_accounting"] is None else child["job_accounting"]["total_cpu_100ns"]/1e7
        timing=dict(cpu_seconds=time.process_time()+childcpu+plan["preparation_timing"]["cpu_seconds"],
            wall_seconds=time.monotonic()-START+plan["preparation_timing"]["wall_seconds"])
        result["timing"]=timing
        held_bytes=sum(x["bytes"] for x in plan["held_metadata"])+pr["bytes"]
        reserved_metadata=256*1024+196*1024+8192
        actual=dict(cpu_seconds=timing["cpu_seconds"]+2,wall_seconds=timing["wall_seconds"]+5,
            file_bytes=payload+held_bytes+reserved_metadata,metadata_bytes=metadata+held_bytes+reserved_metadata)
        result["final_tail_allowance"]=dict(cpu_seconds=2,wall_seconds=5)
        result["timing_scope"]="Through pre-result sample, plus separately reserved final tail; outer receipt and independent audit must verify tail."
        # Include held sources/plan,256KiB final receipt,196KiB future audit and8KiB outer receipts.
        result["metadata_accounting"]=dict(held=plan["held_metadata"],plan_bytes=pr["bytes"],held_bytes=held_bytes,
            final_receipt_reserve=256*1024,future_audit_reserve=196*1024,outer_receipt_reserve=8192)
        result["observed_work_plus_final_receipt_reserve"]=actual
        result["charged_work"]={k:float(Decimal(str(PRIOR[k]))+max(Decimal(str(RESERVATION[k])),Decimal(str(actual[k]))))
            if k.endswith("seconds") else PRIOR[k]+max(RESERVATION[k],actual[k]) for k in RESERVATION}
        if any(actual[k]>RESERVATION[k] for k in RESERVATION):
            errors.append("reservation exceeded; greater actual work charged");result["status"]="REFUSED_ACQUISITION"
        save(out/"result.json",result)
        print(json.dumps(dict(status=result["status"],result=str(out/"result.json"),charged_work=result["charged_work"],errors=errors,
            terminal_parent_cpu_seconds=time.process_time(),terminal_parent_wall_seconds=time.monotonic()-START)))
    return 0 if result["status"]==COMPLETE else 2

def main():
    p=argparse.ArgumentParser();p.add_argument("--prepare",action="store_true");p.add_argument("--source",action="append",default=[])
    p.add_argument("--plan");p.add_argument("--sha256");p.add_argument("--output");p.add_argument("--worker",action="store_true");args=p.parse_args()
    if args.prepare:prepare(args);return 0
    plan,pr,out=setup(args)
    if args.worker:worker(args,plan,pr,out);return 0
    return parent(args,plan,pr,out)
if __name__=="__main__":raise SystemExit(main())
