"""Complete fixed-tone outputs plus frozen native inspection regions."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import struct
import sys
import numpy as np
import tifffile
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def ref(p):
    with p.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--off',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    out=a.out.resolve()
    assert out.is_relative_to(HERE)
    frozen=ROOT/'experiments/quality-september19/vitamin-c-review-1/regions.json'
    regions=json.loads(frozen.read_text())['regions']
    runs=dict(baseline=a.off.resolve(),candidate=a.candidate.resolve())
    receipts={k:json.loads((v/'completion.json').read_text()) for k,v in runs.items()}
    assert receipts['baseline']['disabled_rgb16_bit_exact']
    sources={k:Path(v['image']['path']) for k,v in receipts.items()}
    for k,path in sources.items():
        assert ref(path)==receipts[k]['image']
        actual=json.loads((runs[k]/'output/receipt.json').read_text())
        assert actual['source_frame_count']==70 and actual['crop_quad_xywh']==[28,19,3460,2306]
        assert actual['tone_bits']==[struct.unpack('<I',struct.pack('<f',v))[0] for v in [.090420,.914606,.55]]
    out.mkdir()
    outputs=[]
    helper=ROOT/'experiments/quality-september19/full-output-views.py'
    for arm,path in sources.items():
        with tifffile.TiffFile(path) as tf:
            pixels=tf.asarray()
            assert pixels.shape==(4612,6920,3) and pixels.dtype==np.uint16
            tag=tf.pages[0].tags.get(34675)
            opts={'icc_profile':tag.value} if tag else {}
        for r in regions:
            x,y,w,h=r['xywh']
            assert w==h==384
            patch=((pixels[y:y+h,x:x+w].astype(np.uint32)+128)//257).astype(np.uint8)
            png=out/f"{r['name']}-{arm}.png"
            Image.fromarray(patch).save(png,**opts)
            with Image.open(png) as check: assert np.array_equal(np.asarray(check),patch)
            outputs.append(ref(png))
        del pixels
        command=[sys.executable,'-I','-B',str(helper),str(path),str(out/(arm+'.png'))]
        result=subprocess.run(command,capture_output=True,text=True,timeout=90)
        (out/(arm+'-conversion.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        assert result.returncode==0,result.stderr
        with Image.open(out/(arm+'.png')) as full:
            assert full.size==(6920,4612)
            overview=full.copy()
        overview.thumbnail((1560,1100),Image.Resampling.LANCZOS)
        overview.save(out/(arm+'-overview.jpg'),quality=95,**opts)
        outputs.extend([ref(out/(arm+'.png')),ref(out/(arm+'-overview.jpg'))])
    (out/'receipt.json').write_text(json.dumps(dict(
        sources={k:ref(v) for k,v in sources.items()},regions=regions,frozen_regions=ref(frozen),
        helper=ref(Path(__file__)),full_conversion_helper=ref(helper),outputs=outputs,
        dimensions=[6920,4612],scope='Whole PNGs preserve every output pixel; native crops384x384, rounded division257, ICC retained. Overview resized for orientation only. No quality metric.'),indent=2)+'\n')
    print('Complete paired views retained:',out)

if __name__=='__main__': main()
