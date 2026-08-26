import numpy as np, tifffile
off = tifffile.imread(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\bee-1-cpl.tiff")
on  = tifffile.imread(r"C:\dev\strehl-out\REVIEW\ca\bee-1-cpl--cafix.tiff")
assert off.dtype == np.uint16 and on.dtype == np.uint16
print("DECISIVE TEST.  A global tone-curve change is a PER-VALUE LOOKUP: it has no spatial")
print("content, so d = f(value_off) exactly.  A CA correction is SPATIAL: two pixels with the")
print("same value but different neighbourhoods move differently.")
print("So: regress d on a 65536-bin lookup of the OFF value and report the variance explained.\n")
print("  %-3s %14s %14s %16s" % ("ch","var(d)","var explained","residual (spatial)"))
for i,ch in enumerate("RGB"):
    v = off[...,i].ravel()
    d = (on[...,i].astype(np.int32) - off[...,i].astype(np.int32)).ravel().astype(np.float64)
    cnt = np.bincount(v, minlength=65536).astype(np.float64)
    sm  = np.bincount(v, weights=d, minlength=65536)
    lut = np.divide(sm, cnt, out=np.zeros_like(sm), where=cnt > 0)
    pred = lut[v]
    sst = ((d - d.mean())**2).sum()
    ssr = ((d - pred)**2).sum()
    print("  %-3s %14.1f %13.4f%% %15.4f%%   (resid sd %.2f DN)"
          % (ch, d.var(), 100*(1-ssr/sst), 100*ssr/sst, np.sqrt(ssr/d.size)))
print("\nInterpretation: ~100%% explained  => that channel moved ONLY because of the tone curve.")
print("                large residual    => that channel carries a real spatial correction.")
