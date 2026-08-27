"""Commission statistic E AND orch_sharp1to1's statistic on the SAME arms.

orch_sharp1to1.commission() perturbs ONLY the master. All three of its arms
share one source set, so nothing it does can detect a wrong denominator. The
arms below are split into NUMERATOR arms (perturb the master, as it does) and
DENOMINATOR arms (perturb the reference envelope, which it never does), plus
one arm whose physics fixes its score before the number is read.
"""
import sys, numpy as np
from scipy.ndimage import gaussian_filter
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from sharplib import acutance, orig_detail, P

RNG = np.random.default_rng(11)
NP, NF, PAD = 64, 12, 16
READ_NOISE = 12.0


def make_latent(n):
    """1/f texture plus hard edges -- a real subject's spectrum, not white noise.
    orch_sharp1to1 commissions on white noise + a sine, which has no scale
    structure; defocus on white noise is not defocus on a subject."""
    f = np.fft.fftfreq(n)
    r = np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)
    r[0, 0] = 1e-6
    sp = np.fft.fft2(RNG.normal(0, 1, (n, n))) / r
    a = np.real(np.fft.ifft2(sp))
    a = (a - a.mean()) / a.std()
    for _ in range(6):
        y0, x0 = RNG.integers(0, n - 40, 2)
        a[y0:y0 + 40, x0:x0 + 40] += 3.0
    return 9000 + 2200 * a


def build():
    """A focus stack: each patch has its own in-focus frame."""
    S = P + 2 * PAD
    lat, frames, kstar = [], [], []
    for p in range(NP):
        L = make_latent(S)
        ks = RNG.integers(1, NF - 1)
        fr = []
        for k in range(NF):
            sig = 0.30 + 0.42 * abs(k - ks)
            fr.append(gaussian_filter(L, sig, mode="reflect")
                      + RNG.normal(0, READ_NOISE, (S, S)))
        lat.append(L); frames.append(fr); kstar.append(ks)
    return lat, frames, kstar


def c(a):
    return a[PAD:PAD + P, PAD:PAD + P]


def score(masters, refsets, stat):
    g = []
    for p in range(NP):
        m = stat(c(masters[p]))
        s = max(stat(c(f)) for f in refsets[p])
        if s > 0:
            g.append(m / s)
    return float(np.median(g))


def main():
    lat, frames, kstar = build()
    sharpest = [frames[p][kstar[p]] for p in range(NP)]
    full = [frames[p] for p in range(NP)]
    J = 3   # a fixed frame index for the physics arm

    arms = []
    # ---- NUMERATOR arms: what orch_sharp1to1 already does ----
    arms.append(("NUM  null      master IS the reference, set={it}",
                 sharpest, [[frames[p][kstar[p]]] for p in range(NP)], "== 1.0"))
    arms.append(("NUM  amplitude master x2.0 (pure gain)",
                 [2.0 * s for s in sharpest], full, "== baseline"))
    arms.append(("NUM  selection master = per-patch sharpest frame",
                 sharpest, full, "~ 1.0"))
    arms.append(("NUM  defect    master blurred past every frame",
                 [gaussian_filter(s, 2.2, mode="reflect") for s in sharpest],
                 full, "< 1.0"))
    arms.append(("NUM  improve   master = the latent (true reconstruction)",
                 lat, full, "> 1.0"))
    # ---- the arm whose physics fixes its score BEFORE the number is read ----
    arms.append(("PHYS frame %d as master, set contains that frame" % J,
                 [frames[p][J] for p in range(NP)], full, "<= 1.0 exactly"))
    # ---- DENOMINATOR arms: what orch_sharp1to1 never does ----
    arms.append(("DEN  dropbest  per-patch best frame removed from the set",
                 sharpest,
                 [[f for i, f in enumerate(frames[p]) if i != kstar[p]] for p in range(NP)],
                 "> baseline"))
    arms.append(("DEN  subsample every 3rd frame kept (as nsrc=10 of 299 does)",
                 sharpest, [frames[p][::3] for p in range(NP)], "> baseline"))
    arms.append(("DEN  defocus   every reference frame blurred +0.8 px",
                 sharpest,
                 [[gaussian_filter(f, 0.8, mode="reflect") for f in frames[p]] for p in range(NP)],
                 "> baseline"))
    arms.append(("DEN  sharpen   every reference frame unsharp-masked",
                 sharpest,
                 [[f + 0.8 * (f - gaussian_filter(f, 1.0, mode="reflect")) for f in frames[p]]
                  for p in range(NP)], "< baseline"))

    print("%-58s %12s %12s   %s" % ("arm", "E (mine)", "orig detail", "expected"))
    print("-" * 100)
    for label, m, r, exp in arms:
        e = score(m, r, acutance)
        o = score(m, r, orig_detail)
        print("%-58s %12.4f %12.4f   %s" % (label, e, o, exp))


if __name__ == "__main__":
    main()
