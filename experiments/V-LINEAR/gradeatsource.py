"""How big was the tone confound AT ITS SOURCE -- on the frames Zerene ate?

V-HEADTOHEAD2 measured the confound at the OUTPUT: it fitted a monotone map
from strehl's stacked pixels to Zerene's stacked pixels on 4x4 block means, and
found that map reproduced Zerene's 0.25-0.30 cyc/px band power to 0.02%.  Its
sec.7 called the cause "the comparators' inputs are graded" and asked for a
linear re-development so the comparison could be re-run.

That re-run is impossible on this machine (Zerene's trial licence expired on
2026-06-06 and it refuses to save output; see V-LINEAR.md).  But the INPUT side
of sec.7's claim can still be measured, and has never been measured before,
because both developments of the same 63 RAW frames now exist:

    LIN  strehl --linear-srgb --demosaic, no tone curve at all
    LR   the Lightroom TIFFs that were actually fed to Zerene (Contrast2012=+100)

These are two developments of ONE exposure.  Their noise is the same photons.
So the question "how much fine-scale contrast did the grade add to Zerene's
input?" is answerable directly, with no stacker in the loop.

ARMS.  A number is worthless without a control that could have refuted it, so
three arms run through identical code:

  GRADE  LIN vs LR              -- differs by the development (tone, and see
                                   the disclosure below)
  BLUR   LIN vs blur(LIN)       -- differs ONLY by resolution.  THE FALSIFIER.
                                   A tone fit on 4x4 block means has no access
                                   to frequencies above 0.125 cyc/px, so if the
                                   method is sound it must explain ~NONE of a
                                   pure blur.  If it explains a blur too, then
                                   the method cannot tell tone from resolution
                                   and V-HEADTOHEAD2's 89-212% means nothing.
  NULL   LIN vs LIN             -- must return exactly 1.000 in every band.

DISCLOSURE.  The GRADE arm is not purely tone.  LIN and LR also differ by
demosaic algorithm, by a 1.0018 scale and a crop (measured in geomgrid.py),
and by colour primaries.  So the GRADE arm bounds the tone effect from ABOVE,
and its honest reading is "a block-average tone fit accounts for this fraction
of the whole input-side difference", not "the grade is exactly this big".
geomgrid.py separately establishes there is no non-linear warp between them
(affine to 1.97 px rms; a radial term buys 12% of that), so the geometry
difference is a scale, not a distortion.

The tone fit and its application are gradetest.fit_map / gradetest.apply_map
and the band statistic is h2h2b.band_power -- the prior lane's own code,
imported, not reimplemented.
"""
import os
import sys

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
from h2h2b import band_power, coarse, REF                        # noqa: E402
from gradetest import fit_map, apply_map                         # noqa: E402

LIN = r"C:\dev\strehl-out\V-LINEAR\lintiff"
LRD = r"D:\edited\macro\test2"
T = 256
PAD = 32
PEAK_MIN = 0.70
BLUR_SIGMA = 0.60          # px; small enough to be a plausible resolution
                           # difference between two good stackers, which is the
                           # regime the falsifier has to work in
NAMES = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
LO = np.array([b[0] for b in h2.BANDS])
HI = np.array([b[1] for b in h2.BANDS])


def gauss_blur(a, sigma):
    """Exact Gaussian blur in the Fourier domain.  Done this way rather than
    with a truncated spatial kernel so that the blur applied is EXACTLY the one
    named in the report: a spatial kernel's truncation error lands in precisely
    the high bands being measured."""
    t = a.shape[0]
    r = h2.radial(t)
    m = a.mean()
    return m + np.real(np.fft.ifft2(np.fft.fft2(a - m)
                                    * np.exp(-2 * (np.pi * sigma * r) ** 2)))


def luma(mm, y0, x0, t):
    return h2.luma709(np.asarray(mm[y0:y0 + t, x0:x0 + t, :3], np.float64))


def norm_rows(rows):
    """Each ROI's band vector divided by its own reference band (0.05-0.10),
    then averaged over ROIs -- h2h2b/gradetest's coarse-normalised statistic.
    Normalising per ROI is what makes exposure and scene brightness cancel."""
    r = np.array(rows, float)
    ref = r[:, REF]
    ok = ref > 0
    return (r[ok] / ref[ok, None]).mean(0)


