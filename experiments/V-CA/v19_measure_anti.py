import numpy as np, tifffile, os, json
OUT = r"C:\dev\strehl-out\V-CA-anti"
def rd(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, "EXPECTED uint16, GOT %s" % a.dtype
    return a.astype(np.float64)
arms = ["unset","zero","off","false","correct","anti"]
img = {a: rd(os.path.join(OUT, a+".tif")) for a in arms}
ref = img["unset"]
print("shape %s  dtype-checked uint16" % (ref.shape,))
# PRE-REGISTERED stencil: green |dx|+|dy|, top decile, computed ONCE on unset
g = ref[...,1]
grad = np.abs(np.diff(g,axis=1,prepend=g[:,:1])) + np.abs(np.diff(g,axis=0,prepend=g[:1,:]))
edge = grad >= np.percentile(grad, 90)
print("edge pixels %d (%.2f%% of frame)\n" % (edge.sum(), 100*edge.mean()))
Y = lambda a: 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2]
base = None
print("%-9s %14s %12s   %s" % ("arm","mean|R-Y| DN","vs unset %","note"))
print("-"*62)
res = {}
for a in arms:
    v = np.abs(img[a][...,0] - Y(img[a]))[edge].mean()
    if a == "unset": base = v
    d = 100*(v-base)/base
    res[a] = d
    print("%-9s %14.2f %11.3f%%" % (a, v, d))
print()
print("PRE-REGISTERED TESTS")
anti, corr = res["anti"], res["correct"]
gap = anti - corr
t1 = anti >= 8.0
t2 = gap >= 20.0
t3 = (corr < 0) and (anti > 0)
inert = abs(gap) < 2.0
print("  1. anti >= +8.0%%          : anti = %+.3f%%   -> %s" % (anti, "PASS" if t1 else "FAIL"))
print("  2. anti - correct >= 20pp : gap  = %+.3f pp  -> %s" % (gap, "PASS" if t2 else "FAIL"))
print("  3. signs oppose           : correct %+.3f%%, anti %+.3f%% -> %s" % (corr, anti, "PASS" if t3 else "FAIL"))
print("  FAILURE-THAT-MATTERS |gap|<2pp (inert): %s" % ("TRIGGERED" if inert else "not triggered"))
print()
print("  central prediction was anti = +26.7%% (transfer 0.213 x +125.0%% geometric)")
print("  correct measured here = %+.3f%%  (Addendum 5 on M110 renders: -16.00%%)" % corr)
# per-radius, since that is where Addendum 5/6 disagreed
h,w = g.shape; yy,xx = np.mgrid[0:h,0:w]
r = np.hypot(yy-h/2, xx-w/2); r /= r.max()
print("\n  per-radius %% change vs unset (edge px only):")
print("  %-9s %8s %10s %10s" % ("r","n","correct","anti"))
for lo in np.arange(0.0,0.9,0.1):
    m = edge & (r>=lo) & (r<lo+0.1)
    if m.sum() < 500: continue
    b = np.abs(ref[...,0]-Y(ref))[m].mean()
    c = 100*(np.abs(img['correct'][...,0]-Y(img['correct']))[m].mean()-b)/b
    an= 100*(np.abs(img['anti'][...,0]-Y(img['anti']))[m].mean()-b)/b
    print("  %.1f-%.1f  %8d %9.2f%% %9.2f%%" % (lo,lo+0.1,m.sum(),c,an))
json.dump(res, open(os.path.join(OUT,"metric.json"),"w"), indent=1)
