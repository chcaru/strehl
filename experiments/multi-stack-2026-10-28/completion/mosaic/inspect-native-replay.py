"""Read actual native observations; local-affine fit is diagnostic, not admission."""
import argparse
import json
import os
from pathlib import Path
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "4"
import numpy as np
parser=argparse.ArgumentParser()
parser.add_argument("input",type=Path)
parser.add_argument("output",type=Path)
args=parser.parse_args()
data=json.loads(args.input.read_text())
output=[]
for item in data["measurements"]:
    models=[]; summaries=[]
    for direction in ("forward","reverse"):
        trace=item[direction]
        stage=trace["passes"][trace["selected_fine_pass"]]
        observations=np.array([t["observation"] for t in stage["tiles"] if t["observation"] is not None])
        if stage["kept"] is not None:
            observations=observations[np.array(stage["kept"],dtype=bool)]
        center=observations[:,:2].mean(axis=0)
        x=np.column_stack((np.ones(len(observations)),observations[:,:2]-center))
        y=observations[:,2:]
        fit=np.linalg.lstsq(x,y,rcond=None)[0]
        rms=float(np.sqrt(np.mean(np.sum((x@fit-y)**2,axis=1))))
        loo=[]
        for i in range(len(x)):
            keep=np.arange(len(x))!=i
            alternative=np.linalg.lstsq(x[keep],y[keep],rcond=None)[0]
            loo.append(float(np.linalg.norm(x[i]@alternative-y[i])))
        derivative=np.eye(2)+fit[1:].T
        summaries.append(dict(affine_fit_rms_quad=rms,affine_loo_rms_quad=float(np.sqrt(np.mean(np.array(loo)**2))),affine_loo_max_quad=max(loo),jacobian=float(np.linalg.det(derivative)),singular_values=np.linalg.svd(derivative,compute_uv=False).tolist(),observations=len(x)))
        models.append((np.array(stage["plane_center"]),center,fit))
    def apply(model,p):
        origin,center,fit=model
        return p+np.array([1.,*(p-origin-center)])@fit
    p=np.array(item["native_points"][0]);q=apply(models[0],p);back=apply(models[1],q)
    record=dict(id=item["id"],role=item["role"],sources=item["sources"],similarity_rms_quad=item["rms"],similarity_reciprocal_quad=item["reciprocal_quad"],affine=summaries,affine_reciprocal_quad=float(np.linalg.norm(back-p)))
    output.append(record)
    print(item["id"], "sim",[round(x,3) for x in item["rms"]], "aff",[round(s["affine_fit_rms_quad"],3) for s in summaries], "loo",[round(s["affine_loo_rms_quad"],3) for s in summaries], "reciprocal",round(record["affine_reciprocal_quad"],3))
with args.output.open("x") as stream:
    json.dump(dict(semantics="Read-only local-affine fits to observed native tile measurements. No native threshold or production model changed; a fitted residual is not an independent geometry certificate.",measurements=output),stream,indent=2)
    stream.write("\n")
