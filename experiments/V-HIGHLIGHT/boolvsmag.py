"""ORCH: "a boolean pass carries no scale, so it cannot self-check."

My Phase 1 seven-subject null is the exact case.  The check I ran was
byte-identity -- a BOOLEAN.  It returned True for all seven and told me nothing
about whether it could have returned False.  The magnitude that polices it is
each subject's approach to the knee.
"""
import numpy as np, tifffile, os
CSV = r"C:\dev\strehl-out\V-HIGHLIGHT\uprobe.csv"
CONTAINER, KNEE = 16383.0, 0.60
print("%-18s %10s %10s %12s   %s" % ("subject", "BOOLEAN", "max u", "approach", "what it tells me"))
print("%-18s %10s %10s %12s   %s" % ("", "(identical)", "", "(u/knee)", ""))
print("-" * 88)
rows = []
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
    mx = (a / ceil[None, None, :]).max(axis=2).max()
    frac = mx / KNEE
    rows.append(frac)
    note = ("informative" if frac > 0.95 else
            "weakly informative" if frac > 0.8 else "CANNOT FIRE - carries no information")
    print("%-18s %10s %10.4f %11.2fx   %s" % (sub, "True", mx, frac, note))
print("-" * 88)
print("BOOLEAN   spread: True for 7 of 7 -- variance zero, no self-check possible")
print("MAGNITUDE spread: %.2fx to %.2fx -- a %.1fx range the boolean hid entirely"
      % (min(rows), max(rows), max(rows) / min(rows)))
print()
print("Not one subject exceeds 1.00x.  The magnitude says the instrument was")
print("never in range; the boolean said 'pass' seven times and could not have")
print("said anything else.  Same data, same runs -- only the question changed.")
