"""Why did max-over-63 / max-over-32 read EXACTLY 1.0000 at every band?

Either my even-index subset was wrong, or the MEDIAN is masking the order
statistic.  With 63 frames and the even indices taken, 32 of the 63 possible
argmax positions survive in the subset, so P(the site's max is retained) =
32/63 = 0.508 > 0.5.  Just over half of all sites therefore have ratio exactly
1.0, which puts the MEDIAN at exactly 1.0 no matter how large the inflation is
on the other 49%.  If that is the cause, a simulation with no image data at all
must reproduce a median of exactly 1.0 while the MEAN sits above 1.
"""
import numpy as np
r=np.random.default_rng(5)
for dist,draw in [("gaussian",lambda s: r.standard_normal(s)),
                  ("exponential (power-like)",lambda s: r.exponential(1.0,s))]:
    x=np.abs(draw((200000,63)))
    m63=x.max(1); m32=x[:,0::2].max(1)
    rat=m63/m32
    print(f"  {dist:26s} median {np.median(rat):.4f}   mean {rat.mean():.4f}   "
          f"frac exactly 1.0 {np.mean(rat==1.0):.4f}   p95 {np.percentile(rat,95):.4f}")
print(f"\n  even indices retained out of 63 : {len(range(0,63,2))}  -> P(argmax kept) = {32/63:.4f}")
print("  A median of exactly 1.0000 is therefore the PREDICTED reading, not a bug.")
print("  The order statistic is real but lives in the upper half of the distribution,")
print("  so the mean and p95 are where it must be read.  This does not affect the")
print("  common-denominator comparison, whose denominator is identical in both arms.")
