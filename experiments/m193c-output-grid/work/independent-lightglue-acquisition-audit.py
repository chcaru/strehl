"""Prospective opaque acquisition outcome audit. No network, imports of subjects,
checkpoint deserialization, images or model execution. Re-choose filesystem
inventory/prefixes and final outer-inclusive accounting from actual saved evidence.
Run only after root releases the five actual digests. A retained refusal can pass
this audit while remaining inadmissible for the next model stage.
"""
import argparse
from decimal import Decimal as D, ROUND_CEILING
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.parse

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
OUT=HERE/'lightglue-acquisition-1'
MIB=1<<20
RUNNER_PIN=(22326, 'dab882788ebfae4759981c0784251dfac49d8721db024808e19b0f65ea4a6215')
SPEC_PIN=(6893, '9cc108d4714f0d6f2e8addbbaf7c417535ccfaed9a3525d007b01c486467c8b8')
AREA4_AUDIT=(97082,'02c97674a2128fc1d31ba687aa0fe3e98648e5a0604783ad4006166b29814adc')
AREA4_PLAN=(39877,'7c83db049cc869b2428b7e0aa321ece23b91c0b05c6143c3414591479afa41d6')
COMMIT='eb42fee2d71449efb0aa5c10549752b5d75384d8'
PREFIX='https://raw.githubusercontent.com/cvg/LightGlue/'+COMMIT+'/'
PRIOR=dict(cpu_seconds=639.9375,wall_seconds=757.919086,file_bytes=3969447612,metadata_bytes=44246966)
RESERVATION=dict(cpu_seconds=20,wall_seconds=120,file_bytes=64*MIB,metadata_bytes=MIB)
COMPLETE='COMPLETE_SOURCE_AND_CHECKPOINT_ACQUISITION_ONLY'
ASSETS=[
 dict(id='matcher',url=PREFIX+'lightglue/lightglue.py',name='lightglue.py',expected_bytes=None,max_bytes=MIB,kind='text'),
 dict(id='rootsift_reference',url=PREFIX+'lightglue/sift.py',name='sift.py',expected_bytes=None,max_bytes=MIB,kind='text'),
 dict(id='license',url=PREFIX+'LICENSE',name='license.txt',expected_bytes=None,max_bytes=MIB,kind='text'),
 dict(id='readme',url=PREFIX+'README.md',name='readme.md',expected_bytes=None,max_bytes=MIB,kind='text'),
 dict(id='checkpoint',url='https://github.com/cvg/LightGlue/releases/download/v0.1_arxiv/sift_lightglue.pth',name='sift-lightglue.pth',expected_bytes=47632573,max_bytes=47632573,kind='checkpoint')]
HOSTS={'raw.githubusercontent.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}
CONTROL_IDS=['forbidden-url-'+str(i) for i in range(6)]+['prewrite-overrun','checkpoint-json','checkpoint-html','checkpoint-random','duplicate-plan-key']
USED={}

def need(ok,message):
    if not ok:raise ValueError(message)

def integer(v):return type(v) is int

def number(v):return type(v) in (int,float) and math.isfinite(v)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def canonical(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def strict(raw):
    def pairs(rows):
        v={}
        for k,x in rows:need(k not in v,'duplicate JSON key');v[k]=x
        return v
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'nonfinite JSON token'))
    def finite(v):
        if type(v) is float:need(math.isfinite(v),'nonfinite JSON exponent')
        if isinstance(v,dict):
            for x in v.values():finite(x)
        if isinstance(v,list):
            for x in v:finite(x)
    finite(value);return value

def path(r):return (ROOT/r['path']).resolve()

