"""Prospective independent saved-completion audit. Source only until root release.
Re-choices: literal native rotation, independent integer row reconstruction,
final-map versus refinement membership, actual publication files, physical versus
reserved extents. No subject imports, fitting, images, model or checkpoint reads.
"""
import argparse
import ast
from decimal import Decimal as D, ROUND_CEILING
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import stat
import statistics
import struct
import sys
import time
import traceback
import types
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
OUT=HERE/'sift-lightglue-saved-completion-1'
OLD=HERE/'sift-lightglue-commission-1'
SELF=Path(__file__).resolve()
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
HELPER=HERE/'work/independent-sift-lightglue-commission-audit.py'
HELPER_PIN=(62292,'ccb78254596b6402139bb4ff4541a5bb6f0597175268a426bef66ba5e4f7c03c')
PURE=('need','integer','sha','canonical','strict','path','same','close','f32','pack','flatten','arr','core_expected','exported','truth','corners','sites','learned')
Q=1<<32;KIB=1024;MIB=1<<20
COMPLETE='COMPLETE_SAVED_PRIVATE_LIGHTGLUE_CHECKS_ONLY'
VERSION='m193c-sift-lightglue-saved-completion-v1'
QUAL=dict(coordinate_gauge='native pixel centres; q_native=8*q_coarse+896',coordinate_lattice_step_q8=8,inherited_quantization_guard_q8=1,guard_status='UNQUALIFIED_FOR_COARSE_LATTICE',scope='Private compatibility/known geometry only; no real model pairs, support, overlap, placement or quality admission')
IDS=['private-learned-known-geometry','native-two-pixel-map-destroyer','saved-match-registrar-observer','within-split-association-destroyer','private-restored']
PUB_IDS=['normal','capacity','oversized','late-before-stdout','restored-placebo','stdout-after-escape','emergency-fallback']
NAMES=['result.json','first-publication.json','publication-stage.json','emergency-refusal.json']
ALLOW=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
CAPS=dict(cpu_seconds=60,wall_seconds=120,file_bytes=8*MIB,metadata_bytes=8*MIB)
FAMILY=dict(terminal=512*KIB,log=MIB,publication=256*KIB,data=256*KIB,science=256*KIB,runtime=128*KIB,metadata=512*KIB)
FAMILY_RESERVES=dict(source=64*KIB,final=96*KIB,progress=48*KIB,stderr=16*KIB,outer=8*KIB,review=8*KIB)
PROGRESS=HERE/'work/independent-sift-lightglue-saved-completion-audit-progress.json'
USED={};IDENTITIES={};RUNTIME={};PHASES=[];START=CPU=None;PROGRESS_OWNED=False

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def compact(x):return json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
def strict(raw):
    def pairs(items):
        result={}
        for k,v in items:need(k not in result,'duplicate JSON field');result[k]=v
        return result
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:need(False,'nonfinite JSON'))
    def visit(x):
        if type(x) is float:need(math.isfinite(x),'overflow JSON float')
        elif type(x) is dict:
            for v in x.values():visit(v)
        elif type(x) is list:
            for v in x:visit(v)
    visit(value);return value
def integer(v):return type(v) is int
def ident(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,getattr(s,'st_file_attributes',0),s.st_nlink)
def path(ref):return Path(os.path.abspath(ROOT/ref['path']))
def ref_shape(r):
    need(type(r) is dict and set(r)=={'path','bytes','sha256'} and type(r['path']) is str and integer(r['bytes']) and r['bytes']>=0 and type(r['sha256']) is str and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']),'closed typed FileRef')
def same(a,b):
    ref_shape(a);ref_shape(b)
    return path(a).resolve()==path(b).resolve() and all(a[k]==b[k] for k in ('bytes','sha256'))
def policy(p,s,kind):
    need(stat.S_ISREG(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400 and s.st_nlink>=1,'regular nonreparse stable file')
    if kind=='runtime':need(p in RUNTIME,'exact admitted current runtime path')
    if kind=='runtime' and not p.is_relative_to(ROOT) and p!=PYTHON:pass
    else:need(s.st_nlink==1,'owned source/export/output remains single-link')
def file(p,expected=None,kind='metadata'):
    p=Path(os.path.abspath(p));suffix=p.suffix.lower()
    need(suffix not in {'.arw','.dng','.raw','.tif','.tiff','.png','.jpg','.jpeg','.exr','.bmp','.pth'},'no image/checkpoint stat or content')
    if kind=='metadata':need((p.is_relative_to(ROOT) and suffix in {'.py','.json','.md','.txt','.log','.rs','.toml','.lock','.tsv'}) or p==PYTHON,'bounded metadata/source boundary');cap=32*MIB
    elif kind=='export':need(p.parent==OLD/'worker' and suffix in {'.u8','.i64'},'only original integer exports');cap=128*KIB
    elif kind=='rows':need(p.parent==OUT/'worker' and suffix=='.bin','only actual saved completion row payload');cap=256*KIB
    else:need(kind=='runtime' and p in RUNTIME,'manifest-bound current runtime');cap=64*MIB
    before=p.stat(follow_symlinks=False);policy(p,before,kind);need(p.resolve()==p and 0<=before.st_size<=cap,'literal path and bounded extent')
    identity=ident(before)
    if str(p) in USED:
        need(identity==IDENTITIES[str(p)],'retained file identity unchanged');result=USED[str(p)]
    else:
        digest=hashlib.sha256();count=0
        with p.open('rb') as stream:
            need(ident(os.fstat(stream.fileno()))==identity,'actual opened same file')
            for block in iter(lambda:stream.read(MIB),b''):
                count+=len(block);need(count<=cap,'bounded actual extent');digest.update(block)
        need(ident(p.stat(follow_symlinks=False))==identity and count==before.st_size,'same complete file after read')
        result=dict(path=str(p),bytes=count,sha256=digest.hexdigest());USED[str(p)]=result;IDENTITIES[str(p)]=identity
    if expected is not None:need(same(result,expected),'resolved identity/hash/extent association')
    return result
def raw(r,kind='metadata'):
    ref_shape(r);file(path(r),r,kind)
    with path(r).open('rb') as stream:data=stream.read(r['bytes']+1)
    need(len(data)==r['bytes'] and sha(data)==r['sha256'] and ident(path(r).stat(follow_symlinks=False))==IDENTITIES[str(path(r))],'same bounded parsed bytes')
    return data
def read(r):return strict(raw(r))
def actual(p,kind='metadata'):return read(file(p,kind=kind))
def remember(phase,summary=None,error=None):
    if error is None:PHASES.append(dict(phase=phase,status='VERIFIED_PHASE_ONLY',summary=summary))
    value=dict(schema='m193c-saved-completion-audit-progress-v1',status='AUDIT_INCOMPLETE',admission_allowed=False,active_phase=phase,visited=PHASES,error=error,scope='Explicit visited checks only; no result or eligibility inferred from a partial audit.')
    data=compact(value);need(PROGRESS_OWNED and len(data)<=FAMILY_RESERVES['progress']//2,'bounded24KiB progress plus24KiB staging')
    temporary=PROGRESS.with_suffix('.tmp');need(not temporary.exists(),'fresh atomic progress staging')
    with temporary.open('xb') as stream:
        need(stream.write(data)==len(data),'complete progress write');stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,PROGRESS)
def helper():
    r=file(HELPER);need((r['bytes'],r['sha256'])==HELPER_PIN,'immutable independent helper')
    tree=ast.parse(raw(r),str(HELPER));nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in PURE]
    need(len(nodes)==len(PURE) and {n.name for n in nodes}==set(PURE),'closed independent pure AST function allowlist')
    h=types.ModuleType('saved_completion_independent_math')
    h.__dict__.update(dict(ROOT=ROOT,OUT=OLD,Q=Q,QUAL=QUAL,Path=Path,read=read,raw=raw,need=need,json=json,math=math,hashlib=hashlib,struct=struct,itertools=itertools,statistics=statistics))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),h.__dict__)
    return h,r

