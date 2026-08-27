"""Commission statistic F on REAL data, numerator arms AND denominator arms,
including one arm whose physics fixes its score before the number is read.
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB, sharp_F as SF

def line(tag, r, exp):
    s = SF.summarise(r)
    if s is None:
        print("%-52s %10s %8s   %s" % (tag, "REFUSED", "-", exp)); return None
    print("%-52s %10.4f %8d   %s" % (tag, s[0], s[3], exp)); return s[0]

def main(subj):
    z = SB.build(subj)
    nf = z["A"].shape[0]
    print("########## %s  (%d frames) ##########" % (subj, nf))
    print("%-52s %10s %8s   %s" % ("arm", "F median", "sites", "expected"))
    print("-" * 92)
    base = SF.evaluate(z); b = line("BASELINE  master vs per-patch best frame", base, "")
    print()
    j = nf // 2
    one = np.arange(nf) == j
    line("NULL      numerator = frame %d, set = {frame %d}" % (j, j),
         SF.evaluate(z, numer=0, refidx=one), "== 1.0000 exactly")
    line("AMPLITUDE master x 2.0 (pure gain, nothing sharper)",
         SF.evaluate(z, mgain=2.0), "== BASELINE exactly")
    for jj in (nf//4, nf//2, 3*nf//4):
        line("PHYSICS   numerator = frame %d, set CONTAINS it" % jj,
             SF.evaluate(z, numer=jj), "<= 1.0000 by construction")
    print()
    line("NUM       master blurred  sigma 0.8", SF.evaluate(z, mblur=0.8), "< BASELINE")
    line("NUM       master sharpened (unsharp 0.8)", SF.evaluate(z, msharp=0.8), "> BASELINE")
    print()
    line("DEN       best frame removed from the set", SF.evaluate(z, dropbest=True), "> BASELINE")
    for k in (2, 3, 6):
        line("DEN       keep 1 reference frame in %d" % k,
             SF.evaluate(z, refkeep=k), "> BASELINE")
    line("DEN       every reference frame blurred 0.8", SF.evaluate(z, refblur=0.8), "> BASELINE")
    line("DEN       every reference frame sharpened", SF.evaluate(z, refsharp=0.8), "< BASELINE")
    print("\n--- denominator selection: which frame does the envelope pick? ---")
    bk = base["bestk"][base["ok"]]
    h = np.bincount(bk, minlength=nf)
    print("  " + " ".join("%d:%d" % (i, v) for i, v in enumerate(h) if v))
    ends = int(((bk <= 1) | (bk >= nf - 2)).sum())
    print("  stack-end picks: %d/%d = %.1f%%" % (ends, bk.size, 100.0*ends/max(bk.size,1)))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles")
