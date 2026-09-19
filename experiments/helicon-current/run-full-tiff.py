"""Fixed commercial-product comparison on 70 existing prepared TIFFs."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import tifffile
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('helicon_full_process', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
p = argparse.ArgumentParser()
p.add_argument('method', choices=['b','c'])
a = p.parse_args()
out = HERE / ('vitamin-c-' + a.method + '-2')
out.mkdir()
source = ROOT / 'experiments/quality-september19/vitamin-c-comparator-2/developed'
inputs = sorted(source.glob('DSC*.tiff'))
assert [x.stem for x in inputs] == [f'DSC{i:05d}' for i in range(94,164)]
before = [c.ref(x) for x in inputs]
manifest = out / 'inputs.txt'
manifest.write_text('\n'.join(str(x) for x in inputs)+'\n', encoding='utf-8')
exe = HERE / 'program/HeliconFocus.exe'
output = out / 'whole-stack.tiff'
command = [str(exe), '-silent', '-noprogress', '-i', str(manifest),
    '-mp:' + {'b':'1','c':'2'}[a.method], *(['-rp:8'] if a.method=='b' else []), '-sp:4', '-sort:asc', '-tif:u',
    '-save:' + str(output), '-o', str(out / 'saved-outputs.txt')]
c.save(out / 'bindings.json', dict(executable=c.ref(exe), inputs=before,
    runner=c.ref(Path(__file__)),
    settings=dict(method=a.method,radius=8 if a.method=='b' else 'inactive',smoothing=4,order='ascending',other_settings='application defaults'),
    purpose='Full product output comparison on prepared TIFFs; not native RAW compatibility or matched colour/alignment/timing',
    visual_plan='Full output plus frozen five native detail/background regions; report defects and retained detail, no SOTA score'))
env, removed = c.b.clean_environment([])
c.save(out / 'invocation.json', dict(command=command,environment={},removed_environment=removed))
api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
try:
    result=c.b.run(command,env,ROOT,out/'process.log',api=api,wall_seconds=600,
        cpu_seconds=12000,log_bytes=16<<20,committed_bytes=40<<30)
    c.save(out/'process.json', result)
    print(json.dumps({k:result[k] for k in ('exit_code','error','wall_seconds')}),flush=True)
finally:
    after=[c.ref(x) for x in inputs]
    c.save(out/'inputs-after.json',after)
    assert after==before
assert result['exit_code']==0 and result['error'] is None
assert result['terminal_job_accounting'] and not result['cleanup_errors']
assert output.is_file()
with tifffile.TiffFile(output) as tif:
    pages=[dict(shape=list(x.shape),dtype=str(x.dtype),description=x.description) for x in tif.pages]
assert len(pages)==1 and pages[0]['dtype']=='uint16'
image=tifffile.imread(output)
assert image.ndim==3 and image.shape[2]==3 and image.shape[0]*image.shape[1]>4_000_000
preview=Image.fromarray((image//256).astype('uint8'))
preview.save(out/'whole-stack.png')
preview.thumbnail((1800,1800),Image.Resampling.LANCZOS)
preview.save(out/'whole-stack-preview.png')
c.save(out/'output.json',dict(file=c.ref(output),pages=pages,inputs_unchanged=True,
    preview=c.ref(out/'whole-stack-preview.png'),watermark_visual_check='pending'))
