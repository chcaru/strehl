"""One separately released capture of the childless fixed scratch controls.
No product/controller/helper imports, Cargo, process discovery or tree kill.
"""
import time
START=time.monotonic()
import argparse,hashlib,json,os,stat,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
PY=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
OUTPUT=HERE/'work/scratch-control-external-1';CHILD_OUTPUT=HERE/'work/scratch-scan-controls-1'
PINS={
 'controls':('scratch-scan-controls.py',19863,'37c90e6fc52a0f27f7fe5b8c08092bbc1fcb3acc6181fee96911493bcf552f36'),
 'shim':('scratch-scan.py',2991,'3a1aa413fd4c9d37bccb973a419e3f4c03291903d44b7198c53992e7b00d3e46'),
 'spec':('scratch-scan-spec.md',8590,'c65ef3fbe791c473eb3bdfeca0cd72a40b49f71a6efc3639d442d75566f19ab8')}
LIMIT=1<<20;READ=WRITE=0;CHILD_INTERVAL=0.0

def need(ok,label):
    if not ok:raise ValueError(label)

def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()

def sha(raw):return hashlib.sha256(raw).hexdigest()

def strict(raw):
    def pairs(items):
        v={}
        for k,x in items:need(k not in v,'duplicate JSON key');v[k]=x
        return v
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda v:need(False,'nonfinite JSON'))

def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink,getattr(s,'st_file_attributes',0))

def shared(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,'st_file_attributes',0))

def safe(path):
    p=Path(os.path.abspath(path));need(p.is_relative_to(ROOT) and len(str(p))<=384 and str(p).isascii(),'fixed owned path')
    for a in (p,*p.parents):
        if a.exists():
            s=a.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'ordinary path ancestry')
    return p

def budget(reserve=False):
    elapsed=time.monotonic()-START;overhead=elapsed-min(CHILD_INTERVAL,10.0)
    need(time.process_time()+(1 if reserve else 0)<=5,'wrapper CPU allowance')
    need(overhead+(2 if reserve else 0)<=10 and elapsed+(2 if reserve else 0)<=20,'wrapper overhead/full interval allowance')
    need(READ<=LIMIT and WRITE<=LIMIT,'wrapper read/write allowance')

def read(path,cap,empty=False):
    global READ
    p=safe(path);a=p.lstat();need(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and (0 if empty else 1)<=a.st_size<=cap,'bounded ordinary capture read')
    need(READ+a.st_size+1<=LIMIT,'capture read reservation')
    with p.open('rb') as stream:
        b=os.fstat(stream.fileno());need(shared(a)==shared(b),'capture path/handle identity')
        raw=stream.read(a.st_size+1);READ+=len(raw);c=os.fstat(stream.fileno())
    d=p.lstat();need(identity(a)==identity(d) and identity(b)==identity(c) and len(raw)==a.st_size,'stable exact capture bytes')
    return raw,dict(path=str(p),bytes=len(raw),sha256=sha(raw))

def write(path,raw,cap):
    global WRITE
    p=safe(path);need(p.is_relative_to(OUTPUT) and not p.exists() and len(raw)<=cap,'fresh bounded capture write')
    need(WRITE+len(raw)<=LIMIT,'capture write reservation')
    with p.open('xb') as stream:
        n=stream.write(raw);WRITE+=n;need(n==len(raw),'complete capture write');stream.flush();os.fsync(stream.fileno())
    observed,ref=read(p,cap,empty=True);need(observed==raw,'capture write readback');return ref

