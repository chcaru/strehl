"""Fixed saved-feature LightGlue real-pair diagnostic. SOURCE-ONLY until exact release."""
import time
START=time.monotonic()
import argparse
import ast
from contextlib import contextmanager
import ctypes
import ctypes.wintypes as wt
from decimal import Decimal,ROUND_CEILING
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback
import types

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
SPEC=HERE/"sift-lightglue-real-preregister.md"
MIB=1<<20;KIB=1024
VERSION="m193c-sift-lightglue-real-v1";COMPLETE="COMPLETE_FIXED_REAL_LIGHTGLUE_DIAGNOSTIC_ONLY"
CONTROL_IDS=("private-off","private-on","private-placebo","inference-observer","two-native-map-destroyer","within-split-association-destroyer","private-restored","final-state-restored")
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
CAPS=dict(cpu_seconds=100,wall_seconds=180,file_bytes=8*MIB,metadata_bytes=8*MIB)
COUNTS=(487,1024,1024,1024,1024,1024,1024,910,734)
PAIRS=((0,1),(0,2),(0,4),(0,5),(1,2),(1,3),(1,5),(2,3),(2,4),(2,5),(2,6),(3,4),
       (3,5),(3,7),(4,5),(4,6),(4,8),(5,6),(5,7),(5,8),(6,7),(6,8),(7,8))
FAMILIES=dict(normalized=4236800,predictions=777600,rows=401408,fits=114688,runtime=131072,
              metadata=589824,log=MIB,terminal=512*KIB,publication=256*KIB)
# Metadata has independent subfamily ceilings; all byte totals are asserted before work.
META=dict(codec=204*KIB,inputs=64*KIB,state=64*KIB,manifest=208*KIB,controls=24*KIB,controller=12*KIB)
PIN_HELPER=dict(bytes=44413,sha256="12e3a81fb7dea313375f8227483b2303269c85357246d041a27ccd7d1033df27")
PIN_PUBLISHER=dict(bytes=12343,sha256="875dfb30db4555c1906adec9e446ea7f91763493f0d23f66430d0143b8953f30")
QUALIFIER=dict(scope="REAL_PAIR_DIAGNOSTIC_ONLY",coordinate_gauge="native Q8=8*coarse Q8+896",
    native_coordinate_lattice_step_q8=8,inherited_coordinate_quantization_guard_q8=1,
    support_guard_qualification="UNQUALIFIED",support_or_overlap_admission=False,placement_or_merge_admission=False,
    fit_rms_failure_direction="coherent wrong correspondences can fit tightly; real physical truth is unavailable",
    heldout_scope="geometric fit holdout after whole-pair learned assignment; not independent learned-model generalization")

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def raw(path,cap=4*MIB):
    with Path(path).open("rb") as f:value=f.read(cap+1)
    need(0<len(value)<=cap,"bounded nonempty read");return value
def pin(data):return dict(bytes=len(data),sha256=sha(data))
def path_of(ref):return (ROOT/ref["path"]).resolve()
def same(a,b):return path_of(a)==path_of(b) and all(a[k]==b[k] for k in ("bytes","sha256"))
def instantiate(path,expected,name):
    data=raw(path);need(pin(data)==expected,"exact helper source")
    module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
    exec(compile(data,str(path),"exec"),module.__dict__);return module
def command(argv,plan,request=None):
    return [plan if x=="ACTUAL_PLAN_SHA256" else request if x=="ACTUAL_REQUEST_SHA256" else x for x in argv]

def setup(args):
    c=instantiate(HERE/"sift-lightglue-saved-completion-run.py",PIN_HELPER,"m193c_real_saved_helpers")
    utility=HERE/"native-derivative-run.py";data=raw(utility)
    need(sha(data)==c.PINS[utility.name],"immutable reader source")
    n=instantiate(utility,pin(data),"m193c_real_reader")
    data=raw(args.plan);need(sha(data)==args.sha256,"actual plan SHA")
    plan=n.strict(data);n.closed(plan,"schema source_bindings private_baseline prior_work preparation_allowance python_executable commands".split(),"real plan")
    need(plan["schema"]=="m193c-sift-lightglue-real-plan-v1" and plan["preparation_allowance"]==ALLOWANCE,"plan version/allowance")
    expected=[SELF,SPEC,HERE/"sift-lightglue-real-codec.py",HERE/"sift-lightglue-saved-completion-run.py",
              HERE/"saved-completion-publication.py",c.REFERENCE,c.HARNESS,*[HERE/x for x in c.PINS if x!="reference.py"]]
    for path in expected:
        expected_pin=plan["source_bindings"][n.relative(path)]
        need(pin(raw(path))==expected_pin and (path.name not in c.PINS or expected_pin["sha256"]==c.PINS[path.name]),"entire source closure")
    need(plan["source_bindings"][n.relative(HERE/"sift-lightglue-saved-completion-run.py")]==PIN_HELPER and
         plan["source_bindings"][n.relative(HERE/"saved-completion-publication.py")]==PIN_PUBLISHER,"immutable published helper")
    output=Path(args.output).resolve()
    need(Path.cwd().resolve()==ROOT and output.is_relative_to(HERE) and not output.exists(),"owned fresh output/cwd")
    need(sys.dont_write_bytecode and set(sys._xoptions)=={"faulthandler","pycache_prefix"} and sys._xoptions["faulthandler"] is True,"exact Python options")
    cache=Path(sys._xoptions["pycache_prefix"]).resolve()
    need(not cache.exists() and cache.is_relative_to(output.parent if args.worker else output),"fresh owned cache")
    n.closed(plan["commands"],("parent","worker"),"commands")
    need(command(plan["commands"]["worker" if args.worker else "parent"],args.sha256,args.request_sha256)==sys.orig_argv,"actual exact command")
    pub=instantiate(HERE/"saved-completion-publication.py",PIN_PUBLISHER,"m193c_real_publication")
    codec=instantiate(HERE/"sift-lightglue-real-codec.py",plan["source_bindings"][n.relative(HERE/"sift-lightglue-real-codec.py")],"m193c_real_codec")
    return c,n,pub,codec,plan,output,dict(path=str(Path(args.plan).resolve()),**pin(data))

