import numpy as np, tifffile
OFF = r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\bee-1-cpl.tiff"
ON  = r"C:\dev\strehl-out\REVIEW\ca\bee-1-cpl--cafix.tiff"
def rd(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, "EXPECTED uint16 GOT %s" % a.dtype
    return a
off, on = rd(OFF), rd(ON)
print("shape %s dtype %s   ptp off=%d on=%d" % (off.shape, off.dtype, np.ptp(off), np.ptp(on)))
def srgb_to_lin(u16):
    c = u16.astype(np.float32)/65535.0
    return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4).astype(np.float32)
# THE MATRIX PREDICTION.  crate camera_to_srgb (verified in V-CA-audit Addendum 6):
M = np.array([[ 1.636062,-0.448619,-0.187443],
              [-0.115165, 1.488971,-0.373806],
              [-0.004740,-0.323601, 1.328341]])
pg, pb = M[1,0]/M[0,0], M[2,0]/M[0,0]
print("\nIF the correction is a PURE camera-red operation (V-CA verified: G,B move on 0 px in")
print("camera space), then in LINEAR sRGB every pixel must obey, exactly:")
print("   dG/dR = M10/M00 = %+.6f      dB/dR = M20/M00 = %+.6f" % (pg, pb))
dR = srgb_to_lin(on[...,0]) - srgb_to_lin(off[...,0])
dG = srgb_to_lin(on[...,1]) - srgb_to_lin(off[...,1])
dB = srgb_to_lin(on[...,2]) - srgb_to_lin(off[...,2])
print("\nMEASURED (whole frame, linear sRGB):")
print("  %% px moved:  R %.3f%%   G %.3f%%   B %.3f%%" %
      (100*np.mean(dR!=0), 100*np.mean(dG!=0), 100*np.mean(dB!=0)))
print("  mean|dG|/mean|dR| = %.5f   (matrix predicts %.5f)" % (np.abs(dG).mean()/np.abs(dR).mean(), abs(pg)))
print("  mean|dB|/mean|dR| = %.5f   (matrix predicts %.5f)" % (np.abs(dB).mean()/np.abs(dR).mean(), abs(pb)))
m = dR != 0
sub = np.random.default_rng(0).choice(np.flatnonzero(m), size=min(3_000_000, m.sum()), replace=False)
x = dR.ravel()[sub]
for lab, d, pred in (("G", dG, pg), ("B", dB, pb)):
    y = d.ravel()[sub]
    sl = float(np.dot(x,y)/np.dot(x,x))
    r2 = float(1 - ((y-sl*x)**2).sum()/((y-y.mean())**2).sum())
    print("  regress d%s on dR: slope %+.6f  (matrix %+.6f, err %+.2f%%)   r^2 = %.5f"
          % (lab, sl, pred, 100*(sl-pred)/abs(pred), r2))
