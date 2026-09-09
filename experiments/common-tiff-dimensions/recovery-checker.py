"""Saved dimensions checker: additive execution authority, frozen scientific bodies."""
import time
START=time.perf_counter();CPU=time.process_time()
import argparse,ast,copy,hashlib,json,os,stat,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
ORIGINAL=HERE/'independent-controls.py'
ORIGINAL_SHA='8fefa5e31c614595367f644b314ece77da6bf5d4ec54c4edde80816a0e8cee47'
SPEC_SHA='055b66302e3f73d3d62226c25cef939f74dd664149e1a7d005991ce09286489b'
FREEZE_SHA='f3778c80df31b6cde6e253797cf497ca2cdfced85f8507ae126ba03ce8563708'
SCHEMAS={'common-tiff-dimensions-owned-stage-v1':'common-tiff-dimensions-owned-stage-v2',
 'common-tiff-dimensions-stage-external-v1':'common-tiff-dimensions-stage-external-v2',
 'common-tiff-dimensions-parent-tail-v1':'common-tiff-dimensions-parent-tail-v2',
 'common-tiff-dimensions-stage-release-v1':'common-tiff-dimensions-stage-release-v2','run-stage.py':'run-recovery-stage.py'}
MIB=1<<20;O=A=None;OWN=None;PROOF=None;RECOVERY=None;EXPECTED_SOURCE=None

def need(v,label):
    if not v:raise ValueError(label)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
def check():need(time.process_time()-CPU<=45 and time.perf_counter()-START<=90,'whole checker child work allowance')
def ident(s):return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,'st_file_attributes',0))
def full(s):return ident(s)+(s.st_ctime_ns,)

def read(path,cap):
    check();path=Path(path)
    for q in (path,*path.parents):
        s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'plain adapter read ancestry')
    before=path.lstat();need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=cap,'bounded adapter source/metadata')
    with path.open('rb') as f:
        a=os.fstat(f.fileno());need(ident(before)==ident(a),'shared adapter opened identity')
        raw=f.read(before.st_size+1);z=os.fstat(f.fileno())
    need(full(before)==full(path.lstat()) and full(a)==full(z) and len(raw)==before.st_size,'same adapter authenticated buffer')
    return raw

def load_original():
    global O,PROOF
    raw=read(ORIGINAL,128*1024);need(len(raw)==65751 and sha(raw)==ORIGINAL_SHA,'literal frozen scientific checker source')
    tree=ast.parse(raw);functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
    need(len(functions)==58,'exact58 original function definitions')
    O=types.ModuleType('dimensions_original_scientific_checker');O.__file__=str(ORIGINAL)
    exec(compile(raw,str(ORIGINAL),'exec'),O.__dict__)
    O.START=START;O.START_CPU=CPU
    original=next(n for n in functions if n.name=='saved_render_bundle');candidate=copy.deepcopy(original);counts={k:0 for k in SCHEMAS}
    for n in ast.walk(candidate):
        if isinstance(n,ast.Constant) and type(n.value) is str and n.value in SCHEMAS:
            key=n.value;counts[key]+=1;n.value=SCHEMAS[key]
    need(all(v==1 for v in counts.values()),'exact five execution-authority literals')
    reverse=copy.deepcopy(candidate);back={v:k for k,v in SCHEMAS.items()}
    for n in ast.walk(reverse):
        if isinstance(n,ast.Constant) and type(n.value) is str and n.value in back:n.value=back[n.value]
    need(ast.dump(reverse,include_attributes=False)==ast.dump(original,include_attributes=False),'complete metadata reader reverse AST')
    module=ast.fix_missing_locations(ast.Module(body=[candidate],type_ignores=[]))
    exec(compile(module,str(SELF),'exec'),O.__dict__)
    original_source=O.source_authority
    def fixture_source(expected):
        need(expected==EXPECTED_SOURCE,'current checker source argument')
        own=read(SELF,128*1024);need(sha(own)==expected,'actual execution checker identity')
        need(sha(read(HERE/'independent-spec.md',32*1024))==SPEC_SHA,'literal original fixture specification')
        return original_source(ORIGINAL_SHA)
    O.source_authority=fixture_source
    PROOF=dict(original_source=O.file_ref(ORIGINAL,raw),original_function_definitions=58,
        scientific_functions_loaded_from_exact_original=True,
        metadata_reader_original_ast_sha256=sha(ast.dump(original,include_attributes=False).encode()),
        metadata_reader_reverse_ast_sha256=sha(ast.dump(reverse,include_attributes=False).encode()),
        changed_literals=counts,scope='Only saved_render_bundle execution schemas/controller path and separate source-authority/main adapters; original prepare/main unused')


