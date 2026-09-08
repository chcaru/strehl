"""Root independent actual metadata release read; no image or subject imports."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
seen={}
def check(value, sha=None, size=None):
    p=Path(value)
    p=(p if p.is_absolute() else ROOT/p).resolve()
    assert p.is_relative_to(ROOT) and p.suffix.lower() not in ('.arw','.raw','.tif','.tiff','.npy')
    before=p.stat();assert before.st_size<=64*1024*1024
    h=hashlib.sha256()
    with p.open('rb') as stream:
        while b:=stream.read(1024*1024):h.update(b)
    after=p.stat()
    assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
    got=dict(bytes=before.st_size,sha256=h.hexdigest())
    assert sha is None or sha==got['sha256']
    assert size is None or size==got['bytes']
    assert seen.setdefault(str(p),got)==got
    return p
cli=argparse.ArgumentParser()
cli.add_argument('--release-sha256',required=True)
cli.add_argument('--preparation-sha256',required=True)
args=cli.parse_args()
release_path=check(HERE/'native-sensor-white-artifact-derivative-release-1.json',args.release_sha256)
prep_path=check(HERE/'work/native-sensor-white-artifact-release-1-preparation.json',args.preparation_sha256)
r=json.loads(release_path.read_bytes());p=json.loads(prep_path.read_bytes())
old_path=check(HERE/'native-sensor-white-derivative-release-1.json','70d44a9c43d9d8c194824b214b1287358a4f254e01ce6e1efc955d1f85af6611')
old=json.loads(old_path.read_bytes())
assert set(r)==set(old)
assert r['schema']==old['schema']=='m193c-sensor-white-native-derivative-release-v1'
assert r['scope']==old['scope']=='sensor-white-native-nine'
assert len(r['source_bindings'])==153
assert all(r['source_bindings'][k]==v for k,v in old['source_bindings'].items())
assert all(v in r['inputs'] for v in old['inputs'])
for name,ref in r['source_bindings'].items():check(name,ref['sha256'],ref['bytes'])
for ref in r['inputs']:check(ref['path'],ref['sha256'],ref['bytes'])
assert len({v['path'] for v in r['inputs']})==len(r['inputs'])
assert r['prior_work']==dict(cpu_seconds=50.46875,wall_seconds=45.1272058,file_bytes=244506315,metadata_bytes=7677264)
assert p['carry_before_reserve']==dict(cpu_seconds=50.46875,wall_seconds=45.1272058,file_bytes=243457739,metadata_bytes=6628688)
assert r['reuse_first']==old['reuse_first']==p['primary_reuse']['authority']
assert p['primary_reuse']['new_primary_invocation'] is False and p['primary_reuse']['snapshot_delete'] is False
assert p['previous_refusal']['parent_status']=='REFUSED'
assert p['previous_refusal']['reader_status']=='PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY'
assert p['previous_refusal']['reader_exit']==0 and p['previous_refusal']['parent_exit']==1
assert len(p['new_children'])==17
assert [v['original_index'] for v in p['new_children'] if v['role']=='new-primary']==[13,26,39,52,65,78,91,104]
assert [v['original_index'] for v in p['new_children'] if v['role']=='new-independent-reader']==[0,13,26,39,52,65,78,91,104]
inventory=sum(v['bytes'] for v in p['metadata_files'])
assert len(p['administrative_files'])==3
for v in p['administrative_files']:
    current=v['current'];baseline=v['baseline']
    check(current['path'],current['sha256'],current['bytes'])
    assert current['path']==baseline['path']
    assert v['charged_growth_bytes']==max(0,current['bytes']-baseline['bytes'])
    assert current['path'] not in r['source_bindings'] and all(x['path']!=current['path'] for x in r['inputs'])
    inventory+=v['charged_growth_bytes']
assert inventory==p['observed_metadata_bytes']
total=inventory+prep_path.stat().st_size+p['release_upper_bytes']+p['future_root_metadata']['reserved_bytes']
assert total<p['reserved_bytes']==1048576
assert p['release_upper_bytes']==131072 and release_path.stat().st_size<=131072
assert p['future_root_metadata']['reserved_bytes']==196608
exe=r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe'
output=HERE/'native-sensor-white-artifact-derivative-1'
assert not output.exists()
assert r['commands']==[[exe,'-B','-X','faulthandler','-X','pycache_prefix='+str(output/'parent-cache'),str(HERE/'native-sensor-white-artifact-run.py'),'--release',str(release_path),'--release-sha256','ACTUAL_EXECUTION_RELEASE_SHA256','--output',str(output)]]
assert r['reader']['script']==old['reader']['script'] and r['reader']['runtime']==old['reader']['runtime']
assert len(r['reader']['commands'])==9
for i,cmd in enumerate(r['reader']['commands']):
    base=output/f'frame-{i:02d}'
    assert cmd==[exe,'-B','-X','faulthandler','-X','pycache_prefix='+str(base/'reader-cache'),str(HERE/'independent-sensor-white-derivative-read.py'),'--request',str(base/'read-request.json'),'--request-sha256','ACTUAL_FRAME_REQUEST_SHA256','--output',str(base/'independent')]
print(json.dumps(dict(status='PASS_METADATA_RELEASE_READ_ONLY',files=len(seen),sources=153,inputs=len(r['inputs']),planned_children=17,inventory_bytes=inventory,total_reserved_components=total,release_bytes=release_path.stat().st_size,preparation_bytes=prep_path.stat().st_size,image_payloads_opened=0)))
