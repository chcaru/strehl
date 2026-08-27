"""S2: gain-invariant AND noise-corrected -- and a second, realistic target.

WHERE 01-04 LEFT IT

  S0 (shipped)  10 arms failed. Exactly linear in master gain (x1.85 -> 1.854),
                perverse to noise (N(0,1500) -> 3.4855, reproducing the
                published "perfect" ceiling to 0.03%) and to ringing.
  S1 (f/c)       6 arms failed. Fixes ALL FIVE photometric arms exactly
                (1.0000 on every gain, offset and contrast transform) but its
                blur response collapses to 0.9636 at k=8 where S0 read 0.1717.
                Gain-invariance bought at the cost of near-blindness to the
                one thing the instrument exists to measure. Not a repair.

TWO DEFECTS REMAIN AND THEY HAVE DIFFERENT CAUSES

1. NOISE. `mean|grad|` cannot separate signal gradient from noise gradient
   because absolute values do not add. Squared gradients DO:

       E[(grad(s+n))^2] = E[(grad s)^2] + E[(grad n)^2]      (n independent,
                                                              zero mean)

   exactly, with no cross term. So an ENERGY statistic admits an exact noise
   subtraction that a magnitude statistic does not. This is not a tuning
   choice; it is the reason to prefer energy here.

   sigma is estimated per patch by Immerkaer's 3x3 mask

       [[ 1 -2  1]
        [-2  4 -2]
        [ 1 -2  1]]

   which is orthogonal to any locally-linear signal, so it reads noise and not
   structure. It is a published estimator, not one invented for this file.

2. WHITE-NOISE TEST TARGET. The commission's latent is
   `rng.normal(8000, 1500) + 4000*sin(x/3)` -- i.e. WHITE NOISE plus one
   sinusoid. White noise has a FLAT spectrum with maximum energy at Nyquist,
   which is the pathological input for a gradient statistic and is nothing
   like a photograph (natural images fall off roughly as 1/f). A statistic
   commissioned only on white noise is commissioned on the one signal whose
   band structure it will never meet in the field, and S1's collapse at k=8
   is a symptom of exactly that: on a flat spectrum the band RATIO barely
   moves under blur.

   So every candidate is run against BOTH targets and must pass both. A
   candidate that passes on white noise and fails on a natural-spectrum target
   is not commissioned, and the disagreement is reported rather than averaged.

VERDICT RULES are unchanged from script 04: DEGRADE must fall, NEUTRAL must
hold, IMPROVE must rise and be monotonic. All three kinds, because a battery
of degradations alone cannot tell blind from perverse.
"""
import numpy as np

CROP = 560
PATCH = 70
PATCH_FLOOR = 50.0
IMM = np.array([[1., -2., 1.], [-2., 4., -2.], [1., -2., 1.]])


def conv3(a, k):
    out = np.zeros((a.shape[0] - 2, a.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            out += k[i, j] * a[i:i + a.shape[0] - 2, j:j + a.shape[1] - 2]
    return out


def sigma_immerkaer(y):
    """Robust per-patch noise sigma. Orthogonal to locally-linear signal."""
    if y.shape[0] < 3 or y.shape[1] < 3:
        return 0.0
    r = conv3(y, IMM)
    return float(np.sqrt(np.pi / 2.0) * np.mean(np.abs(r)) / 6.0)


def bands_energy(y):
    """(fine energy, coarse energy) as MEAN SQUARED differences.

    coarse is built on the 2x2 BOX MEAN (not the sum), so that under
    y -> a*y both bands scale by a^2 and their ratio is gain-invariant.
    """
    dx = np.diff(y, axis=1)[:-1, :]
    dy = np.diff(y, axis=0)[:, :-1]
    f = float(np.mean(dx * dx + dy * dy))
    k = 0.25 * (y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2])
    cx = np.diff(k, axis=1)[:-1, :]
    cy = np.diff(k, axis=0)[:, :-1]
    c = float(np.mean(cx * cx + cy * cy))
    return f, c


def bands_abs(y):
    f = np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])
    k = y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2]
    c = np.abs(np.diff(k, axis=1)[:-1, :]) + np.abs(np.diff(k, axis=0)[:, :-1])
    return float(np.mean(f)), float(np.mean(c) / 4.0)


