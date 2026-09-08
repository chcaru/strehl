"""Source-only startup/persistence composition support; no launch on import.
The original sampler, checkpoint implementation and terminal helpers stay bound.
"""
import ast,copy,hashlib,importlib.util,json,sys
from pathlib import Path
import durable as d
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
STARTUP=HERE/'startup-attribution-run-2.py';SAMPLER=ROOT/'experiments/m192c-sampler/sampler.py'
SCHEMA='m192e-startup-production-plan-v1'
PINS={
 'run.py':(37090,'aedfd86f9c5f92ba41b2ad0350a5c1bfbf4bad01bfa543950467aebc2ae3a7e7'),
 'verify.py':(29942,'5cd638a18ce4203be4f1009a5cfabfe6a15c6828f9d9852bb76739fcb935dee9'),
 'launch.py':(8523,'1877773da19ec14e8e2d7378d147b459b8fbadc9eeae61567e290ca912492676'),
 'durable.py':(15166,'41b97a63056332c316daff88c9e172b3c3cdd6de2f36a939ac7eb1bee14fe532'),
 'startup-attribution-run-2.py':(24537,'a6bd95a2f6194e9bc3f0c74c06a7377bdbe5b4c9cebafe8e91adb8b4c5eaac82'),
 'startup-attribution-2-audit-stdout.bin':(30374,'25f27578ea871d87d75f3c35d32fadf60e0a0d771f65be1bede9c05c94f314a9'),
 'startup-attribution-2-audit-outer.json':(1747,'5dba552fbbf69d6e5c63feae0e40b9ede934613f20271ab838c5761425d837cf'),
 'startup-attribution-2-audit-exit.txt':(2,'9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa'),
 'independent-startup-attribution-2-read.md':(11728,'43f05f12bffb454ab202285defae154620446c0699397a2d93ccacbaa1f16cdf'),
 'preparation-1/plan.json':(6921,'9a8bfcef7da8f6bbf1927adcb99039cd1d679da851deb99367c9a1d836a40d73'),
 'rehearsal-1-verification.json':(3086,'a0f4f50e8f2b2c96778966b0714fbe3b6b84b94ace30c11084ba4ea7a784ee10'),
 'independent-rehearsal-1-read.md':(9509,'4d19117d757fd6e814aeba1cbb747f3e53f9b376c2b4d540d6662809b4387ff8')}
PHASES=('startup-system-times','startup-memory-status','startup-create-job','startup-stdout-open','startup-stderr-open','startup-popen','startup-assign-job','startup-resume')
def refs(plan):return {str(Path(x['path']).resolve()):x for x in plan['source_bindings']}
def same(a,b):return d.lexical_path(a['path'])==d.lexical_path(b['path']) and a['bytes']==b['bytes'] and a['sha256'].upper()==b['sha256'].upper()
def pin(ref,name):
 n,h=PINS[name];d.ref_shape(ref);d.need(Path(ref['path']).resolve()==HERE/name and ref['bytes']==n and ref['sha256'].lower()==h,'held prerequisite '+name)
 return d.bytes_binding(ref['path'],n,expected=ref)[0]
