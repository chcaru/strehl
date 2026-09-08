"""Independent saved fixed23 LightGlue audit. SOURCE ONLY until root release.
Reads saved values and hashes; never imports subject/model/fit/image code.
Literal private truth, actual output tensors, source-gauge residuals, complete23
population and physical-vs-reserved resources are independently re-chosen.
"""
import time
START=time.perf_counter()
import argparse
import ast
from decimal import Decimal as D,ROUND_CEILING
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
import traceback
import types
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/m193c-output-grid';WORK=HERE/'work'
OUT=HERE/'sift-lightglue-real-1';OLD=HERE/'sift-lightglue-commission-1';SELF=Path(__file__).resolve()
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
V1=WORK/'independent-sift-lightglue-saved-completion-audit.py'
V1_PIN=(59052,'7c93287992515235438912569520513eb7d2573742304a253d00104d96e044fa')
HELPER=WORK/'independent-sift-lightglue-commission-audit.py'
HELPER_PIN=(62292,'ccb78254596b6402139bb4ff4541a5bb6f0597175268a426bef66ba5e4f7c03c')
PURE=('need','integer','sha','canonical','strict','path','same','close','f32','pack','flatten','arr','core_expected','exported','truth','corners','sites','learned','rootsift64')
Q=1<<32;KIB=1024;MIB=1<<20;BOUND=2**-15
COMPLETE='COMPLETE_FIXED_REAL_LIGHTGLUE_DIAGNOSTIC_ONLY';VERSION='m193c-sift-lightglue-real-v1'
ALLOW=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
CAPS=dict(cpu_seconds=100,wall_seconds=180,file_bytes=8*MIB,metadata_bytes=8*MIB)
FAMILY=dict(normalized=4236800,predictions=777600,rows=401408,fits=114688,runtime=131072,metadata=589824,log=MIB,terminal=512*KIB,publication=256*KIB)
META=dict(codec=204*KIB,inputs=64*KIB,state=64*KIB,manifest=208*KIB,controls=24*KIB,controller=12*KIB)
QUAL=dict(scope='REAL_PAIR_DIAGNOSTIC_ONLY',coordinate_gauge='native Q8=8*coarse Q8+896',native_coordinate_lattice_step_q8=8,inherited_coordinate_quantization_guard_q8=1,support_guard_qualification='UNQUALIFIED',support_or_overlap_admission=False,placement_or_merge_admission=False,fit_rms_failure_direction='coherent wrong correspondences can fit tightly; real physical truth is unavailable',heldout_scope='geometric fit holdout after whole-pair learned assignment; not independent learned-model generalization')
PRIVATE_QUAL=dict(coordinate_gauge='native pixel centres; q_native=8*q_coarse+896',coordinate_lattice_step_q8=8,inherited_quantization_guard_q8=1,guard_status='UNQUALIFIED_FOR_COARSE_LATTICE',scope='Private compatibility/known geometry only; no real model pairs, support, overlap, placement or quality admission')
COUNTS=(487,1024,1024,1024,1024,1024,1024,910,734)
PAIRS=((0,1),(0,2),(0,4),(0,5),(1,2),(1,3),(1,5),(2,3),(2,4),(2,5),(2,6),(3,4),(3,5),(3,7),(4,5),(4,6),(4,8),(5,6),(5,7),(5,8),(6,7),(6,8),(7,8))
IDS=['private-off','private-on','private-placebo','inference-observer','two-native-map-destroyer','within-split-association-destroyer','private-restored','final-state-restored']
PUB_IDS=['normal','capacity','oversized','late-before-stdout','restored-placebo','stdout-after-escape','emergency-fallback']
CODEC_IDS=['whole-actual-record','serializer-observer','one-payload-byte','index-range','declared-dimension','declared-offset','score-bit','whole-record-field','zero-match-structure','restored']
ORDER=('matches0','matches1','matching_scores0','matching_scores1','prune0','prune1','matches','scores')
NAMES=['result.json','first-publication.json','publication-stage.json','emergency-refusal.json']
PROGRESS=WORK/'independent-sift-lightglue-real-audit-progress.json'
FAMILY_RESERVES=dict(source=96*KIB,final=112*KIB,progress=32*KIB,staging=32*KIB,stderr=16*KIB,outer=8*KIB,source_review=8*KIB,report=8*KIB,ledger=8*KIB)
USED={};IDENTITIES={};RUNTIME={};PHASES=[];PROGRESS_OWNED=False;RUNTIME_BYTES=0

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

def typed_work(value):
    need(type(value) is dict and set(value)==set(ALLOW),'closed four work fields')
    need(all(type(value[k]) in (int,float) and math.isfinite(value[k]) and value[k]>=0 for k in ('cpu_seconds','wall_seconds')) and all(integer(value[k]) and value[k]>=0 for k in ('file_bytes','metadata_bytes')),'finite nonnegative typed work')

def residue(row,t):
    rx,ry=row['reference_q8'];sx,sy=row['source_q8']
    return (t['a']*sx-t['b']*sy+t['tx']*256-rx*Q)**2+(t['b']*sx+t['a']*sy+t['ty']*256-ry*Q)**2

def compare_record(value,name,a,b):
    expected=dict(name=name,left_sha256=sha(canonical(a)),right_sha256=sha(canonical(b)),equal=canonical(a)==canonical(b))
    need(value==expected,'complete canonical comparison '+name);return expected['equal']

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

def file(p,expected=None,kind='metadata'):
    global RUNTIME_BYTES
    p=Path(os.path.abspath(p));suffix=p.suffix.lower()
    need(suffix not in {'.arw','.dng','.raw','.tif','.tiff','.png','.jpg','.jpeg','.exr','.bmp','.pth'},'no image/checkpoint stat or content')
    if kind=='metadata':
        need((p.is_relative_to(ROOT) and suffix in {'.py','.json','.md','.txt','.log','.rs','.toml','.lock','.tsv'}) or p==PYTHON,'owned source/metadata');cap=16*MIB
    elif kind=='export':
        need(p.parent==OLD/'worker' and suffix in {'.u8','.i64','.f32'},'only admitted original export payload');cap=512*KIB
    elif kind=='payload':
        need(p.is_relative_to(OUT/'worker') and suffix in {'.bin','.f32'},'actual real numeric payload only');cap=512*KIB
    else:need(kind=='runtime' and p in RUNTIME,'manifest-bound runtime');cap=2<<30
    before=p.stat(follow_symlinks=False);policy(p,before,kind);need(p.resolve()==p and 0<=before.st_size<=cap,'literal bounded file')
    identity=ident(before)
    if str(p) in USED:
        need(identity==IDENTITIES[str(p)],'previous read identity unchanged');result=USED[str(p)]
    else:
        if kind=='runtime':
            RUNTIME_BYTES+=before.st_size;need(RUNTIME_BYTES<=16<<30,'unique runtime hash bytes within frozen16GiB envelope')
        digest=hashlib.sha256();count=0
        with p.open('rb') as f:
            need(ident(os.fstat(f.fileno()))==identity,'same opened identity')
            for block in iter(lambda:f.read(MIB),b''):
                count+=len(block);need(count<=cap,'bounded opened extent');digest.update(block)
            need(ident(os.fstat(f.fileno()))==identity,'same opened after identity')
        need(ident(p.stat(follow_symlinks=False))==identity and count==before.st_size,'same complete file after read')
        result=dict(path=str(p),bytes=count,sha256=digest.hexdigest());USED[str(p)]=result;IDENTITIES[str(p)]=identity
    if expected is not None:need(same(result,expected),'resolved exact extent/hash/path')
    return result

def raw(r,kind='metadata'):
    ref_shape(r);file(path(r),r,kind);identity=IDENTITIES[str(path(r))]
    with path(r).open('rb') as f:
        need(ident(os.fstat(f.fileno()))==identity,'parsed opened identity');data=f.read(r['bytes']+1)
        need(ident(os.fstat(f.fileno()))==identity,'parsed opened unchanged')
    need(len(data)==r['bytes'] and sha(data)==r['sha256'] and ident(path(r).stat(follow_symlinks=False))==identity,'same parsed exact bytes')
    return data

def read(r):return strict(raw(r))
def actual(p,kind='metadata'):return read(file(p,kind=kind))
def remember(phase,summary=None,error=None):
    if error is None:PHASES.append(dict(phase=phase,status='VERIFIED_PHASE_ONLY',summary=summary))
    value=dict(schema='m193c-real-audit-progress-v1',status='AUDIT_INCOMPLETE',admission_allowed=False,active_phase=phase,visited=PHASES,error=error)
    data=compact(value);need(PROGRESS_OWNED and len(data)<=32*KIB,'partial32KiB, simultaneous stage32KiB')
    temporary=PROGRESS.with_suffix('.tmp');need(not temporary.exists(),'fresh staging')
    with temporary.open('xb') as f:need(f.write(data)==len(data),'complete partial write');f.flush();os.fsync(f.fileno())
    os.replace(temporary,PROGRESS)

def replace(argv,p,r=None):return [p if x=='ACTUAL_PLAN_SHA256' else r if x=='ACTUAL_REQUEST_SHA256' else x for x in argv]
def helper():
    r=file(HELPER);need((r['bytes'],r['sha256'])==HELPER_PIN,'frozen independent helper')
    z=file(V1);need((z['bytes'],z['sha256'])==V1_PIN,'frozen shared publisher/parser review source')
    tree=ast.parse(raw(r),str(HELPER));nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in PURE]
    need(len(nodes)==len(PURE),'closed pure independent functions')
    h=types.ModuleType('independent_real_math');h.__dict__.update(dict(ROOT=ROOT,OUT=OLD,Q=Q,QUAL=PRIVATE_QUAL,BOUND=BOUND,Path=Path,read=read,raw=raw,need=need,json=json,math=math,hashlib=hashlib,struct=struct,itertools=itertools,statistics=statistics))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),h.__dict__)
    return h

