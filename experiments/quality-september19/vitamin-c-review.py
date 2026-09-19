"""Freeze native output windows from the complete baseline before comparisons."""
from pathlib import Path
import json
import numpy as np
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'vitamin-c-baseline-1/vitamin-c.tiff'
OUT = HERE / 'vitamin-c-review-1'
REGIONS = [
    {'name':'facet-edges', 'xywh':[2500,2700,384,384]},
    {'name':'pale-background', 'xywh':[400,1150,384,384]},
    {'name':'fine-crystals', 'xywh':[4200,1700,384,384]},
    {'name':'bright-facet', 'xywh':[1150,3850,384,384]},
    {'name':'dark-inclusion', 'xywh':[3050,1850,384,384]},
]
OUT.mkdir()
src = tifffile.imread(SOURCE)
assert src.dtype == np.uint16 and src.shape == (4612,6920,3)
for r in REGIONS:
    x,y,w,h = r['xywh']
    cut = src[y:y+h,x:x+w]
    Image.fromarray(((cut.astype(np.uint32)+128)//257).astype(np.uint8)).save(OUT/(r['name']+'.png'))
(OUT/'regions.json').write_text(json.dumps({'source':str(SOURCE.resolve()),'regions':REGIONS,
    'display':'rounded division by257, no scaling; native output coordinates',
    'selection':'root chose from complete baseline overview before candidate/comparator',
    'scope':'photographic diagnostic regions, no assumed flat calibrated noise ROI'},indent=2)+'\n')
