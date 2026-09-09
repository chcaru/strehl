"""Thin saved-authority continuation for the held independent native reader.
No frozen source is edited. The original Consumer, decode, numerical functions,
and successful 175 controls are reused from exact authenticated source bytes.
Only old clean invocation0 plus new invocations1..8 enter science. Native1 and
its terminated dark child remain failed, separately charged evidence.
"""
from pathlib import Path
import argparse, hashlib, json, os, sys, time, types
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
START=time.monotonic()
MIB=1<<20
OLD_READER={'bytes':81550,'sha256':'b2ff16a277a09ba321c3c54e1788543012e28a5cfc08612d66a62498cbf3f29b'}
OLD_MAP_SHA='7c3867e4957ddb77a3b0c143266fec844afa679e7ce612cc5fed927378bdfb77'
CAPS={'result':256<<10,'tail':8<<10,'outer':64<<10,'stdout':8<<10,'stderr':32<<10,'exit':1024}


def need(value,reason):
    if not value:raise ValueError(reason)

def original_module():
    # Root's owned runner separately authenticates this additive entry point.
    # This finite bootstrap authenticates every byte before executing only the
    # held module's definitions; its __main__ branch is not taken.
    p=HERE/'independent-read.py'
    before=p.stat();need(before.st_size==OLD_READER['bytes'],'held reader bootstrap extent')
    with p.open('rb') as f:
        opened=os.fstat(f.fileno());raw=f.read(OLD_READER['bytes']+1);closed=os.fstat(f.fileno())
    after=p.stat()
    shared=lambda q:(q.st_dev,q.st_ino,q.st_size,q.st_mtime_ns,q.st_nlink)
    full=lambda q:shared(q)+(q.st_ctime_ns,)
    need(full(before)==full(after) and full(opened)==full(closed) and shared(before)==shared(opened) and
         len(raw)==OLD_READER['bytes'] and hashlib.sha256(raw).hexdigest()==OLD_READER['sha256'],'held reader bootstrap bytes')
    module=types.ModuleType('native_frozen_reader');module.__file__=str(p)
    # One source-proven output-role literal changes for fresh verify2 only.
    old_role=b"HERE/'verify-1'/'check'";new_role=b"HERE/'verify-2'/'check'"
    need(raw.count(old_role)==1,'sole original verification output role')
    adapted=raw.replace(old_role,new_role)
    need(adapted.replace(new_role,old_role)==raw,'output-role-only reverse identity')
    exec(compile(adapted,str(p),'exec'),module.__dict__)
    module.START=START
    return module,len(raw)+1

def publication_io(o,limits,output):
    class PublicationIO(o.IO):
        def array(self,name,a):
            # Filename metadata only: the inherited serializer receives a unchanged.
            need(type(name) is str and name.isascii(),'ASCII statistical array name')
            normalized=name.lower().replace('_','-')
            need(len(normalized)==len(name),'same-length array filename normalization')
            if not hasattr(self,'array_names'):self.array_names={}
            need(normalized not in self.array_names,'normalized array publication collision')
            self.array_names[normalized]=name
            return super().array(normalized,a)
    return PublicationIO(limits,output)


def same_bundle(o,left,right):
    o.closed(left,CAPS,'native six roles');o.closed(right,CAPS,'native six roles')
    for k in CAPS:o.same_ref(left[k],right[k],empty=k=='stderr')

