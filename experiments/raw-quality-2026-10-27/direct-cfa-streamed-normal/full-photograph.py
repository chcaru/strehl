"""Root-scheduled full299 original-CFA diagnostic; no import-time jobs."""
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
ROOT=HERE.parents[2]
CACHE=ROOT/"outputs/raw-quality-2026-10-27/direct-cfa-streamed-originals-1/output/receipt.json"
GEOMETRY=ROOT/"outputs/raw-quality-2026-10-27/direct-cfa-forward-cost-precise-1/output/geometry.json"
BASE=ROOT/"outputs/raw-quality-2026-10-26/weevil-107-baseline"
FIELD_HW=(4743,7109)
ORIGIN=(-34,-22)
SOURCE_WH=(7032,4688)
CROP=(68,46,6896,4596)
LIMIT=8<<30
PINNED={
    CACHE:"057b50d7b311d9ff88e818a8d2376a00aac5abf07ab091afea37dd7627c56669",
    GEOMETRY:"a48f5970205e9b4f1afd83f00f4659c0e39909f4ebfc7be2c00f91835af06672",
    BASE/"input-order.json":"0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f",
    BASE/"alignment.txt":"4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225",
    HERE/"bands-gpu.py":"d837961600d327d8aa3b5438565c357dd01327c1e6f6ffc4dc4b445b021cf1be",
    HERE/"normal-operator.py":"0b6d8d2110ae62ddc493cd8f1d2540830884ea1257a1ec2d910208461aa3b269",
    HERE/"solver.py":"e98dbfd8201785ce4f3e068508939d0815c6d3e500085ba0ed875512db8d9c88",
    HERE/"measurement-paired.py":"0adbba770b06305b8bbf26a497b9b1f1ab95332edc28037634362232ebe09023",
    HERE/"delivery.py":"c59c7f6a5f218f8809de43e4315ff88f5c5cd7a124826d016da3b75563b83b3b",
    HERE.parent/"direct-cfa-forward-gpu/measurement-gpu.py":"8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84",
    HERE.parent/"joint-cfa-local-fit/band-residual/sensor-operator.py":"536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac",
    ROOT/"crates/strehl-cli/examples/direct-rgb-develop.rs":"0e2ca203be8d7eb8049eccd856c265e40dd5c29f92e36c9e6e67e70ebd643c2a",
}


def require(ok,message):
    if not ok:
        raise ValueError(message)


def record(path):
    p=Path(path).resolve()
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return dict(path=str(p),sha256=h.hexdigest(),bytes=p.stat().st_size)


def bind(value):
    require(set(value)=={"path","sha256","bytes"},"strict file binding required")
    actual=record(value["path"])
    require(actual["sha256"]==value["sha256"] and actual["bytes"]==value["bytes"],"bound file differs: "+value["path"])
    return Path(actual["path"])


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path,value):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write("\n")


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(Path(path).read_bytes(),str(path),"exec"),module.__dict__)
    return module


def stat(path):
    value=Path(path).stat()
    return dict(bytes=value.st_size,mtime_ns=value.st_mtime_ns)


def f32(bits):
    return struct.unpack("<f",struct.pack("<I",bits))[0]


class Telemetry:
    def __init__(self,path):
        self.file=Path(path).open("x",encoding="utf-8",newline="\n")
        self.started=time.perf_counter()
        self.count=0

    def emit(self,event,**values):
        self.count+=1
        row=dict(sequence=self.count,event=event,seconds_qpc=time.perf_counter()-self.started,**values)
        line=json.dumps(row,separators=(",",":"),allow_nan=False)
        self.file.write(line+"\n")
        self.file.flush()
        print(line,flush=True)

    def close(self):
        self.file.close()


