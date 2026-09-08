"""Prospective saved SIFT-export/private-LightGlue auditor; no subject imports.
Re-choices: exact exported bytes -> original keys/units, scalar float64 RootSIFT
against all actual float32 values, every learned row -> literal physical truth,
exact/radius-one coordinate groups, full metadata/Job/outer inventory. No images,
network, model/checkpoint deserialization, fitting or hypothesis enumeration.
Execute once only after root supplies the five actual outcome digests.
"""
import argparse
from collections import Counter
from decimal import Decimal as D, ROUND_CEILING
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import statistics
import struct
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
OUT=HERE/'sift-lightglue-commission-1'
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
MIB=1<<20
Q=1<<32
BOUND=2**-15
COMPLETE='COMPLETE_SIFT_EXPORT_AND_PRIVATE_LIGHTGLUE_COMMISSION_ONLY'
VERSION='m193c-sift-lightglue-commission-v1'
PINS={
 'sift-lightglue-commission-run.py':(37987,'00ea4a61e59ebc1e36c74cf77ea63bc3167d28e94c5fa84d4ed76eb2a6fd73b1'),
 'sift-lightglue-adapter.py':(24011,'febb91b856ac17c9d453d16e81aa412e9ea46465ca1bc03c9ce3b189e604495c'),
 'sift-lightglue-commission-preregister.md':(20812,'c4889bb8773ad6950282ad9fc9692af578529a5f5f18597c7a00b87a7ad62269')}
AUDITS={'area4':(97082,'02c97674a2128fc1d31ba687aa0fe3e98648e5a0604783ad4006166b29814adc'),
 'acquisition':(21345,'a539ba714a870eea0be485388b322c50bdff1fb48e31a53df72acc4d2f6b1b65'),
 'area8':(78821,'7920f885e0cea2bcfbe2ac4f9af9ffc519212495274798cee23b79aa2e179ccc'),
 'private':(25983,'471c68d50e1cca2804eec32e38756d06b3e0d8db79716de1450fb038ff197b5e')}
CONTROLS=['private-cache-reproduction','serializer-readback-observer-destroyers-restored',*[f'real-cache-reproduction-{i}' for i in range(9)],'private-model-input-observer','private-learned-known-geometry','native-two-pixel-map-destroyer','saved-match-registrar-observer','within-split-association-destroyer','private-restored']
KWARGS=dict(nfeatures=2048,nOctaveLayers=3,contrastThreshold=0.01,edgeThreshold=12,sigma=1.6,enable_precise_upscale=True)
CONF=dict(input_dim=128,descriptor_dim=256,add_scale_ori=True,n_layers=9,num_heads=4,flash=False,mp=False,depth_confidence=-1,width_confidence=-1,filter_threshold=0.1,weights=None)
QUAL=dict(coordinate_gauge='native pixel centres; q_native=8*q_coarse+896',coordinate_lattice_step_q8=8,inherited_quantization_guard_q8=1,guard_status='UNQUALIFIED_FOR_COARSE_LATTICE',scope='Private compatibility/known geometry only; no real model pairs, support, overlap, placement or quality admission')
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
USED={}
IDENTITIES={}
RUNTIME=set()
START=CPU=None


def need(ok,message):
    if not ok:raise ValueError(message)

def integer(x):return type(x) is int

def sha(raw):return hashlib.sha256(raw).hexdigest()

def canonical(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def strict(raw):
    def unique(rows):
        d={}
        for k,v in rows:need(k not in d,'duplicate JSON key');d[k]=v
        return d
    x=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:need(False,'nonfinite literal'))
    def walk(v):
        if type(v) is float:need(math.isfinite(v),'overflow JSON number')
        elif isinstance(v,dict):
            for z in v.values():walk(z)
        elif isinstance(v,list):
            for z in v:walk(z)
    walk(x);return x

def path(r):return (ROOT/r['path']).resolve()

def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,getattr(s,'st_file_attributes',0))

def same(a,b):return path(a)==path(b) and all(a[k]==b[k] for k in ('bytes','sha256'))

def file(p,expected=None,kind='metadata'):
    p=Path(p).resolve()
    need(p.suffix.lower() not in {'.arw','.dng','.raw','.tif','.tiff','.png','.jpg','.jpeg','.exr','.bmp'},'no image payload or stat')
    if kind=='metadata':need((p.is_relative_to(ROOT) and p.suffix.lower() in {'.py','.json','.md','.txt','.log','.rs','.toml','.lock','.tsv'}) or p==PYTHON,'metadata/source boundary');cap=32*MIB
    elif kind=='export':need(p.parent==OUT/'worker' and p.suffix in {'.u8','.i64','.f32'},'fixed owned export');cap=512*1024
    elif kind=='checkpoint':need(p==HERE/'lightglue-acquisition-1/sift-lightglue.pth','one opaque checkpoint');cap=64*MIB
    else:need(kind=='runtime' and str(p) in RUNTIME,'manifest-bound opaque runtime');cap=2<<30
    s=p.stat(follow_symlinks=False);need(not (getattr(s,'st_file_attributes',0)&0x400) and s.st_nlink==1 and 0<=s.st_size<=cap,'ordinary bounded single-link file')
    before=identity(s)
    if str(p) in USED:need(before==IDENTITIES[str(p)],'previously hashed identity unchanged');r=USED[str(p)]
    else:
        h=hashlib.sha256();count=0
        with p.open('rb') as stream:
            need(identity(os.fstat(stream.fileno()))==before,'opened identity')
            for block in iter(lambda:stream.read(MIB),b''):h.update(block);count+=len(block);need(count<=cap,'actual hash extent')
        need(identity(p.stat(follow_symlinks=False))==before and count==s.st_size,'stable complete bytes')
        r=dict(path=str(p),bytes=count,sha256=h.hexdigest());USED[str(p)]=r;IDENTITIES[str(p)]=before
    if expected is not None:need(set(expected)=={'path','bytes','sha256'} and integer(expected['bytes']) and same(r,expected),'exact FileRef association')
    return r

def raw(r,kind='metadata'):
    file(path(r),r,kind);b=path(r).read_bytes();need(len(b)==r['bytes'] and sha(b)==r['sha256'],'same parsed/payload bytes');return b

def read(r):return strict(raw(r))

def actual(p):return read(file(p))

def close(a,b):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)

def comparison(got,label,left,right):
    l,r=canonical(left),canonical(right)
    e=dict(label=label,method='entire registrar return/refusal or trace; exact canonical bytes',equal=l==r,left=dict(bytes=len(l),sha256=sha(l)),right=dict(bytes=len(r),sha256=sha(r)))
    need(got==e,'entire canonical predicate '+label);return l==r

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]

def pack(values,code):return b''.join(struct.pack('<'+code,v) for v in values)

def flatten(x):
    if type(x) is list:return list(itertools.chain.from_iterable(flatten(v) for v in x))
    return [x]

def arr(values,shape,dtype):
    vals=flatten(values);n=math.prod(shape);need(len(vals)==n,'array product')
    code={'<f4':'f','<i8':'q','|u1':'B'}[dtype]
    need(all(math.isfinite(x) for x in vals),'finite reconstructed array')
    return dict(dtype=dtype,shape=shape,sha256=sha(pack(vals,code)))

def original_pairs():
    edges=[(0,1),(0,2),(0,4),(0,5),(1,2),(1,3),(1,5),(2,3),(2,4),(2,5),(2,6),(3,4),(3,5),(3,7),(4,5),(4,6),(4,8),(5,6),(5,7),(5,8),(6,7),(6,8),(7,8)]
    return [dict(id=f'pair-{a}-{z}',reference=5 if 5 in (a,z) else a,source=(z if a==5 else a) if 5 in (a,z) else z,reference_original=65 if 5 in (a,z) else a*13,source_original=((z if a==5 else a) if 5 in (a,z) else z)*13) for a,z in edges]