def budget_for(n,output,prior,worker):
    need(sum(META.values())==FAMILIES["metadata"] and sum(FAMILIES.values())==8086400,"complete integer output ledger")
    class Budget(n.Budget):
        def __init__(self):
            super().__init__(output,prior,START,0.0)
            self.complete=True;self.terminal_mode=False;self.quotas=[];self.overrides={}
        def family(self,path):
            relative=Path(path).relative_to(self.output);parts=relative.parts
            if parts[0]=="worker":parts=parts[1:]
            if parts[0]=="publication-controls" or parts[-1].startswith("publication-"):return "publication"
            if parts[-1] in ("result.json","first-publication.json","publication-stage.json","emergency-refusal.json"):return "terminal"
            if parts[-1]=="worker.log":return "log"
            if parts[0] in FAMILIES:return parts[0]
            return "metadata"
        def totals(self):
            totals={k:0 for k in FAMILIES}
            for path,size in self.extents.items():totals[self.overrides.get(path,self.family(path))]+=size
            return totals
        def check(self,force=False,terminal=None):
            terminal=self.terminal_mode if terminal is None else terminal
            super().check(force);work=self.work()
            need(all(work[k]-self.prior[k]<=value for k,value in CAPS.items()),"local cap")
            need(all(self.totals()[k]<=value for k,value in FAMILIES.items()),"reserved family cap")
            if not terminal:
                cpu,wall=(2,3) if worker else (4,6)
                need(work["cpu_seconds"]<=1200-cpu and work["cpu_seconds"]-self.prior["cpu_seconds"]<=100-cpu,"publication CPU reserve")
                need(work["wall_seconds"]<=1800-wall and work["wall_seconds"]-self.prior["wall_seconds"]<=180-wall,"publication wall reserve")
                if worker:need(time.monotonic()-START<=147,"worker soft wall")
        def reserve(self,path,size,family,terminal):
            path=Path(path).resolve();need(path.is_relative_to(self.output) and family in FAMILIES and type(size) is int and size>0,"owned positive reservation")
            self.check(True,terminal=terminal);before=self.extents.get(str(path),0);growth=max(0,size-before)
            if not terminal:
                for root,limit,start in self.quotas:
                    if path.is_relative_to(root):need(sum(v for p,v in self.extents.items() if Path(p).is_relative_to(root))-start+growth<=limit,"ordinary quota capacity")
            need(self.totals()[family]+growth<=FAMILIES[family],"prewrite family capacity")
            if family=="metadata":
                rel=path.relative_to(self.output);parts=rel.parts[1:] if rel.parts[0]=="worker" else rel.parts
                sub=parts[1] if parts[0]=="metadata" and len(parts)>2 else "controller"
                need(sub in META,"declared metadata subfamily")
                def subgroup(p):
                    q=Path(p).relative_to(self.output).parts;q=q[1:] if q[0]=="worker" else q
                    return q[1] if q[0]=="metadata" and len(q)>2 else "controller"
                used=sum(v for p,v in self.extents.items() if self.overrides.get(p,self.family(p))=="metadata" and subgroup(p)==sub)
                need(used+growth<=META[sub],"metadata subfamily capacity")
            work=self.work()
            need(work["file_bytes"]+growth<=4<<30 and work["metadata_bytes"]+growth<=128*MIB and
                 sum(self.extents.values())+growth<=8*MIB,"prewrite global/local extent")
            self.overrides[str(path)]=family;self.extents[str(path)]=max(before,size)
        @contextmanager
        def terminal(self):
            previous=self.terminal_mode;self.terminal_mode=True
            try:yield
            finally:self.terminal_mode=previous
        @contextmanager
        def quota(self,root,limit):
            root=Path(root).resolve();start=sum(v for p,v in self.extents.items() if Path(p).is_relative_to(root))
            self.quotas.append((root,limit,start))
            try:yield
            finally:self.quotas.pop()
        def limits(self):
            self.check(True);work=self.work()
            wall=min(150,180-(work["wall_seconds"]-self.prior["wall_seconds"])-18,1800-work["wall_seconds"]-18)
            cpu=min(100-(work["cpu_seconds"]-self.prior["cpu_seconds"])-4,1200-work["cpu_seconds"]-4)
            need(wall>3 and cpu>2,"separate12s cleanup plus6s parent publication")
            return dict(cpu_seconds=cpu,wall_seconds=wall,log_bytes=MIB,committed_bytes=8<<30)
    return Budget()

