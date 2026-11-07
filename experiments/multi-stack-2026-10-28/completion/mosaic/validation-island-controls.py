"""Fixed-island sampling feasibility before implementing the image producer.

This is a coordinate/operator control only. Image selection, descriptor and
actual interpolation-tap independence still require the Rust producer controls.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

module_path=Path(__file__).with_name('local-interpolant-controls.py')
spec=importlib.util.spec_from_file_location('local_model',module_path)
api=importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
np=api.np
parser=argparse.ArgumentParser()
parser.add_argument('plant',type=Path)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
frozen=json.loads(args.plant.read_text())
plant=frozen['fit_only_measured_plant']
amplitude=plant['amplitude_quad']
length=plant['analytic_length_quad']
shift=np.array([50.,-10.])
DOMAIN=np.array([3516.,2344.])
SIDE=512.
CENTERS=np.array([[144.,144.],[368.,144.],[256.,368.]])
RADIUS_A=43.
RADIUS_B=69.
QUERY_A=40.5
QUERY_B=QUERY_A*(1+2*amplitude/length)+1


def field(points):
    x,y=points[:,0]/length,points[:,1]/length
    return points+shift+amplitude*np.c_[np.sin(x)*np.sin(y),.7*np.cos(x)*np.sin(.8*y)]


def old_held(center,radius):
    low=np.floor((center-radius)/SIDE).astype(int)
    high=np.floor((center+radius)/SIDE).astype(int)
    return np.all(center-radius>=0) and np.all(center+radius<DOMAIN) and all(
        (x+y)%3==0 for y in range(low[1],high[1]+1) for x in range(low[0],high[0]+1))


def make_islands(seed_shift):
    islands=[]
    rejected=[]
    for by in range(5):
        for bx in range(7):
            if (bx+by)%3!=0:
                continue
            for local,center in enumerate(CENTERS):
                a=center+[bx*SIDE,by*SIDE]
                b=a+seed_shift
                if not old_held(a,RADIUS_A) or not old_held(b,RADIUS_B):
                    rejected.append([bx,by,local])
                    continue
                assert all(not np.all(np.abs(a-old[0])<=2*RADIUS_A) and
                           not np.all(np.abs(b-old[1])<=2*RADIUS_B) for old in islands)
                islands.append((a,b,[bx,by,local]))
    return islands,rejected


def overlaps(center,radius,island,island_radius):
    return bool(np.all(np.abs(center-island)<=radius+island_radius))


def train_sites(points,targets,islands,old_only=False):
    selected=[]
    for i,(p,q) in enumerate(zip(points,targets)):
        if np.any(q-QUERY_B<0) or np.any(q+QUERY_B>=DOMAIN):
            continue
        if old_only:
            # A broader conservative old native footprint, with role boundaries
            # checked in both pass gauges before any coordinate is admitted.
            def old_fit(center,radius):
                lo=np.floor((center-radius)/SIDE).astype(int)
                hi=np.floor((center+radius)/SIDE).astype(int)
                return all((x+y)%3!=0 for y in range(lo[1],hi[1]+1) for x in range(lo[0],hi[0]+1))
            if not old_fit(p,QUERY_A) or not old_fit(q,QUERY_B):
                continue
        if any(overlaps(p,QUERY_A,a,RADIUS_A) or overlaps(q,QUERY_B,b,RADIUS_B) for a,b,_ in islands):
            continue
        if any(overlaps(p,QUERY_A,points[j],QUERY_A) or overlaps(q,QUERY_B,targets[j],QUERY_B) for j in selected):
            continue
        selected.append(i)
    return np.array(selected,dtype=int)


islands,rejected=make_islands(shift)
assert len(islands)>=9
held=np.array([r[0] for r in islands])
held_targets=field(held)
inside=np.array([np.all(np.abs(q-b)+QUERY_B<=RADIUS_B) for q,(_,b,_) in zip(held_targets,islands)])
assert np.all(inside),'fixed search envelope must cover the declared smooth plant'
x,y=np.meshgrid(np.arange(64,3452,32),np.arange(64,2280,32))
points=np.c_[x.ravel(),y.ravel()]
targets=field(points)
old=train_sites(points,targets,islands,True)
new=train_sites(points,targets,islands,False)
assert len(new)>len(old)>=8
trained=api.fit(points[new],targets[new])
errors=np.linalg.norm(api.predict(trained,held)-held_targets,axis=1)
old_errors=np.linalg.norm(api.predict(api.fit(points[old],targets[old]),held)-held_targets,axis=1)
counts={}
for (_,_,identity),error in zip(islands,errors):
    cell=str(identity[:2])
    counts.setdefault(cell,[]).append(float(error))
qualified=sum(len(v)>=3 and max(v)<=.5 for v in counts.values())

# The fixed reservations cannot depend on heldout target values. Poisoning
# held targets affects evaluation only, never the train list or coefficients.
poisoned_targets=held_targets+np.random.default_rng(api.SEED).normal(0,500,held_targets.shape)
assert np.array_equal(trained[1],api.fit(points[new],targets[new])[1])
wrong_error=np.linalg.norm(api.predict(trained,held)-poisoned_targets,axis=1)
assert np.min(wrong_error)>10
wrong_islands,wrong_rejected=make_islands(shift+[300,0])
assert len(wrong_islands)<len(islands) and len(wrong_rejected)>len(rejected)
late_shift=held_targets+[80,0]
late_inside=[np.all(np.abs(q-b)+QUERY_B<=RADIUS_B) for q,(_,b,_) in zip(late_shift,islands)]
assert not any(late_inside)

# A depth discontinuity can invalidate a local join even when all measurements
# are otherwise exact. It is not smoothed into a certificate.
cut=held[0,0]+16
discontinuous=targets.copy()
discontinuous[points[:,0]>cut]+=[35,-25]
held_discontinuous=held_targets.copy()
held_discontinuous[held[:,0]>cut]+=[35,-25]
depth=api.fit(points[new],discontinuous[new])
depth_errors=np.linalg.norm(api.predict(depth,held)-held_discontinuous,axis=1)
assert float(depth_errors.max())>5

result=dict(schema='strehl.mosaic-validation-island-coordinate-controls.v1',command=sys.argv,
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            model_sha256=hashlib.sha256(module_path.read_bytes()).hexdigest(),
            plant_sha256=hashlib.sha256(args.plant.read_bytes()).hexdigest(),
            fixed_plan=dict(old_block_quad=SIDE,centers_within_block=CENTERS.tolist(),radius_a_quad=RADIUS_A,
                            radius_b_quad=RADIUS_B,query_radius_quad=[QUERY_A,QUERY_B],seed_shift_quad=shift.tolist()),
            frozen_islands=[dict(a=a.tolist(),b=b.tolist(),id=i) for a,b,i in islands],
            rejected_islands=rejected,old_fit=len(old),stage2_fit=len(new),heldout=len(held),
            old_fit_errors=api.stats(old_errors),stage2_errors=api.stats(errors),
            heldout_cell_errors=counts,cells_with_three_passing_noncollinear_sites=qualified,
            wrong_identity_errors=api.stats(wrong_error),depth_discontinuity_errors=api.stats(depth_errors),
            projected_old_fit_overlap_refused=True,late_search_outside_reservation_refused=True,
            claim='Coordinate feasibility only, not the actual pixel-producing path or a real-data certificate. All constants declared before this evaluation, initial/global evidence and final half-quad bar unchanged. Product island implementation and actual-footprint poisoning controls remain required.')
with args.out.open('x') as stream:
    json.dump(result,stream,indent=2)
    stream.write('\n')
print(json.dumps({k:result[k] for k in ['old_fit','stage2_fit','heldout','old_fit_errors','stage2_errors','cells_with_three_passing_noncollinear_sites','depth_discontinuity_errors']},indent=2))
