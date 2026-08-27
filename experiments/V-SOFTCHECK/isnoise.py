"""Is the master's excess band energy on the flat half NOISE or FINE TEXTURE?

Discriminator: the spectral shape ratio E_hi/E_mid.
  - pure white noise  -> E_hi/E_mid = G_HI/G_MID = 0.421466/0.078008 = 5.403
  - resolved detail   -> much lower, because real structure is concentrated
    at lower spatial frequency than my hi probe band.
If the master's flat-half shape sits at the white-noise value, its excess is
noise and my band-energy statistic cannot be trusted on that subject.
"""
import numpy as np
from analyze import load
WHITE = 0.421466/0.078008
print(f"white-noise value of E_hi/E_mid = {WHITE:.3f}\n")
print(f"{'subject':22s} {'MASTER flat':>11s} {'frames flat':>11s} {'MASTER detail':>13s} "
      f"{'frames detail':>13s} {'master flat/white':>18s}")
for subj in ("119MSDCF","coffee-bubbles","109MSDCF","flower-bud-alone-cpl"):
    c=load(subj,"lin",128)
    M=np.asarray(c["m_mid_none"]); Mh=np.asarray(c["m_hi_none"])
    F=np.asarray(c["f_mid_none"]).mean(0); Fh=np.asarray(c["f_hi_none"]).mean(0)
    lo=np.asarray(c["m_lo"]); sel=lo>=np.median(lo); flat=~sel
    mf=np.median(Mh[flat]/M[flat]); ff=np.median(Fh[flat]/F[flat])
    md=np.median(Mh[sel]/M[sel]);   fd=np.median(Fh[sel]/F[sel])
    print(f"{subj:22s} {mf:11.3f} {ff:11.3f} {md:13.3f} {fd:13.3f} {mf/WHITE:18.2f}")
print()
print("A value near 5.40 means that region's energy is indistinguishable from white noise.")