def replace(argv,plan_sha,request_sha=None):return [plan_sha if x=='ACTUAL_PLAN_SHA256' else request_sha if x=='ACTUAL_REQUEST_SHA256' else x for x in argv]
def typed_work(value):
    need(type(value) is dict and set(value)==set(ALLOW),'closed four work fields')
    need(all(type(value[k]) in (int,float) and math.isfinite(value[k]) and value[k]>=0 for k in ('cpu_seconds','wall_seconds')) and all(integer(value[k]) and value[k]>=0 for k in ('file_bytes','metadata_bytes')),'finite nonnegative typed work')
def residue(row,t):
    rx,ry=row['reference_q8'];sx,sy=row['source_q8']
    return (t['a']*sx-t['b']*sy+t['tx']*256-rx*Q)**2+(t['b']*sx+t['a']*sy+t['ty']*256-ry*Q)**2

def commissioning(h):
    for bad in (b'{"x":1,"x":2}',b'{"x":1e999}'):
        failed=False
        try:strict(bad)
        except ValueError:failed=True
        need(failed,'parser rejects actual malformed alternative')
    r=dict(path=str(SELF),bytes=1,sha256='a'*64);relative=dict(r,path=SELF.relative_to(ROOT).as_posix())
    need(same(r,relative) and not same(r,dict(r,bytes=2)) and not same(r,dict(r,sha256='b'*64)) and not same(r,dict(r,path=str(HERE/'other.py'))),'same identity spelling and three actual faults')
    try:same(r,dict(r,bytes=True))
    except ValueError:pass
    else:raise ValueError('boolean extent fault must reject')
    s=types.SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0,st_nlink=2)
    placeholder=Path(r'C:\Windows\System32\m193c-policy-only.dll');RUNTIME[placeholder]=r;RUNTIME[SELF]=r;RUNTIME[PYTHON]=r
    policy(placeholder,s,'runtime')
    for p,k,changed in ((SELF,'metadata',s),(SELF,'runtime',s),(PYTHON,'runtime',s),(placeholder,'runtime',types.SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0x400,st_nlink=2)),(placeholder,'runtime',types.SimpleNamespace(st_mode=stat.S_IFDIR,st_file_attributes=0,st_nlink=2)),(placeholder.with_name('unlisted.dll'),'runtime',s)):
        try:policy(p,changed,k)
        except ValueError:pass
        else:raise ValueError('file policy destroyer must reject')
    del RUNTIME[placeholder];del RUNTIME[SELF];del RUNTIME[PYTHON]
    literal=dict(a=0,b=Q,tx=3071*Q,ty=0)
    need(h.corners(literal)['passes'] and not h.corners(dict(literal,tx=literal['tx']+2*Q))['passes'],'literal independent corner positive and two-pixel destroyer')
    rows=[dict(reference_q8=[3071*256,0],source_q8=[0,0]) for _ in range(24)]
    need(h.truth(rows)['passes'] and not h.truth([dict(x,reference_q8=[3075*256,0]) for x in rows])['passes'],'same all-row truth rejects coherent four-pixel wrong map')
    # No fitting: the two named map predicates deliberately classify one row differently.
    row=dict(reference_q8=[0,0],source_q8=[0,0]);identity=dict(a=Q,b=0,tx=0,ty=0);shift=dict(identity,tx=3*Q)
    need(residue(row,identity)<=(512*Q)**2<residue(row,shift),'seed/final membership can differ; no claim these are outputs of a fit')
    return ['duplicate_and_nonfinite_json','resolved_reference_identity_and_extent_hash_path_type_faults','manifest_external_multilink_and_owned_reparse_nonregular_unlisted_rejections','literal_rotation_two_pixel_fault','all_row_four_pixel_fault','distinct_fixed_map_memberships_no_fit']

def prefix_authority(plan):
    refs=plan['commission_prefix'];need(set(refs)==set('plan worker_result outer console exit audit'.split()),'closed prefix bundle')
    previous,old,outer,audit=(read(refs[k]) for k in ('plan','worker_result','outer','audit'))
    need(audit['schema']=='m193c-saved-sift-lightglue-commission-prefix-audit-v3' and audit['status']=='PASS_SAVED_SIFT_LIGHTGLUE_COMMISSION_PREFIX_AUDIT' and audit['saved_prefix_verified'] is True,'successful limited prefix audit')
    need(all(audit[k] is False for k in ('subject_complete','admission_allowed','cpu_accounting_complete')) and audit['parent_result_missing'] is True and audit['cpu_reservation_seconds']==300 and audit['missing_parent_publication_cpu_allowance_seconds']==2,'historical limitations and conservative CPU policy retained')
    need(set(audit['external'])==set(refs)-{'audit'} and all(same(audit['external'][k],refs[k]) for k in audit['external']) and same(audit['worker_result'],refs['worker_result']),'exact old audit association')
    need(path(refs['worker_result'])==OLD/'worker/result.json' and Path(audit['parent_result_expected_path']).resolve()==OLD/'result.json' and not (OLD/'result.json').exists(),'actual missing historical parent')
    need(old['status']=='REFUSED' and old['assembly'] is None and old['active_phase']=='private-known-geometry' and old['counters']['registrar_calls']==0 and old['counters']['feature_extractions']==11 and old['counters']['private_model_forwards']==1 and len(old['exports'])==11 and len(old['controls'])==12 and all(x['passed'] is True for x in old['controls']),'exact scientific prefix, never whole commission')
    need(same(old['plan'],refs['plan']) and old['sources_unchanged'] is True and previous['source_bindings']==old['source_bindings'] and all(plan['source_bindings'].get(k)==v for k,v in previous['source_bindings'].items()),'every historical source preserved')
    need(outer['exit_code']==1 and raw(refs['exit']).strip()==b'1' and outer['plan_sha256']==refs['plan']['sha256'] and outer['command']==replace(previous['commands']['parent'],refs['plan']['sha256']),'old failed outer not relabelled')
    console=strict(raw(refs['console']).splitlines()[-1]);need(len(console['finalization_errors'])==2 and all('trace metadata preallocation' in x for x in console['finalization_errors']),'both actual parent publication failures')
    prior=read(plan['prior_work']);typed_work(prior);base=audit['actual_final_work'];typed_work(base)
    need(D(audit['next_wall_seconds'])==D(str(base['wall_seconds'])),'literal audit wall-string equality')
    expected={k:D(str(base[k])).quantize(D('.000001'),rounding=ROUND_CEILING)+ALLOW[k] if k.endswith('seconds') else base[k]+ALLOW[k] for k in ALLOW}
    need(all(D(str(prior[k]))==D(str(expected[k])) for k in ALLOW),'upward CPU and wall carry plus full preparation')
    need(old['inference_observer_nonperturbation']=='UNTESTED_ONE_FORWARD','one earlier forward only')
    return old,audit,prior

