"""Bounded audit3 metadata preparation only. No candidate/helper/runtime imports or data reads."""
import time
START=time.monotonic()
import argparse,hashlib,json,math,os,stat,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'experiments/m193c-output-grid/work';SELF=Path(__file__).resolve()
PY=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
KIB=1024;MIB=1<<20;EMPTY=hashlib.sha256(b'').hexdigest()
GRANT=WORK/'local-image-audit-recovery-3.json';RECEIPT=WORK/'local-image-audit-3-preparation-1.json'
CONTROLS=WORK/'local-image-audit-3-preparation-controls-1.json';FAILURE=WORK/'local-image-audit-3-preparation-1-failure.json';STAGE=WORK/'local-image-audit-3-preparation-1-failure-stage.json'
PLAN=dict(path='experiments/m193c-output-grid/local-image-probe-plan-1.json',bytes=476283,sha256='337ee76493feb15f14982d14fdb6b6148bc76ba108a9c0d77ba51ca25a6e66c1')
PRIOR=dict(cpu_seconds=1618.443678,wall_seconds=1651.9278447999966,file_bytes=4144759577,metadata_bytes=153498643)
CAPTURE_PRIOR=dict(cpu_seconds=1588.443678,wall_seconds=1601.9278447999966,file_bytes=4140565273,metadata_bytes=149304339)
ENTERED=dict(cpu_seconds=30,wall_seconds=50,file_bytes=4*MIB,metadata_bytes=4*MIB)
PREP=dict(cpu_seconds=5,wall_seconds=10,file_bytes=MIB,metadata_bytes=MIB)
AUDIT=dict(cpu_seconds=25,wall_seconds=30,file_bytes=3*MIB,metadata_bytes=3*MIB)
CAPS=dict(cpu_seconds=1660,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=168*MIB)
COMPONENTS=dict(new_sources=256*KIB,grant=64*KIB,receipt=64*KIB,controls=16*KIB,failure=16*KIB,failure_stage=16*KIB,external_streams_exit_outer=32*KIB)
REQUIRED=('independent-local-image-probe-audit-3.py','local-image-audit-3-runtime.py','independent-local-image-probe-audit-3-ledger.json','independent-local-image-probe-audit-3-preregister.md','independent-local-image-probe-audit-3-source-review.md','prepare-local-image-audit-3.py','local-image-audit-3-preparation.md','independent-local-image-audit-3-preparation-review.md','local-image-audit-3-runtime-decision.md','root-isolated-import-capture-1-terminal-read.json')
TERMINAL_PIN=dict(path='experiments/m193c-output-grid/work/root-isolated-import-capture-1-terminal-read.json',bytes=1499,sha256='77d4fe803ce219e6b78312751e02f02bfad0a6d667447d0f02b04450875bbff6')
SEEN={};ROWS=[];WRITES=0;OBSERVED={};OWNED=False
AUDIT2_PINS={'source': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2.py', 'bytes': 77564, 'sha256': 'ab4731982603f35fa27dc9019ec3f9da88ca31784069f2a296d6790a721a963b'}, 'ledger': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-ledger.json', 'bytes': 2145, 'sha256': '18254f2444a0427e9d7be03b5801a0c579aff4eac6ff78c3bf695ce9a4f0dd3e'}, 'protocol': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-preregister.md', 'bytes': 10189, 'sha256': '58197021d94c13f7659f93e645c989a9e1cb90e36a87e6b24e4f6905606deeeb'}, 'result': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2.json', 'bytes': 168790, 'sha256': '9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f'}, 'progress': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-progress.json', 'bytes': 65536, 'sha256': '6ba1a540308ab39f5f1fbf8ccf424c4fb7ef1299f7eeed19e8632de063dc9329'}, 'outer': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-outer.json', 'bytes': 2138, 'sha256': 'bb583734d952afe54e225bc14c225ac30a7bb8f9944cfc6843eb6ef42a4ed684'}, 'stdout': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-stdout.bin', 'bytes': 168790, 'sha256': '9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f'}, 'stderr': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-stderr.bin', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'exit': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-exit.txt', 'bytes': 2, 'sha256': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865'}}
CAPTURE_PINS={'result': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1.json', 'bytes': 58677, 'sha256': '2bfaa94532ea2e90ad3744475c7e9ce0883121e5ac7a83c31f54c453a6081950'}, 'progress': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-progress.json', 'bytes': 65536, 'sha256': '31077a829dae657322a757aa6e1c2dcc4ae7b38056e3d6455ab6f353ade7cabe'}, 'outer': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-outer.json', 'bytes': 65536, 'sha256': '5f35be74687f17e8289411ea79b0e4fb412bc50e152b25c7ff00948432fd4a8c'}, 'stdout': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-stdout.bin', 'bytes': 323, 'sha256': 'b24751bb1a9ff4d090e8a7aac9a71045d09c99549e9edaf7e7553f578af8ccc4'}, 'stderr': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-stderr.bin', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'exit': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-exit.txt', 'bytes': 2, 'sha256': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865'}, 'external_outer': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-launch-outer.json', 'bytes': 776, 'sha256': 'cc94ca06d3a7cb20b42aa89dbbeebebff7bc5f187118185df17774f56cdabd2f'}, 'external_stdout': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-launch-stdout.bin', 'bytes': 332, 'sha256': '24e3927f4df14387458dd51b1070286c23a991e001ff4a804fd62c0968a36335'}, 'external_stderr': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-launch-stderr.bin', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'external_exit': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-launch-exit.txt', 'bytes': 2, 'sha256': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865'}, 'independent_read': {'path': 'experiments/m193c-output-grid/work/independent-local-image-checker-import-capture-1-read.md', 'bytes': 8119, 'sha256': 'cd6dd372ec2b472f440e25c638844b2eef95a0ba4e96aba1c75abcb1577eb8d7'}, 'diagnosis': {'path': 'experiments/m193c-output-grid/work/independent-isolated-import-registry-diagnosis.md', 'bytes': 5947, 'sha256': 'edb30655c8605d452f986e59acaec8fd94a7d90eb3614c5b1ed97cabb93b0a3b'}}
CAPTURE_GRANT_PIN={'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-grant-1.json', 'bytes': 5213, 'sha256': '66b243268a331b79d04085e8e1cd39c1fe278f0b9a7d95ea4876f222e344d7b9'}
DECISION_PIN={'path': 'experiments/m193c-output-grid/work/local-image-audit-3-runtime-decision.md', 'bytes': 5538, 'sha256': '09b140d3d2c2b27cd4464fd990e4128c4163864020a4c84c946db54cbf883c49'}