def file(p,expected=None):
    p=Path(p).resolve();python=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
    allowed={'.json','.lock','.md','.py','.rs','.toml','.tsv','.txt','.log'}
    checkpoint=p==OUT/'sift-lightglue.pth'
    need((p.is_relative_to(ROOT) and (p.suffix.lower() in allowed or checkpoint)) or p==python,'only owned metadata or exact opaque checkpoint/Python')
    a=p.stat(follow_symlinks=False);need(not getattr(a,'st_file_attributes',0)&0x400 and a.st_nlink==1 and 0<=a.st_size<=64*MIB,'ordinary bounded file')
    h=hashlib.sha256();size=0
    with p.open('rb') as f:
        while chunk:=f.read(MIB):h.update(chunk);size+=len(chunk);need(size<=64*MIB,'bounded read')
    z=p.stat(follow_symlinks=False)
    fields=lambda st:(st.st_size,st.st_dev,st.st_ino,st.st_mtime_ns,getattr(st,'st_file_attributes',0))
    need(fields(a)==fields(z) and size==a.st_size,'stable read identity')
    r=dict(path=str(p),bytes=size,sha256=h.hexdigest())
    if expected is not None:need(set(expected)=={'path','bytes','sha256'} and path(expected)==p and integer(expected['bytes']) and all(expected[k]==r[k] for k in ('bytes','sha256')),'exact reference identity/extent/hash')
    need(str(p) not in USED or USED[str(p)]==r,'conflicting consumed file');USED[str(p)]=r;return r

def read(r):
    file(path(r),r);need(r['bytes']<=8*MIB,'bounded JSON');raw=path(r).read_bytes();need(sha(raw)==r['sha256'],'same parsed bytes');return strict(raw)

def actual(p):return read(file(p))

def same(a,b):return path(a)==path(b) and all(a[k]==b[k] for k in ('bytes','sha256'))

def url_ok(url):
    try:
        p=urllib.parse.urlsplit(url)
        return p.scheme=='https' and p.hostname in HOSTS and p.port in (None,443) and p.username is None and p.password is None and not p.fragment
    except ValueError:return False

def body_prefix_ok(raw,kind):
    low=raw.lstrip().lower()
    return bool(raw) and not low.startswith((b'<!doctype',b'<html',b'{"',b'["')) and (kind!='checkpoint' or raw.startswith((b'PK\x03\x04',b'\x80\x02',b'\x80\x03',b'\x80\x04',b'\x80\x05')))

def commission():
    bad=['http://github.com/a','https://evil.example/a','https://github.com.evil.example/a','https://user:secret@github.com/a','https://github.com:444/a','https://github.com/a#fragment']
    need(all(not url_ok(u) for u in bad) and all(url_ok(a['url']) for a in ASSETS),'independent URL negative/positive')
    need(url_ok('https://release-assets.githubusercontent.com/a?token=opaque'),'allowed redirect control')
    need(not body_prefix_ok(b'{"error":1}','checkpoint') and not body_prefix_ok(b'<html>bad','checkpoint') and not body_prefix_ok(b'random','checkpoint') and body_prefix_ok(b'PK\x03\x04opaque','checkpoint'),'opaque prefix control power')
    for raw in (b'{"x":1,"x":2}',b'1e999',b'NaN'):
        failed=False
        try:strict(raw)
        except ValueError:failed=True
        need(failed,'strict metadata negative control')
    need(7+1<=8 and not 7+2<=8,'inclusive prewrite arithmetic boundary')
    return ['URL_exact_authority','opaque_magic_not_deserialization','duplicate_and_nonfinite_metadata','inclusive_byte_boundary']

