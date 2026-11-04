"""Predeclared support-only boundary diagnostic; never selects by image/difference."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import importlib.util,json
import numpy as np
from PIL import Image,ImageDraw
import tifffile
R=Path(__file__).resolve().parents[4]
p=R/'experiments/multi-stack-2026-10-28/challenge/prepare-review.py';s=importlib.util.spec_from_file_location('h',p);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
base=R/'outputs/multi-stack/completion';out=base/'independent-photographs/sr-full15/boundary-diagnostics';out.mkdir(exist_ok=False)
mask=tifffile.memmap(base/'sr-chart-full-15/reconstruction/support.tiff',mode='r');height,width=mask.shape;size=384
first=None
for y in range(height):
 xs=np.flatnonzero(mask[y,1:]!=mask[y,:-1])
 if xs.size:first=(int(xs[0]+1),y);break
assert first is not None
origins=[('first-raster-transition',[max(0,min(width-size,first[0]-size//2)),max(0,min(height-size,first[1]-size//2))])]
best=(-1,None)
for y in range(0,height-size+1,192):
 for x in range(0,width-size+1,192):
  count=int(mask[y:y+size,x:x+size].sum());score=min(count,size*size-count)
  if score>best[0]:best=(score,[x,y])
origins.append(('maximal-mixed-window',best[1]))
freeze={'schema':'strehl.sr-mask-only-boundary-freeze.v1','source_mask_sha256':h.digest(base/'sr-chart-full-15/reconstruction/support.tiff'),
 'selection':'First raster horizontal0/1 transition centered/clamped; greatest min(supported,unsupported)384window on stride192, raster tie break. No candidate or delta pixels for selection.',
 'origins':origins,'size':size,'supplement_only':True}
h.write_json(out/'selection.json',freeze)
transform=R/'experiments/multi-stack-2026-10-28/review/hdr-physical-reference-transform.json';b=json.loads(transform.read_text());icc=(transform.parent/b['display_icc_file']).read_bytes()
receipt=[]
for name,origin in origins:
 x,y=origin;board=Image.new('RGB',(792,416),(30,30,30));draw=ImageDraw.Draw(board)
 for i,(label,arm) in enumerate((('Native','sr-chart-native-14c'),('SR15','sr-chart-full-15'))):
  a=tifffile.memmap(base/arm/'master.tiff',mode='r');crop=np.array(a[y:y+size,x:x+size]);encoded=h.encoded8(h.display(crop,b['display_baseline']));im=Image.fromarray(encoded)
  path=out/f'{name}-{label}.png';im.save(path,icc_profile=icc);board.paste(im,(8+392*i,24));draw.text((8+392*i,5),label,fill='white');del a
 board.save(out/f'{name}-comparison.png',icc_profile=icc)
 m=np.asarray(mask[y:y+size,x:x+size]);Image.fromarray((m*255).astype(np.uint8)).save(out/f'{name}-support.png')
 receipt.append({'name':name,'origin':origin,'supported_pixels':int(m.sum()),'total_pixels':size*size})
h.write_json(out/'readback.json',{'selection_sha256':h.digest(out/'selection.json'),'transform_sha256':h.digest(transform),'crops':receipt})
print(json.dumps(receipt))