def authority(plan):
 d.need(plan['schema']==SCHEMA,'new explicit startup production plan')
 ss=refs(plan)
 for name in ('run.py','verify.py','launch.py','durable.py','startup-attribution-run-2.py'):pin(ss[str(HERE/name)],name)
 for name in ('startup-production-run.py','startup-production-launch.py','startup-production-verify.py','startup-production-support.py','startup-production-preregister.md'):
  d.need(str(HERE/name) in ss,'complete new local source closure');d.check_ref(ss[str(HERE/name)])
 a=plan['startup_baseline'];d.need(type(a) is dict and set(a)=={'audit','outer','exit','independent_review'},'closed actual private commission')
 values={}
 for role,name in [('audit','startup-attribution-2-audit-stdout.bin'),('outer','startup-attribution-2-audit-outer.json'),('exit','startup-attribution-2-audit-exit.txt'),('independent_review','independent-startup-attribution-2-read.md')]:
  raw=pin(a[role],name)
  if role in ('audit','outer'):values[role]=json.loads(raw)
  if role=='exit':d.need(raw.strip()==b'0','actual private audit zero exit')
 audit=values['audit'];outer=values['outer'];d.need(audit['status']=='PASS_SAVED_PRIVATE_STARTUP_OUTCOME_AUDIT' and audit['commission_pass'] is True and audit['subject_complete'] is True and audit['whole_intrinsic_identity'] is True and len(audit['arms'])==5 and not audit['unvisited'],'actual private commissioning')
 d.need(outer['exit_code']==0 and outer['stdout_bytes']==a['audit']['bytes'] and outer['stderr_bytes']==0 and outer['elapsed_wall_seconds']<=audit['audit_timing']['wall_seconds']+.5,'actual commissioning audit publication tail')
 b=plan['rehearsal_baseline'];d.need(type(b) is dict and set(b)=={'plan','verification','independent_review'},'closed existing durable commission')
 for role,name in [('plan','preparation-1/plan.json'),('verification','rehearsal-1-verification.json'),('independent_review','independent-rehearsal-1-read.md')]:pin(b[role],name)
 old=d.read_ref(b['plan']);v=d.read_ref(b['verification']);d.need(v['status']=='PASS_BOUND_TERMINAL_REHEARSAL_ONLY' and v['integration_pass'] is False and v['output_nonperturbation'] is True and same(v['plan'],b['plan']),'prior integration remains failed')
 for key in ('baseline','python','binary','sidecar'):d.need(plan[key]==old[key],'unchanged original product/input authority')
 for x in old['source_bindings']:d.need(str(Path(x['path']).resolve()) in ss and same(ss[str(Path(x['path']).resolve())],x),'unchanged original full source closure')
 worker=d.read_ref(v['worker'],65536);d.need(worker['status']=='COMPLETE_REHEARSAL_EVIDENCE_ONLY' and len(worker['completed'])==3 and not worker['unvisited'],'old complete durable record population')
 return dict(private=a,rehearsal=b,old_worker=worker,old_verification=v)
def cached_storage(plan):
 prior=authority(plan);r=prior['old_worker']['controls'];rows=d.read_ref(r,128*1024);d.need(len(rows)==8 and all(x['passed'] is True for x in rows),'exact cached eight storage commissions');return r

def cached_invocation(plan):
 v=authority(plan)['old_verification'];parent=d.read_ref(v['parent'],65536);actual=d.read_ref(parent['verification'],128*1024)
 d.need(actual['status']=='PASS_REHEARSAL_BINDINGS_ONLY' and len(actual['new_invocation_controls'])==6 and all(x['expected_error'] for x in actual['new_invocation_controls']),'cached invocation negative population')
 return dict(status='REUSED_PRIOR_COMMISSION',verification=parent['verification'],independent_review=plan['rehearsal_baseline']['independent_review'],cases=6)
def cached_job(plan):
 a=authority(plan)['old_verification']['job_counter_controls'];d.need(a['restored'] is True and len(a['rows'])==3 and all(x['expected_error'] for x in a['rows']),'cached Job component controls');return dict(status='REUSED_PRIOR_COMMISSION',verification=plan['rehearsal_baseline']['verification'],cases=3)
def load_startup(plan):
 source=refs(plan)[str(STARTUP)];raw=pin(source,'startup-attribution-run-2.py');name='m192e_production_commissioned_startup'
 spec=importlib.util.spec_from_loader(name,loader=None);module=importlib.util.module_from_spec(spec);module.__file__=str(STARTUP);sys.modules[name]=module
 exec(compile(raw,str(STARTUP),'exec'),module.__dict__);return module

