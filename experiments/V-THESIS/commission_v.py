"""Commission the V-THESIS instrument BEFORE it is allowed to vote.

Every check below is a plant with a known answer. Two of them are designed so
that a broken instrument produces an obviously wrong number rather than a
plausible one:

  C3  two samplings of the SAME band-limited scene at 800 and 744 px. There is
      no blur difference at all, only the magnification `stack`'s coverage
      rescale introduces. A scene-referred instrument must return 0.000. A
      per-pixel instrument must return the magnification. If the per-pixel
      control does NOT move, the confound is not expressible here and C3 proves
      nothing -- so it is printed too.

  C5  pure noise, at the real per-subject sigma ratios, with no blur. Must
      return 0. Run twice, with and without the noise-floor subtraction, so
      that the null is shown to be EARNED by that step rather than assumed.
"""
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, zoom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from vstat import va_blur_px, vb_f50_scene, sigma_immerkaer, radial_power  # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
RNG = np.random.default_rng(90210)


def green_tile(subject, y, x, n):
    img = tifffile.imread(str(R / subject / "merge.tif"))
    return img[y:y + n, x:x + n, 1].astype(np.float64)


def naive_f50_cycpx(t):
    """Deliberately per-pixel: half-energy frequency in cycles per PIXEL.

    This is the control. It is what a scale-blind instrument reports, and it is
    the family BUILD-THESIS's S2 belongs to.
    """
    T = min(t.shape)
    return vb_f50_scene(t) / T


def synth_pair(Tm, Ta, K=240, alpha=2.5, sigma_px=0.0, seed=7):
    """Two samplings of ONE band-limited scene, at Tm and Ta pixels per span.

    Identical scene-referred Fourier coefficients, so the only difference
    between the two arrays is sampling density. sigma_px is a planted Gaussian
    blur expressed in MERGE pixels and applied in SCENE units to BOTH, then...
    no: applied to the Ta arm only, so the answer is a known -sigma_px
    (argmax blurrier => positive, merge finer).
    """
    rng = np.random.default_rng(seed)
    kys = np.arange(-K, K + 1)
    coef = {}
    for ky in kys:
        for kx in range(0, K + 1):
            if kx == 0 and ky <= 0:
                continue
            k = np.hypot(ky, kx)
            if k > K or k < 1:
                continue
            amp = k ** (-alpha / 2.0)
            coef[(ky, kx)] = amp * (rng.normal() + 1j * rng.normal())

    def build(N, blur_px):
        Z = np.zeros((N, N), dtype=np.complex128)
        sig_s = blur_px / float(Tm)                 # scene units
        for (ky, kx), v in coef.items():
            k = np.hypot(ky, kx)
            mtf = np.exp(-2.0 * np.pi ** 2 * sig_s ** 2 * k ** 2)
            Z[ky % N, kx % N] = v * mtf
            Z[(-ky) % N, (-kx) % N] = np.conj(v * mtf)
        return np.fft.ifft2(Z).real * (N * N)

    return build(Tm, 0.0), build(Ta, sigma_px)


