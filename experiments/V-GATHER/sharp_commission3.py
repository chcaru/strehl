"""Bracket the regime. The improvement plant in sharp_commission2 saturated at
1.018x because the sharpest frame was already sigma=0.30 -- there was nothing
left to recover. That is the SAME defect this lane is auditing in
orch_sharp1to1's RECONSTRUCT arm, so it is fixed here rather than excused:
the stack is rebuilt with a real best-focus blur so the plant has headroom.
"""
import sys, numpy as np
from scipy.ndimage import gaussian_filter
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from sharplib import acutance, orig_detail, P
import sharp_commission as SC

RNG = np.random.default_rng(23)
S0 = 1.00     # best-focus blur: the frames are genuinely soft, so reconstruction
              # has something to reconstruct


def build(nf=12, npatch=48, s0=S0, step=0.42, noise=12.0):
    Sz = P + 2 * SC.PAD
    lat, frames, kstar = [], [], []
    for p in range(npatch):
        L = SC.make_latent(Sz)
        ks = int(RNG.integers(1, nf - 1))
        fr = [gaussian_filter(L, s0 + step * abs(k - ks), mode="reflect")
              + RNG.normal(0, noise, (Sz, Sz)) for k in range(nf)]
        lat.append(L); frames.append(fr); kstar.append(ks)
    return lat, frames, kstar


def main():
    lat, frames, kstar = build()
    npatch = len(lat)
    sharpest = [frames[p][kstar[p]] for p in range(npatch)]
    full = [frames[p] for p in range(npatch)]
    SC.NP = npatch
    print("best-focus blur sigma = %.2f, so the best frame is genuinely soft\n" % S0)
    print("=== GRADED IMPROVEMENT: master = latent blurred by sigma ===")
    print("sigma=%.2f IS the sharpest frame (expect 1.0); sigma=0 is perfect recovery" % S0)
    print("%10s %14s %14s" % ("sigma", "E", "orig"))
    for sg in (1.00, 0.85, 0.70, 0.55, 0.40, 0.25, 0.0):
        m = [gaussian_filter(L, sg, mode="reflect") if sg > 0 else L for L in lat]
        print("%10.2f %14.4f %14.4f" % (sg, SC.score(m, full, acutance),
                                        SC.score(m, full, orig_detail)))
    print("\n=== PHYSICS-FIXED ARM (tight): master = frame j, set CONTAINS frame j ===")
    print("the master is a MEMBER of the set the max is taken over, so the true")
    print("answer is <= 1.0000 for every j by construction. Any excess is bias.")
    print("%10s %14s %14s" % ("j", "E", "orig"))
    for j in (0, 3, 6, 9, 11):
        m = [frames[p][j] for p in range(npatch)]
        print("%10d %14.4f %14.4f" % (j, SC.score(m, full, acutance),
                                      SC.score(m, full, orig_detail)))
    print("\n=== DENOMINATOR SUBSAMPLE (master unchanged) ===")
    print("%10s %8s %14s %14s" % ("keep 1 in", "n", "E", "orig"))
    for st in (1, 2, 3, 4, 6, 12):
        r = [frames[p][::st] for p in range(npatch)]
        print("%10d %8d %14.4f %14.4f" % (st, len(r[0]),
              SC.score(sharpest, r, acutance), SC.score(sharpest, r, orig_detail)))


if __name__ == "__main__":
    main()
