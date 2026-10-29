"""Seal completed root-run focus artifacts; never rewrite the census."""
from pathlib import Path
import argparse,hashlib,json,sys,zipfile
P=argparse.ArgumentParser();P.add_argument('census',type=Path);P.add_argument('receipt',type=Path);P.add_argument('snapshot',type=Path);P.add_argument('--out',type=Path,required=True);P.add_argument('--direct-build',type=Path);a=P.parse_args()
ROOT=Path(__file__).resolve().parents[4];base=a.census.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((base/'report.json').read_text());receipt=json.loads(a.receipt.read_text());build=json.loads((a.snapshot/'build.json').read_text())
assert r['schema']=='strehl.sr-focus-census.v1' and r['raw_decodes']==0
assert receipt['state']=='complete' and receipt['exit_code']==0 and receipt['command']==r['command']
assert sha(ROOT/r['command'][0])==receipt['executable_sha256']
paths=['experiments/multi-stack-2026-10-28/completion/sr/focus-census.rs','crates/strehl-core/src/focus.rs','crates/strehl-core/src/focus-evidence.rs','crates/strehl-core/src/through_focus.rs','crates/strehl-core/src/boxfilter.rs','crates/strehl-core/src/merge.rs','crates/strehl-core/src/noise.rs','crates/strehl-core/src/plane.rs','crates/strehl-core/src/optics.rs','crates/strehl-cli/src/session-sampling.rs','crates/strehl-cli/src/session-focus.rs']
producer={path:build['source_sha256'][path] for path in paths}
archive=a.snapshot/'implementation-source.zip'
with zipfile.ZipFile(archive) as frozen:
    for path,digest in producer.items():assert hashlib.sha256(frozen.read(path)).hexdigest()==digest,('producer/archive source mismatch',path)
exe_name=Path(r['command'][0]).name
direct_binding=None
if a.direct_build:
    direct=json.loads(a.direct_build.read_text())
    assert direct['exit_code']==0
    assert all(direct[k] for k in ('sources_unchanged_during_build','libraries_unchanged_during_build','fingerprint_unchanged_during_build'))
    assert direct['executable_sha256']==receipt['executable_sha256']
    assert direct['compile_environment']['STREHL_BUILD_ID']==r['build']
    assert direct['included_sources'][str(ROOT/paths[0])]==producer[paths[0]]
    assert sha(ROOT/direct['fingerprint'])==direct['fingerprint_sha256']
    for library in direct['libraries'].values():
        assert sha(ROOT/library['file'])==library['sha256']
    direct_binding={'receipt_sha256':sha(a.direct_build),'fingerprint_sha256':direct['fingerprint_sha256'],'libraries':direct['libraries'],'build_id':r['build'],'scope':'Research executable compiled from locally bound sources and the recorded frozen support libraries; listed focus-producing sources equal the support snapshot archive. The snapshot does not claim to contain this later research executable.'}
else:
    assert build['executables'][exe_name]==receipt['executable_sha256']==sha(a.snapshot/exe_name)
assert r['source_sha256']==producer[paths[0]]
files={str(path.relative_to(base)).replace('\\','/'):sha(path) for path in sorted(base.rglob('*')) if path.is_file()}
render=ROOT/r['input_render'];assert sha(render/'alignment.json')==r['alignment_sha256']
seal={'schema':'strehl.sr-focus-artifact-seal.v1','command':sys.argv,'census_report_sha256':sha(base/'report.json'),'run_receipt_sha256':sha(a.receipt),'binary_sha256':receipt['executable_sha256'],'snapshot_sha256':sha(a.snapshot/'build.json'),'source_archive_sha256':sha(archive),'producer_sources':producer,'alignment_sha256':r['alignment_sha256'],'calibration_sha256':sha(render/'calibration.json'),'source_identities_sha256':sha(render/'source-identities.json'),'files':files,'scope':'Exact completed research artifact; producer fingerprints verified against frozen implementation archive and compiled binary, without requiring current working files to remain unchanged; not a new RAW decode or production cache binding'}
if direct_binding:
    seal['direct_link_build']=direct_binding
a.out.parent.mkdir(parents=True,exist_ok=True)
with a.out.open('x') as f:json.dump(seal,f,indent=2);f.write('\n')
print(json.dumps({'seal':str(a.out),'sha256':sha(a.out),'files':len(files),'producer_sources':len(producer),'binary_sha256':seal['binary_sha256']}))
