"""Existing-output coordinate matching and native views; no RAW or merge."""
from pathlib import Path
import hashlib, io, json, math
import cv2
import numpy as np
import tifffile
from PIL import Image, ImageCms, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=HERE/'photo-comparison-1'
FROZEN=ROOT/'experiments/quality-september19/vitamin-c-review-1/regions.json'
PATHS={
 'baseline':ROOT/'experiments/green-match-rgb/full-2/photo-comparison-1/baseline.png',
 'green-match':ROOT/'experiments/green-match-rgb/full-2/photo-comparison-1/candidate.png',
 'helicon-b':HERE/'vitamin-c-b-2/whole-stack.tiff',
 'helicon-c':HERE/'vitamin-c-c-2/whole-stack.tiff',
 'fork':ROOT/'experiments/quality-september19/vitamin-c-fork-40g-1/fork.tiff',
}
LABELS={'baseline':'Strehl baseline','green-match':'Strehl green-match','helicon-b':'Helicon B R8 S4','helicon-c':'Helicon C S4','fork':'Fork (untagged; sRGB requested)'}

def binding(path):
 with path.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest()
 return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha)

def save(path,value):
 with path.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2);f.write('\n')

def read(path):
 if path.suffix=='.png':
  with Image.open(path) as im: a=np.asarray(im.convert('RGB'));icc=im.info.get('icc_profile')
 else:
  with tifffile.TiffFile(path) as tf:
   raw=tf.asarray();assert raw.dtype==np.uint16 and raw.ndim==3 and raw.shape[2]==3
   tag=tf.pages[0].tags.get(34675);icc=tag.value if tag else None
  a=((raw.astype(np.uint32)+128)//257).astype(np.uint8)
 return a,icc

def features(a):
 small=cv2.resize(a,None,fx=.25,fy=.25,interpolation=cv2.INTER_AREA)
 gray=cv2.cvtColor(small,cv2.COLOR_RGB2GRAY)
 points,desc=cv2.SIFT_create(nfeatures=5000).detectAndCompute(gray,None)
 return small,points,desc

def distribution(a):
 return dict(n=len(a),median=float(np.median(a)),p90=float(np.percentile(a,90)),
             p95=float(np.percentile(a,95)),max=float(np.max(a))) if len(a) else None

def registration(ref_features,other_features):
 _,kr,dr=ref_features;_,ko,do=other_features
 matches=cv2.BFMatcher().knnMatch(dr,do,k=2)
 good=[m for m,n in matches if m.distance<.70*n.distance]
 src=np.asarray([kr[m.queryIdx].pt for m in good],dtype=np.float64)*4
 dst=np.asarray([ko[m.trainIdx].pt for m in good],dtype=np.float64)*4
 assert len(src)>100
 # Disjoint spatial cells, fixed before seeing residuals. Held-out coordinates
 # never enter the RANSAC fit; all of their residuals are reported.
 train=((np.floor(src[:,0]/384)+np.floor(src[:,1]/384)).astype(int)%2)==0
 assert train.sum()>50 and (~train).sum()>50
 cv2.setRNGSeed(20260919)
 matrix,inliers=cv2.estimateAffinePartial2D(src[train],dst[train],method=cv2.RANSAC,
    ransacReprojThreshold=4.0,maxIters=10000,confidence=.999,refineIters=10)
 assert matrix is not None and int(inliers.sum())>100
 predicted=src@matrix[:,:2].T+matrix[:,2]
 residual=np.linalg.norm(predicted-dst,axis=1)
 scale=float(math.hypot(matrix[0,0],matrix[1,0]));angle=float(math.degrees(math.atan2(matrix[1,0],matrix[0,0])))
 held=residual[~train]
 assert .9<scale<1.1 and abs(angle)<3
 assert np.median(held)<3 and np.percentile(held,90)<12 and np.mean(held<8)>.75
 evidence=dict(matrix_baseline_to_output=matrix.tolist(),scale=scale,angle_degrees=angle,
    ratio_matches=len(good),training_matches=int(train.sum()),training_inliers=int(inliers.sum()),
    training_residual_all=distribution(residual[train]),heldout_residual_all=distribution(held),
    heldout_fraction_within2=float(np.mean(held<2)),heldout_fraction_within4=float(np.mean(held<4)),
    heldout_fraction_within8=float(np.mean(held<8)),
    heldout_definition='odd checkerboard cells of384native; no held-out match used in fit',
    interpretation='coordinate correspondence only; not placement truth or image quality')
 return matrix,evidence,src,dst,residual,train

def main():
 OUT.mkdir();cv2.setNumThreads(4)
 regions=json.loads(FROZEN.read_text())['regions']
 arrays={};profiles={};inputs={};outputs=[]
 for name,path in PATHS.items():
  arrays[name],profiles[name]=read(path);inputs[name]=binding(path)
  icc=profiles[name]
  inputs[name].update(shape=list(arrays[name].shape),icc_bytes=len(icc) if icc else 0,
    icc_sha256=hashlib.sha256(icc).hexdigest() if icc else None,
    icc_description=ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip() if icc else None)
 assert inputs['fork']['sha256']=='7b83629a998ba543026bb7cce66beaf72c996a77dd9568cae4b5b0c63071c3b9'
 assert profiles['baseline'] and all(profiles[k]==profiles['baseline'] for k in ['green-match','helicon-b','helicon-c'])
 basefeatures=features(arrays['baseline']);registrations={};matches={}
 matrices={'baseline':np.array([[1.,0.,0.],[0.,1.,0.]]),'green-match':np.array([[1.,0.,0.],[0.,1.,0.]])}
 assert arrays['baseline'].shape==arrays['green-match'].shape
 for name in ['helicon-b','helicon-c','fork']:
  targetfeatures=features(arrays[name]);m,ev,src,dst,residual,train=registration(basefeatures,targetfeatures)
  matrices[name]=m;registrations[name]=ev;matches[name]=(src,dst,residual,train)
  save(OUT/(name+'-landmarks.json'),dict(source_xy=src.tolist(),target_xy=dst.tolist(),training=train.tolist(),residual_native=residual.tolist()))
  # A small distributed held-out sample supports direct human correspondence inspection.
  indices=np.flatnonzero((~train)&(residual<4))[::max(1,int(((~train)&(residual<4)).sum())//20)][:20]
  left=Image.fromarray(basefeatures[0]);right=Image.fromarray(targetfeatures[0])
  board=Image.new('RGB',(left.width+right.width,max(left.height,right.height)),(30,30,30));board.paste(left);board.paste(right,(left.width,0));draw=ImageDraw.Draw(board)
  for j,i in enumerate(indices):
   p=tuple(src[i]/4);q=tuple(dst[i]/4+np.array([left.width,0]));colour=(255,255,0)
   for point in [p,q]:draw.ellipse((point[0]-5,point[1]-5,point[0]+5,point[1]+5),outline=colour,width=2);draw.text((point[0]+6,point[1]),str(j),fill=colour)
  board.save(OUT/(name+'-heldout-landmarks.jpg'),quality=95)
  print(name,json.dumps(ev),flush=True)
 try: font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
 except OSError: font=ImageFont.load_default()
 mapped=[]
 for region in regions:
  x,y,w,h=region['xywh'];centre=np.array([x+(w-1)/2,y+(h-1)/2]);row=dict(name=region['name'],baseline_xywh=region['xywh'],arms={})
  board=Image.new('RGB',(3*400,2*428+42),(235,235,235));draw=ImageDraw.Draw(board)
  draw.text((10,8),region['name']+' | native samples; fork ICC absent (sRGB requested)',fill=(0,0,0),font=font)
  for k,(name,a) in enumerate(arrays.items()):
   m=matrices[name];point=m[:,:2]@centre+m[:,2];origin=np.rint(point-np.array([(w-1)/2,(h-1)/2])).astype(int)
   xx,yy=map(int,origin);patch=a[yy:yy+h,xx:xx+w];assert patch.shape==(384,384,3)
   info=dict(xywh=[xx,yy,w,h],mapped_centre=point.tolist(),rounding_native=(origin+np.array([(w-1)/2,(h-1)/2])-point).tolist())
   if name in matches:
    src,dst,residual,train=matches[name];near=(np.linalg.norm(src-centre,axis=1)<700)&(~train)
    info['local_heldout_residual_all']=distribution(residual[near]);info['local_heldout_fraction_within8']=float(np.mean(residual[near]<8)) if near.any() else None
    info['local_status']='at least4 heldout structural correspondences within700native' if near.sum()>=4 else 'global mapping only; sparse local structure'
   row['arms'][name]=info
   im=Image.fromarray(patch);kw={'icc_profile':profiles[name]} if profiles[name] else {}
   path=OUT/(region['name']+'-'+name+'.png');im.save(path,**kw)
   with Image.open(path) as check:assert np.array_equal(np.asarray(check),patch)
   outputs.append(binding(path));bx=(k%3)*400+8;by=(k//3)*428+42
   draw.text((bx,by),LABELS[name],font=font,fill=(0,0,0));board.paste(im,(bx,by+28))
  # Known profiles are identical. The fifth panel has only CLI sRGB provenance;
  # it is displayed as sRGB on this board, explicitly labelled above.
  boardpath=OUT/(region['name']+'-board.png');board.save(boardpath,icc_profile=profiles['baseline']);outputs.append(binding(boardpath));mapped.append(row)
 save(OUT/'coordinate-receipt.json',dict(schema=1,inputs=inputs,helper=binding(Path(__file__)),frozen_regions=binding(FROZEN),registrations=registrations,
    regions=mapped,outputs=outputs,known_profile_equality=True,fork_profile='Absent; existing invocation requests output-colorspace=srgb. Individual fork crops remain untagged; boards display code values in shared sRGB with explicit label.',
    registration='quarter-size SIFT5000, ratio.70; spatially disjoint training/heldout384native cells; similarity RANSAC4native. No crop resampling.',
    green_match_identity='same completed paired renderer geometry and coordinate receipt; no fit needed',
    display='PNG sources unchanged RGB8; TIFF sources rounded (u16+128)//257. 384native crops centered via similarity, no scaling/rotation/resampling. Scale mismatch retained.',
    scope='Existing workspace outputs only; no RAW, new merge, sharpness score or product ranking.'))
 print('READY',OUT,flush=True)

if __name__=='__main__':main()
