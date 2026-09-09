#!/usr/bin/env python3
"""Independent v2 literal fixtures and saved consumer checks. Source-only draft.
Own container conventions derive from the admitted independent v1 checker;
no product writer, core sampler, image library or product launcher is imported.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, stat, struct, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SELF=Path(__file__).resolve();BASE=SELF.parent
PROFILE=ROOT/'experiments/M165-common-input/linear-prophoto-d50-v1.icc'
PROFILE_SHA='16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef'
MAX_TIFF=1638400;MAX_JSON=256*1024;MAX_FILES=32*1024*1024
START=time.perf_counter();START_CPU=time.process_time()
MERGE={"bands":3,"gate":2,"exponent":2,"sharpen_per_octave":1.4,"select":"SoftPower","admission":"HardFloor","base":"Mean","mean_coarse":0,"hull":"InputRange","hull_lambda":2,"hull_low_only":False,"fallback":"Mean","fallback_k":3,"fallback_power":4,"hull_from_level":1,"significance_scale":0}
DOMAIN=b'common-tiff-dimensions-rademacher-v1'
STRIPS=(17,31,48,64,97,23,41,73)
SETS=(('mean-two',64,64,2,'constant'),('mean-five',129,97,5,'constant'),
      ('mean-eight',512,512,8,'constant'),('odd-address',129,97,5,'address'),
      ('odd-offset',129,97,5,'offset'),('odd-noisy',129,97,5,'mixed-noisy'),
      ('count-nine-extra',512,512,1,'ninth'))
# ID, source set, schema version, observer, one defect; exact24 source order.
CASES=(
 ('mean-two-min','mean-two',2,'off',None),('mean-five-odd','mean-five',2,'off',None),
 ('mean-eight-max','mean-eight',2,'off',None),('odd-address','odd-address',2,'on',None),
 ('odd-offset','odd-offset',2,'on',None),('odd-noisy-off','odd-noisy',2,'off',None),
 ('odd-noisy-on','odd-noisy',2,'on',None),('odd-noisy-placebo','odd-noisy',2,'placebo',None),
 ('legacy-constant','legacy',1,'off',None),
 ('count-zero','mean-five',2,'off','count-zero'),('count-one','mean-five',2,'off','count-one'),
 ('count-nine','mean-eight',2,'off','count-nine'),('width-low','mean-five',2,'off','width-low'),
 ('width-high','mean-five',2,'off','width-high'),('height-low','mean-five',2,'off','height-low'),
 ('height-high','mean-five',2,'off','height-high'),('width-u32-overflow','mean-five',2,'off','width-u32-overflow'),
 ('legacy-count-two','legacy',1,'off','legacy-count-two'),('legacy-odd','odd-address',1,'off','legacy-odd'),
 ('duplicate-input','mean-five',2,'off','duplicate-input'),('wrong-profile','mean-five',2,'off','wrong-profile'),
 ('wrong-proxy-variance','odd-noisy',2,'off','wrong-proxy-variance'),
 ('last-geometry','mean-five',2,'off','last-geometry'),('last-file-hash','mean-five',2,'off','last-file-hash'))
REFUSALS={**{i:'v2 requires two to eight inputs' for i in (9,10,11)},
 **{i:'unsupported common grid' for i in (12,13,14,15,18)},
 16:'manifest JSON:',17:'v1 requires exactly three inputs',19:'duplicate input id',
 20:'unadmitted input profile',21:'unsupported noise covariance or proxy variance',
 22:'TIFF dimensions do not match common grid',23:'file hash mismatch'}
LEGACY_INDEX={'path':'experiments/common-tiff-stack/prepare-1/fixtures/index.json','bytes':19328,'sha256':'5c16e7cd7cd6a29377579f643b1b31515ffb99a1f5ad0a5ef32c362de6adeab8'}
LEGACY_REPORT={'path':'experiments/common-tiff-stack/render-1/case-00/report.json','bytes':11635,'sha256':'abc69a25319da0ddb6ce2e9a036d8b37c0e1bcd4c67a9c186e6a647f088b5f9a'}
LEGACY_OUTPUT={'path':'experiments/common-tiff-stack/render-1/case-00/output.tiff','bytes':74807,'sha256':'1e6c9f9bd3146c0c8f7314c422e26c842eb45ba25d76d12adae8f8d690842f7e'}
DESCRIPTION='; identity common-RGB pixels; linear ProPhoto RGB D50; RGB16 code units; no WB, camera matrix, demosaic, exposure, tone or transfer; finite clamp then round half away from zero; simulation-only noise declaration'
RECIPE={'schema':'common-tiff-dimensions-independent-recipe-v1','sets':SETS,'strip_rows':STRIPS,
 'constant':'(8000+240*2^i,16000+160*2^i,24000+80*2^i)',
 'means':{'2':[8360,16240,24120],'5':[9488,16992,24496],'8':[15650,21100,26550]},
 'address':'R=4000+101*x+7*y;G=18000+13*x+83*y;B=36000+47*x+19*y',
 'patch':{'xyxy':[16,24,48,56],'rgb':[8192,24576,49152]},
 'last_column':'x=128:(50000+y,22000+2*y,10000+3*y)',
 'last_row':'y=96:(12000+3*x,52000+x,32000+2*x)',
 'corner':[60001,45003,15007],
 'offset':{'pattern':'(13*x+29*y)%997;patch512;lastcol1200+y;lastrow1400+x;corner1777',
 'rgb_base':[1000,3000,5000],'frame_offsets':[0,40,120,280,600],'ideal_offset':208,'code_tolerance':1},'mixed_base':[14000,24000,34000],
 'mixed_texture':'x>=65:+/-4096,positive iff(x//4+y//4)%2==0',
 'noise':{'domain':DOMAIN.decode(),'counter':'LEu32(frame,y,x,channel)','sign':'+8 iff SHA256 first byte low bit1 else-8'},
 'ninth':[45000,50000,55000],'profile_sha256':PROFILE_SHA,'legacy_output':LEGACY_OUTPUT}

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


def payload(values):
    return struct.pack("<"+"H"*len(values),*values)


def make_tiff(values,width,height,icc,provenance,strip_rows):
    """Independent container construction: payload first, IFD last, descending tags."""
    need(typed_int(width,1,512) and typed_int(height,1,512) and len(values)==width*height*3,
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
    need(len(raw)<=6*width*height+65536, "fixture TIFF cap")
    return bytes(raw)


def inspect_tiff(raw, *, output=False, version=2):
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
    need(1<=width<=512 and 1<=height<=512, "bounded RGB geometry")
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
        need(tags[305][2][:-1]==("strehl-common-input common-tiff-stack-v"+str(version)).encode(), "fixed output software")
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


def association_path(name):
    """Local repository path association only; never equate distinct paths by content."""
    need(type(name) is str and 0<len(name)<=32768 and "\0" not in name,"typed association path")
    if name.startswith("\\\\?\\"):
        local=name[4:]
        need(len(local)>=3 and local[0].isascii() and local[0].isalpha() and local[1:3]==":\\",
             "supported verbatim local-drive path")
        parts=local[3:].split("\\")
        need(all(part and part not in (".","..") and not part.endswith(("."," ")) and ":" not in part
                 for part in parts),"canonical verbatim local components")
        name=local
    need(not name.startswith(("\\\\","//")),"no device or UNC association")
    p=Path(name)
    p=(p if p.is_absolute() else ROOT/p).resolve()
    need(p.is_relative_to(ROOT),"repository association containment")
    return p


def same_ref(a,b):
    def path(ref):
        return association_path(ref["path"])
    return (type(a) is dict and type(b) is dict and set(a)==set(b)=={"path","bytes","sha256"}
            and path(a)==path(b) and a["bytes"]==b["bytes"] and a["sha256"]==b["sha256"])


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
            check_time(45,90)
        after=os.fstat(f.fileno())
    final=p.lstat()
    need(full(before)==full(final) and full(opened)==full(after) and count==ref["bytes"] and
         hasher.hexdigest()==ref["sha256"],"complete unchanged executable bytes")
    return p.resolve()


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


def contributor_ids(rows,expected):
    need(type(rows) is list and len(rows)==len(expected),"complete contributor prefix")
    need([r["id"] for r in rows]==expected and len(set(expected))==len(expected),"unique ordered contributors")
    need(all(type(r["ordinal"]) is int and r["ordinal"]==i and type(r["merge_frames"]) is int and r["merge_frames"]==i+1
             for i,r in enumerate(rows)),"actual single fold per contributor")


def admitted_profile(image):
    need(image["icc_sha256"]==PROFILE_SHA,"actual admitted output profile")
    return True


def negative(ident,reason,call):
    try:call()
    except ValueError as error:
        need(str(error)==reason,"specific negative reason:"+ident)
        return {"id":ident,"rejected":True,"reason":str(error)}
    raise ValueError("unpowered independent control:"+ident)


def bounded_error(error):
    text=str(error);raw=text.encode("utf-8",errors="replace")
    result={"type":type(error).__name__[:64],"message":text[:512],"full_message_bytes":len(raw),"full_message_sha256":digest(raw)}
    while len(canonical(result))>1024:result['message']=result['message'][:len(result['message'])//2]
    return result



def source_authority(expected):
    raw=read_bytes(SELF,128*1024)
    need(sha(expected) and digest(raw)==expected,'independent source identity')
    spec=BASE/'independent-spec.md';sraw=read_bytes(spec,32*1024)
    icc=read_bytes(PROFILE,548)
    need(len(icc)==548 and digest(icc)==PROFILE_SHA,'exact admitted profile')
    return file_ref(SELF,raw),file_ref(spec,sraw),icc

def palette(frame):
    need(typed_int(frame,0,7),'literal contributor ordinal')
    return (8000+240*2**frame,16000+160*2**frame,24000+80*2**frame)

def rounded_mean(contributors):
    n=len(contributors);need(n>0,'nonempty arithmetic competitor')
    return tuple((2*sum(v[c] for v in contributors)+n)//(2*n) for c in range(3))

def mean_competitors(n):
    need(n in (2,5,8),'fixed mean population')
    contributors=[palette(i) for i in range(n)];expected=tuple(RECIPE['means'][str(n)])
    need(rounded_mean(contributors)==expected,'literal complete mean')
    alternatives=[]
    for i in range(n):
        alternatives.append((f'n{n}-omit-{i}',rounded_mean(contributors[:i]+contributors[i+1:])))
        alternatives.append((f'n{n}-append-duplicate-{i}',rounded_mean(contributors+[contributors[i]])))
    for missing in range(n):
        for duplicate in range(n):
            if missing!=duplicate:
                changed=list(contributors);changed[missing]=contributors[duplicate]
                alternatives.append((f'n{n}-replace-{missing}-with-{duplicate}',rounded_mean(changed)))
    need(all(v!=expected for _,v in alternatives),'every fixed mean competitor differs after rounding')
    return alternatives

def literal_pixels(style,frame,w,h):
    need(style in ('constant','address','offset','mixed-noisy','ninth') and
         typed_int(w,1,512) and typed_int(h,1,512),'literal fixture domain')
    result=[]
    for y in range(h):
        for x in range(w):
            if style=='constant':rgb=palette(frame)
            elif style=='ninth':rgb=(45000,50000,55000)
            elif style=='address':
                rgb=(4000+101*x+7*y,18000+13*x+83*y,36000+47*x+19*y)
                if 16<=x<48 and 24<=y<56:rgb=(8192,24576,49152)
                if x==128:rgb=(50000+y,22000+2*y,10000+3*y)
                if y==96:rgb=(12000+3*x,52000+x,32000+2*x)
                if x==128 and y==96:rgb=(60001,45003,15007)
            elif style=='offset':
                p=(13*x+29*y)%997
                if 16<=x<48 and 24<=y<56:p=512
                if x==128:p=1200+y
                if y==96:p=1400+x
                if x==128 and y==96:p=1777
                rgb=tuple(base+p+RECIPE['offset']['frame_offsets'][frame] for base in (1000,3000,5000))
            else:
                d=0 if x<65 else (4096 if (x//4+y//4)%2==0 else -4096)
                rgb=tuple(v+d for v in (14000,24000,34000))
                if style=='mixed-noisy':
                    rgb=tuple(v+(8 if hashlib.sha256(DOMAIN+struct.pack('<4I',frame,y,x,c)).digest()[0]&1 else -8)
                              for c,v in enumerate(rgb))
            need(all(typed_int(v,0,65535) for v in rgb),'unclipped literal RGB')
            result.extend(rgb)
    return result

def levels(w,h):
    result=[]
    for _ in range(4):result.append((w,h));w=(w+1)//2;h=(h+1)//2
    return result

def expected_provenance(ident,model,recipe_sha):
    return dict(schema='common-tiff-stack-input-v1',id=ident,fixture_sha256=recipe_sha,
                color_space='linear-prophoto-d50',noise_model=model,geometry='identity-common-rgb-pixels')

def legacy_authority():
    iraw,_=read_ref(LEGACY_INDEX,256*1024);index=strict_json(iraw)
    rraw,_=read_ref(LEGACY_REPORT,64*1024);report=strict_json(rraw)
    need(report['schema']=='common-tiff-stack-result-v1' and report['status']=='COMPLETE'
         and report['subject_complete'] is True and same_ref(report['output'],LEGACY_OUTPUT),'held legacy completion')
    mref=index['cases'][0]['manifest']
    need(same_ref(mref,report['manifest']),'legacy exact manifest link')
    mraw,_=read_ref(mref,64*1024);manifest=strict_json(mraw)
    need(manifest['schema']=='common-tiff-stack-v1' and manifest['grid']==dict(width=128,height=96,
         channels='RGB',coordinates='identity-common-rgb-pixels') and len(manifest['inputs'])==3,'legacy fixed intake')
    merge_contract(manifest['merge']);noise_contract(manifest['noise'],'synthetic-noiseless-v1')
    return dict(index=LEGACY_INDEX,report=LEGACY_REPORT,manifest=mref,output=LEGACY_OUTPUT),manifest['inputs']

def input_catalog(generated,recipe_sha,icc,*,verify=False):
    # Called only by the released preparation/checker; not during source authoring.
    catalog={};file_refs=[]
    for name,w,h,n,style in SETS:
        model='synthetic-independent-rademacher8-v1' if style=='mixed-noisy' else 'synthetic-noiseless-v1'
        entries=[]
        for i in range(n):
            ident=f'{name}-{i}';filename=ident+'.tiff';prov=expected_provenance(ident,model,recipe_sha)
            values=literal_pixels(style,i,w,h)
            if verify:
                ref,raw=generated[filename]
            else:
                raw=make_tiff(values,w,h,icc,prov,STRIPS[i%8])
                ref=write_fresh(generated/filename,raw,6*w*h+65536)
            image=inspect_tiff(raw)
            need((image['width'],image['height'])==(w,h),'prepared declared grid')
            compare_pixels(image['pixels'],values,'prepared independent literal')
            need(image['icc_sha256']==PROFILE_SHA and strict_json(image['description'])==prov,'prepared profile/provenance')
            need(image['strip_count']==(h+STRIPS[i%8]-1)//STRIPS[i%8],'independent input strip census')
            entries.append(dict(id=ident,tiff=ref,pixel_sha256=image['pixel_sha256'],provenance=prov))
            file_refs.append(ref)
            check_time(45 if verify else 20,90 if verify else 40)
        catalog[name]=entries
    for fault,w,h,filename in [('last-geometry',128,97,'last-geometry.tiff'),
                                ('last-file-hash',129,97,'last-file-hash.tiff')]:
        ident='mean-five-4';prov=expected_provenance(ident,'synthetic-noiseless-v1',recipe_sha)
        values=literal_pixels('constant',4,w,h)
        if fault=='last-file-hash':values[0]+=1
        if verify:ref,raw=generated[filename]
        else:
            raw=make_tiff(values,w,h,icc,prov,STRIPS[4]);ref=write_fresh(generated/filename,raw,6*w*h+65536)
        got=inspect_tiff(raw);compare_pixels(got['pixels'],values,'actual last-frame fault witness')
        need((got['width'],got['height'])==(w,h) and strict_json(got['description'])==prov
             and got['icc_sha256']==PROFILE_SHA,'last-frame fault container authority')
        catalog[fault]=dict(id=ident,tiff=ref,pixel_sha256=got['pixel_sha256'],provenance=prov)
        file_refs.append(ref)
    need(len(file_refs)==33,'fixed actual TIFF population')
    return catalog,file_refs

def case_manifest(ordinal,catalog,legacy,icc_ref):
    ident,group,version,mode,fault=CASES[ordinal]
    if group=='legacy':w,h=128,96;inputs=strict_json(canonical(legacy))
    else:
        _,w,h,_,_=next(s for s in SETS if s[0]==group)
        inputs=strict_json(canonical(catalog[group]))
    model='synthetic-independent-rademacher8-v1' if group=='odd-noisy' else 'synthetic-noiseless-v1'
    noise=expected_noise(model);color=dict(space='linear-prophoto-d50',icc=icc_ref)
    if fault=='count-zero':inputs=[]
    elif fault in ('count-one','legacy-count-two'):inputs=inputs[:1 if fault=='count-one' else 2]
    elif fault=='count-nine':inputs+=strict_json(canonical(catalog['count-nine-extra']))
    elif fault=='width-low':w=63
    elif fault=='width-high':w=513
    elif fault=='height-low':h=63
    elif fault=='height-high':h=513
    elif fault=='width-u32-overflow':w=4294967296
    elif fault=='legacy-odd':inputs=inputs[:3]
    elif fault=='duplicate-input':inputs[1]=strict_json(canonical(inputs[0]))
    elif fault=='wrong-profile':color['icc']=dict(icc_ref,sha256='0'*64)
    elif fault=='wrong-proxy-variance':noise['proxy_variance']=1
    elif fault=='last-geometry':inputs[-1]=strict_json(canonical(catalog[fault]))
    elif fault=='last-file-hash':inputs[-1]['tiff']['path']=catalog[fault]['tiff']['path']
    elif fault is not None:raise ValueError('closed case fault table')
    case=BASE/'render-1'/f'case-{ordinal:02}'
    return dict(schema='common-tiff-stack-v'+str(version),
                grid=dict(width=w,height=h,channels='RGB',coordinates='identity-common-rgb-pixels'),
                color=color,noise=noise,merge=MERGE,inputs=inputs,
                output=dict(path=str(case/'output.tiff'),space='linear-prophoto-d50',sample_format='RGB16',
                            quantization='finite-clamp-round-half-away-v1'))

def case_row(ordinal,mref,manifest):
    ident,group,version,mode,fault=CASES[ordinal];case=BASE/'render-1'/f'case-{ordinal:02}'
    return dict(ordinal=ordinal,id=ident,fixture_kind=group,version=version,observer=mode,
                expected_exit_code=int(fault is not None),expected_folded_frames=(4 if ordinal>=22 else
                    (0 if fault else len(manifest['inputs']))),manifest=mref,
                command=['ACTUAL_BINARY_PATH','--stack-manifest',mref['path'],'--manifest-sha256',mref['sha256'],
                         '--report',str(case/'report.json'),'--observer',mode],
                output_path=str(case/'output.tiff'),report_path=str(case/'report.json'))

def prepare(args):
    own,spec,icc=source_authority(args.source_sha256)
    power=[dict(id=ident,rgb=list(rgb)) for n in (2,5,8) for ident,rgb in mean_competitors(n)]
    need(len(power)==108,'fixed mean competitor population')
    legacy,legacy_inputs=legacy_authority()
    out=Path(args.output).resolve();need(out==BASE/'prepare-1/fixtures' and not out.exists(),'fresh fixed fixture directory')
    need(out.parent.is_dir(),'prepared parent directory')
    out.mkdir();generated=[]
    recipe_raw=canonical(RECIPE)+b'\n';recipe_ref=write_fresh(out/'recipe.json',recipe_raw,64*1024)
    generated.append(recipe_ref);recipe_sha=digest(canonical(RECIPE))
    catalog,tiffs=input_catalog(out,recipe_sha,icc);generated+=tiffs
    rows=[]
    for ordinal in range(24):
        manifest=case_manifest(ordinal,catalog,legacy_inputs,file_ref(PROFILE,icc))
        mref=write_fresh(out/f'case-{ordinal:02}.json',canonical(manifest)+b'\n',64*1024)
        generated.append(mref);rows.append(case_row(ordinal,mref,manifest));check_time(20,40)
    index=dict(schema='common-tiff-dimensions-independent-fixtures-v1',source=own,spec=spec,
               profile=file_ref(PROFILE,icc),recipe=recipe_ref,recipe_sha256=recipe_sha,
               legacy=legacy,generated_files=generated,cases=rows)
    need(len(generated)==58 and sum(r['bytes'] for r in generated)+len(canonical(index))+64*1024<MAX_FILES,'complete fixture extent')
    ref=write_fresh(out/'index.json',canonical(index)+b'\n',MAX_JSON)
    check_time(20,40)
    return dict(schema='common-tiff-dimensions-independent-preparation-v1',status='PREPARED_UNRUN_FIXTURES',index=ref,
                cases=24,generated_files=59,file_bytes=sum(r['bytes'] for r in generated)+ref['bytes'],
                mean_competitors=power,scope='literal fixture preparation only; no product execution')

def fixture_authority(args):
    own,spec,icc=source_authority(args.source_sha256)
    path=Path(args.fixtures).resolve();raw=read_bytes(path,MAX_JSON)
    need(path==BASE/'prepare-1/fixtures/index.json' and digest(raw)==args.fixtures_sha256,'fixed fixture index identity')
    index=strict_json(raw)
    need(set(index)=={'schema','source','spec','profile','recipe','recipe_sha256','legacy','generated_files','cases'}
         and index['schema']=='common-tiff-dimensions-independent-fixtures-v1','closed fixture index')
    need(same_ref(index['source'],own) and same_ref(index['spec'],spec) and same_ref(index['profile'],file_ref(PROFILE,icc)),
         'same fixture source/spec/profile')
    legacy,legacy_inputs=legacy_authority();need(index['legacy']==legacy,'exact unchanged legacy evidence')
    generated=index['generated_files'];need(type(generated) is list and len(generated)==58,'fixed generated population')
    actual={};total=len(raw)
    expected_names={'recipe.json'}|{f'{name}-{i}.tiff' for name,w,h,n,style in SETS for i in range(n)}|{
                   'last-geometry.tiff','last-file-hash.tiff'}|{f'case-{i:02}.json' for i in range(24)}
    for ref in generated:
        data,p=read_ref(ref,MAX_TIFF if ref['path'].endswith('.tiff') else MAX_JSON)
        need(p.parent==path.parent and p.name in expected_names and p.name not in actual,'exact generated namespace')
        actual[p.name]=(ref,data);total+=len(data);check_time(45,90)
    need(set(actual)==expected_names and total<=MAX_FILES,'complete fixture name/extent census')
    need(same_ref(actual['recipe.json'][0],index['recipe']) and
         strict_json(actual['recipe.json'][1])==strict_json(canonical(RECIPE)) and
         index['recipe_sha256']==digest(canonical(RECIPE)),'exact prepared recipe')
    catalog,_=input_catalog(actual,index['recipe_sha256'],icc,verify=True)
    need(type(index['cases']) is list and len(index['cases'])==24,'all fixed case rows')
    for i,row in enumerate(index['cases']):
        manifest=case_manifest(i,catalog,legacy_inputs,index['profile']);mref,data=actual[f'case-{i:02}.json']
        need(strict_json(data)==manifest and row==case_row(i,mref,manifest),'fixed manifest and command row')
    return index,actual,catalog
def gate_record(value,mode,frames,w,h,*,require_mixture=False):
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
    for k,(row,(w,h)) in enumerate(zip(rows,levels(w,h))):
        need(set(row)=={"level","kind","width","height","sites","averaged_fraction","zero_denominator","positive_denominator"} and
             type(row["level"]) is int and row["level"]==k and row["kind"]==("Laplacian" if k<3 else "mean-base") and
             row["width"]==w and row["height"]==h and row["sites"]==w*h,"actual level geometry")
        z,p=row["zero_denominator"],row["positive_denominator"];q=row["averaged_fraction"]
        need(typed_int(z,0,w*h) and typed_int(p,0,w*h) and z+p==w*h and
             type(q) in (float,int) and math.isfinite(q) and abs(q-z/(w*h))<=2e-15,"integer denominator observation")
        if k<3:zsum+=z;psum+=p
        counts.append({"level":k,"zero":z,"positive":p})
    if require_mixture:need(zsum>0 and psum>0,"both Laplacian denominator populations exercised")
    return {"mode":"on","shared_levels":counts,"laplacian_zero_den":zsum,"laplacian_positive_den":psum,"base_excluded":True,"mixture_scope":"collective final Laplacian levels, not each level or fold"}



def constant_contract(actual,rgb,w,h):
    need(len(actual)==w*h*3,'constant literal geometry')
    need(all(value==rgb[i%3] for i,value in enumerate(actual)),'constant literal RGB codes')
    return True

def grid_contract(image,w,h):
    need((image['width'],image['height'])==(w,h),'declared output grid')
    return True

def levels_contract(value,w,h):
    # The same actual gate predicate is used for unchanged and mutated metadata.
    return gate_record(value,'on',value['frames'],w,h)

def product_case(index,row,child,capture,release,actual,catalog,command):
    ordinal=row['ordinal'];ident,group,version,mode,fault=CASES[ordinal]
    need(capture['ordinal']==ordinal and capture['id']==ident and
         capture['expected_exit_code']==row['expected_exit_code'] and
         capture['expected_folded_frames']==row['expected_folded_frames'],'controller case identity')
    directory=BASE/'render-1'/f'case-{ordinal:02}';refs=capture['artifacts']
    n=row['expected_folded_frames']
    names={'report.json','report.incomplete.json'}|{f'report.frame-{i}.json' for i in range(n)}
    if fault is None:names.add('output.tiff')
    need(set(refs)==names,'exact retained case publication population')
    saved={}
    for name,ref in refs.items():
        raw,p=read_ref(ref,MAX_TIFF if name.endswith('.tiff') else 192*1024)
        need(association_path(str(p))==directory/name,'owned case artifact path');saved[name]=raw
    need(saved['report.json']==child['raw_log'],'actual stdout equals saved report')
    v=strict_json(saved['report.json']);plan=strict_json(actual[f'case-{ordinal:02}.json'][1])
    early=9<=ordinal<=21
    expected_version=1 if early else version
    need(v['schema']=='common-tiff-stack-result-v'+str(expected_version) and v['command']==command
         and v['observer_mode']==mode,'source-derived product schema and argv')
    need(same_ref(v['incomplete'],refs['report.incomplete.json']) and same_ref(v['manifest'],row['manifest']),
         'product manifest/incomplete association')
    initial=strict_json(saved['report.incomplete.json'])
    need(initial['schema']=='common-tiff-stack-incomplete-v1' and initial['status']=='INITIAL_INCOMPLETE'
         and initial['subject_complete'] is False and association_path(initial['manifest_path'])==association_path(row['manifest']['path'])
         and initial['manifest_sha256']==row['manifest']['sha256'] and association_path(initial['report'])==directory/'report.json',
         'actual request-level incomplete anchor')
    folds=v['consumed'];contributor_ids(folds,[x['id'] for x in plan['inputs'][:n]])
    need(type(v['frame_receipts']) is list and len(v['frame_receipts'])==n,'complete immutable fold prefix')
    observations=[]
    if early:
        need(v['binary'] is None and all(k not in v for k in ('plan','profile','runtime')),'actual early semantic refusal prefix')
    else:
        w,h=plan['grid']['width'],plan['grid']['height']
        need(same_ref(v['binary'],release['executable']) and same_ref(v['profile'],index['profile']),'actual binary/profile identity')
        rplan=v['plan'];need(set(rplan)==set(plan) and all(rplan[k]==plan[k] for k in ('schema','grid','color','inputs','output')),
                            'actual complete typed plan')
        merge_contract(rplan['merge']);noise_contract(rplan['noise'],plan['noise']['model'])
        runtime=v['runtime'];beta=runtime['actual_core_white_band_gain']
        need(runtime['rayon_threads']==2 and runtime['proxy']=='(R+2G+B)/4 in RGB16 code values'
             and runtime['variance_units']=='RGB16-code squared' and type(beta) is list and len(beta)==4
             and all(finite_nonnegative(x) and x>0 for x in beta) and runtime['passed_frame_beta']==beta[:3],
             'actual injected simulation band inputs')
        for j,fold in enumerate(folds):
            expected=plan['inputs'][j]
            iraw,_=read_ref(expected['tiff'],6*w*h+65536 if version==2 else 256*1024)
            image=inspect_tiff(iraw)
            need((image['width'],image['height'])==(w,h) and image['pixel_sha256']==expected['pixel_sha256']
                 and image['icc_sha256']==PROFILE_SHA and strict_json(image['description'])==expected['provenance'],'consumed independent input identity')
            need(same_ref(fold['file'],expected['tiff']) and fold['width']==w and fold['height']==h
                 and fold['strip_count']==image['strip_count'] and fold['pixel_sha256']==image['pixel_sha256']
                 and fold['icc_sha256']==PROFILE_SHA and fold['provenance']==expected['provenance'],'actual folded image fields')
            need(fold['merge_sha256_before']==fold['merge_sha256_after']==image['pixel_sha256'],'actual unchanged consumed RGB codes')
            values=image['pixels'];proxy=[(values[i]+2*values[i+1]+values[i+2])/4 for i in range(0,len(values),3)]
            ph=digest(f32_bytes(proxy));variance=plan['noise']['proxy_variance'];vh=digest(struct.pack('<f',variance)*(w*h))
            need(fold['proxy_f32_sha256_before']==fold['proxy_f32_sha256_after']==ph,'literal consumed proxy array')
            need(fold['variance_f32_sha256_before']==fold['variance_f32_sha256_after']==vh
                 and number_equal(fold['variance_value_before'],variance) and number_equal(fold['variance_value_after'],variance)
                 and typed_int(fold['variance_sites']) and fold['variance_sites']==w*h,'literal consumed variance array')
            need(fold['passed_frame_beta']==beta[:3],'unchanged injected beta per fold')
            observations.append(gate_record(fold['gate'],mode,j+1,w,h,require_mixture=ordinal==6 and j==4))
            name=f'report.frame-{j}.json';need(same_ref(v['frame_receipts'][j],refs[name]),'exact immutable fold FileRef')
            f=strict_json(saved[name]);need(set(f)=={'schema','manifest','fold'} and
                f['schema']=='common-tiff-stack-frame-v'+str(version) and same_ref(f['manifest'],row['manifest']) and f['fold']==fold,
                'immutable actual fold body')
            check_time(45,90)
    if fault is not None:
        reason=v.get('error');expected=REFUSALS[ordinal]
        specific=(type(reason) is str and reason.startswith(expected) and '4294967296' in reason) if ordinal==16 else reason==expected
        need(v['status']=='REFUSED' and v['subject_complete'] is False and v['output'] is None and specific
             and v['stage']==('manifest' if early else 'input-4'),'exact named semantic refusal')
        return dict(ordinal=ordinal,id=ident,verified=True,expected_refusal=reason,folded_frames=n,
                    gate_observations=observations),None,v
    need(v['status']=='COMPLETE' and v['subject_complete'] is True and v['stage']=='complete' and 'error' not in v
         and v['inputs_rechecked'] is True and same_ref(v['output'],refs['output.tiff']),'complete product publication')
    image=inspect_tiff(saved['output.tiff'],output=True,version=version);grid_contract(image,w,h);admitted_profile(image)
    need(image['description']=='common-tiff-stack-v'+str(version)+DESCRIPTION,'exact output semantics')
    enc=v['encoding'];need(enc['width']==w and enc['height']==h and enc['sample_format']=='RGB16'
        and enc['color_space']=='linear-prophoto-d50' and enc['icc_sha256']==PROFILE_SHA and enc['pixel_sha256']==image['pixel_sha256']
        and enc['quantization']=='finite-clamp-round-half-away-v1' and enc['clipped_low']==[0,0,0] and enc['clipped_high']==[0,0,0],
        'declared encoding and no clips')
    need(v['final_gate']==folds[-1]['gate'],'final census is saved last fold')
    observer=v['observer'];obs=observer['observation'];population=3*w*h
    need(observer['output_f32_sha256_before']==observer['output_f32_sha256_after']==enc['prequantization_f32_sha256']
         and sha(enc['prequantization_f32_sha256']),'actual output unchanged across observer')
    need(obs['called'] is True and obs['mode']==mode and obs['visited_samples']==(population if mode=='on' else 0)
         and obs['allocated_samples']==(0 if mode=='off' else population),'actual output observer population')
    if mode=='on':need(obs['plane_major_f32_sha256']==enc['prequantization_f32_sha256'],'actual observed output hash')
    if mode=='placebo':need(obs['placebo_f32_sha256']==digest(b'\0'*(4*population)),'actual placebo allocation hash')
    if ordinal in (0,1,2):constant_contract(image['pixels'],tuple(RECIPE['means'][str(n)]),w,h)
    if ordinal==3:compare_pixels(image['pixels'],literal_pixels('address',0,w,h),'literal identical-frame output')
    if ordinal==4:offset_contract(image['pixels'])
    if ordinal==8:
        legacy_raw,_=read_ref(LEGACY_OUTPUT,128*1024)
        need(legacy_raw==saved['output.tiff'],'exact archived v1 whole TIFF compatibility')
    return dict(ordinal=ordinal,id=ident,verified=True,folded_frames=n,pixel_sha256=image['pixel_sha256'],
                whole_tiff_sha256=image['file_sha256'],gate_observations=observations),image,v
def saved_render_bundle(args,index):
    raw=read_bytes(args.run_bundle,64*1024)
    need(digest(raw)==args.run_bundle_sha256 and Path(args.run_bundle).resolve()==BASE/"render-bundle-1.json","actual run bundle")
    bundle=strict_json(raw);caps={"result":256*1024,"tail":8192,"outer":65536,"stdout":8192,"stderr":32768,"exit":1024}
    need(type(bundle) is dict and set(bundle)==set(caps),"six external roles")
    b={k:read_ref(bundle[k],cap,empty=k=="stderr")[0] for k,cap in caps.items()}
    result,tail,outer,ad=(strict_json(b[k]) for k in ("result","tail","outer","stdout"))
    need(result["schema"]=="common-tiff-dimensions-owned-stage-v1" and result["stage"]=="render","actual render stage")
    for k,filename in (("result","result.json"),("tail","parent-tail.json")):
        need(Path(bundle[k]["path"]).resolve()==BASE/"render-1"/filename,"render terminal path")
    need(set(outer)=={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds","stdout","stderr","exit",
         "stdout_bytes","stderr_bytes","scope"} and outer["schema"]=="common-tiff-dimensions-stage-external-v1","closed external capture")
    need(outer["command"]==result["invocation"] and type(outer["exit_code"]) is int and b["exit"].strip()==str(outer["exit_code"]).encode(),
         "actual invocation and exit")
    for k in ("stdout","stderr","exit"):need(same_ref(outer[k],bundle[k]),"outer stream association")
    need(outer["stdout_bytes"]==len(b["stdout"]) and outer["stderr_bytes"]==len(b["stderr"]),"outer stream extents")
    need(set(ad)=={"status","result","tail"} and ad["status"]==result["status"] and
         same_ref(ad["result"],bundle["result"]) and same_ref(ad["tail"],bundle["tail"]) and
         b["stdout"]==canonical(ad)+b"\n","exact terminal advertisement")
    need(tail["schema"]=="common-tiff-dimensions-parent-tail-v1" and same_ref(tail["result"],bundle["result"]),"tail result association")
    relraw,_=read_ref(result["release"],1024*1024);release=strict_json(relraw)
    need(release["schema"]=="common-tiff-dimensions-stage-release-v1" and release["stage"]=="render" and
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
    own,spec,_=source_authority(args.source_sha256)
    need(sources[SELF.relative_to(ROOT).as_posix()]=={k:own[k] for k in ('bytes','sha256')} and
         sources[(BASE/'independent-spec.md').relative_to(ROOT).as_posix()]=={k:spec[k] for k in ('bytes','sha256')},
         'same independent fixture/checker source and spec')
    source_authority(args.source_sha256)
    cp=(BASE/"run-stage.py").relative_to(ROOT).as_posix()
    need(same_ref(outer["source"],{"path":cp,**sources[cp]}),"actual controller source")
    exe=hash_large_ref(release["executable"],128*1024*1024)
    need(exe==BASE/"build-1/strehl-common-input.exe","actual compiled product path")
    commands=[[str(exe) if x=="ACTUAL_BINARY_PATH" else x for x in row["command"]] for row in index["cases"]]
    need(release["children"]==[{"command":c,"expected_exit_code":index["cases"][i]["expected_exit_code"]} for i,c in enumerate(commands)],"released fixed schedule")
    observed=result["children"];need(type(observed) is list and len(observed)<=24,"actual bounded child prefix")
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
          type(v.get("exit_code")) is int and v["exit_code"]==index["cases"][i]["expected_exit_code"])
        resources=(used is not None and used<=20 and finite_nonnegative(v.get("wall_seconds")) and v["wall_seconds"]<=20 and
          v.get("configured_job_limits")=={"flags":0x2200,"committed_bytes":1024*1024*1024} and
          typed_int(v.get("job_memory",{}).get("peak_job_memory_used_bytes"),0,1024*1024*1024))
        children.append({"ordinal":i,"record":v,"record_ref":ref,"raw_log":log,"process_complete":clean,
                         "resource_admissible":resources,"job_cpu_seconds":used})
    known=all(finite_nonnegative(tail.get(k)) for k in ("actual_parent_cpu_sample","whole_wall_sample","completed_child_cpu_seconds","live_child_cpu_seconds"))
    need(not known or tail["completed_child_cpu_seconds"]>=cpu,"no underreported terminal Job sum")
    complete=(result["status"]=="COMPLETE_STAGE_UNVERIFIED" and result.get("error") is None and
      result.get("finalization_errors")==[] and len(children)==24 and all(c["process_complete"] and c["resource_admissible"] for c in children) and
      outer["exit_code"]==0 and outer["timeout_terminated"] is False and known and tail["cpu_accounting_complete"] is True and
      tail["live_child_cpu_seconds"]==0 and tail["completed_child_cpu_seconds"]==cpu and
      tail["final_external_allowance"]=={"cpu_seconds":2,"wall_seconds":3} and tail["actual_parent_cpu_sample"]+cpu+2<=180 and
      finite_nonnegative(outer["elapsed_wall_seconds"]) and outer["elapsed_wall_seconds"]<=min(240,tail["whole_wall_sample"]+3))
    need(result['limits']=={'cpu_seconds':180,'wall_seconds':240,'committed_bytes':1024*1024*1024,
         'file_bytes':128*1024*1024,'scratch_bytes':0},'exact finite render stage allocation')
    summary={"child_job_cpu_seconds":cpu,"parent_cpu_sample":tail.get("actual_parent_cpu_sample"),"publication_cpu_allowance":2,
             "outer_wall_seconds":outer["elapsed_wall_seconds"],"scope":"whole child Jobs plus sampled parent and fixed tail"}
    return {"bundle":bundle,"result":result,"release":release,"children":children,"complete":complete,"accounting":summary},commands



def offset_contract(actual):
    expected=[v+208 for v in literal_pixels('offset',0,129,97)]
    need(len(actual)==len(expected),'offset output geometry')
    need(all(typed_int(a,0,65535) and abs(a-b)<=1 for a,b in zip(actual,expected)),
         'offset literal error within one code')
    return {'samples':len(expected),'max_absolute_error':max(abs(a-b) for a,b in zip(actual,expected)),
            'tolerance_codes':1,'scope':'fixed finite odd-grid additive-offset fixture'}


def compact(value,cap,label):
    need(len(canonical(value))<=cap,label)
    return value


WORK={};OUTPUT=None

def progress():
    if OUTPUT is None:return
    raw=canonical(WORK)+b'\n';need(len(raw)<=1024*1024,'progress extent')
    stage=OUTPUT/'progress.stage.json';target=OUTPUT/'progress.json'
    write_fresh(stage,raw,1024*1024);os.replace(stage,target)
    need(read_bytes(target,1024*1024)==raw,'progress same-byte publication')


def independent_power(images,receipts):
    """One fixed135-row saved-copy table; every available row is attempted."""
    tasks=[]
    def add(ident,requires,fn,reason=None):tasks.append((ident,requires,fn,reason))
    for ordinal,n in enumerate((2,5,8)):
        for ident,rgb in mean_competitors(n):
            w,h=(64,64) if n==2 else (129,97) if n==5 else (512,512)
            add(ident,(ordinal,),lambda ordinal=ordinal,rgb=rgb,w=w,h=h:
                constant_contract(images[ordinal]['pixels'],rgb,w,h),'constant literal RGB codes')
        add(f'n{n}-mean-restored',(ordinal,),lambda ordinal=ordinal,n=n,w=w,h=h:
            constant_contract(images[ordinal]['pixels'],tuple(RECIPE['means'][str(n)]),w,h))
    def contributors(which):
        original=receipts[1]['consumed'];ids=[x['id'] for x in original]
        changed=strict_json(canonical(original))
        if which=='omit':changed.pop()
        elif which=='duplicate':changed[-1]=changed[0]
        elif which=='counter':changed[-1]['merge_frames']-=1
        return contributor_ids(changed,ids)
    add('omitted-fold',(1,),lambda:contributors('omit'),'complete contributor prefix')
    add('duplicated-fold',(1,),lambda:contributors('duplicate'),'unique ordered contributors')
    add('wrong-fold-counter',(1,),lambda:contributors('counter'),'actual single fold per contributor')
    add('contributors-restored',(1,),lambda:contributors('restore'))
    def geometry(which):
        gate=strict_json(canonical(receipts[3]['final_gate']))
        if which=='width':gate['levels'][0]['width']-=1
        elif which=='floor':gate['levels'][1].update(width=64,height=48,sites=64*48)
        return levels_contract(gate,129,97)
    add('wrong-level-zero-width',(3,),lambda:geometry('width'),'actual level geometry')
    add('floor-instead-of-ceil',(3,),lambda:geometry('floor'),'actual level geometry')
    add('levels-restored',(3,),lambda:geometry('restore'))
    def address(which):
        values=images[3]['pixels'];w,h=129,97;changed=list(values)
        if which=='column':changed=[values[(y*w+x)*3+c] for y in range(h) for x in range(w-1) for c in range(3)]
        elif which=='row':changed[-w*3:]=values[-2*w*3:-w*3]
        elif which=='corner':changed[-3]^=1
        elif which=='color':changed=[values[i+c] for i in range(0,len(values),3) for c in (2,1,0)]
        elif which=='shift':changed=[values[(y*w+(x+1)%w)*3+c] for y in range(h) for x in range(w) for c in range(3)]
        return compare_pixels(changed,literal_pixels('address',0,w,h),'literal identical-frame output')
    for which,ident in (('column','dropped-last-column'),('row','replaced-last-row'),('corner','wrong-final-corner'),
                        ('color','red-blue-permutation'),('shift','one-pixel-address-shift')):
        reason='geometry' if which=='column' else 'literal RGB codes'
        add(ident,(3,),lambda which=which:address(which),'literal identical-frame output: '+reason)
    add('address-restored',(3,),lambda:address('restore'))
    def observer_fault():
        original=images[6];raw=bytearray(original['_raw']);raw[original['_pixel_offsets'][0]]^=1
        altered=inspect_tiff(bytes(raw),output=True)
        need(altered['pixels']!=original['pixels'],'actual observer-pixel fault exercised')
        return compare_observer([images[5],altered,images[7]])
    add('changed-observer-pixel',(5,6,7),observer_fault,'observer whole TIFF equality')
    add('observer-restored',(5,6,7),lambda:compare_observer([images[i] for i in (5,6,7)]))
    def profile_fault():
        original=images[3];raw=bytearray(original['_raw']);raw[original['_icc_offset']+20]^=1
        altered=inspect_tiff(bytes(raw),output=True)
        need(altered['pixels']==original['pixels'] and altered['icc_sha256']!=original['icc_sha256'],
             'actual ICC-only fault exercised')
        return admitted_profile(altered)
    add('wrong-actual-icc',(3,),profile_fault,'actual admitted output profile')
    add('profile-restored',(3,),lambda:admitted_profile(images[3]))
    def noise(which):
        model='synthetic-independent-rademacher8-v1';v=expected_noise(model)
        # Equivalent finite float spelling is an admitted restored operand.
        v['rgb_covariance']=[[float(x) for x in row] for row in v['rgb_covariance']];v['proxy_variance']=24.0
        if which=='variance':v['proxy_variance']=1
        elif which=='boolean':v['rgb_covariance'][0][1]=False
        return noise_contract(v,model)
    add('variance-one',(),lambda:noise('variance'),'exact injected noise declaration')
    add('boolean-zero-covariance',(),lambda:noise('boolean'),'exact injected noise declaration')
    add('noise-restored',(),lambda:noise('restore'))
    def offset(which):
        values=images[4]['pixels'];changed=list(values)
        if which=='plus-eight':changed=[v+8 for v in changed]
        elif which=='column':
            for y in range(97):changed[(y*129+128)*3:(y*129+129)*3]=values[(y*129+127)*3:(y*129+128)*3]
        elif which=='corner':changed[-3]+=8
        if which!='restore':need(changed!=values,'actual offset destroyer exercised')
        return offset_contract(changed)
    for which in ('plus-eight','column','corner'):
        add('offset-'+which,(4,),lambda which=which:offset(which),'offset literal error within one code')
    add('offset-restored',(4,),lambda:offset('restore'))
    need(len(tasks)==135 and len({row[0] for row in tasks})==135,'fixed135 unique independent controls')
    rows=[]
    for ident,requires,fn,reason in tasks:
        if not all(i in images and i in receipts for i in requires):
            row=dict(id=ident,passed=False,status='UNAVAILABLE',requires=list(requires))
        else:
            try:
                if reason is None:
                    value=fn();row=dict(id=ident,passed=True,restored=True)
                else:row=dict(negative(ident,reason,fn),passed=True)
            except (ValueError,KeyError,TypeError,OSError,UnicodeError,struct.error) as error:
                row=dict(id=ident,passed=False,status='CONTROL_REJECTED',error=bounded_error(error))
        rows.append(compact(row,2048,'control row extent'))
        WORK['independent_controls']=rows;check_time(44,88)
    progress()
    return rows


def verify(args):
    index,actual,catalog=fixture_authority(args)
    saved,commands=saved_render_bundle(args,index)
    captures=saved['result'].get('artifacts',{}).get('cases',[])
    need(type(captures) is list and len(captures)<=24,'bounded retained case prefix')
    summaries=[];images={};receipts={};failures=[]
    WORK.update(cases=summaries,independent_controls=[],failures=failures,accounting=saved['accounting'])
    progress()
    for i,row in enumerate(index['cases']):
        if i>=len(saved['children']) or i>=len(captures):
            summary=dict(ordinal=i,id=row['id'],verified=False,status='NO_LINKED_COMPLETED_CASE',
                         scope='may have been attempted; no completed case claimed')
        else:
            child=saved['children'][i]
            try:
                summary,image,receipt=product_case(index,row,child,captures[i],saved['release'],actual,catalog,commands[i])
                summary.update(process_complete=child['process_complete'],resource_admissible=child['resource_admissible'])
                if image is not None:images[i]=image
                receipts[i]=receipt
            except (ValueError,KeyError,TypeError,OSError,UnicodeError,struct.error) as error:
                error=bounded_error(error);failures.append(compact(dict(ordinal=i,error=error),4096,'error extent'))
                summary=dict(ordinal=i,id=row['id'],verified=False,status='SAVED_CASE_REJECTED',error=error)
        summaries.append(compact(summary,16*1024,'case summary extent'))
        progress();check_time(44,88)
    observer=None
    if all(i in images for i in (5,6,7)):
        try:observer=compare_observer([images[i] for i in (5,6,7)])
        except ValueError as error:failures.append(compact(dict(observer=bounded_error(error)),4096,'observer error extent'))
    gains={}
    for ordinal,receipt in receipts.items():
        if 'runtime' not in receipt:continue
        grid=receipt['plan']['grid'];key=str(grid['width'])+'x'+str(grid['height'])
        beta=receipt['runtime']['actual_core_white_band_gain']
        if key in gains and gains[key]!=beta:
            failures.append(compact(dict(band_gain='different source white gains at the same geometry',ordinal=ordinal),4096,'gain error extent'))
        else:gains[key]=beta
    WORK['band_gain_by_grid']=gains
    controls=independent_power(images,receipts)
    # Rebind immutable inputs/metadata to the original consumed bytes, no product rerun.
    for ref,_ in actual.values():read_ref(ref,MAX_TIFF if ref['path'].endswith('.tiff') else MAX_JSON)
    source_authority(args.source_sha256)
    complete=(saved['complete'] and len(summaries)==24 and all(x['verified'] for x in summaries) and
              len(receipts)==24 and observer is not None and len(controls)==135 and all(x['passed'] for x in controls) and not failures)
    WORK.update(status='PASS_COMMON_RGB_DIMENSIONS_SOFTWARE_INTEGRATION' if complete else 'REFUSED',
                software_integration_complete=complete,observer_comparison=observer,
                fixtures=file_ref(args.fixtures,read_bytes(args.fixtures,MAX_JSON)),
                run_bundle=file_ref(args.run_bundle,read_bytes(args.run_bundle,65536)),
                source=file_ref(SELF,read_bytes(SELF,128*1024)),physical_noise_calibration=False,
                real_geometry_admission=False,quality_admission=False,
                offset_check=offset_contract(images[4]['pixels']) if 4 in images else None,
                scope='Fixed24 identity common-RGB software cases;135 saved controls; no real capture or quality admission.')
    compact({k:v for k,v in WORK.items() if k not in ('cases','independent_controls','failures')},64*1024,'final framing extent')
    return WORK


def main():
    global OUTPUT
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True)
    prep=sub.add_parser('prepare')
    for flag in ('output','source-sha256'):prep.add_argument('--'+flag,required=True)
    check=sub.add_parser('verify')
    for flag in ('fixtures','fixtures-sha256','run-bundle','run-bundle-sha256','output','source-sha256'):
        check.add_argument('--'+flag,required=True)
    args=parser.parse_args()
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,'isolated stdlib-only invocation')
    expected=[sys.executable,'-I','-S','-B',str(SELF),args.mode]
    if args.mode=='prepare':expected+=['--output',str(Path(args.output).resolve())]
    else:expected+=['--fixtures',str(Path(args.fixtures).resolve()),'--fixtures-sha256',args.fixtures_sha256,
                   '--run-bundle',str(Path(args.run_bundle).resolve()),'--run-bundle-sha256',args.run_bundle_sha256,
                   '--output',str(Path(args.output).resolve())]
    expected+=['--source-sha256',args.source_sha256]
    need(sys.orig_argv==expected,'exact independent invocation')
    cpu,wall=(20,40) if args.mode=='prepare' else (45,90)
    WORK.update(schema='common-tiff-dimensions-independent-'+('preparation' if args.mode=='prepare' else 'verification')+'-v1',
                status='REFUSED',software_integration_complete=False)
    try:
        if args.mode=='verify':
            out=Path(args.output).resolve()
            need(out==BASE/'verify-1/check' and not out.exists() and out.parent.is_dir(),'fresh fixed verifier output')
            source_authority(args.source_sha256);out.mkdir();OUTPUT=out;progress()
        answer=prepare(args) if args.mode=='prepare' else verify(args)
    except (ValueError,KeyError,TypeError,OSError,UnicodeError,struct.error) as error:
        answer=WORK;answer.update(status='REFUSED',software_integration_complete=False,error=bounded_error(error),
                                 scope='Independent source/reader refusal, not a product scientific result')
    answer['own_work']={'cpu_seconds':time.process_time()-START_CPU,'wall_seconds':time.perf_counter()-START}
    answer['publication_allowance']={'cpu_seconds':1,'wall_seconds':2}
    if answer['own_work']['cpu_seconds']+1>cpu or answer['own_work']['wall_seconds']+2>wall:
        answer.update(status='REFUSED',software_integration_complete=False,resource_refusal='own allowance including publication')
    cap=64*1024 if args.mode=='prepare' else 1024*1024
    raw=canonical(answer)+b'\n';need(len(raw)<=cap,'fixed independent final extent')
    if OUTPUT is not None:write_fresh(OUTPUT/'result.json',raw,cap)
    need(sys.stdout.buffer.write(raw)==len(raw),'whole independent stdout');sys.stdout.buffer.flush()
    check_time(cpu,wall)
    return 0 if answer['status'] in ('PREPARED_UNRUN_FIXTURES','PASS_COMMON_RGB_DIMENSIONS_SOFTWARE_INTEGRATION') else 1


if __name__=='__main__':
    raise SystemExit(main())
