import os, numpy as np, softcheck as S, hcoh as HC, ncurve as NC
d=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh\bee-1-cpl"
A=S.load_luma(os.path.join(d,"N298-A.tiff"),"srgb"); B=S.load_luma(os.path.join(d,"N298-B.tiff"),"srgb")
oy,ox=NC.pick_tiles(A); T=HC.T; P=HC.PRIMARY; E=HC.E; NB=HC.NB
rA=np.zeros((len(oy),NB)); rM=np.zeros((len(oy),NB)); gam=np.zeros((len(oy),NB))
for k in range(len(oy)):
    y,x=oy[k],ox[k]
    a=A[y:y+T,x:x+T].astype(np.float32); b=B[y:y+T,x:x+T].astype(np.float32)
    FA=HC._ft(a); FB=HC._ft(b); FB,_,_=HC._subpix(FA,FB)   # same registration the statistic uses
    FM=0.5*(FA+FB)
    PA=np.abs(FA)**2; PM=np.abs(FM)**2
    X=FA*np.conj(FB); PB=np.abs(FB)**2
    for i,m in enumerate(HC.MASK):
        rA[k,i]=PA[m].mean(); rM[k,i]=PM[m].mean()
        gam[k,i]=np.abs(X[m].sum())/np.sqrt(PA[m].sum()*PB[m].sum())
print("bee-1-cpl, two independently merged 149-frame halves, pin 9b05d0b7 (44C2F2CD2E5B2894)")
print("PLANTED COHERENCE-ONLY FIX: deliver (A+B)/2 instead of a half.")
print("  It scores f = 0.0000 exactly and half-difference noise = 0.0000 exactly:")
print("  a perfect score on both instruments the user warned are coherence-sensitive.\n")
print("  band          f = 1-gamma   delivered band power vs a half   closed-form (1+gamma)/2")
for i in range(NB):
    g=np.median(gam[:,i]); r=np.median(rM[:,i]/rA[:,i])
    star=" <== reporting band" if i==P else ""
    print("  %.2f-%.2f        %.4f            %.4f                     %.4f%s"%(E[i],E[i+1],1-g,r,(1+g)/2,star))
r=np.median(rM[:,P]/rA[:,P]); g=np.median(gam[:,P])
print()
print("  At the reporting band the coherence-only fix CHANGES DELIVERED BAND POWER BY %+.1f%%."%(100*(r-1)))
print("  Measured %.4f against the closed form (1+gamma)/2 = %.4f -- agreement to %.4f,"%(r,(1+g)/2,abs(r-(1+g)/2)))
print("  so the loss is arithmetic: averaging two arms retains the coherent part and")
print("  halves the power of whatever they disagree about.")
print("  A statistic on the DELIVERED master, against a reference fixed by the input")
print("  bracket, therefore CHARGES this fix instead of rewarding it.")
