"""Render one master per bracket DEPTH, holding focus RANGE and exposure fixed.

Subsets are chosen with linspace(0, Nfull-1, n) rounded, which pins the first and
last frame into every arm by construction.  `frames[::N//n][:n]` -- the form that
silently truncated the focus range on this project before -- is never used, and
the first/last indices are asserted rather than assumed.

Exposure is passed EXPLICITLY and identically to every arm.  --auto-exposure
would solve a different gain per arm; the statistic is exactly linear in gain, so
that alone could manufacture or erase a depth effect.

Each subset directory is deleted the moment its master exists: ten lanes share
this disk.
"""
import os, sys, shutil, subprocess, time, hashlib
BIN=r"C:\dev\strehl-out\V-SOFTCHECK\bin\strehl.exe"
PIN_SHA="44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490"
OUTROOT=r"C:\dev\strehl-out\V-SOFTCHECK\ncurve"
CLEAR=["STREHL_FIX_CA","STREHL_EDGE_AWARE","STREHL_EDGE_TAU","STREHL_EDGE_CONF","STREHL_ACUITY",
       "STREHL_MERGE","STREHL_WARPMAP","STREHL_ALIGN","STREHL_SOFT_GATE","STREHL_PHOTOMETRIC",
       "STREHL_FIX_HALO","STREHL_VEIL","STREHL_COVER","STREHL_FULLRES_GATHER","STREHL_ONLY_FRAME"]

def pin_ok():
    h=hashlib.sha256(open(BIN,"rb").read()).hexdigest().upper()
    return h==PIN_SHA, h

def run(subject, ns, exposure):
    ok,h=pin_ok()
    print(f"pin sha256 {h[:16]}...  matches SHIP-V4 .ok = {ok}")
    if not ok: sys.exit("ABORT: wrong binary")
    src=rf"D:\personal\macro\{subject}"
    allf=sorted(f for f in os.listdir(src) if f.lower().endswith(".arw"))
    NF=len(allf)
    out=os.path.join(OUTROOT,subject); os.makedirs(out,exist_ok=True)
    env=dict(os.environ)
    for v in CLEAR: env.pop(v,None)
    print(f"{subject}: {NF} frames on disk, exposure {exposure} for EVERY arm\n")
    for n in ns:
        dst=os.path.join(out,f"master-N{n:03d}.tiff")
        if os.path.exists(dst):
            print(f"  N={n:3d}  already present, skipped"); continue
        if n>=NF:
            d=src; idx=list(range(NF)); n=NF
        else:
            import numpy as np
            idx=sorted(set(np.linspace(0,NF-1,n).round().astype(int).tolist()))
            assert idx[0]==0 and idx[-1]==NF-1, f"RANGE NOT PRESERVED {idx[0]},{idx[-1]}"
            d=os.path.join(OUTROOT,"_sub",f"{subject}-N{n:03d}")
            os.makedirs(d,exist_ok=True)
            for i in idx:
                t=os.path.join(d,allf[i])
                if not os.path.exists(t): shutil.copy2(os.path.join(src,allf[i]),t)
        got=sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))
        assert got[0]==allf[idx[0]] and got[-1]==allf[idx[-1]], "range check failed on disk"
        t0=time.time()
        r=subprocess.run([BIN,"stack",d,"--out",dst,"--srgb","--exposure",exposure],
                         capture_output=True,env=env)
        el=time.time()-t0
        log=r.stdout.decode("utf-8",errors="replace")+r.stderr.decode("utf-8",errors="replace")
        open(dst+".log","w",encoding="utf-8").write(log)
        exists=os.path.exists(dst)
        placed=[l.strip() for l in log.splitlines() if "placed" in l]
        expo=[l.strip() for l in log.splitlines() if l.startswith("exposure")]
        print(f"  N={n:3d}  {len(got):3d} arw  first={got[0]} last={got[-1]}  "
              f"{el:6.1f}s  file={exists}")
        print(f"        {placed[0] if placed else 'NO PLACEMENT LINE'}")
        print(f"        {expo[0] if expo else 'NO EXPOSURE LINE'}")
        if not exists: sys.exit(f"ABORT: render claimed success but {dst} absent")
        if d!=src: shutil.rmtree(d,ignore_errors=True)
    shutil.rmtree(os.path.join(OUTROOT,"_sub"),ignore_errors=True)

if __name__=="__main__":
    run(sys.argv[1],[int(x) for x in sys.argv[2].split(",")],sys.argv[3])

