import pathlib, sys
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter
sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import radial_power, sigma_immerkaer, va_blur_px

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
img = tifffile.imread(str(R / "leaf-2-cpl" / "merge.tif"))
t = img[900:1700, 1400:2200, 1].astype(np.float64)
for sig in (0.3, 0.5):
    tb = gaussian_filter(t, sig)
    for dn in (True, False):
        sm = sigma_immerkaer(t) if dn else None
        sa = sigma_immerkaer(tb) if dn else None
        k,Pm,Nm = radial_power(t, sm, 320)
        k,Pa,Na = radial_power(tb, sa, 320)
        y = np.log(Pa[34:201]) - np.log(Pm[34:201])
        kk = k[34:201].astype(float)
        pred = -4*np.pi**2*(sig/800.0)**2*kk**2
        print(f"sig={sig} denoise={dn}  VA={va_blur_px(t,tb,denoise=dn):+.4f}")
        print("   k     y_obs    y_pred(exact)")
        for kx in (34,60,100,140,180,200):
            i = kx-34
            print(f"  {kx:>4}  {y[i]:+8.4f}   {pred[i]:+8.4f}")