def get(ref,cap,empty=False):return O.read_ref(ref,cap,empty=empty)[0]
def parsed(ref,cap):return O.strict_json(get(ref,cap))
def same(a,b):return O.same_ref(a,b)

def transport(bundle,stage,sources):
    caps=dict(result=256*1024,tail=8192,outer=65536,stdout=8192,stderr=32768,exit=1024)
    need(type(bundle) is dict and set(bundle)==set(caps),'six actual recovery transport roles')
    raw={k:get(bundle[k],cap,empty=k=='stderr') for k,cap in caps.items()}
    result,tail,outer,advert=(O.strict_json(raw[k]) for k in ('result','tail','outer','stdout'))
    need(A.association_path(bundle['result']['path'])==HERE/'recovery-1/result.json' and
         A.association_path(bundle['tail']['path'])==HERE/'recovery-1/parent-tail.json','canonical recovery terminal locations')
    need(result['schema']=='common-tiff-dimensions-owned-stage-v2' and result['stage']==stage=='recovery'
         and result['status']=='COMPLETE_STAGE_UNVERIFIED' and result['error'] is None and
         result['finalization_errors']==[] and result['children']==[],'actual completed childless recovery parent')
    need(type(outer) is dict and set(outer)=={'schema','command','source','exit_code','timeout_terminated','elapsed_wall_seconds',
         'stdout','stderr','exit','stdout_bytes','stderr_bytes','scope'} and outer['schema']=='common-tiff-dimensions-stage-external-v2'
         and type(outer['exit_code']) is int and outer['exit_code']==0 and outer['timeout_terminated'] is False and raw['exit']==b'0\n',
         'actual recovery external completion')
    cp='experiments/common-tiff-dimensions/run-recovery-stage.py'
    need(same(outer['source'],dict(path=cp,**sources[cp])) and outer['command']==result['invocation'],'recovery actual controller/argv')
    for k in ('stdout','stderr','exit'):need(same(outer[k],bundle[k]),'recovery exact raw stream refs')
    need(type(outer['stdout_bytes']) is int and outer['stdout_bytes']==len(raw['stdout']) and
         type(outer['stderr_bytes']) is int and outer['stderr_bytes']==len(raw['stderr']) and raw['stderr']==b'',
         'complete recovery raw stream extents')
    need(set(advert)=={'status','result','tail'} and advert['status']==result['status'] and
         same(advert['result'],bundle['result']) and same(advert['tail'],bundle['tail']) and raw['stdout']==encoded(advert),
         'recovery same-byte terminal advertisement')
    need(tail['schema']=='common-tiff-dimensions-parent-tail-v2' and same(tail['result'],bundle['result']) and
         tail['cpu_accounting_complete'] is True and type(tail['live_child_cpu_seconds']) in (int,float) and
         type(tail['completed_child_cpu_seconds']) in (int,float) and tail['live_child_cpu_seconds']==tail['completed_child_cpu_seconds']==0 and
         tail['final_external_allowance']==dict(cpu_seconds=2,wall_seconds=3),'recovery childless terminal accounting')
    need(all(O.finite_nonnegative(tail[k]) for k in ('actual_parent_cpu_sample','whole_wall_sample')) and
         O.finite_nonnegative(outer['elapsed_wall_seconds']) and tail['actual_parent_cpu_sample']+2<=10 and
         outer['elapsed_wall_seconds']<=min(20,tail['whole_wall_sample']+3),'recovery finite complete envelope')
    need(result['limits']==dict(cpu_seconds=10,wall_seconds=20,committed_bytes=1<<30,file_bytes=2*MIB,scratch_bytes=0)
         and result['work']['cpu_accounting_complete'] is True,'recovery exact retained allocation')
    release=parsed(result['release'],MIB)
    need(A.association_path(result['release']['path'])==HERE/'work/recovery-recovery-release-1.json','fixed admission release')
    need(set(release)=={'schema','stage','source_bindings','inputs','executable','fixtures','run_bundle','prerequisites','command','children'}
         and release['schema']=='common-tiff-dimensions-stage-release-v2' and release['stage']=='recovery' and
         release['source_bindings']==sources and release['children']==[] and release['run_bundle'] is None,
         'same current recovery release and source namespace')
    need([result['release']['sha256'] if x=='ACTUAL_RELEASE_SHA256' else x for x in release['command']]==result['invocation'],
         'actual recovery release command')
    return result,tail,outer,release


