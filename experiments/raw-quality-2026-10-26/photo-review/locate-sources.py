"""Locate contiguous focus neighborhoods; never a quality metric or merge oracle.

Inputs: --sources-json JSON list of {index,path,sha256}, or the completed native
export receipt; --encoding srgb|linear.
Exactly299 full native source TIFFs in the original frame order are required.
No original RAW is read. Full-frame CFA/radiance arrays are never collected.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline"
REGIONS = ("background-black", "upper-leg-hairs", "thorax-texture", "turquoise-scales")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar_energies(gray):
    # Only2D planes are filtered. These statistics can be fooled by noise/glints.
    assert gray.ndim == 2
    smooth = [ndimage.gaussian_filter(gray, s, mode="reflect") for s in (.7, 1.4, 2.8)]
    return [float(np.mean((smooth[k]-smooth[k+1])**2, dtype=np.float64)) for k in (0, 1)]


def controls():
    y, x = np.indices((384,384), dtype=np.float32)
    structure = .2 + .01*np.sin(x*.5) + .01*np.sin(y*.4)
    flat = np.full((384,384), .2, dtype=np.float32)
    noisy = flat + np.random.default_rng(2710).normal(0, .08, flat.shape).astype(np.float32)
    blurred = ndimage.gaussian_filter(structure, 4)
    values = {"flat": scalar_energies(flat), "structure": scalar_energies(structure),
              "blurred": scalar_energies(blurred), "noisy_flat": scalar_energies(noisy)}
    assert all(a > b for a,b in zip(values["structure"], values["blurred"]))
    assert values["noisy_flat"][0] > values["structure"][0]
    return {"values": values, "interpretation": "Blur lowers structure response, but noisy-flat raises fine response above real structure. This locator cannot establish quality."}


def read_crop(path, rect):
    x,y,w,h = rect
    with tifffile.TiffFile(path) as f:
        assert f.pages[0].shape == (4688,7032,3), "source dimensions/gauge differ"
        image = f.asarray()
        patch = image[y:y+h,x:x+w].copy()
        icc_tag = f.pages[0].tags.get(34675)
        icc = bytes(icc_tag.value) if icc_tag else None
    assert patch.shape == (384,384,3)
    return patch,icc


def normalized(patch, encoding):
    # For toned sRGB TIFFs this returns display-linear AFTER tone, not radiance.
    assert patch.dtype in (np.uint16,np.float32)
    f = patch.astype(np.float32)
    if patch.dtype == np.uint16:
        f /= np.float32(65535)
    if encoding == "srgb":
        f = np.where(f <= .04045, f/12.92, ((np.maximum(f,0)+.055)/1.055)**2.4)
    return f.astype(np.float32)


def preview(patch, encoding):
    if encoding == "srgb" and patch.dtype == np.uint16:
        return ((patch.astype(np.uint32)+128)//257).astype(np.uint8)
    v = normalized(patch, encoding)
    if encoding == "linear":
        v = np.clip(v*np.float32(3.434),0,1)
    v = np.where(v <= .0031308,v*12.92,1.055*np.maximum(v,0)**(1/2.4)-.055)
    return np.rint(np.clip(v,0,1)*255).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-json",type=Path,required=True)
    parser.add_argument("--encoding",choices=("linear","srgb"),required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    source_document = json.loads(args.sources_json.read_text())
    if isinstance(source_document, dict):
        assert source_document["status"] == "299_UNALIGNED_NATIVE_RGB16_DEVELOPED"
        assert source_document["input_content_and_metadata_unchanged"]
        assert source_document["input_order_sha256"] == sha(BASE/"input-order.json")
        assert source_document["active_wh"] == [7032,4688]
        assert source_document["golden"]["status"] == "EXACT"
        assert args.encoding == "srgb", "native export recipe emits toned sRGB16"
        sources = [{"index": r["ordinal"], "path": r["output"], "sha256": r["output_sha256"]}
                   for r in source_document["frames"]]
    else:
        sources = source_document
    assert len(sources)==299 and [r["index"] for r in sources]==list(range(299))
    args.out.mkdir()
    control = controls()  # Must complete before any photographic statistic.
    (args.out/"controls.json").write_text(json.dumps(control,indent=2)+"\n")
    spec=importlib.util.spec_from_file_location("locator_map",ROOT/"experiments/M-PHASE0-PHASE/src/clib.py")
    clib=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clib)
    map_path=BASE/"alignment.txt"
    warp=clib.parse_warpmap(str(map_path))
    assert warp["reference_index"]==149 and warp["frames"]==299 and warp["plane"]==(3516,2344)
    manifest=json.loads((HERE/"baseline-witnesses.json").read_text())
    witnesses={r["name"]:r for r in manifest["witnesses"]}
    rows=[]
    for record in sources:
        path=Path(record["path"])
        assert sha(path)==record["sha256"],"source-development binding changed"
        index=record["index"]
        a,b=warp["placements"][index]
        with tifffile.TiffFile(path) as f:
            assert f.pages[0].shape==(4688,7032,3)
            image=f.asarray()  # One unaligned source, released after this loop.
        regions={}
        for name in REGIONS:  # Background is deliberately measured first.
            x,y,w,h=witnesses[name]["rect_xywh"]
            c=complex(3516,2344)
            p=c+a*(complex(x+68+w/2,y+46+h/2)-c)+2*b
            sx,sy=int(round((p.real-w/2)/2))*2,int(round((p.imag-h/2)/2))*2
            patch=image[sy:sy+h,sx:sx+w]
            assert patch.shape==(384,384,3)
            linear=normalized(patch,args.encoding)
            gray=linear@np.array([.2126,.7152,.0722],dtype=np.float32)
            regions[name]={"rect_xywh":[sx,sy,w,h],"energies":scalar_energies(gray),
                           "mean_inverse_transfer_luma":float(np.mean(gray,dtype=np.float64))}
        rows.append({"index":index,"regions":regions})
        del image
        if index%25==0:
            print(f"Located regions in source{index}/298",flush=True)
    intervals={}
    for name in REGIONS[1:]:
        energy=np.array([r["regions"][name]["energies"] for r in rows],dtype=np.float32)
        background=np.array([r["regions"]["background-black"]["energies"] for r in rows],dtype=np.float32)
        smooth=ndimage.gaussian_filter1d(ndimage.median_filter(energy,size=(5,1)),3,axis=0)
        peaks=np.argmax(smooth,axis=0).tolist()  # Locator only; never a source-reference image.
        normalized_scores=smooth/np.maximum(np.max(smooth,axis=0),np.float32(1e-20))
        score=np.minimum(normalized_scores[:,0],normalized_scores[:,1])
        peak=int(np.argmax(score))
        threshold=float(np.min(score)+(np.max(score)-np.min(score))*.5)
        lo=hi=peak
        while lo>0 and score[lo-1]>=threshold:lo-=1
        while hi<298 and score[hi+1]>=threshold:hi+=1
        center=(lo+hi)//2
        selected=sorted(set([max(0,lo-5),lo,max(lo,center-2),max(lo,center-1),center,min(hi,center+1),min(hi,center+2),hi,min(298,hi+5)]))
        status="VISUAL_INSPECTION_REQUIRED"
        if hi-lo<4 or abs(peaks[0]-peaks[1])>10:status="UNCERTAIN_FOCUS_INTERVAL"
        intervals[name]={"interval_inclusive":[lo,hi],"center":center,"scale_locator_maxima":peaks,
                         "native_sources":selected,"status":status,
                         "median_background_energies":np.median(background,axis=0).tolist(),
                         "median_region_energies":np.median(energy,axis=0).tolist()}
        sheet=Image.new("RGB",(3*144,3*154),(32,32,32))
        draw=ImageDraw.Draw(sheet)
        for j,index in enumerate(selected):
            patch,icc=read_crop(Path(sources[index]["path"]),rows[index]["regions"][name]["rect_xywh"])
            native=Image.fromarray(preview(patch,args.encoding))
            native.save(args.out/f"{name}-source-{index:03}.png",**({"icc_profile":icc} if icc else {}))
            thumb=native.resize((128,128),Image.Resampling.LANCZOS)
            sx,sy=(j%3)*144,(j//3)*154
            sheet.paste(thumb,(sx,sy+20))
            draw.text((sx,sy+3),f"source {index}",fill="white")
        sheet.save(args.out/f"{name}-contact.png")
    result={"schema":1,"status":"LOCATOR_ONLY_NOT_QUALITY_EVIDENCE","encoding":args.encoding,
            "sources_manifest_sha256":sha(args.sources_json),"map_sha256":sha(map_path),
            "script_sha256":sha(Path(__file__).resolve()),"rows":rows,"intervals":intervals,
            "limitations":"Source-center mapping preserves native scale; no new geometry or CA registration. Inverse-sRGB of toned TIFFs is display-linear after tone, not scene radiance. Score maxima only locate a broad connected interval. No frame is a detail ceiling. Noise/glints/halos can increase score; complete photographic comparison and source-neighborhood continuity remain required."}
    (args.out/"locator.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(intervals,indent=2))


if __name__=="__main__":
    main()
