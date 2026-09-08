"""Owned adapters for one offline SIFT-input LightGlue commission. No numerical imports on import."""
import ast
from collections import OrderedDict
from contextlib import contextmanager
import hashlib
import importlib.abc
from importlib import metadata
import math
import os
from pathlib import Path
import struct
import sys
import types

MIB=1<<20
PROVENANCE="QUANTIZED_KEY_DERIVED_ATTRIBUTES"
CONF=dict(input_dim=128,descriptor_dim=256,add_scale_ori=True,n_layers=9,num_heads=4,
          flash=False,mp=False,depth_confidence=-1,width_confidence=-1,filter_threshold=0.1,weights=None)
QUALIFIER=dict(coordinate_gauge="native pixel centres; q_native=8*q_coarse+896",
    coordinate_lattice_step_q8=8,inherited_quantization_guard_q8=1,guard_status="UNQUALIFIED_FOR_COARSE_LATTICE",
    scope="Private compatibility/known geometry only; no real model pairs, support, overlap, placement or quality admission")


def need(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def core(n,feature,coarse_coordinates):
    return dict(count=len(feature.keys),coarse_coordinates_q8=coarse_coordinates.tolist(),
        native_coordinates_q8=feature.coordinates_q8.tolist(),
        descriptors_sha256=sha(feature.descriptors.astype("<i2").tobytes()),
        keys_sha256=sha(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in feature.keys])))


def payloads(np,feature):
    need(feature.descriptors.dtype==np.dtype("int16") and feature.descriptors.shape==(len(feature.keys),128)
         and bool(np.all((feature.descriptors>=0)&(feature.descriptors<=255))),"lossless descriptor-byte export")
    keys=np.asarray([k[:-1] for k in feature.keys],dtype="<i8")
    need(keys.shape==(len(feature.keys),7),"seven original integer key fields")
    desc=feature.descriptors.astype("u1").tobytes()
    need(all(desc[i*128:(i+1)*128]==k[-1] for i,k in enumerate(feature.keys)),"descriptor/key row association")
    return desc,keys.tobytes()


def attributes(np,keys,coarse,size):
    # Evaluate in binary64 in the displayed order, then round each element once to float32.
    scales=np.asarray([int(k[3])/256 for k in keys],dtype="<f4")
    oris=np.asarray([(int(k[4])/256)*math.pi/180 for k in keys],dtype="<f4")
    return dict(keypoints=np.asarray(coarse,dtype="<f4")/np.float32(256),
        scales=scales,oris=oris,image_size=np.asarray(size,dtype="<f4"))


def array_witness(arr):
    return dict(dtype=arr.dtype.str,shape=list(arr.shape),sha256=sha(arr.tobytes(order="C")))


def reconstruct(np,n,descriptors,key_bytes,expected,size,derived=None):
    count=expected["count"]
    need(type(count) is int and 24<=count<=1024 and len(descriptors)==count*128 and len(key_bytes)==count*56,"exact export dimensions")
    desc=np.frombuffer(descriptors,dtype="u1").reshape(count,128)
    keys=np.frombuffer(key_bytes,dtype="<i8").reshape(count,7)
    full=[tuple(int(x) for x in row)+(bytes(desc[i]),) for i,row in enumerate(keys)]
    need(full==sorted(full),"original lexicographic order; no repair/re-sort")
    coarse=np.asarray(expected["coarse_coordinates_q8"],dtype="<i8")
    native=np.asarray(expected["native_coordinates_q8"],dtype="<i8")
    need(coarse.shape==native.shape==(count,2) and bool(np.array_equal(coarse,keys[:,[2,1]]))
         and bool(np.array_equal(native,coarse*8+896)),"same row coordinates and exact native lift")
    actual=dict(count=count,coarse_coordinates_q8=coarse.tolist(),native_coordinates_q8=native.tolist(),
        descriptors_sha256=sha(desc.astype("<i2").tobytes()),
        keys_sha256=sha(n.json_bytes([list(k[:-1])+[k[-1].hex()] for k in full])))
    need(n.json_bytes(actual)==n.json_bytes(expected),"entire reconstructed feature core")
    need(type(size) is list and len(size)==2 and all(type(x) is int and x>0 for x in size),"explicit coarse width/height")
    attrs=attributes(np,keys,coarse,size)
    need(bool(np.isfinite(attrs["oris"]).all()) and bool((attrs["scales"]>0).all()),"finite key-derived attributes")
    witness={k:array_witness(v) for k,v in attrs.items()}
    if derived is not None:need(n.json_bytes(derived)==n.json_bytes(witness),"exact declared attribute units/recipe")
    return dict(descriptors=desc,keys=keys,coarse=coarse,native=native,attributes=attrs),witness


