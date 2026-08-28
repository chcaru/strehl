import numpy as np, glob, os
try:
    import tifffile
except ImportError:
    print("tifffile NOT AVAILABLE"); raise SystemExit(2)

root = r"C:\dev\strehl-out\BUILD-GATE\head\ab\G200"
print(f"{'subject':<26}{'clipped@65535':>15}{'median':>10}{'p99.9':>10}  verdict")
print("-"*75)
worst = 0.0
for f in sorted(glob.glob(os.path.join(root,"*.tif*"))):
    a = tifffile.imread(f)
    a = a.astype(np.uint16, copy=False)
    clip = float((a == 65535).mean())
    med  = float(np.median(a))
    p999 = float(np.percentile(a, 99.9))
    worst = max(worst, clip)
    verdict = "BLOWN" if clip > 0.25 else "clean"
    print(f"{os.path.basename(f):<26}{clip*100:>14.2f}%{med:>10.0f}{p999:>10.0f}  {verdict}")
print("-"*75)
print(f"worst clipped fraction across the 5 section-15 NULL masters: {worst*100:.2f}%")
print("ORCH's BLOWN threshold is >25%; ORCH measured 11 of 18 HEAD --auto-exposure")
print("masters BLOWN, worst 92.13%, several with a pure-white (65535) median.")
