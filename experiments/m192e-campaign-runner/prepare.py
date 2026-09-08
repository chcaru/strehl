"""M192e metadata preparation only; never imports/executes the subject or opens RAW/TIFF payloads."""
import time
START=time.monotonic()
import argparse,hashlib,json,math,os,stat,sys
from pathlib import Path
from uuid import UUID
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OLD=ROOT/"experiments/m192d-production-rehearsal/out-20260907-090514-892948"
PROTOCOL=ROOT/"experiments/M192-m12-certify/protocol.json"
MIB=1<<20
OLD_PINS={
"summary.json":(1156,"CC48A5274186A1FAD3654A02559C715BC7C4DF8E01FA9F2105F08E8C632E6B9F"),
"source-freeze.json":(101039,"FF2599E4B92F1BCD20FA72A21839BEA5F244A98330C81EA48812F16CEE8D8EE3"),
"inputs-before.json":(6933,"772350A1FD0A565DC836C1F52C45FBEBB0A2E84AE32D0511E21593F201636309"),
"inputs-after.json":(6933,"772350A1FD0A565DC836C1F52C45FBEBB0A2E84AE32D0511E21593F201636309"),
"00-record.json":(430304,"AC328301A618805553C4E4493AEC234CA0E54DBF722718D03C5E010F67D6A529"),
"01-record.json":(431320,"8BD07E568B1BA021290052538A4D4DE75D22E4C24398E5D5BFF8525E1A1C0184"),
"02-record.json":(5683289,"C5A56A607A7D3299A210A9849EFAD4F7CEB4AEF0001D14212BFEC187A1B1C8A8"),
"03-record.json":(5667553,"AEF09548DAEE0EC0AD014F724063CAACC69C82BF3E866F3C6804E12CE974BEBB"),
"04-record.json":(5652562,"191F1F19742A367BB0D1ADAD4C32136360DBE71E4D1E191EA6816F86F14CCB69"),
"05-record.json":(5660602,"9D14279637163303B4201D06CE7F7E2FB7680B4CA6AD591C08A580CBB6722F0E"),
"06-record.json":(431248,"664DB1BF9E260644933C79E753C3149F31F5B12022521B9F043F3FE92B62020F")}
REQUIRED=(
"experiments/m192e-campaign-runner/run.py","experiments/m192e-campaign-runner/durable.py",
"experiments/m192e-campaign-runner/launch.py","experiments/m192e-campaign-runner/verify.py",
"experiments/m192e-campaign-runner/preregistration.md","experiments/m192e-campaign-runner/.gitattributes",
"experiments/m192e-campaign-runner/prepare.py","experiments/m192e-campaign-runner/preparation.md",
"experiments/m192c-sampler/sampler.py","experiments/m192b-verifier/verify.py",
"experiments/m192d-production-rehearsal/run.py","experiments/m192d-production-rehearsal/independent-verify.py",
"experiments/M192-m12-certify/protocol.json","experiments/M192-m12-certify/verify.py",
"scripts/check-defaults.py","experiments/m12-scorecard/m12-harness.py",
"experiments/m193c-output-grid/bounded-process.py","experiments/m193c-output-grid/saved-completion-publication.py",
"experiments/m193c-output-grid/sift-lightglue-saved-completion-run.py")
def need(value,message):
    if not value:raise ValueError(message)
def guard():
    need(time.process_time()<=10 and time.monotonic()-START<=20,"preparation10CPU20wall")
def path(value,missing=False):
    p=Path(os.path.abspath(value))
    for part in (p,*p.parents):
        try:s=part.lstat()
        except FileNotFoundError:need(missing,"missing lexical path");continue
        need(not part.is_symlink() and not(getattr(s,"st_file_attributes",0)&0x400),"lexical reparse")
    return p.resolve()
def shape(ref):
    need(type(ref) is dict and set(ref)=={"path","bytes","sha256"} and type(ref["path"]) is str and
        Path(ref["path"]).is_absolute() and type(ref["bytes"]) is int and ref["bytes"]>=0 and
        type(ref["sha256"]) is str and len(ref["sha256"])==64 and
        all(x in "0123456789ABCDEFabcdef" for x in ref["sha256"]),"FileRef shape")
def read(p,cap=8*MIB,expected=None):
    guard();p=path(p);before=p.stat(follow_symlinks=False)
    fields=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,getattr(x,"st_file_attributes",0),x.st_nlink)
    need(stat.S_ISREG(before.st_mode) and before.st_size<=cap,"bounded plain metadata/source")
    with p.open("rb") as stream:
        opened=os.fstat(stream.fileno());need(fields(opened)==fields(before),"opened identity")
        data=stream.read(cap+1);after_handle=os.fstat(stream.fileno())
    need(fields(before)==fields(opened)==fields(after_handle)==fields(p.stat(follow_symlinks=False)) and
        len(data)==before.st_size<=cap,"same complete bytes")
    ref=dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest().upper())
    if expected is not None:
        shape(expected);need(path(expected["path"])==p and ref["bytes"]==expected["bytes"] and
            ref["sha256"]==expected["sha256"].upper(),"exact held input")
    guard();return data,ref
