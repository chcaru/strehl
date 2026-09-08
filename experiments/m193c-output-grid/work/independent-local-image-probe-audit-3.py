"""Independent saved local-image audit. No subject/native-image import or execution.
Numerical work reads only saved patch arrays. No whole-peak/subpixel replay claim.
"""
import time
START=time.monotonic()
import argparse,ast,hashlib,importlib.util,importlib.machinery,json,math,os,stat,sys,traceback,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/m193c-output-grid';SELF=Path(__file__).resolve()
OUT=HERE/'local-image-probe-1';WORK=HERE/'work';KIB=1024;MIB=1<<20
SCHEMA='m193c-saved-local-image-probe-audit-v3';STATUS='PASS_SAVED_LOCAL_IMAGE_PROBE_ISOLATED_AUTHORITY_AUDIT';COMPLETE='COMPLETE_FIXED_LOCAL_IMAGE_PROBE_ONLY'
FINAL=WORK/'independent-local-image-probe-audit-3.json';PROGRESS=WORK/'independent-local-image-probe-audit-3-progress.json';STAGE=WORK/'independent-local-image-probe-audit-3-progress-stage.json'
LIMITS=dict(cpu_seconds=25,wall_seconds=30,file_bytes=3*MIB,metadata_bytes=3*MIB)
BASE=dict(cpu_seconds=1418.443678,wall_seconds=1321.9278447999966,file_bytes=4068213529,metadata_bytes=76952595)
SUBJECT=dict(cpu_seconds=90,wall_seconds=140,file_bytes=60*MIB,metadata_bytes=60*MIB)
FAILED_PREP=dict(cpu_seconds=5,wall_seconds=10,file_bytes=MIB,metadata_bytes=MIB)
CURRENT_PREP=dict(cpu_seconds=20,wall_seconds=60,file_bytes=MIB,metadata_bytes=MIB)
PREP=dict(cpu_seconds=25,wall_seconds=70,file_bytes=2*MIB,metadata_bytes=2*MIB)
PINS={'local-image-probe.py':(7859,'a76393fc3027340174a3b761b692ae2575056c50ed2dbbf574f05993c1a9c577'),
 'local-image-patches.py':(8014,'d407d592e326da587a8057fdb2d4169e81d042a384ee1a2a86c8741a86138f84'),
 'local-image-probe-run.py':(38744,'c9724fae5c8431c58a1c2a8445a633abb70bbf0ecadeb8334b075e489975316a'),
 'local-image-probe-preregister.md':(24374,'4fc987d3a1f759fb105afa271aa224da9642e027861b30c05b200028f279171e'),
 'local-image-probe-ledger.json':(3267,'9ce386f75fe8dec68e5b98bfbf45b18560811c71277950d9fb0aa59fa8e8191b')}
PRIVATE=('zero','integer','fractional','differential-blur','flat','unrelated','periodic','outside-search')
CONTROL=('rgb16-strip-reader',*PRIVATE,'observer-output','literal-displacement-oracle')
TRUTH={'zero':(0.,0.),'integer':(5.,-7.),'fractional':(1.25,-.4),'differential-blur':(1.25,-.4),'outside-search':(40.,0.)}
PAIRS=((0,1),(3,4));ORIGINAL={0:0,1:13,3:39,4:52};LUMA=(.2880402,.7118741,.0000857)
REAL_IDS=[f'{a}-{b}/g{g:02d}/q{q}' for a,b in PAIRS for g in range(16) for q in range(4)]
CAPS=dict(cpu_seconds=1600,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=160*MIB)
OLD_CAPS=dict(cpu_seconds=1440,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=128*MIB)
PHASE=dict(cpu_seconds=140,wall_seconds=240,file_bytes=65*MIB,metadata_bytes=65*MIB)
EMPTY=hashlib.sha256(b'').hexdigest();VERIFIED={};READ_IDENTITIES={};PHASES=[];NP=None

def need(value,message):
 if not value:raise ValueError(message)
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def closed(value,keys):need(type(value) is dict and set(value)==set(keys),'closed '+','.join(keys))
def typed_number(value):return type(value) in (int,float) and math.isfinite(value)
def timer():need(time.process_time()<=24.75 and time.monotonic()-START<=29.5,'bounded independent audit including declared tail')
def identity(s):return tuple(int(getattr(s,k,0)) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_file_attributes','st_nlink'))
def regular(s,p):need(stat.S_ISREG(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024 and s.st_nlink>=1 and (not (p.is_relative_to(ROOT) or p==Path(sys.executable).resolve()) or s.st_nlink==1),'regular non-reparse scoped link identity')
def path(value):return (ROOT/value).resolve()
def ref(p,raw):
 p=Path(p).resolve();return dict(path=p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),bytes=len(raw),sha256=sha(raw))
def read(p,cap,pin=None,payload=False,fixture=False):
 timer();p=Path(p).resolve()
 if fixture:need(p in (OUT/'worker/controls/reader-le.tiff',OUT/'worker/controls/reader-be.tiff'),'private literal TIFF only')
 elif payload:need(p.is_relative_to(OUT/'worker') and p.suffix in ('.u16','.f32'),'saved patch payload only')
 else:need(p.suffix.lower() not in ('.arw','.tiff','.tif','.pth','.pkl'), 'no native/raster/model payload read')
 before=p.lstat();regular(before,p);need(0<=before.st_size<=cap,'bounded read extent')
 with p.open('rb') as f:
  first=os.fstat(f.fileno());regular(first,p);need(identity(first)==identity(before),'same opened identity');raw=f.read(cap+1);after=os.fstat(f.fileno())
 named=p.lstat();regular(named,p);need(identity(first)==identity(after)==identity(named) and len(raw)==first.st_size,'stable same-buffer read')
 actual=ref(p,raw)
 if pin is not None:
  closed(pin,('path','bytes','sha256'));need(type(pin['bytes']) is int and pin['bytes']>=0 and path(pin['path'])==p and pin['bytes']==len(raw) and pin['sha256'].lower()==actual['sha256'],'bound actual FileRef')
 need(str(p) not in VERIFIED or VERIFIED[str(p)]==actual,'same bound bytes across all audit phases')
 need(str(p) not in READ_IDENTITIES or READ_IDENTITIES[str(p)]==identity(named),'same object identity across audit phases')
 VERIFIED[str(p)]=actual;READ_IDENTITIES[str(p)]=identity(named);return raw,actual

def parse(raw):
 def pairs(items):
  d={}
  for k,v in items:need(k not in d,'duplicate JSON key');d[k]=v
  return d
 def walk(v):
  if type(v) is float:need(math.isfinite(v),'finite JSON')
  elif type(v) is dict:
   for x in v.values():walk(x)
  elif type(v) is list:
   for x in v:walk(x)
 v=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)));walk(v);return v

def J(p,cap=2*MIB,pin=None):
 raw,r=read(p,cap,pin);return parse(raw),r

def saved(r,cap=2*MIB):return J(path(r['path']),cap,r)[0]
def same(a,b):return type(a) is dict and type(b) is dict and path(a['path'])==path(b['path']) and a['bytes']==b['bytes'] and a['sha256'].lower()==b['sha256'].lower()
def error():
 raw=traceback.format_exc().encode();v=dict(bytes=len(raw),sha256=sha(raw),suffix=raw[-2048:].decode('utf-8','replace'))
 while len(encoded(v))>4096:v['suffix']=v['suffix'][len(v['suffix'])//2:]
 return v

def remember(phase,summary):
 entry=dict(phase=phase,summary=summary);need(len(encoded(entry))<=8*KIB,'bounded phase summary');PHASES.append(entry)
 value=dict(schema=SCHEMA,status='INCOMPLETE_INDEPENDENT_AUDIT',phases=PHASES,scope='Scoped visited checks only; never whole-subject admission.')
 raw=encoded(value);need(len(raw)<=64*KIB,'combined progress slot');raw=raw.rstrip(b'\n').ljust(64*KIB-1,b' ')+b'\n'
 with STAGE.open('xb') as f:need(f.write(raw)==len(raw),'complete staged progress');f.flush();os.fsync(f.fileno())
 os.replace(STAGE,PROGRESS)

def released(p,digest,cap):
 raw,r=read(p,cap);need(type(digest) is str and len(digest)==64 and r['sha256']==digest.lower(),'external released SHA256');return parse(raw),r



ORIGINAL_AUDITOR=WORK/'independent-local-image-probe-audit.py'
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
RECOVERY_PREP=dict(cpu_seconds=5,wall_seconds=10,file_bytes=MIB,metadata_bytes=MIB)
RETAINED_WORK={k:BASE[k]+PHASE[k] for k in BASE}
SUPPLEMENT=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\Lib\site-packages\_distutils_hack\__init__.py')
SUPPLEMENT_PIN=dict(bytes=6002,sha256='4bf5b0bc8f8af7ce7096e96f7167cf4f776f2cc0983f5c8f876ca780b3a67781')
RECOVERY=None;RECOVERY_REF=None;OLD_AUDIT=None
REQUIRED_RECOVERY_SOURCES=(
 'independent-local-image-probe-audit-2.py','independent-local-image-probe-audit-2-ledger.json',
 'independent-local-image-probe-audit-2-preregister.md','independent-local-image-probe-audit-2-source-review.md',
 'prepare-local-image-audit-2.py','local-image-audit-2-preparation.md',
 'independent-local-image-audit-2-preparation-review.md')


CURRENT_CAPS=dict(cpu_seconds=1660,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=168*MIB)
CAPTURE_PRIOR=dict(cpu_seconds=1588.443678,wall_seconds=1601.9278447999966,file_bytes=4140565273,metadata_bytes=149304339)
ENTERED=dict(cpu_seconds=30,wall_seconds=50,file_bytes=4*MIB,metadata_bytes=4*MIB)
AUDIT3_PRIOR={k:CAPTURE_PRIOR[k]+ENTERED[k] for k in BASE}
AUDIT3_GRANT=WORK/'local-image-audit-recovery-3.json'
RUNTIME_HELPER=WORK/'local-image-audit-3-runtime.py'
RUNTIME_INSPECTOR=None;RUNTIME_RECEIPTS={};RUNTIME_OVERFLOW={};PREFLIGHT=False
REQUIRED3=('independent-local-image-probe-audit-3.py','local-image-audit-3-runtime.py',
 'independent-local-image-probe-audit-3-ledger.json','independent-local-image-probe-audit-3-preregister.md',
 'independent-local-image-probe-audit-3-source-review.md','prepare-local-image-audit-3.py',
 'local-image-audit-3-preparation.md','independent-local-image-audit-3-preparation-review.md',
 'local-image-audit-3-runtime-decision.md','root-isolated-import-capture-1-terminal-read.json')
AUDIT2_PINS={'source': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2.py', 'bytes': 77564, 'sha256': 'ab4731982603f35fa27dc9019ec3f9da88ca31784069f2a296d6790a721a963b'}, 'ledger': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-ledger.json', 'bytes': 2145, 'sha256': '18254f2444a0427e9d7be03b5801a0c579aff4eac6ff78c3bf695ce9a4f0dd3e'}, 'protocol': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-preregister.md', 'bytes': 10189, 'sha256': '58197021d94c13f7659f93e645c989a9e1cb90e36a87e6b24e4f6905606deeeb'}, 'result': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2.json', 'bytes': 168790, 'sha256': '9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f'}, 'progress': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-progress.json', 'bytes': 65536, 'sha256': '6ba1a540308ab39f5f1fbf8ccf424c4fb7ef1299f7eeed19e8632de063dc9329'}, 'outer': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-outer.json', 'bytes': 2138, 'sha256': 'bb583734d952afe54e225bc14c225ac30a7bb8f9944cfc6843eb6ef42a4ed684'}, 'stdout': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-stdout.bin', 'bytes': 168790, 'sha256': '9440c3cd8b25b0d7cba5c938c923e2daf6597eafeeaf4dd785ffb7da3723592f'}, 'stderr': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-stderr.bin', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'exit': {'path': 'experiments/m193c-output-grid/work/independent-local-image-probe-audit-2-exit.txt', 'bytes': 2, 'sha256': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865'}}
CAPTURE_PINS={'result': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1.json', 'bytes': 58677, 'sha256': '2bfaa94532ea2e90ad3744475c7e9ce0883121e5ac7a83c31f54c453a6081950'}, 'progress': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-progress.json', 'bytes': 65536, 'sha256': '31077a829dae657322a757aa6e1c2dcc4ae7b38056e3d6455ab6f353ade7cabe'}, 'outer': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-outer.json', 'bytes': 65536, 'sha256': '5f35be74687f17e8289411ea79b0e4fb412bc50e152b25c7ff00948432fd4a8c'}, 'stdout': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-stdout.bin', 'bytes': 323, 'sha256': 'b24751bb1a9ff4d090e8a7aac9a71045d09c99549e9edaf7e7553f578af8ccc4'}, 'stderr': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-stderr.bin', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'exit': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-exit.txt', 'bytes': 2, 'sha256': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865'}, 'external_outer': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-launch-outer.json', 'bytes': 776, 'sha256': 'cc94ca06d3a7cb20b42aa89dbbeebebff7bc5f187118185df17774f56cdabd2f'}, 'external_stdout': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-launch-stdout.bin', 'bytes': 332, 'sha256': '24e3927f4df14387458dd51b1070286c23a991e001ff4a804fd62c0968a36335'}, 'external_stderr': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-launch-stderr.bin', 'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'external_exit': {'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-1-launch-exit.txt', 'bytes': 2, 'sha256': '4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865'}, 'independent_read': {'path': 'experiments/m193c-output-grid/work/independent-local-image-checker-import-capture-1-read.md', 'bytes': 8119, 'sha256': 'cd6dd372ec2b472f440e25c638844b2eef95a0ba4e96aba1c75abcb1577eb8d7'}, 'diagnosis': {'path': 'experiments/m193c-output-grid/work/independent-isolated-import-registry-diagnosis.md', 'bytes': 5947, 'sha256': 'edb30655c8605d452f986e59acaec8fd94a7d90eb3614c5b1ed97cabb93b0a3b'}}
CAPTURE_GRANT_PIN={'path': 'experiments/m193c-output-grid/work/local-image-checker-import-capture-grant-1.json', 'bytes': 5213, 'sha256': '66b243268a331b79d04085e8e1cd39c1fe278f0b9a7d95ea4876f222e344d7b9'}
DECISION_PIN={'path': 'experiments/m193c-output-grid/work/local-image-audit-3-runtime-decision.md', 'bytes': 5538, 'sha256': '09b140d3d2c2b27cd4464fd990e4128c4163864020a4c84c946db54cbf883c49'}

