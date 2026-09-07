"""Difference-readout live controls on retained M194b TIFF samples."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
import tifffile

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/"m194b-known-scene"


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def moments(a,reference):
    d=np.asarray(a,dtype=float)-reference
    count=np.prod(d.shape[:-1])
    return dict(bias_dn=d.sum(axis=(0,1))/count,mse_dn2=(d*d).sum(axis=(0,1))/count)


def difference(before,after,reference):
    a=moments(before,reference);b=moments(after,reference)
    return dict(bias_dn=b["bias_dn"]-a["bias_dn"],mse_dn2=b["mse_dn2"]-a["mse_dn2"],
                rmse_dn=np.sqrt(b["mse_dn2"])-np.sqrt(a["mse_dn2"]))


def temporal_variance(frames):
    mean=np.zeros_like(frames[0],dtype=float);m2=np.zeros_like(mean)
    for n,value in enumerate(frames,1):
        delta=value-mean;mean+=delta/n;m2+=delta*(value-mean)
    return m2.mean(axis=(0,1))/(len(frames)-1)


def wave_projection(a,fx,fy):
    y,x=np.indices(a.shape[:2],dtype=float);x+=64;y+=64
    return 2*np.mean(a*np.exp(-2j*np.pi*(fx*x+fy*y))[...,None],axis=(0,1))


def main():
    index_path=PREVIOUS/"baseline-1/run-index.json"
    index_sha="37f99736bd32dfb4891bd8fa2b033cacc2c58e9265515fa53cb5921dd80d9c08"
    assert sha(index_path)==index_sha
    index=json.loads(index_path.read_text());case=next(c for c in index["cases"] if c["scene"]=="plane" and c["repeat"] is None)
    arm=next(a for a in case["arms"] if a["name"]=="full9")
    receipt=json.loads((index_path.parent/arm["receipt_path"]).read_text());path=Path(receipt["output"]["path"])
    before=sha(path)
    pixels=tifffile.imread(path)
    real=pixels[50:162,46:238].astype(float)*14848/65535
    assert real.shape==(112,192,3)
    checks={};records={}
    null=difference(real,real,real)
    checks["same-actual-array-exact-zero"]=all(np.array_equal(v,np.zeros(3)) for v in null.values())
    offset=difference(real,real+20,real)
    checks["signed20DN-offset"]=np.max(abs(offset["bias_dn"]-20))<1e-9 and np.max(abs(offset["mse_dn2"]-400))<1e-9
    blurred=gaussian_filter(real,sigma=(.6,.6,0),mode="wrap")
    response_before=wave_projection(real,1/8,-1/16);response_after=wave_projection(blurred,1/8,-1/16)
    checks["spatial-blur-moves-actual-wave"]=np.min(abs(response_before)-abs(response_after))>1
    flat=np.full_like(real,3000.)
    checks["flat-blur-exact-inert"]=np.max(abs(gaussian_filter(flat,sigma=(.6,.6,0),mode="wrap")-flat))<1e-9
    # Use actual analytic-color pixels for a live channel permutation.
    cc=next(c for c in index["cases"] if c["scene"]=="color")
    ca=next(a for a in cc["arms"] if a["name"]=="full9")
    cr=json.loads((index_path.parent/ca["receipt_path"]).read_text())
    color=tifffile.imread(cr["output"]["path"])[50:162,46:238].astype(float)*14848/65535
    permutation=difference(color,color[...,::-1],color)
    checks["actual-color-swap-moves-RB-error"]=min(permutation["mse_dn2"][[0,2]])>1 and permutation["mse_dn2"][1]==0
    # An exactly centred eight-repeat perturbation has closed sample variance.
    k=np.arange(8,dtype=float)-3.5;gain=np.array([1.,2.,4.])
    clean=np.repeat(flat[None],8,axis=0);noisy=clean+k[:,None,None,None]*gain
    got=temporal_variance(noisy)-temporal_variance(clean)
    expected=(k*k).sum()/7*gain*gain
    checks["independent-repeat-noise-variance-difference"]=np.max(abs(got-expected))<1e-9
    records["offset"]={k:v.tolist() for k,v in offset.items()}
    records["blur_amplitude_before"]=abs(response_before).tolist();records["blur_amplitude_after"]=abs(response_after).tolist()
    records["color_permutation_mse_difference"]=permutation["mse_dn2"].tolist();records["temporal_variance_difference"]=got.tolist()
    checks["original-artifacts-unchanged"]=sha(index_path)==index_sha and sha(path)==before
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(schema="m194c-independent-comparison-controls-v1",pass_=all(checks.values()),checks=checks,
                script_sha256=sha(Path(__file__)),baseline_index_sha256=index_sha,source_tiff_sha256=before,
                records=records,scope="difference-instrument controls on private arrays, not replacement candidate outputs")
    (HERE/"independent-comparison-controls.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result));assert result["pass_"]


if __name__=="__main__":main()