def main():
    print("=" * 78)
    print("V-THESIS INSTRUMENT COMMISSIONING")
    print("=" * 78)

    t = green_tile("leaf-2-cpl", 900, 1400, 800)
    print(f"\nreal tile: leaf-2-cpl merge [900:1700, 1400:2200]  "
          f"mean {t.mean():.1f} DN  sigma_immerkaer {sigma_immerkaer(t):.2f} DN")

    print("\nC1 IDENTITY (must be exactly 0.000)")
    print(f"   VA(t, t) = {va_blur_px(t, t):+.4f} px")

    print("\nC2 PLANTED BLUR, SAME SAMPLING (must recover the plant)")
    print(f"   {'planted':>9}{'VA recovered':>15}{'error':>10}")
    for s in (0.10, 0.20, 0.30, 0.50, 0.80, 1.20, 2.00):
        got = va_blur_px(t, gaussian_filter(t, s))
        print(f"   {s:>9.2f}{got:>15.3f}{got - s:>+10.3f}")

    print("\nC2b SIGN TEST: the merge arm made blurrier (must go NEGATIVE)")
    for s in (0.30, 0.80):
        got = va_blur_px(gaussian_filter(t, s), t)
        print(f"   merge blurred {s:.2f} px -> VA {got:+.3f} px")

    print("\nC3 PURE SCALE, NO BLUR -- the false-negative confound")
    print("   two samplings of ONE band-limited scene; correct answer is 0.000")
    print(f"   {'Tm':>5}{'Ta':>5}{'s':>8}{'VA (scene-ref)':>17}"
          f"{'naive cyc/px ratio':>21}{'expected naive':>16}")
    for s in (0.9236, 0.9321, 0.9707):
        Ta = int(round(800 * s))
        m, a = synth_pair(800, Ta, sigma_px=0.0)
        va = va_blur_px(m, a, denoise=False)
        naive = naive_f50_cycpx(m) / naive_f50_cycpx(a)
        print(f"   {800:>5}{Ta:>5}{s:>8.4f}{va:>17.3f}{naive:>21.4f}{s:>16.4f}")

    print("\nC4 PLANTED BLUR ACROSS A SCALE MISMATCH (must still recover)")
    print(f"   {'s':>8}{'planted':>9}{'VA recovered':>15}{'error':>10}")
    for s in (0.9236, 0.9707):
        Ta = int(round(800 * s))
        for sig in (0.30, 0.60, 1.00):
            m, a = synth_pair(800, Ta, sigma_px=sig)
            got = va_blur_px(m, a, denoise=False)
            print(f"   {s:>8.4f}{sig:>9.2f}{got:>15.3f}{got - sig:>+10.3f}")

    print("\nC5 NOISE NULL at the REAL per-subject sigma ratios (must be 0.000)")
    print("   'no floor sub' is the same statistic with the noise-floor")
    print("   subtraction disabled -- it shows the null is earned, not assumed.")
    s0 = sigma_immerkaer(t)
    print(f"   {'sigma ratio':>12}{'VA':>10}{'VA no floor sub':>18}")
    for r in (1.064, 1.078, 1.110, 1.381, 1.625, 2.681):
        add = float(np.sqrt(max((r * s0) ** 2 - s0 ** 2, 0.0)))
        tn = t + RNG.normal(0.0, add, t.shape)
        print(f"   {r:>12.3f}{va_blur_px(t, tn):>10.3f}"
              f"{va_blur_px(t, tn, denoise=False):>18.3f}")

    print("\nC5b IMPULSE NULL (0.05% salt-and-pepper, argmax's measured speckle rate)")
    tn = t.copy()
    n = tn.size
    idx = RNG.choice(n, int(0.0005 * n), replace=False)
    flat = tn.ravel()
    flat[idx] = np.where(RNG.random(idx.size) < 0.5, flat.min(), flat.max())
    print(f"   VA(t, t+impulses) = {va_blur_px(t, tn):+.3f} px")

    print("\nC6 REAL-DATA RESAMPLING FLOOR (known non-zero, reported not hidden)")
    print("   a real merge tile vs itself area-downsampled to Ta: the box filter")
    print("   is a real blur, so a NON-zero answer here is correct.")
    for s in (0.9236, 0.9707):
        Ta = int(round(800 * s))
        a = zoom(t, Ta / 800.0, order=1, prefilter=False)
        print(f"   s={s:.4f}  Ta={Ta}  VA = {va_blur_px(t, a):+.3f} px")

    print("\nC7 DETECTION FLOOR: smallest plant VA reports as nonzero")
    for s in (0.02, 0.05, 0.10, 0.15, 0.25):
        got = va_blur_px(t, gaussian_filter(t, s))
        print(f"   planted {s:.2f} -> {got:+.4f}")


if __name__ == "__main__":
    main()
