"""Actual forty TIFFs against a different analytic integration/readout."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--index",type=Path,required=True);ap.add_argument("--sha256",required=True);ap.add_argument("--score",type=Path,required=True);args=ap.parse_args()
    path=args.index.resolve();assert sha(path)==args.sha256;index=json.loads(path.read_text());assert index["status"]=="complete"
    authored=json.loads(args.score.read_text())
    spec=importlib.util.spec_from_file_location("independent_baseline_optics",HERE/"independent-optics.py")
    optics=importlib.util.module_from_spec(spec);spec.loader.exec_module(optics)
    x,y=np.meshgrid(np.arange(64,256,dtype=float),np.arange(64,176,dtype=float))
    nodes,weights=np.polynomial.legendre.leggauss(32)
    wb=np.array([float(np.float32(4/3)),1.,float(np.float32(5/3))])
    scalar=np.array([.75,1.,.6])*.25*wb
    def wave(amp,fx,fy,phase,kind):
        if kind=="observation":
            offsets=(np.arange(4)+.5)/4-.5
            cell=sum(np.exp(2j*np.pi*(fx*a+fy*b)) for a in offsets for b in offsets)/16
            transfer=optics.pupil_overlap(np.hypot(fx,fy),5.12/(.535*16))
        else:
            cell=sum(w1*w2*np.exp(1j*np.pi*(fx*a+fy*b)) for a,w1 in zip(nodes,weights) for b,w2 in zip(nodes,weights))/4
            transfer=1
        return amp*transfer*np.real(cell*np.exp(1j*(2*np.pi*(fx*x+fy*y)+phase)))
    def target(scene,kind):
        if scene=="flat":return np.full((*x.shape,3),12000)*scalar
        if scene=="plane":
            return (12000+wave(1800,1/16,1/24,.2,kind)+wave(900,1/8,-1/16,1.1,kind))[...,None]*scalar
        lum=3000+wave(450,.08,.03,.2,kind)+wave(180,.19,-.07,1.1,kind)
        c=wave(240,.11,.04,.8,kind) if scene=="color" else 0
        q=wave(120,.05,-.09,2.,kind) if scene=="color" else 0
        return np.stack([lum+c,lum+q,lum-c],axis=-1)
    rows=[];stacks={};max_rmse_delta=0.;max_wave_delta=0.;hashes={}
    for case in index["cases"]:
        plan_path=Path(case["plan_path"]);plan_path=plan_path if plan_path.is_absolute() else path.parent/plan_path
        plan=json.loads(plan_path.read_text());assert plan["crop_quad"]==dict(x=9,y=7,width=142,height=106)
        for arm in case["arms"]:
            rp=Path(arm["receipt_path"]);rp=rp if rp.is_absolute() else path.parent/rp
            receipt=json.loads(rp.read_text());p=Path(receipt["output"]["path"])
            hashes[str(p)]=sha(p)
            with tifffile.TiffFile(p) as t:
                pixels=t.pages[0].asarray();assert pixels.dtype==np.uint16 and pixels.shape==(212,284,3)
            # Fixed native coordinates, explicitly subtract only output origin.
            roi=pixels[64-14:176-14,64-18:256-18,:].astype(float)*14848/65535
            assert roi.shape==(112,192,3)
            key=(case["scene"],case["repeat"],arm["name"])
            stacks[key]=roi
            reference_row=next(r for r in authored["rows"] if (r["scene"],r["repeat"],r["arm"])==key)
            item=dict(scene=key[0],repeat=key[1],arm=key[2],file_sha256=hashes[str(p)])
            for kind in (["ideal","observation"] if key[0] in ["flat","plane"] else ["ideal"]):
                delta=roi-target(key[0],kind)
                # Deliberately direct moments, independent of scorer.error.
                rmse=np.sqrt(np.einsum("yxc,yxc->c",delta,delta)/(112*192))
                bias=delta.sum(axis=(0,1))/(112*192)
                max_rmse_delta=max(max_rmse_delta,float(np.max(abs(rmse-reference_row[kind]["error"]["rmse_dn"]))))
                item[kind]=dict(rmse_dn=rmse.tolist(),bias_dn=bias.tolist())
            if key[0]=="plane":
                # Each wave completes an integer number of x cycles across
                # this ROI; direct complex projection is orthogonal here.
                waves=[]
                for n,(fx,fy) in enumerate([(1/16,1/24),(1/8,-1/16)]):
                    response=2*np.mean(roi*np.exp(-2j*np.pi*(fx*x+fy*y))[...,None],axis=(0,1))
                    amp=np.abs(response);phase=np.angle(response)
                    rootwave=reference_row["output_wave_response"]["waves"][n]
                    max_wave_delta=max(max_wave_delta,float(np.max(abs(amp-rootwave["amplitude_dn"]))))
                    waves.append(dict(amplitude_dn=amp.tolist(),phase_rad=phase.tolist()))
                item["independent_complex_projection"]=waves
            rows.append(item)
    summary={}
    max_variance_delta=0.
    for scene in ["flat","plane"]:
        summary[scene]={}
        for arm in ["full9","single4"]:
            # Streaming Welford temporal variance; the scene never enters a
            # spatial noise SD and pixels are not treated as independent draws.
            mean=np.zeros((112,192,3));m2=np.zeros_like(mean)
            for n,seed in enumerate([701,709,719,727,733,739,743,751],1):
                value=stacks[(scene,seed,arm)];d=value-mean;mean+=d/n;m2+=d*(value-mean)
            v=m2.mean(axis=(0,1))/7
            want=authored["summary"][scene]["observation"][arm]["temporal_variance_dn2"]
            max_variance_delta=max(max_variance_delta,float(np.max(abs(v-want))))
            summary[scene][arm]=dict(temporal_variance_dn2=v.tolist())
    checks={"actual-forty-unique-TIFFs":len(rows)==40 and len(hashes)==40,
            "independent-cell-reference-RMSE-agreement":max_rmse_delta<.001,
            "independent-complex-wave-amplitude-agreement":max_wave_delta<1e-8,
            "independent-Welford-temporal-variance-agreement":max_variance_delta<1e-8,
            "index-and-TIFF-bytes-unchanged":sha(path)==args.sha256 and all(sha(p)==h for p,h in hashes.items())}
    result=dict(schema="m194b-independent-baseline-read-v1",pass_=all(checks.values()),checks=checks,index_sha256=args.sha256,authored_score_sha256=sha(args.score),max_rmse_delta_dn=max_rmse_delta,max_wave_amplitude_delta_dn=max_wave_delta,max_temporal_variance_delta_dn2=max_variance_delta,rows=rows,summary=summary,scope="actual fixed-window numeric read under declared model; no camera calibration or SOTA ranking")
    (HERE/"independent-baseline-read.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(pass_=result["pass_"],checks=checks,max_rmse_delta=max_rmse_delta,max_wave_delta=max_wave_delta,max_variance_delta=max_variance_delta)));assert result["pass_"]


if __name__=="__main__":main()
