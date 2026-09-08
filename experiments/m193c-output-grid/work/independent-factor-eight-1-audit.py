"""Saved evidence only. Never import a subject, decode an image or call a registrar.
Prospective falsifiers: missing/reordered pair, inverted star direction, changed
feature association/split, mismatched observer signature, dropped refusal, false
bridge/component, changed source or detached terminal receipt. Historical chain
is delegated to the pinned completed coverage audit, not reconstructed here.
Execution requires root's actual terminal notice and external outcome digests.
"""
import argparse
from decimal import Decimal as D
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
OUT = HERE / "factor-eight-1"
ORIGINAL = list(range(0, 105, 13))
EDGES = [(0,1),(0,2),(0,4),(0,5),(1,2),(1,3),(1,5),(2,3),(2,4),
         (2,5),(2,6),(3,4),(3,5),(3,7),(4,5),(4,6),(4,8),(5,6),
         (5,7),(5,8),(6,7),(6,8),(7,8)]
IDS = ['geometry-0','geometry-2','observer-null','identity',
       'complementary-refusal','association-destroyer-restored','blob-sha-refusal-restored']
CODE = 'UNMEASURED_INPUT_REGISTRATION_INADEQUATE'
OLD = CODE + ': too few total mutual landmarks'
HISTORY = 'f5372a6fc28f9a0d34cc37356374beeca266ac5539d5fb93d3d1f2ff1b7c979a'
USED = {}
GAPS = []

def need(ok, why):
    if not ok: raise ValueError(why)

def integer(x):
    return type(x) is int

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def unique(pairs):
    result={}
    for key,value in pairs:
        need(key not in result,'duplicate JSON key'); result[key]=value
    return result

def strict(raw):
    value=json.loads(raw,object_pairs_hook=unique,
        parse_constant=lambda x:need(False,'nonfinite JSON'))
    def finite(x):
        if type(x) is float: need(math.isfinite(x),'overflow JSON')
        elif isinstance(x,dict):
            for v in x.values(): finite(v)
        elif isinstance(x,list):
            for v in x: finite(v)
    finite(value)
    return value

def path(ref):
    return (ROOT / ref['path']).resolve()

def file(p,expected=None):
    p=Path(p).resolve()
    allowed={'.json','.lock','.md','.py','.rs','.toml','.tsv','.txt','.log'}
    python=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
    need((p.is_relative_to(ROOT) and p.suffix.lower() in allowed) or p==python,'metadata/source only')
    before=p.stat(follow_symlinks=False)
    need(not (getattr(before,'st_file_attributes',0)&0x400) and before.st_nlink==1 and
         0<before.st_size<=32*(1<<20),'bounded ordinary metadata')
    raw=p.read_bytes(); after=p.stat(follow_symlinks=False)
    fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,getattr(s,'st_file_attributes',0))
    need(fields(before)==fields(after) and len(raw)==after.st_size,'stable metadata identity')
    ref=dict(path=str(p),sha256=sha(raw),bytes=len(raw))
    if expected is not None:
        need(set(expected)=={'path','sha256','bytes'} and integer(expected['bytes']) and
             path(expected)==p and all(ref[k]==expected[k] for k in ('bytes','sha256')),'file association')
    need(str(p) not in USED or USED[str(p)]==ref,'conflicting consumed file')
    USED[str(p)]=ref
    return ref

def read(ref):
    file(path(ref),ref); need(ref['bytes']<=8*(1<<20),'bounded JSON')
    raw=path(ref).read_bytes(); need(sha(raw)==ref['sha256'],'same parsed bytes')
    return strict(raw)

def actual(p):
    return read(file(p))

def same(a,b):
    return path(a)==path(b) and all(a[k]==b[k] for k in ('bytes','sha256'))

def saved(p,value,complete):
    if p.exists(): need(actual(p)==value,'persisted record association')
    else:
        need(not complete,'missing complete artifact'); GAPS.append(str(p))

def planned():
    result=[]
    for i,j in EDGES:
        a,z=(5,i if j==5 else j) if 5 in (i,j) else (i,j)
        result.append(dict(id=f'pair-{i}-{j}',reference=a,source=z,local_span=j-i,
            star=5 in (i,j),reference_original=ORIGINAL[a],source_original=ORIGINAL[z]))
    return result

def components(edges):
    parent=list(range(9))
    def find(i):
        while parent[i]!=i: i=parent[i]
        return i
    for a,b in edges: parent[find(a)]=find(b)
    return sorted([sorted(i for i in range(9) if find(i)==r)
                   for r in set(find(i) for i in range(9))])

def topology(records,g):
    edges=[[r['pair']['reference'],r['pair']['source']] for r in records
           if r['outcome']['status']=='RETURNED']
    groups=components(edges)
    bridges=[e for i,e in enumerate(edges) if len(components(edges[:i]+edges[i+1:]))>len(groups)]
    need(g['anchor_local']==4 and g['anchor_original']==52 and
         g['reference_local']==5 and g['reference_original']==65,'distinct graph gauges')
    need(g['edges']==edges and g['bridges']==bridges and len(g['nodes'])==9,'edge-removal bridges')
    for i,node in enumerate(g['nodes']):
        group=next(c for c in groups if i in c)
        need(node==dict(local=i,original=ORIGINAL[i],component=group,
             anchor_connected=4 in group,degree=sum(i in e for e in edges),
             cycle_participation=any(i in e and e not in bridges for e in edges)),'union-find node')
    return dict(components=groups,edges=edges,bridges=bridges,cycle_rank=len(edges)-9+len(groups))

