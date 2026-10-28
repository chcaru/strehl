"""Current installed export capability; two retained TIFFs, no quality claim."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys
import tifffile

ROOT = Path(__file__).resolve().parents[3]
OLD = Path('C:/dev/blog/death-of-software/projects/strehl')
OUT = ROOT / 'outputs/raw-quality-2026-10-26' / (sys.argv[1] if len(sys.argv) > 1 else 'helicon-witness')
assert OUT.parent == ROOT / 'outputs/raw-quality-2026-10-26'
HELPER = ROOT / 'experiments/m193c-output-grid/bounded-process.py'
spec = importlib.util.spec_from_file_location('helicon_bounded', HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)

def save(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')

def ref(path):
    return dict(path=str(path), **b.binding(path))

assert not OUT.exists()
OUT.mkdir()
source = OLD / 'experiments/quality-september19/vitamin-c-comparator-2/developed'
inputs = [source / name for name in ('DSC00128.tiff', 'DSC00129.tiff')]
before = [ref(p) for p in inputs]
local = []
for p in inputs:
    target = OUT / p.name
    shutil.copyfile(p, target)
    assert b.binding(target) == b.binding(p)
    local.append(target)
manifest = OUT / 'inputs.txt'
manifest.write_text('\n'.join(str(p) for p in local) + '\n', encoding='utf-8')
exe = OLD / 'experiments/helicon-current/program/HeliconFocus.exe'
output = OUT / 'witness.tiff'
command = [str(exe), '-silent', '-noprogress', '-i', str(manifest),
           '-mp:1', '-rp:8', '-sp:4', '-sort:asc', '-tif:u',
           '-save:' + str(output), '-o', str(OUT / 'saved-outputs.txt')]
harness = ROOT / 'experiments/m12-scorecard/m12-harness.py'
save('bindings.json', dict(executable=ref(exe), inputs=before, runner=ref(Path(__file__)),
    helper=ref(HELPER), harness=ref(harness), command=command,
    purpose='Two prepared TIFF export capability only; not full workflow or photographic quality',
    healthy='Export file, saved-output receipt and clean process exit within 90 seconds; no entitlement change'))
env, removed = b.clean_environment()
result = b.run(command, env, OUT, OUT / 'process.log',
    api=b.load_job_api(b.binding(harness)), wall_seconds=90, cpu_seconds=900,
    log_bytes=4 << 20, committed_bytes=8 << 30)
save('process.json', result)
after = [ref(p) for p in inputs]
save('inputs-after.json', after)
assert before == after, 'retained inputs changed'
summary = dict(output_exists=output.is_file(), original_inputs_unchanged=True,
    removed_environment=removed, exit_code=result['exit_code'], error=result['error'])
if output.is_file() and result['error'] is None and result['exit_code'] == 0:
    with tifffile.TiffFile(output) as tif:
        summary['pages'] = [dict(shape=list(p.shape), dtype=str(p.dtype)) for p in tif.pages]
    summary['file'] = ref(output)
    summary['full_resolution_size_witness'] = summary['pages'][0]['shape'][0] * summary['pages'][0]['shape'][1] > 4_000_000
    summary['visual_watermark_check'] = 'pending'
save('result.json', summary)
print(json.dumps(summary, indent=2))
