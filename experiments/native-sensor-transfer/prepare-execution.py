"""Root metadata-only release constructor: controls, native, verify, once each.
Uses held build-source-freeze-4 and fixed six-role stage receipts; imports no
candidate/producer/decoder. No original, ROI, trace, TIFF or executable payload
is read except this metadata process's Python executable. Build executable refs
come from authenticated completed build records and are rehashed by the runner
and reader. Each constructor: 30 CPU / 60 wall, 128 MiB reads / 24 MiB writes.
Current source map is frozen once and must remain identical across three stages.
"""
from pathlib import Path, PureWindowsPath
import argparse, hashlib, io, json, math, os, re, stat, sys, time, zipfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WORK=HERE/'work'
PY=Path(sys.executable).resolve()
START=time.monotonic()
MIB=1<<20
READ=WRITE=0
PUBLISHING=False
EXTRAS=('independent-read.py','independent-numerics.py','independent-decode.py',
        'independent-controls.py','independent-protocol.md','independent-checker-design.md',
        'protocol-choice-review.md','independent-reader-source-review.md',
        'independent-implementation-notes.md','source-choice-review.md',
        'prepare-execution.py','prepare-execution-source-review.md')
STAGES=('controls','native','verify')
PRIORS={'controls':('build-on','build-off'),
        'native':('build-on','build-off','controls'),
        'verify':('build-on','build-off','controls','native')}
BUNDLE_CAPS={'result':256<<10,'tail':8<<10,'outer':64<<10,
             'stdout':8<<10,'stderr':32<<10,'exit':1024}
ORIGINALS=tuple('D:/personal/macro/requests/10-paper-iso-var/DSC%05d.ARW'%i for i in range(235,240))+tuple(
    'D:/personal/macro/requests/6-11-extended-dark-frames/DSC%05d.ARW'%i for i in range(872,894))
BINDING_PIN={'bytes':7119,'sha256':'ab4017907d5ff243ca36883a9e5ff7335717c4f7da4678b01eacab98b3d98b4a'}
TEST='merge_cmd::native_sensor_transfer::fixed_native_sensor_transfer_pair'

def need(value,reason):
    if not value:raise ValueError(reason)

def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def strict(raw):
    def pairs(items):
        out={}
        for k,v in items:
            need(k not in out,'duplicate metadata key');out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))

def check():
    need(time.process_time()+(0 if PUBLISHING else 1)<=30 and
         time.monotonic()-START+(0 if PUBLISHING else 2)<=60,'metadata CPU/wall allocation')
    need(READ<=128*MIB and WRITE+(0 if PUBLISHING else MIB+4096)<=24*MIB,'metadata byte allocation')

def path(value):
    need(type(value) is str and 0<len(value)<=512 and value.isascii() and '\x00' not in value,'bounded ASCII path')
    if value.startswith('\\\\?\\'):
        value=value[4:];need(re.match(r'^[A-Za-z]:[\\/]',value),'local verbatim path')
    w=PureWindowsPath(value)
    need((w.is_absolute() and re.match(r'^[A-Za-z]:[\\/]',value)) or (not w.drive and not w.root and ':' not in value),
         'local absolute or plain relative path')
    need(not value.startswith(('\\\\','//')) and all(v not in ('.','..') for v in value.replace('\\','/').split('/')),
         'local path without dot traversal')
    need(not any(':' in part for part in w.parts[1:] if part not in ('\\','/')),'path alternate stream')
    p=Path(os.path.abspath(value if w.is_absolute() else ROOT/value))
    need(p.is_relative_to(ROOT) or p==PY,'metadata repository/current-Python scope')
    return p

def source_path(key):
    need(type(key) is str and not PureWindowsPath(key).is_absolute() and '\\' not in key,'relative source spelling')
    p=path(key);need(p.is_relative_to(ROOT) and p.suffix in ('.rs','.py','.toml','.lock','.txt','.md','.json'),'source-only member')
    return p

