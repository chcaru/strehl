"""Root-scheduled spectral pilot. No import-time numerical operations."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import os
import struct
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OPERATOR=HERE/"spectral-operator.py"
HELPER=HERE.parents[1]/"direct-cfa-streamed-normal/full-photograph.py"
HELPER_SHA="9c69386259c2b508c059e867af7ec1bc45c88803476b85e9f45451a62cf90458"
OUT26=ROOT/"outputs/raw-quality-2026-10-26"
OUT27=ROOT/"outputs/raw-quality-2026-10-27"
CACHE=OUT27/"direct-cfa-streamed-originals-1/output/receipt.json"
GEOMETRY=OUT27/"direct-cfa-forward-cost-precise-1/output/geometry.json"
ORDER=OUT26/"weevil-107-baseline/input-order.json"
MAP=OUT26/"weevil-107-baseline/alignment.txt"
PINS={
    HELPER:HELPER_SHA,
    CACHE:"057b50d7b311d9ff88e818a8d2376a00aac5abf07ab091afea37dd7627c56669",
    GEOMETRY:"a48f5970205e9b4f1afd83f00f4659c0e39909f4ebfc7be2c00f91835af06672",
    ORDER:"0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f",
    MAP:"4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225",
}
COST_INDICES=(0,108,7848,7956,54,3924,4032,7902,1989,2016,2043,3951,4005,5913,5940,5967)
CROP=(68,46,6896,4596)


def require(ok,message):
    if not ok:raise ValueError(message)


def record(path):
    p=Path(path).resolve(); before=p.stat(); h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    after=p.stat()
    require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),"changed during hash")
    return dict(path=str(p),sha256=h.hexdigest(),bytes=before.st_size)


def stamp(path):
    st=Path(path).stat()
    return dict(bytes=st.st_size,mtime_ns=st.st_mtime_ns)


def read(path):return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path,value):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write("\n")


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m
    spec.loader.exec_module(m)
    return m


def pulls():
    lines=MAP.read_text(encoding="utf-8").splitlines()
    for required in ("strehl-warpmap 1","frames 299","plane 3516x2344","reference 149","resampler catmull-rom"):
        require(required in lines,"held map header differs")
    result=[]
    for row in lines:
        f=row.split("#",1)[0].split()
        if not f or not f[0].isdigit():continue
        require(len(f)==6 and int(f[0])==len(result) and f[1]=="placed","held map order/state differs")
        ar,ai,bx,by=[struct.unpack(">d",bytes.fromhex(v))[0] for v in f[2:]]
        require(all(math.isfinite(v) for v in (ar,ai,bx,by)) and ar*ar+ai*ai>0,"invalid held map")
        # Literal held native pull: C + a*(reference-C) + 2*b.
        result.append(((ar,-ai,3516-ar*3516+ai*2344+2*bx),
                       (ai,ar,2344-ai*3516-ar*2344+2*by)))
    require(len(result)==299,"incomplete held map")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("cost16","source149","full299"),required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--renderer-binding",type=Path)
    p.add_argument("--development-receipt",type=Path)
    a=p.parse_args()
    require((a.renderer_binding is None)==(a.development_receipt is None),"developer arguments must be paired")
    require(a.mode=="cost16" or a.renderer_binding is not None,"complete source/full output requires native developer")
    require(a.mode!="cost16" or a.renderer_binding is None,"partial cost output is not a photograph")
    out=a.out.resolve()
    require(out.is_relative_to((ROOT/"outputs").resolve()) and not out.exists(),"fresh workspace output required")
    out.mkdir(parents=True)
    started=time.perf_counter()
    state=dict(schema=1,status="STARTED_NATIVE_SPECTRAL",complete=False,mode=a.mode,
        quality_claim=False,photographic_admission=False,RAW_reads=0,RAW_decodes=0)
    telemetry=(out/"telemetry.jsonl").open("x",encoding="utf-8",newline="\n")
    def emit(event,**values):
        row=dict(event=event,elapsed_seconds_qpc=time.perf_counter()-started,**values)
        s=json.dumps(row,separators=(",",":"),allow_nan=False)
        telemetry.write(s+"\n");telemetry.flush();print(s,flush=True)
    try:
        bindings=list(PINS)+[Path(__file__),OPERATOR,HERE/"api.md",HERE/"implementation-notes.md",
            HERE/"brief.md",HERE.parent/"design.md",HERE.parents[1]/"dual-tree-cfa-gpu/ordered-fir.py"]
        for path,digest in PINS.items():require(record(path)["sha256"]==digest,"pinned input/helper changed: "+str(path))
        helper=load(HELPER,"spectral_frozen_export_validation")
        export,geometry,order=read(CACHE),read(GEOMETRY),read(ORDER)
        helper.validate_export(export,geometry,order)
        maps=pulls()
        renderer=None;development=None
        if a.renderer_binding:
            renderer=read(a.renderer_binding)
            require(record(renderer["path"])==renderer,"native developer executable binding differs")
            development=read(a.development_receipt)
            require(development["wb_bits"]==export["wb_bits"] and development["xyz_to_cam_bits"]==export["xyz_to_cam_bits"]
                    and [helper.f32(v) for v in development["levels_bits"]]==[512,15360],"held development/source mismatch")
            bindings += [a.renderer_binding.resolve(),Path(renderer["path"]),a.development_receipt.resolve(),
                         HERE/"native-cfa-develop.rs",ROOT/"crates/strehl-cli/src/image_out.rs",ROOT/"crates/strehl-core/src/color.rs"]
            for item in development["source_bindings"]:
                require(record(item["path"])==item,"development provenance changed")
                bindings.append(Path(item["path"]))
        bindings=list(dict.fromkeys(p.resolve() for p in bindings))
        before=[record(path) for path in bindings];binding_stats=[stamp(path) for path in bindings]
        save(out/"bindings-before.json",before)
        ids=[149] if a.mode!="full299" else list(range(299))
        original_stats=[stamp(row["original"]["path"]) for row in export["records"]]
        for row,observed in zip(export["records"],original_stats):
            require(observed==dict(bytes=row["original"]["bytes"],mtime_ns=row["original"]["mtime_ns"]),"original metadata differs from export")
        caches=[];cache_stats=[]
        for i in ids:
            row=export["records"][i];cache=row["cache"]
            expected={k:cache[k] for k in ("path","sha256","bytes")}
            require(record(cache["path"])==expected,"original cache bytes differ")
            with Path(cache["path"]).open("rb") as f:
                require(struct.unpack("<4I",f.read(16))==(0,0,4688,7032),"cache header differs")
            caches.append(expected);cache_stats.append(stamp(cache["path"]))
        save(out/"cache-bindings-before.json",caches)
        save(out/"source-pulls.json",dict(source_ids=ids,pulls=[maps[i] for i in ids],
            reference=149,native_center=[3516,2344],stored_reference_not_forced_identity=True))
        import numpy as np
        import torch as t
        t.set_num_threads(4);t.set_num_interop_threads(1);t.set_default_dtype(t.float32)
        t.cuda.set_device(0);t.cuda.reset_peak_memory_stats(0)
        limit=(10 if a.mode=="cost16" else 12)<<30
        model=load(OPERATOR,"native_spectral_pilot_operator")
        noise_data=export["noise"]
        gain=tuple(helper.f32(b) for b in noise_data["gain_bits4"])
        readvar=tuple(helper.f32(b) for b in noise_data["read_variance_bits4"])
        require(list(gain)==noise_data["gain_dn_per_e4"] and list(readvar)==noise_data["read_variance_dn2_4"]
                and noise_data["phase_order"]==["R","G1","G2","B"] and noise_data["black4"]==[512]*4
                and noise_data["white"]==15360 and noise_data["prnu"] is None,"single injected noise model changed")
        noise=model.Noise(512.,gain,readvar)
        all_origins=model.patch_origins(CROP[2],CROP[3],CROP[:2])
        require(len(all_origins)==7957,"fixed whole patch census differs")
        indices=list(COST_INDICES) if a.mode=="cost16" else list(range(len(all_origins)))
        origins=[all_origins[i] for i in indices]
        save(out/"patches.json",dict(whole_patch_count=len(all_origins),selected_indices=indices,
            selected_origins_native_xy=origins,source_ids=ids,output_xywh=list(CROP),batch_limit=16))
        save(out/"noise.json",noise_data)
        save(out/"environment.json",dict(python=sys.version,torch=t.__version__,numpy=np.__version__,
            cuda=t.version.cuda,device=t.cuda.get_device_name(0),workers=4,interop_workers=1,
            device_limit_bytes=limit,tf32=False,autocast=False))
        init_start=time.perf_counter()
        with t.inference_mode(),t.autocast(device_type="cuda",enabled=False):
            engine=model.SpectralConsumer(t,device_limit_bytes=limit)
            t.cuda.synchronize()
            initialization_seconds=time.perf_counter()-init_start
            accumulator=model.Accumulator(engine,len(origins))
            measured_batches=[];warmup_seconds=None
            for ordinal,i in enumerate(ids):
                cache=export["records"][i]["cache"]
                mm=np.memmap(cache["path"],mode="r",dtype="<u2",offset=16,shape=(4688,7032))
                require(not mm.flags.writeable and mm.strides==(14064,2),"unaligned original storage contract")
                source=engine.source(mm,i,noise)
                t.cuda.synchronize()
                # Warm the entire producing17-draw path once, explicitly outside
                # the measured source batch. This does not enter any accumulator.
                if ordinal==0:
                    warm_start=time.perf_counter()
                    warm_geometry=engine.geometry(origins[:1],maps[i],source.hw)
                    warm=model.Accumulator(engine,1)
                    warm_prepared=engine.prepare_source(source,warm_geometry)
                    warm.add([0],warm_prepared)
                    warm_finished=warm.finish()
                    engine.overlap_add(warm_finished,origins[:1],CROP[2],CROP[3],CROP[:2])
                    t.cuda.synchronize();warmup_seconds=time.perf_counter()-warm_start
                    del warm,warm_finished,warm_geometry,warm_prepared
                    emit("warmup-complete",seconds=warmup_seconds,source_id=i,original_probe_draws=16)
                source_start=time.perf_counter()
                for start in range(0,len(origins),16):
                    end=min(start+16,len(origins))
                    t.cuda.synchronize();batch_start=time.perf_counter()
                    g=engine.geometry(origins[start:end],maps[i],source.hw)
                    prepared=engine.prepare_source(source,g)
                    accumulator.add(list(range(start,end)),prepared)
                    t.cuda.synchronize();seconds=time.perf_counter()-batch_start
                    measured_batches.append(dict(source_id=i,start=start,end=end,patches=end-start,seconds_qpc=seconds))
                    emit("source-patch-batch",source_id=i,patch_start=start,patch_end=end,seconds=seconds)
                    del prepared,g
                t.cuda.synchronize()
                emit("source-complete",source_id=i,seconds=time.perf_counter()-source_start,patch_count=len(origins))
                del source
                mm._mmap.close();del mm
            finish_start=time.perf_counter()
            finished=accumulator.finish()
            result=engine.overlap_add(finished,origins,CROP[2],CROP[3],CROP[:2])
            t.cuda.synchronize();finish_seconds=time.perf_counter()-finish_start
            require(a.mode=="cost16" or result["complete_coverage"],"whole photograph has uncovered pixels")
            arms={}
            for arm in ("candidate","uniform"):
                directory=out/arm;directory.mkdir()
                pixels=result[arm].cpu().numpy().astype("<f4",copy=False)
                require(bool(np.isfinite(pixels).all()),"nonfinite native CFA output")
                path=directory/"cfa-dn.f32le"
                with path.open("xb") as f:pixels.tofile(f)
                arms[arm]=dict(cfa=record(path),shape=[4596,6896],dtype="<f4",units="black-subtracted-DN",
                    physical_pattern="RGGB",active_origin_xy=[68,46],entire_output=result["complete_coverage"],
                    minimum=float(pixels.min()),maximum=float(pixels.max()))
                del pixels
            coverage_path=out/"coverage.f32le"
            with coverage_path.open("xb") as f:result["coverage"].cpu().numpy().astype("<f4",copy=False).tofile(f)
            runtime=engine.metadata()
            require(engine.signal_gathers==len(measured_batches)+1
                    and engine.probe_gathers==16*(len(measured_batches)+1),"missing producing probe pass")
            evidence=finished["evidence"]
            save(out/"runtime.json",runtime)
            save(out/"batch-costs.json",measured_batches)
            del result,finished,accumulator,engine
            t.cuda.empty_cache()
        if renderer:
            for arm,entry in arms.items():
                directory=out/arm
                config=dict(schema=1,cfa=entry["cfa"],width=6896,height=4596,active_origin_xy=[68,46],
                    physical_pattern="RGGB",units="black-subtracted-DN",development_receipt=record(a.development_receipt),
                    out_dir=str(directory/"native"),expected_executable_sha256=renderer["sha256"],parity_reference=None)
                config_path=directory/"native-config.json";save(config_path,config)
                command=[renderer["path"],str(config_path)]
                env=os.environ.copy()
                for key in list(env):
                    if key.startswith("STREHL_"):env.pop(key)
                env["RAYON_NUM_THREADS"]="4"
                process=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=300,check=False,
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                (directory/"native-stdout.log").write_bytes(process.stdout)
                (directory/"native-stderr.log").write_bytes(process.stderr)
                save(directory/"native-invocation.json",dict(command=command,actual_exit=process.returncode,expected_exit=0))
                require(process.returncode==0,"native CFA developer failed")
                native=read(directory/"native/receipt.json")
                require(native["status"]=="COMPLETE_NATIVE_CFA_DEVELOPMENT" and native["complete"]
                        and native["pixel_readback_exact"] and native["development"]==development,"native developer completion mismatch")
                entry["native_receipt"]=record(directory/"native/receipt.json")
                entry["rgb16"]=native["rgb16"];entry["linear_rgb32"]=native["linear_rgb32"]
        for expected,old_stat in zip(caches,cache_stats):
            require(record(expected["path"])==expected and stamp(expected["path"])==old_stat,"cache changed")
        require([stamp(row["original"]["path"]) for row in export["records"]]==original_stats,"original RAW metadata changed")
        after=[record(path) for path in bindings]
        require(after==before and [stamp(path) for path in bindings]==binding_stats,"producer/input binding changed")
        save(out/"bindings-after.json",after);save(out/"cache-bindings-after.json",caches)
        state.update(status="COMPLETE_NATIVE_SPECTRAL_"+a.mode.upper(),complete=True,
            source_count=len(ids),source_ids=ids,source_reference=149,patch_count=len(origins),whole_patch_count=7957,
            whole_output=a.mode!="cost16",native_dimensions=[6896,4596],crop_native_xywh=list(CROP),
            complete_coverage=a.mode!="cost16",coverage=record(coverage_path),arms=arms,accumulation=evidence,
            initialization_seconds_qpc=initialization_seconds,warmup_seconds_qpc=warmup_seconds,
            measured_batch_seconds_qpc=sum(row["seconds_qpc"] for row in measured_batches),
            finish_seconds_qpc=finish_seconds,elapsed_seconds_qpc=time.perf_counter()-started,
            original_noise_draws_per_source_patch=16,signal_plus_probe_passes=17,
            runtime=record(out/"runtime.json"),cache_bytes_and_metadata_unchanged=True,
            original_RAW_metadata_unchanged=True,original_RAW_bytes_rehashed_in_this_worker=False,
            original_byte_identity_from_verified_export=True,source_bindings_unchanged=True,
            independent_decode_extra4_columns_unverified=True,per_source_rgb=False,
            aligned_frame_volume=False,final_demosaic_calls=2 if renderer else 0,
            original_storage="read-only u16 cache; one current original u16 GPU source")
        save(out/"receipt.json",state);emit("complete",status=state["status"])
    except BaseException as error:
        state.update(status="INCOMPLETE_NATIVE_SPECTRAL",complete=False,error=repr(error),traceback=traceback.format_exc())
        if not (out/"receipt.json").exists():save(out/"receipt.json",state)
        emit("failed",error=repr(error))
        raise
    finally:
        telemetry.close()


if __name__=="__main__":main()