def controls(rows):
    need([r['id'] for r in rows]==IDS and all(r['passed'] is True for r in rows),'seven controls')
    e={r['id']:r['evidence'] for r in rows}; o=e['observer-null']
    need(o['off']==o['count']==o['placebo']==e['geometry-0'],'actual observer equality')
    need(o['canonical_signature_sha256']=={k:sha(canonical(o[k])) for k in ('off','count','placebo')},'canonical observer hashes')
    frozen=actual(ROOT/'experiments/M193-cover-overlap/fixtures.json')['synthetic_overlap']['sources']
    for name,w in zip(IDS[:2],frozen[1:]):
        g=e[name]
        need(g['status']=='RETURNED' and g['error'] is None and g['transform']==w['source_to_reference_q32'] and dict(g['metrics'],reference=False)==w['registration'] and g['guard']==w['valid_center_guard_q8'],'fixture oracle')
    need(e['geometry-0']['transform']!=e['geometry-2']['transform'],'distinct associations')
    identity=e['identity']; bad=e['complementary-refusal']; s=e['association-destroyer-restored']
    need(identity['transform']==dict(a=1<<32,b=0,tx=0,ty=0) and identity['metrics']['heldout_rms_reference_px']=='0.000000000','identity')
    need(bad['status']=='REGISTRATION_REFUSED' and bad['error']['code']==CODE and bad['error']['type']=='ContractError','specific refusal')
    need(s['first']==s['restored']==e['geometry-0']['transform'] and s['wrong']==e['geometry-2']['transform'],'swapped/restored')
    blob=e['blob-sha-refusal-restored']
    need(blob==dict(exception='authenticated same TIFF blob',refused_decoder_calls=0,restored_decoder_calls=1),'decoder auth call power')