def need(v,m):
 if not v:raise ValueError(m)


def encode(v):return (json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()


def digest(raw):return hashlib.sha256(raw).hexdigest()


def sampled():return dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)


def guard():
 s=sampled();OBSERVED.update(s)
 need(s["cpu_seconds"]<=4 and s["wall_seconds"]<=9,"current preparation ordinary CPU/wall envelope")


def closed(v,keys):need(type(v) is dict and set(v)==set(keys),"closed metadata fields")


def parse(raw):
 def pairs(items):
  out={}
  for k,v in items:need(k not in out,"duplicate JSON key");out[k]=v
  return out
 def walk(v):
  if type(v) is float:need(math.isfinite(v),"finite JSON")
  elif type(v) is dict:
   for x in v.values():walk(x)
  elif type(v) is list:
   for x in v:walk(x)
 v=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
 walk(v);return v


def path(value):
 need(type(value) is str and 0<len(value)<=2048,"bounded path")
 p=Path(value);need(".." not in p.parts,"no parent traversal")
 p=Path(os.path.abspath(str(ROOT/p)))
 for q in [*reversed(p.parents),p]:
  s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,"st_file_attributes",0)&1024,"no lexical reparse component")
  if q!=p:need(stat.S_ISDIR(s.st_mode),"directory ancestry")
 need(p.resolve(strict=True)==p,"same checked canonical path")
 return p


def identity(s):
 return tuple(int(getattr(s,k,0)) for k in ("st_dev","st_ino","st_size","st_mtime_ns","st_file_attributes","st_nlink"))


def plain(s,p):
 need(stat.S_ISREG(s.st_mode) and not getattr(s,"st_file_attributes",0)&1024
  and s.st_nlink>=1 and (not p.is_relative_to(ROOT) or s.st_nlink==1),"plain scoped file")