def positive_pins(values,cap):
 need(type(values) is dict and 1<=len(values)<=32,'finite supplemental positive namespace')
 total=0;seen=set()
 for key,pin in values.items():
  closed(pin,('bytes','sha256'))
  need(type(key) is str and type(pin['bytes']) is int and 0<pin['bytes']<=cap and type(pin['sha256']) is str and len(pin['sha256'])==64 and all(c in '0123456789abcdef' for c in pin['sha256']),'typed supplementary positive FileRef')
  p=path(key);need(p not in seen,'unique resolved supplemental identity');seen.add(p);total+=pin['bytes']
 need(total<=cap,'whole supplemental namespace extent')
 return seen

def recovery_authority(args):
 global RECOVERY,RECOVERY_REF,OLD_AUDIT
 grant,gr=released(args.recovery_grant,args.recovery_grant_sha256,64*KIB)
 need(path(gr['path'])==AUDIT3_GRANT,'fixed separate audit3 grant')
 closed(grant,('schema','original_plan','failed_audit2','failed_capture','capture_grant','decision','source_bindings','prior_work','resource_allowance','commands'))
 need(grant['schema']=='m193c-local-image-isolated-audit-grant-v1','new isolated audit authority schema')
 def pinned(given,expected,cap=256*KIB):
  closed(given,('path','bytes','sha256'));need(type(given['bytes']) is int and given==expected,'exact typed historical evidence')
  return read(path(given['path']),cap,given)[0]
 original=parse(pinned(grant['original_plan'],ORIGINAL_PLAN,640*KIB))
 oldraw={};closed(grant['failed_audit2'],tuple(AUDIT2_PINS))
 for role,pin in AUDIT2_PINS.items():oldraw[role]=pinned(grant['failed_audit2'][role],pin)
 old=parse(oldraw['result']);oldouter=parse(oldraw['outer'])
 need(old['schema']=='m193c-saved-local-image-probe-audit-v2' and old['status']=='INCOMPLETE_INDEPENDENT_AUDIT'
  and old['subject_complete'] is False and old['scientific_contract_verified'] is False and 'private' not in old
  and old['actual_final_work']==CAPTURE_PRIOR,'exact prior failed pre-private audit and nonrefundable cost')
 need(oldraw['stdout']==oldraw['result'] and oldraw['stderr']==b'' and oldraw['exit']==b'1\n'
  and oldouter['exit_code']==1 and oldouter['stdout_bytes']==len(oldraw['stdout']) and oldouter['stderr_bytes']==0,
  'audit2 actual raw final/stdout/outer refusal')
 need(oldouter['elapsed_wall_seconds']<=old['audit_timing']['wall_seconds']+.5,'prior actual whole audit tail')
 capture={};closed(grant['failed_capture'],tuple(CAPTURE_PINS))
 for role,pin in CAPTURE_PINS.items():capture[role]=pinned(grant['failed_capture'][role],pin)
 c=parse(capture['result']);o=parse(capture['outer']);eo=parse(capture['external_outer'])
 cg=parse(pinned(grant['capture_grant'],CAPTURE_GRANT_PIN));decision=pinned(grant['decision'],DECISION_PIN)
 need(c['status']=='INCOMPLETE_NO_DATA_IMPORT_CAPTURE' and c['capture_complete'] is False and c['subject_complete'] is False
  and c['saved_data_checks_complete'] is False and c['numpy_import_attempted'] is True and len(c['registries'])==1
  and c['registries'][0]['label']=='before-numpy' and len(c['registries'][0]['rows'])==94 and len(c['files'])==62,
  'capture remains failed with no post-import baseline')
 need(c['authority']['grant']==CAPTURE_GRANT_PIN and c['authority']['original_plan']==ORIGINAL_PLAN
  and cg['prior_work']==CAPTURE_PRIOR and cg['cumulative_limits']==CURRENT_CAPS,'exact prior isolated capture authority')
 ad=parse(capture['stdout']);ead=parse(capture['external_stdout'])
 need(same(ad['result'],CAPTURE_PINS['result']) and ad['capture_complete'] is False and ad['exit_code']==1
  and same(ead['result'],CAPTURE_PINS['outer']) and ead['exit_code']==1,'actual two-level capture advertisement binding')
 need(o['status']=='REFUSED' and o['exit_code']==o['child_exit_code']==eo['exit_code']==1
  and capture['exit']==capture['external_exit']==b'1\n' and capture['stderr']==capture['external_stderr']==b''
  and eo['command']==o['launcher_command'] and eo['stdout_bytes']==len(capture['external_stdout']) and eo['stderr_bytes']==0,
  'captured owned and external refusal preserved')
 need(eo['elapsed_wall_seconds']<=o['launcher_sample']['wall_seconds']+2<=32,'captured actual wrapper tail')
 need(o['job_accounting']['active_processes']==0 and o['terminal_cpu_accounting'] is True,'captured owned terminal accounting')
 sources=positive_pins(grant['source_bindings'],256*KIB)
 previous={path(k) for space in ('source_bindings','runtime_bindings','runtime_empty_bindings') for k in original[space]}
 need(all(p.is_relative_to(WORK) for p in sources) and all(WORK/n in sources for n in REQUIRED3)
  and not sources&previous,'bounded new source closure disjoint from original authority')
 for key,pin in grant['source_bindings'].items():read(path(key),256*KIB,dict(path=key,**pin))
 need(grant['source_bindings'].get(SELF.relative_to(ROOT).as_posix())==dict(bytes=SELF.stat().st_size,sha256=args.self_sha256.lower()),'new held executed audit source')
 need(grant['prior_work']==AUDIT3_PRIOR and grant['resource_allowance']==dict(entered=ENTERED,preparation=RECOVERY_PREP,audit=LIMITS,cumulative_limits=CURRENT_CAPS),'retained entered capture phase and remaining finite audit grant')
 need(all(AUDIT3_PRIOR[k]+RECOVERY_PREP[k]+LIMITS[k]<=CURRENT_CAPS[k] for k in BASE),'remaining full reserve fits unchanged phase')
 closed(grant['commands'],('audit',));actual=list(sys.orig_argv)
 need(actual[:5]==[str(Path(sys.executable).resolve()),'-I','-S','-B',str(SELF)],'isolated fixed source invocation')
 expected=[args.recovery_grant_sha256 if v=='ACTUAL_AUDIT3_GRANT_SHA256' else v for v in grant['commands']['audit']]
 need(expected==actual and grant['commands']['audit'].count('ACTUAL_AUDIT3_GRANT_SHA256')==1,'exact granted audit3 argv')
 RECOVERY=grant;RECOVERY_REF=gr;OLD_AUDIT=old
 return dict(grant=gr,original_plan=ORIGINAL_PLAN,failed_audit2=grant['failed_audit2'],failed_capture=grant['failed_capture'],
  capture_grant=CAPTURE_GRANT_PIN,decision=DECISION_PIN,prior_work=AUDIT3_PRIOR,preparation_allowance=RECOVERY_PREP,
  original_subject_remains_refused=True,capture_complete=False,post_import_baseline_equivalence=False,
  original_runtime_authority_unchanged=True,historical_cpu_accounting_complete=False)


def failed_preparation(plan):
 # Exact prior failed attempt; zero stdout has an evidence role, never a positive source role.
 pins={'outer':('outer.json',3150,'23ff1213d9705eaf2785465a1044e7212b945a50341acc3ccb1ce81fa1c78ae6'),'stderr':('stderr.bin',1364,'bda56ca8025fa39f77e305f7f6ed000b9eae335ad76da5a1c64456f68adcfe95'),'stdout':('stdout.bin',0,EMPTY),'exit':('exit.txt',2,'4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865'),'note':('failure.md',3108,'d8b7cdcade03930c299631f7ed1c5f86ec0e2db819dd3714aa91832cc4f90c79')}
 refs={};data={}
 for role,(suffix,n,h) in pins.items():
  p=WORK/('local-image-probe-preparation-1-'+suffix);r=dict(path=p.relative_to(ROOT).as_posix(),bytes=n,sha256=h)
  if n:need(plan['source_bindings'].get(r['path'])==dict(bytes=n,sha256=h),'exact positive failed preparation evidence in source closure')
  else:
   need(role=='stdout' and n==0 and h==EMPTY,'sole exact empty prior stdout role')
   need(all(path(k)!=p for space in ('source_bindings','runtime_bindings','runtime_empty_bindings') for k in plan[space]),'historical empty stdout excluded by resolved identity from all executable namespaces')
  data[role],refs[role]=read(p,n,r)
 outer=parse(data['outer']);need(outer['exit_code']==1 and outer['stdout_bytes']==0 and outer['stderr_bytes']==1364 and data['exit']==b'1\n' and b'preparation including reserved final CPU/wall tail' in data['stderr'],'actual earlier preparation refusal without assigning a unique CPU or wall cause')
 return refs
