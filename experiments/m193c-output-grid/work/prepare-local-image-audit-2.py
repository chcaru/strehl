"""Bounded metadata preparation for audit2; no runtime import or saved-array read."""
import time
START=time.monotonic()
import argparse,hashlib,json,math,os,stat,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/m193c-output-grid';WORK=HERE/'work';SELF=Path(__file__).resolve()
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
KIB=1024;MIB=1<<20;EMPTY=hashlib.sha256(b'').hexdigest();SEEN={}
ORIGINAL_PLAN=dict(path='experiments/m193c-output-grid/local-image-probe-plan-1.json',bytes=476283,sha256='337ee76493feb15f14982d14fdb6b6148bc76ba108a9c0d77ba51ca25a6e66c1')
OLD_AUDIT_PINS={
 'source':('.py',67132,'17dc9cdedde7221f598f7ef9fd37672ad703257173a927717208d2f24deb13ee'),
 'ledger':('-ledger.json',2032,'db2673ea4f04103b8a82970f9bd060ad436d496ddeadceebcf00da538629fb54'),
 'protocol':('-preregister.md',9467,'40aae52cbfbe63fc76960665fd7e76e2b6115b58247afb54a1a1ebd16e37a019'),
 'result':('.json',165322,'38fca0e7096f259ac70956f479b0321e2a25ebde37e1f8fe370f3a9cc4ef913d'),
 'progress':('-progress.json',65536,'41e1b6dd8fc1a7cbef93bd0455969871734bd5191f1528b56b856805481bcae8'),
 'outer':('-outer.json',1890,'dd5db525ca0aab8b1586b2388f7d7bfcc3bc17959f65d0b226910dacce841f97'),
 'stdout':('-stdout.bin',165323,'93367784f650bb350f0f42633cc34a755debc1ce1025ae13b6ab10e048d6fb00'),
 'stderr':('-stderr.bin',0,EMPTY),
 'exit':('-exit.txt',2,'4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865')}
PREP=dict(cpu_seconds=5,wall_seconds=10,file_bytes=MIB,metadata_bytes=MIB)
AUDIT=dict(cpu_seconds=25,wall_seconds=30,file_bytes=3*MIB,metadata_bytes=3*MIB)
PRIOR=dict(cpu_seconds=1558.443678,wall_seconds=1561.9278447999966,file_bytes=4136370969,metadata_bytes=145110035)
CAPS=dict(cpu_seconds=1600,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=160*MIB)
SUPPLEMENT=PYTHON.parent/'Lib/site-packages/_distutils_hack/__init__.py'
SUPPLEMENT_PIN=dict(bytes=6002,sha256='4bf5b0bc8f8af7ce7096e96f7167cf4f776f2cc0983f5c8f876ca780b3a67781')
GRANT=WORK/'local-image-audit-recovery-2.json';RECEIPT=WORK/'local-image-audit-2-preparation.json';FAILURE=WORK/'local-image-audit-2-preparation-failure.json'
REQUIRED=('independent-local-image-probe-audit-2.py','independent-local-image-probe-audit-2-ledger.json',
 'independent-local-image-probe-audit-2-preregister.md','independent-local-image-probe-audit-2-source-review.md',
 'prepare-local-image-audit-2.py','local-image-audit-2-preparation.md','independent-local-image-audit-2-preparation-review.md')
COMPONENTS=dict(helper_recipe_review=64*KIB,grant=64*KIB,receipt=16*KIB,failure=8*KIB,outer_console_exit=16*KIB)
CONTEXT=dict(phase='bootstrap',path=None);LAST=None

def need(ok,message):
 if not ok:raise ValueError(message)
def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def sample():return dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
def check():
 global LAST
 s=sample();LAST=dict(sample=s,cpu_with_tail_pass=s['cpu_seconds']+.25<=5,wall_with_tail_pass=s['wall_seconds']+.5<=10,**CONTEXT)
 need(LAST['cpu_with_tail_pass'] and LAST['wall_with_tail_pass'],'current metadata preparation cap with publication tail')
