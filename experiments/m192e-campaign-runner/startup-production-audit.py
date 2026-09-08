"""Independent saved production-startup audit. Stdlib; no subject imports or launch.
No RAW payload reads, native APIs, monitor calls, control-suite replay or rendering. Saved output TIFF bytes/pixels are streamed.
"""
import time
START=time.monotonic()
import argparse,ast,copy,hashlib,json,math,os,re,stat,struct,sys,traceback
from pathlib import Path
from uuid import UUID
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SELF=Path(__file__).resolve()
KIB=1024;MIB=1<<20;CAPS=dict(cpu_seconds=30,wall_seconds=60,file_bytes=16*MIB)
COMPLETE='COMPLETE_REHEARSAL_EVIDENCE_ONLY';SCHEDULE=('off','on','placebo')
PHASES=('startup-system-times','startup-memory-status','startup-create-job','startup-stdout-open','startup-stderr-open','startup-popen','startup-assign-job','startup-resume')
FAMILIES=dict(terminal=MIB,trace=61*MIB,metadata=12*MIB,logs=16*MIB,raster=672*MIB,scratch=128*MIB)
SOURCE_PINS={
'startup-production-run.py':(38799,'65509f24417ca6da8792be123facc1f14d893a7f423c465b9ac1e06af7ed47ad'),
'startup-production-verify.py':(30832,'50e35c15162e4598981dd81041d7f37f3b199923564592ec956e36c947009dbc'),
'startup-production-launch.py':(8570,'4aac36c592b74ea20777e7ff3bf94e9b7eb823f4cd9e982c972bb2b31a1fd92b'),
'startup-production-support.py':(14013,'bee91a0bad5ae20c2591a5454ffac9a0b12ce0295239ad5fea4b55212b1da670'),
'startup-production-preregister.md':(15688,'b0868b2b441982896ac210a4ca2d02eb373ad4aa841bfc0e90ea3cc130390716')}
SCOPE='Fixed persistence-on off/on/placebo startup observation triplet. Exact output identity and source-defined sampling disposition; bounded histories, no full campaign, speedup, image-quality or historical-cause admission.'
CONSUMED={};STAGES=[];PROGRESS=None;OUT=None;ALLOWED=set();RAW_PATHS=set()

def need(ok,msg):
 if not ok:raise ValueError(msg)
def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def integer(v):return type(v) is int and v>=0
def number(v):return type(v) in (int,float) and math.isfinite(v) and v>=0
def close(a,b,tolerance=1e-8):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tolerance
def check():need(time.process_time()+.25<=30 and time.monotonic()-START+.5<=60,'audit 30CPU/60wall including reserved final tail')
def parse(b):
 def pairs(rows):
  d={}
  for k,v in rows:need(k not in d,'duplicate JSON key');d[k]=v
  return d
 v=json.loads(b,object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
 def finite(x):
  if type(x) is float:need(math.isfinite(x),'finite JSON float')
  elif type(x) is dict:
   for y in x.values():finite(y)
  elif type(x) is list:
   for y in x:finite(y)
 finite(v);return v

def path_of(v,missing=False):
 p=Path(v);need(p.is_absolute(),'absolute evidence path')
 for q in (p,*p.parents):
  try:s=q.lstat()
  except FileNotFoundError:need(missing,'missing evidence path');continue
  need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024,'no lexical reparse evidence')
 return p.resolve()
