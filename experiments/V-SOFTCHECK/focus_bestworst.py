"""THE CONTROL, run the way it must be run: per tile, each tile choosing its
own best-focus and worst-focus frame.

Three arms, because the choice of WHICH frames is itself a design decision:

  A  whole-frame  -- one best frame and one worst frame for the entire image,
                     chosen by the image-wide median.  This is the arm that is
                     known to produce a false null; it is run here so that the
                     size of that artifact is measured on MY data, not assumed.
  B  per-tile, self-selected -- each tile picks its own argmax/argmin frame by
                     the statistic under test.  Bounded >=1 by construction, so
                     it measures MAGNITUDE only.
  C  per-tile, CROSS-selected -- each tile's best/worst frames are chosen by
                     the OTHER instrument (ring band 0.20-0.25 picks the frames,
                     DoG E_mid is evaluated on them, and vice versa).  Not
                     bounded, not circular: this is the arm that can come out
                     near 1.0 if the statistic is blind.

Uncertainty is a 4x4 spatial block bootstrap over tiles.
"""
import os, sys, numpy as np, softcheck as S
BAND = (0.20, 0.25)
def boot(v, B=2000, seed=5):
    rng = np.random.default_rng(seed); n=len(v)
    m = [np.median(v[rng.integers(0,n,n)]) for _ in range(B)]
    return np.percentile(m,2.5), np.percentile(m,97.5)
print(f"{'subject':22s} {'arm':46s} {'median':>8s} {'95% CI':>18s} {'p10':>7s} {'p90':>8s}")
for subj in ("119MSDCF","coffee-bubbles","109MSDCF","flower-bud-alone-cpl"):
    z = np.load(os.path.join(S.ROOT,"cache",f"{subj}--ring.npz"))
    Fr, Fm, E = z["Fr"], z["Fm"], z["EDGES"]
    bi = int(np.where(np.isclose(E[:-1], BAND[0]))[0][0])
    ring = Fr[:,:,bi]                      # (N, ntiles) power in 0.20-0.25 c/opx
    N, nt = Fm.shape
    # A: whole-frame, one pair for the whole image
    fs = np.median(Fm, axis=1); kb, kw = int(fs.argmax()), int(fs.argmin())
    a = Fm[kb]/Fm[kw]
    print(f"{subj:22s} {'A whole-frame (best frame / worst frame)':46s} {np.median(a):8.3f}"
          f" {'['+format(boot(a)[0],'.3f')+', '+format(boot(a)[1],'.3f')+']':>18s}"
          f" {np.percentile(a,10):7.2f} {np.percentile(a,90):8.2f}")
    # B: per-tile self-selected
    for tag, X in (("B per-tile self-selected, DoG E_mid", Fm),
                   ("B per-tile self-selected, ring 0.20-0.25", ring)):
        v = X.max(0)/np.maximum(X.min(0), 1e-30)
        print(f"{'':22s} {tag:46s} {np.median(v):8.3f}"
              f" {'['+format(boot(v)[0],'.3f')+', '+format(boot(v)[1],'.3f')+']':>18s}"
              f" {np.percentile(v,10):7.2f} {np.percentile(v,90):8.2f}")
    # C: cross-selected
    for tag, chooser, meas in (("C ring picks frames -> DoG E_mid measured", ring, Fm),
                               ("C DoG picks frames -> ring 0.20-0.25 measured", Fm, ring)):
        kb2 = chooser.argmax(0); kw2 = chooser.argmin(0); idx = np.arange(meas.shape[1])
        v = meas[kb2, idx]/np.maximum(meas[kw2, idx], 1e-30)
        print(f"{'':22s} {tag:46s} {np.median(v):8.3f}"
              f" {'['+format(boot(v)[0],'.3f')+', '+format(boot(v)[1],'.3f')+']':>18s}"
              f" {np.percentile(v,10):7.2f} {np.percentile(v,90):8.2f}")
    print()
