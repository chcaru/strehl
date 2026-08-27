"""Which mechanism produces coffee-bubbles' blotch excess? Distinguish, do not weigh.

ORCH asked for three hypotheses to be separated rather than balanced:
  (a) a genuine regression the eye can see,
  (b) the merge charged for structure it resolved that no frame contains,
  (c) an artifact of the blotch statistic on this subject's content.

The 1:1 crop and the spectrum turned that into a mechanical question. blotch's
band is boxblur(lum, 25) - boxblur(lum, 200) and boxblur is a SQUARE kernel
51 px wide, so every small bright point in the image is spread into a 51 px
square of band energy. The master's band step-profile peaks at 49.8 px with a
harmonic at 99.7 px, which is that kernel and not anything in the scene: the
luminance spectrum shows no such pitch in the master or in any frame.

So: is the master's excess carried by FINE structure (points the merge resolved
and no single defocused frame did), or by genuine MID-SCALE structure (real
blotching, a regression)? Suppressing features smaller than k with a
morphological filter before the band separates them, because it removes a
point's energy outright while leaving 50-400 px structure alone.

  (b) predicts the excess collapses toward the frame null as k grows.
  (a) predicts it survives.

The instrument is commissioned by planting BOTH mechanisms and requiring it to
tell them apart -- an arm that certifies discrimination, not merely response.
"""
import argparse
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_bubbles as B  # noqa: E402
import vn_lib as L  # noqa: E402
from orch_blotch import boxblur, LO_R, HI_R  # noqa: E402

KS = (1, 5, 9, 17, 33)
CACHE = os.path.join(B.OUT, "lums.npz")


def despeckle(a, k):
    """Remove features smaller than k, both polarities, keeping larger ones."""
    if k <= 1:
        return a
    o = ndimage.grey_opening(a, size=(k, k))
    return ndimage.grey_closing(o, size=(k, k))