def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def pin_shape(value,empty=False,cap=4*MIB):
    need(type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int and
         (0 if empty else 1)<=value['bytes']<=cap and type(value['sha256']) is str and
         re.fullmatch('[0-9a-f]{64}',value['sha256']) is not None,'bounded typed pin')

def ref(p,raw):
    p=path(str(p));return {'path':p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),**pin(raw)}

def same(left,right,empty=False):
    for v in (left,right):
        need(type(v) is dict and set(v)=={'path','bytes','sha256'},'closed FileRef')
        pin_shape({k:v[k] for k in ('bytes','sha256')},empty,128*MIB)
    need(path(left['path'])==path(right['path']) and left['bytes']==right['bytes'] and left['sha256']==right['sha256'],
         'same actual role/path/bytes/hash')

def read(p,cap=4*MIB,empty=False):
    global READ
    check();p=path(str(p))
    for q in (p,*p.parents):
        s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'plain metadata ancestry')
    before=p.stat();need(stat.S_ISREG(before.st_mode) and (0 if empty else 1)<=before.st_size<=cap,'metadata extent/type')
    need(READ+before.st_size+1<=128*MIB,'prospective metadata read');READ+=before.st_size+1
    shared=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,'st_file_attributes',0))
    full=lambda s:shared(s)+(s.st_ctime_ns,)
    with p.open('rb') as f:
        opened=os.fstat(f.fileno());raw=f.read(before.st_size+1);after=os.fstat(f.fileno())
    final=p.stat()
    need(full(before)==full(final) and full(opened)==full(after) and shared(before)==shared(opened)
         and shared(final)==shared(after) and len(raw)==before.st_size,'stable path and handle source bytes')
    check();return raw

def bound_read(value,cap=4*MIB,empty=False):
    need(type(value) is dict and set(value)=={'path','bytes','sha256'},'closed read FileRef')
    pin_shape({k:value[k] for k in ('bytes','sha256')},empty,cap)
    raw=read(value['path'],cap,empty);same(ref(value['path'],raw),value,empty);return raw

def publish_raw(p,raw,cap=MIB):
    global WRITE
    check();p=path(str(p));need(type(raw) is bytes and len(raw)<=cap and not p.exists(),'bounded fresh metadata publication')
    need(WRITE+len(raw)<=24*MIB,'prospective metadata write');WRITE+=len(raw)
    with p.open('xb') as f:
        need(f.write(raw)==len(raw),'full metadata write');f.flush();os.fsync(f.fileno())
    need(read(p,cap)==raw,'actual metadata readback');return ref(p,raw)

def publish(p,value):return publish_raw(p,encoded(value))

def map_shape(value):
    need(type(value) is dict and 1<=len(value)<=512,'bounded source map')
    paths=set()
    for k,v in value.items():
        p=source_path(k);need(p not in paths,'unique source path');paths.add(p);pin_shape(v)
    need(sum(v['bytes'] for v in value.values())<=16*MIB,'source byte aggregate')

def archive_check(value,mapping):
    global READ
    raw=bound_read(value,17*MIB)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(len(z.namelist())==len(mapping) and set(z.namelist())==set(mapping),'exact unique source archive membership')
        for k,v in mapping.items():
            item=z.getinfo(k);need(item.file_size==v['bytes'] and item.compress_type==zipfile.ZIP_STORED,'stored exact source member')
            check();need(READ+v['bytes']<=128*MIB,'prospective archived source read');READ+=v['bytes']
            need(pin(z.read(k))==v,'archived source bytes');check()

