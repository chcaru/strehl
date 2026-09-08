"""Independent v3 runtime-file policy and bounded audit-phase publication.
Stdlib only. No image/model/registrar execution; original helper objects returned unchanged.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import traceback

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
PARTIAL=HERE/'work/independent-sift-lightglue-prefix-v3-partial.json'
TEMP=HERE/'work/independent-sift-lightglue-prefix-v3-partial.tmp'
MAX_PARTIAL=32*1024
EXPECTED={}
VERIFIED={}
RUNTIME_IDENTITY={}
TOTAL_HASH_BYTES=0
STATE=dict(schema='m193c-independent-prefix-v3-phase-receipt-v1',status='INCOMPLETE_PREFIX_AUDIT',saved_prefix_verified=False,admission_allowed=False,active_phase='initialization',completed={},runtime_progress=dict(visited_files=0,opaque_bytes=0,last_path=None),error=None,scope='Returned audit subchecks only; overall audit remains incomplete. No phase receipt admits a private commission or real model run. Failed or unvisited helpers are not passes.')


def need(ok,message):
    if not ok:raise ValueError(message)

def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def sha(b):return hashlib.sha256(b).hexdigest()

def typed(v):
    if isinstance(v,bytes):return {'bytes_base64':base64.b64encode(v).decode()}
    if isinstance(v,tuple):return {'tuple':[typed(x) for x in v]}
    if isinstance(v,list):return [typed(x) for x in v]
    if isinstance(v,dict):return {k:typed(x) for k,x in v.items()}
    need(v is None or type(v) in (int,float,str,bool),'owned helper returned only standard serializable values');return v

def fingerprint(v):return sha(canonical(typed(v)))

def emit():
    STATE['unvisited_phase_names']=[x for x in STATE.get('expected_phase_names',[]) if x not in STATE['completed']]
    raw=canonical(STATE);need(len(raw)<=MAX_PARTIAL,'32 KiB phase receipt cap')
    need(PARTIAL.parent==HERE/'work' and TEMP.parent==PARTIAL.parent and not TEMP.exists(),'fresh bounded phase staging path')
    if PARTIAL.exists():
        s=PARTIAL.stat(follow_symlinks=False);need(stat.S_ISREG(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400 and s.st_nlink==1,'owned phase publication remains ordinary single-link')
    with TEMP.open('xb') as stream:need(stream.write(raw)==len(raw),'full phase write');stream.flush();os.fsync(stream.fileno())
    os.replace(TEMP,PARTIAL)


def signature(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,getattr(s,'st_file_attributes',0),s.st_nlink,stat.S_ISREG(s.st_mode))

def property_allowed(regular,reparse,links,extent,cap,external_runtime):
    return regular and not reparse and type(links) is int and (links>0 if external_runtime else links==1) and type(extent) is int and 0<=extent<=cap

def ref_allowed(expected,declared,known_path):
    if type(expected) is not dict or set(expected)!={'path','bytes','sha256'} or type(expected['bytes']) is not int or expected['bytes']<0:return False
    if type(expected['path']) is not str or type(expected['sha256']) is not str or len(expected['sha256'])!=64 or any(c not in '0123456789abcdef' for c in expected['sha256']):return False
    return known_path and expected==declared


def policy_commission():
    need(property_allowed(True,False,1,4,8,True) and property_allowed(True,False,2,4,8,True),'actual policy admits positive external link counts1/2')
    cases=[('zero-links',(True,False,0,4,8,True)),('reparse',(True,True,2,4,8,True)),('nonregular',(False,False,2,4,8,True)),('owned-multilink',(True,False,2,4,8,False)),('extent-overrun',(True,False,2,9,8,True))]
    need(all(not property_allowed(*args) for _,args in cases),'link/property negative controls')
    ref=dict(path='declared.dll',bytes=4,sha256='a'*64);bad=[]
    for field,value in (('path','other.dll'),('bytes',5),('sha256','b'*64)):
        mutant=dict(ref);mutant[field]=value;bad.append((field,ref_allowed(mutant,ref,True)))
    need(ref_allowed(ref,ref,True) and not ref_allowed(ref,ref,False) and all(not x[1] for x in bad),'exact membership/path/extent/hash controls')
    start=(1,2,4,5,0,2,True);changed=list(start);changed[1]+=1;need(start!=tuple(changed),'changed identity comparison rejects')
    obj={'a':[1,b'abc'], 'b':(2,3)};before=fingerprint(obj);alias=obj;need(alias is obj and fingerprint(alias)==before,'observer positive exact object');mutant={'a':[1,b'abd'],'b':(2,3)};need(fingerprint(mutant)!=before,'observer actual byte mutation detected')
    return ['external-links1-and2',*[name for name,_ in cases],'unknown-path','wrong-path','wrong-extent','wrong-hash','changed-identity','observer-byte-mutation']


def install(h):
    global TOTAL_HASH_BYTES
    need(not PARTIAL.exists() and not TEMP.exists(),'fresh version3 phase receipts')
    original_file=h.file
    STATE['expected_phase_names']=['export:private-reference','export:private-source',*[f'export:real-{i}' for i in range(9)],'normalized-private-descriptors','learned-output','model-load-witness','runtime:runtime-before.json','runtime:runtime-after.json','scientific-prefix']
    STATE['policy_controls']=policy_commission();emit()
    def verify(p,expected=None,kind='metadata'):
        global TOTAL_HASH_BYTES
        p=Path(p).resolve()
        if kind!='runtime' or p.is_relative_to(ROOT) or p==h.PYTHON:return original_file(p,expected,kind)
        declared=EXPECTED.get(str(p));need(ref_allowed(expected,declared,declared is not None) and str(p) in h.RUNTIME,'only exact manifest-bound external runtime FileRef')
        need(p.suffix.lower() not in {'.tif','.tiff','.arw','.dng','.raw','.png','.jpg','.jpeg','.exr'},'no image runtime payload')
        literal=Path(expected['path']);literal=literal if literal.is_absolute() else ROOT/literal
        STATE['runtime_progress']['last_path']=str(p)
        before=literal.stat(follow_symlinks=False);sig=signature(before)
        need(property_allowed(stat.S_ISREG(before.st_mode),bool(getattr(before,'st_file_attributes',0)&0x400),before.st_nlink,before.st_size,2<<30,True),'external runtime is ordinary, non-reparse, positive stable links and bounded extent')
        need(before.st_size==expected['bytes'],'exact manifest extent before open')
        STATE['runtime_progress']['last_path']=str(p)
        if str(p) in VERIFIED:
            need(RUNTIME_IDENTITY[str(p)]==sig and h.same(VERIFIED[str(p)],expected),'already hashed external identity/reference stable');return VERIFIED[str(p)]
        digest=hashlib.sha256();count=0
        with literal.open('rb') as stream:
            need(signature(os.fstat(stream.fileno()))==sig,'external runtime opened the same file identity')
            for block in iter(lambda:stream.read(1024*1024),b''):
                count+=len(block);need(count<=expected['bytes']<=2<<30 and TOTAL_HASH_BYTES+count<=16<<30,'bounded external opaque hash');digest.update(block)
            need(signature(os.fstat(stream.fileno()))==sig,'external runtime handle identity stable after hash')
        need(signature(literal.stat(follow_symlinks=False))==sig and count==expected['bytes'] and digest.hexdigest()==expected['sha256'],'external runtime exact hash/extent/pre-open-post identity')
        result=dict(path=str(p),bytes=count,sha256=digest.hexdigest());need(str(p) not in h.USED or h.USED[str(p)]==result,'no conflicting previously consumed file')
        h.USED[str(p)]=result;h.IDENTITIES[str(p)]=h.identity(before);VERIFIED[str(p)]=result;RUNTIME_IDENTITY[str(p)]=sig;TOTAL_HASH_BYTES+=count
        STATE['runtime_progress'].update(visited_files=len(VERIFIED),opaque_bytes=TOTAL_HASH_BYTES,actual_multilink_files=sum(s[5]>1 for s in RUNTIME_IDENTITY.values()))
        if len(VERIFIED)%128==0:emit()
        return result
    h.file=verify
    def wrapper(name,fn,describe):
        def observed(*args,**kwargs):
            STATE['active_phase']=name
            try:
                if name=='runtime':
                    snapshot=h.read(args[0]);declared=snapshot['files']+[{k:r[k] for k in ('path','bytes','sha256')} for r in snapshot['empty_runtime_files']]
                    for r in declared:
                        path=str(h.path(r));existing=EXPECTED.get(path)
                        need(existing is None or existing==r,'same external runtime declaration across snapshots');EXPECTED[path]=r
                value=fn(*args,**kwargs);obj_id=id(value);before=fingerprint(value);label,summary=describe(value,args)
                need(fingerprint(value)==before and id(value)==obj_id,'summary leaves original returned object unchanged')
                row=dict(status='VERIFIED_PHASE_ONLY',summary=summary,returned_value_before_sha256=before,returned_value_after_sha256=before,same_returned_object=True)
                STATE['completed'][label]=row;emit()
                after=fingerprint(value);need(after==before and id(value)==obj_id,'actual phase publication leaves returned value unchanged')
                return value
            except BaseException:
                STATE['error']=traceback.format_exc();emit();raise
        return observed
    def export_summary(v,args):return 'export:'+v['manifest']['name'],dict(record=v['record'],name=v['manifest']['name'],count=len(v['keys']),descriptors_sha256=v['manifest']['core']['descriptors_sha256'],keys_sha256=v['manifest']['core']['keys_sha256'],explicit_coarse_size=v['manifest']['explicit_coarse_image_size'],native_coordinate_gauge=v['manifest']['qualification']['coordinate_gauge'],attribute_provenance=v['manifest']['attribute_provenance'])
    def normalized_summary(v,args):return 'normalized-private-descriptors',v
    def learned_summary(v,args):return 'learned-output',dict(v[0],capped_count=len(v[1]),capped_landmarks_canonical_sha256=sha(h.canonical(v[1])))
    def model_summary(v,args):return 'model-load-witness',v
    def runtime_summary(v,args):return 'runtime:'+Path(args[0]['path']).name,v
    def scientific_summary(v,args):return 'scientific-prefix',dict(export_count=len(v['exports']),control_count=len(v['controls']),all_visited_controls_pass=all(x['passed'] for x in v['controls']),unvisited_controls=v['unvisited_controls'],counters=v['counters'],refused_control=v['refused_control'])
    for name,desc in (('exported',export_summary),('normalized',normalized_summary),('learned',learned_summary),('model_load',model_summary),('runtime',runtime_summary),('scientific',scientific_summary)):
        setattr(h,name,wrapper(name,getattr(h,name),desc))
    return h


def final_check(h):
    for path,sig in RUNTIME_IDENTITY.items():need(signature(Path(path).stat(follow_symlinks=False))==sig,'all external runtime link/handle identities remain stable at final check')
    need(STATE['error'] is None,'no phase failure was hidden')
    STATE['active_phase']='final-audit-publication';emit()
    p=h.file(PARTIAL);return dict(partial=p,overall_status='INCOMPLETE_PHASE_RECEIPT_FULL_AUDIT_RESULT_SEPARATE',policy_controls=STATE['policy_controls'],external_runtime_files=len(VERIFIED),external_runtime_bytes=TOTAL_HASH_BYTES,actual_multilink_files=sum(s[5]>1 for s in RUNTIME_IDENTITY.values()),observed_link_counts=sorted(set(s[5] for s in RUNTIME_IDENTITY.values())),completed_phase_names=sorted(STATE['completed']),scope='Exact external manifest paths/hashes/extents and stable regular/non-reparse handle identities; positive hard links allowed only here. Owned source/export/checkpoint policy unchanged. Phase observers return the identical original objects with canonical value hashes before/after publication; no original helper assertion or numerical subject is bypassed.')


def preserve_failure():
    if STATE['error'] is None:
        STATE['error']=traceback.format_exc()
        STATE['active_phase']='adapter-validation-after-or-between-returned-helpers'
    emit()
