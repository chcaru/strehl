"""M95 arm 13 -- WHAT IS ACTUALLY IN THE SCORING BAND?

Prompted by the orchestrator's HIGH defect against the high-band-energy metric
family: "if any published sharpness number in this project uses high-band energy
without a flat-ROI placebo, it is mostly measuring noise suppression." M95's
+0.1160 dex / "59% of the high-band loss" is named in that defect.

TWO THINGS ARE ALREADY ESTABLISHED AND THIS SCRIPT DOES NOT RE-LITIGATE THEM:

  * My own B28 fired: flat-region gain +0.1368 against detail-region +0.1343.
  * M113 measured the instrument 97.5% IMAGE-BLIND -- a closed form over a flat
    power spectrum with NO IMAGE AT ALL reads +0.1464 against +0.1428 for nine
    photographs.

So "does the flat ROI move as much as the detail ROI" has been answered YES
twice. Arm C below re-measures it a third time on real pixels anyway, because
the orchestrator asked for it and because a third route is cheap.

THE QUESTION THAT IS ACTUALLY OPEN, AND THAT THIS SCRIPT EXISTS FOR:

An image-blind LINEAR kernel multiplies signal and noise by the same |H(f)|.
So the kernel gain is real *for whatever is in the band* -- and whether that
gain buys the owner any sharpness depends entirely on a quantity nobody in this
corpus has measured: HOW MUCH OF THE 0.30-0.48 cyc/px BAND IS REAL CAPTURED
SIGNAL rather than sensor noise and demosaic invention?

If the band is mostly noise, +0.1160 dex is a noise-amplification number wearing
a sharpness label. If the band carries real subject detail, the gain is real and
the label is right. I do not know which before running this.

-------------------------------------------------------------------------------
PRE-REGISTERED BARS -- committed BEFORE this script was run. Anything that reads
a result and then adjusts a bar is a rationalisation, so the bars are constants
in this file and the verdict strings are computed, not typed.

P1  PLACEBO (the orchestrator's rule, adopted verbatim).
    R1 = |gain_flat| / |gain_detail| for the lanczos3-over-catmullrom gain.
      R1 >= 0.80  -> noise-dominated; the detail claim is NOT established.
      R1 <= 0.30  -> genuine detail loss.
      between     -> partial, and I say so.

P2  SIGNAL FRACTION in the scoring band on real DETAIL tiles.
    S_upper uses an unscaled dark frame as the noise floor. A dark frame has NO
    shot noise, so it UNDERSTATES noise and OVERSTATES signal: S_upper is the
    bound most generous to my published claim. That is deliberate.
      S_upper <= 0.20 -> the band is noise-dominated even on the generous
                         bound, and +0.1160 dex must NOT be called a sharpness
                         number without that rider.
      S_upper >= 0.50 -> the band carries real detail; the gain is substantially
                         real and my published framing stands.
      between         -> partial, and I say so.

P3  POWER CONTROL for the P2 estimator (discipline 595: an absence needs an
    instrument that could have said otherwise). Plant a band-limited signal into
    dark tiles at a known true S, using an INDEPENDENT half of the dark tiles as
    the reference floor.
      plant S_true = 0.90 -> estimator must return 0.90 +/- 0.10
      plant S_true = 0.00 -> estimator must return 0.00 +/- 0.10
    If either fails, S is uninterpretable and P2 is VOID -- reported, not fixed
    after the fact.

P4  POWER CONTROL for the band-power measure itself: a sigma = 1.0 px Fourier
    blur must drop detail-tile band power by >= 0.10 dex. An instrument that
    cannot see a 1 px blur cannot adjudicate a 0.1 dex kernel difference.

P5  OPTICS CROSS-CHECK. My re-derived diffraction MTF at Nyquist, from primary
    optics (f/5.6 marked, 2x teleconverter, m = 2.0, symmetric pupil), must land
    within +/- 0.005 of the corpus's measured 0.036. If it does not, my optical
    model is wrong and PART B's interpretation is unsupported.

PART A is pure geometry over the CFA sampling lattices and has no bar: it cannot
fail, it can only be computed, and it is reported as arithmetic.
-------------------------------------------------------------------------------
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np

from x2_pairs import BAND, LOWBAND, TILE, IMAGES, band_ratio, fourier_blur, freqs, load_luma, pick_tiles, window
from x3_kernel import PAD, resample

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

DARK = r"D:\macro-dark-frames\118MSDCF\DSC00001.ARW"   # ISO 100, ILCE-7CM2, verified by exiftool
NYQBAND = (0.46, 0.50)      # where optical MTF is smallest; used for the harsh bound only
PHASES = [(0.5, 0.0), (0.0, 0.5), (0.5, 0.5), (0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)]
KERNELS = ["catmullrom", "lanczos3"]
NT = 40

# --- bars, as constants -------------------------------------------------------
P1_NOISE = 0.80
P1_REAL = 0.30
P2_NOISE = 0.20
P2_REAL = 0.50
P3_TOL = 0.10
P4_MIN_DEX = 0.10
P5_TOL = 0.005
P5_CORPUS_MTF_NYQ = 0.036

# --- optics, from primary -----------------------------------------------------
LAMBDA_MM = 550e-6      # 550 nm, photopic centre
SENSOR_W_MM = 35.9      # full frame, Sony ILCE-7CM2
F_MARKED = 5.6          # EXIF FNumber, verified: wide open WITH the 2x TC fitted
MAGNIF = 2.0            # 1:1 macro + 2x teleconverter
PUPIL_MAG = 1.0         # symmetric pupil assumed; stated, not measured


def band_power(t, lo, hi):
    """Absolute mean spectral power in an annulus. Identical windowing and
    normalisation to x2_pairs.band_ratio, so the two are commensurable."""
    t = t.astype(np.float64)
    t = t - t.mean()
    f = np.fft.fftshift(np.fft.fft2(t * window(t.shape[0])))
    p = (f.real**2 + f.imag**2) / t.size
    fr = freqs(t.shape[0])
    m = (fr >= lo) & (fr < hi)
    return float(p[m].mean())


def pick_tiles_flat(img, n=NT, tile=TILE):
    """The FLATTEST tiles, by the same gradient-variance score pick_tiles uses to
    find the sharpest. Guarded so it cannot select unexposed frame border: the
    tile mean must sit between the 10th and 99th percentile of all tile means,
    which keeps it inside the photograph. Defocused background is the intended
    catch and is exactly the orchestrator's 'genuinely defocused patch'."""
    h, w = img.shape
    m = 3 * tile
    cand = []
    for y in range(m, h - m - tile, tile):
        for x in range(m, w - m - tile, tile):
            t = img[y : y + tile, x : x + tile]
            cand.append((float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var()), float(t.mean()), y, x))
    means = np.array([c[1] for c in cand])
    lo, hi = np.percentile(means, 10), np.percentile(means, 99)
    cand = [c for c in cand if lo <= c[1] <= hi]
    cand.sort()
    taken = []
    for s, mu, y, x in cand:
        if all(abs(y - ty) >= tile or abs(x - tx) >= tile for _, ty, tx in taken):
            taken.append((s, y, x))
        if len(taken) == n:
            break
    return [(y, x) for _, y, x in taken]


