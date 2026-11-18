"""Predicted colour registration after re-registering the borrowed frame on green: rg(j) - gg(j) per tile against rg(j) as shipped. Optimistic by construction (both terms share the reference and the instrument); the render comparison is the test.

  python -X utf8 axial-an-reregister.py
"""
import numpy as np
from scipy.ndimage import uniform_filter
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
def radial(d,ok):
    x,y=TX[ok],TY[ok]; n=len(x); dx,dy=d[ok][:,0],d[ok][:,1]
    A=np.stack([np.concatenate([x,y]),np.concatenate([np.ones(n),np.zeros(n)]),np.concatenate([np.zeros(n),np.ones(n)])],1)
    p,res=lsq(A,np.concatenate([dx,dy])); return p[0]*1e6, 2*np.sqrt((res**2).sum()/n), 2*1.4826*np.median(np.hypot(res[:n],res[n:]))
def get(n,j): return z[n][JS.index(j)]
print('colour-vs-green registration scatter about a radial model (sensor px rms; robust), tiles in focus at k')
for n,ref in (('rg','gg'),('bg','gg')):
    r0=get(n,0); ok0=good(r0); e,s,rb=radial(r0[...,:2],ok0)
    print(f' {n} j=0 (today, lateral only): eps {e:+.1f} ppm, scatter {s:.3f} ({rb:.3f}) n {ok0.sum()}')
    for j in ([3,5,6] if n=='rg' else [1,2,3]):
        r=get(n,j); g=get(ref,j); ok=good(r)&good(g)&ok0
        e,s,rb=radial(r[...,:2],ok); print(f' {n} j={j} borrowed, as shipped:           eps {e:+.1f}, scatter {s:.3f} ({rb:.3f})')
        e,s,rb=radial(r[...,:2]-g[...,:2],ok); print(f' {n} j={j} borrowed, re-registered on green per tile: eps {e:+.1f}, scatter {s:.3f} ({rb:.3f})')
        # 3x3 smoothed green field (valid tiles only)
        gv=np.where(good(g)[...,None],g[...,:2],0.0); w=good(g).astype(float)
        num=np.stack([uniform_filter(gv[...,c],3,mode='constant') for c in range(2)],-1); den=uniform_filter(w,3,mode='constant')
        gs=num/np.maximum(den,1e-9)[...,None]; ok2=ok&(den>0.3)
        e,s,rb=radial(r[...,:2]-gs,ok2); print(f' {n} j={j} borrowed, re-registered on green, 3x3-tile smooth field: eps {e:+.1f}, scatter {s:.3f} ({rb:.3f})')
