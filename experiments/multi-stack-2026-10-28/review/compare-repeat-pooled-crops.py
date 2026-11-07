import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(r'C:\Users\chris\.codex\worktrees\multi-stack\strehl')
review=root/'experiments/multi-stack-2026-10-28/review'
roi=json.loads((review/'roi-mapped-frozen.json').read_text())
rows=[]
for p in roi['rois']:
    name=p['name']
    paths=[review/'native-crops'/arm/(name+'.png') for arm in ['insect-repeat-4','insect-pooled-4']]
    a,b=[np.asarray(Image.open(p)).astype(np.int16) for p in paths]
    d=np.abs(a-b)
    rows.append({'name':name,'different_rgb8_channels':int(np.count_nonzero(d)),'max_abs_rgb8_code_difference':int(d.max()),'mean_abs_rgb8_code_difference':float(d.mean())})
reports={}
for arm in ['insect-repeat-4','insect-pooled-4']:
    r=json.loads((root/'outputs/multi-stack'/arm/'render-report.json').read_text())
    reports[arm]={k:r[k] for k in ['groups','mode','primary_pass','canvas','diagnostics']}
    reports[arm]['frames']=len(r['frames'])
    reports[arm]['proposed_groups']=len(r['proposed_groups'])
out={'qualification':'Same verified warpmap/canvas and display. Code deltas describe differences, not photographic quality or temporal noise. Only nine frozen native crops measured here.','rows':rows,'render_report_summary':reports}
(review/'repeat-versus-pooled-crop-differences.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'rows':rows,'render_report_summary':reports},indent=2))