def padded(img, coords):
    """A TILE+2*PAD window centred on each TILE tile, so resample has margin and
    the scored region is byte-identical to the tile arm 8 selected."""
    out = []
    for y, x in coords:
        yy, xx = y - PAD, x - PAD
        if yy < 0 or xx < 0 or yy + TILE + 2 * PAD > img.shape[0] or xx + TILE + 2 * PAD > img.shape[1]:
            continue
        out.append(np.ascontiguousarray(img[yy : yy + TILE + 2 * PAD, xx : xx + TILE + 2 * PAD]))
    return out


def kernel_gain(tiles):
    """M95's exact paired statistic: phase-averaged band_ratio after a resample,
    minus the unresampled base. Returns the lanczos3-over-catmullrom gain."""
    base = float(np.mean([band_ratio(t[PAD:-PAD, PAD:-PAD], 1.0) for t in tiles]))
    g = {}
    for name in KERNELS:
        v = []
        for dy, dx in PHASES:
            for t in tiles:
                v.append(band_ratio(resample(t, dy, dx, name)[PAD:-PAD, PAD:-PAD], 1.0))
        g[name] = float(np.mean(v) - base)
    return base, g, g["lanczos3"] - g["catmullrom"]


def decode_dark(path):
    """The IDENTICAL rawpy recipe x0_rawpy.py used for the photograph, so the
    demosaic shapes the dark's noise spectrum exactly as it shapes the frame's."""
    import rawpy

    with rawpy.imread(path) as raw:
        rgb = raw.postprocess(
            output_color=rawpy.ColorSpace.raw,
            gamma=(1, 1),
            no_auto_bright=True,
            output_bps=16,
            user_wb=[1.0, 1.0, 1.0, 1.0],
            use_camera_wb=False,
            use_auto_wb=False,
            half_size=False,
        )
        rgb = np.ascontiguousarray(rgb)
    rgb = rgb.astype(np.float32)
    return 0.25 * rgb[..., 0] + 0.50 * rgb[..., 1] + 0.25 * rgb[..., 2]


