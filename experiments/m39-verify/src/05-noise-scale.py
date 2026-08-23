"""M39 verification, script 05: is the calibrated sigma right in ABSOLUTE scale,
and how big is the fixed-pattern floor?

Two independent measurements, neither of which uses the noise model:

(1) A photon-transfer estimate from D = G1 - G2 on the plane lattice. The two
    greens are separate photosites 1 px apart on the diagonal, so their sensor
    noise is independent and Var(D) = 2*(g*S + read_dn^2) + (local signal
    difference)^2.  The signal term is non-negative, so any patch estimate is an
    UPPER bound; taking a low percentile across many patches at the same signal
    level, and dividing out the chi-square percentile of the same dof, removes
    both the structure contamination and the selection bias.

(2) A fixed-pattern upper bound: the 22-frame per-pixel mean in the flat ROI,
    high-passed. Anything fixed in sensor coordinates survives the temporal
    mean; anything temporal is down by sqrt(22).
"""
import numpy as np, rawpy, glob
from scipy.stats import chi2

FRAMES = sorted(glob.glob(r'D:\personal\macro\109MSDCF\*.ARW'))
BLACK, ISO, GAIN_DIV, RN_E = 512.0, 160.0, 436.8, 4.20
G = ISO / GAIN_DIV; READ_DN = RN_E * G
print(f'model: g = {G:.6f} DN/e-, read = {RN_E} e- = {READ_DN:.6f} DN, '
      f'read^2 = {READ_DN**2:.6f} DN^2')

r = rawpy.imread(FRAMES[11]); a = r.raw_image_visible.astype(np.float64)
g1 = a[0::2, 1::2]; g2 = a[1::2, 0::2]
S = 0.5 * (g1 + g2) - BLACK
D = g1 - g2
H, W = S.shape
print('plane', S.shape)

# ---------------- (1) PTC from G1-G2 ---------------------------------------
P = 32                                   # patch side, plane px
Hh, Ww = (H // P) * P, (W // P) * P
Sp = S[:Hh, :Ww].reshape(Hh // P, P, Ww // P, P).transpose(0, 2, 1, 3).reshape(-1, P * P)
Dp = D[:Hh, :Ww].reshape(Hh // P, P, Ww // P, P).transpose(0, 2, 1, 3).reshape(-1, P * P)
smean = Sp.mean(axis=1)
dvar = Dp.var(axis=1, ddof=1)
dof = P * P - 1
print(f'{Sp.shape[0]} patches of {P}x{P}, dof {dof}')

PCT = 5.0
corr = chi2.ppf(PCT / 100.0, dof) / dof      # E[p-th pct of chi2_dof/dof]
print(f'chi2 {PCT}th-percentile correction factor: {corr:.5f}')
edges = np.array([0, 100, 200, 400, 700, 1100, 1600, 2300, 3200, 4500, 6500, 9000, 13000])
print()
print('  signal bin      n    var(D) 5th pct   /corr = sigma_D^2   model 2*sigma_G^2   ratio')
xs, ys = [], []
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (smean >= lo) & (smean < hi)
    if m.sum() < 40: continue
    v = np.percentile(dvar[m], PCT) / corr
    sbar = np.median(smean[m])
    model = 2 * (G * sbar + READ_DN ** 2)
    xs.append(sbar); ys.append(v)
    print(f'  {lo:5.0f}-{hi:5.0f}  {m.sum():5d}   {np.percentile(dvar[m],PCT):14.2f}   '
          f'{v:17.2f}   {model:17.2f}   {v/model:6.3f}')
xs = np.array(xs); ys = np.array(ys)
A = np.vstack([xs, np.ones_like(xs)]).T
sl, ic = np.linalg.lstsq(A, ys, rcond=None)[0]
print()
print(f'  fit Var(D) = {sl:.6f} * S + {ic:.3f}   ->  g_measured = {sl/2:.6f} DN/e- '
      f'(model {G:.6f}, ratio {sl/2/G:.4f})')
rn2 = ic / 2
print(f'  read^2_measured = {rn2:.4f} DN^2 -> read = {np.sqrt(max(rn2,0)):.4f} DN = '
      f'{np.sqrt(max(rn2,0))/G:.3f} e-  (model {RN_E} e-)')
print(f'  => sigma scale factor k = sqrt(measured/model) at the two detail-ROI levels:')
for lvl, lbl in ((394.6235, 'ROI A'), (1153.3351, 'ROI B')):
    meas = sl * lvl + ic
    mod = 2 * (G * lvl + READ_DN ** 2)
    print(f'     {lbl} at {lvl:9.4f} DN: measured {meas:9.3f}  model {mod:9.3f}  '
          f'k = {np.sqrt(meas/mod):.4f}')

# ---------------- flat ROIs, directly --------------------------------------
print()
print('  the two flat ROIs directly (no percentile, no binning):')
for (fx, fy) in ((2272, 1344), (2352, 1408)):
    sub_s = S[fy:fy+256, fx:fx+256]; sub_d = D[fy:fy+256, fx:fx+256]
    meas = sub_d.var(ddof=1); mod = 2 * (G * sub_s.mean() + READ_DN ** 2)
    print(f'    ROI {fx},{fy}: mean {sub_s.mean():8.2f} DN  var(G1-G2) {meas:9.2f}  '
          f'model {mod:9.2f}  k = {np.sqrt(meas/mod):.4f}  (UPPER bound: structure adds)')

# ---------------- (2) fixed-pattern upper bound ----------------------------
print()
print('(2) fixed-pattern upper bound in the flat ROI 2272,1344,256,256')
stack = []
for p in FRAMES:
    rr = rawpy.imread(p); aa = rr.raw_image_visible
    q = aa[2*1344:2*(1344+256), 2*2272:2*(2272+256)].astype(np.float64)
    stack.append(0.5 * (q[0::2, 1::2] + q[1::2, 0::2]) - BLACK)
    del rr, aa
stack = np.stack(stack)
N = stack.shape[0]
M = stack.mean(axis=0)

def hp(x, k=5):
    from scipy.ndimage import uniform_filter
    return x - uniform_filter(x, size=k, mode='reflect')

hf_mean = hp(M); hf_one = hp(stack[11])
var_hf_mean = hf_mean[6:-6, 6:-6].var()
var_hf_one = hf_one[6:-6, 6:-6].var()
sig_model = np.sqrt(0.5 * (G * M.mean() + READ_DN ** 2))
hp_gain = 1 - 1.0 / 25          # variance retained by (I - 5x5 box) on white noise
print(f'   mean signal {M.mean():.2f} DN, model sigma_L = {sig_model:.3f} DN, N = {N}')
print(f'   var(high-pass of ONE frame)      = {var_hf_one:9.3f} DN^2  '
      f'(pure white noise would give {hp_gain*sig_model**2:.3f} + scene)')
print(f'   var(high-pass of the 22-frame mean) = {var_hf_mean:9.3f} DN^2')
print(f'   temporal part expected in the mean  = {hp_gain*sig_model**2/N:9.3f} DN^2')
fpn2 = var_hf_mean - hp_gain * sig_model ** 2 / N
print(f'   => high-frequency FIXED component <= {max(fpn2,0):9.3f} DN^2 '
      f'-> f <= {np.sqrt(max(fpn2,0))/np.sqrt(hp_gain):.3f} DN at {M.mean():.0f} DN signal')
print('   (UPPER bound: unresolved scene texture and inter-frame drift both inflate it)')
