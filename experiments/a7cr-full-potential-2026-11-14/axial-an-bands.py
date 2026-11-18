"""Per-band energy of the gathered red/blue plane at frame k+j vs k, tiles in focus (green) at k.
Bands in plane frequency: top = plane - gauss(0.6); upper-mid = gauss(0.6)-gauss(1.2); mid = gauss(1.2)-gauss(2.4); low = gauss(2.4)-gauss(4.8)."""
import sys, numpy as np, torch
from pathlib import Path
sys.path.insert(0,'experiments/a7cr-full-potential-2026-11-14'); import fp
O=Path('outputs/a7cr-axial-investigation'); z=np.load(O/'probe.npz')
T=int(z['tile']); W=int(z['w']); H=int(z['h']); kg=z['peak'][1]; con=z['contrast']; clipf=z['clipfrac']; ty,tx=kg.shape
base=np.isfinite(kg)&(clipf==0)&(con[1]>3)
files=sorted((O/'planes').glob('f*.f32')); N=len(files); dev=fp.DEV
def pool(v): return v[:ty*T,:tx*T].reshape(ty,T,tx,T).mean((1,3)).cpu().numpy()
SIG=[0.6,1.2,2.4,4.8]; names=['top (>0.27 c/plane px)','upper-mid','mid','low']
JS=[0,2,5,6]
cache={}
def en(i):
    if i not in cache:
        for o in [k for k in cache if k<i-8]: del cache[o]
        p=torch.from_numpy(np.fromfile(files[i],dtype='<f4').reshape(3,H,W)).to(dev)
        out=np.zeros((3,4,ty,tx))
        for c in range(3):
            g=[p[c]]+[fp.gauss(p[c],s) for s in SIG]
            for b in range(4): out[c,b]=pool((g[b]-g[b+1])**2)
        cache[i]=out
    return cache[i]
kint=np.where(base,np.round(kg),-1).astype(int)
acc={j:[] for j in JS}
for k in range(N):
    sel=kint==k
    if not sel.any() or k+max(JS)>=N: continue
    e0=en(k)
    for j in JS:
        acc[j].append(np.stack([en(k+j)[:,:,sel],e0[:,:,sel]],0))
print('amplitude of the plane at frame k+j relative to frame k (median over tiles in focus for green at k):')
for j in JS[1:]:
    a=np.concatenate(acc[j],-1)  # [2,3,4,n]
    r=np.sqrt(np.median(a[0]/a[1],-1))
    for c,nm in ((0,'red'),(1,'green'),(2,'blue')):
        print(f' j=+{j} {nm:5s} '+'  '.join(f'{names[b]}: {r[c,b]:.3f}' for b in range(4)))
