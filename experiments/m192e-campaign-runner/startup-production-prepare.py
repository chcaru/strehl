"""Bounded metadata-only preparation. No subject imports or child launch."""
import time
START=time.monotonic()
import argparse,copy,hashlib,json,os,re,stat,sys
from pathlib import Path
from uuid import UUID
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SELF=Path(__file__).resolve()
PREP=HERE/'startup-production-preparation-1';OUTPUT=HERE/'rehearsal-startup-production-1'
MIB=1024*1024;LIMITS=dict(cpu_seconds=10,wall_seconds=20,file_bytes=8*MIB)
TAIL=dict(cpu_seconds=.25,wall_seconds=.5)
OLD_PLAN=(HERE/'preparation-1/plan.json',6921,'9a8bfcef7da8f6bbf1927adcb99039cd1d679da851deb99367c9a1d836a40d73')
SUPPORT=(HERE/'startup-production-support.py',14013,'bee91a0bad5ae20c2591a5454ffac9a0b12ce0295239ad5fea4b55212b1da670')
REQUIRED={
 'startup-production-run.py','startup-production-verify.py','startup-production-launch.py',
 'startup-production-support.py','startup-production-preregister.md','startup-production-prepare.py',
 'startup-production-preparation.md','independent-startup-production-source-review.md',
 'independent-startup-production-preparation-review.md','startup-production-audit.py',
 'startup-production-audit-preregister.md','independent-startup-production-audit-source-review.md',
 'startup-attribution-run-2.py','startup-attribution-preregister-2.md','startup-attribution-audit-2.py'}
READS={};CREATED={};ACTIVE='ENTRY'
def need(v,message):
 if not v:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':'))+'\n').encode('ascii')
def strict(raw):
 def pairs(items):
  d={}
  for k,v in items:need(k not in d,'duplicate JSON key');d[k]=v
  return d
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
def lexical(value,missing=False):
 need(type(value) is str and len(value)<=1024 and '\x00' not in value,'bounded literal path')
 p=Path(value);need(p.is_absolute() and '..' not in p.parts and str(p)==value,'absolute normalized path spelling')
 for q in reversed([p,*p.parents]):
  if missing and not q.exists():continue
  s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'non-reparse lexical path')
 return p
def shape(r,cap,positive=True):
 need(type(r) is dict and set(r)=={'path','bytes','sha256'},'closed FileRef')
 need(type(r['bytes']) is int and (1 if positive else 0)<=r['bytes']<=cap,'typed bounded extent')
 need(type(r['sha256']) is str and re.fullmatch('[0-9a-fA-F]{64}',r['sha256']) is not None,'typed SHA256')
 return lexical(r['path'])
def identity(s):return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,getattr(s,'st_file_attributes',0),s.st_nlink]
def read(r,cap,role):
 p=shape(r,cap);before=p.lstat();need(stat.S_ISREG(before.st_mode) and before.st_size==r['bytes'] and before.st_nlink>0,'regular declared object')
 if p.is_relative_to(ROOT):need(before.st_nlink==1,'single-link owned evidence')
 with p.open('rb') as f:
  need(identity(os.fstat(f.fileno()))==identity(before),'same opened object')
  raw=f.read(r['bytes']+1);after=os.fstat(f.fileno())
 need(len(raw)==r['bytes'] and sha(raw)==r['sha256'].lower(),'whole declared extent/digest')
 need(identity(before)==identity(after)==identity(p.lstat()),'stable object through bounded read')
 prior=READS.get(str(p));entry=dict(file=dict(r),identity=identity(after),roles=[role])
 if prior:
  need(prior['file']==entry['file'] and prior['identity']==entry['identity'],'repeated-read same identity')
  entry['roles']=sorted(set(prior['roles']+[role]))
 READS[str(p)]=entry;return raw