def authority(c,n,plan,files):
    bundles=plan["private_baseline"];n.closed(bundles,("commission_prefix","saved_completion"),"two prerequisite bundles")
    prefix=bundles["commission_prefix"];done=bundles["saved_completion"]
    n.closed(prefix,("plan","worker_result","outer","console","exit","audit"),"prefix refs")
    n.closed(done,("plan","result","outer","console","exit","audit"),"completion refs")
    pa,old,pp=(c.read(files,prefix[k]) for k in ("audit","worker_result","plan"))
    need(pa["schema"]=="m193c-saved-sift-lightglue-commission-prefix-audit-v3" and
         pa["status"]=="PASS_SAVED_SIFT_LIGHTGLUE_COMMISSION_PREFIX_AUDIT" and pa["saved_prefix_verified"] is True and
         all(pa[k] is False for k in ("subject_complete","admission_allowed","cpu_accounting_complete")),"saved prefix only, no old successful commission")
    need(set(pa["external"])==set(prefix)-{"audit"} and all(same(pa["external"][k],prefix[k]) for k in pa["external"]) and
         same(pa["worker_result"],prefix["worker_result"]),"prefix audited actual association")
    need(old["status"]=="REFUSED" and old["counters"]["registrar_calls"]==0 and old["counters"]["private_model_forwards"]==1 and
         old["counters"]["real_model_forwards"]==0 and old["inference_observer_nonperturbation"]=="UNTESTED_ONE_FORWARD" and
         len(old["exports"])==11,"fixed eligible failed prefix")
    need(pa["parent_result_missing"] is True and not Path(pa["parent_result_expected_path"]).exists(),"missing old parent retained")
    for key in ("outer","console","exit"):c.checked(files,prefix[key],MIB)
    da,dp,parent,outer=(c.read(files,done[k]) for k in ("audit","plan","result","outer"))
    need(da["schema"]=="m193c-saved-sift-lightglue-saved-completion-audit-v2" and
         da["status"]=="PASS_SAVED_PRIVATE_LIGHTGLUE_COMPLETION_OUTCOME_AUDIT" and da["audit_version"]=="v2-one-runtime-conjunct" and
         all(da[k] is True for k in ("subject_complete","combined_private_prerequisite_eligible","new_run_cpu_accounting_complete")) and
         all(da[k] is False for k in ("admission_allowed","cpu_accounting_complete","original_commission_complete")) and
         da["old_run_status"]=="REFUSED" and da["refused_control"] is None,"independently complete new private checks only")
    need(set(da["external"])==set(done)-{"audit"} and all(same(da["external"][k],done[k]) for k in da["external"]) and
         all(same(da["commission_prefix"][k],prefix[k]) and same(dp["commission_prefix"][k],prefix[k]) for k in prefix),
         "exact two-part private authority")
    child=c.read(files,da["worker_result"])
    need(same(parent["worker_result"],da["worker_result"]) and all(value["status"]==c.COMPLETE and
         value["new_run_cpu_accounting_complete"] is True and value["cpu_accounting_complete"] is False and
         value["sources_unchanged"] is True and value["error"] is None for value in (parent,child)),"complete private current process/accounting")
    need(child["counters"]==dict(images=0,extractions=0,normalizations=0,model_forwards=0,registrar_calls=5) and
         len(child["controls"])==5 and all(x["passed"] is True for x in child["controls"]) and
         len(child["publication_control_summary"])==7 and all(x["passed"] is True for x in child["publication_control_summary"]),"all declared prerequisite controls")
    need(outer["exit_code"]==0 and outer["plan_sha256"]==done["plan"]["sha256"] and
         outer["command"]==command(dp["commands"]["parent"],done["plan"]["sha256"]) and c.checked(files,done["exit"],64).strip()==b"0","actual completed outer")
    console=n.strict(c.checked(files,done["console"],MIB).splitlines()[-1])
    need(console["status"]==c.COMPLETE and same(console["result"],done["result"]),"actual successful canonical stdout")
    for previous in (pp,dp):
        need(all(plan["source_bindings"].get(k)==v for k,v in previous["source_bindings"].items()),"complete immutable historical source closure")
    prior=c.read(files,plan["prior_work"]);base=da["actual_final_work"]
    c.typed_prior(n,prior);c.typed_prior(n,base)
    need(Decimal(da["next_wall_seconds"])==Decimal(str(base["wall_seconds"])),"next wall exact charged carry")
    for key in ALLOWANCE:
        value=Decimal(str(base[key]))
        if key.endswith("seconds"):value=value.quantize(Decimal(".000001"),rounding=ROUND_CEILING)
        need(Decimal(str(prior[key]))==value+ALLOWANCE[key],"ceiling conservative CPU/wall plus exact preparation")
    need(all(prior[k]+CAPS[k]<=limit for k,limit in dict(cpu_seconds=1200,wall_seconds=1800,file_bytes=4<<30,metadata_bytes=128*MIB).items()),
         "entire fixed arm maximum affordable before launch")
    return old,pa,child,da,prior

