"""Seal completed root-run focus artifacts; never rewrite the census."""
from pathlib import Path
import argparse,hashlib,json,sys
P=argparse.ArgumentParser();P.add_argument('census',type=Path);P.add_argument('receipt',type=Path);P.add_argument('snapshot',type=Path);P.add_argument('--out',type=Path,required=True);a=P.parse_args()
ROOT=Path(__file__).resolve().parents[4];base=a.census.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((base/'report.json').read_text());receipt=json.loads(a.receipt.read_text());build=json.loads((a.snapshot/'build.json').read_text())
assert r['schema']=='strehl.sr-focus-census.v1' and r['raw_decodes']==0
assert receipt['state']=='complete' and receipt['exit_code']==0 and receipt['command']==r['command']
assert sha(ROOT/r['command'][0])==receipt['executable_sha256']
paths=['experiments/multi-stack-2026-10-28/completion/sr/focus-census.rs','crates/strehl-core/src/focus.rs','crates/strehl-core/src/focus-evidence.rs','crates/strehl-core/src/through_focus.rs','crates/strehl-core/src/boxfilter.rs','crates/strehl-core/src/merge.rs','crates/strehl-core/src/noise.rs','crates/strehl-core/src/plane.rs','crates/strehl-core/src/optics.rs','crates/strehl-cli/src/session-sampling.rs','crates/strehl-cli/src/session-focus.rs']
producer={path:build['source_sha256'][path] for path in paths}
for path,digest in producer.items():assert sha(ROOT/path)==digest,('producer/current source mismatch',path)
assert r['source_sha256']==producer[paths[0]]
files={str(path.relative_to(base)).replace('\\','/'):sha(path) for path in sorted(base.rglob('*')) if path.is_file()}
render=ROOT/r['input_render'];assert sha(render/'alignment.json')==r['alignment_sha256']
seal={'schema':'strehl.sr-focus-artifact-seal.v1','command':sys.argv,'census_report_sha256':sha(base/'report.json'),'run_receipt_sha256':sha(a.receipt),'binary_sha256':receipt['executable_sha256'],'snapshot_sha256':sha(a.snapshot/'build.json'),'producer_sources':producer,'alignment_sha256':r['alignment_sha256'],'calibration_sha256':sha(render/'calibration.json'),'source_identities_sha256':sha(render/'source-identities.json'),'files':files,'scope':'Exact completed research artifact; current/source fingerprints checked at seal time; not a new RAW decode or production cache binding'}
a.out.parent.mkdir(parents=True,exist_ok=True)
with a.out.open('x') as f:json.dump(seal,f,indent=2);f.write('\n')
print(json.dumps({'seal':str(a.out),'sha256':sha(a.out),'files':len(files),'producer_sources':len(producer),'binary_sha256':seal['binary_sha256']}))