def parse(data):
    def pairs(rows):
        out={}
        for k,v in rows:need(k not in out,"duplicate JSON key");out[k]=v
        return out
    def bad(_):raise ValueError("nonfinite JSON")
    value=json.loads(data,object_pairs_hook=pairs,parse_constant=bad)
    def finite(x):
        if type(x) is float:need(math.isfinite(x),"overflow JSON float")
        elif type(x) is list:
            for child in x:finite(child)
        elif type(x) is dict:
            for child in x.values():finite(child)
    finite(value);return value
def encode(value):return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def pinned(p,size,digest):
    data,ref=read(p,expected=dict(path=str(p.resolve()),bytes=size,sha256=digest))
    return parse(data),ref
def output_ref(record):
    # Inherited expected identity, never a claim that this preparer read a TIFF.
    return dict(path=str(Path(record["output_path"]).resolve()),bytes=record["tiff"]["output_bytes"],
                sha256=record["tiff"]["output_sha256"])
def write(p,data):
    need(0<len(data)<=128*1024 and not p.exists(),"fresh bounded preparation artifact")
    with p.open("xb") as stream:
        need(stream.write(data)==len(data),"complete preparation write");stream.flush();os.fsync(stream.fileno())
    actual,ref=read(p,128*1024);need(actual==data,"same preparation readback");return ref
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",action="append",nargs=3,metavar=("PATH","BYTES","SHA256"),required=True)
    parser.add_argument("--review",action="append",type=Path,required=True)
    parser.add_argument("--campaign-id",required=True)
    parser.add_argument("--output-name",required=True)
    parser.add_argument("--preparation-name",required=True)
    args=parser.parse_args()
    need(sys.dont_write_bytecode and Path.cwd().resolve()==ROOT,"exact no-bytecode root execution")
    need(str(UUID(args.campaign_id))==args.campaign_id,"canonical campaign UUID")
    need(Path(args.output_name).name==args.output_name and args.output_name.startswith("rehearsal-") and
        Path(args.preparation_name).name==args.preparation_name and args.preparation_name.startswith("preparation-"),
        "fresh direct-child names")
    out=path(HERE/args.output_name,True);dest=path(HERE/args.preparation_name,True)
    need(all(not p.exists() for p in (out,out.with_name(out.name+"-outer"),dest)),"fresh paired output/preparation")
    sources={}
    for name,size,digest in args.source:
        p=path(name);ref=dict(path=str(p),bytes=int(size),sha256=digest.upper());shape(ref)
        need(ref["bytes"]>0 and p.is_relative_to(ROOT) and str(p) not in sources,"positive unique owned source")
        read(p,expected=ref);sources[str(p)]=ref
    need({str((ROOT/p).resolve()) for p in REQUIRED}<=sources.keys(),"complete minimum source closure")
    need(all(str(path(p)) in sources for p in args.review),"held independent review in closure")
    values={};refs={}
    for name,(size,digest) in OLD_PINS.items():values[name],refs[name]=pinned(OLD/name,size,digest)
    independent,iref=pinned(OLD.parent/"independent-verification.json",32377,"083CDCD9532B51B6087A9544044318634B88FB0983C4CA2C02FD50D8C3CB6488")
    protocol,pref=pinned(PROTOCOL,9038,"E10723DDEF7D60D7A4C202E726ED998BB4CC7FF95FB3B6ABAA203D98219D9898")
    need(pref==sources[str(PROTOCOL)],"exact frozen protocol in source closure")
    summary=values["summary.json"];freeze=values["source-freeze.json"];positive=values["02-record.json"]
    need(summary["schema"]=="m192d-rehearsal-v1" and summary["status"]=="NONPERTURBATION_VERIFIED" and
        summary["completed"]==7 and summary["identity_and_execution"] is True and
        independent["schema"]=="m192d-independent-artifact-review-v1" and independent["status"]=="PASS" and
        Path(independent["author_output_directory"]).resolve()==OLD,"exact admitted old package")
    inputs=values["inputs-before.json"]
    need(inputs==values["inputs-after.json"] and len(inputs)==33 and
        [Path(r["path"]).name for r in inputs]==[f"DSC{i:05d}.ARW" for i in range(1,34)] and
        all(Path(r["path"]).parent==Path(protocol["inputs"]["33"]) for r in inputs),"literal canonical old33 list")
    rows=[]
    for i in range(7):
        record=values[f"{i:02d}-record.json"];r=output_ref(record);shape(r)
        expected=independent["rows"][i]
        need(record["index"]==expected["index"]==i and record["returncode"]==0 and
            record["identity_matches"] is True and record["terminal_matches"] is True and
            r["bytes"]==197798956 and r["sha256"]==expected["output_sha256"]==freeze["reference_output_sha256"] and
            record["tiff"]["pixel_sha256"]==expected["pixel_sha256"]==freeze["reference_pixel_sha256"],
            "exact independently reviewed old output row")
        rows.append(dict(index=i,record=refs[f"{i:02d}-record.json"],output=r))
    need(positive["mode"]=="on" and positive["index"]==2,"same actual observed positive")
    binary_path=Path(positive["argv"][0]);binary_old=next(r for r in freeze["sources"] if Path(r["path"])==binary_path)
    _,binary=read(binary_path,64*MIB)
    need(binary["bytes"]==binary_old["bytes"] and binary["sha256"]==binary_old["sha256"]==
        positive["binary_sha256"],"opaque frozen binary identity")
    side_path=ROOT/protocol["sidecars"]["33"]["path"];_,sidecar=read(side_path)
    need(sidecar["sha256"]==protocol["sidecars"]["33"]["sha256"]==positive["sidecar_sha256"]==
        freeze["sidecar"]["sha256"] and sidecar["bytes"]==freeze["sidecar"]["bytes"],"same frozen sidecar")
    for old in freeze["sources"]:
        p=str(Path(old["path"]).resolve())
        if p in sources:need(sources[p]["bytes"]==old["bytes"] and sources[p]["sha256"]==old["sha256"],"inherited source unchanged")
    _,python=read(Path(sys.executable),64*MIB)
    preserved=dict(schema="m192e-prior-output-preservation-v1",rows=rows)
    preserved_raw=encode(preserved);preserved_path=dest/"preserved.json"
    preserved_ref=dict(path=str(preserved_path),bytes=len(preserved_raw),sha256=hashlib.sha256(preserved_raw).hexdigest().upper())
    plan=dict(schema="m192e-rehearsal-plan-v1",campaign_id=args.campaign_id,source_bindings=sorted(sources.values(),key=lambda x:x["path"]),
        baseline=dict(summary=refs["summary.json"],independent_review=iref,source_freeze=refs["source-freeze.json"],
            inputs=refs["inputs-before.json"],record=refs["02-record.json"],preserved=preserved_ref),
        python=python,binary=binary,sidecar=sidecar,output_directory=str(out))
    plan_raw=encode(plan);plan_path=dest/"plan.json";plan_sha=hashlib.sha256(plan_raw).hexdigest().upper()
    command=[python["path"],"-B",str(HERE/"launch.py"),"--plan",str(plan_path),"--plan-sha256",plan_sha]
    receipt=dict(schema="m192e-metadata-preparation-v1",status="COMPLETE_METADATA_ONLY_NOT_RELEASE",
        source=sources[str(Path(__file__).resolve())],command=sys.orig_argv,
        plan=dict(path=str(plan_path),bytes=len(plan_raw),sha256=plan_sha),preserved=preserved_ref,
        launch_command=command,verification_command=[python["path"],"-B",str(HERE/"verify.py"),
            "--plan",str(plan_path),"--plan-sha256",plan_sha,"--outer",str(out.with_name(out.name+"-outer")/"outer.json"),
            "--outer-sha256","ACTUAL_OUTER_SHA256"],source_reviews=[sources[str(path(p))] for p in args.review],
        raw_payloads_opened=0,tiff_payloads_opened=0,subject_imports=0,subject_launches=0,
        old_output_binding_scope="Inherited expected identities from held actual records; future worker verifies actual before/after bytes.",
        preparation_sample=None,
        publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),
        external_preparation_receipt_required=True,independent_release_required=True)
    receipt_raw=encode(receipt)
    need(max(map(len,(preserved_raw,plan_raw,receipt_raw)))<=128*1024 and
        sum(map(len,(preserved_raw,plan_raw,receipt_raw)))<=256*1024,"entire preparation output family")
    for ref in [*sources.values(),*refs.values(),iref,pref,python,binary,sidecar]:
        read(ref["path"],64*MIB if ref in (python,binary) else 8*MIB,expected=ref)
    receipt["preparation_sample"]=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
    receipt_raw=encode(receipt)
    need(len(receipt_raw)<=128*1024 and len(preserved_raw)+len(plan_raw)+len(receipt_raw)<=256*1024,"final preparation family")
    guard();need(time.process_time()+.25<=10 and time.monotonic()-START+.5<=20,"reserved final preparation work")
    dest.mkdir();write(preserved_path,preserved_raw);write(plan_path,plan_raw);actual=write(dest/"preparation.json",receipt_raw)
    print(json.dumps(dict(status=receipt["status"],preparation=actual,plan=receipt["plan"]),allow_nan=False),flush=True)
if __name__=="__main__":main()
