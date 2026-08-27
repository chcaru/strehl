"""Where in frequency does my focus signal live, and does the merge deficit
survive there?

Two quantities per ring band, both per tile:
  FOCUS RESPONSE  best-focus / worst-focus frame, with the frames chosen by
                  the OTHER instrument (DoG E_mid) so the arm is not circular
                  and is not bounded below by 1.
  MERGE DEFICIT   master / per-site max over the COMPLETE bracket, i.e. the
                  headline measurement, restricted to that band.

If the deficit only exists in bands where the focus response has already
collapsed, the deficit is a noise artifact.  If it persists in the bands that
demonstrably carry focus, it is optical.

cyc per OUTPUT pixel; the linear gauge is 2x2 binned so cyc/photosite is half.
"""
import os, sys, numpy as np, softcheck as S
def boot(v,B=1500,seed=5):
    rng=np.random.default_rng(seed); n=len(v)
    m=[np.median(v[rng.integers(0,n,n)]) for _ in range(B)]
    return np.percentile(m,2.5), np.percentile(m,97.5)
for subj in ("119MSDCF","coffee-bubbles","109MSDCF","flower-bud-alone-cpl"):
    z=np.load(os.path.join(S.ROOT,"cache",f"{subj}--ring.npz"))
    Mr,Fr,Fm,E = z["Mr"],z["Fr"],z["Fm"],z["EDGES"]
    N,nt,nb = Fr.shape; idx=np.arange(nt)
    kb, kw = Fm.argmax(0), Fm.argmin(0)     # frames chosen by the OTHER instrument
    print(f"\n=== {subj}  (N={N}, {nt} tiles, frames chosen per tile by DoG E_mid)")
    print(f"  {'band c/opx':>13s} {'c/photosite':>13s} {'FOCUS best/worst':>28s} "
          f"{'MERGE deficit':>26s} {'verdict':>10s}")
    for b in range(nb):
        f = Fr[kb,idx,b]/np.maximum(Fr[kw,idx,b],1e-30)
        dfl = Mr[:,b]/np.maximum(Fr[:,:,b].max(0),1e-30)
        fc = boot(f); dc = boot(dfl)
        lab=f"{E[b]:.2f}-{E[b+1]:.2f}"; lab2=f"{E[b]/2:.3f}-{E[b+1]/2:.3f}"
        v = "focus OK" if fc[0] > 2.0 else ("marginal" if fc[0] > 1.3 else "BLIND")
        print(f"  {lab:>13s} {lab2:>13s} {np.median(f):9.2f} [{fc[0]:6.2f},{fc[1]:7.2f}]"
              f" {np.median(dfl):9.4f} [{dc[0]:.4f},{dc[1]:.4f}] {v:>10s}")