def authority(args):
 raw,sr=read(SELF,128*KIB);need(sr['sha256']==args.self_sha256.lower(),'executed audit source authority')
 plan,pr=released(args.plan,args.plan_sha256,640*KIB)
 need(path(pr['path'])==HERE/'local-image-probe-plan-1.json','actual fixed plan')
 closed(plan,('schema','source_bindings','runtime_bindings','runtime_empty_bindings','baseline_audit','baseline_outer','native_audit','resource_authorization','prior_work','python_executable','commands'))
 need(plan['schema']=='m193c-local-image-probe-plan-v1','actual plan schema')
 need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and not sys._xoptions and path(plan['python_executable']['path'])==Path(sys.executable).resolve(),'current pinned audit interpreter/cwd/flags');read(Path(sys.executable),128*MIB,plan['python_executable'])
 for space in ('source_bindings','runtime_bindings','runtime_empty_bindings'):
  need(type(plan[space]) is dict and 1<=len(plan[space])<=8192,'finite original authority namespace')
  for key,pin in plan[space].items():
   closed(pin,('bytes','sha256'));need(type(key) is str and type(pin['bytes']) is int and type(pin['sha256']) is str and len(pin['sha256'])==64 and (pin['bytes']==0 and pin['sha256']==EMPTY if space=='runtime_empty_bindings' else pin['bytes']>0),'typed source/runtime role')
   if space=='source_bindings':read(path(key),128*MIB,dict(path=key,**pin))
 need(not set(plan['runtime_bindings'])&set(plan['runtime_empty_bindings']),'disjoint runtime namespaces')
 runtime_paths=[path(k) for space in ('runtime_bindings','runtime_empty_bindings') for k in plan[space]];need(len(runtime_paths)==len(set(runtime_paths)),'unique resolved runtime roles')
 for name,(n,h) in PINS.items():
  r=dict(path=(HERE/name).relative_to(ROOT).as_posix(),bytes=n,sha256=h);need(plan['source_bindings'].get(r['path'])=={k:r[k] for k in ('bytes','sha256')},'held producer source in original plan');read(HERE/name,128*KIB,r)
 old_source=dict(path=ORIGINAL_AUDITOR.relative_to(ROOT).as_posix(),bytes=OLD_AUDIT_PINS['source'][1],sha256=OLD_AUDIT_PINS['source'][2]);need(plan['source_bindings'].get(old_source['path'])=={k:old_source[k] for k in ('bytes','sha256')},'original prospective checker bound before subject; new SELF is separately authorized')
 need(plan['prior_work']=={k:BASE[k]+PREP[k] for k in BASE},'nonrefunded exact prior')
 baseline=saved(plan['baseline_audit']);bo=saved(plan['baseline_outer']);native=saved(plan['native_audit']);grant=saved(plan['resource_authorization'])
 need(baseline['status']=='PASS_SAVED_REAL_ACCOUNTING_REPAIR_V3_OUTCOME_AUDIT' and baseline['subject_complete'] is True and baseline['actual_final_work']==BASE and baseline['cpu_accounting_complete'] is False,'exact prior outcome/cost history')
 need(bo['exit_code']==0 and bo['stderr_bytes']==0 and bo['stdout_bytes']==plan['baseline_audit']['bytes'] and bo['elapsed_wall_seconds']<=baseline['audit_timing']['wall_seconds']+baseline['audit_publication_allowance']['wall_seconds'],'prior actual audit tail')
 closed(grant['failed_preparation'],('outer','stderr','stdout','exit','note'))
 for r in grant['failed_preparation'].values():
  closed(r,('path','bytes','sha256'));need(type(r['path']) is str and type(r['bytes']) is int and r['bytes']>=0 and type(r['sha256']) is str and len(r['sha256'])==64,'typed actual failed-evidence FileRef; false is not zero')
 subject_ledger=saved(dict(path=(HERE/'local-image-probe-ledger.json').relative_to(ROOT).as_posix(),bytes=PINS['local-image-probe-ledger.json'][0],sha256=PINS['local-image-probe-ledger.json'][1]));need(subject_ledger['preparation_attempts']==dict(failed=FAILED_PREP,current=CURRENT_PREP),'exact subject ledger failed/current preparation allocations')
 need(grant==dict(schema='m193c-local-image-resource-authorization-v1',baseline_audit=plan['baseline_audit'],baseline_outer=plan['baseline_outer'],retained_work=BASE,previous_limits=OLD_CAPS,new_limits=CAPS,phase_allowance=PHASE,preparation_allowance=PREP,subject_allowance=SUBJECT,audit_allowance=LIMITS,preparation_attempts=dict(failed=FAILED_PREP,current=CURRENT_PREP),failed_preparation=failed_preparation(plan),scope='ONE_FIXED_LOCAL_IMAGE_PROBE; NO_RETIRED_COST_REFUND; NO_GEOMETRY_ADMISSION'),'complete closed scoped phase resource grant')
 oldplan=saved(baseline['external']['plan']);need(all(plan['source_bindings'].get(k)==v for k,v in oldplan['source_bindings'].items()),'preserved old positive source closure')
 need(native['status']=='PASS_SAVED_SENSOR_WHITE_ARTIFACT_OUTCOME_AUDIT','native metadata authority only')
 frames={i:native['frames'][i] for i in ORIGINAL}
 need(all(f['ordinal']==i and f['original_index']==ORIGINAL[i] and f['tiff']['bytes']==197798267 for i,f in frames.items()),'four frozen native image roles')
 parent,rr=released(args.result,args.result_sha256,64*KIB);need(path(rr['path'])==OUT/'result.json','parent canonical location')
 outer,orr=released(args.outer,args.outer_sha256,64*KIB)
 cr,console=read(args.console,256*KIB);need(console['sha256']==args.console_sha256.lower(),'actual console pin')
 er,exitref=read(args.exit,1024);need(exitref['sha256']==args.exit_sha256.lower(),'actual exit pin');exit_code=int(er.decode().strip())
 expected=[pr['sha256'] if v=='ACTUAL_PLAN_SHA256' else v for v in plan['commands']['parent']]
 need(outer['command']==expected and outer['exit_code']==exit_code,'exact actual outer argv/exit')
 wall=outer.get('elapsed_wall_seconds',outer.get('wall_seconds'));need(typed_number(wall) and wall>=0,'actual whole parent wall')
 worker=None;wr=None;wp=OUT/'worker/result.json'
 if wp.exists():
  worker,wr=J(wp,64*KIB)
  if parent.get('worker_result') is not None:need(same(parent['worker_result'],wr),'linked worker canonical')
  else:need(args.worker_sha256 is not None and wr['sha256']==args.worker_sha256.lower(),'explicit unlinked worker authority')
 if args.worker_sha256 is not None:need(wr is not None and wr['sha256']==args.worker_sha256.lower(),'released actual worker pin')
 if parent.get('status')==COMPLETE:need(parent.get('plan') is not None,'positive parent actual plan association')
 if worker is not None and worker.get('status')==COMPLETE:need(worker.get('plan') is not None,'positive worker actual plan association')
 if parent.get('plan') is not None:need(same(parent['plan'],pr),'parent plan association')
 if worker is not None and worker.get('plan') is not None:need(same(worker['plan'],pr),'worker plan association')
 summary=dict(plan=pr,parent=rr,worker=wr,outer=orr,console=console,exit=exitref,audit_source=sr,actual_exit_code=exit_code,actual_outer_wall_seconds=wall,prior_work=plan['prior_work'],native_image_payloads_opened=0)
 return plan,frames,parent,worker,summary


def numpy_runtime(plan):
 global NP,RUNTIME_INSPECTOR,PREFLIGHT
 need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.no_user_site==1 and sys.flags.ignore_environment==1
  and sys.flags.safe_path is True and sys.dont_write_bytecode,'actual isolated no-site startup flags')
 python=Path(sys.executable).resolve();package=python.parent/'Lib/site-packages'
 expected=[str(python.parent/'python312.zip'),str(python.parent/'DLLs'),str(python.parent/'Lib'),str(python.parent)]
 need(sys.path==expected,'literal isolated initial search path')
 for p in (python.parent/'python312._pth',python.parent/'python._pth',python.parent/'pyvenv.cfg',python.parent.parent/'pyvenv.cfg'):
  need(not p.exists(),'no alternate isolated startup configuration')
 need(not any(k in sys.modules for k in ('site','sitecustomize','usercustomize','numpy')),'no prior site or NumPy import')
 pins={}
 for space in ('source_bindings','runtime_bindings','runtime_empty_bindings'):
  for key,v in plan[space].items():
   p=path(key);need(p not in pins,'unique actual source/runtime paths');pins[p]=dict(path=key,**v)
 for key,v in RECOVERY['source_bindings'].items():
  p=path(key);need(p not in pins,'no original authority replacement');pins[p]=dict(path=key,**v)
 helperraw,_=read(RUNTIME_HELPER,32*KIB,pins[RUNTIME_HELPER])
 ns=dict(__name__='_m193c_audit3_runtime',types=types,sys=sys,os=os,Path=Path,importlib=importlib,read_identities=READ_IDENTITIES)
 exec(compile(helperraw,str(RUNTIME_HELPER),'exec'),ns)
 RUNTIME_INSPECTOR=ns['Inspector'](pins,read,timer,runtime_write,ROOT,SELF,python,package)
 for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[k]='1'
 sys.path.append(str(package))
 import numpy as np
 NP=np
 before=RUNTIME_INSPECTOR.snapshot('before-data')
 controls=RUNTIME_INSPECTOR.commission()
 need(sys.path==expected+[str(package)] and not any(k in sys.modules for k in ('site','sitecustomize','usercustomize')),'unchanged isolated package path and no site processing')
 PREFLIGHT=True
 return dict(numpy_version=types.ModuleType.__dict__['__dict__'].__get__(np,types.ModuleType).get('__version__'),
  before_data=before,metadata_controls=controls,preflight_verified=True,source=ref(RUNTIME_HELPER,helperraw),
  post_import_baseline_equivalence=False,scope='Actual loaded module-source authority before any saved numerical payload read; no captured post-import population baseline exists.')


def runtime_write(label,record,cap):
 need(label in ('before-data','after-data'),'fixed runtime output role')
 p=WORK/('independent-local-image-probe-audit-3-runtime-'+label+'.json');raw=encoded(record)
 if len(raw)>cap:
  RUNTIME_OVERFLOW[label]=dict(actual_bytes=len(raw),sha256=sha(raw),complete_record_retained=False)
  raw=encoded(dict(schema='m193c-passive-runtime-authority-overflow-v1',label=label,
   overflow=RUNTIME_OVERFLOW[label],aliases=len(record['rows']),errors=len(record['errors']),
   prefix_strings=[x[:256] for x in record['strings'][:4]],prefix_truncated=True,scope='Incomplete metadata overflow; no runtime/data admission.'))
  need(len(raw)<=16*KIB,'bounded runtime overflow terminal')
 with p.open('xb') as f:need(f.write(raw)==len(raw),'full runtime record write');f.flush();os.fsync(f.fileno())
 r=ref(p,raw);RUNTIME_RECEIPTS[label]=r
 need(label not in RUNTIME_OVERFLOW,'runtime full census serialization exceeded declared extent')
 return r


def runtime_final(result):
 if RUNTIME_INSPECTOR is None:return
 inspector=RUNTIME_INSPECTOR;label=inspector.pending_label
 if label is not None and label not in RUNTIME_RECEIPTS and inspector.pending is not None:
  try:
   value=inspector.pending;record=inspector.pack(label,value['rows'],value['errors'],False,dict(added=[],missing=[],rebound=[],changed=[]))
   record.update(incomplete_inspection=True,inspection_pass=inspector.pending_pass,processed=value['processed'],total=value['total'])
   runtime_write(label,record,256*KIB)
  except BaseException:result['runtime_partial_publication_error']=error()
 result['checker_runtime_records']=dict(RUNTIME_RECEIPTS)
 result['checker_runtime_overflow']=dict(RUNTIME_OVERFLOW)
 result['checker_runtime_observations']=dict(inspector.observations)
 result['checker_runtime_controls']=inspector.controls
 result['runtime_preflight_verified']=PREFLIGHT