def landmarks(o,features,p):
    marks=o['landmarks']; status=o['status']; order=[]; held=[]
    need(status in ('RETURNED','REGISTRATION_REFUSED') and len(marks)<=256,'bounded matches')
    coords=[set(map(tuple,features[p[k]]['coordinates_q8'])) for k in ('reference','source')]
    for i,m in enumerate(marks):
        rx,ry=m['reference_q8']; sx,sy=m['source_q8']
        need(all(integer(x) for x in (rx,ry,sx,sy)) and (rx,ry) in coords[0] and (sx,sy) in coords[1] and m['split']==('holdout' if i%2 else 'calibration'),'point/split association')
        need(len(m['digest'])==64 and len(bytes.fromhex(m['digest']))==32,'landmark digest')
        order.append((m['digest'],ry,rx,sy,sx))
        need(type(m['inlier']) is bool if status=='RETURNED' else m['inlier'] is None,'inlier type/scope')
        if i%2 and m['inlier']: held.append(m)
    need(order==sorted(order),'actual digest order')
    if status=='RETURNED':
        m=o['metrics']
        need(all(integer(m[k]) for k in ('mutual_match_count','calibration_count','holdout_count','holdout_inlier_count')),'typed match counts')
        need(o['error'] is None and m['mutual_match_count']==len(marks) and m['calibration_count']==(len(marks)+1)//2 and m['holdout_count']==len(marks)//2 and m['holdout_inlier_count']==len(held)>=12,'match counts')
        need(integer(m['calibration_inlier_count']) and 12<=m['calibration_inlier_count']<=m['calibration_count'],'fit count bounds')
        box={k:[min(m[k][0] for m in held),min(m[k][1] for m in held),max(m[k][0] for m in held),max(m[k][1] for m in held)] for k in ('reference_q8','source_q8')}
        need(o['heldout_bbox_q8']==box,'saved accepted bounds')
    else:
        need(o['transform'] is o['metrics'] is o['guard'] is o['heldout_bbox_q8'] is None and o['error']['type']=='ContractError' and o['error']['code']==CODE and o['error']['message'].startswith(CODE+': ') and 'register_to_reference' in o['error']['traceback'],'scientific refusal')
    return len(marks)
# Independent metadata helpers above are retained as text, not module imports.
from collections import defaultdict
import itertools
import os
import time
RUNNER_PIN=(24036,'3699b85aceed462edb8a5641a3847e5a3676a0166cff7a03f630fa670dff6082')
SPEC_PIN=(12497,'7ba4e7542963423239949aa925ac82fbb8dcfec9c1c185a12d47c10865dedb79')
NATIVE_AUDIT='2b8b4a6ce4e2f245c95249555bdc3911f0802385fcc781b1427f2dc83bb9bef1'
MORE=['area8-half-ties','repeated-block-null','native-rotation-positive','native-two-pixel-map-destroyer','centre-offset-destroyer','native-rotation-restored','rotation-observer-null']
ALL_IDS=IDS+MORE
Q=1<<32
QUAL=dict(coordinate_gauge='native pixel centres; q_native=8*q_coarse+896',coordinate_lattice_step_q8=8,inherited_quantization_guard_q8=1,guard_status='UNQUALIFIED_FOR_COARSE_LATTICE',scope='Diagnostic direct fit only; no support, overlap, placement or quality admission')
BUDGET=dict(cpu_seconds=30,wall_seconds=60,file_bytes=2<<20,metadata_bytes=2<<20)
TIFF_STAT=[]

def hv(value):
    need(type(value) is str and len(value)==64 and len(bytes.fromhex(value))==32,'opaque digest shape')

def image_stat(ref):
    need(set(ref)=={'path','bytes','sha256'} and integer(ref['bytes']),'image reference schema')
    hv(ref['sha256']);p=path(ref)
    need(p.is_relative_to(HERE) and p.suffix=='.tiff','owned TIFF reference')
    s=p.stat(follow_symlinks=False)
    need(s.st_nlink==1 and not getattr(s,'st_file_attributes',0)&0x400 and s.st_size==ref['bytes'],'TIFF extent only')
    v=dict(reference=ref,bytes=s.st_size,device=s.st_dev,file_id=s.st_ino,mtime_ns=s.st_mtime_ns)
    if v not in TIFF_STAT:TIFF_STAT.append(v)

def signature(o):
    e=o['error']
    return {k:o[k] for k in ('status','transform','metrics','guard')}|dict(error=None if e is None else {k:e[k] for k in ('type','code','message')})

def coordinate_rows(values):
    need(type(values) is list and all(type(p) is list and len(p)==2 and all(integer(x) for x in p) for p in values),'Q8 arrays')

def corners(t):
    # source[y_s,x_s]=reference[x_s,3071-y_s], hence x_r=3071-y_s,y_r=x_s.
    need(type(t) is dict and set(t)=={'a','b','tx','ty'} and all(integer(v) for v in t.values()),'Q32 map')
    answer=[]
    for x,y in ((0,0),(2303,0),(0,3071),(2303,3071)):
        dx=t['a']*x-t['b']*y+t['tx']-(3071-y)*Q;dy=t['b']*x+t['a']*y+t['ty']-x*Q
        num=dx*dx+dy*dy;den=Q*Q;g=math.gcd(num,den)
        answer.append(dict(source=[x,y],expected=[3071-y,x],squared_error_numerator=num//g,squared_error_denominator=den//g,error_native_px=math.sqrt(num)/Q))
    return answer

def corner_pass(t):
    return all(c['squared_error_numerator']<=c['squared_error_denominator'] for c in corners(t))

def check_corners(saved_rows,t):
    expected=[] if t is None else corners(t)
    need(len(saved_rows)==len(expected),'corner witness length')
    for s,e in zip(saved_rows,expected):
        need(set(s)==set(e) and all(s[k]==v for k,v in e.items() if k!='error_native_px'),'literal corner rational')
        need(math.isclose(s['error_native_px'],e['error_native_px'],rel_tol=1e-12,abs_tol=1e-12),'corner display')
    return expected

def near_components(rows,side,radius=256):
    sides=('reference_q8','source_q8') if side=='joint' else (side,)
    def distance(i,j):return max(sum((a-b)**2 for a,b in zip(rows[i][s],rows[j][s])) for s in sides)
    remaining=set(range(len(rows)));groups=[];direct=0;adjacent=[set() for _ in rows]
    for i,j in itertools.combinations(range(len(rows)),2):
        if distance(i,j)<=radius*radius:
            adjacent[i].add(j);adjacent[j].add(i);direct+=rows[i]['split']!=rows[j]['split']
    while remaining:
        pending=[min(remaining)];group=[]
        while pending:
            i=pending.pop()
            if i not in remaining:continue
            remaining.remove(i);group.append(i);pending.extend(adjacent[i]&remaining)
        groups.append(sorted(group))
    diameters=[max((distance(i,j) for i,j in itertools.combinations(g,2)),default=0) for g in groups]
    return dict(groups=len(groups),mixed_split_groups=sum(len({rows[i]['split'] for i in g})>1 for g in groups),direct_cross_split_pairs=direct,chained_components=sum(d>radius*radius for d in diameters),max_component_diameter_native_px=math.sqrt(max(diameters,default=0))/256)

def site_check(o):
    marks=o['landmarks'];reported=o['site_evidence'];joint=defaultdict(list);sides={}
    for i,m in enumerate(marks):joint[tuple(m['reference_q8']+m['source_q8'])].append(i)
    for side in ('reference_q8','source_q8'):
        points=sorted({tuple(m[side]) for m in marks});cal={tuple(m[side]) for m in marks if m['split']=='calibration'};held={tuple(m[side]) for m in marks if m['split']=='holdout'}
        e=dict(unique_total=len(points),calibration_unique=len(cal),holdout_unique=len(held),exact_locations_shared_between_splits=[list(p) for p in sorted(cal&held)],bbox_q8=None if not points else [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)])
        need(reported['sides'][side]==e,'exact site extent/intersection')
        expected=[[list(p),[i for i,m in enumerate(marks) if tuple(m[side])==p]] for p in points]
        need(reported['exact_endpoint_groups'][side]==expected,'complete endpoint membership')
        sides[side]=dict(exact_sites=len(points),exact_shared_sites=len(cal&held),radius_one=near_components(marks,side))
    repeated=[dict(reference_q8=list(k[:2]),source_q8=list(k[2:]),ordinals=ids,split_membership=sorted({marks[i]['split'] for i in ids})) for k,ids in sorted(joint.items()) if len(ids)>1]
    need(reported['descriptor_match_count']==len(marks) and reported['exact_joint_groups']==len(joint) and reported['repeated_joint_groups']==repeated,'joint groups')
    need(reported['scope']=='descriptive exact coordinate groups; no independence or coverage acceptance claim' and reported['exact_endpoint_group_layout']=='[coordinate_q8, landmark_ordinals]; split comes from saved landmark row','site scope')
    return dict(descriptor_rows=len(marks),exact_joint_groups=len(joint),exact_joint_mixed=sum(len(g['split_membership'])>1 for g in repeated),radius_one_joint=near_components(marks,'joint'),sides=sides)

def residual(m,t):
    rx,ry=m['reference_q8'];sx,sy=m['source_q8']
    dx=t['a']*sx-t['b']*sy+t['tx']*256-rx*Q;dy=t['b']*sx+t['a']*sy+t['ty']*256-ry*Q
    return dx*dx+dy*dy

def observed(o,ref_coords,src_coords,*,missing=False,captured=True):
    q=dict(QUAL)
    if missing:q.update(coordinate_gauge='active faulty coordinates; q_fault=8*q_coarse+0',expected_ordinary_coordinate_gauge=QUAL['coordinate_gauge'],active_defect='omitted +896 Q8 on both endpoints')
    need(o['qualification']==q,'coarse lattice qualification');marks=o['landmarks'];need(len(marks)<=256,'bounded matches')
    if captured:
        landmarks(o,[dict(coordinates_q8=ref_coords),dict(coordinates_q8=src_coords)],dict(reference=0,source=1))
        if o['status']=='RETURNED':
            held=[]
            for i,m in enumerate(marks):
                e=residual(m,o['transform']);need(m['inlier'] is (e<=(2*256*Q)**2),'retained-map inlier flags')
                if i%2 and m['inlier']:held.append(e)
            need(len(held)>=12 and len(held)*2>=len(marks)//2,'held support minimum')
            total=sum(held);need(total<=len(held)*(256*Q)**2,'one native pixel held RMS')
            rms=math.sqrt(total/len(held))/(256*Q);need(o['metrics']['heldout_rms_reference_px']==f'{rms:.9f}','held RMS')
            det=o['transform']['a']**2+o['transform']['b']**2;need(det>0,'map determinant');mx=max(held);ceiling=math.isqrt(mx//det)
            if ceiling*ceiling*det<mx:ceiling+=1
            need(o['metrics']['heldout_max_source_px_ceil_q8']==ceiling and o['guard']==ceiling+1 and o['metrics']['coordinate_quantization_guard_q8']==1 and o['metrics']['valid_support_continuous_margin_q8']==128+o['guard'],'frozen unqualified guard arithmetic')
    else:need(marks==[] and o['heldout_bbox_q8'] is None and o['status']=='RETURNED' and o['error'] is None,'off/placebo signature only')
    return site_check(o)

def representation(r,shape):
    need(r['method']=='m193c-area8-native-centres-v1' and r['factor']==8 and r['centre_q8']==896 and r['key_coordinate_gauge']=='coarse Q8; unchanged detector keys' and r['native_shape']==shape and r['coarse_shape']==[shape[0]//8,shape[1]//8,3],'fixed AREA8')
    hv(r['coarse_rgb_sha256_u16_le'])

def lifted_arrays(coarse,native,count):
    coordinate_rows(coarse);coordinate_rows(native)
    need(integer(count) and 0<count<=1024 and len(coarse)==len(native)==count,'actual feature count')
    need(all(n==[8*x+896 for x in c] for c,n in zip(coarse,native)),'actual coordinate lift')

def private_features(ref,fixtures):
    r=read(ref);need(path(ref)==OUT/'worker/rotation-feature-record.json','private feature path')
    need(r['schema']=='m193c-factor-eight-private-features-v1' and r['qualification']==QUAL,'private schema')
    need(any(same(r['fixture'],f) for f in fixtures),'private fixture association');image_stat(r['fixture'])
    known=actual(ROOT/'experiments/M193-cover-overlap/fixtures.json')['synthetic_overlap']['sources'][0]
    need(r['fixture']['sha256']==known['source_sha256'],'literal first fixture')
    for name,shape in (('reference',[2304,3072,3]),('source',[3072,2304,3])):
        f=r[name];representation(f['representation'],shape);lifted_arrays(f['coarse_coordinates_q8'],f['native_coordinates_q8'],f['count']);hv(f['descriptors_sha256']);hv(f['keys_sha256'])
    return r

def true_rotation_landmarks(rows):
    from statistics import median
    # All captured rows, no fit-selected subset and no fitted constant.
    offsets=[(r['reference_q8'][0]-(3071*256-r['source_q8'][1]),r['reference_q8'][1]-r['source_q8'][0]) for r in rows]
    squares=[x*x+y*y for x,y in offsets]
    need(len(rows)>0,'truth-score population')
    return dict(scope='all captured landmarks against literal source-to-reference native-centre rotation',count=len(rows),within_two_native_pixels=sum(s<=(2*256)**2 for s in squares),rms_native_pixels=math.sqrt(sum(squares)/len(rows))/256,median_offset_reference_minus_truth_native_pixels=[median(x for x,y in offsets)/256,median(y for x,y in offsets)/256])

def control_audit(rows,fixtures):
    need([r['id'] for r in rows]==ALL_IDS[:len(rows)] and 7<=len(rows)<=14,'fixed control prefix')
    for r in rows:need(type(r['passed']) is bool,'typed control outcome')
    controls(rows[:7])
    for r in rows:saved(OUT/'worker'/('control-'+r['id']+'.json'),r,True)
    e={r['id']:r['evidence'] for r in rows};private=None;positive=None;audit=[]
    for row in rows[7:]:
        name=row['id'];v=row['evidence'];site_summary=None;truth_summary=None
        if set(v)=={'exception'}:
            need(row is rows[-1] and row['passed'] is False and type(v['exception']) is str and 'Traceback' in v['exception'],'retained private exception')
            audit.append(dict(id=name,passed=False,exception=True));break
        if name=='area8-half-ties':
            sums=[31,32,33,95,96,97,64*65535];expected=[[[round(s/64)]*3 for s in sums]]
            need(v['input_channel_sums']==sums and v['expected']==expected,'independent ties-even truth');ok=v['actual']==expected
        elif name=='repeated-block-null':
            need(any(same(v['fixture'],f) for f in fixtures),'repeated fixture ref')
            representation(v['reference'],[2304,3072,3]);representation(v['source'],[3072,2304,3]);hs=v['actual_sha256']
            need(set(hs)=={'original','coarse_reference','expected_rotation','coarse_source'},'null hash keys')
            for h in hs.values():hv(h)
            need(hs['coarse_reference']==v['reference']['coarse_rgb_sha256_u16_le'] and hs['coarse_source']==v['source']['coarse_rgb_sha256_u16_le'],'representation hash association')
            ok=hs['original']==hs['coarse_reference'] and hs['expected_rotation']==hs['coarse_source']
        elif name=='native-rotation-positive':
            private=private_features(v['features'],fixtures);positive=v['outcome']
            site_summary=observed(positive,private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8'])
            check_corners(v['corner_errors'],positive['transform'])
            need(v['literal_truth_q32']==dict(a=0,b=Q,tx=3071*Q,ty=0),'independent rotation truth')
            ok=positive['status']=='RETURNED' and len(positive['landmarks'])>=24 and corner_pass(positive['transform'])
            if positive['landmarks']:truth_summary=true_rotation_landmarks(positive['landmarks'])
        elif name=='native-two-pixel-map-destroyer':
            need(positive is not None and v['baseline']==positive['transform'] and v['qualification']==QUAL and v['added_native_px']==2,'two-pixel baseline')
            need(v['mutated']==dict(positive['transform'],tx=positive['transform']['tx']+2*Q),'tx mutation only')
            check_corners(v['corner_errors'],v['mutated']);ok=not corner_pass(v['mutated'])
        elif name=='centre-offset-destroyer':
            need(private is not None and same(v['features'],e['native-rotation-positive']['features']) and v['active_omission_q8']==896,'same private features')
            o=v['outcome'];site_summary=observed(o,[[8*x for x in p] for p in private['reference']['coarse_coordinates_q8']],[[8*x for x in p] for p in private['source']['coarse_coordinates_q8']],missing=True)
            check_corners(v['corner_errors'],o['transform']);ok=o['status']=='RETURNED' and not corner_pass(o['transform'])
        elif name=='native-rotation-restored':
            o=v['outcome'];site_summary=observed(o,private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8']);check_corners(v['corner_errors'],o['transform'])
            ok=signature(o)==signature(positive) and v['corner_errors']==e['native-rotation-positive']['corner_errors'] and o['status']=='RETURNED' and corner_pass(o['transform'])
        elif name=='rotation-observer-null':
            for mode in ('off','count','placebo'):observed(v[mode],private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8'],captured=mode=='count')
            need(v['count']==e['native-rotation-restored']['outcome'],'count reuses restored call')
            expected={k:sha(canonical(signature(v[k]))) for k in ('off','count','placebo')}
            need(v['canonical_signature_sha256']==expected,'canonical observer hashes');ok=len(set(expected.values()))==1 and len(v['count']['landmarks'])>=24
        need(row['passed'] is ok,'saved boolean versus independent predicate: '+name)
        audit.append(dict(id=name,passed=ok,corner_errors=v.get('corner_errors'),captured_landmarks=len(v.get('outcome',{}).get('landmarks',[])),site_summary=site_summary,literal_truth_all_landmarks=truth_summary))
        if not ok:need(row is rows[-1],'no continuing after failed control')
    all_pass=len(rows)==14 and all(r['passed'] for r in rows)
    if all_pass:saved(OUT/'worker/controls.json',rows,True)
    else:need(not (OUT/'worker/controls.json').exists(),'no complete control record after failure')
    if private is None and (OUT/'worker/rotation-feature-record.json').exists():private=private_features(file(OUT/'worker/rotation-feature-record.json'),fixtures)
    return dict(all_fourteen_pass=all_pass,rows=[dict(id=r['id'],passed=r['passed']) for r in rows],additive_checks=audit,private_features_present=private is not None,private_counts=None if private is None else {k:private[k]['count'] for k in ('reference','source')})

def commissioning():
    truth=dict(a=0,b=Q,tx=3071*Q,ty=0)
    need(corner_pass(truth),'commission literal rotation');need(not corner_pass(dict(truth,tx=3064*Q)),'commission missing centre')
    need(not corner_pass(dict(truth,tx=3073*Q)),'commission two native pixels');need(corner_pass(dict(truth,tx=3072*Q)),'commission exact boundary');need(not corner_pass(dict(truth,b=-Q)),'commission wrong sign')
    def row(x,s):return dict(reference_q8=[x,0],source_q8=[x,0],split=s)
    duplicate=[row((i//6)*2560,'calibration' if i%2==0 else 'holdout') for i in range(12)];distinct=[row(i*2560,'calibration' if i%2==0 else 'holdout') for i in range(12)]
    need(near_components(duplicate,'joint')['groups']==2 and near_components(duplicate,'joint')['mixed_split_groups']==2,'commission repeated sites')
    need(near_components(distinct,'joint')['groups']==12 and near_components(distinct,'joint')['mixed_split_groups']==0,'commission distinct sites')
    chain=near_components([row(0,'calibration'),row(192,'calibration'),row(384,'holdout')],'joint')
    need(chain['groups']==1 and chain['chained_components']==1 and chain['max_component_diameter_native_px']==1.5,'commission chain disclosure')
    correct=[dict(source_q8=[256*x,256*y],reference_q8=[256*(3071-y),256*x]) for x,y in ((11,19),(2048,2500),(301,401))]
    shifted=[dict(r,reference_q8=[r['reference_q8'][0]+4*256,r['reference_q8'][1]]) for r in correct]
    good,bad=true_rotation_landmarks(correct),true_rotation_landmarks(shifted)
    need(good['within_two_native_pixels']==3 and good['rms_native_pixels']==0 and bad['within_two_native_pixels']==0 and bad['rms_native_pixels']==4,'commission all-landmark known shift')
    return ['literal_rotation','missing_centre','plus_two_native','one_pixel_boundary','wrong_rotation_sign','repeated_sites','distinct_companion','chain_disclosure','all_landmarks_literal_truth','all_landmarks_four_pixel_shift']

def all_inventory():
    rows=[]
    # os.walk includes hidden/system entries; no attribute-based filtering.
    for base,dirs,names in os.walk(OUT,followlinks=False):
        for name in dirs:need(not getattr((Path(base)/name).stat(follow_symlinks=False),'st_file_attributes',0)&0x400,'no reparse output directory')
        for name in names:rows.append(file(Path(base)/name))
    return sorted(rows,key=lambda r:r['path'])

def main():
    cpu,wall=time.process_time(),time.perf_counter();parser=argparse.ArgumentParser()
    for k in ('plan','result','outer','console','exit'):parser.add_argument('--'+k+'-sha256',required=True)
    args=parser.parse_args();commissioned=commissioning();refs={}
    names=dict(plan=HERE/'factor-eight-plan-1.json',result=OUT/'result.json',outer=HERE/'work/factor-eight-1-outer.json',console=HERE/'work/factor-eight-1-console.txt',exit=HERE/'work/factor-eight-1-exit.txt')
    for k,p in names.items():refs[k]=file(p);need(refs[k]['sha256']==getattr(args,k+'_sha256'),'external actual '+k)
    plan,parent,outer=(read(refs[k]) for k in ('plan','result','outer'))
    console=strict(path(refs['console']).read_bytes().splitlines()[-1]);exit_code=int(path(refs['exit']).read_bytes().strip())
    need(set(plan)==set('schema source_bindings native_baseline prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-factor-eight-plan-v1','closed new plan')
    need(set(plan['native_baseline'])==set('plan result outer console exit audit'.split()),'six baseline references')
    need(set(outer)==set('scope command plan_sha256 exit_code elapsed_wall_seconds admissible_parent_exit'.split()) and outer['plan_sha256']==refs['plan']['sha256'],'closed actual outer')
    for relative,binding in plan['source_bindings'].items():file(ROOT/relative,dict(path=relative,**binding))
    for relative,pin in (('factor-eight-run.py',RUNNER_PIN),('factor-eight-preregister.md',SPEC_PIN)):
        r=file(HERE/relative);need((r['bytes'],r['sha256'])==pin,'held executed '+relative)
    py=file(path(plan['python_executable']),plan['python_executable'])
    native={k:read(v) if k in ('plan','result','outer','audit') else file(path(v),v) for k,v in plan['native_baseline'].items()}
    old,audit=native['plan'],native['audit']
    need(plan['native_baseline']['audit']['sha256']==NATIVE_AUDIT and audit['status']=='PASS_SAVED_DIRECT_PAIR_OUTCOME_AUDIT' and audit['subject_complete'] is True,'pinned native audit')
    need(len(old['source_bindings'])==170 and all(plan['source_bindings'].get(k)==v for k,v in old['source_bindings'].items()),'old 170 bindings preserved')
    for k in ('plan','result','outer','console','exit'):need(same(plan['native_baseline'][k],audit['external'][k]),'native audit association')
    native_parent=native['result'];native_worker=read(native_parent['worker_result']);native_request=read(native_parent['request'])
    need(same(native_parent['worker_result'],audit['worker_result']) and native_parent['status']==native_worker['status']=='COMPLETE_DIRECT_PAIR_SUPPORT_ONLY' and native_parent['sources_unchanged'] is True and native_worker['sources_unchanged'] is True and native_parent['error'] is native_worker['error'] is None and native_parent['finalization_errors']==native_worker['finalization_errors']==[],'cached complete native authority')
    schedule=planned();need([r['pair'] for r in native_worker['pairs']]==schedule and all(r['outcome']['status']=='REGISTRATION_REFUSED' for r in native_worker['pairs']),'23 cached native refusals')
    prior=read(plan['prior_work']);need(plan['preparation_allowance']==BUDGET,'whole preparation allowance')
    for k,extra in BUDGET.items():need(D(str(prior[k]))==D(audit['next_wall_seconds'] if k=='wall_seconds' else str(audit['actual_final_work'][k]))+extra,'exact no-refund carry')
    need(prior==dict(cpu_seconds=452.453125,wall_seconds=517.0575196,file_bytes=3951075537,metadata_bytes=25874891),'literal new carry')
    need(set(plan['commands'])=={'parent','worker'},'two exact commands');base=[py['path'],'-B','-X','faulthandler','-X']
    pc=base+['pycache_prefix='+str(OUT/'parent-cache'),str(HERE/'factor-eight-run.py'),'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT)]
    command=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else x for x in plan['commands']['parent']]
    need(pc==command==parent['command']==outer['command'] and same(parent['plan'],refs['plan']),'independent parent argv')
    need(integer(outer['exit_code']) and outer['exit_code']==exit_code and outer['admissible_parent_exit'] is (exit_code==0),'actual parent exit')
    need(parent['schema']=='m193c-factor-eight-run-v1' and parent['source_bindings']==plan['source_bindings'] and parent['prior_work']==prior and parent['qualification']==QUAL,'parent association')
    need(parent['sources_unchanged'] is True and parent['finalization_errors']==[],'parent final checks')
    need(console['status']==parent['status'] and Path(console['result']).resolve()==OUT/'result.json' and console['error']==parent['error'] and console['finalization_errors']==parent['finalization_errors'],'terminal publication')
    need(parent['request'] is not None and parent['worker_result'] is not None and parent['child'] is not None,'audited branch has worker')
    request=read(parent['request']);worker=read(parent['worker_result'])
    need(set(request)==set('schema plan pairs rows fixtures native_pairs prior_work'.split()) and request['schema']=='m193c-factor-eight-request-v1','closed request')
    need(same(request['plan'],refs['plan']) and request['pairs']==schedule and request['rows']==native_request['rows'] and request['fixtures']==native_request['fixtures'],'same requested population')
    need([(r['ordinal'],r['original_index']) for r in request['rows']]==list(enumerate(ORIGINAL)) and len(request['fixtures'])==5,'literal nine/five population')
    for r in request['rows']:image_stat(r['tiff'])
    for r in request['fixtures']:image_stat(r)
    need(len(request['native_pairs'])==23,'cached native FileRef count')
    for i,r in enumerate(request['native_pairs']):need(path(r)==HERE/'direct-pair-1/worker'/(schedule[i]['id']+'.json') and read(r)==native_worker['pairs'][i],'exact cached pair FileRef')
    need(all(request['prior_work'][k]>=prior[k] for k in prior),'setup carry into request')
    pair_plan=dict(rows=request['rows'],pairs=schedule,native_pairs=request['native_pairs'])
    saved(OUT/'pair-plan.json',pair_plan,True);saved(OUT/'worker/pair-plan.json',pair_plan,True)
    need(worker['schema']=='m193c-factor-eight-worker-v1' and worker['request']==parent['request'] and worker['plan']==parent['plan'] and worker['source_bindings']==plan['source_bindings'] and worker['prior_work']==prior and worker['qualification']==QUAL and worker['sources_unchanged'] is True and worker['finalization_errors']==[],'worker final/associations')
    wc=base+['pycache_prefix='+str(OUT/'worker-cache'),str(HERE/'factor-eight-run.py'),'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256',parent['request']['sha256']]
    expected=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else parent['request']['sha256'] if x=='ACTUAL_REQUEST_SHA256' else x for x in plan['commands']['worker']]
    child=parent['child'];need(wc==expected==child['command']==worker['command'],'independent worker argv')
    need(parent['environment']==dict.fromkeys(('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'),'2') and parent['removed_environment']==sorted(set(parent['removed_environment'])),'bounded saved environment')
    need(not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'no bytecode/cache artifacts')
    ctrl=control_audit(worker['controls'],request['fixtures']);complete=parent['status']=='COMPLETE_FACTOR_EIGHT_SUPPORT_ONLY'
    features=[];fs=[];pairs=[];records=[];graph=None
    if ctrl['all_fourteen_pass']:
        need(complete and worker['status']==parent['status'] and worker['error'] is parent['error'] is None and worker['real_decode_attempts']==worker['real_decodes_completed']==9 and len(worker['features'])==9 and len(worker['pairs'])==23,'complete real phase')
        for i,ref in enumerate(worker['features']):
            need(path(ref)==OUT/'worker'/f'feature-{i}.json','feature FileRef path');f=read(ref);features.append(f)
            need(f['original_index']==ORIGINAL[i] and same(f['tiff'],request['rows'][i]['tiff']),'real feature association')
            if f['representation'] is not None:representation(f['representation'],[4688,7032,3])
            if f['status']=='RETURNED':
                need(f['error'] is None and f['representation'] is not None,'returned feature receipt');r=f['representation'];lifted_arrays(r['coarse_coordinates_q8'],r['native_coordinates_q8'],f['count'])
                need(f['coordinates_q8']==r['native_coordinates_q8'],'emitted native coordinates');hv(f['descriptors_sha256']);hv(f['keys_sha256'])
            else:need(f['status']=='FEATURE_UNAVAILABLE' and f['error']['code']==CODE,'feature scientific refusal')
            fs.append(dict(original_index=ORIGINAL[i],status=f['status'],count=f.get('count'),representation=f['representation'] is not None,keys_sha256=f.get('keys_sha256'),descriptors_sha256=f.get('descriptors_sha256')))
        for i,index in enumerate(worker['pairs']):
            need(index['pair']==schedule[i] and path(index['record'])==OUT/'worker'/(schedule[i]['id']+'.json'),'ordered pair FileRef')
            record=read(index['record']);records.append(record);o=record['outcome'];p=record['pair']
            need(p==schedule[i] and same(record['native_baseline'],request['native_pairs'][i]) and index['status']==o['status'],'pair cached association')
            a,z=p['reference'],p['source'];missing=[j for j in (a,z) if features[j]['status']!='RETURNED'];sites=None
            if missing:need(o==dict(status='FEATURE_UNAVAILABLE',unavailable=missing,qualification=QUAL),'unavailable propagation')
            else:sites=observed(o,features[a]['coordinates_q8'],features[z]['coordinates_q8'])
            err=o.get('error');pairs.append(dict(id=p['id'],source=z,reference=a,status=o['status'],matches=len(o.get('landmarks',[])),error=None if err is None else {k:err[k] for k in ('code','message')},site_summary=sites))
        need(worker['unvisited']==parent['unvisited']==[] and worker['graph']==parent['graph'] and worker['graph']['qualification']==QUAL,'complete topology')
        graph=topology(records,worker['graph']);need(exit_code==child['exit_code']==0,'complete exits')
    else:
        need(not complete and parent['status']==worker['status']=='REFUSED' and exit_code==child['exit_code']==1 and parent['error'] is not None and worker['error'] is not None,'failed control remains refusal')
        need(worker['controls'][-1]['passed'] is False and len(worker['controls'])>=8,'named additive failed control')
        need(worker['real_decode_attempts']==worker['real_decodes_completed']==0 and worker['features']==worker['pairs']==[] and worker['unvisited']==parent['unvisited']==list(range(23)) and worker['graph'] is parent['graph'] is None,'zero real phase after failed control')
        need(not list((OUT/'worker').glob('feature-*.json')) and not list((OUT/'worker').glob('pair-[0-9]*.json')),'no real records after failed control')
    need(parent['features']==parent['pairs']==parent['controls']==[] and parent['real_decode_attempts']==parent['real_decodes_completed']==0,'parent owns no worker counters')
    runtime=actual(ROOT/'experiments/M193-cover-overlap/contract-v1.json')['reference_environment']
    need(worker['runtime_before']==runtime and worker['runtime_after']==(runtime if complete else None),'runtime branch')
    need(child['error'] is None and child['cleanup_errors']==[] and child['terminal_job_accounting'] is True and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['job_accounting']['active_processes']==0 and child['termination']['attempted'] is False and child['post_exit_drain']['completed'] is True,'terminal Job no kill/error')
    account=child['job_accounting'];need(all(integer(account[k]) for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and account['total_cpu_100ns']==account['total_user_100ns']+account['total_kernel_100ns'],'CPU components')
    log=file(OUT/'worker.log');need(child['log_bytes']==log['bytes'] and (child.get('log') is None or same(child['log'],log)),'actual worker log')
    terminal=strict(path(log).read_bytes().splitlines()[-1]);need(terminal['status']==worker['status'] and terminal['error']==worker['error'] and terminal['finalization_errors']==worker['finalization_errors'] and Path(terminal['result']).resolve()==OUT/'worker/result.json','worker terminal publication')
    need(console['cpu_accounting_complete'] is True and parent['work']['cpu_accounting_complete'] is True and terminal['cpu_accounting_complete'] is True and worker['work']['cpu_accounting_complete'] is True,'complete CPU accounting even on refusal')
    inventory=all_inventory();total=sum(r['bytes'] for r in inventory);work=console['work_through_final_checks']
    need(parent['work']['snapshot_bytes']==worker['work']['snapshot_bytes']==0,'no snapshots')
    need(work['file_bytes']-prior['file_bytes']==work['metadata_bytes']-prior['metadata_bytes']==total,'all actual metadata charged once')
    need(parent['work']['new_extent_bytes']+refs['result']['bytes']==total,'prepublication extent plus result')
    need(D(str(work['cpu_seconds']))-D(str(prior['cpu_seconds']))>=D(account['total_cpu_100ns'])/10000000,'whole terminal Job CPU charged')
    limits=child['limits'];caps={k:D(str(work[k]))-D(str(prior[k]))<=v for k,v in dict(cpu_seconds=300,wall_seconds=480,file_bytes=8<<20,metadata_bytes=8<<20).items()}
    need(all(D(str(work[k]))>=D(str(prior[k])) for k in prior),'no refund')
    caps['global']=work['cpu_seconds']<=1200 and work['wall_seconds']<=1800 and work['file_bytes']<=4*(1<<30) and work['metadata_bytes']<=128*(1<<20)
    caps['child_cpu']=account['total_cpu_100ns']/1e7<=limits['cpu_seconds']<=300;caps['child_wall']=child['wall_seconds']<=limits['wall_seconds']<=240
    caps['child_memory']=child['job_memory']['peak_job_memory_used_bytes']<=limits['committed_bytes']==8*(1<<30);caps['child_log']=log['bytes']<=limits['log_bytes']==1<<20
    need(child['configured_job_limits']['committed_bytes']==limits['committed_bytes'] and all(caps.values()),'actual owned caps')
    for ref in list(USED.values()):file(path(ref),ref)
    for s0 in list(TIFF_STAT):
        s=path(s0['reference']).stat(follow_symlinks=False);need((s.st_size,s.st_dev,s.st_ino,s.st_mtime_ns)==(s0['bytes'],s0['device'],s0['file_id'],s0['mtime_ns']),'unopened TIFF metadata stable')
    result=dict(schema='m193c-saved-factor-eight-audit-v1',status='PASS_SAVED_FACTOR_EIGHT_OUTCOME_AUDIT',subject_complete=complete,subject_status=parent['status'],worker_status=worker['status'],subject_branch='COMPLETE_DIAGNOSTIC_POPULATION' if complete else 'NAMED_CONTROL_FAILED_ZERO_REAL_DECODES',refused_control=None if complete else worker['controls'][-1]['id'],external=refs,audit_source=file(__file__),commissioning=commissioned,native_baseline=plan['native_baseline'],worker_result=parent['worker_result'],controls=ctrl,features=fs,pairs=pairs,graph=graph,qualification=QUAL,unvisited=worker['unvisited'],real_decode_attempts=worker['real_decode_attempts'],real_decodes_completed=worker['real_decodes_completed'],actual_final_work=work,next_wall_seconds=str(D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))),job=child,caps=caps,cpu_accounting_complete=True,inventory=inventory,inventory_total_bytes=total,tiff_extent_checks_only=TIFF_STAT,unique_hashed_metadata_files=len(USED),retention_gaps=GAPS,audit_timing=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall),scope='Saved JSON/metadata only; no TIFF/RAW payload hash, decode, features, matching or fit. Coarse image/descriptor/key hashes are opaque producer witnesses. Returned fits/topology remain unqualified for support, overlap, placement and quality.')
    raw=json.dumps(result,sort_keys=True,allow_nan=False,separators=(',',':')).encode();need(len(raw)<=120*(1<<10),'bounded audit result');print(raw.decode())

if __name__=='__main__':main()
