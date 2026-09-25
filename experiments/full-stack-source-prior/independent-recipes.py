"""Independent recipe provenance check. No RAW decode or original-content hash reads."""
from pathlib import Path
import hashlib
import itertools
import json
import re
import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def digest(rows):
    h = 0xcbf29ce484222325
    for name, size in rows:
        for b in name.encode() + b'\0' + size.to_bytes(8, 'little') + b'\0':
            h = ((h ^ b) * 0x100000001b3) & ((1 << 64) - 1)
    return f'{h:016x}'

results = []
for name, output, crop, exposure, mode, n in [
    ('marigold-4', 'outputs/flower-marigold-cpl/stack-4', [191,128,3134,2088], -.5, 'prior', 488),
    ('ore-100', 'outputs/peacock-ore/100msdcf', [83,55,3351,2234], 0., 'prior', 207),
    ('garnet-104', 'outputs/minerals-september24/104msdcf', [127,85,3262,2174], 0., 'current', 183),
]:
    recipe_path = HERE/'recipes'/f'{name}.json'
    r = json.loads(recipe_path.read_text())
    original_order = json.loads((ROOT/output/'input-order.json').read_text())
    assert len(r['inputs']) == len(original_order) == n
    assert r['mode'] == mode and r['expected_crop'] == crop and r['exposure_stops'] == exposure
    assert r['tone_policy'] == 'automatic-per-arm-current-writer'
    paths, names = [], []
    for i, (item, old) in enumerate(zip(r['inputs'], original_order)):
        old_path = Path(old.get('source', old.get('path')))
        p = Path(item['path'])
        assert item['index'] == old['index'] == i
        assert item['identity_name'] == Path(old.get('staged', str(old_path))).name
        assert item['bytes'] == old['bytes'] and item['sha256'] == old['sha256']
        assert p.is_file() and p.stat().st_size == item['bytes']
        if name == 'garnet-104':
            receipt = next(x for x in json.loads((ROOT/'outputs/minerals-september24/final/folder-label-receipt.json').read_text()) if x['capture'] == '104MSDCF')
            assert Path(receipt['old_path']) == old_path.parent
            assert p.parent == Path(receipt['new_path']) and p.name == old_path.name
            assert receipt['all_sha256_unchanged'] and receipt['verified_raw_files'] == n
        else:
            assert p == old_path
        paths.append(str(p)); names.append(item['identity_name'])
    assert len(set(paths)) == len(set(names)) == n
    map_path = Path(r['warp_map'])
    assert map_path == ROOT/output/'alignment.txt' and sha(map_path) == r['warp_map_sha256']
    lines = map_path.read_text().splitlines()
    headers = dict(x.split(' ', 1) for x in lines if x.startswith(('stack-name ', 'stack-digest ', 'frames ', 'reference ', 'plane ')))
    entries = [x.split() for x in lines if re.match(r'^\d+ ', x)]
    assert [int(x[0]) for x in entries] == list(range(n)) and all(x[1] == 'placed' for x in entries)
    assert headers['stack-name'] == r['stack_name'] and int(headers['reference']) == r['expected_reference']
    assert int(headers['frames']) == n and headers['plane'] == '3516x2344'
    assert r['expected_full_geometry'] == [3516,2344]
    pairs = [(x['identity_name'], x['bytes']) for x in r['inputs']]
    assert digest(pairs) == headers['stack-digest']
    swapped = pairs.copy(); swapped[0], swapped[1] = swapped[1], swapped[0]
    assert digest(swapped) != headers['stack-digest']  # An order mistake can fail this check.
    raw_names_digest = digest([(Path(x['path']).name,x['bytes']) for x in r['inputs']])
    if name == 'marigold-4':
        assert raw_names_digest != headers['stack-digest']  # Staged names are essential here.
    master = Path(r['expected_baseline'])
    assert sha(master) == r['expected_baseline_sha256']
    with tifffile.TiffFile(master) as tf:
        pixels = tf.asarray()
        assert len(tf.pages) == 1 and tf.pages[0].tags[34675].value
    assert pixels.dtype == np.uint16 and pixels.shape == (2*crop[3],2*crop[2],3)
    pixel_sha = hashlib.sha256(pixels.astype('<u2',copy=False).tobytes()).hexdigest()
    assert pixel_sha == r['expected_baseline_pixels_sha256']
    runs = []
    for directory, group in itertools.groupby(paths, key=lambda x: str(Path(x).parent)):
        group = list(group)
        runs.append(dict(directory=directory, count=len(group), first=Path(group[0]).name, last=Path(group[-1]).name))
    results.append(dict(name=name, recipe_sha256=sha(recipe_path), frames=n, reference=r['expected_reference'],
        crop=crop, exposure=exposure, mode=mode, map_digest=headers['stack-digest'],
        source_runs=runs, baseline_sha256=r['expected_baseline_sha256'], pixels_sha256=pixel_sha,
        all_placed=True, source_order_matches_retained=True, swapped_order_rejected=True,
        original_content_rehashed=False))
report = dict(status='INDEPENDENT_RECIPE_CHECK_PASS', results=results)
(HERE/'independent-recipes.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