def write_blob(n,b,files,path,data,cap=128*1024):
    need(path.parent==b.output and not path.exists() and 0<len(data)<=cap<=512*1024,"owned bounded binary export")
    b.check(True);work=b.work()
    need(work["file_bytes"]+len(data)<=4<<30 and sum(b.extents.values())+len(data)<=8*MIB,"binary output reservation")
    with path.open("xb") as stream:
        need(stream.write(data)==len(data),"full binary export write");stream.flush();os.fsync(stream.fileno())
    b.binary.add(str(path));b.extents[str(path)]=len(data)
    ref=files.bind(path,cap,True)
    need(ref["sha256"]==sha(data) and ref["bytes"]==len(data),"actual binary write identity")
    b.check(True);return ref


def export(np,n,b,files,name,feature,expected,size,origin):
    before=core(n,feature,np.asarray(expected["coarse_coordinates_q8"],dtype="<i8"))
    need(n.json_bytes(before)==n.json_bytes(expected),"cached core before serializer")
    desc,keys=payloads(np,feature)
    restored,attrs=reconstruct(np,n,desc,keys,expected,size)
    desc_ref=write_blob(n,b,files,b.output/(name+"-descriptors.u8"),desc)
    key_ref=write_blob(n,b,files,b.output/(name+"-keys.i64"),keys)
    # Read the bytes actually written, then use the identical production decoder.
    loaded=[]
    for ref in (desc_ref,key_ref):
        path=files.verify(ref,128*1024,True)
        with path.open("rb") as stream:data=stream.read(ref["bytes"]+1)
        need(len(data)==ref["bytes"] and sha(data)==ref["sha256"],"same-byte export readback");loaded.append(data)
    reconstruct(np,n,*loaded,expected,size,attrs)
    after=core(n,feature,np.asarray(expected["coarse_coordinates_q8"],dtype="<i8"))
    need(n.json_bytes(before)==n.json_bytes(after),"serializer leaves original FeatureSet unchanged")
    record=dict(schema="m193c-sift-export-feature-v1",name=name,origin=origin,core=expected,
        descriptors=dict(file=desc_ref,dtype="|u1",shape=[expected["count"],128]),
        key_fields=dict(file=key_ref,dtype="<i8",shape=[expected["count"],7]),
        explicit_coarse_image_size=size,attribute_provenance=PROVENANCE,attribute_recipe="size_q8/256; (angle_degrees_q8/256)*pi/180; binary64 then float32",
        attributes=attrs,canonical_before_sha256=sha(n.json_bytes(before)),canonical_after_sha256=sha(n.json_bytes(after)),
        qualification=dict(QUALIFIER))
    return record,restored,loaded