def authority(plan):
    need(set(plan)==set('schema source_bindings private_baseline prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-sift-lightglue-real-plan-v1' and plan['preparation_allowance']==ALLOW,'closed new plan')
    bundles=plan['private_baseline'];need(set(bundles)=={'commission_prefix','saved_completion'},'two limited private prerequisites')
    prefix=bundles['commission_prefix'];done=bundles['saved_completion']
    need(set(prefix)==set('plan worker_result outer console exit audit'.split()) and set(done)==set('plan result outer console exit audit'.split()),'closed prior references')
    pa,old,pp=(read(prefix[k]) for k in ('audit','worker_result','plan'))
    da,parent,dp=(read(done[k]) for k in ('audit','result','plan'))
    need(pa['schema']=='m193c-saved-sift-lightglue-commission-prefix-audit-v3' and pa['status']=='PASS_SAVED_SIFT_LIGHTGLUE_COMMISSION_PREFIX_AUDIT' and pa['saved_prefix_verified'] is True and all(pa[k] is False for k in ('subject_complete','admission_allowed','cpu_accounting_complete')),'limited historical prefix')
    need(da['schema']=='m193c-saved-sift-lightglue-saved-completion-audit-v2' and da['status']=='PASS_SAVED_PRIVATE_LIGHTGLUE_COMPLETION_OUTCOME_AUDIT' and da['audit_version']=='v2-one-runtime-conjunct' and all(da[k] is True for k in ('subject_complete','combined_private_prerequisite_eligible','new_run_cpu_accounting_complete')) and all(da[k] is False for k in ('admission_allowed','cpu_accounting_complete','original_commission_complete')) and da['refused_control'] is None and da['old_run_status']=='REFUSED','audited saved completion prerequisite only')
    for bundle,audit in ((prefix,pa),(done,da)):
        need(set(audit['external'])==set(bundle)-{'audit'} and all(same(audit['external'][k],bundle[k]) for k in audit['external']),'exact prior subject authority')
        for key in bundle:file(path(bundle[key]),bundle[key])
    need(same(pa['worker_result'],prefix['worker_result']) and same(parent['worker_result'],da['worker_result']) and all(same(da['commission_prefix'][k],prefix[k]) and same(dp['commission_prefix'][k],prefix[k]) for k in prefix),'same prior workers and prefix')
    private=read(da['worker_result'])
    need(old['status']=='REFUSED' and old['assembly'] is None and old['counters']['private_model_forwards']==1 and old['counters']['real_model_forwards']==0 and old['counters']['registrar_calls']==0 and len(old['exports'])==11 and old['inference_observer_nonperturbation']=='UNTESTED_ONE_FORWARD','original failed one-forward state unchanged')
    need(not (OLD/'result.json').exists() and pa['parent_result_missing'] is True,'missing original parent stays missing')
    need(parent['status']==private['status']=='COMPLETE_SAVED_PRIVATE_LIGHTGLUE_CHECKS_ONLY' and private['counters']==dict(images=0,extractions=0,normalizations=0,model_forwards=0,registrar_calls=5),'actual completed saved-private population')
    need(len(private['controls'])==5 and all(x['passed'] is True for x in private['controls']) and len(private['publication_control_summary'])==7 and all(x['passed'] is True for x in private['publication_control_summary']),'all actual prerequisite controls')
    for previous in (pp,dp):need(all(plan['source_bindings'].get(k)==v for k,v in previous['source_bindings'].items()),'entire immutable historical source closure')
    prior=read(plan['prior_work']);typed_work(prior);base=da['actual_final_work'];typed_work(base)
    need(D(da['next_wall_seconds'])==D(str(base['wall_seconds'])),'exact accepted prior wall string')
    for k in ALLOW:
        value=D(str(base[k]));value=value.quantize(D('.000001'),rounding=ROUND_CEILING) if k.endswith('seconds') else value
        need(D(str(prior[k]))==value+ALLOW[k],'upward carry and full new preparation')
    return old,private,da,prior

def exports(h,old):
    values=[]
    for i,r in enumerate(old['exports']):
        record=read(r);cache=read(record['origin']['cache']);side=('reference','source')[i] if i<2 else None
        expected=h.core_expected(cache[side] if side else cache,i<2);name='private-'+side if side else 'real-'+str(i-2)
        size=([384,288],[288,384])[i] if i<2 else [879,586]
        values.append(h.exported(r,expected,name,size,record['origin']['cache'],side))
        need(expected['count']==(1024 if i<2 else COUNTS[i-2]),'exact held feature population')
    h.learned(old,values)
    return values,read(old['learned_output'])

def decode(header,payload):
    need(type(header) is dict and set(header)==set('schema n0 n1 accepted_count payload_bytes payload_sha256 segments stop record_sha256 intrinsic_extras'.split()),'complete codec header')
    need(header['schema']=='m193c-lightglue-tensor-output-v1','codec schema')
    n,z,k=(header[x] for x in ('n0','n1','accepted_count'))
    need(all(integer(x) for x in (n,z,k)) and 1<=n<=1024 and 1<=z<=1024 and 0<=k<=min(n,z),'bounded codec counts')
    need(len(payload)==header['payload_bytes']==12*(n+z)+8*k and sha(payload)==header['payload_sha256'],'complete packed extent/hash')
    shapes=([1,n],[1,z],[1,n],[1,z],[1,n],[1,z],[k,2],[k]);out={};witness={};offset=0
    need(type(header['segments']) is list and len(header['segments'])==8,'all eight tensor segments')
    for j,(name,shape,seg) in enumerate(zip(ORDER,shapes,header['segments'],strict=True)):
        storage,code,width=('<i4','i',4) if j<2 else ('<u2','H',2) if j==6 else ('<f4','f',4)
        original,original_code=('<i8','q') if j in (0,1,6) else ('<f4','f')
        count=math.prod(shape)
        need(type(seg) is dict and set(seg)==set('name offset bytes storage_dtype original_dtype shape original_sha256'.split()),'closed segment fields')
        need(seg['name']==name and seg['shape']==shape and all(integer(x) for x in seg['shape']) and seg['storage_dtype']==storage and seg['original_dtype']==original and integer(seg['offset']) and seg['offset']==offset and integer(seg['bytes']) and seg['bytes']==count*width,'exact nonoverlapping segment schema')
        values=list(struct.unpack('<'+str(count)+code,payload[offset:offset+count*width]));offset+=count*width
        if j<2:need(all(-1<=x<(z if j==0 else n) for x in values),'directional range')
        elif j==6:need(all(0<=x<(n if i%2==0 else z) for i,x in enumerate(values)),'compact range')
        else:need(all(math.isfinite(x) and (x==9.0 if j in (4,5) else 0<=x<=1) for x in values),'finite scores and actual float-nine pruning')
        original_bytes=struct.pack('<'+str(count)+original_code,*values)
        need(sha(original_bytes)==seg['original_sha256'],'original tensor byte reconstruction')
        out[name]=[values] if j<6 else [values[i:i+2] for i in range(0,len(values),2)] if j==6 else values
        witness[name]=dict(dtype=original,shape=shape,sha256=sha(original_bytes))
    need(offset==len(payload) and integer(header['stop']) and header['stop']==9,'complete payload and nine layers')
    out['stop']=9;pairs=[[i,j] for i,j in enumerate(out['matches0'][0]) if j>=0]
    need(pairs==out['matches'] and len(pairs)==k and len({x[1] for x in pairs})==k and sum(x>=0 for x in out['matches1'][0])==k,'dense compact one-to-one population')
    need(all(out['matches1'][0][j]==i and out['matching_scores0'][0][i]==out['matching_scores1'][0][j]==score and .1<score<=1 for (i,j),score in zip(pairs,out['scores'],strict=True)),'mutual directional confidence association')
    extras=header['intrinsic_extras'];need(type(extras) is dict and not {'output','tensor_bytes'}&set(extras),'separate entire intrinsic extras')
    record=dict(extras,output=out,tensor_bytes=witness);need(sha(canonical(record))==header['record_sha256'],'whole intrinsic record reconstruction')
    return record

def artifact(ref):
    value=read(ref);need(set(value)=={'header','payload'},'whole codec artifact');return value['header'],raw(value['payload'],'payload')
def clone(value):return strict(canonical(value))
def rejection(fn):
    try:fn()
    except (ValueError,struct.error):return True
    return False

def codec_controls(worker,cached):
    receipts=[];expected_header=None;expected_payload=None
    for ordinal,row in enumerate(worker['codec_controls'],1):
        need(ordinal<=len(CODEC_IDS) and row==dict(id=CODEC_IDS[ordinal-1],passed=True),'ordered actual passed codec prefix')
        ref=file(OUT/'worker/metadata/codec'/('control-'+str(ordinal)+'.json'));rec=read(ref)
        need(rec['id']==row['id'] and rec['passed'] is True,'codec row receipt identity');e=rec['evidence'];name=row['id']
        if name=='whole-actual-record':
            expected_header,expected_payload=artifact(e['artifact']);value=decode(expected_header,expected_payload)
            need(canonical(value)==canonical(cached) and e['record_sha256']==sha(canonical(cached)),'entire actual cached positive')
        elif name=='serializer-observer':need(e['modes']==dict.fromkeys(('off','on','placebo'),sha(canonical(cached))),'actual complete serializer witness')
        elif name=='restored':
            head,data=artifact(e['artifact']);need(head==expected_header and data==expected_payload and decode(head,data)==cached and e['restored_sha256']==e['input_after_sha256']==sha(canonical(cached)),'full original restored codec input')
        elif name=='zero-match-structure':
            head,data=artifact(e['artifact']);value=decode(head,data);o=value['output']
            need(head['n0']==head['n1']==1024 and head['accepted_count']==e['compact_rows']==0 and len(data)==e['dense_bytes']==24576,'actual zero metadata extent')
            need(value['schema']=='m193c-zero-match-codec-fixture-v1' and value['scope']==e['scope'] and 'not an inferred or actual model return' in e['scope'] and all(x==-1 for x in o['matches0'][0]+o['matches1'][0]) and all(x==0.0 for x in o['matching_scores0'][0]+o['matching_scores1'][0]) and o['matches']==o['scores']==[],'labelled zero structure distinct from model measurement')
        else:
            head=clone(expected_header);data=bytearray(expected_payload);error=None
            if name=='one-payload-byte':data[0]^=1;head['payload_sha256']=sha(data)
            elif name=='index-range':data[:4]=struct.pack('<i',-2);head['payload_sha256']=sha(data);error='INDEX_RANGE'
            elif name=='declared-dimension':head['segments'][0]['shape'][1]+=1;error='SEGMENT_SCHEMA'
            elif name=='declared-offset':head['segments'][1]['offset']+=1;error='SEGMENT_OFFSET'
            elif name=='score-bit':data[head['segments'][-1]['offset']]^=1;head['payload_sha256']=sha(data);error=['ORIGINAL_TENSOR_HASH','PRUNING_OR_SCORE_RANGE']
            elif name=='whole-record-field':head['intrinsic_extras']['codec_fixed_metadata_fault']=True;error='WHOLE_RECORD_HASH'
            else:raise ValueError('unregistered codec fault')
            actual_head,actual_data=artifact(e['artifact'])
            need(actual_head==head and actual_data==bytes(data) and e['expected_error']==error and type(e['error']) is str and (error is None or e['error'] in (error if isinstance(error,list) else [error])),'actual retained exact codec mutant and refusal')
            need(rejection(lambda:decode(head,bytes(data))),'independent codec rejection power')
        receipts.append(dict(id=name,passed=True,record=ref))
    return receipts

def input_records(h,worker,old,values):
    if not worker.get('inputs'):return [],[],None
    manifest=read(worker['inputs']);need(manifest['schema']=='m193c-real-input-manifest-v1' and len(manifest['rows'])==11,'all eleven actual model inputs')
    prior=read(old['normalized_private_descriptors']);prior_inputs=read(old['model_inputs']);summary=[]
    for i,(e,data) in enumerate(zip(manifest['rows'],values,strict=True)):
        n=len(data['keys']);need(same(e['export'],data['record']),'actual descriptor row association')
        kind='export' if i<2 else 'payload';payload=raw(e['normalization'],kind)
        need(len(payload)==n*512,'all normalized values retained');actual_values=struct.unpack('<'+str(n*128)+'f',payload)
        need(all(math.isfinite(x) for x in actual_values),'all normalized float32 finite')
        attrs={k:dict(w,shape=[1]+w['shape']) for k,w in data['attributes'].items()};attrs['descriptors']=dict(dtype='<f4',shape=[1,n,128],sha256=sha(payload))
        need(e['tensors']==attrs,'entire shape/type/value input witnesses')
        if i<2:need(same(e['normalization'],prior['sides'][i]['file']) and attrs==prior_inputs['image'+str(i)] and e['provenance']=='REUSED_ADMITTED_ACTUAL_PRIVATE_FLOAT32','same actual private tensors')
        else:need(path(e['normalization'])==OUT/'worker/normalized'/('real-'+str(i-2)+'.f32') and e['provenance']=='NEW_UPSTREAM_ROOTSIFT_ON_EXPORTED_U8_COPY','fixed actual new normalization')
        maximum=0;wrong=None
        for j,row in enumerate(data['descriptors']):
            truth=h.rootsift64(row);part=actual_values[j*128:(j+1)*128];maximum=max(maximum,max(abs(a-b) for a,b in zip(part,truth,strict=True)))
            if i==0 and j==0:
                norm=math.sqrt(sum(x*x for x in row));bad=[x/max(norm,1e-6) for x in row];wrong=max(abs(a-b) for a,b in zip(bad,truth,strict=True));need(len(set(row))>1 and wrong>BOUND,'fixed first-row L2-only alternative fails same bound')
        need(maximum<=BOUND,'every actual float32 component versus independent scalar f64 RootSIFT')
        summary.append(dict(export=e['export'],normalized=e['normalization'],count=n,components=n*128,max_absolute_component_error=maximum,bound=BOUND,fixed_first_row_l2_only_error=wrong))
    return manifest['rows'],summary,worker['inputs']

def model_witness(worker,old):
    if not worker.get('model_loading'):return None,None
    loading=read(worker['model_loading']);prior=old['model_loading']
    need(same(loading['prior_worker'],worker['private_baseline']['commission_prefix']['worker_result']) and loading['prior_field']=='model_loading' and loading['complete_parameter_coverage'] is True and loading['config']==prior['config'] and loading['constructor_buffer']==prior['constructor_buffer'],'fixed loaded model configuration and parameter coverage witness')
    names=loading['compared_field_names'];need(names==sorted(set(names)) and set(names)==set(prior)-{'blocked_imports','import_guard_restored','load_cpu_seconds','load_wall_seconds'},'all actual pre-exit loader fields, no learned omission')
    actual_loading={k:prior[k] for k in names};actual_loading['blocked_imports']=loading['blocked_imports']
    need(sha(canonical(actual_loading))==loading['actual_complete_loading_sha256'],'entire actual pre-exit loader witness reconstruction')
    if not worker.get('state_registry'):return None,dict(loading=worker['model_loading'],scope='Verified actual load witness; state registry unvisited')
    state=read(worker['state_registry']);rows=state['rows']
    need(state['schema']=='m193c-real-state-registry-v1' and rows==sorted(rows) and len({x[0] for x in rows})==len(rows)>0,'unique full state names')
    need(all(type(x) is list and len(x)==4 and x[1]=='torch.float32' and all(integer(v) and v>=0 for v in x[2]) and type(x[3]) is str and len(x[3])==64 for x in rows),'actual float32 parameter/buffer registry')
    need(sha(canonical(rows))==state['canonical_sha256'],'full state registry canonical identity')
    need([x[0] for x in rows]==prior['expected_state_keys'],'complete admitted state name population')
    mappings={x['destination']:x for x in prior['checkpoint_keys']};buffer=prior['constructor_buffer']
    for name,dtype,shape,digest in rows:
        if name==buffer['name']:
            need(dtype=='torch.float32' and shape==[9] and digest==sha(struct.pack('<9f',*buffer['values'])),'actual constructor buffer bytes versus held values')
        else:need(name in mappings and dtype==mappings[name]['dtype'] and shape==mappings[name]['shape'],'all learned destination types/shapes retain admitted mapping')
    return state,dict(loading=worker['model_loading'],registry=worker['state_registry'],state_entries=len(rows),initial_state_sha256=state['canonical_sha256'],scope='Recorded actual complete tensor hashes; byte payloads of model parameters are not independently reread or loaded by this audit.')

def prediction(ref,witness,inputs,indices,mode,state_hash,private,cached):
    v=read(ref);need(v['schema']=='m193c-real-prediction-v1' and v['qualification']==QUAL and v['scope']==('PRIVATE_CONTROL' if private else 'REAL_PAIR_DIAGNOSTIC_ONLY'),'prediction actual experiment scope')
    need(v['header']['n0']==inputs[indices[0]]['tensors']['descriptors']['shape'][1] and v['header']['n1']==inputs[indices[1]]['tensors']['descriptors']['shape'][1],'actual prediction dimensions')
    record=decode(v['header'],raw(v['payload'],'payload'))
    need(record['schema']==cached['schema'] and record['qualification']==PRIVATE_QUAL and record['inference_observer_nonperturbation']=='UNTESTED_ONE_FORWARD','legacy intrinsic labels retained only inside explicit current receipt')
    e=read(witness);actual={side:inputs[i]['tensors'] for side,i in zip(('image0','image1'),indices,strict=True)}
    hashes=[[x['sha256'] for k,x in sorted(tensors.items())] for side,tensors in sorted(actual.items())]
    need(e['mode']==mode and e['called']==(0 if mode=='off' else 1) and e['input_indices']==indices and e['tensor_order']==sorted(actual['image0']) and e['input_before']==hashes,'actual model input identity before call')
    observed_integrity=e['input_after']==hashes and e['immutable_after_sha256']==sha(canonical(actual))
    need(e['full_tensor_shapes_and_types']=='inputs' and e['intrinsic_sha256']==sha(canonical(record)),'complete observed intrinsic hash')
    need(set(e['timing'])=={'cpu_seconds','wall_seconds'} and all(type(x) in (float,int) and math.isfinite(x) and x>=0 for x in e['timing'].values()),'actual finite inference timing')
    if private:
        need(e['state_registry']=='state_registry' and type(e['state_sha256']) is str and len(e['state_sha256'])==64,'complete recorded state identity')
        observed_integrity=observed_integrity and e['state_sha256']==state_hash
    return record,dict(record=ref,witness=witness,uncapped_matches=len(record['output']['matches']),intrinsic_sha256=e['intrinsic_sha256'],timing=e['timing'],input_and_state_integrity_from_recorded_hashes=observed_integrity)

def assemble(reference,source,record):
    rows=[];output=record['output']
    for ordinal,((i,j),score) in enumerate(zip(output['matches'],output['scores'],strict=True)):
        rx,ry=reference['native'][i];sx,sy=source['native'][j]
        digest=sha(b'M193-LANDMARK-SPLIT-V1\0'+struct.pack('>iiii',rx,ry,sx,sy)+reference['descriptors'][i]+source['descriptors'][j])
        rows.append(dict(learned_ordinal=ordinal,reference_feature_index=i,source_feature_index=j,score=score,reference_q8=[rx,ry],source_q8=[sx,sy],digest=digest))
    ordered=sorted(rows,key=lambda r:(r['digest'],r['reference_q8'][1],r['reference_q8'][0],r['source_q8'][1],r['source_q8'][0]))[:256]
    return [dict(r,split='holdout' if i%2 else 'calibration') for i,r in enumerate(ordered)]

def fit(h,ref,links,mode,private=False):
    v=read(ref);need(v['schema']=='m193c-real-fit-v1' and v['mode']==mode and v['qualification']==QUAL,'actual fit scope/mode')
    out=v['intrinsic'];need(set(out)==set('status transform metrics guard error'.split()) and out['status'] in ('RETURNED','REGISTRATION_REFUSED'),'closed retained intrinsic result')
    need(v['supplied_count']==len(links) and v['supplied_canonical_sha256']==sha(canonical(links)),'complete independently assembled supplied rows')
    t=out['transform'];returned=out['status']=='RETURNED';captured=mode=='count';rows=[]
    if returned:need(type(t) is dict and set(t)=={'a','b','tx','ty'} and all(integer(x) for x in t.values()) and t['a']**2+t['b']**2>0 and out['error'] is None,'nondegenerate exact integer returned map')
    else:need(t is out['metrics'] is out['guard'] is None and set(out['error'])=={'type','code','message'} and out['error']['type']=='ContractError' and out['error']['code']=='UNMEASURED_INPUT_REGISTRATION_INADEQUATE' and type(out['error']['message']) is str,'literal scientific refusal')
    meta=v['rows'];need(set(meta)==set('count file row_bytes empty_sha256 canonical_sha256'.split()) and meta['row_bytes']==56 and 'not actual refinement subset' in v['radius_membership'],'actual radius state semantics')
    if not captured or not links:
        need(meta['count']==0 and meta['file'] is None and meta['empty_sha256']==sha(b'') and meta['canonical_sha256']==sha(canonical([])),'empty capture null payload and explicit identity')
    else:
        payload=raw(meta['file'],'payload');need(meta['count']==len(links) and len(payload)==len(links)*56 and meta['empty_sha256'] is None,'whole actual captured population')
        for i,(got,want) in enumerate(zip(struct.iter_unpack('<HHHBB4i32s',payload),links,strict=True)):
            ri,si,ordinal,split,membership,rx,ry,sx,sy,digest=got
            accepted=None if not returned else residue(want,t)<=(512*Q)**2
            need([ri,si,ordinal]==[want[k] for k in ('reference_feature_index','source_feature_index','learned_ordinal')] and split==i%2 and [rx,ry]==want['reference_q8'] and [sx,sy]==want['source_q8'] and digest.hex()==want['digest'] and membership==(0 if accepted is None else 2 if accepted else 1),'every actual index, digest, split, coordinate and returned radius bit')
            rows.append(dict(reference_q8=[rx,ry],source_q8=[sx,sy],digest=digest.hex(),split=want['split'],inlier=accepted))
        need(meta['canonical_sha256']==sha(canonical(rows)),'all original captured row values reconstructed')
    bbox=None;summary=dict(record=ref,status=out['status'],intrinsic=out,heldout=None,calibration_final_radius=None,corners=None,scope='Final-map calibration radius is descriptive; recorded refinement input count is not independently reconstructible without a fit. Real residual is fitted consistency, not physical placement truth.')
    if returned:
        need(len(links)>=24,'unchanged minimum total rows');squares=[residue(r,t) for r in links];inside=[x<=(512*Q)**2 for x in squares]
        cal=squares[0::2];hold=squares[1::2];kept=[x for x,k in zip(hold,inside[1::2],strict=True) if k]
        need(len(kept)>=12 and len(kept)*2>=len(hold) and sum(kept)<=len(kept)*(256*Q)**2,'unchanged exact native heldout count/half/one-pixel RMS')
        rms=math.sqrt(sum(kept)/len(kept))/(256*Q);m=out['metrics']
        fields='mutual_match_count calibration_count calibration_inlier_count holdout_count holdout_inlier_count heldout_rms_reference_px heldout_max_source_px_ceil_q8 coordinate_quantization_guard_q8 valid_support_continuous_margin_q8'.split()
        need(set(m)==set(fields) and all(integer(m[k]) for k in fields if k!='heldout_rms_reference_px'),'complete typed metrics')
        need(m['mutual_match_count']==len(links) and m['calibration_count']==len(cal) and m['holdout_count']==len(hold) and m['holdout_inlier_count']==len(kept) and m['heldout_rms_reference_px']==f'{rms:.9f}' and 2<=m['calibration_inlier_count']<=len(cal),'exact retained counts and selected residual; refinement count recorded only')
        det=t['a']**2+t['b']**2;maximum=max(kept);ceil=math.isqrt(maximum//det)
        if ceil*ceil*det<maximum:ceil+=1
        need(m['heldout_max_source_px_ceil_q8']==ceil and m['coordinate_quantization_guard_q8']==1 and m['valid_support_continuous_margin_q8']==ceil+129 and out['guard']==ceil+1,'source-gauge exact guard arithmetic, still unqualified')
        if captured:
            hr=[row for i,row in enumerate(links) if i%2 and inside[i]]
            bbox={side:[min(x[side][0] for x in hr),min(x[side][1] for x in hr),max(x[side][0] for x in hr),max(x[side][1] for x in hr)] for side in ('reference_q8','source_q8')}
        summary.update(heldout=dict(count=len(hold),within_two_native_pixels=len(kept),all_row_rms_native_reference_pixels=math.sqrt(sum(hold)/len(hold))/(256*Q),selected_rms_native_reference_pixels=rms),calibration_final_radius=dict(count=len(cal),within_two_native_pixels=sum(inside[0::2]),all_row_rms_native_reference_pixels=math.sqrt(sum(cal)/len(cal))/(256*Q),recorded_refinement_fit_count=m['calibration_inlier_count'],scope='DESCRIPTIVE_NOT_REFINEMENT_SUBSET'))
        if private:summary['corners']=h.corners(t)
    need(v['heldout_bbox_q8']==bbox,'entire actual captured bbox or null')
    complete=dict(out,landmarks=rows,heldout_bbox_q8=bbox,qualification=PRIVATE_QUAL) if returned else None
    if not returned:summary['refusal_scope']='Intrinsic code/message retained; unretained traceback and internal hypotheses are not reconstructed. No refusal reason is independently rerun.'
    return out,summary,complete

def truth_summary(h,rows,got):
    want=h.truth(rows)
    need(set(got)==set('scope count within_two_native_pixels sum_squared_error_q16 rms_native_pixels passes'.split()),'whole literal truth summary')
    for k in ('count','within_two_native_pixels','sum_squared_error_q16','passes'):need(got[k]==want[k] and type(got[k]) is type(want[k]),'exact independent all-row truth '+k)
    need((got['rms_native_pixels'] is None if not rows else h.close(got['rms_native_pixels'],want['rms_native_pixels'])),'independent truth RMS')
    return want

def population(worker):
    if not worker.get('population'):return None
    v=read(worker['population']);need(set(v)==set('pairs predictions fits unvisited controls control_records codec_controls'.split()),'complete compact population fields')
    for k in ('pairs','predictions','fits','control_records'):need(worker[k]==dict(count=len(v[k]),record=worker['population']),'terminal count plus exact whole population ref')
    for k in ('unvisited','controls','codec_controls'):need(worker[k]==v[k],'unabridged compact population field')
    need(len(v['pairs'])<=23 and len(v['predictions'])<=26 and len(v['fits'])<=28 and len(v['controls'])<=8 and len(v['control_records'])<=8,'fixed maximum population')
    return v

def scientific(h,worker,old,private,values,cached,inputs,state,pop,complete):
    controls=[];refs=pop['control_records'];preds=pop['predictions'];fits=pop['fits'];summaries=[];prediction_summaries=[];used_fits=[];used_preds=[];trailing=[]
    need(len(refs)<=len(pop['controls'])<=len(refs)+1 and len(refs)<=8,'retained science prefix plus at most one unsaved attempted control')
    if len(refs)<len(pop['controls']):need(not complete and pop['controls'][-1]['id']==IDS[len(refs)],'one final unsaved control remains unverified')
    for i,(ref,short) in enumerate(zip(refs,pop['controls'][:len(refs)],strict=True)):
        got=read(ref);need(got['id']==IDS[i] and short==dict(id=got['id'],passed=got['passed']) and type(got['passed']) is bool,'ordered science control rows')
        controls.append(got)
    baseline=read(private['fits'][0]);private_records=[];private_complete=[];private_links=None
    for i,(mode,fitmode) in enumerate((('off','off'),('on','count'),('placebo','placebo'))):
        if i>=len(preds):break
        row=preds[i];need(row['name']=='private-'+mode,'all private forwards precede every real call')
        record,ps=prediction(row['record'],row['witness'],inputs,[0,1],mode,state['canonical_sha256'],True,cached);used_preds.append(row);prediction_summaries.append(ps)
        links=assemble(values[0],values[1],record);private_records.append(record)
        if i>=len(fits):need(not complete,'operational fit suffix retained');break
        ref=fits[i];out,summary,whole=fit(h,ref,links,fitmode,True);used_fits.append(ref);summaries.append(summary);private_complete.append(whole)
        if i>=len(controls):need(not complete,'operational control suffix retained');break
        ctrl=controls[i];e=ctrl['evidence']
        need(ps['input_and_state_integrity_from_recorded_hashes'],'a control was reached only after actual prediction integrity gates')
        need(same(e['fit'],ref),'private group actual fit association')
        eq1=compare_record(e['model'],'whole-intrinsic-model',cached,record);eq2=compare_record(e['registrar'],'complete-intrinsic-registrar',baseline['intrinsic'],out)
        uncapped=[dict(reference_q8=values[0]['native'][a],source_q8=values[1]['native'][z]) for a,z in record['output']['matches']]
        u=truth_summary(h,uncapped,e['uncapped_truth']);c=truth_summary(h,links,e['capped_truth'])
        relation='UNCAPPED_AND_HASH_CAPPED' if len(links)<len(uncapped) else 'SAME_ROWS';need(e['population_relation']==relation,'overlap/same-population truth qualifier')
        corners=h.corners(out['transform'],e['corners']) if out['status']=='RETURNED' else None
        if corners is None:need(e['corners']==[],'refused private corners explicit empty')
        passed=eq1 and eq2 and u['passes'] and c['passes'] and corners is not None and corners['passes']
        need(ctrl['passed'] is bool(passed),'actual private control independently re-chosen')
        if not passed:need(not complete and i==len(controls)-1,'private failed group stops real population');break
        if mode=='on':private_links=links
    if len(controls)>3:
        e=controls[3]['evidence'];expected=[sha(canonical(x)) for x in private_records]
        need(len(private_records)==3 and e['intrinsic_sha256']==expected and e['scope']=='PASS_THREE_PRIVATE_FORWARDS_AFTER_CALL_SCOPE','three actual inference control operands')
        passed=len(set(expected))==1 and expected[0]==sha(canonical(cached)) and len(private_records[1]['output']['matches'])>0
        need(controls[3]['passed'] is passed and (passed or not complete and len(controls)==4),'actual inference observer gate may refuse')
    if len(controls)>4:
        e=controls[4]['evidence'];shift=dict(private_complete[1]['transform']);shift['tx']+=2*Q
        need(e['transform']==shift and e['qualification']==QUAL and not h.corners(shift,e['corners'])['passes'] and controls[4]['passed'] is True,'literal actual two-native map destroyer')
    if len(fits)>3:
        need(private_links is not None and len(private_complete)==3,'association fit follows all three private predictions')
        permutation=list(range(len(private_links)))
        for split in (0,1):
            indices=list(range(split,len(private_links),2));ranked=sorted(indices,key=lambda i:sha(b'M193C-LG-ASSOCIATION-FAULT\0'+bytes.fromhex(private_links[i]['digest'])))
            for i,j in zip(indices,ranked,strict=True):permutation[i]=j
        faults=[dict(row,source_q8=private_links[permutation[i]]['source_q8'],source_feature_index=private_links[permutation[i]]['source_feature_index']) for i,row in enumerate(private_links)]
        out,summary,_=fit(h,fits[3],faults,'count',True);used_fits.append(fits[3]);summaries.append(summary)
        if len(controls)>5:
            ctrl=controls[5];e=ctrl['evidence'];need(e['permutation']==permutation and same(e['fit'],fits[3]),'actual fixed within-split permutation')
            passed=any(a['source_q8']!=z['source_q8'] for a,z in zip(private_links,faults,strict=True)) and not h.truth(faults)['passes'] and (out['status']!='RETURNED' or not h.corners(out['transform'])['passes'])
            need(ctrl['passed'] is bool(passed),'independent physical fault rejection')
            summary['literal_fault_truth']=h.truth(faults)
    if len(fits)>4:
        out,summary,whole=fit(h,fits[4],private_links,'count',True);used_fits.append(fits[4]);summaries.append(summary)
        if len(controls)>6:
            ctrl=controls[6];e=ctrl['evidence']
            if whole is not None:eq=compare_record(e['comparison'],'entire-restored-actual-outcome',private_complete[1],whole)
            else:
                got=e['comparison'];need(got['name']=='entire-restored-actual-outcome' and got['left_sha256']==sha(canonical(private_complete[1])) and type(got['right_sha256']) is str and len(got['right_sha256'])==64 and got['equal'] is False,'refused restore has a producer-only unretained traceback hash');eq=False
            need(same(e['fit'],fits[4]) and ctrl['passed'] is bool(eq and out==baseline['intrinsic'] and h.corners(out['transform'])['passes']),'whole outcome restored without excluded fields')
    real=[]
    if pop['pairs']:
        need(len(controls)>=7 and all(x['passed'] is True for x in controls[:7]) and len(used_preds)==3 and len(used_fits)==5,'all private gates before any real attempt')
        need(worker['inference_observer_nonperturbation']=='PASS_THREE_PRIVATE_FORWARDS_AFTER_CALL_SCOPE','actual private inference observer gate')
    for ordinal,row in enumerate(pop['pairs']):
        lo,hi=PAIRS[ordinal];reference,source=(5,lo if hi==5 else hi) if 5 in (lo,hi) else (lo,hi);name=f'real-{lo}-{hi}'
        need(row['ordinal']==ordinal and row['ids']==[lo,hi] and [row['reference'],row['source'],row['reference_original'],row['source_original']]==[reference,source,reference*13,source*13],'entire fixed pair direction/order/native population')
        count=3+ordinal
        if count>=len(preds):need(not complete and row['stage']=='MODEL_ATTEMPTED' and row['prediction'] is None and row['fit'] is None and row['status'] is None,'explicit failed model suffix');break
        pr=preds[count];need(pr['name']==name,'actual named real prediction order')
        record,ps=prediction(pr['record'],pr['witness'],inputs,[reference+2,source+2],'on',state['canonical_sha256'],False,cached);used_preds.append(pr);prediction_summaries.append(ps)
        need((row['prediction'] is None and not complete and ordinal==len(pop['pairs'])-1 and row['stage']=='MODEL_ATTEMPTED') or same(row['prediction'],pr['record']),'pair exact actual prediction or retained failed-return prefix');links=assemble(values[reference+2],values[source+2],record)
        count=5+ordinal
        if count>=len(fits):
            need(not complete and row['stage'] in ('MODEL_ATTEMPTED','FIT_ATTEMPTED') and row['fit'] is None and row['status'] is None,'explicit saved-prediction or failed-fit suffix')
            trailing.append(dict(ordinal=ordinal,prediction=ps,stage=row['stage'],scope='VERIFIED_SAVED_PREDICTION_NOT_COMPLETED_PAIR'))
            break
        out,fs,_=fit(h,fits[count],links,'count',False);used_fits.append(fits[count]);summaries.append(fs)
        if row['stage']!='OBSERVED':
            need(not complete and ordinal==len(pop['pairs'])-1 and row['stage']=='FIT_ATTEMPTED' and row['fit'] is None and row['status'] is None,'saved fit returned only to failed final budget check')
            trailing.append(dict(ordinal=ordinal,prediction=ps,fit=fs,stage=row['stage'],scope='VERIFIED_SAVED_FIT_NOT_COMPLETED_PAIR'))
            break
        need(ps['input_and_state_integrity_from_recorded_hashes'] and row['status']==out['status'] and same(row['fit'],fits[count]) and row['uncapped_matches']==len(record['output']['matches']) and row['capped_matches']==len(links),'actual complete observed real pair')
        obs=actual(OUT/'worker/metadata/manifest'/(name+'-observation.json'));need(obs==row,'durable complete pair receipt')
        real.append(dict(ordinal=ordinal,ids=[lo,hi],reference=reference,source=source,uncapped_matches=row['uncapped_matches'],capped_matches=len(links),fit=fs,prediction=ps,coordinate_support=h.sites(links),coordinate_support_scope='Descriptive exact-site and radius-one-native groups; not independent correspondence truth or a new fit gate',physical_truth='UNMEASURED'))
    need(used_preds==preds and used_fits==fits,'no hidden additional prediction or fit records')
    need(pop['unvisited']==[list(x) for x in PAIRS[len(pop['pairs']):]],'exact unvisited suffix after every attempted pair')
    if len(controls)>7:
        e=controls[7]['evidence'];need(e['initial_sha256']==state['canonical_sha256'] and same(e['registry'],worker['state_registry']) and type(e['final_sha256']) is str and len(e['final_sha256'])==64,'complete final state witness')
        passed=e['final_sha256']==state['canonical_sha256'];need(controls[7]['passed'] is passed and (passed or not complete),'actual final state restore gate may refuse')
    if complete:need(len(real)==23 and len(controls)==8 and all(x['passed'] is True for x in controls) and len(preds)==26 and len(fits)==28,'all complete fixed real/scientific populations')
    return dict(controls=[dict(id=x['id'],passed=x['passed'],record=refs[i]) for i,x in enumerate(controls)],private_fits=summaries[:min(5,len(summaries))],real_pairs=real,prediction_count=len(preds),fit_count=len(fits),trailing_saved_values=trailing,private_prediction_witnesses=prediction_summaries[:3],unpublished_control=None if len(refs)==len(pop['controls']) else dict(pop['controls'][-1],scope='UNVERIFIED_UNPUBLISHED_CONTROL'),unvisited=pop['unvisited'])

def runtime_snapshot(ref,plan,old,learned):
    v=read(ref);prior=read(old['runtime_before']);need(v['schema']=='m193c-real-indexed-runtime-presence-v1' and same(v['prior_registry'],old['runtime_before']),'exact indexed admitted runtime')
    codes=v['current_file_codes'];locals_=v['local_source_paths'];paths=[];refs=[];links=[]
    need(type(codes) is list and len(codes)<=(4096 if learned else 1024) and len(set(locals_))==len(locals_),'bounded current runtime table')
    for code in codes:
        if integer(code) and code>0:
            i=code-1;need(0<=i<len(prior['files']),'admitted nonempty runtime index');r=prior['files'][i];RUNTIME[path(r)]=r;file(path(r),r,'runtime')
        elif integer(code) and code<0:
            i=-code-1;need(0<=i<len(locals_) and locals_[i] in plan['source_bindings'],'held source index');r=dict(path=locals_[i],**plan['source_bindings'][locals_[i]]);file(path(r),r)
        else:
            need(type(code) is str and code.startswith('empty:') and code[6:].isdigit() and str(int(code[6:]))==code[6:],'exact empty runtime code')
            i=int(code[6:]);need(0<=i<len(prior['empty_runtime_files']),'admitted empty index');empty=prior['empty_runtime_files'][i];r={k:empty[k] for k in ('path','bytes','sha256')};RUNTIME[path(r)]=r;file(path(r),r,'runtime')
            need(r['bytes']==0 and r['sha256']==sha(b''),'actual empty bytes');m=empty['metadata'];s=path(r).stat(follow_symlinks=False)
            need(m['bytes']==s.st_size==0 and m['mtime_ns']==s.st_mtime_ns and m['device']==s.st_dev and m['file_id']==s.st_ino and m['attributes']==getattr(s,'st_file_attributes',0),'actual unchanged empty metadata')
        paths.append(str(path(r)));refs.append(r);links.append(IDENTITIES[str(path(r))][-1])
    need(len(paths)==len(set(paths)) and set(-c-1 for c in codes if integer(c) and c<0)==set(range(len(locals_))),'unique complete actual runtime files and local table')
    common=v['prior_python_module_indices'];changed=v['changed_python_bindings'];modules=[]
    need(len(common)==len(set(common)) and all(integer(i) and 0<=i<len(prior['python_modules']) for i in common),'exact prior alias indices')
    for i in common:
        row=prior['python_modules'][i];p=str(Path(row['path']).resolve());need(p in paths,'present prior alias actual file');modules.append([row['name'],p])
    for row in changed:
        need(type(row) is list and len(row)==2 and type(row[0]) is str and integer(row[1]) and 0<=row[1]<len(paths),'actual changed alias row');modules.append([row[0],paths[row[1]]])
    need(len({r[0] for r in modules})==len(modules),'complete unique actual aliases including rebindings')
    forbidden={'flash_attn','lightglue','superpoint'} if learned else {'torch','numpy','cv2','tifffile','PIL','lightglue','flash_attn'}
    need(not any(row[0].split('.')[0] in forbidden for row in modules),'actual full module population obeys frozen import guard')
    modules.sort(key=lambda r:r[0]);native=v['native_file_indices']
    need(native==sorted(set(native)) and all(integer(i) and 0<=i<len(paths) for i in native),'unique native indices')
    native_paths=[paths[i] for i in native]
    need({r[1] for r in modules}|set(native_paths)==set(paths),'complete alias/native file union')
    need(v['python_bindings_canonical_sha256']==sha(canonical(modules)) and v['native_bindings_canonical_sha256']==sha(canonical(native_paths)),'whole actual alias and native binding hashes')
    settings=v['settings']
    if learned:
        names='torch_version numpy_version python_version executable num_threads num_interop_threads default_dtype cuda_initialized deterministic_algorithms float32_matmul_precision'.split()
        need(set(settings)==set(names) and all(settings[k]==prior[k] for k in names) and settings['cuda_initialized'] is False,'every held numeric runtime setting')
    else:need(settings==dict(python_version=prior['python_version'],scope='actual stdlib-only parent'),'actual parent runtime scope')
    prior_names={r['name']:str(Path(r['path']).resolve()) for r in prior['python_modules']};current=dict(modules)
    return dict(record=ref,files=len(paths),python_modules=len(modules),native_modules=len(native),external_multiple_links=sum(x>1 for x in links),added_names=sorted(set(current)-set(prior_names)),removed_names_count=len(set(prior_names)-set(current)),rebound_names=sorted(k for k in current.keys()&prior_names.keys() if current[k]!=prior_names[k]),python_bindings_sha256=v['python_bindings_canonical_sha256'],native_bindings_sha256=v['native_bindings_canonical_sha256'],scope='Each complete snapshot independently expanded and current file bytes verified. Source promises manifest membership/settings, not byte-identical stage populations. Full alias presence/absence is retained by original snapshot.' )

def graph(pop,worker):
    edges=[(r['reference'],r['source']) for r in pop['pairs'] if r['status']=='RETURNED']
    # Union-find components re-choose graph bookkeeping without any geometric composition.
    def groups(without=None):
        labels=list(range(9))
        def root(i):
            while labels[i]!=i:i=labels[i]
            return i
        for edge in edges:
            if edge!=without:labels[root(edge[1])]=root(edge[0])
        return [[j for j in range(9) if root(i)==root(j)] for i in range(9)]
    components=groups();bridges=[list(e) for e in edges if e[1] not in groups(e)[e[0]]]
    expected=dict(edges=[list(e) for e in edges],bridges=bridges,components=components,anchor_local=4,cycle_rank=len(edges)-9+len({tuple(c) for c in components}),qualification=QUAL)
    need(worker['graph']==expected,'independent complete graph, no composed transforms')
    outcome='ZERO_OF_23_REFUTES_FIXED_DIAGNOSTIC_FIT_ARM' if not edges else 'DIAGNOSTIC_FIT_FEASIBILITY_ONLY_PHYSICAL_TRUTH_UNMEASURED'
    need(worker['development_outcome']==outcome,'fixed outcome qualifier')
    return expected

def inventory():
    rows=[]
    for directory,dirs,names in os.walk(OUT,followlinks=False):
        for name in dirs:
            s=(Path(directory)/name).stat(follow_symlinks=False);need(stat.S_ISDIR(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'ordinary owned inventory directory')
        for name in names:
            p=Path(directory)/name;rows.append(file(p,kind='payload' if p.suffix.lower() in {'.bin','.f32'} else 'metadata'))
    need(len(rows)<=1024 and sum(r['bytes'] for r in rows)<=8*MIB,'whole actual hidden-inclusive output inventory')
    return sorted(rows,key=lambda r:r['path'])

def family(name,root,merged=False):
    parts=Path(name).parts;child=parts[0]=='worker'
    if child:parts=parts[1:]
    if parts[0]=='publication-controls':return 'publication'
    # Writer explicitly reserves own terminal slots; parent child-ledger merge calls
    # the frozen family() whose publication prefix precedes its terminal clause.
    if parts[-1] in NAMES:
        return 'publication' if child and merged and parts[-1]=='publication-stage.json' else 'terminal'
    if parts[-1].startswith('publication-'):return 'publication'
    if parts[-1]=='worker.log':return 'log'
    return parts[0] if parts[0] in FAMILY else 'metadata'

def ledger(result,root,inv,complete):
    saved=result.get('charged_path_extents')
    if saved is None:return None
    need(type(saved) is dict and len(saved)<=1024,'bounded retained path maxima')
    totals=dict.fromkeys(FAMILY,0);subs=dict.fromkeys(META,0);paths={};merged=root==OUT and result.get('worker_result') is not None
    for name,size in saved.items():
        p=Path(os.path.abspath(root/name));need(type(name) is str and not Path(name).is_absolute() and p.is_relative_to(root) and integer(size) and 0<size<=MIB,'owned monotone maxima')
        f=family(name,root,merged);totals[f]+=size;paths[p]=size
        if f=='metadata':
            parts=Path(name).parts;parts=parts[1:] if parts[0]=='worker' else parts
            sub=parts[1] if parts[0]=='metadata' and len(parts)>2 else 'controller';need(sub in META,'declared metadata subfamily');subs[sub]+=size
    need(len(paths)==len(saved) and all(totals[k]<=FAMILY[k] for k in FAMILY) and all(subs[k]<=META[k] for k in META),'entire family and metadata envelope')
    for name in NAMES:need(paths.get(root/name)==64*KIB,'four nonrefundable fixed slots')
    current={path(r):r for r in inv if path(r).is_relative_to(root)}
    uncovered=[dict(path=str(p),actual_bytes=r['bytes'],saved_maximum=paths.get(p,0)) for p,r in current.items() if p not in paths or r['bytes']>paths[p]]
    if complete:need(not uncovered,'all complete physical extents charged')
    missing=[]
    for p,size in paths.items():
        if p not in current:
            need(p.name in NAMES and (p.name in ('publication-stage.json','emergency-refusal.json') or root==OUT and p.is_relative_to(OUT/'worker')),'only consumed or precharged terminal slots may be absent')
            missing.append(dict(path=p.relative_to(root).as_posix(),charged_bytes=size))
    w=result.get('work');total=sum(paths.values());prior=result['prior_work']
    if w is None:
        need(not complete,'complete ledger must have actual work')
        return dict(total=total,physical_bytes=sum(r['bytes'] for r in current.values()),families=totals,metadata_subfamilies=subs,absent_but_charged=missing,paths=paths,uncovered=uncovered,work_witness_missing=True)
    work=w['conservative_global_work'];typed_work(work)
    need(w['new_charged_extent_bytes']==total and w['local_caps']==CAPS and w['family_limits']==FAMILY and w['metadata_subfamily_limits']==META and w['prior_cpu_accounting_complete'] is False,'entire actual work envelope')
    need(work['file_bytes']==prior['file_bytes']+total and work['metadata_bytes']==prior['metadata_bytes']+total,'all reserved path maxima conservatively charged')
    return dict(total=total,physical_bytes=sum(r['bytes'] for r in current.values()),families=totals,metadata_subfamilies=subs,absent_but_charged=missing,paths=paths,uncovered=uncovered,work_witness_missing=False)

def accounting(parent,worker,outer,advertisement,inv,complete):
    prior=parent['prior_work'];typed_work(prior);pl=ledger(parent,OUT,inv,complete);wl=ledger(worker,OUT/'worker',inv,complete) if worker else None
    missing_assimilation=[]
    if pl and wl:
        missing_assimilation=[dict(path=str(p),worker_maximum=size,parent_maximum=pl['paths'].get(p,0)) for p,size in wl['paths'].items() if pl['paths'].get(p,0)<size]
        if complete:need(not missing_assimilation,'parent incorporates all child maxima on complete outcome')
    conservative_paths={path(r):r['bytes'] for r in inv}
    for item in (pl,wl):
        if item:
            for p,size in item['paths'].items():conservative_paths[p]=max(conservative_paths.get(p,0),size)
    conservative_extent=sum(conservative_paths.values())
    if pl is None or worker is not None and wl is None:conservative_extent=max(conservative_extent,8*MIB)
    child=read(parent['child_observation']) if parent.get('child_observation') else None;cpu=0;new_complete=False;job=None
    if child is not None:
        log=file(OUT/'worker.log');need(child['log_bytes']==log['bytes'] and (child.get('log') is None or same(child['log'],log)),'actual child log')
        a=child.get('job_accounting')
        if a:
            need(all(integer(a[k]) and a[k]>=0 for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and a['total_cpu_100ns']==a['total_user_100ns']+a['total_kernel_100ns'],'exact owned Job CPU components')
            cpu=a['total_cpu_100ns']/1e7;new_complete=child.get('terminal_job_accounting') is True and a['active_processes']==0
        lim=child['limits'];need(0<lim['cpu_seconds']<=96 and 0<lim['wall_seconds']<=150 and lim['log_bytes']==MIB and lim['committed_bytes']==8<<30,'fixed dynamic worker caps')
        if complete:
            need(new_complete and child['exit_code']==0 and child['error'] is None and child['cleanup_errors']==[] and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['post_exit_drain']['completed'] is True and child['termination']['attempted'] is False,'terminal clean owned Job')
            need(cpu<=lim['cpu_seconds'] and child['wall_seconds']<=lim['wall_seconds'] and child['job_memory']['peak_job_memory_used_bytes']<=8<<30 and child['configured_job_limits']['committed_bytes']==8<<30 and integer(child['configured_job_limits']['flags']) and child['configured_job_limits']['flags']&0x2200==0x2200,'actual installed memory and kill-on-close limits')
        job=dict(record=parent['child_observation'],cpu_seconds=cpu,wall_seconds=child['wall_seconds'],terminal_accounting=new_complete,limits=lim,cleanup_errors=child['cleanup_errors'])
    sampled=advertisement.get('conservative_work_through_publication') if advertisement else None
    if sampled is not None:typed_work(sampled)
    if complete:
        need(pl and wl and sampled and new_complete and parent['new_run_cpu_accounting_complete'] is True and worker['new_run_cpu_accounting_complete'] is True,'complete current run accounting')
        need(sampled['file_bytes']==prior['file_bytes']+pl['total'] and sampled['metadata_bytes']==prior['metadata_bytes']+pl['total'],'latest advertisement contains every charged extent')
        need(D(str(sampled['cpu_seconds']))>=D(str(prior['cpu_seconds']))+D(str(cpu)) and all(D(str(sampled[k]))>=D(str(parent['work']['conservative_global_work'][k])) for k in ALLOW),'latest sample includes terminal Job CPU and no refund')
        subject=dict(sampled);subject['cpu_seconds']=float(D(str(sampled['cpu_seconds']))+D(2));subject['wall_seconds']=float(max(D(str(sampled['wall_seconds'])),D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))))
        need(all(D(str(subject[k]))-D(str(prior[k]))<=CAPS[k] for k in CAPS),'actual sample plus explicit2CPU parent tail inside released100/180')
        scope='Whole terminal Job CPU plus latest parent sample and conservative2CPU publication tail; full actual outer wall, no duplicate wall tail.'
    else:
        subject=dict(cpu_seconds=prior['cpu_seconds']+102,wall_seconds=prior['wall_seconds']+outer['elapsed_wall_seconds'],file_bytes=prior['file_bytes']+conservative_extent,metadata_bytes=prior['metadata_bytes']+conservative_extent)
        if sampled:
            subject['cpu_seconds']=max(subject['cpu_seconds'],sampled['cpu_seconds']+2);subject['wall_seconds']=max(subject['wall_seconds'],sampled['wall_seconds'])
            for k in ('file_bytes','metadata_bytes'):subject[k]=max(subject[k],sampled[k])
        scope='Incomplete subject remains ineligible; full100CPU plus2CPU tail reserved, actual outer wall, full8MiB if ledger missing. Reservations are not measured CPU.'
    return dict(subject_final_work=subject,new_run_cpu_accounting_complete=new_complete,job=job,inventory_total_bytes=sum(r['bytes'] for r in inv),inventory_count=len(inv),inventory_canonical_sha256=sha(canonical(inv)),charged_extent_bytes=pl['total'] if pl else None,charged_families=pl['families'] if pl else None,charged_metadata_subfamilies=pl['metadata_subfamilies'] if pl else None,absent_but_charged=pl['absent_but_charged'] if pl else [],missing_parent_assimilation=missing_assimilation,conservative_union_extent_bytes=conservative_extent,uncovered_by_saved_ledger=[] if pl is None else pl['uncovered'],scope=scope)

def commissioning(h):
    for bad in (b'{"x":1,"x":2}',b'{"x":1e999}'):
        need(rejection(lambda:strict(bad)),'powered parser reject')
    row=dict(path=str(SELF),bytes=1,sha256='a'*64)
    need(same(row,dict(row,path=SELF.relative_to(ROOT).as_posix())) and not same(row,dict(row,bytes=2)) and not same(row,dict(row,sha256='b'*64)),'identity spelling positive plus extent/hash destroyers')
    literal=dict(a=0,b=Q,tx=3071*Q,ty=0)
    need(h.corners(literal)['passes'] and not h.corners(dict(literal,tx=literal['tx']+2*Q))['passes'],'literal corner positive/two-native fault')
    rows=[dict(reference_q8=[3071*256,0],source_q8=[0,0]) for _ in range(24)]
    need(h.truth(rows)['passes'] and not h.truth([dict(x,reference_q8=[3075*256,0]) for x in rows])['passes'],'truth rejects coherent four-native error')
    x=dict(reference_q8=[0,0],source_q8=[0,0]);identity=dict(a=Q,b=0,tx=0,ty=0)
    need(residue(x,identity)<=(512*Q)**2<residue(x,dict(identity,tx=3*Q)),'distinct fixed-map memberships are possible, no fit executed')
    fake=Path(r'C:\Windows\System32\m193c-no-content-policy.dll');RUNTIME[fake]=row;RUNTIME[SELF]=row;RUNTIME[PYTHON]=row
    props=types.SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0,st_nlink=2);policy(fake,props,'runtime')
    for p,k,meta in ((SELF,'metadata',props),(SELF,'runtime',props),(PYTHON,'runtime',props),(fake,'runtime',types.SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0x400,st_nlink=2)),(fake.with_name('unlisted.dll'),'runtime',props)):
        need(rejection(lambda:policy(p,meta,k)),'owned/unlisted/reparse policy fault')
    for p in (fake,SELF,PYTHON):del RUNTIME[p]
    return ['strict_json','resolved_reference_identity','literal_two_pixel_and_four_pixel_truth_faults','distinct_fixed_map_memberships_not_refit','narrow_manifest_external_multilink_policy']

