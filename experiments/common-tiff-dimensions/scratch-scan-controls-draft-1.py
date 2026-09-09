"""Independent16-case production scratch-scan controls. Source only until root release."""
from __future__ import annotations
import argparse,ast,errno,hashlib,json,os,stat,sys,time,types
from pathlib import Path
START=time.monotonic();CPU=time.process_time()
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
SELF=Path(__file__).resolve();SHIM=HERE/'scratch-scan.py';SPEC=HERE/'scratch-scan-spec.md'
BASE=ROOT/'experiments/m194h-pedestal-causality/build-and-run.py'
BASE_SHA='b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410'
CAP=1<<20;READ=WRITE=META=0;OUT=None;REPORT={}
IDS=('stable-scratch','delete-before-resolve','restored-after-delete','absent-scratch-root',
     'retained-deletion-refuses','extant-canonical-mismatch','reparse-refuses','nonregular-refuses',
     'permission-refuses','overcapacity-refuses','wrong-scratch-root-refuses','nonbool-policy-refuses',
     'false-policy-keeps-original','walk-permission-refuses','stable-retained','restored-final')

def need(ok,label):
    if not ok:raise ValueError(label)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()

def bound(reserve=False):
    cpu,wall=time.process_time()-CPU,time.monotonic()-START
    need(cpu+(1 if reserve else 0)<=5 and wall+(2 if reserve else 0)<=10,'finite control CPU/wall')
    need(READ<=CAP and WRITE<=CAP and META<=8192,'finite control content/metadata operations')

def full(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink,getattr(s,'st_file_attributes',0))

def shared(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,'st_file_attributes',0))

def safe(path):
    p=Path(os.path.abspath(path))
    need(p.is_relative_to(ROOT) and len(str(p))<=384 and str(p).isascii(),'owned bounded path')
    for ancestor in (p,*p.parents):
        if ancestor.exists():
            s=ancestor.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'plain source/output ancestry')
    return p

def read(path,cap):
    global READ
    p=safe(path);a=p.lstat()
    need(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and 0<a.st_size<=cap,'positive bounded file')
    need(READ+a.st_size+1<=CAP,'aggregate read reservation');bound()
    with p.open('rb') as stream:
        b=os.fstat(stream.fileno());need(shared(a)==shared(b),'path/handle source identity')
        raw=stream.read(a.st_size+1);READ+=len(raw);c=os.fstat(stream.fileno())
    d=p.lstat()
    need(full(a)==full(d) and full(b)==full(c) and len(raw)==a.st_size,'stable same-buffer read')
    return raw,dict(path=str(p),bytes=len(raw),sha256=sha(raw))

def write(path,raw,cap):
    global WRITE
    p=safe(path);need(p.is_relative_to(OUT) and not p.exists() and 0<len(raw)<=cap,'fresh own bounded write')
    need(WRITE+len(raw)<=CAP,'aggregate write reservation');bound()
    with p.open('xb') as stream:
        n=stream.write(raw);WRITE+=n;need(n==len(raw),'complete content write');stream.flush();os.fsync(stream.fileno())
    check,ref=read(p,cap);need(check==raw,'exact write readback');return ref

def retain():
    if OUT is None:return
    raw=encoded(REPORT);need(len(raw)<=40*1024,'progress capacity')
    stage=OUT/'progress-stage.json';write(stage,raw,40*1024);os.replace(stage,OUT/'progress.json')

