"""M113 K1 - is the M95 band metric measuring accuracy, or measuring ringing?

Reuses M95's own `band_ratio` VERBATIM by importing it from
`experiments/M95-resample/src/x2_pairs.py`, so any difference in the verdict is
my method and not a re-implementation of the statistic.

Adds two reference-based statistics M95 never computed:

  RMS_TRUTH   RMS error against a FOURIER-EXACT sub-pixel shift, relative to the
              tile's own RMS. For a band-limited sampled signal the Fourier shift
              is THE band-limited interpolant, so this is the definition of
              "translate without changing content". It penalises blur AND ringing.

  RMS_TRIP    shift by +d then by -d with the SAME kernel and compare to the
              input. The truth here is the input itself, so nothing is modelled.
              FOOLED BY: `nearest`, which is a permutation and round-trips exactly
              (rule 18) -- nearest is therefore excluded from this column's ranking.

The kernel ladder is ordered by passband width and runs PAST Lanczos-3 to a
truncated sinc, so a metric that rewards ringing can be driven off the end.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "M95-resample", "src"))
import x2_pairs as X  # noqa: E402  -- M95's instrument, verbatim

OUT = os.path.join(os.path.dirname(HERE), "out")
TILE = 256
PAD = 48          # > any kernel radius here, cropped off before every statistic
PHASES = [(0.5, 0.0), (0.0, 0.5), (0.5, 0.5), (0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)]


# ---------------------------------------------------------------- kernels
def w_bilinear(t):
    return np.maximum(0.0, 1.0 - np.abs(np.asarray(t, float)))


def w_catmullrom(t):
    a = np.abs(np.asarray(t, float))
    a2, a3 = a * a, a * a * a
    w = np.where(a <= 1.0, 1.5 * a3 - 2.5 * a2 + 1.0, 0.0)
    return np.where((a > 1.0) & (a < 2.0), -0.5 * a3 + 2.5 * a2 - 4.0 * a + 2.0, w)


def lanczos(n):
    def w(t):
        t = np.asarray(t, float)
        with np.errstate(invalid="ignore", divide="ignore"):
            v = np.sinc(t) * np.sinc(t / n)
        return np.where(np.abs(t) < n, v, 0.0)
    return w


def sinc_box(n):
    """Truncated sinc, no window. The ringiest thing on the ladder."""
    def w(t):
        t = np.asarray(t, float)
        return np.where(np.abs(t) < n, np.sinc(t), 0.0)
    return w


# name -> (weight fn, radius). Ordered by passband width / ringiness.
LADDER = [
    ("bilinear",   w_bilinear,    1),
    ("catmullrom", w_catmullrom,  2),
    ("lanczos2",   lanczos(2),    2),
    ("lanczos3",   lanczos(3),    3),
    ("lanczos4",   lanczos(4),    4),
    ("lanczos6",   lanczos(6),    6),
    ("lanczos12",  lanczos(12),  12),
    ("sinc16",     sinc_box(16), 16),
]


def shift1d(a, axis, frac, wfun, radius):
    a = np.moveaxis(a, axis, 0)
    taps = np.arange(-radius + 1, radius + 1)
    w = wfun(frac - taps)
    w = w / w.sum()
    out = np.zeros_like(a, dtype=np.float64)
    for t, wt in zip(taps, w):
        out += wt * np.roll(a, -t, axis=0)
    return np.moveaxis(out, 0, axis)


def kshift(tile, dy, dx, wfun, radius):
    return shift1d(shift1d(tile.astype(np.float64), 0, dy, wfun, radius), 1, dx, wfun, radius)


def fshift(tile, dy, dx):
    """Fourier-exact circular shift. THE band-limited interpolant.

    SIGN CONVENTION, and it is not a detail. `kshift` evaluates the continuous
    reconstruction at (i+dy, j+dx); this must do the SAME or the two arms are a
    shift of 2*d apart and every "error" is the shift itself. The first version
    of this function used exp(-2i*pi*f*d), which is a shift the OTHER way, and
    N4 did not catch it because N4 compared fshift to np.roll rather than to
    kshift. N4B below closes that hole.
    """
    n0, n1 = tile.shape
    fy = np.fft.fftfreq(n0)[:, None]
    fx = np.fft.fftfreq(n1)[None, :]
    ph = np.exp(2j * np.pi * (fy * dy + fx * dx))
    return np.fft.ifft2(np.fft.fft2(tile.astype(np.float64)) * ph).real


def band_boost(tile, gain):
    """N3: pure zero-phase gain inside the metric's own high band. This is
    ringing and nothing else -- no detail is added, existing components are
    amplified. band_ratio MUST like it; truth MUST NOT."""
    n = tile.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    fr = np.sqrt(fy ** 2 + fx ** 2)
    h = np.where((fr >= X.BAND[0]) & (fr < X.BAND[1]), gain, 1.0)
    return np.fft.ifft2(np.fft.fft2(tile.astype(np.float64)) * h).real


def crop(a):
    return a[PAD:-PAD, PAD:-PAD]


def rel_rms(a, b):
    d = crop(a) - crop(b)
    ref = crop(b)
    return float(np.sqrt((d ** 2).mean()) / (np.sqrt(((ref - ref.mean()) ** 2).mean()) + 1e-12))


# ------------------------------------------------------------ tile choice
def geometric_tiles(img):
    """ROI CHOSEN ON GEOMETRY, BEFORE ANY RESULT. Every non-overlapping TILE-px
    tile whose centre lies inside the central half of the frame. No content
    scoring, no dropping, no selection on the answer."""
    h, w = img.shape
    ys = range(h // 4, 3 * h // 4 - TILE, TILE)
    xs = range(w // 4, 3 * w // 4 - TILE, TILE)
    out = [(y, x) for y in ys for x in xs
           if y - PAD >= 0 and x - PAD >= 0 and y + TILE + PAD <= h and x + TILE + PAD <= w]
    return out


def synth_bandlimited(n, seed=1113, cutoff=0.45):
    """A signal that IS band-limited, so the Fourier shift is provably the truth."""
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    fr = np.sqrt(fy ** 2 + fx ** 2)
    a = np.fft.ifft2(np.fft.fft2(a) * (fr < cutoff)).real
    return a / a.std() * 300.0 + 2000.0


# ----------------------------------------------------------------- arms
def run(tiles_iter, label):
    rows = {}
    base = []
    tiles = list(tiles_iter)
    for t in tiles:
        base.append(X.band_ratio(crop(t), 1.0))
    base = float(np.mean(base))

    for name, wf, r in LADDER:
        br, rt, tr = [], [], []
        for t in tiles:
            b_, rt_, tr_ = [], [], []
            for dy, dx in PHASES:
                k = kshift(t, dy, dx, wf, r)
                f = fshift(t, dy, dx)
                back = kshift(k, -dy, -dx, wf, r)
                b_.append(X.band_ratio(crop(k), 1.0))
                rt_.append(rel_rms(k, f))
                tr_.append(rel_rms(back, t))
            br.append(np.mean(b_))
            rt.append(np.mean(rt_))
            tr.append(np.mean(tr_))
        rows[name] = dict(band_delta=float(np.mean(br) - base),
                          rms_truth=float(np.mean(rt)),
                          rms_trip=float(np.mean(tr)))
    return base, rows, len(tiles)


def controls(tiles):
    c = {}
    # N1 null: zero shift
    n1 = {}
    for name, wf, r in LADDER:
        v = [rel_rms(kshift(t, 0.0, 0.0, wf, r), t) for t in tiles]
        n1[name] = float(np.mean(v))
    c["N1_null_rel_rms_at_zero_shift"] = n1
    # N4 loader: integer Fourier shift == np.roll, with the SAME sign kshift uses
    t = tiles[0]
    c["N4_fourier_int_vs_roll_maxabs"] = float(
        np.abs(fshift(t, 3.0, -5.0) - np.roll(np.roll(t, -3, axis=0), 5, axis=1)).max())
    # N4B: THE CONTROL THAT MATTERS, and N4 is not it. N4 checks fshift against
    # np.roll; it says nothing about whether fshift shifts the same WAY kshift
    # does. The first draft of this harness shipped exp(-2i*pi*f*d) against a
    # kshift that evaluates at (i+d) -- a 2*d disagreement -- and N4 passed.
    #
    # The pinning control: on data that IS band-limited, a very high order
    # windowed sinc must converge to the Fourier shift. Same phase, same sign, so
    # a sign error cannot pass. Bar registered at < 0.02 relative RMS; the
    # sign-flipped harness read 1.314 on this exact quantity, a 350x separation.
    syn = [synth_bandlimited(TILE + 2 * PAD, seed=9000 + i) for i in range(4)]
    wf12, r12 = LADDER[-2][1], LADDER[-2][2]
    v = [rel_rms(kshift(t2, 0.37, -0.21, wf12, r12), fshift(t2, 0.37, -0.21)) for t2 in syn]
    c["N4B_lanczos12_vs_fourier_bandlimited_relrms"] = float(np.mean(v))
    c["N4B_pass"] = bool(np.mean(v) < 0.02)
    # N2 response: planted Fourier-exact gaussian blur
    b0 = float(np.mean([X.band_ratio(crop(t), 1.0) for t in tiles]))
    bl = [X.fourier_blur(t, 0.25) for t in tiles]
    c["N2_blur025_band_delta"] = float(np.mean([X.band_ratio(crop(x), 1.0) for x in bl]) - b0)
    c["N2_blur025_rms_truth"] = float(np.mean([rel_rms(x, t) for x, t in zip(bl, tiles)]))
    # N3 falsifier: pure passband boost -- ringing with no added detail
    for g in (1.5, 3.0):
        bo = [band_boost(t, g) for t in tiles]
        c[f"N3_boost{g}_band_delta"] = float(np.mean([X.band_ratio(crop(x), 1.0) for x in bo]) - b0)
        c[f"N3_boost{g}_rms_truth"] = float(np.mean([rel_rms(x, t) for x, t in zip(bo, tiles)]))
    return c


def table(rows, title):
    print(f"\n{title}")
    print(f"  {'kernel':11s} {'band_delta':>11s} {'RMS_TRUTH':>11s} {'RMS_TRIP':>10s}")
    for k, v in rows.items():
        print(f"  {k:11s} {v['band_delta']:+11.4f} {v['rms_truth']:11.5f} {v['rms_trip']:10.5f}")
    bb = max(rows, key=lambda k: rows[k]["band_delta"])
    bt = min(rows, key=lambda k: rows[k]["rms_truth"])
    bp = min(rows, key=lambda k: rows[k]["rms_trip"])
    print(f"  BEST by band_ratio : {bb}")
    print(f"  BEST by RMS_TRUTH  : {bt}")
    print(f"  BEST by RMS_TRIP   : {bp}")
    return dict(best_band=bb, best_truth=bt, best_trip=bp)


def main():
    res = {}

    # --- arm S: synthetic, exactly band-limited. Truth is provable here. ---
    syn = [synth_bandlimited(TILE + 2 * PAD, seed=1113 + i) for i in range(8)]
    _, rs, ns = run(syn, "synthetic")
    res["synthetic"] = dict(rows=rs, n=ns, **table(rs, f"ARM S - synthetic band-limited (cutoff 0.45), n={ns}"))

    # --- arm R: real strehl decode, M95's own B0 file ---
    p = X.IMAGES["B0"]["path"]
    if not os.path.exists(p):
        print(f"MISSING {p}")
        return 2
    img = X.load_luma(p)
    print(f"\nB0 = {p}  {img.shape}")
    tl = geometric_tiles(img)
    tiles = [img[y - PAD:y + TILE + PAD, x - PAD:x + TILE + PAD].astype(np.float64) for y, x in tl]
    print(f"geometric lattice: {len(tiles)} tiles of {TILE}px, centres in the central half")
    # how band-limited is this data, really?
    fr_hi = []
    for t in tiles:
        c = crop(t)
        f = np.abs(np.fft.fft2(c - c.mean())) ** 2
        n = c.shape[0]
        fy = np.fft.fftfreq(n)[:, None]
        fx = np.fft.fftfreq(n)[None, :]
        rr = np.sqrt(fy ** 2 + fx ** 2)
        fr_hi.append(float(f[rr >= 0.40].sum() / f.sum()))
    print(f"power fraction above 0.40 cyc/px: mean {np.mean(fr_hi):.4f} (aliasing exposure)")
    res["alias_fraction_above_0p40"] = float(np.mean(fr_hi))

    cs = controls(tiles)
    print("\n--- CONTROLS ---")
    print(f"  N4 loader: max|fourier_int - roll| = {cs['N4_fourier_int_vs_roll_maxabs']:.3e}")
    print(f"  N4B sign-convention pin: lanczos12 vs fourier on band-limited data = "
          f"{cs['N4B_lanczos12_vs_fourier_bandlimited_relrms']:.5f} rel RMS "
          f"(bar < 0.02): {'PASS' if cs['N4B_pass'] else 'FAIL'}")
    print("  N1 null (rel RMS at zero shift), must be ~0 for interpolating kernels:")
    for k, v in cs["N1_null_rel_rms_at_zero_shift"].items():
        print(f"      {k:11s} {v:.3e}")
    print(f"  N2 blur sigma=0.25: band_delta {cs['N2_blur025_band_delta']:+.4f}  RMS_TRUTH {cs['N2_blur025_rms_truth']:.5f}")
    for g in (1.5, 3.0):
        print(f"  N3 boost x{g} in 0.30-0.48: band_delta {cs[f'N3_boost{g}_band_delta']:+.4f}  "
              f"RMS_TRUTH {cs[f'N3_boost{g}_rms_truth']:.5f}")
    res["controls"] = cs

    _, rr_, nr = run(tiles, "real")
    res["real_B0"] = dict(rows=rr_, n=nr, **table(rr_, f"ARM R - real strehl decode (B0), geometric tiles, n={nr}"))

    json.dump(res, open(os.path.join(OUT, "k1_truth.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k1_truth.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
