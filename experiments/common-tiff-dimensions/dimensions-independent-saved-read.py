"""Saved dimensions evidence reader; SOURCE ONLY until root release.

Draft author coordinate_verification also authored the original checker.
No independence is claimed from authorship alone. sampler_result_review must
challenge this source and interpret the released saved read. No candidate
modules, generators, process helpers, image libraries or checker functions are
imported. This entry point launches no processes and generates no TIFFs.
"""
import time
START = time.perf_counter()
CPU_START = time.process_time()
import argparse, hashlib, io, json, math, ntpath, os, re, stat, struct, sys, zipfile
from pathlib import Path

SELF = Path(__file__).resolve()
HERE = SELF.parent
ROOT = HERE.parents[1]
KIB = 1024
MIB = 1 << 20
EMPTY_SHA = hashlib.sha256(b"").hexdigest()
PROFILE_SHA = "16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef"
LEGACY_SHA = "1e6c9f9bd3146c0c8f7314c422e26c842eb45ba25d76d12adae8f8d690842f7e"
ORIGINAL_SHA = "8fefa5e31c614595367f644b314ece77da6bf5d4ec54c4edde80816a0e8cee47"
ORIGINAL_SPEC_SHA = "055b66302e3f73d3d62226c25cef939f74dd664149e1a7d005991ce09286489b"
PRODUCER_FREEZE_SHA = "f3778c80df31b6cde6e253797cf497ca2cdfced85f8507ae126ba03ce8563708"
FIXTURE_SHA = "d07f356bdd7b2286b88404a337afd831319130e979b9adc27222d5ad71b1bf98"
FIXTURE_AST_SHA = "6fdf3945d43620706246caae9e962209ae3386e9e2b85315baed018d102c90c7"
COMPILED = {"files":118,"canonical_sha256":"ee02f4b41cfc5cc5c1d501c72d9980f2131fba9b891e6b9aca9412e119ff72a8"}
EXE_SHA = "172a52135ebee5853169cd3cd8bd8e9c97b4dc6ad5a886c20bfd57ea0a4a0684"
IDS = ("mean-two-min","mean-five-odd","mean-eight-max","odd-address","odd-offset",
       "odd-noisy-off","odd-noisy-on","odd-noisy-placebo","legacy-constant",
       "count-zero","count-one","count-nine","width-low","width-high","height-low",
       "height-high","width-u32-overflow","legacy-count-two","legacy-odd","duplicate-input",
       "wrong-profile","wrong-proxy-variance","last-geometry","last-file-hash")
MODES = ("off","off","off","on","on","off","on","placebo","off") + ("off",)*15
FOLDS = (2,5,8,5,5,5,5,5,3) + (0,)*13 + (4,4)
REASONS = {9:"v2 requires two to eight inputs",10:"v2 requires two to eight inputs",
           11:"v2 requires two to eight inputs",12:"unsupported common grid",
           13:"unsupported common grid",14:"unsupported common grid",15:"unsupported common grid",
           16:"manifest JSON:",17:"v1 requires exactly three inputs",18:"unsupported common grid",
           19:"duplicate input id",20:"unadmitted input profile",
           21:"unsupported noise covariance or proxy variance",
           22:"TIFF dimensions do not match common grid",23:"file hash mismatch"}
MEANS = {2:(8360,16240,24120),5:(9488,16992,24496),8:(15650,21100,26550)}
DESCRIPTION = ("; identity common-RGB pixels; linear ProPhoto RGB D50; RGB16 code units; "
               "no WB, camera matrix, demosaic, exposure, tone or transfer; finite clamp then "
               "round half away from zero; simulation-only noise declaration")
CATEGORY_CAPS = {"executable":128*MIB,"source":24*MIB,"metadata":32*MIB,
                 "input":32*MIB,"output":16*MIB,"readback":16*MIB}
COUNTERS = dict.fromkeys(CATEGORY_CAPS,0)
CACHE = {}
IMAGES = {}
WRITTEN = 0
STATE = {}
OUTPUT = None
PROGRESS = None

def demand(value, message):
    if not value:
        raise ValueError(message)

def integer(v, low=0, high=(1<<63)-1):
    return type(v) is int and low <= v <= high

def finite(v):
    return type(v) in (int,float) and math.isfinite(v) and v >= 0

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def hash_text(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}",value) is not None

def encode(value):
    return (json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(",",":"))+"\n").encode("ascii")

def object_json(raw):
    def pairs(items):
        answer={}
        for k,v in items:
            demand(k not in answer,"duplicate JSON member")
            answer[k]=v
        return answer
    def invalid(value):
        raise ValueError("nonfinite JSON literal:"+value)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)

def tick(reserve=False):
    cpu=time.process_time()-CPU_START
    wall=time.perf_counter()-START
    demand(cpu+(2 if reserve else 0)<=30 and wall+(3 if reserve else 0)<=60,
           "fixed reader CPU/wall allowance")
    demand(sum(COUNTERS.values())<=256*MIB and WRITTEN<=16*MIB,"fixed read/write allowance")
    return {"cpu_sample_seconds":cpu,"wall_sample_seconds":wall}

def charge(category,n):
    demand(integer(n) and category in COUNTERS,"typed read reservation")
    demand(COUNTERS[category]+n<=CATEGORY_CAPS[category] and sum(COUNTERS.values())+n<=256*MIB,
           "read reservation before allocation:"+category)
    COUNTERS[category]+=n
    tick()

def location(name):
    demand(type(name) is str and 0<len(name)<=512 and name.isascii() and "\x00" not in name,
           "bounded local path spelling")
    text=name.replace("/","\\")
    if text.startswith("\\\\?\\"):
        text=text[4:]
        demand(re.match(r"^[A-Za-z]:\\",text) is not None,"verbatim local drive only")
    demand(not text.startswith("\\\\") and not text.startswith("\\??\\"),
           "no device or UNC path")
    drive,tail=ntpath.splitdrive(text)
    if drive:
        demand(re.fullmatch("[A-Za-z]:",drive) is not None and tail.startswith("\\"),
               "absolute drive path")
        parts=tail[1:].split("\\")
    else:
        demand(not tail.startswith("\\"),"no root-relative path")
        parts=tail.split("\\")
    demand(all(p not in ("",".","..") and ":" not in p and not p.endswith((" ",".")) for p in parts),
           "plain local path components")
    absolute=ntpath.normpath(text if drive else ntpath.join(str(ROOT),text))
    demand(ntpath.commonpath([str(ROOT),absolute]).casefold()==str(ROOT).casefold(),
           "read path inside repository")
    return Path(absolute)

def ref_shape(ref, empty=False):
    demand(type(ref) is dict and set(ref)=={"path","bytes","sha256"},"closed FileRef")
    demand(integer(ref["bytes"],0 if empty else 1) and hash_text(ref["sha256"]),"typed FileRef fields")
    p=location(ref["path"])
    if ref["bytes"]==0:
        demand(empty and ref["sha256"]==EMPTY_SHA,"canonical empty evidence role")
    return p

def same(a,b,empty=False):
    pa,pb=ref_shape(a,empty),ref_shape(b,empty)
    return str(pa).casefold()==str(pb).casefold() and a["bytes"]==b["bytes"] and a["sha256"]==b["sha256"]

def at(ref,path,empty=False):
    demand(str(ref_shape(ref,empty)).casefold()==str(path).casefold(),"exact evidence location:"+str(path))

def shared(s):
    return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,"st_file_attributes",0)

def full(s):
    return shared(s)+(s.st_ctime_ns,)

def plain(path):
    for p in (path,*path.parents):
        s=p.lstat()
        demand(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&0x400,
               "plain no-follow evidence ancestry")

def read(ref,category="metadata",cap=256*KIB,empty=False,stream=False):
    p=ref_shape(ref,empty)
    demand(ref["bytes"]<=cap,"per-role input extent")
    key=str(p).casefold()
    if key in CACHE:
        old=CACHE[key]
        demand(same(ref,old["ref"],empty),"repeated path retains exact original binding")
        demand(full(p.lstat())==old["path_identity"],"cached path stability")
        demand(not (not stream and old["raw"] is None),"stream-only buffer cannot be used as content")
        return old["raw"]
    plain(p)
    first=p.lstat()
    demand(stat.S_ISREG(first.st_mode) and first.st_nlink==1 and first.st_size==ref["bytes"],"bounded ordinary file")
    charge(category,ref["bytes"]+1)
    h=hashlib.sha256()
    pieces=[] if not stream else None
    with p.open("rb") as f:
        opened=os.fstat(f.fileno())
        demand(shared(first)==shared(opened),"cross-API shared opened identity")
        remaining=ref["bytes"]
        while remaining:
            block=f.read(min(MIB,remaining))
            demand(block,"complete bounded file read")
            h.update(block)
            if pieces is not None:pieces.append(block)
            remaining-=len(block)
            tick()
        demand(f.read(1)==b"","declared extent EOF")
        after=os.fstat(f.fileno())
    demand(full(first)==full(p.lstat()) and full(opened)==full(after),"path and handle each stable")
    demand(h.hexdigest()==ref["sha256"],"authenticated exact file bytes")
    raw=b"".join(pieces) if pieces is not None else None
    CACHE[key]={"ref":ref,"path_identity":full(first),"handle_identity":full(opened),"raw":raw,"category":category}
    return raw

def parsed(ref,category="metadata",cap=256*KIB):
    return object_json(read(ref,category,cap))

def ref_from_path(path,expected,cap):
    # Bootstrap has no release FileRef yet; byte extent is bounded before read.
    path=location(str(path))
    demand(hash_text(expected),"bootstrap expected hash")
    extent=path.lstat().st_size
    demand(integer(extent,1,cap),"bootstrap extent")
    return {"path":str(path),"bytes":extent,"sha256":expected}

def map_check(value,count):
    demand(type(value) is dict and len(value)==count and count<=512,"exact finite source population")
    for name,pin in value.items():
        demand(type(name) is str and name==name.replace("\\","/") and not name.startswith("/"),
               "archive source name")
        demand(type(pin) is dict and set(pin)=={"bytes","sha256"} and integer(pin["bytes"],1,4*MIB)
               and hash_text(pin["sha256"]),"positive source namespace")
        location(name)
    return value

def archive_check(ref,expected):
    raw=read(ref,"source",16*MIB)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        items=z.infolist()
        demand(len(items)==len(expected) and len({i.filename for i in items})==len(items)
               and {i.filename for i in items}==set(expected),"exact unique archive members")
        for item in items:
            name=item.filename
            demand(not item.is_dir() and "\\" not in name and not name.startswith("/")
                   and all(x not in ("",".","..") for x in name.split("/")),"normalized archive member")
            pin=expected[name]
            demand(item.file_size==pin["bytes"] and item.file_size<=4*MIB
                   and item.flag_bits&1==0,"bounded unencrypted source member")
            charge("source",item.file_size+1)
            with z.open(item) as f:
                raw=f.read(item.file_size+1)
            demand(len(raw)==pin["bytes"] and digest(raw)==pin["sha256"],"exact inflated source member")
    return {"archive":ref,"members":len(expected),"uncompressed_bytes":sum(v["bytes"] for v in expected.values())}