def audit_bundle(refs,key,status):
    need(set(refs)==set('plan result outer console exit audit'.split()),'closed six-reference authority')
    need((refs['audit']['bytes'],refs['audit']['sha256'])==AUDITS[key],'held independent baseline '+key)
    a=read(refs['audit']);p=read(refs['result']);old=read(refs['plan']);outer=read(refs['outer'])
    need(a['status']==status and a['subject_complete'] is True and a['cpu_accounting_complete'] is True,'complete baseline audit')
    for k in ('plan','result','outer','console','exit'):need(same(a['external'][k],refs[k]),'baseline external association');file(path(refs[k]),refs[k])
    need(same(p['plan'],refs['plan']) and type(outer['exit_code']) is int and outer['exit_code']==0 and outer['admissible_parent_exit'] is True and raw(refs['exit']).strip()==b'0','baseline terminal exit')
    return old,p,a,outer

def baseline(plan):
    a4,p4,audit4,_=audit_bundle(plan['area4_baseline'],'area4','PASS_SAVED_AREA_FOUR_OUTCOME_AUDIT')
    need(len(a4['source_bindings'])==210 and all(plan['source_bindings'].get(k)==v for k,v in a4['source_bindings'].items()),'all 210 old sources preserved')
    w4=read(p4['worker_result']);need(same(p4['worker_result'],audit4['worker_result']) and len(w4['controls'])==14 and all(c['passed'] for c in w4['controls']) and len(w4['features'])==9 and len(w4['pairs'])==23 and all(x['status']=='REGISTRATION_REFUSED' for x in w4['pairs']) and w4['unvisited']==[],'complete AREA4 refusal population')
    trace=read(a4['trace_baseline']['plan']);rplan,rparent,ra,_=audit_bundle(trace['real_baseline'],'area8','PASS_SAVED_REAL_PRECISE_OUTCOME_AUDIT');rw=read(rparent['worker_result']);rq=read(rparent['request'])
    need(same(rparent['worker_result'],ra['worker_result']) and len(rw['features'])==9 and len(rw['pairs'])==23 and len(rw['controls'])==14 and all(x['passed'] for x in rw['controls']) and all(x['status']=='REGISTRATION_REFUSED' for x in rw['pairs']) and rw['unvisited']==[],'same complete AREA8 population')
    need([x['original_index'] for x in rq['rows']]==list(range(0,105,13)) and len(rq['pairs'])==23,'exact nine image identities and directions')
    for x,y in zip(rq['pairs'],original_pairs(),strict=True):need(all(x[k]==v for k,v in y.items()),'fixed native direction schedule')
    pp,pr,pa,_=audit_bundle(rplan['private_baseline'],'private','PASS_SAVED_PRECISE_UPSCALE_CANONICAL_OUTCOME_AUDIT');pw=read(pr['worker_result']);arm=read(pw['arms'][1]);private=read(arm['feature_record'])
    need(same(pr['worker_result'],pa['worker_result']) and arm['name']=='precise-true' and arm['outcome']['status']=='RETURNED','original audited precise-true private')
    for x in (rplan,pp):need(all(plan['source_bindings'].get(k)==v for k,v in x['source_bindings'].items()),'preserved private/AREA8 closure')
    ap,ar,aa,_=audit_bundle(plan['acquisition_receipt'],'acquisition','PASS_SAVED_LIGHTGLUE_ACQUISITION_OUTCOME_AUDIT')
    need(aa['admission_allowed'] is True and aa['subject_status']=='COMPLETE_SOURCE_AND_CHECKPOINT_ACQUISITION_ONLY' and len(ap['source_bindings'])==214 and all(plan['source_bindings'].get(k)==v for k,v in ap['source_bindings'].items()),'admitted entire intake closure')
    assets={x['asset']['id']:x['payload'] for x in aa['assets']['rows']}
    for k,r in assets.items():file(path(r),r,'checkpoint' if k=='checkpoint' else 'metadata')
    need(len(assets)==5 and assets['checkpoint']['bytes']==47632573 and aa['upstream_checkpoint_digest'] is None,'opaque checkpoint identity, no publisher digest')
    prior=read(plan['prior_work']);base=dict(aa['actual_final_work']);base['wall_seconds']=D(aa['next_wall_seconds']).quantize(D('.000001'),rounding=ROUND_CEILING)
    need(set(prior)==set(ALLOWANCE) and all(D(str(prior[k]))==D(str(base[k]))+ALLOWANCE[k] for k in prior),'complete intake carry plus preparation, no refund')
    return dict(private=private,private_ref=arm['feature_record'],real=[read(r) for r in rw['features']],real_refs=rw['features'],rows=rq['rows'],assets=assets,prior=prior,area8_refs=trace['real_baseline'])

def factory(w,scope,i):
    keys=set('scope ordinal requested_true calls restored error'.split())|({'original_index'} if scope=='real' else set())
    need(set(w)==keys and w['scope']==scope and w['ordinal']==i and w['requested_true'] is True and len(w['calls'])<=1 and w['restored'] is True,'fixed factory attempt/restoration')
    if scope=='real':need(w['original_index']==13*i,'factory exact original index')
    for k in w['calls']:need(k==KWARGS and all(type(k[n]) is type(v) for n,v in KWARGS.items()),'exact constructor flag/kwargs')
    return len(w['calls'])==1 and w['error'] is None

def core_expected(cached,private):
    if private:return {k:cached[k] for k in ('count','coarse_coordinates_q8','native_coordinates_q8','descriptors_sha256','keys_sha256')}
    return dict(count=cached['count'],coarse_coordinates_q8=cached['representation']['coarse_coordinates_q8'],native_coordinates_q8=cached['coordinates_q8'],descriptors_sha256=cached['descriptors_sha256'],keys_sha256=cached['keys_sha256'])

def exported(ref,expected,name,size,cache,side=None):
    value=read(ref);n=expected['count'];need(path(ref)==OUT/'worker'/(name+'.json'),'fixed export manifest path')
    need(value['schema']=='m193c-sift-export-feature-v1' and value['name']==name and value['core']==expected and same(value['origin']['cache'],cache),'whole cached export identity')
    if side:need(value['origin']['side']==side,'private side')
    need(value['qualification']==QUAL and value['attribute_provenance']=='QUANTIZED_KEY_DERIVED_ATTRIBUTES' and value['explicit_coarse_image_size']==size and value['attribute_recipe']=='size_q8/256; (angle_degrees_q8/256)*pi/180; binary64 then float32','explicit key-derived units')
    need(integer(n) and 24<=n<=1024,'export count bounds')
    dr,kr=value['descriptors'],value['key_fields'];need(dr['dtype']=='|u1' and dr['shape']==[n,128] and kr['dtype']=='<i8' and kr['shape']==[n,7],'binary types/shapes')
    need(path(dr['file'])==OUT/'worker'/(name+'-descriptors.u8') and path(kr['file'])==OUT/'worker'/(name+'-keys.i64'),'actual export names')
    db,kb=raw(dr['file'],'export'),raw(kr['file'],'export');need(len(db)==n*128 and len(kb)==n*56,'exact unpadded payloads')
    keys=list(struct.iter_unpack('<7q',kb));descs=[db[i*128:(i+1)*128] for i in range(n)];full=[k+(d,) for k,d in zip(keys,descs,strict=True)]
    need(full==sorted(full),'original full key order including duplicates')
    coarse=[[k[2],k[1]] for k in keys];native=[[8*x+896 for x in c] for c in coarse]
    need(expected['coarse_coordinates_q8']==coarse and expected['native_coordinates_q8']==native,'independent key-to-coordinate lift')
    need(sha(pack(db,'h'))==expected['descriptors_sha256'] and sha(canonical([list(k)+[d.hex()] for k,d in zip(keys,descs,strict=True)]))==expected['keys_sha256'],'reconstructed whole original descriptor and key digests')
    attrs=dict(keypoints=arr([[x/256 for x in p] for p in coarse],[n,2],'<f4'),scales=arr([k[3]/256 for k in keys],[n],'<f4'),oris=arr([(k[4]/256)*math.pi/180 for k in keys],[n],'<f4'),image_size=arr(size,[2],'<f4'))
    need(all(k[3]>0 for k in keys) and value['attributes']==attrs,'independent coarse attribute arrays/hashes')
    h=sha(canonical(expected));need(value['canonical_before_sha256']==value['canonical_after_sha256']==h,'original pre/post serializer witness')
    return dict(record=ref,manifest=value,keys=keys,descriptors=descs,coarse=coarse,native=native,attributes=attrs,descriptor_bytes=db,key_bytes=kb)

