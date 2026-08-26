"""Model-free per-tile signal/noise separation for the FRAME arm.

The level-binned noise floor is not good enough. In flowers-cpl the per-tile band
power varies 29% across frames, so max-over-36 of a noise-only tile still reads
~70 DN, and in those tiles argmax lands on k=175 -- the MOST defocused frame in
the stack, which cannot possibly hold the most detail. The statistic was
measuring noise and calling it detail.

This measures the split instead of modelling it. Two frames adjacent in the stack
carry the SAME scene one focus step apart and INDEPENDENT sensor noise. Per tile,
after an integer-shift alignment:

    signal power ~ Cov(b_k, b_k1)     the noise cross-term has zero expectation
    noise power  ~ Var(b_k) - Cov

Alignment is INTEGER-ONLY. Sub-pixel resampling would add blur to the very
quantity being measured and would do it to the frame arm alone. The residual
sub-pixel error therefore biases Cov DOWN -- against the frame, toward H1 -- so
these frame-signal numbers are a LOWER bound. --selftest measures how loose that
bound is (C4) and checks the instrument can return both a null and a positive.
"""
import argparse
import os
import numpy as np
from pathlib import Path
from scipy import ndimage, signal
import bestframe as B

GAL = Path(os.environ.get("VBF_GAL", r"C:\dev\strehl-out\GALLERY-FIXED-SRGB"))
RAW = Path(r"D:\personal\macro")
OUT = Path(os.environ.get("VBF_OUT", r"C:\dev\strehl-out\V-BESTFRAME"))
SEARCH = 10          # +/- px, integer shift search per tile


def band_of(path, m8, m16, band):
    fL = B.luma(B.decode(path)).astype(np.float32)
    s, t, peak = B.register2(m16, B.boxdown(B.raw_green_half(path), 8), down=16)
    xs, ys, cov = B.fit_tone(m8, B.boxdown(fL, 8), s, t)
    fT = B.apply_tone_fast(fL, B.tone_lut(xs, ys)); del fL
    b = B.dog(fT, band[0] * s, band[1] * s)
    return b, s, t, peak, cov


def pair_tiles(b0, b1, s0, t0, ye, xe):
    """Per tile: Var(b0), and max-over-integer-shift Cov(b0, b1)."""
    H, W = b1.shape
    ny, nx = len(ye) - 1, len(xe) - 1
    V = np.full((ny, nx), np.nan); C = np.full((ny, nx), np.nan)
    D = np.full((ny, nx), np.nan); Z = np.full((ny, nx), np.nan)
    for i in range(ny):
        y0 = int(round(s0 * ye[i] + t0[1])); y1 = int(round(s0 * ye[i + 1] + t0[1]))
        for j in range(nx):
            x0 = int(round(s0 * xe[j] + t0[0])); x1 = int(round(s0 * xe[j + 1] + t0[0]))
            ay0, ay1 = max(SEARCH, y0), min(H - SEARCH, y1)
            ax0, ax1 = max(SEARCH, x0), min(W - SEARCH, x1)
            if ay1 - ay0 < 64 or ax1 - ax0 < 64:
                continue
            A = b0[ay0:ay1, ax0:ax1].astype(np.float64)
            W1 = b1[ay0 - SEARCH:ay1 + SEARCH, ax0 - SEARCH:ax1 + SEARCH].astype(np.float64)
            R = signal.correlate(W1, A, mode="valid", method="fft") / A.size
            k = int(np.argmax(R)); dy, dx = np.unravel_index(k, R.shape)
            V[i, j] = float((A ** 2).mean()); C[i, j] = float(R.flat[k])
            Z[i, j] = float(R[SEARCH, SEARCH])
            D[i, j] = float(np.hypot(dy - SEARCH, dx - SEARCH))
    return V, C, D, Z


