"""Exact metadata-only diagnosis of the frozen prefix auditor request conjunction."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];H=ROOT/'experiments/m193c-output-grid'
def rawref(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(name):
 p=H/name;return rawref(p),json.loads(p.read_bytes())
def canon(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def witness(x):
 b=canon(x);return dict(type=type(x).__name__,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def resolved(ref):return str((ROOT/ref['path']).resolve())
def same(a,b):return resolved(a)==resolved(b) and all(a[k]==b[k] for k in ('bytes','sha256'))
rr,r=read('sift-lightglue-commission-1/request.json');wr,w=read('sift-lightglue-commission-1/worker/result.json');pr,p=read('sift-lightglue-commission-plan-1.json')
qr,q=read('real-precise-1/request.json');vr,v=read('real-precise-1/worker/result.json');ar,a=read('work/independent-lightglue-acquisition-audit.json');cr,c=read('precise-upscale-canonical-1/worker/precise-true-arm.json')
assets={x['asset']['id']:x['payload'] for x in a['assets']['rows']}
clauses=[]
def add(name,left,right,rule='exact Python equality',ok=None):
 clauses.append(dict(name=name,rule=rule,passed=(left==right if ok is None else ok),left=witness(left),right=witness(right)))
add('request-path',resolved(w['request']),str(H/'sift-lightglue-commission-1/request.json'))
add('closed-request-keys',sorted(r),sorted('schema plan rows private_ref real_refs assets prior_work'.split()))
add('request-schema',r['schema'],'m193c-sift-lightglue-commission-request-v1')
add('plan-identity',r['plan'],pr,'resolved path + SHA256 + extent',same(r['plan'],pr))
add('whole-nine-rows',r['rows'],q['rows'])
add('whole-nine-real-feature-refs',r['real_refs'],v['features'])
add('private-feature-identity',r['private_ref'],c['feature_record'],'resolved path + SHA256 + extent',same(r['private_ref'],c['feature_record']))
add('whole-asset-ref-mapping',r['assets'],assets)
per=[]
for name in sorted(assets):
 left,right=r['assets'][name],assets[name]
 per.append(dict(id=name,left=left,right=right,path_spelling_equal=left['path']==right['path'],resolved_path_equal=resolved(left)==resolved(right),resolved_path=resolved(left),sha256_equal=left['sha256']==right['sha256'],extent_equal=left['bytes']==right['bytes'],identity_equal=same(left,right),left_canonical=witness(left),right_canonical=witness(right)))
assert [x['name'] for x in clauses if not x['passed']]==['whole-asset-ref-mapping']
assert all(not x['path_spelling_equal'] and x['identity_equal'] for x in per)
result=dict(schema='m193c-prefix-request-metadata-diagnosis-v1',status='VERIFIED_PATH_SPELLING_ONLY_CONJUNCTION_FAILURE',sources=dict(request=rr,worker=wr,plan=pr,real_request=qr,real_worker=vr,acquisition_audit=ar,private_arm=cr),conjuncts=clauses,asset_reference_pairs=per,source=rawref(Path(__file__)),scope='Metadata only. The eight actual request-association operands are reconstructed from retained source-declared baselines without importing auditor or subject. Only exact asset-dictionary equality fails; all five paths resolve identically with identical byte extents and SHA256. No payload reread, numerical normalization/truth check, model or registrar. Canonical witnesses identify complete operands in the retained source FileRefs.')
output=H/'work/independent-sift-lightglue-request-diagnosis.json';assert not output.exists();b=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode();assert len(b)<=12*1024
with output.open('xb') as stream:assert stream.write(b)==len(b)
print(json.dumps(dict(result=rawref(output),failed_conjuncts=[x['name'] for x in clauses if not x['passed']],all_five_asset_identities_equal=True)))