def blotch_of(lum, k):
    d = despeckle(lum, k)
    band = boxblur(d, LO_R // 2) - boxblur(d, HI_R // 2)
    return float(np.std(band)) / max(float(np.mean(d)), 1e-9)


def sweep(mlum, flums, ks=KS):
    """master ratio and the matched leave-one-out frame null, at each k."""
    out = []
    for k in ks:
        m = blotch_of(mlum, k)
        per = np.array([blotch_of(f, k) for f in flums])
        lo = B.loo_min(per[:, None])[:, 0]
        out.append(dict(k=k, master=m, ratio=m / max(per.min(), 1e-12),
                        frm_med=float(np.median(per)),
                        loo_med=float(np.median(per / np.maximum(lo, 1e-12))),
                        loo_max=float(np.max(per / np.maximum(lo, 1e-12))),
                        m_loo=float(np.median(m / np.maximum(lo, 1e-12)))))
    return out


def _fine(rng, shape, n=400, amp=20000.0):
    """Small bright points: what a resolved specular highlight looks like.

    Potency matters and commissioning enforced it. A first version used 260
    points of 900 DN across 3x3, which after a 51x51 box contributes ~3 DN
    each against a ~40 DN band -- the planted arm read 1.0064 against a
    placebo of 1.0124, i.e. below the placebo. An undetectable plant certifies
    nothing, so the arm failed and the plant was made bright and sparse, which
    is also what a specular highlight actually is.
    """
    f = np.zeros(shape, np.float32)
    ys = rng.integers(3, shape[0] - 3, n)
    xs = rng.integers(3, shape[1] - 3, n)
    for y, x in zip(ys, xs):
        f[y:y + 2, x:x + 2] += amp
    return f


def _mid(rng, shape, amp=60.0):
    """Genuine 50-400 px blotching: a real regression, not a resolved point."""
    c = rng.normal(0, 1, (shape[0] // 90 + 2, shape[1] // 90 + 2))
    z = ndimage.zoom(c, (shape[0] / c.shape[0], shape[1] / c.shape[1]), order=1)
    z = z[:shape[0], :shape[1]].astype(np.float32)
    return z / max(float(z.std()), 1e-6) * amp


def commission():
    rng = np.random.default_rng(23)
    master, frames, _ = B.synth(rng, n=10, size=600)
    rows = []

    def show(name, m, fs):
        s = sweep(m, fs)
        r1, rk = s[0]["ratio"], s[-1]["ratio"]
        print("  %-36s %8.4f %8.4f %8.4f  %8.4f"
              % (name, r1, rk, rk / max(r1, 1e-12), s[-1]["loo_med"]))
        return s, r1, rk

    print("COMMISSIONING  mechanism separator, synthetic subject")
    print("  k=1 is the unfiltered statistic; k=%d suppresses features"
          " below %d px." % (KS[-1], KS[-1]))
    print("")
    print("  %-36s %8s %8s %8s  %8s"
          % ("arm", "ratio k1", "ratio k33", "survival", "frm null"))

    _, c1, ck = show("placebo: clean master", master, frames)
    rows.append(("placebo: clean master", "ratio ~1 at every k",
                 abs(c1 - 1) < 0.10 and abs(ck - 1) < 0.10))

    fine = master + _fine(rng, master.shape)
    _, f1, fk = show("fine plant: points on master only", fine, frames)
    rows.append(("fine plant: points on master only", "high at k1",
                 f1 > c1 * 1.25))

    mid = master + _mid(rng, master.shape)
    _, m1, mk = show("mid plant: 50-400px blotch on master", mid, frames)
    rows.append(("mid plant: 50-400px blotch on master", "high at k1",
                 m1 > c1 * 1.25))

    # THE ARM THAT MATTERS. Each plant above only shows the statistic responds.
    # Discrimination is a separate claim and needs its own test: the fine plant
    # must LOSE most of its excess by k=33 and the mid plant must KEEP most of
    # its own. Without this, a filter that simply lowered everything would pass.
    fs_ = (fk - 1) / max(f1 - 1, 1e-9)
    ms_ = (mk - 1) / max(m1 - 1, 1e-9)
    print("")
    print("  DISCRIMINATION  fraction of the excess surviving to k=%d:" % KS[-1])
    print("    fine plant %.3f   mid plant %.3f   separation %.1fx"
          % (fs_, ms_, ms_ / max(fs_, 1e-9)))
    rows.append(("discrimination: fine collapses, mid survives",
                 "mid keeps >4x the fine fraction",
                 fs_ < 0.35 and ms_ > 0.60 and ms_ / max(fs_, 1e-9) > 4.0))

    # DENOMINATOR: put the points on the SOURCES. The reference must be
    # load-bearing: degrading it has to move the reading. Note what this arm
    # must NOT require -- the leave-one-out null is a ratio BETWEEN frames, so
    # raising every frame by a similar factor correctly leaves it unmoved. The
    # first version of this arm demanded the null rise, failed, and the fault
    # was in the requirement rather than the instrument.
    s, _, _ = show("denominator: points on the sources",
                   master, [f + _fine(rng, f.shape) for f in frames])
    base = sweep(master, frames)
    rows.append(("denominator: points on the sources",
                 "frames rise, master ratio falls",
                 s[0]["frm_med"] > base[0]["frm_med"] * 1.15
                 and s[0]["ratio"] < base[0]["ratio"] * 0.9))

    # IMPROVEMENT: the ratio must be able to fall below 1, not only rise.
    sm = boxblur(master, HI_R // 2) + (master - boxblur(master, LO_R // 2))
    _, i1, ik = show("improve: master band removed", sm, frames)
    rows.append(("improve: master band removed", "ratio falls below 1",
                 i1 < 0.85))

    bad = [r for r in rows if not r[2]]
    print("")
    print("%d ok + %d failed = %d arms"
          % (len(rows) - len(bad), len(bad), len(rows)))
    for r in bad:
        print("  NOT COMMISSIONED: %s (required %s)" % (r[0], r[1]))
    return 0 if not bad else 1


def load():
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        return z["m"], [z["f%d" % i] for i in range(int(z["n"]))]
    mwin, flums, _, _, _, _ = B.gather()
    np.savez(CACHE, m=mwin, n=len(flums),
             **{"f%d" % i: f for i, f in enumerate(flums)})
    return mwin, flums


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args(argv)
    if a.commission:
        return commission()

    mlum, flums = load()
    s = sweep(mlum, flums)
    print("")
    print("MECHANISM SWEEP  coffee-bubbles, all 19 sources, whole 900px window")
    print("  %5s %10s %10s %10s %10s" % ("k px", "master", "ratio", "frm null",
                                         "excess"))
    for r in s:
        print("  %5d %10.6f %9.4fx %9.4fx %9.4fx"
              % (r["k"], r["master"], r["ratio"], r["loo_med"],
                 r["ratio"] / max(r["loo_med"], 1e-12)))
    e1 = s[0]["ratio"] / s[0]["loo_med"] - 1
    ek = s[-1]["ratio"] / s[-1]["loo_med"] - 1
    print("")
    print("  excess over the matched frame null: %.1f%% at k=1 -> %.1f%% at"
          " k=%d" % (100 * e1, 100 * ek, KS[-1]))
    print("  fraction of the excess surviving fine-structure removal: %.3f"
          % (ek / max(e1, 1e-9)))
    print("  commissioned separation: a planted FINE mechanism survives at")
    print("  <0.35, a planted MID-SCALE mechanism at >0.60.")
    L.jdump(dict(sweep=s, surv=float(ek / max(e1, 1e-9))),
            os.path.join(B.OUT, "mechanism.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
