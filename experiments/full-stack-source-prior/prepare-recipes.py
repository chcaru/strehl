"""Bind existing delivered products to original read-only inputs; no RAW decode."""
from pathlib import Path
import hashlib
import json
import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def prepare(name, folder, master, mode, crop, exposure, relocated=None):
    folder, master = ROOT/folder, ROOT/master
    order = json.loads((folder/'input-order.json').read_text())
    rows = []
    for row in order:
        old = Path(row.get('source', row.get('path')))
        original = old if relocated is None else Path(relocated)/old.name
        assert original.is_file() and original.stat().st_size == row['bytes']
        rows.append(dict(index=row['index'], path=str(original),
            identity_name=Path(row.get('staged', str(old))).name,
            bytes=row['bytes'], sha256=row['sha256']))
    assert [r['index'] for r in rows] == list(range(len(rows)))
    map_path = folder/'alignment.txt'
    header = dict(line.split(' ', 1) for line in map_path.read_text().splitlines()
                  if line.startswith(('stack-name ', 'reference ', 'frames ')))
    assert int(header['frames']) == len(rows)
    with tifffile.TiffFile(master) as tf:
        pixels = tf.asarray()
        assert len(tf.pages) == 1 and 34675 in tf.pages[0].tags
    assert pixels.dtype == np.uint16 and pixels.shape == (crop[3]*2, crop[2]*2, 3)
    recipe = dict(schema=1, mode=mode, stack_name=header['stack-name'], inputs=rows,
        warp_map=str(map_path), warp_map_sha256=sha(map_path),
        expected_reference=int(header['reference']), expected_full_geometry=[3516,2344],
        expected_crop=crop, expected_baseline=str(master), expected_baseline_sha256=sha(master),
        expected_baseline_pixels_sha256=hashlib.sha256(pixels.astype('<u2',copy=False).tobytes()).hexdigest(),
        expected_camera='ILCE-7CM2', expected_iso=100.0, exposure_stops=exposure,
        tone_policy='automatic-per-arm-current-writer')
    out = HERE/'recipes'/f'{name}.json'
    out.parent.mkdir(exist_ok=True)
    with out.open('x', encoding='utf-8') as f:
        json.dump(recipe, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(recipe=str(out), sources=len(rows), mode=mode,
                         pixels_sha256=recipe['expected_baseline_pixels_sha256'])))

if __name__ == '__main__':
    prepare('marigold-4', 'outputs/flower-marigold-cpl/stack-4',
        'outputs/flower-marigold-cpl/final/marigold-stack-4-master.tiff',
        'prior', [191,128,3134,2088], -.5)
    prepare('ore-100', 'outputs/peacock-ore/100msdcf',
        'outputs/peacock-ore/final/peacock-ore-100msdcf-master.tiff',
        'prior', [83,55,3351,2234], 0.0)
    prepare('garnet-104', 'outputs/minerals-september24/104msdcf',
        'outputs/minerals-september24/final/etched-spessartine-garnet-104msdcf-master.tiff',
        'current', [127,85,3262,2174], 0.0,
        'D:/personal/macro/minerals/etched-spessartine-garnet/104MSDCF')