def composition_check(v):
 d.need(type(v) is dict and set(v)=={'persistence_mode',*(k+'_'+x for k in ('trace','telemetry') for x in ('original_id','installed_id','captured_id'))} and v['persistence_mode']=='on','fixed actual persistence mode')
 for k in ('trace','telemetry'):
  values=[v[k+'_'+x] for x in ('original_id','installed_id','captured_id')];d.need(all(type(x) is int and x>0 for x in values) and values[0]!=values[1]==values[2],'actual post-install copied '+k+' identity')
 return True

def composition_controls(original):
 before=d.sha(d.encode(original));composition_check(original);rows=[]
 for name,key,value in [('preinstall-trace','trace_captured_id',original['trace_original_id']),('preinstall-telemetry','telemetry_captured_id',original['telemetry_original_id']),('wrong-persistence','persistence_mode','off')]:
  bad=copy.deepcopy(original);bad[key]=value;error=None
  try:composition_check(bad)
  except ValueError as exc:error=str(exc)
  d.need(error is not None,'actual composition predicate powered');rows.append(dict(id=name,changed=bad,expected_error=error))
 d.need(d.sha(d.encode(original))==before and composition_check(original),'whole restored composition metadata')
 return dict(schema='m192e-startup-composition-controls-v1',original=original,original_sha256=before,rows=rows,restored_sha256=d.sha(d.encode(original)),scope='Metadata copies of actual installed/captured Python identities; no additional child.')

class Composition:
 def __init__(self,plan,sampler,mode,invocation,original_trace,original_telemetry):
  self.plan=plan;self.s=sampler;self.mode=mode;self.inv=invocation;self.probe=None;self.construction=None;self.old_trace=original_trace;self.old_telemetry=original_telemetry
  if mode=='off':self.function=sampler.monitor
  else:
   c=load_startup(plan);self.probe=c.Probe(mode,sampler,refs(plan));self.function,self.construction=c.selected_function(SAMPLER,'monitor',dict(sampler.__dict__,probe=self.probe),c.MONITOR_CALLS,refs(plan)[str(SAMPLER)])
  self.identities=dict(persistence_mode='on',trace_original_id=id(original_trace),trace_installed_id=id(sampler.Trace),trace_captured_id=id(self.function.__globals__['Trace']),telemetry_original_id=id(original_telemetry),telemetry_installed_id=id(sampler.telemetry),telemetry_captured_id=id(self.function.__globals__['telemetry']))
  composition_check(self.identities)
 def finish(self,raw,error,first_observation):
  probe=self.probe;v=dict(schema='m192e-production-startup-v1',mode=self.mode,persistence_mode='on',invocation=self.inv,composition=self.identities,restored=self.s.Trace is self.old_trace and self.s.telemetry is self.old_telemetry,phases=[] if probe is None else probe.rows,actual_popen_argv=None if probe is None else probe.popen_argv,actual_popen_flags=None if probe is None else probe.popen_flags,child_pid=None if probe is None else probe.child_pid,monitor_ast=self.construction,assignment_ast=None if probe is None else probe.assign_ast,original_monitor_start_ns=None if raw is None else raw['start_ns'],first_observation=first_observation,error=error,scope='Actual startup calls only; no moved sampling clock or product-entry timestamp.')
  d.need(len(d.encode(v))<=16384,'fixed complete startup record');return v

def expected_ast(plan):
 raw,_=d.bytes_binding(plan['startup_baseline']['audit']['path'],32768,expected=plan['startup_baseline']['audit']);return json.loads(raw)['source_structure']
