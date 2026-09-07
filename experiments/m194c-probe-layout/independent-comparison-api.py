"""Independently chosen finite controls for the new comparison API."""
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent


def main():
    spec=importlib.util.spec_from_file_location("independent_m194c_api",HERE/"compare-candidate.py")
    subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
    y,x=np.indices((13,17));mask=(2*x+y)%3!=0
    old=np.full((13,17,3),2000.)+np.stack([x,y,2*x-y],axis=-1)
    new=old.copy()
    inside=list(zip(*np.where(mask)));outside=list(zip(*np.where(~mask)))
    new[inside[0]] += [2,-3,4]
    new[inside[1]] += [-1,0,2]
    new[outside[0]] += [11,13,-17]
    result=subject.pixel_delta(new,old,mask)
    count=int(mask.sum())
    checks={"whole-image-and-mask-counts-separate":result["changed_components"]==8 and result["roi_changed_components"]==5 and result["components"]==13*17*3,
            "whole-image-max-includes-outside-ROI":result["max_abs_dn_by_channel"]==[11.,13.,17.],
            "signed-ROI-movement":np.max(abs(np.array(result["roi_mean_delta_dn_by_channel"])-np.array([1,-3,6])/count))<1e-12,
            "ROI-RMS-movement":np.max(abs(np.array(result["roi_rms_delta_dn_by_channel"])-np.sqrt(np.array([5,9,20])/count)))<1e-12}
    null=subject.pixel_delta(old.copy(),old,mask)
    checks["same-output-exact-null"]=null["changed_components"]==0 and null["roi_changed_components"]==0 and null["roi_rms_delta_dn_by_channel"]==[0,0,0]
    shift=subject.pixel_delta(old+20,old,mask)
    checks["known20DN-offset"]=shift["roi_mean_delta_dn_by_channel"]==[20,20,20] and shift["roi_rms_delta_dn_by_channel"]==[20,20,20]
    k=np.array([-4,-2,-1,0,.5,1,2,5,8.]);n=len(k)
    ag=np.array([.5,2.,-1.]);bg=np.array([1.,.25,3.]);ab=np.array([2.,-1.,4.]);bb=np.array([-1.,3.,.5])
    a=old[None]+(k[:,None]*ag+ab)[:,None,None,:]
    b=old[None]+(k[:,None]*bg+bb)[:,None,None,:]
    paired=subject.version_paired(a,b,old,mask)
    delta=(k[:,None]*ag+ab)**2-(k[:,None]*bg+bb)**2
    mean=delta.sum(axis=0)/n
    sem=np.sqrt(((delta-mean)**2).sum(axis=0)/(n*(n-1)))
    checks["across-version-direction-label"]=paired["direction"]=="M194c candidate minus M194b baseline, same arm and input repeats"
    checks["paired-version-mean-sign"]=np.max(abs(np.array(paired["mean_mse_difference_dn2"])-mean))<1e-9
    checks["paired-whole-repeat-SEM"]=np.max(abs(np.array(paired["mse_difference_sem_dn2"])-sem))<1e-9
    paired_null=subject.version_paired(a,a,old,mask)
    checks["paired-version-exact-null"]=paired_null["mean_mse_difference_dn2"]==[0,0,0] and paired_null["mse_difference_sem_dn2"]==[0,0,0]
    rejected=[]
    for name,fn in [("empty-mask",lambda:subject.pixel_delta(new,old,np.zeros_like(mask))),
                    ("shape-mismatch",lambda:subject.pixel_delta(new[:-1],old,mask)),
                    ("nonfinite",lambda:subject.pixel_delta(new*np.nan,old,mask)),
                    ("paired-two-repeats",lambda:subject.version_paired(a[:2],b[:2],old,mask))]:
        try:fn()
        except ValueError:rejected.append(name)
    checks["four-malformed-refusals"]=len(rejected)==4
    checks={key:bool(value) for key,value in checks.items()}
    out=dict(schema="m194c-independent-comparison-api-v1",pass_=all(checks.values()),checks=checks,
             subject_sha256=subject.S.sha256(HERE/"compare-candidate.py"),pixel_delta=result,paired=paired,rejected=rejected)
    (HERE/"independent-comparison-api.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(dict(pass_=out["pass_"],checks=checks)));assert out["pass_"]


if __name__=="__main__":main()
