"""Is the scale-independent contrast gap a GRADE or a RESOLUTION difference?

A grade difference shows up as a LOCAL SLOPE d(prior)/d(strehl) that exceeds the
level ratio prior/strehl at the tones the subject occupies.  Measure the transfer
curve between the arms non-parametrically, at a coarse scale (16x BOX average --
box, not zoom: zoom(order=1) subsamples and aliases) where the 3.5% raster
mismatch is a fraction of a coarse pixel.
"""
import numpy as np, arms, spec

def box(a, f):
    h = (a.shape[0]//f)*f; w = (a.shape[1]//f)*f
    return a[:h,:w].reshape(h//f, f, w//f, f).mean(axis=(1,3))

P = arms.prior_arm(); S = arms.strehl_arm()
F = 24
pa, pb = [], []
for (y, x) in spec.DETAIL_ROIS + spec.FLAT_ROIS:
    T = 384
    if P.clip[y:y+T, x:x+T].any(): continue
    va = box(P.g[y:y+T, x:x+T].astype(np.float64), F)
    cx, cy = S.px(x+T/2.0, y+T/2.0); Ts = int(round(T*S.scale))
    y0 = int(round(cy-Ts/2)); x0 = int(round(cx-Ts/2))
    vb = box(S.g[y0:y0+Ts, x0:x0+Ts].astype(np.float64), int(round(F*S.scale)))
    n = min(va.shape[0], vb.shape[0])
    pa.append(va[:n,:n].ravel()); pb.append(vb[:n,:n].ravel())
pa = np.concatenate(pa); pb = np.concatenate(pb)
print("coarse sample pairs:", len(pa))
# non-parametric transfer curve prior(strehl)
q = np.quantile(pb, np.linspace(0.005, 0.995, 26))
print(f"\n{'strehl bin':>14}{'n':>7}{'strehl':>9}{'prior':>9}{'level ratio':>13}{'local slope':>13}{'gain factor':>13}")
cent, val = [], []
for i in range(len(q)-1):
    m = (pb >= q[i]) & (pb < q[i+1])
    if m.sum() < 50: continue
    cent.append(pb[m].mean()); val.append(pa[m].mean())
cent = np.array(cent); val = np.array(val)
sl = np.gradient(val, cent)
for c, v, s in zip(cent, val, sl):
    print(f"{'':>14}{0:>7}{c:>9.4f}{v:>9.4f}{v/c:>13.3f}{s:>13.3f}{s/(v/c):>13.3f}")
print("\nlocal slope / level ratio  ==  how much MORE contrast prior renders at that tone")
m = (cent > 0.08) & (cent < 0.35)     # the bean's tonal range
print(f"  over the BEAN range (strehl linear 0.08-0.35): median {np.median((sl/(val/cent))[m]):.3f}")
m2 = cent > 0.5
if m2.any():
    print(f"  over the PAPER range (>0.5):                  median {np.median((sl/(val/cent))[m2]):.3f}")
print(f"\nimplied contrast-VARIANCE ratio strehl/prior from grade alone, bean range: "
      f"{1/np.median((sl/(val/cent))[m])**2:.3f}")
