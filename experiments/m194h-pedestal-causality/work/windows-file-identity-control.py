"""SOURCE ONLY until reviewed/released: fixed actual reader metadata controls.
No candidate main/import, numerical library, process, image or scientific call.
"""
import time
START_CPU,START_WALL=time.process_time(),time.monotonic()
import argparse,ast,hashlib,json,math,os,stat,sys,traceback,types
from pathlib import Path as NativePath
ROOT=NativePath(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m194h-pedestal-causality'
SELF=NativePath(__file__).resolve()
OUT=HERE/'work/windows-file-identity-control-1'
MIB=1<<20;KIB=1024
PINS={
 'prepare-stage.py':(11367,'a01b865ec3cb460958cf8a172aefc3bd13239878bfe0a52dee442214207903ef'),
 'capture-stage.py':(4300,'8255efc220ffa171310e1aa1e31aa031771fe92e7190ce8c3165d3da72358dfd'),
 'work/check-run.py':(5859,'beb4472383f6193f936342ad1a3bdfc86feeeb29fc541b5ebc0c072011c3b877'),
 'build-and-run.py':(34864,'5738d18ac41044361b6083ed38fa743dedee2a3005470130c19b2b5d1e2dadb3'),
 'independent-verify.py':(69266,'800afb0cc1dbfd6528c163fd53fcc67eb325ab7c53943babd40689f0830bdd65')}
SELECTION={
 'prepare-stage.py':('check','live','read'),
 'capture-stage.py':('buffer_ref',),
 'work/check-run.py':('need','read'),
 'build-and-run.py':('need','lexical','identity','shared_identity','read'),
 'independent-verify.py':('ContractError','need','integer','digest','encoded','exact','strict','path_identity','typed_ref','object_identity','shared_identity','Files','numpy_source_observation')}
PROFILES=('prepare.read','capture.buffer_ref','wrapper.read','driver.read','checker.read','checker.actual','checker.numpy-source-stand-in')
MODES=('stable-different-ctime','path-final-ctime','handle-final-ctime','opened-shared-inode','restored')
FIELDS=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_nlink','st_mode','st_file_attributes')
READ_BYTES=0

def need(ok,why):
 if not ok:raise ValueError(why)
def check():
 need(time.process_time()-START_CPU<=9 and time.monotonic()-START_WALL<=18,'ordinary9CPU/18wall cutoff')
 need(READ_BYTES<=4*MIB,'fixed metadata read budget')
def encoded(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def digest(b):return hashlib.sha256(b).hexdigest()
def ident(s):
 values=tuple(getattr(s,k,0) for k in FIELDS)
 need(all(type(v) is int and 0<=v<(1<<128) for v in values),'fixed source metadata integer envelope')
 return values
def shared(s):return tuple(getattr(s,k,0) for k in FIELDS if k!='st_ctime_ns')
def authentic(p,cap,pin=None):
 global READ_BYTES
 check();p=NativePath(p)
 need(p.is_absolute() and p.is_relative_to(ROOT) and p.resolve()==p,'fixed owned input')
 for q in (p,*p.parents):
  s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'non-reparse ancestry')
 a=p.stat();need(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and 0<a.st_size<=cap,'plain bounded source')
 with p.open('rb') as f:
  b=os.fstat(f.fileno());raw=f.read(cap+1);c=os.fstat(f.fileno())
 d=p.stat();READ_BYTES+=len(raw)
 need(ident(a)==ident(d) and ident(b)==ident(c) and shared(a)==shared(b) and len(raw)==a.st_size,'unchanged source bytes/identities')
 if pin is not None:need((len(raw),digest(raw))==pin,'literal source pin')
 check();return raw,dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=digest(raw)),dict(path=list(ident(a)),handle=list(ident(b)))

def publish(name,value,cap):
 b=encoded(value);need(len(b)<=cap,'pre-encoded slot limit')
 p=OUT/name;stage=OUT/(name+'.stage');need(not stage.exists(),'unused simultaneous stage')
 with stage.open('xb') as f:need(f.write(b)==len(b),'whole write');f.flush();os.fsync(f.fileno())
 os.replace(stage,p)
 need(sum(x.stat().st_size for x in OUT.iterdir() if x.is_file())<=384*KIB,'owned actual artifact bound')
 return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=digest(b))