def pin(v,positive=False):
 closed(v,("path","bytes","sha256"))
 need(type(v["bytes"]) is int and (v["bytes"]>0 if positive else v["bytes"]>=0)
  and type(v["sha256"]) is str and len(v["sha256"])==64
  and all(c in "0123456789abcdef" for c in v["sha256"]),"positive source FileRef" if positive else "typed FileRef")
 need(v["bytes"]!=0 or v["sha256"]==EMPTY,"canonical empty hash")
 return path(v["path"])


def ref(p,raw):
 return dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),bytes=len(raw),sha256=digest(raw))


def read(v,cap):
 guard();p=pin(v);need(v["bytes"]<=cap,"prevalidated read extent")
 before=p.lstat();plain(before,p);need(before.st_size==v["bytes"],"bound pre-open extent")
 with p.open("rb") as f:
  first=os.fstat(f.fileno());need(identity(first)==identity(before),"opened exact object")
  raw=f.read(v["bytes"]+1);last=os.fstat(f.fileno())
 named=p.lstat();plain(named,p)
 need(identity(first)==identity(last)==identity(named) and len(raw)==v["bytes"],"stable same-buffer read")
 need(digest(raw)==v["sha256"],"bound file SHA256")
 value=dict(file=ref(p,raw),identity=list(identity(named)))
 need(p not in SEEN or SEEN[p]==value,"same held bytes and identity")
 SEEN[p]=value;return raw


def write(p,value,cap):
 global WRITES
 raw=encode(value);need(len(raw)<=cap and WRITES<8,"finite metadata publication")
 WRITES+=1
 with p.open("xb") as f:
  need(f.write(raw)==len(raw),"full metadata write");f.flush();os.fsync(f.fileno())
 s=p.lstat();plain(s,p)
 with p.open("rb") as f:
  a=os.fstat(f.fileno());need(identity(a)==identity(s),"published opened identity")
  observed=f.read(len(raw)+1);b=os.fstat(f.fileno())
 need(observed==raw and identity(a)==identity(b)==identity(p.lstat()),"published same-byte readback")
 return ref(p,observed)


def default_or_failure(value,initial=False):
 target=FAILURE if initial else STAGE
 r=write(target,value,16*KIB)
 if not initial:
  old_identity=identity(STAGE.lstat());os.replace(STAGE,FAILURE)
  need(identity(FAILURE.lstat())==old_identity,"same atomic failure object")
  r["path"]=FAILURE.relative_to(ROOT).as_posix()
 return r


def original_plan(v):
 pin(v,True);need(v==PLAN,"original plan immutable")


def sources_predicate(values):
 need(type(values) is list and 1<=len(values)<=32,"finite source list")
 paths=[];total=0
 for r in values:
  p=pin(r,True);need(p.is_relative_to(WORK) and p.suffix in (".py",".md",".json"),"new source metadata only")
  paths.append(p);total+=r["bytes"]
 need(len(paths)==len(set(paths)),"unique source identity")
 need(total<=256*KIB,"whole source closure extent")
 return paths


def equal_ref(a,b):
 pin(a);pin(b);return path(a['path'])==path(b['path']) and a['bytes']==b['bytes'] and a['sha256']==b['sha256']