def array(spec,expected_path,shape,dtype):
 closed(spec,('file','dtype','shape'));need(spec['dtype']==dtype and spec['shape']==list(shape) and path(spec['file']['path'])==expected_path,'exact saved array layout/role')
 raw,r=read(expected_path,129*129*6,spec['file'],payload=True)
 need(len(raw)==math.prod(shape)*NP.dtype(dtype).itemsize,'exact binary array extent')
 a=NP.frombuffer(raw,dtype=dtype).reshape(shape);need(NP.isfinite(a).all(),'finite saved array');return a,r

def projection_predicate(rgb,f32):
 expected=NP.sum(rgb.astype(NP.float64)*NP.asarray(LUMA,NP.float64),axis=2);u=2.**-24
 return bool(NP.all(NP.abs(f32.astype(NP.float64)-expected)<=7*u/(1-7*u)*NP.abs(expected)+1e-9))

def inputs(value,prefix):
 closed(value,('reference_rgb','source_rgb','reference_f32','source_f32'));arrays=[];summary=[]
 for role in ('reference','source'):
  rgb,rr=array(value[role+'_rgb'],OUT/'worker'/(prefix+'-'+role+'-rgb.u16'),(129,129,3),'<u2')
  f32,fr=array(value[role+'_f32'],OUT/'worker'/(prefix+'-'+role+'.f32'),(129,129),'<f4')
  expected=NP.sum(rgb.astype(NP.float64)*NP.asarray(LUMA,NP.float64),axis=2)
  difference=NP.abs(f32.astype(NP.float64)-expected);u=2.**-24
  # Seven binary32 rounding factors bound coefficient rounding, three products and two additions; all terms nonnegative.
  bound=7*u/(1-7*u)*NP.abs(expected)+1e-9
  need(projection_predicate(rgb,f32),'independent scalar-coefficient projection bound')
  arrays.append((rgb,f32));summary.append(dict(rgb=rr,f32=fr,maximum_projection_error_dn=float(NP.max(difference)),maximum_rounding_bound_dn=float(NP.max(bound))))
 return arrays,summary

def spatial_candidates(a32,b32,coarse,private_name):
 # Independent f64 means/window formula and direct sliced dot products: no FFT or producer estimator import.
 x=NP.arange(129,dtype=NP.float64);window=NP.ones(129,dtype=NP.float64)
 left=x<16;right=x>112;window[left]=.5*(1+NP.cos(NP.pi*(x[left]/16-1)));window[right]=.5*(1+NP.cos(NP.pi*((x[right]-128)/16+1)))
 w=window[:,None]*window[None,:];a=a32.astype(NP.float64);b=b32.astype(NP.float64);a=(a-NP.mean(a))*w;b=(b-NP.mean(b))*w
 total=float(NP.sqrt(NP.sum(a*a)*NP.sum(b*b)));lags=[]
 def add(q):
  q=tuple(int(v) for v in q)
  if max(abs(v) for v in q)<=128 and q not in lags:lags.append(q)
 add((0,0))
 if coarse is not None:
  cy,cx=coarse
  for q in [(cy,cx),(cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1),(-cy,-cx)]:add(q)
 if private_name in TRUTH:add(tuple(int(round(-v)) for v in TRUTH[private_name]))
 if private_name=='periodic' and coarse is not None:
  for dy,dx in ((16,0),(-16,0),(0,16),(0,-16)):add((coarse[0]+dy,coarse[1]+dx))
 need(len(lags)<=12,'fixed bounded direct-lag population');rows=[]
 for dy,dx in lags:
  timer();ay=slice(max(dy,0),min(129,129+dy));by=slice(max(-dy,0),min(129,129-dy));ax=slice(max(dx,0),min(129,129+dx));bx=slice(max(-dx,0),min(129,129-dx))
  aa=a[ay,ax];bb=b[by,bx];dot=float(NP.sum(aa*bb));overlap=float(NP.sqrt(NP.sum(aa*aa)*NP.sum(bb*bb)))
  global_value=dot/total if total else None;overlap_value=dot/overlap if overlap else None
  need(all(v is None or math.isfinite(v) and abs(v)<=1+1e-12 for v in (global_value,overlap_value)),'finite direct Cauchy bounds')
  rows.append(dict(alignment_dydx=list((dy,dx)),overlap_pixels=int(aa.size),global_energy_normalized=global_value,overlap_energy_normalized=overlap_value))
 return rows

RESULT_KEYS=('schema','status','reason','feature_displacement_source_minus_reference_dydx_native','alignment_to_apply_source_dydx_native','coarse_alignment_dydx_native','peak_global_energy_normalized_correlation','second_local_peak_ratio','input_f32_sha256','std_dn')
REASONS=('FLAT_OR_LOW_CONTRAST','OUTSIDE_FIXED_SEARCH','LOW_CORRELATION','AMBIGUOUS_MULTIPLE_PEAKS','REFINEMENT_INCONSISTENT')
def outcome(value,surface_spec,surface_path,arrays,private_name=None):
 closed(value,RESULT_KEYS);need(value['schema']=='m193c-local-displacement-v1','saved estimator schema')
 a,b=(q[1] for q in arrays);need(value['input_f32_sha256']==[sha(q.astype('<f4',copy=False).tobytes()) for q in (a,b)],'whole actual projected input identities')
 surface,sr=array(surface_spec,OUT/'worker'/surface_path,(65,65),'<f4');std64=[float(NP.std(q.astype(NP.float64))) for q in (a,b)]
 need(type(value['std_dn']) is list and len(value['std_dn'])==2 and all(typed_number(x) and x>=0 for x in value['std_dn']),'recorded finite standard deviations')
 std_delta=[abs(x-y) for x,y in zip(value['std_dn'],std64)]
 # Display the independently re-chosen f64 deviations; don't substitute them for the source's binary32 admission boundary.
 status=value['status'];reason=value['reason'];coarse=value['coarse_alignment_dydx_native'];peak=value['peak_global_energy_normalized_correlation'];ratio=value['second_local_peak_ratio'];shift=value['alignment_to_apply_source_dydx_native'];disp=value['feature_displacement_source_minus_reference_dydx_native']
 need(status in ('REFUSED','RETURNED_LOCAL_TRANSLATION'),'closed outcome disposition')
 if reason=='FLAT_OR_LOW_CONTRAST':
  need(status=='REFUSED' and min(value['std_dn'])<1 and coarse is peak is ratio is shift is disp is None and bool(NP.all(surface==0)),'actual flat branch operands')
 else:
  need(min(value['std_dn'])>=1 and type(coarse) is list and len(coarse)==2 and all(type(v) is int and abs(v)<=128 for v in coarse),'actual finite coarse branch')
  need(typed_number(peak) and typed_number(ratio) and ratio<=1+1e-6,'finite recorded peak/competitor')
  need(float(NP.max(surface))<=peak+1e-7,'saved central surface cannot exceed global winner')
  if max(abs(v) for v in coarse)<=32:need(float(surface[coarse[0]+32,coarse[1]+32])==peak,'exact saved coarse peak sample')
  if status=='RETURNED_LOCAL_TRANSLATION':
   need(reason is None and max(abs(v) for v in coarse)<=32 and peak>=.45 and ratio<=.90,'unchanged returned coarse gates')
   need(type(shift) is list and type(disp) is list and len(shift)==len(disp)==2 and all(typed_number(v) for v in shift+disp),'actual finite returned components')
   need(all(disp[i]==-shift[i] and abs(shift[i])<=32 and abs(shift[i]-coarse[i])<=1 and abs(100*shift[i]-round(100*shift[i]))<=.0004 for i in range(2)),'sign/range/refinement-grid witness')
  else:
   need(reason in REASONS and shift is disp is None,'recorded refusal has no admitted displacement')
   if reason=='LOW_CORRELATION':need(max(abs(v) for v in coarse)<=32 and peak<.45,'low-correlation first failing gate')
   if reason=='AMBIGUOUS_MULTIPLE_PEAKS':need(max(abs(v) for v in coarse)<=32 and peak>=.45 and ratio>.90,'ambiguity first failing gate')
   if reason=='REFINEMENT_INCONSISTENT':need(max(abs(v) for v in coarse)<=32 and peak>=.45 and ratio<=.90,'refinement refusal preceding gates')
   if reason=='OUTSIDE_FIXED_SEARCH' and max(abs(v) for v in coarse)<=32:need(peak>=.45 and ratio<=.90,'refined outside refusal preceding gates')
 truth_error=None
 if private_name in TRUTH and status=='RETURNED_LOCAL_TRANSLATION':truth_error=max(abs(disp[i]-TRUTH[private_name][i]) for i in range(2))
 direct=spatial_candidates(a,b,coarse,private_name)
 q=next((r for r in direct if r['alignment_dydx']==coarse),None)
 delta=None if q is None or q['global_energy_normalized'] is None or peak is None else q['global_energy_normalized']-peak
 return dict(status=status,reason=reason,coarse_alignment=coarse,feature_displacement=disp,recorded_peak=peak,recorded_competitor_ratio=ratio,surface=sr,literal_error_native=truth_error,f64_standard_deviation_dn=std64,recorded_std_difference_dn=std_delta,direct_lag_checks=direct,direct_coarse_minus_recorded_peak=delta,scope='Fixed selected-lag f64 spatial re-choice only; no independent global-peak superiority or subpixel optimizer reconstruction.')

def control_expected(name,result):
 if name in ('zero','integer','fractional','differential-blur'):return result['status']=='RETURNED_LOCAL_TRANSLATION' and result['literal_error_native'] is not None and result['literal_error_native']<=.15
 if name=='flat':return result['status']=='REFUSED' and result['reason']=='FLAT_OR_LOW_CONTRAST'
 if name=='unrelated':return result['status']=='REFUSED'
 if name=='periodic':return result['status']=='REFUSED' and result['reason']=='AMBIGUOUS_MULTIPLE_PEAKS'
 if name=='outside-search':return result['status']=='REFUSED' and result['reason']=='OUTSIDE_FIXED_SEARCH' and result['coarse_alignment'] is not None and max(abs(v) for v in result['coarse_alignment'])>32
 raise ValueError('unlisted private control')

BLOBS=((15.5,21.5,1.5,2.),(26.,99.,3.5,-1.4),(38.5,59.5,2.5,1.1),(47.5,111.5,5.5,.9),(60.5,18.,2.,-1.7),(71.,75.5,4.,1.5),(83.,44.5,3.,-1.2),(94.,105.5,2.,1.8),(108.5,28.5,4.5,1.),(115.5,87.,2.5,-1.3))
COMPONENTS=((1,2,1.2,.1),(2,-3,.8,1.3),(3,5,.6,-.4),(4,1,.5,2.1),(5,-7,.4,.7),(7,4,.35,-1.1),(9,-2,.3,1.9),(11,8,.24,-2.3),(13,-5,.2,.45),(17,3,.15,2.7))

