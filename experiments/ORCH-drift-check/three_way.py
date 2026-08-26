import glob, os, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
def m(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    y = 0.2126*a[...,0]+0.7152*a[...,1]+0.0722*a[...,2]
    mx=a.max(axis=2); mn=a.min(axis=2)
    sat=np.where(mx>8,(mx-mn)/np.maximum(mx,1e-9),np.nan)
    return np.percentile(y,75)-np.percentile(y,25), np.nanmean(sat), np.percentile(y,1)
B=r"C:\dev\strehl-out\SHIP-V2-ICC"
print(f"{'subject':<26} {'midtone contrast (p75-p25)':^34} | {'saturation':^22}")
print(f"{'':<26} {'faithful':>10}{'shipped':>11}{'FIXED':>11} | {'faith':>7}{'ship':>7}{'FIXED':>7}")
print("-"*90)
for f in sorted(glob.glob(r"C:\dev\strehl-out\ORCH-GRADE\*--fixed.jpg")):
    s = os.path.basename(f).replace("--fixed.jpg","")
    fa = glob.glob(os.path.join(B,"_faithful",s+"*.jpg"))
    pr = glob.glob(os.path.join(B,"_presentation",s+"*.jpg"))
    if not fa or not pr: continue
    a=m(fa[0]); b=m(pr[0]); c=m(f)
    print(f"{s:<26} {a[0]:10.1f}{b[0]:11.1f}{c[0]:11.1f} | {a[1]:7.3f}{b[1]:7.3f}{c[1]:7.3f}")