def stage_header(o,io,bundle,attempt,*,success):
    o.closed(bundle,CAPS,'native six actual roles')
    output=HERE/f'native-{attempt}';stem=HERE/'work'/f'native-external-{attempt}-'
    paths={'result':output/'result.json','tail':output/'parent-tail.json',
           'outer':Path(str(stem)+'outer.json'),'stdout':Path(str(stem)+'stdout.bin'),
           'stderr':Path(str(stem)+'stderr.bin'),'exit':Path(str(stem)+'exit.txt')}
    for k,p in paths.items():o.role_ref(bundle[k],p,empty=k=='stderr')
    raw={k:io.read(bundle[k],cap,empty=k=='stderr') for k,cap in CAPS.items()}
    result,tail,outer,advert=[o.metadata_json(raw[k]) for k in ('result','tail','outer','stdout')]
    need(result['schema']=='native-sensor-transfer-owned-stage-v1' and result['stage']=='native' and
         result['status']==('COMPLETE_STAGE_UNVERIFIED' if success else 'REFUSED') and
         (result['error'] is None if success else result['error'] is not None) and result['finalization_errors']==[],
         'actual native parent disposition')
    o.closed(outer,('schema','command','source','exit_code','timeout_terminated','elapsed_wall_seconds',
        'stdout','stderr','exit','stdout_bytes','stderr_bytes','scope'),'native external keys')
    need(outer['schema']=='native-sensor-transfer-stage-external-v1' and type(outer['exit_code']) is int and
         outer['exit_code']==(0 if success else 1) and raw['exit'].strip()==(b'0' if success else b'1') and
         outer['timeout_terminated'] is False and outer['command']==result['invocation'],'actual native outer disposition')
    for k in ('stdout','stderr','exit'):o.same_ref(outer[k],bundle[k],empty=k=='stderr')
    need(type(outer['stdout_bytes']) is int and outer['stdout_bytes']==len(raw['stdout']) and
         type(outer['stderr_bytes']) is int and outer['stderr_bytes']==len(raw['stderr']),'native outer raw extents')
    o.closed(advert,('status','result','tail'),'native actual advertisement')
    need(advert['status']==result['status'] and raw['stdout']==o.encoded(advert),'native raw advertisement bytes')
    o.same_ref(advert['result'],bundle['result']);o.same_ref(advert['tail'],bundle['tail']);o.same_ref(tail['result'],bundle['result'])
    need(tail['schema']=='native-sensor-transfer-parent-tail-v1' and tail['cpu_accounting_complete'] is True and
         tail['live_child_cpu_seconds']==0 and tail['final_external_allowance']=={'cpu_seconds':2,'wall_seconds':3} and
         result['work']['cpu_accounting_complete'] is True,'native complete terminal accounting')
    values={k:o.finite(tail[k],'native tail finite time') for k in
            ('actual_parent_cpu_sample','whole_wall_sample','completed_child_cpu_seconds')}
    elapsed=o.finite(outer['elapsed_wall_seconds'],'native whole stage wall')
    need(all(v>=0 for v in values.values()) and 0<=elapsed<=1200 and elapsed<=values['whole_wall_sample']+3 and
         values['actual_parent_cpu_sample']+values['completed_child_cpu_seconds']+2<=1800,'actual native parent allocation')
    release=io.json(result['release'],MIB)
    keys=('schema','stage','source_bindings','inputs','originals','command','children','binaries','reader_release','prerequisites')
    o.closed(release,keys+(('recovery',) if success else ()),'native actual release keys')
    need(release['schema']==('native-sensor-transfer-continuation-release-v1' if success else 'native-sensor-transfer-stage-release-v1') and
         release['stage']=='native' and release['reader_release'] is None,'native release identity')
    need([result['release']['sha256'] if v=='ACTUAL_RELEASE_SHA256' else v for v in release['command']]==result['invocation'],
         'native actual released command')
    name='run-native-continuation.py' if success else 'run-stage.py'
    key=(HERE/name).relative_to(ROOT).as_posix()
    o.same_ref(outer['source'],{'path':key,**release['source_bindings'][key]})
    io.read({'path':key,**release['source_bindings'][key]},128<<10)
    return {'bundle':bundle,'result':result,'tail':tail,'outer':outer,'release':release,'output':output}

