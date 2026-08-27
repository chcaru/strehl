"""Registration-free signal/noise discriminator.

Photon noise in a stack falls as frame count rises; real scene detail does not.
Render the SAME subject at N=20 and N=40 in both arms and measure flat-tile
high-pass rms.  If the flat-tile high-pass is noise, rms(40) < rms(20) in BOTH
arms.  If it is recovered detail, rms is ~flat in N.
"""
import os, sys, json, subprocess, time
import numpy as np, tifffile

EXE=r"C:\dev\strehl-out\V-GATHER\strehl-pinned.exe"
OUT=r"C:\dev\strehl-out\V-GATHER"
SRC=r"D:\personal\macro"
SUBS=["foam","lavendar-cpl","wrapped-text-1"]
NS=[20,40]

def render(subj,arm,n):
    outp=os.path.join(OUT,f"nc-{subj}-n{n}-g{arm}.tiff")
    if os.path.exists(outp): return outp,0.0
    env=dict(os.environ); env["STREHL_FULLRES_GATHER"]=arm; env["STREHL_FIX_CA"]="off"
    cmd=[EXE,"stack",os.path.join(SRC,subj),"--limit",str(n),
         "--linear-srgb","--demosaic","--out",outp]
    t0=time.perf_counter(); r=subprocess.run(cmd,capture_output=True,text=True)
    el=time.perf_counter()-t0
    open(os.path.join(OUT,f"log-nc-{subj}-n{n}-g{arm}.txt"),"w",errors="replace").write(r.stdout+r.stderr)
    if r.returncode!=0: raise RuntimeError(r.stdout[-800:]+r.stderr[-800:])
    return outp,el

def luma(im): return 0.2126*im[:,:,0]+0.7152*im[:,:,1]+0.0722*im[:,:,2]
def boxblur(y,r):
    k=2*r+1
    c=np.cumsum(np.pad(y,((r+1,r),(0,0)),mode="edge"),axis=0); y1=(c[k:]-c[:-k])/k
    c=np.cumsum(np.pad(y1,((0,0),(r+1,r)),mode="edge"),axis=1); return (c[:,k:]-c[:,:-k])/k
def hp(y,r=3): return y-boxblur(y,r)

def flat_rms_pair(pa,pb,t=256,q=0.25):
    a=luma(tifffile.imread(pa)[:,:,:3].astype(np.float64))
    b=luma(tifffile.imread(pb)[:,:,:3].astype(np.float64))
    h=(min(a.shape[0],b.shape[0])//t)*t; w=(min(a.shape[1],b.shape[1])//t)*t
    a=a[:h,:w]; b=b[:h,:w]; m=(a+b)/2
    st=m.reshape(h//t,t,w//t,t).std(axis=(1,3)); sel=st<=np.quantile(st,q)
    out=[]
    for y in (a,b):
        e=hp(y).reshape(h//t,t,w//t,t); v=(e**2).mean(axis=(1,3))
        out.append(float(np.sqrt(v[sel].mean())))
    return out[0],out[1],int(sel.sum())

if __name__=="__main__":
    paths={}
    for s in SUBS:
        for n in NS:
            for a in ("0","1"):
                p,el=render(s,a,n); paths[(s,n,a)]=p
                print(f"rendered {s} n={n} g{a} ({el:.0f}s)",flush=True)
    print()
    print(f"{'subject':16s}{'arm':5s}{'flatHP n=20':>13s}{'flatHP n=40':>13s}{'n40/n20':>9s}")
    res={}
    for s in SUBS:
        # tile set must be common across the four images -> use the n=20 pair to pick tiles
        r20_0,r20_1,nt=flat_rms_pair(paths[(s,20,"0")],paths[(s,20,"1")])
        r40_0,r40_1,_ =flat_rms_pair(paths[(s,40,"0")],paths[(s,40,"1")])
        res[s]={"g0":[r20_0,r40_0],"g1":[r20_1,r40_1],"tiles":nt}
        print(f"{s:16s}{'g0':5s}{r20_0:13.2f}{r40_0:13.2f}{r40_0/r20_0:9.3f}")
        print(f"{s:16s}{'g1':5s}{r20_1:13.2f}{r40_1:13.2f}{r40_1/r20_1:9.3f}")
        print(f"{'':16s}{'g1/g0':5s}{r20_1/r20_0:13.3f}{r40_1/r40_0:13.3f}")
    print()
    print("pure noise predicts n40/n20 ~ 0.71 ; pure detail predicts ~ 1.00")
    json.dump(res,open(os.path.join(OUT,"ncount.json"),"w"),indent=1)