def baseline(plan):
    refs=plan['area4_baseline'];need(set(refs)==set('plan result outer console exit audit'.split()),'six AREA4 refs')
    old,audit,parent,outer=(read(refs[k]) for k in ('plan','audit','result','outer'))
    for k in ('console','exit'):file(path(refs[k]),refs[k])
    need((refs['plan']['bytes'],refs['plan']['sha256'])==AREA4_PLAN and (refs['audit']['bytes'],refs['audit']['sha256'])==AREA4_AUDIT,'immutable AREA4 actual pins')
    need(audit['schema']=='m193c-saved-area-four-audit-v1' and audit['status']=='PASS_SAVED_AREA_FOUR_OUTCOME_AUDIT' and audit['subject_complete'] is True and audit['refused_control'] is None and audit['cpu_accounting_complete'] is True,'completed independent baseline')
    for k in ('plan','result','outer','console','exit'):need(same(refs[k],audit['external'][k]),'baseline audit association')
    worker=read(parent['worker_result']);need(same(parent['worker_result'],audit['worker_result']) and same(parent['plan'],refs['plan']),'baseline worker/plan')
    need(parent['status']==worker['status']=='COMPLETE_AREA_FOUR_DIAGNOSTIC_ONLY' and parent['sources_unchanged'] is worker['sources_unchanged'] is True and parent['error'] is worker['error'] is None and parent['finalization_errors']==worker['finalization_errors']==[],'baseline complete finalization')
    need(len(old['source_bindings'])==210 and parent['source_bindings']==worker['source_bindings']==old['source_bindings'] and all(plan['source_bindings'].get(k)==v for k,v in old['source_bindings'].items()),'all210 historical bindings preserved')
    need(len(worker['features'])==9 and len(worker['pairs'])==23 and len(worker['controls'])==14 and all(c['passed'] is True for c in worker['controls']) and worker['unvisited']==[] and worker['development_outcome']=='ZERO_RETURNED_EDGES_AT_FIXED_AREA4','complete zero-edge AREA4 population')
    final=strict(path(refs['console']).read_bytes().splitlines()[-1]);need(final['work_through_final_checks']==audit['actual_final_work'] and final['status']==parent['status'] and final['cpu_accounting_complete'] is True and final['error'] is None and final['finalization_errors']==[],'baseline final receipt')
    need(integer(outer['exit_code']) and outer['exit_code']==0 and outer['admissible_parent_exit'] is True and path(refs['exit']).read_bytes().strip()==b'0' and outer['command']==parent['command'],'baseline exit/argv')
    wall=D(str(parent['prior_work']['wall_seconds']))+D(str(outer['elapsed_wall_seconds']));need(wall==D(audit['next_wall_seconds']),'exact baseline outer wall')
    prior=dict(audit['actual_final_work']);prior['wall_seconds']=float(wall.quantize(D('.000001'),rounding=ROUND_CEILING));need(prior==PRIOR,'upward rounded old prior')
    delta=[dict(path=k,**v) for k,v in plan['source_bindings'].items() if k not in old['source_bindings']]
    need(len(delta)==len(plan['held_metadata']) and {str(path(r)):(r['bytes'],r['sha256']) for r in delta}=={str(path(r)):(r['bytes'],r['sha256']) for r in plan['held_metadata']},'complete new held metadata delta')
    for r in plan['held_metadata']:file(path(r),r)
    return refs,audit

def inventory():
    rows=[]
    for base,dirs,names in os.walk(OUT,followlinks=False):
        for name in dirs:need(not getattr((Path(base)/name).stat(follow_symlinks=False),'st_file_attributes',0)&0x400,'no reparse directory')
        for name in names:rows.append(file(Path(base)/name))
    return sorted(rows,key=lambda r:r['path'])

