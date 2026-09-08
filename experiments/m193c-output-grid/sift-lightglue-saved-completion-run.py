"""Private saved-output completion only. No image/model/numerical package imports."""
import time
START=time.monotonic()
import argparse
import ast
from contextlib import contextmanager
import ctypes
import ctypes.wintypes as wt
from dataclasses import dataclass
from decimal import Decimal,ROUND_CEILING
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import traceback
import types
from typing import Any,Sequence

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
SPEC=HERE/"sift-lightglue-saved-completion-preregister.md"
MIB=1<<20;KIB=1024
VERSION="m193c-sift-lightglue-saved-completion-v1"
COMPLETE="COMPLETE_SAVED_PRIVATE_LIGHTGLUE_CHECKS_ONLY"
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
CAPS=dict(cpu_seconds=60,wall_seconds=120,file_bytes=8*MIB,metadata_bytes=8*MIB)
FAMILIES=dict(terminal=512*KIB,log=MIB,publication=256*KIB,data=256*KIB,science=256*KIB,runtime=128*KIB,metadata=512*KIB)
CONTROL_IDS=("private-learned-known-geometry","native-two-pixel-map-destroyer","saved-match-registrar-observer","within-split-association-destroyer","private-restored")
CODE="UNMEASURED_INPUT_REGISTRATION_INADEQUATE"
PINS={
 "native-derivative-run.py":"94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a",
 "bounded-process.py":"47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b",
 "direct-pair-run.py":"fbf89076ae3e8069ab717796818a6c0a2417637cd29973d533ceefdd1fd82782",
 "sift-lightglue-adapter.py":"febb91b856ac17c9d453d16e81aa412e9ea46465ca1bc03c9ce3b189e604495c",
 "factor-eight-prototype.py":"86111beb318f270c4532d4a5299d8b6a14413845c5eb384790f3e8d21d959d6f",
 "reference.py":"c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790"}
REFERENCE=ROOT/"experiments/M193-cover-overlap/reference.py"
HARNESS=ROOT/"experiments/m12-scorecard/m12-harness.py"
PURE=("ContractError","require","round_fraction_ties_even","ceil_sqrt_ratio","Match","SimilarityQ32",
      "quantize_similarity","pair_hypothesis","exact_similarity_fit","residual_squared_q40","inlier_threshold_squared","choose_similarity","register_to_reference")
CONSTANTS=("Q32","XY_Q","MAX_MATCHES","MIN_FIT_MATCHES","MIN_HOLDOUT_MATCHES","INLIER_RADIUS_PX","MAX_HELDOUT_RMS_PX")
JOB_NAMES=("kernel32","ntdll","CREATE_SUSPENDED","JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE",
           "JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS","JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS",
           "IO_COUNTERS","JOBOBJECT_BASIC_LIMIT_INFORMATION","JOBOBJECT_EXTENDED_LIMIT_INFORMATION","JOBOBJECT_BASIC_ACCOUNTING_INFORMATION",
           "create_process_job","assign_process_to_job","job_accounting","job_memory")
JOB_SIGNATURES=tuple(f"{owner}.{method}.{field}" for owner,method in (
    ("kernel32","CloseHandle"),("kernel32","CreateJobObjectW"),("kernel32","AssignProcessToJobObject"),
    ("kernel32","SetInformationJobObject"),("kernel32","QueryInformationJobObject"),("ntdll","NtResumeProcess"))
    for field in ("argtypes","restype"))

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def raw(path,cap=4*MIB):
    with Path(path).open("rb") as stream:data=stream.read(cap+1)
    need(0<len(data)<=cap,"bounded opaque read");return data
def binding(data):return dict(bytes=len(data),sha256=sha(data))
def path_of(ref):return (ROOT/ref["path"]).resolve()
def same(a,b):return path_of(a)==path_of(b) and all(a[k]==b[k] for k in ("bytes","sha256"))
def replace(command,plan,request=None):
    return [plan if x=="ACTUAL_PLAN_SHA256" else request if x=="ACTUAL_REQUEST_SHA256" else x for x in command]

def loaded(path,pin,name):
    data=raw(path);need(binding(data)==pin,"executed whole-source pin")
    module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
    exec(compile(data,str(path),"exec"),module.__dict__);return module

def selected(path,pin,names,globals_=None):
    data=raw(path);need(binding(data)==pin,"selected source pin")
    tree=ast.parse(data,str(path));nodes=[];seen=set()
    for node in tree.body:
        if isinstance(node,ast.ImportFrom) and node.module=="__future__":nodes.append(node);continue
        name=node.name if isinstance(node,(ast.FunctionDef,ast.ClassDef)) else None
        if isinstance(node,ast.Assign) and len(node.targets)==1:
            target=node.targets[0]
            if isinstance(target,ast.Name):name=target.id
            elif isinstance(target,ast.Attribute):name=ast.unparse(target)
        if name in names:
            need(name not in seen,"unique selected AST declaration");seen.add(name);nodes.append(node)
    need(seen==set(names),"complete closed AST declarations")
    module=types.ModuleType("m193c_saved_pure_"+path.stem.replace("-","_"));module.__file__=str(path);sys.modules[module.__name__]=module
    module.__dict__.update(dict(math=math,Fraction=Fraction,dataclass=dataclass,Any=Any,Sequence=Sequence,
                               json=json,traceback=traceback,hashlib=hashlib,struct=struct,need=need,CODE=CODE,
                               ctypes=ctypes,wt=wt,subprocess=subprocess))
    if globals_:module.__dict__.update(globals_)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),module.__dict__)
    return module

