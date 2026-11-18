"""Inter-frame residual of the alignment from axial-probe-pairs.py output: per frame pair, the similarity and affine the alignment left, what remains, and its dependence on defocus. Writes d1-resid.npy and d5-resid.npy beside the input.

  python -X utf8 axial-an-pairs.py   (reads probe.npz and pairs.npz in outputs/a7cr-axial-investigation/)
"""
import numpy as np
z=np.load('outputs/a7cr-axial-investigation/probe.npz'); q=np.load('outputs/a7cr-axial-investigation/pairs.npz')
T=int(z['tile']); W=int(z['w']); H=int(z['h'])
pk=z['peak']; con=z['contrast']; clipf=z['clipfrac']; kg=pk[1]
N=z['energy'].shape[0]; ty,tx=kg.shape
cx,cy=(W-1)/2,(H-1)/2
TX,TY=np.meshgrid((np.arange(tx)+.5)*T-.5-cx,(np.arange(ty)+.5)*T-.5-cy)
base=np.isfinite(kg)&(clipf==0)&(con[1]>3)
def good(r): return base&np.isfinite(r[...,0])&(r[...,2]>0.3)&(r[...,2]<3)&(r[...,3]<0.5)&(r[...,4]>0.5)&(np.abs(r[...,:2]).max(-1)<3)
def lsq(A,t,it=8):
    hw=np.ones(len(t))
    for _ in range(it):
        sw=np.sqrt(hw); p=np.linalg.lstsq(A*sw[:,None],t*sw,rcond=None)[0]
        r=t-A@p; s=1.4826*np.median(np.abs(r))+1e-9; hw=np.minimum(1,2*s/np.maximum(np.abs(r),1e-12))
    return p,r
for name,J in (('d1',1),('d5',5)):
    D=q[name]
    rows=[]
    tot=dict(raw=0,sim=0,aff=0,n=0)
    recs=[]
    for k in range(N-J):
        r=D[k]; delta=kg-(k+J/2)
        ok=good(r)&(np.abs(delta)<=8)
        n=ok.sum()
        if n<150: continue
        x,y=TX[ok],TY[ok]; dx,dy=r[ok][:,0],r[ok][:,1]
        # similarity: dx = s x - th y + tx ; dy = th x + s y + ty
        A=np.zeros((2*n,4)); A[:n,0]=x;A[:n,1]=-y;A[:n,2]=1;A[n:,0]=y;A[n:,1]=x;A[n:,3]=1
        ps,rs=lsq(A,np.concatenate([dx,dy]))
        A6=np.zeros((2*n,6)); A6[:n,0]=x;A6[:n,1]=y;A6[:n,2]=1;A6[n:,3]=x;A6[n:,4]=y;A6[n:,5]=1
        pa,ra=lsq(A6,np.concatenate([dx,dy]))
        tot['raw']+=(dx**2+dy**2).sum(); tot['sim']+=(rs**2).sum(); tot['aff']+=(ra**2).sum(); tot['n']+=n
        rows.append((k,n,ps[0]*1e6,ps[1]*1e6,ps[2]*2,ps[3]*2,2*np.sqrt((dx**2+dy**2).mean()),2*np.sqrt((rs**2).sum()/n),2*np.sqrt((ra**2).sum()/n)))
        recs.append(np.stack([np.full(n,k),x,y,delta[ok],rs[:n],rs[n:],dx,dy],1))
    rows=np.array(rows); R=np.concatenate(recs)
    print(f'== {name}: G(k+{J}) from G(k), tiles within 8 frames of focus; sensor px')
    print(' pooled rms raw %.3f | after per-pair similarity %.3f | after per-pair affine %.3f | pairs %d tiles %d'%(2*np.sqrt(tot['raw']/tot['n']),2*np.sqrt(tot['sim']/tot['n']),2*np.sqrt(tot['aff']/tot['n']),len(rows),tot['n']))
    print(' per-pair similarity the alignment left behind: scale ppm mean %.1f sd %.1f | rot urad mean %.1f sd %.1f | t sensor px mean (%.3f,%.3f) sd (%.3f,%.3f)'%(rows[:,2].mean(),rows[:,2].std(),rows[:,3].mean(),rows[:,3].std(),rows[:,4].mean(),rows[:,5].mean(),rows[:,4].std(),rows[:,5].std()))
    for r in rows[::max(1,len(rows)//12)]: print('   k=%3d n=%4d scale %+7.1f ppm rot %+7.1f urad t (%+.3f,%+.3f) rms raw %.3f sim-resid %.3f aff-resid %.3f'%tuple(r))
    # what explains the similarity residual? defocus delta
    k,x,y,dl,rx,ry=R[:,0],R[:,1],R[:,2],R[:,3],R[:,4],R[:,5]
    rr=np.hypot(x,y); ux,uy=x/np.maximum(rr,1),y/np.maximum(rr,1)
    rad=rx*ux+ry*uy; tan=-rx*uy+ry*ux
    print(' residual (after per-pair similarity) split: radial rms %.3f tangential rms %.3f'%(2*np.sqrt((rad**2).mean()),2*np.sqrt((tan**2).mean())))
    print(' by defocus bin (delta = tile focus frame - pair midpoint): mean radial residual / r  (ppm), mean residual vector, n')
    for lo,hi in [(-8,-5),(-5,-3),(-3,-1),(-1,1),(1,3),(3,5),(5,8)]:
        m=(dl>=lo)&(dl<hi)&(rr>500)
        s=(rad[m]*rr[m]).sum()/(rr[m]**2).sum()
        print('   [%+d,%+d) radial slope %+7.1f ppm  mean vec (%+.3f,%+.3f)  rms %.3f  n %d'%(lo,hi,s*1e6,2*rx[m].mean(),2*ry[m].mean(),2*np.sqrt((rx[m]**2+ry[m]**2).mean()),m.sum()))
    # models on residual: delta-linear scale + delta-linear translation
    n=len(x)
    cols=[np.concatenate([dl*x,dl*y]),np.concatenate([dl,np.zeros(n)]),np.concatenate([np.zeros(n),dl]),np.concatenate([-dl*y,dl*x])]
    A=np.stack(cols,1); p,res=lsq(A,np.concatenate([rx,ry]))
    print(' fit residual = delta*(a*(x,y) + rot + t): a %.2f ppm/frame-of-defocus, t (%.4f,%.4f) px/frame, rot %.2f urad/frame; rms %.3f -> %.3f'%(p[0]*1e6,2*p[1],2*p[2],p[3]*1e6,2*np.sqrt((rx**2+ry**2).mean()),2*np.sqrt((res**2).sum()/n)))
    np.save(f'outputs/a7cr-axial-investigation/{name}-resid.npy',R)
