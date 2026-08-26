"""Adjudicate accept.py's microC against band-limited measures, on BUILD-HULL's
OWN matched pair. Same pixels, same file, four statistics.

accept.py:  thresh = quantile(g[::4,::4], 0.20)   <-- PER ARM
            lit    = g > thresh                    <-- PER ARM
            keep   = tile fraction lit > 0.5       <-- PER ARM
            microC = median over kept tiles of tile.std()

Two candidate defects, isolated separately:
  P (population): the clamp lifts shadows, so the 20th percentile moves, so the
     two arms take their median over DIFFERENT tiles. Repair = one shared mask.
  T (tone):  tile std is a RANGE statistic, not a band-limited one. Raising a
     floor compresses a dark tile and lowers its std with zero loss of detail.
     Repair = std of the tile's high-pass residual instead of the tile itself.
"""
import sys
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter

def load(p):
    im = tifffile.imread(p)
    assert im.dtype == np.uint16, "%s: %s" % (p, im.dtype)
    assert im.ndim == 3 and im.shape[2] == 3
    return im

def tiles_of(g):
    h, w = g.shape; th, tw = h//8*8, w//8*8
    return g[:th,:tw].reshape(th//8,8,tw//8,8).swapaxes(1,2).reshape(-1,64)

def mask_of(lit):
    h, w = lit.shape; th, tw = h//8*8, w//8*8
    return lit[:th,:tw].reshape(th//8,8,tw//8,8).swapaxes(1,2).reshape(-1,64).mean(axis=1) > 0.5

def acuity(g, lit):
    lap = np.zeros_like(g)
    lap[1:-1,1:-1] = 4.0*g[1:-1,1:-1]-g[:-2,1:-1]-g[2:,1:-1]-g[1:-1,:-2]-g[1:-1,2:]
    return float(np.abs(lap)[lit].mean())

subj, cp, up = sys.argv[1], sys.argv[2], sys.argv[3]
C, U = load(cp), load(up)
gc = C[:,:,1].astype(np.float32); gu = U[:,:,1].astype(np.float32)
print("subject %s   shape %s" % (subj, C.shape))
print("green mean  clamped %.0f   unclamped %.0f   (linear camera-native coffee-bean was ~29000 in my binned render)"
      % (gc.mean(), gu.mean()))
print("green p1    clamped %.0f   unclamped %.0f" % (np.percentile(gc,1), np.percentile(gu,1)))

tc, tu = tiles_of(gc), tiles_of(gu)
lit_c = gc > np.quantile(gc[::4,::4], 0.20)
lit_u = gu > np.quantile(gu[::4,::4], 0.20)
kc, ku = mask_of(lit_c), mask_of(lit_u)

print("\n--- accept.py AS WRITTEN (per-arm threshold, per-arm mask, tile std) ---")
mc = float(np.median(tc[kc].std(axis=1))); mu = float(np.median(tu[ku].std(axis=1)))
print("  microC clamped %.2f   unclamped %.2f   retained %.1f%%" % (mc, mu, 100*mc/mu))
print("  kept tiles: clamped %d   unclamped %d   DIFFER BY %d tiles (%.2f%% of kept)"
      % (kc.sum(), ku.sum(), abs(int(kc.sum())-int(ku.sum())),
         100.0*np.logical_xor(kc,ku).sum()/max(ku.sum(),1)))
print("  threshold : clamped %.0f DN   unclamped %.0f DN   moved %+.0f DN"
      % (np.quantile(gc[::4,::4],0.20), np.quantile(gu[::4,::4],0.20),
         np.quantile(gc[::4,::4],0.20)-np.quantile(gu[::4,::4],0.20)))

print("\n--- REPAIR P: one shared mask (from the UNCLAMPED reference arm) ---")
mc2 = float(np.median(tc[ku].std(axis=1))); mu2 = float(np.median(tu[ku].std(axis=1)))
print("  microC clamped %.2f   unclamped %.2f   retained %.1f%%" % (mc2, mu2, 100*mc2/mu2))

print("\n--- REPAIR T: band-limited (std of the tile's high-pass residual), per-arm mask ---")
hc = gc - gaussian_filter(gc, 2.0, mode="reflect"); hu = gu - gaussian_filter(gu, 2.0, mode="reflect")
thc, thu = tiles_of(hc), tiles_of(hu)
mc3 = float(np.median(thc[kc].std(axis=1))); mu3 = float(np.median(thu[ku].std(axis=1)))
print("  microC clamped %.2f   unclamped %.2f   retained %.1f%%" % (mc3, mu3, 100*mc3/mu3))

print("\n--- REPAIR P+T: shared mask AND band-limited ---")
mc4 = float(np.median(thc[ku].std(axis=1))); mu4 = float(np.median(thu[ku].std(axis=1)))
print("  microC clamped %.2f   unclamped %.2f   retained %.1f%%" % (mc4, mu4, 100*mc4/mu4))

print("\n--- accept.py's OWN band-limited witness: acuity (mean |Laplacian|) ---")
ac, au = acuity(gc, lit_c), acuity(gu, lit_u)
print("  acuity clamped %.1f   unclamped %.1f   retained %.1f%%" % (ac, au, 100*ac/au))
acs = acuity(gc, lit_u)
print("  acuity, shared mask                            retained %.1f%%" % (100*acs/au))