def exported_and_learned(h,old):
    exports=[]
    for i,r in enumerate(old['exports']):
        value=read(r);cache=read(value['origin']['cache']);side=('reference','source')[i] if i<2 else None
        expected=h.core_expected(cache[side] if side else cache,i<2)
        name='private-'+side if side else 'real-'+str(i-2)
        size=([384,288],[288,384])[i] if i<2 else [879,586]
        exports.append(h.exported(r,expected,name,size,value['origin']['cache'],side))
    summary,capped=h.learned(old,exports)
    output=read(old['learned_output'])['output']
    for k in ('scores','matching_scores0','matching_scores1'):
        need(all(type(x) is float and 0<=x<=1 for x in h.flatten(output[k])),'complete bounded saved confidence values')
    uncapped=[dict(reference_q8=exports[0]['native'][i],source_q8=exports[1]['native'][j]) for i,j in output['matches']]
    return exports,output,uncapped,capped

def unpack_rows(h,meta,expected,t=None,captured=True,supplied=False):
    need(meta['row_bytes']==56 and 'not refinement subset' in meta['radius_membership'],'explicit row semantics')
    if not captured or not expected:
        need(meta['count']==0 and meta['file'] is None and meta['empty_sha256']==sha(b'') and meta['full_rows_canonical_sha256']==sha(canonical([])),'zero capture uses null and empty identity');return []
    need(meta['count']==len(expected) and meta['empty_sha256'] is None,'entire captured population')
    data=raw(meta['file'],'rows');need(len(data)==len(expected)*56,'exact row byte product')
    rows=[]
    for i,(got,want) in enumerate(zip(struct.iter_unpack('<HHHBB4i32s',data),expected,strict=True)):
        ri,si,ordinal,split,state,rx,ry,sx,sy,digest=got
        need([ri,si,ordinal]==[want[k] for k in ('reference_feature_index','source_feature_index','learned_ordinal')] and split==i%2 and [rx,ry]==want['reference_q8'] and [sx,sy]==want['source_q8'] and digest.hex()==want['digest'],'every row index/coordinate/digest/split association')
        membership=None if t is None else residue(want,t)<=(512*Q)**2
        need(state==(0 if membership is None else 2 if membership else 1),'actual returned-map radius predicate')
        rows.append(dict(reference_q8=[rx,ry],source_q8=[sx,sy],digest=digest.hex(),split=want['split'],inlier=membership))
    original=expected if supplied else rows
    need(meta['full_rows_canonical_sha256']==sha(canonical(original)),'full original row canonical identity')
    return rows

def truth_record(h,record,rows):
    need(record['row_layout']=='<6iQ:reference/source/offset Q8;squared_error Q16','literal truth binary layout')
    want=h.truth(rows)
    if rows:payload=raw(record['rows'],'rows')
    else:
        need(record['rows']==dict(count=0,file=None,bytes=0,sha256=sha(b'')),'empty truth explicit null payload');payload=b''
    need(len(payload)==len(rows)*32,'truth row byte product')
    values=[]
    for row,got in zip(rows,struct.iter_unpack('<6iQ',payload),strict=True):
        rx,ry=row['reference_q8'];sx,sy=row['source_q8'];dx,dy=rx+sy-3071*256,ry-sx
        need(got==(rx,ry,sx,sy,dx,dy,dx*dx+dy*dy),'every independent signed literal truth row')
        values.append(dict(reference_q8=[rx,ry],source_q8=[sx,sy],offset_q8=[dx,dy],squared_error_q16=dx*dx+dy*dy))
    need(record['original_rows_canonical_sha256']==sha(canonical(values)),'whole signed truth canonical identity')
    for key in ('count','within_two_native_pixels','sum_squared_error_q16','passes'):need(record[key]==want[key] and type(record[key]) is type(want[key]),'exact literal truth statistic '+key)
    need(record['rms_native_pixels'] is None if not rows else h.close(record['rms_native_pixels'],want['rms_native_pixels']),'derived truth RMS')
    return want