def error(exc):
    raw=str(exc).encode('utf-8',errors='replace')
    value=dict(type=type(exc).__name__,message=str(exc)[:400],full_bytes=len(raw),sha256=sha(raw))
    while len(encode(value))>1024:value['message']=value['message'][:len(value['message'])//2]
    return value

def main():
    global WRITE,CHILD_INTERVAL
    parser=argparse.ArgumentParser();parser.add_argument('--source-sha256',required=True);args=parser.parse_args()
    need(os.name=='nt' and Path.cwd().resolve()==ROOT and Path(sys.executable)==PY and sys.flags.isolated
         and sys.flags.no_site and sys.dont_write_bytecode,'fixed isolated capture host')
    need(sys.orig_argv==[str(PY),'-I','-S','-B',str(SELF),'--source-sha256',args.source_sha256],'exact wrapper command')
    ownraw,own=read(SELF,32*1024);need(own['sha256']==args.source_sha256,'wrapper source identity')
    sources={'wrapper':own}
    for role,(name,n,digest) in PINS.items():
        raw,ref=read(HERE/name,32*1024)
        need(ref['bytes']==n and ref['sha256']==digest,'exact child source '+role);sources[role]=ref
    budget(reserve=True)
    need(not OUTPUT.exists() and OUTPUT.parent.is_dir() and not CHILD_OUTPUT.exists(),'fresh external and control output roots')
    OUTPUT.mkdir();stdout_path=OUTPUT/'stdout.bin';stderr_path=OUTPUT/'stderr.bin'
    command=[str(PY),'-I','-S','-B',str(HERE/PINS['controls'][0]),
             '--source-sha256',PINS['controls'][2],'--shim-sha256',PINS['shim'][2],
             '--spec-sha256',PINS['spec'][2],'--output',str(CHILD_OUTPUT)]
    record=dict(schema='common-tiff-dimensions-scratch-control-external-v1',status='REFUSED',command=command,
                wrapper_command=sys.orig_argv,sources=sources,child_output=str(CHILD_OUTPUT),
                exit_code=None,timeout_terminated=False,capture_limit_terminated=False,
                termination=dict(attempted=False,kill_succeeded=False,wait_completed=False,error=None),
                errors=[],stdout=None,stderr=None,exit=None,result=None,
                scope='One source-bound childless control interpreter; only its retained Popen handle may be terminated.')
    child=None;child_start=None;child_end=None
    with stdout_path.open('xb') as sout,stderr_path.open('xb') as serr:
        try:
            child_start=time.monotonic()
            child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=sout,stderr=serr)
            while child.poll() is None:
                elapsed=time.monotonic()-child_start
                if elapsed>=10:
                    record['timeout_terminated']=True;break
                if stdout_path.stat().st_size>64*1024 or stderr_path.stat().st_size>16*1024:
                    record['capture_limit_terminated']=True;break
                time.sleep(0.01)
        except (OSError,ValueError) as exc:record['errors'].append(error(exc))
        finally:
            if child is not None:
                if child.poll() is None:
                    record['termination']['attempted']=True
                    try:child.kill();record['termination']['kill_succeeded']=True
                    except OSError as exc:record['termination']['error']=error(exc)
                    try:child.wait(timeout=1);record['termination']['wait_completed']=True
                    except subprocess.TimeoutExpired as exc:record['termination']['error']=error(exc)
                else:child.wait();record['termination']['wait_completed']=True
                record['exit_code']=child.returncode
            child_end=time.monotonic()
            if child_start is not None:CHILD_INTERVAL=child_end-child_start
            sout.flush();serr.flush()
    record['elapsed_wall_seconds']=CHILD_INTERVAL
    # Final files remain even on refusal. Read only after the owned writer exited.
    sizes={'stdout':stdout_path.stat().st_size,'stderr':stderr_path.stat().st_size}
    record['observed_stream_bytes']=sizes
    WRITE+=sum(sizes.values()) # Conservatively also charge child transport to this separate wrapper slice.
    try:
        need(child is not None and child.returncode is not None,'owned child terminal exit retained')
        need(sizes['stdout']<=64*1024 and sizes['stderr']<=16*1024,'bounded final capture streams')
        output,record['stdout']=read(stdout_path,64*1024,empty=True)
        errors,record['stderr']=read(stderr_path,16*1024,empty=True)
        if (CHILD_OUTPUT/'result.json').exists():
            raw,record['result']=read(CHILD_OUTPUT/'result.json',64*1024)
            need(raw==output,'raw child stdout equals final result')
            result=strict(raw)
        else:result=None
        need(record['exit_code']==0 and not record['timeout_terminated'] and not record['capture_limit_terminated']
             and not record['termination']['attempted'] and record['termination']['error'] is None
             and CHILD_INTERVAL<=10 and not errors and not record['errors'],'complete clean control interpreter')
        need(result is not None and result['schema']=='common-tiff-dimensions-scratch-scan-controls-v1'
             and result['status']=='PASS_FIXED_SCRATCH_SCAN_CONTROLS' and result['complete'] is True
             and len(result['rows'])==16 and all(row['passed'] is True for row in result['rows']),
             'actual complete fixed control result')
        for role,key in (('controls','source'),('shim','shim'),('spec','spec')):
            need(result['sources'][key]==sources[role],'actual control source association '+role)
        record['status']='COMPLETE_SCRATCH_CONTROL_CAPTURE'
    except (ValueError,OSError,KeyError,TypeError) as exc:record['errors'].append(error(exc))
    exit_text=('NOT_STARTED\n' if child is None else 'TERMINAL_EXIT_UNAVAILABLE\n') if record['exit_code'] is None else str(record['exit_code'])+'\n'
    record['exit']=write(OUTPUT/'exit.txt',exit_text.encode(),1024)
    for role,ref in sources.items():
        try:
            raw,current=read(ref['path'],32*1024);need(current==ref,'unchanged source after child '+role)
        except (ValueError,OSError) as exc:
            record['status']='REFUSED';record['errors'].append(error(exc))
    record['wrapper_sample']=dict(cpu_seconds=time.process_time(),whole_wall_seconds=time.monotonic()-START,
        charged_overhead_wall_seconds=time.monotonic()-START-min(CHILD_INTERVAL,10.0),read_bytes=READ,written_bytes=WRITE)
    record['reserved_resources']=dict(child=dict(cpu_seconds=5,wall_seconds=10,read_bytes=LIMIT,written_bytes=LIMIT),
        additional_wrapper=dict(cpu_seconds=5,wall_seconds=10,read_bytes=LIMIT,written_bytes=LIMIT),
        full_outer_wall_seconds=20,publication_tail=dict(cpu_seconds=1,wall_seconds=2))
    record['accounting_scope']='Child and wrapper full slices retained; wrapper CPU sample and measured overhead, not exact terminal parent CPU. Root must retain the full wrapper process interval/exit.'
    try:budget(reserve=True)
    except ValueError as exc:record['status']='REFUSED';record['errors'].append(error(exc))
    raw=encode(record);need(len(raw)<=64*1024,'bounded external final')
    outer=write(OUTPUT/'outer.json',raw,64*1024)
    advertisement=encode(dict(status=record['status'],outer=outer,stdout=record['stdout'],stderr=record['stderr'],exit=record['exit']))
    need(len(advertisement)<=8192 and WRITE+len(advertisement)<=LIMIT,'bounded outer advertisement')
    n=sys.stdout.buffer.write(advertisement);WRITE+=n;need(n==len(advertisement),'complete outer advertisement')
    sys.stdout.buffer.flush();budget()
    return 0 if record['status']=='COMPLETE_SCRATCH_CONTROL_CAPTURE' else 1


if __name__=='__main__':raise SystemExit(main())