def main():
    global PROGRESS_OWNED
    parser=argparse.ArgumentParser()
    for key in ('plan','result','outer','console','exit'):parser.add_argument('--'+key+'-sha256',required=True)
    args=parser.parse_args();need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON,'owned exact no-bytecode Python')
    need(not PROGRESS.exists() and not PROGRESS.with_suffix('.tmp').exists(),'fresh atomic audit paths');PROGRESS_OWNED=True
    own=file(SELF);need(own['bytes']<=96*KIB and sum(FAMILY_RESERVES.values())<=384*KIB,'complete new audit family')
    family_ref=file(WORK/'independent-sift-lightglue-real-audit-ledger.json');family_doc=read(family_ref)
    need(family_doc['schema']=='m193c-real-audit-family-v1' and family_doc['limit_bytes']==384*KIB and family_doc['reservations']==FAMILY_RESERVES and family_ref['bytes']<=8*KIB,'held audit family ledger')
    need(family_doc['reserved_total_bytes']==sum(FAMILY_RESERVES.values())==320*KIB and family_doc['full_new_preparation_bound_total_bytes']==sum(family_doc['full_new_preparation_bound'].values())==901833 and family_doc['full_new_preparation_limit_bytes']==MIB and 901833<MIB,'complete declared preparation bound')
    remember('initialization',dict(audit_source=own,reservations=FAMILY_RESERVES))
    paths=dict(plan=HERE/'sift-lightglue-real-plan-1.json',result=OUT/'result.json',outer=WORK/'sift-lightglue-real-1-outer.json',console=WORK/'sift-lightglue-real-1-console.txt',exit=WORK/'sift-lightglue-real-1-exit.txt');external={}
    for key,p in paths.items():
        r=file(p);need(r['sha256']==getattr(args,key+'_sha256'),'root released actual '+key);external[key]=r
    plan=read(external['plan']);parent=read(external['result']);outer=read(external['outer']);exit_code=int(raw(external['exit']).strip())
    for name,binding in plan['source_bindings'].items():file(ROOT/name,dict(path=name,**binding))
    need(plan['source_bindings'].get(SELF.relative_to(ROOT).as_posix())=={k:own[k] for k in ('bytes','sha256')} and plan['source_bindings'].get(path(family_ref).relative_to(ROOT).as_posix())=={k:family_ref[k] for k in ('bytes','sha256')},'actual independent source and ledger held in original plan')
    need(path(plan['python_executable'])==PYTHON,'same pinned Python');file(PYTHON,plan['python_executable'])
    h=helper();checks=commissioning(h);old,private,prior_audit,prior=authority(plan)
    base=[str(PYTHON),'-B','-X','faulthandler','-X'];script=str(HERE/'sift-lightglue-real-run.py');planpath=str(paths['plan'])
    expected_parent=base+['pycache_prefix='+str(OUT/'parent-cache'),script,'--plan',planpath,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT)]
    expected_worker=base+['pycache_prefix='+str(OUT/'worker-cache'),script,'--plan',planpath,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256','ACTUAL_REQUEST_SHA256']
    need(plan['commands']==dict(parent=expected_parent,worker=expected_worker),'literal fixed commands')
    need(outer['command']==replace(expected_parent,external['plan']['sha256']) and outer['plan_sha256']==external['plan']['sha256'] and integer(outer['exit_code']) and outer['exit_code']==exit_code and outer['admissible_parent_exit'] is True,'actual bounded outer/exit association')
    need(type(outer['elapsed_wall_seconds']) in (int,float) and math.isfinite(outer['elapsed_wall_seconds']) and outer['elapsed_wall_seconds']>=0,'finite actual outer')
    need(parent['schema']=='m193c-sift-lightglue-real-run-v1' and parent['implementation_version']==VERSION and same(parent['plan'],external['plan']) and parent['prior_work']==prior and parent['qualification']==QUAL,'actual scoped parent')
    complete=parent['status']==COMPLETE;need(parent['status'] in (COMPLETE,'REFUSED') and exit_code==(0 if complete else 1),'canonical subject/outer agree')
    if 'command' in parent:need(parent['command']==outer['command'],'actual parent argv')
    for k in ('cpu_accounting_complete','original_commission_complete'):need(parent[k] is False,'historical gap not promoted')
    need(parent['old_run_status']=='REFUSED','old failed commission unchanged')
    terminal=own_terminal(OUT,parent,complete);advertisement=terminal_receipt(lines(external['console']),external['result'],parent['status'],complete)
    remember('authority-parent-terminal',dict(status=parent['status'],terminal=terminal,prior_work=prior,commissioning=checks))
    worker=None;worker_ref=None;science=None;pub=[];codec=[];runtime=[];normalized=[];state_summary=None;topology=None;pop=None
    if (OUT/'worker/result.json').exists():
        worker_ref=file(OUT/'worker/result.json');worker=read(worker_ref)
        if parent.get('worker_result') is not None:need(same(parent['worker_result'],worker_ref),'actual worker canonical')
        need(worker['schema']=='m193c-sift-lightglue-real-worker-v1' and worker['implementation_version']==VERSION and same(worker['plan'],external['plan']) and worker['qualification']==QUAL and all(worker[k] is False for k in ('cpu_accounting_complete','original_commission_complete')) and worker['old_run_status']=='REFUSED','actual limited worker')
        need(parent.get('request') is not None and same(worker['request'],parent['request']),'actual worker request')
        request=read(parent['request']);need(path(parent['request'])==OUT/'request.json' and set(request)=={'schema','plan','prior_work'} and request['schema']=='m193c-real-lightglue-request-v1' and same(request['plan'],external['plan']),'closed request')
        typed_work(request['prior_work']);need(worker['prior_work']==request['prior_work'] and all(D(str(request['prior_work'][k]))>=D(str(prior[k])) for k in ALLOW),'worker actual monotone request carry')
        if 'command' in worker:
            need(worker['command']==replace(expected_worker,external['plan']['sha256'],parent['request']['sha256']),'actual worker argv')
            if parent.get('child_observation'):need(read(parent['child_observation'])['command']==worker['command'],'actual launched child command')
        worker_complete=worker['status']==COMPLETE;own_terminal(OUT/'worker',worker,worker_complete)
        terminal_receipt(lines(file(OUT/'worker.log')),worker_ref,worker['status'],worker_complete)
        pop=population(worker);expanded=dict(worker,fits=[] if pop is None else pop['fits'])
        pub=publication_controls(expanded);remember('actual-publication-controls',pub)
        if worker.get('saved_feature_checks'):
            values,cached=exports(h,old);need(worker['saved_feature_checks']==11,'all declared saved features checked')
            codec=codec_controls(worker,cached);remember('saved-exports-codec',dict(export_count=len(values),codec_controls=codec))
            state,state_summary=model_witness(worker,old)
            inputs,normalized,input_ref=input_records(h,worker,old,values)
            if normalized:remember('actual-normalized-values',dict(inputs=input_ref,rows=normalized))
            if inputs and state and pop:
                science=scientific(h,worker,old,private,values,cached,inputs,state,pop,complete)
                remember('science-prefix',dict(controls=science['controls'],real_observed=len(science['real_pairs']),predictions=science['prediction_count'],fits=science['fit_count'],unvisited=science['unvisited']))
        for name in ('runtime_before','runtime_after'):
            if worker.get(name):runtime.append(runtime_snapshot(worker[name],plan,old,True))
        if worker.get('import_guard_final'):
            guard=read(worker['import_guard_final']);need(type(guard['blocked_imports']) is list and type(guard['import_guard_restored']) is bool,'actual guard-exit witness')
            if complete:need(guard['import_guard_restored'] is True,'actual learned guard restored')
        if worker.get('counters'):
            counters=worker['counters'];need(set(counters)==set('images extractions normalizations model_forwards registrar_calls'.split()) and all(integer(x) and x>=0 for x in counters.values()) and counters['images']==counters['extractions']==0 and counters['normalizations']<=9 and counters['model_forwards']<=26 and counters['registrar_calls']<=28,'fixed scientific counters without image work')
        if complete:
            need(worker_complete and parent['error'] is worker['error'] is None and parent['sources_unchanged'] is worker['sources_unchanged'] is True and parent['active_phase']==worker['active_phase']=='complete','complete operational states')
            need(science is not None and len(science['real_pairs'])==23 and len(codec)==10 and len(pub)==7 and all(x['passed'] for x in pub) and len(normalized)==11 and len(runtime)==2,'all fixed prerequisites and complete23 population')
            need(worker['counters']==parent['counters']==dict(images=0,extractions=0,normalizations=9,model_forwards=26,registrar_calls=28) and parent['saved_feature_checks']==worker['saved_feature_checks']==11,'complete actual counters')
            need(parent['inference_observer_nonperturbation']==worker['inference_observer_nonperturbation']=='PASS_THREE_PRIVATE_FORWARDS_AFTER_CALL_SCOPE','actual inference observer scope')
            topology=graph(pop,worker);need(parent['development_outcome']==worker['development_outcome'],'same actual diagnostic decision')
    if parent.get('runtime_final'):runtime.append(runtime_snapshot(parent['runtime_final'],plan,old,False))
    if complete:need(worker is not None and parent.get('runtime_final') and parent.get('child_observation'),'complete parent runtime/Job')
    remember('actual-runtime',runtime)
    inv=inventory();account=accounting(parent,worker,outer,advertisement,inv,complete);remember('resource-accounting',account)
    need(not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'no actual bytecode outputs')
    for p,identity in IDENTITIES.items():need(ident(Path(p).stat(follow_symlinks=False))==identity,'all read evidence/source/runtime identities unchanged')
    elapsed_cpu=time.process_time();elapsed_wall=time.perf_counter()-START
    carry=dict(account['subject_final_work']);carry['cpu_seconds']=float(D(str(carry['cpu_seconds']))+D(str(elapsed_cpu))+D('.25'));carry['wall_seconds']=float(D(str(carry['wall_seconds']))+D(str(elapsed_wall))+D('.5'))
    need(carry['cpu_seconds']<=1200 and carry['wall_seconds']<=1800 and carry['file_bytes']<=4<<30 and carry['metadata_bytes']<=128*MIB,'actual audit carry plus explicit publication allowance inside global caps')
    eligible=complete and account['new_run_cpu_accounting_complete']
    result=dict(schema='m193c-saved-sift-lightglue-real-audit-v1',status='PASS_SAVED_FIXED_REAL_LIGHTGLUE_DIAGNOSTIC_AUDIT',subject_complete=complete,diagnostic_observations_verified=eligible,admission_allowed=False,cpu_accounting_complete=False,new_run_cpu_accounting_complete=account['new_run_cpu_accounting_complete'],old_run_status='REFUSED',original_commission_complete=False,subject_status=parent['status'],worker_status=None if worker is None else worker['status'],external=external,worker_result=worker_ref,audit_source=own,private_baseline=plan['private_baseline'],scientific=science,publication_controls=pub,codec_controls=codec,normalization=normalized,model_state_witness=state_summary,runtime=runtime,graph=topology,accounting=account,actual_final_work=carry,next_wall_seconds=str(D(str(carry['wall_seconds']))),audit_timing=dict(cpu_seconds=elapsed_cpu,wall_seconds=elapsed_wall),audit_publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),audit_family=dict(ledger=family_ref,limit_bytes=384*KIB,reservations=FAMILY_RESERVES),audit_progress=file(PROGRESS),source_bindings_count=len(plan['source_bindings']),scope='Saved actual values plus opaque manifest-bound runtime hashes. No subject/model/fit/image execution or checkpoint read. Actual private inference observer is tested only at the after-call seam. Learned assignment conditions on the whole pair before geometric holdout. All23 scientific refusals can form a complete diagnostic, but operational prefixes are ineligible. Real fitted residual is not physical placement truth, final calibration radius is not refinement membership, and1-Q8 support guard remains unqualified for8-Q8 lattice. No placement/support/merge/SOTA admission. Root must verify actual audit outer and sampled+.5wall publication tail before continuation.')
    data=compact(result);need(len(data)+1<=112*KIB,'bounded final including newline');print(data.decode())

if __name__=='__main__':
    try:main()
    except BaseException:
        try:
            if PROGRESS_OWNED:remember('audit-refused',error=traceback.format_exc())
        except BaseException as exc:print('Partial preservation failed: '+repr(exc),file=sys.stderr)
        raise
