"""Metadata-only preparation of the one saved continuation verification.
Reuses exact held prepare-execution.py reader/publication/pricing definitions;
never calls its main or reads RAW/image/test-executable payloads. Same bounded
30 CPU/60 wall,128 MiB read/24 MiB write slice, with1 CPU/2 wall publication.
"""
from pathlib import Path
import hashlib,os,sys,time,types
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
START=time.monotonic()
MIB=1<<20
PREP_PIN={'bytes':19250,'sha256':'b4e19bd1a2ce5550b286b9d14b8c7e3037657e5e4b7904324aaf57b7a06d92f6'}
OLD_FREEZE={'path':'experiments/native-sensor-transfer/work/execution-source-freeze-1.json','bytes':21318,
            'sha256':'ac5063c60da834a39e8f5e9ac627b481d8451e0af4f295ebeebadbb2aa0e6bbb'}
OLD_MAP_SHA='7c3867e4957ddb77a3b0c143266fec844afa679e7ce612cc5fed927378bdfb77'
NATIVE_EXTRAS=('run-native-continuation.py','native-publication-scan.py','publication-race-controls.py',
               'capture-native-continuation.py','prepare-native-continuation.py')
VERIFY_EXTRAS=('verify-recovery.py','prepare-verify-recovery.py','run-verify-continuation.py','capture-verify-continuation.py')

def need(v,s):
    if not v:raise ValueError(s)

def load_prep():
    p=HERE/'prepare-execution.py';before=p.stat();need(before.st_size==PREP_PIN['bytes'],'held preparation extent')
    with p.open('rb') as f:
        opened=os.fstat(f.fileno());raw=f.read(PREP_PIN['bytes']+1);closed=os.fstat(f.fileno())
    after=p.stat();shared=lambda q:(q.st_dev,q.st_ino,q.st_size,q.st_mtime_ns,q.st_nlink)
    full=lambda q:shared(q)+(q.st_ctime_ns,)
    need(full(before)==full(after) and full(opened)==full(closed) and shared(before)==shared(opened) and
         len(raw)==PREP_PIN['bytes'] and hashlib.sha256(raw).hexdigest()==PREP_PIN['sha256'],'held preparation bytes')
    p=types.ModuleType('held_metadata_preparation');p.__file__=str(HERE/'prepare-execution.py')
    exec(compile(raw,p.__file__,'exec'),p.__dict__);p.START=START;p.READ+=len(raw)+1;p.check();return p

def native_bundle(p):
    output=HERE/'native-3';stem=HERE/'work/native-external-3-'
    paths={'result':output/'result.json','tail':output/'parent-tail.json','outer':Path(str(stem)+'outer.json'),
           'stdout':Path(str(stem)+'stdout.bin'),'stderr':Path(str(stem)+'stderr.bin'),'exit':Path(str(stem)+'exit.txt')}
    raw={k:p.read(v,p.BUNDLE_CAPS[k],empty=k=='stderr') for k,v in paths.items()}
    refs={k:p.ref(paths[k],v) for k,v in raw.items()}
    result,tail,outer,advert=[p.strict(raw[k]) for k in ('result','tail','outer','stdout')]
    need(result['schema']=='native-sensor-transfer-owned-stage-v1' and result['stage']=='native' and
         result['status']=='COMPLETE_STAGE_UNVERIFIED' and result['error'] is None and result['finalization_errors']==[],
         'complete actual continuation parent')
    need(outer['schema']=='native-sensor-transfer-stage-external-v1' and type(outer['exit_code']) is int and
         outer['exit_code']==0 and outer['timeout_terminated'] is False and raw['exit'].strip()==b'0' and
         outer['command']==result['invocation'],'actual continuation external zero')
    for k in ('stdout','stderr','exit'):p.same(outer[k],refs[k],empty=k=='stderr')
    need(outer['stdout_bytes']==len(raw['stdout']) and outer['stderr_bytes']==len(raw['stderr']) and
         p.encoded(advert)==raw['stdout'] and advert['status']==result['status'],'actual continuation streams')
    p.same(advert['result'],refs['result']);p.same(advert['tail'],refs['tail']);p.same(tail['result'],refs['result'])
    need(tail['schema']=='native-sensor-transfer-parent-tail-v1' and tail['cpu_accounting_complete'] is True and
         tail['live_child_cpu_seconds']==0 and tail['final_external_allowance']=={'cpu_seconds':2,'wall_seconds':3},'continuation terminal accounting')
    prior=p.strict(p.bound_read(result['release'],MIB))
    need(prior['schema']=='native-sensor-transfer-continuation-release-v1' and prior['stage']=='native' and
         [result['release']['sha256'] if v=='ACTUAL_RELEASE_SHA256' else v for v in prior['command']]==result['invocation'],
         'actual continuation release command')
    key=(HERE/'run-native-continuation.py').relative_to(ROOT).as_posix()
    p.same(outer['source'],{'path':key,**prior['source_bindings'][key]})
    return refs,result,prior

