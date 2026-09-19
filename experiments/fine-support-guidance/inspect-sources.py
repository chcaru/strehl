"""Native inspection views for fixed pooled nominations, never a quality score."""
from pathlib import Path
import hashlib
import json
import numpy as np
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
out = HERE / 'source-review-1'
out.mkdir()
scan_path = ROOT/'experiments/quality-september19/vitamin-c-source-highlights/scan-1/receipt.json'
scan = json.loads(scan_path.read_text())
records = []
for row in scan['frames']:
    if row['index0'] not in (23,25,27,35):
        continue
    p=Path(row['source_tiff'])
    before=p.stat()
    arr=tifffile.memmap(p,mode='r')
    assert arr.shape==(4688,7032,3) and arr.dtype==np.uint16
    x,y,w,h=row['source_native_xywh']
    cut=np.asarray(arr[y:y+h,x:x+w]).copy()
    del arr
    assert cut.shape==(384,384,3)
    assert hashlib.sha256(cut.tobytes()).hexdigest()==row['crop_rgb16_sha256']
    png=out/f"{row['region']}-source-{row['index0']:02}.png"
    Image.fromarray(((cut.astype(np.uint32)+128)//257).astype(np.uint8)).save(png)
    after=p.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    records.append(row|{'png':str(png),'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest()})
for p in sorted((HERE/'measure-1/output').glob('*-gathered-*.tiff')):
    cut=tifffile.imread(p)
    assert cut.shape==(384,384,3) and cut.dtype==np.uint16
    png=out/(p.stem+'.png')
    Image.fromarray(((cut.astype(np.uint32)+128)//257).astype(np.uint8)).save(png)
    records.append({'gathered_tiff':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                    'png':str(png),'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest()})
(out/'receipt.json').write_text(json.dumps({'source_scan_sha256':hashlib.sha256(scan_path.read_bytes()).hexdigest(),
    'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'scope':'Original-source crops use the existing coordinate-only mapping. Gathered views use the actual consumer. No resize or tone change.',
    'records':records},indent=2)+'\n')
print(f'{len(records)} native 384x384 views retained')
