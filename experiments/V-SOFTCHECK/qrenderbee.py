"""Focus-ladder probes on bee-1-cpl -- band qualification is SUBJECT-dependent, and bee
carries the headline (+0.0748 dex). Qualifying only 113MSDCF would leave the bigger
claim unqualified.

Probes stop at 200. Measured earlier in this lane: bee probes 0-200 register within
60 px and drift smoothly with bracket index (real focus breathing), while 225/250/275/298
jump to 250-330 px as a block, past the T/2 = 64 px trust limit. A probe that cannot be
registered samples different scene content and cannot be compared to anything.
"""
import drender as D
SUBJ = "bee-1-cpl"; EXPO = "1.50"
if __name__ == "__main__":
    h = D.pin(); print("pin sha256 %s...\n" % h[:16])
    src, allf = D.frames(SUBJ); NF = len(allf)
    assert NF == 299, "expected 299 frames, got %d" % NF
    ks = list(range(0, 201, 10))
    print("%s: %d frames, %d probes at exposure +%s (matches R149x2/R299x1)\n" % (SUBJ, NF, len(ks), EXPO))
    for k in ks: D.probe(SUBJ, k, EXPO)
    print("\ndone: %d probes" % len(ks))