def save(pub,b,files,root,relative,value,family="metadata",cap=64*KIB,binary=False,terminal=False):
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
    data=value if binary else (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    need(0<len(data)<=cap,"bounded concrete artifact "+relative)
    ref=pub.Writer(b,path.parent,family).write(path,data,terminal=terminal)
    files.verify(ref,cap,True);return ref

def runtime(c,n,a,files,plan,old,torch=None,np=None):
    prior=c.read(files,old["runtime_before"])
    registry={path_of(ref):(i,ref) for i,ref in enumerate(prior["files"])}
    empty={Path(ref["path"]).resolve():(i,ref) for i,ref in enumerate(prior["empty_runtime_files"])}
    source={ROOT/name:dict(path=name,**expected) for name,expected in plan["source_bindings"].items()}
    entries=[];paths=[];modules=[];native=[];settings={}
    if torch is None:
        actual=c.runtime_presence(n,files,plan,old)
        for entry in actual["entries"]:
            if "prior_runtime_index" in entry:
                index=entry["prior_runtime_index"];entries.append(["prior",index]);paths.append(path_of(prior["files"][index]))
            elif "local_source" in entry:
                entries.append(["source",entry["local_source"]]);paths.append((ROOT/entry["local_source"]).resolve())
            else:
                index=entry["empty_runtime_index"];entries.append(["empty",index]);paths.append(Path(prior["empty_runtime_files"][index]["path"]).resolve())
        modules=actual["python_modules"];native=actual["native_module_indices"]
        settings=dict(python_version=actual["python_version"],scope="actual stdlib-only parent")
    else:
        actual=a.runtime_snapshot(torch,np,n,files)
        keys=("torch_version","numpy_version","python_version","executable","metadata_distributions","num_threads",
              "num_interop_threads","default_dtype","cuda_initialized","deterministic_algorithms","float32_matmul_precision")
        need(all(actual[k]==prior[k] for k in keys) and actual["cuda_initialized"] is False,"exact held CPU learned runtime settings/distributions")
        identities={}
        for ref in actual["files"]:
            path=path_of(ref);identities[str(path)]=len(entries);paths.append(path)
            if path in source:
                need(same(ref,source[path]),"held current source runtime identity");entries.append(["source",n.relative(path)])
            else:
                need(path in registry and same(ref,registry[path][1]),"held imported learned/native binary identity")
                entries.append(["prior",registry[path][0]])
        for value in actual["empty_runtime_files"]:
            path=Path(value["path"]).resolve();need(path in empty and value==empty[path][1],"exact admitted empty runtime file")
            identities[str(path)]=len(entries);paths.append(path);entries.append(["empty",empty[path][0]])
        modules=[[x["name"],identities[x["path"]]] for x in actual["python_modules"]]
        native=sorted(identities[path] for path in actual["native_modules"]);settings={k:actual[k] for k in keys if k!="metadata_distributions"}
    prior_modules={(row["name"],Path(row["path"]).resolve()):i for i,row in enumerate(prior["python_modules"])}
    current_bindings=[[name,str(paths[index])] for name,index in modules]
    common=[];changed=[]
    for name,index in modules:
        key=(name,paths[index])
        if key in prior_modules:common.append(prior_modules[key])
        else:changed.append([name,index])
    locals_=[];codes=[]
    for kind,value in entries:
        if kind=="prior":codes.append(value+1)
        elif kind=="empty":codes.append("empty:"+str(value))
        else:locals_.append(value);codes.append(-len(locals_))
    need(len(set(common))==len(common) and len({name for name,index in modules})==len(modules),"complete unique module aliases")
    return dict(schema="m193c-real-indexed-runtime-presence-v1",prior_registry=old["runtime_before"],
        current_file_codes=codes,local_source_paths=locals_,
        code_layout="positive=1+prior.files index;negative=-(1+local_source_paths index);empty:N=prior.empty_runtime_files index",
        prior_python_module_indices=common,changed_python_bindings=changed,
        changed_binding_layout="[actual module name,current_file_codes index]; complete presence is prior indices plus changed",
        native_file_indices=native,python_bindings_canonical_sha256=sha(n.json_bytes(current_bindings)),
        native_bindings_canonical_sha256=sha(n.json_bytes([str(paths[i]) for i in native])),
        settings=settings,scope="complete actual aliases/presence, including additions/rebindings and absences; no excluded mismatch repair")

def science(c,n,pub,codec,plan,files,b,out,result,old,pa,private,da):
    get=lambda path:plan["source_bindings"][n.relative(path)]
    v=c.selected(c.REFERENCE,get(c.REFERENCE),c.PURE+c.CONSTANTS)
    d=c.selected(HERE/"direct-pair-run.py",get(HERE/"direct-pair-run.py"),("observe_pair","signature"))
    f=c.selected(HERE/"factor-eight-prototype.py",get(HERE/"factor-eight-prototype.py"),("corner_errors","literal_corner_pass"),dict(Q32=v.Q32))
    a=instantiate(HERE/"sift-lightglue-adapter.py",get(HERE/"sift-lightglue-adapter.py"),"m193c_real_adapter")
    v.match_features=lambda x,y:(_ for _ in ()).throw(ValueError("uninstalled saved rows"))
    datas=[];exports=[]
    for ordinal,ref in enumerate(old["exports"]):
        value,record=c.feature(n,files,ref);datas.append(value);exports.append(record)
        expected=1024 if ordinal<2 else COUNTS[ordinal-2]
        need(record["core"]["count"]==expected,"immutable independently admitted exact feature population")
    result["saved_feature_checks"]=11
    cached=c.output_values(n,files,old["learned_output"],1024,1024)
    cache_input=c.read(files,old["model_inputs"])
    normalized=c.read(files,old["normalized_private_descriptors"])
    baseline=c.read(files,private["fits"][0])
    need(baseline["schema"]=="m193c-saved-learned-fit-v1" and baseline["intrinsic"]["status"]=="RETURNED","audited actual private baseline")
    result["active_phase"]="codec-controls";blobs={}
    def artifact(name,header,payload):
        identity=sha(payload)
        if identity not in blobs:
            blobs[identity]=save(pub,b,files,out,"metadata/codec/blob-"+identity+".bin",payload,cap=32768,binary=True)
        return save(pub,b,files,out,"metadata/codec/"+name+".json",dict(header=header,payload=blobs[identity]),cap=4096)
    def codec_progress(rows):
        result["codec_controls"]=[dict(id=row["id"],passed=row["passed"]) for row in rows]
        save(pub,b,files,out,"metadata/codec/control-"+str(len(rows))+".json",rows[-1],cap=2048)
    codec.commission(cached,1024,1024,artifact,codec_progress)
    result["active_phase"]="offline-model-load";loading=dict(blocked_imports=[])
    # Both model construction and all inference execute inside the reviewed import/network guard.
    @contextmanager
    def guarded():
        try:
            with a.import_guard(loading):yield
        finally:
            with b.terminal():
                result["import_guard_final"]=save(pub,b,files,out,"metadata/state/import-guard-final.json",
                    dict(blocked_imports=loading.get("blocked_imports",[]),import_guard_restored=loading.get("import_guard_restored",False),
                         scope="actual context exit, including operational/scientific refusal"),cap=2048,terminal=True)
    with guarded():
        import numpy as np
        import torch
        acquisition=c.read(files,old["acquisition_receipt"]["result"])
        assets={row["id"]:dict(path=row["path"],bytes=row["bytes"],sha256=row["sha256"]) for row in acquisition["assets"]}
        need(set(assets)=={"matcher","rootsift_reference","license","readme","checkpoint"},"fixed offline acquisition assets")
        matcher=c.checked(files,assets["matcher"],MIB);sift=c.checked(files,assets["rootsift_reference"],MIB)
        checkpoint=files.verify(assets["checkpoint"],64*MIB,Path(assets["checkpoint"]["path"]).is_absolute())
        model,rootsift=a.load_model(torch,matcher,path_of(assets["matcher"]),sift,path_of(assets["rootsift_reference"]),checkpoint,loading)
        old_loading=old["model_loading"]
        need(all(key in old_loading and n.json_bytes(value)==n.json_bytes(old_loading[key]) for key,value in loading.items() if key!="blocked_imports"),
             "same complete original offline loader witness and settings")
        result["model_loading"]=save(pub,b,files,out,"metadata/state/model-loading.json",dict(
            prior_worker=plan["private_baseline"]["commission_prefix"]["worker_result"],prior_field="model_loading",
            actual_complete_loading_sha256=sha(n.json_bytes(loading)),compared_field_names=sorted(k for k in loading if k!="blocked_imports"),
            complete_parameter_coverage=loading["complete_parameter_coverage"],
            config=loading["config"],constructor_buffer=loading["constructor_buffer"],blocked_imports=loading.get("blocked_imports",[]),
            scope="every actual learned-load/configuration field equals held old witness; blocked-import activity and guard exit are retained separately; historical timings are not compared"),cap=8192)
        result["runtime_before"]=save(pub,b,files,out,"runtime/worker-before.json",runtime(c,n,a,files,plan,old,torch,np),"runtime",cap=60*KIB)
        def state():
            rows=[[name,str(tensor.dtype),list(tensor.shape),sha(tensor.detach().cpu().numpy().tobytes(order="C"))]
                  for name,tensor in sorted(model.state_dict().items())]
            need(all(tensor.device.type=="cpu" and tensor.dtype==torch.float32 for tensor in model.state_dict().values()),"complete CPU float32 state")
            return rows,sha(n.json_bytes(rows))
        initial,state_hash=state()
        result["state_registry"]=save(pub,b,files,out,"metadata/state/initial-registry.json",
            dict(schema="m193c-real-state-registry-v1",rows=initial,canonical_sha256=state_hash),cap=54*KIB)
        prepared=[];input_manifest=[]
        for ordinal,(data,record) in enumerate(zip(datas,exports,strict=True)):
            result["active_phase"]="input-"+str(ordinal)
            desc=np.frombuffer(b"".join(data["descriptors"]),dtype="u1").reshape(len(data["keys"]),128)
            attrs=a.attributes(np,data["keys"],data["coarse"],record["explicit_coarse_image_size"])
            need({key:a.array_witness(value) for key,value in attrs.items()}==record["attributes"],"actual exact quantized attributes")
            original_hash=sha(desc.tobytes());attribute_hash=sha(n.json_bytes({k:a.array_witness(x) for k,x in attrs.items()}))
            if ordinal<2:
                held=normalized["sides"][ordinal]
                need(same(held["source_export"],old["exports"][ordinal]) and held["dtype"]=="<f4" and held["shape"]==[1,1024,128],"admitted actual private tensor")
                payload=c.checked(files,held["file"],512*KIB)
                tensor=torch.from_numpy(np.frombuffer(payload,dtype="<f4").copy().reshape(1,1024,128))
                tensor_ref=held["file"]
            else:
                b.check(True);result["counters"]["normalizations"]+=1
                tensor=rootsift(torch.from_numpy(desc.copy()).float().unsqueeze(0))
                payload=tensor.detach().cpu().numpy().astype("<f4",copy=False).tobytes(order="C")
                need(len(payload)==COUNTS[ordinal-2]*128*4,"exact real normalized extent")
                tensor_ref=save(pub,b,files,out,"normalized/real-"+str(ordinal-2)+".f32",payload,"normalized",cap=512*KIB,binary=True)
            values={key:torch.from_numpy(value.copy()).unsqueeze(0) for key,value in attrs.items()}
            values["descriptors"]=tensor
            need(all(x.device.type=="cpu" and x.dtype==torch.float32 and bool(torch.isfinite(x).all()) for x in values.values()),"finite CPU float32 input")
            need(sha(desc.tobytes())==original_hash and attribute_hash==sha(n.json_bytes({k:a.array_witness(x) for k,x in attrs.items()})),"original descriptors/attributes unchanged")
            witness=a.tensor_witness(values)
            if ordinal<2:need(witness==cache_input["image"+str(ordinal)],"entire admitted actual private model-input bytes")
            prepared.append(values)
            input_manifest.append(dict(export=old["exports"][ordinal],normalization=tensor_ref,tensors=witness,
                provenance="REUSED_ADMITTED_ACTUAL_PRIVATE_FLOAT32" if ordinal<2 else "NEW_UPSTREAM_ROOTSIFT_ON_EXPORTED_U8_COPY",
                independent_normalization_requirement="all actual components within2^-15 of scalar-f64 normalization before scientific admission"))
        result["inputs"]=save(pub,b,files,out,"metadata/manifest/inputs.json",dict(schema="m193c-real-input-manifest-v1",rows=input_manifest),cap=16*KIB)
        def control(name,passed,evidence):
            row=dict(id=name,passed=bool(passed),evidence=evidence);result["controls"].append(dict(id=name,passed=bool(passed)))
            ref=save(pub,b,files,out,"metadata/controls/"+name+".json",row,cap=3*KIB);result["control_records"].append(ref)
            need(passed,"real private prerequisite "+name)
        def predict(i,j,name,mode,private_call):
            b.check(True);result["counters"]["model_forwards"]+=1
            need(result["counters"]["model_forwards"]<=26,"fixed26 forward maximum")
            inputs={side:{key:value.clone() for key,value in prepared[index].items()} for side,index in (("image0",i),("image1",j))}
            before={side:a.tensor_witness(value) for side,value in inputs.items()}
            immutable={side:input_manifest[index]["tensors"] for side,index in (("image0",i),("image1",j))}
            need(before==immutable,"fresh immutable actual inference inputs")
            start_cpu=time.process_time();start_wall=time.monotonic();observer=[]
            with torch.inference_mode():prediction=model(inputs)
            # This is the exact after-call observer seam used for private and every real call.
            if mode=="on":observer.append(a.output_record(torch,prediction,len(datas[i]["keys"]),len(datas[j]["keys"])))
            elif mode=="placebo":observer.append(tuple(prediction))
            else:need(mode=="off","fixed observer mode")
            record=a.output_record(torch,prediction,len(datas[i]["keys"]),len(datas[j]["keys"]))
            after={side:a.tensor_witness(value) for side,value in inputs.items()}
            current_immutable={side:a.tensor_witness(prepared[index]) for side,index in (("image0",i),("image1",j))}
            timing=dict(cpu_seconds=time.process_time()-start_cpu,wall_seconds=time.monotonic()-start_wall)
            hashes=lambda values:[[item["sha256"] for key,item in sorted(tensors.items())] for side,tensors in sorted(values.items())]
            obs=dict(mode=mode,called=len(observer),input_before=hashes(before),input_after=hashes(after),immutable_after_sha256=sha(n.json_bytes(current_immutable)),
                     full_tensor_shapes_and_types="inputs",tensor_order=sorted(prepared[0]),input_indices=[i,j],
                     intrinsic_sha256=sha(n.json_bytes(record)),timing=timing,
                     observer_scope="actual same after-call helper; no internal attention observer claim")
            if private_call:
                _,current_state=state();obs["state_sha256"]=current_state;obs["state_registry"]="state_registry"
            # Every actual intrinsic value is packed; real arm labels live outside the legacy private-format numeric witness.
            header,payload=codec.pack(record,len(datas[i]["keys"]),len(datas[j]["keys"]))
            blob=save(pub,b,files,out,"predictions/"+name+".bin",payload,"predictions",cap=32768,binary=True)
            manifest=save(pub,b,files,out,"metadata/manifest/"+name+"-prediction.json",
                dict(schema="m193c-real-prediction-v1",header=header,payload=blob,scope="PRIVATE_CONTROL" if private_call else "REAL_PAIR_DIAGNOSTIC_ONLY",
                     legacy_intrinsic_label_scope="frozen numeric serialization identity only; this outer scope describes current experiment",
                     qualification=QUALIFIER),cap=4096)
            witness=save(pub,b,files,out,"metadata/inputs/"+name+".json",obs,cap=2400)
            result["predictions"].append(dict(name=name,record=manifest,witness=witness))
            need(codec.canonical(codec.unpack(header,c.checked(files,blob,32768)))==codec.canonical(record),"actual saved prediction roundtrip")
            need(after==before==current_immutable and (not private_call or current_state==state_hash),"actual inference cannot mutate inputs/state")
            need((mode=="off" and not observer) or (mode!="off" and len(observer)==1),"actual observer/placebo invocation")
            if mode=="on":need(n.json_bytes(observer[0])==n.json_bytes(record),"observed actual output identity")
            b.check(True);return record
        def fit(matches,links,name,mode):
            b.check(True);result["counters"]["registrar_calls"]+=1
            need(result["counters"]["registrar_calls"]<=28,"fixed28 registrar maximum")
            outcome=a.registrar(v,d,matches,mode);intrinsic=d.signature(outcome);payload=[]
            for row,link in zip(outcome["landmarks"],links,strict=mode=="count"):
                need(row["reference_q8"]==link["reference_q8"] and row["source_q8"]==link["source_q8"] and row["digest"]==link["digest"],"unchanged actual saved associations")
                membership=0 if row["inlier"] is None else 2 if row["inlier"] else 1
                payload.append(struct.pack("<HHHBB4i32s",link["reference_feature_index"],link["source_feature_index"],link["learned_ordinal"],
                    int(row["split"]=="holdout"),membership,*row["reference_q8"],*row["source_q8"],bytes.fromhex(row["digest"])))
            blob=b"".join(payload)
            rowref=save(pub,b,files,out,"rows/"+name+".bin",blob,"rows",cap=256*56,binary=True) if blob else None
            compact=dict(schema="m193c-real-fit-v1",intrinsic=intrinsic,mode=mode,
                rows=dict(count=len(payload),file=rowref,row_bytes=56,empty_sha256=sha(b"") if not blob else None,
                          canonical_sha256=sha(n.json_bytes(outcome["landmarks"]))),
                supplied_count=len(links),supplied_canonical_sha256=sha(n.json_bytes(links)),
                radius_membership="0 unknown;1 outside;2 within returned-map2-native radius; not actual refinement subset",
                heldout_bbox_q8=outcome["heldout_bbox_q8"],qualification=QUALIFIER)
            ref=save(pub,b,files,out,"fits/"+name+".json",compact,"fits",cap=4096);result["fits"].append(ref)
            b.check(True);return outcome,ref
        private_records=[];private_outcomes=[];positive_links=None;positive_matches=None
        for mode,fitmode in (("off","off"),("on","count"),("placebo","placebo")):
            result["active_phase"]="private-"+mode;record=predict(0,1,"private-"+mode,mode,True)
            matches,links=a.assemble(v,datas[0],datas[1],record["output"]["matches"],record["output"]["scores"])
            outcome,ref=fit(matches,links,"private-"+mode,fitmode)
            uncapped=a.truth_rows([dict(reference_q8=datas[0]["native"][i],source_q8=datas[1]["native"][j]) for i,j in record["output"]["matches"]])
            capped=a.truth_rows(links)
            truth=lambda x:{k:value for k,value in x.items() if k!="rows"}
            eq=c.compare(n,"whole-intrinsic-model",cached,record)
            fit_eq=c.compare(n,"complete-intrinsic-registrar",baseline["intrinsic"],d.signature(outcome))
            control("private-"+mode,eq["equal"] and fit_eq["equal"] and uncapped["passes"] and capped["passes"] and
                outcome["status"]=="RETURNED" and f.literal_corner_pass(outcome["transform"]),
                dict(model=eq,registrar=fit_eq,fit=ref,uncapped_truth=truth(uncapped),capped_truth=truth(capped),
                     corners=[] if outcome["transform"] is None else f.corner_errors(outcome["transform"]),population_relation="UNCAPPED_AND_HASH_CAPPED" if len(links)<len(record["output"]["matches"]) else "SAME_ROWS"))
            private_records.append(record);private_outcomes.append(outcome)
            if mode=="on":positive_links=links;positive_matches=matches
        control("inference-observer",all(n.json_bytes(record)==n.json_bytes(cached) for record in private_records) and
                len(private_records[1]["output"]["matches"])>0,
                dict(intrinsic_sha256=[sha(n.json_bytes(x)) for x in private_records],scope="PASS_THREE_PRIVATE_FORWARDS_AFTER_CALL_SCOPE"))
        shifted=dict(private_outcomes[1]["transform"]);shifted["tx"]+=2*(1<<32)
        control("two-native-map-destroyer",not f.literal_corner_pass(shifted),dict(transform=shifted,corners=f.corner_errors(shifted),qualification=QUALIFIER))
        result["active_phase"]="private-association-destroyer";permutation=list(range(len(positive_matches)))
        for split in (0,1):
            indices=list(range(split,len(positive_matches),2))
            ranked=sorted(indices,key=lambda i:sha(b"M193C-LG-ASSOCIATION-FAULT\0"+positive_matches[i].digest))
            for i,j in zip(indices,ranked,strict=True):permutation[i]=j
        faults=[v.Match(m.reference_x_q8,m.reference_y_q8,positive_matches[permutation[i]].source_x_q8,
                        positive_matches[permutation[i]].source_y_q8,m.digest) for i,m in enumerate(positive_matches)]
        faultlinks=[dict(row,source_q8=positive_links[permutation[i]]["source_q8"],
                        source_feature_index=positive_links[permutation[i]]["source_feature_index"]) for i,row in enumerate(positive_links)]
        bad,badref=fit(faults,faultlinks,"private-fault","count")
        control("within-split-association-destroyer",
            any(a["source_q8"]!=z["source_q8"] for a,z in zip(positive_links,faultlinks,strict=True)) and
            not a.truth_rows(faultlinks)["passes"] and (bad["status"]!="RETURNED" or not f.literal_corner_pass(bad["transform"])),
            dict(permutation=permutation,fit=badref,scope="labelled metadata fault preserves original digest/split; no new inference"))
        result["active_phase"]="private-restored";restored,ref=fit(positive_matches,positive_links,"private-restored","count")
        eq=c.compare(n,"entire-restored-actual-outcome",private_outcomes[1],restored)
        control("private-restored",eq["equal"] and d.signature(restored)==baseline["intrinsic"] and f.literal_corner_pass(restored["transform"]),dict(comparison=eq,fit=ref))
        need(result["counters"]["model_forwards"]==3 and result["counters"]["registrar_calls"]==5,"fixed private population")
        result["inference_observer_nonperturbation"]="PASS_THREE_PRIVATE_FORWARDS_AFTER_CALL_SCOPE"
        for ordinal,(lo,hi) in enumerate(PAIRS):
            reference,source=(5,lo if hi==5 else hi) if 5 in (lo,hi) else (lo,hi)
            name="real-"+str(lo)+"-"+str(hi);result["active_phase"]=name
            row=dict(ordinal=ordinal,ids=[lo,hi],reference=reference,source=source,reference_original=reference*13,source_original=source*13,
                     stage="MODEL_ATTEMPTED",prediction=None,fit=None,status=None)
            result["pairs"].append(row);result["unvisited"]=[list(pair) for pair in PAIRS[ordinal+1:]]
            record=predict(reference+2,source+2,name,"on",False);row["prediction"]=result["predictions"][-1]["record"];row["stage"]="FIT_ATTEMPTED"
            matches,links=a.assemble(v,datas[reference+2],datas[source+2],record["output"]["matches"],record["output"]["scores"])
            outcome,ref=fit(matches,links,name,"count");row.update(fit=ref,status=outcome["status"],stage="OBSERVED",
                uncapped_matches=len(record["output"]["matches"]),capped_matches=len(matches))
            need(outcome["status"] in ("RETURNED","REGISTRATION_REFUSED"),"scientific status including zero-row refusal")
            save(pub,b,files,out,"metadata/manifest/"+name+"-observation.json",row,cap=1024)
        _,final_state=state()
        control("final-state-restored",final_state==state_hash,dict(initial_sha256=state_hash,final_sha256=final_state,registry=result["state_registry"]))
        result["runtime_after"]=save(pub,b,files,out,"runtime/worker-after.json",runtime(c,n,a,files,plan,old,torch,np),"runtime",cap=60*KIB)
        a.check_empty_runtime(n)
        need(result["counters"]==dict(images=0,extractions=0,normalizations=9,model_forwards=26,registrar_calls=28) and
             tuple(row["id"] for row in result["controls"])==CONTROL_IDS and all(row["passed"] for row in result["controls"]),"exact completed real population and eight controls")
        returned=[(row["reference"],row["source"]) for row in result["pairs"] if row["status"]=="RETURNED"]
        def component(start,exclude=None):
            seen={start};todo=[start]
            while todo:
                node=todo.pop()
                for edge in returned:
                    if edge==exclude or node not in edge:continue
                    other=edge[1] if node==edge[0] else edge[0]
                    if other not in seen:seen.add(other);todo.append(other)
            return sorted(seen)
        bridges=[list(edge) for edge in returned if edge[1] not in component(edge[0],edge)]
        result["graph"]=dict(edges=[list(x) for x in returned],bridges=bridges,components=[component(i) for i in range(9)],
            anchor_local=4,cycle_rank=len(returned)-9+len({tuple(component(i)) for i in range(9)}),qualification=QUALIFIER)
        result["development_outcome"]="ZERO_OF_23_REFUTES_FIXED_DIAGNOSTIC_FIT_ARM" if not returned else "DIAGNOSTIC_FIT_FEASIBILITY_ONLY_PHYSICAL_TRUTH_UNMEASURED"
        result["active_phase"]="complete"

def main():
    parser=argparse.ArgumentParser()
    for key in ("plan","sha256","output"):parser.add_argument("--"+key,required=True)
    parser.add_argument("--worker",action="store_true");parser.add_argument("--request");parser.add_argument("--request-sha256")
    args=parser.parse_args();need(args.worker==(args.request is not None and args.request_sha256 is not None),"worker-only request")
    c,n,pub,codec,plan,output,plan_ref=setup(args)
    prior_bytes=raw(path_of(plan["prior_work"]),MIB)
    need(pin(prior_bytes)=={k:plan["prior_work"][k] for k in ("bytes","sha256")},"exact prior file")
    planned=n.strict(prior_bytes);c.typed_prior(n,planned);prior=planned;request_ref=None
    if args.worker:
        request_bytes=raw(args.request,MIB);need(sha(request_bytes)==args.request_sha256,"actual request digest")
        request=n.strict(request_bytes);n.closed(request,("schema","plan","prior_work"),"worker request")
        need(request["schema"]=="m193c-real-lightglue-request-v1" and same(request["plan"],plan_ref),"actual request plan")
        c.typed_prior(n,request["prior_work"])
        need(all(Decimal(str(request["prior_work"][k]))>=Decimal(str(planned[k])) for k in ALLOWANCE),"monotone request carry")
        prior=request["prior_work"];request_ref=dict(path=str(Path(args.request).resolve()),**pin(request_bytes))
    output.mkdir();b=budget_for(n,output,prior,args.worker);files=n.Files(b)
    result=dict(schema="m193c-sift-lightglue-real-worker-v1" if args.worker else "m193c-sift-lightglue-real-run-v1",
        implementation_version=VERSION,status="REFUSED",plan=plan_ref,request=request_ref,command=sys.orig_argv,prior_work=prior,
        private_baseline=plan["private_baseline"],old_run_status="REFUSED",original_commission_complete=False,
        cpu_accounting_complete=False,new_run_cpu_accounting_complete=False,sources_unchanged=False,
        counters=dict(images=0,extractions=0,normalizations=0,model_forwards=0,registrar_calls=0),
        active_phase="authority",controls=[],control_records=[],codec_controls=[],publication_controls=None,
        publication_control_prefixes=[],publication_control_summary=[],pairs=[],predictions=[],fits=[],
        unvisited=[list(x) for x in PAIRS],runtime_before=None,runtime_after=None,saved_feature_checks=0,
        inference_observer_nonperturbation="UNTESTED_CURRENT_PROCESS",qualification=QUALIFIER,error=None,worker_result=None)
    publisher=pub.Publisher(pub.Writer(b,output,"terminal"),dict(schema=result["schema"],implementation_version=VERSION,plan=plan_ref,
        request=request_ref,prior_work=prior,cpu_accounting_complete=False,new_run_cpu_accounting_complete=False,
        old_run_status="REFUSED",original_commission_complete=False,qualification=QUALIFIER))
    old=None
    try:
        files.verify(plan_ref,MIB,True);n.binding_map(plan["source_bindings"],files)
        need(files.verify(plan["python_executable"],MIB,True)==Path(sys.executable).resolve(),"same held Python")
        old,pa,private,da,derived=authority(c,n,plan,files);need(derived==planned,"actual derived prior agrees")
        if args.worker:
            files.verify(request_ref,MIB,True);result["active_phase"]="publication-controls";observations=[]
            def progress(rows):
                result["publication_control_summary"]=[dict(id=row["id"],passed=row["passed"],error=row.get("error")) for row in rows]
                ref=save(pub,b,files,output,"publication-progress-"+str(len(rows))+".json",
                    dict(schema="m193c-publication-progress-v1",ordinal=len(rows),row=rows[-1],earlier=result["publication_control_prefixes"].copy()),
                    "publication",cap=24*KIB)
                result["publication_control_prefixes"].append(ref)
            controls=pub.commission(b,output/"publication-controls",observations,progress)
            result["publication_controls"]=save(pub,b,files,output,"publication-control-result.json",
                dict(schema=controls["schema"],passed=controls["passed"],scope=controls["scope"],controls=result["publication_control_prefixes"]),"publication",cap=8192)
            science(c,n,pub,codec,plan,files,b,output,result,old,pa,private,da)
            need(c.read(files,result["import_guard_final"])["import_guard_restored"] is True,"actual final import guard restored")
        else:
            result["active_phase"]="request"
            request=dict(schema="m193c-real-lightglue-request-v1",plan=plan_ref,prior_work=b.work())
            request_ref=save(pub,b,files,output,"request.json",request,cap=2048);result["request"]=request_ref
            argv=command(plan["commands"]["worker"],args.sha256,request_ref["sha256"])
            need(argv[argv.index("--output")+1]==str(output/"worker") and argv[argv.index("--request")+1]==str(output/"request.json"),"actual fixed worker paths")
            for name in pub.NAMES:b.reserve(output/"worker"/name,64*KIB,"terminal",True)
            for group in ("normal","capacity","oversized","late-before-stdout","restored-placebo","stdout-after-escape","emergency-fallback"):
                for name in pub.NAMES:b.reserve(output/"worker/publication-controls"/group/name,4096,"publication",True)
            b.reserve(output/"worker.log",MIB,"log",True)
            process=instantiate(HERE/"bounded-process.py",plan["source_bindings"][n.relative(HERE/"bounded-process.py")],"m193c_real_process")
            api=c.selected(c.HARNESS,plan["source_bindings"][n.relative(c.HARNESS)],c.JOB_NAMES+c.JOB_SIGNATURES)
            env,removed=process.clean_environment();removed+=[k for k in env if k.upper().startswith("PYTHON")]
            env={k:value for k,value in env.items() if not k.upper().startswith("PYTHON")};env["CUDA_VISIBLE_DEVICES"]=""
            result["environment_removed"]=sorted(set(removed));result["active_phase"]="worker"
            limits=b.limits();b.complete=False
            observed=process.run(argv,env,ROOT,output/"worker.log",api=api,check=b.check,**limits)
            account=observed.get("job_accounting")
            if type(account) is dict and n.integer(account.get("total_cpu_100ns")):
                b.child_cpu=account["total_cpu_100ns"]/1e7;b.complete=observed.get("terminal_job_accounting") is True and account.get("active_processes")==0
            with b.terminal():
                result["child_observation"]=save(pub,b,files,output,"child-observation.json",observed,cap=8192,terminal=True)
                child_path=output/"worker/result.json"
                if child_path.exists():
                    result["worker_result"]=files.bind(child_path,64*KIB,True);child=c.read(files,result["worker_result"])
                    for name,size in (child.get("charged_path_extents") or {}).items():
                        path=(output/"worker"/name).resolve()
                        need(path.is_relative_to(output/"worker") and type(size) is int and 0<size<=MIB,"authentic bounded child consumed-path ledger")
                        b.reserve(path,size,b.family(path),True)
                    result["worker_status"]=child.get("status");result["worker_active_phase"]=child.get("active_phase")
            n.successful_process(observed,argv)
            need(result["worker_result"] is not None and child["schema"]=="m193c-sift-lightglue-real-worker-v1" and
                child["implementation_version"]==VERSION and child["status"]==COMPLETE and child["error"] is None and
                child["new_run_cpu_accounting_complete"] is True and child["sources_unchanged"] is True and
                same(child["plan"],plan_ref) and same(child["request"],request_ref) and child["command"]==argv,"actual completed fixed worker")
            for key in ("counters","saved_feature_checks","inference_observer_nonperturbation","development_outcome"):
                result[key]=child[key]
            result["unvisited"]=[];result["active_phase"]="complete"
        with b.terminal():
            files.recheck();b.check(True)
            if not args.worker and old:
                result["runtime_final"]=save(pub,b,files,output,"runtime/parent-final.json",runtime(c,n,None,files,plan,old),
                    "runtime",cap=8*KIB,terminal=True)
            need(b.complete,"new run complete measured accounting")
            result["sources_unchanged"]=True;result["new_run_cpu_accounting_complete"]=True;result["status"]=COMPLETE
    except BaseException:
        result["status"]="REFUSED";result["error"]=dict(type=sys.exc_info()[0].__name__,traceback=traceback.format_exc())
    with b.terminal():
        try:
            # Population records remain available on every operational prefix without bloating terminal slots.
            if args.worker:
                population={key:result[key] for key in ("pairs","predictions","fits","unvisited","controls","control_records","codec_controls")}
                result["population"]=save(pub,b,files,output,"metadata/manifest/population.json",population,cap=48*KIB,terminal=True)
                for key in ("pairs","predictions","fits","control_records"):result[key]=dict(count=len(result[key]),record=result["population"])
            b.check(True);result["new_run_cpu_accounting_complete"]=b.complete
            result["work"]=dict(conservative_global_work=b.work(),new_charged_extent_bytes=sum(b.extents.values()),local_caps=CAPS,
                family_limits=FAMILIES,metadata_subfamily_limits=META,new_run_cpu_accounting_complete=b.complete,
                prior_cpu_accounting_complete=False,extent_scope="monotone reserved path maxima; actual inventory is separate")
            result["charged_path_extents"]={Path(path).relative_to(output).as_posix():size for path,size in sorted(b.extents.items())}
        except BaseException:
            result["status"]="REFUSED";result["accounting_finalization_error"]=traceback.format_exc()
        def emit(receipt):
            sys.stdout.write(json.dumps(dict(status=result["status"],result=receipt,cpu_accounting_complete=False,
                new_run_cpu_accounting_complete=b.complete,conservative_work_through_publication=b.work()),allow_nan=False)+"\n");sys.stdout.flush()
        published=publisher.publish(result,late=lambda:b.check(True,terminal=True),emit=emit,after=lambda:b.check(True,terminal=True))
        if not published["passed"]:
            sys.stderr.write(json.dumps(dict(status="REFUSED" if published.get("canonical_refusal_verified") is True else "REFUSAL_PUBLICATION_UNVERIFIED",
                publication=published),allow_nan=False)+"\n");sys.stderr.flush();return 1
        return 0

if __name__=="__main__":raise SystemExit(main())
