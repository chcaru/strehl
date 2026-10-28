"""Complete paired masters and frozen native witnesses with one display transform."""
from pathlib import Path
import hashlib
import json
import time

import numpy as np
from PIL import Image
import tifffile

HERE=Path(__file__).resolve().parent
PHOTO=HERE.parent
ROOT=HERE.parents[3]
BASE=ROOT/"outputs/raw-quality-2026-10-26"
ARMS={"baseline-ca-on":BASE/"weevil-107-baseline", "ca-off":BASE/"weevil-107-ca-off"}


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while block:=f.read(8<<20):h.update(block)
    return h.hexdigest()


def ref(path):
    return {"path":str(path),"sha256":sha(path),"bytes":path.stat().st_size}


def common16(linear):
    v=np.clip(linear*np.float32(3.434),np.float32(0),np.float32(1))
    encoded=np.where(v<=np.float32(.0031308),v*np.float32(12.92),
                     np.float32(1.055)*np.maximum(v,np.float32(0))**np.float32(1/2.4)-np.float32(.055))
    return np.rint(encoded*np.float32(65535)).astype(np.uint16)


def main():
    started=time.monotonic()
    witnesses=json.loads((PHOTO/"baseline-witnesses.json").read_text())["witnesses"]
    records={}
    expected_icc=None
    source_order=None
    for name,source in ARMS.items():
        receipt=json.loads((source/"completion.json").read_text())
        assert receipt["frames"]==299 and receipt["native_dimensions"]==[6896,4596]
        assert receipt["crop_quad_xywh"]==[34,23,3448,2298]
        assert receipt["warp_map"]["sha256"]=="4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"
        assert receipt["executable"]["sha256"]=="89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388"
        assert sha(Path(receipt["master"]["path"]))==receipt["master"]["sha256"]
        order=sha(source/"input-order.json")
        if source_order is None:source_order=order
        assert order==source_order
        out=HERE/name
        out.mkdir(exist_ok=False)
        linear_path=source/"linear-master.tiff"
        linear=tifffile.memmap(linear_path,mode="r")
        assert linear.shape==(4596,6896,3) and linear.dtype==np.float32
        with tifffile.TiffFile(source/"stack-master.tiff") as f:
            icc=bytes(f.pages[0].tags[34675].value)
        if expected_icc is None:expected_icc=icc
        assert icc==expected_icc
        master_path=out/"common-display-master.tiff"
        master=tifffile.memmap(master_path,shape=linear.shape,dtype=np.uint16,photometric="rgb",metadata=None,
            software="Strehl independent CA comparison: fixed gain3.434 and sRGB transfer",
            extratags=[(34675,"B",len(icc),icc,False)])
        for y in range(0,4596,128):
            block=linear[y:y+128]
            assert np.isfinite(block).all()
            master[y:y+128]=common16(block)
        master.flush()
        image8=((master.astype(np.uint32)+128)//257).astype(np.uint8)
        image=Image.fromarray(image8)
        image.save(out/"complete-stack.jpg",quality=98,subsampling=0,icc_profile=icc)
        overview=image.copy()
        overview.thumbnail((1617,1617),Image.Resampling.LANCZOS)
        overview.save(out/"overview.jpg",quality=98,icc_profile=icc)
        rows=[]
        for witness in witnesses:
            x,y,w,h=witness["rect_xywh"]
            crop=master[y:y+h,x:x+w].copy()
            assert np.array_equal(crop,common16(linear[y:y+h,x:x+w]))
            png=out/f'{witness["name"]}.png'
            tiff=out/f'{witness["name"]}.tiff'
            Image.fromarray(((crop.astype(np.uint32)+128)//257).astype(np.uint8)).save(png,icc_profile=icc)
            tifffile.imwrite(tiff,crop,photometric="rgb",metadata=None,extratags=[(34675,"B",len(icc),icc,False)])
            with Image.open(png) as check:
                assert check.size==(384,384) and check.info["icc_profile"]==icc
            assert np.array_equal(tifffile.imread(tiff),crop)
            rows.append({"name":witness["name"],"native_xywh":[x,y,w,h],"resized":False,"png":ref(png),"rgb16":ref(tiff)})
        with tifffile.TiffFile(master_path) as check:
            assert check.pages[0].shape==(4596,6896,3) and check.pages[0].dtype==np.uint16
            assert bytes(check.pages[0].tags[34675].value)==icc
        records[name]={"source_completion":ref(source/"completion.json"),"original_developed_master":receipt["master"],
                       "source_linear_master":ref(linear_path),"common_master":ref(master_path),
                       "complete_jpeg":ref(out/"complete-stack.jpg"),"overview":ref(out/"overview.jpg"),"witnesses":rows}
        del image8,image,overview,master,linear
    capture_path=BASE/"weevil-anchor149-gather-ca-off/capture.json"
    capture=json.loads(capture_path.read_text())
    original_hash=sha(Path(capture["original"]["path"]))
    gathered_hash=sha(Path(capture["gathered"]["path"]))
    assert original_hash==gathered_hash==capture["original"]["sha256"]==capture["gathered"]["sha256"]
    result={"schema":1,"status":"PAIRED_COMPLETE_COMMON_DISPLAY_READY_NO_VERDICT", "frames":299,"dimensions":[6896,4596],
            "display":"Both retained pre-tone linear BT.709/D65 masters -> fixed gain3.434 -> clamp0..1 -> standard sRGB transfer -> roundRGB16; PNG/JPEG conversion (RGB16+128)//257. No source-specific tone, sharpening, filtering, alignment or resize except labeled overviews.",
            "warning":"Original auto-tone differs across runs; original developed TIFFs must not be used for a tone-matched verdict.",
            "gauge":"Delivered native RGB, common origin corresponds to reference-native(68,46), reference149, same map/executable/source order.",
            "input_order_sha256":source_order,"icc_sha256":hashlib.sha256(expected_icc).hexdigest(),
            "ca_off_capture":ref(capture_path),"ca_off_entire_cfa_original_equals_gathered":True,
            "script":ref(Path(__file__).resolve()),"command":"python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/ca-off-review/prepare-common-display.py",
            "operational_seconds":time.monotonic()-started,"arms":records}
    (HERE/"common-display-receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    print(f"Complete paired RGB16 masters, full JPEGs and all20 frozen crops prepared in {result['operational_seconds']:.3f}s; all checks passed.")


if __name__=="__main__":main()
