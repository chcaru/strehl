"""Exact complete RGB16 neutrality, including the wrong-donor control."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent

def binding(path):
    with path.open('rb') as f:
        return dict(path=str(path), sha256=hashlib.file_digest(f, 'sha256').hexdigest())

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--off', type=Path, required=True)
    p.add_argument('--on', type=Path, required=True)
    a = p.parse_args()
    off, on = a.off.resolve(), a.on.resolve()
    assert off.is_relative_to(HERE) and on.is_relative_to(HERE) and off != on
    assert (on/'attribution/receipt.json').is_file()
    assert not (off/'attribution').exists()
    a_bind = json.loads((off/'bindings.json').read_text())
    b_bind = json.loads((on/'bindings.json').read_text())
    assert a_bind['sources'] == b_bind['sources']
    assert a_bind['executable'] == b_bind['executable']
    result = dict(scope='Observer neutrality only, including late-donor placebo; no quality claim', arms={})
    for arm in ('baseline', 'candidate', 'late'):
        paths = [run/'output'/f'{arm}.tiff' for run in (off, on, HERE/'full-1')]
        images = [tifffile.memmap(path, mode='r') for path in paths]
        assert all(im.shape == (4612,6920,3) and im.dtype == np.uint16 for im in images)
        h = hashlib.sha256()
        for y in range(0,4612,128):
            chunk = images[0][y:y+128]
            assert all(np.array_equal(chunk, im[y:y+128]) for im in images[1:]), (arm,y)
            h.update(chunk.astype('<u2', copy=False).tobytes())
        result['arms'][arm] = dict(pixel_sha256=h.hexdigest(), off_on_original_pixels_identical=True,
                                   files=[binding(path) for path in paths])
    result['observer'] = binding(on/'attribution/receipt.json')
    result['helper'] = binding(Path(__file__))
    with (on/'neutrality.json').open('x', encoding='utf-8') as f:
        json.dump(result,f,indent=2); f.write('\n')
    print(json.dumps(result))

if __name__ == '__main__': main()
