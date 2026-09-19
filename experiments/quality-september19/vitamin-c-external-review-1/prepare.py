"""Coordinate-only feature fit; native crops are never resampled."""
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np
import tifffile
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
REGIONS=PARENT/'vitamin-c-review-1/regions.json'
BASE=PARENT/'vitamin-c-baseline-1/vitamin-c.tiff'
FORK=PARENT/'vitamin-c-fork-40g-1/fork.tiff'

def binding(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(1<<20): h.update(b)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=h.hexdigest())

def save(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')

def main():
    start=time.perf_counter(); cv2.setNumThreads(2); cv2.setRNGSeed(19092026)
    regions=json.loads(REGIONS.read_text())['regions']
    assert len(regions)==5
    base=tifffile.imread(BASE);fork=tifffile.imread(FORK)
    assert base.dtype==fork.dtype==np.uint16
    assert base.shape==(4612,6920,3) and fork.shape==(4626,6958,3)
    display=lambda a:((a.astype(np.uint32)+128)//257).astype(np.uint8)
    # Feature matching sees quarter-size luma only. It nominates corresponding
    # crop centres; it has no role in development, image repair or quality scoring.
    shrink=4
    grey=[]
    for source in (base,fork):
        small=cv2.resize(source,(source.shape[1]//shrink,source.shape[0]//shrink),interpolation=cv2.INTER_AREA)
        grey.append(cv2.cvtColor(display(small),cv2.COLOR_RGB2GRAY))
    sift=cv2.SIFT_create(nfeatures=5000)
    k0,d0=sift.detectAndCompute(grey[0],None);k1,d1=sift.detectAndCompute(grey[1],None)
    pairs=cv2.BFMatcher().knnMatch(d0,d1,k=2)
    matches=[a for a,b in pairs if a.distance<.70*b.distance]
    # Scaling uses each actual thumbnail extent, preserving sensor pixel centres.
    def native(k,shape,smallshape):
        return (np.asarray(k,dtype=np.float64)+.5)*np.array([shape[1]/smallshape[1],shape[0]/smallshape[0]])-.5
    p0=native([k0[m.queryIdx].pt for m in matches],base.shape,grey[0].shape)
    p1=native([k1[m.trainIdx].pt for m in matches],fork.shape,grey[1].shape)
    assert len(matches)>=50,'insufficient correspondence; cannot assign diagnostic crops'
    matrix,inlier=cv2.estimateAffinePartial2D(p0,p1,method=cv2.RANSAC,ransacReprojThreshold=4.0,maxIters=3000,confidence=.999,refineIters=10)
    assert matrix is not None
    inlier=inlier[:,0].astype(bool)
    predicted=p0@matrix[:,:2].T+matrix[:,2]
    residual=np.linalg.norm(predicted-p1,axis=1)
    scale=float(np.hypot(matrix[0,0],matrix[1,0]));angle=float(np.degrees(np.arctan2(matrix[1,0],matrix[0,0])))
    assert inlier.sum()>=50 and .98<scale<1.02 and abs(angle)<1
    assert np.median(residual[inlier])<2.5,'coordinate fit too imprecise for native views'
    records=[]
    for r in regions:
        x,y,w,h=r['xywh']; assert(w,h)==(384,384)
        centre=np.array([x+(w-1)/2,y+(h-1)/2])
        mapped=matrix[:,:2]@centre+matrix[:,2]
        cx,cy=np.rint(mapped-np.array([(w-1)/2,(h-1)/2])).astype(int)
        assert 0<=cx<=fork.shape[1]-w and 0<=cy<=fork.shape[0]-h
        for label,source,xx,yy in [('baseline',base,x,y),('fork',fork,cx,cy)]:
            patch=display(source[yy:yy+h,xx:xx+w])
            assert patch.shape==(384,384,3)
            image=Image.fromarray(patch);image.save(HERE/f"{r['name']}-{label}.png")
            if label=='baseline':
                frozen=np.asarray(Image.open(PARENT/'vitamin-c-review-1'/f"{r['name']}.png"))
                assert np.array_equal(patch,frozen),'baseline crop differs from frozen root view'
        records.append(dict(name=r['name'],baseline_xywh=[x,y,w,h],fork_xywh=[int(cx),int(cy),w,h],
                            mapped_centre_native=mapped.tolist(),subpixel_rounding=(np.array([cx+(w-1)/2,cy+(h-1)/2])-mapped).tolist()))
    for label,source in [('baseline',base),('fork',fork)]:
        image=Image.fromarray(display(source));image.thumbnail((1560,1100),Image.Resampling.LANCZOS)
        draw=ImageDraw.Draw(image);sx=image.width/source.shape[1];sy=image.height/source.shape[0]
        for row in records:
            x,y,w,h=row[label+'_xywh'];box=[x*sx,y*sy,(x+w)*sx,(y+h)*sy]
            draw.rectangle(box,outline='yellow',width=2);draw.text((box[0],max(0,box[1]-13)),row['name'],fill='yellow')
        image.save(HERE/f'{label}-orientation.jpg',quality=95)
    save(HERE/'receipt.json',dict(inputs=[binding(BASE),binding(FORK)],frozen_regions=binding(REGIONS),helper=binding(Path(__file__)),
         feature_method='quarter-size SIFT n5000 ratio0.70 + similarity RANSAC native reprojection4; coordinates only',
         feature_counts=[len(k0),len(k1)],ratio_matches=len(matches),inliers=int(inlier.sum()),
         baseline_to_fork_native_matrix=matrix.tolist(),scale=scale,angle_degrees=angle,
         coordinate_residual_native=dict(median=float(np.median(residual[inlier])),p95=float(np.percentile(residual[inlier],95)),
             interpretation='fit consistency only, not alignment truth or image quality'),
         falsifier='unrelated or severely distorted images fail correspondence/inlier/scale/rotation/residual checks',
         regions=records,display='rounded division by257; 384x384 native unresampled crops; integer crop-centre shifts only',
         orientation='whole-field resized images with ROI overlays; no quality inference from these',
         limitations='independent output geometry may differ locally; fixed-size crops preserve native samples rather than conceal scale/shape differences',
         wall_seconds=time.perf_counter()-start))
    print(json.dumps(dict(status='NATIVE_CROPS_WRITTEN',inliers=int(inlier.sum()),scale=scale,angle_degrees=angle,
          coordinate_residual_median_native=float(np.median(residual[inlier])),regions=records)),flush=True)

if __name__=='__main__':main()
