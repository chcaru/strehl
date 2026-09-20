"""Lossless native review views of the delivered whole-image PNGs; no image scores."""
from pathlib import Path
import hashlib
import json
from PIL import Image

HERE = Path(__file__).resolve().parent
FULL = HERE/'full-1'
OUT = HERE/'inspection-1'
REGIONS = [
    ('rail-crossing',1082,942,384,384),
    ('upper-colour',1020,180,512,512),
    ('central-stipple',2960,1290,512,512),
    ('lower-array',550,2780,512,512),
    ('lower-colour',4650,3000,512,512),
    ('surface-scratches',4840,1240,512,512),
    # Independent reviewer chose this from Current alone, before seeing Before.
    ('upper-left-contact-grid',32,320,512,512),
]
def binding(p):
    return {'path':str(p), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

assert json.loads((FULL/'completion.json').read_text())['phase'] == 'full'
OUT.mkdir(exist_ok=False)
with Image.open(FULL/'current-whole.png') as current, Image.open(FULL/'before-whole.png') as before:
    assert current.size == before.size == (6468,4300)
    assert current.mode == before.mode == 'RGB'
    icc = current.info.get('icc_profile')
    assert icc == before.info.get('icc_profile')
    metadata = {'icc_profile':icc} if icc else {}
    records = []
    for name,x,y,w,h in REGIONS:
        assert 0 <= x < x+w <= current.width and 0 <= y < y+h <= current.height
        rect = (x,y,x+w,y+h)
        a,b = current.crop(rect), before.crop(rect)
        pair = Image.new('RGB',(2*w,h))
        pair.paste(a,(0,0)); pair.paste(b,(w,0))
        destination = OUT/(name+'-current-left-before-right.png')
        pair.save(destination, **metadata)
        with Image.open(destination) as check:
            assert check.crop((0,0,w,h)).tobytes() == a.tobytes()
            assert check.crop((w,0,2*w,h)).tobytes() == b.tobytes()
            assert check.info.get('icc_profile') == icc
        records.append({'region':name, 'output_native_xywh':[x,y,w,h], 'view':binding(destination)})
    record = {'script':binding(Path(__file__)),
              'selection':binding(HERE/'photographic-inspection-plan.md'),
              'current_whole':binding(FULL/'current-whole.png'),
              'before_whole':binding(FULL/'before-whole.png'),
              'layout':'Current on left; Before on right. Native scale, no resampling or tone change.',
              'exact_display_slice_checks':True, 'regions':records}
with (OUT/'views.json').open('x',encoding='utf-8') as f:
    json.dump(record,f,indent=2); f.write('\n')
print(json.dumps({'native_views':len(records), 'output':str(OUT)}))