class Scenario:
 def __init__(self,profile,mode):
  self.profile=profile;self.mode=mode;self.path_calls=0;self.handle_calls=0;self.reads=0;self.fd=None;self.changed=False;self.observed=[]
 def altered(self,s,kind):
  d={k:getattr(s,k,0) for k in FIELDS}
  # Deterministic, different domains; stable within each domain unless faulted.
  d['st_ctime_ns']=101 if kind=='path' else 202
  final=3 if self.profile.startswith(('prepare.','capture.')) else 2
  if kind=='path' and self.mode=='path-final-ctime' and self.path_calls==final:d['st_ctime_ns']+=1;self.changed=True
  if kind=='handle' and self.mode=='handle-final-ctime' and self.handle_calls==2:d['st_ctime_ns']+=1;self.changed=True
  if kind=='handle' and self.mode=='opened-shared-inode' and self.handle_calls==1:d['st_ino']+=1;self.changed=True
  need(all(type(v) is int and 0<=v<(1<<128) for v in d.values()),'bounded injected metadata')
  self.observed.append(dict(api=kind,identity=[d[k] for k in FIELDS]))
  return types.SimpleNamespace(**d)
 def path(self,value):
  p=value.p if isinstance(value,Named) else NativePath(value)
  return Named(p,self) if p==SELF else p
 def fstat(self,fd):
  need(fd==self.fd,'only current owned read handle');self.handle_calls+=1
  return self.altered(os.fstat(fd),'handle')

class Named:
 def __init__(self,p,scenario):self.p=p;self.scenario=scenario
 def __getattr__(self,k):return getattr(self.p,k)
 def __str__(self):return str(self.p)
 def __fspath__(self):return str(self.p)
 def __eq__(self,other):return self.p==(other.p if isinstance(other,Named) else other)
 def stat(self):
  self.scenario.path_calls+=1
  return self.scenario.altered(self.p.stat(),'path')
 def open(self,mode):
  need(mode=='rb' and self.p==SELF,'only fixed source data read')
  f=self.p.open(mode);self.scenario.fd=f.fileno();return TrackedStream(f,self.scenario)

class TrackedStream:
 def __init__(self,f,scenario):self.f=f;self.scenario=scenario
 def __enter__(self):return self
 def __exit__(self,*args):return self.f.__exit__(*args)
 def fileno(self):return self.f.fileno()
 def read(self,n):
  global READ_BYTES
  need(type(n) is int and 0<n<=MIB+1,'bounded helper read request')
  b=self.f.read(n);READ_BYTES+=len(b);self.scenario.reads+=len(b);check();return b

class LocalBudget:
 def __init__(self):self.read_bytes=0
 def check(self):check()

class LocalOS:
 def __init__(self,scenario):self.scenario=scenario
 def __getattr__(self,name):return getattr(os,name)
 def fstat(self,fd):return self.scenario.fstat(fd)

def selected(raw,name):
 tree=ast.parse(raw);names=set(SELECTION[name]);nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
 need(len(nodes)==len(names) and {n.name for n in nodes}==names,'unique closed original definitions')
 return compile(ast.Module(body=nodes,type_ignores=[]),str(HERE/name),'exec'),dict(names=sorted(names),ast_sha256=digest(ast.dump(ast.Module(body=nodes,type_ignores=[]),include_attributes=False).encode()))

