"""Independent literal Catmull-Rom sampler controls; no RAW or mean execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import time
import numpy as np

HERE = Path(__file__).resolve().parent
AUTHOR = HERE/"mhc-catmul-mean.py"
started = time.process_time()
binding = hashlib.sha256(AUTHOR.read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location("independent_mean_sampler",AUTHOR)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
sample = subject.catmull_sample
records = []


def check(name,image,positions,expected,exact=False):
    actual = sample(image,np.asarray(positions,dtype=np.float64))
    expected = np.asarray(expected,dtype=np.float32)
    assert actual.shape==expected.shape and actual.dtype==np.float32
    error = float(np.max(np.abs(actual-expected)))
    bound = 0.0 if exact else float(8*np.finfo(np.float32).eps*max(1,float(np.max(np.abs(expected)))))
    assert error<=bound, f"{name}: error{error} exceeds{bound}"
    records.append(dict(name=name,maximum_error=error,bound=bound,actual=actual.tolist(),expected=expected.tolist()))


y,x = np.mgrid[:8,:11]
image = np.stack((100*y+7*x+1,-2*y+3*x+4,.25*y-.5*x+.75),axis=-1).astype(np.float32)
check("integer identity, asymmetric RGB",image,[[1,1],[5,3],[8,5]],
      [[108,5,.5],[336,13,-1],[557,18,-2]],exact=True)
literal_half = [-1/16,9/16,9/16,-1/16]
for axis in ("x","y"):
    for tap,weight in enumerate(literal_half):
        impulse = np.zeros((8,11,3),dtype=np.float32)
        if axis=="x":
            impulse[3,2+tap] = [1,2,4]
            position = [[3.5,3]]
        else:
            impulse[2+tap,3] = [1,2,4]
            position = [[3,3.5]]
        check(f"literal half-step {axis} tap{tap}",impulse,position,[[weight,2*weight,4*weight]],exact=True)
positions = np.array([[1.13,1.71],[3.5,2.25],[6.81,4.33],[8.999,5.999]],dtype=np.float64)
constant = np.broadcast_to(np.array([.125,.375,1.25],dtype=np.float32),(8,11,3)).copy()
check("constant reproduction",constant,positions,[[.125,.375,1.25]]*len(positions))
affine = np.stack((2+.25*x-.125*y,-1+.375*x+.0625*y,4-.5*x+.75*y),axis=-1).astype(np.float32)
px,py = positions[:,0],positions[:,1]
expected_affine = np.column_stack((2+.25*px-.125*py,-1+.375*px+.0625*py,4-.5*px+.75*py))
check("independent affine formula",affine,positions,expected_affine)
# At y-fraction1/4, literal weights are [-9,111,29,-3]/128;
# at x-fraction1/2 they are [-1,9,9,-1]/16. Distinct channel impulses
# and unequal x/y fractions reject both axis swaps and channel permutations.
asymmetric = np.zeros((8,11,3),dtype=np.float32)
asymmetric[1,4,0] = 1
asymmetric[3,2,1] = 2
asymmetric[4,5,2] = 8
check("asymmetric xy/channel impulses",asymmetric,[[3.5,2.25],[6.25,4.5]],
      [[-81/2048,-58/2048,24/2048],[0,0,-648/2048]],exact=True)
refusals = []
for position in ([.999,3],[9,3],[3,.999],[3,6],[float("nan"),3],[3,float("inf")]):
    try:
        sample(constant,np.array([position],dtype=np.float64))
    except AssertionError:
        refusals.append([str(v) if not np.isfinite(v) else v for v in position])
    else:
        raise AssertionError(f"incomplete/invalid support was accepted:{position}")
assert len(refusals)==6
assert hashlib.sha256(AUTHOR.read_bytes()).hexdigest()==binding
elapsed = time.process_time()-started
assert elapsed<60
result = dict(status="INDEPENDENT_CATMULL_SAMPLER_PASS",source=str(AUTHOR),source_sha256=binding,
    tests=records,refused_positions=refusals,cpu_seconds=elapsed,
    scope="catmull_sample only, exact literal half/quarter weights and independent affine truth; no RAW or mean run; source unchanged")
with (HERE/"mhc-catmull-sampler-controls-1.json").open("x",encoding="utf-8") as stream:
    json.dump(result,stream,indent=2,allow_nan=False)
    stream.write("\n")
print(json.dumps(dict(status=result["status"],passed=len(records),refusals=len(refusals),cpu_seconds=elapsed,source_sha256=binding)))