def S0(y):
    return bands_abs(y)[0]


def S1(y):
    f, c = bands_abs(y)
    return f / c if c > 0 else float("nan")


def S2(y):
    """Gain-invariant AND noise-corrected.

    Noise bookkeeping, for independent N(0, s^2) per pixel:
      fine   : each first difference has variance 2s^2; two axes -> 4s^2
      coarse : the 2x2 MEAN has variance s^2/4; difference 2*(s^2/4)=s^2/2;
               two axes -> s^2
    Both are subtracted before the ratio is taken. Clamped at zero, and a
    patch whose signal energy does not survive the subtraction returns NaN
    rather than a small positive number, so it is COUNTED as unmeasurable
    instead of silently contributing a meaningless ratio.
    """
    s = sigma_immerkaer(y)
    f, c = bands_energy(y)
    fs = f - 4.0 * s * s
    cs = c - 1.0 * s * s
    if cs <= 0 or fs <= 0:
        return float("nan")
    return float(np.sqrt(fs / cs))


def blur(a, k):
    if k <= 1:
        return a.copy()
    c = np.cumsum(np.pad(a, ((0, 0), (k, k)), mode="edge"), axis=1)
    h = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    c = np.cumsum(np.pad(h, ((k, k), (0, 0)), mode="edge"), axis=0)
    return (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)


def usm(a, amount, k=3):
    return a + amount * (a - blur(a, k))


def target_white(seed=7):
    """The commission's own latent: white noise + a sinusoid."""
    rng = np.random.default_rng(seed)
    lat = rng.normal(8000, 1500, (CROP, CROP))
    return np.clip(lat + 4000 * np.sin(np.arange(CROP) / 3.0)[None, :], 0, 65535)


def target_natural(seed=11):
    """A 1/f-spectrum target with edges: a far better model of a photograph.

    Built by shaping white noise in the Fourier domain to a 1/f amplitude
    falloff, then adding hard-edged bars and discs so there is genuine
    structure at several scales rather than only texture.
    """
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (CROP, CROP))
    fy = np.fft.fftfreq(CROP)[:, None]
    fx = np.fft.fftfreq(CROP)[None, :]
    r = np.sqrt(fy * fy + fx * fx)
    r[0, 0] = 1.0 / CROP
    shaped = np.real(np.fft.ifft2(np.fft.fft2(n) / r))
    shaped = shaped / shaped.std()
    img = 24000 + 6000 * shaped
    yy, xx = np.mgrid[0:CROP, 0:CROP]
    for i in range(6):
        cy, cx = rng.integers(80, CROP - 80, 2)
        rad = rng.integers(18, 46)
        img[(yy - cy) ** 2 + (xx - cx) ** 2 < rad * rad] += 14000
    for i in range(5):
        x0 = int(rng.integers(40, CROP - 90))
        img[:, x0:x0 + rng.integers(4, 11)] -= 11000
    return np.clip(img, 0, 65535)


def ratio_of(stat, ref, srcs, patch=PATCH):
    n = ref.shape[0] // patch
    out, unmeas = [], 0
    for py in range(n):
        for px in range(n):
            sl = (slice(py * patch, (py + 1) * patch),
                  slice(px * patch, (px + 1) * patch))
            if bands_abs(ref[sl])[0] < PATCH_FLOOR and \
               max(bands_abs(c[sl])[0] for c in srcs) < PATCH_FLOOR:
                continue
            m = stat(ref[sl])
            cand = [stat(c[sl]) for c in srcs]
            cand = [v for v in cand if np.isfinite(v)]
            if not np.isfinite(m) or not cand or max(cand) <= 0:
                unmeas += 1
                continue
            out.append(m / max(cand))
    a = np.array(out)
    a = a[np.isfinite(a)]
    return (float(np.median(a)) if a.size else float("nan")), unmeas


