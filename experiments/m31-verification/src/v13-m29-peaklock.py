"""V13 -- M29 script 06 measures 0.07-0.22 green px adjacent-frame displacement
by phase correlation + parabolic subpixel fit.  Below ~0.5 px the correlation
peak sits at lag 0 and a parabolic fit there is the classic peak-locking case.
Control: plant a KNOWN Fourier subpixel shift into a real tile and see what the
identical estimator returns.  Then cross-check with an unbiased gradient
(Lucas-Kanade) estimator on the real adjacent pairs."""
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

def fshift(a,dy,dx):
    ky=np.fft.fftfreq(a.shape[0])[:,None]; kx=np.fft.fftfreq(a.shape[1])[None,:]
    return np.real(np.fft.ifft2(np.fft.fft2(a)*np.exp(-2j*np.pi*(ky*dy+kx*dx))))

def lk(a,b):
    """gradient least squares: b(x) ~ a(x - d).  Unbiased for small d."""
    gy,gx=np.gradient(a)
    d=b-a
    M=np.array([[ (gy*gy).sum(),(gy*gx).sum()],[(gy*gx).sum(),(gx*gx).sum()]])
    v=np.array([-(gy*d).sum(),-(gx*d).sum()])
    s=np.linalg.solve(M,v)
    return s[0],s[1]

def green(p):
    with rawpy.imread(p) as r: return r.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK

for name,folder in (("109MSDCF",r"D:\personal\macro\109MSDCF"),
                    ("coffee-bean",r"D:\personal\macro\coffee-bean")):
    fs=sorted(glob.glob(os.path.join(folder,"*.ARW")))
    g0=green(fs[0]); g1=green(fs[1])
    h,w=g0.shape; cy,cx=h//2,w//2
    print(f"\n=== {name}  green plane {g0.shape} ===")
    tiles=[]
    for fr in (0.15,0.35,0.55,0.75):
        for ang in (0,90,180,270):
            y=int(cy+fr*(h/2-T)*np.cos(np.radians(ang)))
            x=int(cx+fr*(w/2-T)*np.sin(np.radians(ang)))
            tiles.append((fr,y-T//2,x-T//2))
    print("  PLANT CONTROL: known Fourier shift applied to frame-0 tiles, "
          "recovered by the M29 estimator")
    print(f"    {'true dy':>9s}{'phasecorr median':>19s}{'ratio':>8s}{'LK median':>12s}{'ratio':>8s}")
    for true in (0.05,0.1,0.2,0.3,0.5,0.8,1.0,2.0):
        pc=[];lkv=[]
        for (fr,y,x) in tiles:
            a=g0[y:y+T,x:x+T]
            b=fshift(g0[y-8:y+T+8,x-8:x+T+8],true,0.0)[8:-8,8:-8]
            dy,dx=shift_est(a,b); pc.append(np.hypot(dy,dx))
            dy2,dx2=lk(a,b); lkv.append(np.hypot(dy2,dx2))
        print(f"    {true:9.2f}{np.median(pc):19.4f}{np.median(pc)/true:8.2f}"
              f"{np.median(lkv):12.4f}{np.median(lkv)/true:8.2f}")
    print("  REAL adjacent pair (frames 0,1), same tiles, two estimators:")
    print(f"    {'radius':>8s}{'phasecorr (M29)':>17s}{'Lucas-Kanade':>15s}")
    for fr in (0.15,0.35,0.55,0.75):
        pc=[];lkv=[]
        for (f2,y,x) in tiles:
            if f2!=fr: continue
            a=g0[y:y+T,x:x+T]; b=g1[y:y+T,x:x+T]
            dy,dx=shift_est(a,b); pc.append(np.hypot(dy,dx))
            dy2,dx2=lk(a,b); lkv.append(np.hypot(dy2,dx2))
        print(f"    {fr:8.2f}{np.median(pc):17.3f}{np.median(lkv):15.3f}")