def run_arm(name, pairs):
    """pairs: list of (crop_lin_padded, crop_other_padded) at PAD+T+PAD."""
    a_rows, b_rows, m_rows = [], [], []
    for ca, cb in pairs:
        inner = slice(PAD, PAD + T)
        m = fit_map(coarse(ca).ravel(), coarse(cb).ravel())
        cm = apply_map(m, ca)
        pa = band_power(ca[inner, inner], LO, HI)
        pb = band_power(cb[inner, inner], LO, HI)
        pm = band_power(cm[inner, inner], LO, HI)
        if pa is None or pb is None or pm is None:
            continue
        a_rows.append(pa)
        b_rows.append(pb)
        m_rows.append(pm)
    A, B, M = norm_rows(a_rows), norm_rows(b_rows), norm_rows(m_rows)
    gap = B / A
    tone = M / A
    print(f"\n=== arm {name}   n={len(a_rows)} ROIs ===")
    print(f"{'band':>11} {'gap B/A':>9} {'tone M/A':>9} {'explained':>10}")
    for i, nm in enumerate(NAMES):
        if abs(gap[i] - 1.0) < 1e-6:
            frac = "n/a"
        else:
            frac = f"{100 * (tone[i] - 1) / (gap[i] - 1):9.1f}%"
        print(f"{nm:>11} {gap[i]:9.4f} {tone[i]:9.4f} {frac:>10}")
    return gap, tone


def main():
    frames = [int(v) for v in (sys.argv[1].split(",") if len(sys.argv) > 1
                               else ["10", "20", "30", "40", "50"])]
    fdel = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    step = T + 2 * PAD
    grade, blur, null = [], [], []
    fine = slice(3, 7)          # 0.20-0.48 cyc/px, the bands under test
    for n in frames:
        mmL = tifffile.memmap(os.path.join(LIN, f"DSC{n:05d}.tif"), mode="r")
        mmR = tifffile.memmap(os.path.join(LRD, f"20260507-DSC{n:05d}.tif"),
                              mode="r")
        # FOCUS GATE.  These are single frames of a focus stack, so most of each
        # frame is defocused.  In a defocused region strehl's linear develop
        # carries shot noise where Lightroom's carries denoised nothing, and
        # comparing the two there measures noise policy, not the grade.  A tile
        # is admitted only where THIS frame is a local maximum of fine-band
        # power against its neighbours +/-fdel frames away -- the same
        # interior-maximum rule geom.py uses, applied to focus instead of
        # scale.  An earlier version of this arm had no such gate and reported
        # a 25x fine-band deficit that was mostly defocused noise.
        nbr = []
        for d in (-fdel, fdel):
            p = os.path.join(LIN, f"DSC{n + d:05d}.tif")
            nbr.append(tifffile.memmap(p, mode="r") if os.path.exists(p) else None)
        H, W = mmR.shape[0], mmR.shape[1]
        ys = np.linspace(700, H - 700 - step, 4).astype(int)
        xs = np.linspace(700, W - 700 - step, 5).astype(int)
        kept = defoc = 0
        for y in ys:
            for x in xs:
                cb = luma(mmR, y, x, step)
                dy, dx, pk = h2.integer_shift(cb, luma(mmL, y + 8, x + 12, step),
                                              maxshift=12)
                if pk < PEAK_MIN or max(abs(dy), abs(dx)) >= 12:
                    continue
                yy, xx = y + 8 + dy, x + 12 + dx
                ca = luma(mmL, yy, xx, step)
                p0 = band_power(ca[PAD:PAD + T, PAD:PAD + T], LO, HI)
                if p0 is None:
                    continue
                s0 = p0[fine].sum() / p0[REF]
                infocus = True
                for mm in nbr:
                    if mm is None:
                        continue
                    pn = band_power(luma(mm, yy, xx, step)[PAD:PAD + T,
                                                           PAD:PAD + T], LO, HI)
                    if pn is not None and pn[fine].sum() / pn[REF] >= s0:
                        infocus = False
                if not infocus:
                    defoc += 1
                    continue
                grade.append((ca, cb))
                blur.append((ca, gauss_blur(ca, BLUR_SIGMA)))
                null.append((ca, ca))
                kept += 1
        print(f"frame {n}: {kept}/{len(ys) * len(xs)} tiles kept "
              f"({defoc} dropped as defocused vs frames +/-{fdel})")

    print(f"\nblur falsifier sigma = {BLUR_SIGMA} px; tone map fitted on "
          f"{T + 2 * PAD}px tiles reduced to 4x4 block means "
          f"({(T + 2 * PAD) // 4}x{(T + 2 * PAD) // 4} samples), which carry no "
          "information above 0.125 cyc/px")
    run_arm("NULL   LIN vs LIN", null)
    run_arm(f"BLUR   LIN vs blur(LIN, sigma={BLUR_SIGMA})", blur)
    g, t = run_arm("GRADE  LIN vs Lightroom (what Zerene ate)", grade)

    print("\nreading: 'gap' is how much more fine-scale contrast the second "
          "image has;\n'tone' is how much of that a 4x4-block tone fit "
          "reproduces from the FIRST image's own pixels.")


if __name__ == "__main__":
    main()
