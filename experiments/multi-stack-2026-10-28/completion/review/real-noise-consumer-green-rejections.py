"""Classify frozen source qualification failures without reading measurement pixels."""
from pathlib import Path
import argparse, collections, json, hashlib
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
criteria={'mean_dn':('gt',64.),'guide_range_p95_sigma':('le',1.),'validation_p95_sigma':('le',.65),'mean_drift_sigma':('le',.25),'guide_gradient_p95_sigma':('le',.5)}
rows=[];counts=collections.Counter();margins=collections.defaultdict(list);sources={}
for base in [12,20,28,36,44,52]:
 path=a.root/f'registered-noise-window-{base}-01/qualification.json';q=json.loads(path.read_text());sources[str(base)]=hashlib.sha256(path.read_bytes()).hexdigest()
 for roi in q['rois']:
  for tile in roi['tiles']:
   red=tile['accepted_components_before_measurement'][0]
   for color,name in [(1,'G1'),(3,'G2')]:
    failed=[];detail=[]
    for pi,pas in enumerate(tile['passes']):
     if not pas['complete_support']:failed.append(f'pass{pi}:support')
     for key,(op,bound) in criteria.items():
      value=pas['colors'][color][key];ok=value>bound if op=='gt' else value<=bound
      if not ok:failed.append(f'pass{pi}:{key}')
      if red:margins[(name,pi,key)].append(value)
     detail.append(pas['colors'][color])
    gap=tile['mean_gap_combined_sigma'][color]
    if gap>.5:failed.append('cross_pass_mean_gap')
    assert bool(failed)!=tile['accepted_components_before_measurement'][color]
    for criterion in failed:counts[(name,red,criterion)]+=1
    rows.append({'base':base,'roi':roi['name'],'tile':tile['tile'],'color':name,'red_qualified':red,'failures':failed,'passes':detail,'cross_pass_gap_sigma':gap})
report={'schema':'strehl.real-noise-green-rejection-census.v1','qualification_sha256':sources,'measurement_pixels_loaded':False,'thresholds_unchanged':True,'counts_nonexclusive':[{'color':k[0],'red_qualified':k[1],'criterion':k[2],'count':v} for k,v in sorted(counts.items())],'red_qualified_green_ranges':[{'color':k[0],'pass':k[1],'metric':k[2],'minimum':min(v),'median':sorted(v)[len(v)//2],'maximum':max(v)} for k,v in sorted(margins.items())],'rows':rows}
a.out.write_text(json.dumps(report,indent=2)+'\n')
for row in report['counts_nonexclusive']:
 if row['red_qualified']:print(row)
print('ranges')
for row in report['red_qualified_green_ranges']:print(row)