def private_pixels(name,arrays):
 # Different binary64 continuous evaluation; <=1 DN explicitly tolerates nearest-integer boundary changes.
 y,x=NP.indices((129,129),dtype=NP.float64);values=[]
 for role in range(2):
  if name in TRUTH:
   dy,dx=(0.,0.) if role==0 else TRUTH[name];blur=2. if role==1 and name=='differential-blur' else 0.;yy=y-dy;xx=x-dx;v=NP.full((129,129),20000.)
   for cy,cx,sigma,amp in BLOBS:
    variance=sigma*sigma+blur*blur;v+=3000*amp*sigma*sigma/variance*NP.exp(-((yy-cy)**2+(xx-cx)**2)/(2*variance))
   for ky,kx,amp,phase in COMPONENTS:
    gain=math.exp(-2*math.pi**2*blur*blur*(ky*ky+kx*kx)/(129*129));v+=150*amp*gain*NP.sin(2*math.pi/129*(ky*yy+kx*xx)+phase)
  elif name=='flat':v=NP.full((129,129),20000.+1000*role)
  elif name=='unrelated':v=20000+3000*NP.sin(2*math.pi*(x/17 if role==0 else y/19))
  elif name=='periodic':v=20000+3000*(NP.sin(2*math.pi/16*(x-(2.25 if role else 0)))+NP.cos(2*math.pi/16*(y+(1.5 if role else 0))))
  else:raise ValueError('fixed private pixel role')
  rgb=arrays[role][0];need(bool(NP.all(rgb==rgb[:,:,:1])),'equal-channel actual private RGB16');expected=NP.rint(v);delta=NP.abs(rgb[:,:,0].astype(NP.float64)-expected)
  need(float(NP.max(delta))<=1 and (name!='flat' or not bool(NP.any(delta))),'independently evaluated continuous/quantized fixture')
  values.append(dict(maximum_integer_difference_dn=float(NP.max(delta)),different_pixels=int(NP.count_nonzero(delta)),scope='Binary64 continuous fixture re-choice; at most one quantization DN, not original binary32 bit equivalence.'))
 return values

def reader_control(value):
 import struct
 need(type(value['cases']) is list and len(value['cases'])==2,'two actual private endian reader cases');summary=[]
 for row,endian,label in zip(value['cases'],('<','>'),('le','be')):
  p=OUT/'worker/controls'/('reader-'+label+'.tiff');raw,rr=read(p,256*KIB,row['file'],fixture=True)
  need(row['endian']==endian and row['rect']==[5,7,129,129] and raw[:2]==(b'II' if endian=='<' else b'MM'),'actual endian/rectangle fixture role')
  def unpack(fmt,at):
   n=struct.calcsize(endian+fmt);need(type(at) is int and 0<=at<=len(raw)-n,'private fixture bounded range');return struct.unpack_from(endian+fmt,raw,at)
  need(unpack('H',2)==(42,),'classic private TIFF');start=unpack('I',4)[0];count=unpack('H',start)[0];need(count==11 and unpack('I',start+2+count*12)==(0,),'literal private single IFD');tags={}
  for i in range(count):
   at=start+2+12*i;tag,typ,n=unpack('HHI',at);need(tag not in tags and typ in (2,3,4) and 0<n<=4096,'private IFD entry')
   size=n*{2:1,3:2,4:4}[typ];pos=at+8 if size<=4 else unpack('I',at+8)[0];need(0<=pos<=len(raw)-size,'private tag extent');tags[tag]=raw[pos:pos+size] if typ==2 else unpack(('H' if typ==3 else 'I')*n,pos)
  need(set(tags)=={256,257,258,259,262,270,273,277,278,279,305} and tags[256]==(137,) and tags[257]==(139,) and tags[258]==(16,16,16) and tags[259]==(1,) and tags[262]==(2,) and tags[277]==(3,) and tags[278]==(17,),'literal private pixel layout')
  offsets,counts=tags[273],tags[279];need(len(offsets)==len(counts)==9,'cross-strip fixture extent');rows=[]
  for y in range(5,134):
   idx,within=divmod(y,17);at=offsets[idx]+(within*137+7)*6;need(counts[idx]==min(17,139-17*idx)*137*6 and offsets[idx]<=at<=offsets[idx]+counts[idx]-129*6,'independent strided patch range');rows.append(raw[at:at+129*6])
  actual=NP.frombuffer(b''.join(rows),dtype=endian+'u2').reshape(129,129,3).astype('<u2');y,x=NP.indices((129,129),dtype=NP.uint16);y+=5;x+=7;expected=NP.stack((100+3*y+x,200+y+2*x,300+2*y+3*x),axis=2).astype('<u2')
  h=sha(actual.tobytes());need(bool(NP.array_equal(actual,expected)) and row['literal_rgb_sha256']==h and type(row['actual_rgb_sha256']) is str and len(row['actual_rgb_sha256'])==64,'independently indexed literal strip bytes')
  need(typed_number(row['projection_maximum_error_dn']) and 0<=row['projection_maximum_error_dn']<=.001 and type(row['out_of_image_rejected']) is bool and type(row['passed']) is bool,'reader scalar witness types')
  # No separately saved projection exists here: the exact output remains a producer witness, bounded by the later saved-patch projection checks.
  passed=row['actual_rgb_sha256']==row['literal_rgb_sha256'] and row['out_of_image_rejected'] and row['projection_maximum_error_dn']<=.001;need(row['passed']==passed,'reader actual expected disposition');summary.append(dict(record=rr,rgb_sha256=h,passed=passed,invalid_rectangle_is_outside=(11+129>139),projection_scope='Recorded producer scalar error only; independent projection uses retained private/real f32 arrays.'))
 return all(x['passed'] for x in summary),summary

def namespace_receipts(plan,worker):
 result={}
 for key,name,cap in (('runtime_namespace_controls','runtime-namespace-controls.json',8*KIB),('runtime_intake','runtime-intake.json',4*KIB)):
  p=OUT/'worker'/name
  if not p.exists():need(worker.get(key) is None,'absent namespace receipt association');continue
  v,r=J(p,cap);linked=worker.get(key) is not None
  if linked:need(same(worker[key],r),'namespace receipt exact link')
  result[key]=dict(record=r,linked=linked)
  if key=='runtime_intake':
   both={**plan['runtime_bindings'],**plan['runtime_empty_bindings']};need(v['schema']=='m193c-local-image-runtime-intake-v1' and v['declared_files']==len(both) and v['empty_files']==len(plan['runtime_empty_bindings']) and v['declared_bytes']==sum(x['bytes'] for x in both.values()) and v['complete_namespace_sha256']==sha(encoded(both)),'actual runtime intake metadata witness')
  else:
   original=sha(encoded([plan['runtime_bindings'],plan['runtime_empty_bindings']]));ids=['actual-positive-and-empty-runtime','zero-as-source','false-empty','nonzero-empty','wrong-empty-sha','overlapping-runtime-path','unknown-empty-file-role','restored-namespace'];need([x['id'] for x in v['rows']]==ids and v['complete_namespace_before_sha256']==v['complete_namespace_after_sha256']==original,'exact namespace restoration')
   derived=[]
   for i,row in enumerate(v['rows']):
    want=i not in (0,7);need(row['expected_refusal'] is want and type(row['passed']) is bool and (row['error'] is None or type(row['error']) is str),'namespace expected fault witnesses');passed=(row['error'] is not None)==want;need(row['passed']==passed,'recorded namespace reject disposition');derived.append(passed)
   need(v['passed']==all(derived) and v['positive_count']==len(plan['runtime_bindings']) and v['empty_count']==len(plan['runtime_empty_bindings']),'namespace counts/result')
   empty=v['actual_empty_file'];need(plan['runtime_empty_bindings'].get(empty['path'])=={k:empty[k] for k in ('bytes','sha256')},'actual empty role');read(path(empty['path']),0,empty)
   result[key]['passed']=v['passed']
 return result

def private_controls(worker):
 linked=worker.get('controls',[]);need(type(linked) is list and len(linked)<=11 and [r['id'] for r in linked]==list(CONTROL[:len(linked)]),'ordered private control prefix');results=[];cache={};failed=False
 for i,name in enumerate(CONTROL):
  p=OUT/'worker/controls'/(name+'.json')
  if not p.exists():need(i>=len(linked),'declared control missing');break
  need(not failed,'no later control after literal failed gate');value,r=J(p,64*KIB);need(value['schema']=='m193c-local-image-control-v1' and value['id']==name and type(value['passed']) is bool,'actual private control record')
  islinked=i<len(linked)
  if islinked:need(same(linked[i]['record'],r) and linked[i]['passed']==value['passed'],'whole linked control row')
  else:need(i==len(linked),'at most one unlinked trailing control')
  detail={}
  if name=='rgb16-strip-reader':passed,detail=reader_control(value)
  elif name in PRIVATE:
   arrays,projections=inputs(value['inputs'],'controls/'+name);pixels=private_pixels(name,arrays);s=outcome(value['outcome'],value['surface'],'controls/'+name+'-surface.f32',arrays,name);passed=control_expected(name,s)
   need(value['literal_displacement_dydx_native']==(list(TRUTH[name]) if name in TRUTH else None) and value['maximum_component_error_native']==s['literal_error_native'],'literal control truth/error independent association')
   required={'flat':'FLAT_OR_LOW_CONTRAST','periodic':'AMBIGUOUS_MULTIPLE_PEAKS','outside-search':'OUTSIDE_FIXED_SEARCH'}.get(name);need(value['required_reason']==required,'fixed negative reason')
   detail=dict(outcome=s,projection=projections,continuous_fixture=pixels);cache[name]=(arrays,value['outcome'],s)
  elif name=='observer-output':
   need('fractional' in cache,'observer fixed actual fractional input');arrays,baseline,_=cache['fractional'];rows=value['rows'];modes=['off','on','placebo','restored','after-rejected-mutation'];need([x['mode'] for x in rows]==modes,'fixed observer modes');checks=[];hashes=[]
   for row,mode in zip(rows,modes):
    suffix='after-mutation' if mode=='after-rejected-mutation' else mode;s=outcome(row['outcome'],row['surface'],'controls/observer-'+suffix+'-surface.f32',arrays,'fractional');h=[sha(encoded(row['outcome'])),row['surface']['file']['sha256']];hashes.append(h)
    visits=row['observer_visits'];need(type(visits) is list and len(visits)==(1 if mode in ('on','placebo') else 0),'actual observer visit count')
    if visits:
     need(visits[0]['surface_hash']==h[1],'observer actual complete surface hash')
     if mode=='placebo':need(visits[0]['peak']==visits[0]['mean']==0.,'placebo equal-access zeroed observation')
    checks.append(s)
   need(value['whole_outcome_and_surface_hashes']==hashes and type(value['actual_mutating_observer_rejected']) is bool,'whole observer saved hash records');passed=value['actual_mutating_observer_rejected'] and all(h==hashes[0] for h in hashes)
   detail=dict(outcomes=checks,whole_hashes=hashes,all_literal_truth_pass=all(x['literal_error_native'] is not None and x['literal_error_native']<=.15 for x in checks),matches_original_fractional=all(h[0]==sha(encoded(baseline)) for h in hashes),mutation_rejection_scope='Recorded actual callback exception; independent saved bytes and literal truth checked.')
  else:
   need('fractional' in cache,'literal oracle baseline');baseline=cache['fractional'][1];wrong=parse(encoded(baseline));wrong['feature_displacement_source_minus_reference_dydx_native']=[-v for v in wrong['feature_displacement_source_minus_reference_dydx_native']];a=max(abs(baseline['feature_displacement_source_minus_reference_dydx_native'][i]-TRUTH['fractional'][i]) for i in range(2));b=max(abs(wrong['feature_displacement_source_minus_reference_dydx_native'][i]-TRUTH['fractional'][i]) for i in range(2))
   need(value['original']==baseline and value['wrong_sign']==wrong and value['literal']==list(TRUTH['fractional']) and value['original_error_native']==a and value['wrong_error_native']==b and value['restored_complete_outcome_sha256']==sha(encoded(baseline)),'independent literal-sign destroyer and whole restoration');passed=a<=.15 and b>.15;detail=dict(original_error_native=a,wrong_error_native=b)
  need(value['passed']==bool(passed),'independently derived actual control flag');results.append(dict(id=name,record=r,linked=islinked,passed=bool(passed),detail=detail));failed=not passed
  if not islinked or failed:break
 producer_complete=len(results)==11 and all(x['passed'] and x['linked'] for x in results)
 observer=next((x['detail'] for x in results if x['id']=='observer-output'),{})
 complete=producer_complete and observer.get('all_literal_truth_pass') is True and observer.get('matches_original_fractional') is True
 return dict(controls=results,producer_controls_complete=producer_complete,private_prerequisite_verified=complete,scope='False or unlinked final control retained without granting real work.'),cache
