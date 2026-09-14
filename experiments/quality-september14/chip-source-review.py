"""One IC reference original, independent decode and four native views."""
from pathlib import Path
import json
import sys
import importlib.util
import subprocess
import struct
import hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/"chip-source-review-1"
BASE=HERE/"chip-baseline-1"
SOURCE=Path("D:/personal/macro/requests/misc-diagnostic/uncapped-IC-chip-cpl/DSC00150.ARW")

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    sys.modules[name]=obj
    spec.loader.exec_module(obj)
    return obj

def save(path,value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2)
        stream.write("\n")

def child():
    import numpy as np
    import rawpy
    from PIL import Image
    clib=module("chip_source_map",ROOT/"experiments/M-PHASE0-PHASE/src/clib.py")
    warp=clib.parse_warpmap(str(BASE/"chip.warpmap.txt"))
    a,b=warp["placements"][149]
    residual=2*(abs(a-1)*((1758**2+1172**2)**0.5)+abs(b))
    assert warp["reference_index"]==149 and residual<1e-9
    crops=json.loads((BASE/"views/crops.json").read_text())
    assert crops["reference_index"]==149 and crops["output_origin_native"]==[266,178]
    regions=crops["regions"]
    for r in regions:
        r["sensor_x"]=r["x"]+266;r["sensor_y"]=r["y"]+178
    x0=min(r["sensor_x"] for r in regions);y0=min(r["sensor_y"] for r in regions)
    x1=max(r["sensor_x"]+r["width"] for r in regions)
    y1=max(r["sensor_y"]+r["height"] for r in regions)
    original=(SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns)
    with rawpy.imread(str(SOURCE)) as raw:
        patch=raw.raw_image_visible[y0:y1,x0:x1].copy()
        assert raw.raw_pattern.tolist()==[[0,1],[3,2]]
        black=list(raw.black_level_per_channel);white=raw.white_level
        meta=dict(rawpy=rawpy.__version__,libraw=list(rawpy.libraw_version),black=black,white=white,
            visible_shape=list(raw.raw_image_visible.shape),camera_whitebalance=raw.camera_whitebalance)
        developed=raw.postprocess(use_camera_wb=True,no_auto_bright=True,output_bps=16,
            gamma=(1,1),output_color=rawpy.ColorSpace.sRGB,demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
        rgb={r["name"]:developed[r["sensor_y"]:r["sensor_y"]+r["height"],
            r["sensor_x"]:r["sensor_x"]+r["width"]].copy() for r in regions}
        del developed
    np.save(OUT/"source-visible-union.npy",patch,allow_pickle=False)
    secondary=ROOT/"experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe"
    result=subprocess.run([str(secondary),str(SOURCE),str(OUT),"reference149",str(y0),str(x0),str(y1-y0),str(x1-x0)],
        capture_output=True,text=True,check=True,timeout=30)
    (OUT/"secondary.log").write_text(result.stdout+result.stderr,encoding="utf-8")
    blob=(OUT/"rawler-reference149.bin").read_bytes()
    assert struct.unpack("<4I",blob[:16])==(y0,x0,y1-y0,x1-x0)
    other=np.frombuffer(blob,dtype="<u2",offset=16).reshape(patch.shape)
    different=int(np.count_nonzero(patch!=other))
    assert different==0,"independent RAW decode mismatch"
    def display(v):
        return np.rint(255*np.clip(v*1.050,0,1)**(1/2.2)).astype(np.uint8)
    for r in regions:
        x,y=r["sensor_x"]-x0,r["sensor_y"]-y0
        a=patch[y:y+r["height"],x:x+r["width"]]
        for name,dx,dy,c in [("g1",1,0,1),("g2",0,1,3)]:
            v=(a[dy::2,dx::2].astype(np.float32)-black[c])/(white-black[c])
            Image.fromarray(display(v)).save(OUT/f"{r['name']}-{name}.png")
        np.save(OUT/f"{r['name']}-libraw-linear.npy",rgb[r["name"]],allow_pickle=False)
        Image.fromarray(display(rgb[r["name"]].astype(np.float32)/65535)).save(OUT/f"{r['name']}-libraw.png")
    assert (SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns)==original
    save(OUT/"receipt.json",dict(status="CHIP_SOURCE_READY",source=str(SOURCE),original_bytes=original[0],
        original_mtime_ns=original[1],original_metadata_unchanged=True,reference_index=149,
        reference_displacement_bound_native=residual,native_output_origin=[266,178],regions=regions,
        union_xywh=[x0,y0,x1-x0,y1-y0],decoder=meta,raw_u16_sha256=hashlib.sha256(patch.tobytes()).hexdigest(),
        independent_decode_different_sensels=different,
        display="Source fixed gain1.050, gamma1/2.2, round8; native RGB1:1; G192x192 at original same-colour pitch2. No spatial resampling.",
        developer="LibRaw AHD cameraWB sRGBlinear, no auto brightness; differs from baseline colour/tone, qualitative only.",
        command="python -X faulthandler experiments/quality-september14/chip-source-review.py"))
    assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())<64<<20

def main():
    if "--child" in sys.argv:
        child();return
    OUT.mkdir(exist_ok=False)
    bounded=module("chip_source_bounded",ROOT/"experiments/m193c-output-grid/bounded-process.py")
    env,_=bounded.clean_environment(dict(OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",RAYON_NUM_THREADS="1").items())
    api=bounded.load_job_api(bounded.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
    result=bounded.run([sys.executable,"-X","faulthandler",str(Path(__file__)),"--child"],env,ROOT,
        OUT/"process.log",api=api,wall_seconds=90,cpu_seconds=60,log_bytes=1<<20,committed_bytes=2<<30)
    save(OUT/"process.json",result)
    print(json.dumps(dict(exit_code=result["exit_code"],error=result["error"],accounting=result["job_accounting"])))
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"]
    assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())<64<<20

if __name__=="__main__":main()