def invoke(code,profile,mode,self_ref):
 scenario=Scenario(profile,mode);budget=LocalBudget()
 scope=dict(Path=scenario.path,os=LocalOS(scenario),stat=stat,hashlib=hashlib,json=json,math=math,sys=sys,time=time,ROOT=ROOT,
  MIB=MIB,KIB=KIB,START=START_WALL,EMPTY_SHA=digest(b''),NP=types.SimpleNamespace(__file__=str(SELF),__version__='SOURCE_METADATA_STAND_IN'))
 exec(code,scope)
 returned=None;error=None
 try:
  if profile=='prepare.read':returned=scope['read'](scenario.path(SELF),64*KIB)
  elif profile=='capture.buffer_ref':returned=scope['buffer_ref'](scenario.path(SELF))[0]
  elif profile=='wrapper.read':returned=scope['read'](scenario.path(SELF),64*KIB)
  elif profile=='driver.read':returned=scope['read'](scenario.path(SELF),64*KIB,self_ref,check=check)[0]
  elif profile=='checker.read':returned=scope['Files'](budget).read(self_ref,64*KIB)
  elif profile=='checker.actual':returned=scope['Files'](budget).actual(SELF,64*KIB)
  else:returned=scope['numpy_source_observation'](budget)['module_source']
 except (ValueError,AssertionError) as exc:error=dict(type=type(exc).__name__,reason=str(exc))
 expected=mode in ('stable-different-ctime','restored')
 if expected:
  need(error is None,'actual selected baseline/restored reader refused: '+str(error))
  if isinstance(returned,bytes):need((len(returned),digest(returned))==(self_ref['bytes'],self_ref['sha256']),'actual returned whole source bytes')
  else:need(returned['bytes']==self_ref['bytes'] and returned['sha256']==self_ref['sha256'],'actual returned source FileRef')
  need(scenario.path_calls>1 and scenario.handle_calls==2,'full positive path/handle lifecycle')
 else:need(error is not None and scenario.changed,'powered actual selected-reader rejection')
 return dict(profile=profile,mode=mode,expected_pass=expected,passed=error is None,rejection=error,
  path_calls=scenario.path_calls,handle_calls=scenario.handle_calls,read_bytes=scenario.reads,
  injected_field_reached=scenario.changed,observations=scenario.observed,
  restored_source_sha256=self_ref['sha256'] if mode=='restored' else None)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-sha256',required=True);args=parser.parse_args()
 need(NativePath.cwd()==ROOT and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,'fixed -I -S -B invocation')
 need(sys.orig_argv==[sys.executable,'-I','-S','-B',str(SELF),'--source-sha256',args.source_sha256],'exact actual argv')
 own,self_ref,own_identity=authentic(SELF,64*KIB);need(self_ref['sha256']==args.source_sha256,'external self pin')
 need(not OUT.exists(),'fresh once-only output');OUT.mkdir()
 rows=[];phases=[];sources={};codes={}
 base=dict(schema='m194h-windows-file-identity-control-v1',status='INITIAL_INCOMPLETE',source=self_ref,
  limits=dict(cpu_seconds=10,wall_seconds=20,file_bytes=MIB),prior_observation_charge='includes root prior three-file OS metadata observations; not remeasured here',rows=rows)
 publish('result.json',base,128*KIB)
 try:
  for name,pin in PINS.items():
   raw,ref,identities=authentic(HERE/name,128*KIB,pin);codes[name],ast_ref=selected(raw,name);sources[name]=dict(ref=ref,selection=ast_ref,actual_source_identities=identities)
  for profile in PROFILES:
   name={'prepare':'prepare-stage.py','capture':'capture-stage.py','wrapper':'work/check-run.py','driver':'build-and-run.py','checker':'independent-verify.py'}[profile.split('.')[0]]
   for mode in MODES:rows.append(invoke(codes[name],profile,mode,self_ref))
   phases.append(publish('progress.json',dict(status='INCOMPLETE_UNTIL_FINAL',completed_profiles=len(phases)+1,rows=rows),128*KIB));check()
  need(len(rows)==35 and sum(r['expected_pass'] for r in rows)==14,'fixed35 metadata rows')
  for name,pin in PINS.items():authentic(HERE/name,128*KIB,pin)
  authentic(SELF,64*KIB,(self_ref['bytes'],self_ref['sha256']))
  check();base.update(status='PASS_ACTUAL_READER_METADATA_CONTROLS_ONLY',sources=sources,own_initial_identities=own_identity,completed_profiles=7,
   own_sample=dict(cpu_seconds=time.process_time()-START_CPU,wall_seconds=time.monotonic()-START_WALL),tail_reserve=dict(cpu_seconds=1,wall_seconds=2),
   scope='35 deterministic reader-metadata rows on this fixed source; actual data bytes unchanged. NumPy profile uses a labelled source stand-in. No scientific, process, actual runtime or filesystem mutation control.')
  publish('result.json',base,128*KIB);sys.stdout.buffer.write(encoded(base));return 0
 except BaseException as exc:
  b=traceback.format_exc().encode();base.update(status='REFUSED',error=dict(type=type(exc).__name__,bytes=len(b),sha256=digest(b),suffix=b[-2048:].decode('utf8','replace')),
   own_sample=dict(cpu_seconds=time.process_time()-START_CPU,wall_seconds=time.monotonic()-START_WALL))
  publish('result.json',base,128*KIB);sys.stdout.buffer.write(encoded(base));return 1
if __name__=='__main__':raise SystemExit(main())
