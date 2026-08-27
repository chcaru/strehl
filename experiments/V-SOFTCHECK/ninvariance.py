"""N-INVARIANCE ACCEPTANCE CRITERION -- callable by the re-certification harness.

Certifies one property, stated in PREREG-ninvariance.md and fixed before use:

    At matched focus RANGE and matched exposure, deepening a bracket must not
    make the merged master measurably SOFTER.

One-sided by design: depth may help as much as it likes.  Below coverage
saturation it genuinely does, and penalising that would be wrong.

Exit codes for the harness:  0 PASS   1 FAIL   2 VOID
VOID is NOT a pass.  A run whose commissioning did not pass, or whose arms were
not built as specified, reports VOID rather than a number.

Usage:
    python ninvariance.py <subject> <exposure>            evaluate one subject
    python ninvariance.py --all                           evaluate the pinned set
"""
import os, sys, json, numpy as np, softcheck as S
from ncurve import rings, pick_tiles, align_int, boot, gauss, EDGES, T, NT
ROOT=r"C:\dev\strehl-out\V-SOFTCHECK\ncurve"
PRIMARY=3      # 0.20-0.25 cyc per OUTPUT pixel, the only promotable band
SECOND=4       # 0.25-0.30, reported, NOT gated
PINNED=[("bee-1-cpl",299,149),("113MSDCF",63,31),("flower-bud-alone-cpl",205,102)]

def commission(M,oy,ox):
    """Four arms.  All must pass or the run is VOID.  IMPROVE is the load-bearing
    one: it proves the statistic can reward a build and is not bounded below."""
    base=rings(M,oy,ox); out={}
    out["NULL"]=np.median((rings(M.copy(),oy,ox)/base)[:,PRIMARY])
    out["DEGRADE"]=np.median((rings(gauss(M,1.0),oy,ox)/base)[:,PRIMARY])
    imp=M.astype(np.float32)+0.8*(M.astype(np.float32)-gauss(M,1.2))
    out["IMPROVE"]=np.median((rings(imp,oy,ox)/base)[:,PRIMARY])
    out["REFPERT"]=np.median((base/np.maximum(rings(gauss(M,1.0),oy,ox),1e-30))[:,PRIMARY])
    ok=(abs(out["NULL"]-1)<1e-9 and out["DEGRADE"]<0.97
        and out["IMPROVE"]>1.03 and abs(out["REFPERT"]-1)>0.03)
    return ok,out

def evaluate(subject,nfull,nhalf,verbose=True):
    d=os.path.join(ROOT,subject)
    ff=os.path.join(d,f"master-N{nfull:03d}.tiff"); hf=os.path.join(d,f"master-N{nhalf:03d}.tiff")
    for f in (ff,hf):
        if not os.path.exists(f):
            return dict(subject=subject,verdict="VOID",reason=f"missing arm {os.path.basename(f)}")
    F=S.load_luma(ff,"srgb"); H=S.load_luma(hf,"srgb")
    oy,ox=pick_tiles(F)
    ok,arms=commission(F,oy,ox)
    if not ok:
        return dict(subject=subject,verdict="VOID",reason="commissioning failed",arms=arms)
    sy,sx=align_int(F,H)
    r=rings(H,oy+sy,ox+sx)/np.maximum(rings(F,oy,ox),1e-30)
    Rp=float(np.median(r[:,PRIMARY])); lo,hi=boot(r[:,PRIMARY])
    Rs=float(np.median(r[:,SECOND]))
    verdict="FAIL" if lo>1.0 else "PASS"
    res=dict(subject=subject,n_full=nfull,n_half=nhalf,band="0.20-0.25",
             R=round(Rp,4),ci=[round(float(lo),4),round(float(hi),4)],
             R_0p25_0p30=round(Rs,4),shift=[int(sy),int(sx)],verdict=verdict,
             commissioning={k:round(float(v),4) for k,v in arms.items()})
    if verbose:
        print(f"  {subject:<22s} N {nfull:3d} vs {nhalf:3d}   "
              f"R(0.20-0.25) = {Rp:.4f} [{lo:.4f},{hi:.4f}]   "
              f"R(0.25-0.30) = {Rs:.4f}   {verdict}")
    return res

if __name__=="__main__":
    print("N-INVARIANCE CRITERION   pin 9b05d0b7 / 44C2F2CD2E5B2894   backend pyramid")
    print("  R > 1 means the HALF-depth stack is SHARPER than the full stack.")
    print("  FAIL when the CI lower bound exceeds 1.0 in the primary band.\n")
    if sys.argv[1]=="--all": jobs=PINNED
    else: jobs=[(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]))]
    out=[evaluate(*j) for j in jobs]
    print()
    for r in out:
        if r["verdict"]=="VOID": print(f"  VOID {r['subject']}: {r['reason']}")
    n_pass=sum(1 for r in out if r["verdict"]=="PASS")
    n_fail=sum(1 for r in out if r["verdict"]=="FAIL")
    n_void=sum(1 for r in out if r["verdict"]=="VOID")
    print(f"  partition: {len(out)} attempted = {n_pass} pass + {n_fail} fail + {n_void} void")
    c=out[0].get("commissioning")
    if c: print(f"  commissioning (primary band): " +
                "  ".join(f"{k}={v}" for k,v in c.items()))
    open(os.path.join(ROOT,"ninvariance.json"),"w").write(json.dumps(out,indent=1))
    print(f"  machine-readable: {os.path.join(ROOT,'ninvariance.json')}")
    sys.exit(2 if n_void else (1 if n_fail else 0))
