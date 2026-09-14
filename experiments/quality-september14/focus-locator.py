"""Bounded original-frame locator; its focus score is never quality evidence."""
from pathlib import Path
import importlib.util
import json
import sys
import hashlib
import subprocess
import struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/"focus-locator-1"
BASE=HERE/"baseline-1"
SOURCE=Path("D:/personal/macro/requests/misc-diagnostic/3d-printer-piece-cpl")
REGIONS=[("fibre",3084,3100), ("junction",3434,2534)]

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

def inventory():
    return [dict(name=p.name,bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns)
            for p in sorted(SOURCE.iterdir()) if p.is_file()]

def child():
    import numpy as np
    import rawpy
    from scipy.ndimage import gaussian_filter,gaussian_filter1d
    from PIL import Image
    def score(plane):
        assert plane.ndim==2,"no frame axis in spatial filter"
        smooth=gaussian_filter(plane.astype(np.float32),1.2,mode="reflect")
        gy,gx=np.gradient(smooth)
        return float(np.mean(gx[4:-4,4:-4]**2+gy[4:-4,4:-4]**2,dtype=np.float64))
    # FIRST: disclose failure direction. Noise can raise this locator score.
    rng=np.random.default_rng(14092026)
    yy,xx=np.mgrid[:150,:150]
    flat=np.full((150,150),1000,dtype=np.float32)
    texture=flat+100*np.cos((xx+0.3*yy)*2*np.pi/12)
    values=dict(flat=score(flat),flat_noise_sigma10=score(flat+rng.normal(0,10,flat.shape)),
                flat_noise_sigma100=score(flat+rng.normal(0,100,flat.shape)),
                sharp_texture=score(texture),blurred_texture=score(gaussian_filter(texture,5)))
    assert values["flat"]==0 and values["flat_noise_sigma100"]>values["flat_noise_sigma10"]>0
    assert values["sharp_texture"]>values["blurred_texture"]
    assert values["flat_noise_sigma100"]>values["blurred_texture"]
    save(OUT/"controls.json",dict(status="PASS",values=values,
        failure_input="A noisy flat patch can outscore a blurred real pattern; sigma100 control must demonstrate this.",
        interpretation="Locator only. Score rises with noise, contrast and structure; no image quality or calibrated noise claim.",
        spatial_filter="2D plane gaussian sigma1.2; np.gradient; interior pooled energy. No frame axis passed to a spatial filter."))
    clib=module("locator_existing_map",ROOT/"experiments/M-PHASE0-PHASE/src/clib.py")
    map_path=BASE/"printer.warpmap.txt"
    warp=clib.parse_warpmap(str(map_path))
    assert warp["reference_index"]==52 and warp["plane"]==(3516,2344)
    before=inventory()
    save(OUT/"originals-before.json",before)
    assert [r["name"] for r in before if r["name"].lower().endswith(".arw")]==[f"DSC{i:05}.ARW" for i in range(1,106)]
    cached={}
    first=json.loads((HERE/"source-review-1/receipt.json").read_text())
    cached[52]=(HERE/"source-review-1/source-visible-union.npy",first["raw_union_xywh"])
    for r in json.loads((HERE/"source-review-2/receipt.json").read_text())["records"]:
        cached[r["frame_index"]]=(HERE/f"source-review-2/frame-{r['frame_index']}-raw.npy",r["raw_union_xywh"])
    # u16 storage only. 37.8 MB total, containing no full decoded frame.
    patches=np.lib.format.open_memmap(OUT/"native-cfa-patches.npy",mode="w+",dtype="uint16",shape=(105,2,300,300))
    records=[]
    scores=np.zeros((105,2),dtype=np.float64)
    for index in range(105):
        a,b=warp["placements"][index]
        rois=[]
        for name,x,y in REGIONS:
            mx,my=clib.apply_at(a,b,(x+96+150)/2,(y+64+150)/2,1758,1172)
            sx,sy=int(round((2*mx-150)/2))*2,int(round((2*my-150)/2))*2
            rois.append(dict(name=name,source_xywh=[sx,sy,300,300],reference_output_xywh=[x,y,300,300]))
        if index in cached:
            path,(ox,oy,_,_)=cached[index]
            union=np.load(path,allow_pickle=False,mmap_mode="r")
            for k,r in enumerate(rois):
                x,y,w,h=r["source_xywh"]
                patches[index,k]=union[y-oy:y-oy+h,x-ox:x-ox+w]
            del union
        else:
            with rawpy.imread(str(SOURCE/f"DSC{index+1:05}.ARW")) as raw:
                assert raw.raw_pattern.tolist()==[[0,1],[3,2]]
                for k,r in enumerate(rois):
                    x,y,w,h=r["source_xywh"]
                    # Copy each bounded patch while LibRaw still owns its view.
                    patches[index,k]=raw.raw_image_visible[y:y+h,x:x+w].copy()
        for k,r in enumerate(rois):
            g1=patches[index,k,0::2,1::2].astype(np.float32)
            # Frozen within-patch supports: winding strand above the large
            # lower flap; junction's lower bright edge. These locate those marks.
            support=g1[5:80,4:145] if k==0 else g1[90:145,4:145]
            scores[index,k]=score(support)
        records.append(dict(frame_index=index,rois=rois,scale=abs(a),rotation_radians=float(np.angle(a)),cache_reused=index in cached))
        if index%20==0 or index==104:
            print(json.dumps(dict(stage="locate",frame=index)),flush=True)
    patches.flush()
    # Intentional frame-axis smoothing of TWO SCALAR score curves only.
    smoothed=gaussian_filter1d(scores,sigma=2,axis=0,mode="nearest")
    selected={}
    for k,(name,_,_) in enumerate(REGIONS):
        peak=int(np.argmax(smoothed[:,k]))
        neighbor=peak+2 if peak+2<105 else peak-2
        selected[name]=[peak,neighbor]
    save(OUT/"locator.json",dict(records=records,score_curves=scores.tolist(),smoothed_score_curves=smoothed.tolist(),
        nominations=selected,frame_smoothing="gaussian1d sigma2 axis0 on pooled scalar curves only",
        supports_green_xywh=dict(fibre=[4,5,141,75],junction=[4,90,141,55]),
        map_sha256=hashlib.sha256(map_path.read_bytes()).hexdigest(),
        purpose="Only nominate a focus neighbourhood for visual inspection; no pixelwise winner, no quality claim."))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(8,5),layout="constrained")
    for k,(name,_,_) in enumerate(REGIONS):
        axes[k].plot(scores[:,k],color="0.7",label="spatially pooled locator")
        axes[k].plot(smoothed[:,k],color="#175b8e",label="scalar curve smoothed over frames")
        for idx in selected[name]:axes[k].axvline(idx,color="#cc7733",linestyle=":")
        axes[k].set_title(name+": candidate focus neighbourhood only")
        axes[k].set_ylabel("locator score")
    axes[0].legend(fontsize=7)
    axes[1].set_xlabel("zero-based frame index")
    fig.suptitle("Noise and contrast can raise this score. Not image-quality evidence.",fontsize=10)
    fig.savefig(OUT/"focus-neighbourhoods.png",dpi=130)
    plt.close(fig)
    def display(v):
        return np.rint(255*np.clip(v*2.809,0,1)**(1/2.2)).astype(np.uint8)
    comparisons=[]
    secondary=ROOT/"experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe"
    for index in sorted(set(sum(selected.values(),[]))):
        chosen=[k for k,(name,_,_) in enumerate(REGIONS) if index in selected[name]]
        rois=[records[index]["rois"][k] for k in chosen]
        x0=min(r["source_xywh"][0] for r in rois);y0=min(r["source_xywh"][1] for r in rois)
        x1=max(r["source_xywh"][0]+300 for r in rois);y1=max(r["source_xywh"][1]+300 for r in rois)
        path=SOURCE/f"DSC{index+1:05}.ARW"
        result=subprocess.run([str(secondary),str(path),str(OUT),str(index),str(y0),str(x0),str(y1-y0),str(x1-x0)],
            capture_output=True,text=True,check=True,timeout=15)
        (OUT/f"selected-{index}-secondary.log").write_text(result.stdout+result.stderr,encoding="utf-8")
        blob=(OUT/f"rawler-{index}.bin").read_bytes()
        assert struct.unpack("<4I",blob[:16])==(y0,x0,y1-y0,x1-x0)
        other=np.frombuffer(blob,dtype="<u2",offset=16).reshape(y1-y0,x1-x0)
        for k in chosen:
            x,y,w,h=records[index]["rois"][k]["source_xywh"]
            different=int(np.count_nonzero(patches[index,k]!=other[y-y0:y-y0+h,x-x0:x-x0+w]))
            assert different==0,"independent decode mismatch"
            comparisons.append(dict(frame_index=index,region=REGIONS[k][0],different_sensels=different))
        with rawpy.imread(str(path)) as raw:
            black=list(raw.black_level_per_channel);white=raw.white_level
            for k in chosen:
                x,y,w,h=records[index]["rois"][k]["source_xywh"]
                assert np.array_equal(raw.raw_image_visible[y:y+h,x:x+w],patches[index,k])
            developed=raw.postprocess(use_camera_wb=True,no_auto_bright=True,output_bps=16,
                gamma=(1,1),output_color=rawpy.ColorSpace.sRGB,demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
            for k in chosen:
                name=REGIONS[k][0]
                x,y,w,h=records[index]["rois"][k]["source_xywh"]
                rgb=developed[y:y+h,x:x+w].astype(np.float32)/65535
                Image.fromarray(display(rgb)).save(OUT/f"frame-{index}-{name}-libraw.png")
                for label,dx,dy,c in [("g1",1,0,1),("g2",0,1,3)]:
                    v=(patches[index,k,dy::2,dx::2].astype(np.float32)-black[c])/(white-black[c])
                    Image.fromarray(display(v)).save(OUT/f"frame-{index}-{name}-{label}.png")
            del developed
        print(json.dumps(dict(stage="selected_ready",frame=index,regions=[REGIONS[k][0] for k in chosen])),flush=True)
    after=inventory()
    assert before==after,"original inventory changed"
    save(OUT/"completion.json",dict(status="FOCUS_NEIGHBOURHOODS_READY",nominations=selected,
        independent_decode_checks=comparisons,original_inventory_unchanged=True,
        new_locator_decodes=101,cached_originals_reused=[26,52,78,104],
        selected_frame_postprocesses=len(set(sum(selected.values(),[]))),
        display="Sources fixed gain2.809 gamma1/2.2; native RGB1:1. Green150x150 is original same-colour pitch2. No image resampling.",
        source_scales_retained=True))
    assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())<64<<20

def main():
    if "--child" in sys.argv:
        child();return
    OUT.mkdir(exist_ok=False)
    bounded=module("locator_bounded",ROOT/"experiments/m193c-output-grid/bounded-process.py")
    env,_=bounded.clean_environment(dict(OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",RAYON_NUM_THREADS="1").items())
    api=bounded.load_job_api(bounded.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
    result=bounded.run([sys.executable,"-X","faulthandler",str(Path(__file__)),"--child"],env,ROOT,
        OUT/"process.log",api=api,wall_seconds=180,cpu_seconds=120,log_bytes=2<<20,committed_bytes=2<<30)
    save(OUT/"process.json",result)
    print(json.dumps(dict(exit_code=result["exit_code"],error=result["error"],accounting=result["job_accounting"])))
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"]
    assert sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())<64<<20

if __name__=="__main__":main()
