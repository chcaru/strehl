"""Neutral full-image previews and native crops, original TIFFs untouched."""
from pathlib import Path
import hashlib,json
import numpy as np,tifffile
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
REGIONS={1:[('bud-rim',2900,540,600,500),('left-petal-over-bud',640,1480,600,600),('central-pocket',2730,1900,600,600)],4:[('central-throat',2350,2310,700,500),('left-rim',1170,1380,650,600),('foreground-over-bud',3230,3000,600,600)]}
records=[];rois=[];tiles=[]
for k in range(1,5):
 p=ROOT/f'outputs/flower-marigold-cpl/final/marigold-stack-{k}-master.tiff'
 with tifffile.TiffFile(p) as f:a=f.asarray();icc=bytes(f.pages[0].tags[34675].value)
 rgb=((a.astype(np.uint32)+128)//257).astype(np.uint8)
 im=Image.fromarray(rgb);im.thumbnail((1617,1617),Image.Resampling.LANCZOS)
 dest=OUT/f'stack-{k}-overview.png'; im.save(dest,icc_profile=icc)
 records.append(dict(stack=k,source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=list(a.shape),overview=str(dest),display='rounded u16/257; LANCZOS complete image max 1617; original ICC'))
 for name,x,y,w,h in REGIONS.get(k,[]):
  dest=OUT/f'stack-{k}-{name}.png';Image.fromarray(rgb[y:y+h,x:x+w]).save(dest,icc_profile=icc)
  rois.append(dict(stack=k,name=name,rect=[x,y,w,h],path=str(dest)))
  for tx in (0,max(0,w-384)):
   for ty in (0,max(0,h-384)):
    dest=OUT/f'stack-{k}-{name}-tile-{tx}-{ty}.png'
    Image.fromarray(rgb[y+ty:y+ty+min(384,h),x+tx:x+tx+min(384,w)]).save(dest,icc_profile=icc)
    tiles.append(dict(stack=k,region=name,rect=[x+tx,y+ty,min(384,w),min(384,h)],path=str(dest)))
(OUT/'overview-receipt.json').write_text(json.dumps(records,indent=2)+'\n')
(OUT/'regions.json').write_text(json.dumps(rois,indent=2)+'\n')
(OUT/'native-tiles.json').write_text(json.dumps(tiles,indent=2)+'\n')
print('four complete previews; six native regions; original ICC retained')
