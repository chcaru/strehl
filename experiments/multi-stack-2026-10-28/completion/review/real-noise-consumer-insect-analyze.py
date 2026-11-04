"""Classify the complete frozen insect source-only census; no new pixels."""
from pathlib import Path
import json, collections, hashlib, argparse
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('out',type=Path);a=p.parse_args();q=json.loads((a.run/'qualification.json').read_text());rows=[];fail=collections.Counter()
criteria={'mean_dn':('gt',64.),'guide_range_p95_sigma':('le',1.),'validation_p95_sigma':('le',.65),'mean_drift_sigma':('le',.25),'guide_gradient_p95_sigma':('le',.5)}
for window in q['windows']:
 for roi in window['rois']:
  count=[[0]*4 for _ in range(2)];both=[0]*4;joint=[0]*4
  for tile in roi['tiles']:
   for color,name in enumerate(['R','G1','B','G2']):
    allowed=[]
    for pi,pas in enumerate(tile['passes']):
     v=pas['colors'][color];ok=pas['complete_support'] and v['accepted'];count[pi][color]+=ok;allowed.append(ok)
     if not pas['complete_support']:fail[(pi,name,'support')]+=1
     for key,(op,bound) in criteria.items():
      if not (v[key]>bound if op=='gt' else v[key]<=bound):fail[(pi,name,key)]+=1
    both[color]+=all(allowed);joint[color]+=tile['accepted_components_before_measurement'][color]
  rows.append({'base':window['window']['base'],'roi':roi['name'],'per_pass_components':count,'both_passes_before_mean_match':both,'joint_components':joint})
summary={'schema':'strehl.real-noise-insect-source-census.v1','qualification_sha256':hashlib.sha256((a.run/'qualification.json').read_bytes()).hexdigest(),'cache_hits':q['cache_disk_hits'],'measurement_loaded':q['measurement_loaded'],'rows':rows,'failure_counts_nonexclusive':[{'pass':k[0],'color':k[1],'criterion':k[2],'count':v} for k,v in sorted(fail.items())],'totals':{'per_pass':[[sum(r['per_pass_components'][pi][c] for r in rows) for c in range(4)] for pi in range(2)],'both_before_mean_match':[sum(r['both_passes_before_mean_match'][c] for r in rows) for c in range(4)],'joint':[sum(r['joint_components'][c] for r in rows) for c in range(4)]},'interpretation':'Source-only gate refusal. No measurement outputs, no noise-gain inference and no threshold change.'};a.out.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary['totals']))
for row in summary['failure_counts_nonexclusive']:print(row)