def main():
    p=load_prep();py=str(Path(sys.executable));work=HERE/'work'
    need(os.name=='nt' and Path.cwd().resolve()==ROOT and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
         'fixed metadata-only recovery preparation')
    need(len(sys.orig_argv)==5 and sys.orig_argv[:4]==[py,'-I','-S','-B'] and
         p.path(sys.orig_argv[4])==HERE/'prepare-verify-recovery.py','exact preparation command')
    released=work/'verify-continuation-release-2.json';reader_path=work/'verify-recovery-reader-release-2.json'
    freeze_path=work/'verify-recovery-source-freeze-2.json';receipt_path=work/'verify-recovery-preparation-2.json'
    need(all(not q.exists() for q in (released,reader_path,freeze_path,receipt_path,HERE/'verify-2')),'fresh single verification preparation')
    original=p.strict(p.bound_read(OLD_FREEZE,MIB))['source_bindings'];p.map_shape(original)
    need(len(original)==150 and p.pin(p.encoded(original))['sha256']==OLD_MAP_SHA,'held original150 source map')
    native_ref,native,prior=native_bundle(p)
    held_freeze_raw=p.read(work/'native-continuation-source-freeze-3.json',MIB);held_freeze=p.strict(held_freeze_raw)
    need(held_freeze['schema']=='native-sensor-transfer-continuation-source-freeze-v1','held runtime source freeze')
    p.same(held_freeze['original_source_freeze'],OLD_FREEZE)
    previous=held_freeze['source_bindings'];p.map_shape(previous)
    addition={(HERE/name).relative_to(ROOT).as_posix() for name in NATIVE_EXTRAS}
    need(set(previous)==set(original)|addition and all(previous[k]==v for k,v in original.items()) and
         prior['source_bindings']==previous,'exact historical155 source map')
    current=dict(previous)
    for name in VERIFY_EXTRAS:
        key=(HERE/name).relative_to(ROOT).as_posix();need(key not in current,'additive verification source')
        current[key]=p.pin(p.read(HERE/name))
    current=dict(sorted(current.items()));p.map_shape(current);need(len(current)==159,'fixed current159 source map')
    for k,v in current.items():need(p.pin(p.read(p.source_path(k)))==v,'all actual unchanged source bytes')
    build_freeze=p.strict(p.read(work/'build-source-freeze-4.json',MIB))['source_bindings']
    bundles={};results={}
    for name in ('build-on','build-off','controls'):
        bundles[name],results[name]=p.bundle(name,original,build_freeze)
        for role in p.BUNDLE_CAPS:p.same(bundles[name][role],prior['prerequisites'][name][role],empty=role=='stderr')
    bundles['native']=native_ref
    closure=native['compiled_source_closure'];need(all(v['compiled_source_closure']==closure for v in results.values()),'same compiled closure')
    binaries={role:results[name]['artifacts']['executable'] for role,name in (('feature_on','build-on'),('feature_off','build-off'))}
    for role in binaries:p.same(binaries[role],prior['binaries'][role])
    original_refs=prior['originals'];binding=p.read(HERE/'input-bindings-1.json',16<<10)
    need(p.pin(binding)==p.BINDING_PIN and p.strict(binding)['originals']==original_refs,'same exact27 original identities')
    recovery=prior['recovery'];need(set(recovery)=={'failed_native','relocation','reused0'},'fixed actual recovery association')
    # Read only the authenticated root preservation metadata; never partial data.
    p.bound_read(recovery['relocation'],64<<10)
    prices=p.pricing('verify',current,binaries)
    prices['components']['extra_failed_native_header_child_and_bootstrap']=8*MIB
    prices['sum_bytes']=sum(prices['components'].values());prices['read_bytes']=((prices['sum_bytes']+MIB-1)//MIB)*MIB
    need(prices['read_bytes']<=2*1024*MIB,'bounded recovery reader read ceiling')
    limits={'cpu_seconds':1000,'wall_seconds':850,'memory_bytes':1024*MIB,'read_bytes':prices['read_bytes'],'write_bytes':64*MIB}
    command=[py,'-I','-S','-B',str(HERE/'verify-recovery.py'),'--mode','verify','--release',str(reader_path),
             '--release-sha256','ACTUAL_RELEASE_SHA256']
    reader=p.publish(reader_path,{'schema':'native-sensor-transfer-reader-recovery-release-v1','mode':'verify',
        'source_bindings':current,'originals':original_refs,'builds':{'feature_on':bundles['build-on'],'feature_off':bundles['build-off']},
        'native':{'failed':recovery['failed_native'],'resumed':native_ref},'controls':bundles['controls'],
        'output':str(HERE/'verify-2/check'),'limits':limits,'command':command})
    freeze=p.publish(freeze_path,{'schema':'native-sensor-transfer-verify-recovery-source-freeze-v1',
        'original_source_freeze':OLD_FREEZE,'native_source_freeze':p.ref(work/'native-continuation-source-freeze-3.json',held_freeze_raw),
        'source_bindings':current})
    inputs=[p.ref(Path(py),p.read(Path(py),MIB))]
    value={'schema':'native-sensor-transfer-continuation-release-v1','stage':'verify','source_bindings':current,'inputs':inputs,
        'originals':original_refs,'command':[py,'-I','-S','-B',str(HERE/'run-verify-continuation.py'),'--release',str(released),
                                           '--release-sha256','ACTUAL_RELEASE_SHA256'],
        'children':[{'command':[reader['sha256'] if x=='ACTUAL_RELEASE_SHA256' else x for x in command],'expected_exit_code':0}],
        'binaries':binaries,'reader_release':reader,'prerequisites':bundles,'recovery':recovery}
    for k,v in current.items():need(p.pin(p.read(p.source_path(k)))==v,'source stability through release')
    released_ref=p.publish(released,value);p.check();p.PUBLISHING=True
    record={'schema':'native-sensor-transfer-verify-recovery-preparation-v1','release':released_ref,'reader_release':reader,
        'source_freeze':freeze,'read_pricing':prices,'source_files':159,'invocation':sys.orig_argv,
        'cpu_sample_seconds':time.process_time(),'wall_sample_seconds':time.monotonic()-START,
        'read_bytes_sample':p.READ,'write_bytes_sample':p.WRITE,
        'allocation':{'cpu_seconds':30,'wall_seconds':60,'read_bytes':128*MIB,'write_bytes':24*MIB,'publication_cpu_seconds':1,'publication_wall_seconds':2},
        'scope':'Only metadata/source/Python bytes; no originals, partial payload, controls or scientific execution. Samples exclude final publication; external root accounting required.'}
    receipt=p.publish(receipt_path,record);raw=p.encoded({'release':released_ref,'reader_release':reader,'preparation':receipt})
    need(len(raw)<=4096 and p.WRITE+len(raw)<=24*MIB,'bounded metadata stdout');p.WRITE+=len(raw)
    need(sys.stdout.buffer.write(raw)==len(raw),'full preparation stdout');sys.stdout.buffer.flush();p.check()

if __name__=='__main__':main()
