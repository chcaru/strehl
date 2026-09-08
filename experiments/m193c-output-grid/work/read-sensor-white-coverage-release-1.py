"""Root independent coverage release audit; metadata hashes plus nine TIFF stats only."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
H=ROOT/'experiments/m193c-output-grid'
seen={}
def check(value,sha=None,size=None):
 p=Path(value);p=(p if p.is_absolute() else ROOT/p).resolve()
 assert p.is_relative_to(ROOT) or p==Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
 assert p.suffix.lower() not in ('.arw','.raw','.dng','.tif','.tiff','.npy','.npz')
 a=p.stat();assert 0<a.st_size<=64*1024*1024
 h=hashlib.sha256()
 with p.open('rb') as s:
  while b:=s.read(1024*1024):h.update(b)
 z=p.stat();assert (a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_ino,z.st_size,z.st_mtime_ns)
 got=dict(bytes=a.st_size,sha256=h.hexdigest())
 assert sha is None or got['sha256']==sha
 assert size is None or got['bytes']==size
 assert seen.setdefault(str(p),got)==got
 return p
cli=argparse.ArgumentParser()
cli.add_argument('--release-sha256',required=True)
cli.add_argument('--preparation-sha256',required=True)
args=cli.parse_args()
rp=check(H/'sensor-white-coverage-release-1.json',args.release_sha256)
dp=check(H/'work/sensor-white-coverage-release-1-preparation.json',args.preparation_sha256)
r=json.loads(rp.read_bytes());d=json.loads(dp.read_bytes())
old=json.loads(check(H/'native-sensor-white-artifact-derivative-release-1.json','ad8b391f54d3fd10843a75e4515a8344b5e2b903145d5f256c0248f7758e95ec').read_bytes())
native=json.loads(check(H/'native-sensor-white-artifact-derivative-1/result.json','2cdf0f949100a8a0400579dcf5689dbc671d15362f51b3e8ebf363a972b079c4').read_bytes())
assert set(r)==set('schema scope source_bindings inputs commands python_executable native prior_work'.split())
assert r['schema']=='m193c-sensor-white-coverage-release-v1' and r['scope']=='sensor-white-native-nine-coverage'
assert all(r['source_bindings'][k]==v for k,v in old['source_bindings'].items())
assert all(v in r['inputs'] for v in old['inputs'])
assert len({v['path'] for v in r['inputs']})==len(r['inputs'])
assert native['status']=='COMPLETE_NINE_SENSOR_WHITE_DERIVATIVES_AWAITING_COVERAGE' and native['unvisited']==[]
tiffs={Path(x['tiff']['path']).resolve():x['tiff'] for x in native['rows']};assert len(tiffs)==9
image_inputs=[]
for name,ref in r['source_bindings'].items():check(name,ref['sha256'],ref['bytes'])
for ref in r['inputs']:
 p=Path(ref['path']);p=(p if p.is_absolute() else ROOT/p).resolve()
 if p.suffix.lower()=='.tiff':
  assert p in tiffs and all(ref[k]==tiffs[p][k] for k in ('sha256','bytes'))
  st=p.stat();assert st.st_size==ref['bytes'] and st.st_nlink==1
  image_inputs.append(p)
 else:check(p,ref['sha256'],ref['bytes'])
assert set(image_inputs)==set(tiffs) and len(image_inputs)==9
prior=json.loads(check(r['prior_work']['path'],r['prior_work']['sha256'],r['prior_work']['bytes']).read_bytes())
assert prior==dict(cpu_seconds=294.453125,wall_seconds=287.4812478,file_bytes=2155324564,metadata_bytes=18870081)==d['carry']
assert d['preparation_reserved_not_measured']==dict(cpu_seconds=30,wall_seconds=60,file_bytes=2097152,metadata_bytes=2097152)
snapshot=sum(v['bytes'] for v in tiffs.values())+5*1024*1024
assert snapshot==d['snapshot_reservation_bytes']==1785427283
assert prior['file_bytes']+snapshot==3940751847<4294967296
assert len(d['admitted_rows'])==9 and d['source_count']==len(r['source_bindings'])
audit=json.loads(check(d['audit']['path'],d['audit']['sha256'],d['audit']['bytes']).read_bytes())
assert audit['status']=='PASS_SAVED_SENSOR_WHITE_ARTIFACT_OUTCOME_AUDIT' and audit['subject_complete'] is True
assert len(audit['frames'])==9 and audit['fresh_primary_jobs']==8 and audit['fresh_reader_jobs']==9
assert audit['source_count']==153 and audit['input_count']==145
assert r['commands']==d['commands']
output=H/'sensor-white-coverage-1';assert not output.exists()
exe=r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe'
base=[exe,'-B','-X','faulthandler','-X']
script=str(H/'coverage-sensor-white-run.py')
assert r['commands']['parent']==base+['pycache_prefix='+str(output/'parent-cache'),script,'--release',str(rp),'--sha256','ACTUAL_EXECUTION_RELEASE_SHA256','--output',str(output)]
assert r['commands']['worker']==base+['pycache_prefix='+str(output/'worker-cache'),script,'--release',str(rp),'--sha256','ACTUAL_EXECUTION_RELEASE_SHA256','--output',str(output/'worker'),'--worker','--request',str(output/'request.json'),'--request-sha256','ACTUAL_COVERAGE_REQUEST_SHA256']
assert rp.stat().st_size<=262144 and dp.stat().st_size<=262144
print(json.dumps(dict(status='PASS_COVERAGE_RELEASE_METADATA_ONLY',hashed_files=len(seen),source_count=len(r['source_bindings']),input_count=len(r['inputs']),tiff_stats_only=9,image_payloads_opened=0,snapshot_reservation_bytes=snapshot,remaining_file_bytes_before_worker=4294967296-prior['file_bytes']-snapshot,release_bytes=rp.stat().st_size,preparation_bytes=dp.stat().st_size)))
