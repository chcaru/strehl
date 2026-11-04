"""Predeclared appearance controls on frozen native crops; no RAW or image fitting."""
from pathlib import Path
import importlib.util,json
import numpy as np
from PIL import Image
import tifffile
s=Path('experiments/multi-stack-2026-10-28/challenge/prepare-review.py');sp=importlib.util.spec_from_file_location('h',s);h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
run=Path('outputs/multi-stack/completion/appearance-layers-13');out=Path('outputs/multi-stack/completion/appearance-review-13')
r=json.loads((out/'roi-frozen.json').read_text());baseline=json.loads((out/'fixed-transform.json').read_text())['display_baseline'];icc=(out/'display-srgb.icc').read_bytes()
a=tifffile.memmap(run/'layer-01/master.tiff',mode='r');b=tifffile.memmap(run/'layer-02/master.tiff',mode='r');reports=[]
for roi in r:
 x,y=roi['origins']['layer-01'];aa=np.array(a[y:y+384,x:x+384]);bb=np.array(b[y:y+384,x:x+384]);null=h.encoded8(h.display(aa,baseline))
 assert np.array_equal(null,np.array(Image.open(out/'layer-01'/('native-'+roi['name']+'.png'))))
 board=Image.new('RGB',(768,768))
 for im,pos in [(null,(0,0)),(h.encoded8(h.display(bb,baseline)),(384,0)),(h.encoded8(h.display(aa*np.float32(3.2/5),baseline)),(0,384)),(h.encoded8(h.display((aa+bb)*np.float32(.5),baseline)),(384,384))]:board.paste(Image.fromarray(im),pos)
 board.save(out/('selection-control-'+roi['name']+'.png'),icc_profile=icc)
 if roi['name']=='brown-eye':
  shifted=np.array(b[y+8:y+392,x:x+384]);Image.fromarray(h.encoded8(h.display((aa+shifted)*np.float32(.5),baseline))).save(out/'negative-eye-shift-y8.png',icc_profile=icc)
 reports.append({'name':roi['name'],'null_exact':True,'nominal_shutter_gain_first':3.2/5,'display_file_sha256':h.digest(out/('selection-control-'+roi['name']+'.png'))})
h.write_json(out/'selection-controls.json',{'script_sha256':h.digest(__file__),'protocol_sha256':h.digest('experiments/multi-stack-2026-10-28/completion/review/diversity-protocol-frozen.json'),'layout':'Top left/right: original layer01/layer02; bottom left:first*3.2/5, bottomright:equal post-render linear RGB mean. Everypanel384 exact samples.','scope':'Nominal shutter compensation is not calibrated reflectance normalization. Post-render RGB mean illustrates altered appearance and is not an actual RAW fusion foil or quality metric.','negative':'Brown-eye second image shifted8 native y before mean; wrong-registration visual control.','rows':reports})