def recovery_preflight(args):
    global A,RECOVERY
    # Authenticate new execution and historical admission before original
    # fixture_authority opens any TIFF payload or reconstructs literal pixels.
    rb=read(args.run_bundle,65536);need(sha(rb)==args.run_bundle_sha256 and Path(args.run_bundle).resolve()==HERE/'render-bundle-1.json','root-bound actual render bundle')
    bundle=O.strict_json(rb);result=parsed(bundle['result'],256*1024);release=parsed(result['release'],MIB)
    need(set(release)=={'schema','stage','source_bindings','inputs','executable','fixtures','run_bundle','prerequisites','command','children'}
         and release['schema']=='common-tiff-dimensions-stage-release-v2' and release['stage']=='render','closed current render release')
    need(Path(result['release']['path']).resolve()==HERE/'work/render-recovery-release-1.json' or
         (ROOT/result['release']['path']).resolve()==HERE/'work/render-recovery-release-1.json','current render release location')
    sources=release['source_bindings'];key='experiments/common-tiff-dimensions/recovery-authority.py'
    need(type(sources) is dict and key in sources,'current authority source pin')
    hraw=get(dict(path=key,**sources[key]),32*1024)
    A=types.ModuleType('independent_checker_recovery_authority');A.__file__=str(ROOT/key)
    exec(compile(hraw,str(ROOT/key),'exec'),A.__dict__)
    fraw=get(A.HISTORY['producer_freeze'],65536)
    need(sha(fraw)==FREEZE_SHA,'literal original190 freeze')
    frozen=O.strict_json(fraw);producer=frozen['source_bindings'];A.extension(producer,sources)
    need(sources['experiments/common-tiff-dimensions/recovery-checker.py']==dict(bytes=OWN['bytes'],sha256=OWN['sha256']),
         'root-bound actual execution checker source')
    need(producer['experiments/common-tiff-dimensions/independent-controls.py']==dict(bytes=65751,sha256=ORIGINAL_SHA)
         and producer['experiments/common-tiff-dimensions/independent-spec.md']==dict(bytes=19270,sha256=SPEC_SHA),
         'original fixture producer/specification remain unchanged')
    prior=release['prerequisites']
    need(type(prior) is dict and set(prior)=={'build','prepare','recovery'} and A.exact(prior['build'],A.HISTORY['build'])
         and A.exact(prior['prepare'],A.HISTORY['prepare']),'historical build and refused preparation remain separate')
    rec,tail,outer,rr=transport(prior['recovery'],'recovery',sources)
    need(rr['prerequisites']=={'build':A.HISTORY['build'],'prepare':A.HISTORY['prepare']} and
         A.exact(rr['fixtures'],A.HISTORY['index']) and A.exact(release['fixtures'],A.HISTORY['index']) and
         A.exact(rr['executable'],A.EXE_REF) and A.exact(release['executable'],A.EXE_REF),'same admitted historical inputs')
    need(rec['compiled_source_closure']==A.COMPILED,'recovery actual unchanged compiled source closure')
    admission_ref=rec['artifacts']['admission']
    need(A.association_path(admission_ref['path'])==HERE/'recovery-1/admission.json' and
         same(rec['artifacts']['fixture_index'],A.HISTORY['index']),'genuine saved-fixture receipt location')
    admission=parsed(admission_ref,128*1024)
    indexraw=get(A.HISTORY['index'],256*1024);index=O.strict_json(indexraw)
    need(sha(indexraw)==args.fixtures_sha256 and Path(args.fixtures).resolve()==HERE/'prepare-1/fixtures/index.json','unchanged fixed fixture metadata')
    A.admission_association(admission,A.HISTORY['index'],A.HISTORY['producer_freeze'],producer,sources,
                            [A.HISTORY['index'],*index['generated_files']])
    # The pure admission control is additional to authenticating actual immutable
    # failure metadata. No historical failed parent is coerced into completion.
    p=parsed(A.HISTORY['prepare']['result'],256*1024);c=parsed(A.HISTORY['prepare_child'],32768)
    g=parsed(A.HISTORY['prepare_log'],65536);t=parsed(A.HISTORY['prepare']['tail'],8192)
    outer_old=parsed(A.HISTORY['prepare']['outer'],65536);oldrelease=parsed(A.HISTORY['prepare_release'],MIB)
    need(oldrelease['source_bindings']==producer and oldrelease['schema']=='common-tiff-dimensions-stage-release-v1'
         and oldrelease['stage']=='prepare' and len(oldrelease['children'])==1,'actual historical generator release')
    summary=A.admit_saved_prepare(p,c,g,t,outer_old,get(A.HISTORY['prepare']['exit'],1024),A.HISTORY['index'],oldrelease['children'][0]['command'])
    need(same(p['release'],A.HISTORY['prepare_release']) and type(p['children']) is list and len(p['children'])==1
         and same(p['children'][0],A.HISTORY['prepare_child'])
         and same(c['log'],A.HISTORY['prepare_log']) and c['log_bytes']==A.HISTORY['prepare_log']['bytes'],'linked original generator receipt')
    controls=admission['controls'];controlraw=get(controls['result'],128*1024)
    need(controlraw==get(controls['stdout'],128*1024) and get(controls['stderr'],16384,True)==b'' and
         get(controls['exit'],1024)==b'0\n','actual unchanged recovery control bytes')
    cv=O.strict_json(controlraw)
    need(cv['schema']=='common-tiff-dimensions-recovery-controls-v1' and cv['status']=='PASS_FIXED_RECOVERY_METADATA_CONTROLS'
         and cv['controls_complete'] is True and type(cv['groups']) is int and cv['groups']==40 and
         type(cv['completed_groups']) is int and cv['completed_groups']==40 and len(cv['rows'])==40 and
         all(r['passed'] is True for r in cv['rows']) and same(cv['source'],dict(path='experiments/common-tiff-dimensions/recovery-controls.py',
         **sources['experiments/common-tiff-dimensions/recovery-controls.py'])),'actual independent metadata control pass/source')
    control_source=get(dict(path='experiments/common-tiff-dimensions/recovery-controls.py',
                           **sources['experiments/common-tiff-dimensions/recovery-controls.py']),128*1024)
    definitions=[n for n in ast.parse(control_source).body if isinstance(n,ast.Assign) and
                 any(isinstance(t,ast.Name) and t.id=='IDS' for t in n.targets)]
    need(len(definitions)==1,'one fixed control population declaration')
    ids=ast.literal_eval(definitions[0].value)
    need(type(ids) is tuple and len(ids)==len(set(ids))==40 and [r['id'] for r in cv['rows']]==list(ids),
         'exact independently fixed40 metadata groups')
    expected_control=[sys.executable,'-I','-S','-B',str(HERE/'recovery-controls.py'),'--source-sha256',
        sources['experiments/common-tiff-dimensions/recovery-controls.py']['sha256'],'--output',str(HERE/'work/recovery-controls-1')]
    need(cv['invocation']==expected_control,'actual independent controls invocation')
    control_outer=parsed(controls['outer'],65536)
    outer_keys={'schema','command','source','exit_code','timeout_terminated','elapsed_wall_seconds',
                'stdout','stderr','exit','stdout_bytes','stderr_bytes','scope','capture_accounting'}
    need(type(control_outer) is dict and set(control_outer)==outer_keys and
         control_outer['schema']=='common-tiff-dimensions-recovery-controls-external-v1' and
         type(control_outer['exit_code']) is int and control_outer['exit_code']==0 and
         control_outer['timeout_terminated'] is False and control_outer['command']==expected_control and
         same(control_outer['source'],cv['source']),'actual controls outer/source/command/no-timeout')
    need(A.association_path(controls['outer']['path'])==HERE/'work/controls-recovery-external-1-outer.json' and
         A.association_path(controls['result']['path'])==HERE/'work/recovery-controls-1/result.json',
         'fixed actual control result and outer paths')
    for role,suffix in (('stdout','stdout.bin'),('stderr','stderr.bin'),('exit','exit.txt')):
        need(same(control_outer[role],controls[role]) and A.association_path(controls[role]['path'])==
             HERE/('work/controls-recovery-external-1-'+suffix),'controls outer actual raw associations')
    need(type(control_outer['stdout_bytes']) is int and control_outer['stdout_bytes']==len(controlraw) and
         type(control_outer['stderr_bytes']) is int and control_outer['stderr_bytes']==0 and
         O.finite_nonnegative(control_outer['elapsed_wall_seconds']) and control_outer['elapsed_wall_seconds']<=10,
         'actual complete controls child interval and streams')
    ca=control_outer['capture_accounting']
    need(type(ca) is dict and set(ca)=={'parent_cpu_sample','whole_wall_sample','publication_allowance','reserved','admitted','error','scope'} and
         ca['admitted'] is True and ca['error'] is None and
         O.finite_nonnegative(ca['parent_cpu_sample']) and O.finite_nonnegative(ca['whole_wall_sample']) and
         A.exact(ca['publication_allowance'],{'cpu_seconds':1,'wall_seconds':2}) and
         A.exact(ca['reserved'],{'cpu_seconds':5,'overhead_wall_seconds':10,'whole_wall_seconds':20}) and
         ca['parent_cpu_sample']+1<=5 and ca['whole_wall_sample']>=control_outer['elapsed_wall_seconds'] and
         ca['whole_wall_sample']+2<=20 and ca['whole_wall_sample']-control_outer['elapsed_wall_seconds']+2<=10,
         'separate controls capture sampled work and publication allowance')
    RECOVERY=dict(admission=admission_ref,recovery_bundle=prior['recovery'],old_prepare=summary,
        producer_freeze=A.HISTORY['producer_freeze'],producer_source_map_sha256=A.map_sha(producer),execution_source_map_sha256=A.map_sha(sources),
        controls=controls,scope='Recovered saved fixtures; historical prepare REFUSED; actual new recovery parent complete. No physical/scientific conclusion.')
    return index


