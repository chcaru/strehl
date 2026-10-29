from pathlib import Path
import json, hashlib, math, sys
import numpy as np
from PIL import Image
import tifffile
import importlib.util
base=Path('outputs/multi-stack/completion/razor-aperture-review-13');run=Path('outputs/multi-stack/completion/razor-aperture-layers-13')
p=Path('experiments/multi-stack-2026-10-28/challenge/prepare-review.py');sp=importlib.util.spec_from_file_location('h',p);h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
r=json.loads((base/'roi-frozen.json').read_text());tr=json.loads((base/'fixed-transform.json').read_text())['display_baseline'];icc=(base/'display-srgb.icc').read_bytes()
a=tifffile.memmap(run/'layer-01/master.tiff',mode='r');b=tifffile.memmap(run/'layer-02/master.tiff',mode='r')
rows=[]
for roi in r:
 x,y=roi['origins']['layer-01'];aa=np.array(a[y:y+384,x:x+384]);bb=np.array(b[y:y+384,x:x+384]);gain=np.float32((8/5.6)**2)
 null=h.encoded8(h.display(aa,tr));assert np.array_equal(null,np.array(Image.open(base/'layer-01'/('native-'+roi['name']+'.png'))))
 # Rows: delivered f5.6/f8, then dimmed f5.6 / nominally raised f8. Not fitted.
 board=Image.new('RGB',(768,768))
 for im,pos in [(null,(0,0)),(h.encoded8(h.display(bb,tr)),(384,0)),(h.encoded8(h.display(aa/gain,tr)),(0,384)),(h.encoded8(h.display(bb*gain,tr)),(384,384))]:board.paste(Image.fromarray(im),pos)
 board.save(base/('exposure-sanity-'+roi['name']+'.png'),icc_profile=icc)
 if roi['name']=='edge-middle':
  shifted=np.array(b[y+8:y+392,x:x+384]);mix=(aa+shifted)*np.float32(.5)
  Image.fromarray(h.encoded8(h.display(mix,tr))).save(base/'negative-shifted-y8px-overlay.png',icc_profile=icc)
 rows.append({'name':roi['name'],'zero_opacity_null_exact':True,'nominal_f8_gain':float(gain),'f5_6_dim_gain':float(1/gain)})
h.write_json(base/'secondary-exposure-sanity-y8.json',{'scope':'Added after first complete/native comparison exposed brightness confounding. Fixed nominal aperture-area gains, no image fitting; these controls do not calibrate transmission, focus, illumination or CPL. Not part of the original predeclared display.','layout':'Top delivered f5.6/f8; bottom f5.6 dimmed by (5.6/8)^2 and f8 raised by (8/5.6)^2. Every384panel exact native samples.','zero_opacity_null':'All8 PNGs exactly reproduced.','shifted_negative':'edge-middle, second layer shifted+8 native y then equal mix; diagnostic registration foil only, not actualRAWmerge.','rows':rows})
