import numpy as np, tifffile, glob, os
# NEGATIVE CONTROL FOR ORCH'S EXPOSURE REGRESSION.
# A band ratio measures relationships between neighbouring pixels.  A saturated
# region has none, so a clipped develop would read as "no signal in any band" --
# which is exactly the verdict just returned for 112MSDCF at 0.25-0.50.  If
# these develops are blown, that verdict is an artifact of the render and not a
# property of the subject.  Measure before believing it.
for key in ["112MSDCF"]:
    fs = sorted(glob.glob(rf"C:\dev\strehl-out\V-LINEAR\r2\{key}\lintiff\*.tif"))
    print(f"{key}: {len(fs)} develops")
    for p in [fs[0], fs[len(fs)//2], fs[-1]]:
        a = tifffile.imread(p)
        hi = int((a == 65535).sum()); lo = int((a == 0).sum())
        print(f"  {os.path.basename(p):16s} median={int(np.median(a)):6d} mean={a.mean():9.1f} "
              f"max={int(a.max()):6d}  clipped_hi={100.0*hi/a.size:6.3f}%  zero={100.0*lo/a.size:6.3f}%")
