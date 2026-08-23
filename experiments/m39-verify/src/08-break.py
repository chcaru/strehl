"""M39 verification, script 08: attempts to BREAK the corrected metric.

Six attacks, each designed so that it can succeed:
  1. does the (2,1,1) coefficient structure matter on the REAL merged output?
     (every unit test in the repo uses a spatially UNIFORM sigma, where it cannot)
  2. selection seams: at gate 0 adjacent pixels come from different frames, which
     manufactures gradient that is not detail -- and it inflates the DENOMINATOR
     of the -4.6%.
  3. what blur does -4.6% actually correspond to? (calibrate the metric)
  4. RMS is dominated by the strongest edges -- is the metric blind to the
     destruction of low-contrast fine detail?
  5. low-SNR regime: where does the clean-vs-noisy invariance break, and where
     does max(0, .) clamp?
  6. spatially CORRELATED / ANTI-CORRELATED noise with the SAME marginal sigma:
     the correction assumes per-pixel independence. What happens when it fails?
"""
import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter

rng = np.random.default_rng(39)
BLACK, ISO, GAIN_DIV, RN_E = 512.0, 160.0, 436.8, 4.20
G = ISO / GAIN_DIV; READ_DN = RN_E * G
def sigma_luma(S): return np.sqrt(0.5 * (G * np.maximum(S, 0.0) + READ_DN * READ_DN))

def parts(v):
    dx = v[:-1, 1:] - v[:-1, :-1]; dy = v[1:, :-1] - v[:-1, :-1]
    return dx, dy
def raw_rms(v):
    dx, dy = parts(v); return np.sqrt((dx*dx + dy*dy).mean())
def noise_rms(sig, coef=(2, 1, 1)):
    s2 = sig**2
    return np.sqrt((coef[0]*s2[:-1,:-1] + coef[1]*s2[:-1,1:] + coef[2]*s2[1:,:-1]).mean())
def corrected(v, sig, coef=(2,1,1)):
    r = raw_rms(v); n = noise_rms(sig, coef)
    return np.sqrt(max(0.0, r*r - n*n))
def m2(v):
    dx, dy = parts(v); return (0.5*(np.abs(dx)+np.abs(dy))).mean()

d = np.load('out/07-merged-rois.npz')
print('=' * 78)
print('ATTACK 1 -- does the (2,1,1) structure matter where sigma is NOT uniform?')
print('=' * 78)
for k in ('A', 'B'):
    for gate in (0.0, 2.0, 8.0):
        v = d[f'{k}_merged_{gate}']; n = d[f'{k}_n_{gate}']
        sig = sigma_luma(v) / np.sqrt(n)
        base = corrected(v, sig)
        alts = {'(1,1,2)': (1,1,2), '(4,0,0)': (4,0,0), '(0,2,2)': (0,2,2)}
        s = f'  ROI {k} gate {gate:4.1f}  n in [{n.min()},{n.max()}]  sigma spread '
        s += f'{sig.min():.3f}-{sig.max():.3f} DN   corrected {base:9.4f} '
        for lbl, c in alts.items():
            s += f'  {lbl}:{100*(corrected(v,sig,c)/base-1):+.3f}%'
        print(s)
print('  => the coefficient STRUCTURE is worth <0.3% even where n varies 1..22.')
print('     It is correct (script 01), but NO test in the repo can see it: every')
print('     detail_metrics test passes a spatially uniform sigma array.')

print()
print('=' * 78)
print('ATTACK 2 -- selection seams inflate the gate-0 reference')
print('=' * 78)
for k in ('A', 'B'):
    v = d[f'{k}_merged_0.0']; w = d[f'{k}_win']
    dx, dy = parts(v)
    sx = (w[:-1,1:] != w[:-1,:-1]); sy = (w[1:,:-1] != w[:-1,:-1])
    e_same = (dx[~sx]**2).sum() + (dy[~sy]**2).sum()
    e_seam = (dx[sx]**2).sum() + (dy[sy]**2).sum()
    ntot = dx.size + dy.size
    print(f'  ROI {k}: {100*(sx.sum()+sy.sum())/ntot:5.2f}% of difference pairs cross a '
          f'winner boundary, carrying {100*e_seam/(e_same+e_seam):5.2f}% of the squared-gradient energy')
    frac = e_seam / (e_same + e_seam)
    print(f'          mean sq gradient across a seam is '
          f'{ (e_seam/max(sx.sum()+sy.sum(),1)) / (e_same/max(ntot-sx.sum()-sy.sum(),1)) :5.2f}x '
          f'the within-winner value')

