"""drender.py -- render arms with EXPLICIT frame-index lists, for the dilution test.

nrender.py and hrender.py both pin the subset to the FULL focus range by
construction (linspace(0, NF-1, n)), which is exactly right for a matched-range
depth curve and useless here: the dilution hypothesis is discriminated by an arm
that holds the STEP and lets the RANGE grow.  So this renders whatever index list
it is given, and asserts on disk what that list was.

Every arm gets the same explicit --exposure.  --auto-exposure is forbidden: it
solves a different gain per arm and the band statistics are linear in gain, so it
could manufacture or erase a depth effect on its own.  That trap has already
produced one wrong published number on this project.

STREHL_ONLY_FRAME probes render a single bracket frame with NO election
(merge_cmd.rs:1748 at the pin) through the identical pipeline, so they land on the
same output grid as the merges and can be compared to them directly.
"""
import os, sys, shutil, subprocess, time, hashlib
BIN=r"C:\dev\strehl-out\V-SOFTCHECK\bin\strehl.exe"
PIN_SHA="44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490"
OUTROOT=r"C:\dev\strehl-out\V-SOFTCHECK\dilut"
CLEAR=["STREHL_FIX_CA","STREHL_EDGE_AWARE","STREHL_EDGE_TAU","STREHL_EDGE_CONF","STREHL_ACUITY",
       "STREHL_MERGE","STREHL_WARPMAP","STREHL_ALIGN","STREHL_SOFT_GATE","STREHL_PHOTOMETRIC",
       "STREHL_FIX_HALO","STREHL_VEIL","STREHL_COVER","STREHL_FULLRES_GATHER","STREHL_ONLY_FRAME"]

def pin():
    h=hashlib.sha256(open(BIN,"rb").read()).hexdigest().upper()
    if h!=PIN_SHA: sys.exit("ABORT: wrong binary %s"%h[:16])
    return h

def base_env():
    env=dict(os.environ)
    for v in CLEAR: env.pop(v,None)
    return env

def frames(subject):
    src=rf"D:\personal\macro\{subject}"
    return src, sorted(f for f in os.listdir(src) if f.lower().endswith(".arw"))

def merge_arm(subject, tag, idx, exposure):
    src,allf=frames(subject)
    out=os.path.join(OUTROOT,subject); os.makedirs(out,exist_ok=True)
    dst=os.path.join(out,f"{tag}.tiff")
    if os.path.exists(dst):
        print(f"  {tag:10s} present, skipped"); return dst
    d=os.path.join(OUTROOT,"_sub",f"{subject}-{tag}"); os.makedirs(d,exist_ok=True)
    for i in idx: shutil.copy2(os.path.join(src,allf[i]),os.path.join(d,allf[i]))
    got=sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))
    assert len(got)==len(idx), f"{tag}: {len(got)} on disk vs {len(idx)} requested"
    assert got[0]==allf[idx[0]] and got[-1]==allf[idx[-1]], f"{tag}: range check failed on disk"
    t0=time.time()
    r=subprocess.run([BIN,"stack",d,"--out",dst,"--srgb","--exposure",exposure],
                     capture_output=True,env=base_env())
    el=time.time()-t0
    log=r.stdout.decode("utf-8","replace")+r.stderr.decode("utf-8","replace")
    open(dst+".log","w",encoding="utf-8").write(log)
    expo=[l.strip() for l in log.splitlines() if l.startswith("exposure")]
    step=(idx[1]-idx[0]) if len(idx)>1 else 0
    print(f"  {tag:10s} N={len(idx):3d} idx {idx[0]}..{idx[-1]} step~{step}  {el:6.1f}s  "
          f"file={os.path.exists(dst)}   {expo[0] if expo else 'NO EXPOSURE LINE'}")
    if not os.path.exists(dst): sys.exit(f"ABORT: {tag} claimed success but file absent")
    shutil.rmtree(d,ignore_errors=True)
    return dst

def probe(subject, k, exposure):
    src,allf=frames(subject)
    out=os.path.join(OUTROOT,subject,"probe"); os.makedirs(out,exist_ok=True)
    dst=os.path.join(out,f"F{k:03d}.tiff")
    if os.path.exists(dst):
        print(f"  probe {k:3d}  present, skipped"); return dst
    env=base_env(); env["STREHL_ONLY_FRAME"]=str(k)
    t0=time.time()
    r=subprocess.run([BIN,"stack",src,"--out",dst,"--srgb","--exposure",exposure],
                     capture_output=True,env=env)
    el=time.time()-t0
    log=r.stdout.decode("utf-8","replace")+r.stderr.decode("utf-8","replace")
    open(dst+".log","w",encoding="utf-8").write(log)
    noelect=[l.strip() for l in log.splitlines() if "NO election" in l]
    if not noelect: sys.exit(f"ABORT: probe {k} did not report NO election -- ONLY_FRAME did not take")
    print(f"  probe {k:3d}  {el:6.1f}s  file={os.path.exists(dst)}   {noelect[0]}")
    if not os.path.exists(dst): sys.exit(f"ABORT: probe {k} claimed success but file absent")
    return dst

if __name__=="__main__":
    h=pin(); print("pin sha256 %s...  SHIP-V4 ok\n"%h[:16])
    SUBJ="bee-1-cpl"; EXPO="1.50"
    src,allf=frames(SUBJ); NF=len(allf)
    print(f"{SUBJ}: {NF} frames, exposure {EXPO} on EVERY arm and probe\n")
    HALF=NF//2                                   # 149
    import numpy as np
    print("MERGE ARMS")
    merge_arm(SUBJ,"R150x1",list(range(0,HALF+1)),EXPO)          # step 1, range 0-149
    merge_arm(SUBJ,"R075x2",list(range(0,HALF+1,2)),EXPO)        # step 2, range 0-148
    # Re-render the two full-range arms rather than inherit them.  ncurve's
    # master-N299.tiff.log is ZERO BYTES: that arm's development gain cannot be
    # verified, and it is the shared endpoint of both discriminator comparisons.
    # An unverifiable gauge on one side of a ratio is the exact trap that produced a
    # sign flip on this project.  Index lists reproduce ncurve.py's subsets exactly.
    q=sorted(set(np.linspace(0,NF-1,149).round().astype(int).tolist()))
    assert q[0]==0 and q[-1]==NF-1 and len(q)==149, "Q subset not reproduced: %d"%len(q)
    merge_arm(SUBJ,"R149x2",q,EXPO)                              # step 2, range 0-298
    merge_arm(SUBJ,"R299x1",list(range(NF)),EXPO)                # step 1, range 0-298
    print("\nFOCUS PROBES (single frame, no election)")
    for k in [0,25,50,75,100,125,150,175,200,225,250,275,NF-1]:
        probe(SUBJ,k,EXPO)
    print("\ndone")
