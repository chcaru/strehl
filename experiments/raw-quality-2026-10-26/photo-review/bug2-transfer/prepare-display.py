"""Frozen bug2 transfer review, one declared arm at a time; no RAW reads."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image
import tifffile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/"outputs/raw-quality-2026-10-26"
WITNESSES=[
    ("dark-background",6180,40,"Far-right dark control; not a calibrated noise flat."),
    ("green-fine-texture",380,720,"Left-field green surface microtexture and small marks."),
    ("left-green-rim",100,2970,"Far-left green edge, dark surround and fine fibres."),
    ("junction-white-strands",990,2040,"Three-surface junction and white strands at distinct depths."),
    ("orange-network-upper",2820,430,"Orange branched surface pattern in upper field."),
    ("orange-network-lower",1530,3460,"Orange fine network in lower-left field."),
    ("central-green-orange-rim",2790,2160,"Green/orange meeting edge and broad dark contour."),
    ("central-seam",4250,2970,"Diagonal seam, fine edge colour and coarse occlusion contour."),
    ("right-reflective-orange",5560,2560,"Right-field reflective orange microtexture and bright haze."),
    ("right-outer-fibres",5960,900,"Far-right outer boundary, white fibres and glints."),
]


def sha(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        while block:=stream.read(8<<20):digest.update(block)
    return digest.hexdigest()


def ref(path):return {"path":str(path),"sha256":sha(path),"bytes":path.stat().st_size}


def display16(linear,gain):
    v=np.clip(linear*np.float32(gain),np.float32(0),np.float32(1))
    encoded=np.where(v<=np.float32(.0031308),v*np.float32(12.92),
        np.float32(1.055)*v**np.float32(1/2.4)-np.float32(.055))
    return np.rint(encoded*np.float32(65535)).astype(np.uint16)


def main():
    arm=sys.argv[1]
    assert arm in ("baseline","ca-off")
    frozen=HERE/"frozen-witnesses.json"
    baseline=BASE/"bug2-100-baseline"
    if arm=="baseline":
        assert not frozen.exists(),"baseline witnesses already frozen"
        record=json.loads((baseline/"completion.json").read_text())
        log=(baseline/"render.log").read_text()
        assert "gain 4.993x" in log and "white 0.19560" in log
        config={"status":"FROZEN_BEFORE_CA_OFF_VIEW", "candidate_seen":False,
            "gain":4.993,"gain_source":"Baseline log auto-exposure suggestion4.993; no per-arm fit.",
            "dimensions":[6566,4376],"crop_quad_xywh":[117,78,3283,2188],
            "native_reference_offset":[234,156],"baseline_completion":ref(baseline/"completion.json"),
            "baseline_source_master_sha256":record["master"]["sha256"],
            "map_sha256":record["warp_map"]["sha256"],"executable_sha256":record["executable"]["sha256"],
            "input_order_sha256":sha(baseline/"input-order.json"),
            "whole_baseline_viewed_before_selection":True,"whole_tool_display":[1920,1280],
            "witnesses":[{"name":n,"native_xywh":[x,y,384,384],"role":r} for n,x,y,r in WITNESSES]}
        frozen.write_text(json.dumps(config,indent=2)+"\n")
    config=json.loads(frozen.read_text())
    source=BASE/f"bug2-100-{arm}"
    record=json.loads((source/"completion.json").read_text())
    assert record["frames"]==299 and record["native_dimensions"]==config["dimensions"]
    assert record["crop_quad_xywh"]==config["crop_quad_xywh"]
    assert record["warp_map"]["sha256"]==config["map_sha256"]
    assert record["executable"]["sha256"]==config["executable_sha256"]
    assert sha(source/"input-order.json")==config["input_order_sha256"]
    assert sha(Path(record["master"]["path"]))==record["master"]["sha256"]
    with tifffile.TiffFile(source/"stack-master.tiff") as file:
        icc=bytes(file.pages[0].tags[34675].value)
    with tifffile.TiffFile(baseline/"stack-master.tiff") as file:
        assert bytes(file.pages[0].tags[34675].value)==icc
    linear_path=source/"linear-master.tiff"
    linear=tifffile.memmap(linear_path,mode="r")
    assert linear.shape==(4376,6566,3) and linear.dtype==np.float32
    out=HERE/arm
    out.mkdir(exist_ok=False)
    master_path=out/"common-display-master.tiff"
    master=tifffile.memmap(master_path,shape=linear.shape,dtype=np.uint16,photometric="rgb",metadata=None,
        software="Strehl bug2 transfer common display gain4.993+sRGB",
        extratags=[(34675,"B",len(icc),icc,False)])
    for y in range(0,4376,128):
        block=linear[y:y+128]
        assert np.isfinite(block).all()
        master[y:y+128]=display16(block,config["gain"])
    master.flush()
    image=Image.fromarray(((master.astype(np.uint32)+128)//257).astype(np.uint8))
    image.save(out/"complete-stack.jpg",quality=98,subsampling=0,icc_profile=icc)
    image.thumbnail((1617,1617),Image.Resampling.LANCZOS)
    image.save(out/"overview.jpg",quality=98,icc_profile=icc)
    crops=[]
    for row in config["witnesses"]:
        name=row["name"]
        x,y,w,h=row["native_xywh"]
        crop=master[y:y+h,x:x+w].copy()
        assert crop.shape==(384,384,3)
        assert np.array_equal(crop,display16(linear[y:y+h,x:x+w],config["gain"]))
        png=out/f"{name}.png"
        tiff=out/f"{name}.tiff"
        Image.fromarray(((crop.astype(np.uint32)+128)//257).astype(np.uint8)).save(png,icc_profile=icc)
        tifffile.imwrite(tiff,crop,photometric="rgb",metadata=None,extratags=[(34675,"B",len(icc),icc,False)])
        assert np.array_equal(tifffile.imread(tiff),crop)
        with Image.open(png) as check:assert check.size==(384,384) and check.info["icc_profile"]==icc
        crops.append({**row,"png":ref(png),"rgb16":ref(tiff),"resized":False})
    result={"status":"COMPLETE_COMMON_DISPLAY_READY", "arm":arm,"frozen_plan":ref(frozen),
        "source_completion":ref(source/"completion.json"),"source_linear":ref(linear_path),
        "common_master":ref(master_path),"complete_jpeg":ref(out/"complete-stack.jpg"),"overview":ref(out/"overview.jpg"),
        "display":"Both arms use baseline-chosen gain4.993, clamp0..1, standard sRGB transfer, roundRGB16; PNG/JPEG=(RGB16+128)//257. SameICC, no filtering/sharpening or local fit. Native384 crops are exact subarrays.",
        "icc_sha256":hashlib.sha256(icc).hexdigest(),"crops":crops,"script":ref(Path(__file__).resolve()),
        "command":f"python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/bug2-transfer/prepare-display.py {arm}"}
    (out/"receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    print(f"{arm}: complete6566x4376RGB16 and10native384 witnesses ready, fixedgain4.993.")


if __name__=="__main__":main()
