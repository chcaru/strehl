"""Was my Phase 1 seven-subject null in the roll-off's sensitive range at all?

Standing question: what property of the input decides whether this check can see
anything?  For a knee-gated roll-off it is the subject's max u.  I never varied
-- or even measured -- it.  Doing that now.
"""
import numpy as np, tifffile, os
CSV = r"C:\dev\strehl-out\V-HIGHLIGHT\uprobe.csv"
CONTAINER = 16383.0
KNEE = 0.60
print("%-18s %8s %8s %8s   %s" % ("subject", "max u", "p99.99", "raw DN", "verdict"))
print("-" * 74)
rows = []
for line in open(CSV):
    line = line.strip()
    if not line:
        continue
    sub, black, white, wr, wg, wb_ = line.split(",")
    black, white = float(black), float(white)
    k0 = (CONTAINER - black) / (white - black)
    ceil = k0 * np.array([float(wr), float(wg), float(wb_)])
    p = r"C:\dev\strehl-out\V-HIGHLIGHT\u-%s.tiff" % sub
    if not os.path.exists(p):
        print("%-18s  MISSING RENDER" % sub); continue
    a = tifffile.imread(p).astype(np.float64) / 65535.0
    u = (a / ceil[None, None, :]).max(axis=2)
    mx = u.max()
    rows.append((sub, mx))
    print("%-18s %8.4f %8.4f %8.0f   %s"
          % (sub, mx, np.percentile(u, 99.99),
             black + mx * (CONTAINER - black),
             "REACHES knee" if mx > KNEE else "below knee -- roll-off CANNOT fire"))
print("-" * 74)
above = [s for s, m in rows if m > KNEE]
print("subjects able to reach the %.2f knee: %d of %d" % (KNEE, len(above), len(rows)))
print("max u across all seven          : %.4f" % max(m for _, m in rows))
print()
if not above:
    print("CONCLUSION: every one of the seven sits below the knee.  Their")
    print("byte-identity was GUARANTEED A PRIORI and is not evidence about the")
    print("roll-off.  My 'widened to 8 subjects' overstated the null's support.")
else:
    print("CONCLUSION: %d subject(s) could have moved and did not -- those are"
          % len(above))
    print("real evidence: %s" % ", ".join(above))