def sources(stage):
    base_raw=read(WORK/'build-source-freeze-4.json',MIB);base= strict(base_raw)
    need(set(base)=={'schema','source_bindings','archive'} and base['schema']=='native-sensor-transfer-build-source-freeze-v1','held build freeze schema')
    original=base['source_bindings'];map_shape(original);archive_check(base['archive'],original)
    current=dict(original);buffers={}
    for k,v in original.items():
        raw=read(source_path(k));need(pin(raw)==v,'unchanged compiled/build source');buffers[k]=raw
    for name in EXTRAS:
        k=(HERE/name).relative_to(ROOT).as_posix();need(k not in current,'closed additive reader source population')
        raw=read(HERE/name);current[k]=pin(raw);buffers[k]=raw
    current=dict(sorted(current.items()));map_shape(current)
    freeze=WORK/'execution-source-freeze-1.json'
    if stage=='controls':
        archive=WORK/'execution-source-1.zip';need(not freeze.exists() and not archive.exists(),'fresh execution source freeze')
        # At most16 MiB content plus bounded names/ZIP metadata; no code runs.
        need(sum(v['bytes'] for v in current.values())+sum(2*len(k.encode())+128 for k in current)+1024<=17*MIB,'stored archive layout')
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as z:
            for k in current:z.writestr(k,buffers[k])
        ar=publish_raw(archive,stream.getvalue(),17*MIB);archive_check(ar,current)
        frozen=publish(freeze,{'schema':'native-sensor-transfer-execution-source-freeze-v1',
            'build_source_freeze':ref(WORK/'build-source-freeze-4.json',base_raw),'source_bindings':current,'archive':ar})
    else:
        raw=read(freeze,MIB);held=strict(raw)
        need(set(held)=={'schema','build_source_freeze','source_bindings','archive'} and
             held['schema']=='native-sensor-transfer-execution-source-freeze-v1' and held['source_bindings']==current,
             'unchanged controls/native/verify source map')
        same(held['build_source_freeze'],ref(WORK/'build-source-freeze-4.json',base_raw));archive_check(held['archive'],current)
        frozen=ref(freeze,raw)
    return original,current,buffers,frozen

def bundle(stage,current,original):
    attempt=4 if stage=='build-on' else 1
    output=HERE/f'{stage}-{attempt}';stem=WORK/f'{stage}-external-{attempt}-'
    paths={'result':output/'result.json','tail':output/'parent-tail.json',
           'outer':Path(str(stem)+'outer.json'),'stdout':Path(str(stem)+'stdout.bin'),
           'stderr':Path(str(stem)+'stderr.bin'),'exit':Path(str(stem)+'exit.txt')}
    raw={k:read(p,BUNDLE_CAPS[k],empty=k=='stderr') for k,p in paths.items()}
    refs={k:ref(paths[k],v) for k,v in raw.items()}
    result,tail,outer,advert=(strict(raw[k]) for k in ('result','tail','outer','stdout'))
    need(result['schema']=='native-sensor-transfer-owned-stage-v1' and result['stage']==stage and
         result['status']=='COMPLETE_STAGE_UNVERIFIED' and result['error'] is None and not result['finalization_errors'],
         'actual completed prerequisite stage')
    need(outer['schema']=='native-sensor-transfer-stage-external-v1' and type(outer['exit_code']) is int and
         outer['exit_code']==0 and outer['timeout_terminated'] is False and raw['exit'].strip()==b'0','actual prior exit/no intervention')
    for k in ('stdout','stderr','exit'):same(outer[k],refs[k],empty=k=='stderr')
    need(outer['stdout_bytes']==len(raw['stdout']) and outer['stderr_bytes']==len(raw['stderr']) and
         outer['command']==result['invocation'],'prior actual streams/command')
    need(set(advert)=={'status','result','tail'} and advert['status']==result['status'] and encoded(advert)==raw['stdout'],'exact prior advertisement')
    same(advert['result'],refs['result']);same(advert['tail'],refs['tail']);same(tail['result'],refs['result'])
    need(tail['schema']=='native-sensor-transfer-parent-tail-v1' and tail['cpu_accounting_complete'] is True and
         tail['live_child_cpu_seconds']==0 and tail['final_external_allowance']=={'cpu_seconds':2,'wall_seconds':3},'prior terminal accounting')
    historical=strict(bound_read(result['release'],MIB))
    need(historical['schema']=='native-sensor-transfer-stage-release-v1' and historical['stage']==stage and
         historical['source_bindings']==(original if stage.startswith('build-') else current),'prerequisite source map')
    expected=[result['release']['sha256'] if v=='ACTUAL_RELEASE_SHA256' else v for v in historical['command']]
    need(expected==result['invocation'],'historical release actual command')
    key=(HERE/'run-stage.py').relative_to(ROOT).as_posix();same(outer['source'],{'path':key,**historical['source_bindings'][key]})
    return refs,result