def attempts(result):
    rows=[];started=0;complete_count=0;missing_final=None;refused=None;known={'controls.json','worker-result.json','worker.log','result.json'}
    for i,a in enumerate(ASSETS):
        sp=OUT/f'attempt-{i}-start.json';fp=OUT/f'attempt-{i}-final.json';payload=OUT/a['name'];known.update((sp.name,fp.name,payload.name))
        if not sp.exists():
            need(not fp.exists() and not payload.exists(),'no body/final without start');continue
        need(i==started and refused is None and missing_final is None,'contiguous attempts without retry after refusal');started+=1
        start=actual(sp);need(start==dict(id=a['id'],url=a['url'],redirects=[],status='STARTED',bytes=0,sha256=None,error=None),'exact starting attempt')
        body=file(payload) if payload.exists() else None
        if body is not None:need(body['bytes']<=a['max_bytes'],'actual prefix within per-asset cap')
        if not fp.exists():
            missing_final=a['id'];rows.append(dict(asset=a,start=file(sp),final=None,payload=body,status='STARTED_NO_FINAL_RECEIPT'));continue
        final=actual(fp);need(final['id']==a['id'] and final['url']==a['url'] and path(final)==payload,'exact final association')
        need(type(final['redirects']) is list and len(final['redirects'])<=4,'bounded redirects');previous=a['url']
        for redirect in final['redirects']:
            need(set(redirect)=={'status','from_url','to_url'} and redirect['from_url']==previous and redirect['status'] in (301,302,303,307,308) and url_ok(redirect['to_url']),'redirect chain');previous=redirect['to_url']
        if 'final_url' in final:need(final['final_url']==previous and url_ok(final['final_url']),'actual final URL')
        need(number(final['elapsed_wall_seconds']) and final['elapsed_wall_seconds']>=0,'retained attempt time')
        if body is None:need(final['bytes']==0 and final['sha256']==sha(b''),'empty absent prefix')
        else:need(integer(final['bytes']) and final['bytes']==body['bytes'] and final['sha256']==body['sha256'],'actual retained prefix hash/extent')
        done=final['status']=='COMPLETE_OPAQUE_ASSET'
        if done:
            need(final['error'] is None and body is not None and body['bytes']>0 and final['http_status']==200 and 'final_url' in final,'complete response')
            length=final['content_length'];need(length is None or (type(length) is str and length.isascii() and length.isdecimal() and int(length)==body['bytes']),'declared/actual content length')
            need(a['expected_bytes'] is None or body['bytes']==a['expected_bytes'],'checkpoint exact47MiB extent')
            mime=final['content_type'].split(';')[0].strip().lower();need(mime not in ('text/html','application/json'),'no HTTP error mime')
            if a['kind']=='checkpoint':need(mime in ('application/octet-stream','binary/octet-stream','application/x-pytorch'),'checkpoint MIME')
            with payload.open('rb') as stream:prefix=stream.read(64)
            need(body_prefix_ok(prefix,a['kind']),'opaque prefix witness')
            if a['kind']=='text':payload.read_text(encoding='utf8')
            complete_count+=1
        else:need(final['status']=='REFUSED_ASSET' and type(final['error']) is str and bool(final['error']),'named retained asset refusal');refused=a['id']
        rows.append(dict(asset=a,start=file(sp),final=file(fp),payload=body,status=final['status'],http_status=final.get('http_status'),redirects=final['redirects'],final_url=final.get('final_url'),error=final['error']))
    actual_names={r.name for r in OUT.iterdir()};need(actual_names<=known,'only declared intake artifacts')
    projected=[dict(id=a['id'],url=a['url'],final_url=actual(OUT/f'attempt-{i}-final.json')['final_url'],path=r['path'],bytes=r['bytes'],sha256=r['sha256'],expected_bytes=a['expected_bytes']) for i,a in enumerate(ASSETS) if (r:=next((x['payload'] for x in rows if x['asset']['id']==a['id'] and x['status']=='COMPLETE_OPAQUE_ASSET'),None)) is not None]
    for i,got in enumerate(result['assets']):
        want=projected[i];need(got['id']==want['id'] and got['url']==want['url'] and got['final_url']==want['final_url'] and got['expected_bytes']==want['expected_bytes'] and same(got,want),'parent asset prefix')
    return dict(rows=rows,started=started,complete_assets=complete_count,refused_asset=refused,missing_final_asset=missing_final,unvisited=[a['id'] for a in ASSETS[started:]])