def fit_record(h,ref,expected,mode):
    value=read(ref);need(value['schema']=='m193c-saved-learned-fit-v1' and value['mode']==mode and value['qualification']==QUAL,'fit metadata version/mode/gauge')
    out=value['intrinsic'];need(set(out)==set('status transform metrics guard error'.split()) and out['status'] in ('RETURNED','REGISTRATION_REFUSED'),'complete intrinsic signature')
    t=out['transform'];returned=out['status']=='RETURNED'
    if returned:need(type(t) is dict and set(t)=={'a','b','tx','ty'} and all(integer(x) for x in t.values()) and t['a']**2+t['b']**2>0 and out['error'] is None,'integer nondegenerate returned map')
    else:need(t is out['metrics'] is out['guard'] is None and out['error']['type']=='ContractError' and out['error']['code']=='UNMEASURED_INPUT_REGISTRATION_INADEQUATE' and type(out['error']['message']) is str,'literal retained registrar refusal')
    captured=mode=='count';rows=unpack_rows(h,value['captured_rows'],expected,t,captured)
    summary=dict(record=ref,status=out['status'],intrinsic=out,corners=None,calibration_final_radius=None,heldout=None,full_outcome_hash_independently_reconstructible=returned,refinement_membership_scope='Calibration fit-subset count is recorded only. Seed min12/half is not a final-map gate; exact refinement membership/trajectory is unretained and is not reconstructed without a fit.')
    bbox=None
    if returned:
        # Final map can be independently scored even when the observer captured no rows.
        squares=[residue(row,t) for row in expected];kept=[x<=(512*Q)**2 for x in squares]
        cal=squares[0::2];hold=squares[1::2];hs=[x for x,a in zip(hold,kept[1::2],strict=True) if a]
        need(len(hs)>=12 and len(hs)*2>=len(hold) and sum(hs)<=len(hs)*(256*Q)**2,'exact frozen heldout minimum/half/one-native RMS gate')
        rms=math.sqrt(sum(hs)/len(hs))/(256*Q);m=out['metrics']
        need(set(m)==set('mutual_match_count calibration_count calibration_inlier_count holdout_count holdout_inlier_count heldout_rms_reference_px heldout_max_source_px_ceil_q8 coordinate_quantization_guard_q8 valid_support_continuous_margin_q8'.split()),'closed actual returned metrics')
        need(all(integer(m[k]) for k in m if k!='heldout_rms_reference_px'),'integer recorded count/guard metrics')
        need(m['mutual_match_count']==len(expected) and m['calibration_count']==len(cal) and m['holdout_count']==len(hold) and m['holdout_inlier_count']==len(hs) and m['heldout_rms_reference_px']==f'{rms:.9f}','exact count and heldout residual display')
        need(integer(m['calibration_inlier_count']) and 2<=m['calibration_inlier_count']<=len(cal),'recorded refinement input count only, not final membership')
        det=t['a']**2+t['b']**2;maximum=max(hs);ceil=math.isqrt(maximum//det)
        if ceil*ceil*det<maximum:ceil+=1
        need(m['heldout_max_source_px_ceil_q8']==ceil and m['coordinate_quantization_guard_q8']==1 and m['valid_support_continuous_margin_q8']==129+ceil and out['guard']==ceil+1,'exact source-gauge guard arithmetic, still unqualified')
        hr=[row for i,row in enumerate(expected) if i%2 and kept[i]]
        if captured:bbox={side:[min(r[side][0] for r in hr),min(r[side][1] for r in hr),max(r[side][0] for r in hr),max(r[side][1] for r in hr)] for side in ('reference_q8','source_q8')}
        summary.update(corners=h.corners(t),calibration_final_radius=dict(count=len(cal),within_two_native_pixels=sum(kept[0::2]),all_row_rms_native_reference_pixels=math.sqrt(sum(cal)/len(cal))/(256*Q),recorded_refinement_fit_count=m['calibration_inlier_count'],scope='DESCRIPTIVE_FINAL_MAP_MEMBERSHIP_NOT_REFIT_SUBSET'),heldout=dict(count=len(hold),within_two_native_pixels=len(hs),all_row_rms_native_reference_pixels=math.sqrt(sum(hold)/len(hold))/(256*Q),selected_rms_native_reference_pixels=rms))
    need(value['heldout_bbox_q8']==bbox,'actual captured heldout bbox or null off/placebo')
    if returned:
        complete=dict(out,landmarks=rows,heldout_bbox_q8=bbox,qualification=QUAL)
        need(value['full_outcome_canonical_sha256']==sha(canonical(complete)),'entire returned outcome independently reconstructed')
    else:summary['unretained_refusal_traceback']='Only intrinsic type/code/message retained; full outcome hash includes an unretained traceback and is a producer witness.'
    return value,summary

def compare_record(value,name,a,b):
    expected=dict(name=name,left_sha256=sha(canonical(a)),right_sha256=sha(canonical(b)),equal=canonical(a)==canonical(b))
    need(value==expected,'complete canonical comparison '+name);return expected['equal']

def science(h,worker,old,audit):
    exports,prediction,uncapped,capped=exported_and_learned(h,old)
    need(sha(canonical(capped))==audit['recovered_assembly']['expanded_landmarks_canonical_sha256'],'independent saved learned assembly agrees with prior audit')
    remember('saved-exports-and-learned-rows',dict(exports=11,uncapped_count=len(uncapped),capped_count=len(capped),new_images=0,new_models=0,new_fits=0))
    assembly=None
    if worker.get('assembly') is not None:
        a=read(worker['assembly']);need(a['schema']=='m193c-saved-learned-assembly-v1' and a['qualification']==QUAL and same(a['learned_output'],old['learned_output']) and len(a['private_exports'])==2 and all(same(x,y) for x,y in zip(a['private_exports'],old['exports'][:2],strict=True)),'saved assembly associations')
        unpack_rows(h,a['rows'],capped,supplied=True)
        need(a['full_landmarks_canonical_sha256']==sha(canonical(capped)),'entire original landmarks')
        relation='SAME_ROWS_NO_INDEPENDENT_CORROBORATION' if len(uncapped)<=256 else 'UNCAPPED_AND_HASH_CAPPED_POPULATIONS'
        need(a['population_relation']==relation,'explicit uncapped/capped relation')
        assembly=dict(record=worker['assembly'],uncapped=truth_record(h,a['uncapped'],uncapped),capped=truth_record(h,a['capped'],capped),population_relation=relation)
        remember('literal-uncapped-and-capped-truth',assembly)
    permutation=list(range(len(capped)))
    for split in (0,1):
        ids=list(range(split,len(capped),2));ranked=sorted(ids,key=lambda i:hashlib.sha256(b'M193C-LG-ASSOCIATION-FAULT\0'+bytes.fromhex(capped[i]['digest'])).digest())
        for i,j in zip(ids,ranked,strict=True):permutation[i]=j
    fault=[dict(r,source_q8=capped[permutation[i]]['source_q8'],source_feature_index=capped[permutation[i]]['source_feature_index']) for i,r in enumerate(capped)]
    changed=any(x['source_q8']!=y['source_q8'] for x,y in zip(capped,fault,strict=True))
    fit_refs=worker.get('fits',[]);need(len(fit_refs)<=5,'fixed five fit maximum');fits=[];records=[]
    for i,ref in enumerate(fit_refs):
        name=('baseline','off','placebo','fault','restored')[i];need(path(ref)==OUT/'worker'/('science-'+name+'-fit.json'),'fixed fit order')
        v,summary=fit_record(h,ref,fault if i==3 else capped,'off' if i==1 else 'placebo' if i==2 else 'count');records.append(v);fits.append(summary)
        remember('saved-fit-'+name,summary)
    controls=worker.get('controls',[]);need([r['id'] for r in controls]==IDS[:len(controls)] and len(controls)<=5,'ordered actual scientific prefix')
    checked_controls=[]
    for i,row in enumerate(controls):
        if row.get('record') is not None:
            stored=read(row['record']);need(stored=={k:v for k,v in row.items() if k!='record'},'actual individual scientific control evidence')
        else:need(worker['status']=='REFUSED','missing individual control record cannot complete')
        e=row['evidence']
        if i==0:
            need(fits and assembly is not None and same(e['fit'],fit_refs[0]) and same(e['truth'],worker['assembly']),'positive actual science refs')
            if fits[0]['corners'] is not None:h.corners(records[0]['intrinsic']['transform'],e['corners'])
            else:need(e['corners']==[],'refusal has no invented map corners')
            passed=fits[0]['status']=='RETURNED' and fits[0]['corners']['passes'] and assembly['uncapped']['passes'] and assembly['capped']['passes']
        elif i==1:
            shifted=dict(records[0]['intrinsic']['transform']);shifted['tx']+=2*Q
            need(e['transform']==shifted and e['qualification']==QUAL,'exact two-native map fault')
            passed=not h.corners(shifted,e['corners'])['passes']
        elif i==2:
            need(len(fits)>=3 and same(e['off'],fit_refs[1]) and same(e['placebo'],fit_refs[2]) and len(e['comparisons'])==2,'actual observer signatures')
            comparison_results=[compare_record(c,name,records[0]['intrinsic'],records[j]['intrinsic']) for c,name,j in zip(e['comparisons'],('off','placebo'),(1,2),strict=True)]
            passed=all(comparison_results)
        elif i==3:
            need(len(fits)>=4 and e['permutation']==permutation and e['actual_pairing_changed'] is changed and same(e['fit'],fit_refs[3]),'fixed actual within-split permutation')
            badtruth=truth_record(h,e['truth'],fault)
            passed=changed and not badtruth['passes'] and (fits[3]['status']!='RETURNED' or not fits[3]['corners']['passes'])
        else:
            need(len(fits)==5 and same(e['fit'],fit_refs[4]),'actual restored fit')
            # Returned complete records were reconstructed above, including both full outcome hashes.
            got=e['comparison'];need(got['name']=='entire-restored-outcome' and got['left_sha256']==records[0]['full_outcome_canonical_sha256'] and got['right_sha256']==records[4]['full_outcome_canonical_sha256'] and got['equal'] is (got['left_sha256']==got['right_sha256']),'entire restored hash comparison')
            passed=got['equal'] and fits[4]['status']=='RETURNED' and fits[4]['corners']['passes']
        need(type(row['passed']) is bool and row['passed'] is passed,'independent actual scientific gate '+row['id'])
        if not passed:need(i==len(controls)-1,'science stops at failed group')
        checked_controls.append(dict(id=row['id'],passed=passed,record=row.get('record'),evidence_retained_in_worker=True))
    need(worker['counters']['registrar_calls']>=len(fits) and worker['counters']['registrar_calls']<=min(5,len(fits)+1),'retained fits plus at most one failed unretained invocation')
    return dict(assembly=assembly,fits=fits,controls=checked_controls,unvisited_controls=IDS[len(controls):],refused_control=next((x['id'] for x in checked_controls if not x['passed']),None),scope='Actual saved associations and literal native truth; final-map residuals are fitted consistency, not real per-frame placement truth.')

def slot(p,size):
    r=file(p);data=raw(r);need(len(data)==size,'fixed actual padded slot extent');value=strict(data)
    need(data==canonical(value)+b' '*(size-len(canonical(value))),'canonical JSON plus only declared whitespace padding');return value,r

def publication_controls(worker):
    prefixes=worker.get('publication_control_prefixes',[]);need(len(prefixes)<=7,'fixed publication prefix population')
    rows=[];earlier=[];success=dict(schema='m193c-publication-control-result-v1',status='COMPLETE',answer=41)
    for ordinal,ref in enumerate(prefixes,1):
        p=read(ref);need(p['schema']=='m193c-publication-progress-v1' and p['ordinal']==ordinal and p['earlier']==earlier,'actual linked progress history');earlier.append(ref)
        row=p['row'];name=PUB_IDS[ordinal-1];need(row['id']==name and type(row['passed']) is bool,'named attempted publication control')
        directory=OUT/'worker/publication-controls'/name
        inventory={x.name:dict(bytes=file(x)['bytes'],sha256=file(x)['sha256']) for x in directory.iterdir() if x.is_file()} if directory.exists() else {}
        need(row['after']==inventory,'every actual control-file extent/hash')
        if row['passed']:
            default=dict(schema='m193c-publication-control-slot-v1',control=name,status='REFUSED',publication_phase='INITIAL_INCOMPLETE',error=None)
            initial=canonical(default)+b' '*(4096-len(canonical(default)))
            need(row['before']==dict.fromkeys(NAMES,sha(initial)),'independent all-four initial refusal identity')
            value,current=slot(directory/'result.json',4096);first,_=slot(directory/'first-publication.json',4096)
            r=row['result'];need(same(r['canonical'],current),'actual final canonical control reference')
            if r['first_positive'] is not None:
                need(same(r['first_positive'],file(directory/'first-publication.json')),'actual retained first-positive reference')
            if name in ('oversized','late-before-stdout','stdout-after-escape'):
                expected_refusal=dict(default if r['error']['phase']=='ENCODING' else success,status='REFUSED',publication_phase='TERMINAL_REFUSAL',error=r['error'],first_positive=r['first_positive'])
                need(value==expected_refusal,'entire actual detailed canonical refusal')
            if name in ('normal','restored-placebo'):
                need(value==first==success and r['passed'] is True and row['intrinsic_sha256']==sha(canonical(success)),'retained and canonical positive equality')
            else:need(value['status']=='REFUSED' and r['passed'] is False and r['canonical_refusal_verified'] is True,'actual verified control refusal')
            if name=='capacity':
                need(raw(file(directory/'filled.txt'))==b'x'*4096 and not (directory/'one-extra-byte.txt').exists() and row['error']=='ordinary quota capacity' and row['payload_sha256']==sha(b'x'*4096) and value==dict(default,publication_phase='CAPACITY_FAULT') and first==default,'saturated ordinary bytes and real terminal refusal')
            if name=='oversized':need(r['error']['phase']=='ENCODING' and r['error']['message']=='terminal slot capacity' and first==default,'one-byte oversized serialization denied before positive retention')
            if name=='late-before-stdout':need(first==success and r['error']==dict(type='ValueError',message='DECLARED_POST_PUBLICATION_FAULT',phase='LATE_CHECK_BEFORE_STDOUT'),'actual declared pre-stdout late fault')
            if name=='restored-placebo':
                fault=row['preceding_fault'];need(fault['passed'] is False and fault['canonical_refusal_verified'] is True and fault['error']['message']=='DECLARED_RESTORATION_PRECEDING_FAULT' and row['placebo_calls']==['placebo'],'same-instance earlier failure/restoration witness')
                data=raw(file(directory/'unchanged.txt'));need(data==b'ACTUAL_ORDINARY_PAYLOAD' and row['ordinary_before']==row['ordinary_after']==sha(data),'same actual payload remains identical')
            if name=='stdout-after-escape':need(first==success and r['error']['phase']=='STDOUT' and r['error']['message']=='DECLARED_STDOUT_FAILURE_AFTER_ESCAPE' and len(row['escaped_stdout_witness'])==1 and row['escaped_stdout_witness'][0]['status']=='COMPLETE','escaped positive remains explicitly overridden by canonical refusal')
            if name=='emergency-fallback':need(value==default and first==success and r['error']['message']=='x'*8192 and r['revocation_errors'][0]['stage']=='detailed' and r['revocation_errors'][0]['message']=='terminal slot capacity' and not (directory/'emergency-refusal.json').exists(),'actual consumed emergency fallback and retained first positive')
        else:need(ordinal==len(prefixes) and row.get('error') is not None,'failed control is final explicit attempted row')
        rows.append(dict(id=name,passed=row['passed'],record=ref))
    summary=worker.get('publication_control_summary',[])
    need(len(summary) in (len(rows),len(rows)+1) and [dict(id=x['id'],passed=x['passed']) for x in summary[:len(rows)]]==rows_without_refs(rows),'compact publication summary exactly names retained prefix')
    if len(summary)>len(rows):
        last=summary[-1];need(worker['status']=='REFUSED' and last['id']==PUB_IDS[len(rows)],'only next failed publication-progress write can be unretained')
        rows.append(dict(id=last['id'],passed=None,recorded_passed=last['passed'],record=None,scope='UNVERIFIED_UNPUBLISHED_PROGRESS; full control row not retained'))
    if worker.get('publication_controls') is not None:
        final=read(worker['publication_controls']);need(final['schema']=='m193c-durable-publication-controls-v1' and final['controls']==prefixes and final['passed'] is True and len(rows)==7 and all(x['passed'] for x in rows),'complete actual publication commission')
    if worker.get('fits'):need(len(rows)==7 and all(x['passed'] for x in rows),'all durable publication gates before science')
    return rows

def rows_without_refs(rows):return [dict(id=x['id'],passed=x['passed']) for x in rows]

def runtime_record(ref,plan,old):
    value=read(ref);need(value['schema']=='m193c-saved-completion-runtime-presence-v1' and same(value['prior_registry'],old['runtime_before']),'actual indexed runtime authority')
    previous=read(old['runtime_before']);prior=previous['files'];empties=previous['empty_runtime_files'];paths=[];nlinks=[]
    for entry in value['entries']:
        need(type(entry) is dict and len(entry)==1,'one runtime association per entry')
        if 'local_source' in entry:
            name=entry['local_source'];need(name in plan['source_bindings'],'declared actual local source');r=dict(path=name,**plan['source_bindings'][name]);file(path(r),r)
        elif 'prior_runtime_index' in entry:
            i=entry['prior_runtime_index'];need(integer(i) and 0<=i<len(prior),'exact prior runtime index');r=prior[i];RUNTIME[path(r)]=r;file(path(r),r,'runtime')
        else:
            need(set(entry)=={'empty_runtime_index'},'closed empty entry');i=entry['empty_runtime_index'];need(integer(i) and 0<=i<len(empties),'exact prior empty index')
            old_empty=empties[i];r={k:old_empty[k] for k in ('path','bytes','sha256')};RUNTIME[path(r)]=r;file(path(r),r,'runtime');need(r['bytes']==0 and r['sha256']==sha(b''),'actual empty runtime')
        paths.append(path(r));nlinks.append(IDENTITIES[str(path(r))][-1])
    need(len(paths)==len(set(paths))<=1024 and value['python_version']==previous['python_version'],'unique complete current indexed runtime')
    modules=value['python_modules'];native=value['native_module_indices']
    need(len({r[0] for r in modules})==len(modules) and all(type(r) is list and len(r)==2 and type(r[0]) is str and integer(r[1]) and 0<=r[1]<len(paths) for r in modules),'all current Python module indices')
    need(all(integer(i) and 0<=i<len(paths) for i in native) and len(set(native))==len(native)<=2048 and {r[1] for r in modules}|set(native)==set(range(len(paths))),'exact native/Python file union')
    need(not any(r[0].split('.')[0] in {'torch','numpy','cv2','tifffile','PIL','lightglue','flash_attn'} for r in modules),'no declared image/model/numerical package import')
    wanted=[x for x in empties if path(x) in paths]
    need(len(value['empty_current_files'])==len(wanted),'complete current empty witnesses')
    for got in value['empty_current_files']:
        candidates=[x for x in wanted if path(x)==path(got)];need(len(candidates)==1 and got==candidates[0],'same admitted empty witness')
        s=path(got).stat(follow_symlinks=False);m=got['metadata']
        need(m['bytes']==s.st_size==0 and m['mtime_ns']==s.st_mtime_ns and m['device']==s.st_dev and m['file_id']==s.st_ino and m['attributes']==getattr(s,'st_file_attributes',0),'current empty opened identity and complete saved metadata')
    return dict(record=ref,files=len(paths),python_modules=len(modules),native_modules=len(native),external_multiple_link_files=sum(x>1 for x in nlinks),current_file_identity_sha256=sha(canonical([str(p) for p in paths])),scope='Saved current-process module/native registry plus exact current file hashes and opened identities; external manifest files may have positive stable hard links. No new runtime enumeration, model or ABI claim.')

def inventory():
    rows=[]
    for directory,dirs,names in os.walk(OUT,followlinks=False):
        for name in dirs:
            s=(Path(directory)/name).stat(follow_symlinks=False);need(stat.S_ISDIR(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'ordinary owned inventory directory')
        for name in names:
            p=Path(directory)/name;rows.append(file(p,kind='rows' if p.suffix=='.bin' else 'metadata'))
    need(len(rows)<=256,'bounded complete output inventory including hidden names');return sorted(rows,key=lambda r:r['path'])
def family(name):
    parts=Path(name).parts
    if parts[0]=='worker':parts=parts[1:]
    if parts[0]=='publication-controls':return 'publication'
    if parts[-1] in NAMES:return 'terminal'
    if parts[-1]=='worker.log':return 'log'
    if parts[-1].startswith('publication-'):return 'publication'
    if parts[-1].startswith('science-'):return 'data' if Path(parts[-1]).suffix=='.bin' else 'science'
    if parts[-1].startswith('runtime-'):return 'runtime'
    return 'metadata'
def ledger(result,root,inv):
    saved=result.get('charged_path_extents')
    if saved is None:return None
    need(type(saved) is dict and len(saved)<=256,'bounded monotone ledger')
    totals=dict.fromkeys(FAMILY,0);paths={}
    for name,size in saved.items():
        p=Path(os.path.abspath(root/name));need(type(name) is str and not Path(name).is_absolute() and p.is_relative_to(root) and integer(size) and 0<size<=MIB,'owned positive ledger extent')
        paths[p]=size;totals[family(name)]+=size
    need(len(paths)==len(saved) and all(totals[k]<=FAMILY[k] for k in FAMILY),'unique normalized ledger paths and all family caps')
    for name in NAMES:need(paths.get(root/name)==64*KIB,'four fixed nonrefundable own terminal reservations')
    actual={path(r):r for r in inv if path(r).is_relative_to(root)}
    need(all(p in paths and r['bytes']<=paths[p] for p,r in actual.items()),'every actual file is covered by charged maxima')
    missing=[]
    for p,size in paths.items():
        if p not in actual:
            need(p.name in NAMES and (p.name in ('publication-stage.json','emergency-refusal.json') or (root==OUT and (p.is_relative_to(OUT/'worker/publication-controls') or p.parent==OUT/'worker'))),'only consumed staging/fallback or precharged unvisited control slots may be absent')
            missing.append(dict(path=p.relative_to(root).as_posix(),charged_bytes=size))
    total=sum(paths.values());w=result.get('work');need(w is not None and w['new_charged_extent_bytes']==total and w['local_caps']==CAPS and w['prior_cpu_accounting_complete'] is False,'whole ledger work association')
    prior=result['prior_work'];work=w['conservative_global_work'];typed_work(work)
    need(work['file_bytes']==prior['file_bytes']+total and work['metadata_bytes']==prior['metadata_bytes']+total,'all reserved bytes charged conservatively as metadata')
    return dict(total=total,physical_bytes=sum(r['bytes'] for r in actual.values()),families=totals,absent_but_charged=missing,paths=paths)

def lines(ref):
    result=[]
    for line in raw(ref).splitlines():
        try:value=strict(line)
        except (ValueError,UnicodeDecodeError):continue
        if type(value) is dict:result.append(value)
    return result

def terminal_receipt(records,expected,status,complete):
    ads=[x for x in records if type(x.get('result')) is dict and set(x['result'])=={'path','bytes','sha256'}]
    revocations=[x for x in records if type(x.get('publication')) is dict]
    if complete:
        need(ads and ads[-1]['status']==status and same(ads[-1]['result'],expected) and not revocations,'last actual complete advertisement binds sealed canonical output')
        return ads[-1]
    if revocations:
        last=revocations[-1];r=last['publication']
        need(last['status'] in ('REFUSED','REFUSAL_PUBLICATION_UNVERIFIED') and r['passed'] is False,'explicit actual terminal refusal path')
        if r.get('canonical_refusal_verified') is True:need(r['canonical'] is not None and same(r['canonical'],expected) and last['status']=='REFUSED','verified canonical refusal overrides escaped stdout')
    return ads[-1] if ads else None

def own_terminal(directory,result,complete):
    value,current=slot(directory/'result.json',64*KIB);need(value==result,'actual canonical result')
    first,firstref=slot(directory/'first-publication.json',64*KIB)
    if complete:need(first==result and firstref['sha256']==current['sha256'],'retained first-positive equals sealed canonical complete bytes')
    else:need(value['status']=='REFUSED','actual canonical refusal governs')
    return dict(canonical=current,first_positive=firstref,first_status=first['status'],canonical_status=value['status'])

def accounting(parent,worker,outer,advertisement,inv,complete):
    prior=parent['prior_work'];typed_work(prior);pl=ledger(parent,OUT,inv);wl=ledger(worker,OUT/'worker',inv) if worker else None
    if pl and wl:need(all(pl['paths'].get(p,0)>=size for p,size in wl['paths'].items()),'parent contains every child monotone extent')
    child=parent.get('child');job_cpu=0;new_complete=False;job_summary=None
    if child is not None:
        if parent.get('child_observation') is not None:need(read(parent['child_observation'])==child,'retained full child cleanup observation')
        log=file(OUT/'worker.log');need(child['log_bytes']==log['bytes'] and (child.get('log') is None or same(child['log'],log)),'complete actual child log identity')
        a=child.get('job_accounting')
        if a is not None:
            need(all(integer(a[k]) and a[k]>=0 for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and a['total_cpu_100ns']==a['total_user_100ns']+a['total_kernel_100ns'],'actual terminal owned Job CPU components')
            job_cpu=a['total_cpu_100ns']/1e7;new_complete=child.get('terminal_job_accounting') is True and a['active_processes']==0
        limits=child['limits'];need(0<limits['cpu_seconds']<=56 and 0<limits['wall_seconds']<=90 and limits['log_bytes']==MIB and limits['committed_bytes']==8<<30,'tighter child dynamic limits with cleanup/publication reserve')
        if complete:
            need(new_complete and child['exit_code']==0 and child['error'] is None and child['cleanup_errors']==[] and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['post_exit_drain']['completed'] is True and child['termination']['attempted'] is False,'complete owned Job and clean terminal cleanup')
            need(job_cpu<=limits['cpu_seconds'] and child['wall_seconds']<=limits['wall_seconds'] and log['bytes']<=MIB and child['job_memory']['peak_job_memory_used_bytes']<=8<<30 and child['configured_job_limits']['committed_bytes']==8<<30 and integer(child['configured_job_limits']['flags']) and child['configured_job_limits']['flags']&0x2200==0x2200,'actual worker resource limits including observed installed memory and kill-on-close flags')
        job_summary=dict(record=parent.get('child_observation'),cpu_seconds=job_cpu,wall_seconds=child['wall_seconds'],terminal_accounting=new_complete,limits=limits,cleanup_errors=child['cleanup_errors'])
    physical=sum(r['bytes'] for r in inv)
    need(physical<=8*MIB,'actual owned output bytes')
    sampled=advertisement.get('conservative_work_through_publication') if advertisement else None
    if sampled is not None:typed_work(sampled)
    if complete:
        need(pl is not None and wl is not None and sampled is not None and new_complete and parent['new_run_cpu_accounting_complete'] is True and worker['new_run_cpu_accounting_complete'] is True,'complete new accounting witnesses')
        need(sampled['file_bytes']==prior['file_bytes']+pl['total'] and sampled['metadata_bytes']==prior['metadata_bytes']+pl['total'],'latest advertisement uses monotone final ledger')
        need(D(str(sampled['cpu_seconds']))>=D(str(prior['cpu_seconds']))+D(str(job_cpu)),'parent sample contains whole worker Job CPU')
        need(all(D(str(sampled[k]))>=D(str(parent['work']['conservative_global_work'][k])) for k in ALLOW),'no publication-time work refund')
        subject=dict(sampled);subject['cpu_seconds']=float(D(str(subject['cpu_seconds']))+D('2'))
        subject['wall_seconds']=float(max(D(str(subject['wall_seconds'])),D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))))
        scope='Actual parent publication sample plus complete Job CPU; conservative2-CPU parent tail inside released60. Full actual outer wall supersedes earlier sample; no duplicate wall tail.'
        need(all(D(str(subject[k]))-D(str(prior[k]))<=CAPS[k] for k in CAPS),'conservative complete subject inside local60/120/8MiB caps')
    else:
        # A missing terminal sample cannot be replaced with zero work or promoted to complete accounting.
        subject=dict(cpu_seconds=prior['cpu_seconds']+62,wall_seconds=prior['wall_seconds']+outer['elapsed_wall_seconds'],file_bytes=prior['file_bytes']+(pl['total'] if pl else 8*MIB),metadata_bytes=prior['metadata_bytes']+(pl['total'] if pl else 8*MIB))
        if sampled:
            subject['cpu_seconds']=max(subject['cpu_seconds'],sampled['cpu_seconds']+2)
            subject['wall_seconds']=max(subject['wall_seconds'],sampled['wall_seconds'])
        scope='Incomplete new subject: full60-CPU reservation plus2 publication allowance, actual outer wall, full8MiB if charged ledger absent. Conservative charges are not measurements.'
    return dict(subject_final_work=subject,new_run_cpu_accounting_complete=new_complete,job=job_summary,inventory_total_bytes=physical,charged_extent_bytes=None if pl is None else pl['total'],charged_families=None if pl is None else pl['families'],absent_but_charged=[] if pl is None else pl['absent_but_charged'],parent_publication_cpu_allowance_seconds=2,scope=scope)

def main():
    global START,CPU,PROGRESS_OWNED
    START=time.perf_counter();CPU=time.process_time()
    parser=argparse.ArgumentParser()
    for key in ('plan','result','outer','console','exit'):parser.add_argument('--'+key+'-sha256',required=True)
    args=parser.parse_args();need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON,'owned cwd, exact Python and no bytecode')
    need(not PROGRESS.exists() and not PROGRESS.with_suffix('.tmp').exists(),'fresh versioned audit progress only')
    PROGRESS_OWNED=True
    need(SELF.stat().st_size<=FAMILY_RESERVES['source'] and sum(FAMILY_RESERVES.values())<=256*KIB,'entire prospective audit family256KiB inside preparation; pinned reused helper is previously charged')
    remember('initialization',dict(reservations=FAMILY_RESERVES,previously_charged_helper=dict(path=str(HELPER),bytes=HELPER_PIN[0],sha256=HELPER_PIN[1])))
    paths=dict(plan=HERE/'sift-lightglue-saved-completion-plan-1.json',result=OUT/'result.json',outer=HERE/'work/sift-lightglue-saved-completion-1-outer.json',console=HERE/'work/sift-lightglue-saved-completion-1-console.txt',exit=HERE/'work/sift-lightglue-saved-completion-1-exit.txt')
    external={}
    for key,p in paths.items():
        ref=file(p);need(ref['sha256']==getattr(args,key+'_sha256'),'root released actual '+key);external[key]=ref
    plan=read(external['plan']);parent=read(external['result']);outer=read(external['outer']);exit_code=int(raw(external['exit']).strip())
    need(set(plan)==set('schema source_bindings commission_prefix prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-sift-lightglue-saved-completion-plan-v1' and plan['preparation_allowance']==ALLOW,'closed held plan')
    for name,pin in plan['source_bindings'].items():file(ROOT/name,dict(path=name,**pin))
    own=file(SELF);need(plan['source_bindings'].get(SELF.relative_to(ROOT).as_posix())=={k:own[k] for k in ('bytes','sha256')},'independent auditor held before execution')
    need(path(plan['python_executable'])==PYTHON,'exact executable association');file(PYTHON,plan['python_executable'])
    h,helper_ref=helper();checks=commissioning(h);old,audit,prior=prefix_authority(plan)
    base=[str(PYTHON),'-B','-X','faulthandler','-X'];script=str(HERE/'sift-lightglue-saved-completion-run.py');p=str(paths['plan'])
    expected_parent=base+['pycache_prefix='+str(OUT/'parent-cache'),script,'--plan',p,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT)]
    expected_worker=base+['pycache_prefix='+str(OUT/'worker-cache'),script,'--plan',p,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256','ACTUAL_REQUEST_SHA256']
    need(plan['commands']==dict(parent=expected_parent,worker=expected_worker),'exact literal bounded commands')
    need(outer['command']==replace(expected_parent,external['plan']['sha256']) and outer['plan_sha256']==external['plan']['sha256'] and integer(outer['exit_code']) and outer['exit_code']==exit_code and outer['admissible_parent_exit'] is True,'actual launched outer command/exit association')
    need(type(outer['elapsed_wall_seconds']) in (int,float) and math.isfinite(outer['elapsed_wall_seconds']) and outer['elapsed_wall_seconds']>=0,'finite full actual outer wall')
    need(parent['schema']=='m193c-sift-lightglue-saved-completion-run-v1' and parent['implementation_version']==VERSION and same(parent['plan'],external['plan']) and parent['prior_work']==prior,'actual parent exact plan and carry')
    complete=parent['status']==COMPLETE
    need(parent['status'] in (COMPLETE,'REFUSED') and exit_code==(0 if complete else 1),'canonical complete/refusal and outer exit agree')
    if 'command' in parent:need(parent['command']==outer['command'],'actual parent argv')
    for key in ('cpu_accounting_complete','original_commission_complete'):need(parent[key] is False,'historical incompleteness unchanged')
    need(parent['old_run_status']=='REFUSED' and parent['inference_observer_nonperturbation']=='UNTESTED_ONE_FORWARD','no old complete/model observer promotion')
    terminal=own_terminal(OUT,parent,complete);ads=lines(external['console']);advertisement=terminal_receipt(ads,external['result'],parent['status'],complete)
    remember('authority-and-parent-canonical',dict(subject_status=parent['status'],terminal=terminal,prior_work=prior,commissioning=checks))
    worker=None;science_summary=None;pub_summary=[];runtime=[];worker_ref=None
    if (OUT/'worker/result.json').exists():
        worker_ref=file(OUT/'worker/result.json');worker=read(worker_ref)
        if parent.get('worker_result') is not None:need(same(parent['worker_result'],worker_ref),'actual retained worker canonical')
        need(worker['schema']=='m193c-sift-lightglue-saved-completion-worker-v1' and worker['implementation_version']==VERSION and same(worker['plan'],external['plan']) and worker['cpu_accounting_complete'] is False and worker['original_commission_complete'] is False and worker['old_run_status']=='REFUSED' and worker['inference_observer_nonperturbation']=='UNTESTED_ONE_FORWARD','actual scoped worker')
        need(parent.get('request') is not None and same(worker['request'],parent['request']),'exact worker request association')
        request=read(parent['request']);need(path(parent['request'])==OUT/'request.json' and set(request)=={'schema','plan','prior_work'} and request['schema']=='m193c-saved-completion-request-v1' and same(request['plan'],external['plan']),'closed actual request')
        typed_work(request['prior_work']);need(worker['prior_work']==request['prior_work'] and all(D(str(request['prior_work'][k]))>=D(str(prior[k])) for k in prior),'worker uses actual request carry without refund')
        if 'command' in worker:need(worker['command']==replace(expected_worker,external['plan']['sha256'],parent['request']['sha256'])==parent['child']['command'],'exact actual child command')
        worker_complete=worker['status']==COMPLETE;own_terminal(OUT/'worker',worker,worker_complete)
        worker_log=file(OUT/'worker.log');terminal_receipt(lines(worker_log),worker_ref,worker['status'],worker_complete)
        pub_summary=publication_controls(worker);remember('actual-publication-controls',pub_summary)
        for name in ('runtime_before','runtime_after'):
            if worker.get(name) is not None:runtime.append(runtime_record(worker[name],plan,old))
        if worker.get('counters'):
            counters=worker['counters'];need(set(counters)==set('images extractions normalizations model_forwards registrar_calls'.split()) and all(integer(counters[k]) and counters[k]==0 for k in counters if k!='registrar_calls'),'zero new image/extractor/normalizer/model calls')
            science_summary=science(h,worker,old,audit)
        if complete:
            need(worker_complete and parent['error'] is worker['error'] is None and parent['sources_unchanged'] is worker['sources_unchanged'] is True and parent['active_phase']==worker['active_phase']=='complete','complete actual scientific/finalization states')
            need(science_summary is not None and len(science_summary['controls'])==5 and all(r['passed'] for r in science_summary['controls']) and len(science_summary['fits'])==5 and worker['counters']['registrar_calls']==5 and worker['saved_feature_checks']==11,'all five fixed saved controls and eleven checks')
            need(parent['counters']==worker['counters'] and parent['saved_feature_checks']==11 and len(runtime)==2 and read(worker['runtime_before'])==read(worker['runtime_after']),'exact parent counters and stable worker runtime')
    if parent.get('runtime_final') is not None:runtime.append(runtime_record(parent['runtime_final'],plan,old))
    if complete:need(worker is not None and parent.get('runtime_final') is not None and parent.get('child_observation') is not None,'complete parent runtime and Job evidence')
    remember('runtime-and-scientific-prefix',dict(runtime=runtime,controls=[] if science_summary is None else science_summary['controls']))
    inv=inventory();account=accounting(parent,worker,outer,advertisement,inv,complete)
    remember('accounting-and-physical-inventory',account)
    need(not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'actual no-bytecode caches remain absent')
    for p,identity in IDENTITIES.items():need(ident(Path(p).stat(follow_symlinks=False))==identity,'all consumed immutable source/evidence/runtime identities remain stable')
    elapsed_cpu=time.process_time()-CPU;elapsed_wall=time.perf_counter()-START
    carry=dict(account['subject_final_work']);carry['cpu_seconds']=float(D(str(carry['cpu_seconds']))+D(str(elapsed_cpu))+D('.25'));carry['wall_seconds']=float(D(str(carry['wall_seconds']))+D(str(elapsed_wall))+D('.5'))
    need(carry['cpu_seconds']<=1200 and carry['wall_seconds']<=1800 and carry['file_bytes']<=4<<30 and carry['metadata_bytes']<=128*MIB,'conservative carry including audit stays within global caps')
    eligible=complete and account['new_run_cpu_accounting_complete']
    result=dict(schema='m193c-saved-sift-lightglue-saved-completion-audit-v1',status='PASS_SAVED_PRIVATE_LIGHTGLUE_COMPLETION_OUTCOME_AUDIT',subject_complete=complete,combined_private_prerequisite_eligible=eligible,admission_allowed=False,cpu_accounting_complete=False,new_run_cpu_accounting_complete=account['new_run_cpu_accounting_complete'],old_run_status='REFUSED',original_commission_complete=False,inference_observer_nonperturbation='UNTESTED_ONE_FORWARD',external=external,worker_result=worker_ref,audit_source=own,reused_previously_charged_helper=helper_ref,commission_prefix=plan['commission_prefix'],subject_status=parent['status'],worker_status=None if worker is None else worker['status'],refused_control=None if science_summary is None else science_summary['refused_control'],scientific=science_summary,publication_controls=pub_summary,runtime=runtime,accounting=account,inventory=inv,actual_final_work=carry,next_wall_seconds=str(D(str(carry['wall_seconds']))),audit_timing=dict(cpu_seconds=elapsed_cpu,wall_seconds=elapsed_wall),audit_publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),audit_family=dict(limit_bytes=256*KIB,reservations=FAMILY_RESERVES,previously_charged_helper=helper_ref),audit_progress=file(PROGRESS),source_bindings_count=len(plan['source_bindings']),scope='Saved metadata/integer binary rows and opaque current-runtime hashes only. No subject imports, images, normalization, model/checkpoint read, inference, registration or fit. Private literal truth only; final calibration radius membership is descriptive, refinement subset unretained. Overall CPU remains historically incomplete; current parent tail is conservatively charged. Combined private prerequisite is not real correspondence/placement/support/render admission. Inference observer remains untested and lattice guard unqualified. Root must verify actual auditor outer exit, output pin and .25/.5 publication tail before any later release.')
    data=compact(result);need(len(data)+1<=FAMILY_RESERVES['final'],'final96KiB including newline');print(data.decode())

if __name__=='__main__':
    try:main()
    except BaseException:
        try:
            if PROGRESS_OWNED:remember('audit-refused',error=traceback.format_exc())
        except BaseException as error:print('Audit phase preservation failed: '+repr(error),file=sys.stderr)
        raise
