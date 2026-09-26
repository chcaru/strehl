"""Compare retained deliveries with corrected full renders; pixel changes are not quality scores."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import tifffile
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]

def ref(path):
    with path.open('rb') as f:
        return dict(path=str(path.resolve()), bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(f, 'sha256').hexdigest())

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def rgb(path):
    with tifffile.TiffFile(path) as tf:
        assert len(tf.pages) == 1
        pixels = tf.asarray()
        icc = bytes(tf.pages[0].tags[34675].value)
    assert pixels.ndim == 3 and pixels.shape[2] == 3 and pixels.dtype == np.uint16 and icc
    return pixels, icc

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--code', required=True)
    p.add_argument('--delivery', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    assert not out.exists() and out.is_relative_to(ROOT/'experiments/garnet-spatial-trace')
    inventory = ROOT/'experiments/quality-september25/minerals/inventory.json'
    old = next(row for row in read(inventory) if row['code'] == a.code)
    old_path = Path(old['master'])
    assert ref(old_path)['sha256'] == old['sha256']
    done = read(a.delivery/'completion.json')
    current_path = a.delivery/'stack-master.tiff'
    assert ref(current_path) == done['master']
    assert done['original_bytes_and_metadata_unchanged']
    before, icc = rgb(old_path)
    after, new_icc = rgb(current_path)
    assert before.shape == after.shape == tuple(old['output_shape']) and icc == new_icc
    out.mkdir()
    largest = np.zeros(before.shape[:2], dtype=np.uint16)
    for c in range(3):
        delta = np.abs(after[:,:,c].astype(np.int32)-before[:,:,c].astype(np.int32)).astype(np.uint16)
        np.maximum(largest, delta, out=largest)
    # A location selected by numerical change is for inspecting the repair or
    # regression, never independently selected evidence of photographic benefit.
    peak = int(largest.argmax())
    y, x = np.unravel_index(peak, largest.shape)
    w = h = 384
    x0 = max(0, min(int(x)-w//2, before.shape[1]-w))
    y0 = max(0, min(int(y)-h//2, before.shape[0]-h))
    views = []
    for name, data in [('before', before), ('corrected', after)]:
        patch = ((data[y0:y0+h,x0:x0+w].astype(np.uint32)+128)//257).astype(np.uint8)
        file = out/f'{name}-largest-change-native.png'
        Image.fromarray(patch).save(file, icc_profile=icc)
        views.append(ref(file))
    result = dict(code=a.code, inputs=[ref(inventory),ref(old_path),ref(current_path),ref(a.delivery/'completion.json')],
        full_shape=list(before.shape), pixels_changed=int(np.count_nonzero(largest)),
        pixels_max_channel_change_gt_32=int(np.count_nonzero(largest>32)),
        max_channel_change=int(largest.max()), selected_peak_native_xy=[int(x),int(y)],
        diagnostic_crop_native_xywh=[x0,y0,w,h], views=views,
        scope='Whole delivered RGB comparison. Differences include automatic-tone changes. Change counts are not quality metrics; view location is deliberately selected by change.',
        photographic_verdict=None)
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('code','pixels_changed','pixels_max_channel_change_gt_32','max_channel_change','diagnostic_crop_native_xywh')}))

if __name__ == '__main__':
    main()