def actual_invocation(o,child,operation,invocation,on,off,*,continued):
    expected=[str(Path(o.canonical_path((on if invocation<7 else off)['path']))),'--ignored','--exact',
              'merge_cmd::native_sensor_transfer::fixed_native_sensor_transfer_pair','--nocapture','--test-threads=1']
    actual=child['value']['command']
    need(len(actual)==len(expected) and o.canonical_path(actual[0])==o.canonical_path(expected[0]) and actual[1:]==expected[1:],
         'actual continuation feature executable/argv')
    baseline={'ordinal':invocation-1 if continued else invocation,'expected_exit_code':0,'status':'EXPECTED_PROCESS_DISPOSITION',
              'environment':{'RAYON_NUM_THREADS':'4','STREHL_PYRAMID_WORKERS':'4','NATIVE_SENSOR_TRANSFER_INVOCATION':str(invocation)}}
    if continued:baseline['invocation']=invocation
    need(operation==baseline,'actual continuation operation/environment')
    need(b'running 1 test' in child['raw_log'] and b'1 passed; 0 failed' in child['raw_log'],'actual completed single test')

def refused_child(o,io,stage):
    value=io.json(stage['result']['children'][1],32<<10)
    o.role_ref(stage['result']['children'][1],stage['output']/'child-01.json')
    o.role_ref(value['log'],stage['output']/'child-01.log');log=io.read(value['log'],MIB,empty=True)
    need(type(value['log_bytes']) is int and value['log_bytes']==len(log) and
         value['command']==stage['release']['children'][1]['command'],'failed dark child command/log')
    job=value['job_accounting'];parts=[o.integer(job[k],0,2**63,'failed Job CPU integer') for k in
                                    ('total_user_100ns','total_kernel_100ns','total_cpu_100ns')]
    need(parts[0]+parts[1]==parts[2] and job['active_processes']==0 and value['terminal_job_accounting'] is True,
         'failed dark terminal Job accounting')
    need(type(value['exit_code']) is int and value['exit_code']!=0 and type(value['error']) is str and
         'FileNotFoundError' in value['error'] and 'frame-18-original.u16.stage' in value['error'] and
         value['cleanup_errors']==[] and value['termination']['attempted'] is True and value['termination']['succeeded'] is True,
         'retained scanner-interrupted dark failure')
    need(value['configured_job_limits']=={'flags':0x2200,'committed_bytes':2*1024*MIB} and
         o.integer(value['job_memory']['peak_job_memory_used_bytes'],0,2**63,'failed Job peak')<=2*1024*MIB and
         0<=o.finite(value['wall_seconds'],'failed child wall')<=1200 and parts[2]/1e7<=1800,'failed dark actual resource bounds')
    return {'record':stage['result']['children'][1],'log':value['log'],'status':'FAILED_EXCLUDED_FROM_SCIENCE',
            'error':value['error'],'exit_code':value['exit_code'],'job_cpu_seconds':parts[2]/1e7,
            'wall_seconds':value['wall_seconds'],'termination':value['termination'],
            'direct_exit_observed':value['direct_exit_observed'],'pipe_eof_observed':value['pipe_eof_observed']}