def path(value):return (ROOT/value).resolve()
def identity(s):return tuple(int(getattr(s,k,0)) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_file_attributes','st_nlink'))
def regular(s,p):need(stat.S_ISREG(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024 and s.st_nlink>=1 and (not p.is_relative_to(WORK) or s.st_nlink==1),'ordinary bound file identity')
def ancestry(p):
 p=Path(os.path.abspath(p))
 for parent in (p.parent,*p.parent.parents):
  s=parent.lstat();need(stat.S_ISDIR(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024 and not stat.S_ISLNK(s.st_mode),'ordinary lexical ancestry')
 return p
def ref(p,raw):return dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),bytes=len(raw),sha256=sha(raw))
def read(p,cap,pin=None,empty=False):
 p=ancestry(p);CONTEXT['path']=str(p);check();before=p.lstat();regular(before,p)
 need(type(cap) is int and (0 if empty else 1)<=before.st_size<=cap,'bounded pre-read extent')
 if pin is not None:
  need(type(pin) is dict and set(pin)=={'path','bytes','sha256'} and type(pin['bytes']) is int and path(pin['path'])==p and before.st_size==pin['bytes'],'typed same-path expected FileRef')
 with p.open('rb') as f:
  first=os.fstat(f.fileno());regular(first,p);need(identity(before)==identity(first),'same opened identity');raw=f.read(before.st_size+1);after=os.fstat(f.fileno())
 named=p.lstat();regular(named,p);need(identity(first)==identity(after)==identity(named) and len(raw)==before.st_size,'same complete buffer identity')
 actual=ref(p,raw)
 if pin is not None:need(actual==pin,'exact expected metadata/runtime bytes')
 if not raw:need(empty and actual['sha256']==EMPTY,'explicit exact old empty stderr only')
 if str(p) in SEEN:need(SEEN[str(p)]==(identity(named),actual),'unchanged repeat metadata read')
 SEEN[str(p)]=(identity(named),actual);check();return raw,actual
def strict(raw):
 def pairs(xs):
  d={}
  for k,v in xs:need(k not in d,'duplicate JSON key');d[k]=v
  return d
 def finite(v):
  if type(v) is float:need(math.isfinite(v),'finite JSON')
  elif type(v) is dict:
   for x in v.values():finite(x)
  elif type(v) is list:
   for x in v:finite(x)
 v=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)));finite(v);return v
def write(p,raw,cap):
 need(type(raw) is bytes and len(raw)<=cap and not p.exists(),'bounded exclusive metadata write')
 with p.open('xb') as f:
  need(f.write(raw)==len(raw),'full metadata write');f.flush();os.fsync(f.fileno());first=os.fstat(f.fileno());regular(first,p)
 before=p.lstat();regular(before,p);need(identity(before)==identity(first),'same written name')
 with p.open('rb') as f:
  opened=os.fstat(f.fileno());need(identity(opened)==identity(first),'same metadata readback object');observed=f.read(len(raw)+1);after=os.fstat(f.fileno())
 named=p.lstat();regular(named,p);need(identity(opened)==identity(after)==identity(named) and observed==raw,'exact stable metadata readback')
 return ref(p,observed)

