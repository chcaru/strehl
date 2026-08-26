"""Does a global RMS hide a large fractional loss inside low-amplitude texture?
ORCH's hypothesis, tested directly: stratify retention by LOCAL AMPLITUDE decile.

Strata are defined ONCE, on the UNCLAMPED reference arm, so both arms are scored
on identical pixel populations (the defect found in accept.py). Band-limited:
h = g - Gauss(g, 2.0); local amplitude a = Gauss(|h|, 4.0); retention per decile
= RMS(h_clamped)/RMS(h_unclamped) over that decile's pixels.
"""
import sys
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter
def G(p):
    im = tifffile.imread(p); assert im.dtype == np.uint16
    return im[:,:,1].astype(np.float32)
subj, cp, up = sys.argv[1], sys.argv[2], sys.argv[3]
gc, gu = G(cp), G(up)
hc = gc - gaussian_filter(gc, 2.0, mode="reflect")
hu = gu - gaussian_filter(gu, 2.0, mode="reflect")
amp = gaussian_filter(np.abs(hu), 4.0, mode="reflect")     # strata from REFERENCE arm
qs = np.percentile(amp[::3,::3], np.arange(0,101,10))
print("%s   global retention %.2f%%" % (subj, 100*np.sqrt((hc.astype(np.float64)**2).mean()/(hu.astype(np.float64)**2).mean())))
print("%6s %14s %12s %12s %10s %12s" % ("decile","amp range DN","RMS unclamp","RMS clamp","retained","share of loss"))
tot_loss = float((hu.astype(np.float64)**2).sum() - (hc.astype(np.float64)**2).sum())
for i in range(10):
    m = (amp >= qs[i]) & (amp < qs[i+1]) if i < 9 else (amp >= qs[i])
    n = int(m.sum())
    if n == 0: continue
    ru = float(np.sqrt((hu[m].astype(np.float64)**2).mean()))
    rc = float(np.sqrt((hc[m].astype(np.float64)**2).mean()))
    loss = float((hu[m].astype(np.float64)**2).sum() - (hc[m].astype(np.float64)**2).sum())
    print("%6d %6.0f-%-7.0f %12.1f %12.1f %9.2f%% %11.1f%%"
          % (i+1, qs[i], qs[i+1] if i<9 else amp.max(), ru, rc, 100*rc/ru, 100*loss/tot_loss))