def error_value(exc):
    raw=str(exc).encode('utf-8',errors='replace')
    v=dict(type=type(exc).__name__,message=str(exc)[:400],full_bytes=len(raw),sha256=sha(raw))
    while len(encoded(v))>1024:v['message']=v['message'][:len(v['message'])//2]
    return v

def fixture(path,data):
    p=safe(path)
    if p.exists():
        raw,_=read(p,11);need(raw==data,'exact restored fixture content')
    else:write(p,data,11)


def held_module(tree,context):
    """Exact held definitions; I/O adapters live only in this new module."""
    wanted=('need','lexical','owned','scan')
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
    need(tuple(n.name for n in nodes)==wanted,'exact held definition order/population')
    module=types.ModuleType('private_scratch_control_held')
    def meta():
        global META
        META+=1;bound()
    def as_path(v):return v.p if isinstance(v,ControlPath) else Path(v)
    def copied_stat(s,**updates):
        fields={name:getattr(s,name) for name in dir(s) if name.startswith('st_')}
        fields.update(updates);return types.SimpleNamespace(**fields)
    class ControlPath:
        def __init__(self,value):self.p=as_path(value)
        def __fspath__(self):return str(self.p)
        def __str__(self):return str(self.p)
        def __repr__(self):return repr(self.p)
        def __eq__(self,other):
            try:return self.p==as_path(other)
            except TypeError:return False
        def __hash__(self):return hash(self.p)
        def __truediv__(self,part):return ControlPath(self.p/part)
        @property
        def parents(self):return tuple(ControlPath(p) for p in self.p.parents)
        def is_absolute(self):return self.p.is_absolute()
        def is_relative_to(self,other):return self.p.is_relative_to(as_path(other))
        def exists(self):meta();return self.p.exists()
        def lstat(self):
            meta();s=self.p.lstat()
            if self.p==context['victim'] and context['mode']=='reparse':
                context['fired']+=1
                return copied_stat(s,st_file_attributes=getattr(s,'st_file_attributes',0)|0x400)
            return s
        def stat(self):
            meta();s=self.p.stat()
            if self.p==context['victim'] and context['mode']=='nonregular':
                context['fired']+=1;return copied_stat(s,st_mode=(s.st_mode&0o777)|stat.S_IFIFO)
            return s
        def resolve(self,strict=False):
            meta();need(type(strict) is bool,'delegated strict argument')
            context['resolves'].append(dict(path=self.p.name,strict=strict))
            need(len(context['resolves'])<=12,'bounded resolve observations')
            if self.p==context['victim']:
                context['victim_resolve_strict']=strict
                if context['mode']=='delete':
                    # Real deletion is after lexical ancestry and immediately before native resolution.
                    need(self.p.is_relative_to(OUT) and self.p.name=='victim.bin','only own named deletion')
                    need(self.p.read_bytes()==b'B'*11,'actual deletion operand')
                    global READ
                    READ+=11;need(READ<=CAP,'deletion read accounting')
                    self.p.unlink();context['fired']+=1
                    context['missing_after_unlink']=not self.p.exists()
                elif context['mode']=='permission':
                    context['fired']+=1;raise PermissionError(errno.EACCES,'injected-resolve-permission',str(self.p))
                elif context['mode']=='canonical':
                    need(self.p.exists() and context['other'].exists(),'two extant canonical operands')
                    actual=self.p.resolve(strict=strict)
                    need(actual!=context['other'],'distinct actual canonical locations')
                    context['fired']+=1;context['declared']=str(self.p);context['substituted']=str(context['other'])
                    return ControlPath(context['other'])
            return ControlPath(self.p.resolve(strict=strict))
    def walk(root,followlinks=False,onerror=None):
        meta();context['walk_calls']+=1
        need(followlinks is False and callable(onerror),'unchanged walk arguments')
        if context['mode']=='walk-permission':
            context['fired']+=1;onerror(PermissionError(errno.EACCES,'injected-walk-permission',str(as_path(root))));return
        yield from os.walk(as_path(root),followlinks=followlinks,onerror=onerror)
    module.__dict__.update(ROOT=ROOT,Path=ControlPath,stat=stat,os=types.SimpleNamespace(path=os.path,walk=walk))
    compile_tree=ast.Module(body=nodes,type_ignores=[]);ast.fix_missing_locations(compile_tree)
    exec(compile(compile_tree,str(BASE),'exec'),module.__dict__)
    return module


def positive(value,files,bytes_,absent=False,raced=0):
    need(type(value) is dict and set(value)=={'files','bytes','initial_absent','observed_disappearances',
         'disappearance_samples','tolerate_disappearance','scope'},'actual unchanged scanner schema')
    need(type(value['files']) is int and type(value['bytes']) is int and value['files']==files and value['bytes']==bytes_,
         'exact independent observed extents')
    need(value['initial_absent'] is absent and type(value['observed_disappearances']) is int
         and value['observed_disappearances']==raced,'exact absence/disappearance observation')
    need(len(value['disappearance_samples'])==raced,'exact bounded disappearance sample')
    if raced:
        row=value['disappearance_samples'][0]
        need(row['operation']=='file-inspection' and Path(row['path']).name=='victim.bin'
             and row['path_truncated'] is False,'actual missing victim association')
    need('Non-atomic' in value['scope'] and 'not unique files or a peak-size certificate' in value['scope'],
         'unchanged non-atomic evidence scope')


def run_case(index,tree,shim,scratch,retained):
    ident=IDS[index];root=scratch;policy=True;mode='none';limit=18
    if index in (1,4):mode='delete'
    if index in (5,12):mode='canonical'
    if index==6:mode='reparse'
    if index==7:mode='nonregular'
    if index==8:mode='permission'
    if index==9:limit=17
    if index==13:mode='walk-permission'
    if index in (4,12,14):policy=False
    if index==11:policy=1
    if index==14:root=retained
    target=scratch if index!=3 else OUT/'missing-root'
    if index==3:root=target
    if index==10:root=retained
    for folder in (scratch,retained):
        fixture(folder/'keep.bin',b'A'*7);fixture(folder/'victim.bin',b'B'*11)
    context=dict(victim=root/'victim.bin',other=root/'keep.bin',mode=mode,fired=0,walk_calls=0,resolves=[],
                 victim_resolve_strict=None,missing_after_unlink=False)
    held=held_module(tree,context);before=(held.scan,held.owned,held.lexical)
    dispatch=shim.make_scanner(held,target)
    need(all(a is b for a,b in zip(before,(held.scan,held.owned,held.lexical))),'factory preserves original helper objects')
    caught=None;value=None
    try:value=dispatch(root,limit,tolerate_disappearance=policy)
    except (ValueError,OSError) as error:caught=error
    need(all(a is b for a,b in zip(before,(held.scan,held.owned,held.lexical))),'invocation preserves original helper objects')
    if index in (0,2,15):
        need(caught is None,'clean scratch positive');positive(value,2,18)
        need(value['tolerate_disappearance'] is True and context['resolves']
             and all(x['strict'] for x in context['resolves']),'actual strict scratch resolver')
    elif index==1:
        need(caught is None and context['fired']==1 and context['missing_after_unlink']
             and context['victim_resolve_strict'] is True and not context['victim'].exists(),'actual strict deletion seam exercised')
        positive(value,1,7,raced=1)
    elif index==3:
        need(caught is None and not target.exists() and context['walk_calls']==0 and not context['resolves'],'actual initially absent target')
        positive(value,0,0,absent=True)
    elif index==14:
        need(caught is None and context['resolves'] and all(not x['strict'] for x in context['resolves']),'retained original resolver')
        positive(value,2,18);need(value['tolerate_disappearance'] is False,'retained strict policy')
    else:
        need(caught is not None,'named negative actually refuses')
        if index==4:
            need(type(caught) is FileNotFoundError and caught.errno==errno.ENOENT and context['fired']==1
                 and context['missing_after_unlink'] and context['victim_resolve_strict'] is False,'original retained deletion rejection')
        elif index==5:
            need(type(caught) is ValueError and 'canonical scratch path declared=' in str(caught) and ' resolved=' in str(caught)
                 and repr(context['declared']) in str(caught) and repr(context['substituted']) in str(caught)
                 and context['fired']==1 and context['victim_resolve_strict'] is True,'extant canonical mismatch rejection')
        elif index in (6,7):
            token='reparse/symlink path' if index==6 else 'plain output file'
            need(type(caught) is ValueError and token in str(caught) and context['fired']==1,'specific metadata fault rejection')
        elif index in (8,13):
            token='injected-resolve-permission' if index==8 else 'injected-walk-permission'
            need(type(caught) is PermissionError and caught.errno==errno.EACCES and token in str(caught)
                 and context['fired']==1,'specific permission propagation')
        elif index==9:need(type(caught) is ValueError and 'file family capacity' in str(caught),'actual capacity rejection')
        elif index==10:
            need(type(caught) is ValueError and str(caught)=='exact declared scratch scan root'
                 and context['walk_calls']==0 and not context['resolves'],'wrong-root dispatcher rejection')
        elif index==11:
            need(type(caught) is ValueError and str(caught)=='typed scratch scan policy'
                 and context['walk_calls']==0 and not context['resolves'],'typed-policy dispatcher rejection')
        elif index==12:
            need(type(caught) is ValueError and 'canonical path' in str(caught) and 'canonical scratch path' not in str(caught)
                 and context['fired']==1 and context['victim_resolve_strict'] is False,'false-policy original canonical rejection')
    summary=dict(id=ident,passed=True,mode=mode,policy=policy,original_helpers_unchanged=True,
                 fault_fired=context['fired'],walk_calls=context['walk_calls'],resolves=context['resolves'],
                 actual_deleted=context['missing_after_unlink'],evidence_kind='actual own deletion' if mode=='delete' else
                 'injected metadata/I/O response' if mode!='none' else 'actual fixture metadata')
    if value is not None:summary['scan']=value
    if caught is not None:summary['expected_error']=error_value(caught)
    need(len(encoded(summary))<=2048,'fixed control row capacity')
    return summary


def main():
    global OUT,REPORT
    parser=argparse.ArgumentParser()
    for name in ('source-sha256','shim-sha256','spec-sha256','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    need(os.name=='nt' and Path.cwd().resolve()==ROOT and sys.flags.isolated and sys.flags.no_site
         and sys.dont_write_bytecode,'fixed Windows isolated invocation')
    expected=[sys.executable,'-I','-S','-B',str(SELF),'--source-sha256',args.source_sha256,
              '--shim-sha256',args.shim_sha256,'--spec-sha256',args.spec_sha256,'--output',str(Path(args.output).resolve())]
    need(sys.orig_argv==expected,'exact control invocation')
    REPORT=dict(schema='common-tiff-dimensions-scratch-scan-controls-v1',status='REFUSED',complete=False,rows=[],
                historical_build1_cause='unknown; missing resolved spellings were not retained',
                scope='actual production shim with private controlled I/O; no compiler/product or peer process activity')
    try:
        pins={};raws={}
        for role,path,cap,expected in (('source',SELF,32*1024,args.source_sha256),('shim',SHIM,16*1024,args.shim_sha256),
                                      ('spec',SPEC,16*1024,args.spec_sha256),('held',BASE,64*1024,BASE_SHA)):
            raw,pin=read(path,cap);need(pin['sha256']==expected and len(expected)==64,'exact released '+role)
            raws[role]=raw;pins[role]=pin
        REPORT['sources']=pins
        out=safe(args.output);need(out==HERE/'work/scratch-scan-controls-1' and not out.exists() and out.parent.is_dir(),'fresh fixed control root')
        out.mkdir();OUT=out;scratch=out/'scratch';retained=out/'retained';scratch.mkdir();retained.mkdir()
        shim=types.ModuleType('independent_actual_scratch_shim');shim.__file__=str(SHIM)
        exec(compile(raws['shim'],str(SHIM),'exec'),shim.__dict__)
        tree=ast.parse(raws['held'],str(BASE));retain()
        for index,ident in enumerate(IDS):
            try:row=run_case(index,tree,shim,scratch,retained)
            except (ValueError,OSError,TypeError,KeyError,AttributeError) as error:
                row=dict(id=ident,passed=False,error=error_value(error))
            need(len(encoded(row))<=2048,'bounded row before retention');REPORT['rows'].append(row);retain();bound()
        for role,pin in pins.items():
            raw,after=read(pin['path'],64*1024);need(after==pin,'unchanged final exact source '+role)
        need(len(REPORT['rows'])==16 and [r['id'] for r in REPORT['rows']]==list(IDS),'complete fixed row identities')
        REPORT['complete']=all(r['passed'] for r in REPORT['rows'])
        if REPORT['complete']:REPORT['status']='PASS_FIXED_SCRATCH_SCAN_CONTROLS'
    except (ValueError,OSError,TypeError,KeyError,AttributeError) as error:
        REPORT.update(status='REFUSED',complete=False,error=error_value(error))
    REPORT['work_sample']=dict(cpu_seconds=time.process_time()-CPU,wall_seconds=time.monotonic()-START,
                               read_bytes=READ,written_bytes=WRITE,metadata_operations=META)
    REPORT['publication_allowance']=dict(cpu_seconds=1,wall_seconds=2)
    try:bound(reserve=True)
    except ValueError as error:REPORT.update(status='REFUSED',complete=False,resource_error=error_value(error))
    raw=encoded(REPORT);need(len(raw)<=64*1024,'finite final record')
    if OUT is not None:write(OUT/'result.json',raw,64*1024)
    need(sys.stdout.buffer.write(raw)==len(raw),'complete stdout');sys.stdout.buffer.flush();bound()
    return 0 if REPORT['complete'] else 1


if __name__=='__main__':raise SystemExit(main())