def serializer_controls(np,n,feature,expected,size,loaded,progress):
    original=core(n,feature,np.asarray(expected["coarse_coordinates_q8"],dtype="<i8"))
    desc,keys=loaded
    _,attrs=reconstruct(np,n,desc,keys,expected,size)
    modes={}
    for mode in ("off","on","placebo"):
        if mode=="on":
            got=payloads(np,feature);reconstruct(np,n,*got,expected,size,attrs)
        elif mode=="placebo":tuple(feature.keys)  # pass-through metadata access, no encoding or detector hook
        modes[mode]=sha(n.json_bytes(core(n,feature,np.asarray(expected["coarse_coordinates_q8"],dtype="<i8"))))
    need(len(set(modes.values()))==1 and modes["off"]==sha(n.json_bytes(original)),"post-extraction serializer observer hashes")
    mutants=[]
    bad=bytearray(desc);bad[0]^=1;mutants.append(("one-descriptor-byte",bytes(bad),keys,attrs))
    different=next((i for i in range(1,expected["count"]) if keys[i*56:(i+1)*56]!=keys[:56]),None)
    need(different is not None,"actual distinct key rows for row-order fault")
    order=bytearray(keys);order[:56],order[different*56:(different+1)*56]=order[different*56:(different+1)*56],order[:56]
    mutants.append(("key-row-association",desc,bytes(order),attrs))
    wrong={k:dict(v) for k,v in attrs.items()}
    vals=attributes(np,np.frombuffer(keys,dtype="<i8").reshape(-1,7),expected["coarse_coordinates_q8"],size)
    wrong["scales"]=array_witness(vals["scales"]*np.float32(8))
    mutants.append(("native-instead-of-coarse-scale",desc,keys,wrong))
    evidence=[]
    for name,ds,ks,at in mutants:
        error=None
        try:reconstruct(np,n,ds,ks,expected,size,at)
        except ValueError as exc:error=str(exc)
        evidence.append(dict(id=name,rejected=error is not None,error=error,descriptor_sha256=sha(ds),keys_sha256=sha(ks),attributes=at))
        progress(evidence)
        need(error is not None,"powered export fault: "+name)
    reconstruct(np,n,desc,keys,expected,size,attrs)
    return dict(scope="post-extraction serialization/readback only; no detector or inference observer",
        observer_feature_sha256=modes,mutants=evidence,restored_core_sha256=sha(n.json_bytes(original)),restored_attributes=attrs)


@contextmanager
def import_guard(witness):
    blocked=("flash_attn","lightglue","superpoint")
    need(not any(k.split(".")[0] in blocked for k in sys.modules),"excluded optional/package module absent")
    class Blocker(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split(".")[0] in blocked:
                witness["blocked_imports"].append(fullname)
                raise ModuleNotFoundError("blocked optional/package import: "+fullname,name=fullname)
    guard=Blocker();sys.meta_path.insert(0,guard)
    try:yield
    finally:
        sys.meta_path.remove(guard);witness["import_guard_restored"]=True
        need(not any(k.split(".")[0] in blocked for k in sys.modules),"excluded package/optional source never imported")


def load_model(torch,matcher_bytes,matcher_path,sift_bytes,sift_path,checkpoint,witness):
    need(torch.get_default_dtype()==torch.float32 and not torch.is_autocast_enabled(),"fresh float32/no autocast")
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.manual_seed(0)
    module=types.ModuleType("m193c_offline_lightglue");module.__file__=str(matcher_path);sys.modules[module.__name__]=module
    exec(compile(matcher_bytes,str(matcher_path),"exec"),module.__dict__)
    # Exact original function AST only; no SIFT/package/utils/Kornia import.
    tree=ast.parse(sift_bytes,filename=str(sift_path))
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="sift_to_rootsift"]
    need(len(nodes)==1 and not nodes[0].decorator_list,"one unchanged upstream RootSIFT function")
    scope={"torch":torch};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(sift_path),"exec"),scope)
    model=module.LightGlue(features=None,**CONF).cpu().float().eval()
    source=torch.load(checkpoint,map_location="cpu",weights_only=True)
    need(type(source) in (dict,OrderedDict) and source and all(type(k) is str and isinstance(v,torch.Tensor) for k,v in source.items()),"plain weights-only tensor state dictionary")
    remapped={};renames=[]
    for key,value in source.items():
        destination=key
        for i in range(9):
            for old,new in ((f"self_attn.{i}",f"transformers.{i}.self_attn"),(f"cross_attn.{i}",f"transformers.{i}.cross_attn")):
                if destination==old or destination.startswith(old+"."):destination=new+destination[len(old):]
        need(destination not in remapped,"bijective checkpoint key rename")
        remapped[destination]=value;renames.append(dict(source=key,destination=destination,shape=list(value.shape),dtype=str(value.dtype)))
    expected=model.state_dict()
    missing=sorted(set(expected)-set(remapped));unexpected=sorted(set(remapped)-set(expected))
    witness.update(checkpoint_keys=renames,missing_state_keys=missing,unexpected_state_keys=unexpected,
        expected_state_keys=sorted(expected),complete_parameter_coverage=False)
    # The sole constructor-derived buffer is not a learned parameter. Its exact fixed formula is retained separately.
    need(missing in ([],["confidence_thresholds"]) and unexpected==[],"exhaustive state key coverage")
    need(set(dict(model.named_parameters()))<=set(remapped),"all learned parameters supplied")
    buffer=expected["confidence_thresholds"]
    witness["constructor_buffer"]=dict(name="confidence_thresholds",values=buffer.tolist(),
        provenance="SYNTHESIZED_FIXED_CONSTRUCTOR_BUFFER" if missing else "CHECKPOINT_BUFFER_CHECKED_AGAINST_FIXED_CONSTRUCTOR",
        formula="clip(0.8+0.1*exp(-4*i/9),0,1), original upstream constructor rounded to float32")
    if missing:remapped["confidence_thresholds"]=buffer
    else:need(torch.equal(remapped["confidence_thresholds"],buffer),"checkpoint fixed buffer equals held constructor formula")
    need(all(value.shape==expected[k].shape and value.dtype==expected[k].dtype and value.device.type=="cpu"
             and bool(torch.isfinite(value).all()) for k,value in remapped.items()),"exact state tensor shape/dtype/device/finite")
    loaded=model.load_state_dict(remapped,strict=True)
    need(not loaded.missing_keys and not loaded.unexpected_keys,"strict final model load")
    need(all(p.dtype==torch.float32 and p.device.type=="cpu" for p in model.parameters()),"all parameters CPU float32")
    witness.update(complete_parameter_coverage=True,config=dict(CONF),features_argument=None,device="cpu",
        num_threads=torch.get_num_threads(),num_interop_threads=torch.get_num_interop_threads(),
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),float32_matmul_precision=torch.get_float32_matmul_precision())
    return model,scope["sift_to_rootsift"]