def rootsift64(row):
    total=sum(row);first=[math.sqrt(max(x/max(total,1e-6),1e-6)) for x in row];norm=math.sqrt(math.fsum(x*x for x in first));return [x/max(norm,1e-6) for x in first]

def normalized(worker,exports):
    if worker['normalized_private_descriptors'] is None:return None
    manifest=read(worker['normalized_private_descriptors']);inputs=read(worker['model_inputs']);need(manifest['schema']=='m193c-private-rootsift-payloads-v1' and len(manifest['sides'])==2,'two actual input payloads');summary=[];first_actual=None
    for i,z in enumerate(manifest['sides']):
        data=exports[i];side=f'image{i}';n=len(data['keys']);need(z['side']==side and same(z['source_export'],data['record']) and z['dtype']=='<f4' and z['shape']==[1,n,128],'normalized original row association')
        need(path(z['file'])==OUT/'worker'/(side+'-rootsift.f32'),'fixed actual float payload')
        b=raw(z['file'],'export');need(len(b)==4*n*128 and z['tensor_sha256']==sha(b),'actual normalized extent/hash')
        vals=struct.unpack('<'+str(n*128)+'f',b);need(all(math.isfinite(x) for x in vals),'finite actual normalized values')
        need(inputs[side]['descriptors']==dict(dtype='<f4',shape=[1,n,128],sha256=sha(b)),'actual input tensor association')
        for k,w in data['attributes'].items():need(inputs[side][k]==dict(w,shape=[1]+w['shape']),'actual input attribute association')
        diffs=[];max_norm_error=0;max_l1=0
        for j,row in enumerate(data['descriptors']):
            target=rootsift64(row);actual_values=vals[j*128:(j+1)*128];diff=max(abs(a-b) for a,b in zip(actual_values,target,strict=True));diffs.append(diff);max_l1=max(max_l1,sum(row));max_norm_error=max(max_norm_error,abs(math.sqrt(math.fsum(x*x for x in actual_values))-1))
        need(max(diffs)<=BOUND,'all actual float32 RootSIFT components vs independent scalar f64')
        if i==0:first_actual=vals[:128]
        summary.append(dict(side=side,record=z['file'],rows=n,components=n*128,max_absolute_component_error=max(diffs),maximum_row_l1_integer_sum=max_l1,maximum_l2_norm_error=max_norm_error,bound=BOUND,rows_exceeding_bound=sum(x>BOUND for x in diffs)))
    if worker['normalization_destroyer'] is None:return dict(sides=summary,destroyer=None,scope='Actual correct payloads retained; wrong-normalization witness unvisited')
    wrong=read(worker['normalization_destroyer']);row=exports[0]['descriptors'][0];truth=rootsift64(row);values=wrong['wrong_float32_values'];need(wrong['schema']=='m193c-private-rootsift-wrong-normalization-v1' and wrong['side']=='image0' and wrong['row_index']==0 and wrong['rule']=='L2_ONLY_OMITS_L1_CLAMP_SQRT' and wrong['eps']==1e-6 and wrong['componentwise_absolute_bound']==BOUND and same(wrong['actual_correct_payload'],worker['normalized_private_descriptors']),'fixed preregistered first-row fault')
    need(len(set(row))>1 and wrong['row_has_variation'] is True and len(values)==128 and all(f32(x)==x for x in values),'actual variable fixed row/float values')
    nrm=math.sqrt(sum(x*x for x in row));l2=[x/max(nrm,1e-6) for x in row];l2err=max(abs(a-b) for a,b in zip(values,l2,strict=True));bad=max(abs(a-b) for a,b in zip(values,truth,strict=True));versus_actual=max(abs(f32(a-b)) for a,b in zip(values,first_actual,strict=True))
    need(l2err<=BOUND and bad>BOUND and close(versus_actual,wrong['max_abs_difference_from_actual_correct_float32']),'same bound accepts declared L2 values but rejects wrong RootSIFT')
    return dict(sides=summary,destroyer=dict(record=worker['normalization_destroyer'],row_index=0,row_variation=len(set(row)),max_absolute_error_from_f64_rootsift=bad,max_absolute_error_from_f64_l2_only=l2err,max_absolute_difference_from_actual_correct=versus_actual,rejected=True),scope='All actual float32 components versus scalar f64 full RootSIFT; integer u8 L1 sums exact <=32640, 512 float32 unit roundoffs fixed before execution. No subject function import, row search or extra forward.')

def truth(rows,saved=None):
    values=[]
    for r in rows:
        rx,ry=r['reference_q8'];sx,sy=r['source_q8'];dx,dy=rx+sy-3071*256,ry-sx
        need(all(integer(v) for v in (rx,ry,sx,sy)),'integer native truth coordinates')
        values.append(dict(reference_q8=[rx,ry],source_q8=[sx,sy],offset_q8=[dx,dy],squared_error_q16=dx*dx+dy*dy))
    squares=[x['squared_error_q16'] for x in values];n=len(values);count=sum(x<=512**2 for x in squares);total=sum(squares)
    passed=n>=24 and 2*count>=n and total<=n*256**2
    rms=None if not n else math.sqrt(total/n)/256
    if saved is not None:
        need(saved['rows']==values and saved['count']==n and saved['within_two_native_pixels']==count and saved['sum_squared_error_q16']==total and saved['passes'] is passed,'every exact literal truth row and gate')
        need(saved['rms_native_pixels'] is None if rms is None else close(saved['rms_native_pixels'],rms),'truth RMS display')
    return dict(count=n,within_two_native_pixels=count,sum_squared_error_q16=total,rms_native_pixels=rms,passes=passed,conventional_median_native_pixels=None if not n else statistics.median(math.sqrt(x)/256 for x in squares),median_offset_q8=None if not n else [statistics.median(x['offset_q8'][i] for x in values) for i in (0,1)])

