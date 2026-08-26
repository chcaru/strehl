import numpy as np, tifffile
# Camera-native render: out = clamp(v,0,1)*65535, v normalised so Levels::white = 1.
a = tifffile.imread(r"C:\dev\strehl-out\V-HIGHLIGHT\fba-cam.tiff").astype(np.float64)
v = a / 65535.0
BLACK, WHITE, CONTAINER = 512.0, 15360.0, 16383.0
rng = WHITE - BLACK
k0 = (CONTAINER - BLACK) / rng
wb = np.array([2.6464844, 1.0, 1.4589844])
ceil = k0 * wb                       # exposure gain = 1 (no --exposure flag)
print("levels black %.0f white %.0f  range %.0f" % (BLACK, WHITE, rng))
print("k0 = (container-black)/range = %.6f" % k0)
print("wb coeffs (probe)      : R %.4f G %.4f B %.4f" % tuple(wb))
print("per-channel ceiling    : R %.4f G %.4f B %.4f" % tuple(ceil))
print("green has %.2fx less headroom than blue, %.2fx less than red"
      % (ceil[1]/ceil[1]*ceil[2]/ceil[1], ceil[0]/ceil[1]))
u = v / ceil[None, None, :]
umax = u.max(axis=2)
print("\n--- u = v_c / ceiling_c, the WB-invariant fraction of raw headroom ---")
print("frame max u            : %.4f" % umax.max())
for q in [50, 90, 99, 99.9, 99.99, 100]:
    print("   p%-6s u = %.4f" % (q, np.percentile(umax, q)))
print("argmax channel of u    : R %.2f%%  G %.2f%%  B %.2f%%"
      % tuple(100.0*(u.argmax(axis=2) == c).mean() for c in range(3)))
print("\nKNEE = 0.60. Pixels above it: %d (%.6f%%)" % ((umax > 0.60).sum(), 100.0*(umax > 0.60).mean()))
print("Headroom to the knee   : max u is %.4f, which is %.4f BELOW the knee (%.1f%% of the way there)"
      % (umax.max(), 0.60 - umax.max(), 100.0*umax.max()/0.60))
# what raw DN does the brightest pixel correspond to?
print("\nbrightest pixel: raw DN = black + u*(container-black) = %.0f DN of a %d container"
      % (BLACK + umax.max()*(CONTAINER-BLACK), CONTAINER))
print("camera-native max per channel (of 65535): R %.0f G %.0f B %.0f" % tuple(a[:,:,c].max() for c in range(3)))
print("pixels at 65535 in camera-native: %.6f%%" % (100.0*(a >= 65535).any(axis=2).mean()))
