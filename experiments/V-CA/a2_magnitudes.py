import numpy as np, tifffile
off = tifffile.imread(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\bee-1-cpl.tiff")
on  = tifffile.imread(r"C:\dev\strehl-out\REVIEW\ca\bee-1-cpl--cafix.tiff")
assert off.dtype == np.uint16 and on.dtype == np.uint16
print("ABSOLUTE magnitudes in DN (16-bit), whole frame:\n")
print("  %-3s %10s %10s %10s %12s %12s" % ("ch","mean|d|","median|d|","p99|d|","max|d|","%px moved"))
for i,ch in enumerate("RGB"):
    d = on[...,i].astype(np.int32) - off[...,i].astype(np.int32)
    a = np.abs(d)
    print("  %-3s %10.2f %10d %10d %12d %11.3f%%" %
          (ch, a.mean(), np.median(a), np.percentile(a,99), a.max(), 100*np.mean(a!=0)))
print("\nIs the G/B movement a 1-DN reduction-order noise floor, or real?")
for i,ch in enumerate("RGB"):
    d = np.abs(on[...,i].astype(np.int32) - off[...,i].astype(np.int32))
    nz = d[d!=0]
    print("  %s: of moved px, %.2f%% moved by exactly 1 DN, %.2f%% by <=2 DN, mean of moved = %.2f DN"
          % (ch, 100*np.mean(nz==1), 100*np.mean(nz<=2), nz.mean()))