def pricing(mode,current,binaries):
    # Request ceilings mirror held independent-read.py. No result/array function
    # is executed. Actual refs are narrower; a failed attempt is never refunded.
    parts={'sources_twice':2*sum(v['bytes'] for v in current.values()),
           'copied_executables_once':sum(v['bytes'] for v in binaries.values()),
           'reader_release_entry_and_exit':2*MIB,
           'two_build_bundles_releases_runners_children_logs':2*(sum(BUNDLE_CAPS.values())+MIB+(128<<10)+(32<<10)+16*MIB),
           'bounded_read_plus_one_and_metadata_margin':MIB}
    if mode=='verify':
        parts.update(original_snapshots_once=926855168,
            controls_native_bundles_releases_runners=2*(sum(BUNDLE_CAPS.values())+MIB+(128<<10)),
            ten_terminal_children_and_logs=10*((32<<10)+MIB),
            saved_control_result_and_release=(128<<10)+MIB,
            nine_traversal_json=9*(64<<10),hundred_frame_json=100*(64<<10),
            original_roi_replays=(27+100)*131072,
            prepared_roi_on_and_placebo=72*131072,
            traces_on_and_placebo=72*2*MIB,
            eighteen_collapsed_and_tiff=18*(262144+512*1024))
    total=sum(parts.values());ceiling=((total+MIB-1)//MIB)*MIB
    need(ceiling<=2*1024*MIB,'prospective reader maximum two GiB')
    return {'components':parts,'sum_bytes':total,'read_bytes':ceiling,
        'scope':'Fixed successful-path read-request ceiling, including one-byte probes/margin; no implicit library/DLL reads or source snapshot claim.'}

def main():
    global WRITE,PUBLISHING
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=STAGES);args=parser.parse_args();stage=args.stage
    need(os.name=='nt' and Path.cwd().resolve()==ROOT and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
         'fixed isolated Windows metadata constructor')
    need(path(sys.orig_argv[4])==HERE/'prepare-execution.py' and sys.orig_argv[:4]==[str(PY),'-I','-S','-B'] and
         sys.orig_argv[5:]==[stage],'exact metadata constructor invocation')
    need(WORK.is_dir(),'existing work directory')
    release_path=WORK/f'{stage}-release-1.json';reader_path=WORK/f'{stage}-reader-release-1.json'
    receipt_path=WORK/f'{stage}-execution-preparation-1.json'
    need(not release_path.exists() and not receipt_path.exists() and not (HERE/f'{stage}-1').exists(),'fresh fixed stage release/output')
    if stage!='native':need(not reader_path.exists(),'fresh fixed reader release')
    if stage=='native':need(all(not (HERE/f'native-run-{i}').exists() for i in range(9)),'fresh nine native outputs')
    original,current,buffers,freeze=sources(stage)
    binding=read(HERE/'input-bindings-1.json',16<<10);need(pin(binding)==BINDING_PIN,'held 27 original metadata identities')
    originals=strict(binding)['originals']
    need(len(originals)==27 and [v['path'].replace('\\','/') for v in originals]==list(ORIGINALS) and
         sum(v['bytes'] for v in originals)==926855168,'fixed original order/encoded extent')
    prior={};results={}
    for name in PRIORS[stage]:prior[name],results[name]=bundle(name,current,original)
    closure=results['build-on']['compiled_source_closure']
    need(all(v['compiled_source_closure']==closure for v in results.values()),'same actual compiled closure in all prerequisites')
    binaries={}
    for role,name,attempt in (('feature_on','build-on',4),('feature_off','build-off',1)):
        value=results[name]['artifacts']['executable']
        need(type(value) is dict and set(value)=={'path','bytes','sha256'} and path(value['path'])==HERE/f'{name}-{attempt}'/'cli-tests.exe','fixed copied binary role')
        pin_shape({k:value[k] for k in ('bytes','sha256')},cap=64*MIB);binaries[role]=value
    inputs=[ref(PY,read(PY,MIB))]
    reader=None;prices=None
    if stage in ('controls','verify'):
        prices=pricing(stage,current,binaries)
        limits={'cpu_seconds':100 if stage=='controls' else 1000,'wall_seconds':150 if stage=='controls' else 850,
                'memory_bytes':1024*MIB,'read_bytes':prices['read_bytes'],'write_bytes':(62 if stage=='controls' else 64)*MIB}
        command=[str(PY),'-I','-S','-B',str(HERE/'independent-read.py'),'--mode',stage,'--release',str(reader_path),
                 '--release-sha256','ACTUAL_RELEASE_SHA256']
        reader=publish(reader_path,{'schema':'native-sensor-transfer-reader-release-v1','mode':stage,'source_bindings':current,
            'originals':originals,'builds':{'feature_on':prior['build-on'],'feature_off':prior['build-off']},
            'native':prior['native'] if stage=='verify' else None,'controls':prior['controls'] if stage=='verify' else None,
            'output':str(HERE/f'{stage}-1'/'check'),'limits':limits,'command':command})
        commands=[[reader['sha256'] if v=='ACTUAL_RELEASE_SHA256' else v for v in command]]
    else:
        commands=[[str(HERE/('build-on-4' if i<7 else 'build-off-1')/'cli-tests.exe'),'--ignored','--exact',TEST,
                   '--nocapture','--test-threads=1'] for i in range(9)]
    command=[str(PY),'-I','-S','-B',str(HERE/'run-stage.py'),'--release',str(release_path),'--release-sha256','ACTUAL_RELEASE_SHA256']
    value={'schema':'native-sensor-transfer-stage-release-v1','stage':stage,'source_bindings':current,'inputs':inputs,
           'originals':originals,'command':command,'children':[{'command':v,'expected_exit_code':0} for v in commands],
           'binaries':binaries,'reader_release':reader,'prerequisites':prior}
    for k,v in current.items():need(pin(read(source_path(k)))==v,'source held through release preparation')
    released=publish(release_path,value)
    check();PUBLISHING=True
    record={'schema':'native-sensor-transfer-execution-preparation-v1','stage':stage,'release':released,'reader_release':reader,
            'source_freeze':freeze,'source_files':len(current),'source_bytes':sum(v['bytes'] for v in current.values()),
            'read_pricing':prices,'compiled_source_closure':closure,'invocation':sys.orig_argv,
            'cpu_sample_seconds':time.process_time(),'wall_sample_seconds':time.monotonic()-START,
            'read_bytes_sample':READ,'write_bytes_sample':WRITE,
            'allocation':{'cpu_seconds':30,'wall_seconds':60,'read_bytes':128*MIB,'write_bytes':24*MIB,
                          'publication_reserve_cpu_seconds':1,'publication_reserve_wall_seconds':2},
            'scope':'Metadata/source/Python hashing only. Original payloads, copied test executable payloads, images, controls and candidates not read or run. Samples precede publication; root owns actual external interval/exit.'}
    receipt=publish(receipt_path,record)
    advert=encoded({'release':released,'preparation':receipt,'source_files':len(current)})
    need(len(advert)<=4096 and WRITE+len(advert)<=24*MIB,'bounded metadata stdout');WRITE+=len(advert)
    need(sys.stdout.buffer.write(advert)==len(advert),'complete metadata stdout');sys.stdout.buffer.flush();check()

if __name__=='__main__':main()
