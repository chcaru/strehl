"""Existing-output native boards and activity receipts, no merge/RAW/quality metric."""
from pathlib import Path
import hashlib,json
import numpy as np
import tifffile
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUN=HERE/'full-1'
VIEWS=RUN/'photo-comparison-1'
OUT=HERE/'review-1'
HREC=ROOT/'experiments/helicon-current/photo-comparison-1/coordinate-receipt.json'
REGIONS=ROOT/'experiments/quality-september19/vitamin-c-review-1/regions.json'
ZOOMS=[('facet-core-boundary',[2533,2846,160,160]),('dark-core-boundary',[3011,2097,160,160]),('competing-structure',[3180,2010,120,120])]
SEGMENTS=[((2624,2906),(2602,2945)),((3080,2150),(3102,2203)),((3240,2070),(3240,2070))]

def bind(path):
 with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
 return dict(path=str(path),bytes=path.stat().st_size,sha256=digest)
def save(path,data):
 with path.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def readpng(path):
 with Image.open(path) as im:return np.array(im),im.info.get('icc_profile')
def main():
 if OUT.exists():assert not any(OUT.iterdir()),'Refuse to replace previous review outputs'
 OUT.mkdir(exist_ok=True);arrays={};profile=None
 inputs={}
 for arm in ['baseline','candidate','late']:
  path=VIEWS/(arm+'.png');arrays[arm],icc=readpng(path);inputs[arm]=bind(path)
  if profile is None:profile=icc
  assert icc==profile
 hb=ROOT/'experiments/helicon-current/vitamin-c-b-2/whole-stack.tiff'
 with tifffile.TiffFile(hb) as tf:
  raw=tf.asarray();icc=tf.pages[0].tags[34675].value
 arrays['helicon-b']=((raw.astype(np.uint32)+128)//257).astype(np.uint8)
 assert icc==profile;inputs['helicon-b']=bind(hb);del raw
 matrix=np.array(json.loads(HREC.read_text())['registrations']['helicon-b']['matrix_baseline_to_output'])
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
 regions=json.loads(REGIONS.read_text())['regions'];rows=[]
 for name,box,zoom in [(r['name'],r['xywh'],1) for r in regions]+[(n,b,3) for n,b in ZOOMS]:
  x,y,w,h=box;cx=x+(w-1)/2;cy=y+(h-1)/2;row=dict(name=name,baseline_xywh=box,display_integer_zoom=zoom,arms={})
  tilew=w*zoom;tileh=h*zoom;board=Image.new('RGB',(2*(tilew+16),2*(tileh+42)+36),(235,235,235));draw=ImageDraw.Draw(board)
  draw.text((8,8),name+(' | native samples' if zoom==1 else ' | 3x nearest; no image smoothing'),font=font,fill='black')
  for k,(arm,a) in enumerate(arrays.items()):
   if arm=='helicon-b':
    p=matrix@np.array([cx,cy,1.]);xx,yy=np.rint(p-[(w-1)/2,(h-1)/2]).astype(int)
   else:xx,yy=x,y
   patch=a[yy:yy+h,xx:xx+w];assert patch.shape==(h,w,3);im=Image.fromarray(patch)
   row['arms'][arm]=[int(xx),int(yy),w,h]
   if zoom>1:im.resize((tilew,tileh),Image.Resampling.NEAREST).save(OUT/(name+'-'+arm+'-zoom.png'),icc_profile=profile)
   bx=(k%2)*(tilew+16)+8;by=(k//2)*(tileh+42)+36
   draw.text((bx,by),{'baseline':'Baseline','candidate':'Donors28/33/25','late':'Late69; same masks','helicon-b':'Helicon B (scale1.0107)'}[arm],font=font,fill='black')
   board.paste(im.resize((tilew,tileh),Image.Resampling.NEAREST),(bx,by+26))
  board.save(OUT/(name+'-board.png'),icc_profile=profile);rows.append(row)
  # Separate geometry overlay so the unmarked image remains available.
  if zoom>1:
   overlay=Image.fromarray(arrays['baseline'][y:y+h,x:x+w]).resize((tilew,tileh),Image.Resampling.NEAREST)
   od=ImageDraw.Draw(overlay)
   for a,b in SEGMENTS:
    for radius,colour in [(16,(255,255,0)),(24,(255,0,255))]:
     yy,xx=np.mgrid[y:y+h,x:x+w];vx=b[0]-a[0];vy=b[1]-a[1];norm=vx*vx+vy*vy
     t=np.clip(((xx-a[0])*vx+(yy-a[1])*vy)/norm,0,1) if norm else 0
     d=np.hypot(xx-a[0]-t*vx,yy-a[1]-t*vy);points=np.argwhere(np.abs(d-radius)<.55)
     for py,px in points:od.rectangle((int(px)*zoom,int(py)*zoom,int(px)*zoom+zoom-1,int(py)*zoom+zoom-1),fill=colour)
   overlay.save(OUT/(name+'-mask-outline.png'),icc_profile=profile)
 baseline=tifffile.imread(RUN/'output/baseline.tiff');activity={}
 for arm in ['candidate','late']:
  actual=tifffile.imread(RUN/'output'/ (arm+'.tiff'));assert actual.shape==baseline.shape
  count=0;outside=0;bbox=[baseline.shape[1],baseline.shape[0],-1,-1];canonical={}
  for y in range(0,baseline.shape[0],256):
   change=np.any(actual[y:y+256]!=baseline[y:y+256],axis=2)
   yy,xx=np.nonzero(change);count+=len(xx)
   if len(xx):bbox=[min(bbox[0],int(xx.min())),min(bbox[1],int(yy.min()+y)),max(bbox[2],int(xx.max())),max(bbox[3],int(yy.max()+y))]
   if len(xx):
    gy=yy+y;inside=np.zeros(len(xx),dtype=bool)
    for a,b in SEGMENTS:
     vx=b[0]-a[0];vy=b[1]-a[1];norm=vx*vx+vy*vy;t=np.clip(((xx-a[0])*vx+(gy-a[1])*vy)/norm,0,1) if norm else 0
     inside|=np.hypot(xx-a[0]-t*vx,gy-a[1]-t*vy)<=24
    outside+=int((~inside).sum())
  for r in regions:
   x,y,w,h=r['xywh'];canonical[r['name']]=int(np.any(actual[y:y+h,x:x+w]!=baseline[y:y+h,x:x+w],axis=2).sum())
  activity[arm]=dict(changed_rgb16_pixels=count,outside_native_radius24_footprints=outside,changed_bbox_inclusive=bbox,canonical_changed_rgb16_pixels=canonical)
 save(OUT/'receipt.json',dict(inputs=inputs,helper=bind(Path(__file__)),canonical_regions=bind(REGIONS),helicon_registration=bind(HREC),photo_receipt=bind(VIEWS/'coordinate-receipt.json'),rows=rows,activity=activity,
     geometry_overlay='Yellow radius16, magenta radius24 on baseline only; no outline on comparison boards.',
     meaning='Activity counts show intervention support, not noise or quality. Gaussian expansion legitimately extends outside native mask. Canonical regions preserved; three independent centred boundary/detail views added.',
     scope='No originals or new merge. Common sRGB profile, no tone adjustment. Zoom uses nearest replication; Helicon native scale mismatch retained.'))
 print(json.dumps(activity,indent=2))
if __name__=='__main__':main()
