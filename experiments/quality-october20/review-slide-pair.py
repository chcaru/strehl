"""Complete photographs first, fixed native crops second; no sharpening metric."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
import tifffile

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"outputs/quality-october20-slide"
OUT=BASE/"review"
REGIONS={"qr-edge":(4650,400,640,640),"centre-text":(3300,1800,640,640),"grey-ramp":(2200,650,640,640)}

def main():
    OUT.mkdir(exist_ok=True)
    for label in ["baseline","repair"]:
        with tifffile.TiffFile(BASE/label/"result.tiff") as tf:
            pixels=tf.asarray()
            icc=tf.pages[0].tags.get(34675)
            options={"icc_profile":icc.value} if icc else {}
        assert pixels.dtype==np.uint16 and pixels.shape==(4688,7032,3)
        rgb8=((pixels.astype(np.uint32)+128)//257).astype(np.uint8)
        image=Image.fromarray(rgb8)
        overview=image.copy()
        overview.thumbnail((1500,1100),Image.Resampling.BOX)
        overview.save(OUT/f"{label}-whole.png",**options)
        for name,(x,y,w,h) in REGIONS.items():
            image.crop((x,y,x+w,y+h)).save(OUT/f"{label}-{name}.png",**options)
        del pixels,rgb8,image,overview
    a=tifffile.imread(BASE/"baseline/result.tiff")
    b=tifffile.imread(BASE/"repair/result.tiff")
    outside_changed=0;outside_count=0;outside_max=0;inside_changed=0;inside_max=0
    # The tiny extension allows the actual final demosaic's finite spatial support.
    x0,y0,x1,y1=4646,396,5294,1044
    for y in range(a.shape[0]):
        delta=abs(a[y].astype(np.int32)-b[y].astype(np.int32))
        outside=np.ones(a.shape[1],bool)
        if y0<=y<y1:outside[x0:x1]=False
        outside_changed+=int(np.any(delta[outside]>0,axis=1).sum())
        outside_count+=int(outside.sum())
        outside_max=max(outside_max,int(delta[outside].max()))
        if (~outside).any():
            inside_changed+=int(np.any(delta[~outside]>0,axis=1).sum())
            inside_max=max(inside_max,int(delta[~outside].max()))
    report={"geometry":[7032,4688],"fixed_regions":REGIONS,
        "exterior_rgb_pixels_changed":outside_changed,"exterior_rgb_pixels":outside_count,
        "maximum_exterior_16bit_channel_difference":outside_max,
        "region_rgb_pixels_changed":inside_changed,"maximum_region_16bit_channel_difference":inside_max,
        "meaning":"Change-locality check, not a sharpness/quality score; legacy tone placement may change after a source repair."}
    (OUT/"locality.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