def main():
    global EXPECTED_SOURCE,OWN
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['verify'])
    for flag in ('fixtures','fixtures-sha256','run-bundle','run-bundle-sha256','output','source-sha256'):parser.add_argument('--'+flag,required=True)
    args=parser.parse_args();out=Path(args.output).resolve();EXPECTED_SOURCE=args.source_sha256
    expected=[sys.executable,'-I','-S','-B',str(SELF),'verify','--fixtures',str(Path(args.fixtures).resolve()),'--fixtures-sha256',args.fixtures_sha256,
        '--run-bundle',str(Path(args.run_bundle).resolve()),'--run-bundle-sha256',args.run_bundle_sha256,'--output',str(out),'--source-sha256',args.source_sha256]
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.orig_argv==expected,'actual isolated recovery checker invocation')
    raw=read(SELF,128*1024);need(sha(raw)==args.source_sha256,'actual recovery checker source identity')
    OWN=dict(path=str(SELF),bytes=len(raw),sha256=sha(raw));load_original()
    need(out==HERE/'verify-1/check' and not out.exists() and out.parent.is_dir(),'fresh original fixed saved-checker output')
    out.mkdir();O.OUTPUT=out;O.WORK.update(schema='common-tiff-dimensions-independent-verification-v1',status='REFUSED',software_integration_complete=False,
        execution_source=OWN,invocation=sys.orig_argv,source_adapter=PROOF)
    try:
        O.progress();recovery_preflight(args);O.WORK['recovery_authority']=RECOVERY;O.progress();answer=O.verify(args)
    except (ValueError,KeyError,TypeError,OSError,UnicodeError,O.struct.error) as e:
        answer=O.WORK;answer.update(status='REFUSED',software_integration_complete=False,error=O.bounded_error(e),
            scope='Recovery execution authority or saved-reader refusal; not a new product result')
    answer['own_work']=dict(cpu_seconds=time.process_time()-CPU,wall_seconds=time.perf_counter()-START)
    answer['publication_allowance']=dict(cpu_seconds=1,wall_seconds=2)
    if answer['own_work']['cpu_seconds']+1>45 or answer['own_work']['wall_seconds']+2>90:
        answer.update(status='REFUSED',software_integration_complete=False,resource_refusal='checker allowance including publication')
    raw=O.canonical(answer)+b'\n';need(len(raw)<=MIB,'unchanged1MiB checker report cap')
    O.write_fresh(out/'result.json',raw,MIB)
    need(sys.stdout.buffer.write(raw)==len(raw),'whole saved checker stdout');sys.stdout.buffer.flush();check()
    return 0 if answer['software_integration_complete'] else 1

if __name__=='__main__':raise SystemExit(main())
