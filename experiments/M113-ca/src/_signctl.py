import importlib.util, os, sys, numpy as np
sys.path.insert(0, os.getcwd())
from lk import fshift2, lk_shift
ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
spec = importlib.util.spec_from_file_location("cs", os.path.join(ORCH, "ca_shift.py"))
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)
TILE, PAD, WIN = 256, 64, 128

def ncc_int(r, g, lo=-4, hi=4):
    best, bestv = None, -2.0
    gg = g[PAD:PAD+WIN, PAD:PAD+WIN]; gg = (gg-gg.mean())/(gg.std()+1e-9)
    for d in range(lo, hi+1):
        rr = r[PAD:PAD+WIN, PAD-d:PAD-d+WIN]; rr = (rr-rr.mean())/(rr.std()+1e-9)
        v = float((rr*gg).mean())
        if v > bestv: bestv, best = v, d
    return best

off, W, H = cs.load_tiff_u16(r"C:\dev\strehl-out\M114-ca-verify\r1\off.tif")
cx, cy = W/2.0, H/2.0; half = float(np.hypot(cx, cy))
wins=[]
for k in range(180):
    th=2.0*np.pi*k/180
    px,py = cx+0.50*half*np.cos(th), cy+0.50*half*np.sin(th)
    x0,y0 = int(round(px-TILE/2.0)), int(round(py-TILE/2.0))
    if x0<4 or y0<4 or x0+TILE>W-4 or y0+TILE>H-4: continue
    g=np.asarray(off[y0+PAD:y0+PAD+WIN, x0+PAD:x0+PAD+WIN,1]).astype(np.float32)
    if float(cs.grad_mag(g).mean())<cs.MIN_EDGE_ENERGY: continue
    wins.append((x0,y0))
    if len(wins)>=40: break

print("SIGN CONTROL for ncc_int: plant a KNOWN integer shift into R.")
print("Convention under test: does argmax d equal +plant or -plant?")
print()
print("%-8s %10s %10s %12s" % ("plant", "NCC med d", "LK med sx", "ORCH med dx"))
for plant in (-2,-1,0,1,2):
    nd, lkv, ov = [], [], []
    for (x0,y0) in wins:
        tr=np.asarray(off[y0:y0+TILE, x0:x0+TILE,0]).astype(np.float64)
        tg=np.asarray(off[y0:y0+TILE, x0:x0+TILE,1]).astype(np.float64)
        trs = np.roll(tr, plant, axis=1) if plant else tr
        nd.append(ncc_int(trs, tg))
        sx,sy,c = lk_shift(trs, tg, PAD, WIN)
        if np.isfinite(sx) and c>1e-4: lkv.append(sx)
        dyo,dxo,pk = cs.shift_of(trs[PAD:PAD+WIN,PAD:PAD+WIN].astype(np.float32),
                                 tg[PAD:PAD+WIN,PAD:PAD+WIN].astype(np.float32))
        if pk>=cs.MIN_PEAK and abs(dxo)<cs.MAX_SHIFT: ov.append(dxo)
    print("%-8d %10.2f %10.4f %12.4f" % (plant, float(np.median(nd)), float(np.median(lkv)), float(np.median(ov))))
print()
print("np.roll(tr, plant, axis=1) moves R content by +plant px, so the true")
print("displacement of R relative to G increases by exactly +plant.")