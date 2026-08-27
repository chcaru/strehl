import numpy as np, tifffile, rawpy, sys, os
np.random.seed(20260824)

ARW = r"D:\personal\macro\113MSDCF\DSC00001.ARW"
LIN = r"C:\dev\strehl-out\V-LINEAR\lintiff\DSC00001.tif"
TILE, THR, MAXLAG = 96, 0.10, 24

def opponent(rgb):
    r,g,b = rgb[...,0], rgb[...,1], rgb[...,2]
    Y = 0.2126*r + 0.7152*g + 0.0722*b
    return Y, (r-Y), (b-Y)

def box(a, k):
    from scipy.ndimage import uniform_filter
    return uniform_filter(a, k, mode="reflect")

def pick_tiles(Y, stride=128, max_tiles=150):
    """Flat DARK tiles, absolute floors. Returns list of (y,x). Aborts caller if too few."""
    H,W = Y.shape
    lo = box(Y, 17)
    cand = []
    ys = range(TILE, H-2*TILE, stride); xs = range(TILE, W-2*TILE, stride)
    for y in ys:
        for x in xs:
            t = Y[y:y+TILE, x:x+TILE]; tl = lo[y:y+TILE, x:x+TILE]
            m = float(t.mean())
            if m <= 1e-4: continue                       # absolute floor: not clipped black
            mod = float(tl.std())/m
            if mod > 0.05: continue                      # absolute floor: genuinely flat
            cand.append((mod, m, y, x))
    cand.sort()
    dark = sorted(cand, key=lambda c: c[1])[:max(1,len(cand)//2)]   # dark half
    return [(y,x) for _,_,y,x in dark[:max_tiles]], len(cand)

def corrlen(hp):
    hp = hp - hp.mean()
    den = float((hp*hp).mean())
    if den <= 0: return np.nan
    r=[1.0]
    for L in range(1, MAXLAG+1):
        cx = float((hp[:, :-L]*hp[:, L:]).mean()); cy = float((hp[:-L,:]*hp[L:,:]).mean())
        r.append(0.5*(cx+cy)/den)
    for L in range(1, MAXLAG+1):
        if r[L] < THR:
            a,b = r[L-1], r[L]
            return float(L-1 + (a-THR)/(a-b)) if a!=b else float(L)
    return float(MAXLAG)

def D1(planes, tiles):
    """planes = (Y,C1,C2). Returns median corrlen per channel over tiles."""
    out = {}
    for name, P in zip(("luma","R-Y","B-Y"), planes):
        hp = P - box(P, 9)
        v = [corrlen(hp[y:y+TILE, x:x+TILE]) for (y,x) in tiles]
        v = np.array([q for q in v if np.isfinite(q)])
        out[name] = (float(np.median(v)), float(np.percentile(v,25)), float(np.percentile(v,75)), len(v))
    return out

def show(tag, d):
    print(f"  {tag:<34}", end="")
    for k in ("luma","R-Y","B-Y"):
        m,q1,q3,n = d[k]; print(f"  {k}={m:5.2f} [{q1:4.2f},{q3:4.2f}]", end="")
    print(f"   tiles={d['luma'][3]}")

def dev(**kw):
    with rawpy.imread(ARW) as raw:
        return raw.postprocess(output_bps=16, gamma=(1,1), no_auto_bright=True,
                               use_camera_wb=True, output_color=rawpy.ColorSpace.sRGB,
                               demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD, **kw)

print("="*100); print("COMMISSIONING  (all three arms must pass before any verdict is read)"); print("="*100)

# ---- LibRaw, NR fully OFF -> the reference
a = dev(fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off, median_filter_passes=0, noise_thr=None)
ref = np.asarray(a, np.float32)/65535.0; del a
Yr,C1r,C2r = opponent(ref)
tiles_r, ncand = pick_tiles(Yr)
print(f"\nLibRaw grid: shape={ref.shape} flat-dark tiles={len(tiles_r)} (of {ncand} passing absolute floors)")
if len(tiles_r) < 40:
    print("ABORT: too few tiles met the absolute flatness floor; the site picker must be able to fail."); sys.exit(2)
d_ref = D1((Yr,C1r,C2r), tiles_r)
show("LibRaw  NR OFF   (reference)", d_ref)

# ---- C1 NULL: same data again
d_null = D1((Yr,C1r,C2r), tiles_r)
c1 = all(abs(d_ref[k][0]-d_null[k][0])<1e-12 for k in d_ref)
show("C1 null  (same frame twice)", d_null)
print(f"  C1 null -> ratio exactly 1.000 on all channels: {c1}")

# ---- C3 CLEAN FLOOR: synthetic white noise
wn = np.random.normal(0,1,(TILE,TILE)).astype(np.float32)
wn_hp = wn - box(wn,9); c3v = corrlen(wn_hp)
print(f"  C3 clean floor (white noise)        corrlen = {c3v:.2f} px")
del ref, Yr, C1r, C2r

# ---- C2 POTENCY: the identical RAW through a REAL denoiser
b = dev(fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Full, median_filter_passes=2, noise_thr=None)
nr = np.asarray(b, np.float32)/65535.0; del b
Yn,C1n,C2n = opponent(nr)
d_nr = D1((Yn,C1n,C2n), tiles_r)
show("LibRaw  FBDD-full + median x2", d_nr)
del nr, Yn, C1n, C2n
sep = {k: d_nr[k][0]/d_ref[k][0] for k in d_ref}
print("  C2 potency  denoised/reference:  " + "  ".join(f"{k}={sep[k]:.3f}x" for k in ("luma","R-Y","B-Y")))
c2 = max(sep["R-Y"], sep["B-Y"]) > 1.15
print(f"  C2 potency -> probe separates a REAL denoiser on chroma: {c2}")
c3 = c3v <= min(d_ref[k][0] for k in d_ref)
print(f"  C3 -> white noise reads shortest of anything measured: {c3}")

print()
if not (c1 and c2 and c3):
    print("COMMISSIONING FAILED -> no verdict may be read from this probe."); sys.exit(3)
print("COMMISSIONING PASSED on all three arms.")

print(); print("="*100); print("MEASUREMENT: the actual comparator input frame"); print("="*100)
im = tifffile.imread(LIN).astype(np.float32)/65535.0
Ys,C1s,C2s = opponent(im)
tiles_s, nc2 = pick_tiles(Ys)
print(f"\nstrehl-developed grid: shape={im.shape} flat-dark tiles={len(tiles_s)} (of {nc2})")
if len(tiles_s) < 40:
    print("ABORT: too few tiles."); sys.exit(2)
d_s = D1((Ys,C1s,C2s), tiles_s)
del im, Ys, C1s, C2s

print()
show("LibRaw  NR OFF   (reference)", d_ref)
show("strehl 740e7056 (COMPARATOR INPUT)", d_s)
show("LibRaw  FBDD-full (denoised)", d_nr)

print(); print("VERDICT against the pre-registered rule:")
for k in ("luma","R-Y","B-Y"):
    lo, me, hi = d_ref[k][0], d_s[k][0], d_nr[k][0]
    if me <= lo*1.05: v = "NO NR  (at or below the undenoised reference)"
    elif me >= lo + 0.5*(hi-lo): v = "NR PRESENT"
    else: v = "INDETERMINATE"
    print(f"  {k:<5} ref={lo:5.2f}  strehl={me:5.2f}  denoised={hi:5.2f}   ->  {v}")
np.savez(r"C:\dev\strehl-out\V-REVIEW\nr_d1.npz", ref=[d_ref[k][0] for k in ("luma","R-Y","B-Y")],
         s=[d_s[k][0] for k in ("luma","R-Y","B-Y")], nr=[d_nr[k][0] for k in ("luma","R-Y","B-Y")])
