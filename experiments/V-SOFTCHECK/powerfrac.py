"""What fraction of my statistic's power sits in each band, under BOTH
readings of "cyc/px"?

The other lane's boundaries are quoted in "cyc/px" without saying whether px
means a photosite of the 7032x4688 sensor or a pixel of the 3516x2344 binned
output.  The two differ by exactly 2x.  Rather than guess, report my power
fractions under both, and let the measured focus response decide which
reading is consistent with their numbers.
"""
import numpy as np, softcheck as S
def prof(sig, n=512):
    d=np.zeros((n,n),np.float32); d[n//2,n//2]=1.0
    H=np.abs(np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(S.dog(d,sig)))))**2
    f=np.fft.fftshift(np.fft.fftfreq(n)); R=np.hypot(*np.meshgrid(f,f,indexing="ij"))
    return R.ravel(), H.ravel()
for name, sig in (("E_mid  (THE STATISTIC)", S.S_MID), ("E_hi   (noise proxy only)", S.S_HI)):
    R,H = prof(sig); tot=H.sum()
    print(f"\n{name}  sigma={sig}")
    print("  reading A -- their cyc/px == my OUTPUT pixel (binned 3516x2344):")
    for lab,a,b in (("below 0.20",0,0.20),("0.20-0.25 REAL",0.20,0.25),
                    ("0.25-0.30 marginal",0.25,0.30),("above 0.30 FAILS",0.30,10)):
        m=(R>=a)&(R<b); print(f"    {lab:20s} {100*H[m].sum()/tot:6.2f}% of power")
    print("  reading B -- their cyc/px == PHOTOSITE (sensor 7032x4688); my c/opx = 2x theirs:")
    for lab,a,b in (("below 0.20",0,0.40),("0.20-0.25 REAL",0.40,0.50),
                    ("0.25-0.30 marginal",0.50,0.60),("above 0.30 FAILS",0.60,10)):
        m=(R>=a)&(R<b); print(f"    {lab:20s} {100*H[m].sum()/tot:6.2f}% of power")
print("\nNyquist of the binned linear gauge is 0.50 cyc/output-px = 0.25 cyc/photosite.")