def model_input(torch,rootsift,data):
    attrs=data["attributes"]
    result={k:torch.from_numpy(v.copy()).unsqueeze(0) for k,v in attrs.items()}
    result["descriptors"]=rootsift(torch.from_numpy(data["descriptors"].copy()).to(dtype=torch.float32).unsqueeze(0))
    need(all(v.dtype==torch.float32 and v.device.type=="cpu" and bool(torch.isfinite(v).all()) for v in result.values()),"CPU float32 finite input")
    return result


def tensor_witness(value):
    return {k:array_witness(v.detach().cpu().numpy()) for k,v in value.items()}


def input_controls(torch,rootsift,data):
    before={k:sha(v.tobytes()) for k,v in data.items() if hasattr(v,"tobytes")}
    attribute_before={k:array_witness(v) for k,v in data["attributes"].items()}
    result={}
    for mode in ("off","on","placebo"):
        value=model_input(torch,rootsift,data)
        if mode=="on":tensor_witness(value)
        elif mode=="placebo":tuple(value)
        result[mode]=tensor_witness(value)
    need(result["off"]==result["on"]==result["placebo"],"input observer tensor-byte identity")
    need(before=={k:sha(v.tobytes()) for k,v in data.items() if hasattr(v,"tobytes")},"RootSIFT cannot mutate original export")
    need(attribute_before=={k:array_witness(v) for k,v in data["attributes"].items()},"input attributes unchanged")
    return result


