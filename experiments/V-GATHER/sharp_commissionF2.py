"""Final commissioning of statistic F, with the two arms that were mis-built on
the first pass repaired: NULL needs minframes=1 (a one-frame reference set can
never satisfy MIN_FRAMES=3), and AMPLITUDE must sit INSIDE the content gate.
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB, sharp_F as SF

def line(tag, r, exp):
    s = SF.summarise(r)
    if s is None:
        print("%-52s %10s %7s   %s" % (tag, "REFUSED", "-", exp)); return None
    print("%-52s %10.6f %7d   %s" % (tag, s[0], s[3], exp)); return s[0]

def main(subj):
    z = SB.build(subj); nf = z["A"].shape[0]
    print("########## %s  (%d frames) ##########" % (subj, nf))
    print("%-52s %10s %7s   %s" % ("arm", "F median", "sites", "expected"))
    print("-" * 92)
    base = SF.evaluate(z); b = line("BASELINE  master vs per-patch best frame", base, "")
    print()
    j = nf // 2
    line("NULL      numerator = frame %d, set = {frame %d}" % (j, j),
         SF.evaluate(z, numer=0, refidx=(np.arange(nf) == j), minframes=1),
         "== 1.000000 EXACTLY")
    for g in (1.1, 1.3, 1.6):
        line("AMPLITUDE master x %.1f (pure gain, inside the gate)" % g,
             SF.evaluate(z, mgain=g), "== BASELINE %.6f" % b)
    line("AMPLITUDE master x 4.0 (pure gain, OUTSIDE the gate)",
         SF.evaluate(z, mgain=4.0), "REFUSED, not a wrong number")
    print()
    for jj in (nf//4, nf//2, 3*nf//4):
        line("PHYSICS   numerator = frame %d, set CONTAINS it" % jj,
             SF.evaluate(z, numer=jj), "<= 1.0 by construction")
    print()
    for s_ in (0.4, 0.8, 1.6):
        line("NUM       master blurred sigma %.1f" % s_, SF.evaluate(z, mblur=s_), "< BASELINE, monotone")
    for s_ in (0.4, 0.8, 1.6):
        line("NUM       master unsharp-masked %.1f" % s_, SF.evaluate(z, msharp=s_), "> BASELINE, monotone")
    print()
    line("DEN       best frame removed", SF.evaluate(z, dropbest=True), "> BASELINE")
    for k in (2, 3):
        line("DEN       keep 1 reference frame in %d" % k, SF.evaluate(z, refkeep=k), "> BASELINE")
    for s_ in (0.4, 0.8):
        line("DEN       every reference frame blurred %.1f" % s_, SF.evaluate(z, refblur=s_), "> BASELINE")
    line("DEN       every reference frame sharpened", SF.evaluate(z, refsharp=0.8), "< BASELINE")
    print("\n--- PARTITION (sites) ---")
    tot = base["nsites"]; meas = int(base["ok"].sum())
    print("  %4d passed the absolute floors and entered the test" % tot)
    print("  %4d MEASURED" % meas)
    print("  %4d refused: master detail band is noise-dominated" % base["r_noisy"])
    print("  %4d refused: fewer than %d reference frames passed the content gate"
          % (base["r_fewframes"], SF.MIN_FRAMES))
    print("  %4d sum" % (meas + base["r_noisy"] + base["r_fewframes"]))
    bk = base["bestk"][base["ok"]]
    ends = int(((bk <= 1) | (bk >= nf - 2)).sum())
    print("  denominator stack-end picks: %d/%d = %.1f%%" % (ends, bk.size, 100.0*ends/max(bk.size,1)))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles")
