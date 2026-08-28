"""ORCH item 1: is band 0 at FLAT SITES on bee-1-cpl signal or noise, measured
with V-LINEAR's OWN frozen statistic rather than with my split-half instrument?

ORCH said not to grant me my own defence, so this does not use sigref at all.
It uses V-LINEAR2/bandsignal.py's R = P(best-focus)/P(defocused), its band list,
its bootstrap and its PASS/MARGINAL/FAIL rule, imported not reimplemented.

Three tile populations, same frames, same statistic:
  GRID  V-LINEAR's own 5x6 placement          -- CONTROL. Must reproduce 0.48.
  FLAT  the 12 sites the gate-floor comparison scores
  EDGE  the 12 sites it contrasts them against

Site coords come from the PLANE-grid master and are doubled, because the merge
runs at half sensor resolution and the develops are full resolution.
"""
import os, sys, subprocess, shutil
import numpy as np, tifffile
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD2")
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-LINEAR2")
import h2
from h2h2b import band_power
import bandsignal as BS
import slopetest as st

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = sys.argv[1] if len(sys.argv)>1 else r"D:\personal\macro\bee-1-cpl"
SCRATCH = r"C:\dev\strehl-out\V-BANDFLOOR\qual"
MASTER = sys.argv[2] if len(sys.argv)>2 else r"C:\dev\strehl-out\V-BANDFLOOR\nscale\bee1__EVEN__A-unset.tiff"
STEP = int(sys.argv[3]) if len(sys.argv)>3 else 4
FAR = int(sys.argv[4]) if len(sys.argv)>4 else 4
os.makedirs(SCRATCH, exist_ok=True)

m = tifffile.imread(MASTER)
g = h2.luma709(m.astype(np.float64))
fl, ed, nx = st.sites(g)
def coords(idx):
    return [(int(divmod(int(f), nx)[0]) * st.S * 2, int(divmod(int(f), nx)[1]) * st.S * 2)
            for f in idx]
flc, edc = coords(fl), coords(ed)
print("plane master %s -> full-res sites doubled; tile %d plane = %d full"
      % (str(g.shape), st.S, st.S * 2), flush=True)

frames = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".arw"))
use = frames[::STEP]
print("frames %d, using %d (step %d), far=%d" % (len(frames), len(use), STEP, FAR), flush=True)

allb = BS.BANDS + BS.FINE + [(BS.SEL_LO, BS.SEL_HI)]
lo = np.array([b[0] for b in allb]); hi = np.array([b[1] for b in allb])
nsel = len(allb) - 1

pops = {}
env = dict(os.environ); env["STREHL_ALIGN"] = "0"
tmp = os.path.join(SCRATCH, "f.tif")
for k, f in enumerate(use):
    if os.path.exists(tmp): os.remove(tmp)
    one = os.path.join(SCRATCH, "one")
    shutil.rmtree(one, ignore_errors=True); os.makedirs(one, exist_ok=True)
    shutil.copy2(os.path.join(SRC, f), one)
    r = subprocess.run([EXE, "stack", one, "-o", tmp,
                        "--linear-srgb", "--demosaic"],
                       capture_output=True, env=env)
    if not os.path.exists(tmp):
        print("DEVELOP FAILED %s\n%s" % (f, r.stderr.decode()[-500:])); sys.exit(1)
    mm = tifffile.memmap(tmp, mode="r")
    if k == 0:
        H, W = mm.shape[0], mm.shape[1]
        ys = np.linspace(BS.MARGIN, H - BS.MARGIN - BS.T, 5).astype(int)
        xs = np.linspace(BS.MARGIN, W - BS.MARGIN - BS.T, 6).astype(int)
        pops["GRID"] = ([(int(y), int(x)) for y in ys for x in xs], BS.T)
        pops["FLAT"] = (flc, st.S * 2)
        pops["EDGE"] = (edc, st.S * 2)
        print("develop %dx%d (master x2 = %dx%d)" % (H, W, g.shape[0]*2, g.shape[1]*2), flush=True)
        store = {n: np.zeros((len(use), len(p), len(allb))) for n, (p, _) in pops.items()}
    for n, (p, T) in pops.items():
        for i, (y, x) in enumerate(p):
            c = h2.luma709(np.asarray(mm[y:y+T, x:x+T, :3], np.float64))
            bp = band_power(c, lo, hi)
            store[n][k, i] = np.nan if bp is None else bp
    del mm
    sys.stderr.write("\rframe %d/%d" % (k + 1, len(use)))
os.remove(tmp)
sys.stderr.write("\n")

for n in ("GRID", "FLAT", "EDGE"):
    power = store[n]
    sel = power[:, :, nsel]; best = np.nanargmax(sel, axis=0)
    pf, pd, selr = [], [], []
    for i in range(power.shape[1]):
        b = int(best[i])
        if b < 1 or b > len(use) - 2: continue
        ref = [r for r in (b - FAR, b + FAR) if 0 <= r < len(use)]
        if not ref: continue
        pf.append(power[b, i]); pd.append(power[ref, i].mean(0))
        selr.append(power[b, i, nsel] / power[ref, i, nsel].mean())
    pf, pd, selr = np.array(pf), np.array(pd), np.array(selr)
    conf = selr >= 2.0
    print("\n===== %s =====  %d tiles kept, CONFIRMED %d" % (n, len(pf), conf.sum()))
    for label, mask in (("ALL", np.ones(len(pf), bool)), ("CONFIRMED", conf)):
        if mask.sum() < 4:
            print("  [%s] too few tiles (%d) -- NOT REPORTED" % (label, mask.sum())); continue
        print("  [%s] n=%d" % (label, mask.sum()))
        for j, (a, b) in enumerate(allb):
            if j == nsel or a < 0.10: continue
            r, cl, ch = BS.ratio_ci(pf[mask, j], pd[mask, j])
            print("    %.2f-%.2f  R=%8.3f  [%6.3f,%6.3f]  %s"
                  % (a, b, r, cl, ch, BS.verdict(r, cl)))
