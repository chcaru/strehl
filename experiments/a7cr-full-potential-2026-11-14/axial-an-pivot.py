"""Pivot test: is the fixed inter-frame field a defocus walk (each colour pivots on its own focus, so the in-frame colour residual carries -d F / 5) or frame misregistration (slope 0)? Needs d5-resid.npy from axial-an-pairs.py.

  python -X utf8 axial-an-pivot.py
"""
import numpy as np
z=np.load('outputs/a7cr-axial-investigation/probe.npz')
JS=list(z['js']); T=int(z['tile']); W=int(z['w']); H=int(z['h'])
pk=z['peak']; con=z['contrast']; clipf=z['clipfrac']; kg=pk[1]; ty,tx=kg.shape
cx,cy=(W-1)/2,(H-1)/2
TX,TY=np.meshgrid((np.arange(tx)+.5)*T-.5-cx,(np.arange(ty)+.5)*T-.5-cy)
base=np.isfinite(kg)&(clipf==0)&(con[1]>3)
def good(r): return base&np.isfinite(r[...,0])&(r[...,2]>0.2)&(r[...,2]<5)&(r[...,3]<0.6)&(r[...,4]>0.5)&(np.abs(r[...,:2]).max(-1)<3)
def lsq(A,t):
    hw=np.ones(len(t))
    for _ in range(10):
        sw=np.sqrt(hw); p=np.linalg.lstsq(A*sw[:,None],t*sw,rcond=None)[0]
        r=t-A@p; s=1.4826*np.median(np.abs(r))+1e-9; hw=np.minimum(1,2*s/np.maximum(np.abs(r),1e-12))
    return p,r
def radial_resid(r,ok):
    x,y=TX[ok],TY[ok]; n=len(x); dx,dy=r[ok][:,0],r[ok][:,1]
    A=np.stack([np.concatenate([x,y]),np.concatenate([np.ones(n),np.zeros(n)]),np.concatenate([np.zeros(n),np.ones(n)])],1)
    p,res=lsq(A,np.concatenate([dx,dy]))
    out=np.full(r.shape[:2]+(2,),np.nan); out[ok]=np.stack([res[:n],res[n:]],1); return out
# fixed field from d5 similarity residuals (mean over pairs per tile)
R=np.load('outputs/a7cr-axial-investigation/d5-resid.npy'); k,x,y,dl,rx,ry=R.T[:6]
ix=((x+cx+.5)/T-.5).round().astype(int); iy=((y+cy+.5)/T-.5).round().astype(int)
S=np.zeros((ty,tx,2)); C=np.zeros((ty,tx)); np.add.at(S,(iy,ix),np.stack([rx,ry],1)); np.add.at(C,(iy,ix),1)
F=S/np.maximum(C,1)[...,None]; okF=C>=6
print('fixed field F (5-frame span, per-pair similarity removed): rms %.3f sensor px over %d tiles'%(2*np.sqrt((F[okF]**2).sum(-1).mean()),okF.sum()))
def reg(a,b,m):
    av=a[m].ravel(); bv=b[m].ravel(); s=(av*bv).sum()/(bv*bv).sum(); c=(av*bv).sum()/np.sqrt((av*av).sum()*(bv*bv).sum())
    # bootstrap over tiles
    idx=np.argwhere(m); rng=np.random.default_rng(0); bs=[]
    A=a[m]; B=b[m]
    for _ in range(400):
        q=rng.integers(0,len(A),len(A)); bs.append((A[q]*B[q]).sum()/(B[q]*B[q]).sum())
    return s,np.std(bs),c
def get(n,j): return z[n][JS.index(j)]
print('Walk test. Under a defocus walk (each colour pivots on its OWN focus) the in-frame colour residual at j=0 must be -d*F/5: slope -%.2f for red (d=4.8), -%.2f for blue (d=1.8). Under plain frame misregistration: 0.'%(4.8/5,1.8/5))
for n in ['rg','bg']:
    r=get(n,0); ok=good(r); res=radial_resid(r,ok); m=ok&okF
    s,se,c=reg(res,F,m); print('  %s(0) residual on F: slope %+.3f +- %.3f, corr %+.3f, n %d'%(n,s,se,c,m.sum()))
print('Sanity: the between-frame motion of each channel on F (expect ~+1 if F is what moves the frames 5 apart)')
for n in ['gg','rr','bb']:
    r=get(n,5); ok=good(r); res=radial_resid(r,ok); m=ok&okF
    s,se,c=reg(res,F,m); print('  %s(5) residual on F: slope %+.3f +- %.3f, corr %+.3f'%(n,s,se,c))
for j in [3,5,6]:
    r=get('rg',j); ok=good(r)&good(get('rg',0)); res=radial_resid(r,ok); m=ok&okF
    s,se,c=reg(res,F,m); print('  rg(%d) residual on F: slope %+.3f +- %.3f, corr %+.3f'%(j,s,se,c))
np.save('outputs/a7cr-axial-investigation/F5.npy',np.where(okF[...,None],F,np.nan))
