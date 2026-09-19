"""Root-fixed follow-up: inspect defocused sources without resampling."""
from pathlib import Path
import json, hashlib
import numpy as np
import tifffile
from PIL import Image
HERE=Path(__file__).resolve().parent
scan=json.loads((HERE/'scan-1/receipt.json').read_text())
out=HERE/'distant-1';out.mkdir()
records=[]
for r in scan['frames']:
    if r['index0'] not in (0,17,52,69): continue
    p=Path(r['source_tiff']);before=p.stat()
    arr=tifffile.memmap(p,mode='r');assert arr.shape==(4688,7032,3)
    x,y,w,h=r['source_native_xywh'];cut=np.asarray(arr[y:y+h,x:x+w]).copy();del arr
    assert cut.shape==(384,384,3) and cut.dtype==np.uint16
    assert hashlib.sha256(cut.tobytes()).hexdigest()==r['crop_rgb16_sha256']
    stem=f"{r['region']}-source-{r['index0']:02}-{Path(r['original_raw_name']).stem}"
    tifffile.imwrite(out/(stem+'.tiff'),cut,photometric='rgb')
    Image.fromarray(((cut.astype(np.uint32)+128)//257).astype(np.uint8)).save(out/(stem+'.png'))
    after=p.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    records.append(r|{'display_png':str((out/(stem+'.png')).resolve())})
(out/'receipt.json').write_text(json.dumps({'fixed_distant_indices0':[0,17,52,69],
    'coordinate_receipt_sha256':hashlib.sha256((HERE/'scan-1/receipt.json').read_bytes()).hexdigest(),
    'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'frames':records},indent=2)+'\n')
print(f'retained {len(records)} native crops; exact crop hashes match the initial scan')