print()
print('=' * 78)
print('ATTACK 3 -- what blur does -4.6% correspond to? (metric calibration)')
print('=' * 78)
for k, target in (('A', -4.58), ('B', -3.57)):
    v = d[f'{k}_merged_0.0']; n = d[f'{k}_n_0.0']
    sig = sigma_luma(v) / np.sqrt(n)
    base_c = corrected(v, sig); base_m2 = m2(v)
    dxr, dyr = parts(v); g0 = np.hypot(dxr, dyr)
    print(f'  ROI {k}: gate-0 corrected {base_c:.4f}')
    print(f'    blur sd   corrected     d%      m2      d%    p25|grad|    d%')
    for sb in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0):
        vb = gaussian_filter(v, sb) if sb > 0 else v
        # the blur also correlates the noise; use the clean-signal correction (sig
        # unchanged) exactly as the shipped metric would
        c = corrected(vb, sig); mm = m2(vb)
        dxb, dyb = parts(vb); gb = np.hypot(dxb, dyb)
        print(f'    {sb:7.2f}   {c:9.4f} {100*(c/base_c-1):+7.2f}%  {mm:7.3f} '
              f'{100*(mm/base_m2-1):+7.2f}%   {np.percentile(gb,25):8.3f} '
              f'{100*(np.percentile(gb,25)/np.percentile(g0,25)-1):+7.2f}%')

print()
print('=' * 78)
print('ATTACK 4 -- RMS is dominated by the strongest edges. Is it blind to the')
print('            total destruction of low-contrast fine detail?')
print('=' * 78)
W = 256
strong = np.zeros((W, W))
for e in range(1, 8):                      # 7 strong step edges
    strong[:, e * 32:] += 2000.0
fine = 20.0 * rng.standard_normal((W, W))  # low-contrast fine texture everywhere
zero = np.zeros((W, W))
c_with = corrected(strong + fine, zero); c_without = corrected(strong, zero)
m_with = m2(strong + fine); m_without = m2(strong)
print(f'  strong edges + fine texture : corrected {c_with:10.4f}   m2 {m_with:9.4f}')
print(f'  fine texture DELETED ENTIRELY: corrected {c_without:10.4f}   m2 {m_without:9.4f}')
print(f'  => deleting 100% of the fine detail costs the corrected metric '
      f'{100*(c_without/c_with-1):+.2f}% and m2 {100*(m_without/m_with-1):+.2f}%')
print('     A -4.6% reading is therefore compatible with total loss of low-contrast')
print('     detail. The metric bounds the STRONG edges, not "detail".')

print()
print('=' * 78)
print('ATTACK 5 -- low SNR: invariance break and the max(0,.) clamp')
print('=' * 78)
base = d['A_merged_8.0']                     # use the quietest merged output as "signal"
base = base - base.mean()
sd = 12.0
print('   contrast   raw_rms  noise_rms  corrected(noisy)  corrected(clean)   error')
for c in (1.0, 0.5, 0.25, 0.1, 0.05, 0.02, 0.01):
    s = c * base
    noisy = s + sd * rng.standard_normal(s.shape)
    sig = np.full(s.shape, sd)
    cn = corrected(noisy, sig); cc = corrected(s, np.zeros_like(s))
    print(f'   {c:8.3f}  {raw_rms(noisy):8.3f}  {noise_rms(sig):9.3f}  {cn:16.4f}  '
          f'{cc:16.4f}  {100*(cn/cc-1) if cc>0 else float("nan"):+7.2f}%')
print('   (the clamp bites, and the estimator becomes badly biased, once the signal')
print('    gradient falls under roughly half the noise gradient)')

print()
print('=' * 78)
print('ATTACK 6 -- SAME marginal sigma, but spatially correlated / anti-correlated')
print('=' * 78)
s = d['A_merged_8.0']; s = s - s.mean()
sd = 12.0
white = sd * rng.standard_normal(s.shape)
corr = uniform_filter(white, 3); corr *= sd / corr.std()
anti = white - uniform_filter(white, 3); anti *= sd / anti.std()
sig = np.full(s.shape, sd)
truth = corrected(s, np.zeros_like(s))
for lbl, nz in (('white (model is right)', white), ('correlated 3x3', corr),
                ('anti-correlated', anti)):
    v = s + nz
    print(f'  {lbl:24s} marginal sd {nz.std():6.3f}  raw_rms {raw_rms(v):8.3f}  '
          f'corrected {corrected(v, sig):9.4f}  vs true {truth:9.4f}  '
          f'({100*(corrected(v,sig)/truth-1):+7.2f}%)')
print('  => the correction is exact ONLY for pixel-independent noise. Any stage that')
print('     resamples (alignment) makes it CONSERVATIVE; any stage that sharpens or')
print('     deconvolves makes it OPTIMISTIC -- it would credit amplified noise as detail.')
