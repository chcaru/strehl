"""One isolated import collector in an owned bounded Windows Job. No subject import."""
import time
START=time.monotonic()
import argparse,ast,ctypes,ctypes.wintypes as wt,hashlib,json,math,os,queue,stat,subprocess,sys,threading,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];WORK=ROOT/'experiments/m193c-output-grid/work';SELF=Path(__file__).resolve()
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe');COLLECTOR=WORK/'local-image-checker-isolated-runtime.py';PROTOCOL=WORK/'local-image-checker-import-capture-preregister.md';GRANT=WORK/'local-image-checker-import-capture-grant-1.json';HARNESS=ROOT/'experiments/m12-scorecard/m12-harness.py'
KIB=1024;MIB=1<<20;STEM='local-image-checker-import-capture-1';STDOUT=WORK/(STEM+'-stdout.bin');STDERR=WORK/(STEM+'-stderr.bin');EXIT=WORK/(STEM+'-exit.txt');OUTER=WORK/(STEM+'-outer.json');STAGE=WORK/(STEM+'-outer-stage.json')
PLAN=dict(path='experiments/m193c-output-grid/local-image-probe-plan-1.json',bytes=476283,sha256='337ee76493feb15f14982d14fdb6b6148bc76ba108a9c0d77ba51ca25a6e66c1')
COLLECTOR_PIN=(28139,'eebc2b6c8c0ba2c74672ac41287eab643ae16adb754e08639d3d7f45bdd12011')
SCHEMA='m193c-isolated-import-owned-launch-v1';COMPLETE='COMPLETE_OWNED_IMPORT_CAPTURE_ONLY';LIMITS=dict(child_cpu_seconds=15,child_wall_seconds=25,committed_bytes=1<<30,launcher_cpu_seconds=3,launcher_wall_seconds=32,cleanup_wall_seconds=5,publication_wall_seconds=2)
NAMES=('kernel32','ntdll','CREATE_SUSPENDED','JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE','JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS','JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS','IO_COUNTERS','JOBOBJECT_BASIC_LIMIT_INFORMATION','JOBOBJECT_EXTENDED_LIMIT_INFORMATION','JOBOBJECT_BASIC_ACCOUNTING_INFORMATION','create_process_job','job_accounting','job_memory')
SIGS=tuple(f'{a}.{b}.{c}' for a,b in (('kernel32','CloseHandle'),('kernel32','CreateJobObjectW'),('kernel32','AssignProcessToJobObject'),('kernel32','SetInformationJobObject'),('kernel32','QueryInformationJobObject'),('ntdll','NtResumeProcess')) for c in ('argtypes','restype'))
SEEN={}
def need(v,msg):
 if not v:raise ValueError(msg)