def ref_tuple(t):return dict(path=str(t[0]),bytes=t[1],sha256=t[2])
def sample():return dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
def envelope(t,added):
 need(type(t) is dict and set(t)=={'cpu_seconds','wall_seconds'} and all(type(v) in (int,float) and not isinstance(v,bool) and v>=0 and v<float('inf') for v in t.values()),'finite preparation timing')
 need(type(added) is int and 0<=added<=2*MIB,'fresh source/review two-MiB slot')
 need(t['cpu_seconds']+TAIL['cpu_seconds']<=10 and t['wall_seconds']+TAIL['wall_seconds']<=20,'preparation plus publication allowance')
def sources_check(rows,old):
 need(type(rows) is list and 1<=len(rows)<=128,'bounded source row population')
 for row in rows:
  p=shape(row,MIB);need(p.is_relative_to(ROOT),'source inside held repository');need(p.suffix.lower() in {'.py','.md','.json'} or p.name=='.gitattributes','source/metadata file kinds only')
 paths=[r['path'] for r in rows];need(len(paths)==len({str(Path(p).resolve()).casefold() for p in paths}),'unique source namespace')
 need(sum(r['bytes'] for r in rows)<=8*MIB,'source intake eight-MiB aggregate')
 present={r['path']:r for r in rows}
 need({str(HERE/n) for n in REQUIRED}<=set(present),'required source/review/checker closure')
 for r in old:need(present.get(r['path'])==r,'unchanged original source binding')
 return present
def namespace_controls(rows,old):
 before=sha(encoded(rows));sources_check(rows,old);tests=[]
 reasons={**dict.fromkeys(('zero','bool-zero','float-extent','negative','oversized'),'typed bounded extent'),
  'malformed-digest':'typed SHA256','duplicate-path':'unique source namespace','missing-required-source':'required source/review/checker closure',
  'changed-old-binding':'unchanged original source binding','cpu-envelope':'preparation plus publication allowance',
  'wall-envelope':'preparation plus publication allowance','source-slot':'fresh source/review two-MiB slot'}
 def reject(name,bad,which='source'):
  error=None
  try:
   if which=='source':sources_check(bad,old)
   else:envelope(*bad)
  except ValueError as e:error=str(e)
  need(error==reasons[name],'specific powered metadata boundary '+name)
  tests.append(dict(id=name,changed_sha256=sha(encoded(bad)),expected_error=error))
 for name,value in [('zero',0),('bool-zero',False),('float-extent',1.0),('negative',-1),('oversized',MIB+1)]:
  bad=copy.deepcopy(rows);bad[-1]['bytes']=value;reject(name,bad)
 bad=copy.deepcopy(rows);bad[-1]['sha256']='z'*64;reject('malformed-digest',bad)
 bad=copy.deepcopy(rows);bad.append(copy.deepcopy(bad[-1]));reject('duplicate-path',bad)
 bad=[copy.deepcopy(r) for r in rows if r['path']!=str(SELF)];reject('missing-required-source',bad)
 bad=copy.deepcopy(rows);bad[0]['sha256']='0'*64;reject('changed-old-binding',bad)
 for name,bad in [('cpu-envelope',(dict(cpu_seconds=10,wall_seconds=0),0)),('wall-envelope',(dict(cpu_seconds=0,wall_seconds=20),0)),('source-slot',(dict(cpu_seconds=0,wall_seconds=0),2*MIB+1))]:reject(name,bad,'envelope')
 envelope(dict(cpu_seconds=0,wall_seconds=0),0);sources_check(rows,old)
 need(sha(encoded(rows))==before,'restored whole positive namespace')
 return dict(schema='m192e-startup-production-preparation-controls-v1',scope='Metadata predicates only; no files corrupted, subjects imported or processes launched.',original_sha256=before,restored_sha256=sha(encoded(rows)),rows=tests)
def write(name,raw,cap):
 need(len(raw)<=cap,'fixed preparation artifact extent '+name);p=PREP/name
 need(p.parent==PREP and not p.exists(),'fresh preparation artifact')
 with p.open('xb') as f:need(f.write(raw)==len(raw),'whole exclusive write');f.flush();os.fsync(f.fileno())
 r=dict(path=str(p),bytes=len(raw),sha256=sha(raw));readback=read(r,cap,'new preparation artifact')
 need(readback==raw,'same-buffer exact new-file readback');CREATED[name]=r;return r
