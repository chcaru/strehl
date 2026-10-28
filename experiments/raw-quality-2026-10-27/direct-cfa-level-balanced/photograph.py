"""One root-scheduled four-step all299 pilot with complete intermediate outputs."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"direct-cfa-streamed-normal"
FROZEN_WORKER=OLD/"full-photograph.py"
FROZEN_WORKER_SHA="9c69386259c2b508c059e867af7ec1bc45c88803476b85e9f45451a62cf90458"
if hashlib.sha256(FROZEN_WORKER.read_bytes()).hexdigest()!=FROZEN_WORKER_SHA:
    raise ValueError("frozen complete-source validation helper changed")
spec=importlib.util.spec_from_file_location("level_balanced_frozen_source_helpers",FROZEN_WORKER)
old=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=old
exec(compile(FROZEN_WORKER.read_bytes(),str(FROZEN_WORKER),"exec"),old.__dict__)
ROOT,CACHE,GEOMETRY,BASE=old.ROOT,old.CACHE,old.GEOMETRY,old.BASE
FIELD_HW,ORIGIN,CROP,LIMIT=old.FIELD_HW,old.ORIGIN,old.CROP,old.LIMIT
require,record,bind,read,save,load,stat,f32=old.require,old.record,old.bind,old.read,old.save,old.load,old.stat,old.f32


def write_checkpoint(t,np,problem,z,entry,iteration,out,renderer,renderer_path,development_path,
                     development,delivery,views,telemetry):
    checkpoint=out/"checkpoints"/f"iteration-{iteration:02d}"
    checkpoint.mkdir(parents=True,exist_ok=False)
    telemetry.emit("checkpoint-start",iteration=iteration,recursive_only=True)
    # z is the callback's private clone. No developed result enters the fit.
    latent=problem.restore(z)
    require(bool(t.isfinite(latent).all()),"nonfinite checkpoint latent")
    latent_path=checkpoint/"latent.f32le"
    host=latent.cpu().contiguous().numpy().astype("<f4",copy=False)
    with latent_path.open("xb") as f:host.tofile(f)
    del host
    latent_spec=record(latent_path)
    metadata=dict(schema="strehl-direct-cfa-latent-v1",field_hw=list(FIELD_HW),
        reference_origin_xy=list(ORIGIN),channels=["R","G","B"],units="black-subtracted-camera-DN",
        dtype="<f4",latent_sha256=latent_spec["sha256"],source_count=299,source_order=list(range(299)),
        source_export=record(CACHE),geometry=record(GEOMETRY),held_reference=149,iteration=iteration,
        recursive_history=entry,numerical_acceptance_assessed=False,quality_claim=False,photographic_admission=False)
    save(checkpoint/"latent-metadata.json",metadata)
    directory=checkpoint/"delivery";directory.mkdir()
    t.cuda.empty_cache()
    deliver=delivery.ReferenceDelivery(t,FIELD_HW,ORIGIN,LIMIT)
    camera=deliver.integrate(latent,CROP)
    camera_path=directory/"camera-rgb-dn.f32le"
    host=camera.cpu().numpy().astype("<f4",copy=False)
    require(bool(np.isfinite(host).all()),"nonfinite complete delivered camera RGB")
    with camera_path.open("xb") as f:host.tofile(f)
    camera_spec=record(camera_path)
    save(directory/"receipt.json",dict(schema=1,status="COMPLETE_REFERENCE_CELL_CAMERA_RGB",complete=True,
        camera_rgb=camera_spec,shape=[4596,6896,3],dtype="<f4",channels=["R","G","B"],
        units="black-subtracted-camera-DN",delivery_xywh=list(CROP),reference_origin_xy=list(ORIGIN),
        latent=latent_spec,latent_metadata=record(checkpoint/"latent-metadata.json"),runtime=deliver.metadata(),
        negative_samples=int((host<0).sum()),minimum=float(host.min()),maximum=float(host.max()),
        retained_input_bytes_and_metadata_unchanged=True,RAW_reads=0,entire_output=True,
        demosaic_calls=0,remosaic_calls=0,quality_claim=False,photographic_admission=False,
        intermediate=True,iteration=iteration,numerical_acceptance_assessed=False))
    del host,camera,latent,deliver
    t.cuda.empty_cache()
    config=dict(schema=1,camera_rgb=camera_spec,delivery_receipt=record(directory/"receipt.json"),
        development_receipt=record(development_path),out_dir=str(checkpoint/"native"),
        expected_executable_sha256=renderer["sha256"])
    save(checkpoint/"renderer-config.json",config)
    command=[str(renderer_path),str(checkpoint/"renderer-config.json")]
    env=os.environ.copy();removed=sorted(k for k in env if k.startswith("STREHL_"))
    for key in removed:env.pop(key)
    env["RAYON_NUM_THREADS"]="4"
    started=time.perf_counter()
    process=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=300,check=False,
                           creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    (checkpoint/"renderer-stdout.log").write_bytes(process.stdout)
    (checkpoint/"renderer-stderr.log").write_bytes(process.stderr)
    save(checkpoint/"renderer-invocation.json",dict(command=command,actual_exit=process.returncode,
        expected_exit=0,removed_environment=removed,seconds=time.perf_counter()-started,workers=4))
    require(process.returncode==0,"native checkpoint developer failed")
    native=read(checkpoint/"native/receipt.json")
    require(native["status"]=="COMPLETE_DIRECT_RGB_NATIVE_DEVELOPMENT" and native["complete"]
        and native["native_dimensions"]==[6896,4596] and native["pixel_readback_exact"]
        and native["demosaic_calls"]==native["remosaic_calls"]==native["RAW_reads"]==0
        and native["development"]==development,"fixed native checkpoint contract differs")
    bind(native["rgb16"])
    published=views.publish_checkpoint(checkpoint_dir=checkpoint,iteration=iteration,
        native_receipt=checkpoint/"native/receipt.json",held_development_receipt=development_path)
    require(published["complete"],"incomplete checkpoint presentation")
    result=dict(schema=1,status="COMPLETE_LEVEL_BALANCED_CHECKPOINT",complete=True,iteration=iteration,
        source_count=299,latent=latent_spec,latent_metadata=record(checkpoint/"latent-metadata.json"),
        camera_rgb=camera_spec,delivery=record(directory/"receipt.json"),rgb16=native["rgb16"],
        native_development=record(checkpoint/"native/receipt.json"),views=record(checkpoint/"views/receipt.json"),
        native_dimensions=[6896,4596],delivery_xywh=list(CROP),entire_output=True,
        recursive_history=entry,numerical_acceptance_assessed=False,intermediate=True,
        full_job_completion_asserted=False,quality_claim=False,photographic_admission=False)
    save(checkpoint/"receipt.json",result)
    telemetry.emit("checkpoint-complete",iteration=iteration,receipt=record(checkpoint/"receipt.json"))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--renderer-binding",type=Path,required=True)
    parser.add_argument("--development-receipt",type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    require(out.is_relative_to((ROOT/"outputs").resolve()) and not out.exists(),"fresh workspace output required")
    out.mkdir(parents=True);telemetry=old.Telemetry(out/"telemetry.ndjson")
    state=dict(schema=1,status="STARTED_LEVEL_BALANCED_FULL299_PILOT",complete=False,source_count=299,
        maximum_iterations=4,scheduled_checkpoints=[1,2,4],quality_claim=False,photographic_admission=False,
        admission=False,RAW_reads=0,field_hw=list(FIELD_HW),reference_origin_xy=list(ORIGIN))
    started=time.perf_counter();checkpoints=[]
    try:
        renderer_binding=args.renderer_binding.resolve();renderer=read(renderer_binding);renderer_path=bind(renderer)
        development_path=args.development_receipt.resolve();development=read(development_path)
        require(development["schema"]==1 and development["exposure_bits"]==1065353216,"fixed development schema/exposure")
        views=load(HERE/"views.py","level_balanced_checkpoint_views")
        paths=list(old.PINNED)+[FROZEN_WORKER,Path(__file__),HERE/"bands-gpu.py",HERE/"normal-operator.py",
            HERE/"solver.py",HERE/"implementation-notes.md",HERE/"brief.md",HERE/"views.py",
            renderer_binding,renderer_path,development_path,HERE.parent/"dual-tree-cfa-gpu/ordered-fir.py",
            ROOT/"crates/strehl-cli/src/image_out.rs",ROOT/"crates/strehl-core/src/color.rs"]
        paths+=views.source_dependencies()
        paths+=[bind(s) for s in development["source_bindings"]]
        paths=list(dict.fromkeys(Path(p).resolve() for p in paths))
        before=[record(p) for p in paths];source_stats=[stat(p) for p in paths]
        for p,item in zip(paths,before):
            require(p not in old.PINNED or item["sha256"]==old.PINNED[p],"frozen producing dependency changed: "+str(p))
        save(out/"bindings-before.json",before)
        export,geometry,order=read(CACHE),read(GEOMETRY),read(BASE/"input-order.json")
        old.validate_export(export,geometry,order)
        require(development["wb_bits"]==export["wb_bits"] and development["xyz_to_cam_bits"]==export["xyz_to_cam_bits"]
            and [f32(b) for b in development["levels_bits"]]==export["levels"],"development/source metadata differs")
        caches=[];cache_stats=[];original_stats=[]
        for i,row in enumerate(export["records"]):
            item={k:row["cache"][k] for k in ("path","sha256","bytes")};p=bind(item)
            with p.open("rb") as f:require(list(struct.unpack("<4I",f.read(16)))==[0,0,4688,7032],"cache header differs")
            caches.append(item);cache_stats.append(stat(p));raw_stat=stat(row["original"]["path"])
            require(raw_stat==dict(bytes=row["original"]["bytes"],mtime_ns=row["original"]["mtime_ns"]),"original RAW metadata differs")
            original_stats.append(raw_stat);telemetry.emit("cache-preflight",source_id=i)
        save(out/"cache-bindings-before.json",caches);save(out/"geometry.json",geometry)
        import numpy as np
        import torch as t
        t.set_num_threads(4);t.set_num_interop_threads(1);t.set_default_dtype(t.float32)
        t.backends.cuda.matmul.allow_tf32=False;t.backends.cudnn.allow_tf32=False
        require(t.cuda.is_available(),"CUDA required");t.cuda.set_device(0)
        properties=t.cuda.get_device_properties(0);require(properties.total_memory>=LIMIT,"8GiB device allowance unavailable")
        t.cuda.set_per_process_memory_fraction(LIMIT/properties.total_memory,0);t.cuda.reset_peak_memory_stats(0)
        save(out/"environment.json",dict(python=sys.version,torch=t.__version__,cuda=t.version.cuda,numpy=np.__version__,
            device=properties.name,workers=4,interop_workers=1,device_limit_bytes=LIMIT,TF32=False,autocast=False))
        solver=load(HERE/"solver.py","level_balanced_photographic_solver");normal=solver.operator
        paired=load(OLD/"measurement-paired.py","level_balanced_frozen_paired_measurement")
        delivery=load(OLD/"delivery.py","level_balanced_frozen_delivery")
        nr=export["noise"];shot=tuple(f32(b) for b in nr["gain_bits4"]);rv=tuple(f32(b) for b in nr["read_variance_bits4"])
        require(list(shot)==nr["gain_dn_per_e4"] and list(rv)==nr["read_variance_dn2_4"]
            and nr["phase_order"]==["R","G1","G2","B"] and nr["white"]==15360
            and nr["black4"]==[512]*4 and nr["prnu"] is None,"supplied noise bits differ")
        noise=normal.Noise(shot,rv,tuple(nr["black4"]),nr["white"]);save(out/"noise.json",nr)
        loads=[0]*299
        def loader(i):
            loads[i]+=1
            array=np.memmap(caches[i]["path"],mode="r",dtype="<u2",offset=16,shape=(4688,7032))
            require(not array.flags.writeable and array.strides==(14064,2),"original cache view differs")
            return array
        sources=[normal.Source(i,(0,0,7032,4688),row["source_to_latent_2x3"],lambda i=i:loader(i))
                 for i,row in enumerate(geometry["maps"])]
        ObservedProblem=old.observed_problem_class(normal,telemetry)
        with t.inference_mode(),t.autocast(device_type="cuda",enabled=False):
            measurement=paired.PairedMeasurementGpu(t,FIELD_HW,device_limit_bytes=LIMIT)
            problem=ObservedProblem(t,FIELD_HW,sources,noise,measurement=measurement,device_limit_bytes=LIMIT)
            require(problem.paired and problem.count==299*7032*4688,"all299 paired original support required")
            save(out/"constructor.json",dict(metadata=problem.metadata(),loader_calls=loads.copy()))
            def checkpoint(iteration,z,entry):
                checkpoints.append(write_checkpoint(t,np,problem,z,entry,iteration,out,renderer,renderer_path,
                    development_path,development,delivery,views,telemetry))
            telemetry.emit("fixed4-solve-start");fit_start=time.perf_counter()
            result=solver.fit(problem,checkpoint=checkpoint);fit_seconds=time.perf_counter()-fit_start
            require(tuple(result.x.shape)==(*FIELD_HW,3) and bool(t.isfinite(result.x).all())
                and bool(t.isfinite(result.correction_z).all()),"nonfinite final pilot")
            require(result.evidence["maximum_iterations"]==4 and result.evidence["restarts"]==0
                and result.evidence["preconditioner"] is None,"four-step unchanged CG contract differs")
            fit_receipt=result.save(out/"fit")
            final_checkpoint=next((c for c in checkpoints if c["iteration"]==result.iterations),None)
            if final_checkpoint is not None:
                require(fit_receipt["latent"]["sha256"]==final_checkpoint["latent"]["sha256"],
                        "checkpoint restore differs from final restored latent")
            telemetry.emit("fixed4-solve-complete",iterations=result.iterations,status=result.status,
                converged=result.converged,seconds=fit_seconds)
            final_calls=dict(problem.calls)
            solver_status,converged,iterations=result.status,result.converged,result.iterations
            # An early numerical stop remains an honestly partial schedule.
            # It does not authorize extra iterations or duplicating photographs.
            complete_schedule=[c["iteration"] for c in checkpoints]==[1,2,4]
            del result,problem,measurement,sources
            t.cuda.empty_cache()
        after=[]
        for i,item in enumerate(caches):
            p=bind(item);require(stat(p)==cache_stats[i],"cache metadata changed")
            require(stat(export["records"][i]["original"]["path"])==original_stats[i],"original RAW metadata changed")
            after.append(item);telemetry.emit("cache-postflight",source_id=i)
        after_bindings=[record(p) for p in paths]
        require(after_bindings==before and [stat(p) for p in paths]==source_stats,"bound source/executable/metadata changed")
        require(max(t.cuda.max_memory_allocated(0),t.cuda.max_memory_reserved(0))<=LIMIT,"8GiB device high-water exceeded")
        save(out/"cache-bindings-after.json",after);save(out/"bindings-after.json",after_bindings)
        state.update(status="COMPLETE_LEVEL_BALANCED_FULL299_PILOT" if complete_schedule else "INCOMPLETE_LEVEL_BALANCED_CHECKPOINT_SCHEDULE",
            complete=complete_schedule,source_count=299,all_sources_consumed=True,checkpoints=checkpoints,
            fit=record(out/"fit/result.json"),final_latent=fit_receipt["latent"],final_correction=fit_receipt["correction-z"],
            solver_status=solver_status,numeric_converged=converged,iterations=iterations,
            final_status_not_overridden_for_render=True,cache_bytes_and_metadata_unchanged=True,
            final_checkpoint_latent_exact=final_checkpoint is not None,
            original_RAW_metadata_unchanged=True,original_RAW_bytes_rehashed_in_this_worker=False,
            original_byte_identity_from_verified_export=True,source_bindings_unchanged=True,
            loader_calls=loads,operator_calls=final_calls,fit_seconds_qpc=fit_seconds,
            elapsed_seconds_qpc=time.perf_counter()-started,peak_allocated_bytes=t.cuda.max_memory_allocated(0),
            peak_reserved_bytes=t.cuda.max_memory_reserved(0),device_limit_bytes=LIMIT,
            per_source_rgb=False,aligned_frame_volume=False,final_demosaic_calls=0,final_remosaic_calls=0,
            old_generated_quality_failures_retained=True,no_automatic_extension=True)
        save(out/"receipt.json",state);telemetry.emit("complete",status=state["status"],numeric_converged=converged)
    except BaseException as error:
        state.update(status="INCOMPLETE_LEVEL_BALANCED_FULL299_PILOT",complete=False,error=repr(error),
            traceback=traceback.format_exc(),checkpoints=checkpoints,elapsed_seconds_qpc=time.perf_counter()-started)
        if not (out/"receipt.json").exists():save(out/"receipt.json",state)
        telemetry.emit("failed",error=repr(error));raise
    finally:
        telemetry.close()


if __name__=="__main__":main()