def observed_problem_class(normal,telemetry):
    class ObservedProblem(normal.StreamedProblem):
        """Pass-through telemetry only; every numerical call remains super()."""
        def __init__(self,*args,**kwargs):
            self.telemetry_stage="constructor"
            self.telemetry_normal_calls=0
            self.telemetry_evaluations=0
            telemetry.emit("constructor-start",source_count=299)
            start=time.perf_counter()
            super().__init__(*args,**kwargs)
            telemetry.emit("constructor-complete",seconds=time.perf_counter()-start,calls=dict(self.calls))

        def current_source(self,source,collect_evidence=False):
            s=self._source(source)
            stage=self.telemetry_stage
            if stage=="constructor":
                stage="common-metric-scan" if collect_evidence else "constant-Gram-G"
            start=time.perf_counter()
            value=super().current_source(source,collect_evidence=collect_evidence)
            telemetry.emit("source-prepared",stage=stage,source_id=s.source_id,
                           source_preparations=self.calls["source_preparations"],seconds=time.perf_counter()-start)
            return value

        def _adjoint(self,source,value,out):
            start=time.perf_counter()
            result=super()._adjoint(source,value,out)
            telemetry.emit("source-adjoint-complete",stage=self.telemetry_stage,source_id=source.source_id,
                           source_adjoint_count=self.calls["adjoint_source"],seconds=time.perf_counter()-start)
            return result

        def _rhs_pass(self,projected):
            old=self.telemetry_stage
            self.telemetry_stage="projected-RHS" if projected else "unprojected-RHS"
            try:
                return super()._rhs_pass(projected)
            finally:
                self.telemetry_stage=old

        def normal(self,x,projected=True):
            old=self.telemetry_stage
            self.telemetry_normal_calls+=1
            iteration=self.telemetry_normal_calls
            self.telemetry_stage="CG-normal-"+str(iteration)
            telemetry.emit("iteration-normal-start",iteration=iteration)
            start=time.perf_counter()
            try:
                value=super().normal(x,projected=projected)
                telemetry.emit("iteration-normal-complete",iteration=iteration,seconds=time.perf_counter()-start,
                               calls=dict(self.calls))
                return value
            finally:
                self.telemetry_stage=old

        def evaluate(self,z):
            old=self.telemetry_stage
            self.telemetry_evaluations+=1
            self.telemetry_stage=("constant-only-reference-evaluation" if self.telemetry_evaluations==1
                                  else "restored-final-evaluation")
            telemetry.emit("true-audit-start",audit=self.telemetry_evaluations)
            start=time.perf_counter()
            try:
                value=super().evaluate(z)
                telemetry.emit("true-audit-complete",audit=self.telemetry_evaluations,
                               seconds=time.perf_counter()-start)
                return value
            finally:
                self.telemetry_stage=old
    return ObservedProblem


