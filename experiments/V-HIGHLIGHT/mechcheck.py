"""Measure the mechanism I relied on instead of trusting it.

I asserted u_c = v_c/(k0*wb_c) cancels to (dn-black)/(CONTAINER-black),
independent of white balance.  If that is true it makes a sharp prediction:
u * (CONTAINER-black) must land on INTEGERS, because raw DN is integral.
If my ceiling arithmetic were wrong the residuals would be scattered.
"""
import numpy as np, tifffile, os
CSV = r"C:\dev\strehl-out\V-HIGHLIGHT\uprobe.csv"
CONTAINER = 16383.0
print("%-18s %8s %10s %10s %9s" % ("subject", "max u", "implied DN", "nearest", "residual"))
print("-" * 60)
res = []
for line in open(CSV):
    line = line.strip()
    if not line: continue
    sub, black, white, wr, wg, wb_ = line.split(",")
    black, white = float(black), float(white)
    k0 = (CONTAINER - black) / (white - black)
    ceil = k0 * np.array([float(wr), float(wg), float(wb_)])
    p = r"C:\dev\strehl-out\V-HIGHLIGHT\u-%s.tiff" % sub
    if not os.path.exists(p): continue
    a = tifffile.imread(p).astype(np.float64) / 65535.0
    u = (a / ceil[None, None, :]).max(axis=2)
    mx = u.max()
    dn = black + mx * (CONTAINER - black)
    r = abs(dn - round(dn))
    res.append(r)
    print("%-18s %8.5f %10.3f %10d %9.3f" % (sub, mx, dn, round(dn), r))
print("-" * 60)
print("max residual from integer DN : %.4f" % max(res))
print("mean residual                : %.4f" % (sum(res)/len(res)))
print()
if max(res) < 0.5:
    print("Every implied DN lands within %.3f of an integer.  A wrong ceiling" % max(res))
    print("would not do this -- the residuals would be scattered uniformly over")
    print("[0, 0.5], mean ~0.25.  The WB cancellation is measured, not assumed.")
else:
    print("RESIDUALS TOO LARGE -- the cancellation does NOT hold; my u values are")
    print("suspect and the seven-subject knee measurement must be redone.")
print()
# null: what a WRONG ceiling looks like, same data
bad = []
for line in open(CSV):
    line = line.strip()
    if not line: continue
    sub, black, white, wr, wg, wb_ = line.split(",")
    black, white = float(black), float(white)
    ceil = np.array([float(wr), float(wg), float(wb_)])      # k0 omitted
    p = r"C:\dev\strehl-out\V-HIGHLIGHT\u-%s.tiff" % sub
    if not os.path.exists(p): continue
    a = tifffile.imread(p).astype(np.float64) / 65535.0
    mx = (a / ceil[None, None, :]).max(axis=2).max()
    dn = black + mx * (CONTAINER - black)
    bad.append(abs(dn - round(dn)))
print("NEGATIVE CONTROL (drop k0 from the ceiling, same pixels):")
print("  max residual %.4f   mean %.4f" % (max(bad), sum(bad)/len(bad)))
