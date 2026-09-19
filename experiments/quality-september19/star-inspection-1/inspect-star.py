"""Frozen native crops and an explicitly resized orientation overview."""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw
import tifffile

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / 'star-baseline-1'
ROIS = {'ridged-shell': [1360, 1136, 392, 392], 'porous-grain': [440, 1320, 392, 392]}
EXPECTED = '0111ed93166e775f87d50399ce75b5e2b039d74ff956208c50ca6d29bcd7e459'
image_path = BASELINE / 'star.tiff'
assert hashlib.sha256(image_path.read_bytes()).hexdigest() == EXPECTED
rgb = tifffile.imread(image_path)
assert rgb.shape == (4480, 6724, 3) and rgb.dtype == np.uint16

def display(a):
    return (a.astype(np.uint32) * 255 // 65535).astype(np.uint8)

overview = Image.fromarray(display(rgb)).resize((1513, 1008), Image.Resampling.LANCZOS)
overview.save(HERE / 'overview-orientation.png')
annotated = overview.copy()
draw = ImageDraw.Draw(annotated)
records = []
for name, (x, y, w, h) in ROIS.items():
    patch = rgb[y:y+h, x:x+w].copy()
    tifffile.imwrite(HERE / f'{name}-native.tiff', patch, photometric='rgb')
    Image.fromarray(display(patch)).save(HERE / f'{name}-native.png')
    sx, sy = overview.width / rgb.shape[1], overview.height / rgb.shape[0]
    draw.rectangle((x*sx, y*sy, (x+w)*sx, (y+h)*sy), outline=(255, 40, 0), width=2)
    draw.text((x*sx, max(0, y*sy-14)), name, fill=(255, 40, 0))
    records.append(dict(name=name, output_xywh=[x,y,w,h], reference_sensor_xywh=[x+154,y+104,w,h],
                        raw_u16_rgb_sha256=hashlib.sha256(patch.tobytes()).hexdigest()))
annotated.save(HERE / 'overview-roi-locations.png')
receipt = dict(source=str(image_path), source_sha256=EXPECTED, source_shape=list(rgb.shape),
               reference_index=129, reference_filename='DSC00145.ARW', sensor_crop_origin=[154,104],
               plane_crop_origin=[77,52], tone_log_rounded=dict(black=.01566,white=.51099,contrast=.55),
               tone_precision='Printed log values only; not exact renderer float bits',
               native_crop_encoding='Unresampled RGB16 TIFF and uint16*255//65535 RGB8 PNG; no enhancement',
               overview='1513x1008 Lanczos resize for orientation only; not quality evidence', rois=records)
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
print(json.dumps(receipt))
