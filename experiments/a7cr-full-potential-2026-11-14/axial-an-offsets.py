"""Colour-against-green and same-channel displacement versus frame offset j, from axial-probe.py output: radial fit, residual scatter, neighbour coherence; and band energy at k + j against k.

  python -X utf8 axial-an-offsets.py   (reads outputs/a7cr-axial-investigation/probe.npz)
"""
import numpy as np
z=np.load('outputs/a7cr-axial-investigation/probe.npz')
JS=list(z['js']); T=int(z['tile']); W=int(z['w']); H=int(z['h'])
E=z['energy']; pk=z['peak']; con=z['contrast']; clipf=z['clipfrac']
N,_,ty,tx=E.shape
kg=pk[1]
cx,cy=(W-1)/2,(H-1)/2
TX,TY=np.meshgrid((np.arange(tx)+.5)*T-.5-cx,(np.arange(ty)+.5)*T-.5-cy)
hd=np.hypot(cx,cy)
base=np.isfinite(kg)&(clipf==0)&(con[1]>3)
print('usable tiles',base.sum())
def fit(A,t):
    hw=np.ones(len(t))
    for _ in range(10):
        sw=np.sqrt(hw); p=np.linalg.lstsq(A*sw[:,None],t*sw,rcond=None)[0]
        r=t-A@p; s=1.4826*np.median(np.abs(r))+1e-9; hw=np.minimum(1,2*s/np.maximum(np.abs(r),1e-12))
    return p,r
def rms(dx,dy): return np.sqrt(np.mean(dx**2+dy**2))
def robust(dx,dy): return 1.4826*np.median(np.hypot(dx,dy))
print('all displacement figures in SENSOR px (plane px x2); eps in ppm')
for name in ['rg','bg','gg','rr']:
    print('==',name)
    for ji,j in enumerate(JS):
        r=z[name][ji]
        ok=base&np.isfinite(r[...,0])&(r[...,2]>0.2)&(r[...,2]<5)&(r[...,3]<0.6)&(r[...,4]>0.5)&(np.abs(r[...,:2]).max(-1)<3)
        if ok.sum()<50: print(j,'n',ok.sum()); continue
        x,y=TX[ok],TY[ok]; dx,dy=r[ok][:,0],r[ok][:,1]
        n=len(x)
        # radial + translation
        A=np.stack([np.concatenate([x,y]),np.concatenate([np.ones(n),np.zeros(n)]),np.concatenate([np.zeros(n),np.ones(n)])],1)
        p,res=fit(A,np.concatenate([dx,dy]))
        rx,ry=res[:n],res[n:]
        # similarity+affine: 6 dof
        A6=np.zeros((2*n,6)); A6[:n,0]=x;A6[:n,1]=y;A6[:n,2]=1;A6[n:,3]=x;A6[n:,4]=y;A6[n:,5]=1
        p6,res6=fit(A6,np.concatenate([dx,dy]))
        # neighbour coherence of radial-model residual
        R=np.full((ty,tx,2),np.nan); R[ok]=np.stack([rx,ry],1)
        a=R[:,:-1];b=R[:,1:]; m=np.isfinite(a[...,0])&np.isfinite(b[...,0])
        coh=(a[m]*b[m]).sum()/np.sqrt((a[m]**2).sum()*(b[m]**2).sum())
        # per-frame mean residual
        k=np.round(kg[ok]).astype(int); 
        fm=[(rx[k==q].mean(),ry[k==q].mean(),(k==q).sum()) for q in np.unique(k) if (k==q).sum()>=15]
        fm=np.array(fm); frm=np.sqrt(np.average(fm[:,0]**2+fm[:,1]**2,weights=fm[:,2])) if len(fm) else np.nan
        print(f'j={j:+d} n={n:4d} a_med={np.median(r[ok][:,2]):.2f} eps={p[0]*1e6:+7.1f} t=({2*p[1]:+.3f},{2*p[2]:+.3f}) rms raw {2*rms(dx,dy):.3f} radial-resid {2*rms(rx,ry):.3f} (robust {2*robust(rx,ry):.3f}) affine-resid {2*rms(res6[:n],res6[n:]):.3f} nb-coh {coh:+.2f} per-frame-mean rms {2*frm:.3f}')
# sharpness available: energy ratio at k+j vs k for red, at green-focus tiles
print('== band energy of X at frame round(kg)+j relative to j=0 (amplitude = sqrt), median over usable tiles')
for c,nm in ((0,'red'),(1,'green'),(2,'blue')):
    out=[]
    for j in [-6,-3,0,1,2,3,4,5,6,7,9]:
        v=[]
        for (yy,xx) in np.argwhere(base):
            k=int(round(kg[yy,xx]))
            if 0<=k+j<N: v.append(E[k+j,c,yy,xx]/E[k,c,yy,xx])
        out.append(f'{j:+d}:{np.sqrt(np.median(v)):.3f}')
    print(nm,' '.join(out))
d=pk-kg
for c,nm in ((0,'red'),(2,'blue')):
    m=base&np.isfinite(d[c]); print(nm,'peak offset median',np.median(d[c][m]),'IQR',np.percentile(d[c][m],[25,75]),'n',m.sum())
