"""Build only bounded research controls against the frozen release13 core."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,sys,shutil
p=argparse.ArgumentParser();p.add_argument('arm',choices=['insect','chart','insect-wide','chart-wide','insect-wide-discrete','chart-wide-discrete','insect-wide-guarded','chart-wide-guarded','insect-boundary-guarded','chart-boundary-guarded','chart-global-guarded']);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[4];sources=Path(__file__).parent
reference=root/'outputs/multi-stack/completion/sr-chart-roi-build-02/build-receipt.json';bound=json.loads(reference.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
core=bound['libraries']['strehl_core'];lib=root/core['file'];assert sha(lib)==core['sha256']
source=sources/{'insect':'continuous-geometry-signal-controls.rs','chart':'continuous-chart-geometry-controls.rs','insect-wide':'continuous-wide-geometry-controls.rs','chart-wide':'continuous-wide-chart-controls.rs','insect-wide-discrete':'discrete-wide-geometry-controls.rs','chart-wide-discrete':'discrete-wide-chart-controls.rs','insect-wide-guarded':'guarded-wide-geometry-controls.rs','chart-wide-guarded':'guarded-wide-chart-controls.rs','insect-boundary-guarded':'guarded-boundary-insect-controls.rs','chart-boundary-guarded':'guarded-boundary-chart-controls.rs','chart-global-guarded':'guarded-global-chart-controls.rs'}[a.arm]
a.out.mkdir(parents=True,exist_ok=False);exe=a.out/'controls.exe'
files=[source,sources/'continuous-translation.rs',sources/('local-registration.rs' if a.arm.endswith('discrete') else 'local-registration-continuous.rs'),sources/'local-registration-tests.rs',sources/'local-lowpass-unit-tests.rs',sources/('measured-trajectory-01.rs' if a.arm.startswith('insect') else 'chart-measured-trajectory-01.rs')]
if a.arm.endswith('guarded'):
 files=[source,sources/('measured-trajectory-01.rs' if a.arm.startswith('insect') else 'chart-measured-trajectory-01.rs')]
 files += [root/'crates/strehl-core/src'/name for name in ['reconstruction-registration.rs','reconstruction-registration-tests.rs','reconstruction-registration-lowpass-tests.rs','reconstruction-registration-footprint.rs','reconstruction-registration-footprint-tests.rs']]
if a.arm == 'chart-global-guarded':
 files += [root/'crates/strehl-core/src/reconstruction-registration-global.rs', root/'crates/strehl-core/src/reconstruction-registration-graph.rs', root/'crates/strehl-core/src/reconstruction-registration-graph-tests.rs']
(a.out/'source').mkdir()
for f in files:shutil.copyfile(f,a.out/'source'/f.name)
command=['rustc','--edition=2024','--test','-C','opt-level=3','-C','lto=thin','-C','codegen-units=1',str(source),'-L',f'dependency={root/"target/release/deps"}','--extern',f'strehl_core={lib}','-o',str(exe)]
r={'schema':'strehl.sr-continuous-controls-build.v1','command':command,'driver_command':sys.argv,'started_unix':time.time(),'frozen_library_receipt_sha256':sha(reference),'library':{'path':str(lib),'sha256':sha(lib)},'compilation_scope': 'Fresh registration module and controls use frozen13 alignment/noise/plane support; the old reconstruction registration code inside linked rlib is not called' if a.arm.endswith('guarded') else 'Research registration and controls use frozen13 support library','sources':{str(f.relative_to(root)):sha(f) for f in files},'rustc':subprocess.check_output(['rustc','--version','--verbose'],text=True)}
with (a.out/'build.log').open('w') as log:c=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
r.update(exit_code=c.returncode,finished_unix=time.time(),executable_sha256=sha(exe) if c.returncode==0 else None)
(a.out/'build-receipt.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'out':str(a.out),'exit_code':c.returncode,'executable_sha256':r['executable_sha256']}));sys.exit(c.returncode)
