"""Whole-image RGB16 TIFF to RGB8 PNG, with no crop, resampling or tone change."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import tifffile
from PIL import Image

def main():
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with tifffile.TiffFile(a.source) as tf:
        src = tf.asarray()
        assert src.dtype == np.uint16 and src.ndim == 3 and src.shape[2] == 3
        tag = tf.pages[0].tags.get(34675)
        icc = tag.value if tag else None
    pixels = ((src.astype(np.uint32) + 128) // 257).astype(np.uint8)
    kw = {'icc_profile': icc} if icc else {}
    Image.fromarray(pixels).save(a.output, **kw)
    check = np.asarray(Image.open(a.output))
    assert check.shape == src.shape and np.array_equal(check, pixels)
    receipt = {'source': str(a.source.resolve()), 'output': str(a.output.resolve()),
               'shape': list(src.shape), 'conversion': 'rounded division by 257; full extent; no resampling',
               'source_sha256': hashlib.file_digest(a.source.open('rb'), 'sha256').hexdigest(),
               'png_sha256': hashlib.file_digest(a.output.open('rb'), 'sha256').hexdigest(),
               'icc_preserved': bool(icc)}
    a.output.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
