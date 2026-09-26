"""Exhaustive saved RGB16 reference comparison; no RAW reads or image writes."""
from pathlib import Path
import hashlib
import json

import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'parallel-cfa-wavelet/full-1/output/baseline.tiff'
NEW=HERE/'full-cost-1/output/baseline-historical-tone.tiff'


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle,'sha256').hexdigest()


def main():
    images=[]; bindings=[]; profiles=[]
    for path in (OLD,NEW):
        with tifffile.TiffFile(path) as tf:
            assert len(tf.pages)==1
            page=tf.pages[0]
            assert page.shape==(4612,6920,3) and page.dtype==np.uint16
            assert int(page.photometric)==2
            profiles.append(bytes(page.tags[34675].value))
            images.append(page.asarray())
        bindings.append({'path':str(path),'file_sha256':sha(path),'bytes':path.stat().st_size})
    old,new=images
    pixel_hash=[hashlib.sha256(),hashlib.sha256()]
    display_hash=[hashlib.sha256(),hashlib.sha256()]
    differences=[]; changed=0; maximum=0; display_changed=0
    # Every channel in every row, independently partitioned into257-row blocks.
    for y in range(0,len(old),257):
        a,b=old[y:y+257],new[y:y+257]
        delta=b.astype(np.int32)-a.astype(np.int32)
        yy,xx,cc=np.nonzero(delta)
        changed+=len(yy); maximum=max(maximum,int(np.max(np.abs(delta))))
        differences.extend({'y':int(y+i),'x':int(j),'channel':int(k),
                            'prior':int(a[i,j,k]),'current':int(b[i,j,k])}
                           for i,j,k in zip(yy,xx,cc))
        a8=((a.astype(np.uint32)+128)//257).astype(np.uint8)
        b8=((b.astype(np.uint32)+128)//257).astype(np.uint8)
        display_changed+=int(np.count_nonzero(a8!=b8))
        for i,(v,v8) in enumerate(((a,a8),(b,b8))):
            pixel_hash[i].update(v.astype('<u2',copy=False).tobytes())
            display_hash[i].update(v8.tobytes())
    for i,binding in enumerate(bindings):
        binding.update(rgb16_le_sha256=pixel_hash[i].hexdigest(),rgb8_sha256=display_hash[i].hexdigest())
    result={'schema':1,'scope':'All saved RGB16 channels, not a selected ROI; no RAW or candidate read.',
        'shape':list(old.shape),'channel_samples':int(old.size),'changed_channel_samples':changed,
        'maximum_absolute_code_difference':maximum,'differences':differences,
        'rgb8_changed_samples':display_changed,'icc_exact':profiles[0]==profiles[1],
        'icc_sha256':hashlib.sha256(profiles[0]).hexdigest(),'bindings':bindings,
        'script_sha256':sha(Path(__file__))}
    expected=json.loads((HERE/'full-cost-1/baseline-discrepancy.json').read_text())
    assert differences==expected['differences'] and changed==expected['changed_channel_samples']==4
    assert maximum==1 and display_changed==0 and profiles[0]==profiles[1]
    with (HERE/'baseline-reference-check.json').open('x',encoding='utf-8') as handle:
        json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(result))


if __name__=='__main__':
    main()
