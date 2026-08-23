"""M39 verification, script 06: sharper absolute-scale and fixed-pattern measurements.

Script 05's wide signal bins biased the percentile estimator (within a wide bin the
lowest-variance patches are the lowest-SIGNAL patches). This one works with the
per-patch RATIO to the model, in narrow bins, and adds three cross-checks:

  (i)   is the ARW lossy-compressed? (quantised codes would distort every noise stat)
  (ii)  a temporal-pair sigma: Var(frame_k - frame_k+1)/2 in the flat ROIs
  (iii) a fixed-pattern bound with ZERO temporal-noise contribution: the covariance
        of the high-passed means of two DISJOINT halves of the stack.
"""
import numpy as np, rawpy, glob
from scipy.stats import chi2
from scipy.ndimage import uniform_filter

FRAMES = sorted(glob.glob(r'D:\personal\macro\109MSDCF\*.ARW'))
BLACK, ISO, GAIN_DIV, RN_E = 512.0, 160.0, 436.8, 4.20
G = ISO / GAIN_DIV; READ_DN = RN_E * G
def modvar_G(S):  return G * np.maximum(S, 0.0) + READ_DN ** 2

# ---------------- (i) compression -------------------------------------------
r = rawpy.imread(FRAMES[11]); a = r.raw_image_visible.astype(np.int64)
for lo, hi in ((600, 700), (2400, 2600), (6000, 6200)):
    seg = a[(a >= lo) & (a < hi)]
    u = np.unique(seg)
    gaps = np.diff(u)
    print(f'(i) codes in [{lo},{hi}): {u.size} distinct of {hi-lo} possible, '
          f'modal gap {np.bincount(gaps).argmax() if gaps.size else 0}')
print('    (all gaps 1 => not code-quantised in that range)')

g1 = a[0::2, 1::2].astype(np.float64); g2 = a[1::2, 0::2].astype(np.float64)
S = 0.5 * (g1 + g2) - BLACK; D = g1 - g2
H, W = S.shape

# ---------------- (ii) narrow-bin ratio PTC ---------------------------------
P = 24
Hh, Ww = (H // P) * P, (W // P) * P
Sp = S[:Hh, :Ww].reshape(Hh//P, P, Ww//P, P).transpose(0,2,1,3).reshape(-1, P*P)
Dp = D[:Hh, :Ww].reshape(Hh//P, P, Ww//P, P).transpose(0,2,1,3).reshape(-1, P*P)
smean = Sp.mean(axis=1); dvar = Dp.var(axis=1, ddof=1)
dof = P*P - 1
ratio = dvar / (2 * modvar_G(smean))          # 1.0 if the model is exactly right
PCTS = (2.0, 5.0, 10.0, 25.0)
print()
print(f'(ii) PTC by RATIO, {Sp.shape[0]} patches of {P}x{P} (dof {dof}).')
print('     ratio = var(G1-G2) / model.  A percentile of a chi2_dof/dof is divided out,')
print('     so an unstructured patch reads 1.000 in expectation.')
hdr = '      signal bin      n  ' + '  '.join(f'p{p:g}' .rjust(8) for p in PCTS)
print(hdr)
edges = [150, 250, 350, 450, 600, 800, 1000, 1300, 1700, 2200, 2900, 3800, 5000, 7000, 10000]
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (smean >= lo) & (smean < hi)
    if m.sum() < 60: continue
    row = f'   {lo:6.0f}-{hi:6.0f} {m.sum():6d}  '
    for p in PCTS:
        row += f'{np.percentile(ratio[m], p) / (chi2.ppf(p/100, dof)/dof):8.3f}  '
    print(row)
print('     (a well-calibrated model with clean flat patches available in every bin')
print('      reads ~1.000 at the LOW percentiles; > 1 means the model UNDER-predicts.)')

# ---------------- (iii) temporal pairs in the flat ROIs ---------------------
print()
print('(iii) temporal-pair sigma in the flat ROIs: Var(frame_k - frame_k+1)/2')
def roi_luma(path, x, y, w=256, h=256):
    rr = rawpy.imread(path); aa = rr.raw_image_visible
    q = aa[2*y:2*(y+h), 2*x:2*(x+w)].astype(np.float64)
    return 0.5 * (q[0::2, 1::2] + q[1::2, 0::2]) - BLACK
for (fx, fy) in ((2272, 1344), (2352, 1408)):
    stack = np.stack([roi_luma(p, fx, fy) for p in FRAMES])
    diffs = [np.var(stack[k+1] - stack[k], ddof=1) / 2 for k in range(len(FRAMES)-1)]
    mv = 0.5 * modvar_G(stack.mean())
    print(f'   ROI {fx},{fy}: mean {stack.mean():8.2f} DN   model Var(L) = {mv:8.2f} DN^2')
    print(f'     Var(diff)/2 over the 21 consecutive pairs: min {min(diffs):8.2f}  '
          f'median {np.median(diffs):8.2f}  max {max(diffs):8.2f}')
    print(f'     k = sqrt(min/model) = {np.sqrt(min(diffs)/mv):.4f}   '
          f'k = sqrt(median/model) = {np.sqrt(np.median(diffs)/mv):.4f}  (UPPER bounds)')

    # ------------ (iv) disjoint-half fixed-pattern covariance --------------
    A = stack[0::2].mean(axis=0); B = stack[1::2].mean(axis=0)
    hpA = A - uniform_filter(A, 5, mode='reflect'); hpB = B - uniform_filter(B, 5, mode='reflect')
    ca, cb = hpA[6:-6, 6:-6], hpB[6:-6, 6:-6]
    cov = float(np.mean((ca - ca.mean()) * (cb - cb.mean())))
    hp_gain = 1 - 1/25
    print(f'     disjoint-half high-pass covariance = {cov:8.3f} DN^2 '
          f'(temporal noise contributes ZERO in expectation)')
    print(f'     => fixed high-frequency component f <= {np.sqrt(max(cov,0)/hp_gain):.3f} DN '
          f'at {stack.mean():.0f} DN  (still an UPPER bound: shared scene texture)')
