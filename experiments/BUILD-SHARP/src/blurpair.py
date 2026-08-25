"""Paired equivalent-blur between two arms rendered in IDENTICAL geometry.

The instrument
--------------
If arm B is arm A convolved with a small isotropic Gaussian of width sigma,
then to second order

    B = A + (sigma^2 / 2) * laplacian(A)

so regressing the DIFFERENCE image on the LAPLACIAN of A recovers sigma^2
directly, in pixels, with a SIGN:

    alpha = <B - A, L> / <L, L>            sigma_eq = sqrt(2 * alpha)

alpha > 0  =>  B is blurrier than A by sqrt(2*alpha) px
alpha < 0  =>  B is sharper than A (reported as a negative sigma^2)

Why this and not band power (AGENTS rules 2, 9, 18)
---------------------------------------------------
A high-pass energy statistic rises when a merge MANUFACTURES structure exactly
as it does when a merge preserves it, and this project has twice shipped a
"sharpness" number that a flat crop and a dark frame satisfied. This statistic
is a PROJECTION onto the structure that is already in A. Injected structure
that is uncorrelated with laplacian(A) -- speckle, blotch, election patchwork,
independent noise -- contributes ZERO in expectation, not a positive amount.

How it can be fooled, stated where it is used (rule 18)
-------------------------------------------------------
1. Noise in A appears in BOTH terms: <-n_A, lap(n_A)> = +|grad n_A|^2 > 0, so
   an arm pair whose noise levels differ reads a spurious POSITIVE alpha --
   i.e. it is biased toward calling the QUIETER arm blurry. That bias is
   measured, not argued: the same statistic is reported on DEFOCUS tiles that
   contain no resolvable subject, where the true answer is zero and whatever
   is left is exactly this bias. Both numbers are printed in the same table
   (rule 5), raw beside control.
2. It assumes the two arms are registered. Both arms here come out of the same
   binary with the same warp solve, so they are registered by construction; the
   integer-shift check in `--verify-registration` asserts it rather than
   assuming it.
3. It is a small-blur expansion. Above sigma ~ 1 px it under-reads. The planted
   ladder in `--plant` shows exactly where it starts to.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import ndimage

import bslib as B
from bands import TILE, pick_tiles

# 5-point laplacian. Deliberately the smallest stencil: a wide one would
# respond to the low frequencies where every arm agrees and dilute the
# statistic with pixels that carry no information about the question.
LAP = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)


def alpha_tile(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """(alpha, r) for one tile: alpha in px^2/2, r the correlation of the fit."""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    lap = ndimage.convolve(a, LAP, mode="nearest")
    d = b - a
    # drop the border, where the stencil is extrapolated
    lap = lap[2:-2, 2:-2]
    d = d[2:-2, 2:-2]
    lap = lap - lap.mean()
    d = d - d.mean()
    den = float((lap * lap).sum())
    if den <= 0:
        return 0.0, 0.0
    num = float((lap * d).sum())
    alpha = num / den
    dn = float(np.sqrt((d * d).sum()))
    r = num / (np.sqrt(den) * dn) if dn > 0 else 0.0
    return alpha, r


def sigma_eq(alpha: float) -> float:
    """Equivalent Gaussian sigma, signed. sigma^2 = 2*alpha."""
    s = 2.0 * alpha
    return float(np.sign(s) * np.sqrt(abs(s)))


def score(ga: np.ndarray, gb: np.ndarray, tiles):
    out = []
    for y, x, _ in tiles:
        a = ga[y : y + TILE, x : x + TILE]
        b = gb[y : y + TILE, x : x + TILE]
        al, r = alpha_tile(a, b)
        out.append((al, r))
    al = np.array([o[0] for o in out])
    r = np.array([o[1] for o in out])
    return al, r


def gauss_exact(img: np.ndarray, sigma: float) -> np.ndarray:
    """Fourier-exact Gaussian blur.

    A sampled kernel of radius ceil(4*sigma) degenerates to a delta at small
    sigma and reads as an instrument floor (M95 F-3, fact P53). exp(-2 pi^2
    sigma^2 f^2) cannot truncate.
    """
    if sigma <= 0:
        return img.copy()
    h, w = img.shape
    F = np.fft.rfft2(img.astype(np.float64))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    mtf = np.exp(-2.0 * np.pi**2 * sigma**2 * (fy**2 + fx**2))
    return np.fft.irfft2(F * mtf, s=(h, w)).astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--a", required=True, help="reference arm")
    ap.add_argument("--b", nargs="+", required=True, help="arms scored against A")
    ap.add_argument("--select-on", default="g0-nn")
    ap.add_argument("--ntiles", type=int, default=40)
    ap.add_argument("--plant", action="store_true", help="run the planted-blur ladder")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    sel = B.read_green(B.arm(a.subject, a.select_on))
    margin = 600
    detail = pick_tiles(sel, a.ntiles, True, margin)
    flat = pick_tiles(sel, a.ntiles, False, margin,
                      exclude=[(y, x) for y, x, _ in detail])
    del sel

    ga = B.read_green(B.arm(a.subject, a.a))
    results = {}

    if a.plant:
        print("PLANTED-BLUR LADDER (positive control): blur arm A by a known sigma")
        print(f"{'planted':>8} {'detail sigma_eq':>16} {'sd':>8} {'defocus sigma_eq':>18} "
              f"{'recovery':>9}")
        for s in [0.0, 0.10, 0.25, 0.40, 0.70, 1.00]:
            gb = gauss_exact(ga, s)
            ad, _ = score(ga, gb, detail)
            af, _ = score(ga, gb, flat)
            sd_ = sigma_eq(float(ad.mean()))
            sf_ = sigma_eq(float(af.mean()))
            rec = sd_ / s if s > 0 else float("nan")
            print(f"{s:8.2f} {sd_:16.4f} {sigma_eq(float(ad.std())):8.4f} "
                  f"{sf_:18.4f} {rec:9.4f}")
            results[f"plant_{s}"] = dict(planted=s, detail=sd_, defocus=sf_)
        print()

    print(f"A = {a.a}   ({a.subject}, {len(detail)} detail / {len(flat)} defocus tiles, "
          f"tile {TILE} px, selected on {a.select_on})")
    print(f"{'B arm':>14} {'detail sigma_eq':>16} {'sem':>8} {'defocus sigma_eq':>18} "
          f"{'sem':>8} {'excess':>9} {'fit r':>7}")
    for name in a.b:
        gb = B.read_green(B.arm(a.subject, name))
        if gb.shape != ga.shape:
            raise SystemExit(f"{name}: shape {gb.shape} != {ga.shape}")
        ad, rd = score(ga, gb, detail)
        af, _ = score(ga, gb, flat)
        sd_ = sigma_eq(float(ad.mean()))
        sf_ = sigma_eq(float(af.mean()))
        semd = sigma_eq(float(ad.std() / np.sqrt(len(ad))))
        semf = sigma_eq(float(af.std() / np.sqrt(len(af))))
        exc = sigma_eq(float(ad.mean() - af.mean()))
        print(f"{name:>14} {sd_:16.4f} {semd:8.4f} {sf_:18.4f} {semf:8.4f} "
              f"{exc:9.4f} {float(rd.mean()):7.3f}")
        results[name] = dict(detail_sigma_eq=sd_, defocus_sigma_eq=sf_,
                             detail_sem=semd, defocus_sem=semf, excess=exc,
                             detail_alpha=float(ad.mean()),
                             defocus_alpha=float(af.mean()),
                             fit_r=float(rd.mean()))
        del gb

    out = Path(a.out) if a.out else (Path(__file__).resolve().parents[1] / "out" /
                                     f"blurpair-{a.subject}-{a.a}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(subject=a.subject, reference=a.a,
                                   select_on=a.select_on, tile=TILE,
                                   results=results), indent=1))
    print(f"\nwrote {out}")
    print("\npositive sigma_eq = B is BLURRIER than A. The defocus column is the "
          "\nnoise-asymmetry bias measured on tiles with no resolvable subject; "
          "\n'excess' is detail minus defocus, and BOTH are reported (rule 5).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
