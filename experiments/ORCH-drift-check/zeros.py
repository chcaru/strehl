import numpy as np, tifffile, glob, os
def L(a): return 0.2126*a[:,:,0]+0.7152*a[:,:,1]+0.0722*a[:,:,2] if a.ndim==3 else a
subs = sorted({os.path.basename(p).split("--")[0] for p in glob.glob("clean6/*--ctrl.tiff")})
print(f"{'subject':32s} {'arm':6s} {'exact0 px':>12s} {'exact0 %':>9s} {'luma<500 %':>11s} {'med DN':>9s}")
print("-"*86)
req, scored, missing = len(subs), 0, []
for s in subs:
    c, b = f"clean6/{s}--ctrl.tiff", f"clean6/{s}--blend.tiff"
    if not (os.path.exists(c) and os.path.exists(b)):
        missing.append(s); continue
    scored += 1
    for nm, p in (("ctrl", c), ("blend", b)):
        a = tifffile.imread(p).astype(np.float64)
        z = (a <= 0).all(axis=2) if a.ndim==3 else (a<=0)
        y = L(a)
        print(f"{s:32s} {nm:6s} {z.sum():12,} {100*z.mean():8.3f}% {100*(y<500).mean():10.3f}% {np.median(y):9.1f}")
    print()
print(f"SUMMARY requested {req}  scored {scored}  missing {len(missing)} {missing}")
assert scored + len(missing) == req