def history():
 original=parse(read(PLAN,640*KIB));need(original['schema']=='m193c-local-image-probe-plan-v1','unchanged original plan')
 a={k:read(v,256*KIB) for k,v in AUDIT2_PINS.items()};old=parse(a['result']);outer=parse(a['outer'])
 need(old['schema']=='m193c-saved-local-image-probe-audit-v2' and old['status']=='INCOMPLETE_INDEPENDENT_AUDIT' and old['subject_complete'] is False and old['scientific_contract_verified'] is False and 'private' not in old and old['actual_final_work']==CAPTURE_PRIOR,'exact failed audit2 and retained charges')
 need(a['stdout']==a['result'] and a['stderr']==b'' and a['exit']==b'1\n' and outer['exit_code']==1 and outer['stdout_bytes']==len(a['stdout']) and outer['stderr_bytes']==0 and outer['elapsed_wall_seconds']<=old['audit_timing']['wall_seconds']+.5,'audit2 whole raw transport and actual tail')
 c={k:read(v,256*KIB) for k,v in CAPTURE_PINS.items()};capture=parse(c['result']);owned=parse(c['outer']);external=parse(c['external_outer'])
 grant=parse(read(CAPTURE_GRANT_PIN,64*KIB));read(DECISION_PIN,16*KIB);terminal=parse(read(TERMINAL_PIN,16*KIB))
 need(capture['status']=='INCOMPLETE_NO_DATA_IMPORT_CAPTURE' and capture['capture_complete'] is False and capture['subject_complete'] is False and capture['saved_data_checks_complete'] is False and capture['numpy_import_attempted'] is True and len(capture['registries'])==1 and capture['registries'][0]['label']=='before-numpy' and len(capture['registries'][0]['rows'])==94 and len(capture['files'])==62,'failed capture has no admitted post-import baseline')
 need(capture['authority']['grant']==CAPTURE_GRANT_PIN and capture['authority']['original_plan']==PLAN and grant['prior_work']==CAPTURE_PRIOR and grant['cumulative_limits']==CAPS,'exact failed capture authority')
 advert=parse(c['stdout']);outer_advert=parse(c['external_stdout'])
 need(equal_ref(advert['result'],CAPTURE_PINS['result']) and advert['capture_complete'] is False and advert['exit_code']==1 and equal_ref(outer_advert['result'],CAPTURE_PINS['outer']) and outer_advert['exit_code']==1,'capture two-level advertisements')
 need(owned['status']=='REFUSED' and owned['exit_code']==owned['child_exit_code']==external['exit_code']==1 and c['exit']==c['external_exit']==b'1\n' and c['stderr']==c['external_stderr']==b'' and external['command']==owned['launcher_command'] and external['stdout_bytes']==len(c['external_stdout']) and external['stderr_bytes']==0,'owned and external capture refusal')
 need(external['elapsed_wall_seconds']<=owned['launcher_sample']['wall_seconds']+2<=32 and owned['terminal_cpu_accounting'] is True and owned['job_accounting']['active_processes']==0,'capture terminal and actual whole interval')
 need(terminal['status']=='VERIFIED_REFUSAL_TRANSPORT_AND_TERMINAL_ONLY' and equal_ref(terminal['collector'],CAPTURE_PINS['result']) and equal_ref(terminal['outer'],CAPTURE_PINS['outer']) and equal_ref(terminal['external'],CAPTURE_PINS['external_outer']) and equal_ref(terminal['source_grant'],CAPTURE_GRANT_PIN),'root terminal supplement exact association')
 # The old capture source map is historical metadata, never merged into new authority.
 prior_sources=[]
 for key,v in grant['source_bindings'].items():prior_sources.append(dict(path=key,**v))
 sources_predicate(prior_sources)
 for r in prior_sources:read(r,256*KIB)
 need(original['python_executable']==grant['python_executable'] and pin(original['python_executable'],True)==PY,'unchanged pinned Python');read(original['python_executable'],MIB)
 for role in ('plan','parent','worker','outer','console','exit'):
  r=old['authority'][role];pin(r,True);need(r['bytes']<=640*KIB,'finite original actual metadata');read(r,640*KIB)
 need(equal_ref(old['authority']['plan'],PLAN),'same original actual plan')
 return original,old

def controls(values):
 before=digest(encode([values,PLAN,AUDIT2_PINS,CAPTURE_PINS]))
 def source_fault(kind):
  v=parse(encode(values))
  if kind=='zero':v[0].update(bytes=0,sha256=EMPTY)
  elif kind=='bool':v[0].update(bytes=False,sha256=EMPTY)
  elif kind=='duplicate':v[-1]=dict(v[0])
  sources_predicate(v)
 def plan_fault():
  v=dict(PLAN);v['bytes']+=1;original_plan(v)
 def source_hash():
  v=dict(next(r for r in values if path(r['path'])==SELF));v['sha256']=('0' if v['sha256'][0]!='0' else '1')+v['sha256'][1:];read(v,256*KIB)
 def empty_fault(kind):
  v=dict(AUDIT2_PINS['stderr'])
  if kind=='bool':v['bytes']=False
  else:v['sha256']='0'*64
  read(v,0)
 cases=[('positive',lambda:source_fault(None),None),('wrong-original-plan',plan_fault,'original plan immutable'),('zero-source',lambda:source_fault('zero'),'positive source FileRef'),('bool-source-extent',lambda:source_fault('bool'),'positive source FileRef'),('duplicate-source',lambda:source_fault('duplicate'),'unique source identity'),('wrong-source-hash',source_hash,'bound file SHA256'),('bool-empty-evidence',lambda:empty_fault('bool'),'typed FileRef'),('wrong-empty-evidence-hash',lambda:empty_fault('hash'),'canonical empty hash')]
 for name,call,expected in cases:
  row=dict(id=name,passed=False);ROWS.append(row);got=None
  try:call()
  except ValueError as e:got=str(e)
  row.update(rejection=got,passed=got==expected);need(row['passed'],'exact powered metadata control '+name)
 restored=parse(encode(values));sources_predicate(restored);read(AUDIT2_PINS['stderr'],0)
 need(digest(encode([values,PLAN,AUDIT2_PINS,CAPTURE_PINS]))==before==digest(encode([restored,PLAN,AUDIT2_PINS,CAPTURE_PINS])),'whole source and evidence restoration')
 ROWS.append(dict(id='restored',passed=True,rejection=None))
 return dict(schema='m193c-local-image-audit3-preparation-controls-v1',rows=ROWS,original_sha256=before,restored_sha256=before,scope='Actual metadata/source-byte predicates only; no checker/helper imports or data.')

