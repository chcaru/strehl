"""Whole previews plus exact native tiles for frozen photograph comparisons."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stack', choices=('marigold-4','ore-100','garnet-104'), required=True)
    p.add_argument('--image', action='append', required=True, help='arm=absolute TIFF path')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    if a.stack == 'marigold-4':
        target_file = HERE/'marigold/highlight-targets.json'
        targets = json.loads(target_file.read_text())['targets']
    else:
        target_file = HERE/'minerals/native-tiles.json'
        capture = '100-' if a.stack == 'ore-100' else '104-'
        targets = [dict(name=Path(r['path']).stem,
                        output_native_xywh=r['output_native_xywh'])
                   for r in json.loads(target_file.read_text())
                   if Path(r['path']).name.startswith(capture)]
    assert targets and all(r['output_native_xywh'][2:]==[384,384] for r in targets)
    out.mkdir()
    rows = []
    icc_hashes = set()
    shape = None
    names = set()
    for entry in a.image:
        name, path = entry.split('=',1)
        assert name and all(c.isalnum() or c=='-' for c in name) and name not in names
        names.add(name)
        source = Path(path).resolve()
        with tifffile.TiffFile(source) as f:
            assert len(f.pages)==1
            pixels = f.asarray()
            icc = bytes(f.pages[0].tags[34675].value)
        assert pixels.dtype==np.uint16 and pixels.ndim==3 and pixels.shape[2]==3
        if shape is None: shape=pixels.shape
        assert shape==pixels.shape
        icc_hashes.add(hashlib.sha256(icc).hexdigest())
        image = Image.fromarray(((pixels.astype(np.uint32)+128)//257).astype(np.uint8))
        del pixels
        views=[]
        for r in targets:
            x,y,w,h = r['output_native_xywh']
            assert 0<=x and 0<=y and x+w<=image.width and y+h<=image.height
            tile = out/(name+'-'+r['name']+'.png')
            image.crop((x,y,x+w,y+h)).save(tile,icc_profile=icc)
            views.append(dict(target=r['name'], rect=[x,y,w,h], path=str(tile), sha256=sha(tile)))
        image.thumbnail((1617,1617),Image.Resampling.LANCZOS)
        overview = out/(name+'-whole.jpg')
        image.save(overview,quality=98,subsampling=0,icc_profile=icc)
        rows.append(dict(arm=name, master=str(source), master_sha256=sha(source),
                         complete_overview=str(overview), overview_sha256=sha(overview), tiles=views))
    assert len(icc_hashes)==1
    (out/'receipt.json').write_text(json.dumps(dict(stack=a.stack,target_file=str(target_file),
        target_sha256=sha(target_file),native_shape=shape,icc_sha256=next(iter(icc_hashes)),
        display='rounded RGB16/257, same original ICC; native tiles unresampled; whole JPEG98 orientation only',
        images=rows),indent=2)+'\n')
    print(json.dumps(dict(out=str(out), arms=len(rows), native_tiles=len(rows)*len(targets))))

if __name__=='__main__': main()