def enc(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def clock():return dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
def guard(final=False):
 x=clock();need(x['cpu_seconds']<=(2.75 if final else 2.5) and x['wall_seconds']<=(32 if final else 30),'launcher time envelope')
def parse(b):
 def pairs(rows):
  v={}
  for k,x in rows:need(k not in v,'duplicate key');v[k]=x
  return v
 v=json.loads(b,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
 def walk(x):
  if type(x) is float:need(math.isfinite(x),'finite JSON')
  elif type(x) is list:
   for y in x:walk(y)
  elif type(x) is dict:
   for y in x.values():walk(y)
 walk(v);return v

def path(v):
 p=Path(os.path.abspath(str(ROOT/Path(v))));need('..' not in Path(v).parts,'no traversal')
 for q in (p,*p.parents):
  s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024,'no lexical reparse')
 return p.resolve()
def ident(s):return tuple(int(getattr(s,k,0)) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_file_attributes','st_nlink'))
def shape(r):need(type(r) is dict and set(r)=={'path','bytes','sha256'} and type(r['path']) is str and type(r['bytes']) is int and r['bytes']>=0 and type(r['sha256']) is str and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']),'typed FileRef')
def file(p,cap,ref=None):
 p=path(p);s=p.lstat();need(stat.S_ISREG(s.st_mode) and s.st_size<=cap and (not p.is_relative_to(ROOT) or s.st_nlink==1),'bounded plain file')
 if ref is not None:shape(ref);need(path(ref['path'])==p and ref['bytes']==s.st_size,'exact file role/extent')
 with p.open('rb') as f:
  a=os.fstat(f.fileno());need(ident(a)==ident(s),'opened identity');b=f.read(cap+1);z=os.fstat(f.fileno())
 need(ident(s)==ident(a)==ident(z)==ident(p.lstat()) and len(b)==s.st_size,'same stable whole buffer');r=dict(path=str(p),bytes=len(b),sha256=sha(b))
 if ref is not None:need(r['sha256']==ref['sha256'],'exact SHA');need(str(p) not in SEEN or SEEN[str(p)]==r,'same repeated evidence');SEEN[str(p)]=r
 return b,r

def publish(v):
 raw=enc(v);need(len(raw)<=64*KIB,'outer64KiB');raw=raw.rstrip(b'\n').ljust(64*KIB-1,b' ')+b'\n'
 with STAGE.open('xb') as f:need(f.write(raw)==len(raw),'whole staged outer');f.flush();os.fsync(f.fileno())
 before=ident(STAGE.lstat());os.replace(STAGE,OUTER);need(ident(OUTER.lstat())==before,'same staged object');b,r=file(OUTER,64*KIB);need(b==raw,'outer readback');return r

def api_from(raw):
 tree=ast.parse(raw,str(HARNESS));nodes=[];seen=set();wanted=set(NAMES+SIGS)
 for n in tree.body:
  if isinstance(n,ast.ImportFrom) and n.module=='__future__':nodes.append(n);continue
  name=n.name if isinstance(n,(ast.ClassDef,ast.FunctionDef)) else None
  if isinstance(n,ast.Assign) and len(n.targets)==1:
   x=n.targets[0];name=x.id if isinstance(x,ast.Name) else ast.unparse(x) if isinstance(x,ast.Attribute) else None
  if name in wanted:need(name not in seen,'unique selected declaration');seen.add(name);nodes.append(n)
 need(seen==wanted,'closed native Job API');t=ast.Module(body=nodes,type_ignores=[]);g=dict(__name__='owned_job_api',ctypes=ctypes,wt=wt,subprocess=subprocess);exec(compile(t,str(HARNESS),'exec'),g)
 return types.SimpleNamespace(**g),dict(names=sorted(seen),ast_sha256=sha(ast.dump(t,include_attributes=False).encode()))

def authority(a):
 need(os.name=='nt' and Path.cwd().resolve()==ROOT and path(sys.executable)==PYTHON and sys.flags.isolated==sys.flags.no_site==sys.flags.ignore_environment==sys.flags.no_user_site==1 and sys.flags.safe_path is True and sys.dont_write_bytecode and not sys._xoptions,'isolated Windows launcher')
 need(path(a.grant)==GRANT and sys.orig_argv==[str(PYTHON),'-I','-S','-B',str(SELF),'--grant',str(GRANT),'--grant-sha256',a.grant_sha256,'--self-sha256',a.self_sha256],'literal launcher argv')
 b,gr=file(GRANT,256*KIB,dict(path=str(GRANT),bytes=GRANT.stat().st_size,sha256=a.grant_sha256));g=parse(b)
 need(set(g)=={'schema','original_plan','failed_audit2','source_bindings','python_executable','startup_policy','prior_work','resources','cumulative_limits','command'} and g['schema']=='m193c-isolated-numpy-import-grant-v1' and g['original_plan']==PLAN,'closed grant/original plan')
 need(g['resources']['capture']==dict(cpu_seconds=15,wall_seconds=25,file_bytes=2*MIB,metadata_bytes=2*MIB) and g['resources']['independent_and_external']==dict(cpu_seconds=10,wall_seconds=15,file_bytes=MIB,metadata_bytes=MIB),'declared resource lanes')
 need(g['startup_policy']['flags']==['-I','-S','-B'] and g['startup_policy']['site_processing'] is False,'collector policy');sources={};need(type(g['source_bindings']) is dict and 1<=len(g['source_bindings'])<=32,'source population')
 for key,v in g['source_bindings'].items():
  r=dict(path=key,**v);shape(r);q=path(key);need(q.is_relative_to(WORK) and r['bytes']>0 and q not in sources,'positive unique source role');sources[q]=r
 need(sum(r['bytes'] for r in sources.values())<=256*KIB and all(q in sources for q in (SELF,COLLECTOR,PROTOCOL)),'source closure')
 need(sources[SELF]['sha256']==a.self_sha256 and (sources[COLLECTOR]['bytes'],sources[COLLECTOR]['sha256'])==COLLECTOR_PIN,'self/held collector pins')
 for r in sources.values():file(r['path'],256*KIB,r)
 b,pr=file(ROOT/PLAN['path'],640*KIB,PLAN);p=parse(b);need(p['schema']=='m193c-local-image-probe-plan-v1' and g['python_executable']==p['python_executable'],'original interpreter authority');file(g['python_executable']['path'],MIB,g['python_executable']);need(path(g['python_executable']['path'])==PYTHON,'pinned actual interpreter')
 hr=dict(path=str(HARNESS),**p['source_bindings'][HARNESS.relative_to(ROOT).as_posix()]);hb,hpin=file(HARNESS,256*KIB,hr)
 command=[str(PYTHON),'-I','-S','-B',str(COLLECTOR),'--grant',str(GRANT),'--grant-sha256',a.grant_sha256,'--self-sha256',sources[COLLECTOR]['sha256']];expected=command.copy();expected[expected.index('--grant-sha256')+1]='ACTUAL_CAPTURE_GRANT_SHA256';need(g['command']==expected,'authorized collector argv')
 return command,dict(grant=gr,plan=pr,python=g['python_executable'],launcher=sources[SELF],collector=sources[COLLECTOR],protocol=sources[PROTOCOL],job_source=hpin),hb

def times(api,p):
 v=[wt.FILETIME() for _ in range(4)];fn=api.kernel32.GetProcessTimes;fn.argtypes=[wt.HANDLE,*([ctypes.POINTER(wt.FILETIME)]*4)];fn.restype=wt.BOOL;need(bool(fn(wt.HANDLE(int(p._handle)),*[ctypes.byref(x) for x in v])),'retained-handle GetProcessTimes');n=[(int(x.dwHighDateTime)<<32)|int(x.dwLowDateTime) for x in v];return dict(created_100ns=n[0],exited_100ns=n[1],kernel_cpu_100ns=n[2],user_cpu_100ns=n[3])
def cpu(v):
 need(all(type(v.get(k)) is int and v[k]>=0 for k in ('total_user_100ns','total_kernel_100ns','total_cpu_100ns','active_processes')) and v['total_cpu_100ns']==v['total_user_100ns']+v['total_kernel_100ns'],'typed Job CPU');return v['total_cpu_100ns']/1e7

def main():
 p=argparse.ArgumentParser();p.add_argument('--grant',required=True);p.add_argument('--grant-sha256',required=True);p.add_argument('--self-sha256',required=True);a=p.parse_args();need(not any(q.exists() for q in (STDOUT,STDERR,EXIT,OUTER,STAGE)),'fresh launcher artifacts')
 r=dict(schema=SCHEMA,status='REFUSED',phase='INITIAL_INCOMPLETE',launcher_command=list(sys.orig_argv),command=None,exit_code=1,child_exit_code=None,authority=None,limits=LIMITS,error=None,cleanup_errors=[],job_accounting=None,job_memory=None,configured_job_limits=None,process_id=None,process_times_before=None,process_times_after=None,terminal_cpu_accounting=False,termination_attempted=False,assigned=False,resumed=False,pipe_eof=dict(stdout=False,stderr=False),stream_overflow=dict(stdout=False,stderr=False),observed_stream_bytes=dict(stdout=0,stderr=0),stdout=None,stderr=None,child_elapsed_wall_seconds=None,scope='One owned collector. Terminal Job CPU once; direct CPU is a cross-check. Wrapper CPU separate; committed memory not RSS. Actual external whole-wrapper receipt required.')
 publish(r);api=job=child=None;start=None;streams={};threads=[];stop=threading.Event();messages=queue.Queue(maxsize=16);code=1
 def send(v):
  while not stop.is_set():
   try:messages.put(v,timeout=.02);return
   except queue.Full:pass
 def pump(stream,name):
  try:
   while not stop.is_set():
    b=os.read(stream.fileno(),4096)
    if not b:break
    send((name,'data',b))
  except BaseException as e:send((name,'error',str(e)[-512:]))
  finally:send((name,'eof',None))
 def drain():
  while True:
   try:name,kind,b=messages.get_nowait()
   except queue.Empty:break
   if kind=='eof':r['pipe_eof'][name]=True
   elif kind=='error':r['cleanup_errors'].append(name+': '+b)
   else:
    r['observed_stream_bytes'][name]+=len(b);cap=8*KIB if name=='stdout' else 31*KIB;chunk=b[:max(0,cap-streams[name].tell())]
    if chunk:need(streams[name].write(chunk)==len(chunk),'whole retained stream prefix')
    if len(chunk)!=len(b):r['stream_overflow'][name]=True
 def observe():
  if job is None:return None
  v=api.job_accounting(job);c=cpu(v);old=r['job_accounting'];need(old is None or v['total_cpu_100ns']>=old['total_cpu_100ns'],'monotone Job CPU');r['job_accounting']=v;r['job_memory']=api.job_memory(job);return c
 try:
  command,auth,hb=authority(a);r.update(command=command,authority=auth,phase='AUTHENTICATED');api,profile=api_from(hb);r['selected_job_api']=profile;job=api.create_process_job()
  v=api.JOBOBJECT_EXTENDED_LIMIT_INFORMATION();v.basic_limit_information.limit_flags=0x2204;v.basic_limit_information.per_job_user_time_limit=150000000;v.job_memory_limit=1<<30
  need(bool(api.kernel32.SetInformationJobObject(job,api.JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,ctypes.byref(v),ctypes.sizeof(v))),'install Job limits');q=api.JOBOBJECT_EXTENDED_LIMIT_INFORMATION();n=wt.DWORD();need(bool(api.kernel32.QueryInformationJobObject(job,api.JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,ctypes.byref(q),ctypes.sizeof(q),ctypes.byref(n))),'read installed limits')
  r['configured_job_limits']=dict(flags=int(q.basic_limit_information.limit_flags),committed_bytes=int(q.job_memory_limit),per_job_user_100ns=int(q.basic_limit_information.per_job_user_time_limit));need(r['configured_job_limits']==dict(flags=0x2204,committed_bytes=1<<30,per_job_user_100ns=150000000),'exact actual limit readback')
  guard();need(time.monotonic()-START<=5,'full child window before final publication');streams['stdout']=STDOUT.open('xb',buffering=0);streams['stderr']=STDERR.open('xb',buffering=0);start=time.monotonic()
  child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,creationflags=api.CREATE_SUSPENDED|subprocess.CREATE_NO_WINDOW);r['process_id']=child.pid;r['process_times_before']=times(api,child)
  for name,stream in (('stdout',child.stdout),('stderr',child.stderr)):
   t=threading.Thread(target=pump,args=(stream,name),daemon=True);t.start();threads.append(t)
  need(bool(api.kernel32.AssignProcessToJobObject(job,wt.HANDLE(int(child._handle)))),'assign owned suspended child');r['assigned']=True;need(api.ntdll.NtResumeProcess(wt.HANDLE(int(child._handle)))==0,'resume actual child');r['resumed']=True;r['phase']='COLLECTOR_RUNNING'
  while True:
   drain();c=observe();elapsed=time.monotonic()-start;r['child_elapsed_wall_seconds']=elapsed;need(c<=15 and r['job_memory']['peak_job_memory_used_bytes']<=1<<30 and elapsed<=25,'whole child CPU/memory/wall');guard();need(not any(r['stream_overflow'].values()) and not r['cleanup_errors'],'complete bounded streams')
   if child.poll() is not None and r['job_accounting']['active_processes']==0 and all(r['pipe_eof'].values()):break
   time.sleep(.01)
  r['child_exit_code']=child.wait();r['phase']='COLLECTOR_EXIT_OBSERVED'
 except BaseException as e:r['error']=dict(type=type(e).__name__,message=str(e)[-1024:])
 finally:
  deadline=min(time.monotonic()+5,START+30)
  if job is not None:
   try:
    observe()
    if r['job_accounting']['active_processes']:
     r['termination_attempted']=True;fn=api.kernel32.TerminateJobObject;fn.argtypes=[wt.HANDLE,wt.UINT];fn.restype=wt.BOOL;need(bool(fn(job,0xE193C001)),'terminate only owned Job')
   except BaseException as e:r['cleanup_errors'].append(str(e)[-512:])
  if child is not None and not r['assigned'] and child.poll() is None:
   try:child.kill();r['direct_assignment_failure_kill']=True
   except BaseException as e:r['cleanup_errors'].append(str(e)[-512:])
  while child is not None and time.monotonic()<deadline:
   try:drain();observe()
   except BaseException as e:r['cleanup_errors'].append(str(e)[-512:]);break
   if child.poll() is not None and all(r['pipe_eof'].values()) and (job is None or r['job_accounting']['active_processes']==0):break
   time.sleep(.01)
  if child is not None:
   try:
    need(child.poll() is not None,'owned exit not observed by deadline');r['child_exit_code']=child.wait(timeout=0);z=times(api,child);b=r['process_times_before'];need(z['created_100ns']==b['created_100ns']>0 and z['exited_100ns']>=z['created_100ns'] and z['kernel_cpu_100ns']>=b['kernel_cpu_100ns'] and z['user_cpu_100ns']>=b['user_cpu_100ns'],'terminal same owned process identity');r['process_times_after']=z;r['terminal_cpu_accounting']=True
   except BaseException as e:r['cleanup_errors'].append(str(e)[-512:])
  try:drain();observe()
  except BaseException as e:r['cleanup_errors'].append(str(e)[-512:])
  stop.set()
  for t in threads:t.join(timeout=max(0,min(.05,deadline-time.monotonic())))
  alive=any(t.is_alive() for t in threads)
  if alive:r['cleanup_errors'].append('pipe reader incomplete')
  if child is not None:
   if not alive:
    for stream in (child.stdout,child.stderr):
     if stream is not None:stream.close()
   child._handle.Close()
  if job is not None:api.kernel32.CloseHandle(job)
  for stream in streams.values():
   try:stream.flush();os.fsync(stream.fileno());stream.close()
   except BaseException as e:r['cleanup_errors'].append(str(e)[-512:])
  if start is not None:r['child_elapsed_wall_seconds']=time.monotonic()-start
 try:
  for name,q,cap in (('stdout',STDOUT,8*KIB),('stderr',STDERR,31*KIB)):
   if not q.exists():
    with q.open('xb'):pass
   _,r[name]=file(q,cap)
  good=(r['error'] is None and not r['cleanup_errors'] and not r['termination_attempted'] and r['assigned'] and r['resumed'] and r['child_exit_code']==0 and r['terminal_cpu_accounting'] and all(r['pipe_eof'].values()) and not any(r['stream_overflow'].values()) and r['job_accounting']['active_processes']==0 and cpu(r['job_accounting'])<=15 and r['job_memory']['peak_job_memory_used_bytes']<=1<<30 and r['child_elapsed_wall_seconds']<=25)
  if r['terminal_cpu_accounting']:
   z=r['process_times_after'];r['direct_terminal_cpu_seconds']=(z['kernel_cpu_100ns']+z['user_cpu_100ns'])/1e7
   if r['assigned']:need(r['job_accounting'] is not None and r['direct_terminal_cpu_seconds']<=cpu(r['job_accounting']),'direct CPU contained in Job, not added twice')
  if good:
   b,_=file(STDOUT,8*KIB);v=parse(b);need(v['schema']=='m193c-isolated-numpy-import-capture-v1' and v['status']=='COMPLETE_NO_DATA_IMPORT_CAPTURE_ONLY' and v['capture_complete'] is True and type(v['exit_code']) is int and v['exit_code']==0,'collector console');shape(v['result']);need(path(v['result']['path'])==WORK/(STEM+'.json'),'collector final role');b,ref=file(v['result']['path'],1152*KIB,v['result']);x=parse(b);need(x['status']==v['status'] and x['capture_complete'] is True and x['subject_complete'] is False and x['saved_data_checks_complete'] is False and x['authority']['grant']['sha256']==a.grant_sha256,'same capture-only final');r['collector_result']=ref;guard(True);r.update(status=COMPLETE,phase='TERMINAL_CAPTURE',exit_code=0);code=0
  r['launcher_sample']=clock();r['launcher_publication_allowance']=dict(cpu_seconds=.25,wall_seconds=2);r['actual_external_full_launcher_receipt_required']=True
  if r['launcher_sample']['cpu_seconds']+.25>3 or r['launcher_sample']['wall_seconds']+2>32:r.update(status='REFUSED',exit_code=1);code=1
  with EXIT.open('xb') as f:need(f.write((str(code)+'\n').encode())==2,'exit disposition');f.flush();os.fsync(f.fileno())
  r['exit_file']=file(EXIT,KIB)[1];outer=publish(r);guard(True);b=enc(dict(schema=SCHEMA,status=r['status'],result=outer,exit_code=code));need(len(b)<=8*KIB,'advertisement bound');need(sys.stdout.buffer.write(b)==len(b),'whole raw advertisement');sys.stdout.buffer.flush();guard(True)
 except BaseException as e:
  code=1;r.update(status='REFUSED',exit_code=1,publication_error=dict(type=type(e).__name__,message=str(e)[-1024:]),launcher_sample=clock())
  try:
   with EXIT.open('wb') as f:f.write(b'1\n');f.flush();os.fsync(f.fileno())
   r['exit_file']=file(EXIT,KIB)[1];publish(r)
  except BaseException:pass
 return code
if __name__=='__main__':raise SystemExit(main())