def preparation(plan,plan_ref,py):
    refs={k:file(HERE/'work'/('lightglue-acquisition-preparation-1-'+suffix)) for k,suffix in (('outer','outer.json'),('console','console.txt'),('exit','exit.txt'))}
    outer=read(refs['outer']);lines=path(refs['console']).read_bytes().splitlines();need(bool(lines),'preparation terminal stdout');console=strict(lines[-1])
    need(set(outer)==set('command exit_code elapsed_wall_seconds admissible_parent_exit plan plan_sha256'.split()) and integer(outer['exit_code']) and outer['exit_code']==0 and outer['admissible_parent_exit'] is True and same(outer['plan'],plan_ref) and outer['plan_sha256']==plan_ref['sha256'] and path(refs['exit']).read_bytes().strip()==b'0','actual preparation outer/exit/plan')
    need(console['status']=='PREPARED_METADATA_ONLY' and same(console['plan'],plan_ref) and console['source_count']==len(plan['source_bindings']) and console['controls']==[dict(id=k,passed=True) for k in CONTROL_IDS] and console['image_payloads_opened']==0,'actual successful preparation')
    argv=outer['command'];need(type(argv) is list and all(type(x) is str for x in argv) and argv[:2]==[py['path'],'-B'],'preparation Python/bytecode argv')
    rest=argv[2:]
    if rest[:2]==['-X','faulthandler']:rest=rest[2:]
    need(rest[:2]==[str(HERE/'lightglue-acquisition-run.py'),'--prepare'],'preparation exact entry/mode');rest=rest[2:]
    need(len(rest)%2==0 and all(rest[i]=='--source' for i in range(0,len(rest),2)),'only explicit source arguments')
    paths=[(ROOT/rest[i]).resolve() for i in range(1,len(rest),2)];expected=[path(r) for r in plan['held_metadata'] if path(r) not in (HERE/'lightglue-acquisition-run.py',HERE/'lightglue-acquisition-preregister.md')]
    need(len(paths)==len(set(paths)) and set(paths)==set(expected),'complete explicitly prepared additional sources')
    elapsed=outer['elapsed_wall_seconds'];need(number(elapsed) and elapsed>=0,'preparation outer duration')
    # The immutable prepare path imports only stdlib and starts no threads/children.
    # Full outer wall is a conservative CPU bound, not a measured CPU value.
    cpu=max(D(str(elapsed)),D(str(plan['preparation_timing']['cpu_seconds'])))
    return dict(external=refs,command=argv,outer_wall_seconds=str(D(str(elapsed))),cpu_upper_bound_seconds=str(cpu),cpu_scope='max(saved CPU sample, full outer wall), single-thread single-process stdlib preparation; conservative bound')


