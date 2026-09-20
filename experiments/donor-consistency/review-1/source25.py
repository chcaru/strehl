from pathlib import Path
import json,hashlib
import numpy as np
import tifffile
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
receipt=ROOT/'experiments/quality-september19/vitamin-c-source-highlights/scan-1/receipt.json'
row=next(r for r in json.loads(receipt.read_text())['frames'] if r['index0']==25 and r['region']=='dark-inclusion')
source=Path(row['source_tiff']);x,y,w,h=row['source_native_xywh']
with tifffile.TiffFile(source) as tf:
    pixels=tf.asarray();icc=tf.pages[0].tags[34675].value
crop=pixels[y:y+h,x:x+w];assert hashlib.sha256(crop.tobytes()).hexdigest()==row['crop_rgb16_sha256']
Image.fromarray(((crop.astype(np.uint32)+128)//257).astype(np.uint8)).save(OUT/'dark-inclusion-source25.png',icc_profile=icc)
data=dict(source=str(source),crop_xywh=[x,y,w,h],retained_scan_receipt=str(receipt),crop_sha256_matches_retained=True,
    purpose='Actual retained developed source25, mapped original384native window; no resampling. No RAW read or new merge.')
(OUT/'source25-receipt.json').write_text(json.dumps(data,indent=2)+'\n')
