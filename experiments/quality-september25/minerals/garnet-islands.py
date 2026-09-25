"""Three already-sampled original frames; bounded island provenance only."""
from pathlib import Path
import importlib.util,json,hashlib
import rawpy,numpy as np,tifffile
from PIL import Image
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mineral_samples',HERE/'raw-samples.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
item=[x for x in json.loads((HERE/'inventory.json').read_text()) if x['code']=='104'][0]
master=Path(item['master']);box=(4720,1930,256,256)
with tifffile.TiffFile(master) as tf:
 out=tf.asarray();icc=bytes(tf.pages[0].tags[34675].value)
x,y,w,h=box;out=out[y:y+h,x:x+w]
Image.fromarray(((out.astype(np.uint32)+128)//257).astype(np.uint8)).save(HERE/'104-islands-native256.png',icc_profile=icc)
rows=[]
for index in [91,120,137]:
 path=Path(item['source_folder'])/f'DSC{27+index:05d}.ARW'
 with rawpy.imread(str(path)) as raw: a=raw.raw_image_visible.copy()
 planes=[a[0::2,0::2],a[0::2,1::2],a[1::2,0::2],a[1::2,1::2]]
 yy,xx=np.mgrid[0:h//2,0:w//2];xx=xx+x/2+item['crop_quad_xywh'][0];yy=yy+y/2+item['crop_quad_xywh'][1]
 sx,sy=m.transform(m.ROOT/'outputs/minerals-september24/104msdcf/alignment.txt',index,xx,yy)
 sx=np.rint(sx).astype(int);sy=np.rint(sy).astype(int)
 p=[v[sy,sx] for v in planes]
 for name,v in zip(['r','g1','g2','b'],p):
  np.save(HERE/f'104-islands-raw-{index}-{name}.npy',v)
  signal=np.clip((v.astype(np.float32)-512)/15871,0,1)
  display=np.where(signal<=.0031308,12.92*signal,1.055*signal**(1/2.4)-.055)
  Image.fromarray(np.repeat(np.round(display*255).astype(np.uint8)[...,None],3,axis=2)).save(HERE/f'104-islands-raw-{index}-{name}.png',icc_profile=icc)
 rows.append(dict(index=index,path=str(path),file_sha256=m.mod.sha(path),output_native_xywh=box,
   sampling='same retained sidecar; nearest CFA-quad;128x128 original plane samples; noCA/MHC/merge/tone',
   planes={name:m.census(v) for name,v in zip(['R','G1','G2','B'],p)}))
(HERE/'garnet-islands.json').write_text(json.dumps(rows,indent=2)+'\n')
