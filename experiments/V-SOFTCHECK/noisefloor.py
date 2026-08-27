"""How much noise does the master carry relative to its own frames?

E_hi = DoG(0.35,0.7)^2 is my white-noise proxy.  If the master's E_hi far
exceeds the frames', then the NOSUB arm (which counts noise as signal) is
scoring the master on its own amplified noise, and the two noise arms will
disagree -- which is exactly the condition under which neither arm decides
the sign.  Reported on the FLAT half, where there is no real detail to
confuse the proxy, as well as the detail half.
"""
import numpy as np
from analyze import load
print(f"{'subject':22s} {'N':>4s} {'Ehi m/f detail':>14s} {'Ehi m/f FLAT':>12s} "
      f"{'Emid m/f FLAT':>13s} {'NOSUB':>8s} {'SUB':>8s}")
CN=0.185088
for subj in ("119MSDCF","coffee-bubbles","109MSDCF","flower-bud-alone-cpl"):
    c=load(subj,"lin",128); N=int(c["N"])
    M=np.asarray(c["m_mid_none"]); Mh=np.asarray(c["m_hi_none"])
    F=np.asarray(c["f_mid_none"]); Fh=np.asarray(c["f_hi_none"])
    lo=np.asarray(c["m_lo"]); sel=lo>=np.median(lo); flat=~sel
    hd = np.median(Mh[sel]/Fh.mean(0)[sel]); hf = np.median(Mh[flat]/Fh.mean(0)[flat])
    mf = np.median(M[flat]/F.mean(0)[flat])
    ns = np.median(M[sel]/F[:,sel].max(0)); sb=np.median((M-CN*Mh)[sel]/(F-CN*Fh)[:,sel].max(0))
    print(f"{subj:22s} {N:4d} {hd:14.3f} {hf:12.3f} {mf:13.3f} {ns:8.4f} {sb:8.4f}")
print()
print("m/f > 1 means the MASTER carries more of that band than the average frame.")
print("On the flat half there is no detail, so any excess is noise the merge added.")
