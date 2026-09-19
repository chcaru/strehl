"""Check saved PNG pixels rather than a multi-image presentation of them."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
rectangles = {
    'run-1': [(160, 990, 460, 1030), (5, 430, 140, 710)],
    'views-2': [(260, 1230, 1850, 1290), (10, 220, 240, 430)],
}
results = []
for directory, boxes in rectangles.items():
    hashes = [[] for _ in boxes]
    for name in ['facet-glint', 'dark-glint', 'real-structure']:
        path = HERE / directory / (name + '.png')
        with Image.open(path) as image:
            rgb = np.asarray(image.convert('RGB'))
        regions = []
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            pixels = np.ascontiguousarray(rgb[y0:y1, x0:x1])
            dark = int(np.count_nonzero(np.min(pixels, axis=-1) < 128))
            digest = hashlib.sha256(pixels.tobytes()).hexdigest()
            assert dark > 0, 'saved label region is blank'
            hashes[i].append(digest)
            regions.append(dict(box=[x0,y0,x1,y1], dark_pixels=dark, sha256=digest))
        results.append(dict(path=str(path), file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            shape=list(rgb.shape), regions=regions))
    assert all(len(set(h)) == 1 for h in hashes), 'saved label regions differ between targets'
result = dict(status='VERIFIED', conclusion='Selected nonblank label regions are byte-identical across the three saved target PNGs in each version. Missing-label file-defect claim withdrawn; presentation cause not established.',
              script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), files=results)
with (HERE / 'label-pixels-1.json').open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(result['conclusion'])
