"""Compare two arms' noise on the SAME tiles, under three stated selection rules.

Selection is threshold-free: within each signal bin take the flattest K% of
tiles ranked by COARSE structure (std after 8x8 box-average), which is dominated
by scene content rather than noise and does not assume the noise is white.
(An absolute structure threshold does assume that, and rejected 8029/8030 tiles
on real demosaiced data -- recorded in V-BLEND-verification.md.)

Three selectors, because ORCH selected on the arm-average and asked whether that
biases the result:
   avg    : rank on (A+B)/2   -- ORCH's rule
   before : rank on BEFORE only
   after  : rank on AFTER only
If the arm ordering is the same under all three, selection did not drive it.
"""
import sys
import numpy as np
import tifffile
from noisefloor import tiles, sigma_std, immerkaer, BOX

def green(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    return a[:, :, 1].astype(np.float32)

def coarse_structure(t, ds=8):
    n = t.shape[0]; b = t.shape[1]//ds
    d = t.reshape(n, b, ds, b, ds).mean(axis=(2, 4)).astype(np.float32)
    return sigma_std(d)

def check_alignment(a, b):
    """Integer shift between arms via cross-correlation of a central crop.
    A non-zero shift would invalidate every tile-wise comparison."""
    cy, cx = a.shape[0]//2, a.shape[1]//2
    A = a[cy-256:cy+256, cx-256:cx+256].astype(np.float64)
    B = b[cy-256:cy+256, cx-256:cx+256].astype(np.float64)
    A -= A.mean(); B -= B.mean()
    F = np.fft.rfft2(A)*np.conj(np.fft.rfft2(B))
    c = np.fft.irfft2(F, s=A.shape)
    k = np.unravel_index(np.argmax(c), c.shape)
    dy = k[0] if k[0] <= A.shape[0]//2 else k[0]-A.shape[0]
    dx = k[1] if k[1] <= A.shape[1]//2 else k[1]-A.shape[1]
    return dy, dx

def stats(path):
    g = green(path); t = tiles(g)
    o = dict(mean=t.mean(axis=(1, 2)), std=sigma_std(t), hf=immerkaer(t),
             coarse=coarse_structure(t))
    del g, t
    return o

if __name__ == "__main__":
    pb, pa, label = sys.argv[1], sys.argv[2], sys.argv[3]
    K = float(sys.argv[4]) if len(sys.argv) > 4 else 10.0   # flattest K% per bin

    gb, ga = green(pb), green(pa)
    dy, dx = check_alignment(gb, ga)
    print(f"=== {label} ===")
    print(f"BEFORE {pb}")
    print(f"AFTER  {pa}")
    print(f"alignment check: integer shift AFTER vs BEFORE = ({dy}, {dx})"
          f"  {'OK' if (dy, dx) == (0, 0) else '*** NON-ZERO: tile comparison INVALID ***'}")
    del gb, ga

    B, A = stats(pb), stats(pa)
    avg_coarse = 0.5*(A["coarse"]+B["coarse"])
    mean_sig = 0.5*(A["mean"]+B["mean"])
    edges = np.array([200, 500, 1000, 2000, 4000, 8000, 16000, 32000, 65536])

    for selname, sel in (("avg (ORCH's rule)", avg_coarse), ("before-only", B["coarse"]),
                         ("after-only", A["coarse"])):
        print(f"\n--- selector: {selname};  flattest {K:.0f}% of tiles per signal bin ---")
        print("   signal bin      ntile |  BEFORE std   AFTER std   ratio |  BEFORE hf    AFTER hf   ratio |"
              "  B std/hf  A std/hf")
        tot = []
        for i in range(len(edges)-1):
            m = (mean_sig >= edges[i]) & (mean_sig < edges[i+1])
            if m.sum() < 20: continue
            idx = np.where(m)[0]
            keep = idx[sel[idx] <= np.percentile(sel[idx], K)]
            if keep.size < 8: continue
            bs, as_ = np.median(B["std"][keep]), np.median(A["std"][keep])
            bh, ah = np.median(B["hf"][keep]), np.median(A["hf"][keep])
            tot.append((keep.size, bs, as_, bh, ah))
            print(f"  {edges[i]:6d}-{edges[i+1]:6d}  {keep.size:6d} | {bs:10.3f} {as_:11.3f} "
                  f"{as_/bs:7.3f} | {bh:10.3f} {ah:10.3f} {ah/bh:7.3f} | {bs/bh:9.3f} {as_/ah:9.3f}"
                  )
        if tot:
            w = np.array([t[0] for t in tot], float)
            f = lambda j: float(np.sum(w*np.array([t[j] for t in tot]))/w.sum())
            print(f"  {'WEIGHTED':>13}  {int(w.sum()):6d} | {f(1):10.3f} {f(2):11.3f} "
                  f"{f(2)/f(1):7.3f} | {f(3):10.3f} {f(4):10.3f} {f(4)/f(3):7.3f} | "
                  f"{f(1)/f(3):9.3f} {f(2)/f(4):9.3f}")
