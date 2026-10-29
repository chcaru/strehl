"""Read checkpoint receipts and source; bounded analytical controls, no image/RAW input."""
import hashlib,json,math,statistics,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE='ef65505013585abcc86b1410e4bf902bf34ed479'
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
source_paths=['crates/strehl-core/src/session-fusion.rs','crates/strehl-cli/src/session-align.rs','crates/strehl-cli/src/session-consumer.rs','crates/strehl-cli/src/session-input.rs','crates/strehl-ui/src/process-session.rs']
result={'schema':'strehl.completion-independent-checkpoint-audit.v1','base':BASE,'scope':'Saved JSON and committed source only; no RAW, render, image processing or engine test','source_sha256':{},'proposal_sha256':{},'arms':[],'derivations':{}}
for name in source_paths:
 data=subprocess.check_output(['git','-C',str(ROOT),'--work-tree='+str(ROOT),'show',BASE+':'+name])
 result['source_sha256'][name]=sha(data)
for name in ['Proposal.md','Derivations.md']:
 result['proposal_sha256'][name]=sha((Path('C:/Users/chris/Downloads')/name).read_bytes())
for name in ['insect-repeat-4','slide-hdr-pair-6']:
 p=ROOT/'outputs/multi-stack'/name;r=load(p/'render-report.json');a=load(p/'alignment.json')['report'];cand=a['focus_candidates'];mutual=[v for v in cand if v['mutual_nearest']];eligible=[v for v in cand if v['candidate_same_focus']]
 allowed=[v['allowed_log_scale_gap'] for v in mutual if v['allowed_log_scale_gap'] is not None]
 gaps=[v['log_scale_gap']/(v['allowed_log_scale_gap']/0.25) for v in mutual if v['allowed_log_scale_gap']]
 arm={'name':name,'render_report_sha256':sha((p/'render-report.json').read_bytes()),'alignment_sha256':sha((p/'alignment.json').read_bytes()),'source_count':len(r['frames']),'groups':r['groups'],'pair_candidates':len(cand),'mutual_pairs':len(mutual),'eligible_pairs':len(eligible),'paired_sources':sum(len(v) for v in r['proposed_groups'] if len(v)>1),'possible_pairs_upper_bound':min(v['frames'] if 'frames' in v else v.get('total',0) for v in a['passes']) if a['passes'] else None,'mutual_gap_small_step_units':{'min':min(gaps),'median':statistics.median(gaps),'max':max(gaps)},'eligible_indices':{'i_min':min(v['i'] for v in eligible),'i_max':max(v['i'] for v in eligible),'j_min':min(v['j'] for v in eligible),'j_max':max(v['j'] for v in eligible)},'band_acceptance':[]}
 for k,d in enumerate(r['diagnostics']):
  denom=d['averaged']+d['ordinary_fallback']+d['primary_fallback']
  arm['band_acceptance'].append({'level':k,'averaged':d['averaged'],'two_source_candidate_sites':denom,'fraction_averaged_conditional_on_two_supported':d['averaged']/denom if denom else None,'single_source_sites':d['single_source'],'uncovered_group_sites':d['uncovered']})
 arm['caution']='Counts sum group coefficients, not unique output pixels or normalized final contribution. Low-frequency disagreement is not classified by cause.'
 result['arms'].append(arm)
# Fixed equal independent observations: one pair's variance in units of long-source variance.
c=2.533541440963745
cases={}
for name,ratio in [('same_noise',1.0),('hdr_shot_limited_equal_beta',c),('hdr_read_limited_equal_beta',c*c),('unequal_warp_transfer_ratio4',4.0)]:
 equal=(1+ratio)/4; optimal=ratio/(1+ratio)
 cases[name]={'variance_short_over_long':ratio,'equal_pair_var_over_long':equal,'inverse_variance_pair_var_over_long':optimal,'equal_pair_sigma_over_long':math.sqrt(equal),'inverse_variance_pair_sigma_over_long':math.sqrt(optimal),'optimal_long_weight':ratio/(1+ratio),'equal_over_optimal_variance':equal/optimal}
 assert equal>=optimal-1e-15
cases['same_noise']['exact_average_sigma']=1/math.sqrt(2)
result['derivations']['fixed_weight_pair_noise']=cases
# Model correct only for independent, fixed eligibility and weights. Shared noise foil.
result['derivations']['shared_noise_foil']={'var1':1.0,'var2':1.0,'covariance':1.0,'actual_pair_variance':1.0,'independence_formula_incorrect':0.5}
# Using constituent as evaluation reference is not independent and scales with blend amount.
result['derivations']['constituent_reference_foil']=[{'alpha_weight_B':alpha,'candidate_minus_A_variance_for_equal_unit_noise':2*alpha*alpha,'candidate_true_variance':(1-alpha)**2+alpha**2} for alpha in [0.0,0.25,0.5,1.0]]
(HERE/'checkpoint-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'arms':[{k:v for k,v in arm.items() if k not in ['band_acceptance','caution']} for arm in result['arms']],'noise_cases':cases,'receipt_sha256':sha((HERE/'checkpoint-audit.json').read_bytes())},indent=2))
