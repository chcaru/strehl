"""Rule48 followup: exact384px tiles inside previously selected640px regions."""
from pathlib import Path
import hashlib,json
from PIL import Image
HERE=Path(__file__).resolve().parent
rois=json.loads((HERE/'rois.json').read_text())
rows=[]
for code,regions in rois.items():
 for name,(x,y,w,h) in regions.items():
  source=HERE/f'{code}-{name}-stack.png'
  with Image.open(source) as im:
   icc=im.info['icc_profile'];tile=im.crop((128,128,512,512))
   assert tile.size==(384,384)
   output=HERE/f'{code}-{name}-native384.png'
   tile.save(output,icc_profile=icc)
  rows.append(dict(path=str(output),output_native_xywh=[x+128,y+128,384,384],
       source=str(source),operation='exact integer crop; no resampling or re-encoding',
       sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
(HERE/'native-tiles.json').write_text(json.dumps(rows,indent=2)+'\n')
