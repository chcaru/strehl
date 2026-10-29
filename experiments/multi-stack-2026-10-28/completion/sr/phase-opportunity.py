"""Geometry-only phase opportunity, bounded to one BLAS worker; no RAW reads."""
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[name] = '1'
import hashlib
import json
import math
from pathlib import Path
import struct
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def decode(hex_bits):
    return struct.unpack('>d', bytes.fromhex(hex_bits))[0]

def measure(phases, aliases):
    a = np.exp(2j * np.pi * (phases @ aliases.T))
    vals = np.linalg.svd(a, compute_uv=False)
    if len(vals) < len(aliases) or vals[-1] <= vals[0] * 1e-10:
        return {'rank': int(np.sum(vals > vals[0]*1e-10)), 'condition': None}
    return {'rank': len(aliases), 'condition': float(vals[0]/vals[-1])}

def aliases(axis):
    return np.array([(x,y) for x in range(axis) for y in range(axis)], dtype=float)

# Gate controls are measured before the real geometry. A perfect 2-D phase grid
# conditions four replicas; duplicates and a one-axis walk must remain singular.
controls = {}
for name, phases in [('grid_2d',[[0,0],[.5,0],[0,.5],[.5,.5]]), ('duplicate',[[0,0]]*8), ('x_only',[[k/8,0] for k in range(8)])]:
    controls[name] = measure(np.array(phases), aliases(2))
assert abs(controls['grid_2d']['condition']-1) < 1e-10
assert controls['duplicate']['rank'] == 1 and controls['duplicate']['condition'] is None
assert controls['x_only']['rank'] == 2 and controls['x_only']['condition'] is None

start = time.perf_counter()
alignment_path = ROOT/'outputs/multi-stack/full-geometry-2/alignment.json'
render_path = ROOT/'outputs/multi-stack/insect-repeat-7/render-report.json'
metadata_path = ROOT/'experiments/multi-stack-2026-10-28/corpus/inventory-table.md'
doc = json.loads(alignment_path.read_bytes())
render = json.loads(render_path.read_bytes())
geom = doc['report']['geometry_plane_pixels']
cx, cy = geom[0]*.5, geom[1]*.5 # Exact stored WarpMap fitting origin, not sample centroid
maps = {}
for line in doc['warpmap'].splitlines():
    words=line.split()
    if len(words)>=6 and words[0].isdigit() and words[1]=='placed':
        maps[int(words[0])] = [decode(v) for v in words[2:6]]
assert len(maps)==598
transforms=np.array([maps[i] for i in range(598)])
scales=np.hypot(transforms[:,0],transforms[:,1])
logs=np.log(scales)
# Fitted scale, not filename phase/focus assumptions. These are candidate
# neighborhoods only; actual sharpness/motion/clipping admission can reduce them.
anchors=list(range(0,299,10)) + [298]
points={'centre':[cx,cy], 'inner_x_300_sensels':[cx+150,cy], 'inner_y_300_sensels':[cx,cy+150], 'x_1000_sensels':[cx+500,cy], 'y_1000_sensels':[cx,cy+500], 'upper_left':[.1*geom[0],.1*geom[1]], 'upper_right':[.9*geom[0],.1*geom[1]], 'lower_left':[.1*geom[0],.9*geom[1]], 'lower_right':[.9*geom[0],.9*geom[1]]}
rows=[]
for anchor in anchors:
    for per_pass in [1,3,5,9]:
        each=[sorted(range(p*299,(p+1)*299),key=lambda i:abs(logs[i]-logs[anchor]))[:per_pass] for p in [0,1]]
        for scope,idx in [('first_pass',each[0]),('both_passes',each[0]+each[1])]:
            for point,(x,y) in points.items():
                t=transforms[idx]
                qx=t[:,0]*(x-cx)-t[:,1]*(y-cy)+t[:,2]+cx
                qy=t[:,1]*(x-cx)+t[:,0]*(y-cy)+t[:,3]+cy
                valid=(qx>=3)&(qy>=3)&(qx<geom[0]-4)&(qy<geom[1]-4)
                # The common CFA-site offset contributes only a column phase.
                # It does not change singular values. These are local pull-gauge
                # phases, an opportunity approximation under small scale/rotation.
                phases=np.column_stack([qx[valid],qy[valid]])
                for scale,axis in [(1.,2),(1.5,3),(2.,4)]:
                    result=measure(phases,aliases(axis)) if len(phases) else {'rank':0,'condition':None}
                    rows.append({'anchor':anchor,'per_pass':per_pass,'scope':scope,'point':point,'target_scale':scale,'required_rb_replicas':axis*axis,'geometry_supported_frames':int(valid.sum()),'candidate_indices':[idx[k] for k in np.flatnonzero(valid)],**result})
summary=[]
for scope in ['first_pass','both_passes']:
    for n in [1,3,5,9]:
        for scale in [1.,1.5,2.]:
            subset=[r for r in rows if r['scope']==scope and r['per_pass']==n and r['target_scale']==scale]
            finite=[r['condition'] for r in subset if r['condition'] is not None]
            summary.append({'scope':scope,'per_pass':n,'target_scale':scale,'cases':len(subset),'full_rank':len(finite),'condition_le_10':sum(c<=10 for c in finite),'condition_le_20':sum(c<=20 for c in finite),'condition_percentiles_full_rank':None if not finite else dict(zip(['p10','p50','p90'],map(float,np.percentile(finite,[10,50,90]))))})
frame_support={'frames':len(render['frames']),'minimum_covered_pixels':min(f['covered_pixels'] for f in render['frames']),'maximum_clipped_pixels':max(f['clipped_pixels'] for f in render['frames']),'frames_with_any_clipped_pixels':sum(f['clipped_pixels']>0 for f in render['frames']),'crop_plane_pixels':render['canvas']}
report={'schema':'strehl.sr-phase-opportunity.v1','elapsed_seconds':time.perf_counter()-start,'workers':1,'numpy':np.__version__,'inputs':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in [alignment_path,render_path,metadata_path]],'controls':controls,'reference_frame':doc['report']['reference_frame'],'geometry_plane_pixels':geom,'points_plane_pixels':points,'phase_convention':'source pull evaluated in green-luma quad gauge, site-centre phase offset does not change singular values','scope':'Geometry-only optimistic opportunity. Fitted-scale neighborhoods are not validated sharp sets. No per-pixel clipping, focus, motion, optical-bandwidth, registration-error or radiometric weights are available here. No quality or SR gain claim. Local similar-lattice approximation ignores Jacobian variation inside each reconstruction kernel. R/B lattice is conservative full-RGB requirement; green quincunx is not two independent acquisitions.','frame_support':frame_support,'summary':summary,'rows':rows}
(OUT/'phase-opportunity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'controls':controls,'summary':summary,'frame_support':frame_support,'elapsed_seconds':report['elapsed_seconds']},indent=2))