def validate_export(export,geometry,input_order):
    require(export["schema"]==1 and export["status"]=="COMPLETE299_ORIGINAL_NATIVE_CFA_EXPORT"
            and export["complete"] and export["mechanical_pass"] and export["source_count"]==299,
            "incomplete original-cache export")
    require(export["original_sensor_codes_preserved"] and export["unaligned"] and not export["developed"]
            and export["original_bytes_and_metadata_unchanged"] and export["source_bindings_unchanged"],
            "original-cache contract differs")
    require(export["active_wh"]==list(SOURCE_WH) and export["active_origin_xy"]==[0,0]
            and export["physical_phase_order"]==["R","G1","G2","B"]
            and export["physical_phase_offsets_xy"]==[[0,0],[1,0],[0,1],[1,1]]
            and export["measurement_channel_map"]==[0,1,1,2] and export["levels"]==[512,15360],
            "source extent/phase/levels differ")
    require(export["held_map"]["sha256"]==PINNED[BASE/"alignment.txt"]
            and export["input_order"]["sha256"]==PINNED[BASE/"input-order.json"],"export map/order differs")
    require(geometry["source_count"]==299 and geometry["source_wh"]==list(SOURCE_WH)
            and geometry["field_wh"]==list(reversed(FIELD_HW)) and geometry["reference"]==149
            and geometry["reference_integer_origin"]==list(ORIGIN)
            and geometry["native_center"]==[3516.,2344.] and not geometry["stored_anchor_coerced_to_identity"],
            "frozen global geometry differs")
    require(len(export["records"])==len(geometry["maps"])==len(input_order)==299,"all299 sources required")
    for i,(row,mapping,original) in enumerate(zip(export["records"],geometry["maps"],input_order)):
        require(row["index"]==row["source_id"]==mapping["source_index"]==original["index"]==i,"ordinal differs")
        for key in ("path","sha256","bytes"):
            require(row["original"][key]==original[key],"cache provenance differs from original order")
        require(Path(original["path"]).name==f"DSC{i+1:05}.ARW","original filename order differs")
        cache=row["cache"]
        require(cache["header_u32le_yxhw"]==[0,0,4688,7032]
                and cache["payload_offset_bytes"]==16 and cache["dtype"]=="<u2"
                and cache["shape"]==[4688,7032] and cache["row_stride_samples"]==7032
                and cache["original_active_xywh"]==[0,0,7032,4688]
                and cache["bytes"]==16+7032*4688*2,"original cache format differs")
        require(Path(cache["path"]).name==f"rawler-{i:03}.bin"
                and Path(cache["path"]).resolve().parent==(CACHE.parent/"frames").resolve(),"cache path differs")
        actual_bits=[[struct.pack(">d",v).hex() for v in r] for r in mapping["source_to_latent_2x3"]]
        require(actual_bits==mapping["source_to_latent_f64_bits"],"affine f64 bits differ")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--renderer-binding",type=Path,required=True)
    parser.add_argument("--development-receipt",type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    require(out.is_relative_to((ROOT/"outputs").resolve()) and not out.exists(),"fresh workspace output required")
    out.mkdir(parents=True)
    telemetry=Telemetry(out/"telemetry.ndjson")
    state=dict(schema=1,status="STARTED_FULL299_ORIGINAL_CFA_DIAGNOSTIC",complete=False,
               quality_claim=False,photographic_admission=False,admission=False,RAW_reads=0,
               source_count=299,maximum_iterations=64,field_hw=list(FIELD_HW),reference_origin_xy=list(ORIGIN))
    started=time.perf_counter()
    try:
        renderer_binding=args.renderer_binding.resolve()
        renderer=read(renderer_binding)
        renderer_path=bind(renderer)
        development_path=args.development_receipt.resolve()
        development=read(development_path)
        require(development["schema"]==1 and development["exposure_bits"]==1065353216,"pinned development schema/exposure")
        paths=list(PINNED)+[Path(__file__),HERE/"full-photograph-notes.md",renderer_binding,renderer_path,
                            development_path,HERE.parent/"dual-tree-cfa-gpu/ordered-fir.py",
                            ROOT/"crates/strehl-cli/src/image_out.rs",ROOT/"crates/strehl-core/src/color.rs"]
        for spec in development["source_bindings"]:
            p=bind(spec)
            if p not in paths:
                paths.append(p)
        bindings_before=[record(p) for p in paths]
        for path,item in zip(paths,bindings_before):
            require(path not in PINNED or item["sha256"]==PINNED[path],"frozen source changed: "+str(path))
        source_stats_before=[stat(p) for p in paths]
        save(out/"bindings-before.json",bindings_before)
        export,geometry,input_order=read(CACHE),read(GEOMETRY),read(BASE/"input-order.json")
        validate_export(export,geometry,input_order)
        require(development["wb_bits"]==export["wb_bits"]
                and development["xyz_to_cam_bits"]==export["xyz_to_cam_bits"]
                and [f32(b) for b in development["levels_bits"]]==export["levels"],"native development/source metadata differs")
        caches=[];cache_stats=[];original_stats=[]
        for i,row in enumerate(export["records"]):
            item={k:row["cache"][k] for k in ("path","sha256","bytes")}
            p=bind(item)
            with p.open("rb") as f:
                require(list(struct.unpack("<4I",f.read(16)))==[0,0,4688,7032],"native cache header differs")
            caches.append(item);cache_stats.append(stat(p))
            raw_stat=stat(row["original"]["path"])
            require(raw_stat==dict(bytes=row["original"]["bytes"],mtime_ns=row["original"]["mtime_ns"]),
                    "original RAW metadata differs from export")
            original_stats.append(raw_stat)
            telemetry.emit("cache-preflight",source_id=i,cache_bytes=item["bytes"])
        save(out/"cache-bindings-before.json",caches)
        save(out/"geometry.json",geometry)
        clock=vars(time.get_clock_info("perf_counter"))
        require(clock["monotonic"] and clock["resolution"]<=1e-6,"QPC interval clock required")
        import numpy as np
        import torch as t
        t.set_num_threads(4);t.set_num_interop_threads(1);t.set_default_dtype(t.float32)
        t.backends.cuda.matmul.allow_tf32=False;t.backends.cudnn.allow_tf32=False
        require(t.cuda.is_available(),"CUDA required")
        t.cuda.set_device(0)
        properties=t.cuda.get_device_properties(0)
        require(properties.total_memory>=LIMIT,"8GiB device allowance unavailable")
        t.cuda.set_per_process_memory_fraction(LIMIT/properties.total_memory,0)
        t.cuda.reset_peak_memory_stats(0)
        save(out/"environment.json",dict(python=sys.version,torch=t.__version__,cuda=t.version.cuda,numpy=np.__version__,
             device=properties.name,workers=4,interop_workers=1,device_limit_bytes=LIMIT,
             matmul_tf32=False,cudnn_tf32=False,autocast=False,clock=clock))
        solver=load(HERE/"solver.py","full299_frozen_solver")
        normal=solver.operator
        paired=load(HERE/"measurement-paired.py","full299_paired_measurement")
        noise_record=export["noise"]
        shot=tuple(f32(b) for b in noise_record["gain_bits4"])
        read_variance=tuple(f32(b) for b in noise_record["read_variance_bits4"])
        require(list(shot)==noise_record["gain_dn_per_e4"] and list(read_variance)==noise_record["read_variance_dn2_4"]
                and noise_record["phase_order"]==["R","G1","G2","B"] and noise_record["white"]==15360
                and noise_record["black4"]==[512]*4 and noise_record["prnu"] is None,"injected noise bits differ")
        noise=normal.Noise(shot,read_variance,tuple(noise_record["black4"]),noise_record["white"])
        save(out/"noise.json",noise_record)
        loads=[0]*299
        def loader(index):
            loads[index]+=1
            array=np.memmap(caches[index]["path"],mode="r",dtype="<u2",offset=16,shape=(4688,7032))
            require(not array.flags.writeable and array.strides==(14064,2),"original cache mapping differs")
            return array
        sources=[normal.Source(i,(0,0,7032,4688),row["source_to_latent_2x3"],lambda i=i:loader(i))
                 for i,row in enumerate(geometry["maps"])]
        ObservedProblem=observed_problem_class(normal,telemetry)
        with t.inference_mode(),t.autocast(device_type="cuda",enabled=False):
            measurement=paired.PairedMeasurementGpu(t,FIELD_HW,device_limit_bytes=LIMIT)
            problem=ObservedProblem(t,FIELD_HW,sources,noise,measurement=measurement,device_limit_bytes=LIMIT)
            require(problem.paired and problem.count==299*7032*4688,"complete actual paired source support required")
            save(out/"constructor.json",dict(metadata=problem.metadata(),loader_calls=loads.copy()))
            telemetry.emit("fixed64-solve-start")
            fit_started=time.perf_counter()
            result=solver.fit(problem)
            fit_seconds=time.perf_counter()-fit_started
            require(tuple(result.x.shape)==(*FIELD_HW,3) and tuple(result.correction_z.shape)==(*FIELD_HW,3)
                    and bool(t.isfinite(result.x).all()) and bool(t.isfinite(result.correction_z).all()),
                    "nonfinite/incomplete final reconstruction")
            require(result.evidence["maximum_iterations"]==64 and result.evidence["restarts"]==0
                    and result.evidence["preconditioner"] is None,"fixed solver contract changed")
            telemetry.emit("fixed64-solve-complete",status=result.status,converged=result.converged,
                           iterations=result.iterations,seconds=fit_seconds)
            fit_receipt=result.save(out/"fit")
            fit_record=record(out/"fit/result.json")
            latent_spec={k:fit_receipt["latent"][k] for k in ("path","sha256")}
            latent_spec["bytes"]=Path(latent_spec["path"]).stat().st_size
            latent_metadata=dict(schema="strehl-direct-cfa-latent-v1",field_hw=list(FIELD_HW),
                reference_origin_xy=list(ORIGIN),channels=["R","G","B"],units="black-subtracted-camera-DN",dtype="<f4",
                latent_sha256=latent_spec["sha256"],source_count=299,source_order=list(range(299)),
                source_export=record(CACHE),geometry=record(GEOMETRY),held_reference=149,fit_receipt=fit_record,
                solver_status=result.status,numerically_converged=result.converged,iterations=result.iterations,
                quality_claim=False,photographic_admission=False,old_generated_flat_failure_retained=True)
            save(out/"latent-metadata.json",latent_metadata)
            latent=result.x
            solver_status,solver_converged,iterations=result.status,result.converged,result.iterations
            final_calls=dict(problem.calls)
            del result,problem,measurement,sources
            t.cuda.empty_cache()
            delivery=load(HERE/"delivery.py","full299_frozen_delivery")
            delivery_dir=out/"delivery";delivery_dir.mkdir()
            telemetry.emit("whole-reference-cell-delivery-start",delivery_xywh=list(CROP))
            deliver=delivery.ReferenceDelivery(t,FIELD_HW,ORIGIN,LIMIT)
            camera=deliver.integrate(latent,CROP)
            camera_path=delivery_dir/"camera-rgb-dn.f32le"
            host_camera=camera.cpu().numpy().astype("<f4",copy=False)
            require(bool(np.isfinite(host_camera).all()),"nonfinite delivered camera RGB")
            with camera_path.open("xb") as f:
                host_camera.tofile(f)
            camera_spec=record(camera_path)
            delivery_receipt=dict(schema=1,status="COMPLETE_REFERENCE_CELL_CAMERA_RGB",complete=True,
                camera_rgb=camera_spec,shape=[4596,6896,3],dtype="<f4",channels=["R","G","B"],
                units="black-subtracted-camera-DN",delivery_xywh=list(CROP),reference_origin_xy=list(ORIGIN),
                latent=latent_spec,latent_metadata=record(out/"latent-metadata.json"),runtime=deliver.metadata(),
                negative_samples=int((host_camera<0).sum()),minimum=float(host_camera.min()),maximum=float(host_camera.max()),
                retained_input_bytes_and_metadata_unchanged=True,RAW_reads=0,entire_output=True,
                demosaic_calls=0,remosaic_calls=0,quality_claim=False,photographic_admission=False)
            save(delivery_dir/"receipt.json",delivery_receipt)
            del host_camera,camera,latent,deliver
            t.cuda.empty_cache()
            telemetry.emit("whole-reference-cell-delivery-complete",camera_rgb=camera_spec)
        # Develop this complete integrated output even if the finite solver
        # refused convergence. No earlier baseline image substitutes for it.
        renderer_config=dict(schema=1,camera_rgb=camera_spec,delivery_receipt=record(delivery_dir/"receipt.json"),
            development_receipt=record(development_path),out_dir=str(out/"native"),expected_executable_sha256=renderer["sha256"])
        save(out/"renderer-config.json",renderer_config)
        command=[str(renderer_path),str(out/"renderer-config.json")]
        env=os.environ.copy()
        removed=sorted(k for k in env if k.startswith("STREHL_"))
        for key in removed:env.pop(key)
        env["RAYON_NUM_THREADS"]="4"
        telemetry.emit("native-development-start")
        render_started=time.perf_counter()
        process=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=300,check=False,
                               creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        (out/"renderer-stdout.log").write_bytes(process.stdout)
        (out/"renderer-stderr.log").write_bytes(process.stderr)
        save(out/"renderer-invocation.json",dict(command=command,actual_exit=process.returncode,expected_exit=0,
             removed_environment=removed,seconds=time.perf_counter()-render_started,workers=4))
        require(process.returncode==0,"native final RGB developer failed")
        rendered=read(out/"native/receipt.json")
        require(rendered["status"]=="COMPLETE_DIRECT_RGB_NATIVE_DEVELOPMENT" and rendered["complete"]
                and rendered["native_dimensions"]==[6896,4596] and rendered["pixel_readback_exact"]
                and rendered["demosaic_calls"]==rendered["remosaic_calls"]==rendered["RAW_reads"]==0
                and rendered["development"]==development,"native final output contract differs")
        bind(rendered["rgb16"])
        telemetry.emit("native-development-complete",master=rendered["rgb16"])
        after=[]
        for i,item in enumerate(caches):
            p=bind(item)
            require(stat(p)==cache_stats[i],"cache metadata changed")
            require(stat(export["records"][i]["original"]["path"])==original_stats[i],"original RAW metadata changed")
            after.append(item)
            telemetry.emit("cache-postflight",source_id=i)
        bindings_after=[record(p) for p in paths]
        require(bindings_after==bindings_before and [stat(p) for p in paths]==source_stats_before,
                "bound source/metadata/executable changed")
        require(max(t.cuda.max_memory_allocated(0),t.cuda.max_memory_reserved(0))<=LIMIT,"8GiB device high-water exceeded")
        save(out/"cache-bindings-after.json",after)
        save(out/"bindings-after.json",bindings_after)
        require(len(loads)==299 and all(v>=3 for v in loads),"incomplete original source consumption")
        state.update(status="COMPLETE_DIRECT_CFA_FULL_PHOTOGRAPH",complete=True,
            all_sources_consumed=True,solver_status=solver_status,numeric_converged=solver_converged,
            numerically_converged=solver_converged,iterations=iterations,
            fit=fit_record,latent=latent_spec,latent_metadata=record(out/"latent-metadata.json"),
            camera_rgb=camera_spec,delivery=record(delivery_dir/"receipt.json"),
            rgb16=rendered["rgb16"],native_development=record(out/"native/receipt.json"),
            native_dimensions=[6896,4596],delivery_xywh=list(CROP),entire_output=True,
            cache_bytes_and_metadata_unchanged=True,original_RAW_metadata_unchanged=True,
            original_RAW_bytes_rehashed_in_this_worker=False,original_byte_identity_from_verified_export=True,
            source_bindings_unchanged=True,loader_calls=loads,operator_calls=final_calls,
            final_status_not_overridden_for_render=True,old_generated_flat_failure_retained=True,
            production_speed_acceptance=False,fit_seconds_qpc=fit_seconds,elapsed_seconds_qpc=time.perf_counter()-started,
            peak_allocated_bytes=t.cuda.max_memory_allocated(0),peak_reserved_bytes=t.cuda.max_memory_reserved(0),
            device_limit_bytes=LIMIT,per_source_rgb=False,aligned_frame_volume=False,
            original_storage="read-only unaligned u16 memmap, one current loader view",final_demosaic_calls=0,final_remosaic_calls=0)
        save(out/"receipt.json",state)
        telemetry.emit("complete",status=state["status"],solver_status=solver_status,numerically_converged=solver_converged)
    except BaseException as error:
        state.update(status="INCOMPLETE_FULL299_ORIGINAL_CFA_DIAGNOSTIC",complete=False,error=repr(error),
                     traceback=traceback.format_exc(),elapsed_seconds_qpc=time.perf_counter()-started)
        if not (out/"receipt.json").exists():save(out/"receipt.json",state)
        telemetry.emit("failed",error=repr(error))
        raise
    finally:
        telemetry.close()


if __name__=="__main__":
    main()