def namespace_contract(original,sources,runtime):
 for values,cap in ((sources,256*KIB),(runtime,64*KIB)):
  need(type(values) is dict and 1<=len(values)<=32,'finite recovery namespace')
  for key,pin in values.items():
   need(type(key) is str and type(pin) is dict and set(pin)=={'bytes','sha256'} and type(pin['bytes']) is int and 0<pin['bytes']<=cap and type(pin['sha256']) is str and len(pin['sha256'])==64 and all(c in '0123456789abcdef' for c in pin['sha256']),'positive recovery namespace')
  need(sum(v['bytes'] for v in values.values())<=cap,'bounded whole recovery namespace')
 previous={path(k) for space in ('source_bindings','runtime_bindings','runtime_empty_bindings') for k in original[space]}
 current={path(k) for k in sources};extra={path(k) for k in runtime}
 need(len(current)==len(sources) and len(extra)==len(runtime) and not current&previous,'new source identity disjoint')
 need(extra=={SUPPLEMENT} and not extra&(previous|current),'exact checker-only supplementary identity')
 return True

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source',action='append',nargs=3,required=True);args=parser.parse_args()
 need(Path.cwd().resolve()==ROOT and Path(sys.executable).resolve()==PYTHON and sys.dont_write_bytecode and not sys._xoptions,'exact metadata interpreter and cwd')
 expected=[str(PYTHON),'-B',str(SELF)]
 for row in args.source:expected+=['--source',*row]
 need(sys.orig_argv==expected,'exact metadata preparation argv')
 audit_outputs=[WORK/('independent-local-image-probe-audit-2'+s) for s in ('.json','-progress.json','-progress-stage.json','-outer.json','-stdout.bin','-stderr.bin','-exit.txt')]
 need(all(not p.exists() for p in [GRANT,RECEIPT,FAILURE,*audit_outputs]),'fresh recovery metadata and actual audit2 outputs')
 CONTEXT['phase']='original-plan-and-failed-audit'
 original_raw,_=read(path(ORIGINAL_PLAN['path']),640*KIB,ORIGINAL_PLAN);original=strict(original_raw)
 oldrefs={};oldraw={}
 for role,(suffix,n,h) in OLD_AUDIT_PINS.items():
  p=WORK/('independent-local-image-probe-audit'+suffix);r=dict(path=p.relative_to(ROOT).as_posix(),bytes=n,sha256=h)
  oldraw[role],oldrefs[role]=read(p,256*KIB,r,empty=role=='stderr')
  if role in ('source','ledger','protocol'):need(original['source_bindings'].get(r['path'])==dict(bytes=n,sha256=h),'original checker was prospectively source-bound')
 old=strict(oldraw['result']);outer=strict(oldraw['outer'])
 need(old['status']=='INCOMPLETE_INDEPENDENT_AUDIT' and old['subject_complete'] is False and old['scientific_contract_verified'] is False and old['cpu_accounting_complete'] is False,'no first audit completion admission')
 need(outer['exit_code']==1 and outer['stdout_bytes']==165323 and outer['stderr_bytes']==0 and oldraw['exit']==b'1\n' and not oldraw['stderr'] and oldraw['result'].endswith(b'\n') and oldraw['stdout']==oldraw['result'][:-1]+b'\r\n','exact historical failure/transport records')
 need(old['authority']['plan']==ORIGINAL_PLAN and 'declared checker module file: '+str(SUPPLEMENT) in old['exception']['suffix'],'actual original plan and observed checker-only supplement')
 CONTEXT['phase']='fresh-recovery-source-closure';sources={}
 need(sum(int(row[1]) for row in args.source if row[1].isdecimal())<=256*KIB,'aggregate source preflight')
 for name,n,h in args.source:
  need(n.isdecimal() and int(n)>0 and len(h)==64 and all(c in '0123456789abcdef' for c in h),'typed positive new source triple')
  p=path(name);need(p.is_relative_to(WORK) and p.suffix in ('.py','.md','.json'),'bounded owned recovery source role')
  r=dict(path=p.relative_to(ROOT).as_posix(),bytes=int(n),sha256=h);_,actual=read(p,256*KIB,r)
  need(actual['path'] not in sources,'unique new source');sources[actual['path']]=dict(bytes=actual['bytes'],sha256=actual['sha256'])
 need(all((WORK/n).relative_to(ROOT).as_posix() in sources for n in REQUIRED),'complete independently reviewed recovery closure')
 previous={path(k) for space in ('source_bindings','runtime_bindings','runtime_empty_bindings') for k in original[space]}
 need(not {path(k) for k in sources}&previous,'new source grant never replaces original authority')
 CONTEXT['phase']='one-fixed-checker-runtime-file'
 _,supplement=read(SUPPLEMENT,64*KIB,dict(path=str(SUPPLEMENT),**SUPPLEMENT_PIN));need(SUPPLEMENT not in previous and SUPPLEMENT not in {path(k) for k in sources},'supplement disjoint from original and new sources')
 runtime={supplement['path']:dict(bytes=supplement['bytes'],sha256=supplement['sha256'])}
 CONTEXT['phase']='metadata-authority-controls'
 signature=sha(encode([sources,runtime,oldrefs]));namespace_contract(original,sources,runtime);controls=[dict(id='actual-recovery-namespaces',passed=True)]
 first=next(iter(sources));zero={**sources,first:{**sources[first],'bytes':0}}
 changed_runtime={str(SUPPLEMENT.with_name('undeclared-checker-module.py')):next(iter(runtime.values()))}
 for name,bad_sources,bad_runtime,message in (
  ('zero-new-source',zero,runtime,'positive recovery namespace'),
  ('undeclared-checker-module',sources,changed_runtime,'exact checker-only supplementary identity')):
  rejected=False
  try:namespace_contract(original,bad_sources,bad_runtime)
  except ValueError as exc:need(str(exc)==message,'exact namespace control rejection');rejected=True
  need(rejected,'namespace destroyer has power');controls.append(dict(id=name,passed=True,error=message))
 for name,bad,message in (
  ('boolean-empty-evidence',{**oldrefs['stderr'],'bytes':False},'typed same-path expected FileRef'),
  ('changed-empty-evidence-hash',{**oldrefs['stderr'],'sha256':'0'*64},'exact expected metadata/runtime bytes')):
  rejected=False
  try:read(path(oldrefs['stderr']['path']),0,bad,empty=True)
  except ValueError as exc:need(str(exc)==message,'exact empty-evidence control rejection');rejected=True
  need(rejected,'empty evidence destroyer has power');controls.append(dict(id=name,passed=True,error=message))
 read(path(oldrefs['stderr']['path']),0,oldrefs['stderr'],empty=True);namespace_contract(original,sources,runtime)
 need(sha(encode([sources,runtime,oldrefs]))==signature,'complete namespaces/evidence restored')
 controls.append(dict(id='restored-recovery-authority',passed=True,canonical_sha256=signature))
 need(all(PRIOR[k]+PREP[k]+AUDIT[k]<=CAPS[k] for k in PRIOR) and sum(COMPONENTS.values())<=MIB,'full retained phase and metadata family')
 command=[str(PYTHON),'-B',str(WORK/'independent-local-image-probe-audit-2.py')]
 for flag,role in (('plan','plan'),('result','parent'),('outer','outer'),('console','console'),('exit','exit')):
  r=old['authority'][role];command+=['--'+flag,str(path(r['path'])),'--'+flag+'-sha256',r['sha256']]
 command+=['--self-sha256',sources[(WORK/'independent-local-image-probe-audit-2.py').relative_to(ROOT).as_posix()]['sha256'],
  '--worker-sha256',old['authority']['worker']['sha256'],'--recovery-grant',str(GRANT),'--recovery-grant-sha256','ACTUAL_RECOVERY_GRANT_SHA256']
 grant=dict(schema='m193c-local-image-audit-recovery-v1',original_plan=ORIGINAL_PLAN,failed_audit=oldrefs,source_bindings=sources,
  checker_runtime_bindings=runtime,prior_work=PRIOR,resource_allowance=dict(preparation=PREP,audit=AUDIT,cumulative_limits=CAPS),commands=dict(audit=command))
 raw=encode(grant);need(len(raw)<=64*KIB,'complete recovery grant extent')
 CONTEXT['phase']='final-source-evidence-recheck'
 for name,(expected_identity,_) in SEEN.items():
  p=Path(name);st=p.lstat();regular(st,p);need(identity(st)==expected_identity,'all held inputs unchanged before release')
 check();observed=sample();grantref=ref(GRANT,raw);launch=[grantref['sha256'] if x=='ACTUAL_RECOVERY_GRANT_SHA256' else x for x in command]
 receipt=encode(dict(schema='m193c-local-image-audit-recovery-preparation-v1',status='COMPLETE_METADATA_PREPARATION_ONLY',grant=grantref,
  argv=sys.orig_argv,launch_command=launch,sample=observed,last_guard=LAST,publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),
  allowance=PREP,component_caps=COMPONENTS,authority_controls=controls,authority_before_sha256=signature,authority_after_sha256=signature,complete_process_cpu_accounting=False,external_exit_and_whole_wall_required=True,
  scope='One fixed checker supplement hashed; no imports, discovery, saved arrays or subject execution. Original producer authority unchanged.'))
 CONTEXT['phase']='publication';write(GRANT,raw,64*KIB);receiptref=write(RECEIPT,receipt,16*KIB);last=sample()
 need(last['cpu_seconds']<=5 and last['wall_seconds']<=10,'actual metadata publication cap')
 output=encode(dict(status='COMPLETE_METADATA_PREPARATION_ONLY',receipt=receiptref,grant=grantref,post_publication_sample=last,
  publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),external_exit_and_whole_wall_required=True))
 need(sys.stdout.buffer.write(output)==len(output),'complete binary metadata stdout');sys.stdout.buffer.flush();return 0

if __name__=='__main__':
 try:code=main()
 except Exception as error:
  failure=dict(schema='m193c-local-image-audit-recovery-preparation-failure-v1',status='REFUSED',last_guard=LAST,sample=sample(),**CONTEXT,
   error=dict(type=type(error).__name__,message=str(error)[:1024]),allowance=PREP,publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),
   complete_process_cpu_accounting=False,external_exit_and_whole_wall_required=True)
  try:write(FAILURE,encode(failure),8*KIB)
  except Exception as publication:print(encode(dict(failure=failure,publication_error=str(publication)[:512])).decode(),file=sys.stderr,flush=True)
  raise
 raise SystemExit(code)
