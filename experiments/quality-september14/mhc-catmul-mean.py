"""Eight retained RAW patches, MHC then Catmull-Rom gather and running RGB mean.

Comparator only: this is not the product pyramid or a censored estimator. It
keeps only the current unaligned source RGB and two output means. No RAW reads.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "mhc-catmul-mean-2"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _weights(f):
    """Explicit Catmull-Rom alpha=-.5, same f32 order as core align.rs."""
    f = np.asarray(f, dtype=np.float32)
    f2, f3 = f*f, f*f*f
    return np.column_stack((np.float32(-.5)*f3+f2-np.float32(.5)*f,
        np.float32(1.5)*f3-np.float32(2.5)*f2+np.float32(1),
        np.float32(-1.5)*f3+np.float32(2)*f2+np.float32(.5)*f,
        np.float32(.5)*f3-np.float32(.5)*f2))


def catmull_sample(rgb, xy):
    """Nx2 local source (x,y) centres -> Nx3 f32 rows, complete4x4 support.

    Refuses outside points rather than inventing border coverage. No spatial
    image resampling library, clamping, renormalization, or channel mixing.
    """
    rgb, xy = np.asarray(rgb), np.asarray(xy)
    assert rgb.dtype == np.float32 and rgb.ndim == 3 and rgb.shape[2] == 3
    assert xy.dtype == np.float64 and xy.ndim == 2 and xy.shape[1] == 2 and np.isfinite(xy).all()
    h, w = rgb.shape[:2]
    assert (xy[:,0] >= 1).all() and (xy[:,0] < w-2).all()
    assert (xy[:,1] >= 1).all() and (xy[:,1] < h-2).all()
    base = np.floor(xy).astype(np.int32)
    wx, wy = _weights(xy[:,0]-base[:,0]), _weights(xy[:,1]-base[:,1])
    result = np.zeros((len(xy),3), dtype=np.float32)
    for dy in range(4):
        row = np.zeros_like(result)
        for dx in range(4):
            row += rgb[base[:,1]+dy-1, base[:,0]+dx-1] * wx[:,dx,None]
        result += row * wy[:,dy,None]
    return result


def normalized_mosaic(raw, x, y, wb, black, inv_range):
    yy, xx = np.indices(raw.shape, dtype=np.int32)
    xx += x
    yy += y
    channels = np.where((xx+yy)%2==1,1,np.where(yy%2==0,0,2))
    result = np.maximum(raw.astype(np.float32)-black,np.float32(0))*wb[channels]*inv_range
    return result, channels


def child():
    import tifffile
    from PIL import Image
    started = time.process_time()
    rawdir = HERE / "joint-raw-samples-2"
    rawreceipt = rawdir / "receipt.json"
    localpath = HERE / "local-green-translation-1/result.json"
    mhcpath = ROOT / "experiments/M95-demosaic/src/m95dem.py"
    pins = {str(path):digest(path) for path in (rawreceipt,localpath,mhcpath,HERE/"joint-inputs.py")}
    receipt = json.loads(rawreceipt.read_text())
    local = json.loads(localpath.read_text())
    assert local["source_map_sha256"] == receipt["map_sha256"]
    assert digest(HERE/"chip-baseline-1/chip.warpmap.txt") == receipt["map_sha256"]
    corrections = {r["frame"]:r for r in local["frames"]}
    mhc = module("mean_m95dem",mhcpath).demosaic_mhc
    h,w = receipt["target_shape"]
    origin = complex(*receipt["target_origin_native"])
    sensor_h,sensor_w = receipt["native_sensor_shape"]
    center = complex(sensor_w/2,sensor_h/2)
    wb = np.asarray(receipt["wb_bits"],dtype="<u4").view("<f4")
    black,white = np.asarray(receipt["levels"],dtype=np.float32)
    inv_range = np.float32(1)/(white-black)
    means = {name:np.zeros((h,w,3),np.float32) for name in ("original-map-eight-mean","local-map-eight-mean")}
    frames = [r for r in receipt["frames"] if 146<=r["index"]<=153]
    assert [r["index"] for r in frames] == list(range(146,154))
    coverage=[]; known_comparison=None
    for count,frame in enumerate(frames,1):
        index=frame["index"]
        row=corrections[index]
        assert row["converged"] and not row["at_translation_bound"]
        if index!=149: assert row["validation_ratio"]<1
        delta=complex(*row["delta_source_native"])
        if index==149: assert delta==0
        rawpath=rawdir/f"frame-{index}-cfa.npy"
        raw=np.load(rawpath,allow_pickle=False)
        assert raw.dtype==np.uint16 and hashlib.sha256(raw.tobytes()).hexdigest()==frame["raw_u16_sha256"]
        x0,y0,sw,sh=frame["source_xywh"]
        assert raw.shape==(sh,sw) and x0%2==y0%2==0
        mosaic,phase=normalized_mosaic(raw,x0,y0,wb,black,inv_range)
        source=mhc(mosaic)
        assert np.array_equal(source[np.indices(raw.shape)[0],np.indices(raw.shape)[1],phase],mosaic)
        if index==149:
            ox,oy=receipt["target_origin_native"]
            target_mosaic=mosaic[oy-y0:oy-y0+h,ox-x0:ox-x0+w]
            reference=mhc(target_mosaic)
            actual=np.fromfile(HERE/"matched-chip-on-1/pale-circuit-frame149-raw-mhc-camera-rgb.f32",dtype="<f4").reshape(h,w,3)
            difference=reference.astype("f8")-actual
            yy,xx=np.indices((h,w)); target_phase=np.where((xx+yy)%2==1,1,np.where(yy%2==0,0,2))
            known=np.count_nonzero(reference[yy,xx,target_phase]!=actual[yy,xx,target_phase])
            # The held observer divides by range; joint-inputs multiplies by
            # the rounded reciprocal. Preserve the latter in both means and
            # expose that f32 discrepancy rather than calling it demosaic error.
            cutraw=raw[oy-y0:oy-y0+h,ox-x0:ox-x0+w]
            held_mosaic=np.maximum(cutraw.astype(np.float32)-black,np.float32(0))*wb[target_phase]/(white-black)
            held_reference=mhc(held_mosaic)
            held_known=np.count_nonzero(held_reference[yy,xx,target_phase]!=actual[yy,xx,target_phase])
            assert held_known==0
            held_difference=held_reference.astype("f8")-actual
            known_comparison=dict(maximum_absolute_f32_difference=float(np.abs(difference).max()),
                rms_difference=float(np.sqrt(np.mean(difference*difference))),
                different_f32_channels=int(np.count_nonzero(difference)),
                known_cfa_site_differences_due_to_normalization_order=int(known),known_cfa_sites=h*w,
                same_normalization_known_cfa_site_differences=int(held_known),
                same_normalization_mhc_maximum_absolute_difference=float(np.abs(held_difference).max()),
                same_normalization_mhc_rms_difference=float(np.sqrt(np.mean(held_difference*held_difference))),
                own_normalized_cfa_site_identity_exact=True,
                scope="Same392x392 source extent and mirror boundary. Means retain joint-inputs rounded-reciprocal normalization; held observer uses division. Separate same-normalization comparison isolates M95 SciPy versus actual Rust convolution f32 rounding.")
            reference.astype("<f4",copy=False).tofile(OUT/"source149-m95-mhc-camera-rgb.f32")
        a,b=complex(*frame["a"]),complex(*frame["b_plane"])
        gaps=[]
        for y in range(h):
            ref=origin+np.arange(w,dtype=np.float64)+1j*y
            position=center+a*(ref-center)+2*b-complex(x0,y0)
            for name,shift in (("original-map-eight-mean",0),("local-map-eight-mean",delta)):
                z=position+shift
                xy=np.column_stack((z.real,z.imag))
                #4x4 Catmull plus MHC's2px support remains inside retained RAW.
                gap=min(float(xy[:,0].min()),float(xy[:,1].min()),float(sw-1-xy[:,0].max()),float(sh-1-xy[:,1].max()))
                assert gap>=4
                gaps.append(gap)
                gathered=catmull_sample(source,xy)
                means[name][y] += (gathered-means[name][y])/np.float32(count)
        coverage.append(dict(frame=index,minimum_source_border_distance_native=min(gaps),pixels_per_arm=h*w,delta_source_native=[delta.real,delta.imag]))
        print(f"frame{index}: both means updated",flush=True)
        del source,mosaic,raw
    candidates=[]
    for name,image in means.items():
        assert np.isfinite(image).all()
        path=OUT/(name+"-camera-rgb.f32")
        image.astype("<f4",copy=False).tofile(path)
        candidates.append(dict(name=name,rgb=str(path)))
    cfg=json.loads((HERE/"joint-local-comparison-1/render-config.json").read_text())
    cfg["out"]=str(OUT/"render");cfg["candidates"]=candidates
    save(OUT/"render-config.json",cfg)
    exe=HERE/"patch-render-build-2/saved-rgb-render.exe"
    assert digest(exe)=="3fea4f37deeb5935406d47e050276d72cf9eec5c624f268963b67d4a63f2ea49"
    command=[str(exe),str(OUT/"render-config.json")]
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    (OUT/"render.log").write_text(result.stdout+result.stderr,encoding="utf-8")
    assert result.returncode==0,result.stderr
    development=json.loads((OUT/"render/receipt.json").read_text())
    assert development["baseline_differing_u16_samples"]==0
    for name in development["outputs"]:
        image=tifffile.imread(OUT/"render"/(name+".tiff"))[32:-32,32:-32]
        assert image.shape==(328,328,3)
        Image.fromarray((image.astype(np.uint32)*255//65535).astype(np.uint8)).save(OUT/"render"/(name+"-native.png"))
    assert all(digest(Path(path))==sha for path,sha in pins.items())
    save(OUT/"receipt.json",dict(status="EIGHT_FRAME_MHC_CATMULL_MEANS_COMPLETE",source_pins=pins,
        source_frames=list(range(146,154)),target_origin_native=receipt["target_origin_native"],shape=[h,w],trim=32,
        source149_mhc_comparison=known_comparison,coverage=coverage,cpu_seconds=time.process_time()-started,
        render_command=command,baseline_product_differing_u16_samples=0,
        scope="Eight-frame RGB mean comparator, not the actual product pyramid. All source values including pins retained; no CA correction, fitted photometric gain/bias, noise weighting, or focus selection. Local source delta is added after original pull map. Float32 streaming means; no aligned frame collection."))


def main():
    if "--child" in sys.argv:
        child();return
    OUT.mkdir(exist_ok=False)
    bounded=module("mean_bounded",ROOT/"experiments/m193c-output-grid/bounded-process.py")
    env,_=bounded.clean_environment(dict(OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",RAYON_NUM_THREADS="1").items())
    api=bounded.load_job_api(bounded.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
    command=[sys.executable,"-I","-B","-X","faulthandler",str(Path(__file__)),"--child"]
    result=bounded.run(command,env,ROOT,OUT/"process.log",api=api,wall_seconds=60,cpu_seconds=30,log_bytes=1<<20,committed_bytes=2<<30)
    save(OUT/"process.json",dict(command=command,result=result))
    print(json.dumps(dict(exit_code=result["exit_code"],error=result["error"],accounting=result["job_accounting"])))
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"]


if __name__=="__main__":main()
