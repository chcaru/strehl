import json,hashlib
from pathlib import Path
root=Path(r'C:\Users\chris\.codex\worktrees\multi-stack\strehl'); review=root/'experiments/multi-stack-2026-10-28/review'
labels=['insect-repeat-4','insect-pooled-4','insect-only-106-4','insect-only-107-4','insect-primary-6']
reports={label:json.loads((root/'outputs/multi-stack'/label/'render-report.json').read_text()) for label in labels}
ref=reports['insect-repeat-4']; byid={f['frame']:f for f in ref['frames']}
fields=['luma_beta','color_beta','beta_samples','beta_realizations','photometric_gain','covered_pixels','clipped_pixels','path','pass']
rows=[]
for label in labels:
 r=reports[label]; c=json.loads((root/'outputs/multi-stack'/label/'calibration.json').read_text())
 display=(review/'full-displays'/label) if label in ['insect-only-107-4','insect-primary-6'] else root/'outputs/multi-stack/independent-review'/label
 readback=json.loads((display/'readback.json').read_text())
 mismatches=[{'frame':f['frame'],'fields':[k for k in fields if f[k]!=byid[f['frame']][k]]} for f in r['frames'] if any(f[k]!=byid[f['frame']][k] for k in fields)]
 rows.append({'label':label,'source_count':len(r['frames']),'groups':r['groups'],'primary':r['primary_pass'],'layer_pass':r['layer_pass'],'canvas':r['canvas'],'operator_and_support_matches_repeat':not mismatches,'mismatches':mismatches,'calibration_wb_equal_between_passes':c[0]['white_balance']==c[1]['white_balance'],'recipe_equal_to_repeat':r['recipe']==ref['recipe'],'recipe':r['recipe'],'master_sha256':readback['master']['file_sha256'],'complete_display_sha256':readback['complete_display_sha256'],'display_transform_sha256':readback['transform_file_sha256'],'crop_receipt_sha256':hashlib.sha256((review/'native-crops'/label/'receipt.json').read_bytes()).hexdigest()})
(review/'insect-five-arm-review-binding.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows: print(json.dumps({k:v for k,v in row.items() if k not in ['recipe','mismatches']}))
print('Recipe keys:',list(ref['recipe']))
