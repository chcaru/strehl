"""Commission a bounded independent observer, not the product or camera model."""
import hashlib,json,math,os
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
rng=np.random.default_rng(2026102817)
T,H,W=64,64,64
# Independent repeats and explicitly supplied truth. Flat is exercised first.
a=rng.normal(0,20,(T,H,W)); b=rng.normal(0,10,(T,H,W))
flat=200.0
arms={'single_A':flat+a,'single_B':flat+b,'equal':flat+(a+b)/2,'inverse_variance':flat+0.2*a+0.8*b,'duplicate_A_mean':flat+(a+a)/2}
expected={'single_A':400,'single_B':100,'equal':125,'inverse_variance':80,'duplicate_A_mean':400}
flat_result={}
for name,arr in arms.items():
 variance=float(arr.var(axis=0,ddof=1).mean());bias=float(arr.mean()-flat)
 flat_result[name]={'temporal_variance':variance,'expected_variance':expected[name],'ratio_to_expected':variance/expected[name],'mean_bias':bias}
 assert abs(variance/expected[name]-1)<.03
 assert abs(bias)<.2
# Independent known latent signal guards that a favorable flat noise result cannot hide blur.
x=np.arange(W)[None,:];y=np.arange(H)[:,None]
s1=np.sin(2*np.pi*x/8)+np.zeros((H,1)); s2=np.sin(2*np.pi*y/16)+np.zeros((1,W))
truth=200+50*s1+20*s2
base=truth[None,:,:]+0.2*a+0.8*b
def blur(v):
 z=(np.roll(v,1,axis=-1)+2*v+np.roll(v,-1,axis=-1))/4
 return (np.roll(z,1,axis=-2)+2*z+np.roll(z,-1,axis=-2))/4
variants={'correct_weighted':base,'blur':blur(blur(base)),'sharpen':base+1.5*(base-blur(base)),'constant':np.zeros_like(base)+200,'one_pixel_shift':np.roll(base,1,axis=-1)}
texture_result={}
for name,v in variants.items():
 mean=v.mean(axis=0);noisevar=float(v.var(axis=0,ddof=1).mean())
 gains=[float(np.mean((mean-200)*template)/np.mean(template*template)/amp) for template,amp in [(s1,50),(s2,20)]]
 mse=float(np.mean((mean-truth)**2));passes=all(abs(g-1)<.025 for g in gains)
 texture_result[name]={'temporal_variance':noisevar,'known_signal_gains':gains,'mean_image_truth_mse':mse,'passes_two_frequency_transfer_sentinel':passes}
 assert passes==(name=='correct_weighted')
assert texture_result['blur']['temporal_variance'] < texture_result['correct_weighted']['temporal_variance']
# A constituent reference changes with the blend parameter, even when actual variance improves.
reference_foil=[]
for alpha in [0,.25,.5,1]:
 v=(1-alpha)*a+alpha*b
 reference_foil.append({'weight_B':alpha,'true_temporal_var':float(v.var(axis=0,ddof=1).mean()),'mse_against_constituent_A':float(np.mean((v-a)**2))})
result={'schema':'strehl.independent-observer-commission.v1','scope':'Known-truth synthetic observer checks only; no product engine, RAW, real-camera or photo-quality claim','seed':2026102817,'trials':T,'dimensions':[H,W],'independence':'A and B independently generated; duplicate control deliberately shares A','flat_first':flat_result,'texture_and_adversarial_controls':texture_result,'constituent_reference_foil':reference_foil,'limits':['Temporal variation assumes fixed latent signal; drift/focus/registration must be separately bounded on real captures.','Known-frequency transfer sentinels are scoped observables, not a universal photographic detail measure.','A fixed frozen-weight prediction is not a certificate of adaptive gating variance.'],'environment':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']},'numpy':np.__version__,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(HERE/'observer-controls.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'flat':flat_result,'transfer':texture_result,'receipt_sha256':hashlib.sha256((HERE/'observer-controls.json').read_bytes()).hexdigest()},indent=2))