def source_history(release):
    producer=parsed(release["producer_freeze"],"source",64*KIB)
    demand(release["producer_freeze"]["sha256"]==PRODUCER_FREEZE_SHA
           and producer["schema"]=="common-tiff-dimensions-root-source-freeze-v2","held producer190 freeze")
    base=parsed(producer["base_freeze"],"source",64*KIB)
    demand(base["schema"]=="common-tiff-dimensions-root-source-freeze-v1"
           and same(base["archive"],producer["base_archive"]),"base181 freeze/archive")
    bm=map_check(base["source_bindings"],181)
    pm=map_check(producer["source_bindings"],190)
    changed=producer["changed_or_new"]
    demand(type(changed) is list and len(changed)==len(set(changed))
           and set(changed)=={k for k,v in pm.items() if bm.get(k)!=v}
           and set(bm)<=set(pm),"exact producer replacement/addition set")
    execution=parsed(release["execution_freeze"],"source",64*KIB)
    demand(set(execution)=={"schema","producer_freeze","source_bindings","delta_archive"}
           and execution["schema"]=="common-tiff-dimensions-recovery-source-freeze-v1"
           and same(execution["producer_freeze"],release["producer_freeze"]),"additive recovery freeze")
    em=map_check(execution["source_bindings"],200)
    extras=set(em)-set(pm)
    expected={"run-recovery-stage.py","recovery-authority.py","prepare-recovery-release.py",
              "capture-recovery-stage.py","recovery-contract.md","recoverydesign.md",
              "recovery-controls.py","recovery-spec.md","recovery-checker.py","recovery-source-review.md"}
    demand(extras=={"experiments/common-tiff-dimensions/"+x for x in expected}
           and all(em[k]==v for k,v in pm.items()),"original190 unchanged plus closed10")
    demand(pm["experiments/common-tiff-dimensions/independent-controls.py"]=={"bytes":65751,"sha256":ORIGINAL_SHA}
           and pm["experiments/common-tiff-dimensions/independent-spec.md"]=={"bytes":19270,"sha256":ORIGINAL_SPEC_SHA},
           "original fixture/checker producer identity")
    proofs=[archive_check(base["archive"],bm),archive_check(producer["delta_archive"],{k:pm[k] for k in changed}),
            archive_check(execution["delta_archive"],{k:em[k] for k in extras})]
    STATE["source_composition"]={"base_count":181,"producer_count":190,"execution_count":200,"archives":proofs,
         "scope":"Archived exact source buffers; no module execution, live runtime inventory or external library closure."}
    return bm,pm,em

def job_cpu(job):
    demand(type(job) is dict,"actual Job record")
    for k in ("total_user_100ns","total_kernel_100ns","total_cpu_100ns","active_processes"):
        demand(integer(job.get(k)),"nonnegative integer Job operand")
    demand(job["total_cpu_100ns"]==job["total_user_100ns"]+job["total_kernel_100ns"],"Job integer sum")
    return job["total_cpu_100ns"]/10_000_000

def compile_policy(record):
    c=record["compile_cleanup"]
    keys={"schema","policy","disposition","attempted","succeeded","completed","before_accounting",
          "after_accounting","remaining_process_ids","pid_query_performed","pid_query_error",
          "started_wall_seconds","ended_wall_seconds","wait_seconds","max_wait_seconds","error","scope"}
    demand(type(c) is dict and set(c)==keys and c["schema"]=="m194h-compile-owned-descendant-cleanup-v1"
           and c["policy"]=="AFTER_DIRECT_ZERO_AND_PIPE_EOF" and c["completed"] is True
           and c["error"] is None and c["pid_query_error"] is None,"explicit compile completion")
    before,after=c["before_accounting"],c["after_accounting"]
    demand(job_cpu(before)<=job_cpu(after)<=job_cpu(record["job_accounting"])
           and after["active_processes"]==0,"final zero and monotone compile Job")
    demand(all(finite(c[k]) for k in ("started_wall_seconds","ended_wall_seconds","wait_seconds"))
           and c["max_wait_seconds"]==5 and c["wait_seconds"]==c["ended_wall_seconds"]-c["started_wall_seconds"]
           and c["wait_seconds"]<=5 and c["ended_wall_seconds"]<=record["wall_seconds"],"bounded compile cleanup interval")
    ids=c["remaining_process_ids"]
    demand(type(c["pid_query_performed"]) is bool,"typed PID-query flag")
    if c["pid_query_performed"]:
        demand(type(ids) is list and len(ids)<=1024 and len(ids)==len(set(ids))
               and all(integer(x,1,(1<<32)-1) for x in ids),"bounded actual PID-only census")
    else:demand(ids is None,"unqueried PID census remains unknown")
    if c["disposition"]=="NATURAL_JOB_EXIT":
        demand(c["attempted"] is False and c["succeeded"] is False and before["active_processes"]==0,
               "natural compile completion")
    else:
        demand(c["disposition"]=="INTENTIONAL_OWNED_JOB_CLEANUP" and c["attempted"] is True
               and c["succeeded"] is True and before["active_processes"]>0 and c["pid_query_performed"],
               "intentional owned descendant cleanup distinguished")
    return c["disposition"]

def child_read(ref,command,expected,cap_cpu,cap_wall,cap_memory,log_cap,expected_log,compile_only=False):
    value=parsed(ref,cap=32*KIB)
    at(value["log"],expected_log)
    raw=read(value["log"],cap=log_cap)
    demand(value["command"]==command and integer(value["log_bytes"]) and value["log_bytes"]==len(raw),
           "actual child argv and log association")
    cpu=job_cpu(value["job_accounting"])
    reasons=[]
    tests={"clean_exit":type(value.get("exit_code")) is int and value["exit_code"]==expected,
      "terminal":value.get("terminal_job_accounting") is True and value["job_accounting"]["active_processes"]==0,
      "direct_exit_and_eof":value.get("direct_exit_observed") is True and value.get("pipe_eof_observed") is True,
      "drain":value.get("post_exit_drain",{}).get("completed") is True,
      "no_error":value.get("error") is None and value.get("cleanup_errors")==[],
      "no_emergency_kill":value.get("termination",{}).get("attempted") is False,
      "cpu_bound":cpu<=cap_cpu,
      "wall_bound":finite(value.get("wall_seconds")) and value["wall_seconds"]<=cap_wall}
    limits=value.get("configured_job_limits")
    tests["installed_memory_limit"]=(type(limits) is dict and integer(limits.get("flags"))
           and limits["flags"]==0x2200 and integer(limits.get("committed_bytes")) and limits["committed_bytes"]==cap_memory)
    memory=value.get("job_memory")
    tests["peak_memory_bound"]=(type(memory) is dict and integer(memory.get("peak_job_memory_used_bytes"))
                               and memory["peak_job_memory_used_bytes"]<=cap_memory)
    disposition="STRICT_NATURAL_REQUIRED"
    if compile_only:
        try:disposition=compile_policy(value)
        except (ValueError,KeyError,TypeError) as exc:tests["compile_policy"]=False;reasons.append(str(exc))
    else:tests["strict_noncompile"]="compile_cleanup" not in value
    summary={"record":ref,"log":value["log"],"exit_code":value.get("exit_code"),"cpu_seconds":cpu,
             "job_integer_operands":value["job_accounting"],"wall_seconds":value.get("wall_seconds"),
             "compile_completion":disposition,"checks":tests,"errors":reasons,"admissible":all(tests.values())}
    return value,raw,summary

STAGE_LIMITS={"build":(600,300,3<<30,128*MIB),"prepare":(30,60,1<<30,34*MIB),
              "recovery":(10,20,1<<30,2*MIB),"render":(180,240,1<<30,128*MIB),
              "verify":(60,120,1<<30,19*MIB)}
CHILD_LIMITS={"build":(600,300,3<<30,16*MIB),"prepare":(20,40,1<<30,256*KIB),
              "render":(20,20,1<<30,256*KIB),"verify":(45,90,1<<30,MIB)}

