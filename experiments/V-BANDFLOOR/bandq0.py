"""Is the merge's band 0 NOISE or SIGNAL on the high-averaged-fraction subjects?

ORCH's question: on subjects where band-0 averaged fraction is high, is the
merge correctly reporting an empty capture, or is the floor rejecting real signal?

THE BAND THIS ASKS ABOUT IS NOT V-LINEAR'S BAND 0. Measured: the merge emits
2344x3516 under --linear-srgb against 4688x7032 under --srgb, and the binary
states "one election per 2x2 CFA quad" on the PLANE grid. So merge band 0 = the
top octave of the plane grid = 0.125-0.25 cyc/px FULL-SENSOR. V-LINEAR's band 0
is 0.25-0.50 full-sensor -- one octave higher. Qualifying the wrong one is how
you get a correct-looking answer to the wrong question.

So this reports BOTH: the sub-bands spanning the merge's band 0, and the
sub-bands spanning V-LINEAR's band 0, side by side, per subject.

Instrument: V-LINEAR2/bandsignal.py, imported not reimplemented -- its BANDS,
FINE, ratio_ci, verdict, T, MARGIN, and its 5x6 grid placement. Validated: this
driver reproduced V-LINEAR's published 112MSDCF row digit-for-digit
(3.012/1.724/1.202/1.089/1.049).
"""
import os, sys, subprocess, shutil
import numpy as np, tifffile
R = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
sys.path.insert(0, os.path.join(R, "V-HEADTOHEAD2"))
sys.path.insert(0, os.path.join(R, "V-LINEAR2"))
import h2
from h2h2b import band_power
import bandsignal as BS

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SCRATCH = r"D:\strehl-out\V-BANDFLOOR\bandq0"          # heavy output on D:
os.makedirs(SCRATCH, exist_ok=True)

MERGE_B0 = [(0.11, 0.14), (0.14, 0.17), (0.17, 0.20), (0.20, 0.25)]
VL_B0    = [(0.25, 0.30), (0.30, 0.40), (0.40, 0.48)]
SUBJECTS = [s.strip() for s in sys.argv[1].split(",")]

allb = BS.BANDS + BS.FINE + [(BS.SEL_LO, BS.SEL_HI)]
lo = np.array([b[0] for b in allb]); hi = np.array([b[1] for b in allb])
nsel = len(allb) - 1
env = dict(os.environ); env["STREHL_ALIGN"] = "0"
tmp = os.path.join(SCRATCH, "f.tif"); one = os.path.join(SCRATCH, "one")

for subj in SUBJECTS:
    src = os.path.join(r"D:\personal\macro", subj)
    frames = sorted(f for f in os.listdir(src) if f.lower().endswith(".arw"))
    step = max(1, int(round(len(frames) / 80.0)))
    use = frames[::step]
    far = max(2, int(round(20.0 / step)))
    print("\n########## %s  N=%d  step=%d  used=%d  far=%d ##########"
          % (subj, len(frames), step, len(use), far), flush=True)
    power = None
    for k, f in enumerate(use):
        if os.path.exists(tmp): os.remove(tmp)
        shutil.rmtree(one, ignore_errors=True); os.makedirs(one, exist_ok=True)
        shutil.copy2(os.path.join(src, f), one)
        r_ = subprocess.run([EXE, "stack", one, "-o", tmp, "--linear-srgb", "--demosaic"],
                            capture_output=True, env=env)
        if not os.path.exists(tmp):
            print("DEVELOP FAILED %s: %s" % (f, r_.stderr.decode()[-300:])); break
        mm = tifffile.memmap(tmp, mode="r")
        if power is None:
            H, W = mm.shape[0], mm.shape[1]
            ys = np.linspace(BS.MARGIN, H - BS.MARGIN - BS.T, 5).astype(int)
            xs = np.linspace(BS.MARGIN, W - BS.MARGIN - BS.T, 6).astype(int)
            pos = [(int(y), int(x)) for y in ys for x in xs]
            power = np.zeros((len(use), len(pos), len(allb)))
        for i, (y, x) in enumerate(pos):
            c = h2.luma709(np.asarray(mm[y:y+BS.T, x:x+BS.T, :3], np.float64))
            bp = band_power(c, lo, hi)
            power[k, i] = np.nan if bp is None else bp
        del mm
        sys.stderr.write("\r  %d/%d" % (k + 1, len(use)))
    sys.stderr.write("\n")
    sel = power[:, :, nsel]; best = np.nanargmax(sel, axis=0)
    pf, pd, selr = [], [], []
    for i in range(power.shape[1]):
        b = int(best[i])
        if b < 1 or b > len(use) - 2: continue
        ref = [q for q in (b - far, b + far) if 0 <= q < len(use)]
        if not ref: continue
        pf.append(power[b, i]); pd.append(power[ref, i].mean(0)); selr.append(
            power[b, i, nsel] / power[ref, i, nsel].mean())
    pf, pd, selr = np.array(pf), np.array(pd), np.array(selr)
    conf = selr >= 2.0
    mask = conf if conf.sum() >= 4 else np.ones(len(pf), bool)
    tag = "CONFIRMED" if conf.sum() >= 4 else "ALL(fallback)"
    print("  %s n=%d of %d kept" % (tag, mask.sum(), len(pf)))
    for title, blist in (("MERGE band 0 (0.125-0.25 full-sensor)", MERGE_B0),
                         ("V-LINEAR band 0 (0.25-0.50)", VL_B0)):
        print("   %s" % title)
        for (a, b) in blist:
            j = allb.index((a, b))
            r, cl, ch = BS.ratio_ci(pf[mask, j], pd[mask, j])
            print("     %.2f-%.2f  R=%8.3f  [%6.3f,%6.3f]  %s"
                  % (a, b, r, cl, ch, BS.verdict(r, cl)))
