import json,hashlib
from pathlib import Path
r=Path(r'C:\Users\chris\.codex\worktrees\multi-stack\strehl')
def read(label):
 p=r/'outputs/multi-stack'/label
 a=json.loads((p/'alignment.json').read_text()); d=json.loads((p/'render-report.json').read_text())
 lines=[s for s in a['warpmap'].splitlines() if s.startswith(('plane ','reference ','resampler ')) or (s.split() and s.split()[0].isdigit())]
 return a,d,lines
base,br,bl=read('insect-repeat-4')
rows=[]
for label in ['insect-only-107-4','insect-primary-6']:
 a,d,lines=read(label)
 rows.append({'label':label,'warp_rows_exact':lines==bl,'raw_warp_text_equal':a['warpmap']==base['warpmap'],'canvas_equal':d['canvas']==br['canvas'],'canvas':d['canvas'],'reference_frame':a['report']['reference_frame'],'reference_pass':a['report']['reference_pass'],'primary_pass':d['primary_pass'],'sources':len(d['frames']),'groups':d['groups'],'completed':json.loads((r/'outputs/multi-stack'/label/'completed.json').read_text())})
print(json.dumps(rows,indent=2))
(r/'experiments/multi-stack-2026-10-28/review/primary-insect-geometry-check.json').write_text(json.dumps(rows,indent=2)+'\n')