def main():
    cpu0,wall0=time.process_time(),time.perf_counter();parser=argparse.ArgumentParser()
    for k in ('plan','result','outer','console','exit'):parser.add_argument('--'+k+'-sha256',required=True)
    args=parser.parse_args();commissioned=commission();refs={}
    names=dict(plan=HERE/'lightglue-acquisition-plan-1.json',result=OUT/'result.json',outer=HERE/'work/lightglue-acquisition-1-outer.json',console=HERE/'work/lightglue-acquisition-1-console.txt',exit=HERE/'work/lightglue-acquisition-1-exit.txt')
    for k,p in names.items():refs[k]=file(p);need(refs[k]['sha256']==getattr(args,k+'_sha256'),'actual external '+k)
    plan,result,outer=(read(refs[k]) for k in ('plan','result','outer'));console=strict(path(refs['console']).read_bytes().splitlines()[-1]);exitcode=int(path(refs['exit']).read_bytes().strip())
    need(set(plan)==set('schema source_bindings area4_baseline prior_work reservation assets source_commit asset_release_id upstream_checkpoint_digest upstream_digest_observation python_executable commands held_metadata preparation_timing'.split()),'closed plan')
    need(plan['schema']=='m193c-lightglue-acquisition-plan-v1' and plan['prior_work']==PRIOR and plan['reservation']==RESERVATION and plan['source_commit']==COMMIT and plan['asset_release_id']==131252238 and plan['assets']==ASSETS and plan['upstream_checkpoint_digest'] is None,'literal intake specification')
    need(plan['upstream_digest_observation']=='Official v0.1_arxiv release asset metadata reports digest:null; local hash is an integrity pin, not an independent publisher digest.','no publisher-digest substitution')
    for k,v in plan['source_bindings'].items():file(ROOT/k,dict(path=k,**v))
    for name,pin in (('lightglue-acquisition-run.py',RUNNER_PIN),('lightglue-acquisition-preregister.md',SPEC_PIN)):
        r=file(HERE/name);need((r['bytes'],r['sha256'])==pin,'held subject pin')
    need(any(path(r)==Path(__file__).resolve() for r in plan['held_metadata']),'prospective auditor held in release')
    baseline_refs,baseline_audit=baseline(plan);py=file(path(plan['python_executable']),plan['python_executable']);prepared=preparation(plan,refs['plan'],py)
    need(set(plan['commands'])=={'parent','worker'},'closed commands');pc=[py['path'],'-B','-X','faulthandler',str(HERE/'lightglue-acquisition-run.py'),'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT)];wc=pc+['--worker']
    replace=lambda xs:[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else x for x in xs]
    need(replace(plan['commands']['parent'])==pc==result['command']==outer['command'] and replace(plan['commands']['worker'])==wc,'independent exact argv')
    need(set(outer) in (set('command exit_code elapsed_wall_seconds admissible_parent_exit plan_sha256'.split()),set('command exit_code elapsed_wall_seconds admissible_parent_exit plan_sha256 scope'.split()),set('command exit_code elapsed_wall_seconds admissible_parent_exit plan_sha256 plan'.split())),'closed intake outer')
    need(integer(outer['exit_code']) and outer['exit_code']==exitcode and outer['plan_sha256']==refs['plan']['sha256'] and outer['admissible_parent_exit'] is (exitcode==0),'actual outer/exit')
    if 'plan' in outer:need(same(outer['plan'],refs['plan']),'optional actual plan FileRef')
    need(result['schema']=='m193c-lightglue-acquisition-v1' and same(result['plan'],refs['plan']) and result['prior_work']==PRIOR and result['reservation']==RESERVATION and result['source_commit']==COMMIT and result['asset_release_id']==131252238 and result['upstream_checkpoint_digest'] is None,'actual result association')
    need(same(result['source'],file(HERE/'lightglue-acquisition-run.py')) and result['model_imports']==result['image_payloads_opened']==result['checkpoint_parses']==0,'source and opaque scope witnesses')
    need(console['status']==result['status'] and Path(console['result']).resolve()==OUT/'result.json' and console['charged_work']==result['charged_work'] and console['errors']==result['errors'],'actual terminal association')
    child=result['child'];need(child is not None and child['command']==wc,'owned child receipt')
    log=file(OUT/'worker.log');need(log['bytes']==child['log_bytes'],'actual child log')
    if child.get('log') is not None:need(same(child['log'],log),'log reference')
    account=child['job_accounting'];need(type(account) is dict and child['terminal_job_accounting'] is True and account['active_processes']==0,'terminal CPU ownership')
    need(all(integer(account[k]) for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and account['total_cpu_100ns']==account['total_user_100ns']+account['total_kernel_100ns'],'actual CPU sum')
    controls=actual(OUT/'controls.json');need(controls==[dict(id=k,passed=True) for k in CONTROL_IDS],'actual intake validator controls')
    observed=attempts(result);complete=result['status']==COMPLETE
    worker=None
    if (OUT/'worker-result.json').exists():
        wr=file(OUT/'worker-result.json');worker=read(wr);need(worker['status']==COMPLETE and same(worker['plan'],refs['plan']) and worker['command']==wc and worker['controls']==controls,'worker complete association')
    if complete:
        need(exitcode==child['exit_code']==0 and child['error'] is None and child['cleanup_errors']==[] and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['termination']['attempted'] is False and worker is not None,'complete clean owned child')
        need(observed['started']==observed['complete_assets']==5 and observed['refused_asset'] is observed['missing_final_asset'] is None and len(result['assets'])==5 and result['errors']==[],'complete five opaque assets')
    else:need(result['status']=='REFUSED_ACQUISITION' and exitcode==2 and result['errors'],'retained operational refusal')
    inv=inventory();pre=[r for r in inv if path(r)!=OUT/'result.json'];need(len(pre)==len(result['inventory']),'prepublication inventory length')
    need({str(path(r)):(r['bytes'],r['sha256']) for r in pre}=={str(path(r)):(r['bytes'],r['sha256']) for r in result['inventory']},'independent hidden-inclusive inventory')
    payload=sum(r['bytes'] for r in pre);metadata=sum(r['bytes'] for r in pre if path(r)!=OUT/'sift-lightglue.pth');held=sum(r['bytes'] for r in plan['held_metadata'])+refs['plan']['bytes']
    expected_meta=dict(held=plan['held_metadata'],plan_bytes=refs['plan']['bytes'],held_bytes=held,final_receipt_reserve=256*1024,future_audit_reserve=196*1024,outer_receipt_reserve=8192)
    need(result['metadata_accounting']==expected_meta,'complete reserved metadata accounting')
    need(refs['result']['bytes']<=256*1024 and sum(refs[k]['bytes']+prepared['external'][k]['bytes'] for k in ('outer','console','exit'))<=8192,'reserved final/six-external extent')
    timing=result['timing'];prep=plan['preparation_timing'];need(set(prep)=={'cpu_seconds','wall_seconds'} and 0<=prep['cpu_seconds']<2 and 0<=prep['wall_seconds']<5,'bounded metadata preparation sample')
    need(timing['cpu_seconds']>=account['total_cpu_100ns']/1e7+prep['cpu_seconds'] and timing['wall_seconds']>=prep['wall_seconds'],'parent plus prep and Job time')
    need(result['final_tail_allowance']==dict(cpu_seconds=2,wall_seconds=5) and result['timing_scope']=='Through pre-result sample, plus separately reserved final tail; outer receipt and independent audit must verify tail.','explicit tail semantics')
    reserved=256*1024+196*1024+8192;declared=dict(cpu_seconds=timing['cpu_seconds']+2,wall_seconds=timing['wall_seconds']+5,file_bytes=payload+held+reserved,metadata_bytes=metadata+held+reserved)
    need(result['observed_work_plus_final_receipt_reserve']==declared,'subject sample plus receipt reserve')
    charged={k:float(D(str(PRIOR[k]))+max(D(str(RESERVATION[k])),D(str(declared[k])))) if k.endswith('seconds') else PRIOR[k]+max(RESERVATION[k],declared[k]) for k in RESERVATION}
    need(result['charged_work']==charged,'whole reservation or greater observed work')
    need(number(outer['elapsed_wall_seconds']) and outer['elapsed_wall_seconds']>=0,'actual launcher wall')
    need(number(console['terminal_parent_cpu_seconds']) and number(console['terminal_parent_wall_seconds']) and console['terminal_parent_cpu_seconds']>=0 and console['terminal_parent_wall_seconds']>=0,'later terminal parent samples')
    terminal_cpu=D(str(console['terminal_parent_cpu_seconds']))+D(account['total_cpu_100ns'])/10000000+D(str(prep['cpu_seconds']))
    terminal_wall=D(str(console['terminal_parent_wall_seconds']))+D(str(prep['wall_seconds']))
    need(terminal_cpu>=D(str(timing['cpu_seconds'])) and terminal_wall>=D(str(timing['wall_seconds'])),'terminal samples include result write/hash')
    need(D(str(outer['elapsed_wall_seconds']))>=D(str(console['terminal_parent_wall_seconds'])),'actual outer includes terminal')
    need(child['limits']==dict(wall_seconds=110,cpu_seconds=15,log_bytes=65536,committed_bytes=512*MIB),'fixed owned process caps')
    for r in list(USED.values()):file(path(r),r)
    audit_cpu=time.process_time()-cpu0;audit_wall=time.perf_counter()-wall0
    # Explicit final serialization/publication/report headroom inside the same 2/5 tail.
    # The root launch receipt must later confirm this audit's own outer fits the bound.
    publication=dict(cpu_seconds=0.25,wall_seconds=0.5)
    actual_cpu=D(str(console['terminal_parent_cpu_seconds']))+D(account['total_cpu_100ns'])/10000000+D(prepared['cpu_upper_bound_seconds'])+D(str(audit_cpu))+D(str(publication['cpu_seconds']))
    outer_inclusive=D(str(outer['elapsed_wall_seconds']))+D(prepared['outer_wall_seconds'])+D(str(audit_wall))+D(str(publication['wall_seconds']))
    accounted=dict(cpu_seconds=actual_cpu,wall_seconds=outer_inclusive,file_bytes=D(declared['file_bytes']),metadata_bytes=D(declared['metadata_bytes']))
    final_work={k:float(D(str(PRIOR[k]))+max(D(str(RESERVATION[k])),D(str(declared[k])),accounted[k])) if k.endswith('seconds') else PRIOR[k]+int(max(D(RESERVATION[k]),D(declared[k]),accounted[k])) for k in RESERVATION}
    caps=dict(global_cpu=final_work['cpu_seconds']<=1200,global_wall=final_work['wall_seconds']<=1800,global_files=final_work['file_bytes']<=4*(1<<30),global_metadata=final_work['metadata_bytes']<=128*MIB,reserved_files=declared['file_bytes']<=RESERVATION['file_bytes'],reserved_metadata=declared['metadata_bytes']<=MIB,reserved_cpu=actual_cpu<=20 and declared['cpu_seconds']<=20,reserved_outer_wall=outer_inclusive<=120 and declared['wall_seconds']<=120,final_cpu_tail=actual_cpu<=D(str(declared['cpu_seconds'])),final_wall_tail=outer_inclusive<=D(str(declared['wall_seconds'])),preparation_cpu=D(prepared['cpu_upper_bound_seconds'])<2,preparation_wall=D(prepared['outer_wall_seconds'])<5,child_cpu=account['total_cpu_100ns']/1e7<=15,child_wall=child['wall_seconds']<=110,child_memory=child['job_memory']['peak_job_memory_used_bytes']<=512*MIB,child_log=log['bytes']<=65536)
    admission=complete and all(caps.values())
    out=dict(schema='m193c-saved-lightglue-acquisition-audit-v1',status='PASS_SAVED_LIGHTGLUE_ACQUISITION_OUTCOME_AUDIT',subject_complete=complete,admission_allowed=admission,subject_status=result['status'],subject_errors=result['errors'],external=refs,preparation=prepared,worker_result=None if worker is None else wr,source_commit=COMMIT,asset_release_id=131252238,upstream_checkpoint_digest=None,area4_baseline=baseline_refs,assets=observed,job=child,cpu_accounting_complete=True,actual_final_work=final_work,next_wall_seconds=str(D(str(final_work['wall_seconds']))),subject_charged_work=result['charged_work'],outer_inclusive_seconds=str(outer_inclusive),accounted_intake_and_audit_cpu_upper_bound_seconds=str(actual_cpu),audit_publication_allowance=publication,tail_scope='Includes full preparation outer duration as CPU bound, terminal parent plus Job CPU, intake outer wall, audit own samples and explicit publication allowance; root must verify actual audit launcher wall before next admission.',metadata_accounting=expected_meta,inventory=inv,inventory_total_bytes=sum(r['bytes'] for r in inv),unique_hashed_files=len(USED),caps=caps,commissioning=commissioned,audit_source=file(__file__),audit_timing=dict(cpu_seconds=audit_cpu,wall_seconds=audit_wall),scope='Metadata and opaque file hashes only. No network, imported acquired source, checkpoint parse, images, extraction, matching or model use. HTTPS URL, content type and magic are acquisition checks, not independent publisher authentication, safe deserialization, strict state loading, numerical compatibility or quality. Retained refusal is operational, not a zero-real-map experiment.')
    raw=json.dumps(out,sort_keys=True,allow_nan=False,separators=(',',':')).encode();need(len(raw)+Path(__file__).stat().st_size+8192<=196*1024,'196KiB auditor source/result/report');print(raw.decode())

if __name__=='__main__':main()
