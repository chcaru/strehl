"""Why is strehl's contrast variance ~0.5x prior's at EVERY scale?
A scale-independent ratio cannot be a sharpness difference.  Candidates:
  (a) a residual tone/gamma error in my inversion,
  (b) a genuine grade difference (prior develop applied more contrast),
  (c) a FLARE / BLACK-OFFSET difference: contrast is sigma/mean, so an additive
      offset changes it at every scale by the same factor.
Distinguish them by fitting prior = a*strehl + b on COARSE (16x box) versions of
each ROI, where the 3.5% scale mismatch is sub-coarse-pixel and registration is
not an issue.  b != 0 is a flare/offset difference; a curved fit is (a) or (b).
"""
import numpy as np, arms, spec
from scipy import ndimage
P = arms.prior_arm(); S = arms.strehl_arm()
print(f"{'roi':<14}{'prior mean':>11}{'strehl mean':>12}{'ratio':>8}{'  a (slope)':>12}{'  b (offset)':>12}{'  b/strehlmean':>15}{'  r2':>7}")
rows = []
for (y, x) in spec.DETAIL_ROIS[:12] + spec.FLAT_ROIS[:4]:
    T = 384
    va = P.g[y:y+T, x:x+T].astype(np.float64)
    cx, cy = S.px(x + T/2.0, y + T/2.0); Ts = int(round(T*S.scale))
    vb = S.g[int(round(cy-Ts/2)):int(round(cy-Ts/2))+Ts,
             int(round(cx-Ts/2)):int(round(cx-Ts/2))+Ts].astype(np.float64)
    if P.clip[y:y+T, x:x+T].any(): continue
    ca = ndimage.zoom(va, 24/T, order=1); cb = ndimage.zoom(vb, 24/Ts, order=1)
    n = min(ca.shape[0], cb.shape[0])
    A = np.stack([cb[:n,:n].ravel(), np.ones(n*n)], 1)
    sol, *_ = np.linalg.lstsq(A, ca[:n,:n].ravel(), rcond=None)
    pred = A @ sol
    r2 = 1 - ((ca[:n,:n].ravel()-pred)**2).sum() / ((ca[:n,:n].ravel()-ca.mean())**2).sum()
    rows.append((va.mean(), vb.mean(), sol[0], sol[1], r2))
    print(f"{str((y,x)):<14}{va.mean():>11.4f}{vb.mean():>12.4f}{va.mean()/vb.mean():>8.3f}"
          f"{sol[0]:>12.4f}{sol[1]:>12.5f}{sol[1]/vb.mean():>15.3f}{r2:>7.3f}")
r = np.array(rows)
print(f"\nmedian slope a = {np.median(r[:,2]):.4f}   median offset b = {np.median(r[:,3]):.5f}")
print("If b were 0, the contrast (sigma/mean) ratio would be 1.0 for a pure gain.")
print("Predicted contrast-variance ratio strehl/prior from (a,b) alone, per ROI:")
# contrast_prior = a*sigma_s/(a*mu_s+b);  contrast_strehl = sigma_s/mu_s
# ratio_var = (mu_p/(a*mu_s))^2 = ((a*mu_s+b)/(a*mu_s))^2
pred = ((r[:,2]*r[:,1] + r[:,3]) / (r[:,2]*r[:,1]))**2
print("  " + " ".join(f"{1/p:.3f}" for p in pred))
print(f"  median predicted strehl/prior contrast-variance ratio = {np.median(1/pred):.3f}")