def corners(t,saved=None):
    need(type(t) is dict and set(t)=={'a','b','tx','ty'} and all(integer(v) for v in t.values()),'integer Q32 map')
    rows=[]
    for x,y in ((0,0),(2303,0),(0,3071),(2303,3071)):
        dx=t['a']*x-t['b']*y+t['tx']-(3071-y)*Q;dy=t['b']*x+t['a']*y+t['ty']-x*Q;sq=dx*dx+dy*dy;den=Q*Q;g=math.gcd(sq,den)
        rows.append(dict(source=[x,y],expected=[3071-y,x],squared_error_numerator=sq//g,squared_error_denominator=den//g,error_native_px=math.sqrt(sq)/Q))
    if saved is not None:
        need(len(saved)==4,'all four native rectangle corners')
        for a,b in zip(saved,rows,strict=True):need(set(a)==set(b) and all(a[k]==v for k,v in b.items() if k!='error_native_px') and close(a['error_native_px'],b['error_native_px']),'independent exact corners')
    return dict(passes=all(x['squared_error_numerator']<=x['squared_error_denominator'] for x in rows),rows=rows)

def signature(o):
    e=o['error'];return {k:o[k] for k in ('status','transform','metrics','guard')}|dict(error=None if e is None else {k:e[k] for k in ('type','code','message')})

def reg_outcome(o,rows,captured=True):
    need(o['qualification']==QUAL and o['status'] in ('RETURNED','REGISTRATION_REFUSED'),'private unqualified saved registrar result')
    if captured:
        need(len(o['landmarks'])==len(rows),'complete captured registrar rows')
        for a,b in zip(o['landmarks'],rows,strict=True):need(all(a[k]==b[k] for k in ('reference_q8','source_q8','digest','split')),'saved registrar association')
    else:need(o['landmarks']==[] and o['heldout_bbox_q8'] is None,'off/placebo has signature only')
    if o['status']=='REGISTRATION_REFUSED':
        need(o['transform'] is o['metrics'] is o['guard'] is None and o['error']['code']=='UNMEASURED_INPUT_REGISTRATION_INADEQUATE','retained scientific refusal')
        if captured:need(all(r['inlier'] is None for r in o['landmarks']),'refusal does not invent inliers')
        return dict(status=o['status'],error={k:o['error'][k] for k in ('code','message')},corners=None)
    need(o['error'] is None,'returned has no refusal');t=o['transform'];c=corners(t);splits={}
    if captured:
        residuals=[];accepted=[]
        for r in o['landmarks']:
            rx,ry=r['reference_q8'];sx,sy=r['source_q8'];dx=t['a']*sx-t['b']*sy+t['tx']*256-rx*Q;dy=t['b']*sx+t['a']*sy+t['ty']*256-ry*Q;sq=dx*dx+dy*dy
            need(r['inlier'] is (sq<=(512*Q)**2),'exact native inlier predicate');residuals.append(sq);accepted.append(r['inlier'])
        for offset,name in ((0,'calibration'),(1,'holdout')):
            squares=residuals[offset::2];kept=[s for s,a in zip(squares,accepted[offset::2],strict=True) if a];need(len(kept)>=12 and len(kept)*2>=len(squares),'unchanged minimum/half registrar gate')
            splits[name]=dict(count=len(squares),within_two_native_pixels=len(kept),all_row_rms_native_reference_pixels=math.sqrt(sum(squares)/len(squares))/(256*Q),selected_rms_native_reference_pixels=math.sqrt(sum(kept)/len(kept))/(256*Q))
        m=o['metrics'];need(m['calibration_inlier_count']==splits['calibration']['within_two_native_pixels'] and m['heldout_rms_reference_px']==f"{splits['holdout']['selected_rms_native_reference_pixels']:.9f}" and splits['holdout']['selected_rms_native_reference_pixels']<=1,'native selected heldout RMS/count')
        held=[r for i,r in enumerate(o['landmarks']) if i%2 and r['inlier']];bbox={side:[min(r[side][0] for r in held),min(r[side][1] for r in held),max(r[side][0] for r in held),max(r[side][1] for r in held)] for side in ('reference_q8','source_q8')};need(o['heldout_bbox_q8']==bbox,'all saved heldout inlier bounding box')
        det=t['a']**2+t['b']**2;maximum=max(s for i,s in enumerate(residuals) if i%2 and accepted[i]);ceil=math.isqrt(maximum//det)
        if ceil*ceil*det<maximum:ceil+=1
        need(m['heldout_max_source_px_ceil_q8']==ceil and m['coordinate_quantization_guard_q8']==1 and o['guard']==ceil+1 and m['valid_support_continuous_margin_q8']==129+ceil,'inherited guard remains unqualified')
    return dict(status='RETURNED',transform=t,corners=c,all_row_split_consistency=splits)

def sites(rows):
    result={}
    for side in ('reference_q8','source_q8','joint'):
        def point(r):return tuple(r['reference_q8']+r['source_q8']) if side=='joint' else tuple(r[side])
        groups={}
        for i,r in enumerate(rows):groups.setdefault(point(r),[]).append(i)
        def d(i,j):
            sides=('reference_q8','source_q8') if side=='joint' else (side,)
            return max(sum((a-b)**2 for a,b in zip(rows[i][s],rows[j][s],strict=True)) for s in sides)
        adjacency=[set() for _ in rows];cross=0
        for i,j in itertools.combinations(range(len(rows)),2):
            if d(i,j)<=256**2:adjacency[i].add(j);adjacency[j].add(i);cross+=rows[i]['split']!=rows[j]['split']
        remaining=set(range(len(rows)));components=[]
        while remaining:
            pending=[min(remaining)];g=[]
            while pending:
                i=pending.pop()
                if i not in remaining:continue
                remaining.remove(i);g.append(i);pending.extend(adjacency[i]&remaining)
            components.append(g)
        diam=[max((d(i,j) for i,j in itertools.combinations(g,2)),default=0) for g in components]
        result[side]=dict(exact_sites=len(groups),exact_mixed_split_groups=sum(len({rows[i]['split'] for i in g})>1 for g in groups.values()),radius_one_groups=len(components),radius_one_mixed_split_groups=sum(len({rows[i]['split'] for i in g})>1 for g in components),direct_cross_split_pairs=cross,chained_components=sum(v>256**2 for v in diam),max_component_diameter_native_pixels=math.sqrt(max(diam,default=0))/256)
    return result

def learned(worker,exports):
    if worker['learned_output'] is None:return None,[]
    rec=read(worker['learned_output']);o=rec['output'];need(rec['schema']=='m193c-private-lightglue-output-v1' and rec['qualification']==QUAL and rec['inference_observer_nonperturbation']=='UNTESTED_ONE_FORWARD','honest learned output scope')
    need(set(o)==set('matches scores matches0 matches1 matching_scores0 matching_scores1 stop prune0 prune1'.split()),'complete output fields')
    pairs,scores=o['matches'],o['scores'];n0,n1=[len(x['keys']) for x in exports[:2]]
    need(len(pairs)==len(scores)<=min(n0,n1) and pairs==sorted(pairs) and len({p[0] for p in pairs})==len({p[1] for p in pairs})==len(pairs) and all(len(p)==2 and integer(p[0]) and integer(p[1]) and 0<=p[0]<n0 and 0<=p[1]<n1 for p in pairs),'ordered valid one-to-one indices')
    need(all(0.1<s<=1 and f32(s)==s for s in scores) and o['stop']==9,'fixed learned threshold and complete layers')
    expected_shapes={'matches':[len(pairs),2],'scores':[len(scores)],'matches0':[1,n0],'matches1':[1,n1],'matching_scores0':[1,n0],'matching_scores1':[1,n1],'prune0':[1,n0],'prune1':[1,n1]}
    need(set(rec['tensor_bytes'])==set(expected_shapes),'complete tensor value witnesses')
    for k,shape in expected_shapes.items():
        dtype='<i8' if k in ('matches','matches0','matches1') else '<f4'
        need(rec['tensor_bytes'][k]==arr(o[k],shape,dtype),'actual saved output values recreate tensor hash '+k)
    fwd,rev=o['matches0'][0],o['matches1'][0];s0,s1=o['matching_scores0'][0],o['matching_scores1'][0]
    need(all(integer(j) and -1<=j<n1 for j in fwd) and all(integer(i) and -1<=i<n0 for i in rev),'bidirectional sentinel/index bounds')
    need([[i,j] for i,j in enumerate(fwd) if j>=0]==pairs and sum(i>=0 for i in rev)==len(pairs) and all(rev[j]==i and s0[i]==s1[j]==s for (i,j),s in zip(pairs,scores,strict=True)),'every compact/bidirectional confidence association')
    need(all(x==9 for k in ('prune0','prune1') for x in flatten(o[k])),'disabled pruning uses float nine counters')
    rows=[]
    for ordinal,((i,j),score) in enumerate(zip(pairs,scores,strict=True)):
        rx,ry=exports[0]['native'][i];sx,sy=exports[1]['native'][j];digest=sha(b'M193-LANDMARK-SPLIT-V1\0'+struct.pack('>iiii',rx,ry,sx,sy)+exports[0]['descriptors'][i]+exports[1]['descriptors'][j])
        rows.append(dict(learned_ordinal=ordinal,reference_feature_index=i,source_feature_index=j,score=score,reference_q8=[rx,ry],source_q8=[sx,sy],digest=digest))
    ordered=sorted(rows,key=lambda r:(r['digest'],r['reference_q8'][1],r['reference_q8'][0],r['source_q8'][1],r['source_q8'][0]))
    capped=[dict(r,split='holdout' if i%2 else 'calibration') for i,r in enumerate(ordered[:256])]
    summary=dict(record=worker['learned_output'],uncapped=truth(rows),count=len(rows),scores_min=min(scores,default=None),scores_max=max(scores,default=None),assembly=None)
    if worker['assembly'] is not None:
        a=read(worker['assembly']);need(a['landmarks']==capped and a['qualification']==QUAL,'complete hash cap and alternating split')
        relation='SAME_ROWS_NO_INDEPENDENT_CORROBORATION' if len(rows)<=256 else 'UNCAPPED_AND_HASH_CAPPED_POPULATIONS';need(a['truth']['population_relation']==relation,'population relation')
        summary.update(uncapped=truth(rows,a['truth']['uncapped']),capped=truth(capped,a['truth']['capped']),population_relation=relation,sites=sites(capped),assembly=worker['assembly'])
    return summary,capped

def serializer(e,data,prefixes):
    h=sha(canonical(data['manifest']['core']));need(e['observer_feature_sha256']==dict.fromkeys(('off','on','placebo'),h) and e['restored_core_sha256']==h and e['restored_attributes']==data['attributes'],'post-extraction mutation/restore witnesses')
    db,kb=data['descriptor_bytes'],data['key_bytes'];different=next((i for i in range(1,len(data['keys'])) if kb[i*56:(i+1)*56]!=kb[:56]),None);need(different is not None,'actual distinct row')
    bad=bytearray(db);bad[0]^=1;swapped=bytearray(kb);swapped[:56],swapped[different*56:(different+1)*56]=swapped[different*56:(different+1)*56],swapped[:56]
    wrong=dict(data['attributes']);wrong['scales']=arr([f32(k[3]/256)*8 for k in data['keys']],[len(data['keys'])],'<f4')
    desired=[('one-descriptor-byte',bytes(bad),kb,data['attributes']),('key-row-association',db,bytes(swapped),data['attributes']),('native-instead-of-coarse-scale',db,kb,wrong)]
    need(len(e['mutants'])==3 and len(prefixes)==3 and e['actual_fault_prefixes']==prefixes,'three saved fault prefixes')
    for i,(x,(name,ds,ks,at)) in enumerate(zip(e['mutants'],desired,strict=True)):
        need(x['id']==name and x['rejected'] is True and type(x['error']) is str and x['descriptor_sha256']==sha(ds) and x['keys_sha256']==sha(ks) and x['attributes']==at,'actual production mutant identity/refusal')
        need(read(prefixes[i])==e['mutants'][:i+1],'prefix saved before assertion')
    need(sha(pack(bad,'h'))!=data['manifest']['core']['descriptors_sha256'] and sha(canonical([list(k)+[d.hex()] for k,d in zip(struct.iter_unpack('<7q',swapped),data['descriptors'],strict=True)]))!=data['manifest']['core']['keys_sha256'] and wrong['scales']!=data['attributes']['scales'],'independently powered descriptor/association/unit faults')
    return dict(changed_distinct_key_row=different,three_mutants_rejected=True,scope='Recorded production refusal plus independent byte/unit mismatch; no decoder or inference observer claim')

def model_load(w):
    if w is None:return None
    if not w.get('model_load_completed'):return dict(completed=False,witness_location='worker_result.model_loading',witness_sha256=sha(canonical(w)),fields=sorted(w),missing_state_keys=w.get('missing_state_keys'),unexpected_state_keys=w.get('unexpected_state_keys'))
    need(w['import_guard_restored'] is True and w['complete_parameter_coverage'] is True and w['config']==CONF and w['features_argument'] is None and w['device']=='cpu' and w['num_threads']==2 and w['num_interop_threads']==1 and w['deterministic_algorithms'] is True and w['float32_matmul_precision']=='highest','held offline configuration and restoration')
    pairs=w['checkpoint_keys'];sources=set();destinations=set()
    for r in pairs:
        source=r['source'];dest=source
        for i in range(9):
            for old,new in ((f'self_attn.{i}',f'transformers.{i}.self_attn'),(f'cross_attn.{i}',f'transformers.{i}.cross_attn')):
                if dest==old or dest.startswith(old+'.'):dest=new+dest[len(old):]
        need(source not in sources and dest not in destinations and dest==r['destination'] and r['dtype']=='torch.float32' and all(integer(d) and d>=0 for d in r['shape']),'bijective complete recorded checkpoint-key translation');sources.add(source);destinations.add(dest)
    expected=set(w['expected_state_keys']);need(len(expected)==len(w['expected_state_keys']) and w['expected_state_keys']==sorted(expected) and w['missing_state_keys']==sorted(expected-destinations) and w['missing_state_keys'] in ([],['confidence_thresholds']) and w['unexpected_state_keys']==[] and destinations<=expected,'reported exhaustive state-key coverage')
    buffer=w['constructor_buffer'];need(buffer['name']=='confidence_thresholds' and buffer['values']==[f32(min(1,max(0,.8+.1*math.exp(-4*i/9)))) for i in range(9)],'independent constructor buffer formula')
    need(buffer['provenance']==('SYNTHESIZED_FIXED_CONSTRUCTOR_BUFFER' if w['missing_state_keys'] else 'CHECKPOINT_BUFFER_CHECKED_AGAINST_FIXED_CONSTRUCTOR'),'constructor-only exception named')
    return dict(completed=True,checkpoint_tensor_keys=len(pairs),expected_state_keys=len(expected),missing_state_keys=w['missing_state_keys'],constructor_buffer=buffer,config=CONF,blocked_imports=w['blocked_imports'],import_guard_restored=True,scope='Recorded strict state/load/finite/device witnesses; opaque checkpoint hash only, no independent tensor deserialization or expected model-shape reconstruction')

def runtime(ref):
    if ref is None:return None
    value=read(ref);files=value['files'];empty=value['empty_runtime_files'];mods=value['python_modules'];native=value['native_modules'];paths={str(path(r)) for r in files+empty}
    need(len(files)+len(empty)==len(paths)<=4096 and len(native)<=2048 and len(native)==len(set(native)),'bounded complete declared runtime paths')
    expected={str(Path(r['path']).resolve()) for r in mods}|{str(Path(p).resolve()) for p in native};need(paths==expected,'actual module/native path union covers files including empty')
    need(not any(x['name'].split('.')[0] in ('flash_attn','lightglue','superpoint') for x in mods),'no excluded module in snapshots')
    RUNTIME.update(paths);total=0
    for r in files:
        need(r['bytes']>0,'nonempty runtime FileRef');file(path(r),r,'runtime');total+=r['bytes'];need(total<=16<<30,'16 GiB total runtime rehash boundary')
    for r in empty:
        p=path(r);base={k:r[k] for k in ('path','bytes','sha256')};file(p,base,'runtime');need(base['bytes']==0 and base['sha256']==sha(b''),'actual empty runtime rehash');s=p.stat(follow_symlinks=False);m=r['metadata'];need(m['bytes']==0 and m['device']==s.st_dev and m['file_id']==s.st_ino,'empty handle identity witness')
    need(Path(value['executable']).resolve()==PYTHON and value['num_threads']==2 and value['num_interop_threads']==1 and value['default_dtype']=='torch.float32' and value['cuda_initialized'] is False and value['deterministic_algorithms'] is True and value['float32_matmul_precision']=='highest','actual CPU runtime witness')
    return dict(record=ref,torch_version=value['torch_version'],numpy_version=value['numpy_version'],python_version=value['python_version'],file_count=len(paths),nonempty_files=len(files),empty_files=len(empty),native_module_count=len(native),python_module_count=len(mods),opaque_bytes_rehashed=total,path_inventory_sha256=sha(canonical(sorted(paths))),metadata_distribution_count=len(value['metadata_distributions']),metadata_distributions_sha256=sha(canonical(value['metadata_distributions'])),scope='Saved loaded-module inventory plus independent opaque current file hashes/identities. No imports, source interpretation, new runtime enumeration or ABI/inference proof; dist metadata cannot substitute for actual module files.')

def scientific(worker,base):
    refs=worker['exports'];need(len(refs)<=11,'bounded export prefix');names=['private-reference','private-source']+[f'real-{i}' for i in range(9)];exports=[]
    for i,r in enumerate(refs):
        private=i<2;side=('reference','source')[i] if private else None;cached=base['private'][side] if private else base['real'][i-2];cache=base['private_ref'] if private else base['real_refs'][i-2];size=([384,288] if i==0 else [288,384]) if private else [879,586]
        data=exported(r,core_expected(cached,private),names[i],size,cache,side);need(data['manifest']['origin']['representation']==cached['representation'],'actual representation equals cached record')
        if not private:need(same(data['manifest']['origin']['tiff'],base['rows'][i-2]['tiff']),'export image association, metadata only')
        exports.append(data)
    obs=worker['precise_factory_observations'];need(set(obs)=={'private','real'} and len(obs['private'])<=2 and len(obs['real'])<=9,'factory prefix dimensions')
    factory_completed={scope:[factory(w,scope,i) for i,w in enumerate(obs[scope])] for scope in ('private','real')}
    counters=worker['counters'];maximum=dict(private_decodes=1,real_decode_attempts=9,real_decodes_completed=9,feature_extractions=11,private_model_forwards=1,real_model_forwards=0,registrar_calls=5)
    need(set(counters)==set(maximum) and all(integer(counters[k]) and 0<=counters[k]<=v for k,v in maximum.items()),'actual bounded scientific counters')
    need(counters['real_decodes_completed']<=counters['real_decode_attempts'] and counters['feature_extractions']<=2+counters['real_decodes_completed'],'decode/extract prefix relation')
    real_exported=max(0,len(exports)-2);need(worker['unvisited_real_exports']==list(range(real_exported,9)),'exact unvisited real-export suffix')
    if worker['export_admission']=='ALL_ELEVEN_CACHED_FEATURES_REPRODUCED_AND_READ_BACK':need(len(exports)==11,'admitted complete export count')
    else:need(worker['export_admission']=='NOT_ADMITTED' and counters['private_model_forwards']==0,'no private inference before complete export admission')
    ctrl=worker['controls'];need([x['id'] for x in ctrl]==CONTROLS[:len(ctrl)] and all(x['passed'] is True for x in ctrl[:-1]) and len(ctrl)<=17,'exact control prefix with at most final failure')
    recs={};notes=[]
    for r in ctrl:
        v=read(r['record']);need(path(r['record'])==OUT/'worker'/('control-'+r['id']+'.json') and v['id']==r['id'] and v['passed'] is r['passed'],'individual actual control association');recs[r['id']]=v
    for r in ctrl:
        name=r['id'];e=recs[name]['evidence'];passed=None;note={}
        if name=='private-cache-reproduction':
            actual_private=read(e['actual']);need(len(e['canonical_comparisons'])==1,'one full private predicate');passed=comparison(e['canonical_comparisons'][0],'entire-private-AREA8-precise-features',actual_private,base['private'])
        elif name.startswith('real-cache-reproduction-'):
            i=int(name.rsplit('-',1)[1]);a=read(e['actual']);need(same(e['cache'],base['real_refs'][i]) and len(e['canonical_comparisons'])==1,'one exact whole real predicate');passed=comparison(e['canonical_comparisons'][0],f'entire-real-AREA8-precise-feature-{i}',a,base['real'][i])
        elif name=='serializer-readback-observer-destroyers-restored':note=serializer(e,exports[0],worker['serializer_fault_prefixes']);passed=True
        elif name=='private-model-input-observer':
            need(len(e['sides'])==2 and same(e['wrong_normalization'],worker['normalization_destroyer']),'input observer actual payload association');inputs=read(worker['model_inputs'])
            for i,m in enumerate(e['sides']):need(set(m)=={'off','on','placebo'} and m['off']==m['on']==m['placebo']==inputs[f'image{i}'],'two actual input construction observer triplets')
            wrong=read(worker['normalization_destroyer']);passed=wrong['row_has_variation'] and wrong['max_abs_difference_from_actual_correct_float32']>BOUND
        if passed is not None:need(r['passed'] is passed,'saved control boolean matches retained full evidence '+name);notes.append(dict(id=name,passed=passed,record=r['record'],details=note))
    norm=normalized(worker,exports)
    learned_summary,rows=learned(worker,exports);known=None
    for r in ctrl:
        name=r['id']
        if name not in CONTROLS[12:]:continue
        e=recs[name]['evidence'];note={}
        if name=='private-learned-known-geometry':
            known=e['outcome'];note=reg_outcome(known,rows);need(same(e['assembly'],worker['assembly']),'positive exact assembly association')
            if known['transform'] is not None:corners(known['transform'],e['corner_errors'])
            else:need(e['corner_errors']==[],'refused positive has no map corners')
            passed=note['status']=='RETURNED' and note['corners']['passes'] and learned_summary['uncapped']['passes'] and learned_summary['capped']['passes']
        elif name=='native-two-pixel-map-destroyer':
            shifted=dict(known['transform']);shifted['tx']+=2*Q;need(e['transform']==shifted and e['qualification']==QUAL,'exact +2 native map fault');note=corners(shifted,e['corner_errors']);passed=not note['passes']
        elif name=='saved-match-registrar-observer':
            need(len(e['canonical_comparisons'])==2,'two registrar observer predicates');eq=[]
            for i,mode in enumerate(('off','placebo')):
                reg_outcome(e[mode],rows,False);eq.append(comparison(e['canonical_comparisons'][i],'registrar-observer-'+mode,signature(known),signature(e[mode])))
            passed=all(eq);note=dict(scope='actual three registrar calls, count/off/placebo; signature only for off/placebo, no inference observer')
        elif name=='within-split-association-destroyer':
            perm=list(range(len(rows)))
            for split in (0,1):
                ids=list(range(split,len(rows),2));ranked=sorted(ids,key=lambda i:hashlib.sha256(b'M193C-LG-ASSOCIATION-FAULT\0'+bytes.fromhex(rows[i]['digest'])).digest())
                for a,b in zip(ids,ranked,strict=True):perm[a]=b
            need(e['permutation']==perm and all(a%2==b%2 for a,b in enumerate(perm)) and sorted(perm)==list(range(len(rows))),'exact within-split marginal-preserving permutation')
            bad=[dict(r,source_q8=rows[perm[i]]['source_q8']) for i,r in enumerate(rows)];changed=any(a['source_q8']!=b['source_q8'] for a,b in zip(rows,bad,strict=True));need(e['actual_pairing_changed'] is changed,'actual fault exercised')
            bt=truth(bad,e['truth']);fit=reg_outcome(e['outcome'],bad);passed=changed and not bt['passes'] and (fit['status']!='RETURNED' or not fit['corners']['passes']);note=dict(truth=bt,outcome=fit,changed_rows=sum(a['source_q8']!=b['source_q8'] for a,b in zip(rows,bad,strict=True)))
        elif name=='private-restored':
            note=reg_outcome(e['outcome'],rows);need(len(e['canonical_comparisons'])==1,'one whole restored outcome predicate');equal=comparison(e['canonical_comparisons'][0],'entire-restored-learned-registrar-outcome',e['outcome'],known);passed=equal and note['status']=='RETURNED' and note['corners']['passes']
        need(r['passed'] is passed,'saved scientific control boolean versus independently chosen truth '+name);notes.append(dict(id=name,passed=passed,record=r['record'],details=note))
    need(len(notes)==len(ctrl),'every visited control independently accounted')
    for i,r in enumerate(worker['representation_attempts']):
        v=read(r)
        if i==0:need(same(v['fixture'],base['private']['fixture']) and all(v[k]==base['private'][k]['representation'] for k in ('reference','source')),'private pre-extraction representation')
        else:
            j=i-1;need(j<9 and same(v['tiff'],base['rows'][j]['tiff']),'real pre-extraction representation identity');receipt=v['representation'];cached=base['real'][j]['representation']
            # Pre-extraction receipts intentionally precede native coordinates/final factory calls.
            need(all(receipt[k]==cached[k] for k in receipt if k!='precise_factory'),'saved pre-extraction fields equal cached representation')
            w=receipt['precise_factory'];need(w['scope']=='real' and w['ordinal']==j and w['requested_true'] is True and w['calls']==[] and w['restored'] is False and w['error'] is None,'actual pre-extraction factory state')
    if worker['status']==COMPLETE:
        need(len(ctrl)==17 and all(r['passed'] for r in ctrl) and counters==maximum and all(all(v) for v in factory_completed.values()) and len(obs['private'])==2 and len(obs['real'])==9 and len(worker['representation_attempts'])==10,'complete fixed populations')
        need(worker['extractor_runtime_before']==worker['extractor_runtime_after']==actual(ROOT/'experiments/M193-cover-overlap/contract-v1.json')['reference_environment'],'same frozen extractor runtime')
    if counters['private_model_forwards']:
        need(len(exports)==11 and all(recs[x]['passed'] is True for x in CONTROLS[:12]),'model forward only after all eleven reproductions/input controls')
    expected_fits=(1 if 'private-learned-known-geometry' in recs else 0)+(2 if 'saved-match-registrar-observer' in recs else 0)+(1 if 'within-split-association-destroyer' in recs else 0)+(1 if 'private-restored' in recs else 0)
    need(counters['registrar_calls']>=expected_fits,'every completed saved registrar observation charged')
    return dict(exports=[dict(record=x['record'],name=x['manifest']['name'],count=len(x['keys']),descriptor_file=x['manifest']['descriptors']['file'],key_file=x['manifest']['key_fields']['file'],original_descriptors_sha256=x['manifest']['core']['descriptors_sha256'],original_keys_sha256=x['manifest']['core']['keys_sha256'],exact_duplicate_full_keys=len(x['keys'])-len(set(k+(d,) for k,d in zip(x['keys'],x['descriptors'],strict=True))),coarse_size=x['manifest']['explicit_coarse_image_size'],attributes=x['attributes']) for x in exports],controls=notes,normalized_private_descriptors=norm,learned=learned_summary,model_loading=model_load(worker['model_loading']),runtime_before=runtime(worker['runtime_before']),runtime_after=runtime(worker['runtime_after']),factory_observations=obs,counters=counters,export_admission=worker['export_admission'],unvisited_real_exports=worker['unvisited_real_exports'],unvisited_controls=CONTROLS[len(ctrl):],active_phase=worker['active_phase'],refused_control=next((r['id'] for r in ctrl if not r['passed']),None))

def inventory():
    rows=[]
    for directory,dirs,names in os.walk(OUT,followlinks=False):
        for name in dirs:need(not (getattr((Path(directory)/name).stat(follow_symlinks=False),'st_file_attributes',0)&0x400),'no reparse output directory')
        for name in names:
            p=Path(directory)/name;kind='export' if p.suffix in ('.u8','.i64','.f32') else 'metadata';rows.append(file(p,kind=kind))
    return sorted(rows,key=lambda r:r['path'])

def replace(argv,plan_sha,request_sha=None):
    return [plan_sha if x=='ACTUAL_PLAN_SHA256' else request_sha if x=='ACTUAL_REQUEST_SHA256' else x for x in argv]

def cpu_complete(job,parent_claim):
    if job is None:return parent_claim is True
    return job['terminal_job_accounting'] is True and job['job_accounting']['active_processes']==0

def commission():
    need(cpu_complete(None,True) and not cpu_complete(None,False) and not cpu_complete(dict(terminal_job_accounting=True,job_accounting=dict(active_processes=1)),True),'parent-only complete and incomplete/active-Job accounting alternatives')
    for bad in (b'{"a":1,"a":2}',b'{"x":1e999}'):
        failed=False
        try:strict(bad)
        except ValueError:failed=True
        need(failed,'metadata parser actual negative')
    literal=dict(a=0,b=Q,tx=3071*Q,ty=0);need(corners(literal)['passes'] and not corners(dict(literal,tx=literal['tx']+2*Q))['passes'],'literal independent corner positive and +2 fault')
    row=dict(reference_q8=[3071*256,0],source_q8=[0,0],split='calibration');rows=[row]*24;need(truth(rows)['passes'] and not truth([dict(row,reference_q8=[3075*256,0])]*24)['passes'],'all-row truth rejects self-consistent four-pixel translation')
    a=rootsift64(bytes(range(128)));n=math.sqrt(sum(x*x for x in range(128)));bad=[x/n for x in range(128)];need(max(abs(x-y) for x,y in zip(a,bad,strict=True))>BOUND and abs(sum(x*x for x in a)-1)<1e-12,'RootSIFT scalar oracle power with different normalization')
    chain=[dict(reference_q8=[x,0],source_q8=[x,0],split='holdout' if i%2 else 'calibration') for i,x in enumerate((0,200,400))];s=sites(chain);need(s['joint']['radius_one_groups']==1 and s['joint']['chained_components']==1,'radius grouping explicitly recognizes chaining beyond one pixel')
    return ['parent_only_and_incomplete_job_accounting','duplicate_and_exponent_overflow','literal_rotation_and_two_pixel_fault','all_rows_four_pixel_translation','different_normalization','radius_one_chaining']

def main():
    global START,CPU
    START=time.perf_counter();CPU=time.process_time()
    parser=argparse.ArgumentParser()
    for key in ('plan','result','outer','console','exit'):parser.add_argument('--'+key+'-sha256',required=True)
    args=parser.parse_args();need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode,'owned cwd and no bytecode')
    paths=dict(plan=HERE/'sift-lightglue-commission-plan-1.json',result=OUT/'result.json',outer=HERE/'work/sift-lightglue-commission-1-outer.json',console=HERE/'work/sift-lightglue-commission-1-console.txt',exit=HERE/'work/sift-lightglue-commission-1-exit.txt')
    external={}
    for k,p in paths.items():
        r=file(p);need(r['sha256']==getattr(args,k+'_sha256'),'root released actual '+k);external[k]=r
    commissioned=commission();plan=read(external['plan']);parent=read(external['result']);outer=read(external['outer']);console=strict(raw(external['console']).splitlines()[-1]);exit_code=int(raw(external['exit']).strip())
    need(set(plan)==set('schema source_bindings area4_baseline acquisition_receipt prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-sift-lightglue-commission-plan-v1' and plan['preparation_allowance']==ALLOWANCE,'closed held plan')
    for name,pin in PINS.items():r=file(HERE/name);need((r['bytes'],r['sha256'])==pin,'held subject/source pin '+name)
    for p,binding in plan['source_bindings'].items():file(ROOT/p,dict(path=p,**binding))
    own=file(__file__);need(plan['source_bindings'].get(Path(__file__).relative_to(ROOT).as_posix())=={k:own[k] for k in ('bytes','sha256')},'auditor held in prospective source closure')
    need(path(plan['python_executable'])==PYTHON,'fixed Python');file(PYTHON,plan['python_executable'])
    command_base=[str(PYTHON),'-B','-X','faulthandler','-X'];script=str(HERE/'sift-lightglue-commission-run.py');planpath=str(paths['plan'])
    expected_parent=command_base+['pycache_prefix='+str(OUT/'parent-cache'),script,'--plan',planpath,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT)]
    expected_worker=command_base+['pycache_prefix='+str(OUT/'worker-cache'),script,'--plan',planpath,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256','ACTUAL_REQUEST_SHA256']
    need(plan['commands']==dict(parent=expected_parent,worker=expected_worker),'literal exact parent/worker paths and options')
    need(not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'fresh no-bytecode cache paths remain absent')
    base=baseline(plan);prior=base['prior'];need(parent['schema']=='m193c-sift-lightglue-commission-run-v1' and parent['implementation_version']==VERSION and parent['qualification']==QUAL and same(parent['plan'],external['plan']) and parent['source_bindings']==plan['source_bindings'] and parent['prior_work']==prior and parent['acquisition_receipt']==plan['acquisition_receipt'],'actual parent/source/carry authority')
    need(parent['command']==outer['command']==replace(plan['commands']['parent'],external['plan']['sha256']) and outer['plan_sha256']==external['plan']['sha256'] and integer(outer['exit_code']) and outer['exit_code']==exit_code and outer['admissible_parent_exit'] is True,'actual exact parent argv/exit')
    need(parent['command'][:4]==[str(PYTHON),'-B','-X','faulthandler'] and '-X' in parent['command'] and any(x.startswith('pycache_prefix=') for x in parent['command']),'held no-image command options')
    need(console['status']==parent['status'] and console['error']==parent['error'] and console['finalization_errors']==parent['finalization_errors'] and Path(console['result']).resolve()==OUT/'result.json','actual last parent publication')
    child=parent['child'];worker=None;science=None;request=None;terminal=None
    if parent['request'] is not None:
        request=read(parent['request']);need(path(parent['request'])==OUT/'request.json' and set(request)==set('schema plan rows private_ref real_refs assets prior_work'.split()) and request['schema']=='m193c-sift-lightglue-commission-request-v1' and same(request['plan'],external['plan']) and request['rows']==base['rows'] and same(request['private_ref'],base['private_ref']) and request['real_refs']==base['real_refs'] and request['assets']==base['assets'],'exact private2/real9/asset request')
        need(all(D(str(request['prior_work'][k]))>=D(str(prior[k])) for k in prior),'actual request prior no refund')
    if parent['worker_result'] is not None:
        worker=read(parent['worker_result']);need(path(parent['worker_result'])==OUT/'worker/result.json' and worker['schema']=='m193c-sift-lightglue-commission-worker-v1' and worker['implementation_version']==VERSION and same(worker['plan'],external['plan']) and same(worker['request'],parent['request']) and worker['source_bindings']==plan['source_bindings'] and worker['prior_work']==prior,'actual saved worker/source association')
        need(worker['command']==child['command']==replace(plan['commands']['worker'],external['plan']['sha256'],parent['request']['sha256']),'exact worker/request argv')
        need(worker['qualification']==QUAL and worker['inference_observer_nonperturbation']==parent['inference_observer_nonperturbation']=='UNTESTED_ONE_FORWARD','no inference observer overclaim')
        science=scientific(worker,base)
        log=file(OUT/'worker.log');terminal=strict(raw(log).splitlines()[-1]);need(terminal['status']==worker['status'] and terminal['error']==worker['error'] and terminal['finalization_errors']==worker['finalization_errors'] and Path(terminal['result']).resolve()==OUT/'worker/result.json','last worker publication retained')
    complete=parent['status']==COMPLETE
    need(parent['status'] in (COMPLETE,'REFUSED') and exit_code==(0 if complete else 1),'subject completion kept distinct from audit pass')
    if complete:
        need(worker is not None and worker['status']==COMPLETE and parent['error'] is worker['error'] is None and parent['finalization_errors']==worker['finalization_errors']==[] and parent['sources_unchanged'] is worker['sources_unchanged'] is True and worker['active_phase']=='complete','complete terminal states')
        for k in ('controls','exports','serializer_fault_prefixes','representation_attempts','unvisited_real_exports','export_admission','active_phase','counters','model_loading','model_inputs','normalized_private_descriptors','normalization_destroyer','learned_output','assembly','inference_timing','extractor_runtime_before','extractor_runtime_after','runtime_before','runtime_after','precise_factory_observations'):need(parent[k]==worker[k],'complete parent copied evidence '+k)
    else:need(parent['error'] is not None or parent['finalization_errors'],'actual refusal retained')
    fixed=dict(private_decodes=1,real_decodes=9,feature_extractions=11,private_model_forwards=1,real_model_forwards=0,registrar_calls=5,post_extraction_serializer_modes=3,private_model_input_constructions=8,wrong_normalization_rows=1)
    need(parent['fixed_maximum_calls']==fixed and (worker is None or worker['fixed_maximum_calls']==fixed),'maximum call contract')
    accounting=cpu_complete(child,console['cpu_accounting_complete']);caps={};job_cpu=0
    if child is None:need(parent['worker_result'] is None and parent['counters']==dict(private_decodes=0,real_decode_attempts=0,real_decodes_completed=0,feature_extractions=0,private_model_forwards=0,real_model_forwards=0,registrar_calls=0),'no retained Job has no copied scientific work')
    if child is not None:
        log=file(OUT/'worker.log');need(child['log_bytes']==log['bytes'] and (child.get('log') is None or same(child['log'],log)),'actual complete child log bytes')
        account=child['job_accounting'];need(all(integer(account[k]) for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and account['total_cpu_100ns']==account['total_user_100ns']+account['total_kernel_100ns'],'owned Job CPU components')
        job_cpu=account['total_cpu_100ns']/1e7;accounting=child['terminal_job_accounting'] is True and account['active_processes']==0
        if complete:need(child['exit_code']==0 and child['error'] is None and child['cleanup_errors']==[] and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['post_exit_drain']['completed'] is True and child['termination']['attempted'] is False,'clean actual Job completion')
        limits=child['limits'];caps.update(child_cpu=job_cpu<=limits['cpu_seconds']<=300,child_wall=child['wall_seconds']<=limits['wall_seconds']<=240,child_log=log['bytes']<=limits['log_bytes']<=MIB,child_memory=child['job_memory']['peak_job_memory_used_bytes']<=limits['committed_bytes']==8<<30)
        need(child['configured_job_limits']['committed_bytes']==limits['committed_bytes'],'configured owned memory cap')
    need(console['cpu_accounting_complete'] is parent['work']['cpu_accounting_complete'] is accounting,'parent actual complete-CPU flag')
    if worker is not None:need(terminal['cpu_accounting_complete'] is worker['work']['cpu_accounting_complete'] is True,'worker subobservation terminal accounting')
    inv=inventory();total=sum(r['bytes'] for r in inv);binary=sum(r['bytes'] for r in inv if path(r).suffix in ('.u8','.i64','.f32'));final=console['work_through_final_checks'];need(parent['work']['snapshot_bytes']==0 and (worker is None or worker['work']['snapshot_bytes']==0),'no snapshots')
    need(final['file_bytes']-prior['file_bytes']==total and total-binary<=final['metadata_bytes']-prior['metadata_bytes']<=total,'actual byte inventory once; conservative parent binary-as-metadata allowed')
    need(parent['work']['new_extent_bytes']+external['result']['bytes']==total,'final result added to exact prior extent')
    need(D(str(final['cpu_seconds']))-D(str(prior['cpu_seconds']))>=D(str(job_cpu)) and all(D(str(final[k]))>=D(str(prior[k])) for k in prior),'whole terminal CPU/bytes no refund')
    caps.update({k:D(str(final[k]))-D(str(prior[k]))<=v for k,v in dict(cpu_seconds=300,wall_seconds=480,file_bytes=8*MIB,metadata_bytes=8*MIB).items()})
    caps['global_subject']=final['cpu_seconds']<=1200 and final['wall_seconds']<=1800 and final['file_bytes']<=4<<30 and final['metadata_bytes']<=128*MIB
    for p,r in USED.items():need(identity(Path(p).stat(follow_symlinks=False))==IDENTITIES[p],'all retained source/runtime identities final recheck')
    audit_cpu=time.process_time()-CPU;audit_wall=time.perf_counter()-START
    # Audit cost is explicit; ordinary prep reservation is never used as a refund.
    carry=dict(final);carry['cpu_seconds']=float(D(str(final['cpu_seconds']))+D(str(audit_cpu))+D('.25'))
    outer_wall=D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']));carry['wall_seconds']=float(max(D(str(final['wall_seconds'])),outer_wall)+D(str(audit_wall))+D('.5'))
    caps['global_including_audit']=carry['cpu_seconds']<=1200 and carry['wall_seconds']<=1800 and carry['file_bytes']<=4<<30 and carry['metadata_bytes']<=128*MIB
    need(all(caps.values()),'all actual local/global/audit accounting caps')
    admitted=complete and accounting
    result=dict(schema='m193c-saved-sift-lightglue-commission-audit-v1',status='PASS_SAVED_SIFT_LIGHTGLUE_COMMISSION_OUTCOME_AUDIT',subject_complete=complete,admission_allowed=admitted,subject_status=parent['status'],worker_status=None if worker is None else worker['status'],refused_control=None if science is None else science['refused_control'],subject_errors=dict(parent=parent['error'],worker=None if worker is None else worker['error']),finalization_errors=dict(parent=parent['finalization_errors'],worker=None if worker is None else worker['finalization_errors']),external=external,worker_result=parent['worker_result'],audit_source=own,source_bindings_count=len(plan['source_bindings']),area4_baseline=plan['area4_baseline'],area8_feature_baseline=base['area8_refs'],acquisition_receipt=plan['acquisition_receipt'],scientific= science,subject_final_work=final,actual_final_work=carry,next_wall_seconds=str(D(str(carry['wall_seconds']))),cpu_accounting_complete=accounting,job=child,caps=caps,inventory=inv,inventory_total_bytes=total,inventory_binary_bytes=binary,unique_hashed_files=len(USED),runtime_unique_hashed_files=len(RUNTIME),commissioning=commissioned,audit_timing=dict(cpu_seconds=audit_cpu,wall_seconds=audit_wall),audit_publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),scope='Saved metadata/export values and opaque file hashes only. No network, image stat/payload/decode, extraction, model/checkpoint import or deserialization, matching, registrar/refit or second inference. All private learned rows scored versus literal native rotation; complete export identity proves retained-row reproduction, not unretained detector selection or raw OpenCV attributes. Recorded runtime/state tensors remain producer witnesses. Exact/radius-one sites are descriptive and may chain; no physical independence claim. Private compatibility only, coarse lattice guard unqualified. Inference observer remains UNTESTED_ONE_FORWARD. Root must check actual auditor launcher wall against sampled audit wall plus publication allowance before next admission.')
    output=json.dumps(result,sort_keys=True,allow_nan=False,separators=(',',':')).encode();need(len(output)<=96*1024 and 96*1024+Path(__file__).stat().st_size+16*1024<=196*1024,'96 KiB JSON plus source/report/outer within196 KiB');print(output.decode())

if __name__=='__main__':main()
