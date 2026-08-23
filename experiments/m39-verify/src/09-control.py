"""M39 verification, script 09: the control that decides whether the corrected
metric is usable as an acceptance criterion at all.

(a) THE CONTROL. Fact 19/24: a plain unweighted mean of all 22 frames measures
    0.534x noise and collapses detail -58%. If the CORRECTED metric reads the
    plain mean at roughly the same -4.6% it reads the gate-8 merge, then the
    corrected metric cannot tell the merge from the known-bad baseline, and
    invariant 2 is not an acceptance test.
(b) how concentrated is the squared-gradient energy in the REAL ROIs? (attack 4
    used a synthetic; this asks whether the real data has the same shape)
(c) a cleaner blur calibration than script 08 attack 3: take the quietest merged
    output as the signal, blur ONLY the signal, then add fresh INDEPENDENT noise
    at the model level, so signal blur is not conflated with noise correlation.
"""
import numpy as np, rawpy, glob
from scipy.ndimage import gaussian_filter

rng = np.random.default_rng(390)
FRAMES = sorted(glob.glob(r'D:\personal\macro\109MSDCF\*.ARW'))
BLACK, ISO, GAIN_DIV, RN_E = 512.0, 160.0, 436.8, 4.20
G = ISO / GAIN_DIV; READ_DN = RN_E * G
ROIS = {'A': (1630, 1044, 256, 256), 'B': (64, 800, 256, 256)}
def sigma_luma(S): return np.sqrt(0.5*(G*np.maximum(S,0.0) + READ_DN*READ_DN))
def parts(v): return v[:-1,1:]-v[:-1,:-1], v[1:,:-1]-v[:-1,:-1]
def raw_rms(v):
    dx, dy = parts(v); return np.sqrt((dx*dx+dy*dy).mean())
def noise_rms(sig):
    s2 = sig**2; return np.sqrt((2*s2[:-1,:-1]+s2[:-1,1:]+s2[1:,:-1]).mean())
def corrected(v, sig):
    r = raw_rms(v); n = noise_rms(sig); return np.sqrt(max(0.0, r*r-n*n))
def m2(v):
    dx, dy = parts(v); return (0.5*(np.abs(dx)+np.abs(dy))).mean()

# ---------- (a) the plain-mean control -------------------------------------
print('=' * 78)
print('(a) THE CONTROL: the plain unweighted mean of all 22 frames')
print('=' * 78)
sums = {k: 0.0 for k in ROIS}
for p in FRAMES:
    r = rawpy.imread(p); a = r.raw_image_visible
    for k, (x, y, w, h) in ROIS.items():
        q = a[2*y:2*(y+h), 2*x:2*(x+w)].astype(np.float64)
        sums[k] = sums[k] + 0.5*(q[0::2,1::2] + q[1::2,0::2]) - BLACK
    del r, a
d = np.load('out/07-merged-rois.npz')
N = len(FRAMES)
print(f'  {"":18s}{"corrected":>11s}{"vs gate0":>10s}{"raw_rms":>10s}'
      f'{"noise_rms":>11s}{"m2":>9s}{"vs gate0":>10s}')
for k in ROIS:
    pm = sums[k] / N
    sig_pm = sigma_luma(pm) / np.sqrt(N)
    rows = []
    for lbl, v, n in (('gate 0 (selection)', d[f'{k}_merged_0.0'], d[f'{k}_n_0.0']),
                      ('gate 2.0',           d[f'{k}_merged_2.0'], d[f'{k}_n_2.0']),
                      ('gate 8.0',           d[f'{k}_merged_8.0'], d[f'{k}_n_8.0']),
                      ('PLAIN MEAN n=22',    pm, np.full(pm.shape, N))):
        sig = sigma_luma(v) / np.sqrt(n)
        rows.append((lbl, corrected(v, sig), raw_rms(v), noise_rms(sig), m2(v)))
    c0, m0 = rows[0][1], rows[0][4]
    print(f'  ROI {k}')
    for lbl, c, r_, n_, mm in rows:
        print(f'   {lbl:18s}{c:11.4f}{100*(c/c0-1):+9.2f}%{r_:10.4f}{n_:11.4f}'
              f'{mm:9.4f}{100*(mm/m0-1):+9.2f}%')

# ---------- (b) gradient-energy concentration in the real ROIs -------------
print()
print('=' * 78)
print('(b) how concentrated is the squared-gradient energy in the REAL ROIs?')
print('=' * 78)
for k in ROIS:
    v = d[f'{k}_merged_0.0']
    dx, dy = parts(v)
    e = np.concatenate([dx.ravel()**2, dy.ravel()**2])
    e = np.sort(e)[::-1]
    tot = e.sum()
    fr = [np.searchsorted(np.cumsum(e), f*tot)/e.size for f in (0.5, 0.8, 0.9)]
    print(f'  ROI {k}: the top {100*fr[0]:5.2f}% of difference pairs carry 50% of the '
          f'squared-gradient energy;')
    print(f'          top {100*fr[1]:5.2f}% carry 80%;  top {100*fr[2]:5.2f}% carry 90%.')
    for frac in (0.5, 0.25, 0.1):
        thr = np.quantile(np.abs(np.concatenate([dx.ravel(), dy.ravel()])), 1-frac)
        keep = e[e >= thr*thr].sum()
        print(f'          the strongest {100*frac:4.1f}% of differences carry '
              f'{100*keep/tot:5.2f}% of the energy')

# ---------- (c) clean blur calibration -------------------------------------
print()
print('=' * 78)
print('(c) blur calibration with the noise held INDEPENDENT (script 08 attack 3')
print('    blurred the noise too, which over-subtracts)')
print('=' * 78)
for k in ROIS:
    sgn = d[f'{k}_merged_8.0']                      # quietest available; treated as signal
    n0 = d[f'{k}_n_0.0']
    sig = sigma_luma(sgn) / np.sqrt(n0)             # gate-0 noise level
    print(f'  ROI {k}: model sigma at gate 0 = {sig.mean():.3f} DN mean')
    print(f'    blur sd    corrected      d%       m2       d%')
    base = None
    for sb in (0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.6):
        s = gaussian_filter(sgn, sb) if sb > 0 else sgn
        v = s + sig * rng.standard_normal(s.shape)
        c = corrected(v, sig); mm = m2(v)
        if base is None: base, basem = c, mm
        print(f'    {sb:7.2f}   {c:10.4f} {100*(c/base-1):+7.2f}%  {mm:8.3f} '
              f'{100*(mm/basem-1):+7.2f}%')
