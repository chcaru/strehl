"""cositeab.py -- empirical A/B for the chroma co-site sharpness fix.

BUILD-SHARP (docs/research/BUILD-SHARP.md 20-21) found that the viewable render
applies a fixed phi=0.25 Catmull-Rom shift to R and B on BOTH axes, serially,
AFTER the alignment gather, at image_out.rs:956-957.  It runs only inside
write_binned -- the viewable path -- so every ESF number the project ever took
on linear.tif excluded it.  BUILD-COSITE is folding that shift into the gather
transform, where it costs nothing.

This instrument decides whether that actually happened, on the delivered pixels,
without trusting the implementer's own numbers.

WHY THIS SHAPE OF TEST
----------------------
The fix has an exceptionally sharp signature, and it is not "the image got
sharper".  Removing a separable phi=0.25 resample on R and B, and only on R and
B, must:

  1. leave GREEN BIT-IDENTICAL.  Green never had the shift.  This is a placebo
     that is free, exact, and impossible to fake: any change in green means the
     change did something other than what it claims.

  2. multiply the R and B amplitude spectrum by exactly 1/|H_CR(0.25, f)| --
     a specific CURVE, rising from 1.0 at DC to ~2.1 at f=0.5.  Not "bigger":
     a predicted shape across the whole frequency axis.

A test that only asked "did R get sharper" would be satisfied by any sharpening
whatsoever, including a wrong one.  Matching the curve is a much narrower
target, so passing it means much more.

Measuring along the fx axis (averaging row spectra) isolates the x-resample:
at fy = 0 the y-kernel contributes |H(0)| = 1 exactly, so the observed ratio is
the 1-D response and is directly comparable to the closed form.  Same for
columns and the y-resample.  Doing it this way avoids having to model the 2-D
product on a radial average, where the two axes mix.

NOISE IS NOT A CONFOUND HERE, AND THAT IS WORTH SAYING
------------------------------------------------------
Removing a resample un-blurs signal and noise alike, so both rise.  For the
usual "is the image better" question that would be a problem.  For THIS question
it is not, because the prediction is about the RATIO of spectra, and the ratio
is the kernel's inverse response whatever the underlying spectrum happens to be.
The instrument tests the operator, not the scene.

COMMISSIONING
-------------
--commission takes one render, applies a known phi=0.25 Catmull-Rom shift to R
and B (the defect, synthesised), and checks that the instrument recovers the
predicted curve when comparing shifted-vs-original.  An instrument that cannot
see a co-site it planted itself cannot be trusted to confirm one was removed.
It also runs a null (a file against itself), which must return exactly 1.0.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import tifffile


# ---------------------------------------------------------------- kernel

def cr_taps(phi: float) -> np.ndarray:
    """Catmull-Rom weights at fractional phase phi, for offsets -1, 0, 1, 2."""
    p, p2, p3 = phi, phi * phi, phi * phi * phi
    return np.array([
        -0.5 * p3 + p2 - 0.5 * p,
        1.5 * p3 - 2.5 * p2 + 1.0,
        -1.5 * p3 + 2.0 * p2 + 0.5 * p,
        0.5 * p3 - 0.5 * p2,
    ])


def cr_amplitude(phi: float, f: np.ndarray) -> np.ndarray:
    """|H(f)| for a Catmull-Rom resample at phase phi.  f in cycles/sample."""
    w = cr_taps(phi)
    offsets = np.array([-1.0, 0.0, 1.0, 2.0])
    # H(f) = sum_k w_k exp(-2 pi i f k); |H| is the retained amplitude, the
    # unit-magnitude phase factor of the shift itself dropping out of the modulus.
    ph = np.exp(-2j * np.pi * np.outer(f, offsets))
    return np.abs(ph @ w)


def apply_cr_shift(plane: np.ndarray, phi: float, axis: int) -> np.ndarray:
    """Shift a plane by phi samples along `axis` using Catmull-Rom, edge-clamped."""
    w = cr_taps(phi)
    a = np.moveaxis(plane.astype(np.float64), axis, 0)
    n = a.shape[0]
    out = np.zeros_like(a)
    for k, off in enumerate((-1, 0, 1, 2)):
        idx = np.clip(np.arange(n) + off, 0, n - 1)
        out += w[k] * a[idx]
    return np.moveaxis(out, 0, axis)


# ---------------------------------------------------------------- spectra

def axis_amplitude_spectrum(plane: np.ndarray, axis: int, n_fft: int = 1024):
    """Mean amplitude spectrum along `axis`, averaged over the other axis.

    Hann-windowed so that the wrap discontinuity does not inject a broadband
    pedestal that would flatten the ratio toward 1 and hide the effect.
    """
    a = np.moveaxis(plane.astype(np.float64), axis, -1)
    a = a[:, :n_fft] if a.shape[-1] >= n_fft else a
    a = a - a.mean(axis=-1, keepdims=True)
    win = np.hanning(a.shape[-1])
    spec = np.fft.rfft(a * win, axis=-1)
    power = (np.abs(spec) ** 2).mean(axis=0)
    freq = np.fft.rfftfreq(a.shape[-1])
    return freq, np.sqrt(power)


def ratio_curve(before: np.ndarray, after: np.ndarray, axis: int, n_fft: int):
    f, sb = axis_amplitude_spectrum(before, axis, n_fft)
    _, sa = axis_amplitude_spectrum(after, axis, n_fft)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(sb > 0, sa / sb, np.nan)
    return f, r


# ---------------------------------------------------------------- io

def load_rgb(path: Path, crop: int) -> np.ndarray:
    arr = tifffile.imread(str(path))
    assert arr.dtype == np.uint16, f"{path.name}: expected uint16, got {arr.dtype}"
    assert arr.ndim == 3 and arr.shape[2] >= 3, f"{path.name}: expected HxWx3+, got {arr.shape}"
    h, w = arr.shape[:2]
    if crop and (h > crop or w > crop):
        y0, x0 = (h - crop) // 2, (w - crop) // 2
        arr = arr[y0:y0 + crop, x0:x0 + crop, :3]
    return np.ascontiguousarray(arr[:, :, :3])


def plane_hash(p: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest()[:16].upper()


# ---------------------------------------------------------------- report

BANDS = [(0.10, 0.15), (0.20, 0.30), (0.30, 0.40), (0.40, 0.50)]
CH = ("R", "G", "B")


def band_mean(f: np.ndarray, r: np.ndarray, lo: float, hi: float) -> float:
    m = (f >= lo) & (f < hi) & np.isfinite(r)
    return float(np.mean(r[m])) if m.any() else float("nan")


def compare(before: np.ndarray, after: np.ndarray, n_fft: int, phi: float, label: str) -> bool:
    print(f"\n=== {label} ===")
    print(f"  crop {before.shape[0]}x{before.shape[1]}, n_fft {n_fft}")

    # --- the free, exact placebo -------------------------------------------
    hb, ha = plane_hash(before[:, :, 1]), plane_hash(after[:, :, 1])
    green_identical = hb == ha
    print(f"\n  GREEN PLACEBO  before {hb}  after {ha}   "
          f"{'IDENTICAL' if green_identical else '*** CHANGED ***'}")
    if not green_identical:
        d = after[:, :, 1].astype(np.int32) - before[:, :, 1].astype(np.int32)
        print(f"    green delta: max |d| = {int(np.abs(d).max())} DN, "
              f"mean |d| = {np.abs(d).mean():.4f} DN, "
              f"{100.0 * np.count_nonzero(d) / d.size:.3f}% of pixels moved")
        print("    -> green must not move.  Either the fix touched the wrong planes,")
        print("       or the two arms differ by something besides the co-site.")

    # --- the predicted curve ------------------------------------------------
    fgrid = np.linspace(0.0, 0.5, 256)
    pred = 1.0 / np.maximum(cr_amplitude(phi, fgrid), 1e-12)

    hdr = "  band        " + "".join(f"{f'{lo:.2f}-{hi:.2f}':>12}" for lo, hi in BANDS)
    print("\n  amplitude ratio  after / before   (1.000 = no change)")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    print("  predicted   ", end="")
    for lo, hi in BANDS:
        print(f"{band_mean(fgrid, pred, lo, hi):>12.3f}", end="")
    print("   <- 1/|H_CR(0.25)|, what removing the co-site must give R and B")

    verdicts = {}
    for axis, aname in ((1, "x (rows)"), (0, "y (cols)")):
        print(f"\n  along {aname}")
        for ci, cname in enumerate(CH):
            f, r = ratio_curve(before[:, :, ci], after[:, :, ci], axis, n_fft)
            print(f"    {cname}         ", end="")
            vals = []
            for lo, hi in BANDS:
                v = band_mean(f, r, lo, hi)
                vals.append(v)
                print(f"{v:>12.3f}", end="")
            verdicts[(aname, cname)] = vals
            if cname == "G":
                worst = max(abs(v - 1.0) for v in vals if np.isfinite(v))
                print(f"   control, max |dev| {worst:.4f}", end="")
            print()

    # --- agreement with the predicted shape, on R and B only ---------------
    #
    # The closed form is a 1-D idealisation and the real operator is separable
    # on BOTH axes, so this row is a LOWER BOUND on the true signature, not the
    # target.  Averaging row spectra estimates the integral of P(fx, fy) over
    # fy; a y-resample multiplies P by |H(fy)|^2, so it depresses that integral
    # even at fy = 0.  Restoring both axes therefore lifts the measured x-ratio
    # by more than the x-kernel alone accounts for.  Use the PLANTED row from a
    # commissioning run on the same subject as the empirical target.
    pred_bands = [band_mean(fgrid, pred, lo, hi) for lo, hi in BANDS]
    chroma = {k: v for k, v in verdicts.items() if k[1] != "G"}
    print("\n  per-band deviation from the 1-D closed form (R and B, both axes):")
    print("    band        ", end="")
    for lo, hi in BANDS:
        print(f"{f'{lo:.2f}-{hi:.2f}':>12}", end="")
    print()
    print("    dev %       ", end="")
    per_band = []
    for bi, p in enumerate(pred_bands):
        cells = [vals[bi] for vals in chroma.values() if np.isfinite(vals[bi])]
        d = 100 * np.mean([abs(c - p) / p for c in cells]) if cells else float("nan")
        per_band.append(d)
        print(f"{d:>12.1f}", end="")
    print()
    finite = [d for d in per_band if np.isfinite(d)]
    if finite:
        print(f"    mean {np.mean(finite):.1f}%, worst band {np.max(finite):.1f}%")
    print("    NB: the closed form is 1-D; the operator is separable on both axes,")
    print("        so a correct fix OVERSHOOTS this row.  Compare against the")
    print("        PLANTED row of a commissioning run, not against this one.")

    # Machine-readable signature so a later real A/B can be compared to the
    # planted one directly rather than to the idealisation.
    sig = []
    for (aname, cname), vals in sorted(chroma.items()):
        sig.append(f"{cname}{aname[0]}=" + ",".join(f"{v:.4f}" for v in vals))
    print("  SIGNATURE " + " ".join(sig))
    return green_identical


# ---------------------------------------------------------------- commission

def commission(src: Path, crop: int, n_fft: int, phi: float) -> int:
    print("=" * 74)
    print("COMMISSIONING -- can this instrument see a co-site it planted itself?")
    print("=" * 74)
    print(f"  source: {src}")

    orig = load_rgb(src, crop)

    print("\n--- structural checks on the kernel ---")
    t0 = cr_taps(0.0)
    print(f"  taps(0.0)          = {np.array2string(t0, precision=6)}")
    ok_ident = np.array_equal(t0, np.array([0.0, 1.0, 0.0, 0.0]))
    print(f"  taps(0) == [0,1,0,0]  {ok_ident}   "
          f"(interpolating kernel: a zero-phase resample is the exact identity)")
    s = cr_taps(phi).sum()
    print(f"  sum taps({phi})      = {s:.12f}   (must be 1: DC must be preserved)")
    a0 = float(cr_amplitude(phi, np.array([0.0]))[0])
    print(f"  |H({phi}, f=0)|      = {a0:.12f}   (no gain at DC)")
    ok_struct = ok_ident and abs(s - 1.0) < 1e-12 and abs(a0 - 1.0) < 1e-12
    if not ok_struct:
        print("  *** structural checks FAILED -- kernel is wrong, stop here")
        return 1

    # NULL: a file against itself.  Must be exactly 1.0 everywhere.  If the
    # instrument reports anything else here, every other number it prints is
    # noise of its own making.
    print("\n" + "-" * 74)
    green_ok_null = compare(orig, orig.copy(), n_fft, phi, "NULL CONTROL -- file against itself")

    # PLANTED: synthesise the defect on R and B, both axes, and ask the
    # instrument to recover 1/|H| when comparing planted -> original.
    planted = orig.astype(np.float64).copy()
    for ci in (0, 2):
        p = planted[:, :, ci]
        p = apply_cr_shift(p, phi, axis=1)
        p = apply_cr_shift(p, phi, axis=0)
        planted[:, :, ci] = p
    planted_u16 = np.clip(np.rint(planted), 0, 65535).astype(np.uint16)

    print("\n" + "-" * 74)
    print("PLANTED -- 'before' carries a synthetic phi=0.25 co-site on R,B (both axes);")
    print("'after' is the clean original.  This is exactly what removing the co-site")
    print("should look like, so the measured ratio must track the predicted curve.")
    green_ok_plant = compare(planted_u16, orig, n_fft, phi, "PLANTED CO-SITE -> CLEAN")

    print("\n" + "=" * 74)
    print("COMMISSIONING VERDICT")
    print("=" * 74)
    print(f"  kernel structural checks     : {'PASS' if ok_struct else 'FAIL'}")
    print(f"  null returns identical green : {'PASS' if green_ok_null else 'FAIL'}")
    print(f"  planted arm leaves green be  : {'PASS' if green_ok_plant else 'FAIL'}")
    print("\n  Read the PLANTED table above: R and B must track the 'predicted' row")
    print("  and G must sit at 1.000.  If R and B track it, this instrument can")
    print("  confirm or refute BUILD-COSITE's fix on real renders.")
    return 0 if (ok_struct and green_ok_null and green_ok_plant) else 1


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before", type=Path, nargs="?", help="16-bit sRGB TIFF, pre-fix")
    ap.add_argument("after", type=Path, nargs="?", help="16-bit sRGB TIFF, post-fix")
    ap.add_argument("--commission", type=Path, default=None,
                    help="run self-commissioning on this single render instead")
    ap.add_argument("--crop", type=int, default=2048)
    ap.add_argument("--n-fft", type=int, default=1024)
    ap.add_argument("--phi", type=float, default=0.25)
    a = ap.parse_args()

    if a.commission is not None:
        return commission(a.commission, a.crop, a.n_fft, a.phi)

    if not a.before or not a.after:
        ap.error("need both before and after, or --commission")

    before = load_rgb(a.before, a.crop)
    after = load_rgb(a.after, a.crop)
    assert before.shape == after.shape, f"shape mismatch {before.shape} vs {after.shape}"

    print("=" * 74)
    print("CO-SITE A/B  (measured on the VIEWABLE render -- linear.tif never")
    print("carries the co-site and will show nothing)")
    print("=" * 74)
    print(f"  before: {a.before}")
    print(f"  after : {a.after}")
    green_ok = compare(before, after, a.n_fft, a.phi, "REAL A/B")
    print("\n  Reminder: G bit-identical is a requirement, not a nicety.  A build that")
    print("  sharpens R and B but also moves G has done something other than fold a")
    print("  constant chroma shift into the gather.")
    return 0 if green_ok else 2


if __name__ == "__main__":
    sys.exit(main())
