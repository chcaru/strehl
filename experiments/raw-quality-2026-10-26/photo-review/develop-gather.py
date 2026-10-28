"""Develop actual pre/post production gather captures; no RAW reads or handported gather."""
from pathlib import Path
import hashlib
import importlib.util
import json

import numpy as np
from PIL import Image
import tifffile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CAPTURE=ROOT/"outputs/raw-quality-2026-10-26/weevil-anchor149-gather/capture.json"
BASE=ROOT/"outputs/raw-quality-2026-10-26/weevil-107-baseline"
OUT=HERE/"source149-gather-1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def main():
    receipt=json.loads(CAPTURE.read_text())
    assert receipt["status"]=="ACTUAL_BASELINE_GATHER_CAPTURED_NO_QUALITY_CLAIM"
    assert receipt["original_map_order_unchanged"]
    assert receipt["map"]["sha256"]==sha(BASE/"alignment.txt")
    capture={}
    for arm in ("original","gathered"):
        row=receipt[arm]
        path=Path(row["path"])
        assert sha(path)==row["sha256"]
        assert row["reference_native_crop_xywh"]==[68,46,6896,4596]
        capture[arm]=np.memmap(path,mode="r",dtype="<u2",shape=(4596,6896))
    original=np.load(HERE/"source-149/active-cfa-u16.npy",mmap_mode="r")
    assert np.array_equal(capture["original"],original[46:46+4596,68:68+6896])
    source=receipt["source"]
    wb=np.array(source["resolved_wb_gains"],dtype=np.float32)
    xyz=np.array(source["resolved_xyz_to_cam"][0],dtype=np.float32)
    standard=np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]],dtype=np.float64)
    fwd=xyz.astype(np.float64)@standard
    matrix=np.linalg.inv(fwd/fwd.sum(axis=1)[:,None]).astype(np.float32)
    mhc_path=ROOT/"experiments/M95-demosaic/src/m95dem.py"
    mhc=module("gather_mhc",mhc_path)
    developer=module("gather_display",HERE/"develop-source.py")
    baseline=tifffile.memmap(BASE/"linear-master.tiff")
    with tifffile.TiffFile(BASE/"stack-master.tiff") as f:
        icc=bytes(f.pages[0].tags[34675].value)
    witnesses=json.loads((HERE/"baseline-witnesses.json").read_text())["witnesses"]
    OUT.mkdir(exist_ok=False)
    rows=[]
    for witness in witnesses:
        name=witness["name"]
        if name not in ("upper-leg-hairs","background-black"):
            continue
        x,y,w,h=witness["rect_xywh"]
        rgb={"stack":baseline[y:y+h,x:x+w].copy()}
        for arm,cfa in capture.items():
            cut=cfa[y-8:y+h+8,x-8:x+w+8]
            yy,xx=np.indices(cut.shape)
            phase=np.where((xx+yy)%2,1,np.where(yy%2,2,0))
            norm=np.maximum(cut.astype(np.float32)-np.float32(source["black"]),0)*wb[phase]/np.float32(source["white"]-source["black"])
            camera=mhc.demosaic_mhc(norm)[8:-8,8:-8]
            rgb[arm]=camera@matrix.T
        files=[]
        for arm,value in rgb.items():
            image=OUT/f"{name}-{arm}.png"
            linear=OUT/f"{name}-{arm}-linear.npy"
            np.save(linear,value,allow_pickle=False)
            Image.fromarray(developer.display(value)).save(image,icc_profile=icc)
            files.append({"arm":arm,"png":str(image),"png_sha256":sha(image),"linear":str(linear),"linear_sha256":sha(linear)})
        rows.append({"name":name,"native_master_xywh":[x,y,w,h],"resampled":False,"outputs":files})
    result={"status":"ACTUAL_GATHER_SPLIT_READY_FOR_NATIVE_VISUAL_REVIEW","capture_receipt_sha256":sha(CAPTURE),
            "source_original_matches_independent_rawpy_cfa":True,"display":"All arms: fixed gain3.434, standard sRGB transfer, round8, originalICC; no sharpening or local fit.",
            "development":"Original/gathered capture u16 -> levels512/15360 and as-shotWB -> same repositoryMHC port -> same camera matrix. Stack is retained actual linear master. Gather is actual product capture, not Python reproduction.",
            "limits":"One anchor and two regions; different source depths remain in stack. MHC port f32 order may differ from native writer. This does not isolate CA versus firstMHC/resampling without another actual consumer arm.",
            "script_sha256":sha(Path(__file__).resolve()),"mhc_source_sha256":sha(mhc_path),"rows":rows}
    (OUT/"receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Actual gather split developed; original matches independent savedCFA exactly; no RAW reads.")


if __name__=="__main__":main()
