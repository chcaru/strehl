"""Three frozen manual anatomical counterparts; no registration or quality score."""
from pathlib import Path
import hashlib
import json
import struct
import zlib

import cv2
import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARMS = {
    'current': (ROOT/'experiments/garnet-spatial-trace/marigold4-fixed-1/output/candidate.tiff',
                '19e657e419d52adf567ec86472f917ad9b9abfc9b0812131e9bba0eacbae462f', [6268, 4176]),
    'b': (HERE.parent/'run-2/helicon-b/whole-stack.tiff',
          '30740f1c0c9cd9c5d24112121117b76da8444da0951ba26408dd5f365385cee5', [7032, 4688]),
}
CHOICES = [
    {'name': 'fan', 'current': [3230, 3000, 384, 384], 'b': [3690, 3400, 384, 384],
     'landmark': 'Hanging petal tip and rear hair fan; Current is the existing frozen fan core.'},
    {'name': 'rounded-petal', 'current': [1436, 1844, 384, 384], 'b': [1566, 2113, 384, 384],
     'landmark': 'Rounded bright petal with the orange speck cluster.'},
    {'name': 'upper-cup', 'current': [1448, 273, 384, 384], 'b': [1644, 339, 384, 384],
     'landmark': 'Upper-left folded cup and its diagonal interior.'},
]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def ref(path):
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def save_png(path, pixels, icc):
    def chunk(tag, data):
        return struct.pack('>I', len(data))+tag+data+struct.pack('>I', zlib.crc32(tag+data)&0xffffffff)
    h, w, _ = pixels.shape
    scan = b''.join(b'\0'+row.astype('>u2').tobytes() for row in pixels)
    data = b'\x89PNG\r\n\x1a\n'
    data += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 16, 2, 0, 0, 0))
    data += chunk(b'iCCP', b'sRGB\0\0'+zlib.compress(icc))
    data += chunk(b'IDAT', zlib.compress(scan))+chunk(b'IEND', b'')
    with path.open('xb') as f:
        f.write(data)
    decoded = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert np.array_equal(decoded[..., ::-1], pixels)


assert not (HERE/'receipt.json').exists()
rows, masters = [], []
for arm, (path, expected, wh) in ARMS.items():
    before = (path.stat().st_size, path.stat().st_mtime_ns)
    source = ref(path)
    assert source['sha256'] == expected
    with tifffile.TiffFile(path) as tf:
        assert len(tf.pages) == 1 and tf.pages[0].shape == (wh[1], wh[0], 3)
        assert tf.pages[0].dtype == np.uint16
        icc = bytes(tf.pages[0].tags[34675].value)
    assert hashlib.sha256(icc).hexdigest() == '238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
    image = tifffile.memmap(path, mode='r')
    for choice in CHOICES:
        x, y, w, h = choice[arm]
        assert w == h == 384 and 0 <= x <= wh[0]-w and 0 <= y <= wh[1]-h
        pixels = np.array(image[y:y+h, x:x+w], copy=True)
        master = HERE/f'{arm}-{choice["name"]}.tiff'
        png = HERE/f'{arm}-{choice["name"]}.png'
        assert not master.exists() and not png.exists()
        tifffile.imwrite(master, pixels, photometric='rgb', metadata=None,
                        extratags=[(34675, 'B', len(icc), icc, False)])
        assert np.array_equal(tifffile.imread(master), pixels)
        save_png(png, pixels, icc)
        rows.append({'arm': arm, 'name': choice['name'], 'native_xywh': choice[arm],
                     'native_grid_wh': wh, 'master': ref(master), 'display': ref(png),
                     'rgb16_le_sha256': hashlib.sha256(pixels.astype('<u2').tobytes()).hexdigest()})
    del image
    assert before == (path.stat().st_size, path.stat().st_mtime_ns)
    assert ref(path) == source
    masters.append({'arm': arm, 'source': source, 'native_wh': wh,
                    'icc_sha256': hashlib.sha256(icc).hexdigest(), 'metadata_and_content_unchanged': True})

receipt = {'status': 'SIX_FIXED_NATIVE_PANELS_EXTRACTED', 'choices': CHOICES, 'masters': masters,
           'panels': rows, 'source': ref(Path(__file__)), 'resampling': False, 'registration': False,
           'display': 'Exact RGB16 PNG with the original ICC; no resizing or tone change.',
           'correspondence': 'Manual recognizable anatomy from each full overview; not aligned pixel truth.',
           'choice_policy': 'No moving a window after viewing its panel; failed correspondence is uninformative.',
           'quality_score': None}
with (HERE/'receipt.json').open('x', encoding='utf-8') as f:
    json.dump(receipt, f, indent=2, allow_nan=False)
    f.write('\n')
print('Saved six fixed native panels; no image registration, source selection or quality score.')