def projection_power(arrays):
 # These audit-only arrays are copies of retained actual pixels; no estimator, image read or new subject call.
 rgb,f32=arrays[0];original=sha(f32.tobytes());changed=f32.copy();changed[0,0]+=NP.float32(1)
 baseline=projection_predicate(rgb,f32);fault=projection_predicate(rgb,changed);restored=projection_predicate(rgb,f32)
 need(baseline and not fault and restored and sha(f32.tobytes())==original,'powered same-predicate +1 DN projection fault/restoration')
 return dict(actual_baseline_pass=baseline,plus_one_dn_rejected=not fault,restored_pass=restored,original_sha256=original,restored_sha256=sha(f32.tobytes()),scope='Checker-only actual saved-pixel mutation; no subject call.')

def real_population(worker,frames,private):
 linked=worker.get('real',[]);need(type(linked) is list and len(linked)<=128 and [x['id'] for x in linked]==REAL_IDS[:len(linked)],'exact ordered declared real prefix');rows=[];record_values={};record_refs={};disjoint=[]
 centres=[((2*j*4688+5)//10,(2*i*7032+5)//10) for j in range(1,5) for i in range(1,5)];offsets=((-96,-96),(-96,96),(96,-96),(96,96))
 for idx,key in enumerate(REAL_IDS):
  p=OUT/'worker/real'/(key+'.json')
  if not p.exists():need(idx>=len(linked),'missing linked real metadata');break
  need(private['producer_controls_complete'],'real record requires all original private gates');v,r=J(p,64*KIB);pair_part,g_part,q_part=key.split('/');pair=tuple(map(int,pair_part.split('-')));g=int(g_part[1:]);q=int(q_part[1:]);cy,cx=centres[g];dy,dx=offsets[q];rect=[cy+dy-64,cx+dx-64,129,129]
  expected=dict(schema='m193c-local-image-patch-v1',id=key,pair=list(pair),original_pair=[ORIGINAL[x] for x in pair],native_images=[frames[x]['tiff'] for x in pair],grid_index=g,grid_centre_yx_native=[cy,cx],quadrant=q,rect_yxhw_native=rect)
  closed(v,(*expected,'inputs','outcome','surface'));need(all(v[k]==value for k,value in expected.items()),'exact real patch population/rectangle/native metadata association')
  need(0<=rect[0]<=4688-129 and 0<=rect[1]<=7032-129,'in-image rectangle metadata');arrays,projection=inputs(v['inputs'],'real/'+key);s=outcome(v['outcome'],v['surface'],'real/'+key+'-surface.f32',arrays)
  islinked=idx<len(linked)
  if islinked:need(same(linked[idx]['record'],r) and linked[idx]['status']==s['status'] and linked[idx]['reason']==s['reason'],'linked real outcome association')
  else:need(idx==len(linked),'one retained unlinked real outcome');
  rows.append(dict(id=key,record=r,linked=islinked,rect_yxhw_native=rect,projection=projection,outcome=s));record_values[key]=v;record_refs[key]=r
  if not islinked:break
 # Full independent point-set nonoverlap for each four-window group. This is rectangle geometry, not displacement accuracy.
 linked_groups=worker.get('disjoint',[]);need(type(linked_groups) is list and len(linked_groups)<=32,'finite linked disjoint population');group_refs=[]
 for a,b in PAIRS:
  for g in range(16):
   p=OUT/'worker/real'/f'{a}-{b}/g{g:02d}-disjoint.json'
   if not p.exists():continue
   keys=[f'{a}-{b}/g{g:02d}/q{q}' for q in range(4)];need(all(k in record_values for k in keys),'disjoint row requires four retained complete patches');v,r=J(p,64*KIB);need(v['schema']=='m193c-local-image-disjoint-v1' and v['pair']==[a,b] and v['grid_index']==g and len(v['patch_records'])==4 and all(same(x,record_refs[k]) for x,k in zip(v['patch_records'],keys)),'disjoint exact complete patch associations')
   rects=[record_values[k]['rect_yxhw_native'] for k in keys]
   for i in range(4):
    for j in range(i):
     y,x,h,w=rects[i];yy,xx,hh,ww=rects[j];need(y+h<=yy or yy+hh<=y or x+w<=xx or xx+ww<=x,'literal pixel-disjoint native windows')
   outcomes=[record_values[k]['outcome'] for k in keys]
   if any(x['status']!='RETURNED_LOCAL_TRANSLATION' for x in outcomes):expected=dict(status='UNAVAILABLE_DISJOINT_EVIDENCE',diagonal_a=None,diagonal_b=None,maximum_difference_native=None)
   else:
    d=[x['feature_displacement_source_minus_reference_dydx_native'] for x in outcomes];first=[(d[0][i]+d[3][i])/2 for i in range(2)];second=[(d[1][i]+d[2][i])/2 for i in range(2)];diff=max(abs(first[i]-second[i]) for i in range(2));expected=dict(status='DISJOINT_DIAGONAL_AGREEMENT' if diff<=.5 else 'DISAGREEMENT',diagonal_a=first,diagonal_b=second,maximum_difference_native=diff)
   need(v['reproducibility']==expected,'exact descriptive opposite-diagonal response');group_refs.append(r);disjoint.append(dict(record=r,pair=[a,b],grid_index=g,**expected))
 need(len(linked_groups)<=len(group_refs) and all(same(a,b) for a,b in zip(linked_groups,group_refs)) and len(group_refs)-len(linked_groups)<=1,'at most one prewritten unlinked disjoint receipt')
 if 'unvisited' in worker and 'planned_controls' in worker:need(worker['unvisited']==REAL_IDS[len(linked):],'canonical unvisited exact suffix')
 return dict(rows=rows,disjoint=disjoint,linked_real_count=len(linked),retained_real_count=len(rows),linked_disjoint_count=len(linked_groups),retained_disjoint_count=len(disjoint),complete_saved_population=len(rows)==len(linked)==128 and len(disjoint)==len(linked_groups)==32,scope='Reproducibility is descriptive texture-weighted local correlation; neither agreement nor sharp peaks establishes real physical displacement truth.'),record_values

def runtime_records(plan,worker):
 summary={};allowed={path(k):v for space in ('source_bindings','runtime_bindings','runtime_empty_bindings') for k,v in plan[space].items()}
 p=OUT/'worker/runtime-modules.json'
 if p.exists():
  v,r=J(p,2*MIB);need(v['schema']=='m193c-local-image-runtime-v1' and type(v['files']) is list and len(v['files'])<=8192 and type(v['modules']) is list and len(v['modules'])<=16384,'finite actual runtime module manifest');seen=set();names=[]
  for f in v['files']:
   pp=path(f['path']);need(pp not in seen and allowed.get(pp)=={k:f[k] for k in ('bytes','sha256')},'unique declared actual runtime file');seen.add(pp);read(pp,128*MIB,f)
  for row in v['modules']:
   need(type(row) is list and len(row)==2 and type(row[0]) is str and type(row[1]) is int and 0<=row[1]<len(v['files']),'actual module alias/index');names.append(row[0])
  need(names==sorted(set(names)),'complete unique sorted module aliases')
  aliases={name:v['files'][i] for name,i in v['modules']}
  for module,source in (('__main__','local-image-probe-run.py'),('m193c_fixed_local_estimator','local-image-probe.py'),('m193c_fixed_native_patches','local-image-patches.py')):
   need(module in aliases and path(aliases[module]['path'])==HERE/source and {k:aliases[module][k] for k in ('bytes','sha256')}==plan['source_bindings'][(HERE/source).relative_to(ROOT).as_posix()],'declared current scientific module binding')
  need('numpy' in aliases and 'scipy' in aliases and 'skimage' in aliases,'recorded expected numerical package aliases')
  linked=worker.get('runtime_modules') is not None
  if linked:need(same(worker['runtime_modules'],r),'linked actual runtime manifest')
  summary['modules']=dict(record=r,linked=linked,files=len(seen),aliases=len(names),alias_binding_sha256=sha(encoded([[name,v['files'][i]] for name,i in v['modules']])),scope='Authenticated actual Python module-file alias witnesses; no runtime dependent-DLL closure or import execution replay.')
 else:need(worker.get('runtime_modules') is None,'missing declared runtime manifest')
 native=[]
 for a,b in PAIRS:
  p=OUT/'worker/real'/f'{a}-{b}/native-file-reads.json'
  if not p.exists():continue
  v,r=J(p,64*KIB);need(len(v['images'])==len(v['receipts'])==2,'two native initial/final read witnesses')
  for image,receipt in zip(v['images'],v['receipts']):
   need(type(receipt) is dict,'typed native receipt')
   if not receipt:continue
   closed(receipt,('initial_identity','layout','initial_hash_verified','final_hash_verified'));ident=receipt['initial_identity'];need(type(ident) is list and len(ident)==6 and all(type(x) is int for x in ident) and ident[2]==image['bytes'] and ident[-1]==1 and ident[4]&1024==0 and receipt['initial_hash_verified'] is True and type(receipt['final_hash_verified']) is bool,'recorded native read identity/status');layout=receipt['layout'];need(layout['shape']==[4688,7032,3] and layout['endian'] in ('<','>') and type(layout['rows_per_strip']) is int and layout['rows_per_strip']>0,'native stored strip layout witness')
   offsets,counts=layout['strip_offsets'],layout['strip_bytes'];need(len(offsets)==len(counts)==math.ceil(4688/layout['rows_per_strip']),'complete native strip witness');ranges=[]
   for i,(off,n) in enumerate(zip(offsets,counts)):
    need(type(off) is type(n) is int and n==min(layout['rows_per_strip'],4688-i*layout['rows_per_strip'])*7032*6 and 8<=off<=image['bytes']-n,'native range metadata witness');ranges.append((off,off+n))
   need(all(x[1]<=y[0] for x,y in zip(sorted(ranges),sorted(ranges)[1:])),'native strips do not overlap')
  native.append(dict(record=r,images=v['images'],initial_complete=all(x.get('initial_hash_verified') is True for x in v['receipts']),final_complete=all(x.get('final_hash_verified') is True for x in v['receipts']),scope='Saved producer full-native-read witness only; checker never opens native images or independently attributes saved pixels to those files.'))
 linked=worker.get('native_reads',[]);need(len(linked)<=len(native) and all(same(x,y['record']) for x,y in zip(linked,native)) and len(native)-len(linked)<=1,'retained linked/unlinked native final receipts');summary['native_reads']=native;return summary
def job_counts(v):
 need(type(v) is dict,'actual Job counter record')
 for k in ('total_user_100ns','total_kernel_100ns','total_cpu_100ns','active_processes'):need(type(v.get(k)) is int and v[k]>=0,'typed nonnegative Job witness')
 need(v['total_cpu_100ns']==v['total_user_100ns']+v['total_kernel_100ns'],'independent actual user/kernel sum');return v['total_cpu_100ns']/1e7

def advertisements(raw):
 values=[]
 for line in raw.splitlines():
  try:v=parse(line)
  except (ValueError,UnicodeError):continue
  if type(v) is dict and v.get('schema')=='m193c-local-image-terminal-v1':values.append(v)
 return values

def terminal_accounting(plan,parent,worker,auth):
 p=OUT/'child-terminal.json';summary=dict(record=None,linked=False,current_job_accounting_complete=False,clean_child=False,terminal_job_cpu_seconds=None);job=None
 if p.exists():
  v,r=J(p,64*KIB);need(v['schema']=='m193c-local-image-child-terminal-v1' and same(v['plan'],auth['plan']),'retained exact Job receipt/plan');linked=parent.get('child_terminal') is not None
  if linked:need(same(parent['child_terminal'],r),'canonical actual Job receipt association')
  job=v['job'];expected=[auth['plan']['sha256'] if s=='ACTUAL_PLAN_SHA256' else s for s in plan['commands']['worker']];need(job['command']==expected and job['limits']==dict(wall_seconds=130,cpu_seconds=85,log_bytes=256*KIB,committed_bytes=1<<30),'exact bounded actual child argv/limits')
  need(type(v['live_queries']) is int and v['live_queries']>=0 and (v['accounting_error'] is None or type(v['accounting_error']) is str),'retained live-accounting metadata')
  cpu=None
  if job['job_accounting'] is not None:cpu=job_counts(job['job_accounting'])
  if v['latest_job'] is not None:
   latest=job_counts(v['latest_job']);need(cpu is None or latest==cpu,'final wrapper observation equals retained terminal Job')
  configured=job.get('configured_job_limits');installed=False
  if configured is not None:
   need(type(configured['flags']) is int and type(configured['committed_bytes']) is int,'typed installed Job memory flags');installed=bool(configured['flags']&0x200 and configured['flags']&0x2000 and configured['committed_bytes']==1<<30)
  drain=job.get('post_exit_drain');drained=False
  if drain is not None:
   need(type(drain['observation_count']) is int and len(drain['observations'])<=16 and drain['observation_count']>=len(drain['observations']),'bounded actual exit-drain witnesses');previous=-1
   for row in drain['observations']:
    value=job_counts(row['accounting']);need(value>=previous and typed_number(row['wall_seconds']) and row['wall_seconds']>=0,'monotone saved drain observations');previous=value
   for role in ('initial_accounting','last_accounting'):
    if drain[role] is not None:job_counts(drain[role])
   drained=drain['completed'] is True and drain['last_accounting'] is not None and drain['last_accounting']['active_processes']==0
  complete=job['terminal_job_accounting'] is True and job['job_accounting'] is not None and job['job_accounting']['active_processes']==0
  memory=job.get('job_memory');memory_ok=False
  if memory is not None:need(type(memory['peak_job_memory_used_bytes']) is int and memory['peak_job_memory_used_bytes']>=0,'actual committed-memory extent');memory_ok=memory['peak_job_memory_used_bytes']<=1<<30
  fixed={k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','PYTHONDONTWRITEBYTECODE')};fixed['PYTHONHASHSEED']='0';need(v['environment_fixed']==fixed and type(v['environment_removed']) is list and v['environment_removed']==sorted(set(v['environment_removed'])),'fixed actual child environment witness')
  logref=job.get('log');logads=[]
  if logref is not None:
   need(path(logref['path'])==OUT/'worker.log','owned child log');raw,_=read(OUT/'worker.log',256*KIB,logref);need(job['log_bytes']==len(raw),'exact actual child log extent');logads=advertisements(raw)
  clean=complete and installed and memory_ok and drained and job['exit_code']==0 and job['error'] is None and job['cleanup_errors']==[] and job['direct_exit_observed'] is True and job['pipe_eof_observed'] is True and job['termination']['attempted'] is False and v['accounting_error'] is None and cpu is not None and cpu<=85 and typed_number(job['wall_seconds']) and 0<=job['wall_seconds']<=130
  if worker is not None and worker.get('status')==COMPLETE:
   expectedad={k:worker[k] for k in ('status','timing_sample','resource_admissible','charged_work_policy')};expectedad.update(schema='m193c-local-image-terminal-v1',result=auth['worker']);need(len(logads)==1 and logads[0]==expectedad,'actual complete child final advertisement/canonical association')
  summary=dict(record=r,linked=linked,current_job_accounting_complete=complete,clean_child=clean,terminal_job_cpu_seconds=cpu,installed_committed_memory_limit=installed,actual_peak_committed_bytes=None if memory is None else memory['peak_job_memory_used_bytes'],actual_child_wall_seconds=job['wall_seconds'],current_job_fields=job['job_accounting'],exit_drain_completed=drained,actual_log=logref,scope='Owned Job CPU is counted once; parent process sample plus reserved tail is not a measured terminal parent CPU.')
 else:need(parent.get('child_terminal') is None,'declared actual Job receipt absent')
 checks={};samples={}
 for role,value in (('parent',parent),('worker',worker)):
  if value is None:continue
  need(value['schema']==('m193c-local-image-probe-run-v1' if role=='parent' else 'm193c-local-image-probe-worker-v1') and value['status'] in ('REFUSED',COMPLETE),'canonical terminal schema/status')
  sample=value.get('timing_sample')
  if sample is None:checks[role]=None;continue
  for k in ('process_cpu_seconds','wall_seconds'):need(typed_number(sample[k]) and sample[k]>=0,'finite terminal sampled cost')
  if sample['job_cpu_seconds'] is not None:need(typed_number(sample['job_cpu_seconds']) and sample['job_cpu_seconds']>=0,'finite Job cost sample')
  if role=='worker':need(sample['job_cpu_seconds'] is None,'worker does not duplicate its containing Job CPU')
  if role=='parent' and summary['current_job_accounting_complete']:need(sample['job_cpu_seconds']==summary['terminal_job_cpu_seconds'],'parent terminal sample exact complete Job association')
  tailcpu,tailwall=(2,5) if role=='parent' else (0,0);admissible=sample['process_cpu_seconds']+(sample['job_cpu_seconds'] or 0)+tailcpu<=(90 if role=='parent' else 85) and sample['wall_seconds']+tailwall<=(140 if role=='parent' else 130);need(value['resource_admissible']==admissible,'independent measured-sample resource predicate')
  charge=dict(SUBJECT)
  if role=='parent':charge['cpu_seconds']=max(90,sample['process_cpu_seconds']+(sample['job_cpu_seconds'] or 0)+2);charge['wall_seconds']=max(140,sample['wall_seconds']+5)
  expectedcharge={k:plan['prior_work'][k]+charge[k] for k in BASE};need(value['charged_work_policy']==expectedcharge and value['unspent_audit_reservation']==LIMITS and value['historical_cpu_accounting_complete'] is False,'nonrefunded recorded subject charge/history')
  capacity=all(expectedcharge[k]+LIMITS[k]<=CAPS[k] for k in BASE);need(value['cumulative_capacity_for_reserved_audit']==capacity,'recorded complete future audit reserve');checks[role]=admissible and capacity;samples[role]=sample
 parentraw,_=read(path(auth['console']['path']),256*KIB,auth['console']);ads=advertisements(parentraw)
 if parent.get('status')==COMPLETE:
  expected={k:parent[k] for k in ('status','timing_sample','resource_admissible','charged_work_policy')};expected.update(schema='m193c-local-image-terminal-v1',result=auth['parent']);need(len(ads)==1 and ads[0]==expected,'actual complete parent final advertisement')
 # Actual whole outer includes publication. A late outer/exit failure denies completion while retained worker science remains useful.
 sample=samples.get('parent');outer_ok=sample is not None and auth['actual_outer_wall_seconds']<=sample['wall_seconds']+5 and auth['actual_outer_wall_seconds']<=140
 summary.update(sampled_checks=checks,samples=samples,outer_wall_within_reserved_tail=outer_ok,complete_outer_exit=auth['actual_exit_code']==0,actual_outer_wall_seconds=auth['actual_outer_wall_seconds'])
 return summary

def inventory():
 allowed_paths=set()
 for name in ('result.json','result-stage.json','worker.log','child-terminal.json'):allowed_paths.add(name)
 for name in ('result.json','result-stage.json','runtime-modules.json','runtime-intake.json','runtime-namespace-controls.json'):allowed_paths.add('worker/'+name)
 for name in CONTROL:allowed_paths.add('worker/controls/'+name+'.json')
 for name in PRIVATE:
  for suffix in ('-reference-rgb.u16','-source-rgb.u16','-reference.f32','-source.f32','-surface.f32'):allowed_paths.add('worker/controls/'+name+suffix)
 for name in ('le','be'):allowed_paths.add('worker/controls/reader-'+name+'.tiff')
 for mode in ('off','on','placebo','restored','after-mutation'):allowed_paths.add('worker/controls/observer-'+mode+'-surface.f32')
 for key in REAL_IDS:
  for suffix in ('.json','-reference-rgb.u16','-source-rgb.u16','-reference.f32','-source.f32','-surface.f32'):allowed_paths.add('worker/real/'+key+suffix)
 for a,b in PAIRS:
  allowed_paths.add(f'worker/real/{a}-{b}/native-file-reads.json')
  for g in range(16):allowed_paths.add(f'worker/real/{a}-{b}/g{g:02d}-disjoint.json')
 rows=[];total=0;worker_bytes=0
 for root,dirs,files in os.walk(OUT):
  dirs.sort();files.sort()
  for d in dirs:
   st=(Path(root)/d).lstat();need(stat.S_ISDIR(st.st_mode) and not getattr(st,'st_file_attributes',0)&1024,'owned inventory regular non-reparse directory')
  for name in files:
   p=Path(root)/name;rel=p.relative_to(OUT).as_posix();isworker=rel.startswith('worker/');short=rel[7:] if isworker else rel
   allowed=rel in allowed_paths
   need(bool(allowed),'closed owned artifact family: '+rel);cap=2*MIB if short=='runtime-modules.json' else 256*KIB if short in ('worker.log','controls/reader-le.tiff','controls/reader-be.tiff') else 129*129*6 if p.suffix in ('.u16','.f32') else 64*KIB
   raw,r=read(p,cap,payload=p.suffix in ('.u16','.f32'),fixture=p.suffix=='.tiff');total+=len(raw);worker_bytes+=len(raw) if isworker else 0;rows.append(r);need(len(rows)<=900,'bounded physical file population')
 need(total<=60*MIB and worker_bytes<=59*MIB and total-worker_bytes<=MIB,'actual complete physical output extents')
 return dict(files=len(rows),file_bytes=total,worker_file_bytes=worker_bytes,parent_file_bytes=total-worker_bytes,inventory_sha256=sha(encoded(rows)),records=rows,scope='Physical inventory differs from logical consumed staging/high-water reservations; full fixed allowance remains charged.')

def counter_disposition(worker,private,real):
 counters=worker.get('counters')
 if counters is None:return dict(recorded=None,complete=False,scope='No durable scientific counters; none inferred.')
 keys=('image_patch_reads','real_estimator_calls','private_estimator_calls','raw_decodes','full_frame_arrays','feature_extractions','model_calls','registrar_calls');closed(counters,keys);need(all(type(v) is int and v>=0 for v in counters.values()),'typed scientific counters')
 need(all(counters[k]==0 for k in keys[3:]) and counters['image_patch_reads']<=256 and counters['real_estimator_calls']<=128 and counters['private_estimator_calls']<=14,'fixed counters and no wider scientific work witness')
 linked=real['linked_real_count'];private_lower=sum(1 for x in private['controls'] if x['linked'] and x['id'] in PRIVATE)
 if any(x['linked'] and x['id']=='observer-output' for x in private['controls']):private_lower+=6
 need(counters['real_estimator_calls']>=linked and counters['image_patch_reads']>=2*linked and counters['private_estimator_calls']>=private_lower,'counter lower bounds from canonical linked completed records')
 expected=dict(image_patch_reads=256,real_estimator_calls=128,private_estimator_calls=14,raw_decodes=0,full_frame_arrays=0,feature_extractions=0,model_calls=0,registrar_calls=0)
 return dict(recorded=counters,complete=counters==expected,scope='Recorded call counts, independently checked against retained completed rows; unretained partial calls are not reconstructed.')

def safe_phase(phase,value):
 # Progress is deliberately compact; final retains full bounded rows and exact original references.
 remember(phase,value)


def recovery_accounting(result):
 observed=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
 result['audit_timing']=observed;result['audit_publication_allowance']=dict(cpu_seconds=.25,wall_seconds=.5)
 result['current_audit_complete_process_cpu']=False
 result['current_audit_scope']='Latest process sample plus tail; full25CPU/30wall reservation retained, actual external exit/wall required.'
 if RECOVERY is None:result['recovery_authority_verified']=False;return
 charge=result.get('subject_charge_policy',SUBJECT)
 prior={k:AUDIT3_PRIOR[k]+max(0,charge[k]-SUBJECT[k]) for k in BASE}
 current={k:max(LIMITS[k],observed[k]+(.25 if k=='cpu_seconds' else .5)) if k in observed else LIMITS[k] for k in BASE}
 result.update(recovery_authority_verified=True,retained_previous_work_policy=prior,entered_phase_charge=ENTERED,
  recovery_preparation_charge=RECOVERY_PREP,current_audit_charge=current,first_audit_complete_process_cpu=False,
  historical_cpu_accounting_complete=False)
 result['actual_final_work']={k:prior[k]+RECOVERY_PREP[k]+current[k] for k in BASE}
 result['resource_capacity_within_phase']=all(result['actual_final_work'][k]<=CURRENT_CAPS[k] for k in BASE)
 result['next_wall_seconds']=str(result['actual_final_work']['wall_seconds'])

def main():
 parser=argparse.ArgumentParser()
 for name in ('plan','plan-sha256','result','result-sha256','outer','outer-sha256','console','console-sha256','exit','exit-sha256','self-sha256'):parser.add_argument('--'+name,required=True)
 parser.add_argument('--worker-sha256');parser.add_argument('--recovery-grant',required=True);parser.add_argument('--recovery-grant-sha256',required=True);args=parser.parse_args();need(not any(p.exists() for p in (FINAL,PROGRESS,STAGE)),'fresh independent outcome family')
 result=dict(schema=SCHEMA,status='INCOMPLETE_INDEPENDENT_AUDIT',subject_complete=False,scientific_contract_verified=False,real_geometry_admission=False,cpu_accounting_complete=False,exception=None)
 try:
  result['recovery']=recovery_authority(args);plan,frames,parent,worker,auth=authority(args);result['authority']=auth;
  need(parent['status']=='REFUSED' and worker is not None and worker['status']=='REFUSED' and worker.get('runtime_modules') is None,'immutable original producer runtime/completion refusal');safe_phase('authority',dict(plan=auth['plan'],parent=auth['parent'],worker=auth['worker'],outer=auth['outer'],source=auth['audit_source']))
  ledger_path=WORK/'independent-local-image-probe-audit-3-ledger.json';key=ledger_path.relative_to(ROOT).as_posix();need(key in RECOVERY['source_bindings'],'new audit ledger bound by recovery grant');ledger=saved(dict(path=key,**RECOVERY['source_bindings'][key]));need(ledger['schema']=='m193c-local-image-independent-audit-ledger-v3' and ledger['allowance']==LIMITS and sum(ledger['component_caps'].values())<=3*MIB and ledger['component_caps']['source']>=auth['audit_source']['bytes']+RECOVERY['source_bindings'][RUNTIME_HELPER.relative_to(ROOT).as_posix()]['bytes'],'finite complete independent audit family');result['audit_ledger']=dict(path=key,**RECOVERY['source_bindings'][key])
  result['checker_runtime']=numpy_runtime(plan);safe_phase('runtime-preflight',result['checker_runtime']);need(PREFLIGHT,'runtime barrier before all saved payload reads')
  physical=inventory();external_refs=[auth[k] for k in ('outer','console','exit')];need(sum(r['bytes'] for r in external_refs)<=64*KIB,'complete subject outer/console/exit64KiB family')
  external_bytes=sum(r['bytes'] for r in external_refs if not path(r['path']).is_relative_to(OUT));need(physical['parent_file_bytes']+external_bytes<=MIB and physical['file_bytes']+external_bytes<=60*MIB,'actual subject directory plus external receipts within declared family')
  physical['external_subject_bytes']=external_bytes;physical['total_subject_file_bytes']=physical['file_bytes']+external_bytes;need(physical==OLD_AUDIT['physical_inventory'],'entire previously retained866-file inventory unchanged');result['physical_inventory']=physical;safe_phase('physical-prefix', {k:v for k,v in physical.items() if k!='records'})
  private=dict(controls=[],producer_controls_complete=False,private_prerequisite_verified=False);real=dict(rows=[],disjoint=[],linked_real_count=0,retained_real_count=0,linked_disjoint_count=0,retained_disjoint_count=0,complete_saved_population=False);runtime={};namespace={};counter=dict(recorded=None,complete=False);cache={}
  if worker is not None:
   namespace=namespace_receipts(plan,worker);result['namespace']=namespace;safe_phase('runtime-intake',namespace)
   numerical=any((OUT/'worker/controls'/(name+'.json')).exists() for name in CONTROL)
   if numerical:
    private,cache=private_controls(worker);result['private']=private
    if cache:result['checker_projection_controls']=projection_power(next(iter(cache.values()))[0])
    safe_phase('private-literal-controls',dict(rows=[{k:x[k] for k in ('id','passed','linked','record')} for x in private['controls']],producer_controls_complete=private['producer_controls_complete'],independent_private_prerequisite=private['private_prerequisite_verified'],projection_power=result.get('checker_projection_controls')))
    real,records=real_population(worker,frames,private);result['real']=real;safe_phase('fixed-real-population',dict(retained=real['retained_real_count'],linked=real['linked_real_count'],groups=real['retained_disjoint_count'],complete=real['complete_saved_population'],whole_summary_sha256=sha(encoded(real))))
   else:
    need(not worker.get('controls') and not worker.get('real') and not any((OUT/'worker/real'/(k+'.json')).exists() for k in REAL_IDS),'no scientific metadata after missing control prefix')
   runtime=runtime_records(plan,worker);result['runtime']=runtime;safe_phase('native-and-runtime-witnesses',runtime);counter=counter_disposition(worker,private,real);result['counters']=counter
  terminal=terminal_accounting(plan,parent,worker,auth);result['terminal']=terminal;safe_phase('owned-terminal',terminal)
  native_ok=len(runtime.get('native_reads',[]))==2 and all(x['initial_complete'] and x['final_complete'] for x in runtime.get('native_reads',[]))
  if worker is not None:
   for row,pair in zip(runtime.get('native_reads',[]),PAIRS):need(row['images']==[frames[x]['tiff'] for x in pair],'native witness exact directed image population')
  namespace_ok=namespace.get('runtime_namespace_controls',{}).get('passed') is True and namespace.get('runtime_namespace_controls',{}).get('linked') is True and namespace.get('runtime_intake',{}).get('linked') is True
  worker_verified=worker is not None and worker['status']==COMPLETE and private['producer_controls_complete'] and real['complete_saved_population'] and counter['complete'] and native_ok and runtime.get('modules',{}).get('linked') is True and namespace_ok
  independent_science=worker_verified and private['private_prerequisite_verified'];positive=parent['status']==COMPLETE and worker_verified and terminal['clean_child'] and terminal['linked'] and parent.get('worker_result') is not None and terminal['sampled_checks'].get('parent') is True and terminal['sampled_checks'].get('worker') is True and terminal['outer_wall_within_reserved_tail'] and terminal['complete_outer_exit']
  result.update(status=STATUS,subject_complete=bool(positive),worker_complete_saved_population_verified=bool(worker_verified),scientific_contract_verified=bool(independent_science),real_geometry_admission=False,current_job_accounting_complete=terminal['current_job_accounting_complete'],current_run_accounting_scope='Complete owned child Job when available plus latest parent CPU sample and reserved 2 CPU/5 wall publication tail; historical CPU completeness remains false.')
  need(not positive and not worker_verified and not independent_science,'original runtime refusal cannot be promoted by checker supplements')
  result['saved_data_checks_complete']=bool(private['private_prerequisite_verified'] and real['complete_saved_population'] and counter['complete'] and native_ok and namespace_ok)
  result['producer_runtime_verified']=False;result['audit_version']='v3-isolated-source-authority'
  counts={}
  for row in real['rows']:
   name=row['outcome']['reason'] or row['outcome']['status'];counts[name]=counts.get(name,0)+1
  groups={}
  for row in real['disjoint']:groups[row['status']]=groups.get(row['status'],0)+1
  result['diagnostic_disposition']=dict(real_outcome_counts=counts,disjoint_counts=groups,all_fixed_real_rows_observed=real['complete_saved_population'],scope='Counted all retained rows; no selection, graph/placement or real displacement truth. Selected-lag alternate correlations cannot establish the unvisited full global peak or subpixel optimum.')
  prior=plan['prior_work'];charge=dict(SUBJECT);sample=terminal['samples'].get('parent');charge['wall_seconds']=max(140,auth['actual_outer_wall_seconds'],0 if sample is None else sample['wall_seconds']+5)
  if sample is not None:charge['cpu_seconds']=max(90,sample['process_cpu_seconds']+(terminal['terminal_job_cpu_seconds'] or sample['job_cpu_seconds'] or 0)+2)
  charge['file_bytes']=charge['metadata_bytes']=max(60*MIB,physical['total_subject_file_bytes']);audit_sample=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START);timer()
  result['subject_charge_policy']=charge;result['audit_timing']=audit_sample;result['audit_publication_allowance']=dict(cpu_seconds=.25,wall_seconds=.5);recovery_accounting(result)
  after=RUNTIME_INSPECTOR.snapshot('after-data');result['checker_runtime']['after_data']=after;result['checker_runtime']['final_identity_recheck']=RUNTIME_INSPECTOR.recheck();runtime_final(result);safe_phase('runtime-after-data',after)
  result['audit_scope']=['No subject source imported or executed. No native image/model/RAW/full-frame payload opened.','Saved RGB16/f32 projection and literal continuous private controls independently checked.','Direct spatial binary64 correlation evaluated only at predeclared deduplicated selected integer lags, with both energy normalizations.','Full global peak ranking, optimizer execution, actual unretained callback exceptions and native-to-patch origin remain bounded producer witnesses.','Private literal truth and real disjoint reproducibility are separate claims. All incomplete or false-control prefixes remain ineligible for whole-subject completion.']
  safe_phase('complete-audit-before-publication',dict(subject_complete=result['subject_complete'],worker_verified=worker_verified,science=independent_science,diagnostic=result['diagnostic_disposition'],final_work=result['actual_final_work']))
 except BaseException:
  result['status']='INCOMPLETE_INDEPENDENT_AUDIT';result['exception']=error();result['subject_complete']=False;result['saved_data_checks_complete']=False;result['scientific_contract_verified']=False
  try:remember('audit-refusal',dict(error=result['exception'],retained_phase_count=len(PHASES)))
  except BaseException:pass
 runtime_final(result)
 recovery_accounting(result)
 raw=encoded(result)
 if len(raw)>MIB:
  raw=encoded(dict(schema=SCHEMA,status='INCOMPLETE_INDEPENDENT_AUDIT',subject_complete=False,exception='AUDIT_FINAL_EXTENT',actual_bytes=len(raw),audit_timing=result.get('audit_timing'),audit_publication_allowance=result.get('audit_publication_allowance'),actual_final_work=result.get('actual_final_work'),recovery=result.get('recovery'),progress=ref(PROGRESS,PROGRESS.read_bytes()) if PROGRESS.exists() else None))
 with FINAL.open('xb') as f:need(f.write(raw)==len(raw),'complete audit final write');f.flush();os.fsync(f.fileno())
 need(sys.stdout.buffer.write(raw)==len(raw),'complete binary audit stdout write');sys.stdout.buffer.flush();return 0 if result['status']==STATUS and len(encoded(result))<=MIB else 1

if __name__=='__main__':raise SystemExit(main())