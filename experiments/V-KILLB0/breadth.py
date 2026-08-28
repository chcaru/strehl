"""V-KILLB0 breadth.py -- does SELF-TARGETING hold beyond two subjects?

Self-targeting means: at STRUCTURED sites the knob does nothing, at FLAT sites
it removes a lot.  That is a two-sided claim and both sides must be measured on
the same subject with the same instrument.  bee-1-cpl satisfies it perfectly
and leaf-2-cpl violates it catastrophically; this settles which of the two the
rest of the corpus resembles.

BAND CHOICE, under ORCH correction #4 (no fixed band, no cross-subject band
ratios).  I report each subject's OWN arm ratio -- never a ratio of ratios
across subjects.  The scoring band is 0.05-0.14 cyc/px, which lies BELOW the
lowest boundary V-LINEAR measured on any subject (flower-bud, 0.17) across a
2.8x spread, so on all five measured subjects it is qualified SIGNAL.  For the
fourteen subjects V-LINEAR has not measured this is an ASSUMPTION and is
flagged UNQUAL in the output; it is the most conservative band available, not a
proven one.

0.30-0.48 is also printed: that is where the knob nominally acts, so a
self-targeting knob should move it at flat sites and not at structured ones.
"""
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp

OUT = r"C:\dev\strehl-out\V-KILLB0"
SIG = (0.05, 0.14)      # below every measured boundary
TGT = (0.30, 0.48)      # where the knob nominally acts
QUAL = {"bee-1-cpl": 0.48, "113MSDCF": 0.25, "119MSDCF": 0.25,
        "leaf-2-cpl": 0.20, "flower-bud-alone-cpl": 0.17}


def radial(img, f0, f1):
    a = np.fft.rfft2(img.astype(np.float32))
    h, w = img.shape
    r = np.hypot(np.fft.fftfreq(h)[:, None], np.fft.rfftfreq(w)[None, :])
    a *= ((r >= f0) & (r < f1))
    return np.fft.irfft2(a, s=img.shape)


def score(la, lb, f0, f1, m):
    a = radial(la, f0, f1)[m].astype(np.float64)
    b = radial(lb, f0, f1)[m].astype(np.float64)
    a -= a.mean(); b -= b.mean()
    ea, eb = np.sqrt((a * a).mean()), np.sqrt((b * b).mean())
    return (eb / ea if ea else np.nan), ((a * b).mean() / (ea * eb) if ea and eb else np.nan)


arm = sys.argv[1] if len(sys.argv) > 1 else "b0x4"
subs = sorted(os.path.splitext(f)[0] for f in os.listdir(os.path.join(OUT, arm))
              if f.endswith(".tiff"))
print(f"== BREADTH  {arm} vs default   SIG band {SIG[0]}-{SIG[1]} (below every measured "
      f"boundary)   TGT band {TGT[0]}-{TGT[1]}")
print(f"{'subject':<26} {'qual':>6} {'median':>7} {'clip%':>6} {'blk%':>6} "
      f"| {'SIG STRUCT':>10} {'rho':>6} {'SIG FLAT':>9} "
      f"| {'TGT STRUCT':>10} {'rho':>6} {'TGT FLAT':>9}")
for s in subs:
    pa = os.path.join(OUT, "default", s + ".tiff")
    pb = os.path.join(OUT, arm, s + ".tiff")
    la = bp.channels(bp.load(pa))["L"]
    lb = bp.channels(bp.load(pb))["L"]
    if la.shape != lb.shape:
        print(f"{s:<26} SHAPE MISMATCH {la.shape} {lb.shape}")
        continue
    sel = gaussian_filter(np.abs(radial(la, 0.030, 0.085)), 3.0)
    st = sel >= np.percentile(sel, 75)
    fl = sel < np.percentile(sel, 25)
    ss, sr = score(la, lb, SIG[0], SIG[1], st)
    fs, _ = score(la, lb, SIG[0], SIG[1], fl)
    ts, tr = score(la, lb, TGT[0], TGT[1], st)
    tf, _ = score(la, lb, TGT[0], TGT[1], fl)
    q = f"{QUAL[s]:.2f}" if s in QUAL else "UNQUAL"
    print(f"{s:<26} {q:>6} {np.median(la):7.0f} {100*(la>=65000).mean():6.3f} "
          f"{100*(la<=200).mean():6.3f} | {ss:10.4f} {sr:6.3f} {fs:9.4f} "
          f"| {ts:10.4f} {tr:6.3f} {tf:9.4f}", flush=True)