def pinned_json(r,cap,role):return strict(read(r,cap,role))
def arguments():
 p=argparse.ArgumentParser();p.add_argument('--source-sha256',required=True);p.add_argument('--campaign-id',required=True)
 p.add_argument('--source',nargs=3,action='append',default=[],metavar=('PATH','BYTES','SHA256'))
 return p.parse_args()
def main():
 global ACTIVE
 args=arguments();need(len(encoded(list(sys.orig_argv)))<=16384,'fixed actual command extent');need(os.name=='nt' and sys.dont_write_bytecode and Path.cwd().resolve()==ROOT,'exact Windows -B repository preparation')
 need(len(sys.orig_argv)>=3 and sys.orig_argv[1]=='-B' and Path(sys.orig_argv[0]).resolve()==Path(sys.executable).resolve() and sys.orig_argv[2]==str(SELF),'exact interpreter flags and source entry')
 need(str(UUID(args.campaign_id))==args.campaign_id,'canonical new campaign UUID')
 need(not PREP.exists() and not OUTPUT.exists() and not OUTPUT.with_name(OUTPUT.name+'-outer').exists(),'fresh fixed preparation/subject/outer roots')
 own=ref_tuple((SELF,SELF.stat().st_size,args.source_sha256.lower()));ownraw=read(own,MIB,'actual preparer source')
 ACTIVE='HELD_AUTHORITY'
 oldref=ref_tuple(OLD_PLAN);old=pinned_json(oldref,MIB,'exact original plan')
 need(set(old)=={'schema','campaign_id','source_bindings','baseline','python','binary','sidecar','output_directory'} and old['schema']=='m192e-rehearsal-plan-v1','closed unchanged old plan')
 need(args.campaign_id!=old['campaign_id'],'fresh campaign identity')
 oldrows=old['source_bindings'];need(type(oldrows) is list and len(oldrows)==22,'all22 old source bindings')
 supportraw=read(ref_tuple(SUPPORT),MIB,'held support source')
 tree=ast_parse(supportraw);pins=literal_assignment(tree,'PINS')
 extras=[]
 for path,size,digest in args.source:
  need(re.fullmatch('[1-9][0-9]{0,8}',size) is not None,'literal positive source extent');extras.append(dict(path=path,bytes=int(size),sha256=digest.lower()))
 oldpaths={r['path'] for r in oldrows};need(not any(r['path'] in oldpaths for r in extras),'no replacing or duplicating old source namespace')
 rows=[*copy.deepcopy(oldrows),*sorted(extras,key=lambda x:x['path'])];mapping=sources_check(rows,oldrows)
 need(mapping[str(SELF)]==own,'command/source-list exact preparer authority')
 added=sum(r['bytes'] for r in extras);envelope(sample(),added)
 for r in rows:read(r,MIB,'plan source')
 for name in ('run.py','verify.py','launch.py','durable.py','startup-attribution-run-2.py'):
  n,h=pins[name];r=mapping[str(HERE/name)];need(r['bytes']==n and r['sha256'].lower()==h,'exact support-pinned original source')
 startup={};rehearsal={}
 for role,name in [('audit','startup-attribution-2-audit-stdout.bin'),('outer','startup-attribution-2-audit-outer.json'),('exit','startup-attribution-2-audit-exit.txt'),('independent_review','independent-startup-attribution-2-read.md')]:
  n,h=pins[name];startup[role]=ref_tuple((HERE/name,n,h));read(startup[role],128*1024,'startup prerequisite '+role)
 for role,name in [('plan','preparation-1/plan.json'),('verification','rehearsal-1-verification.json'),('independent_review','independent-rehearsal-1-read.md')]:
  n,h=pins[name];rehearsal[role]=ref_tuple((HERE/name,n,h));read(rehearsal[role],128*1024,'rehearsal prerequisite '+role)
 a=pinned_json(startup['audit'],128*1024,'actual startup audit');o=pinned_json(startup['outer'],8192,'actual startup audit outer')
 need(a['status']=='PASS_SAVED_PRIVATE_STARTUP_OUTCOME_AUDIT' and a['commission_pass'] is True and a['subject_complete'] is True and a['whole_intrinsic_identity'] is True and len(a['arms'])==5 and not a['unvisited'],'actual private commission')
 need(o['exit_code']==0 and o['stdout_bytes']==startup['audit']['bytes'] and o['stderr_bytes']==0 and o['elapsed_wall_seconds']<=a['audit_timing']['wall_seconds']+.5 and read(startup['exit'],32,'actual prior exit').strip()==b'0','actual prior audit outer/tail')
 v=pinned_json(rehearsal['verification'],65536,'actual old independent verification')
 need(v['status']=='PASS_BOUND_TERMINAL_REHEARSAL_ONLY' and v['integration_pass'] is False and v['output_nonperturbation'] is True,'old integration failure remains visible')
 need(v['plan']['path']==oldref['path'] and v['plan']['bytes']==oldref['bytes'] and v['plan']['sha256'].lower()==oldref['sha256'],'exact old verification plan')
 need(type(old['baseline']) is dict and set(old['baseline'])=={'summary','independent_review','source_freeze','inputs','record','preserved'},'six unchanged old evidence roles')
 for key,r in old['baseline'].items():read(r,8*MIB,'old baseline metadata '+key)
 need(Path(old['python']['path']).resolve()==Path(sys.executable).resolve(),'same held Python executable')
 for key,cap in [('python',16*MIB),('binary',16*MIB),('sidecar',MIB)]:read(old[key],cap,'opaque held '+key)
 ACTIVE='METADATA_CONTROLS';controls=namespace_controls(rows,oldrows)
 for label in ('wrong-source-digest','wrong-source-extent'):
  bad=dict(own)
  if label=='wrong-source-digest':bad['sha256']=('0' if bad['sha256'][0]!='0' else '1')+bad['sha256'][1:]
  else:bad['bytes']+=1
  error=None
  try:read(bad,MIB,'injected own-source binding fault')
  except ValueError as exc:error=str(exc)
  need(error=={'wrong-source-digest':'whole declared extent/digest','wrong-source-extent':'regular declared object'}[label],'specific actual source-read predicate powered');controls['rows'].append(dict(id=label,changed=bad,expected_error=error))
 need(read(own,MIB,'restored actual source')==ownraw,'whole original source restored')
 controls_raw=encoded(controls);need(len(controls_raw)<=32*1024,'controls output cap')
 plan=dict(schema='m192e-startup-production-plan-v1',campaign_id=args.campaign_id,source_bindings=rows,
   baseline=copy.deepcopy(old['baseline']),python=copy.deepcopy(old['python']),binary=copy.deepcopy(old['binary']),sidecar=copy.deepcopy(old['sidecar']),
   output_directory=str(OUTPUT),startup_baseline=startup,rehearsal_baseline=rehearsal)
 need(len(plan)==10,'literal ten-key new plan');planraw=encoded(plan);need(len(planraw)<=MIB,'new plan cap')
 predicted_plan=dict(path=str(PREP/'plan.json'),bytes=len(planraw),sha256=sha(planraw))
 grant=dict(schema='m192e-startup-production-allocation-v1',plan=predicted_plan,prior_work_preserved=True,
   preparation=LIMITS,subject=dict(cpu_seconds=600,wall_seconds=240,file_bytes=1024*MIB,worker_committed_bytes=8192*MIB,worker_wall_seconds=210),
   launcher=dict(cpu_seconds=5,wall_seconds=255,nested_subject_wall=True,bytes_in_subject=True),
   independent_saved_audit=dict(cpu_seconds=30,wall_seconds=60,file_bytes=16*MIB),
   new_phase=dict(cpu_seconds=645,sequential_wall_seconds=335,file_bytes=1048*MIB),
   scope='Fixed3 N33/W8 startup off/on/placebo, persistence and sampler on; no automatic launch, retry, prior refund or M193c transfer.',
   required_actual_admission='Independent source/auditor reviews, actual preparation outer/exit/stdout association and publication tail, then explicit root release.')
 grantraw=encoded(grant);need(len(grantraw)<=65536,'allocation receipt cap')
 ACTIVE='PREWRITE_RECHECK'
 for entry in list(READS.values()):read(entry['file'],max(entry['file']['bytes'],1),'final held authority recheck')
 envelope(sample(),added)
 inventory=[dict(file=e['file'],identity=e['identity'],roles=e['roles']) for _,e in sorted(READS.items())]
 inventoryraw=encoded(dict(schema='m192e-startup-production-preparation-inventory-v1',reads=inventory,no_subject_imports=True,no_process_launches=True,no_raw_or_raster_reads=True))
 need(len(inventoryraw)<=256*1024,'whole read inventory cap')
 # Fixed reserved extents fit8 MiB before the first directory or output write.
 fixed_slots=dict(fresh_sources_reviews=2*MIB,plan=MIB,grant_inventory=MIB,outer_logs=MIB,independent_checker_source=MIB,other_preparation=2*MIB)
 need(sum(fixed_slots.values())==8*MIB and added<=fixed_slots['fresh_sources_reviews'],'complete nonrefundable preparation ledger')
 PREP.mkdir();ACTIVE='PUBLICATION'
 planref=write('plan.json',planraw,MIB);grantref=write('allocation.json',grantraw,65536)
 controlref=write('controls.json',controls_raw,32768);inventoryref=write('inventory.json',inventoryraw,256*1024)
 for r in rows:read(r,MIB,'after preparation writes source recheck')
 envelope(sample(),added)
 receipt=dict(schema='m192e-startup-production-preparation-v1',status='COMPLETE_METADATA_PREPARATION_ONLY',source=own,plan=planref,
  allocation=grantref,controls=controlref,inventory=inventoryref,actual_command=list(sys.orig_argv),source_counts=dict(old=22,new=len(extras),total=len(rows)),
  source_bytes=dict(new=added,total=sum(r['bytes'] for r in rows)),allocation_slots=fixed_slots,
  baseline_preservation=dict(original_plan=oldref,original_source_rows_unchanged=True,baseline_fields_unchanged=True),
  prospective_launcher_command=[old['python']['path'],'-B',str(HERE/'startup-production-launch.py'),'--plan',planref['path'],'--plan-sha256',planref['sha256']],
  output_directory=str(OUTPUT),subject_executed=False,actual_outer_required=True,preparation_sample=sample(),publication_allowance=TAIL)
 raw=encoded(receipt);need(len(raw)<=256*1024,'whole receipt cap');receiptref=write('receipt.json',raw,256*1024)
 envelope(sample(),added);terminal=dict(schema='m192e-startup-production-preparation-publication-tail-v1',status=receipt['status'],source=own,receipt=receiptref,plan=planref,actual_command=list(sys.orig_argv),sample=sample(),publication_allowance=TAIL,
  created_file_bytes=sum(r['bytes'] for r in CREATED.values()),new_source_bytes=added,actual_outer_required=True,scope='Whole process CPU sample and internal wall through pre-stdout; last stdout write requires actual outer association.')
 raw=encoded(terminal);need(len(raw)<=65536,'bounded final stdout');sys.stdout.buffer.write(raw);sys.stdout.buffer.flush();return 0

def ast_parse(raw):
 import ast
 return ast.parse(raw)
def literal_assignment(tree,name):
 import ast
 matches=[n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
 need(len(matches)==1,'single source literal '+name);return ast.literal_eval(matches[0])
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as exc:
  failure=dict(schema='m192e-startup-production-preparation-failure-v1',status='REFUSED',phase=ACTIVE,error=dict(type=type(exc).__name__,message=str(exc)[-1024:]),sample=sample(),publication_allowance=TAIL,created=dict(CREATED),subject_executed=False,actual_outer_required=True)
  raw=encoded(failure);need(len(raw)<=16384,'bounded failure publication')
  if PREP.exists() and CREATED:
   try:write('failure.json',raw,16384)
   except Exception as publication:sys.stderr.write('failure publication: '+type(publication).__name__+'\n')
  sys.stdout.buffer.write(raw);sys.stdout.buffer.flush();raise SystemExit(1)