def selftest(subj, band):
    """Three checks the instrument must survive, two of which must be able to fail."""
    mL = B.luma(B.read_merge(GAL / f"{subj}.tiff")).astype(np.float32)
    ye = B.tile_edges(mL.shape[0], B.NTY); xe = B.tile_edges(mL.shape[1], B.NTX)
    m8, m16 = B.boxdown(mL, 8), B.boxdown(mL, 16); del mL
    fs = sorted((RAW / subj).glob("*.ARW"))
    k = len(fs) // 4
    b0, s0, t0, p0, _ = band_of(fs[k], m8, m16, band)
    print(f"C-selftest on {subj} frame {k} ({fs[k].name}) s={s0:.4f} peak={p0:.3f}")

    V, C, D, Z = pair_tiles(b0, b0, s0, t0, ye, xe)
    r = C / V
    print(f"  C1 identity      Cov(b,b)/Var median={np.nanmedian(r):.6f} "
          f"min={np.nanmin(r):.6f} max={np.nanmax(r):.6f} "
          f"shift=0 in {np.nansum(D == 0):.0f}/{np.sum(~np.isnan(D))} tiles "
          f"-> {'PASS' if abs(np.nanmedian(r) - 1) < 1e-9 else 'FAIL'}")

    rng = np.random.default_rng(7)
    amp = float(np.sqrt(np.nanmedian(V)))
    n0 = (b0 + rng.normal(0, amp, b0.shape).astype(np.float32))
    n1 = (b0 + rng.normal(0, amp, b0.shape).astype(np.float32))
    V2, C2, _, _ = pair_tiles(n0, n1, s0, t0, ye, xe)
    print(f"  C2 planted noise recovered signal frac median={np.nanmedian(C2 / V2):.4f} "
          f"(truth 0.5 by construction, noise amp = median frame band amp) "
          f"-> {'PASS' if 0.40 < np.nanmedian(C2 / V2) < 0.60 else 'FAIL'}")

    ind0 = rng.normal(0, amp, b0.shape).astype(np.float32)
    ind1 = rng.normal(0, amp, b0.shape).astype(np.float32)
    V3, C3, _, Z3 = pair_tiles(ind0, ind1, s0, t0, ye, xe)
    print(f"  C3 pure-noise null  Cov/Var median={np.nanmedian(C3 / V3):.5f} "
          f"at-zero-shift median={np.nanmedian(Z3 / V3):+.5f} "
          f"-> {'PASS' if np.nanmedian(C3 / V3) < 0.05 else 'FAIL'}  "
          f"(THIS IS THE MAX-BIAS FLOOR: the +ve bias from picking the best of "
          f"{(2*SEARCH+1)**2} shifts)")

    sh = ndimage.shift(b0, (0.5, 0.5), order=3, mode="nearest")
    V4, C4, _, _ = pair_tiles(b0, sh, s0, t0, ye, xe)
    print(f"  C4 subpixel penalty Cov/Var median={np.nanmedian(C4 / V4):.4f} "
          f"(1.0 = no loss; this is how much a half-pixel residual costs the "
          f"frame arm, i.e. how loose the LOWER bound is)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--pairs", type=int, default=10)
    ap.add_argument("--band", default="fine")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    band = B.FINE if a.band == "fine" else B.MID
    if a.selftest:
        selftest(a.subject, band); return
    subj = a.subject
    mL = B.luma(B.read_merge(GAL / f"{subj}.tiff")).astype(np.float32)
    ye = B.tile_edges(mL.shape[0], B.NTY); xe = B.tile_edges(mL.shape[1], B.NTX)
    m_tiles = B.tile_stats(mL, ye, xe)
    m8, m16 = B.boxdown(mL, 8), B.boxdown(mL, 16)
    del mL
    fs = sorted((RAW / subj).glob("*.ARW"))
    anchors = np.unique(np.linspace(0, len(fs) - 2, a.pairs).round().astype(int))
    print(f"{subj}: {len(fs)} frames on disk, probing {len(anchors)} ADJACENT PAIRS "
          f"(k,k+1) at k={list(anchors)}  band={a.band}{band}", flush=True)
    S = np.full((len(anchors), B.NTY, B.NTX), np.nan)
    N = np.full_like(S, np.nan)
    for n, k in enumerate(anchors):
        b0, s0, t0, p0, c0 = band_of(fs[k], m8, m16, band)
        b1, s1, t1, p1, c1 = band_of(fs[k + 1], m8, m16, band)
        V, C, D, Z = pair_tiles(b0, b1, s0, t0, ye, xe)
        del b0, b1
        S[n] = np.maximum(C, 0.0); N[n] = np.maximum(V - C, 0.0)
        frac = S[n] / np.maximum(V, 1e-9)
        print(f"  k={k:3d}/{k+1:<3d} {fs[k].name} s={s0:.4f}/{s1:.4f} "
              f"peak={p0:.3f}/{p1:.3f} | med signalRMS {np.sqrt(np.nanmedian(S[n])):7.2f} "
              f"noiseRMS {np.sqrt(np.nanmedian(N[n])):7.2f} DN, signal frac "
              f"med {np.nanmedian(frac):.4f} p95 {np.nanpercentile(frac, 95):.4f}, "
              f"|shift| med {np.nanmedian(D):.1f} max {np.nanmax(D):.1f} px", flush=True)
    np.savez_compressed(OUT / f"{subj}__paircov_{a.band}.npz", S=S, N=N,
                        anchors=anchors, merge_tiles=m_tiles, ye=ye, xe=xe,
                        band=np.array(band), n_on_disk=len(fs))
    print(f"  -> {subj}__paircov_{a.band}.npz")


if __name__ == "__main__":
    main()