def startup_check(value,invref,inv,raw,mode,structure):
 d.need(value['schema']=='m192e-production-startup-v1' and value['mode']==mode and value['persistence_mode']=='on' and same(value['invocation'],invref),'new exact startup/actual invocation association')
 composition_check(value['composition']);d.need(value['restored'] is True and value['error'] is None and value['original_monitor_start_ns']==raw['start_ns'],'actual restoration and unchanged original clock')
 first=value['first_observation'];d.need(type(first) is dict and set(first)=={'poll','start_ns','observed_ns'} and all(type(x) is int and x>=0 for x in first.values()) and first['poll']==0 and raw['start_ns']<=first['start_ns']<=first['observed_ns']<=raw['end_ns'],'actual bounded first-observation witness')
 d.need((first['observed_ns']-raw['start_ns'])/1e6<=raw['max_interval_ms_including_final'],'retained first interval inside original maximum')
 for row in raw['trace']['observations']:
  if row['poll']==0:d.need(all(row[k]==first[k] for k in first),'first observation agrees wherever final tail retains it')
 rows=value['phases']
 if mode=='off':d.need(rows==[] and all(value[k] is None for k in ('actual_popen_argv','actual_popen_flags','child_pid','monitor_ast','assignment_ast')),'actual startup observer off')
 else:
  d.need([x['phase'] for x in rows]==list(PHASES) and all(x['scope']=='ACTUAL_STARTUP_CALL' and x.get('error') is None for x in rows),'all eight actual native/file seams, no delay')
  d.need(value['actual_popen_argv']==inv['argv'] and value['actual_popen_flags']==4 and type(value['child_pid']) is int and value['child_pid']>0,'actual product Popen/argv/suspended flag')
  matches=[x for x in raw['processes'] if x['pid']==value['child_pid']];d.need(len(matches)==1 and type(matches[0]['created']) is int,'actual monitored product creation identity')
  for x in rows:
   d.need(all(type(x[k]) is int and x[k]>=0 for k in ('start_ns','end_ns','thread_cpu_start_ns','thread_cpu_end_ns')) and raw['start_ns']<=x['start_ns']<=x['end_ns']<=first['start_ns'] and x['thread_cpu_start_ns']<=x['thread_cpu_end_ns'],'actual bracket clocks')
  d.need(all(a['end_ns']<=b['start_ns'] for a,b in zip(rows,rows[1:])) and rows[5]['returned_pid']==value['child_pid'] and rows[2]['native_result']>0 and rows[6]['native_result']!=0 and rows[7]['native_result']==0,'original startup order and successful native calls')
  for key,which in [('monitor_ast','monitor'),('assignment_ast','assignment')]:
   proof=value[key];d.need(proof['original_ast_sha256'].lower()==proof['restored_ast_sha256'].lower()==structure[which+'_original_ast_sha256'] and proof['changed_ast_sha256'].lower()==structure[which+'_changed_ast_sha256'] and proof['replacement_counts']==proof['reverse_replacement_counts']==structure[which+'_counts'],'unchanged commissioned complete AST transformation')
 return dict(mode=mode,startup_complete=True,original_start_ns=raw['start_ns'],phase_count=len(rows),first_observation=first,persistence_mode='on',scope='Phase wall includes waiting; product-entry time and historical cause remain unknown.')
def binding_controls(value,invref,inv,raw,mode,structure):
 before=d.sha(d.encode(value));startup_check(value,invref,inv,raw,mode,structure);rows=[]
 for label in ('invocation','pid','row','clock','first-observation'):
  bad=copy.deepcopy(value)
  if label=='invocation':bad['invocation']['path']=str(Path(invref['path']).with_name('WRONG.json'))
  elif label=='pid':bad['child_pid']+=1
  elif label=='row':bad['phases'].pop()
  elif label=='clock':bad['original_monitor_start_ns']+=1
  else:bad['first_observation']['poll']=1
  error=None
  try:startup_check(bad,invref,inv,raw,mode,structure)
  except (ValueError,KeyError) as exc:error=str(exc)
  d.need(error is not None and d.sha(d.encode(value))==before,'powered current startup association');rows.append(dict(id=label,changed=bad,expected_error=error))
 startup_check(value,invref,inv,raw,mode,structure);return dict(original_sha256=before,restored_sha256=d.sha(d.encode(value)),rows=rows)