def setup(args):
    utility=HERE/"native-derivative-run.py";data=raw(utility)
    need(sha(data)==PINS[utility.name],"immutable reader hash")
    n=loaded(utility,binding(data),"m193c_saved_reader")
    data=raw(args.plan);need(sha(data)==args.sha256,"external plan SHA")
    plan=n.strict(data);n.closed(plan,"schema source_bindings commission_prefix prior_work preparation_allowance python_executable commands".split(),"saved completion plan")
    need(plan["schema"]=="m193c-sift-lightglue-saved-completion-plan-v1" and plan["preparation_allowance"]==ALLOWANCE,"version/allowance")
    paths=[SELF,SPEC,HERE/"saved-completion-publication.py",REFERENCE,HARNESS,*[HERE/name for name in PINS if name!="reference.py"]]
    for path in paths:
        pin=plan["source_bindings"][n.relative(path)]
        need(binding(raw(path))==pin and (path.name not in PINS or pin["sha256"]==PINS[path.name]),"closed held source")
    output=Path(args.output).resolve()
    need(Path.cwd().resolve()==ROOT and output.is_relative_to(HERE) and not output.exists(),"fresh owned output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions)=={"faulthandler","pycache_prefix"} and sys._xoptions["faulthandler"] is True,"no bytecode/exact options")
    cache=Path(sys._xoptions["pycache_prefix"]).resolve()
    need(not cache.exists() and cache.is_relative_to(output.parent if args.worker else output),"fresh owned cache")
    n.closed(plan["commands"],("parent","worker"),"commands")
    need(replace(plan["commands"]["worker" if args.worker else "parent"],args.sha256,args.request_sha256)==sys.orig_argv,"exact command")
    publication=loaded(HERE/"saved-completion-publication.py",plan["source_bindings"][n.relative(HERE/"saved-completion-publication.py")],"m193c_saved_publication")
    return n,publication,plan,output,dict(path=str(Path(args.plan).resolve()),**binding(data))

def budget_for(n,output,prior,worker):
    class Budget(n.Budget):
        def __init__(self):
            super().__init__(output,prior,START,0.0)
            self.complete=True;self.terminal_mode=False;self.quotas=[];self.family_overrides={}
        def family(self,path):
            path=Path(path);relative=path.relative_to(self.output)
            parts=relative.parts[1:] if relative.parts[0]=="worker" else relative.parts
            if parts[0]=="publication-controls":return "publication"
            if parts[-1] in ("result.json","first-publication.json","publication-stage.json","emergency-refusal.json"):return "terminal"
            if parts[-1]=="worker.log":return "log"
            if parts[-1].startswith("publication-"):return "publication"
            if parts[-1].startswith("science-"):return "data" if path.suffix==".bin" else "science"
            if parts[-1].startswith("runtime-"):return "runtime"
            return "metadata"
        def check(self,force=False,terminal=None):
            terminal=self.terminal_mode if terminal is None else terminal
            super().check(force)
            work=self.work()
            for key,value in CAPS.items():need(work[key]-self.prior[key]<=value,"local "+key+" cap")
            totals={key:0 for key in FAMILIES}
            for path,size in self.extents.items():totals[self.family_overrides.get(path,self.family(path))]+=size
            need(all(totals[k]<=v for k,v in FAMILIES.items()),"output family maximum")
            if not terminal:
                cpu=2 if worker else 4;wall=3 if worker else 6
                need(work["cpu_seconds"]<=1200-cpu and work["cpu_seconds"]-self.prior["cpu_seconds"]<=60-cpu,"reserved publication CPU")
                need(work["wall_seconds"]<=1800-wall and work["wall_seconds"]-self.prior["wall_seconds"]<=120-wall,"reserved publication wall")
                if worker:need(time.monotonic()-START<=87,"worker publication margin")
        def reserve(self,path,size,family,terminal):
            path=Path(path).resolve();need(path.is_relative_to(self.output) and family in FAMILIES,"owned reservation family")
            need(type(size) is int and size>0,"positive allocation")
            before=self.extents.get(str(path),0);growth=max(0,size-before)
            self.check(True,terminal=terminal)
            if not terminal:
                for root,cap,start in self.quotas:
                    if path.is_relative_to(root):
                        used=sum(v for p,v in self.extents.items() if Path(p).is_relative_to(root))-start
                        need(used+growth<=cap,"ordinary quota capacity")
            totals=sum(v for p,v in self.extents.items() if self.family_overrides.get(p,self.family(p))==family)
            need(totals+growth<=FAMILIES[family],"prewrite family reservation")
            work=self.work()
            need(work["file_bytes"]+growth<=4<<30 and work["metadata_bytes"]+growth<=128*MIB,"prewrite global reservation")
            need(sum(self.extents.values())+growth<=8*MIB,"prewrite local reservation")
            self.family_overrides[str(path)]=family;self.extents[str(path)]=max(before,size)
        @contextmanager
        def quota(self,root,cap):
            root=Path(root).resolve();start=sum(v for p,v in self.extents.items() if Path(p).is_relative_to(root))
            self.quotas.append((root,cap,start))
            try:yield
            finally:self.quotas.pop()
        @contextmanager
        def terminal(self):
            before=self.terminal_mode;self.terminal_mode=True
            try:yield
            finally:self.terminal_mode=before
        def limits(self,metadata_cap=MIB):
            self.check(True);work=self.work()
            # Original launcher's cleanup has5s Job termination+5s wait+1s join.
            wall=min(90,120-(work["wall_seconds"]-self.prior["wall_seconds"])-18,1800-work["wall_seconds"]-18)
            cpu=min(60-(work["cpu_seconds"]-self.prior["cpu_seconds"])-4,1200-work["cpu_seconds"]-4)
            need(wall>3 and cpu>2,"child envelope plus12s cleanup and6s publication margin")
            return dict(cpu_seconds=cpu,wall_seconds=wall,log_bytes=MIB,committed_bytes=8<<30)
    return Budget()

def checked(files,ref,cap=4*MIB):
    path=files.verify(ref,cap,Path(ref["path"]).is_absolute())
    data=raw(path,cap);need(binding(data)=={k:ref[k] for k in ("bytes","sha256")},"same bytes")
    return data
def read(files,ref):return files.read(ref,absolute=Path(ref["path"]).is_absolute())
def typed_prior(n,value):
    n.closed(value,ALLOWANCE,"four carry fields")
    need(all(n.number(value[k]) if k.endswith("seconds") else n.integer(value[k]) for k in ALLOWANCE),"typed carry")

def authority(n,plan,files):
    refs=plan["commission_prefix"];n.closed(refs,("plan","worker_result","outer","console","exit","audit"),"actual failed prefix")
    previous,worker,outer,audit=(read(files,refs[k]) for k in ("plan","worker_result","outer","audit"))
    need(audit["schema"]=="m193c-saved-sift-lightglue-commission-prefix-audit-v3" and
         audit["status"]=="PASS_SAVED_SIFT_LIGHTGLUE_COMMISSION_PREFIX_AUDIT" and audit["saved_prefix_verified"] is True and
         audit["subject_complete"] is False and audit["admission_allowed"] is False and audit["cpu_accounting_complete"] is False and
         audit["parent_result_missing"] is True,"explicit limited failed-prefix eligibility")
    need(set(audit["external"])==set(refs)-{"audit"} and all(same(audit["external"][k],refs[k]) for k in audit["external"])
         and same(audit["worker_result"],refs["worker_result"]),"audit exact saved inputs")
    need(audit["cpu_reservation_seconds"]==300 and audit["missing_parent_publication_cpu_allowance_seconds"]==2,
         "accepted missing-CPU conservative charges")
    missing=Path(audit["parent_result_expected_path"]).resolve()
    need(missing==path_of(refs["worker_result"]).parent.parent/"result.json" and not missing.exists(),"audited parent is still absent")
    need(previous["schema"]=="m193c-sift-lightglue-commission-plan-v1" and worker["status"]=="REFUSED" and
         worker["active_phase"]=="private-known-geometry" and worker["assembly"] is None and worker["counters"]["registrar_calls"]==0,
         "old attempt stays refused at zero fits")
    need(worker["counters"]==dict(private_decodes=1,real_decode_attempts=9,real_decodes_completed=9,feature_extractions=11,
         private_model_forwards=1,real_model_forwards=0,registrar_calls=0) and len(worker["exports"])==11 and
         len(worker["controls"])==12 and all(x["passed"] is True for x in worker["controls"]),"exact saved scientific prefix")
    need(same(worker["plan"],refs["plan"]) and worker["sources_unchanged"] is True and worker["source_bindings"]==previous["source_bindings"] and
         all(plan["source_bindings"].get(k)==v for k,v in previous["source_bindings"].items()),"immutable full old source closure")
    need(outer["exit_code"]==1 and outer["plan_sha256"]==refs["plan"]["sha256"] and
         outer["command"]==replace(previous["commands"]["parent"],refs["plan"]["sha256"]),"actual failed outer association")
    need(checked(files,refs["exit"],64).strip()==b"1","actual failed exit")
    console=n.strict(checked(files,refs["console"],MIB).splitlines()[-1])
    need(set(console)=={"error","finalization_errors"} and len(console["finalization_errors"])==2 and
         all("trace metadata preallocation" in x for x in console["finalization_errors"]),"actual both failed parent publications")
    prior=read(files,plan["prior_work"]);typed_prior(n,prior)
    base=dict(audit["actual_final_work"]);typed_prior(n,base)
    next_wall=Decimal(audit["next_wall_seconds"])
    need(next_wall.is_finite() and next_wall>=0 and next_wall==Decimal(str(base["wall_seconds"])),"audit wall string agrees with charged work")
    for key in ("cpu_seconds","wall_seconds"):base[key]=Decimal(str(base[key])).quantize(Decimal(".000001"),rounding=ROUND_CEILING)
    need(all(Decimal(str(prior[k]))==Decimal(str(base[k]))+ALLOWANCE[k] for k in ALLOWANCE),"audited conservative carry plus preparation")
    need(worker["inference_observer_nonperturbation"]=="UNTESTED_ONE_FORWARD","no inherited inference-observer pass")
    for ref in worker["exports"]+[r["record"] for r in worker["controls"]]+[
        worker[k] for k in ("model_inputs","normalized_private_descriptors","normalization_destroyer","learned_output","runtime_before","runtime_after")]:
        read(files,ref)
    need(same(worker["runtime_before"],worker["runtime_after"]) or
         all(worker["runtime_before"][k]==worker["runtime_after"][k] for k in ("bytes","sha256")),"exact identical prior runtime bytes")
    return worker,audit,prior


def feature(n,files,ref):
    value=read(files,ref);core=value["core"];count=core["count"]
    need(value["schema"]=="m193c-sift-export-feature-v1" and type(count) is int and 24<=count<=1024,"saved feature shape")
    need(value["descriptors"]["dtype"]=="|u1" and value["descriptors"]["shape"]==[count,128] and
         value["key_fields"]["dtype"]=="<i8" and value["key_fields"]["shape"]==[count,7],"exact export types")
    desc=checked(files,value["descriptors"]["file"],128*KIB);keys_raw=checked(files,value["key_fields"]["file"],64*KIB)
    need(len(desc)==count*128 and len(keys_raw)==count*56,"exact binary extents")
    keys=list(struct.iter_unpack("<7q",keys_raw));descriptors=[desc[i*128:(i+1)*128] for i in range(count)]
    full=[key+(descriptors[i],) for i,key in enumerate(keys)]
    need(full==sorted(full),"original row order, no repair")
    coarse=[[key[2],key[1]] for key in keys];native=[[8*x+896,8*y+896] for x,y in coarse]
    actual=dict(count=count,coarse_coordinates_q8=coarse,native_coordinates_q8=native,
                descriptors_sha256=sha(b"".join(struct.pack("<128h",*row) for row in descriptors)),
                keys_sha256=sha(n.json_bytes([list(row[:-1])+[row[-1].hex()] for row in full])))
    need(n.json_bytes(actual)==n.json_bytes(core) and value["canonical_before_sha256"]==value["canonical_after_sha256"]==sha(n.json_bytes(core)),
         "entire saved feature core and original digest identities")
    size=value["explicit_coarse_image_size"]
    attrs=dict(keypoints=([count,2],[v/256 for point in coarse for v in point]),
               scales=([count],[key[3]/256 for key in keys]),
               oris=([count],[(key[4]/256)*math.pi/180 for key in keys]),
               image_size=([2],size))
    for name,(shape,vals) in attrs.items():
        need(all(type(x) in (int,float) and math.isfinite(x) for x in vals),"finite saved key-derived attributes")
        witness=dict(dtype="<f4",shape=shape,sha256=sha(struct.pack("<"+"f"*len(vals),*vals)))
        need(witness==value["attributes"][name],"exact previously declared auxiliary units")
    return dict(keys=keys,descriptors=descriptors,coarse=coarse,native=native),value

def output_values(n,files,ref,n0,n1):
    saved=read(files,ref);o=saved["output"];w=saved["tensor_bytes"]
    need(saved["schema"]=="m193c-private-lightglue-output-v1" and
         set(o)==set("matches matches0 matches1 matching_scores0 matching_scores1 prune0 prune1 scores stop".split()) and
         type(o["stop"]) is int and o["stop"]==9,"full saved learned output contract")
    count=len(o["matches"]);need(0<=count<=min(n0,n1) and len(o["scores"])==count,"uncapped learned population")
    shapes=dict(matches=[count,2],scores=[count],matches0=[1,n0],matches1=[1,n1],
                matching_scores0=[1,n0],matching_scores1=[1,n1],prune0=[1,n0],prune1=[1,n1])
    def flatten(value,shape):
        need(type(value) is list and len(value)==shape[0],"actual nested tensor shape")
        return [z for x in value for z in flatten(x,shape[1:])] if len(shape)>1 else value
    need(set(w)==set(shapes),"every original tensor witness")
    flat={}
    for key,shape in shapes.items():
        vals=flatten(o[key],shape);integer=key.startswith("matches")
        need(all(type(x) is int for x in vals) if integer else all(type(x) is float and math.isfinite(x) for x in vals),"original tensor element type")
        data=struct.pack("<"+("q" if integer else "f")*len(vals),*vals)
        need(w[key]==dict(dtype="<i8" if integer else "<f4",shape=shape,sha256=sha(data)),"whole original tensor bytes")
        if not integer:need(list(struct.unpack("<"+"f"*len(vals),data))==vals,"saved values exactly representable as original float32")
        flat[key]=vals
    need(all(x==9.0 for x in flat["prune0"]+flat["prune1"]),"actual disabled-pruning values")
    need(all(0<=x<=1 for key in ("scores","matching_scores0","matching_scores1") for x in flat[key]),"bounded original confidence values")
    m0,m1=flat["matches0"],flat["matches1"];s0,s1=flat["matching_scores0"],flat["matching_scores1"]
    need(all(-1<=j<n1 for j in m0) and all(-1<=i<n0 for i in m1),"all dense indices")
    expected=[]
    for i,j in enumerate(m0):
        if j>=0:
            need(m1[j]==i and .1<s0[i]<=1 and s1[j]==s0[i],"actual mutual accepted association/confidence")
            expected.append([i,j])
    need(o["matches"]==expected and o["scores"]==[s0[i] for i,j in expected],"uncapped compact output equals dense accepted population")
    need(all(i<0 or m0[i]==j for j,i in enumerate(m1)),"reverse dense mutual consistency")
    return saved

def runtime_presence(n,files,plan,old):
    need(not any(name.split(".")[0] in {"torch","numpy","cv2","tifffile","PIL","lightglue","flash_attn"} for name in sys.modules),"no forbidden process imports")
    modules=[];paths=set()
    for name,module in sorted(tuple(sys.modules.items())):
        filename=getattr(module,"__file__",None)
        if filename:
            path=Path(filename).resolve()
            if path.is_file():modules.append((name,path));paths.add(path)
    kernel=ctypes.WinDLL("kernel32",use_last_error=True);psapi=ctypes.WinDLL("psapi",use_last_error=True)
    kernel.GetCurrentProcess.argtypes=[];kernel.GetCurrentProcess.restype=wt.HANDLE
    psapi.EnumProcessModulesEx.argtypes=[wt.HANDLE,ctypes.POINTER(wt.HMODULE),wt.DWORD,ctypes.POINTER(wt.DWORD),wt.DWORD];psapi.EnumProcessModulesEx.restype=wt.BOOL
    psapi.GetModuleFileNameExW.argtypes=[wt.HANDLE,wt.HMODULE,wt.LPWSTR,wt.DWORD];psapi.GetModuleFileNameExW.restype=wt.DWORD
    handles=(wt.HMODULE*2048)();needed=wt.DWORD();handle=kernel.GetCurrentProcess()
    need(psapi.EnumProcessModulesEx(handle,handles,ctypes.sizeof(handles),ctypes.byref(needed),3),"actual native modules")
    need(needed.value<=ctypes.sizeof(handles) and needed.value%ctypes.sizeof(wt.HMODULE)==0,"complete native list")
    native=[]
    for h in handles[:needed.value//ctypes.sizeof(wt.HMODULE)]:
        buf=ctypes.create_unicode_buffer(32768);length=psapi.GetModuleFileNameExW(handle,h,buf,len(buf))
        need(0<length<len(buf)-1,"complete native path")
        path=Path(buf.value).resolve();paths.add(path);native.append(path)
    need(len(paths)<=1024,"bounded current stdlib/native closure")
    previous=read(files,old["runtime_before"]);registry={path_of(ref):(i,ref) for i,ref in enumerate(previous["files"])}
    empty_registry={Path(x["path"]).resolve():x for x in previous["empty_runtime_files"]}
    local={ROOT/name:dict(path=name,**pin) for name,pin in plan["source_bindings"].items()}
    entries=[];indices={};empties=[]
    for path in sorted(paths,key=str):
        indices[path]=len(entries)
        if path in local:
            files.verify(local[path],4*MIB);entries.append(dict(local_source=n.relative(path)))
        elif path in registry:
            index,ref=registry[path];files.verify(ref,64*MIB,True);entries.append(dict(prior_runtime_index=index))
        elif path in empty_registry:
            before=n.metadata(path);expected=empty_registry[path]
            need(before["bytes"]==0 and before==expected["metadata"] and expected["sha256"]==sha(b""),"admitted empty runtime identity")
            with path.open("rb") as stream:
                opened=os.fstat(stream.fileno())
                need((opened.st_dev,opened.st_ino)==(before["device"],before["file_id"]) and stream.read(1)==b"","bounded opened empty runtime")
            need(n.metadata(path)==before,"empty runtime unchanged after bounded read")
            witness=dict(path=str(path),metadata=before,bytes=0,sha256=sha(b""));empties.append(witness);entries.append(dict(empty_runtime_index=list(empty_registry).index(path)))
        else:raise ValueError("unlisted actual executable dependency: "+str(path))
    return dict(schema="m193c-saved-completion-runtime-presence-v1",prior_registry=old["runtime_before"],entries=entries,
                python_modules=[[name,indices[path]] for name,path in modules],native_module_indices=sorted(indices[path] for path in native),
                empty_current_files=empties,python_version=sys.version,scope="actual current stdlib/native presence; no model or image imports")

def write_json(pub,b,files,path,value,family,terminal=False):
    ref=pub.Writer(b,path.parent,family).write(path,pub.encoded(value),terminal=terminal)
    files.verify(ref,4*MIB,True);return ref
def write_bin(pub,b,files,path,data):
    if not data:return dict(count=0,file=None,bytes=0,sha256=sha(b""))
    ref=pub.Writer(b,path.parent,"data").write(path,data);files.verify(ref,MIB,True);return ref
def compare(n,name,a,z):return dict(name=name,left_sha256=sha(n.json_bytes(a)),right_sha256=sha(n.json_bytes(z)),equal=n.json_bytes(a)==n.json_bytes(z))

def science(n,pub,plan,files,b,output,result,old,audit):
    get=lambda path:plan["source_bindings"][n.relative(path)]
    v=selected(REFERENCE,get(REFERENCE),PURE+CONSTANTS)
    d=selected(HERE/"direct-pair-run.py",get(HERE/"direct-pair-run.py"),("observe_pair","signature"))
    s=selected(HERE/"sift-lightglue-adapter.py",get(HERE/"sift-lightglue-adapter.py"),("assemble","truth_rows","registrar","QUALIFIER"))
    f=selected(HERE/"factor-eight-prototype.py",get(HERE/"factor-eight-prototype.py"),("corner_errors","literal_corner_pass"),dict(Q32=v.Q32))
    v.match_features=lambda a,z:(_ for _ in ()).throw(ValueError("uninstalled saved-match callback"))
    result["qualification"]=s.QUALIFIER
    data=[]
    for ref in old["exports"]:
        item,record=feature(n,files,ref)
        if len(data)<2:data.append(item)
    result["saved_feature_checks"]=11
    saved=output_values(n,files,old["learned_output"],len(data[0]["keys"]),len(data[1]["keys"]))
    result["active_phase"]="saved-assembly"
    matches,landmarks=s.assemble(v,*data,saved["output"]["matches"],saved["output"]["scores"])
    raw_rows=[dict(reference_q8=data[0]["native"][i],source_q8=data[1]["native"][j]) for i,j in saved["output"]["matches"]]
    truths=dict(uncapped=s.truth_rows(raw_rows),capped=s.truth_rows(landmarks))
    need(truths["uncapped"]["count"]==len(saved["output"]["matches"]) and truths["capped"]["count"]==min(256,len(saved["output"]["matches"])),"uncapped/capped actual populations")
    recovered=audit["recovered_assembly"]
    if "expanded_landmarks_canonical_sha256" in recovered:
        need(sha(n.json_bytes(landmarks))==recovered["expanded_landmarks_canonical_sha256"],"independent complete capped row equality")
    else:need(n.json_bytes(landmarks)==n.json_bytes(recovered["landmarks"]),"independent complete capped row equality")
    def truth_record(name,truth):
        blob=b"".join(struct.pack("<6iQ",*row["reference_q8"],*row["source_q8"],*row["offset_q8"],row["squared_error_q16"]) for row in truth["rows"])
        payload=write_bin(pub,b,files,output/("science-"+name+"-truth.bin"),blob)
        return dict({k:x for k,x in truth.items() if k!="rows"},row_layout="<6iQ:reference/source/offset Q8;squared_error Q16",rows=payload,
                    original_rows_canonical_sha256=sha(n.json_bytes(truth["rows"])))
    def packed_rows(name,rows,association):
        payload=[]
        for i,row in enumerate(rows):
            linked=association[i];need(row["digest"]==linked["digest"] and row["reference_q8"]==linked["reference_q8"] and row["source_q8"]==linked["source_q8"],"actual captured rows equal supplied associations")
            state=0 if row.get("inlier") is None else 2 if row["inlier"] else 1
            payload.append(struct.pack("<HHHBB4i32s",linked["reference_feature_index"],linked["source_feature_index"],linked["learned_ordinal"],
                                       int(row["split"]=="holdout"),state,*row["reference_q8"],*row["source_q8"],bytes.fromhex(row["digest"])))
        blob=b"".join(payload)
        return dict(count=len(rows),file=write_bin(pub,b,files,output/("science-"+name+"-rows.bin"),blob) if blob else None,
                    empty_sha256=sha(b"") if not blob else None,row_bytes=56,
                    radius_membership="0 unknown;1 outside;2 within returned-map2-native radius; not refinement subset",
                    full_rows_canonical_sha256=sha(n.json_bytes(rows)))
    assembly=dict(schema="m193c-saved-learned-assembly-v1",rows=packed_rows("supplied",landmarks,landmarks),
                  uncapped=truth_record("uncapped",truths["uncapped"]),capped=truth_record("capped",truths["capped"]),
                  population_relation="SAME_ROWS_NO_INDEPENDENT_CORROBORATION" if len(raw_rows)<=256 else "UNCAPPED_AND_HASH_CAPPED_POPULATIONS",
                  learned_output=old["learned_output"],private_exports=old["exports"][:2],qualification=s.QUALIFIER,
                  full_landmarks_canonical_sha256=sha(n.json_bytes(landmarks)))
    result["assembly"]=write_json(pub,b,files,output/"science-assembly.json",assembly,"science")
    def fit(values,associated,name,mode="count"):
        b.check(True);result["counters"]["registrar_calls"]+=1;need(result["counters"]["registrar_calls"]<=5,"five fit maximum")
        outcome=s.registrar(v,d,values,mode)
        compact=dict(schema="m193c-saved-learned-fit-v1",mode=mode,intrinsic=d.signature(outcome),
                     captured_rows=packed_rows(name,outcome["landmarks"],associated),heldout_bbox_q8=outcome["heldout_bbox_q8"],
                     full_outcome_canonical_sha256=sha(n.json_bytes(outcome)),qualification=s.QUALIFIER)
        ref=write_json(pub,b,files,output/("science-"+name+"-fit.json"),compact,"science");result["fits"].append(ref)
        b.check(True);return outcome,ref
    def control(name,ok,evidence):
        row=dict(id=name,passed=bool(ok),evidence=evidence);result["controls"].append(row)
        row["record"]=write_json(pub,b,files,output/("science-control-"+name+".json"),row,"science")
        need(ok,"saved private control: "+name)
    result["active_phase"]=CONTROL_IDS[0]
    baseline,baseline_ref=fit(matches,landmarks,"baseline")
    control(CONTROL_IDS[0],baseline["status"]=="RETURNED" and f.literal_corner_pass(baseline["transform"]) and
            truths["uncapped"]["passes"] and truths["capped"]["passes"],dict(fit=baseline_ref,truth=result["assembly"],
            corners=[] if baseline["transform"] is None else f.corner_errors(baseline["transform"])))
    result["active_phase"]=CONTROL_IDS[1];shifted=dict(baseline["transform"]);shifted["tx"]+=2*(1<<32)
    control(CONTROL_IDS[1],not f.literal_corner_pass(shifted),dict(transform=shifted,corners=f.corner_errors(shifted),qualification=s.QUALIFIER))
    result["active_phase"]=CONTROL_IDS[2]
    off,off_ref=fit(matches,landmarks,"off","off");placebo,placebo_ref=fit(matches,landmarks,"placebo","placebo")
    comparisons=[compare(n,name,d.signature(baseline),d.signature(value)) for name,value in (("off",off),("placebo",placebo))]
    control(CONTROL_IDS[2],all(x["equal"] for x in comparisons),dict(comparisons=comparisons,off=off_ref,placebo=placebo_ref))
    result["active_phase"]=CONTROL_IDS[3];permutation=list(range(len(matches)))
    for split in (0,1):
        ids=list(range(split,len(matches),2));ranked=sorted(ids,key=lambda i:hashlib.sha256(b"M193C-LG-ASSOCIATION-FAULT\0"+matches[i].digest).digest())
        for at,other in zip(ids,ranked,strict=True):permutation[at]=other
    bad=[v.Match(m.reference_x_q8,m.reference_y_q8,matches[permutation[i]].source_x_q8,matches[permutation[i]].source_y_q8,m.digest) for i,m in enumerate(matches)]
    badlinks=[dict(row,source_q8=landmarks[permutation[i]]["source_q8"],source_feature_index=landmarks[permutation[i]]["source_feature_index"]) for i,row in enumerate(landmarks)]
    changed=any(a["source_q8"]!=z["source_q8"] for a,z in zip(landmarks,badlinks,strict=True))
    badtruth=s.truth_rows(badlinks);badfit,badref=fit(bad,badlinks,"fault")
    control(CONTROL_IDS[3],changed and not badtruth["passes"] and (badfit["status"]!="RETURNED" or not f.literal_corner_pass(badfit["transform"])),
            dict(permutation=permutation,actual_pairing_changed=changed,truth=truth_record("fault",badtruth),fit=badref,
                 scope="labelled metadata pairing fault; original row order/digest/split retained"))
    result["active_phase"]=CONTROL_IDS[4];restored,restored_ref=fit(matches,landmarks,"restored")
    comparison=compare(n,"entire-restored-outcome",baseline,restored)
    control(CONTROL_IDS[4],comparison["equal"] and restored["status"]=="RETURNED" and f.literal_corner_pass(restored["transform"]),
            dict(comparison=comparison,fit=restored_ref))
    result["active_phase"]="complete"


def run_main():
    parser=argparse.ArgumentParser()
    for name in ("plan","sha256","output"):parser.add_argument("--"+name,required=True)
    parser.add_argument("--worker",action="store_true");parser.add_argument("--request");parser.add_argument("--request-sha256")
    args=parser.parse_args();need(args.worker==(args.request is not None and args.request_sha256 is not None),"worker request arguments")
    n,pub,plan,output,plan_ref=setup(args)
    prior_raw=raw(path_of(plan["prior_work"]),MIB)
    need(binding(prior_raw)=={k:plan["prior_work"][k] for k in ("bytes","sha256")},"held carry bytes")
    plan_prior=n.strict(prior_raw);typed_prior(n,plan_prior)
    prior=plan_prior;request=None;request_ref=None
    if args.worker:
        request_raw=raw(args.request,MIB);need(sha(request_raw)==args.request_sha256,"held request SHA")
        request=n.strict(request_raw);n.closed(request,("schema","plan","prior_work"),"worker request")
        need(request["schema"]=="m193c-saved-completion-request-v1" and same(request["plan"],plan_ref),"bound request plan")
        typed_prior(n,request["prior_work"])
        need(all(Decimal(str(request["prior_work"][k]))>=Decimal(str(plan_prior[k])) for k in ALLOWANCE),"request carry at least plan carry")
        prior=request["prior_work"];request_ref=dict(path=str(Path(args.request).resolve()),**binding(request_raw))
    output.mkdir();b=budget_for(n,output,prior,args.worker);files=n.Files(b)
    result=dict(schema="m193c-sift-lightglue-saved-completion-worker-v1" if args.worker else "m193c-sift-lightglue-saved-completion-run-v1",
                implementation_version=VERSION,status="REFUSED",plan=plan_ref,request=request_ref,prior_work=prior,
                command=sys.orig_argv,commission_prefix=plan["commission_prefix"],old_run_status="REFUSED",original_commission_complete=False,
                prior_cpu_accounting_complete=False,cpu_accounting_complete=False,new_run_cpu_accounting_complete=False,
                accounting_scope="conservative audited prior charge; only this new run can have complete measured Job CPU",
                active_phase="authority",publication_control_summary=[],publication_control_prefixes=[],publication_controls=None,
                controls=[],fits=[],assembly=None,runtime_before=None,runtime_after=None,child=None,worker_result=None,
                counters=dict(images=0,extractions=0,normalizations=0,model_forwards=0,registrar_calls=0),saved_feature_checks=0,
                inference_observer_nonperturbation="UNTESTED_ONE_FORWARD",sources_unchanged=False,error=None,work=None,charged_path_extents=None)
    publisher=pub.Publisher(pub.Writer(b,output,"terminal"),dict(schema=result["schema"],implementation_version=VERSION,
        plan=plan_ref,request=request_ref,prior_work=prior,cpu_accounting_complete=False,new_run_cpu_accounting_complete=False,
        old_run_status="REFUSED",original_commission_complete=False,inference_observer_nonperturbation="UNTESTED_ONE_FORWARD"))
    old=audit=None
    try:
        files.verify(plan_ref,MIB,True);n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True)==Path(sys.executable).resolve(),"actual Python executable")
        old,audit,derived=authority(n,plan,files);need(derived==plan_prior,"same derived conservative prior")
        if args.worker:
            files.verify(request_ref,MIB,True);result["active_phase"]="publication-controls";observations=[]
            def progress(rows):
                result["publication_control_summary"]=[dict(id=row["id"],passed=row["passed"],error=row.get("error")) for row in rows]
                ref=write_json(pub,b,files,output/("publication-progress-"+str(len(rows))+".json"),
                               dict(schema="m193c-publication-progress-v1",ordinal=len(rows),row=rows[-1],earlier=result["publication_control_prefixes"].copy()),"publication")
                result["publication_control_prefixes"].append(ref)
            commissioned=pub.commission(b,output/"publication-controls",observations,progress)
            result["publication_controls"]=write_json(pub,b,files,output/"publication-control-result.json",dict(schema=commissioned["schema"],passed=commissioned["passed"],scope=commissioned["scope"],controls=result["publication_control_prefixes"]),"publication")
            result["runtime_before"]=write_json(pub,b,files,output/"runtime-before.json",runtime_presence(n,files,plan,old),"runtime")
            result["active_phase"]="saved-evidence"
            science(n,pub,plan,files,b,output,result,old,audit)
            result["runtime_after"]=write_json(pub,b,files,output/"runtime-after.json",runtime_presence(n,files,plan,old),"runtime")
            need(result["counters"]==dict(images=0,extractions=0,normalizations=0,model_forwards=0,registrar_calls=5) and
                 tuple(row["id"] for row in result["controls"])==CONTROL_IDS and all(row["passed"] is True for row in result["controls"]),
                 "exact completed private saved-data population")
        else:
            result["active_phase"]="request"
            request=dict(schema="m193c-saved-completion-request-v1",plan=plan_ref,prior_work=b.work())
            request_ref=write_json(pub,b,files,output/"request.json",request,"metadata");result["request"]=request_ref
            command=replace(plan["commands"]["worker"],args.sha256,request_ref["sha256"])
            need(command[command.index("--output")+1]==str(output/"worker") and command[command.index("--request")+1]==str(output/"request.json"),
                 "exact actual worker paths")
            # Precharge all fixed child publication slots: polling cannot observe every consumed staging path.
            for name in pub.NAMES:b.reserve(output/"worker"/name,64*KIB,"terminal",True)
            for group in ("normal","capacity","oversized","late-before-stdout","restored-placebo","stdout-after-escape","emergency-fallback"):
                for name in pub.NAMES:b.reserve(output/"worker/publication-controls"/group/name,4096,"publication",True)
            b.reserve(output/"worker.log",MIB,"log",True)
            process=loaded(HERE/"bounded-process.py",plan["source_bindings"][n.relative(HERE/"bounded-process.py")],"m193c_saved_process")
            api=selected(HARNESS,plan["source_bindings"][n.relative(HARNESS)],JOB_NAMES+JOB_SIGNATURES)
            env,removed=process.clean_environment()
            removed+=[key for key in env if key.upper().startswith("PYTHON")]
            env={key:value for key,value in env.items() if not key.upper().startswith("PYTHON")}
            env["CUDA_VISIBLE_DEVICES"]=""
            result["environment_removed"]=sorted(set(removed));result["active_phase"]="worker"
            limits=b.limits();b.complete=False
            observed=process.run(command,env,ROOT,output/"worker.log",api=api,check=b.check,**limits);result["child"]=observed
            account=observed.get("job_accounting")
            if type(account) is dict and n.integer(account.get("total_cpu_100ns")):
                b.child_cpu=account["total_cpu_100ns"]/1e7
                b.complete=observed.get("terminal_job_accounting") is True and account.get("active_processes")==0
            with b.terminal():
                result["child_observation"]=pub.Writer(b,output,"metadata").write(output/"child-observation.json",pub.encoded(observed),terminal=True)
                child_path=output/"worker/result.json"
                if child_path.exists():
                    child_ref=files.bind(child_path,64*KIB,True);result["worker_result"]=child_ref
                    child=read(files,child_ref)
                    # Authentic child ledger discloses consumed staging paths; fixed reservations were charged even on a prefix.
                    if child.get("charged_path_extents") is not None:
                        for name,size in child["charged_path_extents"].items():
                            path=(output/"worker"/name).resolve()
                            need(path.is_relative_to(output/"worker") and type(size) is int and 0<size<=MIB,"bounded child reservation ledger")
                            family=b.family(path);b.reserve(path,size,family,True)
                    result["worker_status"]=child.get("status");result["worker_active_phase"]=child.get("active_phase")
                    result["worker_control_summary"]=[dict(id=row["id"],passed=row["passed"]) for row in child.get("controls",[])]
            n.successful_process(observed,command)
            need(result["worker_result"] is not None and child["schema"]=="m193c-sift-lightglue-saved-completion-worker-v1" and
                 child["implementation_version"]==VERSION and child["status"]==COMPLETE and child["error"] is None and
                 child["sources_unchanged"] is True and child["new_run_cpu_accounting_complete"] is True and
                 same(child["plan"],plan_ref) and same(child["request"],request_ref) and child["command"]==command,
                 "actual complete saved-data worker")
            result["counters"]=child["counters"];result["saved_feature_checks"]=child["saved_feature_checks"]
            result["active_phase"]="complete"
        with b.terminal():
            files.recheck();b.check(True)
            if old:
                current=runtime_presence(n,files,plan,old)
                if args.worker:
                    after=read(files,result["runtime_after"])
                    need(current==after,"actual final runtime presence unchanged")
                else:
                    result["runtime_final"]=write_json(pub,b,files,output/"runtime-final.json",current,"runtime",terminal=True)
            result["sources_unchanged"]=True;result["new_run_cpu_accounting_complete"]=b.complete
            need(b.complete,"new process accounting complete");result["status"]=COMPLETE
    except BaseException:
        result["error"]=dict(type=sys.exc_info()[0].__name__,traceback=traceback.format_exc())
        result["status"]="REFUSED"
    with b.terminal():
        try:
            b.check(True);result["new_run_cpu_accounting_complete"]=b.complete
            result["work"]=dict(conservative_global_work=b.work(),new_charged_extent_bytes=sum(b.extents.values()),
                                local_caps=CAPS,new_run_cpu_accounting_complete=b.complete,prior_cpu_accounting_complete=False,
                                extent_scope="monotone reserved path maxima including fixed padded slots/log ceiling; not current physical inventory")
            result["charged_path_extents"]={Path(path).relative_to(output).as_posix():size for path,size in sorted(b.extents.items())}
        except BaseException:
            result["status"]="REFUSED";result["accounting_finalization_error"]=traceback.format_exc()
        def emit(receipt):
            value=dict(status=result["status"],result=receipt,new_run_cpu_accounting_complete=b.complete,cpu_accounting_complete=False,
                       conservative_work_through_publication=b.work(),scope="prior CPU is conservatively charged, not measured complete")
            sys.stdout.write(json.dumps(value,allow_nan=False)+"\n");sys.stdout.flush()
        publication=publisher.publish(result,late=lambda:b.check(True,terminal=True),emit=emit,after=lambda:b.check(True,terminal=True))
        if not publication["passed"]:
            # A stdout line may already have escaped. Canonical refusal plus outer/audit governs admission.
            sys.stderr.write(json.dumps(dict(status="REFUSED" if publication.get("canonical_refusal_verified") is True else "REFUSAL_PUBLICATION_UNVERIFIED",publication=publication),allow_nan=False)+"\n");sys.stderr.flush()
            return 1
        need(publication["canonical"] is not None,"sealed positive receipt")
        return 0

if __name__=="__main__":raise SystemExit(run_main())
