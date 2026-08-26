import numpy as np, tifffile
from PIL import Image
from scipy.ndimage import median_filter, maximum_filter

X0, Y0, S = 3200, 800, 800          # ORCH-specified crop origin
def crop(p):
    return tifffile.imread(p)[Y0:Y0+S, X0:X0+S].astype(np.float64)

arms = {
  "CA-on  (default, knee default)": r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-default.tiff",
  "CA-off (STREHL_FIX_CA=off)    ": r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-CAoff.tiff",
}
res = {}
for name, p in arms.items():
    a = crop(p)
    # magenta index in the VIEWED (sRGB-encoded) domain: what the eye sees
    m = (a[:,:,0] + a[:,:,2]) * 0.5 - a[:,:,1]
    # local excess: subtract a wide median so the bud's intrinsic green cancels
    exc = m - median_filter(m, size=41)
    res[name] = (a, m, exc)
    print("%s  max m %8.1f   max local-excess %8.1f   px exc>1500 %5d" %
          (name, m.max(), exc.max(), (exc > 1500).sum()))
    Image.fromarray(np.clip(a/257,0,255).astype(np.uint8)).save(
        "fba-crop-%s.png" % name.split()[0].replace("(",""))

on  = res["CA-on  (default, knee default)"]
off = res["CA-off (STREHL_FIX_CA=off)    "]
# fringe pixels = strongest local magenta excess in the CA-OFF arm
mask = off[2] > np.percentile(off[2], 99.9)
print("\nfringe population = top 0.1%% local magenta excess in CA-off arm: %d px" % mask.sum())
print("   local magenta excess at those SAME pixels:")
print("      CA-off : mean %8.1f   p90 %8.1f   max %8.1f" % (off[2][mask].mean(), np.percentile(off[2][mask],90), off[2][mask].max()))
print("      CA-on  : mean %8.1f   p90 %8.1f   max %8.1f" % (on [2][mask].mean(), np.percentile(on [2][mask],90), on [2][mask].max()))
print("   => CA correction removes %.1f%% of the magenta excess at the fringe"
      % (100.0*(1 - on[2][mask].mean()/off[2][mask].mean())))
d = off[0] - on[0]
print("\nCA correction moves the crop: %.4f%% of px, max|d| R %.0f G %.0f B %.0f"
      % (100.0*(d!=0).any(axis=2).mean(), np.abs(d[:,:,0]).max(), np.abs(d[:,:,1]).max(), np.abs(d[:,:,2]).max()))
