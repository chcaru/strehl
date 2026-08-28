"""Render INTERLEAVED half-stack pairs at several bracket depths.

For total depth N the subset is linspace(0,NF-1,N) rounded; half A is its even
positions and half B its odd ones.  Interleaving means both halves span the focus
RANGE instead of each taking one end, which is the trap that shortened the range on
this project before.  First and last subset indices are asserted on disk.

Exposure is passed EXPLICITLY and identically to every arm and every depth.
--auto-exposure would solve a different gain per arm and the statistic is not
gain-free unless the arms match.
"""
import os, sys, shutil, subprocess, time, hashlib, numpy as np
BIN=r"C:\dev\strehl-out\V-SOFTCHECK\bin\strehl.exe"
PIN_SHA="44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490"
OUTROOT=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh"
CLEAR=["STREHL_FIX_CA","STREHL_EDGE_AWARE","STREHL_EDGE_TAU","STREHL_EDGE_CONF","STREHL_ACUITY",
       "STREHL_MERGE","STREHL_WARPMAP","STREHL_ALIGN","STREHL_SOFT_GATE","STREHL_PHOTOMETRIC",
       "STREHL_FIX_HALO","STREHL_VEIL","STREHL_COVER","STREHL_FULLRES_GATHER","STREHL_ONLY_FRAME"]

def run(subject, ns, exposure):
    h=hashlib.sha256(open(BIN,"rb").read()).hexdigest().upper()
    print(f"pin sha256 {h[:16]}...  matches SHIP-V4 .ok = {h==PIN_SHA}")
    if h!=PIN_SHA: sys.exit("ABORT: wrong binary")
    src=rf"D:\personal\macro\{subject}"
    allf=sorted(f for f in os.listdir(src) if f.lower().endswith(".arw"))
    NF=len(allf); out=os.path.join(OUTROOT,subject); os.makedirs(out,exist_ok=True)
    env=dict(os.environ)
    for v in CLEAR: env.pop(v,None)
    print(f"{subject}: {NF} frames on disk, exposure {exposure} for EVERY arm and half\n")
    for n in ns:
        sub=sorted(set(np.linspace(0,NF-1,min(n,NF)).round().astype(int).tolist()))
        assert sub[0]==0 and sub[-1]==NF-1, f"RANGE NOT PRESERVED {sub[0]},{sub[-1]}"
        for tag,idx in (("A",sub[0::2]),("B",sub[1::2])):
            dst=os.path.join(out,f"N{n:03d}-{tag}.tiff")
            if os.path.exists(dst):
                print(f"  N={n:3d} {tag}  present, skipped"); continue
            d=os.path.join(OUTROOT,"_sub",f"{subject}-N{n:03d}{tag}")
            os.makedirs(d,exist_ok=True)
            for i in idx: shutil.copy2(os.path.join(src,allf[i]),os.path.join(d,allf[i]))
            got=sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))
            assert got[0]==allf[idx[0]] and got[-1]==allf[idx[-1]], "range check failed on disk"
            t0=time.time()
            r=subprocess.run([BIN,"stack",d,"--out",dst,"--srgb","--exposure",exposure],
                             capture_output=True,env=env)
            el=time.time()-t0
            log=r.stdout.decode("utf-8","replace")+r.stderr.decode("utf-8","replace")
            open(dst+".log","w",encoding="utf-8").write(log)
            expo=[l.strip() for l in log.splitlines() if l.startswith("exposure")]
            print(f"  N={n:3d} {tag}  {len(got):3d} arw  frames {idx[0]}..{idx[-1]}  "
                  f"{el:6.1f}s  file={os.path.exists(dst)}   {expo[0] if expo else 'NO EXPOSURE LINE'}")
            if not os.path.exists(dst): sys.exit(f"ABORT: render claimed success but {dst} absent")
            shutil.rmtree(d,ignore_errors=True)
    shutil.rmtree(os.path.join(OUTROOT,"_sub"),ignore_errors=True)

if __name__=="__main__":
    run(sys.argv[1],[int(x) for x in sys.argv[2].split(",")],sys.argv[3])
