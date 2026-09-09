from pathlib import Path
import json,hashlib
import numpy as np
import tifffile
from PIL import Image
root=Path.cwd()
p=root/"experiments/native-stroke-correction"
out=p/"view-1";out.mkdir()
base=root/"experiments/native-product-comparison/run-1/native-coffee-bean.tiff"
new=p/"render-1/corrected-coffee-bean.tiff"
a=tifffile.memmap(base);b=tifffile.memmap(new)
assert a.shape==b.shape==(4524,6784,3) and a.dtype==b.dtype==np.uint16
rois=json.loads((root/"experiments/native-product-comparison/next-rois.json").read_text())
regions=[dict(id="stroke",xywh=rois["stroke"]),dict(id="clean",xywh=rois["nearby_clean"])]
existing=json.loads((root/"experiments/native-product-comparison/view-1/regions.json").read_text())
regions.extend(dict(id=r["id"],xywh=r["native"]) for r in existing["regions"] if r["id"]!="background")
records=[]
for r in regions:
    x,y,w,h=r["xywh"];old=np.array(a[y:y+h,x:x+w],copy=True);cur=np.array(b[y:y+h,x:x+w],copy=True)
    delta=cur.astype(np.int32)-old.astype(np.int32)
    row=dict(**r,different_values=int(np.count_nonzero(delta)),total_values=int(delta.size),
        minimum_dn=int(delta.min()),maximum_dn=int(delta.max()),mean_abs_dn=float(np.mean(np.abs(delta))))
    if w<=400 and h<=200:
        # Vertical before/after pair; same rounded RGB16/257 to RGB8, no resampling.
        array=np.concatenate((old,cur),axis=0)
        image=np.rint(array.astype(np.float32)/257).clip(0,255).astype(np.uint8)
        path=out/(r["id"]+".png");Image.fromarray(image).save(path)
        row["preview"]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            top="savedbaseline",bottom="corrected",resized=False)
    elif np.any(delta):
        # Split each source into <=256x256 original-sampling tiles, never resized.
        row["tiles"]=[]
        for ty in range(0,h,256):
            for tx in range(0,w,256):
                for label,img in (("before",old),("after",cur)):
                    path=out/f'{r["id"]}-{tx}-{ty}-{label}.png'
                    pix=np.rint(img[ty:ty+256,tx:tx+256].astype(np.float32)/257).clip(0,255).astype(np.uint8)
                    Image.fromarray(pix).save(path)
                    row["tiles"].append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    records.append(row)
del a,b
summary=dict(sources=dict(baseline=str(base),corrected=str(new)),regions=records,
    display="round(RGB16/257) identical perarm; every pixel at1:1, no registration/tone/resize repair",
    scope="local target comparison and fixed actual source controls; no sharpness or noise quality metric")
(out/"regions.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print(json.dumps([{k:v for k,v in r.items() if k not in ("tiles","preview")} for r in records],indent=2))
