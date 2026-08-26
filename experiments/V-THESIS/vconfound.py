"""Is the across-rescale blindness in THEIR chain, or in my control's resampler?

Their chain read a planted 0.8 px blur as S2_f50 1.052x across a 6.6% rescale.
Two possible causes, and they have opposite consequences:

  (a) my synthetic arm was built with cv2 INTER_LANCZOS4, which does NOT
      prefilter when shrinking, so it ALIASES: high-frequency energy folds back
      and makes the synthetic arm look sharper than it is. Then the blindness is
      MY artifact and says nothing about their headline.

  (b) their tile-comparison chain loses the blur across the rescale. Then their
      headline null is partly manufactured and the confound is real.

Discriminator: my own instrument is scale-immune by construction (bin index =
cycles across tile) and translation-invariant. Run it on the SAME synthetic
pairs. If mine also reads ~0, the loss is in the data (a). If mine reads 0.8,
the loss is in their chain (b).

Also builds a second control set rescaled by an exact band-limited Fourier
resample, which cannot alias, and reads both.
"""
import json, pathlib, sys
import numpy as np, tifffile, cv2

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import va_blur_px          # noqa: E402
from vplant import gauss_exact        # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
GREEN = 1
TILE = 512


def fourier_scale(a, s):
    """Exact band-limited rescale about the centre: crop the spectrum, no alias."""
    h, w = a.shape
    F = np.fft.fftshift(np.fft.fft2(a))
    nh, nw = int(round(h * s)), int(round(w * s))
    y0, x0 = (h - nh) // 2, (w - nw) // 2
    C = F[y0:y0 + nh, x0:x0 + nw]
    small = np.real(np.fft.ifft2(np.fft.ifftshift(C))) * (nh * nw) / (h * w)
    out = np.full((h, w), float(np.median(a)))
    oy, ox = (h - nh) // 2, (w - nw) // 2
    out[oy:oy + nh, ox:ox + nw] = small
    return out


def sites(m, a, s, n=6):
    """Matched sites: merge tile at p, synthetic-arm tile at s*p + c(1-s)."""
    h, w = m.shape
    cy, cx = h / 2.0, w / 2.0
    out = []
    step = (min(h, w) - 2 * TILE) // 3
    for gy in range(TILE, h - TILE, max(step, TILE)):
        for gx in range(TILE, w - TILE, max(step, TILE)):
            tm = m[gy:gy + TILE, gx:gx + TILE]
            if tm.shape != (TILE, TILE) or tm.std() < 30:
                continue
            ax, ay = s * gx + cx * (1 - s), s * gy + cy * (1 - s)
            Ta = int(round(TILE * s))
            ax, ay = int(round(ax)), int(round(ay))
            ta = a[ay:ay + Ta, ax:ax + Ta]
            if ta.shape != (Ta, Ta):
                continue
            out.append((tm, ta))
            if len(out) >= n:
                return out
    return out


rows = []
for kind, maker in (("lanczos", None), ("fourier", fourier_scale)):
    for sigma in (0.0, 0.4, 0.8):
        if maker is None:
            d = R / f"VCTRL-s-blur{sigma:.1f}"
            m = tifffile.imread(str(d / "merge.tif"))[:, :, GREEN].astype(np.float64)
            a = tifffile.imread(str(d / "argmax.tif"))[:, :, GREEN].astype(np.float64)
        else:
            m = tifffile.imread(str(R / "leaf-2-cpl" / "merge.tif"))[:, :, GREEN].astype(np.float64)
            src = gauss_exact(m, sigma) if sigma > 0 else m
            a = maker(src, 0.9342)
        vs = [va_blur_px(tm, ta, denoise=False) for tm, ta in sites(m, a, 0.9342)]
        vs = [v for v in vs if v is not None and np.isfinite(v)]
        rows.append((kind, sigma, len(vs), float(np.median(vs)) if vs else float("nan")))
        print(f"{kind:<8} planted {sigma:.1f} px  ->  V reads {rows[-1][3]:+.3f} px   (n={len(vs)})")

print("\n(positive = merge finer, i.e. the plant recovered)")
pathlib.Path(r"C:\dev\strehl-out\V-THESIS\confound.json").write_text(
    json.dumps(rows, indent=1), encoding="utf8")
