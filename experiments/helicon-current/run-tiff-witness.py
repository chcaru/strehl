"""Two already-developed, full-resolution TIFFs; bounded compatibility witness."""
from pathlib import Path
import importlib.util
import json
import sys
import tifffile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('helicon_tiff_process', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
out = HERE / 'tiff-witness-1'
out.mkdir()
source = ROOT / 'experiments/quality-september19/vitamin-c-comparator-2/developed'
inputs = [source / name for name in ['DSC00128.tiff', 'DSC00129.tiff']]
before = [c.ref(p) for p in inputs]
manifest = out / 'inputs.txt'
manifest.write_text('\n'.join(str(p) for p in inputs) + '\n', encoding='utf-8')
exe = HERE / 'program/HeliconFocus.exe'
output = out / 'witness.tiff'
command = [str(exe), '-silent', '-noprogress', '-i', str(manifest),
           '-mp:1', '-rp:8', '-sp:4', '-sort:asc', '-tif:u',
           '-save:' + str(output), '-o', str(out / 'saved-outputs.txt')]
c.save(out / 'bindings.json', dict(executable=c.ref(exe), inputs=before,
    runner=c.ref(Path(__file__)),
    purpose='Prepared TIFF compatibility and full-resolution trial witness; no RAW loader or quality claim',
    settings='method B, radius8, smoothing4, ascending; other settings application defaults'))
try:
    c.job(command, {}, out, wall=180)
finally:
    after = [c.ref(p) for p in inputs]
    c.save(out / 'inputs-after.json', after)
    assert after == before
assert output.is_file(), 'No TIFF; inspect vendor log and output list'
with tifffile.TiffFile(output) as tif:
    pages = [dict(shape=list(p.shape), dtype=str(p.dtype), description=p.description,
        software=str(p.tags['Software'].value) if 'Software' in p.tags else None) for p in tif.pages]
c.save(out / 'output.json', dict(file=c.ref(output), pages=pages,
    full_resolution_witness=pages[0]['shape'][0]*pages[0]['shape'][1] > 4_000_000,
    watermark_visual_check='pending', inputs_unchanged=True))
print(json.dumps(pages))
