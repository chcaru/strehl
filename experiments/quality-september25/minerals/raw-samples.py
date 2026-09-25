"""Fixed-index RAW census, not a best-frame selector. No originals modified."""
from pathlib import Path
import hashlib,json,struct,importlib.util,sys
import numpy as np,rawpy,tifffile
from PIL import Image,ImageCms
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('mineral_inventory',HERE/'inspect.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def census(a):
 return dict(n=int(a.size),minimum=int(a.min()),maximum=int(a.max()),
  at_nominal_white_15360=int(np.count_nonzero(a>=15360)),at_container_max_16383=int(np.count_nonzero(a>=16383)),
  percentiles={str(p):float(np.percentile(a,p)) for p in [50,99,99.9,99.99]},
  sha256=hashlib.sha256(a.tobytes()).hexdigest())
def transform(path,index,x,y):
 line=[s.split() for s in path.read_text().splitlines() if s.startswith(f'{index} placed ')][0]
 ar,ai,br,bi=[struct.unpack('>d',bytes.fromhex(v))[0] for v in line[2:6]]
 dx=x-(3516-1)/2;dy=y-(2344-1)/2
 return ar*dx-ai*dy+br+(3516-1)/2,ai*dx+ar*dy+bi+(2344-1)/2
def main():
 extra='--extra' in sys.argv
 records=json.loads((HERE/'raw-samples.json').read_text()) if extra else []
 inventory=json.loads((HERE/'inventory.json').read_text())
 # Locations selected from complete stack overviews, before examining RAW frames.
 rois={'100':{'white-patch':[1080,620,640,640],'blue-control':[2780,2640,640,640]},
       '102':{'white-patch':[1270,2620,640,640],'blue-control':[3200,1500,640,640]},
       '103':{'reflection':[3500,1530,640,640],'colour-control':[2000,2100,640,640]},
       '104':{'white-facet':[4540,1730,640,640],'red-control':[2940,1780,640,640]},
       '105':{'gold-blades':[4580,2250,640,640],'dark-control':[2300,2300,640,640]}}
 for item,(_,label,first,last,group) in zip(inventory,mod.ITEMS):
  code=item['code'];n=item['frames'];inds=sorted(set([0,n//2,n-1]+([n//4,3*n//4] if code in ['100','104'] else [])))
  if extra:
   inds={'100':[70,80,90],'104':[110,120,130]}.get(code,[])
   if not inds: continue
  master=Path(item['master']);icc=None
  with tifffile.TiffFile(master) as tf:
   rgb=tf.asarray();icc=bytes(tf.pages[0].tags[34675].value)
  for name,(x,y,w,h) in rois[code].items():
   Image.fromarray(((rgb[y:y+h,x:x+w].astype(np.uint32)+128)//257).astype(np.uint8)).save(HERE/f'{code}-{name}-stack.png',icc_profile=icc)
  del rgb
  for i in inds:
   path=Path(item['source_folder'])/f'DSC{first+i:05d}.ARW'
   with rawpy.imread(str(path)) as raw:
    a=raw.raw_image_visible.copy()
    meta=dict(raw_sizes=str(raw.sizes),black=list(raw.black_level_per_channel),white=raw.white_level,
       camera_white=raw.camera_white_level_per_channel,wb=list(raw.camera_whitebalance),pattern=raw.raw_pattern.tolist())
   # LibRaw reports 7028 visible columns; product rawler reports 7032. Only the
   # independent decoder's populated visible region is counted. Selected ROIs
   # are interior to both; no right-edge padding enters any statistic.
   assert a.shape==(4688,7028) and a.dtype==np.uint16 and meta['pattern']==[[0,1],[3,2]]
   planes=[a[0::2,0::2],a[0::2,1::2],a[1::2,0::2],a[1::2,1::2]]
   rec=dict(code=code,index=i,path=str(path),file_sha256=mod.sha(path),metadata=meta,active=census(a),planes={key:census(p) for key,p in zip(['R','G1','G2','B'],planes)},rois={})
   for name,(x,y,w,h) in rois[code].items():
    ox,oy=item['crop_quad_xywh'][:2]
    yy,xx=np.mgrid[0:h//2,0:w//2];xx=xx+x/2+ox;yy=yy+y/2+oy
    sx,sy=transform(ROOT/'outputs'/group/f'{code}msdcf'/'alignment.txt',i,xx,yy)
    sx=np.rint(sx).astype(int);sy=np.rint(sy).astype(int)
    assert sx.min()>=0 and sy.min()>=0 and sx.max()<3514 and sy.max()<2344
    gathered=[p[sy,sx] for p in planes]
    rec['rois'][name]=dict(output_native_xywh=[x,y,w,h],gauge='held sidecar reference, nearest CFA-quad sample; no CA',
      planes={key:census(p) for key,p in zip(['R','G1','G2','B'],gathered)})
    g=(gathered[1].astype(np.float32)+gathered[2].astype(np.float32))/2
    # Fixed physical DN scaling shared by all sources, reaching white only at
    # actual 14-bit container maximum, not an arbitrary bright display cutoff.
    v=np.clip((g-512)/15871,0,1);v=np.where(v<=.0031308,12.92*v,1.055*v**(1/2.4)-.055)
    view=np.repeat(np.round(v*255).astype(np.uint8)[...,None],3,axis=2)
    Image.fromarray(view).save(HERE/f'{code}-{name}-raw-{i:03d}.png',icc_profile=icc)
   # Whole original green witness, fixed DN display, no auto tone or spatial selection.
   g=(planes[1].astype(np.float32)+planes[2].astype(np.float32))/2
   v=np.clip((g-512)/15871,0,1);v=np.where(v<=.0031308,12.92*v,1.055*v**(1/2.4)-.055)
   im=Image.fromarray(np.repeat(np.round(v*255).astype(np.uint8)[...,None],3,axis=2));im.thumbnail((1617,1617),Image.Resampling.LANCZOS)
   im.save(HERE/f'{code}-raw-{i:03d}-whole.jpg',quality=98,subsampling=0,icc_profile=icc)
   records.append(rec);print(code,i,rec['active']['maximum'],rec['active']['at_nominal_white_15360'],rec['active']['at_container_max_16383'],flush=True)
  (HERE/'raw-samples.json').write_text(json.dumps(records,indent=2)+'\n')
 (HERE/'rois.json').write_text(json.dumps(rois,indent=2)+'\n')
if __name__=='__main__':main()
