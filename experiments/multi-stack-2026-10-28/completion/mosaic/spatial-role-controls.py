"""Commission fixed physical spatial splits before new real native matching.

This diagnostic uses an analytic curved field, with amplitude and curvature
scale derived only from the already frozen independent FIT locations. It does
not validate the optical model or certify any real mesh. The exact native pixel
observer remains the producing-path independence check in the replay.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

module_path = Path(__file__).with_name('local-interpolant-controls.py')
spec = importlib.util.spec_from_file_location('local_model', module_path)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
np = api.np

parser = argparse.ArgumentParser()
parser.add_argument('sites', type=Path)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
data = json.loads(args.sites.read_text())
records = [r['receipt'] for r in data['records'] if r['receipt']['candidate']['role']=='fit']
p = np.array([r['candidate']['point_a_quad'] for r in records])
q = np.array([r['refined_b_quad'] for r in records])
linear = np.c_[np.ones(len(p)), p]
residual = q-linear@np.linalg.lstsq(linear,q,rcond=None)[0]
amplitude = float(np.percentile(np.linalg.norm(residual,axis=1),90))
curvatures = []
radii = []
for point in p:
    neighbors = np.argsort(np.linalg.norm(p-point,axis=1))[:12]
    v = (p[neighbors]-point)/1000
    design = np.c_[np.ones(12),v,v[:,0]**2,v[:,0]*v[:,1],v[:,1]**2]
    coefficients = np.linalg.lstsq(design,q[neighbors]-p[neighbors],rcond=None)[0]
    curvatures.append(np.linalg.norm(np.r_[2*coefficients[3],coefficients[4],2*coefficients[5]])/1e6)
    radii.append(np.linalg.norm(p[neighbors[-1]]-point))
curvature = float(np.median(curvatures))
length = float(np.sqrt(amplitude/curvature))


def field(point):
    x,y = point[:,0]/length,point[:,1]/length
    return point+[50,-10]+amplitude*np.c_[np.sin(x)*np.sin(y),.7*np.cos(x)*np.sin(.8*y)]


def role(point, radius, side):
    if np.any(point-radius<0):
        return None
    block = np.floor(point/side).astype(int)
    heldout = sum(block)%3==0
    low = np.floor((point-radius)/side).astype(int)
    high = np.floor(np.ceil(point+radius)/side).astype(int)
    for y in range(low[1],high[1]+1):
        for x in range(low[0],high[0]+1):
            if ((x+y)%3==0)!=heldout:
                return None
    return bool(heldout)


def selection(points, targets, side):
    # Enclose actual 3x3 native32 patches, radius8 search, interpolation and a
    # conservative extra margin. B includes the maximum analytic local stretch.
    radius_a = 48.0
    radius_b = radius_a*(1+2*amplitude/length)+2
    candidates=[]
    for i,(a,b) in enumerate(zip(points,targets)):
        ra,rb=role(a,radius_a,side),role(b,radius_b,side)
        if ra is not None and ra==rb:
            candidates.append((i,ra))
    chosen=[]
    # Role and traversal are fixed independently of target matching errors.
    for i,heldout in sorted(candidates,key=lambda item:(item[1],item[0])):
        if any(np.all(np.abs(points[i]-points[j])<=2*radius_a) or
               np.all(np.abs(targets[i]-targets[j])<=2*radius_b) for j,_ in chosen):
            continue
        chosen.append((i,heldout))
    # Every pair of retained source footprints is disjoint in both originals.
    for pos,(i,_) in enumerate(chosen):
        for j,_ in chosen[:pos]:
            assert not np.all(np.abs(points[i]-points[j])<=2*radius_a)
            assert not np.all(np.abs(targets[i]-targets[j])<=2*radius_b)
    return chosen, radius_a,radius_b


x,y=np.meshgrid(np.arange(80,3436,32),np.arange(80,2264,32))
points=np.c_[x.ravel(),y.ravel()]
targets=field(points)
arms=[]
for side in (512,256):
    selected,ra,rb=selection(points,targets,side)
    train=np.array([i for i,h in selected if not h],dtype=int)
    held=np.array([i for i,h in selected if h],dtype=int)
    assert len(train)>=8 and len(held)>=3
    model=api.fit(points[train],targets[train])
    errors=np.linalg.norm(api.predict(model,points[held])-targets[held],axis=1)
    nearest=np.min(np.linalg.norm(points[held,None,:]-points[train][None,:,:],axis=2),axis=1)
    cells={}
    for i,h in selected:
        cell=tuple(np.minimum((points[i]/[3515/7,2343/5]).astype(int),[6,4]))
        counts=cells.setdefault(str(cell),[0,0])
        counts[int(h)]+=1
    # Wrong original identities cannot become a good spatial model by adding FIT.
    wrong=api.fit(points[train],np.random.default_rng(api.SEED).permutation(targets[train]))
    wrong_error=np.linalg.norm(api.predict(wrong,points[held])-targets[held],axis=1)
    assert np.median(wrong_error)>100
    # Expanding a patch across a role boundary must be refused, even if its
    # undilated centre is valid. This is a commissioning analogue of the actual
    # native filter/search/interpolation observer, not a substitute for it.
    assert role(np.array([side+20.,side/2]),5.,side) is not None
    assert role(np.array([side+20.,side/2]),25.,side) is None
    arms.append(dict(block_quad=side,fit=len(train),heldout=len(held),
                     assumed_complete_patch_radius_quad=[ra,rb],heldout_error=api.stats(errors),
                     nearest_fit_quad=dict(median=float(np.median(nearest)),maximum=float(nearest.max())),
                     cells_fit_heldout=cells,cells_with_three_heldouts=sum(v[1]>=3 for v in cells.values()),
                     cells_with_fit_and_three_heldouts=sum(v[0]>0 and v[1]>=3 for v in cells.values()),
                     wrong_identity_heldout=api.stats(wrong_error),all_original_footprints_disjoint=True))
result=dict(schema='strehl.mosaic-spatial-role-controls.v1',command=sys.argv,
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            local_model_sha256=hashlib.sha256(module_path.read_bytes()).hexdigest(),
            input_sites_sha256=hashlib.sha256(args.sites.read_bytes()).hexdigest(),
            fit_only_measured_plant=dict(amplitude_quad=amplitude,curvature_per_quad=curvature,
                                        analytic_length_quad=length,measurement_neighborhood_median_quad=float(np.median(radii)),
                                        translation_quad=[50,-10],measurement_scope='Local quadratic estimate from frozen FIT only; not calibrated depth or noise.'),
            arms=arms,
            claim='Fixed512 versus256quad role layout commissioning, actual descriptor/native pixel checks still required. No residual threshold changed; all heldouts evaluated. A more local split can still fail real geometry or lack independent support.')
with args.out.open('x') as stream:
    json.dump(result,stream,indent=2)
    stream.write('\n')
print(json.dumps({'plant':result['fit_only_measured_plant'],'arms':[{k:v for k,v in arm.items() if k!='cells_fit_heldout'} for arm in arms]},indent=2))
