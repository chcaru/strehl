"""Inspect the existing merged CFA values before the writer, no RAW read."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'garnet-cache-planes'
CACHE=ROOT/'experiments/full-stack-source-prior/garnet104-full-1/output/baseline-cache.json'
m=json.loads(CACHE.read_text()); source=CACHE.parent/m['binary']
with source.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==m['binary_sha256']
assert m['phase']=='full' and m['crop']==[127,85,3262,2174]
a=np.memmap(source,dtype='<f4',mode='r',shape=(4,2174,3262))
x,y,w,h=4668,1858,384,384
OUT.mkdir(exist_ok=False)
rows=[]
for i,name in enumerate(('r','g1','g2','b')):
    v=a[i,y//2:(y+h)//2,x//2:(x+w)//2].copy()
    assert v.shape==(192,192) and np.isfinite(v).all()
    dest=OUT/(name+'.png')
    Image.fromarray(np.rint(np.sqrt(np.clip(v/15871.0,0,1))*255).astype(np.uint8)).save(dest)
    np.save(OUT/(name+'.npy'),v)
    rows.append(dict(plane=name,path=str(dest),minimum=float(v.min()),maximum=float(v.max()),
                     at_sensor_span=int((v>=15871).sum())))
(OUT/'receipt.json').write_text(json.dumps(dict(cache=str(CACHE),binary_sha256=m['binary_sha256'],
    output_native_xywh=[x,y,w,h],display='192x192 CFA quad sites, fixed sqrt(clamp(black-subtracted DN/15871))*255; no WB, matrix, MHC or tone',
    planes=rows),indent=2)+'\n')
print(json.dumps(rows))