def output_record(torch,output,n0,n1):
    need(set(output)==set("matches0 matches1 matching_scores0 matching_scores1 matches scores stop prune0 prune1".split()),"exact learned output contract")
    compact=output["matches"][0];scores=output["scores"][0]
    need(compact.dtype==torch.int64 and compact.ndim==2 and compact.shape[1]==2 and len(scores)==len(compact),"compact index/score shape")
    need(output["stop"]==9,"fixed complete nine layers")
    pairs=compact.tolist();values=scores.tolist()
    need(len(pairs)<=min(n0,n1) and len({p[0] for p in pairs})==len(pairs)==len({p[1] for p in pairs})
         and pairs==sorted(pairs) and all(0<=a<n0 and 0<=z<n1 for a,z in pairs),"ordered one-to-one returned indices")
    need(all(math.isfinite(x) and 0.1<x<=1 for x in values),"fixed learned confidence acceptance")
    need(output["matches0"].shape==(1,n0) and output["matches1"].shape==(1,n1)
         and output["matching_scores0"].shape==(1,n0) and output["matching_scores1"].shape==(1,n1),"bidirectional output shapes")
    forward=output["matches0"][0].tolist();reverse=output["matches1"][0].tolist()
    ms0=output["matching_scores0"][0].tolist();ms1=output["matching_scores1"][0].tolist()
    need([[i,j] for i,j in enumerate(forward) if j>=0]==pairs
         and all(reverse[j]==i and ms0[i]==ms1[j]==score for (i,j),score in zip(pairs,values,strict=True))
         and sum(j>=0 for j in reverse)==len(pairs),"compact/bidirectional match and score association")
    need(all(v.dtype==torch.float32 and v.device.type=="cpu" and bool(torch.isfinite(v).all())
             for k,v in output.items() if isinstance(v,torch.Tensor) and k not in ("matches0","matches1")),"complete float output witnesses")
    # With pruning disabled, upstream uses ones_like(float matching scores), not integer index counters.
    need(output["prune0"].shape==(1,n0) and output["prune1"].shape==(1,n1)
         and bool((output["prune0"]==9).all()) and bool((output["prune1"]==9).all()),"disabled-pruning nine-layer float counters")
    result={}
    for k,v in output.items():
        if k in ("matches","scores"):result[k]=v[0].tolist()
        elif isinstance(v,torch.Tensor):result[k]=v.tolist()
        else:result[k]=v
    return dict(schema="m193c-private-lightglue-output-v1",output=result,
        tensor_bytes={k:array_witness(v[0].detach().cpu().numpy()) if isinstance(v,list) else array_witness(v.detach().cpu().numpy())
                      for k,v in output.items() if isinstance(v,(list,torch.Tensor))},
        qualification=dict(QUALIFIER),inference_observer_nonperturbation="UNTESTED_ONE_FORWARD")


def assemble(v1,reference,source,pairs,scores):
    rows=[]
    for ordinal,((i,j),score) in enumerate(zip(pairs,scores,strict=True)):
        rx,ry=(int(x) for x in reference["native"][i]);sx,sy=(int(x) for x in source["native"][j])
        preimage=b"M193-LANDMARK-SPLIT-V1\0"+struct.pack(">iiii",rx,ry,sx,sy)+bytes(reference["descriptors"][i])+bytes(source["descriptors"][j])
        match=v1.Match(rx,ry,sx,sy,hashlib.sha256(preimage).digest())
        rows.append((match,dict(learned_ordinal=ordinal,reference_feature_index=i,source_feature_index=j,score=score,
            reference_q8=[rx,ry],source_q8=[sx,sy],digest=match.digest.hex())))
    rows.sort(key=lambda r:(r[0].digest,r[0].reference_y_q8,r[0].reference_x_q8,r[0].source_y_q8,r[0].source_x_q8))
    retained=rows[:v1.MAX_MATCHES]
    return [x[0] for x in retained],[dict(x[1],split="holdout" if i%2 else "calibration") for i,x in enumerate(retained)]


def truth_rows(rows):
    values=[]
    for row in rows:
        rx,ry=row["reference_q8"];sx,sy=row["source_q8"]
        dx,dy=rx-(3071*256-sy),ry-sx
        values.append(dict(reference_q8=[rx,ry],source_q8=[sx,sy],offset_q8=[dx,dy],squared_error_q16=dx*dx+dy*dy))
    squares=[x["squared_error_q16"] for x in values];count=len(values)
    return dict(scope="every supplied correspondence versus literal native rotation, no fitted subset",rows=values,count=count,
        within_two_native_pixels=sum(x<=(2*256)**2 for x in squares),
        sum_squared_error_q16=sum(squares),rms_native_pixels=None if not count else math.sqrt(sum(squares)/count)/256,
        passes=count>=24 and 2*sum(x<=(2*256)**2 for x in squares)>=count and sum(squares)<=count*256**2)


def registrar(v1,d,matches,mode="count"):
    original=v1.match_features;calls=[]
    def supplied(a,z):
        need(a is None and z is None,"saved learned-match registrar path");calls.append(1);return list(matches)
    try:
        v1.match_features=supplied;outcome=d.observe_pair(v1,None,None,mode)
    finally:v1.match_features=original
    need(len(calls)==1,"exactly one unchanged registrar call")
    outcome["qualification"]=dict(QUALIFIER);return outcome


EMPTY_RUNTIME={}


