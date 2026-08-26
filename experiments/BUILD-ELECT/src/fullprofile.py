"""Print the FULL radial backdrop profile to the frame limit, both arms.

No verdict, no reference window chosen in advance. The point is to find out
where the profile actually flattens, because peaksite.py assumed 600-1400 px
was far field AND used 700-1050 as its null -- the null was inside the
reference, and if the defect reaches that far both are contaminated together.
"""
import sys
import numpy as np
import ringprofile as rp

FB = r"C:\dev\strehl-out\BUILD-BLEND\flip\flower-bud-alone-cpl--{}.tiff"
STEP = 50

mask, thr, kept, found = rp.subject_mask(rp.load_luma(FB.format("estimator")))
signed = rp.signed_distance(mask)
print(f"shared mask from estimator arm: {mask.mean()*100:.2f}% of frame, "
      f"thr {thr:.0f} DN, {kept} of {found} components")
print(f"max outward distance available: {signed.max():.0f} px")
print()

prof = {}
for arm in ("pyramid", "estimator"):
    lum = rp.load_luma(FB.format(arm))
    ds, vs, ns = [], [], []
    for d in range(0, int(signed.max()), STEP):
        m = (signed >= d) & (signed < d + STEP)
        n = int(m.sum())
        if n < 2000:
            continue
        ds.append(d + STEP / 2)
        vs.append(float(np.median(lum[m])))
        ns.append(n)
    prof[arm] = (np.array(ds), np.array(vs), np.array(ns))
    print(f"{arm}: {len(ds)} bins, backdrop clipped at 65535 = "
          f"{100.0*float((lum[signed>0]>=65535).mean()):.3f}% of backdrop")
print()

dp, vp, npx = prof["pyramid"]
de, ve, _ = prof["estimator"]
assert np.array_equal(dp, de), "bin grids differ"
print(f"  {'d px':>7} {'px':>10} | {'pyramid DN':>11} {'estimator DN':>13} "
      f"| {'pyr /max':>9} {'est /max':>9}")
for i in range(len(dp)):
    print(f"  {dp[i]:>7.0f} {npx[i]:>10d} | {vp[i]:>11.0f} {ve[i]:>13.0f} "
          f"| {vp[i]/vp.max():>9.4f} {ve[i]/ve.max():>9.4f}")
