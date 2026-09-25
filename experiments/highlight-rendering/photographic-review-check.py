"""Independent bindings/display checks for the two completed renderer factorials."""
from pathlib import Path
import hashlib,json
import numpy as np,tifffile
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
result={'command':'python -I -B -X faulthandler experiments/highlight-rendering/photographic-review-check.py','subjects':[]}
for subject,run in [('marigold','marigold4'),('ore','ore100')]:
 viewpath=ROOT/f'experiments/quality-september25/{subject}-render-views-1/receipt.json'
 view=json.loads(viewpath.read_text());rp=HERE/f'replay-{run}-1/output/receipt.json';receipt=json.loads(rp.read_text())
 expected={r['arm']:r for r in receipt['arms']};entries=[];current={}
 for item in view['images']:
  arm=item['arm'];p=Path(item['master']);assert sha(p)==item['master_sha256']==expected[arm]['file_sha256']
  assert sha(Path(item['complete_overview']))==item['overview_sha256']
  with tifffile.TiffFile(p) as f:
   assert len(f.pages)==1;pixels=f.asarray();icc=bytes(f.pages[0].tags[34675].value)
  assert pixels.dtype==np.uint16 and list(pixels.shape)==view['native_shape']
  assert hashlib.sha256(icc).hexdigest()==view['icc_sha256']
  assert hashlib.sha256(pixels.astype('<u2',copy=False).tobytes()).hexdigest()==expected[arm]['rgb16_le_sha256']
  checks=[]
  for tile in item['tiles']:
   x,y,w,h=tile['rect'];assert 0<w<=384 and 0<h<=384
   path=Path(tile['path']);assert sha(path)==tile['sha256']
   with Image.open(path) as im:
    rgb=np.asarray(im);assert im.info['icc_profile']==icc
   actual=((pixels[y:y+h,x:x+w].astype(np.uint32)+128)//257).astype(np.uint8)
   assert np.array_equal(rgb,actual)
   if arm=='current':current[tile['target']]=rgb.copy()
   ref=current[tile['target']];delta=np.abs(rgb.astype(np.int16)-ref.astype(np.int16))
   checks.append(dict(target=tile['target'],rect=tile['rect'],display_changed_pixels=int(np.any(delta!=0,axis=2).sum()),max_display_code_delta=int(delta.max())))
  entries.append(dict(arm=arm,master_sha256=item['master_sha256'],rgb16_le_sha256=expected[arm]['rgb16_le_sha256'],tiles=checks))
 result['subjects'].append(dict(subject=subject,view_receipt_sha256=sha(viewpath),render_receipt_sha256=sha(rp),arms=entries))
(HERE/'photographic-review-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