def fields(s):return tuple(int(getattr(s,k,0)) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_file_attributes','st_nlink'))
def ref_shape(r):need(type(r) is dict and set(r)=={'path','bytes','sha256'} and type(r['path']) is str and Path(r['path']).is_absolute() and integer(r['bytes']) and type(r['sha256']) is str and re.fullmatch('[a-fA-F0-9]{64}',r['sha256']) is not None,'closed typed FileRef')
def same(a,b):
 ref_shape(a);ref_shape(b);return path_of(a['path'])==path_of(b['path']) and a['bytes']==b['bytes'] and a['sha256'].lower()==b['sha256'].lower()
def file(path,cap,expected=None,expected_hash=None,keep=True):
 check();p=path_of(path);need(p not in RAW_PATHS,'RAW payload reads prohibited');s=p.lstat()
 need(stat.S_ISREG(s.st_mode) and 0<=s.st_size<=cap and (not p.is_relative_to(ROOT) or s.st_nlink==1),'bounded ordinary evidence')
 if expected is not None:ref_shape(expected);need(path_of(expected['path'])==p and expected['bytes']==s.st_size,'exact named file before read')
 h=hashlib.sha256();parts=[];n=0
 with p.open('rb') as f:
  opened=os.fstat(f.fileno());need(fields(s)==fields(opened),'same opened handle')
  while True:
   chunk=f.read(min(MIB,cap-n+1))
   if not chunk:break
   n+=len(chunk);need(n<=cap,'bounded complete read');h.update(chunk)
   if keep:parts.append(chunk)
   check()
  after=os.fstat(f.fileno())
 need(fields(s)==fields(opened)==fields(after)==fields(p.lstat()) and n==s.st_size,'stable whole evidence')
 r=dict(path=str(p),bytes=n,sha256=h.hexdigest())
 if expected is not None:need(r['sha256']==expected['sha256'].lower(),'same exact saved bytes')
 if expected_hash is not None:need(r['sha256']==expected_hash.lower(),'released exact digest')
 need(str(p) not in CONSUMED or CONSUMED[str(p)]==r,'unchanged repeated evidence');CONSUMED[str(p)]=r
 return b''.join(parts) if keep else None,r

def read(r,cap=8*MIB):
 ref_shape(r);b,actual=file(r['path'],cap,expected=r);return parse(b),actual
def read_at(r,p,cap=8*MIB):
 ref_shape(r);need(path_of(r['path'])==path_of(p),'fixed evidence role');return read(r,cap)
def direct(p,cap=8*MIB,digest=None):
 b,r=file(p,cap,expected_hash=digest);return parse(b),r
def remember(name,value):
 if PROGRESS is None:return
 STAGES.append(dict(phase=name,summary=value));b=encode(dict(schema='m192e-production-audit-progress-v1',status='INCOMPLETE_NO_ADMISSION',visited=STAGES))
 need(len(b)<=256*KIB,'progress256KiB');stage=PROGRESS.with_name(PROGRESS.stem+'-stage.json')
 with stage.open('xb') as f:need(f.write(b)==len(b),'whole progress');f.flush();os.fsync(f.fileno())
 os.replace(stage,PROGRESS)

def job(v):
 need(type(v) is dict and all(integer(v.get(k)) for k in ('total_user_100ns','total_kernel_100ns','total_cpu_100ns','active_processes')),'typed Job counters')
 need(v['total_cpu_100ns']==v['total_user_100ns']+v['total_kernel_100ns'],'Job component sum');return v['total_cpu_100ns']/1e7

def authority(args):
 global OUT,RAW_PATHS
 p,pr=direct(args.plan,MIB,args.plan_sha256)
 need(set(p)=={'schema','campaign_id','source_bindings','baseline','python','binary','sidecar','output_directory','startup_baseline','rehearsal_baseline'} and p['schema']=='m192e-startup-production-plan-v1','closed production plan')
 need(str(UUID(p['campaign_id']))==p['campaign_id'],'canonical campaign ID');OUT=path_of(p['output_directory'],missing=True);need(OUT.parent==HERE and OUT.name.startswith('rehearsal-'),'owned production output')
 need(type(p['source_bindings']) is list and len(p['source_bindings'])<=128,'bounded source count')
 refs={}
 for r in p['source_bindings']:
  ref_shape(r);q=path_of(r['path']);need(r['bytes']>0 and str(q) not in refs,'positive unique source namespace');refs[str(q)]=r
 need(sum(r['bytes'] for r in refs.values())<=8*MIB,'aggregate source extent')
 need(str(SELF) in refs and refs[str(SELF)]['sha256'].lower()==args.source_sha256.lower(),'current checker bound in actual plan')
 for name,(n,h) in SOURCE_PINS.items():
  r=refs[str(HERE/name)];need(r['bytes']==n and r['sha256'].lower()==h,'immutable production source '+name)
 need(set(p['baseline'])=={'summary','independent_review','source_freeze','inputs','record','preserved'},'six original baselines')
 for r in refs.values():file(r['path'],8*MIB,expected=r,keep=False)
 for role in ('python','binary','sidecar'):file(p[role]['path'],16*MIB,expected=p[role],keep=False)
 need(path_of(p['python']['path'])==Path(sys.executable).resolve() and sys.dont_write_bytecode and Path.cwd().resolve()==ROOT,'exact interpreter/cwd/-B')
 base={k:read(r)[0] for k,r in p['baseline'].items()};inputs=base['inputs'];need(type(inputs) is list and len(inputs)==33,'fixed input metadata')
 RAW_PATHS={path_of(x['path']) for x in inputs};need(len(RAW_PATHS)==33,'unique native inputs')
 prot=read(refs[str(ROOT/'experiments/M192-m12-certify/protocol.json')])[0]
 need(all(q.parent==path_of(prot['inputs']['33']) for q in RAW_PATHS),'selected input root')
 for x in inputs:
  q=path_of(x['path']);st=q.lstat();need(st.st_size==x['bytes'] and st.st_mtime_ns==x['mtime_ns'],'selected input metadata only')
 need(base['summary']['status']=='NONPERTURBATION_VERIFIED' and base['summary']['completed']==7 and base['independent_review']['status']=='PASS','old admitted sampler record set')
 old,pold=read(p['rehearsal_baseline']['plan']);v,_=read(p['rehearsal_baseline']['verification']);need(v['status']=='PASS_BOUND_TERMINAL_REHEARSAL_ONLY' and v['integration_pass'] is False and v['output_nonperturbation'] is True and same(v['plan'],pold),'old negative integration preserved')
 for k in ('baseline','python','binary','sidecar'):need(p[k]==old[k],'literal immutable original '+k)
 for r in old['source_bindings']:need(str(path_of(r['path'])) in refs and same(r,refs[str(path_of(r['path']))]),'whole old source closure retained')
 need(set(p['startup_baseline'])=={'audit','outer','exit','independent_review'} and set(p['rehearsal_baseline'])=={'plan','verification','independent_review'},'closed independent prerequisite bundles')
 a,_=read(p['startup_baseline']['audit']);o,_=read(p['startup_baseline']['outer']);exitraw,_=file(p['startup_baseline']['exit']['path'],16,expected=p['startup_baseline']['exit'])
 need(a['status']=='PASS_SAVED_PRIVATE_STARTUP_OUTCOME_AUDIT' and a['commission_pass'] is True and a['subject_complete'] is True and a['whole_intrinsic_identity'] is True and len(a['arms'])==5 and a['unvisited']==[],'actual private commission')
 need(exitraw==b'0\n' and o['exit_code']==0 and o['stderr_bytes']==0 and o['stdout_bytes']==p['startup_baseline']['audit']['bytes'] and o['elapsed_wall_seconds']<=a['audit_timing']['wall_seconds']+.5,'prior actual outer/private association')
 for name in ('startup_baseline','rehearsal_baseline'):
  for r in p[name].values():file(r['path'],MIB,expected=r,keep=False)
 # Independent literal held prerequisites, extracted as DATA from the immutable support AST.
 tree=ast.parse(file(HERE/'startup-production-support.py',MIB,expected=refs[str(HERE/'startup-production-support.py')])[0]);pins=ast.literal_eval(next(x.value for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINS' for t in x.targets)))
 for name,(n,h) in pins.items():
  q=HERE/name;actual=CONSUMED.get(str(q.resolve()))
  if actual is None:_,actual=file(q,MIB)
  need(actual['bytes']==n and actual['sha256']==h,'held prerequisite '+name)
 return p,pr,refs,prot,base,v
def source_structure(sources):
    # Re-choose the original AST slices. No compile/exec or subject function call.
    def source(path):
        ref=sources[str(path.resolve())];raw,_=file(ref['path'],MIB,expected=ref);return ast.parse(raw,str(path))
    sampler=source(ROOT/'experiments/m192c-sampler/sampler.py');harness=source(ROOT/'experiments/m12-scorecard/m12-harness.py')
    monitor=next(n for n in sampler.body if isinstance(n,ast.FunctionDef) and n.name=='monitor');assign=next(n for n in harness.body if isinstance(n,ast.FunctionDef) and n.name=='assign_process_to_job')
    boundary=min(n.lineno for n in ast.walk(monitor) if isinstance(n,ast.While))
    mkeys=('h.system_times','h.memory_status','k32.CreateJobObjectW',"(folder / 'stdout.log').open","(folder / 'stderr.log').open",'subprocess.Popen','h.assign_process_to_job')
    akeys=('kernel32.AssignProcessToJobObject','ntdll.NtResumeProcess')
    def counts(node,keys,before):return {k:sum(isinstance(n,ast.Call) and ast.unparse(n.func)==k and n.lineno<before for n in ast.walk(node)) for k in keys}
    mc=counts(monitor,mkeys,boundary);ac=counts(assign,akeys,10**9);need(all(v==1 for v in [*mc.values(),*ac.values()]),'independently selected complete startup call population')
    def rewritten(original,mapping,before):
        node=copy.deepcopy(original)
        for call in list(ast.walk(node)):
            if not isinstance(call,ast.Call) or call.lineno>=before:continue
            key=ast.unparse(call.func)
            if key not in mapping:continue
            if key=='h.assign_process_to_job':call.func=ast.Attribute(value=ast.Name(id='probe',ctx=ast.Load()),attr='assign',ctx=ast.Load())
            else:
                call.args=[ast.Constant(mapping[key]),call.func,*call.args];call.func=ast.Attribute(value=ast.Name(id='probe',ctx=ast.Load()),attr='call',ctx=ast.Load())
        return sha(ast.dump(node,include_attributes=False).encode())
    mm=dict(zip(mkeys,(*PHASES[:6],'assignment-helper')));am=dict(zip(akeys,PHASES[6:]))
    return dict(monitor_original_ast_sha256=sha(ast.dump(monitor,include_attributes=False).encode()),assignment_original_ast_sha256=sha(ast.dump(assign,include_attributes=False).encode()),monitor_changed_ast_sha256=rewritten(monitor,mm,boundary),assignment_changed_ast_sha256=rewritten(assign,am,10**9),monitor_counts=mc,assignment_counts=ac)

def proof(value,kind,expected):
    need(type(value) is dict and value['original_ast_sha256'].lower()==value['restored_ast_sha256'].lower()==expected[kind+'_original_ast_sha256'],'original/restored complete AST hashes')
    counts=expected['monitor_counts' if kind=='monitor' else 'assignment_counts'];need(value['replacement_counts']==value['reverse_replacement_counts']==counts,'complete forward/reverse counts')
    need(value['changed_ast_sha256'].lower()==expected[kind+'_changed_ast_sha256'] and value['changed_ast_sha256'].lower()!=value['original_ast_sha256'].lower(),'complete independently re-derived wrapper AST')

def composition(v):
 need(type(v) is dict and set(v)=={'persistence_mode',*(a+'_'+b for a in ('trace','telemetry') for b in ('original_id','installed_id','captured_id'))} and v['persistence_mode']=='on','fixed persistence composition')
 for k in ('trace','telemetry'):
  x=[v[k+'_'+t] for t in ('original_id','installed_id','captured_id')];need(all(type(i) is int and i>0 for i in x) and x[0]!=x[1]==x[2],'post-install '+k+' identity')
 return True

def startup(v,invref,inv,raw,mode,structure):
 need(v['schema']=='m192e-production-startup-v1' and v['mode']==mode and v['persistence_mode']=='on' and same(v['invocation'],invref),'startup invocation/mode binding');composition(v['composition'])
 need(v['restored'] is True and v['error'] is None and v['original_monitor_start_ns']==raw['start_ns'],'restored original clock')
 first=v['first_observation'];need(type(first) is dict and set(first)=={'poll','start_ns','observed_ns'} and all(integer(x) for x in first.values()) and first['poll']==0,'literal first observation')
 need(raw['start_ns']<=first['start_ns']<=first['observed_ns']<=raw['end_ns'],'first clock bounds')
 need((first['observed_ns']-raw['start_ns'])/1e6<=raw['max_interval_ms_including_final'],'first interval consistent with original maximum')
 for row in raw['trace']['observations']:
  if row['poll']==0:need(all(row[k]==first[k] for k in first),'retained poll0 matches separately saved witness')
 rows=v['phases']
 if mode=='off':need(rows==[] and all(v[k] is None for k in ('actual_popen_argv','actual_popen_flags','child_pid','monitor_ast','assignment_ast')),'startup observer off absence')
 else:
  need([r['phase'] for r in rows]==list(PHASES) and all(r['scope']=='ACTUAL_STARTUP_CALL' and r.get('error') is None for r in rows),'exact eight startup brackets')
  need(v['actual_popen_argv']==inv['argv'] and v['actual_popen_flags']==4 and type(v['child_pid']) is int and v['child_pid']>0,'actual Popen witness')
  matches=[p for p in raw['processes'] if p['pid']==v['child_pid']];need(len(matches)==1 and type(matches[0]['created']) is int,'same PID plus creation identity')
  for r in rows:
   need(all(integer(r.get(k)) for k in ('start_ns','end_ns','thread_cpu_start_ns','thread_cpu_end_ns')) and raw['start_ns']<=r['start_ns']<=r['end_ns']<=first['start_ns'] and r['thread_cpu_start_ns']<=r['thread_cpu_end_ns'],'ordered startup/sample boundaries')
  need(all(a['end_ns']<=b['start_ns'] for a,b in zip(rows,rows[1:])) and rows[5]['returned_pid']==v['child_pid'] and type(rows[2]['native_result']) is int and rows[2]['native_result']>0 and rows[6]['native_result']!=0 and rows[7]['native_result']==0,'successful native call sequence')
  proof(v['monitor_ast'],'monitor',structure);proof(v['assignment_ast'],'assignment',structure)
 spans=[dict(phase=r['phase'],wall_ms=(r['end_ns']-r['start_ns'])/1e6,thread_cpu_ms=(r['thread_cpu_end_ns']-r['thread_cpu_start_ns'])/1e6) for r in rows]
 initial=first['observed_ns']-raw['start_ns'];covered=sum(r['end_ns']-r['start_ns'] for r in rows)
 return dict(first=first,first_interval_ms=initial/1e6,first_sample_duration_ms=(first['observed_ns']-first['start_ns'])/1e6,phase_intervals=spans,startup_call_wall_ms=covered/1e6,unattributed_before_sample_ms=(first['start_ns']-raw['start_ns']-covered)/1e6,pid=v['child_pid'],creation_identity=None if not rows else matches[0]['created'],scope='Disjoint actual call brackets, uncovered time and first sampling query. Waiting is inside wall durations; no product-entry timestamp or historical cause.')

def powered_metadata(original,predicate,faults):
 before=sha(encode(original));predicate(original);rows=[]
 for label,bad in faults:
  err=None
  try:predicate(bad)
  except (ValueError,KeyError,TypeError) as exc:err=type(exc).__name__+': '+str(exc)
  need(err is not None,'independent predicate rejects '+label);rows.append(dict(id=label,changed_sha256=sha(encode(bad)),error=err))
 need(sha(encode(original))==before,'whole independent control restoration');predicate(original)
 return dict(original_sha256=before,restored_sha256=sha(encode(original)),rows=rows,scope='Checker-only metadata copies through actual predicates; no new child or original control-suite replay.')

def checkpoints(record,adapter,raw,p,mode):
 rid='native-n33-w8-'+mode;folder=OUT/'records'/rid/'trace';n=raw['sample_count'];count=n//100
 need(adapter['mode']=='on' and record['persistence_mode']=='on' and adapter['checkpoint_every_observations']==100 and adapter['calls']==n and adapter['telemetry_calls']==(n+9)//10 and adapter['restored'] is True and adapter['latest_telemetry'] is None,'actual fixed persistent adapter')
 need(type(count) is int and count>=0 and adapter['checkpoint_count']==record['checkpoint_count']==count and record['checkpoint_exercised'] is (count>0),'actual exercised or unexercised checkpoint disposition')
 generations=[];observations=[];phase_events=[];incidents=[]
 for i in range(2):
  v,r=direct(folder/('slot-'+str(i)+'.json'),4*MIB);need(r['bytes']==4*MIB,'fixed checkpoint slot size')
  need(set(v)=={'schema','identity','sequence','status','previous_sha256','payload_sha256','payload'} and v['schema']=='m192e-checkpoint-v1' and v['identity']==dict(campaign_id=p['campaign_id'],run_id=rid) and v['status']=='INCOMPLETE','closed checkpoint identity')
  q=v['sequence'];need(type(q) is int and q>=-1 and re.fullmatch('[0-9A-F]{64}',v['previous_sha256']) is not None,'typed checkpoint generation')
  need(v['payload_sha256']==sha(encode(v['payload'])).upper(),'independently sealed payload')
  if q in (-1,0):need(v['previous_sha256']=='0'*64,'initial predecessor')
  if q==-1:need(v['payload'] is None,'unwritten slot');generations.append((q,v,r));continue
  pl=v['payload'];need(set(pl)=={'trace','latest_telemetry','telemetry_calls','last_observation','retained_scope','placebo_label'} and pl['placebo_label'] is False,'whole persisted prefix fields')
  tr=pl['trace'];obs=tr['observations'];nn=(q+1)*100
  need(tr['enabled'] is True and tr['placebo'] is False and 1<=len(obs)<=1000 and len(obs)+tr['dropped']['observations']==nn and obs[-1]['poll']==nn-1 and obs[-1]['observed_ns']==pl['last_observation'],'persisted observation prefix')
  need(pl['telemetry_calls']==(nn+9)//10 and pl['latest_telemetry']['end_ns']<=pl['last_observation'],'persisted latest completed telemetry')
  need(len(tr['events'])<=4096 and len(tr['incidents'])<=32 and all(integer(x) for x in tr['dropped'].values()),'bounded checkpoint tails')
  observations.extend(obs);phase_events.extend(tr['events']);incidents.extend(tr['incidents']);generations.append((q,v,r))
 generations.sort(key=lambda r:r[0]);a,b=generations
 if a[0]>=0:need(b[0]==a[0]+1 and b[1]['previous_sha256']==a[2]['sha256'].upper(),'adjacent linked generations')
 receipt=record['trace_recovery'];need(receipt['status']=='RECOVERABLE_INCOMPLETE' and receipt['errors']==[] and receipt['may_resume'] is False and receipt['may_certify'] is False and receipt['sequence']==b[0]==count-1 and same(receipt['latest'],b[2]) and len(receipt['generations'])==2 and all(same(x,y[2]) for x,y in zip(receipt['generations'],generations)),'actual recovery selects newest valid prefix')
 return dict(count=count,last_sequence=b[0],generations=[x[2] for x in generations],scope='Two retained generations; recovery does not confer resume or completion.'),observations,phase_events,incidents

def trace_read(raw,first,extra_obs,extra_events,extra_incidents):
 start,end=raw['start_ns'],raw['end_ns'];n=raw['sample_count'];tr=raw['trace'];dropped=tr['dropped']
 need(integer(start) and integer(end) and start<end and integer(n) and n>0 and close(raw['wall_seconds'],(end-start)/1e9),'typed monitor time/population')
 need(tr['enabled'] is True and tr['placebo'] is False and tr['injection'] is None and tr['injected'] is False and set(dropped)=={'events','observations','incidents','telemetry'} and all(integer(v) for v in dropped.values()),'unchanged sampling observer mode')
 obs=tr['observations'];need(1<=len(obs)<=1000 and len(obs)+dropped['observations']==n and obs[-1]['poll']==n-1 and len(tr['events'])<=4096 and len(tr['incidents'])<=32,'bounded final observation tail')
 unique={};origins={}
 for group,rows in [('checkpoint',extra_obs),('final',obs)]:
  for row in rows:
   i=row['poll'];need(integer(i) and i<n and integer(row['start_ns']) and integer(row['observed_ns']) and start<=row['start_ns']<=row['observed_ns']<=end,'retained observation interval')
   need(i not in unique or unique[i]==row,'overlapping actual snapshots identical');unique[i]=row;origins.setdefault(i,set()).add(group)
   need(row['private_bytes']==sum(x['private'] for x in row['processes']) and 0<=row['private_bytes']<=raw['peak_private_bytes'],'private bytes are process sum, not working set')
 if 0 in unique:need(all(unique[0][k]==first[k] for k in first),'first witness agrees with snapshot union')
 intervals={i:(r['start_ns'],r['observed_ns']) for i,r in unique.items()};intervals[0]=(first['start_ns'],first['observed_ns']);ordered=sorted(intervals)
 need(all(intervals[b][0]>=intervals[a][1] for a,b in zip(ordered,ordered[1:])),'whole retained union time order')
 gaps=[first['observed_ns']-start]
 for a,b in zip(ordered,ordered[1:]):
  if b==a+1:gaps.append(intervals[b][1]-intervals[a][1])
 events={};incidents=tr['incidents']+extra_incidents
 for x in [*tr['events'],*extra_events,*[e for i in incidents for e in i['context']+i['following']]]:
  key=(x['phase'],x['poll'],x['start_ns']);need(key not in events or events[key]==x,'same event across overlapping stores');events[key]=x
 for x in events.values():
  need(integer(x['start_ns']) and integer(x['end_ns']) and start<=x['start_ns']<=x['end_ns']<=end and close(x['wall_ms'],(x['end_ns']-x['start_ns'])/1e6,1e-6) and x['injected_delay_ms']==0 and number(x['observer_thread_cpu_ms']),'actual unmodified phase intervals')
 finals=[e for e in events.values() if e['phase']=='final-memory'];need(len(finals)==1,'unique observed final-memory bracket')
 last=intervals[n-1][1];lo=finals[0]['end_ns']-last;hi=end-last;need(0<=lo<=hi,'independent final closure bounds');exact=None
 for row in incidents:
  t=row['trigger']
  if t['kind'] in ('observation-gap','final-closure-gap'):
   gap=t['end_ns']-t['start_ns'];need(integer(t['start_ns']) and integer(t['end_ns']) and start<=t['start_ns']<=t['end_ns']<=end and close(t['gap_ms'],gap/1e6,1e-6),'incident exact original gap');gaps.append(gap)
   if t['kind']=='final-closure-gap':need(t['start_ns']==last and lo<=gap<=hi,'final incident lies in independent bracket');exact=gap
 tail=raw['final_interval_ms']*1e6;need(number(tail) and lo-1e-6<=tail<=hi+1e-6,'reported tail within independently observed bounds')
 if exact is not None:need(close(tail,exact,1e-6),'retained exact final closure')
 reported=raw['max_interval_ms_including_final'];lower=max([lo,*gaps])/1e6;need(number(reported) and lower<=reported+1e-8,'retained gap lower bound cannot exceed source maximum')
 complete_intervals=ordered==list(range(n));upper=None;exact_max=None
 if complete_intervals:
  a=max(gaps);upper=max(a,hi)/1e6
  if exact is not None:lower=upper=max(a,exact)/1e6
  elif a>=hi:lower=upper=a/1e6
  need(lower-1e-8<=reported<=upper+1e-8,'complete union determines maximum bounds')
  if lower==upper:exact_max=lower
  missed=0;next_at=start
  for i in range(n-1):
   next_at+=10000000
   if next_at<=intervals[i][0]:skip=(intervals[i][0]-next_at)//10000000+1;missed+=skip;next_at+=skip*10000000
  need(raw['missed_intervals']==missed,'independently reconstructed skipped cadence')
 need(integer(raw['missed_intervals']) and close(raw['coverage'],n/(n+raw['missed_intervals'])),'reported full coverage ratio')
 disposition=reported<=100 and raw['coverage']>=.9;need(raw['sampling_pass'] is disposition,'unchanged100ms/90percent original gate')
 need(sum(tr['phase_counts'].values())==len(tr['events'])+dropped['events'],'whole phase count arithmetic')
 for key in ('sleep-wakeup','job-pids','job-accounting','job-memory'):need(tr['phase_counts'][key]==n,'one native observation phase per poll')
 for key in ('final-poll','final-accounting','final-memory'):need(tr['phase_counts'][key]==1 and any(e['phase']==key for e in events.values()),'observed final phase')
 for e in events.values():need(e['wall_ms']<=tr['phase_max_ms'][e['phase']]+1e-8,'retained event inside source phase maximum')
 need(tr['phase_counts']['telemetry']==(n+9)//10 and len(raw['telemetry'])+dropped['telemetry']==(n+9)//10,'retained telemetry count')
 for key in ('host_start','host_end'):
  h=raw[key];need(all(integer(h[k]) for k in ('kernel_100ns','user_100ns','idle_100ns','total_100ns','busy_100ns')) and h['total_100ns']==h['kernel_100ns']+h['user_100ns'] and h['busy_100ns']==h['total_100ns']-h['idle_100ns'],'independent host counter arithmetic')
 need(close(raw['host_busy_cpu_seconds'],(raw['host_end']['busy_100ns']-raw['host_start']['busy_100ns'])/1e7) and close(raw['product_cpu_seconds'],job(raw['job_accounting'])),'recorded CPU domains')
 for a,b in zip(raw['telemetry'],raw['telemetry'][1:]):
  for k in ('observer_process_cpu_s','observer_thread_cpu_s','product_cpu_100ns'):need(number(a[k]) and b[k]>=a[k],'monotone telemetry CPU')
 for t in raw['telemetry']:
  need(start<=t['start_ns']<=t['end_ns']<=end and t['product_cpu_100ns']<=raw['job_accounting']['total_cpu_100ns'],'telemetry observation range')
  h=t['host'];need(h['total_100ns']==h['kernel_100ns']+h['user_100ns'] and h['busy_100ns']==h['total_100ns']-h['idle_100ns'],'telemetry host counters')
  count=len(t['per_core_cpu_seconds']);need(count>0 and len(t['processor_power'])==count and sorted(x['number'] for x in t['processor_power'])==list(range(count)) and 0<=t['observer_cpu_number']<count and t['power_query_status']==0,'per-core telemetry population')
 return dict(sample_count=n,retained_unique_interval_witnesses=len(intervals),complete_interval_history=complete_intervals,complete_observation_payload_history=len(unique)==n,observation_union_sha256=sha(encode([[i,*intervals[i]] for i in ordered])),reported_sampling_pass=disposition,reported_maximum_ms=reported,retained_gap_lower_ms=lower,complete_maximum_upper_ms=upper,exact_full_maximum_ms=exact_max,final_closure_lower_ms=lo/1e6,final_closure_upper_ms=hi/1e6,reported_final_interval_ms=raw['final_interval_ms'],coverage=raw['coverage'],coverage_reconstructed_from_starts=complete_intervals,missed_intervals=raw['missed_intervals'],dropped=dropped,retained_unique_events=len(events),telemetry_retained=len(raw['telemetry']),independent_failure_seen=(lower>100 or raw['coverage']<.9),scope='Checkpoints and incident contexts union by original identities; absent history stays absent. Source aggregate pass is not an independently reconstructed full history when intervals were evicted.')
def tiff_digest(ref):
 p=path_of(ref['path']);ref_shape(ref);need(p.is_relative_to(OUT/'work'/'outputs') and p.suffix=='.tiff' and 0<ref['bytes']<=224*MIB,'current bounded output TIFF only')
 s=p.lstat();need(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'ordinary owned TIFF');whole=hashlib.sha256();pixel=hashlib.sha256()
 with p.open('rb') as f:
  opened=os.fstat(f.fileno());need(fields(s)==fields(opened),'same TIFF handle')
  def take(offset,n):
   need(integer(offset) and integer(n) and n<=MIB and offset+n<=s.st_size,'bounded TIFF tag read');f.seek(offset);b=f.read(n);need(len(b)==n,'complete TIFF field');return b
  header=take(0,8);need(header[:4]==b'II*\x00','little-endian classic TIFF');at=struct.unpack_from('<I',header,4)[0];need(at>=8,'ordinary IFD offset')
  count=struct.unpack('<H',take(at,2))[0];need(1<=count<=128,'bounded IFD population');entries=take(at+2,12*count);need(take(at+2+12*count,4)==b'\0'*4,'single TIFF page');tags={}
  for i in range(count):
   key,kind,n,pos=struct.unpack_from('<HHII',entries,12*i);need(key not in tags and kind in (1,2,3,4,5,7,9,10,11,12),'unique declared TIFF tag type');width={1:1,2:1,3:2,4:4,5:8,7:1,9:4,10:8,11:4,12:8}[kind];length=n*width;offset=at+2+12*i+8 if length<=4 else pos;b=take(offset,length);tags[key]=list(struct.unpack('<'+{3:'H',4:'I'}[kind]*n,b)) if kind in (3,4) else b
  scalar=lambda k,default=None:tags[k][0] if k in tags else default
  w,h=scalar(256),scalar(257);need([h,w,3]==[4688,7032,3] and tags[258]==[16]*3 and scalar(259)==1 and scalar(262)==2 and scalar(277)==3 and scalar(284,1)==1 and scalar(274,1)==1 and (339 not in tags or tags[339] in ([1],[1,1,1])),'native RGB16 uncompressed active output')
  rows=scalar(278);offsets,counts=tags[273],tags[279];need(type(rows) is int and rows>0 and len(offsets)==len(counts)==math.ceil(h/rows),'complete strip population')
  ranges=[]
  for i,(offset,n) in enumerate(zip(offsets,counts)):
   need(integer(offset) and n==min(rows,h-i*rows)*w*6 and offset+n<=s.st_size,'strip exact pixel extent');ranges.append((offset,offset+n));f.seek(offset);remaining=n
   while remaining:
    b=f.read(min(MIB,remaining));need(b,'whole strip');pixel.update(b);remaining-=len(b);check()
  ordered=sorted(ranges);need(all(a[1]<=b[0] for a,b in zip(ordered,ordered[1:])),'independent nonoverlapping pixel strips')
  f.seek(0);n=0
  while b:=f.read(MIB):whole.update(b);n+=len(b);check()
  after=os.fstat(f.fileno())
 need(fields(s)==fields(opened)==fields(after)==fields(p.lstat()) and n==ref['bytes'] and whole.hexdigest()==ref['sha256'].lower(),'whole same-handle TIFF identity')
 actual=dict(path=str(p),bytes=n,sha256=whole.hexdigest());need(str(p) not in CONSUMED or CONSUMED[str(p)]==actual,'TIFF stable after earlier read');CONSUMED[str(p)]=actual
 return dict(shape=[h,w,3],pixel_sha256=pixel.hexdigest(),output_sha256=whole.hexdigest(),output_bytes=n,strip_count=len(offsets),scope='Streamed original byte/pixel identities; no decode, quality metric or aligned frame.')

def environment_domain(refs):
 source=file(ROOT/'scripts/check-defaults.py',MIB,expected=refs[str(ROOT/'scripts/check-defaults.py')])[0]
 need(sha(source.replace(b'\r\n',b'\n'))=='2c1763df47fc04b082d7969470f347d2a5d8960bb0eadb16f4587b52cb5d013f','held declared environment source')
 declared=set(re.findall(r'"(STREHL_[A-Z0-9_]+)"\s*:\s*Declared\(',source.decode('utf-8')));need(declared,'nonempty actual declaration domain')
 return declared|{'MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','RAYON_NUM_THREADS','STREHL_PYRAMID_WORKERS','STREHL_WARPMAP','STREHL_CACHE_DIR','TEMP','TMP'}

def invocation(v,p,pr,prot,index,mode,input_ref,domain):
 rid='native-n33-w8-'+mode;dest=OUT/'work'/'outputs'/(rid+'.tiff');command=[p['binary']['path'],'stack',prot['inputs']['33'],'--limit','33','--out',str(dest),*prot['configuration']['arguments_after_output']]
 need(v['schema']=='m192e-invocation-v1' and v['campaign_id']==p['campaign_id'] and v['run_id']==rid and type(v['sequence']) is int and v['sequence']==index and v['mode']==mode and v['sampler_mode']=='on' and type(v['limit']) is int and v['limit']==33 and type(v['workers']) is int and v['workers']==8 and v['argv']==command,'fixed complete native invocation')
 need(same(v['source_plan'],pr) and same(v['binary'],p['binary']) and same(v['input_binding'],input_ref),'current invocation authority')
 active=dict(STREHL_PYRAMID_WORKERS='8',STREHL_WARPMAP=str(OUT/'work'/'sidecars'/'n33.warpmap.txt'),STREHL_CACHE_DIR=str(OUT/'work'/'cache'/'native'/'n33'),TEMP=str(OUT/'work'/'monitor'/rid/'temp'),TMP=str(OUT/'work'/'monitor'/rid/'temp'))
 removed=v['cleared_present_variables'];need(type(removed) is list and removed==sorted(set(removed)) and all(type(k) is str and k.upper().startswith(('STREHL_','RAYON_','OMP_','OPENBLAS_','MKL_','NUMEXPR_')) for k in removed),'cleared inherited environment names')
 need(v['environment_domain']==sorted(domain) and set(v['environment'])==domain|set(active)|set(removed) and all(v['environment'][k]==active.get(k) for k in v['environment']) and v['actual_monitor_folder']==str(OUT/'work'/'monitor'/rid),'actual complete environment witness')
 read_at_ref=v['sidecar'];need(path_of(read_at_ref['path'])==OUT/'work'/'sidecars'/'n33.warpmap.txt' and read_at_ref['bytes']==p['sidecar']['bytes'] and read_at_ref['sha256'].lower()==p['sidecar']['sha256'].lower(),'exact copied sidecar');file(read_at_ref['path'],MIB,expected=read_at_ref,keep=False)
 return command

def markers(stack,destination):return [f'frames          : 33 from {stack}','coverage mode   : scale -- as asked, --cover','alignment       : ON (sidecar-override)','33 placed / 0 refused','folded          : 33 / 33 frames','8 execution threads','memory plan     : 4 canonical chunks, 1 reusable frame worker, 1 retained + 1 scratch accumulator','camera RGB -> LINEAR sRGB','Malvar-He-Cutler demosaic','wrote           : '+str(destination),'total           :']

def product_record(ref,p,pr,prot,base,worker,mode,index,structure,domain):
 rid='native-n33-w8-'+mode;folder=OUT/'records'/rid;rec,rr=read_at(ref,folder/'record.json',64*KIB)
 need(rec['schema']=='m192e-record-v1' and rec['campaign_id']==p['campaign_id'] and rec['run_id']==rid and rec['sequence']==index and rec['mode']==mode,'ordered current product record')
 inv,ir=read_at(rec['invocation'],folder/'invocation.json',64*KIB);cmd=invocation(inv,p,pr,prot,index,mode,worker['inputs_before'],domain)
 raw,mr=read_at(rec['monitor'],folder/'monitor.json',8*MIB);need(raw['argv']==cmd and raw['mode']=='on' and (raw['returncode'] is None or type(raw['returncode']) is int),'actual original monitor invocation')
 adapter,ar=read_at(rec['adapter'],folder/'adapter.json',4*KIB);sv,sr=read_at(rec['startup'],folder/'startup.json',16*KIB);need(sv['first_observation']==adapter['first_observation'],'separately stored copies of the same callback witness agree')
 startup_summary=startup(sv,ir,inv,raw,mode,structure);cp,obs,events,incidents=checkpoints(rec,adapter,raw,p,mode);trace=trace_read(raw,sv['first_observation'],obs,events,incidents)
 need(rec['sampling_pass'] is raw['sampling_pass'] and close(rec['coverage'],raw['coverage']) and close(rec['max_interval_ms_including_final'],raw['max_interval_ms_including_final']) and rec['dropped']==raw['trace']['dropped'] and rec['full_trace_retained'] is all(v==0 for v in raw['trace']['dropped'].values()),'current recorded sampling disposition')
 logs={}
 for stream in ('stdout','stderr'):
  origin=rec['log_origins'][stream];copyref=rec['logs'][stream];need(path_of(origin['path'])==OUT/'work'/'monitor'/rid/(stream+'.log') and path_of(copyref['path'])==OUT/'logs'/(rid+'.'+stream+'.log'),'actual/archive log paths')
  a,_=file(origin['path'],2*MIB,expected=origin);b,br=file(copyref['path'],2*MIB,expected=copyref);need(a==b,'whole original/archive stream bytes');logs[stream]=(b,br)
 text=logs['stderr'][0].decode('utf-8');expected={k:k in text for k in markers(prot['inputs']['33'],OUT/'work'/'outputs'/(rid+'.tiff'))};need(rec['terminal_markers']==expected,'literal terminal markers derived from actual stderr')
 natural=raw['returncode']==0 and raw['job_accounting']['active_processes']==0 and raw['job_accounting']['total_terminated_processes']==0;need(rec['natural_complete'] is natural,'actual natural product disposition')
 image=None
 if rec['output'] is not None:
  need(path_of(rec['output']['path'])==OUT/'work'/'outputs'/(rid+'.tiff'),'fixed current TIFF path');image=tiff_digest(rec['output'])
  for k in ('output_sha256','pixel_sha256'):need(image[k]==rec['tiff'][k].lower(),'actual retained TIFF witness '+k)
 identity=image is not None and all(image[k]==base['record']['tiff'][k].lower() for k in ('output_sha256','pixel_sha256'));need(rec['identity_matches'] is identity,'whole baseline nonperturbation disposition')
 operational=natural and all(expected.values()) and adapter['restored'] is True and rec['checkpoint_exercised'] is True
 result=dict(mode=mode,record=rr,monitor=mr,invocation=ir,startup_record=sr,adapter=ar,startup=startup_summary,trace=trace,checkpoint=cp,output=image,output_identity_verified=identity,natural=natural,operational_record_verified=operational,sampling_pass=raw['sampling_pass'],product_job_cpu_seconds=job(raw['job_accounting']),scope='Product Job CPU is descriptive inside the worker Job and must not be added again.')
 return result,(sv,ir,inv,raw,mode),rec

def preserved(worker,p,base):
 before,bref=read(worker['inputs_before']);need(len(before)==33 and len(base['inputs'])==33,'input metadata population')
 for a,b in zip(before,base['inputs']):need(path_of(a['path'])==path_of(b['path']) and a['bytes']==b['bytes'] and a['sha256'].lower()==b['sha256'].lower() and a['mtime_ns']==b['mtime_ns'],'recorded exact original input identity')
 after=None
 if worker.get('inputs_after') is not None:after,aref=read(worker['inputs_after']);need(after==before,'whole recorded before/after native manifests')
 manifest=base['preserved'];need(manifest['schema']=='m192e-prior-output-preservation-v1' and len(manifest['rows'])==7,'old seven outputs')
 expected=[]
 for i,row in enumerate(manifest['rows']):
  need(row['index']==i,'old output order');r,rr=read(row['record']);ref_shape(row['output']);q=path_of(row['output']['path']);need(q==path_of(r['output_path']) and row['output']['sha256'].lower()==r['tiff']['output_sha256'].lower()==base['independent_review']['rows'][i]['output_sha256'].lower(),'independently admitted old output identity')
  _,actual=file(q,224*MIB,expected=row['output'],keep=False);expected.append(dict(index=i,record=row['record'],output=actual))
 seen=[]
 for name in ('preserved_before','preserved_after'):
  if worker.get(name) is None:continue
  v,r=read(worker[name]);need(v['schema']=='m192e-old-output-preservation-v1' and len(v['rows'])==7,'current seven-output preservation witness')
  for a,b in zip(v['rows'],expected):need(a['index']==b['index'] and same(a['record'],b['record']) and same(a['output'],b['output']),'current old-output witness matches actual preserved bytes')
  seen.append(name)
 return dict(input_manifest_before=bref,input_payloads_independently_read=False,input_metadata_currently_checked=33,recorded_inputs_before_after_equal=after is not None,old_outputs_hashed=7,old_output_bytes=sum(r['output']['bytes'] for r in expected),preservation_witnesses=seen,scope='No RAW payload reads. Native payload preservation remains a producer before/after hash witness plus current metadata; old TIFF preservation is independently hashed.')
def publisher(role,pr,released=None):
 folder=OUT/role;values={};refs={}
 for name in ('result.json','first-publication.json','publication-stage.json','emergency-refusal.json'):
  q=folder/name
  if not q.exists():continue
  raw,r=file(q,64*KIB,expected_hash=released if name=='result.json' else None);v=parse(raw);plain=(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
  need(len(raw)==64*KIB and raw==plain+b' '*(64*KIB-len(plain)),'fixed publisher complete padding');values[name]=v;refs[name]=r
 if not values:return None,None,dict(present=False,role=role)
 need('result.json' in values,'canonical retained publisher record');v=values['result.json']
 need(v['schema']=='m192e-'+role+'-v1' and v['status'] in ('REFUSED',COMPLETE),'canonical role/status')
 if v.get('plan') is not None:need(same(v['plan'],pr),'canonical actual plan')
 if v['status']==COMPLETE:need(values.get('first-publication.json')==v and refs['first-publication.json']['sha256']==refs['result.json']['sha256'],'whole durable first-positive identity')
 return v,refs['result.json'],dict(role=role,present=True,status=v['status'],canonical=refs['result.json'],slots=refs,first_positive_preserved=values.get('first-publication.json',{}).get('status')==COMPLETE,scope='Canonical final and actual terminal exit govern; first positive alone cannot admit.')

def advertisements(raw,role):
 values=[]
 for line in raw.splitlines():
  try:v=parse(line)
  except (ValueError,UnicodeError):continue
  if type(v) is dict and v.get('schema')=='m192e-terminal-advertisement-v1' and v.get('role')==role:values.append(v)
 need(len(values)<=1,'at most one actual role advertisement');return values

def tail(role,canonical,cref,pr,command,logref):
 raw,_=file(logref['path'],MIB,expected=logref);adverts=advertisements(raw,role);path=OUT/role/'terminal-tail.json'
 if not path.exists():
  need(canonical['status']!=COMPLETE,'positive canonical requires actual terminal tail')
  return dict(present=False,status='UNOBSERVED_TERMINAL_TAIL',advertisements=len(adverts),scope='Publisher may precede tail construction; no terminal admission.'),None,None
 v,r=direct(path,8192)
 need(r['bytes']==8192 and v['schema']=='m192e-publication-tail-v1' and v['role']==role and same(v['plan'],pr),'fixed original tail role/plan')
 summary=dict(record=r,status=v['status'],phase=v['phase'],advertisements=len(adverts),advertised_status=None if not adverts else adverts[0]['status'])
 if canonical['status']!=COMPLETE or v['status']!=COMPLETE or len(adverts)!=1:return summary,v,None
 a=adverts[0];need(a['status']==COMPLETE and a['complete_cpu_accounting'] is False and a['outer_exit_required'] is True and same(a['plan'],pr) and same(a['canonical'],cref) and same(a['tail'],r),'actual positive advertisement identifies final bytes')
 need(v['phase']=='AFTER_CANONICAL_PUBLICATION' and same(v['canonical'],cref) and v['complete_cpu_accounting'] is False and v['outer_exit_required'] is True and type(v['process_id']) is int and v['process_id']>0 and v['process_id']==a['process_id'],'positive tail association')
 need(canonical['command']==command and canonical['terminal_tail_path']==str(path) and canonical['complete_cpu_accounting'] is False and canonical['outer_exit_required'] is True,'exact conditional terminal command')
 for sample in (v['sample'],a['sample_after_tail']):
  need(all(number(sample.get(k)) for k in ('process_cpu_seconds','latest_owned_job_cpu_seconds','combined_cpu_seconds','wall_seconds')) and sample['combined_cpu_seconds']==sample['process_cpu_seconds']+sample['latest_owned_job_cpu_seconds'] and sample['accounting_error'] is None,'typed publication sample')
 need(all(a['sample_after_tail'][k]>=v['sample'][k] for k in ('process_cpu_seconds','latest_owned_job_cpu_seconds','combined_cpu_seconds','wall_seconds')) and number(v['publication']['cpu_seconds']) and v['publication']['cpu_seconds']<=2 and number(v['publication']['wall_seconds']) and v['publication']['wall_seconds']<=3 and a['sample_after_tail']['wall_seconds']<=(240 if role=='parent' else 210),'ordered finite publication samples')
 return summary,v,a

def external(args,p,pr):
 v,r=direct(args.outer,16*KIB,args.outer_sha256);need(set(v)=={'command','exit_code','elapsed_wall_seconds','stdout_bytes','stderr_bytes','scope'} and type(v['exit_code']) is int and number(v['elapsed_wall_seconds']) and integer(v['stdout_bytes']) and integer(v['stderr_bytes']) and type(v['scope']) is str,'closed actual full-launcher receipt')
 command=[p['python']['path'],'-B',str(HERE/'startup-production-launch.py'),'--plan',str(path_of(args.plan)),'--plan-sha256',args.plan_sha256];need(v['command']==command,'actual full-wrapper command')
 stdout,sr=file(args.stdout,MIB,expected_hash=args.stdout_sha256);stderr,er=file(args.stderr,64*KIB,expected_hash=args.stderr_sha256);exitraw,xr=file(args.exit,32,expected_hash=args.exit_sha256)
 need(sr['bytes']==v['stdout_bytes'] and er['bytes']==v['stderr_bytes'] and exitraw==(str(v['exit_code'])+'\n').encode(),'exact raw external streams/exit')
 advertised=[]
 for line in stdout.splitlines():
  try:x=parse(line)
  except (ValueError,UnicodeError):continue
  if type(x) is dict and set(x)=={'status','result'}:advertised.append(x)
 need(len(advertised)<=1,'at most one launcher advertisement')
 path=OUT.with_name(OUT.name+'-outer')/'outer.json'
 if not path.exists():return dict(receipt=r,stdout=sr,stderr=er,exit=xr,external=v,owned_outer=None,advertisements=len(advertised)),None,None
 owned,orr=direct(path,8192);need(orr['bytes']==8192 and owned['schema']=='m192e-outer-run-v1' and same(owned['plan'],pr),'owned launcher fixed receipt')
 if advertised:need(same(advertised[0]['result'],orr) and advertised[0]['status']==owned['status'],'external stdout identifies actual canonical outer')
 return dict(receipt=r,stdout=sr,stderr=er,exit=xr,external=v,owned_outer=orr,advertisements=len(advertised)),owned,orr

def terminal(p,pr,parent,pref,worker,wref,ext,outer,refs):
 answer=dict(complete_subject_cpu_accounting=False,subject_complete=False,worker_terminal_complete=False,resource_envelope_verified=False,outer=ext['owned_outer'])
 if outer is None:return answer
 command=[p['python']['path'],'-B',str(HERE/'startup-production-run.py'),'--plan',pr['path'],'--plan-sha256',ext['external']['command'][-1]]
 need(outer['command']==command and same(outer['source'],refs[str(HERE/'startup-production-launch.py')]) and (outer['exit_code'] is None or type(outer['exit_code']) is int),'owned parent source/command/typed exit')
 for stream in ('stdout','stderr'):
  if outer.get(stream) is not None:
   need(path_of(outer[stream]['path'])==OUT.with_name(OUT.name+'-outer')/(stream+'.log'),'actual parent log path');file(outer[stream]['path'],MIB,expected=outer[stream],keep=False)
 pt=pa=wt=wa=None
 if parent is not None and outer.get('stdout') is not None:
  desc,pt,pa=tail('parent',parent,pref,pr,command,outer['stdout']);answer['parent_tail']=desc
 child=None;childref=None;childpath=OUT/'child.json'
 if childpath.exists():
  child,childref=direct(childpath,128*KIB);answer['child']=childref;answer['child_status']=child.get('status');answer['child_error']=child.get('error')
  if parent is not None and parent.get('child') is not None:need(same(parent['child'],childref),'parent links actual child receipt')
  if 'command' in child:
   need(child['command']==command+['--worker'] and (child['exit_code'] is None or type(child['exit_code']) is int),'literal worker command/typed exit')
   if child.get('log') is not None:need(path_of(child['log']['path'])==OUT/'worker.log','actual worker log role');file(child['log']['path'],MIB,expected=child['log'],keep=False)
   if worker is not None and child.get('log') is not None:
    desc,wt,wa=tail('worker',worker,wref,pr,command+['--worker'],child['log']);answer['worker_tail']=desc
   account=child.get('job_accounting');cpu=job(account) if account is not None else None;answer['observed_worker_job_cpu_seconds']=cpu
   limits=child.get('limits');configured=child.get('configured_job_limits');memory=child.get('job_memory')
   if limits is not None:need(limits['wall_seconds']==210 and limits['log_bytes']==MIB and limits['committed_bytes']==8*(1<<30) and number(limits['cpu_seconds']) and 0<limits['cpu_seconds']<=600,'fixed current worker envelope')
   if configured is not None:need(configured['committed_bytes']==8*(1<<30) and type(configured['flags']) is int and configured['flags']&0x200 and configured['flags']&0x2000,'actual installed committed-memory flags')
   answer['worker_committed_memory']=memory
   childpositive=(child.get('terminal_job_accounting') is True and child.get('exit_code')==0 and child.get('error') is None and child.get('cleanup_errors')==[] and child.get('termination',{}).get('attempted') is False and account is not None and account['active_processes']==0 and child.get('direct_exit_observed') is True and child.get('pipe_eof_observed') is True and child.get('post_exit_drain',{}).get('completed') is True)
   if childpositive:
    drain=child['post_exit_drain'];previous=-1
    need(type(drain['observations']) is list and 1<=len(drain['observations'])==drain['observation_count'] and number(drain['started_wall_seconds']) and drain['started_wall_seconds']<=drain['ended_wall_seconds']<=child['wall_seconds'],'terminal Job drain times/count')
    for row in drain['observations']:
     c=job(row['accounting']);need(previous<=c<=cpu and drain['started_wall_seconds']<=row['wall_seconds']<=drain['ended_wall_seconds'],'monotone actual drain');previous=c
    need(drain['observations'][0]['accounting']==drain['initial_accounting'] and drain['observations'][-1]['accounting']==drain['last_accounting'] and drain['last_accounting']['active_processes']==0,'drain associations')
    need(limits is not None and configured is not None and memory is not None and all(integer(memory.get(k)) and memory[k]<=limits['committed_bytes'] for k in ('peak_job_memory_used_bytes','peak_process_memory_used_bytes')),'complete installed memory receipt below bound')
    need(child['log']['bytes']==child['log_bytes']<=MIB and number(child['wall_seconds']),'owned worker retained log and whole wall sample')
    if wt is not None and wa is not None:need(wa['sample_after_tail']['process_cpu_seconds']<=cpu,'terminal worker includes its publication CPU');answer['worker_terminal_complete']=worker['status']==COMPLETE
    faults=[]
    for label,key,value in [('wrong-total','total_cpu_100ns',account['total_cpu_100ns']+1),('negative-user','total_user_100ns',-1),('bool-active','active_processes',False)]:
     bad=copy.deepcopy(account);bad[key]=value;faults.append((label,bad))
    answer['independent_job_controls']=powered_metadata(account,job,faults)
 # Terminal CPU is measurable even if another completion predicate failed.
 before,after=outer.get('process_times_before'),outer.get('process_times_after');parent_cpu=None
 if outer.get('terminal_cpu_accounting') is True:
  keys={'created_100ns','exited_100ns','kernel_cpu_100ns','user_cpu_100ns'}
  need(all(type(v) is dict and set(v)==keys and all(integer(i) for i in v.values()) for v in (before,after)) and before['created_100ns']==after['created_100ns']>0 and after['exited_100ns']>=after['created_100ns'] and after['kernel_cpu_100ns']>=before['kernel_cpu_100ns'] and after['user_cpu_100ns']>=before['user_cpu_100ns'],'same retained owned-process handle identity and monotone terminal CPU')
  parent_cpu=(after['kernel_cpu_100ns']+after['user_cpu_100ns'])/1e7;answer['parent_terminal_cpu_seconds']=parent_cpu
 if parent_cpu is not None and child is not None and child.get('terminal_job_accounting') is True and child.get('job_accounting') is not None:
  childcpu=job(child['job_accounting']);combined=parent_cpu+childcpu;answer.update(combined_terminal_cpu_seconds=combined,complete_subject_cpu_accounting=child['job_accounting']['active_processes']==0)
  answer['measured_combined_cpu_within600']=combined<=600
  if pa is not None:need(parent_cpu>=pa['sample_after_tail']['process_cpu_seconds'] and childcpu==pa['sample_after_tail']['latest_owned_job_cpu_seconds']==pt['sample']['latest_owned_job_cpu_seconds'],'terminal CPU includes complete parent publication and child exactly once')
 if outer.get('job_accounting') is not None:answer['outer_job_cpu_cross_bound_seconds']=job(outer['job_accounting'])
 wrapper=outer.get('wrapper_sample');answer['wrapper_sample']=wrapper
 wrapperok=False
 if wrapper is not None:
  need(wrapper['publication_allowance']==dict(cpu_seconds=.25,wall_seconds=.5) and number(wrapper['cpu_seconds']) and number(wrapper['wall_seconds']),'wrapper sampled/tail domains')
  wrapperok=wrapper['cpu_seconds']+.25<=5 and wrapper['wall_seconds']+.5<=255 and ext['external']['elapsed_wall_seconds']<=wrapper['wall_seconds']+.5 and ext['external']['elapsed_wall_seconds']<=255
 outerpositive=(outer['status']=='COMPLETE_OUTER_CAPTURE_ONLY' and outer['phase']=='TERMINAL_CAPTURE' and outer['exit_code']==0 and outer['error'] is None and outer['cleanup_errors']==[] and outer['termination_attempted'] is False and outer['terminal_cpu_accounting'] is True and outer.get('job_accounting',{}).get('active_processes')==0 and ext['external']['exit_code']==0 and ext['external']['stderr_bytes']==0 and ext['advertisements']==1)
 wallok=number(outer.get('elapsed_wall_seconds')) and outer['elapsed_wall_seconds']<=240
 if pa is not None:need(outer['process_id']==pt['process_id'] and outer['elapsed_wall_seconds']>=pa['sample_after_tail']['wall_seconds'],'actual owned parent identity and full wall includes publication')
 answer['resource_envelope_verified']=answer.get('measured_combined_cpu_within600',False) and wallok and wrapperok and answer.get('outer_job_cpu_cross_bound_seconds',601)<=600
 answer['subject_complete']=outerpositive and parent is not None and parent['status']==COMPLETE and worker is not None and worker['status']==COMPLETE and pa is not None and wa is not None and answer['worker_terminal_complete'] and answer['resource_envelope_verified']
 if answer['subject_complete']:need(same(parent['worker'],wref) and parent['error'] is None and parent['full_campaign_certificate'] is False and worker['error'] is None and worker['full_campaign_certificate'] is False,'canonical complete subject association')
 answer['whole_parent_wall_seconds']=outer.get('elapsed_wall_seconds');answer['scope']='Same retained parent process plus contained worker Job counted once; outer Job only cross-check. Committed memory is distinct from RSS. Wrapper CPU remains sampled with reserved tail; external full wall is required.'
 return answer

def inventory():
 rows=[];totals={k:0 for k in FAMILIES}
 for root in (OUT,OUT.with_name(OUT.name+'-outer')):
  if not root.exists():continue
  for directory,dirs,files in os.walk(root,followlinks=False):
   for name in dirs+files:path_of(Path(directory)/name)
   for name in files:
    p=Path(directory)/name;s=p.lstat();need(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'force-visible ordinary output census');rel=p.relative_to(OUT).as_posix() if root==OUT else p.relative_to(root).as_posix()
    if root!=OUT:family='logs' if name.endswith('.log') else 'metadata'
    elif rel.endswith('.tiff'):family='raster'
    elif rel.endswith('.log'):family='logs'
    elif '/trace/' in '/'+rel or rel.endswith('/monitor.json'):family='trace'
    elif rel.startswith(('work/cache/','work/monitor/')):family='scratch'
    elif rel=='child.json' or name in ('result.json','first-publication.json','publication-stage.json','emergency-refusal.json','terminal-tail.json','terminal-tail-stage.json'):family='terminal'
    else:family='metadata'
    totals[family]+=s.st_size;rows.append(dict(path=str(p),bytes=s.st_size,identity=fields(s),family=family))
    need(len(rows)<=4096,'bounded total owned file population')
 return sorted(rows,key=lambda x:x['path']),totals
def current_controls(worker,prior,p,rows,bundles):
 result={}
 if worker.get('controls') is not None:
  oldworker,_=read(prior['worker'],64*KIB);need(same(worker['controls'],oldworker['controls']) and worker['control_scope']=='REUSED_PRIOR_COMMISSION' and worker['reused_prior_commissions']==dict(startup=p['startup_baseline'],rehearsal=p['rehearsal_baseline']),'exact explicit prior commissions')
  old,_=read(worker['controls'],128*KIB);need(len(old)==8 and all(x['passed'] is True for x in old),'eight actual cached storage dispositions');result['prior_storage']=dict(record=worker['controls'],cases=8,replayed=False)
 if worker.get('composition_controls') is not None:
  v,r=read_at(worker['composition_controls'],OUT/'composition-controls.json',16*KIB);orig=v['original'];composition(orig);need(v['original_sha256']==v['restored_sha256']==sha(encode(orig)).upper(),'original/restored actual composition hash')
  mutations=[('preinstall-trace','trace_captured_id',orig['trace_original_id']),('preinstall-telemetry','telemetry_captured_id',orig['telemetry_original_id']),('wrong-persistence','persistence_mode','off')];need(len(v['rows'])==3,'three exact actual composition mutations');faults=[]
  for row,(label,key,value) in zip(v['rows'],mutations):
   bad=copy.deepcopy(orig);bad[key]=value;need(row['id']==label and row['changed']==bad and type(row['expected_error']) is str and row['expected_error'],'exact actual one-field composition fault');faults.append((label,bad))
  result['composition']=dict(record=r,independently_powered=powered_metadata(orig,composition,faults))
  if bundles and bundles[0] is not None:need(orig==bundles[0][0]['composition'],'same actual first arm composition')
 if len(bundles)>1 and bundles[1] is not None:
  sv,ir,inv,raw,mode=bundles[1];structure=source_structure({str(path_of(x['path'])):x for x in p['source_bindings']});faults=[]
  for label in ('invocation','pid','row','clock','first-observation'):
   bad=copy.deepcopy(sv)
   if label=='invocation':bad['invocation']['path']=str(Path(ir['path']).with_name('WRONG.json'))
   elif label=='pid':bad['child_pid']+=1
   elif label=='row':bad['phases'].pop()
   elif label=='clock':bad['original_monitor_start_ns']+=1
   else:bad['first_observation']['poll']=1
   faults.append((label,bad))
  result['startup_association']=powered_metadata(sv,lambda v:startup(v,ir,inv,raw,mode,structure),faults)
  result['actual_on_original_sha256']=sha(encode(sv))
  result['mutated_values']=faults # Removed from final summary after authored-receipt association.
 return result

def authored_receipt(parent,rows,controls,worker):
 if parent is None or parent.get('verification') is None:return dict(present=False,scope='No independent evidence inferred from an absent operational verifier.')
 v,r=read_at(parent['verification'],OUT/'verification.json',128*KIB)
 need(v['schema']=='m192e-rehearsal-verification-v1' and v['status']=='PASS_REHEARSAL_BINDINGS_ONLY' and v['persistence_mode']=='on','current operational verification schema')
 need(len(v['rows'])==len(rows)==3,'actual authored/current population')
 for x,y in zip(v['rows'],rows):
  need(x['mode']==y['mode'] and same(x['record'],y['record']) and x['output_sha256'].lower()==y['output']['output_sha256'] and x['pixel_sha256'].lower()==y['output']['pixel_sha256'] and x['sampling_pass'] is y['sampling_pass'] and close(x['max_interval_ms_including_final'],y['trace']['reported_maximum_ms']) and close(x['coverage'],y['trace']['coverage']),'authored receipt consistent with independently read actual data')
 if 'mutated_values' in controls:
  tests=v['new_startup_controls'];need(tests['original_sha256'].lower()==tests['restored_sha256'].lower()==controls['actual_on_original_sha256'] and len(tests['rows'])==5,'actual original/restored current startup fault identity')
  for row,(label,bad) in zip(tests['rows'],controls['mutated_values']):need(row['id']==label and row['changed']==bad and type(row['expected_error']) is str and row['expected_error'],'whole exact actual one-field startup fault record')
 for k in ('output_nonperturbation','sampling_all_pass','integration_pass'):need(v[k] is worker[k],'authored actual reduction consistency')
 return dict(present=True,record=r,scope='Authored operational receipt checked against saved evidence; its status is not the independent audit conclusion.')

def main():
 global PROGRESS
 ap=argparse.ArgumentParser()
 for name in ('plan','outer','stdout','stderr','exit'):ap.add_argument('--'+name,type=Path,required=True);ap.add_argument('--'+name+'-sha256',required=True)
 ap.add_argument('--source-sha256',required=True);ap.add_argument('--result-sha256');ap.add_argument('--worker-sha256');args=ap.parse_args()
 need(all(re.fullmatch('[a-fA-F0-9]{64}',getattr(args,k)) for k in ('plan_sha256','outer_sha256','stdout_sha256','stderr_sha256','exit_sha256','source_sha256')),'exact typed released digests')
 need(sys.dont_write_bytecode and Path.cwd().resolve()==ROOT,'independent audit -B/cwd')
 file(SELF,128*KIB,expected_hash=args.source_sha256)
 # Fixed separate audit root; mkdir is the first output mutation. No subject root is written.
 header,pr=direct(args.plan,MIB,args.plan_sha256);out=path_of(header['output_directory'],missing=True);need(out.parent==HERE and out.name.startswith('rehearsal-'),'owned actual subject output')
 auditdir=HERE/(out.name+'-independent-audit');need(not auditdir.exists(),'fresh independent saved audit, no retry/overwrite');auditdir.mkdir();PROGRESS=auditdir/'progress.json';final=auditdir/'result.json'
 result=dict(schema='m192e-saved-startup-production-audit-v1',status='INCOMPLETE_INDEPENDENT_AUDIT',subject_complete=False,worker_complete_verified=False,integration_pass=False,complete_subject_cpu_accounting=False,full_campaign_certificate=False,scope=SCOPE,audit_source=CONSUMED[str(SELF)],command=sys.orig_argv,exceptions=[],rows=[],unvisited=list(SCHEDULE),raw_payloads_opened=0)
 initial=None;parent=worker=pref=wref=None
 try:
  p,pr,refs,prot,base,prior=authority(args);result['plan']=pr;result['campaign_id']=p['campaign_id'];remember('authority',dict(plan=pr,sources=len(refs),fixed_modes=list(SCHEDULE)))
  initial,totals=inventory();result['physical_inventory']=dict(files=len(initial),bytes=sum(totals.values()),family_bytes=totals,inventory_sha256=sha(encode(initial)),family_bounds_ok=all(totals[k]<=FAMILIES[k] for k in totals) and sum(totals.values())<=1<<30)
  remember('inventory',result['physical_inventory'])
  ext,outer,orr=external(args,p,pr);result['external']=ext
  parent,pref,pp=publisher('parent',pr,args.result_sha256);worker,wref,wp=publisher('worker',pr,args.worker_sha256);result['publication']=dict(parent=pp,worker=wp)
  need((pref is not None)==(args.result_sha256 is not None) and (wref is not None)==(args.worker_sha256 is not None),'release separately pins every actually present canonical parent/worker')
  if parent is not None:need(parent['campaign_id']==p['campaign_id'],'actual parent campaign')
  if worker is not None:need(worker['campaign_id']==p['campaign_id'],'actual worker campaign')
  result['terminal']=terminal(p,pr,parent,pref,worker,wref,ext,outer,refs);result['complete_subject_cpu_accounting']=result['terminal']['complete_subject_cpu_accounting'];remember('terminal',dict(subject_complete=result['terminal']['subject_complete'],accounting_complete=result['complete_subject_cpu_accounting'],child=result['terminal'].get('child'),observed_cpu=result['terminal'].get('combined_terminal_cpu_seconds')))
  contexts=[];row_records=[];completed=[] if worker is None else worker.get('completed',[])
  need(type(completed) is list and len(completed)<=3,'bounded recorded completed prefix')
  if worker is not None and 'unvisited' in worker:need(worker['unvisited']==list(SCHEDULE[len(completed):]),'source fixed recorded unvisited suffix')
  structure=source_structure(refs);domain=environment_domain(refs);result['source_structure']=structure
  input_ref=None if worker is None else worker.get('inputs_before')
  if input_ref is not None:result['preservation']=preserved(worker,p,base)
  for i,mode in enumerate(SCHEDULE):
   folder=OUT/'records'/('native-n33-w8-'+mode);path=folder/'record.json';retained=[]
   if not path.exists():
    for name in ('invocation.json','adapter.json','startup.json','monitor.json'):
     q=folder/name
     if q.exists():v,r=direct(q,8*MIB if name=='monitor.json' else 64*KIB);retained.append(dict(role=name,record=r,status=v.get('status'),error=v.get('error')))
    if retained:result.setdefault('unlinked_prefix_records',[]).append(dict(mode=mode,records=retained,scope='Available records before publication of a complete arm; no inferred missing result.'))
    contexts.append(None);continue
   _,actual=direct(path,64*KIB);linked=i<len(completed)
   if linked:need(same(completed[i],actual),'literal completed ordered record FileRef')
   context=worker
   if input_ref is None:
    before=OUT/'inputs-before.json';need(before.exists(),'available actual input manifest for retained record');_,ir=direct(before);context=dict(worker or {},inputs_before=ir)
   row,bundle,rec=product_record(actual,p,pr,prot,base,context,mode,i,structure,domain);row['linked_in_canonical_worker']=linked;result['rows'].append(row);row_records.append(rec);contexts.append(bundle);result['unvisited'].remove(mode)
   remember('record-'+mode,dict(record=actual,linked=linked,natural=row['natural'],output_identity=row['output_identity_verified'],sampling=row['sampling_pass'],first_interval_ms=row['startup']['first_interval_ms'],reported_maximum_ms=row['trace']['reported_maximum_ms'],retained_lower_ms=row['trace']['retained_gap_lower_ms']))
  controls={} if worker is None else current_controls(worker,prior,p,result['rows'],contexts);result['current_controls']=controls
  receipt=authored_receipt(parent,result['rows'],controls,worker) if len(result['rows'])==3 else dict(present=False,scope='Full current operational verifier comparison not visited for incomplete prefix.')
  controls.pop('mutated_values',None);result['authored_verifier']=receipt
  full=(worker is not None and worker['status']==COMPLETE and len(completed)==len(result['rows'])==3 and worker.get('active') is None and worker.get('unvisited')==[] and worker.get('error') is None and all(r['operational_record_verified'] and r['linked_in_canonical_worker'] for r in result['rows']) and 'composition' in controls and 'startup_association' in controls and result.get('preservation',{}).get('recorded_inputs_before_after_equal') is True and result['preservation']['preservation_witnesses']==['preserved_before','preserved_after'])
  identities=len(result['rows'])==3 and all(r['output_identity_verified'] for r in result['rows']);sampling=len(result['rows'])==3 and all(r['sampling_pass'] for r in result['rows'])
  if full:
   need(worker['output_nonperturbation'] is identities and worker['sampling_all_pass'] is sampling and worker['integration_pass'] is (identities and sampling),'independently rederived worker fixed reduction')
  subject=result['terminal']['subject_complete'] and full and result['physical_inventory']['family_bounds_ok']
  result.update(status='PASS_SAVED_STARTUP_PRODUCTION_OUTCOME_AUDIT',subject_complete=subject,worker_complete_verified=full and result['terminal']['worker_terminal_complete'],worker_records_verified=full,output_nonperturbation=identities,sampling_all_pass=sampling,integration_pass=subject and identities and sampling,independent_full_interval_histories=full and all(r['trace']['complete_interval_history'] for r in result['rows']))
 except BaseException as exc:
  error=dict(type=type(exc).__name__,message=str(exc)[-2048:],traceback=traceback.format_exc()[-4096:]);result['exceptions'].append(error)
  try:remember('audit-refusal',error)
  except BaseException as e:result['progress_error']=str(e)[-512:]
 try:
  if initial is not None:
   ending,_=inventory();need(ending==initial,'whole owned file identities unchanged during independent read')
  result['audit_timing']=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START);result['audit_publication_allowance']=dict(cpu_seconds=.25,wall_seconds=.5);result['audit_reservation']=CAPS
  result['actual_audit_complete_process_cpu']=False;result['external_audit_receipt_required']=True
  need(result['audit_timing']['cpu_seconds']+.25<=30 and result['audit_timing']['wall_seconds']+.5<=60,'own sampled audit plus final reserves')
 except BaseException as exc:result['exceptions'].append(dict(type=type(exc).__name__,message=str(exc)[-1024:]));result.update(status='INCOMPLETE_INDEPENDENT_AUDIT',subject_complete=False,integration_pass=False)
 payload=encode(result);need(len(payload)<=MIB,'final1MiB independent output bound')
 with final.open('xb') as f:need(f.write(payload)==len(payload),'whole independent final');f.flush();os.fsync(f.fileno())
 need(sys.stdout.buffer.write(payload)==len(payload),'whole raw stdout bytes');sys.stdout.buffer.flush()
 return 0 if result['status']=='PASS_SAVED_STARTUP_PRODUCTION_OUTCOME_AUDIT' else 1
if __name__=='__main__':raise SystemExit(main())