def recovery(o,io,release,old,current,on,off,closure):
    need(old['result']['compiled_source_closure']==closure,'old native compiled closure')
    need(len(old['result']['children'])==2 and len(old['result']['operations'])==2 and len(old['release']['children'])==9,
         'actual old prefix population')
    need(old['result']['operations'][1]=={'ordinal':1,'expected_exit_code':0,'status':'ATTEMPTED',
         'environment':{'RAYON_NUM_THREADS':'4','STREHL_PYRAMID_WORKERS':'4','NATIVE_SENSOR_TRANSFER_INVOCATION':'1'}},'old failed invocation')
    good=o.terminal_child(io,old['result']['children'][0],old['release']['children'][0],0,'native',old['output'])
    actual_invocation(o,good,old['result']['operations'][0],0,on,off,continued=False)
    failed=refused_child(o,io,old)
    need(good['cpu_seconds']+failed['job_cpu_seconds']==old['tail']['completed_child_cpu_seconds'],'old Jobs charged exactly once')
    old_entries=old['result']['artifacts']['traversals']
    need(type(old_entries) is list and len(old_entries)==1 and old_entries[0]['invocation']==0,'old sole completed paper traversal')
    o.role_ref(old_entries[0]['result'],HERE/'native-run-0/result.json')
    resumed=stage_header(o,io,release['native']['resumed'],3,success=True)
    mapping=resumed['release']['source_bindings']
    need(set(old['release']['source_bindings'])<=set(mapping)<=set(current) and
         all(current[k]==v for k,v in mapping.items()),'unchanged historical resumed source subset')
    need(resumed['result']['compiled_source_closure']==closure and resumed['release']['originals']==release['originals'],
         'same resumed compiled closure/originals')
    evidence=resumed['release']['recovery'];o.closed(evidence,('failed_native','relocation','reused0'),'released recovery roles')
    same_bundle(o,evidence['failed_native'],release['native']['failed'])
    o.closed(evidence['reused0'],('child','result'),'reused paper roles')
    o.same_ref(evidence['reused0']['child'],good['record']);o.same_ref(evidence['reused0']['result'],old_entries[0]['result'])
    for key in ('failed_native','relocation','reused0'):
        if key=='failed_native':same_bundle(o,resumed['result']['recovery'][key],evidence[key])
        elif key=='relocation':o.same_ref(resumed['result']['recovery'][key],evidence[key])
        else:
            for role in ('child','result'):o.same_ref(resumed['result']['recovery'][key][role],evidence[key][role])
    o.role_ref(evidence['relocation'],HERE/'work/native-partial-archive-1.json')
    relocation=io.json(evidence['relocation'],64<<10)
    o.closed(relocation,('source_commit','from','to','files','bytes','content_hashes_preserved','partial_population_excluded'),'root partial relocation receipt')
    need(o.canonical_path(relocation['from'])==o.canonical_path(str(HERE/'native-run-1')) and
         o.canonical_path(relocation['to'])==o.canonical_path(str(HERE/'native-attempt-1-partial')) and
         type(relocation['files']) is int and relocation['files']==130 and type(relocation['bytes']) is int and relocation['bytes']==48620310 and
         relocation['content_hashes_preserved'] is True and relocation['partial_population_excluded'] is True,
         'exact preserved partial population excluded')
    need(len(resumed['result']['children'])==len(resumed['release']['children'])==len(resumed['result']['operations'])==8,
         'eight actual continuation children')
    children=[]
    for i in range(8):
        child=o.terminal_child(io,resumed['result']['children'][i],resumed['release']['children'][i],i,'native',resumed['output'])
        actual_invocation(o,child,resumed['result']['operations'][i],i+1,on,off,continued=True);children.append(child)
    need(sum(v['cpu_seconds'] for v in children)==resumed['tail']['completed_child_cpu_seconds'],'new Jobs charged once without reused0')
    entries=resumed['result']['artifacts']['traversals'];need(type(entries) is list and len(entries)==9,'nine joined completed traversals')
    for i,item in enumerate(entries):
        o.closed(item,('invocation','result'),'joined traversal role');need(type(item['invocation']) is int and item['invocation']==i,'fixed joined order')
        o.role_ref(item['result'],HERE/f'native-run-{i}/result.json')
    o.same_ref(entries[0]['result'],old_entries[0]['result'])
    summary={'failed_parent':old['bundle'],'failed_parent_status':'REFUSED','reused_paper_child':good['record'],
             'excluded_dark_attempt':failed,'partial_preservation':evidence['relocation'],'resumed_parent':resumed['bundle'],
             'new_children':8,'selected_complete_traversals':9,'total_actual_child_attempts':10,
             'old_job_cpu_seconds':old['tail']['completed_child_cpu_seconds'],
             'new_job_cpu_seconds':resumed['tail']['completed_child_cpu_seconds'],
             'total_job_cpu_seconds':old['tail']['completed_child_cpu_seconds']+resumed['tail']['completed_child_cpu_seconds'],
             'parent_cpu_samples':[old['tail']['actual_parent_cpu_sample'],resumed['tail']['actual_parent_cpu_sample']],
             'parent_cpu_reservations':[2,2],'outer_stage_wall_seconds':[old['outer']['elapsed_wall_seconds'],resumed['outer']['elapsed_wall_seconds']],
             'scope':'Two actual parents retained; original failure never promoted. Failed partial images unvisited by this reader. Selected population excludes interrupted dark attempt; its work remains charged.'}
    return [io.json(item['result'],64<<10) for item in entries],summary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('verify',),required=True)
    parser.add_argument('--release',required=True);parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    o,boot=original_module();io=None;suite=None;consumer=None;release=None
    result={'schema':'native-sensor-transfer-independent-result-v1','mode':'verify','status':'REFUSED','error':None,
            'software_associations_complete':False,'physical_model_pass':None,'groups':[],
            'science_scope':'Original conditional Crop diagnostic; no repeated successful private controls or physical-model PASS.'}
    try:
        need(os.name=='nt' and Path.cwd().resolve()==ROOT and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,'fixed isolated recovery reader')
        need(Path(args.release).is_absolute(),'absolute recovery reader release');o.digest(args.release_sha256)
        raw,release_ref=o.bootstrap(args.release,MIB);need(release_ref['sha256']==args.release_sha256,'actual recovery release SHA')
        release=o.metadata_json(raw);o.closed(release,('schema','mode','source_bindings','originals','builds','native','controls','output','limits','command'),'closed recovery reader release')
        need(release['schema']=='native-sensor-transfer-reader-recovery-release-v1' and release['mode']=='verify','recovery reader schema/mode')
        expected=[str(Path(sys.executable)),'-I','-S','-B',str(HERE/'verify-recovery.py'),'--mode','verify','--release',str(Path(args.release)),
                  '--release-sha256',args.release_sha256]
        need(sys.orig_argv==expected==[args.release_sha256 if v=='ACTUAL_RELEASE_SHA256' else v for v in release['command']],'actual recovery reader command')
        need(release['limits']['cpu_seconds']<=1000 and release['limits']['wall_seconds']<=850 and release['limits']['write_bytes']<=64*MIB,'unchanged verify reader ceilings')
        io=publication_io(o,release['limits'],release['output']);io.read_bytes+=boot+len(raw)+1;io.tick()
        result.update(release=release_ref,command=sys.orig_argv,source_bindings_sha256=o.sha(o.encoded(release['source_bindings'])))
        o.original_population(release['originals']);o.closed(release['native'],('failed','resumed'),'two real native bundles')
        old=stage_header(o,io,release['native']['failed'],1,success=False)
        history=old['release']['source_bindings'];current=release['source_bindings']
        need(len(history)==150 and o.sha(o.encoded(history))==OLD_MAP_SHA and set(history)<set(current) and
             all(current[k]==v for k,v in history.items()),'exact original150 immutable source namespace')
        need(old['release']['originals']==release['originals'],'same historical27 originals')
        modules,buffers=o.load_independent_modules(io,current);n,d,c=modules
        result['original_source_bindings_sha256']=OLD_MAP_SHA
        result['additive_runtime_sources']=[{'path':k,**v} for k,v in current.items() if k not in history]
        o.closed(release['builds'],('feature_on','feature_off'),'both held build roles')
        builds={role:o.bundle_read(io,release['builds'][role],stage,history) for role,stage in
                (('feature_on','build-on'),('feature_off','build-off'))}
        exes={role:o.compiled_executable(io,v,role=='feature_on') for role,v in builds.items()}
        closure=o.compiled_closure(current,buffers)
        need(all(v['result']['compiled_source_closure']==closure for v in builds.values()),'unchanged compiled source closure')
        controls=o.bundle_read(io,release['controls'],'controls',history)
        need(controls['result']['compiled_source_closure']==closure,'original controls compiled closure')
        rows=o.saved_control_rows(io,controls,history,release['originals'])
        traversals,proof=recovery(o,io,release,old,current,exes['feature_on'],exes['feature_off'],closure)
        result['recovery_authority']=proof;result['compiled_source_closure']=closure
        result['stages']=[v['summary'] for v in builds.values()]+[controls['summary']]
        np,rawpy,runtime=o.array_runtime('verify',n);result['runtime']=runtime
        suite=c.Suite(np,n,d,io.tick);suite.rows={row['id']:row for row in rows}
        consumer=o.Consumer(np,n,d,io,release['originals']);result['population']=consumer.catalog(traversals)
        result['population_scope']='Nine selected complete traversals only; interrupted first dark work remains separate in recovery_authority.'
        decoded=consumer.independent_decode(rawpy);result['independent_decodes']=len(decoded)
        result['independent_decode_result']=io.publish('independent-decodes.json',decoded,MIB)
        frame_rows,outputs,witnesses=consumer.saved_arrays()
        suite.actual_observers(witnesses);suite.actual_weight(consumer.first_actual_weight);suite.output(complete=True)
        result['frame_checks']=io.publish('actual-frame-checks.json',frame_rows,2*MIB)
        result['output_checks']=io.publish('native-output-checks.json',outputs,128<<10)
        result['statistics']=consumer.statistics()
        result['software_associations_complete']=True;result['status']='PASS_CONDITIONAL_NATIVE_DIAGNOSTIC'
        for k,v in current.items():io.read({'path':k,**v},4*MIB)
        io.read(release_ref,MIB);io.tick(reserve=True)
    except BaseException as exc:
        result['status']='REFUSED';result['software_associations_complete']=False
        result['error']={'type':type(exc).__name__,'message':str(exc)[:4096]}
    if io is not None:io.publishing=True
    if consumer is not None:
        result['independent_decode_attempts']=getattr(consumer,'decode_attempts',0)
        result['independent_decodes']=len(getattr(consumer,'decode_observations',[]))
        result['saved_frame_attempts']=getattr(consumer,'frame_attempts',0)
        result['saved_frames_checked']=len(getattr(consumer,'frame_observations',[]))
        if result['status']=='REFUSED':
            if hasattr(consumer,'decode_observations') and not (io.output/'independent-decodes.json').exists():
                result['independent_decode_result']=io.publish('independent-decodes.json',consumer.decode_observations,MIB)
            if hasattr(consumer,'frame_observations') and not (io.output/'actual-frame-checks.json').exists():
                result['frame_checks']=io.publish('actual-frame-checks.json',consumer.frame_observations,2*MIB)
    if suite is not None:result['groups']=suite.output()
    if io is not None:
        result['array_filename_normalization']={'rule':'ASCII lowercase and underscore-to-hyphen','published_names':len(getattr(io,'array_names',{})),'unique':True,'numerical_values_changed':False}
        result['accounting']=io.account();raw=o.encoded(result);need(len(raw)<=128<<10,'recovery final/raw log cap')
        io.publish_raw('result.json',raw,128<<10);need(io.write_bytes+len(raw)<=io.limits['write_bytes'],'recovery stdout charged')
        io.write_bytes+=len(raw);need(sys.stdout.buffer.write(raw)==len(raw),'full recovery stdout');sys.stdout.buffer.flush();io.tick()
    else:
        raw=o.encoded(result);need(len(raw)<=8192,'bootstrap refusal cap');sys.stdout.buffer.write(raw);sys.stdout.buffer.flush()
    return 0 if result['status']=='PASS_CONDITIONAL_NATIVE_DIAGNOSTIC' else 1

if __name__=='__main__':raise SystemExit(main())