def battery(stat, name, target, tname):
    lat = target()
    srcs = [blur(lat, k) for k in (2, 3, 4, 5)]
    sharp = blur(lat, 2)
    rng = np.random.default_rng(3)

    base, _ = ratio_of(stat, sharp, srcs)
    perfect, _ = ratio_of(stat, lat, srcs)
    print("-" * 96)
    print("%s   on target: %s" % (name, tname))
    print("  SELECTION anchor %.4f   RECONSTRUCT(perfect) %.4f" % (base, perfect))

    arms = []
    arms.append(("DEGRADE", "blur master k=8", ratio_of(stat, blur(lat, 8), srcs)[0]))
    arms.append(("DEGRADE", "blur master k=3", ratio_of(stat, blur(lat, 3), srcs)[0]))
    for sd in (200, 600, 1500):
        arms.append(("DEGRADE", "master + N(0,%d)" % sd,
                     ratio_of(stat, sharp + rng.normal(0, sd, (CROP, CROP)), srcs)[0]))
    for amt in (0.5, 1.5, 3.0):
        arms.append(("DEGRADE", "master USM x%.1f" % amt,
                     ratio_of(stat, usm(sharp, amt), srcs)[0]))
    for g in (1.20, 1.50, 1.854):
        arms.append(("NEUTRAL", "master x%.3f gain" % g,
                     ratio_of(stat, g * sharp, srcs)[0]))
    arms.append(("NEUTRAL", "master +3000 offset",
                 ratio_of(stat, sharp + 3000.0, srcs)[0]))
    arms.append(("NEUTRAL", "contrast x1.3 about mean",
                 ratio_of(stat, (sharp - sharp.mean()) * 1.3 + sharp.mean(), srcs)[0]))
    arms.append(("IMPROVE", "half-deblurred t=0.50",
                 ratio_of(stat, 0.5 * sharp + 0.5 * lat, srcs)[0]))

    nbad = 0
    for kind, label, val in arms:
        if not np.isfinite(val) or not np.isfinite(base) or base == 0:
            good, v = False, "UNMEASURABLE"
        elif kind == "DEGRADE":
            good = val < base * 0.98
            v = "PASS" if good else "PERVERSE %.3fx" % (val / base)
        elif kind == "NEUTRAL":
            good = abs(val - base) / base < 0.02
            v = "PASS" if good else "INFLATED %.3fx" % (val / base)
        else:
            good = base * 1.02 < val
            v = "PASS" if good else "FAIL"
        nbad += 0 if good else 1
        print("    %-8s %-26s %10.4f  %s" % (kind, label, val, v))

    prev, mono = None, True
    seq = []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        r, _ = ratio_of(stat, (1 - t) * sharp + t * lat, srcs)
        seq.append(r)
        if prev is not None and not (np.isfinite(r) and r > prev):
            mono = False
        prev = r
    print("    IMPROVE  sweep t=0..1            %s  %s"
          % (" ".join("%.3f" % v for v in seq), "monotonic PASS" if mono else "NOT MONOTONIC"))
    if not mono:
        nbad += 1
    print("    -> %d arm(s) failed   %s"
          % (nbad, "COMMISSIONED" if nbad == 0 else "NOT COMMISSIONED"))
    return nbad


def main():
    print("=" * 96)
    print("THREE CANDIDATES x TWO TARGETS. A candidate must pass BOTH targets.")
    print("=" * 96)
    tot = {}
    for stat, name in ((S0, "S0 fine-only (SHIPPED)"),
                       (S1, "S1 fine/coarse"),
                       (S2, "S2 energy, gain-inv + noise-corrected")):
        a = battery(stat, name, target_white, "white noise + sinusoid (the commission's own)")
        b = battery(stat, name, target_natural, "1/f spectrum + edges (photograph-like)")
        tot[name] = (a, b)
        print()
    print("=" * 96)
    print("%-42s %14s %16s" % ("candidate", "white target", "natural target"))
    print("-" * 96)
    for k, (a, b) in tot.items():
        print("%-42s %10d fail %12d fail" % (k, a, b))
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