def stage_read(name,bundle,maps,expected_status="COMPLETE_STAGE_UNVERIFIED"):
    caps={"result":256*KIB,"tail":8192,"outer":65536,"stdout":8192,"stderr":32768,"exit":1024}
    demand(type(bundle) is dict and set(bundle)==set(caps),"closed six-role stage bundle")
    raw={k:read(bundle[k],cap=n,empty=k=="stderr") for k,n in caps.items()}
    p,t,o,advert=(object_json(raw[k]) for k in ("result","tail","outer","stdout"))
    version=1 if name in ("build","prepare") else 2
    demand(p["schema"]==f"common-tiff-dimensions-owned-stage-v{version}" and p["stage"]==name,
           "actual stage schema")
    stage_dir={"build":"build-2","prepare":"prepare-1","recovery":"recovery-1","render":"render-1","verify":"verify-1"}[name]
    at(bundle["result"],HERE/stage_dir/"result.json")
    at(bundle["tail"],HERE/stage_dir/"parent-tail.json")
    demand(p["status"]==expected_status and p["finalization_errors"]==[],"actual recorded stage disposition")
    demand((p.get("error") is None)==(expected_status=="COMPLETE_STAGE_UNVERIFIED"),"stage error/disposition")
    outer_keys={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds",
                "stdout","stderr","exit","stdout_bytes","stderr_bytes","scope"}
    expected_exit=1 if expected_status=="REFUSED" else 0
    demand(set(o)==outer_keys and o["schema"]==f"common-tiff-dimensions-stage-external-v{version}"
           and type(o["exit_code"]) is int and o["exit_code"]==expected_exit and o["timeout_terminated"] is False
           and raw["exit"]==f"{expected_exit}\n".encode(),"external stage outcome without intervention")
    for role in ("stdout","stderr","exit"):
        demand(same(o[role],bundle[role],empty=role=="stderr"),"outer raw role association")
    demand(o["stdout_bytes"]==len(raw["stdout"]) and o["stderr_bytes"]==len(raw["stderr"])
           and raw["stderr"]==b"" and raw["stdout"]==encode(advert),"whole raw advertisement")
    demand(set(advert)=={"status","result","tail"} and advert["status"]==p["status"]
           and same(advert["result"],bundle["result"]) and same(advert["tail"],bundle["tail"]),"publication association")
    r=parsed(p["release"],cap=MIB)
    demand(r["schema"]==f"common-tiff-dimensions-stage-release-v{version}" and r["stage"]==name
           and r["source_bindings"]==maps,"same exact stage source map")
    demand(set(r)=={"schema","stage","source_bindings","inputs","executable","fixtures","run_bundle",
                    "prerequisites","command","children"},"ten-key stage release")
    command=[p["release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in r["command"]]
    demand(command==p["invocation"]==o["command"],"actual released controller command")
    controller="experiments/common-tiff-dimensions/"+("run-stage.py" if version==1 else "run-recovery-stage.py")
    demand(same(o["source"],{"path":controller,**maps[controller]}),"actual stage controller source")
    demand(t["schema"]==f"common-tiff-dimensions-parent-tail-v{version}" and same(t["result"],bundle["result"])
           and t["cpu_accounting_complete"] is True and finite(t["live_child_cpu_seconds"])
           and t["live_child_cpu_seconds"]==0 and t["final_external_allowance"]=={"cpu_seconds":2,"wall_seconds":3},
           "terminal accounting and publication reserve")
    demand(type(p["children"]) is list and type(r["children"]) is list,"child sequence")
    expected_count=0 if name=="recovery" else 24 if name=="render" else 1
    demand(len(p["children"])==len(r["children"])==expected_count,"fixed stage child count")
    children=[]
    for i,ref in enumerate(p["children"]):
        at(ref,HERE/stage_dir/f"child-{i:02}.json")
        spec=r["children"][i]
        demand(spec["expected_exit_code"]==(int(i>=9) if name=="render" else 0),"fixed expected child exit")
        c,log,summary=child_read(ref,spec["command"],spec["expected_exit_code"],*CHILD_LIMITS[name],
                                   expected_log=HERE/stage_dir/f"child-{i:02}.log",compile_only=name=="build")
        children.append((c,log,summary))
    total=sum(c[2]["cpu_seconds"] for c in children)
    demand(finite(t["completed_child_cpu_seconds"]) and t["completed_child_cpu_seconds"]==total,
           "actual integer Job totals counted once in parent tail")
    cpu,wall,mem,files=STAGE_LIMITS[name]
    demand(all(finite(t[k]) for k in ("actual_parent_cpu_sample","whole_wall_sample"))
           and finite(o["elapsed_wall_seconds"]) and t["actual_parent_cpu_sample"]+total+2<=cpu
           and o["elapsed_wall_seconds"]<=min(wall,t["whole_wall_sample"]+3),"stage sample plus tail and actual external interval")
    demand(p["limits"]=={"cpu_seconds":cpu,"wall_seconds":wall,"committed_bytes":mem,"file_bytes":files,
                         "scratch_bytes":4*(1<<30) if name=="build" else 0},"fixed stage resources")
    summary={"name":name,"bundle":bundle,"status":p["status"],"error":p.get("error"),
             "children":[x[2] for x in children],"actual_external_child_wall_seconds":o["elapsed_wall_seconds"],
             "parent_cpu_sample":t["actual_parent_cpu_sample"],"tail_reserve":t["final_external_allowance"],
             "child_job_cpu_seconds":total,"all_children_admissible":all(x[2]["admissible"] for x in children),
             "scope":"Parent CPU is sampled plus reserve; outer interval is actual controller child duration, not the capture wrapper lifetime."}
    STATE["stages"].append(summary)
    return {"parent":p,"tail":t,"outer":o,"release":r,"children":children,"summary":summary}

def tiff_decode(ref,output=False,version=2):
    """Different address choice: each y selects its strip then its row offset.
    Pixel bytes are read through that row address, not by concatenating strips.
    """
    category="output" if output else "input"
    key=str(ref_shape(ref)).casefold()
    if key in IMAGES:
        demand(same(IMAGES[key]["ref"],ref),"cached TIFF identity")
        return IMAGES[key]
    raw=read(ref,category,(128*KIB if output else 256*KIB) if version==1 else 1638400)
    demand(len(raw)>=8 and raw[:4]==b"II*\x00","little-endian classic TIFF")
    u16=lambda offset:struct.unpack_from("<H",raw,offset)[0]
    u32=lambda offset:struct.unpack_from("<I",raw,offset)[0]
    directory=u32(4)
    demand(8<=directory<=len(raw)-6,"IFD offset within buffer")
    count=u16(directory)
    end=directory+2+12*count+4
    demand(13<=count<=19 and end<=len(raw) and u32(end-4)==0,"bounded single IFD")
    required={256,257,258,259,262,270,273,277,278,279,284,339,34675}
    allowed=required|({274,282,283,296,305,317} if output else set())
    sizes={1:1,2:1,3:2,4:4,5:8,7:1}
    fields={}
    occupied=[(0,8,"header"),(directory,end,"IFD")]
    order=[]
    for n in range(count):
        entry=directory+2+n*12
        tag,kind=struct.unpack_from("<HH",raw,entry)
        number=u32(entry+4)
        demand(tag in allowed and tag not in fields and kind in sizes and number>0,"unique admitted IFD field")
        length=number*sizes[kind]
        start=entry+8 if length<=4 else u32(entry+8)
        demand(0<=start<=len(raw)-length,"field buffer bounds")
        if length>4:
            demand(start>=8,"external field beyond header")
            occupied.append((start,start+length,"field:"+str(tag)))
        fields[tag]=(kind,number,start,length)
        order.append(tag)
    demand(required<=set(fields),"complete RGB16 IFD")
    def numbers(tag):
        kind,number,start,length=fields[tag]
        demand(kind in (3,4) and number<=513,"bounded integer TIFF field")
        code="H" if kind==3 else "I"
        return struct.unpack_from("<"+str(number)+code,raw,start)
    def scalar(tag,expected=None):
        values=numbers(tag)
        demand(len(values)==1 and (expected is None or values[0]==expected),"scalar TIFF field:"+str(tag))
        return values[0]
    width,height=scalar(256),scalar(257)
    demand(1<=width<=512 and 1<=height<=512,"bounded decoded geometry")
    for tag,value in ((259,1),(262,2),(277,3),(284,1)):scalar(tag,value)
    demand(numbers(258)==(16,16,16) and numbers(339)==(1,1,1),"unsigned interleaved RGB16")
    if 274 in fields:scalar(274,1)
    if 317 in fields:scalar(317,1)
    if output:demand(317 in fields and 305 in fields,"writer predictor/software present")
    for tag in (282,283):
        if tag in fields:
            kind,number,start,length=fields[tag]
            demand(kind==5 and number==1 and u32(start+4)>0,"finite rational resolution")
    if 296 in fields:demand(scalar(296) in (1,2,3),"resolution unit")
    rows=scalar(278)
    demand(1<=rows<(1<<32),"positive RowsPerStrip")
    offsets,extents=numbers(273),numbers(279)
    demand(len(offsets)==len(extents)==(height+rows-1)//rows,"row coverage by strips")
    for i,(offset,extent) in enumerate(zip(offsets,extents)):
        expected=min(rows,height-i*rows)*width*6
        demand(extent==expected and offset>=8 and offset<=len(raw)-extent,"exact full-strip extent")
        occupied.append((offset,offset+extent,"strip:"+str(i)))
    ordered=sorted(occupied)
    demand(all(a[1]<=b[0] for a,b in zip(ordered,ordered[1:])),"disjoint occupied TIFF intervals")
    def ascii_field(tag):
        kind,number,start,length=fields[tag]
        demand(kind==2 and number==length and raw[start+length-1]==0,"terminated ASCII field")
        value=raw[start:start+length-1]
        demand(b"\0" not in value,"single TIFF ASCII string")
        return value.decode("utf-8")
    description=ascii_field(270)
    if output:
        demand(ascii_field(305)==f"strehl-common-input common-tiff-stack-v{version}","schema-specific writer label")
        demand(description==f"common-tiff-stack-v{version}"+DESCRIPTION,"schema-specific output semantics")
    kind,number,start,length=fields[34675]
    demand(kind in (1,7) and number==length==548 and raw[start+36:start+40]==b"acsp"
           and digest(raw[start:start+length])==PROFILE_SHA,"exact admitted ICC bytes")
    payload=bytearray(6*width*height)
    address_hash=hashlib.sha256()
    for y in range(height):
        strip=y//rows
        relative_row=y-strip*rows
        row_start=offsets[strip]+relative_row*width*6
        row_end=row_start+width*6
        demand(row_start>=offsets[strip] and row_end<=offsets[strip]+extents[strip],"row's actual strip-address range")
        payload[y*width*6:(y+1)*width*6]=raw[row_start:row_end]
        address_hash.update(struct.pack("<III",y,row_start,row_end))
        tick()
    answer={"ref":ref,"width":width,"height":height,"payload":bytes(payload),
            "pixel_sha256":digest(payload),"file_sha256":ref["sha256"],"description":description,
            "icc_sha256":PROFILE_SHA,"strip_count":len(offsets),"ifd_tag_order":order,
            "row_address_sha256":address_hash.hexdigest(),"occupied_intervals":len(occupied)}
    IMAGES[key]=answer
    return answer

def pixel(image,x,y):
    return struct.unpack_from("<HHH",image["payload"],6*(y*image["width"]+x))

def address_literal(x,y):
    if x==128 and y==96:return (60001,45003,15007)
    if y==96:return (12000+3*x,52000+x,32000+2*x)
    if x==128:return (50000+y,22000+2*y,10000+3*y)
    if 16<=x<48 and 24<=y<56:return (8192,24576,49152)
    return 4000+101*x+7*y,18000+13*x+83*y,36000+47*x+19*y

def offset_literal(x,y,offset=208):
    if x==128 and y==96:p=1777
    elif y==96:p=1400+x
    elif x==128:p=1200+y
    elif 16<=x<48 and 24<=y<56:p=512
    else:p=(13*x+29*y)%997
    return tuple(base+p+offset for base in (1000,3000,5000))

def constant_color(i):
    return (8000+240*(1<<i),16000+160*(1<<i),24000+80*(1<<i))

def noise_literal(i,x,y):
    sign=4096 if (x//4+y//4)%2==0 else -4096
    texture=sign if x>=65 else 0
    colors=[]
    for channel,base in enumerate((14000,24000,34000)):
        h=hashlib.sha256(b"common-tiff-dimensions-rademacher-v1"+struct.pack("<IIII",i,y,x,channel)).digest()
        colors.append(base+texture+(8 if h[0]&1 else -8))
    return tuple(colors)

def image_literal(image,kind,frame):
    w,h=image["width"],image["height"]
    constant=constant_color(frame) if kind in ("constant","bad-geometry","bad-hash") else (45000,50000,55000) if kind=="ninth" else None
    if constant is not None:
        expected=struct.pack("<HHH",*constant)*w*h
        if kind=="bad-hash":
            expected=struct.pack("<H",constant[0]+1)+expected[2:]
        demand(image["payload"]==expected,"literal full constant/fault image")
        return
    for y in range(h):
        row=bytearray(w*6)
        for x in range(w):
            rgb=address_literal(x,y) if kind=="address" else offset_literal(x,y,(0,40,120,280,600)[frame]) if kind=="offset" else noise_literal(frame,x,y)
            struct.pack_into("<HHH",row,x*6,*rgb)
        demand(image["payload"][y*w*6:(y+1)*w*6]==row,"literal spatial/noisy input row:"+str(y))
        tick()

def proxy_digest(image):
    if "proxy_sha256" not in image:
        out=hashlib.sha256()
        row_bytes=6*image["width"]
        for y in range(image["height"]):
            row=bytearray(4*image["width"])
            for x,(r,g,b) in enumerate(struct.iter_unpack("<HHH",image["payload"][y*row_bytes:(y+1)*row_bytes])):
                struct.pack_into("<f",row,x*4,(r+2*g+b)/4)
            out.update(row)
            tick()
        image["proxy_sha256"]=out.hexdigest()
    return image["proxy_sha256"]

def eight_partition(x,y):
    if x==128 and y==96:return 0
    if y==96:return 1
    if x==128:return 2
    if 16<=x<48 and 24<=y<56:return 3
    return 4+2*(x&1)+(y&1)

def partition_errors(image,kind):
    demand((image["width"],image["height"])==(129,97),"odd output partition geometry")
    names=("corner","final-row-excluding-corner","final-column-excluding-corner","flat-interior-patch",
           "remaining-even-x-even-y","remaining-even-x-odd-y","remaining-odd-x-even-y","remaining-odd-x-odd-y")
    rows=[{"id":name,"sites":0,"channels":[{"signed_min":65535,"signed_max":-65535,
             "max_abs":0,"nonzero":0,"outside_tolerance":0,"first_failure":None} for _ in range(3)]} for name in names]
    tolerance=0 if kind=="address" else 1
    for y in range(97):
        for x in range(129):
            row=rows[eight_partition(x,y)]
            row["sites"]+=1
            target=address_literal(x,y) if kind=="address" else offset_literal(x,y)
            for c,(actual,expected) in enumerate(zip(pixel(image,x,y),target)):
                error=actual-expected
                q=row["channels"][c]
                q["signed_min"]=min(q["signed_min"],error)
                q["signed_max"]=max(q["signed_max"],error)
                q["max_abs"]=max(q["max_abs"],abs(error))
                q["nonzero"]+=int(error!=0)
                q["outside_tolerance"]+=int(abs(error)>tolerance)
                if abs(error)>tolerance and q["first_failure"] is None:
                    q["first_failure"]={"x":x,"y":y,"actual":actual,"expected":expected}
        tick()
    demand([r["sites"] for r in rows]==[1,128,96,1024,2816,2816,2816,2816],"fixed disjoint exhaustive spatial partition")
    return {"kind":kind,"tolerance_codes":tolerance,"rows":rows,
            "passed":all(c["outside_tolerance"]==0 for r in rows for c in r["channels"]),
            "scope":"Disjoint spatial audit of the same saved image, not independent repeats or a new quality metric."}

def numeric_equal(a,b):
    return type(a) in (int,float) and math.isfinite(a) and a==b

def noise_check(value):
    keys={"model","units","rgb_covariance","proxy_variance","band_transfer"}
    demand(type(value) is dict and set(value)==keys and value["model"] in
           ("synthetic-noiseless-v1","synthetic-independent-rademacher8-v1"),"closed simulation-only noise declaration")
    noisy=value["model"]=="synthetic-independent-rademacher8-v1"
    covariance=value["rgb_covariance"]
    demand(type(covariance) is list and len(covariance)==3 and all(type(r) is list and len(r)==3 for r in covariance),
           "RGB covariance shape")
    demand(all(numeric_equal(covariance[i][j],64 if noisy and i==j else 0) for i in range(3) for j in range(3))
           and numeric_equal(value["proxy_variance"],24 if noisy else 0)
           and value["units"]=="rgb16-code-squared" and value["band_transfer"]=="core-white-bandgain-v1",
           "literal covariance/proxy semantics, excluding bool")
    return 24 if noisy else 0

def merge_check(value):
    fixed={"bands":3,"gate":2,"exponent":2,"sharpen_per_octave":1.4,"select":"SoftPower",
       "admission":"HardFloor","base":"Mean","mean_coarse":0,"hull":"InputRange","hull_lambda":2,
       "hull_low_only":False,"fallback":"Mean","fallback_k":3,"fallback_power":4,"hull_from_level":1,
       "significance_scale":0}
    demand(type(value) is dict and set(value)==set(fixed),"closed fixed merge recipe")
    for k,want in fixed.items():
        if type(want) in (int,float):
            demand(type(value[k]) in (int,float) and math.isfinite(value[k])
                   and struct.pack("<f",value[k])==struct.pack("<f",want),"fixed numeric merge value:"+k)
        else:demand(type(value[k]) is type(want) and value[k]==want,"fixed merge value:"+k)

def ceiling_levels(w,h):
    out=[]
    for _ in range(4):
        out.append((w,h))
        w=(w+1)//2;h=(h+1)//2
    return out

def census(gate,mode,frames,w,h):
    demand(type(gate) is dict and gate.get("called") is True and gate.get("mode")==mode,"gate observer identity")
    if mode!="on":
        demand(gate.get("visited_levels")==0 and gate.get("levels") is None
               and type(gate.get("visited_levels")) is int and type(gate.get("allocated_rows")) is int
               and gate.get("allocated_rows")==(4 if mode=="placebo" else 0),"off/placebo does not claim observed gates")
        if mode=="placebo":
            row={"level":0,"kind":"placebo","width":0,"height":0,"sites":0,"averaged_fraction":0.0,
                 "zero_denominator":0,"positive_denominator":0}
            expected=(json.dumps([row]*4,separators=(",",":"),allow_nan=False)+"\n").encode()
            demand(gate["placebo_rows_sha256"]==digest(expected),"literal allocated gate-placebo rows")
        return {"mode":mode,"observed":False}
    demand(type(gate.get("visited_levels")) is int and type(gate.get("allocated_rows")) is int
           and type(gate.get("frames")) is int and gate.get("visited_levels")==gate.get("allocated_rows")==4 and gate.get("frames")==frames
           and type(gate.get("levels")) is list and len(gate["levels"])==4,"four actual on census levels")
    rows=[]
    for k,((width,height),row) in enumerate(zip(ceiling_levels(w,h),gate["levels"])):
        size=width*height
        demand(type(row["level"]) is int and row["level"]==k and row["kind"]==("Laplacian" if k<3 else "mean-base")
               and integer(row["width"]) and row["width"]==width and integer(row["height"]) and row["height"]==height
               and integer(row["sites"]) and row["sites"]==size,"ceil level shape")
        zero,pos=row["zero_denominator"],row["positive_denominator"]
        demand(integer(zero,0,size) and integer(pos,0,size) and zero+pos==size
               and finite(row["averaged_fraction"]) and abs(row["averaged_fraction"]-zero/size)<=2e-15,
               "full denominator partition and fraction")
        rows.append({"level":k,"width":width,"height":height,"zero":zero,"positive":pos})
    return {"mode":"on","observed":True,"levels":rows,"collective_laplacian_zero":sum(r["zero"] for r in rows[:3]),
            "collective_laplacian_positive":sum(r["positive"] for r in rows[:3]),"base_excluded":True}

def fixed_input_files(index,release):
    demand(index["schema"]=="common-tiff-dimensions-independent-fixtures-v1" and
           set(index)=={"schema","source","spec","profile","recipe","recipe_sha256","legacy","generated_files","cases"},
           "original fixed fixture index schema")
    demand(index["source"]["sha256"]==ORIGINAL_SHA and index["spec"]["sha256"]==ORIGINAL_SPEC_SHA,
           "unchanged fixture author/source authority")
    demand(len(index["generated_files"])==58 and len(index["cases"])==24,"fixed generated and case population")
    demand(same(index["profile"],release["profile"]) and release["profile"]["bytes"]==548
           and release["profile"]["sha256"]==PROFILE_SHA,"held independent profile")
    read(release["profile"],"source",548)
    names={}
    for ref in index["generated_files"]:
        p=ref_shape(ref)
        demand(p.parent==HERE/"prepare-1/fixtures" and p.name not in names,"unique actual generated-file role")
        names[p.name]=ref
    expected={f"case-{i:02}.json" for i in range(24)}|{"recipe.json","last-geometry.tiff","last-file-hash.tiff"}
    groups=(("mean-two",2,64,64,"constant"),("mean-five",5,129,97,"constant"),("mean-eight",8,512,512,"constant"),
            ("odd-address",5,129,97,"address"),("odd-offset",5,129,97,"offset"),("odd-noisy",5,129,97,"noise"),
            ("count-nine-extra",1,512,512,"ninth"))
    expected|={f"{name}-{i}.tiff" for name,n,_,_,_ in groups for i in range(n)}
    demand(set(names)==expected and len(expected)==58,"exact generated file names")
    recipe_raw=read(index["recipe"],cap=64*KIB)
    demand(same(index["recipe"],names["recipe.json"]) and digest(recipe_raw.rstrip(b"\n"))==index["recipe_sha256"],
           "literal recipe document binding")
    input_rows=[]
    for name,n,w,h,kind in groups:
        for i in range(n):
            ref=names[f"{name}-{i}.tiff"]
            image=tiff_decode(ref)
            demand((image["width"],image["height"])==(w,h),"fixed new input geometry")
            image_literal(image,kind,i)
            model="synthetic-independent-rademacher8-v1" if kind=="noise" else "synthetic-noiseless-v1"
            expected_prov={"schema":"common-tiff-stack-input-v1","id":f"{name}-{i}",
               "fixture_sha256":index["recipe_sha256"],"color_space":"linear-prophoto-d50",
               "noise_model":model,"geometry":"identity-common-rgb-pixels"}
            demand(object_json(image["description"])==expected_prov,"literal input identity/provenance")
            demand(image["strip_count"]==(h+(17,31,48,64,97,23,41,73)[i]-1)//(17,31,48,64,97,23,41,73)[i],
                   "actual deliberately varied input strip geometry")
            input_rows.append({"file":ref,"width":w,"height":h,"strip_count":image["strip_count"],
                               "pixel_sha256":image["pixel_sha256"],"literal_kind":kind,"row_address_sha256":image["row_address_sha256"]})
            tick()
    for name,w,kind in (("last-geometry",128,"bad-geometry"),("last-file-hash",129,"bad-hash")):
        image=tiff_decode(names[name+".tiff"])
        demand((image["width"],image["height"])==(w,97),"independent actual late failure geometry")
        image_literal(image,kind,4)
        prov=object_json(image["description"])
        demand(prov=={"schema":"common-tiff-stack-input-v1","id":"mean-five-4","fixture_sha256":index["recipe_sha256"],
                      "color_space":"linear-prophoto-d50","noise_model":"synthetic-noiseless-v1",
                      "geometry":"identity-common-rgb-pixels"},"late failure TIFF provenance")
        input_rows.append({"file":names[name+".tiff"],"width":w,"height":97,"literal_kind":kind,
                           "pixel_sha256":image["pixel_sha256"],"row_address_sha256":image["row_address_sha256"]})
    legacy=release["legacy"]
    demand(set(legacy)=={"index","report","manifest","output"} and all(same(legacy[k],index["legacy"][k]) for k in legacy),
           "exact legacy evidence roles")
    old_index=parsed(legacy["index"],cap=256*KIB)
    old_report=parsed(legacy["report"],cap=64*KIB)
    old_plan=parsed(legacy["manifest"],cap=64*KIB)
    demand(old_report["schema"]=="common-tiff-stack-result-v1" and old_report["status"]=="COMPLETE"
           and old_report["subject_complete"] is True and same(old_report["manifest"],legacy["manifest"])
           and same(old_report["output"],legacy["output"]) and same(old_index["cases"][0]["manifest"],legacy["manifest"]),
           "held actual v1 report and manifest")
    demand(old_plan["schema"]=="common-tiff-stack-v1" and len(old_plan["inputs"])==3
           and old_plan["grid"]=={"width":128,"height":96,"channels":"RGB","coordinates":"identity-common-rgb-pixels"},
           "one fixed legacy triple")
    for entry in old_plan["inputs"]:
        image=tiff_decode(entry["tiff"],version=1)
        demand((image["width"],image["height"])==(128,96) and image["pixel_sha256"]==entry["pixel_sha256"]
               and object_json(image["description"])==entry["provenance"],"actual legacy input association")
        input_rows.append({"file":entry["tiff"],"width":128,"height":96,"literal_kind":"held-v1-input",
                           "pixel_sha256":image["pixel_sha256"],"row_address_sha256":image["row_address_sha256"]})
    demand(len(input_rows)==36 and len({str(ref_shape(r["file"])).casefold() for r in input_rows})==36,
           "exact unique33 new plus3 legacy input files")
    legacy_image=tiff_decode(legacy["output"],output=True,version=1)
    demand(legacy["output"]["bytes"]==74807 and legacy["output"]["sha256"]==LEGACY_SHA,"exact archived whole TIFF")
    STATE["input_files"]=input_rows
    return names,old_plan,legacy_image


def manifest_contributors(i,plan,names,legacy_inputs):
    """Independent whole population, not just producer prefix against itself."""
    def entry(filename):
        ref=names[filename]
        image=IMAGES[str(ref_shape(ref)).casefold()]
        prov=object_json(image["description"])
        return {"id":prov["id"],"tiff":ref,"pixel_sha256":image["pixel_sha256"],"provenance":prov}
    group="mean-two" if i==0 else "mean-eight" if i in (2,11) else "odd-address" if i in (3,18) else "odd-offset" if i==4 else "odd-noisy" if i in (5,6,7,21) else "mean-five"
    count=2 if group=="mean-two" else 8 if group=="mean-eight" else 5
    expected=[entry(f"{group}-{j}.tiff") for j in range(count)]
    if i in (8,17):expected=list(legacy_inputs[:3 if i==8 else 2])
    elif i==9:expected=[]
    elif i==10:expected=expected[:1]
    elif i==11:expected.append(entry("count-nine-extra-0.tiff"))
    elif i==18:expected=expected[:3]
    elif i==19:expected[1]=expected[0]
    elif i==22:expected[4]=entry("last-geometry.tiff")
    elif i==23:
        old=expected[4]
        expected[4]={**old,"tiff":{**old["tiff"],"path":names["last-file-hash.tiff"]["path"]}}
    demand(type(plan["inputs"]) is list and len(plan["inputs"])==len(expected),"independent full manifest contributor count")
    for got,want in zip(plan["inputs"],expected):
        demand(type(got) is dict and set(got)==set(want) and got["id"]==want["id"]
               and same(got["tiff"],want["tiff"]) and got["pixel_sha256"]==want["pixel_sha256"]
               and got["provenance"]==want["provenance"],"independently fixed contributor order/set/full binding")
    w,h=(64,64) if i==0 else (512,512) if i in (2,11) else (128,96) if i in (8,17) else (129,97)
    if i in (12,13,16):w={12:63,13:513,16:4294967296}[i]
    if i in (14,15):h={14:63,15:513}[i]
    grid=plan["grid"]
    demand(set(grid)=={"width","height","channels","coordinates"} and type(grid["width"]) is int
           and type(grid["height"]) is int and grid=={"width":w,"height":h,"channels":"RGB","coordinates":"identity-common-rgb-pixels"},
           "independently fixed complete manifest grid")
    demand(plan["output"]=={"path":str(HERE/"render-1"/f"case-{i:02}"/"output.tiff"),
            "space":"linear-prophoto-d50","sample_format":"RGB16","quantization":"finite-clamp-round-half-away-v1"},
           "independently fixed output consumer contract")

def expected_manifest_fault(i,plan):
    demand(type(plan) is dict and set(plan)=={"schema","grid","color","noise","merge","inputs","output"},"closed actual manifest")
    expected_version=1 if i in (8,17,18) else 2
    demand(plan["schema"]==f"common-tiff-stack-v{expected_version}","literal manifest version")
    if i in (9,10,11):demand(len(plan["inputs"])=={9:0,10:1,11:9}[i],"actual count refusal operand")
    if i in (12,13,14,15,16):
        axis,value={12:("width",63),13:("width",513),14:("height",63),15:("height",513),16:("width",4294967296)}[i]
        demand(type(plan["grid"][axis]) is int and plan["grid"][axis]==value,"actual grid refusal operand")
    if i==17:demand(len(plan["inputs"])==2,"actual legacy count refusal operand")
    if i==18:demand(plan["grid"]["width"]==129 and plan["grid"]["height"]==97,"actual legacy grid refusal operand")
    if i==19:demand(len(plan["inputs"])==5 and plan["inputs"][0]==plan["inputs"][1],"actual duplicated manifest entry")
    if i==20:demand(plan["color"]["icc"]["sha256"]!=PROFILE_SHA,"actual rejected profile declaration")
    if i==21:demand(numeric_equal(plan["noise"]["proxy_variance"],1),"actual rejected proxy variance operand")
    return expected_version

def inspect_case(i,index,names,stage,release,old_image,legacy_inputs):
    row=index["cases"][i]
    demand(row["ordinal"]==i and row["id"]==IDS[i] and row["observer"]==MODES[i]
           and row["expected_exit_code"]==int(i>=9) and row["expected_folded_frames"]==FOLDS[i],"fixed case identity")
    plan=parsed(row["manifest"],cap=64*KIB)
    demand(same(row["manifest"],names[f"case-{i:02}.json"]),"actual fixed manifest member")
    version=expected_manifest_fault(i,plan)
    manifest_contributors(i,plan,names,legacy_inputs)
    directory=HERE/"render-1"/f"case-{i:02}"
    demand(location(row["report_path"])==directory/"report.json"
           and location(row["output_path"])==directory/"output.tiff","fixed product publication paths")
    command=[str(ref_shape(release["executable"])) if x=="ACTUAL_BINARY_PATH" else x for x in row["command"]]
    child,log,process=stage["children"][i]
    demand(child["command"]==command,"fixed literal product invocation")
    captures=stage["parent"].get("artifacts",{}).get("cases",[])
    demand(i<len(captures),"actual retained case capture")
    capture=captures[i]
    demand(capture["ordinal"]==i and capture["id"]==IDS[i]
           and capture["expected_exit_code"]==int(i>=9) and capture["expected_folded_frames"]==FOLDS[i],
           "actual case capture association")
    artifacts=capture["artifacts"]
    expected={"report.json","report.incomplete.json"}|{f"report.frame-{j}.json" for j in range(FOLDS[i])}
    if i<9:expected.add("output.tiff")
    demand(set(artifacts)==expected,"exact case artifact population")
    for name,ref in artifacts.items():at(ref,directory/name)
    raw=read(artifacts["report.json"],cap=192*KIB)
    demand(log==raw,"actual process stdout exactly final report")
    value=object_json(raw)
    early=9<=i<=21
    demand(value["schema"]==f"common-tiff-stack-result-v{1 if early else version}"
           and value["command"]==command and value["observer_mode"]==MODES[i],"actual report identity")
    demand(same(value["manifest"],row["manifest"]) and same(value["incomplete"],artifacts["report.incomplete.json"]),
           "actual manifest and initial publication associations")
    initial=parsed(artifacts["report.incomplete.json"],cap=4096)
    demand(initial["schema"]=="common-tiff-stack-incomplete-v1" and initial["status"]=="INITIAL_INCOMPLETE"
           and initial["subject_complete"] is False and location(initial["manifest_path"])==ref_shape(row["manifest"])
           and initial["manifest_sha256"]==row["manifest"]["sha256"] and location(initial["report"])==directory/"report.json",
           "actual request-level initial witness")
    folds=value["consumed"]
    demand(type(folds) is list and len(folds)==FOLDS[i] and type(value["frame_receipts"]) is list
           and len(value["frame_receipts"])==FOLDS[i],"exact full observed fold prefix")
    demand(len({r["id"] for r in folds})==len(folds),"unique actual contributor IDs")
    observation=[]
    gain=None
    if early:
        demand(value["binary"] is None and all(k not in value for k in ("profile","plan","runtime")),
               "early refusal stays before binary/runtime/profile")
    else:
        demand(same(value["binary"],release["executable"]) and same(value["profile"],index["profile"]),
               "actual product binary/profile")
        got=value["plan"]
        demand(set(got)==set(plan) and all(got[k]==plan[k] for k in ("schema","grid","color","inputs","output")),
               "same manifest with typed numeric plan")
        merge_check(got["merge"])
        variance=noise_check(got["noise"])
        demand(variance==noise_check(plan["noise"]),"same supplied noise semantics")
        w,h=plan["grid"]["width"],plan["grid"]["height"]
        demand(integer(w,64,512) and integer(h,64,512) and plan["grid"]["channels"]=="RGB"
               and plan["grid"]["coordinates"]=="identity-common-rgb-pixels","admitted consumer geometry")
        runtime=value["runtime"]
        gain=runtime["actual_core_white_band_gain"]
        demand(type(gain) is list and len(gain)==4 and all(finite(x) and x>0 for x in gain)
               and runtime["passed_frame_beta"]==gain[:3] and runtime["rayon_threads"]==2
               and runtime["proxy"]=="(R+2G+B)/4 in RGB16 code values"
               and runtime["variance_units"]=="RGB16-code squared","explicit actual white-band inputs")
        for j,fold in enumerate(folds):
            contributor=plan["inputs"][j]
            demand(type(fold["ordinal"]) is int and fold["ordinal"]==j and fold["id"]==contributor["id"]
                   and type(fold["merge_frames"]) is int and fold["merge_frames"]==j+1,"one actual ordered fold per contributor")
            image=tiff_decode(contributor["tiff"],version=version)
            demand((image["width"],image["height"])==(w,h) and image["pixel_sha256"]==contributor["pixel_sha256"]
                   and object_json(image["description"])==contributor["provenance"],"independent consumed input bytes")
            demand(same(fold["file"],contributor["tiff"]) and fold["width"]==w and fold["height"]==h
                   and fold["strip_count"]==image["strip_count"] and fold["pixel_sha256"]==image["pixel_sha256"]
                   and fold["icc_sha256"]==PROFILE_SHA and fold["provenance"]==contributor["provenance"],
                   "full consumed file and pixel provenance")
            demand(fold["merge_sha256_before"]==fold["merge_sha256_after"]==image["pixel_sha256"],
                   "unchanged before/after canonical u16 evidence")
            proxy=proxy_digest(image)
            variance_hash=digest(struct.pack("<f",variance)*(w*h))
            demand(fold["proxy_f32_sha256_before"]==fold["proxy_f32_sha256_after"]==proxy
                   and fold["variance_f32_sha256_before"]==fold["variance_f32_sha256_after"]==variance_hash
                   and numeric_equal(fold["variance_value_before"],variance) and numeric_equal(fold["variance_value_after"],variance)
                   and integer(fold["variance_sites"]) and fold["variance_sites"]==w*h
                   and fold["passed_frame_beta"]==gain[:3],"literal supplied proxy/variance array hashes")
            frame_ref=artifacts[f"report.frame-{j}.json"]
            demand(same(frame_ref,value["frame_receipts"][j]),"immutable frame receipt identity")
            frame=parsed(frame_ref,cap=16*KIB)
            demand(set(frame)=={"schema","manifest","fold"} and frame["schema"]==f"common-tiff-stack-frame-v{version}"
                   and same(frame["manifest"],row["manifest"]) and frame["fold"]==fold,"immutable full fold body")
            observation.append(census(fold["gate"],MODES[i],j+1,w,h))
            tick()
    result={"ordinal":i,"id":IDS[i],"status":"SAVED_BYTES_CHECKED","passed":False,"folded_frames":len(folds),
            "process":process,"report":artifacts["report.json"],"frame_receipts":value["frame_receipts"],
            "gate_observations":observation,"band_gains":gain}
    if i>=9:
        error=value.get("error")
        reason=(type(error) is str and error.startswith("manifest JSON:") and "4294967296" in error) if i==16 else error==REASONS[i]
        demand(value["status"]=="REFUSED" and value["subject_complete"] is False and value["output"] is None
               and value["stage"]==("manifest" if early else "input-4") and reason,"actual error-specific semantic refusal")
        if i>=22:
            actual=tiff_decode(names[("last-geometry" if i==22 else "last-file-hash")+".tiff"])
            entry=plan["inputs"][4]
            demand(location(entry["tiff"]["path"])==ref_shape(actual["ref"]),"actual failed input address")
            if i==22:
                demand(same(entry["tiff"],actual["ref"]) and actual["width"]==128 and plan["grid"]["width"]==129,
                       "powered wrong fifth geometry with correct hash")
            else:
                demand(entry["tiff"]["bytes"]==actual["ref"]["bytes"]
                       and entry["tiff"]["sha256"]!=actual["file_sha256"]
                       and entry["pixel_sha256"]!=actual["pixel_sha256"]
                       and (actual["width"],actual["height"])==(129,97),"actual same-shape changed fifth bytes")
        result.update(passed=process["admissible"],semantic_refusal=error,
                      error_sha256=digest(error.encode("utf-8")),original_subject_complete=False)
        return result,None,value
    demand(value["status"]=="COMPLETE" and value["subject_complete"] is True and value["stage"]=="complete"
           and "error" not in value and value["inputs_rechecked"] is True and same(value["output"],artifacts["output.tiff"]),
           "completed actual product publication")
    image=tiff_decode(artifacts["output.tiff"],output=True,version=version)
    demand((image["width"],image["height"])==(w,h),"actual output consumer grid")
    enc=value["encoding"]
    demand(enc["width"]==w and enc["height"]==h and enc["sample_format"]=="RGB16"
           and enc["color_space"]=="linear-prophoto-d50" and enc["icc_sha256"]==PROFILE_SHA
           and enc["pixel_sha256"]==image["pixel_sha256"] and enc["quantization"]=="finite-clamp-round-half-away-v1"
           and enc["clipped_low"]==[0,0,0] and enc["clipped_high"]==[0,0,0],"actual encoded RGB and finite/no-clip witness")
    demand(value["final_gate"]==folds[-1]["gate"],"final census equals last immutable fold")
    observer=value["observer"]
    ob=observer["observation"]
    size=3*w*h
    pre=enc["prequantization_f32_sha256"]
    demand(hash_text(pre) and observer["output_f32_sha256_before"]==observer["output_f32_sha256_after"]==pre,
           "retained before/after prequantization equality witness")
    demand(ob["called"] is True and ob["mode"]==MODES[i] and ob["visited_samples"]==(size if MODES[i]=="on" else 0)
           and ob["allocated_samples"]==(0 if MODES[i]=="off" else size),"actual output observer shape")
    if MODES[i]=="on":demand(ob["plane_major_f32_sha256"]==pre,"on observer retained hash")
    if MODES[i]=="placebo":demand(ob["placebo_f32_sha256"]==digest(b"\0"*(size*4)),"literal zero-allocation output placebo hash")
    if i<3:
        rgb=MEANS[FOLDS[i]]
        low=[65535]*3;high=[0]*3
        for triple in struct.iter_unpack("<HHH",image["payload"]):
            for c,v in enumerate(triple):low[c]=min(low[c],v);high[c]=max(high[c],v)
        result["constant"]={"expected":rgb,"actual_min":low,"actual_max":high,
                            "passed":low==high==list(rgb),"all_codes_compared":3*w*h}
        result["numerical_passed"]=result["constant"]["passed"]
    elif i in (3,4):
        partitions=partition_errors(image,"address" if i==3 else "offset")
        result["partitions"]=partitions
        result["numerical_passed"]=partitions["passed"]
    elif i==6:
        last=observation[-1]
        result["numerical_passed"]=last["collective_laplacian_zero"]>0 and last["collective_laplacian_positive"]>0
    elif i==8:
        demand(image["ref"]["bytes"]==old_image["ref"]["bytes"] and image["file_sha256"]==old_image["file_sha256"]
               and read(image["ref"],"output",128*KIB)==read(old_image["ref"],"output",128*KIB),"actual old v1 whole-output identity")
    result.update(passed=process["admissible"] and result.get("numerical_passed",True),output=image["ref"],pixel_sha256=image["pixel_sha256"],
                  row_address_sha256=image["row_address_sha256"],ifd_tag_order=image["ifd_tag_order"],
                  prequantization_scope="Retained f32 hash equality, not independent reconstruction of an unsaved f32 buffer.")
    return result,image,value

def mean_family():
    """Independently form the fixed integer sums; no image mutations are run."""
    rows=[]
    for n in (2,5,8):
        colors=[constant_color(i) for i in range(n)]
        sums=[sum(c[k] for c in colors) for k in range(3)]
        rounding=lambda s,count:tuple((2*v+count)//(2*count) for v in s)
        demand(rounding(sums,n)==MEANS[n],"independent literal full mean")
        for i in range(n):
            rows.append((f"n{n}-omit-{i}",n,rounding([sums[k]-colors[i][k] for k in range(3)],n-1)))
            rows.append((f"n{n}-append-duplicate-{i}",n,rounding([sums[k]+colors[i][k] for k in range(3)],n+1)))
        for missing in range(n):
            for duplicate in range(n):
                if missing!=duplicate:
                    rows.append((f"n{n}-replace-{missing}-with-{duplicate}",n,
                                 rounding([sums[k]-colors[missing][k]+colors[duplicate][k] for k in range(3)],n)))
        rows.append((f"n{n}-mean-restored",n,MEANS[n]))
    return rows

OTHER_CONTROLS=(
 ("omitted-fold","complete contributor prefix"),("duplicated-fold","unique ordered contributors"),
 ("wrong-fold-counter","actual single fold per contributor"),("contributors-restored",None),
 ("wrong-level-zero-width","actual level geometry"),("floor-instead-of-ceil","actual level geometry"),("levels-restored",None),
 ("dropped-last-column","literal identical-frame output: geometry"),
 ("replaced-last-row","literal identical-frame output: literal RGB codes"),
 ("wrong-final-corner","literal identical-frame output: literal RGB codes"),
 ("red-blue-permutation","literal identical-frame output: literal RGB codes"),
 ("one-pixel-address-shift","literal identical-frame output: literal RGB codes"),("address-restored",None),
 ("changed-observer-pixel","observer whole TIFF equality"),("observer-restored",None),
 ("wrong-actual-icc","actual admitted output profile"),("profile-restored",None),
 ("variance-one","exact injected noise declaration"),("boolean-zero-covariance","exact injected noise declaration"),("noise-restored",None),
 ("offset-plus-eight","offset literal error within one code"),("offset-column","offset literal error within one code"),
 ("offset-corner","offset literal error within one code"),("offset-restored",None))

def control_blueprint():
    first=[(ident,None if ident.endswith("-restored") else "constant literal RGB codes",n,rgb)
           for ident,n,rgb in mean_family()]
    result=first+[(ident,reason,None,None) for ident,reason in OTHER_CONTROLS]
    demand(len(result)==135 and len({x[0] for x in result})==135
           and sum(reason is None for _,reason,_,_ in result)==10,"exact135 original control population")
    return result

def saved_controls(checker,images):
    actual=checker.get("independent_controls",[])
    demand(type(actual) is list and len(actual)<=135,"bounded saved original control prefix")
    blueprint=control_blueprint()
    index={}
    for row in actual:
        demand(type(row) is dict and type(row.get("id")) is str and row["id"] not in index,"unique saved control IDs")
        index[row["id"]]=row
    demand(set(index)<={x[0] for x in blueprint},"no extra original control ID")
    rows=[]
    for ordinal,(ident,reason,n,rgb) in enumerate(blueprint):
        original=index.get(ident)
        row={"ordinal":ordinal,"id":ident,"expected_restoration":reason is None,
             "original":original,"passed":False}
        if original is None:
            row["status"]="NO_SAVED_ORIGINAL_ROW"
        else:
            good=(actual[ordinal]["id"]==ident if ordinal<len(actual) else False) and original.get("passed") is True
            if reason is None:good=good and original.get("restored") is True
            else:good=good and original.get("rejected") is True and original.get("reason")==reason
            if n is not None:
                image=images.get({2:0,5:1,8:2}[n])
                if image is None:
                    good=False
                    row["mean_rechoice"]="corresponding saved image unavailable"
                else:
                    # Membership in the constant image can be decided by its complete byte buffer.
                    equal=image["payload"]==struct.pack("<HHH",*rgb)*image["width"]*image["height"]
                    good=good and (equal if reason is None else not equal)
                    row.update(independent_integer_expected=rgb,decoded_full_image_matches=equal,
                               mean_rechoice="Actual saved constant TIFF compared to the independently formed integer competitor; no product or mutant rerun.")
            else:
                row["mutation_scope"]="Original source-bound report of a temporary changed operand; altered buffers were not saved and are not independently observed."
            row.update(status="SAVED_CONTROL_DISPOSITION_CHECKED",passed=good)
        rows.append(row)
    return rows

def observer_comparison(images,receipts):
    demand(all(i in images for i in (5,6,7)),"all actual observer TIFFs available")
    off,on,placebo=(images[i] for i in (5,6,7))
    whole=len({v["file_sha256"] for v in (off,on,placebo)})==1
    payload=len({v["pixel_sha256"] for v in (off,on,placebo)})==1
    parts=[{"id":"x-less-than-65","sites":0,"channels_different":[0,0,0]},
           {"id":"x-at-least-65","sites":0,"channels_different":[0,0,0]}]
    for y in range(97):
        for x in range(129):
            row=parts[int(x>=65)]
            row["sites"]+=1
            triples=[pixel(im,x,y) for im in (off,on,placebo)]
            for c in range(3):row["channels_different"][c]+=int(len({t[c] for t in triples})!=1)
        tick()
    demand([p["sites"] for p in parts]==[6305,6208],"exhaustive noisy halves")
    for i in (5,6,7):
        demand(receipts[i]["runtime"]["actual_core_white_band_gain"]==receipts[5]["runtime"]["actual_core_white_band_gain"],
               "same-grid injected white gains across observer arms")
    return {"whole_tiff_equal":whole,"payload_equal":payload,"partitions":parts,
            "passed":whole and payload and all(not any(p["channels_different"]) for p in parts),
            "scope":"Complete saved TIFF observer nonperturbation. Spatial partitions are correspondence checks, not per-repeat variance or physical noise calibration."}

RECOVERY_IDS=("ordinary-positive","verbatim-to-ordinary","ordinary-to-verbatim","different-manifest-same-bytes",
 "different-output-same-bytes","wrong-extent","wrong-digest","boolean-extent","float-extent","zero-extent",
 "extra-ref-key","nonstring-path","device-path","unc-path","verbatim-unc","alternate-stream","nul-path",
 "dot-components","trailing-components","empty-component","outside-repository","drive-relative","malformed-verbatim-drive",
 "restored-associations","saved-negative-parent-positive","historical-parent-complete","historical-failure-changed",
 "child-nonzero","child-incomplete-job","child-command-changed","child-index-changed","restored-saved-parent",
 "admission-positive","admission-status-changed","admission-old-parent-complete","admission-index-changed",
 "producer-map-changed","execution-map-changed","archive-and-proof-associations","restored-admission")

def recovery_controls(bundle,mapping):
    demand(type(bundle) is dict and set(bundle)=={"result","outer","stdout","stderr","exit"},"five recovery-control roles")
    raw=read(bundle["result"],cap=128*KIB)
    demand(raw==read(bundle["stdout"],cap=128*KIB) and read(bundle["stderr"],cap=16*KIB,empty=True)==b""
           and read(bundle["exit"],cap=1024)==b"0\n","same actual recovery control output and exit")
    v=object_json(raw)
    o=parsed(bundle["outer"],cap=64*KIB)
    demand(v["schema"]=="common-tiff-dimensions-recovery-controls-v1" and v["status"]=="PASS_FIXED_RECOVERY_METADATA_CONTROLS"
           and v["controls_complete"] is True and v["groups"]==v["completed_groups"]==40
           and [r["id"] for r in v["rows"]]==list(RECOVERY_IDS) and all(r["passed"] is True for r in v["rows"]),
           "all fixed saved metadata control groups")
    source={"path":"experiments/common-tiff-dimensions/recovery-controls.py",
            **mapping["experiments/common-tiff-dimensions/recovery-controls.py"]}
    command=[sys.executable,"-I","-S","-B",str(HERE/"recovery-controls.py"),
             "--source-sha256",source["sha256"],"--output",str(HERE/"work/recovery-controls-1")]
    demand(same(v["source"],source) and v["invocation"]==command and o["command"]==command
           and same(o["source"],source) and o["schema"]=="common-tiff-dimensions-recovery-controls-external-v1",
           "actual control source and invocation")
    for k in ("stdout","stderr","exit"):demand(same(o[k],bundle[k],empty=k=="stderr"),"actual control outer raw refs")
    demand(type(o["exit_code"]) is int and o["exit_code"]==0 and o["timeout_terminated"] is False
           and o["stdout_bytes"]==len(raw) and o["stderr_bytes"]==0
           and finite(o["elapsed_wall_seconds"]) and o["elapsed_wall_seconds"]<=10,"actual control child interval")
    c=o["capture_accounting"]
    demand(set(c)=={"parent_cpu_sample","whole_wall_sample","publication_allowance","reserved","admitted","error","scope"}
           and c["admitted"] is True and c["error"] is None
           and c["publication_allowance"]=={"cpu_seconds":1,"wall_seconds":2}
           and c["reserved"]=={"cpu_seconds":5,"overhead_wall_seconds":10,"whole_wall_seconds":20}
           and finite(c["parent_cpu_sample"]) and finite(c["whole_wall_sample"])
           and c["parent_cpu_sample"]+1<=5 and c["whole_wall_sample"]+2<=20
           and 0<=c["whole_wall_sample"]-o["elapsed_wall_seconds"]<=8,"separate capture sample plus allowance")
    return {"bundle":bundle,"groups":40,"passed":True,
            "scope":"Actual saved fixed metadata controls, not rerun by this reader; independent review publication/readback is separately retained."}

def recovered_authority(release,stages,producer,execution,index):
    prepare=stages["prepare"]
    p=prepare["parent"]
    demand(p["status"]=="REFUSED" and p["artifacts"]=={} and type(p["error"]) is dict
           and p["error"].get("sha256")=="c7ca5efa219aefb6d3517658d1d8a1539d831b22187e180ce4bc31c7ff21518b",
           "unchanged actual preparation failure")
    child,raw,summary=prepare["children"][0]
    demand(summary["admissible"],"successful actual generator child despite failed parent")
    advert=object_json(raw)
    demand(advert["schema"]=="common-tiff-dimensions-independent-preparation-v1"
           and advert["status"]=="PREPARED_UNRUN_FIXTURES" and advert["cases"]==24
           and advert["generated_files"]==59 and advert["file_bytes"]==16025258
           and same(advert["index"],release["fixtures"]),"actual completed saved generator publication")
    r=stages["recovery"]["parent"]
    admission_ref=r["artifacts"]["admission"]
    at(admission_ref,HERE/"recovery-1/admission.json")
    admission=parsed(admission_ref,cap=128*KIB)
    demand(admission["schema"]=="common-tiff-dimensions-saved-fixture-admission-v1"
           and admission["status"]=="SAVED_FIXTURES_ADMITTED" and admission["old_prepare_status"]=="REFUSED"
           and admission["subject_complete"] is False,"new admission does not rewrite original failure")
    demand(same(admission["producer_freeze"],release["producer_freeze"])
           and admission["producer_source_map_sha256"]==digest(encode(producer))
           and admission["execution_source_map_sha256"]==digest(encode(execution))
           and admission["compiled_source_closure"]==COMPILED,"admission frozen source associations")
    for key,stage in (("build","build"),("failed_prepare","prepare")):
        demand(set(admission[key])==set(release["stages"][stage])
               and all(same(admission[key][role],release["stages"][stage][role],empty=role=="stderr")
                       for role in admission[key]),"admission historical bundle association")
    demand(same(admission["generator_child"],p["children"][0]) and same(admission["generator_stdout"],child["log"])
           and same(admission["index"],release["fixtures"]),"admission actual generator/index association")
    files=[release["fixtures"],*index["generated_files"]]
    demand(type(admission["files"]) is list and len(admission["files"])==len(files)==59
           and all(same(a,b) for a,b in zip(admission["files"],files))
           and admission["file_bytes"]==sum(r["bytes"] for r in files)==16025258,"complete fixed59 saved file bindings")
    proof=admission["fixture_read_proof"]
    demand(set(proof)=={"scope","replaced_calls","original_ast_sha256","reverse_ast_sha256","visits"}
           and type(proof["replaced_calls"]) is int and proof["replaced_calls"]==2
           and proof["original_ast_sha256"]==proof["reverse_ast_sha256"]==FIXTURE_AST_SHA
           and type(proof["visits"]) is list and len(proof["visits"])==2,"exact source-bound two-callsite proof")
    old_report=parsed(release["legacy"]["report"],cap=64*KIB)
    for visit,role in zip(proof["visits"],("manifest","output")):
        demand(set(visit)=={"left","right","matched"} and visit["matched"] is True
               and same(visit["left"],old_report[role]) and same(visit["right"],release["legacy"][role]),
               "ordered manifest/output proof operands")
    controls=recovery_controls(admission["controls"],execution)
    STATE["recovery"]={"admission":admission_ref,"original_prepare_status":"REFUSED","generator_child_exit":0,
        "files":59,"actual_control_evidence":controls,"proof":proof,"subject_complete":False}
    STATE["original_failures"].append({"name":"prepare-1","bundle":release["stages"]["prepare"],"status":"REFUSED",
         "error":p["error"],"generator_child_successful":True,
         "scope":"Exact original parent failure retained; recovery is a separate authenticated saved-fixture admission."})

def root_capture_records(release,stages):
    demand(type(release["root_captures"]) is dict and set(release["root_captures"])=={"recovery","render","verify"},
           "three separate complete root capture records")
    rows=[]
    for name,ref in release["root_captures"].items():
        at(ref,HERE/f"work/{name}-recovery-capture-root-1.json")
        value=parsed(ref,cap=16*KIB)
        demand(set(value)=={"schema","stage","source_commit","release_commit","release_sha256","command",
                           "exit_code","whole_wrapper_wall_seconds","scope"}
               and value["schema"]=="dimensions-recovery-capture-root-v1" and value["stage"]==name,
               "closed actual root capture record")
        stage=stages[name]
        expected=[sys.executable,"-I","-S","-B","experiments/common-tiff-dimensions/capture-recovery-stage.py",name,
                  "--release-sha256",stage["parent"]["release"]["sha256"]]
        demand(value["command"]==expected and value["release_sha256"]==stage["parent"]["release"]["sha256"]
               and type(value["exit_code"]) is int and value["exit_code"]==stage["outer"]["exit_code"],
               "root actual capture command/exit/release")
        demand(type(value["source_commit"]) is str and re.fullmatch("[0-9a-f]{8,40}",value["source_commit"])
               and type(value["release_commit"]) is str and re.fullmatch("[0-9a-f]{8,40}",value["release_commit"]),
               "recorded immutable source/release commit names")
        demand(finite(value["whole_wrapper_wall_seconds"])
               and value["whole_wrapper_wall_seconds"]>=stage["outer"]["elapsed_wall_seconds"],
               "root full capture interval contains the runner interval")
        rows.append({"file":ref,**value,
          "interpretation":"Full direct capture-wrapper interval through immediate exit capture; excludes subsequent root-record publication. Commit names are recorded associations, not a Git-history execution by this reader."})
    demand(len({r["source_commit"] for r in rows})==1,"same committed capture source across three stages")
    STATE["root_capture_records"]=rows

def preserved_build_failure(bundle,base):
    caps={"result":256*KIB,"tail":8192,"outer":65536,"stdout":8192,"stderr":32768,"exit":1024}
    demand(type(bundle) is dict and set(bundle)==set(caps),"preserved build1 six-role history")
    raw={k:read(bundle[k],cap=n,empty=k=="stderr") for k,n in caps.items()}
    p,t,o,advert=(object_json(raw[k]) for k in ("result","tail","outer","stdout"))
    at(bundle["result"],HERE/"build-1/result.json")
    demand(p["status"]=="REFUSED" and p["stage"]=="build" and p["error"] is not None
           and raw["exit"]==b"1\n" and type(o["exit_code"]) is int and o["exit_code"]==1,
           "original build1 remains refused")
    for k in ("stdout","stderr","exit"):demand(same(o[k],bundle[k],empty=k=="stderr"),"historical build1 raw binding")
    demand(raw["stdout"]==encode(advert) and advert["status"]==p["status"]
           and same(advert["result"],bundle["result"]) and same(advert["tail"],bundle["tail"])
           and same(t["result"],bundle["result"]),"historical build1 publication identity")
    original=parsed(p["release"],cap=MIB)
    demand(original["source_bindings"]==base and p["invocation"]==o["command"]
           and p["invocation"]==[p["release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in original["command"]],
           "original build1 released source and command")
    records=[]
    for ref in p.get("children",[]):
        c=parsed(ref,cap=32*KIB)
        read(c["log"],cap=16*MIB)
        records.append({"file":ref,"log":c["log"],"exit_code":c.get("exit_code"),"error":c.get("error"),
                        "terminal_job_accounting":c.get("terminal_job_accounting"),"job_accounting":c.get("job_accounting"),
                        "termination":c.get("termination"),"compile_cleanup":c.get("compile_cleanup")})
    STATE["original_failures"].append({"name":"build-1","bundle":bundle,"status":"REFUSED","error":p["error"],
        "children":records,"tail":t,"outer":o,"scope":"Source/path-census failure retained; the missing resolved-spelling operand was not saved, so its physical cause remains unknown. No failed build cost is refunded."})

def link_stages(release,stages):
    for name in ("build","prepare","recovery","render","verify"):
        stage=stages[name]
        r=stage["release"]
        demand(stage["parent"]["compiled_source_closure"]==COMPILED,"same compiled source closure on every stage")
        if name=="build":
            demand(stage["parent"]["compiled_source_closure"]==COMPILED,"build compiled source closure")
            a=stage["parent"]["artifacts"]
            demand(same(a["executable"],release["executable"]),"actual copied executable binding")
            raw=stage["children"][0][1]
            demand(b"Compiling strehl-cli" in raw,"actual compilation evidence")
            messages=[]
            for line in raw.splitlines():
                if line.startswith(b"{"):
                    try:messages.append(object_json(line))
                    except (ValueError,UnicodeError):pass
            finished=[x for x in messages if x.get("reason")=="build-finished"]
            binaries=[x for x in messages if x.get("reason")=="compiler-artifact"
                      and x.get("target",{}).get("name")=="strehl-common-input" and x.get("executable")]
            demand(len(finished)==1 and finished[0].get("success") is True and len(binaries)==1
                   and binaries[0].get("fresh") is False and binaries[0].get("profile",{}).get("test") is False
                   and binaries[0].get("target",{}).get("kind")==["bin"]
                   and binaries[0].get("features")==[],"fresh default binary rather than an unrelated artifact")
            demand(location(binaries[0]["target"]["src_path"])==ROOT/"crates/strehl-cli/src/bin/strehl-common-input.rs"
                   and location(binaries[0]["manifest_path"])==ROOT/"crates/strehl-cli/Cargo.toml",
                   "actual intended Cargo target")
            demand(a["compiler_message"]==binaries[0] and a["build_finished"]==finished[0],
                   "saved build artifacts equal the sole raw Cargo records")
            origin=ref_shape(a["compiled_original"])
            demand(origin==location(binaries[0]["executable"]) and origin.is_relative_to(ROOT/"target/common-tiff-dimensions-2")
                   and a["compiled_original"]["bytes"]==release["executable"]["bytes"]
                   and a["compiled_original"]["sha256"]==release["executable"]["sha256"],
                   "actual compiled-origin location and byte identity to copied executable")
            continue
        demand(same(r["executable"],release["executable"]),"same actual binary across stages")
        if name!="prepare":demand(same(r["fixtures"],release["fixtures"]),"same actual admitted saved index")
        needed={"prepare":{"build"},"recovery":{"build","prepare"},"render":{"build","prepare","recovery"},
                "verify":{"build","prepare","recovery","render"}}[name]
        demand(set(r["prerequisites"])==needed,"exact stage prerequisite roles")
        for key in needed:
            old=r["prerequisites"][key]
            demand(set(old)==set(release["stages"][key]) and
                   all(same(old[k],release["stages"][key][k],empty=k=="stderr") for k in old),"exact historical prerequisite bundle")
        if name in ("render","verify"):
            demand(stage["parent"]["compiled_source_closure"]==COMPILED,"unchanged compiled source closure")
    demand(len(stages["render"]["parent"]["artifacts"]["cases"])==24
           and sum(len(x["artifacts"]) for x in stages["render"]["parent"]["artifacts"]["cases"])==108,
           "complete actual24 cases and108 publications")

def retained_history(release):
    rows=release["retained_history"]
    demand(type(rows) is list and len(rows)<=16,"bounded separate retained history")
    seen=set()
    out=[]
    for row in rows:
        demand(type(row) is dict and set(row)=={"role","file"} and type(row["role"]) is str
               and 0<len(row["role"])<=96 and row["role"] not in seen,"named distinct history role")
        seen.add(row["role"])
        ref=row["file"]
        raw=read(ref,cap=256*KIB,empty=True)
        # These are authenticated original reports/receipts, not a second pass
        # over the private controls or a claim that their publication met its slice.
        out.append({"role":row["role"],"file":ref,"bytes_authenticated":len(raw),
                    "scope":"Retained original metadata. Saved-control-review publication refusal and separately reserved readback remain distinct; no automatic retry or cost refund."})
    STATE["retained_history"]=out

def error_record(error):
    v={"type":type(error).__name__,"message":str(error)}
    raw=encode(v)
    if len(raw)>4096:
        v={"type":type(error).__name__,"message_prefix":str(error)[:384],
           "full_encoded_error_bytes":len(raw),"full_encoded_error_sha256":digest(raw),
           "scope":"Only the prefix is displayed; full error text is represented by its digest."}
    demand(len(encode(v))<=4096,"bounded saved error")
    return v

def publish_progress():
    global WRITTEN
    if PROGRESS is None:return
    v={"schema":"common-tiff-dimensions-final-saved-read-progress-v1","status":"INCOMPLETE",
       "cases":[{k:r[k] for k in ("ordinal","id","status","passed") if k in r} for r in STATE.get("cases",[])],
       "controls_observed":len([r for r in STATE.get("controls",[]) if r.get("original") is not None]),
       "errors":STATE.get("errors",[])[:32],"read_bytes":dict(COUNTERS)}
    raw=encode(v)
    demand(len(raw)<=64*KIB and WRITTEN+len(raw)<=16*MIB,"bounded progress serialization/write")
    WRITTEN+=len(raw)
    with PROGRESS.open("wb") as f:
        demand(f.write(raw)==len(raw),"whole progress write")
        f.flush();os.fsync(f.fileno())
    tick()

def run(release):
    bm,pm,em=source_history(release)
    stages={}
    for name in ("build","prepare","recovery","render","verify"):
        expected="REFUSED" if name=="prepare" else "COMPLETE_STAGE_UNVERIFIED"
        if name=="verify":
            recorded=parsed(release["stages"][name]["result"],cap=256*KIB)["status"]
            demand(recorded in ("REFUSED","COMPLETE_STAGE_UNVERIFIED"),"bounded actual verifier disposition")
            expected=recorded
        stages[name]=stage_read(name,release["stages"][name],pm if name in ("build","prepare") else em,expected)
    preserved_build_failure(release["history"]["build1"],bm)
    retained_history(release)
    root_capture_records(release,stages)
    link_stages(release,stages)
    exe=release["executable"]
    at(exe,HERE/"build-2/strehl-common-input.exe")
    demand(exe["bytes"]==3201536 and exe["sha256"]==EXE_SHA,"literal actual copied executable")
    read(exe,"executable",128*MIB,stream=True)
    at(release["fixtures"],HERE/"prepare-1/fixtures/index.json")
    demand(release["fixtures"]["bytes"]==40481 and release["fixtures"]["sha256"]==FIXTURE_SHA,"unchanged saved index")
    index=parsed(release["fixtures"],cap=256*KIB)
    recovered_authority(release,stages,pm,em,index)
    at(release["checker"],HERE/"verify-1/check/result.json")
    checker_raw=read(release["checker"],cap=MIB)
    checker=object_json(checker_raw)
    verify=stages["verify"]
    demand(checker_raw==verify["children"][0][1] and checker["schema"]=="common-tiff-dimensions-independent-verification-v1",
           "actual saved checker raw stdout and schema")
    if verify["parent"]["status"]=="COMPLETE_STAGE_UNVERIFIED":
        demand(same(verify["parent"]["artifacts"]["independent_result"],release["checker"]),"linked completed checker artifact")
    demand(same(checker["execution_source"],{"path":"experiments/common-tiff-dimensions/recovery-checker.py",
                   **em["experiments/common-tiff-dimensions/recovery-checker.py"]})
           and checker["invocation"]==verify["children"][0][0]["command"],"actual checker source and command")
    STATE["original_checker"]={"file":release["checker"],"status":checker.get("status"),
       "software_integration_complete":checker.get("software_integration_complete"),"failures":checker.get("failures"),
       "error":checker.get("error"),"saved_case_rows":checker.get("cases",[]),
       "saved_control_rows":checker.get("independent_controls",[]),
       "scope":"Original checker outcome is retained, never relabeled by this reader."}
    names,old_plan,old_image=fixed_input_files(index,release)
    images={}
    receipts={}
    publish_progress()
    for i in range(24):
        try:
            row,image,receipt=inspect_case(i,index,names,stages["render"],release,old_image,old_plan["inputs"])
            STATE["cases"][i]=row
            receipts[i]=receipt
            if image is not None:images[i]=image
        except (ValueError,KeyError,TypeError,OSError,UnicodeError,struct.error) as exc:
            STATE["cases"][i]={"ordinal":i,"id":IDS[i],"status":"SAVED_CASE_REJECTED","passed":False,"error":error_record(exc)}
            STATE["errors"].append({"case":i,"error":error_record(exc)})
        publish_progress()
        tick()
    gains={}
    for i,value in receipts.items():
        if "runtime" in value:
            grid=value["plan"]["grid"]
            key=f'{grid["width"]}x{grid["height"]}'
            gain=value["runtime"]["actual_core_white_band_gain"]
            if key in gains and gains[key]!=gain:
                STATE["errors"].append({"case":i,"error":{"message":"different retained white gains at same geometry"}})
            else:gains[key]=gain
    STATE["band_gains_by_geometry"]=gains
    try:STATE["observer"]=observer_comparison(images,receipts)
    except (ValueError,KeyError,TypeError) as exc:
        STATE["observer"]={"passed":False,"error":error_record(exc)}
        STATE["errors"].append({"observer":error_record(exc)})
    STATE["controls"]=saved_controls(checker,images)
    original_cases=checker.get("cases",[])
    demand(type(original_cases) is list and len(original_cases)<=24,"bounded original checker case prefix")
    for i,row in enumerate(STATE["cases"]):
        old=original_cases[i] if i<len(original_cases) else None
        row["original_checker_row"]=old
        row["original_checker_case_admitted"]=(type(old) is dict and old.get("ordinal")==i
                                              and old.get("id")==IDS[i] and old.get("verified") is True)
    observed_folds=sum(r.get("folded_frames",0) for r in STATE["cases"])
    output_count=len(images)
    STATE["coverage"]={"case_rows":24,"case_rows_passed":sum(r.get("passed") is True for r in STATE["cases"]),
       "controls":135,"control_rows_passed":sum(r["passed"] is True for r in STATE["controls"]),
       "observed_complete_fold_count":observed_folds,"required_fold_count":51,"positive_outputs":output_count,
       "required_positive_outputs":9,"required_case_artifacts":108,"required_inputs":36}
    complete=(not STATE["errors"] and all(r.get("passed") is True and r["original_checker_case_admitted"] for r in STATE["cases"])
              and all(r["passed"] is True for r in STATE["controls"]) and STATE["observer"]["passed"]
              and observed_folds==51 and output_count==9 and len(STATE["input_files"])==36
              and checker.get("status")=="PASS_COMMON_RGB_DIMENSIONS_SOFTWARE_INTEGRATION"
              and checker.get("software_integration_complete") is True
              and all(s["summary"]["all_children_admissible"] for s in stages.values())
              and verify["parent"]["status"]=="COMPLETE_STAGE_UNVERIFIED")
    STATE["saved_evidence_complete"]=complete
    STATE["status"]="PASS_SAVED_DIMENSIONS_EVIDENCE_READER" if complete else "REFUSED_SAVED_DIMENSIONS_EVIDENCE"
    return complete

def main():
    global OUTPUT,PROGRESS,WRITTEN
    parser=argparse.ArgumentParser()
    parser.add_argument("--release",required=True)
    parser.add_argument("--release-sha256",required=True)
    parser.add_argument("--source-sha256",required=True)
    args=parser.parse_args()
    actual=[sys.executable,"-I","-S","-B",str(SELF),"--release",str(location(args.release)),
            "--release-sha256",args.release_sha256,"--source-sha256",args.source_sha256]
    demand(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.orig_argv==actual,
           "exact actual isolated reader invocation")
    own=ref_from_path(SELF,args.source_sha256,128*KIB)
    read(own,"source",128*KIB)
    release_ref=ref_from_path(args.release,args.release_sha256,256*KIB)
    release=parsed(release_ref,cap=256*KIB)
    demand(type(release) is dict and set(release)=={"schema","reader","plan","amendment","producer_freeze","execution_freeze",
       "stages","history","fixtures","checker","executable","legacy","profile","root_captures","retained_history","output"}
       and release["schema"]=="common-tiff-dimensions-final-saved-read-release-v1","closed final16-key evidence release")
    demand(same(release["reader"],own) and set(release["stages"])=={"build","prepare","recovery","render","verify"}
           and set(release["history"])=={"build1"},"fixed reader/stage/history roles")
    at(release["plan"],HERE/"dimensions-independent-result-plan.md")
    at(release["amendment"],HERE/"dimensions-independent-result-recovery-amendment.md")
    read(release["plan"],"source",32*KIB)
    read(release["amendment"],"source",32*KIB)
    OUTPUT=location(release["output"])
    demand(OUTPUT==HERE/"work/dimensions-independent-read-1.json" and not OUTPUT.exists(),"fresh fixed one-shot result")
    PROGRESS=HERE/"work/dimensions-independent-read-1-progress.json"
    demand(not PROGRESS.exists() and OUTPUT.parent.is_dir(),"fresh progress within existing output parent")
    plain(OUTPUT.parent)
    STATE.update(schema="common-tiff-dimensions-final-saved-read-v1",status="INCOMPLETE",saved_evidence_complete=False,
        source=own,release=release_ref,invocation=sys.orig_argv,stages=[],original_failures=[],errors=[],
        cases=[{"ordinal":i,"id":ident,"status":"NOT_YET_READ","passed":False} for i,ident in enumerate(IDS)],
        controls=[{"ordinal":i,"id":r[0],"status":"NOT_YET_READ","passed":False} for i,r in enumerate(control_blueprint())],
        authorship={"draft_author":"coordinate_verification","original_checker_author_overlap":True,
          "independent_source_and_choice_review_required":"sampler_result_review",
          "scope":"A draft from the original checker author is not self-verification. Independent review and released execution/interpretation are required."},
        claims={"identity_common_rgb_software_only":True,"physical_noise_calibration":False,"real_geometry_accuracy":False,
                "quality_or_default_admission":False,"per_repeat_variance":False,"case04_independent_float_proof":False},
        reservation={"cpu_seconds":30,"wall_seconds":60,"aggregate_read_bytes":256*MIB,"new_retention_bytes":16*MIB,
                     "nonrefundable":True})
    try:
        publish_progress()
        run(release)
    except (ValueError,KeyError,TypeError,OSError,UnicodeError,struct.error,zipfile.BadZipFile) as exc:
        STATE.update(status="REFUSED_SAVED_DIMENSIONS_EVIDENCE",saved_evidence_complete=False)
        STATE["errors"].append({"reader":error_record(exc)})
    sample=tick(reserve=True)
    STATE["accounting"]={**sample,"publication_allowance":{"cpu_seconds":2,"wall_seconds":3},
                        "read_bytes_by_category":dict(COUNTERS),"physical_and_inflated_read_bytes":sum(COUNTERS.values()),
                        "writes_before_final":WRITTEN,"category_caps":CATEGORY_CAPS,
                        "scope":"Samples before final publication. Root must retain the actual complete interpreter interval and exit. Full30CPU/60wall is charged even on refusal."}
    STATE["authenticated_files"]=[{"file":v["ref"],"category":v["category"]} for v in CACHE.values()]
    raw=encode(STATE)
    demand(len(raw)<=2*MIB and WRITTEN+len(raw)<=16*MIB,"bounded complete final serialization and writes")
    WRITTEN+=len(raw)
    with OUTPUT.open("xb") as f:
        demand(f.write(raw)==len(raw),"whole fresh final write")
        f.flush();os.fsync(f.fileno())
    final_ref={"path":str(OUTPUT),"bytes":len(raw),"sha256":digest(raw)}
    demand(read(final_ref,"readback",2*MIB)==raw,"same final publication readback")
    advertisement=encode({"schema":"common-tiff-dimensions-final-saved-read-advertisement-v1",
        "status":STATE["status"],"result":final_ref,"saved_evidence_complete":STATE["saved_evidence_complete"],
        "case_rows":24,"control_rows":135})
    demand(len(advertisement)<=4096 and WRITTEN+len(advertisement)<=16*MIB,"bounded advertisement write reservation")
    WRITTEN+=len(advertisement)
    demand(sys.stdout.buffer.write(advertisement)==len(advertisement),"whole bounded final advertisement")
    sys.stdout.buffer.flush()
    tick()
    return 0 if STATE["saved_evidence_complete"] else 1

if __name__=="__main__":
    raise SystemExit(main())
