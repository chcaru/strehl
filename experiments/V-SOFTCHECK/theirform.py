"""Replicate the OTHER LANE'S focus construction, exactly as described, on my
own independently rendered data, on the SHIPPING GRID where cyc/px is
unambiguous.

Their construction, as corrected by ORCH:
  * selecting band 0.05-0.20 cyc/px  -- used ONLY to choose each tile's
    in-focus frame
  * reporting band 0.20-0.25 cyc/px  -- DISJOINT from the selecting band, so
    the argmax cannot bias the reported number
  * defocused side is a FIXED 20-step offset from the selected frame, NOT an
    argmin.  There is no minimisation over N on that side, so the winner's
    curse objection does not apply and I apply no discount for it.
  * per TILE, never per frame: in a focus stack "in focus" is a property of a
    tile in a frame.

Reported as a distribution across tiles, not a single number.
"""
import os, numpy as np, softcheck as S
subj="119MSDCF"; OFF=20
z=np.load(os.path.join(S.ROOT,"cache",f"{subj}--shipring.npz"))
Fr,E,N=z["Fr"],z["EDGES"],int(z["N"])
sb=[i for i in range(len(E)-1) if E[i]>=0.05-1e-9 and E[i+1]<=0.20+1e-9]
rb=[i for i in range(len(E)-1) if E[i]>=0.20-1e-9 and E[i+1]<=0.25+1e-9]
print(f"{subj}: N={N} frames, {Fr.shape[1]} tiles, SHIPPING GRID 7032x4688")
print(f"  selecting band {E[sb[0]]:.2f}-{E[sb[-1]+1]:.2f} cyc/px (bands {sb})")
print(f"  reporting band {E[rb[0]]:.2f}-{E[rb[-1]+1]:.2f} cyc/px (bands {rb})")
print(f"  disjoint: {set(sb).isdisjoint(set(rb))}")
selp=Fr[:,:,sb].mean(2); repp=Fr[:,:,rb].mean(2)
best=selp.argmax(0)
off=np.where(best+OFF<N, best+OFF, best-OFF)
ok=(off>=0)&(off<N)
r=repp[best[ok],np.arange(Fr.shape[1])[ok]]/np.maximum(repp[off[ok],np.arange(Fr.shape[1])[ok]],1e-30)
rng=np.random.default_rng(3); n=len(r)
ci=np.percentile([np.median(r[rng.integers(0,n,n)]) for _ in range(2000)],[2.5,97.5])
print(f"\n  PER-TILE (their construction)  n={n} tiles")
print(f"    R = {np.median(r):.3f}   CI [{ci[0]:.3f}, {ci[1]:.3f}]")
print(f"    quartiles {np.percentile(r,25):.2f} / {np.percentile(r,50):.2f} / {np.percentile(r,75):.2f}"
      f"   deciles {np.percentile(r,10):.2f} .. {np.percentile(r,90):.2f}")
print(f"    fraction of tiles with R>1 : {100*(r>1).mean():.1f}%")
wf_best=int(np.bincount(best).argmax()); wf_off=wf_best+OFF if wf_best+OFF<N else wf_best-OFF
rw=repp[wf_best]/np.maximum(repp[wf_off],1e-30)
print(f"\n  WHOLE-FRAME (the construction known to give a false null)")
print(f"    single frame {wf_best} vs {wf_off} for ALL tiles:  R = {np.median(rw):.3f}")
print(f"    per-tile / whole-frame suppression factor = {np.median(r)/np.median(rw):.2f}x")
print(f"\n  per band, same construction:")
for b in range(len(E)-1):
    p=Fr[:,:,b]
    rb2=p[best[ok],np.arange(Fr.shape[1])[ok]]/np.maximum(p[off[ok],np.arange(Fr.shape[1])[ok]],1e-30)
    print(f"    {E[b]:.2f}-{E[b+1]:.2f} cyc/px   R = {np.median(rb2):8.3f}")
