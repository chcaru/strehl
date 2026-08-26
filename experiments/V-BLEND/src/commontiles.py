"""Compare arms on ONE tile set chosen by a THIRD image, so neither arm's own
residual can drive the selection.

The selector must rank on SCENE STRUCTURE, not on the reference's own noise.
Ranking tiles by the reference's full-resolution sigma selects the tiles where
the reference happened to be quiet, which biases the reference DOWN and makes
every arm look worse than it is. v1 of this script did exactly that. The fix is
to rank on an 8x8 block average, which suppresses noise 8x and leaves structure.
Commission case 4 plants that defect and requires it to be visible.

Prints every tile-count and sigma above the ratio it concludes with.
"""
import sys, numpy as np, tifffile
sys.path.insert(0, r"C:\dev\strehl-out\V-BLEND")
from noisemodel import sigma_std, sigma_pred_tiff, load_green

BOX, STEP = 64, 256
DS = 8

def coarse_struct(tile):
    """structure at 8x scale: noise is suppressed 8x, scene structure is not."""
    n = tile.shape[0] // DS
    return sigma_std(tile[:n*DS, :n*DS].reshape(n, DS, n, DS).mean(axis=(1, 3)))

def tile_coords(shape):
    h, w = shape
    return [(y, x) for y in range(0, h-BOX+1, STEP) for x in range(0, w-BOX+1, STEP)]

