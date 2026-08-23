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
depth=np.clip(x//(Npx//5),0,4)*(K-1)//4
dlat=np.gradient(latent)
def dcorr(a):
    da=np.gradient(a); return float(np.dot(da,dlat)/np.sqrt(np.dot(da,da)*np.dot(dlat,dlat)))
def smooth(v,w=9):
    k=np.ones(w)/w; return np.convolve(v,k,mode='same')

def run(sigma,mode,tau,seed):
    r=np.random.default_rng(seed)
    Y=np.stack([PL[np.abs(k-depth),x]+r.normal(0,sigma,Npx) for k in range(K)])
    fm=np.stack([np.convolve(np.abs(np.gradient(y)),np.ones(27)/27,mode='same') for y in Y])
    sel=Y[np.argmax(fm,0),x]; Yf=np.fft.rfft(Y,axis=1); selF=np.fft.rfft(sel)
    nvar=sigma**2*Npx
    if   mode=='oracle': prior=S_true
    elif mode=='est-sel':                       # from the selected frame, deconvolved by its own OTF
        prior=np.maximum(smooth(np.abs(selF)**2/Npx)-sigma**2, 1e-6)/np.maximum(DIFF**2,1e-3)
    elif mode=='est-mf':                        # from the matched-filter output
        j0=K//2; Hk=HK[j0]; sH2=(Hk**2).sum(0)
        mf=np.abs((Hk*Yf).sum(0))**2/np.maximum(sH2,1e-9)**2
        prior=np.maximum(smooth(mf/Npx)-nvar/np.maximum(sH2,1e-9)/Npx, 1e-6)
    elif mode=='powerlaw':                      # fit S = A f^-b to the selected frame's spectrum
        P=smooth(np.abs(selF)**2/Npx); m=(FT>0.01)&(FT<f_c(n))
        b,a=np.polyfit(np.log(FT[m]),np.log(np.maximum(P[m],1e-12)),1)
        prior=np.exp(a)*np.maximum(FT,1e-3)**b
    wie=np.zeros(Npx); gua=np.zeros(Npx)
    for j in np.unique(depth):
        m=depth==j; Hk=HK[j]; sH2=(Hk**2).sum(0)
        num=(Hk*Yf).sum(0); nt=nvar/np.maximum(prior,1e-12)
        wie[m]=np.fft.irfft(num/(sH2+nt),Npx)[m]
        w=sH2/(sH2+tau*nt)
        gua[m]=np.fft.irfft(w*(num/(sH2+nt))+(1-w)*selF,Npx)[m]
    e=lambda a: float(np.sqrt(np.mean((a-latent)**2)))
    return (e(sel),e(wie),e(gua)),(dcorr(sel),dcorr(wie),dcorr(gua))

print("=== 16. DATA-ESTIMATED PRIOR: does the reframe survive without oracle knowledge? ===")
print("    tau=3. 4 seeds. 'gua/sel' < 1.0 means the deconvolution merge BEATS plain selection.")
print(f"{'sigma':>7} {'prior mode':>11} | {'RMSE sel':>9} {'wiener':>8} {'guarded':>8} | {'gua/sel':>8} | {'dcorr sel':>10} {'dcorr gua':>10}")
for sg in (0.01,0.02,0.03,0.05):
    for mode in ('oracle','est-sel','est-mf','powerlaw'):
        R=[run(sg,mode,3.0,900+s) for s in range(4)]
        E=np.mean([q[0] for q in R],0); G=np.mean([q[1] for q in R],0)
        print(f"{sg:>7.3f} {mode:>11} | {E[0]:>9.4f} {E[1]:>8.4f} {E[2]:>8.4f} | {E[2]/E[0]:>8.3f} | {G[0]:>10.4f} {G[2]:>10.4f}")
    print()
