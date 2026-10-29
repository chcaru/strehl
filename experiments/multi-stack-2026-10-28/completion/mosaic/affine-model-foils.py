"""Training-only source-coordinate model foils on saved native measurements."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='4'
import numpy as np
parser=argparse.ArgumentParser()
parser.add_argument('native',type=Path)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
raw=args.native.read_bytes()
accepted=[r for r in json.loads(raw) if r['accepted']]
fits=[r for r in accepted if r['candidate']['role']=='fit']
held=[r for r in accepted if r['candidate']['role']=='heldout']
def coordinates(rows):
    return (np.array([r['candidate']['point_a_quad'] for r in rows]),
            np.array([r['refined_b_quad'] for r in rows]),
            np.array([r['candidate']['source_a']/339 for r in rows]))
x,y,z=coordinates(fits);hx,hy,hz=coordinates(held)
results=[]
for name in ['affine','affine_focus','affine_focus_squared']:
    def design(x,z):
        cols=[x[:,0]/3516,x[:,1]/2344,np.ones(len(x))]
        if name!='affine':cols+=[z]
        if name.endswith('squared'):cols+=[z*z]
        return np.array(cols).T
    d=design(x,z)
    coefficients=np.linalg.lstsq(d,y,rcond=None)[0]
    error=np.linalg.norm(d@coefficients-y,axis=1)
    validation=np.linalg.norm(design(hx,hz)@coefficients-hy,axis=1)
    loo=[]
    for i in range(len(fits)):
        keep=np.arange(len(fits))!=i
        model=np.linalg.lstsq(d[keep],y[keep],rcond=None)[0]
        loo.append(float(np.linalg.norm(d[i]@model-y[i])))
    results.append({'model':name,'coefficients':coefficients.tolist(),
                    'fit_rms_quad':float(np.sqrt(np.mean(error**2))),
                    'heldout_errors_quad':validation.tolist(),
                    'leave_one_out_rms_quad':float(np.sqrt(np.mean(np.array(loo)**2))),
                    'leave_one_out_errors_quad':loo})
receipt={'schema':'strehl.mosaic-native-model-foils.v1','argv':sys.argv,
         'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'input_sha256':hashlib.sha256(raw).hexdigest(),'models':results,
         'fit_ids':[r['candidate']['id'] for r in fits],'heldout_ids':[r['candidate']['id'] for r in held],
         'coordinate_units':'pass-anchor native green quads; source ordinal divided by339 for conditioning only, not metric depth',
         'limitations':'All native-accepted receipts from the specified older arm are used, before stricter physical-support independence. These diagnostic foils are not production geometry, do not change admission, and cannot certify an image. Heldouts never fit any coefficient.'}
with args.out.open('x') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
print(json.dumps([{k:v for k,v in r.items() if k not in ['coefficients','leave_one_out_errors_quad']} for r in results],indent=2))
