"""Read complete consumer receipts, retaining signal/noise and target distinctions."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True)
p.add_argument('--psf',type=Path,required=True);p.add_argument('--prior',type=Path,required=True)
p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
prior=json.loads(a.prior.read_text());original=json.loads(a.original.read_text());psf=json.loads(a.psf.read_text())
assert len(original['rows'])==len(prior['rows'])==594 and len(psf['rows'])==378
assert all(all(new[k]==old[k] for k in old) for old,new in zip(prior['rows'],original['rows']))
results=[]
for label,data in [('original',original),('psf',psf)]:
 for case in dict.fromkeys(r['case'] for r in data['rows']):
  rows=[r for r in data['rows'] if r['case']==case]
  temporal={r['arm']:r for r in data['temporal_summary'] if r['case']==case}
  def risk(arm):
   r=[r for r in rows if r['arm']==arm and r['seed'] is not None];assert len(r)==8
   return np.mean([[[v['mse'] for v in state] for state in x['against_clean_passes']] for x in r],axis=(0,1))
  proposal=risk('proposal')
  arms=[]
  for arm in temporal:
   clean=next(r for r in rows if r['arm']==arm and r['seed'] is None)
   t=temporal[arm]
   # Finite sample MSE = bias(mean)^2 +(n-1)/n sample temporal variance.
   measured=risk(arm)
   bias=np.mean([[v['mse'] for v in state] for state in t['mean_against_clean_passes']],axis=0)
   reconstructed=bias+np.array(t['sample_temporal_variance'])*7/8
   assert np.allclose(measured,reconstructed,rtol=3e-4,atol=.01),(label,case,arm,measured,reconstructed)
   arms.append(dict(arm=arm,own_clean_pass_average_mse=measured.tolist(),
       sample_temporal_variance=t['sample_temporal_variance'],
       clean_vs_all_single=clean['against_clean_all_single'],
       clean_vs_each_pass=clean['against_clean_passes'],
       unclipped_consumer_sentinel=clean['against_unclipped_consumer_sentinel']))
  results.append(dict(set=label,case=case,arms=arms,
      proposal_own_clean_pass_mse_ratio_vs_single=(proposal/risk('all-single')).tolist(),
      proposal_own_clean_pass_mse_ratio_vs_legacy=(proposal/risk('legacy-partial')).tolist(),
      proposal_sample_temporal_variance_ratio_vs_single=(np.array(temporal['proposal']['sample_temporal_variance'])/
           np.array(temporal['all-single']['sample_temporal_variance'])).tolist()))
out=dict(schema='strehl.repeat-proposal-consumer-analysis.v1',inputs={k:sha(getattr(a,k)) for k in ['original','psf','prior']},
    prior_594_rows_exact=True,mse_variance_identity_checked=True,cases=results,
    scope='MEASURED synthetic actual native consumer. Temporal variance is across8independent seeded originals; MSE references are noiseless consumer outputs, not latent per-acquisition truth. Contrast plants and analytic Gaussian PSF plants remain distinct. Low MSE or variance without preserved target-specific signal transfer is not photographic improvement. No default promotion or real-photo quality claim.')
a.out.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(prior_rows_exact=True,cases=len(results),output=str(a.out))))
