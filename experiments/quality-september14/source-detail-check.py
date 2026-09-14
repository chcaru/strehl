"""Three named original frames, mapped native crops, no image resampling."""
from pathlib import Path
import importlib.util
import json
import sys
import subprocess
import struct
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "source-review-2"
MAP = HERE / "baseline-1/printer.warpmap.txt"
SOURCE_DIR = Path("D:/personal/macro/requests/misc-diagnostic/3d-printer-piece-cpl")
SECONDARY = ROOT / "experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe"
REGIONS = [("fibre",3084,3100), ("junction",3434,2534)]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

def child():
    import numpy as np
    import rawpy
    from PIL import Image
    clib = module("source_detail_existing_map", ROOT/"experiments/M-PHASE0-PHASE/src/clib.py")
    warp = clib.parse_warpmap(str(MAP))
    assert warp["reference_index"] == 52 and warp["plane"] == (3516,2344)
    def display(v):
        return np.rint(255*np.clip(v*2.809,0,1)**(1/2.2)).astype(np.uint8)
    records = []
    for number in (27,79,105):
        index = number-1
        source = SOURCE_DIR/f"DSC{number:05d}.ARW"
        original = (source.stat().st_size, source.stat().st_mtime_ns)
        a,b = warp["placements"][index]
        regions = []
        for name,x,y in REGIONS:
            # Native reference -> plane -> mapped source native. Centre only;
            # an integer native crop follows, with no scale/rotation correction.
            rx,ry = x+96,y+64
            mx,my = clib.apply_at(a,b,(rx+150)/2,(ry+150)/2,1758,1172)
            sx,sy = int(round((2*mx-150)/2))*2, int(round((2*my-150)/2))*2
            regions.append(dict(name=name,reference_output_xywh=[x,y,300,300],
                reference_sensor_xywh=[rx,ry,300,300], mapped_source_centre_native=[2*mx,2*my],
                source_sensor_xywh=[sx,sy,300,300]))
        x0=min(r["source_sensor_xywh"][0] for r in regions)
        y0=min(r["source_sensor_xywh"][1] for r in regions)
        x1=max(r["source_sensor_xywh"][0]+300 for r in regions)
        y1=max(r["source_sensor_xywh"][1]+300 for r in regions)
        w,h=x1-x0,y1-y0
        with rawpy.imread(str(source)) as raw:
            patch = raw.raw_image_visible[y0:y1,x0:x1].copy()
            pattern = raw.raw_pattern.copy().tolist()
            black = list(raw.black_level_per_channel)
            white = raw.white_level
            assert pattern == [[0,1],[3,2]]
            developed = raw.postprocess(use_camera_wb=True,no_auto_bright=True,output_bps=16,
                gamma=(1,1),output_color=rawpy.ColorSpace.sRGB,
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
            colour={r["name"]:developed[r["source_sensor_xywh"][1]:r["source_sensor_xywh"][1]+300,
                r["source_sensor_xywh"][0]:r["source_sensor_xywh"][0]+300].copy() for r in regions}
            del developed
        np.save(OUT/f"frame-{index}-raw.npy",patch,allow_pickle=False)
        result=subprocess.run([str(SECONDARY),str(source),str(OUT),str(index),str(y0),str(x0),str(h),str(w)],
            capture_output=True,text=True,check=True,timeout=15)
        (OUT/f"frame-{index}-secondary.log").write_text(result.stdout+result.stderr,encoding="utf-8")
        blob=(OUT/f"rawler-{index}.bin").read_bytes()
        assert struct.unpack("<4I",blob[:16])==(y0,x0,h,w)
        other=np.frombuffer(blob,dtype="<u2",offset=16).reshape(h,w)
        different=int(np.count_nonzero(patch!=other))
        assert different==0,"independent RAW decode mismatch"
        for r in regions:
            sx,sy,_,_=r["source_sensor_xywh"]
            local=patch[sy-y0:sy-y0+300,sx-x0:sx-x0+300]
            for name,dx,dy,c in [("g1",1,0,1),("g2",0,1,3)]:
                signal=(local[dy::2,dx::2].astype(np.float32)-black[c])/(white-black[c])
                Image.fromarray(display(signal)).save(OUT/f"frame-{index}-{r['name']}-{name}.png")
            Image.fromarray(display(colour[r["name"]].astype(np.float32)/65535)).save(
                OUT/f"frame-{index}-{r['name']}-libraw.png")
        assert (source.stat().st_size,source.stat().st_mtime_ns)==original
        records.append(dict(frame_index=index,source=str(source),original_bytes=original[0],
            original_mtime_ns=original[1],regions=regions,raw_union_xywh=[x0,y0,w,h],
            independent_decode_different_sensels=different,raw_u16_sha256=hashlib.sha256(patch.tobytes()).hexdigest(),
            frame_scale=abs(a),rotation_radians=float(np.angle(a)),a=[a.real,a.imag],b=[b.real,b.imag],
            decoder_black=black,decoder_white=white))
        print(json.dumps(dict(frame=index,status="PATCHES_READY",scale=abs(a))),flush=True)
        assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()) <= 100<<20
    existing=json.loads((HERE/"baseline-1/views/crops.json").read_text())["regions"]
    for name,x,y in REGIONS:
        old=next(r for r in existing if r["name"]==name)
        dx,dy=x-old["x"],y-old["y"]
        for arm,source in [("baseline",HERE/f"baseline-1/views/{name}.png"),
                           ("frame-52",HERE/f"source-review-1/{name}-libraw.png")]:
            Image.open(source).crop((dx,dy,dx+300,dy+300)).save(OUT/f"{arm}-{name}-libraw.png")
    save(OUT/"receipt.json",dict(status="SOURCE_DETAIL_CROPS_READY",records=records,
        map_sha256=hashlib.sha256(MAP.read_bytes()).hexdigest(),reference_index=52,
        display="Sources: fixed gain2.809, power1/2.2, round8; LibRaw AHD cameraWB sRGBlinear, no auto brightness. Baseline: existing product tone.",
        sampling="Native RGB1:1; green each150x150 at original CFA pitch2; rounded-even source crop centre only; no image resampling",
        interpretation="Different frame scales are retained. No sharpness metric or best-frame argmax. Visual feature existence/separation/continuity only."))

def main():
    if "--child" in sys.argv:
        child()
        return
    OUT.mkdir(exist_ok=False)
    bounded=module("source_detail_bounded",ROOT/"experiments/m193c-output-grid/bounded-process.py")
    env,removed=bounded.clean_environment(dict(OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",RAYON_NUM_THREADS="1").items())
    api=bounded.load_job_api(bounded.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
    result=bounded.run([sys.executable,"-X","faulthandler",str(Path(__file__)),"--child"],env,ROOT,
        OUT/"process.log",api=api,wall_seconds=60,cpu_seconds=30,log_bytes=1<<20,committed_bytes=2<<30)
    save(OUT/"process.json",result)
    print(json.dumps(dict(exit_code=result["exit_code"],error=result["error"],accounting=result["job_accounting"])))
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"]
    assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()) <= 100<<20

if __name__=="__main__":
    main()