def retain_empty_runtime(n,path,expected=None):
    path=Path(path).resolve();before=n.metadata(path)
    need(before["bytes"]==0,"explicit zero-byte runtime file")
    with path.open("rb") as stream:
        info=os.fstat(stream.fileno())
        need((info.st_dev,info.st_ino)==(before["device"],before["file_id"]) and stream.read(1)==b"","actual empty runtime handle identity")
    need(n.metadata(path)==before,"empty runtime file unchanged while read")
    witness=dict(path=str(path),bytes=0,sha256=sha(b""),metadata=before)
    need(expected is None or witness==expected,"exact retained empty runtime witness")
    need(str(path) not in EMPTY_RUNTIME or EMPTY_RUNTIME[str(path)]==witness,"empty runtime file remained unchanged")
    EMPTY_RUNTIME[str(path)]=witness
    return witness


def check_empty_runtime(n):
    for path,witness in tuple(EMPTY_RUNTIME.items()):retain_empty_runtime(n,path,witness)


def runtime_snapshot(torch,np,n,files):
    """Loaded Python file and native-module inventory; hashes only, no source interpretation."""
    import ctypes
    from ctypes import wintypes
    need(os.name=="nt","bounded Windows commissioning runtime")
    paths=set()
    python_modules=[]
    for name,module in sorted(tuple(sys.modules.items())):
        raw=getattr(module,"__file__",None)
        if raw is not None:
            path=Path(raw).resolve()
            if path.is_file():paths.add(path);python_modules.append(dict(name=name,path=str(path)))
    kernel=ctypes.WinDLL("kernel32",use_last_error=True);psapi=ctypes.WinDLL("psapi",use_last_error=True)
    kernel.GetCurrentProcess.argtypes=[];kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.EnumProcessModulesEx.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.HMODULE),wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),wintypes.DWORD]
    psapi.EnumProcessModulesEx.restype=wintypes.BOOL
    psapi.GetModuleFileNameExW.argtypes=[wintypes.HANDLE,wintypes.HMODULE,wintypes.LPWSTR,wintypes.DWORD]
    psapi.GetModuleFileNameExW.restype=wintypes.DWORD
    modules=(wintypes.HMODULE*2048)();needed=wintypes.DWORD();handle=kernel.GetCurrentProcess()
    need(psapi.EnumProcessModulesEx(handle,modules,ctypes.sizeof(modules),ctypes.byref(needed),3),"actual loaded native module enumeration")
    need(needed.value<=ctypes.sizeof(modules) and needed.value%ctypes.sizeof(wintypes.HMODULE)==0,"complete bounded native module list")
    native=[]
    for module in modules[:needed.value//ctypes.sizeof(wintypes.HMODULE)]:
        buffer=ctypes.create_unicode_buffer(32768)
        length=psapi.GetModuleFileNameExW(handle,module,buffer,len(buffer))
        need(0<length<len(buffer)-1,"complete native module path")
        path=Path(buffer.value).resolve();paths.add(path);native.append(str(path))
    need(len(paths)<=4096,"bounded actual runtime file population")
    total=0;bindings=[];empty=[]
    for path in sorted(paths,key=str):
        total+=path.stat().st_size;need(total<=16<<30,"bounded aggregate runtime bytes hashed")
        if path.stat().st_size==0:empty.append(retain_empty_runtime(n,path))
        else:bindings.append(files.bind(path,2<<30,True))
    distributions=[]
    for dist in metadata.distributions():
        name=dist.metadata.get("Name","")
        if name.lower().replace("_","-") in ("torch","torchvision","numpy"):
            distributions.append(dict(name=name,version=dist.version,root=str(dist.locate_file("")),metadata_path=str(dist._path)))
    return dict(torch_version=torch.__version__,numpy_version=np.__version__,python_version=sys.version,
        executable=sys.executable,python_modules=python_modules,native_modules=sorted(native),files=bindings,empty_runtime_files=empty,
        metadata_distributions=sorted(distributions,key=lambda x:(x["name"],x["metadata_path"])),
        scope="actual loaded Python and native files; runtime compatibility observation, not inferred from distribution names",
        num_threads=torch.get_num_threads(),num_interop_threads=torch.get_num_interop_threads(),
        default_dtype=str(torch.get_default_dtype()),cuda_initialized=torch.cuda.is_initialized(),
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),float32_matmul_precision=torch.get_float32_matmul_precision())