def mtf_diffraction(nu):
    nu = np.clip(np.asarray(nu, dtype=np.float64), 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(nu) - nu * np.sqrt(np.maximum(0.0, 1.0 - nu * nu)))


def band_limited_field(rng, n, lo, hi):
    """A field whose power lies entirely inside [lo, hi) cyc/px."""
    a = rng.normal(0.0, 1.0, size=(n, n))
    f = np.fft.fftshift(np.fft.fft2(a))
    fr = freqs(n)
    f[~((fr >= lo) & (fr < hi))] = 0.0
    return np.fft.ifft2(np.fft.ifftshift(f)).real


def main():
    rng = np.random.default_rng(20260824)
    J = {"bars": {"P1_noise": P1_NOISE, "P1_real": P1_REAL, "P2_noise": P2_NOISE,
                  "P2_real": P2_REAL, "P3_tol": P3_TOL, "P4_min_dex": P4_MIN_DEX,
                  "P5_tol": P5_TOL, "P5_corpus": P5_CORPUS_MTF_NYQ}}

    print("=" * 78)
    print("M95 arm 13 -- what is actually IN the 0.30-0.48 cyc/px scoring band?")
    print("=" * 78)

    # ---------------------------------------------------------------- PART A
    print("\nPART A -- CFA sampling geometry of the scoring band (pure arithmetic)")
    n = 2048
    ax = (np.arange(n) - n // 2) / n
    fy, fx = np.meshgrid(ax, ax, indexing="ij")
    fr = np.sqrt(fy**2 + fx**2)
    ann = (fr >= BAND[0]) & (fr < BAND[1])
    rb_ok = (np.abs(fy) <= 0.25) & (np.abs(fx) <= 0.25)      # R,B: square lattice, pitch 2 px
    g_ok = (np.abs(fy) + np.abs(fx)) <= 0.5                  # G: quincunx, diamond Nyquist cell
    a_rb = float((ann & rb_ok).sum() / ann.sum())
    a_g = float((ann & g_ok).sum() / ann.sum())
    J["partA"] = {"frac_band_sampled_by_RB": a_rb, "frac_band_sampled_by_G": a_g,
                  "lowband_frac_RB": float((((fr >= LOWBAND[0]) & (fr < LOWBAND[1])) & rb_ok).sum()
                                           / ((fr >= LOWBAND[0]) & (fr < LOWBAND[1])).sum())}
    print(f"  scoring band {BAND[0]}-{BAND[1]} cyc/px")
    print(f"    fraction inside the RED/BLUE Nyquist cell (square, 0.25 cyc/px): {a_rb:.4f}")
    print(f"    fraction inside the GREEN quincunx Nyquist cell (|fx|+|fy|<=0.5): {a_g:.4f}")
    print(f"    (low band {LOWBAND[0]}-{LOWBAND[1]} inside R/B cell, for contrast: {J['partA']['lowband_frac_RB']:.4f})")

    # ---------------------------------------------------------------- PART B
    print("\nPART B -- optics, re-derived from primary")
    A = load_luma(IMAGES["A"]["path"])
    pitch_mm = SENSOR_W_MM / A.shape[1]
    n_eff = F_MARKED * (1.0 + MAGNIF / PUPIL_MAG)
    cutoff = 1.0 / (LAMBDA_MM * n_eff)
    nyq = 1.0 / (2.0 * pitch_mm)
    mtf_nyq = float(mtf_diffraction(nyq / cutoff))
    band_lo_cymm, band_hi_cymm = BAND[0] / pitch_mm, BAND[1] / pitch_mm
    p5_ok = abs(mtf_nyq - P5_CORPUS_MTF_NYQ) <= P5_TOL
    J["partB"] = {"decoded_shape": list(A.shape), "pitch_um": pitch_mm * 1000.0, "N_eff": n_eff,
                  "cutoff_cy_per_mm": cutoff, "nyquist_cy_per_mm": nyq, "mtf_at_nyquist": mtf_nyq,
                  "band_cy_per_mm": [band_lo_cymm, band_hi_cymm],
                  "mtf_at_band_lo": float(mtf_diffraction(band_lo_cymm / cutoff)),
                  "mtf_at_band_hi": float(mtf_diffraction(band_hi_cymm / cutoff)),
                  "mtf_at_74_cy_per_mm": float(mtf_diffraction(74.0 / cutoff)),
                  "P5_pass": bool(p5_ok)}
    print(f"  decoded {A.shape}, pixel pitch {pitch_mm*1000:.3f} um")
    print(f"  N_eff = {F_MARKED} * (1 + {MAGNIF}) = {n_eff:.2f}   cutoff {cutoff:.1f} cy/mm   Nyquist {nyq:.1f} cy/mm")
    print(f"  MTF at Nyquist = {mtf_nyq:.4f}   corpus says {P5_CORPUS_MTF_NYQ}   "
          f"P5 {'PASS' if p5_ok else 'FAIL'}")
    print(f"  scoring band = {band_lo_cymm:.1f}-{band_hi_cymm:.1f} cy/mm, optical MTF "
          f"{J['partB']['mtf_at_band_lo']:.4f} -> {J['partB']['mtf_at_band_hi']:.4f}")
    print(f"  MTF at 74 cy/mm (the artifact floor M85 named) = {J['partB']['mtf_at_74_cy_per_mm']:.4f}")

    # ---------------------------------------------------------------- tiles
    print("\nloading tiles ...")
    det_c = pick_tiles(A, n=NT)
    flat_c = pick_tiles_flat(A, n=NT)
    det = padded(A, det_c)
    flat = padded(A, flat_c)
    print(f"  detail tiles {len(det)}   flat tiles {len(flat)}")
    D = decode_dark(DARK)
    print(f"  dark decoded {D.shape}, mean {float(D.mean()):.2f} DN")
    dcoords = [(y, x) for y, x in det_c if y + TILE + PAD < D.shape[0] and x + TILE + PAD < D.shape[1]]
    dark = padded(D, dcoords)
    print(f"  dark tiles {len(dark)}")

    # ---------------------------------------------------------------- PART C
    print("\nPART C -- the placebo: does the FLAT ROI gain as much as the DETAIL ROI?")
    res = {}
    for label, tiles in (("detail", det), ("flat", flat), ("dark", dark)):
        base, g, gain = kernel_gain(tiles)
        res[label] = {"base_band_ratio": base, "catmullrom": g["catmullrom"],
                      "lanczos3": g["lanczos3"], "gain": gain, "n": len(tiles)}
        print(f"  {label:7s} n={len(tiles):3d}  base {base:+.4f}   cr {g['catmullrom']:+.4f}   "
              f"l3 {g['lanczos3']:+.4f}   GAIN {gain:+.4f} dex")
    r1 = abs(res["flat"]["gain"]) / abs(res["detail"]["gain"])
    r1_dark = abs(res["dark"]["gain"]) / abs(res["detail"]["gain"])
    v1 = ("NOISE-DOMINATED, detail claim NOT established" if r1 >= P1_NOISE
          else "GENUINE DETAIL LOSS" if r1 <= P1_REAL else "PARTIAL")
    J["partC"] = dict(res, R1_flat_over_detail=r1, R1_dark_over_detail=r1_dark, verdict=v1)
    print(f"\n  R1 = |gain_flat|/|gain_detail| = {r1:.4f}  (bars: >={P1_NOISE} noise, <={P1_REAL} real)")
    print(f"  and on a DARK FRAME, which contains no photograph at all: {r1_dark:.4f}")
    print(f"  P1 VERDICT: {v1}")

    # ---------------------------------------------------------------- PART D
    print("\nPART D -- how much of the band is real signal?")
    pb_det = float(np.mean([band_power(t[PAD:-PAD, PAD:-PAD], *BAND) for t in det]))
    pb_flat = float(np.mean([band_power(t[PAD:-PAD, PAD:-PAD], *BAND) for t in flat]))
    pb_dark = float(np.mean([band_power(t[PAD:-PAD, PAD:-PAD], *BAND) for t in dark]))
    nq_det = float(np.mean([band_power(t[PAD:-PAD, PAD:-PAD], *NYQBAND) for t in det]))
    nq_dark = float(np.mean([band_power(t[PAD:-PAD, PAD:-PAD], *NYQBAND) for t in dark]))
    s_upper = (pb_det - pb_dark) / pb_det
    scale = nq_det / nq_dark
    s_lower = (pb_det - pb_dark * scale) / pb_det
    s_flat = (pb_flat - pb_dark) / pb_flat
    v2 = ("NOISE-DOMINATED even on the generous bound" if s_upper <= P2_NOISE
          else "REAL DETAIL, published framing stands" if s_upper >= P2_REAL else "PARTIAL")
    J["partD"] = {"band_power_detail": pb_det, "band_power_flat": pb_flat, "band_power_dark": pb_dark,
                  "nyq_detail": nq_det, "nyq_dark": nq_dark, "shot_scale": scale,
                  "S_upper": s_upper, "S_lower": s_lower, "S_flat_upper": s_flat, "verdict": v2}
    print(f"  band power  detail {pb_det:.4e}   flat {pb_flat:.4e}   dark {pb_dark:.4e}")
    print(f"  S_upper (dark unscaled, read noise only -- GENEROUS to the claim) = {s_upper:.4f}")
    print(f"  shot-noise scale from {NYQBAND[0]}-{NYQBAND[1]} cyc/px = {scale:.3f}x")
    print(f"  S_lower (dark scaled by that, HARSH)                    = {s_lower:.4f}")
    print(f"  same generous bound on the FLAT tiles                   = {s_flat:.4f}")
    print(f"  P2 VERDICT: {v2}")

    # ---------------------------------------------------------------- PART E
    print("\nPART E -- controls")
    half = len(dark) // 2
    d_a = [t[PAD:-PAD, PAD:-PAD] for t in dark[:half]]
    d_b = [t[PAD:-PAD, PAD:-PAD] for t in dark[half:]]
    ref = float(np.mean([band_power(t, *BAND) for t in d_b]))
    p3 = {}
    for s_true in (0.90, 0.00):
        planted = []
        for t in d_a:
            pn = band_power(t, *BAND)
            if s_true == 0.0:
                planted.append(t.copy())
                continue
            f = band_limited_field(rng, t.shape[0], *BAND)
            pf = band_power(f, *BAND)
            target = pn * s_true / (1.0 - s_true)
            planted.append(t + f * np.sqrt(target / pf))
        est = float(np.mean([band_power(t, *BAND) for t in planted]))
        s_hat = (est - ref) / est
        ok = abs(s_hat - s_true) <= P3_TOL
        p3[f"plant_{s_true:.2f}"] = {"S_hat": s_hat, "pass": bool(ok)}
        print(f"  P3 plant S_true={s_true:.2f} -> S_hat={s_hat:+.4f}  {'PASS' if ok else 'FAIL'}")
    b0 = float(np.mean([np.log10(band_power(t[PAD:-PAD, PAD:-PAD], *BAND)) for t in det]))
    b1 = float(np.mean([np.log10(band_power(fourier_blur(t, 1.0)[PAD:-PAD, PAD:-PAD], *BAND)) for t in det]))
    p4_ok = (b0 - b1) >= P4_MIN_DEX
    print(f"  P4 sigma=1.0 px blur moves band power by {b1-b0:+.4f} dex  "
          f"(bar >= {P4_MIN_DEX}) {'PASS' if p4_ok else 'FAIL'}")
    J["partE"] = {"P3": p3, "P4_blur_dex": b1 - b0, "P4_pass": bool(p4_ok)}

    p3_ok = all(v["pass"] for v in p3.values())
    J["controls_all_pass"] = bool(p3_ok and p4_ok and p5_ok)
    print(f"\n  controls: P3 {'PASS' if p3_ok else 'FAIL'}   P4 {'PASS' if p4_ok else 'FAIL'}   "
          f"P5 {'PASS' if p5_ok else 'FAIL'}")
    if not p3_ok:
        print("  *** P3 FAILED -- P2's S is UNINTERPRETABLE and is reported VOID ***")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "x11_bandsignal.json"), "w", encoding="utf-8") as fh:
        json.dump(J, fh, indent=1)
    print("\nwrote out/x11_bandsignal.json")


if __name__ == "__main__":
    main()