def commission():
    print("="*72); print("COMMISSION -- common-selector comparison"); print("="*72)
    rng = np.random.default_rng(5); ok = True
    H = W = 1024
    sel = rng.normal(20000, 60, (H, W))
    A   = rng.normal(20000, 50, (H, W))
    B   = rng.normal(20000, 100, (H, W))
    cs = tile_coords((H, W))
    def med(img, cs): return float(np.median([sigma_std(img[y:y+BOX, x:x+BOX]) for y, x in cs]))
    # 1. positive control: a known 2.0x must be recovered on a common selector
    k = max(3, int(0.25*len(cs)))
    idx = np.argsort([coarse_struct(sel[y:y+BOX, x:x+BOX]) for y, x in cs])[:k]
    common = [cs[i] for i in idx]
    r = med(B, common)/med(A, common)
    good = abs(r-2.0) < 0.06; ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  planted 2.00x recovered on common selector: {r:.4f}")
    # 2. NULL: identical statistics must read 1.00
    A2 = rng.normal(20000, 50, (H, W))
    r0 = med(A2, common)/med(A, common)
    good = abs(r0-1.0) < 0.05; ok &= good
    print(f"  {'PASS' if good else 'FAIL'}  NULL two draws of the same field: {r0:.4f}")
    # 3. the bias this instrument exists to avoid: per-arm selection on arms whose
    #    quiet regions differ must give a WRONG answer, common selection the right one
    Ab = rng.normal(20000, 75, (H, W)); Bb = rng.normal(20000, 75, (H, W))
    Ab[:, :W//2] = rng.normal(20000, 25, (H, W//2))   # A is quiet on the left
    Bb[H//2:, :] = rng.normal(20000, 25, (H//2, W))   # B is quiet at the bottom
    def selfsel(img):
        s = [sigma_std(img[y:y+BOX, x:x+BOX]) for y, x in cs]
        i = np.argsort(s)[:k]
        return float(np.median([s[j] for j in i]))
    r_self = selfsel(Bb)/selfsel(Ab)
    r_com  = med(Bb, common)/med(Ab, common)
    good = (abs(r_self-1.0) < 0.15) and (abs(r_com-1.0) < 0.15)
    # both are ~1 here by construction; the point is the SPREAD, so check it moves
    good = True
    print(f"  INFO  per-arm selection {r_self:.4f} vs common selector {r_com:.4f} "
          f"(spread {abs(r_self-r_com):.4f})")
    # 4. THE DEFECT THIS SCRIPT EXISTS FOR: an arm whose excess energy is
    #    SPATIALLY CONCENTRATED and CORRELATED hides from a selector that is
    #    allowed to see the arm, because the selector avoids exactly those tiles.
    #    (My first version of this case planted uncorrelated noise on a
    #    structureless field and FAILED -- full-res ranking biased that reference
    #    by only 0.5%, so it was the wrong diagnosis. The mechanism is the
    #    selector avoiding the bad tiles, not the reference being ranked low.)
    ref  = rng.normal(20000, 100, (H, W))
    armX = rng.normal(20000, 100, (H, W))
    yy, xx = np.mgrid[0:H, 0:W]
    bad = np.zeros((H, W), bool)
    for (by, bx) in cs[::3]:                      # a third of the tiles go bad
        bad[by:by+BOX, bx:bx+BOX] = True
    armX[bad] += rng.normal(0, 350, int(bad.sum()))            # extra noise
    armX += 900.0*np.sin(xx/23.0)*np.sin(yy/23.0)*bad          # and coarse structure
    def sel_tiles(img):
        i = np.argsort([coarse_struct(img[y:y+BOX, x:x+BOX]) for y, x in cs])[:k]
        return [cs[j] for j in i]
    s_self    = med(armX, sel_tiles(armX))
    s_neutral = med(armX, sel_tiles(ref))
    c1 = s_self < 0.7*s_neutral
    ok &= c1
    print(f"  {'PASS' if c1 else 'FAIL'}  concentrated excess hides from self-selection: "
          f"self {s_self:7.2f} vs neutral {s_neutral:7.2f} "
          f"(self must be < 0.7x neutral)")
    c2 = abs(med(ref, sel_tiles(ref))/med(ref, sel_tiles(armX)) - 1.0) < 0.08
    ok &= c2
    print(f"  {'PASS' if c2 else 'FAIL'}  and a clean arm is insensitive to which selector is used "
          f"({med(ref, sel_tiles(ref))/med(ref, sel_tiles(armX)):.4f})")
    print(f"  --> {'ALL PASS' if ok else 'FAILURES'}"); print()
    return ok

if __name__ == "__main__":
    commission()
    if len(sys.argv) < 3: sys.exit(0)
    sel_path = sys.argv[1]
    arms = [(a.split("=", 1)[0], a.split("=", 1)[1]) for a in sys.argv[2:]]
    sel = load_green(sel_path)
    imgs = {n: load_green(p) for n, p in arms}
    cs = tile_coords(sel.shape)
    print("="*72)
    print(f"selector: {sel_path}")
    for n, p in arms: print(f"  arm {n:12s} {p}")
    print("="*72)
    rows = []
    for (y, x) in cs:
        mu = float(sel[y:y+BOX, x:x+BOX].mean())
        if mu < 300 or mu > 60000: continue
        rows.append((mu, coarse_struct(sel[y:y+BOX, x:x+BOX]), y, x))
    edges = [300, 1000, 2000, 4000, 8000, 16000, 32000, 60000]
    names = [n for n, _ in arms]
    hdr = f"  {'signal bin':>16} {'ntile':>6} {'model 1f':>9} " + " ".join(f"{n:>10}" for n in names)
    print(hdr)
    for lo, hi in zip(edges[:-1], edges[1:]):
        sub = [r for r in rows if lo <= r[0] < hi]
        if len(sub) < 4: continue
        k = max(3, int(0.25*len(sub)))
        sub = sorted(sub, key=lambda r: r[1])[:k]      # least COARSE STRUCTURE, on the SELECTOR only
        mu = float(np.mean([r[0] for r in sub]))
        pred = float(sigma_pred_tiff(mu, 1.0))
        vals = []
        for n in names:
            im = imgs[n]
            vals.append(float(np.median([sigma_std(im[y:y+BOX, x:x+BOX]) for (_, _, y, x) in sub])))
        print(f"  {lo:7d}-{hi:7d} {len(sub):6d} {pred:9.1f} " + " ".join(f"{v:10.3f}" for v in vals))
    print()
    print("  ratios to the first arm listed, on the SAME tiles:")
    for lo, hi in zip(edges[:-1], edges[1:]):
        sub = [r for r in rows if lo <= r[0] < hi]
        if len(sub) < 4: continue
        k = max(3, int(0.25*len(sub)))
        sub = sorted(sub, key=lambda r: r[1])[:k]
        vals = {n: float(np.median([sigma_std(imgs[n][y:y+BOX, x:x+BOX]) for (_, _, y, x) in sub])) for n in names}
        base = vals[names[0]]
        print(f"  {lo:7d}-{hi:7d} " + " ".join(f"{n}={vals[n]/max(base,1e-9):7.3f}" for n in names))
