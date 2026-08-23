import numpy as np
from scipy.special import j1
PITCH_UM,LAM_UM=5.12,0.550
def f_c(n): return PITCH_UM/(LAM_UM*n)
def mtf_diff(f,n):
    u=np.clip(np.asarray(f,float)/f_c(n),0,1)
    return (2/np.pi)*(np.arccos(u)-u*np.sqrt(np.maximum(0,1-u*u)))
def mtf_disc(f,d):
    x=np.pi*abs(d)*np.asarray(f,float); o=np.ones_like(x); nz=np.abs(x)>1e-12
    o[nz]=np.abs(2*j1(x[nz])/x[nz]); return o

Npx,K,step,n=2048,25,1.0,33.0
x=np.arange(Npx); FT=np.fft.rfftfreq(Npx)
latent=np.zeros(Npx)
for c,w in [(300,40),(700,8),(1100,4),(1500,2),(1900,60)]: latent[c-w//2:c+w//2]=1.0
latent+=0.15*np.sin(2*np.pi*x/17)
DIFF=mtf_diff(FT,n)
HK=np.stack([[mtf_disc(FT,abs(k-j)*step)*DIFF for k in range(K)] for j in range(K)])  # HK[j][k]
Lf=np.fft.rfft(latent)
PL=np.stack([np.fft.irfft(Lf*mtf_disc(FT,abs(d))*DIFF,Npx) for d in range(K)])  # blur by d steps
S_true=np.abs(Lf)**2/Npx
DEPTHS={
 'ramp (every pixel a depth boundary)': (x/Npx*(K-1)).astype(int),
 'slabs (5 piecewise-constant layers)': np.clip((x//(Npx//5)),0,4)*(K-1)//4,
 'single plane (null: no depth at all)': np.zeros(Npx,int),
}
def trial(depth,sigma,seed,prior):
    r=np.random.default_rng(seed)
    Y=np.stack([PL[np.abs(k-depth),x]+r.normal(0,sigma,Npx) for k in range(K)])
    fm=np.stack([np.convolve(np.abs(np.gradient(y)),np.ones(27)/27,mode='same') for y in Y])
    sel=Y[np.argmax(fm,0),x]; mean=Y.mean(0)
    Yf=np.fft.rfft(Y,axis=1); out=np.zeros(Npx); gate=np.zeros(Npx)
    for j in np.unique(depth):
        m=depth==j
        Hk=HK[j]; sH2=(Hk**2).sum(0)
        num=(Hk*Yf).sum(0); den=sH2+(sigma**2*Npx)/np.maximum(prior,1e-12)
        out[m]=np.fft.irfft(num/den,Npx)[m]
        # GUARDED: blend toward the SELECTED frame (no deconvolution) where sum|H|^2 is weak.
        noise_term=(sigma**2*Npx)/np.maximum(prior,1e-12)
        wgt=sH2/(sH2+3.0*noise_term)
        self_=np.fft.rfft(sel)
        gate[m]=np.fft.irfft(wgt*(num/den)+(1.0-wgt)*self_,Npx)[m]
    e=lambda a: float(np.sqrt(np.mean((a-latent)**2)))
    g=lambda a: float(np.mean(np.abs(np.gradient(a))))
    return (e(sel),e(mean),e(out),e(gate)), (g(sel),g(mean),g(out),g(gate))
gl=float(np.mean(np.abs(np.gradient(latent))))
print(f"latent mean|grad| = {gl:.4f}\n")
for name,depth in DEPTHS.items():
    print(f"=== depth model: {name} ===")
    print(f"{'sigma':>7} | {'RMSE sel':>9} {'mean':>8} {'wiener':>8} {'guarded':>8} | {'grad sel':>9} {'mean':>8} {'wiener':>8} {'guarded':>8} | winner(RMSE)")
    for sg in (0.002,0.01,0.02,0.03,0.05):
        E=[];G=[]
        for s in range(4):
            e,g=trial(depth,sg,500+s,S_true); E.append(e); G.append(g)
        E=np.mean(E,0); G=np.mean(G,0)
        w=['sel','mean','wiener','guarded'][int(np.argmin(E))]
        print(f"{sg:>7.3f} | {E[0]:>9.4f} {E[1]:>8.4f} {E[2]:>8.4f} {E[3]:>8.4f} | "
              f"{G[0]:>9.4f} {G[1]:>8.4f} {G[2]:>8.4f} {G[3]:>8.4f} | {w}")
    print()


