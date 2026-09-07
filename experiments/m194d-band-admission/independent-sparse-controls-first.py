"""Independent pure sparse-reader commissioning, with no image render.

Choice points fixed before first execution: 4x7 non-square arrays, eight
irregularly masked sites, decreasing native x coordinates, nonconstant truth,
signed/tied residual lists, an error sign flip with no change in absolute error,
a moved isolated error preserving all marginal error statistics, and manual
linear interpolation versus the separately preregistered nearest-rank tail.
Malformed coordinates must not silently wrap to int64; complex samples must
not silently discard their imaginary component. Finite values whose residual
overflows must refuse rather than return nonfinite evidence.
"""
import copy
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import warnings

import numpy as np

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def linear(values,probability):
    ordered=sorted(abs(float(v)) for v in values)
    position=probability*(len(ordered)-1)
    lower=position.numerator//position.denominator
    upper=min(lower+1,len(ordered)-1)
    return ordered[lower]+float(position-lower)*(ordered[upper]-ordered[lower])


def close(a,b):return abs(float(a)-float(b))<1e-10


def main():
    source=HERE/"sparse-error.py";source_before=sha(source)
    spec=importlib.util.spec_from_file_location("m194d_independent_sparse_subject",source)
    subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
    yy,xx=np.indices((4,7));x=300-2*xx;y=100+3*yy
    mask=np.zeros((4,7),bool)
    sites=[(0,1),(0,5),(1,0),(1,3),(2,2),(2,6),(3,1),(3,4)]
    for j,i in sites:mask[j,i]=True
    reference=np.stack([1000+7*xx+11*yy+c*19 for c in range(3)],axis=-1).astype(float)
    errors=np.array([[-9,-4,0],[0,3,-30],[2,-6,5],[-9,8,30],[6,0,-2],[11,8,6],[-11,-6,-8],[23,1,30]],float)
    rgb=reference.copy();rgb[mask]+=errors
    original_bytes=[a.tobytes() for a in [rgb,reference,mask,x,y]]
    checks=[];details={};malformed=[]
    def record(name,fn):
        try:value=fn();passed=bool(value)
        except Exception as e:checks.append(dict(name=name,pass_=False,error=f"{type(e).__name__}: {e}"));return
        checks.append(dict(name=name,pass_=passed))
    def point(array,index,c):
        j,i=sites[index]
        return dict(native_xy=[int(x[j,i]),int(y[j,i])],value_dn=float(array[j,i,c]),truth_dn=float(reference[j,i,c]),signed_error_dn=float(array[j,i,c]-reference[j,i,c]))
    summary=subject.summarize(rgb,reference,mask,x,y)
    details["summary"]=summary
    def summary_exact():
        assert summary["mask_pixels"]==8 and summary["quantile_method"]=="linear" and summary["tie"]=="first row-major site"
        for c,row in enumerate(summary["channels"]):
            vals=errors[:,c].tolist()
            imin=min(range(8),key=lambda k:vals[k]);imax=max(range(8),key=lambda k:vals[k]);iabs=max(range(8),key=lambda k:abs(vals[k]))
            assert row["channel"]=="RGB"[c]
            assert row["minimum_signed_error"]==point(rgb,imin,c)
            assert row["maximum_signed_error"]==point(rgb,imax,c)
            assert row["maximum_absolute_error"]==point(rgb,iabs,c)
            assert close(row["absolute_error_p99_dn"],linear(vals,Fraction(99,100)))
            assert close(row["absolute_error_p999_dn"],linear(vals,Fraction(999,1000)))
        return True
    record("known-signed-tied-residual-lists-and-manual-linear-quantiles",summary_exact)
    nearest=[sorted(abs(float(v)) for v in errors[:,c])[-1] for c in range(3)]
    details["nearest_rank_p999_dn"]=nearest
    record("nearest-rank-alternate-is-explicitly-distinct",lambda:nearest[0]==23 and close(summary["channels"][0]["absolute_error_p999_dn"],22.916) and nearest[0]!=summary["channels"][0]["absolute_error_p999_dn"])
    outside=rgb.copy();outside[~mask]=np.nan
    outside_reference=reference.copy();outside_reference[~mask]=np.inf
    outside_x=x.astype(float);outside_x[~mask]=np.nan
    record("outside-mask-values-and-coordinates-are-inert",lambda:subject.summarize(outside,outside_reference,mask,outside_x,y)==summary)
    old_error=np.array([[30,-12,0],[5,0,0],[-8,5,0],[5,-5,0],[-2,8,0],[0,8,0],[12,1,0],[-4,0,0]],float)
    new_error=np.array([[-30,-2,5],[20,14,-9],[-1,15,0],[20,-15,9],[-10,8,2],[0,3,0],[4,1,1],[-4,0,0]],float)
    baseline=reference.copy();candidate=reference.copy();baseline[mask]+=old_error;candidate[mask]+=new_error
    comparison=subject.compare(candidate,baseline,reference,mask,x,y);details["comparison"]=comparison
    def compare_exact():
        for c,row in enumerate(comparison["channels"]):
            old=old_error[:,c].tolist();new=new_error[:,c].tolist()
            change=[abs(n)-abs(o) for n,o in zip(new,old)];movement=[n-o for n,o in zip(new,old)]
            for name,index in [("maximum_absolute_error_change",max(range(8),key=lambda k:change[k])),
                               ("minimum_absolute_error_change",min(range(8),key=lambda k:change[k])),
                               ("largest_absolute_output_movement",max(range(8),key=lambda k:abs(movement[k])))]:
                j,i=sites[index]
                wanted=dict(native_xy=[int(x[j,i]),int(y[j,i])],baseline_dn=float(baseline[j,i,c]),candidate_dn=float(candidate[j,i,c]),
                            truth_dn=float(reference[j,i,c]),baseline_signed_error_dn=old[index],candidate_signed_error_dn=new[index],
                            absolute_error_change_dn=change[index],output_movement_dn=movement[index])
                assert row[name]==wanted
        return True
    record("paired-signs-ties-and-largest-movement-do-not-mean-harm",compare_exact)
    record("sixty-DN-sign-flip-has-zero-absolute-error-change",lambda:comparison["channels"][0]["largest_absolute_output_movement"]["output_movement_dn"]==-60 and comparison["channels"][0]["largest_absolute_output_movement"]["absolute_error_change_dn"]==0)
    null=subject.compare(rgb,rgb.copy(),reference,mask,x,y)
    record("same-output-exact-null",lambda:all(p["absolute_error_change_dn"]==p["output_movement_dn"]==0 and p["native_xy"]==[298,100] for r in null["channels"] for n,p in r.items() if n!="channel"))
    isolated_old=reference.copy();isolated_new=reference.copy()
    isolated_old[sites[0]][0]+=20;isolated_new[sites[-1]][0]+=20
    isolated=subject.compare(isolated_new,isolated_old,reference,mask,x,y)
    record("moved-isolated-error-preserves-marginals-but-exposes-harm",lambda:np.array_equal(np.sort((isolated_old-reference)[mask,0]),np.sort((isolated_new-reference)[mask,0])) and isolated["channels"][0]["maximum_absolute_error_change"]["absolute_error_change_dn"]==20 and isolated["channels"][0]["maximum_absolute_error_change"]["native_xy"]==[292,109] and isolated["channels"][0]["minimum_absolute_error_change"]["absolute_error_change_dn"]==-20)
    improved=subject.compare(reference+1,reference+9,reference,mask,x,y)
    record("all-improving-maximum-remains-negative",lambda:all(r["maximum_absolute_error_change"]["absolute_error_change_dn"]==-8 for r in improved["channels"]))
    worse=subject.compare(reference+9,reference+1,reference,mask,x,y)
    record("all-worsening-minimum-remains-positive",lambda:all(r["minimum_absolute_error_change"]["absolute_error_change_dn"]==8 for r in worse["channels"]))
    record("source-input-arrays-unchanged",lambda:original_bytes==[a.tobytes() for a in [rgb,reference,mask,x,y]])
    valid=[rgb,reference,mask,x,y]
    def bad(name,index,value,operation="summarize"):
        inputs=[a.copy() for a in valid];inputs[index]=value
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                if operation=="summarize":subject.summarize(*inputs)
                else:subject.compare(inputs[0],baseline,*inputs[1:])
            except (ValueError,TypeError,OverflowError) as e:row=dict(name=name,rejected=True,error=f"{type(e).__name__}: {e}")
            else:row=dict(name=name,rejected=False)
            row["warnings"]=[str(w.message) for w in caught]
        malformed.append(row)
    bad("wrong-RGB-shape",0,rgb[:,:,:2]);bad("wrong-reference-shape",1,reference[:-1])
    bad("integer-mask",2,mask.astype(int));bad("empty-mask",2,np.zeros_like(mask));bad("wrong-mask-shape",2,mask[:,:-1])
    bad("wrong-coordinate-shape",3,x[:-1])
    for label,index,value in [("RGB-nan",0,np.nan),("truth-infinity",1,np.inf),("coordinate-nan",3,np.nan),("coordinate-fraction",3,.25),("coordinate-outside-int64",3,1e30)]:
        a=valid[index].astype(float).copy();a[sites[0]]=value;bad(label,index,a)
    complex_rgb=rgb.astype(complex);complex_rgb[sites[0]]+=3j;bad("complex-samples-must-not-lose-imaginary-part",0,complex_rgb)
    complex_x=x.astype(complex);complex_x[sites[0]]+=3j;bad("complex-coordinates-must-not-lose-imaginary-part",3,complex_x)
    bad("compare-nonfinite-candidate",0,np.full_like(rgb,np.inf),"compare")
    huge=np.full_like(rgb,1e308);negative=-huge
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:subject.summarize(huge,negative,mask,x,y)
        except (ValueError,TypeError,OverflowError) as e:malformed.append(dict(name="finite-input-residual-overflow",rejected=True,error=f"{type(e).__name__}: {e}"))
        else:malformed.append(dict(name="finite-input-residual-overflow",rejected=False,warnings=[str(w.message) for w in caught]))
    unchanged=sha(source)==source_before
    out=dict(schema="m194d-independent-sparse-controls-v1",pass_=all(c["pass_"] for c in checks) and all(r["rejected"] for r in malformed) and unchanged,
             source_sha256=source_before,source_unchanged=unchanged,script_sha256=sha(__file__),checks=checks,malformed=malformed,details=details,
             scope="pure API controls; malformed out-of-domain numeric values do not describe actual bounded u16 benchmark data")
    (HERE/"independent-sparse-controls.json").write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:out[k] for k in ["pass_","source_sha256","checks","malformed"]},indent=2));assert out["pass_"]


if __name__=="__main__":main()
