#!/usr/bin/env python3
"""Independent literal fixtures and saved checks for the common-RGB stack consumer.
No subject imports, external image readers, product launch or RAW.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
BASE = SELF.parent
PROFILE = ROOT / "experiments/M165-common-input/linear-prophoto-d50-v1.icc"
PROFILE_SHA = "16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef"
WIDTH, HEIGHT = 128, 96
MAX_TIFF = 128 * 1024
MAX_JSON = 256 * 1024
MAX_FILES = 4 * 1024 * 1024
DOMAIN = b"common-tiff-stack-rademacher-v1"
CONSTANTS = ((12000,17000,23000),(15000,20000,26000),(24000,32000,38000))
MEAN = (17000,23000,29000)
LEVELS = ((128,96),(64,48),(32,24),(16,12))
START = time.perf_counter()
START_CPU = time.process_time()
# Exact MergeConfig literal is supplied only after the author's source contract is held.
MERGE = {"bands":3,"gate":2,"exponent":2,"sharpen_per_octave":1.4,"select":"SoftPower","admission":"HardFloor","base":"Mean","mean_coarse":0,"hull":"InputRange","hull_lambda":2,"hull_low_only":False,"fallback":"Mean","fallback_k":3,"fallback_power":4,"hull_from_level":1,"significance_scale":0}
CASES = (
    ("constant", "off", None), ("address", "off", None),
    ("mixed-null", "on", None),
    ("mixed-noisy", "off", None), ("mixed-noisy", "on", None),
    ("mixed-noisy", "placebo", None),
    ("mixed-noisy", "off", "noise-provenance"),
    ("mixed-noisy", "off", "variance-one"),
    ("mixed-noisy", "off", "profile"),
    ("mixed-noisy", "off", "camera-output"),
    ("mixed-noisy", "off", "third-size"),
    ("mixed-noisy", "off", "third-payload"),
)
RECIPE = {
    "schema":"common-tiff-stack-independent-recipe-v1",
    "grid":[WIDTH,HEIGHT,3], "constant_rgb":CONSTANTS, "mean_rgb":MEAN,
    "address":"R=4000+101*x+7*y;G=18000+13*x+83*y;B=36000+47*x+19*y",
    "address_patch":{"xyxy":[16,24,48,56],"rgb":[8192,24576,49152]},
    "mixed_base":[14000,24000,34000],
    "mixed_texture":"x>=64: +/-4096; positive iff (x//4+y//4)%2==0",
    "noise":{"domain":DOMAIN.decode(),"counter":"LE u32 frame,y,x,channel",
             "sign":"+8 iff SHA256(domain+counter)[0]&1, else -8",
             "rgb_covariance":[[64,0,0],[0,64,0],[0,0,64]],
             "proxy_variance":24,"law_scope":"declared deterministic simulation, not empirical independence"},
    "strip_rows":[24,32,48],"profile_sha256":PROFILE_SHA,
}

def need(ok, label):
    if not ok:
        raise ValueError(label)

def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def typed_int(v, low=0, high=2**63-1):
    return type(v) is int and low <= v <= high

def sha(v):
    return type(v) is str and len(v)==64 and all(c in "0123456789abcdef" for c in v)

def shared(s):
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,
            getattr(s,"st_file_attributes",0))

def full(s):
    return shared(s)+(s.st_ctime_ns,)

def read_bytes(path, cap, *, empty=False):
    path=Path(path)
    s=path.lstat()
    need(stat.S_ISREG(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400
         and s.st_nlink==1, "owned ordinary single-link file")
    need((0 if empty else 1)<=s.st_size<=cap, "read extent cap")
    with path.open("rb") as f:
        a=os.fstat(f.fileno())
        need(shared(s)==shared(a), "path to opened handle identity")
        raw=f.read(s.st_size+1)
        z=os.fstat(f.fileno())
    t=path.lstat()
    need(full(s)==full(t) and full(a)==full(z) and len(raw)==s.st_size,
         "same API stable read")
    return raw

def file_ref(path, raw=None, *, empty=False):
    path=Path(path).resolve()
    if raw is None:
        raw=read_bytes(path,MAX_JSON if path.suffix==".json" else MAX_TIFF,empty=empty)
    return {"path":str(path),"bytes":len(raw),"sha256":digest(raw)}

def read_ref(ref, cap, *, anchor=ROOT, empty=False):
    need(type(ref) is dict and set(ref)=={"path","bytes","sha256"}, "closed FileRef")
    need(type(ref["path"]) is str and ref["path"] and typed_int(ref["bytes"],0 if empty else 1,cap)
         and sha(ref["sha256"]), "typed FileRef")
    p=Path(ref["path"])
    if not p.is_absolute():
        p=anchor/p
    raw=read_bytes(p,cap,empty=empty)
    need(len(raw)==ref["bytes"] and digest(raw)==ref["sha256"], "exact FileRef bytes")
    return raw,p.resolve()

def strict_json(raw):
    def pairs(items):
        result={}
        for k,v in items:
            need(k not in result, "duplicate JSON key")
            result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))

def check_time(cpu, wall):
    need(time.process_time()-START_CPU<=cpu and time.perf_counter()-START<=wall,
         "own finite work allowance")

def write_fresh(path, raw, cap):
    need(len(raw)<=cap, "fixed output extent")
    with Path(path).open("xb") as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    need(read_bytes(path,cap,empty=not raw)==raw, "new file readback")
    return file_ref(path,raw)

def pixels(kind, frame, width=WIDTH, height=HEIGHT):
    need(kind in {"constant","address","mixed-null","mixed-noisy"} and
         typed_int(frame,0,2), "fixed literal fixture")
    output=[]
    for y in range(height):
        for x in range(width):
            if kind=="constant":
                rgb=CONSTANTS[frame]
            elif kind=="address":
                rgb=(4000+101*x+7*y,18000+13*x+83*y,36000+47*x+19*y)
                if 16<=x<48 and 24<=y<56:
                    rgb=(8192,24576,49152)
            else:
                d=0 if x<64 else (4096 if (x//4+y//4)%2==0 else -4096)
                rgb=tuple(v+d for v in (14000,24000,34000))
                if kind=="mixed-noisy":
                    rgb=tuple(v+(8 if hashlib.sha256(DOMAIN+struct.pack("<4I",frame,y,x,c)).digest()[0]&1 else -8)
                              for c,v in enumerate(rgb))
            need(all(typed_int(v,0,65535) for v in rgb), "unclipped literal fixture")
            output.extend(rgb)
    return output

def payload(values):
    return struct.pack("<"+"H"*len(values),*values)

def make_tiff(values,width,height,icc,provenance,strip_rows):
    """Independent container construction: payload first, IFD last, descending tags."""
    need(typed_int(width,1,128) and typed_int(height,1,96) and len(values)==width*height*3,
         "fixture shape")
    need(type(icc) is bytes and len(icc)==548 and digest(icc)==PROFILE_SHA, "held ICC")
    raw=bytearray(b"II"+struct.pack("<HI",42,0))
    offset=len(raw);rgb=payload(values);raw.extend(rgb)
    offsets=[];counts=[]
    for y in range(0,height,strip_rows):
        offsets.append(offset+y*width*6);counts.append(min(strip_rows,height-y)*width*6)
    fields={
        256:(4,1,struct.pack("<I",width)),257:(4,1,struct.pack("<I",height)),
        258:(3,3,struct.pack("<3H",16,16,16)),259:(3,1,struct.pack("<H",1)),
        262:(3,1,struct.pack("<H",2)),270:(2,0,canonical(provenance)+b"\0"),
        273:(4,len(offsets),struct.pack("<"+"I"*len(offsets),*offsets)),
        277:(3,1,struct.pack("<H",3)),278:(4,1,struct.pack("<I",strip_rows)),
        279:(4,len(counts),struct.pack("<"+"I"*len(counts),*counts)),
        284:(3,1,struct.pack("<H",1)),339:(3,3,struct.pack("<3H",1,1,1)),
        34675:(7,len(icc),icc),
    }
    entries=[]
    for tag in sorted(fields,reverse=True):
        typ,count,data=fields[tag]
        if tag==270:
            count=len(data)
        if len(data)<=4:
            encoded=data.ljust(4,b"\0")
        else:
            if len(raw)&1:raw.append(0)
            at=len(raw);raw.extend(data);encoded=struct.pack("<I",at)
        entries.append(struct.pack("<HHI",tag,typ,count)+encoded)
    if len(raw)&1:raw.append(0)
    ifd=len(raw);raw[4:8]=struct.pack("<I",ifd)
    raw.extend(struct.pack("<H",len(entries))+b"".join(entries)+b"\0"*4)
    need(len(raw)<=MAX_TIFF, "fixture TIFF cap")
    return bytes(raw)

def inspect_tiff(raw, *, output=False):
    """Parse same authenticated buffer; strip metadata is independent of producer receipts."""
    need(type(raw) is bytes and 8<=len(raw)<=MAX_TIFF, "TIFF extent")
    need(raw[:4]==b"II*\0", "LE classic TIFF")
    at=struct.unpack_from("<I",raw,4)[0]
    need(8<=at<=len(raw)-6, "IFD location")
    count=struct.unpack_from("<H",raw,at)[0]
    end=at+2+12*count+4
    need(13<=count<=18 and end<=len(raw), "IFD table cap")
    need(struct.unpack_from("<I",raw,end-4)[0]==0, "one TIFF image")
    used=[(0,8,"header"),(at,end,"IFD")];tags={}
    sizes={1:1,2:1,3:2,4:4,5:8,7:1}
    required={256,257,258,259,262,270,273,277,278,279,284,339,34675}
    allowed=required|({274,282,283,296,305,317} if output else set())
    for i in range(count):
        pos=at+2+12*i;tag,typ,n=struct.unpack_from("<HHI",raw,pos)
        need(tag in allowed and tag not in tags and typ in sizes and n>0, "TIFF tag schema")
        extent=n*sizes[typ]
        if extent<=4:
            data=raw[pos+8:pos+8+extent]
        else:
            off=struct.unpack_from("<I",raw,pos+8)[0]
            need(8<=off and off+extent<=len(raw), "TIFF field extent")
            used.append((off,off+extent,"tag-"+str(tag)));data=raw[off:off+extent]
        tags[tag]=(typ,n,data)
    need(required<=set(tags), "required RGB TIFF tags")
    def numbers(tag):
        typ,n,data=tags[tag]
        need(typ in {3,4}, "integer structural tag")
        return struct.unpack("<"+("H" if typ==3 else "I")*n,data)
    def scalar(tag,value=None):
        v=numbers(tag);need(len(v)==1, "scalar structural tag")
        if value is not None:need(v[0]==value, "fixed structural value")
        return v[0]
    width,height=scalar(256),scalar(257)
    need(1<=width<=128 and 1<=height<=96, "bounded RGB geometry")
    for tag,value in ((259,1),(262,2),(277,3),(284,1)):
        scalar(tag,value)
    need(numbers(258)==(16,16,16) and numbers(339)==(1,1,1), "RGB16 unsigned samples")
    if 274 in tags:scalar(274,1)
    if output:
        need(317 in tags,"output predictor present");scalar(317,1)
    if 296 in tags:need(scalar(296) in (1,2,3), "resolution unit")
    for tag in (282,283):
        if tag in tags:
            typ,n,data=tags[tag];need(typ==5 and n==1 and struct.unpack("<2I",data)[1]>0,
                                    "positive rational resolution")
    rows=scalar(278);need(1<=rows<2**32, "strip row extent")
    offsets,counts=numbers(273),numbers(279)
    need(len(offsets)==len(counts)==(height+rows-1)//rows, "complete strip population")
    pieces=[]
    for i,(off,n) in enumerate(zip(offsets,counts)):
        need(n==min(rows,height-i*rows)*width*6 and 8<=off and off+n<=len(raw),
             "exact strip byte extent")
        used.append((off,off+n,"strip-"+str(i)));pieces.append(raw[off:off+n])
    used.sort()
    need(all(a[1]<=b[0] for a,b in zip(used,used[1:])), "nonoverlapping TIFF regions")
    if output:
        need(305 in tags and tags[305][0]==2 and tags[305][2].endswith(b"\0"), "output Software ASCII")
        need(tags[305][2][:-1]==b"strehl-common-input common-tiff-stack-v1", "fixed output software")
    need(tags[270][0]==2 and tags[270][2].endswith(b"\0"), "ASCII description")
    description=tags[270][2][:-1].decode("utf-8")
    need(tags[34675][0] in (1,7), "ICC byte type")
    icc=tags[34675][2]
    need(len(icc)>=128 and icc[36:40]==b"acsp", "ICC signature")
    rgb=b"".join(pieces)
    values=list(struct.unpack("<"+"H"*(len(rgb)//2),rgb))
    return {"width":width,"height":height,"file_sha256":digest(raw),
            "pixel_sha256":digest(rgb),"icc_sha256":digest(icc),
            "description":description,"pixels":values,
            "strip_count":len(pieces),"tag_ids":sorted(tags),"payload":rgb,
            "_raw":raw,"_pixel_offsets":list(offsets),
            "_icc_offset":next(a for a,b,label in used if label=="tag-34675")}

def compare_pixels(actual,expected,label):
    need(len(actual)==len(expected), label+": geometry")
    mismatch=next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None)
    need(mismatch is None, label+": literal RGB codes")
    return {"samples":len(expected),"exact":True}

def compare_observer(images):
    need(len(images)==3, "three observer arms")
    need(len({x["file_sha256"] for x in images})==1, "observer whole TIFF equality")
    need(len({x["pixel_sha256"] for x in images})==1, "observer pixel equality")
    return {"whole_tiff_equal":True,"pixel_equal":True}

def expected_noise(model):
    need(model in {"synthetic-noiseless-v1","synthetic-independent-rademacher8-v1"},
         "admitted simulation noise")
    v=0 if model=="synthetic-noiseless-v1" else 64
    return {"model":model,"units":"rgb16-code-squared",
            "rgb_covariance":[[v,0,0],[0,v,0],[0,0,v]],
            "proxy_variance":0 if v==0 else 24,"band_transfer":"core-white-bandgain-v1"}

def number_equal(actual,expected):
    return type(actual) in (int,float) and math.isfinite(actual) and actual==expected

def noise_contract(noise,model):
    expected=expected_noise(model)
    need(type(noise) is dict and set(noise)==set(expected), "closed noise fields")
    for key in ("model","units","band_transfer"):
        need(type(noise[key]) is str and noise[key]==expected[key], "exact noise semantics")
    cov=noise["rgb_covariance"]
    need(type(cov) is list and len(cov)==3 and all(type(row) is list and len(row)==3 for row in cov),
         "RGB covariance shape")
    need(all(number_equal(cov[i][j],expected["rgb_covariance"][i][j]) for i in range(3) for j in range(3))
         and number_equal(noise["proxy_variance"],expected["proxy_variance"]),
         "exact injected noise declaration")
    return True


def source_authority(expected):
    raw=read_bytes(SELF,128*1024)
    need(sha(expected) and digest(raw)==expected, "checker source identity")
    spec_path=BASE/"independent-controls-spec.md"
    spec_raw=read_bytes(spec_path,16*1024)
    icc=read_bytes(PROFILE,548)
    need(len(icc)==548 and digest(icc)==PROFILE_SHA, "frozen profile identity")
    return file_ref(SELF,raw),file_ref(spec_path,spec_raw),icc

def prepare(args):
    own,spec,icc=source_authority(args.source_sha256)
    need(MERGE is not None, "held complete merge contract")
    out=Path(args.output).resolve()
    need(out==BASE/"prepare-1/fixtures" and not out.exists(), "fresh fixed fixture root")
    need(out.parent.is_dir(), "owned prepare parent exists")
    out.mkdir()
    generated=[]
    recipe_raw=canonical(RECIPE)+b"\n"
    recipe_ref=write_fresh(out/"recipe.json",recipe_raw,8192);generated.append(recipe_ref)
    recipe_sha=digest(canonical(RECIPE))
    common={}
    for kind in ("constant","address","mixed-null","mixed-noisy"):
        model="synthetic-independent-rademacher8-v1" if kind=="mixed-noisy" else "synthetic-noiseless-v1"
        entries=[]
        for frame,rows in enumerate((24,32,48)):
            ident=kind+"-"+str(frame)
            prov={"schema":"common-tiff-stack-input-v1","id":ident,"fixture_sha256":recipe_sha,
                  "color_space":"linear-prophoto-d50","noise_model":model,
                  "geometry":"identity-common-rgb-pixels"}
            values=pixels(kind,frame)
            raw=make_tiff(values,WIDTH,HEIGHT,icc,prov,rows)
            got=inspect_tiff(raw)
            compare_pixels(got["pixels"],values,"fixture container roundtrip")
            need(got["icc_sha256"]==PROFILE_SHA and strict_json(got["description"])==prov,
                 "fixture colour/provenance")
            f=write_fresh(out/(ident+".tiff"),raw,MAX_TIFF);generated.append(f)
            entries.append({"id":ident,"tiff":f,"pixel_sha256":got["pixel_sha256"],"provenance":prov})
            check_time(5,10)
        common[kind]=entries
    # Two distinct actual negative files, each bound by the fixture index.
    original=common["mixed-noisy"][2]
    prov=original["provenance"]
    small_values=pixels("mixed-noisy",2,127,96)
    small=make_tiff(small_values,127,96,icc,prov,48)
    small_ref=write_fresh(out/"wrong-size-third.tiff",small,MAX_TIFF);generated.append(small_ref)
    changed_values=pixels("mixed-noisy",2);changed_values[0]+=1
    changed=make_tiff(changed_values,WIDTH,HEIGHT,icc,prov,48)
    changed_ref=write_fresh(out/"altered-third.tiff",changed,MAX_TIFF);generated.append(changed_ref)
    cases=[]
    for ordinal,(kind,observer,fault) in enumerate(CASES):
        model="synthetic-independent-rademacher8-v1" if kind=="mixed-noisy" else "synthetic-noiseless-v1"
        case_dir=BASE/"render-1"/("case-"+str(ordinal).zfill(2))
        inputs=strict_json(canonical(common[kind]))
        manifest={"schema":"common-tiff-stack-v1",
                  "grid":{"width":WIDTH,"height":HEIGHT,"channels":"RGB","coordinates":"identity-common-rgb-pixels"},
                  "color":{"space":"linear-prophoto-d50","icc":file_ref(PROFILE,icc)},
                  "noise":expected_noise(model),"merge":MERGE,
                  "inputs":inputs,
                  "output":{"path":str(case_dir/"output.tiff"),"space":"linear-prophoto-d50",
                            "sample_format":"RGB16","quantization":"finite-clamp-round-half-away-v1"}}
        if fault=="noise-provenance":manifest["noise"]["model"]="unadmitted-developed-rgb-v1"
        elif fault=="variance-one":manifest["noise"]["proxy_variance"]=1
        elif fault=="profile":manifest["color"]["icc"]["sha256"]="0"*64
        elif fault=="camera-output":manifest["output"]["space"]="camera-native"
        elif fault=="third-size":
            inputs[2]["tiff"]=small_ref
            inputs[2]["pixel_sha256"]=inspect_tiff(small)["pixel_sha256"]
        elif fault=="third-payload":
            # Actual file is bound above; product must reject the old expected identity.
            inputs[2]["tiff"]["path"]=changed_ref["path"]
        elif fault is not None:raise ValueError("fixed case fault")
        m=write_fresh(out/("case-"+str(ordinal).zfill(2)+".json"),canonical(manifest)+b"\n",64*1024)
        generated.append(m)
        cases.append({"ordinal":ordinal,"id":fault or (("noisy" if kind=="mixed-noisy" else kind)+"-"+observer),"fixture_kind":kind,
                      "observer":observer,"expected_exit_code":int(fault is not None),
                      "expected_folded_frames":2 if fault in ("third-size","third-payload") else (0 if fault else 3),
                      "manifest":m,"command":["ACTUAL_BINARY_PATH","--stack-manifest",m["path"],
                        "--manifest-sha256",m["sha256"],"--report",str(case_dir/"report.json"),
                        "--observer",observer],
                      "output_path":str(case_dir/"output.tiff"),"report_path":str(case_dir/"report.json")})
        check_time(5,10)
    index={"schema":"common-tiff-stack-independent-fixtures-v1","source":own,"spec":spec,
           "profile":file_ref(PROFILE,icc),"recipe":recipe_ref,"recipe_sha256":recipe_sha,
           "generated_files":generated,"cases":cases}
    need(len(canonical(index))+sum(x["bytes"] for x in generated)+64*1024<MAX_FILES,
         "full fixture file allowance")
    index_ref=write_fresh(out/"index.json",canonical(index)+b"\n",MAX_JSON)
    check_time(5,10)
    return {"schema":"common-tiff-stack-independent-preparation-v1",
            "status":"PREPARED_UNRUN_FIXTURES","index":index_ref,"cases":12,
            "generated_files":len(generated)+1,
            "file_bytes":sum(x["bytes"] for x in generated)+index_ref["bytes"],
            "scope":"literal fixture preparation only; no product execution"}

def same_ref(a,b):
    def path(ref):
        p=Path(ref["path"])
        return (p if p.is_absolute() else ROOT/p).resolve()
    return (type(a) is dict and type(b) is dict and set(a)==set(b)=={"path","bytes","sha256"}
            and path(a)==path(b) and a["bytes"]==b["bytes"] and a["sha256"]==b["sha256"])

def fixture_authority(args):
    raw=read_bytes(args.fixtures,MAX_JSON)
    need(digest(raw)==args.fixtures_sha256 and Path(args.fixtures).resolve()==BASE/"prepare-1/fixtures/index.json",
         "actual fixed fixture index")
    v=strict_json(raw);own,spec,icc=source_authority(args.source_sha256)
    need(set(v)=={"schema","source","spec","profile","recipe","recipe_sha256","generated_files","cases"} and
         v["schema"]=="common-tiff-stack-independent-fixtures-v1", "closed fixture index")
    need(same_ref(v["source"],own) and same_ref(v["spec"],spec) and
         same_ref(v["profile"],file_ref(PROFILE,icc)), "fixture source/spec/profile authority")
    recipe,rp=read_ref(v["recipe"],8192)
    need(strict_json(recipe)==strict_json(canonical(RECIPE)) and v["recipe_sha256"]==digest(canonical(RECIPE)),
         "fixed independently declared recipe")
    fs=v["generated_files"];need(type(fs) is list and len(fs)==27,"fixed generated file population")
    actual={};total=0
    for ref in fs:
        b,p=read_ref(ref,MAX_JSON)
        need(p.parent==Path(args.fixtures).parent and p.name not in actual and p.name!="index.json","generated file namespace")
        actual[p.name]=(ref,b);total+=len(b)
    need(total+len(raw)<=MAX_FILES,"fixture total extent")
    need(rp==Path(args.fixtures).parent/"recipe.json" and "recipe.json" in actual and
         same_ref(actual["recipe.json"][0],v["recipe"]),"generated recipe exact association")
    for kind in ("constant","address","mixed-null","mixed-noisy"):
        for frame in range(3):
            name=kind+"-"+str(frame)+".tiff";got=inspect_tiff(actual[name][1])
            compare_pixels(got["pixels"],pixels(kind,frame),"literal prepared RGB")
            model="synthetic-independent-rademacher8-v1" if kind=="mixed-noisy" else "synthetic-noiseless-v1"
            need(got["icc_sha256"]==PROFILE_SHA and strict_json(got["description"])=={
                "schema":"common-tiff-stack-input-v1","id":kind+"-"+str(frame),"fixture_sha256":v["recipe_sha256"],
                "color_space":"linear-prophoto-d50","noise_model":model,"geometry":"identity-common-rgb-pixels"},
                "literal input provenance")
    small=inspect_tiff(actual["wrong-size-third.tiff"][1])
    need((small["width"],small["height"])==(127,96),"wrong-size witness")
    compare_pixels(small["pixels"],pixels("mixed-noisy",2,127,96),"wrong-size literal pixels")
    changed=inspect_tiff(actual["altered-third.tiff"][1]);expected=pixels("mixed-noisy",2);expected[0]+=1
    compare_pixels(changed["pixels"],expected,"altered third literal pixel")
    rows=v["cases"];need(type(rows) is list and len(rows)==12,"fixed 12 rows")
    for i,(kind,observer,fault) in enumerate(CASES):
        row=rows[i];case=BASE/"render-1"/f"case-{i:02}";name=f"case-{i:02}.json"
        ident=fault or (("noisy" if kind=="mixed-noisy" else kind)+"-"+observer)
        need(set(row)=={"ordinal","id","fixture_kind","observer","expected_exit_code","expected_folded_frames",
             "manifest","command","output_path","report_path"} and type(row["ordinal"]) is int and row["ordinal"]==i and
             row["id"]==ident and row["fixture_kind"]==kind and row["observer"]==observer,"fixed case row")
        need(type(row["expected_exit_code"]) is int and row["expected_exit_code"]==int(i>=6) and
             type(row["expected_folded_frames"]) is int and row["expected_folded_frames"]==(2 if i>=10 else (0 if fault else 3)),
             "fixed expected dispositions")
        need(same_ref(row["manifest"],actual[name][0]) and row["output_path"]==str(case/"output.tiff") and
             row["report_path"]==str(case/"report.json"),"case path bindings")
        need(row["command"]==["ACTUAL_BINARY_PATH","--stack-manifest",str(Path(args.fixtures).parent/name),
             "--manifest-sha256",row["manifest"]["sha256"],"--report",row["report_path"],"--observer",observer],
             "exact command template")
        m=strict_json(actual[name][1]);noise=expected_noise("synthetic-independent-rademacher8-v1" if kind=="mixed-noisy" else "synthetic-noiseless-v1")
        if fault=="noise-provenance":noise["model"]="unadmitted-developed-rgb-v1"
        if fault=="variance-one":noise["proxy_variance"]=1
        color={"space":"linear-prophoto-d50","icc":file_ref(PROFILE,icc)}
        if fault=="profile":color["icc"]["sha256"]="0"*64
        inputs=[]
        for j in range(3):
            ref,b=actual[kind+"-"+str(j)+".tiff"];got=inspect_tiff(b);f=dict(ref);pixel=got["pixel_sha256"]
            if j==2 and fault=="third-size":f=actual["wrong-size-third.tiff"][0];pixel=small["pixel_sha256"]
            if j==2 and fault=="third-payload":f["path"]=actual["altered-third.tiff"][0]["path"]
            inputs.append({"id":kind+"-"+str(j),"tiff":f,"pixel_sha256":pixel,"provenance":strict_json(got["description"])})
        expected={"schema":"common-tiff-stack-v1","grid":{"width":128,"height":96,"channels":"RGB","coordinates":"identity-common-rgb-pixels"},
                  "color":color,"noise":noise,"merge":MERGE,"inputs":inputs,
                  "output":{"path":str(case/"output.tiff"),"space":"camera-native" if fault=="camera-output" else "linear-prophoto-d50",
                            "sample_format":"RGB16","quantization":"finite-clamp-round-half-away-v1"}}
        need(m==expected,"one exact preregistered manifest defect")
        check_time(20,30)
    return v,actual

def finite_nonnegative(v):
    return type(v) in (float,int) and math.isfinite(v) and v>=0

def job_cpu(v):
    need(type(v) is dict and all(typed_int(v.get(k)) for k in
         ("total_user_100ns","total_kernel_100ns","total_cpu_100ns","active_processes")),"typed actual Job")
    need(v["total_cpu_100ns"]==v["total_user_100ns"]+v["total_kernel_100ns"],"Job components add")
    return v["total_cpu_100ns"]/1e7

def hash_large_ref(ref,cap):
    need(type(ref) is dict and set(ref)=={"path","bytes","sha256"} and
         typed_int(ref["bytes"],1,cap) and sha(ref["sha256"]),"bounded executable FileRef")
    p=Path(ref["path"])
    if not p.is_absolute():p=ROOT/p
    before=p.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==ref["bytes"] and
         not getattr(before,"st_file_attributes",0)&0x400,"ordinary bounded executable")
    hasher=hashlib.sha256();count=0
    with p.open("rb") as f:
        opened=os.fstat(f.fileno());need(shared(before)==shared(opened),"executable handle identity")
        while True:
            chunk=f.read(min(1024*1024,ref["bytes"]-count+1))
            if not chunk:break
            count+=len(chunk);need(count<=ref["bytes"],"executable read bound");hasher.update(chunk)
            check_time(20,30)
        after=os.fstat(f.fileno())
    final=p.lstat()
    need(full(before)==full(final) and full(opened)==full(after) and count==ref["bytes"] and
         hasher.hexdigest()==ref["sha256"],"complete unchanged executable bytes")
    return p.resolve()

def saved_render_bundle(args,index):
    raw=read_bytes(args.run_bundle,64*1024)
    need(digest(raw)==args.run_bundle_sha256 and Path(args.run_bundle).resolve()==BASE/"render-bundle-1.json","actual run bundle")
    bundle=strict_json(raw);caps={"result":65536,"tail":8192,"outer":65536,"stdout":8192,"stderr":32768,"exit":1024}
    need(type(bundle) is dict and set(bundle)==set(caps),"six external roles")
    b={k:read_ref(bundle[k],cap,empty=k=="stderr")[0] for k,cap in caps.items()}
    result,tail,outer,ad=(strict_json(b[k]) for k in ("result","tail","outer","stdout"))
    need(result["schema"]=="common-tiff-stack-owned-stage-v1" and result["stage"]=="render","actual render stage")
    for k,filename in (("result","result.json"),("tail","parent-tail.json")):
        need(Path(bundle[k]["path"]).resolve()==BASE/"render-1"/filename,"render terminal path")
    need(set(outer)=={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds","stdout","stderr","exit",
         "stdout_bytes","stderr_bytes","scope"} and outer["schema"]=="common-tiff-stack-stage-external-v1","closed external capture")
    need(outer["command"]==result["invocation"] and type(outer["exit_code"]) is int and b["exit"].strip()==str(outer["exit_code"]).encode(),
         "actual invocation and exit")
    for k in ("stdout","stderr","exit"):need(same_ref(outer[k],bundle[k]),"outer stream association")
    need(outer["stdout_bytes"]==len(b["stdout"]) and outer["stderr_bytes"]==len(b["stderr"]),"outer stream extents")
    need(set(ad)=={"status","result","tail"} and ad["status"]==result["status"] and
         same_ref(ad["result"],bundle["result"]) and same_ref(ad["tail"],bundle["tail"]) and
         b["stdout"]==canonical(ad)+b"\n","exact terminal advertisement")
    need(tail["schema"]=="common-tiff-stack-parent-tail-v1" and same_ref(tail["result"],bundle["result"]),"tail result association")
    relraw,_=read_ref(result["release"],1024*1024);release=strict_json(relraw)
    need(release["schema"]=="common-tiff-stack-stage-release-v1" and release["stage"]=="render" and
         [result["release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in release["command"]]==result["invocation"],
         "exact released argv")
    need(same_ref(release["fixtures"],file_ref(args.fixtures,read_bytes(args.fixtures,MAX_JSON))),"released fixture index")
    sources=release["source_bindings"];need(type(sources) is dict and 1<=len(sources)<=512,"source map count")
    total=0
    for path,pin in sources.items():
        need(type(pin) is dict and set(pin)=={"bytes","sha256"} and typed_int(pin["bytes"],1,4*1024*1024) and sha(pin["sha256"]),"positive source pin")
        total+=pin["bytes"]
    need(total<=16*1024*1024,"source byte aggregate")
    for path,pin in sources.items():read_ref({"path":path,**pin},4*1024*1024)
    need(sources[SELF.relative_to(ROOT).as_posix()]["sha256"]==args.source_sha256,"same checker source")
    cp=(BASE/"run-stage.py").relative_to(ROOT).as_posix()
    need(same_ref(outer["source"],{"path":cp,**sources[cp]}),"actual controller source")
    exe=hash_large_ref(release["executable"],64*1024*1024)
    need(exe==BASE/"build-2/strehl-common-input.exe","actual compiled product path")
    commands=[[str(exe) if x=="ACTUAL_BINARY_PATH" else x for x in row["command"]] for row in index["cases"]]
    need(release["children"]==[{"command":c,"expected_exit_code":int(i>=6)} for i,c in enumerate(commands)],"released fixed schedule")
    observed=result["children"];need(type(observed) is list and len(observed)<=12,"actual bounded child prefix")
    children=[];cpu=0.0
    for i,ref in enumerate(observed):
        raw,p=read_ref(ref,32768);v=strict_json(raw)
        need(p==BASE/"render-1"/f"child-{i:02}.json" and v["command"]==commands[i],"actual child ordinal/command")
        log,lp=read_ref(v["log"],256*1024,empty=True)
        need(lp==BASE/"render-1"/f"child-{i:02}.log" and len(log)==v["log_bytes"],"actual linked raw child log")
        used=job_cpu(v["job_accounting"]) if v.get("job_accounting") is not None else None
        if used is not None:cpu+=used
        clean=(used is not None and v.get("terminal_job_accounting") is True and v["job_accounting"]["active_processes"]==0 and
          v.get("error") is None and v.get("cleanup_errors")==[] and v.get("direct_exit_observed") is True and
          v.get("pipe_eof_observed") is True and v.get("post_exit_drain",{}).get("completed") is True and
          v.get("termination",{}).get("attempted") is False and "compile_cleanup" not in v and
          type(v.get("exit_code")) is int and v["exit_code"]==int(i>=6))
        resources=(used is not None and used<=15 and finite_nonnegative(v.get("wall_seconds")) and v["wall_seconds"]<=15 and
          v.get("configured_job_limits")=={"flags":0x2200,"committed_bytes":256*1024*1024} and
          typed_int(v.get("job_memory",{}).get("peak_job_memory_used_bytes"),0,256*1024*1024))
        children.append({"ordinal":i,"record":v,"record_ref":ref,"raw_log":log,"process_complete":clean,
                         "resource_admissible":resources,"job_cpu_seconds":used})
    known=all(finite_nonnegative(tail.get(k)) for k in ("actual_parent_cpu_sample","whole_wall_sample","completed_child_cpu_seconds","live_child_cpu_seconds"))
    need(not known or tail["completed_child_cpu_seconds"]>=cpu,"no underreported terminal Job sum")
    complete=(result["status"]=="COMPLETE_STAGE_UNVERIFIED" and result.get("error") is None and
      result.get("finalization_errors")==[] and len(children)==12 and all(c["process_complete"] and c["resource_admissible"] for c in children) and
      outer["exit_code"]==0 and outer["timeout_terminated"] is False and known and tail["cpu_accounting_complete"] is True and
      tail["live_child_cpu_seconds"]==0 and tail["completed_child_cpu_seconds"]==cpu and
      tail["final_external_allowance"]=={"cpu_seconds":2,"wall_seconds":3} and tail["actual_parent_cpu_sample"]+cpu+2<=60 and
      finite_nonnegative(outer["elapsed_wall_seconds"]) and outer["elapsed_wall_seconds"]<=min(120,tail["whole_wall_sample"]+3))
    summary={"child_job_cpu_seconds":cpu,"parent_cpu_sample":tail.get("actual_parent_cpu_sample"),"publication_cpu_allowance":2,
             "outer_wall_seconds":outer["elapsed_wall_seconds"],"scope":"whole child Jobs plus sampled parent and fixed tail"}
    return {"bundle":bundle,"result":result,"release":release,"children":children,"complete":complete,"accounting":summary},commands

def f32_bytes(values):
    return b"".join(struct.pack("<f",v) for v in values)

def f32_equal(a,b):
    return type(a) in (float,int) and math.isfinite(a) and struct.pack("<f",a)==struct.pack("<f",b)

def merge_contract(actual):
    need(type(actual) is dict and set(actual)==set(MERGE),"complete explicit merge config")
    for key,expected in MERGE.items():
        v=actual[key]
        if type(expected) is bool:ok=type(v) is bool and v==expected
        elif type(expected) is str:ok=type(v) is str and v==expected
        elif key in ("bands","mean_coarse","fallback_k","hull_from_level"):ok=type(v) is int and v==expected
        else:ok=f32_equal(v,expected)
        need(ok,"exact fixed merge field:"+key)

def gate_record(value,mode,frames,*,require_mixture=False):
    need(type(value) is dict and value.get("called") is True and value.get("mode")==mode,"actual gate observer call")
    if mode!="on":
        keys={"called","mode","visited_levels","allocated_rows","levels"}|({"placebo_rows_sha256"} if mode=="placebo" else set())
        need(set(value)==keys and value["visited_levels"]==0 and value["levels"] is None and
             value["allocated_rows"]==(4 if mode=="placebo" else 0),"off/placebo gate scope")
        if mode=="placebo":
            rows=[{"level":0,"kind":"placebo","width":0,"height":0,"sites":0,"averaged_fraction":0.0,
                   "zero_denominator":0,"positive_denominator":0}]*4
            # GateRow is serialized as a struct in declared field order, not a sorted map.
            raw=(json.dumps(rows,separators=(",",":"),allow_nan=False)+"\n").encode()
            need(value["placebo_rows_sha256"]==digest(raw),"actual allocated gate placebo digest")
        return {"mode":mode,"observed_levels":0}
    need(set(value)=={"called","mode","visited_levels","allocated_rows","scope","frames","levels"} and
         value["visited_levels"]==4 and value["allocated_rows"]==4 and type(value["frames"]) is int and value["frames"]==frames,
         "actual four shared levels")
    rows=value["levels"];need(type(rows) is list and len(rows)==4,"actual level population")
    zsum=psum=0;counts=[]
    for k,(row,(w,h)) in enumerate(zip(rows,LEVELS)):
        need(set(row)=={"level","kind","width","height","sites","averaged_fraction","zero_denominator","positive_denominator"} and
             type(row["level"]) is int and row["level"]==k and row["kind"]==("Laplacian" if k<3 else "mean-base") and
             row["width"]==w and row["height"]==h and row["sites"]==w*h,"actual level geometry")
        z,p=row["zero_denominator"],row["positive_denominator"];q=row["averaged_fraction"]
        need(typed_int(z,0,w*h) and typed_int(p,0,w*h) and z+p==w*h and
             type(q) in (float,int) and math.isfinite(q) and abs(q-z/(w*h))<=2e-15,"integer denominator observation")
        if k<3:zsum+=z;psum+=p
        counts.append({"level":k,"zero":z,"positive":p})
    if require_mixture:need(zsum>0 and psum>0,"both Laplacian denominator populations exercised")
    return {"mode":"on","shared_levels":counts,"laplacian_zero_den":zsum,"laplacian_positive_den":psum,"base_excluded":True}

def contributor_ids(rows,expected):
    need(type(rows) is list and len(rows)==len(expected),"complete contributor prefix")
    need([r["id"] for r in rows]==expected and len(set(expected))==len(expected),"unique ordered contributors")
    need(all(type(r["ordinal"]) is int and r["ordinal"]==i and type(r["merge_frames"]) is int and r["merge_frames"]==i+1
             for i,r in enumerate(rows)),"actual single fold per contributor")

REFUSAL_REASONS={
    6:"unsupported noise provenance",7:"unsupported noise covariance or proxy variance",
    8:"unadmitted input profile",9:"unsupported output semantics",
    10:"TIFF dimensions do not match common grid",11:"file hash mismatch",
}
OUTPUT_DESCRIPTION="common-tiff-stack-v1; identity common-RGB pixels; linear ProPhoto RGB D50; RGB16 code units; no WB, camera matrix, demosaic, exposure, tone or transfer; finite clamp then round half away from zero; simulation-only noise declaration"

def admitted_profile(image):
    need(image["icc_sha256"]==PROFILE_SHA,"actual admitted output profile")
    return True

def product_case(index,index_row,child,case_capture,release,actual,command):
    ordinal=index_row["ordinal"];kind,mode,fault=CASES[ordinal]
    need(case_capture["ordinal"]==ordinal and case_capture["id"]==index_row["id"] and
         case_capture["expected_exit_code"]==index_row["expected_exit_code"] and
         case_capture["expected_folded_frames"]==index_row["expected_folded_frames"],"controller case association")
    refs=case_capture["artifacts"];directory=BASE/"render-1"/f"case-{ordinal:02}"
    expected_names={"report.json","report.incomplete.json"}|{f"report.frame-{i}.json" for i in range(index_row["expected_folded_frames"])}
    if fault is None:expected_names.add("output.tiff")
    need(set(refs)==expected_names,"exact retained case publication population")
    saved={}
    for name,ref in refs.items():
        raw,p=read_ref(ref,MAX_TIFF if name.endswith(".tiff") else 65536)
        need(p==directory/name,"case retained path")
        saved[name]=raw
    raw=saved["report.json"];need(raw==child["raw_log"],"product report equals actual raw stdout")
    v=strict_json(raw)
    need(v["schema"]=="common-tiff-stack-result-v1" and v["command"]==command and v["observer_mode"]==mode,
         "actual product invocation")
    need(same_ref(v["incomplete"],refs["report.incomplete.json"]) and same_ref(v["manifest"],index_row["manifest"]),
         "actual incomplete/manifest associations")
    initial=strict_json(saved["report.incomplete.json"])
    need(initial["schema"]=="common-tiff-stack-incomplete-v1" and initial["status"]=="INITIAL_INCOMPLETE" and
         initial["subject_complete"] is False and Path(initial["manifest_path"]).resolve()==Path(index_row["manifest"]["path"]).resolve()
         and initial["manifest_sha256"]==index_row["manifest"]["sha256"] and Path(initial["report"]).resolve()==directory/"report.json",
         "actual initial refusal anchor")
    plan=strict_json(actual[f"case-{ordinal:02}.json"][1])
    n=index_row["expected_folded_frames"];rows=v["consumed"]
    contributor_ids(rows,[x["id"] for x in plan["inputs"][:n]])
    need(type(v["frame_receipts"]) is list and len(v["frame_receipts"])==n,"immutable completed fold count")
    observed_gates=[]
    if ordinal in (6,7,8,9):
        need(v["binary"] is None and "plan" not in v and "profile" not in v and "runtime" not in v,
             "source-derived early semantic refusal prefix")
    else:
        need(same_ref(v["binary"],release["executable"]) and same_ref(v["profile"],index["profile"]),"actual product/profile identity")
        receipt_plan=v["plan"]
        need(set(receipt_plan)==set(plan) and all(receipt_plan[k]==plan[k] for k in ("schema","grid","color","inputs","output")),
             "actual complete typed plan")
        merge_contract(receipt_plan["merge"]);noise_contract(receipt_plan["noise"],plan["noise"]["model"])
        runtime=v["runtime"];beta=runtime["actual_core_white_band_gain"]
        need(runtime["rayon_threads"]==2 and runtime["proxy"]=="(R+2G+B)/4 in RGB16 code values" and
             runtime["variance_units"]=="RGB16-code squared" and type(beta) is list and len(beta)==4 and
             all(type(x) in (float,int) and math.isfinite(x) and x>0 for x in beta) and runtime["passed_frame_beta"]==beta[:3],
             "actual declared code-unit runtime inputs")
        for j,row in enumerate(rows):
            expected=plan["inputs"][j];image=inspect_tiff(actual[kind+"-"+str(j)+".tiff"][1])
            need(same_ref(row["file"],expected["tiff"]) and row["width"]==128 and row["height"]==96 and
                 row["strip_count"]==image["strip_count"] and row["pixel_sha256"]==image["pixel_sha256"] and
                 row["icc_sha256"]==PROFILE_SHA and row["provenance"]==expected["provenance"],"consumed actual image identity")
            need(row["merge_sha256_before"]==row["merge_sha256_after"]==image["pixel_sha256"],"actual consumed RGB unchanged")
            samples=image["pixels"];proxy=[(samples[k]+2*samples[k+1]+samples[k+2])/4 for k in range(0,len(samples),3)]
            ph=digest(f32_bytes(proxy));variance=plan["noise"]["proxy_variance"];vh=digest(struct.pack("<f",variance)*(128*96))
            need(row["proxy_f32_sha256_before"]==row["proxy_f32_sha256_after"]==ph,"literal actual proxy array")
            need(row["variance_f32_sha256_before"]==row["variance_f32_sha256_after"]==vh and
                 number_equal(row["variance_value_before"],variance) and number_equal(row["variance_value_after"],variance) and
                 type(row["variance_sites"]) is int and row["variance_sites"]==12288,"literal actual injected variance array")
            need(row["passed_frame_beta"]==beta[:3],"same actual band transfer per fold")
            observed_gates.append(gate_record(row["gate"],mode,j+1,require_mixture=ordinal==4 and j==2))
            name=f"report.frame-{j}.json";need(same_ref(v["frame_receipts"][j],refs[name]),"immutable fold FileRef")
            fv=strict_json(saved[name])
            need(set(fv)=={"schema","manifest","fold"} and fv["schema"]=="common-tiff-stack-frame-v1" and
                 same_ref(fv["manifest"],index_row["manifest"]) and fv["fold"]==row,"immutable actual fold body")
    if fault is not None:
        need(v["status"]=="REFUSED" and v["subject_complete"] is False and v["output"] is None and
             v["error"]==REFUSAL_REASONS[ordinal] and v["stage"]==("manifest" if ordinal<10 else "input-2"),
             "specific registered product refusal")
        return {"ordinal":ordinal,"id":index_row["id"],"verified":True,"expected_refusal":v["error"],
                "folded_frames":n,"gate_observations":observed_gates},None,v
    need(v["status"]=="COMPLETE" and v["subject_complete"] is True and v["stage"]=="complete" and
         "error" not in v and v["inputs_rechecked"] is True and same_ref(v["output"],refs["output.tiff"]),
         "complete product publication")
    image=inspect_tiff(saved["output.tiff"],output=True)
    admitted_profile(image)
    need(image["width"]==128 and image["height"]==96 and
         image["description"]==OUTPUT_DESCRIPTION,"truthful already-RGB output")
    enc=v["encoding"]
    need(enc["width"]==128 and enc["height"]==96 and enc["sample_format"]=="RGB16" and
         enc["color_space"]=="linear-prophoto-d50" and enc["icc_sha256"]==PROFILE_SHA and
         enc["pixel_sha256"]==image["pixel_sha256"] and enc["quantization"]=="finite-clamp-round-half-away-v1" and
         enc["clipped_low"]==[0,0,0] and enc["clipped_high"]==[0,0,0],"actual encoding semantics and no clips")
    need(v["final_gate"]==rows[-1]["gate"],"final gate is actual last fold observation")
    obs=v["observer"];o=obs["observation"]
    need(obs["output_f32_sha256_before"]==obs["output_f32_sha256_after"]==enc["prequantization_f32_sha256"] and
         sha(enc["prequantization_f32_sha256"]),"actual output untouched by observer")
    need(o["called"] is True and o["mode"]==mode and o["visited_samples"]==(36864 if mode=="on" else 0) and
         o["allocated_samples"]==(0 if mode=="off" else 36864),"exercised output observer mode")
    if mode=="on":need(o["plane_major_f32_sha256"]==enc["prequantization_f32_sha256"],"actual observed output values")
    if mode=="placebo":need(o["placebo_f32_sha256"]==digest(b"\0"*(4*36864)),"actual allocated output placebo")
    literal=None
    if ordinal==0:literal=list(MEAN)*12288
    if ordinal==1:literal=pixels("address",0)
    if ordinal==2:literal=pixels("mixed-null",0)
    if literal is not None:
        compare_pixels(image["pixels"],literal,"literal final image")
        pm=[literal[i+c] for c in range(3) for i in range(0,len(literal),3)]
        need(enc["prequantization_f32_sha256"]==digest(f32_bytes(pm)),"literal prequantization identity")
    return {"ordinal":ordinal,"id":index_row["id"],"verified":True,"folded_frames":3,
            "literal_samples":len(literal) if literal is not None else 0,"pixel_sha256":image["pixel_sha256"],
            "whole_tiff_sha256":image["file_sha256"],"gate_observations":observed_gates},image,v

def negative(ident,reason,call):
    try:call()
    except ValueError as error:
        need(str(error)==reason,"specific negative reason:"+ident)
        return {"id":ident,"rejected":True,"reason":str(error)}
    raise ValueError("unpowered independent control:"+ident)

def independent_power(images,receipts):
    """In-memory adversarial copies; no product invocation or file mutation."""
    rows=[]
    literal=list(MEAN)*12288
    compare_pixels(images[0]["pixels"],literal,"literal final image")
    rows.append(negative("copied-first-contributor","literal final image: literal RGB codes",
                         lambda:compare_pixels(list(CONSTANTS[0])*12288,literal,"literal final image")))
    address=images[1]["pixels"];expected=pixels("address",0)
    shifted=[]
    for y in range(HEIGHT):
        for x in range(WIDTH):
            p=(y*WIDTH+(x+1)%WIDTH)*3;shifted.extend(address[p:p+3])
    rows.append(negative("one-pixel-address-shift","literal final image: literal RGB codes",
                         lambda:compare_pixels(shifted,expected,"literal final image")))
    swapped=[address[i+c] for i in range(0,len(address),3) for c in (2,1,0)]
    rows.append(negative("red-blue-permutation","literal final image: literal RGB codes",
                         lambda:compare_pixels(swapped,expected,"literal final image")))
    transferred=[int(math.floor(65535*(v/65535)**(1/1.8)+0.5)) for v in address]
    rows.append(negative("second-transfer-curve","literal final image: literal RGB codes",
                         lambda:compare_pixels(transferred,expected,"literal final image")))
    compare_pixels(address,expected,"literal final image")
    rows.append({"id":"literal-address-restored","passed":True})
    model="synthetic-independent-rademacher8-v1";floating=expected_noise(model)
    floating["rgb_covariance"]=[[float(x) for x in row] for row in floating["rgb_covariance"]]
    floating["proxy_variance"]=24.0
    noise_contract(floating,model);rows.append({"id":"equivalent-float-spelling","passed":True})
    wrong=strict_json(canonical(floating));wrong["proxy_variance"]=1
    rows.append(negative("variance-one","exact injected noise declaration",lambda:noise_contract(wrong,model)))
    wrong=strict_json(canonical(floating));wrong["rgb_covariance"][0][1]=False
    rows.append(negative("boolean-zero-covariance","exact injected noise declaration",lambda:noise_contract(wrong,model)))
    noise_contract(floating,model);rows.append({"id":"noise-restored","passed":True})
    contributors=receipts[0]["consumed"];ids=[x["id"] for x in contributors]
    rows.append(negative("omitted-contributor","complete contributor prefix",lambda:contributor_ids(contributors[:2],ids)))
    repeated=[contributors[0],contributors[1],contributors[1]]
    rows.append(negative("duplicated-contributor","unique ordered contributors",lambda:contributor_ids(repeated,ids)))
    contributor_ids(contributors,ids);rows.append({"id":"contributors-restored","passed":True})
    triple=[images[i] for i in (3,4,5)];compare_observer(triple)
    pixel_fault=bytearray(triple[1]["_raw"])
    pixel_fault[triple[1]["_pixel_offsets"][0]]^=1
    changed_image=inspect_tiff(bytes(pixel_fault),output=True)
    need(changed_image["pixels"]!=triple[1]["pixels"],"actual pixel destroyer exercised")
    bad=[triple[0],changed_image,triple[2]]
    rows.append(negative("changed-observer-pixel","observer whole TIFF equality",lambda:compare_observer(bad)))
    compare_observer(triple);rows.append({"id":"observer-restored","passed":True})
    profile_fault=bytearray(images[1]["_raw"])
    profile_fault[images[1]["_icc_offset"]+20]^=1
    altered=inspect_tiff(bytes(profile_fault),output=True)
    need(altered["pixels"]==images[1]["pixels"] and altered["icc_sha256"]!=images[1]["icc_sha256"],
         "actual ICC-only destroyer exercised")
    rows.append(negative("rehash-with-wrong-icc","actual admitted output profile",lambda:admitted_profile(altered)))
    admitted_profile(images[1]);rows.append({"id":"profile-restored","passed":True})
    return rows

def bounded_error(error):
    text=str(error);raw=text.encode("utf-8",errors="replace")
    return {"type":type(error).__name__,"message":text[:512],"full_message_bytes":len(raw),"full_message_sha256":digest(raw)}

def verify(args):
    index,actual=fixture_authority(args)
    saved,commands=saved_render_bundle(args,index)
    result=saved["result"];captures=result.get("artifacts",{}).get("cases",[])
    need(type(captures) is list and len(captures)<=12,"bounded retained case prefix")
    summaries=[];images={};receipts={};failures=[]
    for i,row in enumerate(index["cases"]):
        if i>=len(saved["children"]) or i>=len(captures):
            summaries.append({"ordinal":i,"id":row["id"],"verified":False,"status":"NO_LINKED_COMPLETED_CASE",
                              "scope":"may have been attempted; no completed case claimed"})
            continue
        child=saved["children"][i]
        try:
            summary,image,receipt=product_case(index,row,child,captures[i],saved["release"],actual,commands[i])
            summary["process_complete"]=child["process_complete"]
            summary["resource_admissible"]=child["resource_admissible"]
            summaries.append(summary)
            if image is not None:images[i]=image
            receipts[i]=receipt
        except (ValueError,KeyError,TypeError,OSError,UnicodeError,struct.error) as error:
            e=bounded_error(error);failures.append({"ordinal":i,"error_sha256":e["full_message_sha256"]})
            summaries.append({"ordinal":i,"id":row["id"],"verified":False,"status":"SAVED_CASE_REJECTED","error":e})
        check_time(20,30)
    controls=[];observer=None
    if all(i in images for i in range(6)):
        try:
            observer=compare_observer([images[i] for i in (3,4,5)])
            controls=independent_power(images,receipts)
        except (ValueError,KeyError,TypeError) as error:
            failures.append({"independent_control_error":bounded_error(error)})
    # Re-read only immutable generated inputs/metadata, never rerun the product.
    for ref,_ in actual.values():read_ref(ref,MAX_JSON)
    source_authority(args.source_sha256)
    complete=(saved["complete"] and len(summaries)==12 and all(x["verified"] for x in summaries) and
              len(receipts)==12 and observer is not None and len(controls)==16 and not failures)
    return {"schema":"common-tiff-stack-independent-verification-v1",
            "status":"PASS_COMMON_RGB_STACK_SOFTWARE_INTEGRATION" if complete else "REFUSED",
            "software_integration_complete":complete,"physical_noise_calibration":False,
            "real_geometry_admission":False,"quality_admission":False,
            "fixtures":file_ref(args.fixtures,read_bytes(args.fixtures,MAX_JSON)),
            "run_bundle":file_ref(args.run_bundle,read_bytes(args.run_bundle,65536)),
            "source":file_ref(SELF,read_bytes(SELF,128*1024)),"cases":summaries,
            "independent_controls":controls,"observer_comparison":observer,
            "accounting":saved["accounting"],"failures":failures,
            "scope":"Three simulation contributors; identity common-RGB pixel gauge; exact literal/software checks only."}

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="mode",required=True)
    prep=sub.add_parser("prepare");prep.add_argument("--output",required=True);prep.add_argument("--source-sha256",required=True)
    check=sub.add_parser("verify")
    for flag in ("fixtures","fixtures-sha256","run-bundle","run-bundle-sha256","output","source-sha256"):
        check.add_argument("--"+flag,required=True)
    args=parser.parse_args()
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,"isolated stdlib-only invocation")
    expected=[sys.executable,"-I","-S","-B",str(SELF),args.mode]
    if args.mode=="prepare":expected+=["--output",str(Path(args.output).resolve())]
    else:expected+=["--fixtures",str(Path(args.fixtures).resolve()),"--fixtures-sha256",args.fixtures_sha256,
                   "--run-bundle",str(Path(args.run_bundle).resolve()),"--run-bundle-sha256",args.run_bundle_sha256,
                   "--output",str(Path(args.output).resolve())]
    expected+=["--source-sha256",args.source_sha256]
    need(sys.orig_argv==expected,"exact independent invocation")
    out=None
    try:
        if args.mode=="verify":
            out=Path(args.output).resolve()
            need(out==BASE/"verify-1/check" and not out.exists() and out.parent.is_dir(),"fresh fixed verifier output")
            out.mkdir()
        answer=prepare(args) if args.mode=="prepare" else verify(args)
    except (ValueError,KeyError,TypeError,OSError,UnicodeError,struct.error) as error:
        answer={"schema":"common-tiff-stack-independent-"+("preparation" if args.mode=="prepare" else "verification")+"-v1",
                "status":"REFUSED","software_integration_complete":False,"error":bounded_error(error),
                "scope":"independent source/reader refusal, not a product scientific result"}
    answer["own_work"]={"cpu_seconds":time.process_time()-START_CPU,"wall_seconds":time.perf_counter()-START}
    answer["publication_allowance"]={"cpu_seconds":0.25,"wall_seconds":0.5}
    limit_cpu,limit_wall=(5,10) if args.mode=="prepare" else (20,30)
    if answer["own_work"]["cpu_seconds"]+0.25>limit_cpu or answer["own_work"]["wall_seconds"]+0.5>limit_wall:
        answer["status"]="REFUSED";answer["software_integration_complete"]=False;answer["resource_refusal"]="own allowance including tail"
    raw=canonical(answer)+b"\n";need(len(raw)<=128*1024,"fixed independent terminal extent")
    if out is not None:write_fresh(out/"result.json",raw,128*1024)
    need(sys.stdout.buffer.write(raw)==len(raw),"whole independent stdout");sys.stdout.buffer.flush()
    return 0 if answer["status"] in ("PREPARED_UNRUN_FIXTURES","PASS_COMMON_RGB_STACK_SOFTWARE_INTEGRATION") else 1

if __name__=="__main__":
    raise SystemExit(main())
