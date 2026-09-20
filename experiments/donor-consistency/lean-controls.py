"""Quick diagnostic linking the already-bound core; final CLI build still required."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('donor_lean_common',ROOT/'experiments/full-context-placement/run.py')
c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
out=args.out.resolve();assert out.is_relative_to(HERE);out.mkdir()
build=HERE/'build-1'
prior=json.loads((build/'sources.json').read_text())
# Only reuse the core if its source and experiment bridge are still exactly bound.
for relative in ['crates/strehl-core/src/pyramid.rs','experiments/donor-consistency/core-bridge.rs']:
    path=(ROOT/relative).resolve();record=next(x for x in prior if Path(x['path'])==path)
    assert c.ref(path)==record
libs={}
for line in (build/'process.log').read_text().splitlines():
    try: row=json.loads(line)
    except ValueError: continue
    name=row.get('target',{}).get('name')
    if row.get('reason')=='compiler-artifact' and name in ['strehl_core','serde_json','sha2']:
        libs[name]=Path(next(x for x in row['filenames'] if x.endswith('.rlib')))
assert set(libs)=={'strehl_core','serde_json','sha2'}
source=(HERE/'implementation.rs').read_text()
def function(name):
    start=source.index('pub(crate) fn '+name+'(');left=source.index('{',start);depth=1;i=left+1
    while depth:
        depth+=(source[i]=='{')-(source[i]=='}');i+=1
    return source[start:i]
start=source.index('pub(crate) const SEGMENTS:');end=source.index('];',start)+2
text=source[start:end]+'\n'+function('capsule_at')+'\n'+function('fixed_masks')
control_path=(HERE/'independent-controls.rs').as_posix()
text+='\nmod independent_controls { include!(r"'+control_path+'"); }\n'
harness=out/'lean.rs';harness.write_text(text)
bindings=[c.ref(HERE/x) for x in ['core-bridge.rs','implementation.rs','independent-controls.rs','independent-plan.md','lean-controls.py']]
c.save(out/'bindings.json',dict(source=bindings,libs={k:c.ref(v) for k,v in libs.items()},harness=c.ref(harness),
    purpose='Same core and exact independent controls; generated geometry copied verbatim; debugging, not full CLI/source integration proof'))
command=['rustc','--edition=2021','--test','-O','-C','lto=thin',str(harness),'-L','dependency='+str(libs['strehl_core'].parent),'-o',str(out/'lean.exe')]
for name,path in libs.items():command+=['--extern',name+'='+str(path)]
compile_dir=out/'compile';compile_dir.mkdir();c.job(command,{'RAYON_NUM_THREADS':'2'},compile_dir,wall=120)
run=out/'controls';run.mkdir();c.job([str(out/'lean.exe'),'--nocapture','--test-threads=1'],{'RAYON_NUM_THREADS':'2'},run,wall=120)
assert all(c.ref(Path(x['path']))==x for x in bindings)
log=(run/'process.log').read_text();assert 'test result: ok. 2 passed;' in log
c.save(out/'completion.json',dict(passed=True,source_unchanged=True,executable=c.ref(out/'lean.exe')))
