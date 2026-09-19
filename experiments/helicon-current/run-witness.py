"""One bounded compatibility/trial witness on workspace copies of two RAWs."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys
import tifffile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('helicon_witness_process', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)

out = HERE / 'raw-witness-1'
out.mkdir()
copies = out / 'input'
copies.mkdir()
source = Path(r'D:\personal\macro\requests\misc-diagnostic\crystalized-vitamin-c-cpl')
originals = [source / name for name in ['DSC00128.ARW', 'DSC00129.ARW']]
before = [c.ref(p) for p in originals]
inputs = []
for p, r in zip(originals, before):
    dest = copies / p.name
    shutil.copyfile(p, dest)
    assert c.ref(dest)['sha256'] == r['sha256']
    inputs.append(dest)
manifest = out / 'inputs.txt'
manifest.write_text('\n'.join(str(p) for p in inputs) + '\n', encoding='utf-8')
exe = HERE / 'program/HeliconFocus.exe'
output = out / 'witness.tiff'
command = [str(exe), '-silent', '-noprogress', '-i', str(manifest),
           '-mp:1', '-rp:8', '-sp:4', '-sort:asc', '-tif:u',
           '-save:' + str(output), '-o', str(out / 'saved-outputs.txt')]
c.save(out / 'bindings.json', dict(executable=c.ref(exe), originals=before,
    inputs=[c.ref(p) for p in inputs], runner=c.ref(Path(__file__)),
    purpose='RAW compatibility and full-resolution trial witness; not a quality or timing comparison',
    codec_development_alignment_settings='application defaults, not yet independently established'))
try:
    c.job(command, {}, out, wall=180)
finally:
    after = [c.ref(p) for p in originals]
    c.save(out / 'originals-after.json', after)
    assert after == before
assert output.is_file(), 'No TIFF; inspect console and saved-output list'
with tifffile.TiffFile(output) as tif:
    pages = [dict(shape=list(p.shape), dtype=str(p.dtype),
        description=p.description,
        software=str(p.tags.get('Software').value) if 'Software' in p.tags else None)
        for p in tif.pages]
c.save(out / 'output.json', dict(file=c.ref(output), pages=pages,
    full_resolution_witness=pages[0]['shape'][0]*pages[0]['shape'][1] > 4_000_000,
    watermark_visual_check='pending', originals_unchanged=True))
print(json.dumps(pages))
