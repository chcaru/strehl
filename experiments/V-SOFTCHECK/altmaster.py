"""Point the SAME instrument at alternative numerators rendered by the SAME
binary from the SAME bracket, reusing the cached reference maxima verbatim.
The reference does not move between these rows, so any movement is the
numerator's."""
import os, sys, numpy as np, softcheck as S
from analyze import load, arms, line

subj = sys.argv[1]; gauge = sys.argv[2] if len(sys.argv) > 2 else "lin"
T = int(sys.argv[3]) if len(sys.argv) > 3 else 128
c = load(subj, gauge, T)
d = os.path.join(S.ROOT, gauge, subj)
oy, ox = c["oy"], c["ox"]
M0 = S.load_luma(os.path.join(d, "master.tiff"), gauge)
print(f"=== {subj}/{gauge}  alternative numerators, reference cache UNCHANGED")
for name, fn in (("shipped SOFT merge", "master.tiff"),
                 ("hard-max (PMax) control", "master_hardmax.tiff"),
                 ("soft + --pyramid-sharpen 1.5", "master_sharpen.tiff")):
    path = os.path.join(d, fn)
    if not os.path.exists(path): print(f"  {name}: MISSING"); continue
    M = S.load_luma(path, gauge)
    coef, rms, kp, tot = S.register(M0, M)
    cc = dict(c)
    cc["m_mid_alt"] = S.tile_means(S.dog(M, S.S_MID)**2, oy, ox, T)
    cc["m_hi_alt"]  = S.tile_means(S.dog(M, S.S_HI)**2,  oy, ox, T)
    r = arms(cc, m_plant="alt", f_key="none")
    print(line(f"  {name}", r, f"geom-vs-master rms={rms:.2f}px"))
