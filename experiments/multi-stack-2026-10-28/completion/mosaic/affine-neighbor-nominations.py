"""One generation of untrusted neighbor proposals from accepted FIT pixel maps.

No new geometry is accepted here. Every proposal needs fresh original-source
NCC/native/LOO/reciprocal measurements and physical-support independence.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '4'
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--pilot', type=Path, required=True)
parser.add_argument('--parents', type=Path, required=True)
parser.add_argument('--guides', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--features', type=Path)
parser.add_argument('--coarse', action='store_true')
parser.add_argument('--target-features', action='store_true')
args = parser.parse_args()
args.out.mkdir(exist_ok=False, parents=True)
MAXIMUM = 512
RADIUS = 512.0
STRIDE = 128
SEARCH = 8

def load(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def number(bits): return struct.unpack('<d', int(bits, 16).to_bytes(8, 'little'))[0]
def affine(values):
    a,b,c,d,tx,ty = values
    return np.array([[a,b,tx],[c,d,ty],[0.,0.,1.]])
def similarity(values, shape):
    ar,ai,br,bi = values
    center = np.array(shape)*0.5
    linear = np.array([[ar,-ai],[ai,ar]])
    shift = center+np.array([br,bi])-linear@center
    return affine([ar,-ai,ai,ar,*shift])

records = load(args.parents/'mosaic-native-measurements.json')
original_pairs = load(args.parents/'mosaic-candidates.json')
session = load(args.pilot/'session.json')
guides = []
maps = []
dtype = np.dtype({'names':['covered','sources','ordinal','width'],
                 'formats':['u1',('<u8',4),'<f4','<f4'],
                 'offsets':[4,6,38,42],'itemsize':46})
for pass_id in range(len(session['passes'])):
    with (args.guides/f'guide-{pass_id}.bin').open('rb') as stream:
        prefix=stream.read(12); assert prefix[:8]==b'STRHGUI1'
        header=json.loads(stream.read(struct.unpack('<I',prefix[8:])[0]))
        data=np.frombuffer(stream.read(),dtype=dtype)
    receipt=header['receipt']; w,h=receipt['guide_geometry']
    assert len(data)==w*h
    guides.append((receipt,data))
    directory=sorted(args.pilot.glob('pass-*'))[pass_id]
    focus=load(directory/'focus/geometry.json')
    start=focus['ordinal_mapping'][0]['global_index']
    placement={}
    for line in load(directory/'alignment.json')['warpmap'].splitlines():
        fields=line.split()
        if len(fields)>5 and fields[1]=='placed':
            placement[start+int(fields[0])]=similarity([number(v) for v in fields[2:6]],receipt['source_geometry'])
    maps.append(placement)

def witness(pass_id, point):
    receipt,data=guides[pass_id]; w,h=receipt['guide_geometry']; step=receipt['step_quad_pixels']
    x,y=[math.floor((q-(step-1)*0.5)/step+0.5) for q in point]
    if not(0<=x<w and 0<=y<h):return None
    row=data[y*w+x]
    if not row['covered']:return None
    source=next((int(s) for s in row['sources'] if int(s)!=2**64-1),None)
    return source if source in maps[pass_id] else None

def role(pass_id, point, feature_radius=0.0):
    receipt,_=guides[pass_id]; step=receipt['step_quad_pixels']; q=(np.array(point)-(step-1)*0.5)/step
    # Conservative nomination margin; actual complete warped native search
    # footprints are checked again by the consuming estimator.
    radius=max(128.0,feature_radius)/step
    if np.any(q-radius<0):return None
    block=np.floor(q/128).astype(int); heldout=(sum(block)%3)==0
    low=np.floor((q-radius)/128).astype(int); high=np.floor((q+radius)/128).astype(int)
    if any(((x+y)%3==0)!=heldout for x in range(low[0],high[0]+1) for y in range(low[1],high[1]+1)):return None
    return block.tolist(),heldout

feature_receipts=load(args.features) if args.features else None
assert not args.target_features or feature_receipts, 'target feature nomination needs bound original features'
parents=[]; proposals=[]
for record in records:
    c=record['candidate']
    if not record['accepted'] or c['role']!='fit':continue
    stages=[m for m in record['measurements'] if m['direction']=='forward-affine' and m.get('affine_fit')]
    if not stages:continue
    a,b=c['pass_a'],c['pass_b']; ia,ib=c['source_a'],c['source_b']
    transform=np.linalg.inv(maps[b][ib])@affine(stages[-1]['affine_fit'])@maps[a][ia]
    pa=np.array(c['point_a_quad']); observed=np.array(record['refined_b_quad'])
    assert np.linalg.norm((transform@np.r_[pa,1])[:2]-observed)<1e-6
    singular=np.linalg.svd(transform[:2,:2],compute_uv=False)
    if np.linalg.det(transform[:2,:2])<=0 or min(singular)<0.5 or max(singular)>2:continue
    linear=[(transform[0,0]+transform[1,1])*0.5,(transform[1,0]-transform[0,1])*0.5]
    parent_id=len(parents)
    parents.append({'id':c['id'],'source_ids':[ia,ib],'anchor_point':pa.tolist(),
                    'anchor_affine':transform.tolist(),'fit_role_only':True})
    pair=next(p for p in original_pairs if (p['pass_a'],p['pass_b'])==(a,b))
    model=pair.get('ordinal_seed')
    center=np.floor((pa-65.5)/STRIDE+0.5).astype(int)
    if feature_receipts:
        locations=[(f"feature-{f['index']}",np.array(f['point_quad']),f['source'],f['support_radius_quad'],f['focus'])
                   for f in feature_receipts[a]['feature_witnesses']]
    else:
        locations=[]
        for dy in range(-4,5):
            for dx in range(-4,5):
                gx,gy=center+[dx,dy]
                locations.append((f'{gx}-{gy}',np.array([65.5+STRIDE*gx,65.5+STRIDE*gy]),None,0.0,None))
    for location,p,feature_source,feature_radius,focus_a in locations:
        distance=float(np.linalg.norm(p-pa))
        if distance<96 or distance>RADIUS:continue
        q=(transform@np.r_[p,1])[:2]
        sa=feature_source if feature_source is not None else witness(a,p)
        ra=role(a,p,feature_radius)
        if sa is None or sa not in maps[a] or ra is None:continue
        moving=[]
        if args.target_features:
            # Original feature locations only nominate source pairs. A nearby
            # point is never an accepted correspondence or an independent vote.
            for f in feature_receipts[b]['feature_witnesses']:
                observed=np.array(f['point_quad'])
                error=float(np.linalg.norm(observed-q))
                rb=role(b,observed,f['support_radius_quad'])
                if error>48 or f['source'] not in maps[b] or rb is None or ra[1]!=rb[1]:continue
                moving.append((error,f['index'],f['source'],observed,rb,f['focus']))
            moving.sort(key=lambda x:(x[0],x[1]))
            moving=moving[:4]
        else:
            sb=witness(b,q);rb=role(b,q)
            if sb is None or rb is None or ra[1]!=rb[1]:continue
            ids=[]
            if model and model['source_interval'][0]<=sa<=model['source_interval'][1]:
                slope,intercept=model['target_source_linear']; predicted=math.floor(slope*sa+intercept+0.5)
                delta=max(math.ceil(model['target_source_rms_ordinals']),1)
                for value in [predicted,predicted-delta,predicted+delta]:
                    if model['target_source_interval'][0]<=value<=model['target_source_interval'][1] and value in maps[b] and value!=sb:ids.append(value)
            ids.append(sb)
            moving=[(0.0,None,value,q,rb,None) for value in ids]
        for error,target_id,source_b,point_b,rb,focus_b in moving:
            suffix='' if target_id is None else f'-targetfeature{target_id}'
            candidate={'id':f'p{a}-p{b}-fit-neighbor-{parent_id}-{location}-source{source_b}{suffix}',
                'pass_a':a,'pass_b':b,'point_a_quad':p.tolist(),'point_b_quad':point_b.tolist(),
                'source_a':sa,'source_b':source_b,'focus_a':focus_a,'focus_b':focus_b,
                'role':'heldout' if ra[1] else 'fit','spatial_blocks':[ra[0],rb[0]],
                'descriptor_distance':0.0,'seed_residual_quad':error,'within_seed_support':True,
                'grid_nomination':args.coarse,'spatial_roles_match':True}
            proposals.append((distance,parent_id,candidate,linear))

# At most two independently trained parent proposals per physical/source site.
# Disagreeing native alternatives later exclude the site; ancestry is not a vote.
proposals.sort(key=lambda r:(r[0],r[1],r[2]['id']))
counts={}; chosen=[]
for row in proposals:
    c=row[2]; key=(c['pass_a'],c['pass_b'],*c['point_a_quad'],c['source_a'],c['source_b'])
    if counts.get(key,0)>=2:continue
    counts[key]=counts.get(key,0)+1;chosen.append(row)
    if len(chosen)==MAXIMUM:break
pairs=[]
for parent_id,parent in enumerate(parents):
    subset=[r for r in chosen if r[1]==parent_id]
    if not subset:continue
    c=subset[0][2];linear=subset[0][3]
    pairs.append({'pass_a':c['pass_a'],'pass_b':c['pass_b'],'features_a':0,'features_b':0,
        'reciprocal_matches':0,'directional_ratio_matches':[0,0],
        'nomination':'Untrusted FIT affine neighbor; ancestor '+parent['id']+'; one generation, maximum512quad nomination radius, native search8quad; every new point needs direct original-image measurement',
        'fit_inliers':0,'seed_a_to_b':[*linear,0.,0.],'ordinal_seed':None,'seed_fit_rms_quad':None,
        'seed_semantics':'Only bounded local linear seed; each proposal anchors its own source coordinates. No accepted chained placement.',
        'correspondences':[r[2] for r in subset],'refusal':None})
record={'schema':'strehl.mosaic-fit-neighbor-nominations.v1','parents':parents,
        'command':sys.argv,'script_sha256':sha(Path(__file__)),
        'coarse_original_image_search':args.coarse,
        'target_original_features':args.target_features,
        'maximum_target_feature_nomination_error_quad':48 if args.target_features else None,
        'candidate_count':len(chosen),'considered':len(proposals),'maximum_candidates':MAXIMUM,
        'maximum_nomination_radius_quad':RADIUS,'native_search_radius_quad':SEARCH,
        'native_measurements_sha256':sha(args.parents/'mosaic-native-measurements.json'),
        'source_identities_sha256':sha(args.pilot/'source-identities.json'),
        'original_feature_witnesses_sha256':sha(args.features) if args.features else None,
        'candidate_ancestry':[{'id':r[2]['id'],'ancestor':parents[r[1]]['id'],'distance_quad':r[0]} for r in chosen],
        'semantics':'No photo or placement claim. All proposed matches require native validation. No heldout parent or recursively accepted placement is used.'}
(args.out/'neighbor-pairs.json').write_text(json.dumps(pairs,indent=2)+'\n')
(args.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
(args.out/'nomination-source.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'parents':len(parents),'proposals':len(chosen),'considered':len(proposals),
                  'heldout':sum(r[2]['role']=='heldout' for r in chosen)},indent=2))
