"""Independent M25 API-scope challenge; no optics or complete-render claim.

Predeclared choices: 17x26 arrays, asymmetric ramp with spatially distinct RGB,
order=1, identity, translation(+2,-1), rotation(-.07rad) about (10.25,6.75).
Scalar transforms must execute with finite same-shape changed outputs; RGB
identity must pass while both nonidentity calls must refuse with shape unpack.
Failure of either direction rejects this narrow scope conclusion.
"""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT/'experiments/m25-simulator/src/strehl_sim/render.py'
SCENE = ROOT/'experiments/m25-simulator/src/strehl_sim/scene.py'
digest = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before = {str(p.relative_to(ROOT)):digest(p) for p in (SOURCE,SCENE)}
sys.path.insert(0,str(SOURCE.parents[1]))
from strehl_sim.render import similarity_warp

y,x = np.mgrid[:17,:26].astype(float)
scalar = x+3*y
rgb = np.stack([scalar,x*x+y,2*x-y*y],axis=-1)
rows = []
for name,tx,ty,theta in [('identity',0.,0.,0.),('translation',2.,-1.,0.),('rotation',0.,0.,-.07)]:
    for kind,array in [('scalar',scalar),('rgb',rgb)]:
        try:
            value = similarity_warp(array,1.,10.25,6.75,tx,ty,theta,1)
            assert kind=='scalar' or name=='identity', 'RGB nonidentity unexpectedly supported'
            assert value.shape==array.shape and np.isfinite(value).all()
            difference = float(np.max(np.abs(value-array)))
            if name=='identity':
                assert difference==0 and value is array
            else:
                assert difference>.01, 'scalar control did not actually warp'
            if name=='translation':
                assert np.max(np.abs(value[2:-2,3:-3]-(scalar[2:-2,3:-3]+1)))<1e-12
            rows.append(dict(kind=kind,arm=name,accepted=True,shape=list(value.shape),
                             max_absolute_change=difference))
        except ValueError as error:
            assert kind=='rgb' and name!='identity' and str(error)=='too many values to unpack (expected 2)'
            rows.append(dict(kind=kind,arm=name,accepted=False,error=str(error)))
assert before=={str(p.relative_to(ROOT)):digest(p) for p in (SOURCE,SCENE)}
result = dict(status='PASS',scope='Independent API dimensionality check only; no optics or full-render commission',
    source_hashes=before,independent_source_sha256=digest(Path(__file__)),
    command='python -B experiments/review-production-truth/independent-producer-scope.py',
    choices=dict(shape=[17,26],center=[10.25,6.75],scale=1.,order=1,
                 translation=[2.,-1.],rotation_radians=-.07),rows=rows,original_sources_unchanged=True)
(HERE/'independent-producer-scope.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
