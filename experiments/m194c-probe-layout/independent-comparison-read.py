"""Independent actual-pixel comparison of the complete fixed version pair."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/"m194b-known-scene"
SEEDS=[701,709,719,727,733,739,743,751]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def path_at(p,root):return Path(p) if Path(p).is_absolute() else root/p


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--candidate-index",type=Path,required=True);ap.add_argument("--index-sha",required=True);ap.add_argument("--comparison",type=Path,required=True);ap.add_argument("--comparison-sha",required=True);args=ap.parse_args()
    assert sha(args.candidate_index)==args.index_sha and sha(args.comparison)==args.comparison_sha
    old_path=BASE/"baseline-1/run-index.json";old_sha="37f99736bd32dfb4891bd8fa2b033cacc2c58e9265515fa53cb5921dd80d9c08"
    assert sha(old_path)==old_sha
    authored=load(args.comparison)
    spec=importlib.util.spec_from_file_location("m194c_independent_integral",BASE/"independent-optics.py")
    optics=importlib.util.module_from_spec(spec);spec.loader.exec_module(optics)
    spec=importlib.util.spec_from_file_location("m194c_independent_moments",HERE/"independent-comparison-controls.py")
    stats=importlib.util.module_from_spec(spec);spec.loader.exec_module(stats)
    expected={(scene,seed,arm) for scene in ["flat","plane"] for seed in [None]+SEEDS for arm in ["full9","single4"]}|{(scene,None,arm) for scene in ["color","color-null"] for arm in ["full9","single4"]}
    signatures={};arrays={};hashes={}
    for version,index_path in [("before",old_path),("after",args.candidate_index)]:
        index=load(index_path);assert index["status"]=="complete"
        for case in index["cases"]:
            plan_path=path_at(case["plan_path"],index_path.parent);assert sha(plan_path)==case["plan_sha256"]
            plan=load(plan_path);assert plan["crop_quad"]==dict(x=9,y=7,width=142,height=106)
            plan_comparable={key:value for key,value in plan.items() if key not in {"software"}}
            for arm in case["arms"]:
                key=(case["scene"],case["repeat"],arm["name"])
                assert key in expected and (version,key) not in arrays
                signature=dict(manifest_sha256=case["manifest_sha256"],plan=plan_comparable)
                if version=="before":signatures[key]=signature
                else:assert signature==signatures[key],f"changed actual input/config: {key}"
                rp=path_at(arm["receipt_path"],index_path.parent);assert sha(rp)==arm["receipt_sha256"]
                receipt=load(rp);p=Path(receipt["output"]["path"])
                hashes[str(p)]=sha(p);assert hashes[str(p)]==receipt["output"]["sha256"]
                pixels=tifffile.imread(p);assert pixels.dtype==np.uint16 and pixels.shape==(212,284,3)
                arrays[(version,key)]=pixels.astype(float)*14848/65535
        assert {k for v,k in arrays if v==version}==expected
    x,y=np.meshgrid(np.arange(64,256,dtype=float),np.arange(64,176,dtype=float))
    nodes,weights=np.polynomial.legendre.leggauss(32)
    scalar=np.array([.75*float(np.float32(4/3)),1.,.6*float(np.float32(5/3))])*.25
    def wave(amp,fx,fy,phase,kind):
        if kind=="observation":
            o=(np.arange(4)+.5)/4-.5
            cell=sum(np.exp(2j*np.pi*(fx*a+fy*b)) for a in o for b in o)/16
            transfer=optics.pupil_overlap(np.hypot(fx,fy),5.12/(.535*16))
        else:
            cell=sum(wa*wb*np.exp(1j*np.pi*(fx*a+fy*b)) for a,wa in zip(nodes,weights) for b,wb in zip(nodes,weights))/4;transfer=1.
        return amp*transfer*np.real(cell*np.exp(1j*(2*np.pi*(fx*x+fy*y)+phase)))
    def target(scene,kind):
        if scene=="flat":return np.full((*x.shape,3),12000.)*scalar
        if scene=="plane":return (12000+wave(1800,1/16,1/24,.2,kind)+wave(900,1/8,-1/16,1.1,kind))[...,None]*scalar
        lum=3000+wave(450,.08,.03,.2,kind)+wave(180,.19,-.07,1.1,kind)
        c=wave(240,.11,.04,.8,kind) if scene=="color" else 0
        q=wave(120,.05,-.09,2.,kind) if scene=="color" else 0
        return np.stack([lum+c,lum+q,lum-c],axis=-1)
    roi=lambda a:a[50:162,46:238]
    root_rows={(r["scene"],r["repeat"],r["arm"]):r for r in authored["rows"]}
    assert set(root_rows)==expected
    rows=[];paired=[];triggers=[];maximum=dict(rmse=0.,wave=0.,pixel=0.,variance=0.,paired_mean=0.,paired_sem=0.,jackknife=0.)
    for key in sorted(expected,key=str):
        before=arrays[("before",key)];after=arrays[("after",key)];a,b=roi(after),roi(before)
        d=after-before;rd=a-b;r=root_rows[key]
        assert r["pixels"]["changed_components"]==int(np.count_nonzero(d))
        assert r["pixels"]["roi_changed_components"]==int(np.count_nonzero(rd))
        pixel_rms=np.sqrt(np.einsum("yxc,yxc->c",rd,rd)/(112*192))
        maximum["pixel"]=max(maximum["pixel"],float(np.max(abs(pixel_rms-r["pixels"]["roi_rms_delta_dn_by_channel"]))))
        item=dict(scene=key[0],repeat=key[1],arm=key[2],changed_components=int(np.count_nonzero(d)),roi_pixel_rms_dn=pixel_rms.tolist())
        for kind in (["ideal","observation"] if key[0] in ["flat","plane"] else ["ideal"]):
            delta=stats.difference(b,a,target(key[0],kind))
            maximum["rmse"]=max(maximum["rmse"],float(np.max(abs(delta["rmse_dn"]-r[kind+"_rmse_change_dn"]))))
            item[kind]={name:value.tolist() for name,value in delta.items()}
            if max(delta["rmse_dn"])>1:triggers.append((key,kind,"rmse"))
        if key[0]=="plane":
            values=[]
            for i,(fx,fy) in enumerate([(1/16,1/24),(1/8,-1/16)]):
                pa=stats.wave_projection(a,fx,fy);pb=stats.wave_projection(b,fx,fy)
                amp=abs(pa)-abs(pb);phase=np.angle(pa*np.conj(pb))
                maximum["wave"]=max(maximum["wave"],float(np.max(abs(amp-r["wave_amplitude_change_dn"][i]))))
                values.append(dict(amplitude_change_dn=amp.tolist(),phase_change_rad=phase.tolist()))
                if key[1] is None and min(amp)<-1:triggers.append((key,i,"wave"))
            item["waves"]=values
        rows.append(item)
    for scene in ["flat","plane"]:
        for arm in ["full9","single4"]:
            a=np.stack([roi(arrays[("after",(scene,seed,arm))]) for seed in SEEDS]);b=np.stack([roi(arrays[("before",(scene,seed,arm))]) for seed in SEEDS])
            av=stats.temporal_variance(a);bv=stats.temporal_variance(b);vd=av-bv;ratio=av/bv
            if max(ratio)>1.02:triggers.append(((scene,arm),None,"variance"))
            for kind in ["ideal","observation"]:
                ref=target(scene,kind)
                each=np.stack([stats.difference(bb,aa,ref)["mse_dn2"] for aa,bb in zip(a,b)])
                mean=each.sum(axis=0)/8;sem=np.sqrt(((each-mean)**2).sum(axis=0)/(8*7))
                loo=np.stack([stats.temporal_variance(np.delete(a,i,axis=0))-stats.temporal_variance(np.delete(b,i,axis=0)) for i in range(8)])
                jack=np.sqrt(7/8*((loo-loo.mean(axis=0))**2).sum(axis=0))
                r=next(r for r in authored["paired"] if (r["scene"],r["arm"],r["target"])==(scene,arm,kind))["difference"]
                for name,value,rootkey in [("variance",vd,"temporal_variance_difference_dn2"),("paired_mean",mean,"mean_mse_difference_dn2"),("paired_sem",sem,"mse_difference_sem_dn2"),("jackknife",jack,"variance_difference_jackknife_se_dn2")]:maximum[name]=max(maximum[name],float(np.max(abs(value-r[rootkey]))))
                paired.append(dict(scene=scene,arm=arm,target=kind,mse_difference_dn2=mean.tolist(),mse_difference_sem_dn2=sem.tolist(),temporal_variance_difference_dn2=vd.tolist(),variance_ratio=ratio.tolist(),variance_jackknife_se_dn2=jack.tolist()))
    checks=dict(complete80_actual_TIFF_reads=len(arrays)==80,matched_actual_inputs_and_plans=True,
                rmse_agreement=maximum["rmse"]<.001,wave_agreement=maximum["wave"]<1e-8,pixel_agreement=maximum["pixel"]<1e-8,
                temporal_variance_agreement=maximum["variance"]<1e-8,paired_mean_agreement=maximum["paired_mean"]<.001,
                paired_sem_agreement=maximum["paired_sem"]<.001,jackknife_agreement=maximum["jackknife"]<1e-8,
                engineering_trigger_count_agrees=len(triggers)==len(authored["engineering_review_triggers"]),
                actual_bytes_unchanged=sha(args.candidate_index)==args.index_sha and sha(old_path)==old_sha and all(sha(p)==h for p,h in hashes.items()))
    out=dict(schema="m194c-independent-comparison-read-v1",pass_=all(checks.values()),checks=checks,max_disagreements=maximum,candidate_index_sha256=args.index_sha,comparison_sha256=args.comparison_sha,rows=rows,paired=paired,independent_engineering_triggers=triggers,scope="same-input actual-pixel differences under fixed synthetic model, not general quality admission")
    (HERE/"independent-comparison-read.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(dict(pass_=out["pass_"],checks=checks,max_disagreements=maximum,triggers=triggers)));assert out["pass_"]


if __name__=="__main__":main()
