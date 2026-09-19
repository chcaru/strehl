"""Colour-tagged full-frame previews from the retained commercial TIFFs."""
from pathlib import Path
import hashlib
import json
import tifffile
from PIL import Image

HERE=Path(__file__).resolve().parent
out=HERE/'full-views'
out.mkdir()
records=[]
for method in ['b','c']:
    source=HERE/f'vitamin-c-{method}-2/whole-stack.tiff'
    with tifffile.TiffFile(source) as tif:
        page=tif.pages[0]
        icc=page.tags[34675].value
        pixels=page.asarray()
    assert hashlib.sha256(icc).hexdigest()=='238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
    image=Image.fromarray(((pixels.astype('uint32')+128)//257).astype('uint8'))
    image.save(out/f'helicon-{method}.png',icc_profile=icc)
    image.thumbnail((1800,1800),Image.Resampling.LANCZOS)
    image.save(out/f'helicon-{method}-preview.png',icc_profile=icc)
    records.append(dict(method=method,source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        dimensions=list(pixels.shape),mapping='round(u16/257); unchanged sRGB ICC; no new tone or sharpening'))
(out/'receipt.json').write_text(json.dumps(records,indent=2)+'\n')
