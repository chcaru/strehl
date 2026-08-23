"""V16 -- exact independent reproduction of M29 script 06's sep-1 displacement
column (the only column the D=0.999 refutation uses), plus (a) the same medians
from an independent Lucas-Kanade estimator, (b) a test of the script's own stated
model that breathing is a SCALE change so displacement must grow with radius."""
import glob, os
import numpy as np, rawpy
BLACK,T=512.0,256
def shift_est(a,b):
    a=a-a.mean(); b=b-b.mean()
    win=np.outer(np.hanning(a.shape[0]),np.hanning(a.shape[1]))
    A,B=np.fft.rfft2(a*win),np.fft.rfft2(b*win)
    R=A*np.conj(B); R/=np.maximum(np.abs(R),1e-12)
    c=np.fft.irfft2(R,s=a.shape)
    i,j=np.unravel_index(np.argmax(c),c.shape)
    def sub(v0,v1,v2):
        d=v0-2*v1+v2
        return 0.0 if abs(d)<1e-12 else 0.5*(v0-v2)/d
    dy=i+sub(c[(i-1)%c.shape[0],j],c[i,j],c[(i+1)%c.shape[0],j])
    dx=j+sub(c[i,(j-1)%c.shape[1]],c[i,j],c[i,(j+1)%c.shape[1]])
    if dy>a.shape[0]/2: dy-=a.shape[0]
    if dx>a.shape[1]/2: dx-=a.shape[1]
    return dy,dx
def lk(a,b):
    gy,gx=np.gradient(a); d=b-a
    M=np.array([[(gy*gy).sum(),(gy*gx).sum()],[(gy*gx).sum(),(gx*gx).sum()]])
    v=np.array([-(gy*d).sum(),-(gx*d).sum()])
    s=np.linalg.solve(M,v); return s[0],s[1]

PUB={"109MSDCF":[0.146,0.183,0.187,0.217],"coffee-bean":[0.117,0.107,0.123,0.075]}
for name,folder,nmax in (("109MSDCF",r"D:\personal\macro\109MSDCF",22),
                         ("coffee-bean",r"D:\personal\macro\coffee-bean",24)):
    files=sorted(glob.glob(os.path.join(folder,"*.ARW")))[:nmax]
    with rawpy.imread(files[0]) as r: h,w=r.raw_image_visible[0::2,1::2].shape
    cy,cx=h//2,w//2
    tiles=[]
    for fr in (0.15,0.35,0.55,0.75):
        for ang in (0,90,180,270):
            y=int(cy+fr*(h/2-T)*np.cos(np.radians(ang)))
            x=int(cx+fr*(w/2-T)*np.sin(np.radians(ang)))
            r_px=float(np.hypot(y-cy,x-cx))
            tiles.append((fr,y-T//2,x-T//2,r_px))
    stack=[]
    for f in files:
        with rawpy.imread(f) as r: g=r.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        stack.append([g[y:y+T,x:x+T].copy() for (_,y,x,_) in tiles])
    print(f"\n=== {name}: {len(stack)} frames, {len(tiles)} tiles, sep 1 ===")
    print(f"{'radius':>7s}{'r_px':>8s}{'phasecorr (M29)':>17s}{'published':>11s}"
          f"{'x2 (peak-lock)':>16s}{'Lucas-Kanade':>14s}")
    rr=[];dd=[]
    for i,fr in enumerate((0.15,0.35,0.55,0.75)):
        pc=[];lv=[];rpx=[]
        for ti,(f2,y,x,r_px) in enumerate(tiles):
            if f2!=fr: continue
            rpx.append(r_px)
            for k in range(len(stack)-1):
                dy,dx=shift_est(stack[k][ti],stack[k+1][ti])
                if abs(dy)<T/4 and abs(dx)<T/4: pc.append(np.hypot(dy,dx))
                dy2,dx2=lk(stack[k][ti],stack[k+1][ti]); lv.append(np.hypot(dy2,dx2))
        m=float(np.median(pc))
        rr.append(np.mean(rpx)); dd.append(m)
        print(f"{fr:7.2f}{np.mean(rpx):8.0f}{m:17.3f}{PUB[name][i]:11.3f}"
              f"{2*m:16.3f}{float(np.median(lv)):14.3f}")
    A=np.vstack([np.ones(4),rr]).T
    coef,_,_,_=np.linalg.lstsq(A,np.array(dd),rcond=None)
    print(f"  fit d = {coef[0]:.4f} + {coef[1]:.3e}*r_px   -> pure-scale model "
          f"needs intercept 0; translation term = {coef[0]:.3f} px")
    print(f"  ratio d(r=0.75)/d(r=0.15) = {dd[3]/dd[0]:.2f}   "
          f"(pure scale predicts {rr[3]/rr[0]:.2f})")
    del stack
