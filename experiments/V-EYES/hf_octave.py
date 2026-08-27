"""Does the delivered master carry information above 0.5 Nyquist?

Motivation. The render's own provenance says the focus decision is made at
"3516 x 2344 per CFA plane", one decision per 2x2 quad, and warns "Interpolated
-- do not measure resolution on it." It also reports a "coverage" rescale that
upsamples the field by 1/coverage. Both mean the delivered 7032 x 4688 grid may
be carrying detail that was only ever sampled at half that pitch. If so, the
"33 MP, 23.4 x 15.6 inches at 300 DPI" claim on the deliverable is a claim about
pixels, not about detail, and a 1:1 viewer or an A3 print will see mush.

The measurement. Fraction of total spectral power lying in the top octave, 0.5
to 1.0 Nyquist, of the tile's own grid. Hann-windowed to stop the tile edge
from contributing a sinc. Call it HF.

Commissioning, per AGENTS.md: a metric is worthless until it has been shown to
read a planted defect the wrong way and a planted improvement the right way.
Both arms are built in, on the same tile, so the reader can check them:

  DEFECT  (must lower HF): master downsampled 2x by area and re-upsampled by
          Lanczos. This is an exact model of "decided at half pitch, then
          interpolated". If the master's HF equals this control's HF, the
          master contains no more information than a 2x upsample does.
  IMPROVE (must raise HF): master unsharp-masked. Adds real high-frequency
          energy, so a metric that is merely blind or perverse will fail here
          even if it passes the defect arm.

  REFERENCE: a single source frame demosaiced by rawpy (a different demosaicer
          than the tool's, so absolute sharpness is not comparable) at full
          sensor resolution. It is here to show what HF a genuinely full-pitch
          sampling of this same scene looks like -- it establishes that the
          top octave is reachable at all on this subject and optic, which a
          diffraction-limited system might not manage.

Usage: python hf_octave.py <master.tiff> <x> <y> <size> [ref.ARW ...]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2


def hf_fraction(tile, lo=0.5, hi=1.0):
    a = tile.astype(np.float64)
    a = a - a.mean()
    n = min(a.shape)
    a = a[:n, :n]
    w = np.hanning(n)
    a = a * w[:, None] * w[None, :]
    f = np.fft.fftshift(np.abs(np.fft.fft2(a)) ** 2)
    c = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.sqrt((yy - c) ** 2 + (xx - c) ** 2) / float(c)  # 1.0 == Nyquist
    inside = r <= 1.0
    band = inside & (r >= lo) & (r < hi)
    tot = f[inside].sum()
    return float(f[band].sum() / tot) if tot > 0 else 0.0


def report(name, tile):
    print(f"  {name:<44} HF(0.5-1.0 Nyq) = {hf_fraction(tile) * 100:>7.3f}%")
    return hf_fraction(tile)


def main():
    mpath = sys.argv[1]
    x, y, size = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    refs = sys.argv[5:]

    m = tifffile.imread(mpath)
    g = m[y : y + size, x : x + size, 1].astype(np.float64)
    print(f"{pathlib.Path(mpath).name}  tile ({x},{y}) {size}x{size}  green channel")
    print()
    print("  MEASURED")
    hf_m = report("master as delivered", g)

    print()
    print("  COMMISSIONING -- planted defect, HF must FALL")
    small = cv2.resize(g, (size // 2, size // 2), interpolation=cv2.INTER_AREA)
    up = cv2.resize(small, (size, size), interpolation=cv2.INTER_LANCZOS4)
    hf_d = report("master -> 2x down -> 2x up (half-pitch model)", up)

    print()
    print("  COMMISSIONING -- planted improvement, HF must RISE")
    blur = cv2.GaussianBlur(g, (0, 0), 1.2)
    sharp = np.clip(g + 1.0 * (g - blur), 0, 65535)
    hf_i = report("master + unsharp mask (amount 1.0, sigma 1.2)", sharp)

    ok_d = hf_d < hf_m
    ok_i = hf_i > hf_m
    print()
    print(f"  defect arm  {'PASS' if ok_d else 'FAIL'}: "
          f"{hf_d * 100:.3f}% {'<' if ok_d else '>='} {hf_m * 100:.3f}%")
    print(f"  improve arm {'PASS' if ok_i else 'FAIL'}: "
          f"{hf_i * 100:.3f}% {'>' if ok_i else '<='} {hf_m * 100:.3f}%")
    print(f"  master / half-pitch-model ratio = {hf_m / hf_d if hf_d else float('nan'):.3f}"
          "   (1.00 means the master carries no more detail than a 2x upsample)")

    if refs:
        import rawpy

        print()
        print("  REFERENCE -- genuine full-pitch sampling of the same scene")
        for r in refs:
            with rawpy.imread(r) as raw:
                rgb = raw.postprocess(
                    output_bps=16, no_auto_bright=True, use_camera_wb=True
                )
            t = rgb[y : y + size, x : x + size, 1].astype(np.float64)
            report(f"{pathlib.Path(r).name} (rawpy demosaic, full res)", t)


if __name__ == "__main__":
    main()
