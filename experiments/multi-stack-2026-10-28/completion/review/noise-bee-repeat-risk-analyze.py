"""Read-only complete-row analysis of the frozen conditional bee assay."""
import argparse,collections,hashlib,json,statistics
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();assert not a.output.exists()
b=a.input.read_bytes();d=json.loads(b);rows=d['rows'];assert len(rows)==10368
status=collections.Counter(r['status'] for r in rows);assert set(status)<={'available','not-qualified','unavailable-support'}
scopes=[];regions=[];arms=['equal','precision']
for arm in arms:
 for witness in dict.fromkeys(r['witness'] for r in rows):
  for color in range(4):
   all_rows=[r for r in rows if r['arm']==arm and r['witness']==witness and r['color']==color]
   v=[r for r in all_rows if r['status']=='available'];window_means=[]
   for window in range(4):
    w=[r for r in v if r['window']==window];states=[]
    for state in range(2):
     s=[r for r in w if r['state']==state]
     states.append({'state':state,'available_blocks':len(s),'mean_difference':statistics.mean(r['metric']['difference_vs_own_single'] for r in s) if s else None,'positive_blocks':sum(r['metric']['difference_vs_own_single']>0 for r in s)})
    wm=statistics.mean(r['metric']['difference_vs_own_single'] for r in w) if w else None
    if wm is not None:window_means.append(wm)
    scopes.append({'arm':arm,'witness':witness,'color':color,'window':window,'states':states,'two_state_mean_difference':wm,'available_block_states':len(w),'retained_unavailable':sum(r['window']==window and r['status']=='unavailable-support' for r in all_rows)})
   def total(k):return sum(r['metric'][k] for r in v)
   regions.append({'arm':arm,'witness':witness,'color':color,'available_block_states':len(v),'reference_mse_ratio_pooled':total('candidate_reference_mse')/total('own_single_reference_mse') if v else None,'mean_difference_pooled':total('difference_vs_own_single')/len(v) if v else None,'window_means':window_means,'mean_difference_equal_window_weight':statistics.mean(window_means) if window_means else None,'positive_block_states':sum(r['metric']['difference_vs_own_single']>0 for r in v),'difference_range':[min(r['metric']['difference_vs_own_single'] for r in v),max(r['metric']['difference_vs_own_single'] for r in v)] if v else None})
summary={'schema':'strehl.bee-conditional-reference-analysis.v1','input_sha256':hashlib.sha256(b).hexdigest(),'command':['python',__file__,str(a.input),str(a.output)],'status':dict(status),'regions':regions,'window_state_scopes':scopes,'uncertainty':'Four actual windows are acquisition-level units; neighboring blocks, CFA, reference states and windows share fixed geometry/optics. No pixel-count confidence interval and no universal gain guarantee. Window ranges and every adverse block retained.','scope':'Conditional empirical two-state reference agreement; not unbiased risk, sigma/SNR, or current wholephoto grouping benefit.'}
a.output.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
for arm in arms:
 r=[x for x in regions if x['arm']==arm];rat=[x['reference_mse_ratio_pooled'] for x in r];print(arm,'ratios',min(rat),max(rat),'adverse block-state',sum(x['positive_block_states'] for x in r),'regions',len(r))
