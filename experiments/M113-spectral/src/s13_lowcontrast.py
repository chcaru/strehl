"""M113 s13: the low-contrast regime, which s12 FAILED TO TEST.

s12 tried to establish that my estimator's quantisation immunity came from the
edge-energy floor selecting textured windows. It reported NOT CONFIRMED. That
report was wrong to phrase it as a refutation: at floor 5.0 and floor 0.0 the
window count saturated at 693, and 693 is the ENTIRE GRID (21 y-positions x 33
x-positions at STEP=100 on a 2344x3516 image). Every candidate window in bee-3
already exceeds an edge energy of 5, so lowering the floor admitted no smooth
content and the control could not fire. It tested nothing.

ORCH's damaging case was a low-contrast detail ROI left with NINE distinct
levels. This script creates that regime rather than hoping to find it: compress
contrast about the local mean by K before narrowing, so the occupied range -- and
therefore the surviving level count -- shrinks the way a low-contrast crop's
does. That is the condition under which dither should fail and a location
estimator should finally bias.
"""
import json, os, sys
import numpy as np

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                        # noqa: E402
from c4_globalfit import cs, fit_eps              # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_measure import measure_ch                 # noqa: E402

CA_LIN = r"C:\dev\strehl-out\M113-ca\lin"
TILE = c4g.TILE
c4g.STEP = 100

def run(arr, floor=0.0):
    H, W = arr.shape[:2]
    cx, cy = W / 2.0, H / 2.0
    ws = []
    for y0 in range(4, H - TILE - 4, c4g.STEP):
        for x0 in range(4, W - TILE - 4, c4g.STEP):
            g = np.asarray(arr[y0 + c4g.PAD:y0 + c4g.PAD + c4g.WIN,
                               x0 + c4g.PAD:x0 + c4g.PAD + c4g.WIN, 1]).astype(np.float32)
            if float(cs.grad_mag(g).mean()) < floor:
                continue
            ws.append((x0, y0))
    if len(ws) < 10:
        return float("nan"), len(ws), float("nan")
    e, tx, ty, n, rms = fit_eps(measure_ch(arr, ws, 0, cx, cy), cx, cy)
    return -e * 1e6, len(ws), rms

def levels(a, n=40):
    H, W = a.shape[:2]
    rng = np.random.default_rng(3); out = []
    for _ in range(n):
        y = int(rng.integers(0, H - TILE)); x = int(rng.integers(0, W - TILE))
        out.append(len(np.unique(np.asarray(a[y:y + TILE, x:x + TILE, 1]))))
    return float(np.median(out))

a0, W, H = cs.load_tiff_u16(os.path.join(CA_LIN, "bee-3-cpl-binned-off.tif"))
a0 = np.asarray(a0).astype(np.float32)
ny = len(range(4, H - TILE - 4, c4g.STEP)); nx = len(range(4, W - TILE - 4, c4g.STEP))
print("grid is %d x %d = %d candidate windows -- this is why s12's floor sweep saturated"
      % (ny, nx, ny * nx))

mean = a0.mean(axis=(0, 1), keepdims=True)
print("\n" + "=" * 100)
print("LOW-CONTRAST LADDER: compress contrast by K, then apply the PIL narrowing (>>8)")
print("=" * 100)
print("%-6s %12s %13s %13s %11s %10s %9s"
      % ("K", "levels/win", "truth ppm", "narrowed ppm", "err %", "windows", "rms px"))
out = []
for K in (1, 5, 20, 60, 150):
    lo = mean + (a0 - mean) / K
    t, nt, rt = run(lo)
    q = (np.clip(lo, 0, 65535).astype(np.uint16) >> 8).astype(np.float32) * 256.0
    lv = levels(q)
    e, nw, rms = run(q)
    err = 100 * (e / t - 1) if t == t and t else float("nan")
    print("%-6d %12.0f %13.1f %13.1f %+10.1f%% %10d %9.4f"
          % (K, lv, t, e, err, nw, rms))
    out.append(dict(K=K, levels=lv, truth=t, narrowed=e, err=err, wins=nw, rms=rms))
    del lo, q

print("\n" + "-" * 100)
brk = [r for r in out if not (abs(r["err"]) <= 5.0)]
if brk:
    f = max(brk, key=lambda r: r["levels"])
    print("FAILS at %.0f levels/window (K=%d): %.1f -> %.1f ppm, err %+.1f%%"
          % (f["levels"], f["K"], f["truth"], f["narrowed"], f["err"]))
    print("So the immunity IS conditional on the local signal spanning enough levels,")
    print("and ORCH's nine-level case sits in the failing regime.")
else:
    print("No failure across the ladder, down to %.0f levels/window." % min(r["levels"] for r in out))
    print("The location estimator is robust even in the low-contrast regime tested here.")
json.dump(out, open(r"C:\dev\strehl-out\M113-spectral\s13_lowcontrast.json", "w"),
          indent=2, default=float)
print("wrote s13_lowcontrast.json")