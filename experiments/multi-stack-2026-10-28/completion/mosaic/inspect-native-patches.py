"""Render exact cached native-green patch pairs for diagnosis, never output fusion."""
import argparse,hashlib,json,os,struct
from pathlib import Path
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='4'
import numpy as np
import cv2
from PIL import Image,ImageDraw
cv2.setNumThreads(4)
p=argparse.ArgumentParser();p.add_argument('--pilot',type=Path,required=True);p.add_argument('--replay',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--id',action='append');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
identities=json.loads((a.pilot/'source-identities.json').read_text());headers={}
for path in a.cache.glob('*.cfa'):
 with path.open('rb') as f:
  prefix=f.read(12);assert prefix[:8]==b'STRHCFA1';n=struct.unpack('<I',prefix[8:])[0];assert n<262144;head=json.loads(f.read(n))
 headers[(head['source']['sha256'],head['source']['path'])]=(path,12+n,head)
def source(index):
 identity=identities[index];path,offset,head=headers[(identity['sha256'],identity['path'])];assert identity==head['source'];w,h=head['geometry']['width'],head['geometry']['height'];assert path.stat().st_size==offset+2*w*h+32
 with path.open('rb') as f:
  f.seek(12);digest=hashlib.sha256(f.read(offset-12));remaining=2*w*h
  while remaining:
   b=f.read(min(1048576,remaining));assert b;digest.update(b);remaining-=len(b)
  assert digest.digest()==f.read(32)
 raw=np.memmap(path,dtype='<u2',mode='r',offset=offset,shape=(h,w));black=struct.unpack('<f',struct.pack('<I',head['metadata']['black_bits']))[0]
 # Exact production green_luma operation order.
 values=(np.maximum(raw[0::2,1::2].astype(np.float32)-black,0)+np.maximum(raw[1::2,0::2].astype(np.float32)-black,0))*.5
 return values,head
records=json.loads((a.replay/'mosaic-native-measurements.json').read_text());results=[]
selected=a.id or ['p0-p1-grid-304-400-source691','p0-p1-f421-f499','p0-p1-grid-144-560-source610']
for record in records:
 if record['candidate']['id'] not in selected:continue
 c=record['candidate'];m=next(m for m in record['measurements'] if m['direction']=='forward');obs=np.array(m['observations']);keep=np.array(m['kept'],dtype=bool) if m['kept'] else np.ones(len(obs),dtype=bool);obs=obs[keep]
 rows=[];target=[]
 for x,y,dx,dy in obs:rows.extend([[x,-y,1,0],[y,x,0,1]]);target.extend([dx,dy])
 fit=np.linalg.lstsq(rows,target,rcond=None)[0];centre=np.array(m['plane_center']);point=centre+obs[:,:2].mean(0)
 yy,xx=np.mgrid[-64:64,-64:64];x=point[0]+xx;y=point[1]+yy
 bx=x+fit[0]*(x-centre[0])-fit[1]*(y-centre[1])+fit[2];by=y+fit[1]*(x-centre[0])+fit[0]*(y-centre[1])+fit[3]
 va,ha=source(c['source_a']);pa=cv2.remap(va,x.astype(np.float32),y.astype(np.float32),cv2.INTER_LINEAR);del va
 vb,hb=source(c['source_b']);pb=cv2.remap(vb,bx.astype(np.float32),by.astype(np.float32),cv2.INTER_LINEAR);del vb
 lo,hi=np.percentile(np.r_[pa.ravel(),pb.ravel()],[1,99]);render=lambda q:np.uint8(np.clip((q-lo)/(hi-lo),0,1)*255)
 canvas=Image.new('RGB',(512,160),(20,20,20));draw=ImageDraw.Draw(canvas)
 for k,(name,patch) in enumerate([('A native',pa),('B fitted native',pb),('A lowpass',cv2.GaussianBlur(pa,(5,5),1.0)),('B lowpass',cv2.GaussianBlur(pb,(5,5),1.0))]):
  canvas.paste(Image.fromarray(render(patch)),(128*k,25));draw.text((128*k+3,5),name,fill='white')
 path=a.out/(c['id']+'.png');canvas.save(path)
 result={'id':c['id'],'sources':[c['source_a'],c['source_b']],'source_sha256':[identities[c['source_a']]['sha256'],identities[c['source_b']]['sha256']],'reference_quad_centre':point.tolist(),'size_quad':128,'display_percentiles':[float(lo),float(hi)],'similarity_fit_from_saved_observations':fit.tolist(),'semantics':'Native128quad patches, no resize. Interpolated diagnostic B using fitted production observations; not independent placement proof. Gaussian panels orientation only, not production geometry.'};results.append(result)
assert sorted(r['id'] for r in results)==sorted(selected), 'requested native receipts absent'
(a.out/'receipt.json').write_text(json.dumps({'command':__import__('sys').argv,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'native_measurements_sha256':hashlib.sha256((a.replay/'mosaic-native-measurements.json').read_bytes()).hexdigest(),'patches':results},indent=2)+'\n')
