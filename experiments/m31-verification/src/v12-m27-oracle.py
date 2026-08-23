"""V12 -- M27 fact 213's 'deployable criterion' is computed with the FULL-STACK
minimum (script 05 nw_fix).  On a genuinely coarse bracket you do not have that.
What does the actually-deployable (own-min) version read?"""
import numpy as np
vol=np.load(r"C:\dev\blog\death-of-software\projects\strehl\experiments\m31-verification\out\cb_vol_mine.npy")
n=vol.shape[0]; fmin_full=vol.min(0)
k_full=vol.argmax(0); fk_full=np.take_along_axis(vol,k_full[None],0)[0]
c_full=(fk_full-fmin_full)/np.maximum(fk_full,1e-6)
rel=(c_full>0.6)&(k_full>2)&(k_full<n-3)&(fk_full>np.percentile(fk_full,50))
print(f"reliable {int(rel.sum()):,} of {rel.size:,} ({100*rel.mean():.1f}%)\n")
print(f"{'step':>5}{'frames':>8}{'<=1 FULL-min (published)':>26}{'<=1 own-min (deployable)':>26}"
      f"{'<=1 own-min ALL px':>21}")
for s in (1,2,3,4,6):
    sub=vol[::s]; fk=sub.max(0); om=sub.min(0)
    fix=(sub>=(fmin_full+0.5*(fk-fmin_full))[None]).sum(0)
    own=(sub>=(om+0.5*(fk-om))[None]).sum(0)
    print(f"{s:>5}{sub.shape[0]:>8}{100*float((fix[rel]<=1).mean()):>25.2f}%"
          f"{100*float((own[rel]<=1).mean()):>25.2f}%{100*float((own<=1).mean()):>20.2f}%")
print("\nSanity: the two thresholds differ because own-min > full-min once frames")
print("are dropped; own-min RAISES the half-height bar and so LOWERS nwide.")
