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
DIFF=mtf_diff(FT,n); Lf=np.fft.rfft(latent)
HK=np.stack([[mtf_disc(FT,abs(k-j)*step)*DIFF for k in range(K)] for j in range(K)])
PL=np.stack([np.fft.irfft(Lf*mtf_disc(FT,abs(d))*DIFF,Npx) for d in range(K)])
S_true=np.abs(Lf)**2/Npx
S_flat=np.full_like(S_true,S_true.mean())
S_1f2=1.0/np.maximum(FT,1e-3)**2; S_1f2*=S_true.sum()/S_1f2.sum()
S_10x=S_true*10.0; S_01x=S_true*0.1
depth=np.clip(x//(Npx//5),0,4)*(K-1)//4
dlat=np.gradient(latent)
def detail_corr(a):     # noise CANNOT inflate this: normalised correlation of gradients
    da=np.gradient(a)
    return float(np.dot(da,dlat)/np.sqrt(np.dot(da,da)*np.dot(dlat,dlat)))
def run(sigma,prior,tau,seed):
    r=np.random.default_rng(seed)
    Y=np.stack([PL[np.abs(k-depth),x]+r.normal(0,sigma,Npx) for k in range(K)])
    fm=np.stack([np.convolve(np.abs(np.gradient(y)),np.ones(27)/27,mode='same') for y in Y])
    sel=Y[np.argmax(fm,0),x]; Yf=np.fft.rfft(Y,axis=1); selF=np.fft.rfft(sel)
    wie=np.zeros(Npx); gua=np.zeros(Npx)
    for j in np.unique(depth):
        m=depth==j; Hk=HK[j]; sH2=(Hk**2).sum(0)
        num=(Hk*Yf).sum(0); nt=(sigma**2*Npx)/np.maximum(prior,1e-12)
        wie[m]=np.fft.irfft(num/(sH2+nt),Npx)[m]
        w=sH2/(sH2+tau*nt)
        gua[m]=np.fft.irfft(w*(num/(sH2+nt))+(1-w)*selF,Npx)[m]
    e=lambda a: float(np.sqrt(np.mean((a-latent)**2)))
    return (e(sel),e(wie),e(gua)),(detail_corr(sel),detail_corr(wie),detail_corr(gua))

print("=== 13. GUARD CONSTANT SWEEP -- is the win an artifact of tuning tau? ===")
print(f"{'sigma':>7} {'tau':>6} | {'RMSE sel':>9} {'wiener':>8} {'guarded':>8} | guarded/sel")
for sg in (0.01,0.03,0.05):
    for tau in (0.5,1.0,2.0,3.0,6.0,12.0):
        E=np.mean([run(sg,S_true,tau,300+s)[0] for s in range(3)],0)
        print(f"{sg:>7.3f} {tau:>6.1f} | {E[0]:>9.4f} {E[1]:>8.4f} {E[2]:>8.4f} | {E[2]/E[0]:.3f}")
    print()

print("=== 14. THE PRIOR IS NOT KNOWABLE. Does the guard survive a wrong S? (tau=3) ===")
print(f"{'sigma':>7} {'prior':>10} | {'sel':>8} {'wiener':>8} {'guarded':>8} | {'gua/sel':>8}")
for sg in (0.01,0.03,0.05):
    for lab,pr in (('oracle',S_true),('flat',S_flat),('1/f^2',S_1f2),('10x too big',S_10x),('10x too small',S_01x)):
        E=np.mean([run(sg,pr,3.0,600+s)[0] for s in range(3)],0)
        print(f"{sg:>7.3f} {lab:>10} | {E[0]:>8.4f} {E[1]:>8.4f} {E[2]:>8.4f} | {E[2]/E[0]:>8.3f}")
    print()

print("=== 15. NOISE-IMMUNE DETAIL METRIC (gradient correlation with truth; 1.0 = perfect) ===")
print(f"{'sigma':>7} | {'sel':>8} {'wiener':>8} {'guarded':>8}")
for sg in (0.002,0.01,0.02,0.03,0.05):
    G=np.mean([run(sg,S_true,3.0,800+s)[1] for s in range(3)],0)
    print(f"{sg:>7.3f} | {G[0]:>8.4f} {G[1]:>8.4f} {G[2]:>8.4f}")
