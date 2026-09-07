"""Closed finite-repeat reference for paired whole-image uncertainty."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent


def main():
    spec=importlib.util.spec_from_file_location("independent_paired_subject",HERE/"score.py")
    score=importlib.util.module_from_spec(spec);spec.loader.exec_module(score)
    # Nine deliberately asymmetric repeat scalars, new dimensions and mask.
    k=np.array([-3.,-2.,-1.,0.,.5,1.,2.,4.,7.])
    n=len(k);shape=(19,27,3)
    y,x=np.indices(shape[:2]);mask=(x+3*y)%4!=0
    target=np.full(shape,3000.)
    ca=np.array([2.,.5,3.]);cb=np.array([1.,2.,-1.]);ba=np.array([1.,-4.,2.]);bb=np.array([-3.,1.,4.])
    aa=ba+k[:,None]*ca;bc=bb+k[:,None]*cb
    a=target+aa[:,None,None,:];b=target+bc[:,None,None,:]
    got=score.paired_error(a,b,target,mask)
    deltas=aa*aa-bc*bc
    mean=deltas.sum(axis=0)/n
    sem=np.sqrt(((deltas-mean)**2).sum(axis=0)/(n*(n-1)))
    k_variance=((k*k).sum()-k.sum()**2/n)/(n-1)
    variance_delta=k_variance*(ca*ca-cb*cb)
    loo=[]
    for omitted in k:
        total=k.sum()-omitted;squares=(k*k).sum()-omitted**2
        loo.append((squares-total**2/(n-1))/(n-2)*(ca*ca-cb*cb))
    loo=np.array(loo);jack=np.sqrt((n-1)/n*((loo-loo.sum(axis=0)/n)**2).sum(axis=0))
    checks={"paired-finite-deltas":np.max(abs(np.asarray(got["repeat_mse_difference_dn2"])-deltas))<1e-9,
            "paired-finite-mean":np.max(abs(np.asarray(got["mean_mse_difference_dn2"])-mean))<1e-9,
            "paired-finite-SEM":np.max(abs(np.asarray(got["mse_difference_sem_dn2"])-sem))<1e-9,
            "finite-temporal-variance-difference":np.max(abs(np.asarray(got["temporal_variance_difference_dn2"])-variance_delta))<1e-9,
            "finite-leave-one-out-variance":np.max(abs(np.asarray(got["leave_one_out_variance_difference_dn2"])-loo))<1e-9,
            "finite-jackknife-uncertainty":np.max(abs(np.asarray(got["variance_difference_jackknife_se_dn2"])-jack))<1e-9}
    null=score.paired_error(a,a,target,mask)
    checks["identical-arm-null"]=max(abs(v) for key in ["mean_mse_difference_dn2","mse_difference_sem_dn2","temporal_variance_difference_dn2","variance_difference_jackknife_se_dn2"] for v in null[key])==0
    wrong=score.paired_error(a,b[::-1],target,mask)
    checks["pair-permutation-preserves-marginal-mean"]=np.max(abs(np.asarray(wrong["mean_mse_difference_dn2"])-mean))<1e-9
    checks["pair-permutation-changes-uncertainty"]=np.max(abs(np.asarray(wrong["mse_difference_sem_dn2"])-sem))>1
    checks={key:bool(value) for key,value in checks.items()}
    result=dict(schema="m194b-independent-paired-v1",pass_=all(checks.values()),checks=checks,
                scorer_sha256=hashlib.sha256((HERE/"score.py").read_bytes()).hexdigest(),expected=dict(mean=mean.tolist(),sem=sem.tolist(),variance_delta=variance_delta.tolist(),jackknife=jack.tolist()),actual=got,
                scope="finite component uncertainty under matched repeats; jackknife is not a calibrated eight-repeat confidence interval")
    (HERE/"independent-paired.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(pass_=result["pass_"],checks=checks)));assert result["pass_"]


if __name__=="__main__":main()
