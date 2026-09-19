"""Independent full-image location check for saved merged observer patches."""
from pathlib import Path
import hashlib
import json

import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent/'star-matched-source-1'
BASELINE=HERE.parent/'star-full-context-placement/baseline-1/output/replay.tiff'
receipt=json.loads((HERE/'output/receipt.json').read_text())
full=tifffile.imread(BASELINE)
assert full.shape==(4480,6724,3) and full.dtype==np.uint16
checks=[]
for record in receipt['patches']:
    if record['stage']!='merged':
        continue
    image=tifffile.imread(HERE/'output'/(record['stem']+'.tiff'))
    assert image.shape==(336,336,3) and image.dtype==np.uint16
    assert record['trim']==4 and record['reference_output_xywh']==[472,1352,328,328]
    # These are frozen output coordinates, read independently of the captured
    # padded-origin field. Compare native RGB16 before any PNG conversion.
    target=full[1352:1680,472:800]
    observed=image[4:332,4:332]
    differences=int(np.count_nonzero(observed!=target))
    # Wrong-location placebo must be detectably wrong; otherwise this region
    # has no power to verify registration of the saved patch.
    wrong=full[1352:1680,474:802]
    wrong_differences=int(np.count_nonzero(observed!=wrong))
    assert wrong_differences>0, 'Location placebo has no power'
    # A second defensible interior changes the boundary choice, rather than
    # merely re-running one comparison at the observer author\'s exact trim.
    inner_differences=int(np.count_nonzero(image[20:316,20:316]!=full[1368:1664,488:784]))
    checks.append(dict(frame=record['frame'],stem=record['stem'],different_rgb16_samples=differences,
                       independently_trimmed_inner_differences=inner_differences,
                       wrong_x_plus_two_different_samples=wrong_differences,
                       pixel_sha256=hashlib.sha256(observed.tobytes()).hexdigest()))
    assert differences==inner_differences==0, 'Merged observer patch does not equal full baseline'
assert [r['frame'] for r in checks]==[125,129,133]
result=dict(status='MERGED_PATCH_LOCATION_VERIFIED',checks=checks,
            baseline_file_sha256=hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
            note='All three merged captures are the same output field, not independent photographic replicates',
            scope='Independent actual RGB16 full-image lookup, alternate inner trim, and wrong-location placebo; no RAW decode')
(HERE/'merged-patch-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
