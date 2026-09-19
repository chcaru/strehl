"""Fixed native views and exact change support; no sharpness acceptance score."""
from pathlib import Path
import hashlib, json
import numpy as np
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "comparison-1"
OUT.mkdir()
regions = {
    "core": [1098, 958, 328, 328],
    "left-transition": [1020, 958, 128, 328],
    "right-transition": [1376, 958, 128, 328],
    "top-transition": [1098, 882, 328, 128],
    "bottom-transition": [1098, 1236, 328, 128],
    "far-control": [3500, 2500, 328, 328],
}
records = {}
images = {}
for arm in ("baseline", "candidate"):
    path = HERE / (arm + "-1/output/replay.tiff")
    images[arm] = tifffile.imread(path)
    assert images[arm].shape == (4332, 6500, 3)
    assert images[arm].dtype == np.uint16
    records[arm] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    for name, (x, y, w, h) in regions.items():
        crop = images[arm][y:y+h, x:x+w]
        Image.fromarray(((crop.astype(np.uint32)+128)//257).astype(np.uint8)).save(OUT / f"{name}-{arm}.png")
        tifffile.imwrite(OUT / f"{name}-{arm}.tiff", crop, photometric="rgb")
changed = np.any(images["baseline"] != images["candidate"], axis=2)
yy, xx = np.nonzero(changed)
per_region = {}
for name, (x,y,w,h) in regions.items():
    a = images["baseline"][y:y+h,x:x+w]
    z = images["candidate"][y:y+h,x:x+w]
    per_region[name] = dict(changed_pixels=int(np.any(a != z, axis=2).sum()), pixels=w*h,
                           max_abs_16bit=int(np.abs(a.astype(np.int32)-z).max()))
receipt = dict(images=records, output_native_regions=regions, input_sensor_origin=[266,178],
    changed_pixels=int(changed.sum()), changed_bbox_xyxy=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())] if xx.size else None,
    region_changes=per_region, interpretation="Changes measure intervention liveness, never photographic quality. All PNGs are native crops rounded from the same 16-bit sRGB development; no resizing.")
(OUT / "receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt,indent=2))
