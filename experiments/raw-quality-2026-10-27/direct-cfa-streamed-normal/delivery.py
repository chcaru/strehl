"""Final reference-cell RGB integration, without remosaic or demosaic."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time

HERE=Path(__file__).resolve().parent
MEASUREMENT_PATH=HERE.parent/"direct-cfa-forward-gpu"/"measurement-gpu.py"
MEASUREMENT_SHA="8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84"
FULL_CROP=(68,46,6896,4596)
LIMIT=8<<30


def require(condition,message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda:f.read(1024*1024),b""):
            h.update(data)
    return h.hexdigest()


def record(path):
    p=Path(path).resolve()
    return dict(path=str(p),sha256=digest(p),bytes=p.stat().st_size)


def bound_file(spec):
    require(isinstance(spec,dict) and set(spec)=={"path","sha256","bytes"},"strict file binding required")
    path=Path(spec["path"]).resolve()
    require(path.is_file() and path.stat().st_size==spec["bytes"] and digest(path)==spec["sha256"],
            "bound input differs: "+str(path))
    return path


def write_json(path,value):
    with Path(path).open("x",encoding="utf-8",newline="\n") as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write("\n")


def load_measurement():
    require(digest(MEASUREMENT_PATH)==MEASUREMENT_SHA,"frozen measurement changed")
    name="direct_rgb_frozen_measurement"
    spec=importlib.util.spec_from_file_location(name,MEASUREMENT_PATH)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(MEASUREMENT_PATH.read_bytes(),str(MEASUREMENT_PATH),"exec"),module.__dict__)
    return module


class ReferenceDelivery:
    def __init__(self,torch,field_hw,reference_origin_xy,device_limit_bytes=LIMIT):
        self.torch=torch
        self.field_hw=tuple(field_hw)
        self.reference_origin_xy=tuple(reference_origin_xy)
        require(len(self.reference_origin_xy)==2 and all(type(v)is int and abs(v)<2**31 for v in self.reference_origin_xy),
                "declared integer global reference origin required")
        self.limit=device_limit_bytes
        module=load_measurement()
        # These selectors request each final RGB component at every output cell.
        # They are deliberately not the original RGGB measurement phase rule.
        self.engines=[module.MeasurementGpu(torch,self.field_hw,device_limit_bytes=device_limit_bytes,
                        diagnostic_channel_map=(c,c,c,c)) for c in range(3)]
        self.calls=[]

    def integrate(self,latent,output_xywh):
        t=self.torch
        require(tuple(latent.shape)==(*self.field_hw,3) and latent.dtype==t.float32
                and latent.device.type=="cuda" and latent.device.index==0 and latent.is_contiguous(),
                "global contiguous CUDA0 f32 camera-RGB field required")
        require(len(output_xywh)==4 and all(type(v)is int for v in output_xywh),"integer delivery rectangle required")
        x,y,w,h=output_xywh
        require(x>=0 and y>=0 and 1<=w<=8192 and 1<=h<=8192,"delivery rectangle unsupported")
        require(bool(t.isfinite(latent).all()),"nonfinite saved latent field")
        affine=((1.0,0.0,float(-self.reference_origin_xy[0])),
                (0.0,1.0,float(-self.reference_origin_xy[1])))
        output=t.empty((h,w,3),dtype=t.float32,device="cuda:0")
        rows=max(1,1048576//w)
        strips=[]
        start=time.perf_counter()
        for oy in range(0,h,rows):
            height=min(rows,h-oy)
            rect=(x,y+oy,w,height)
            for c,engine in enumerate(self.engines):
                output[oy:oy+height,:,c].copy_(engine.forward(latent,rect,affine))
            strips.append(list(rect))
        t.cuda.synchronize()
        require(bool(t.isfinite(output).all()),"nonfinite delivered RGB")
        require(max(t.cuda.max_memory_allocated(0),t.cuda.max_memory_reserved(0))<=self.limit,"delivery allocation cap")
        self.calls.append(dict(output_xywh=list(output_xywh),source_to_latent_2x3=[list(v) for v in affine],
                               rectangles=strips,seconds_qpc=time.perf_counter()-start))
        return output

    def metadata(self):
        return dict(field_hw=list(self.field_hw),reference_origin_xy=list(self.reference_origin_xy),
                    output_channel_selectors=[[0]*4,[1]*4,[2]*4],
                    channel_selector_meaning="final reference RGB cell integrals, not original Bayer phase selection",
                    calls=self.calls,measurement=[e.metadata(strict=True) for e in self.engines],
                    signed_camera_DN_preserved=True,black_pedestal_added=False,white_balance_applied=False,
                    demosaic_calls=0,remosaic_calls=0,sensor_response_assumption="uniform unit square GL3x3",
                    quality_claim=False,photographic_admission=False)


def integrate_rgb(torch,latent,reference_origin_xy,output_xywh,device_limit_bytes=LIMIT):
    """Small-control seam; full CLI below pins the complete weevil crop."""
    engine=ReferenceDelivery(torch,tuple(latent.shape[:2]),reference_origin_xy,device_limit_bytes)
    return engine.integrate(latent,output_xywh)


def run(config_path):
    # No NumPy/Torch import or CUDA work occurs merely by importing this module.
    import numpy as np
    import torch
    config_path=Path(config_path).resolve()
    cfg=json.loads(config_path.read_text(encoding="utf-8"))
    require(set(cfg)=={"schema","latent","latent_metadata","out_dir"} and cfg["schema"]==1,"unsupported delivery configuration")
    latent_path=bound_file(cfg["latent"])
    metadata_path=bound_file(cfg["latent_metadata"])
    metadata=json.loads(metadata_path.read_text(encoding="utf-8"))
    required={"schema","field_hw","reference_origin_xy","channels","units","dtype","latent_sha256"}
    require(required.issubset(metadata) and metadata["schema"]=="strehl-direct-cfa-latent-v1",
            "unsupported latent metadata")
    require(metadata["channels"]==["R","G","B"] and metadata["dtype"]=="<f4"
            and metadata["units"]=="black-subtracted-camera-DN"
            and metadata["latent_sha256"]==cfg["latent"]["sha256"],"latent quantity/binding differs")
    hw=tuple(metadata["field_hw"])
    require(len(hw)==2 and all(type(v)is int and 8<=v<=8192 for v in hw),"latent extent invalid")
    require(cfg["latent"]["bytes"]==hw[0]*hw[1]*3*4,"latent byte count differs")
    paths=[config_path,latent_path,metadata_path,Path(__file__).resolve(),MEASUREMENT_PATH]
    before=[record(p) for p in paths]
    stats=[(p.stat().st_size,p.stat().st_mtime_ns) for p in paths]
    out=Path(cfg["out_dir"]).resolve()
    out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    require(torch.cuda.is_available(),"CUDA unavailable")
    torch.cuda.set_device(0)
    props=torch.cuda.get_device_properties(0)
    torch.cuda.set_per_process_memory_fraction(min(1.0,LIMIT/props.total_memory),0)
    torch.cuda.reset_peak_memory_stats()
    original=np.memmap(latent_path,dtype="<f4",mode="r",shape=(*hw,3))
    require(bool(np.isfinite(original).all()),"nonfinite input latent")
    with torch.inference_mode(),torch.autocast(device_type="cuda",enabled=False):
        latent=torch.from_numpy(np.array(original,copy=True)).to(device="cuda:0",dtype=torch.float32)
        engine=ReferenceDelivery(torch,hw,metadata["reference_origin_xy"],LIMIT)
        camera=engine.integrate(latent,FULL_CROP)
        camera_path=out/"camera-rgb-dn.f32le"
        output_array=camera.cpu().numpy().astype("<f4",copy=False)
        with camera_path.open("xb") as f:
            output_array.tofile(f)
        ranges=[dict(channel=c,minimum=float(output_array[...,c].min()),maximum=float(output_array[...,c].max()),
                     negative_samples=int((output_array[...,c]<0).sum())) for c in range(3)]
        runtime=engine.metadata()
    after=[record(p) for p in paths]
    require(before==after and stats==[(p.stat().st_size,p.stat().st_mtime_ns) for p in paths],"delivery input/source changed")
    receipt=dict(schema=1,status="COMPLETE_REFERENCE_CELL_CAMERA_RGB",complete=True,
        camera_rgb=record(camera_path),shape=[FULL_CROP[3],FULL_CROP[2],3],dtype="<f4",
        channels=["R","G","B"],units="black-subtracted-camera-DN",delivery_xywh=list(FULL_CROP),
        reference_origin_xy=metadata["reference_origin_xy"],latent_metadata=metadata,
        ranges=ranges,runtime=runtime,inputs_before=before,inputs_after=after,
        retained_input_bytes_and_metadata_unchanged=True,RAW_reads=0,
        entire_output=True,quality_claim=False,photographic_admission=False,
        demosaic_calls=0,remosaic_calls=0,noise_model_estimated=False,
        threads=torch.get_num_threads(),torch_version=torch.__version__,device=props.name)
    write_json(out/"receipt.json",receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,required=True)
    args=parser.parse_args()
    run(args.config)


if __name__=="__main__":
    main()
