import sys, numpy as np, tifffile
from scipy import ndimage

def erode_profile(mask, kmax=6):
    """fraction of the mask surviving k rounds of 4-connected erosion.
    a rim of width w vanishes by k = ceil(w/2); a solid blob survives."""
    m = mask.copy(); n0 = float(m.sum()); out=[]
    for k in range(1, kmax+1):
        m = ndimage.binary_erosion(m, structure=ndimage.generate_binary_structure(2,1))
        out.append(float(m.sum())/max(n0,1))
    return out

def gradstats(ref, mask):
    gy, gx = np.gradient(ref)
    g = np.hypot(gy, gx)
    return float(np.median(g[mask])), float(np.median(g))

def commission():
    print("="*66); print("COMMISSION -- erosion must separate a rim from a blob"); print("="*66)
    ok = True
    H = W = 400
    # a 2-px-wide rim around a disc
    yy,xx = np.mgrid[0:H,0:W]; r = np.hypot(yy-200, xx-200)
    rim = (r>100)&(r<=102)
    blob = (r<=30)
    # thresholds are the MEASURED behaviour of these known shapes, not guesses:
    # discrete 4-connected erosion leaves ~9% of a 2px annulus at k1, so the
    # honest rim signature is "gone by k2" (2px) / "gone by k3" (4px).
    for name, m, expect_gone_by, expect_alive in (
            ("2px rim",  rim,  2, None),
            ("4px rim",  (r>100)&(r<=104), 3, None),
            ("r=30 blob",blob, None, 0.60)):
        p = erode_profile(m)
        s = "  ".join(f"k{i+1}:{v:.3f}" for i,v in enumerate(p))
        if expect_gone_by is not None:
            good = p[expect_gone_by-1] < 0.02
            print(f"  {'PASS' if good else 'FAIL'}  {name:10s} {s}   (must be <0.02 by k{expect_gone_by})")
        else:
            good = p[2] > expect_alive
            print(f"  {'PASS' if good else 'FAIL'}  {name:10s} {s}   (must be >{expect_alive} at k3)")
        ok &= good
    # NULL: empty mask must not crash or claim survival
    p = erode_profile(np.zeros((50,50), bool))
    good = all(v == 0.0 for v in p); ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  NULL empty mask -> {p[0]:.3f}")
    print(f"  --> {'ALL PASS' if ok else 'FAILURES'}"); print()
    return ok

if __name__ == "__main__":
    commission()
    if len(sys.argv) < 3: sys.exit(0)
    A = tifffile.imread(sys.argv[1]); B = tifffile.imread(sys.argv[2])
    assert A.dtype == np.uint16 and B.dtype == np.uint16
    ch = 2
    a = A[:,:,ch].astype(np.float64); b = B[:,:,ch].astype(np.float64)
    m = (a <= 0)
    n = int(m.sum())
    print("="*66)
    print(f"AFTER {sys.argv[1]}\nBEFORE {sys.argv[2]}   blue channel")
    print("="*66)
    print(f"  zeros: {n:,}  ({100.0*n/a.size:.4f}%)")
    gm, gi = gradstats(b, m)
    print(f"  control-arm |grad| at zeros median {gm:8.1f}  image-wide {gi:8.1f}  ratio {gm/max(gi,1e-9):6.2f}x")
    p = erode_profile(m)
    print("  erosion survival: " + "  ".join(f"k{i+1}:{v:.3f}" for i,v in enumerate(p)))
    lab, nl = ndimage.label(m, structure=ndimage.generate_binary_structure(2,1))
    sizes = np.bincount(lab.ravel())[1:]
    print(f"  connected components: {nl:,}   largest {sizes.max():,} px   "
          f"median {np.median(sizes):.0f} px")
    frac_big = float(sizes[sizes>=1000].sum())/max(sizes.sum(),1)
    print(f"  fraction of zero mass in components >= 1000 px: {100*frac_big:.1f}%")
    print()
    print("  INTERPRETATION (evidence is above this line):")
    print(f"    a 2 px rim is gone by k2 and a 4 px rim by k3; a solid disc reads k3 = 0.83.")
    print(f"    this mask reads k1 {p[0]:.3f}, k2 {p[1]:.3f}, k3 {p[2]:.3f}, k6 {p[5]:.3f}.")
