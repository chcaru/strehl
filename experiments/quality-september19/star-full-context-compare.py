"""Prepared native full-star pair comparison; no image-quality scalar."""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np
from PIL import Image
import tifffile

HERE = Path(__file__).resolve().parent/'star-full-context-placement'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=HERE/'baseline-1/output/replay.tiff')
    parser.add_argument('--candidate',type=Path,default=HERE/'candidate-1/output/replay.tiff')
    parser.add_argument('--out',type=Path,default=HERE/'comparison-1')
    args=parser.parse_args()
    frozen=json.loads((HERE/'frozen-comparison.json').read_text())
    regions=frozen['output_native_regions']
    args.out.mkdir(exist_ok=False)
    images={}
    inputs={}
    for arm,path in (('baseline',args.baseline),('candidate',args.candidate)):
        image=tifffile.imread(path)
        assert list(image.shape)==frozen['output_shape'] and image.dtype==np.uint16
        images[arm]=image
        inputs[arm]=dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        for name,(x,y,w,h) in regions.items():
            crop=image[y:y+h,x:x+w]
            assert crop.shape==(h,w,3) and max(w,h)<=392
            tifffile.imwrite(args.out/f'{name}-{arm}.tiff',crop,photometric='rgb')
            Image.fromarray(((crop.astype(np.uint32)+128)//257).astype(np.uint8)).save(args.out/f'{name}-{arm}.png')
    changed=np.any(images['baseline']!=images['candidate'],axis=2)
    yy,xx=np.nonzero(changed)
    stats={}
    for name,(x,y,w,h) in regions.items():
        a=images['baseline'][y:y+h,x:x+w]
        b=images['candidate'][y:y+h,x:x+w]
        stats[name]=dict(changed_pixels=int(np.any(a!=b,axis=2).sum()),pixels=w*h,
                         max_abs_16bit=int(np.abs(a.astype(np.int32)-b.astype(np.int32)).max()))
    result=dict(images=inputs,frozen=frozen,changed_pixels=int(changed.sum()),
                changed_bbox_xyxy=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())] if xx.size else None,
                region_changes=stats,far_control_pixel_identical=stats['far-control']['changed_pixels']==0,
                interpretation='Change counts measure intervention liveness/locality, not photographic quality or noise. Native PNGs round identical RGB16 development without resizing.')
    (args.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