def fresh():
 fixed=[GRANT,RECEIPT,CONTROLS,FAILURE,STAGE]
 suffixes=('.json','-progress.json','-progress-stage.json','-outer.json','-stdout.bin','-stderr.bin','-exit.txt','-runtime-before-data.json','-runtime-after-data.json')
 fixed += [WORK/('independent-local-image-probe-audit-3'+s) for s in suffixes]
 need(all(not p.exists() for p in fixed),'fresh preparation and audit3 artifact family')

def main():
 global OWNED
 result=dict(schema='m193c-local-image-audit3-preparation-v1',status='INITIAL_INCOMPLETE')
 try:
  ap=argparse.ArgumentParser();ap.add_argument('--source',action='append',nargs=3,required=True);args=ap.parse_args()
  expected=[str(PY),'-I','-S','-B',str(SELF)]
  for row in args.source:expected+=['--source',*row]
  need(Path.cwd().resolve()==ROOT and path(sys.executable)==PY and sys.orig_argv==expected and sys.flags.isolated==sys.flags.no_site==sys.flags.ignore_environment==sys.flags.no_user_site==1 and sys.flags.safe_path is True and sys.dont_write_bytecode and not sys._xoptions,'exact isolated metadata argv/profile')
  fresh();OWNED=True;default_or_failure(result,True)
  need(1<=len(args.source)<=32,'finite source argv count');values=[]
  for name,n,h in args.source:
   need(type(n) is str and n.isascii() and n.isdecimal() and 1<=len(n)<=9,'positive decimal source extent')
   values.append(dict(path=name,bytes=int(n),sha256=h))
  listed=sources_predicate(values);need(set(WORK/n for n in REQUIRED)<=set(listed),'complete new source and review closure')
  need(sum(COMPONENTS.values())<=MIB,'complete new-byte preparation ledger')
  # All source types and aggregate extents are checked before source hashing.
  for r in values:read(r,256*KIB)
  mapping={path(r['path']).relative_to(ROOT).as_posix():dict(bytes=r['bytes'],sha256=r['sha256']) for r in values}
  need(mapping[SELF.relative_to(ROOT).as_posix()]['sha256']==SEEN[SELF]['file']['sha256'],'same-buffer actual preparer source binding')
  for r in (DECISION_PIN,TERMINAL_PIN):need(mapping.get(r['path'])==dict(bytes=r['bytes'],sha256=r['sha256']),'exact decision and terminal supplement source closure')
  original,old=history()
  previous={str(Path(os.path.abspath(str(ROOT/k)))) for space in ('source_bindings','runtime_bindings','runtime_empty_bindings') for k in original[space]}
  need(not previous&{str(p) for p in listed},'new namespace cannot replace original authority')
  need(all(PRIOR[k]==CAPTURE_PRIOR[k]+ENTERED[k] and PRIOR[k]+PREP[k]+AUDIT[k]<=CAPS[k] for k in PRIOR),'full retained and remaining phase fits unchanged amended caps')
  checked=controls(values);control_raw=encode(checked);need(len(control_raw)<=COMPONENTS['controls'],'control receipt capacity')
  auditor=WORK/'independent-local-image-probe-audit-3.py';command=[str(PY),'-I','-S','-B',str(auditor)]
  for flag,role in (('plan','plan'),('result','parent'),('outer','outer'),('console','console'),('exit','exit')):
   r=old['authority'][role];command+=['--'+flag,str(path(r['path'])),'--'+flag+'-sha256',r['sha256']]
  command+=['--self-sha256',mapping[auditor.relative_to(ROOT).as_posix()]['sha256'],'--worker-sha256',old['authority']['worker']['sha256'],'--recovery-grant',str(GRANT),'--recovery-grant-sha256','ACTUAL_AUDIT3_GRANT_SHA256']
  grant=dict(schema='m193c-local-image-isolated-audit-grant-v1',original_plan=PLAN,failed_audit2=AUDIT2_PINS,failed_capture=CAPTURE_PINS,capture_grant=CAPTURE_GRANT_PIN,decision=DECISION_PIN,source_bindings=mapping,prior_work=PRIOR,resource_allowance=dict(entered=ENTERED,preparation=PREP,audit=AUDIT,cumulative_limits=CAPS),commands=dict(audit=command))
  need(len(grant)==10 and command.count('ACTUAL_AUDIT3_GRANT_SHA256')==1,'exact ten-key grant and single actual digest substitution')
  grant_raw=encode(grant);need(len(grant_raw)<=COMPONENTS['grant'],'complete grant capacity');grant_ref=ref(GRANT,grant_raw)
  # Exact original buffers are already authenticated; no runtime or payload walk.
  for r in values:read(r,256*KIB)
  for p,w in SEEN.items():
   s=p.lstat();plain(s,p);need(list(identity(s))==w['identity'],'all bound metadata unchanged before publication')
  guard();launch=[grant_ref['sha256'] if x=='ACTUAL_AUDIT3_GRANT_SHA256' else x for x in command]
  result.update(status='COMPLETE_AUDIT3_METADATA_PREPARATION_ONLY',grant=grant_ref,controls=ref(CONTROLS,control_raw),source=SEEN[SELF]['file'],command=list(sys.orig_argv),launch_command=launch,prior_work=PRIOR,charged_preparation=PREP,remaining_audit=AUDIT,component_caps=COMPONENTS,component_total_bytes=sum(COMPONENTS.values()),sources=len(values),source_bytes=sum(r['bytes'] for r in values),retained_evidence_files=len(SEEN),sampled_work=sampled(),publication_allowance=dict(cpu_seconds=1,wall_seconds=1),cpu_accounting_complete=False,external_exit_and_whole_wall_required=True,scope='Metadata only. No imports, discovery, original image/payload access or checker execution; no scientific admission.')
  need(len(encode(result))<=COMPONENTS['receipt'],'complete preparation receipt capacity')
  # All complete normal artifacts fit before the first successful output is written.
  write(CONTROLS,checked,COMPONENTS['controls']);write(GRANT,grant,COMPONENTS['grant']);receipt_ref=write(RECEIPT,result,COMPONENTS['receipt'])
  post=sampled();need(post['cpu_seconds']+.25<=5 and post['wall_seconds']+.5<=10,'prestdout preparation with explicit tail')
  out=encode(dict(schema=result['schema'],status=result['status'],grant=grant_ref,receipt=receipt_ref,post_publication_sample=post,publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),actual_external_required=True))
  need(len(out)<=8*KIB and sys.stdout.buffer.write(out)==len(out),'whole bounded raw console');sys.stdout.buffer.flush();last=sampled();need(last['cpu_seconds']<=5 and last['wall_seconds']<=10,'observed final preparation envelope');return 0
 except BaseException:
  raw=traceback.format_exc().encode();failure=dict(schema='m193c-local-image-audit3-preparation-v1',status='REFUSED_AUDIT3_METADATA_PREPARATION',sampled_work=sampled(),last_guard=OBSERVED,charged_preparation=PREP,cpu_accounting_complete=False,external_exit_and_whole_wall_required=True,error=dict(bytes=len(raw),sha256=digest(raw),suffix=raw[-2048:].decode('utf-8','replace')),rows=ROWS)
  while len(encode(failure))>16*KIB and failure['error']['suffix']:failure['error']['suffix']=failure['error']['suffix'][len(failure['error']['suffix'])//2:]
  if OWNED:
   try:default_or_failure(failure)
   except BaseException:pass
  return 1
if __name__=='__main__':raise SystemExit(main())
