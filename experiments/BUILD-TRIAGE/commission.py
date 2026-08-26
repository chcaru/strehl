#!/usr/bin/env python3
"""Commission the BUILD-TRIAGE instrument before any verdict is trusted.

An uncommissioned instrument and a genuinely null result look identical.  This
runs four checks and HARD-ERRORS on any of them:

  C1 NULL          -- a file against itself must return the identity: ratio
                      exactly 1.0 in every band, offset exactly (0,0), ncc 1.0.
  C2 REGISTRATION  -- a crop displaced by a KNOWN integer offset must be
                      relocated at exactly that offset.
  C3 POSITIVE (exact) -- a 2-tap [1/2, 1/2] horizontal filter has the closed
                      form discrete MTF |cos(pi*fx)|.  The instrument must
                      recover the power-weighted band average of that to <1%.
                      This control is EXACT discrete mathematics, not a
                      continuous approximation, so it cannot be circular.
  C4 POSITIVE (resample) -- the Catmull-Rom coverage rescale must (a) be the
                      exact identity at k = 1.0 and (b) cost a measurable,
                      bounded amount at the k the real merges actually use.

Every planted mutation is asserted to have LANDED -- an anchor that does not
bite is a silent no-op, and a silent no-op passes every test.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str) -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<34s} {detail}")
    if not ok:
        FAIL.append(name)


def band_pred(tile: np.ndarray, mtf2: np.ndarray, band: str) -> float:
    """Power-weighted band-average of a KNOWN mtf, for prediction.

    ratio = sqrt( sum(P * MTF^2) / sum(P) ) over the band -- the same average
    the instrument itself forms, so the two are commensurable.
    """
    r, p = tri.spectrum(tile)
    lo, hi = tri.BANDS[band]
    m = (r >= lo) & (r < hi)
    return float(np.sqrt((p[m] * mtf2[m]).sum() / p[m].sum()))


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tri.LIN, "109MSDCF.tiff")
    print(f"COMMISSIONING BUILD-TRIAGE instrument\n  subject file: {src}")
    log = tri.read_log(os.path.join(tri.LIN, os.path.basename(src)[:-5] + ".log"),
                       require=("coverage_k", "n_frames", "resampler"))
    print(f"  provenance  : n_frames={log.get('n_frames')} "
          f"ref_frame={log.get('ref_frame')} coverage_k={log.get('coverage_k')} "
          f"resampler={log.get('resampler')}")
    print(f"  levels      : {log.get('levels')}")
    print(f"  colour      : {log.get('colour')}")

    rgb = tri.load16(src)
    y = tri.luma(rgb)
    h, w = y.shape
    N = 512
    # A tile with real detail in it; the controls are meaningless on flat sky.
    best, bv = (h // 2, w // 2), -1.0
    for cy in range(N, h - N, 400):
        for cx in range(N, w - N, 400):
            t = y[cy:cy + N, cx:cx + N]
            v = tri.band_amp(t)["high"]
            if v > bv:
                bv, best = v, (cy, cx)
    cy, cx = best
    tile = np.ascontiguousarray(y[cy:cy + N, cx:cx + N])
    a0 = tri.band_amp(tile)
    print(f"  control tile: ({cx},{cy}) {N}x{N}  "
          f"mean={a0['mean']:.1f} DN  high={a0['high']:.3f} DN  "
          f"mid={a0['mid']:.3f} DN")

    # ---- C1 NULL --------------------------------------------------------
    print("\nC1 NULL (a file against itself)")
    b0 = tri.band_amp(tile)
    ratios = {k: b0[k] / a0[k] for k in tri.BANDS}
    exact = all(b0[k] == a0[k] for k in tri.BANDS) and b0["mean"] == a0["mean"]
    check("identity, all bands", exact,
          "  ".join(f"{k}={ratios[k]:.10f}" for k in tri.BANDS))
    my, mx, ncc = tri.find_match(tile, y, cy, cx, N, search=48)
    check("self-registration", (my, mx) == (cy, cx) and abs(ncc - 1.0) < 1e-4,
          f"found ({mx},{my}) want ({cx},{cy})  ncc={ncc:.6f}")

    # ---- C2 REGISTRATION at a planted offset -----------------------------
    print("\nC2 REGISTRATION (planted integer offset)")
    for (dy, dx) in ((7, -13), (-23, 31), (0, 40)):
        sub = np.ascontiguousarray(y[cy + dy:cy + dy + N, cx + dx:cx + dx + N])
        assert not np.array_equal(sub, tile), (
            f"planted offset ({dy},{dx}) did not change the tile -- anchor did "
            "not land, the control is a no-op")
        fy, fx, n2 = tri.find_match(sub, y, cy, cx, N, search=48)
        check(f"offset ({dy:+d},{dx:+d})", (fy, fx) == (cy + dy, cx + dx),
              f"found ({fx - cx:+d},{fy - cy:+d})  ncc={n2:.6f}")

    # ---- C3 POSITIVE, exact discrete MTF ---------------------------------
    print("\nC3 POSITIVE CONTROL -- 2-tap [1/2,1/2], exact MTF |cos(pi*fx)|")
    blur = np.empty_like(tile)
    blur[:, 1:] = 0.5 * (tile[:, 1:] + tile[:, :-1])
    blur[:, 0] = tile[:, 0]
    assert not np.allclose(blur, tile), "2-tap plant did not land"
    fx = np.fft.fftfreq(N)[None, :] * np.ones((N, 1))
    mtf2 = np.cos(np.pi * fx) ** 2
    ab = tri.band_amp(blur)
    for band in ("mid", "high"):
        got = ab[band] / a0[band]
        want = band_pred(tile, mtf2, band)
        err = abs(got - want) / want
        check(f"{band}: recovers |cos(pi fx)|", err < 0.01,
              f"measured={got:.4f}  predicted={want:.4f}  err={err * 100:.2f}%")
    check("level is preserved by a blur",
          abs(ab["mean"] - a0["mean"]) / a0["mean"] < 1e-3,
          f"mean {a0['mean']:.1f} -> {ab['mean']:.1f} DN "
          f"(delta {ab['mean'] - a0['mean']:+.2f} DN)")

    # ---- C4 POSITIVE, the coverage resample -------------------------------
    print("\nC4 POSITIVE CONTROL -- Catmull-Rom coverage rescale")
    con = np.full((256, 256), 1234.5, np.float32)
    rc = tri.catmull_rom_scale(con, 0.99)
    check("constant image is preserved exactly",
          float(np.abs(rc - 1234.5).max()) < 1e-2,
          f"mean {rc.mean():.4f} DN  max|err| {np.abs(rc - 1234.5).max():.6f} DN")
    ramp = (np.arange(256, dtype=np.float32)[:, None] * np.ones((1, 256), np.float32))
    cc = (256 - 1) / 2.0
    wantr = (np.arange(256, dtype=np.float32) - cc) * 0.99 + cc
    check("linear ramp matches closed form",
          float(np.abs(tri.catmull_rom_scale(ramp, 0.99) - wantr[:, None]).max()) < 1e-2,
          f"max|err| {np.abs(tri.catmull_rom_scale(ramp, 0.99) - wantr[:, None]).max():.6f} DN")

    idn = tri.catmull_rom_scale(tile, 1.0)
    check("k=1.0 is the exact identity", np.allclose(idn, tile, atol=1e-3),
          f"max|diff| = {np.abs(idn - tile).max():.6f} DN")

    k_merge = log["coverage_k"]
    k_ref = 0.9974
    # THE ASSUMPTION UNDER TEST.  Both arms get exactly ONE Catmull-Rom gather:
    # the merge at its own coverage k, a STREHL_ONLY_FRAME render at the 3 px
    # floor k=0.9974.  Treating that loss as common-mode is only legitimate if
    # the loss depends on APPLYING the kernel and not on the SIZE of the scale
    # change.  Measure it across the whole range of k this corpus actually uses
    # (0.9046 .. 0.9974) rather than assume it.
    print("       Catmull-Rom loss vs scale k, measured at matched SENSOR "
          "frequency:")
    print(f"       {'k':>8s} {'high x':>8s} {'mid x':>8s} {'low x':>8s} "
          f"{'d-mean DN':>10s} {'ncc':>7s}")
    losses = []
    for k in (0.9974, 0.99, 0.97, 0.95, 0.93, 0.9046):
        full = tri.catmull_rom_scale(y, k)
        assert not np.allclose(full[cy:cy + N, cx:cx + N], tile, atol=1e-3), \
            f"rescale k={k} did not land -- control is a no-op"
        my2, mx2, n3 = tri.find_match(tile, full, cy, cx, N, search=96)
        ar = tri.band_amp(np.ascontiguousarray(full[my2:my2 + N, mx2:mx2 + N]), k)
        aa = tri.band_amp(tile, 1.0)
        print(f"       {k:8.4f} {ar['high'] / aa['high']:8.4f} "
              f"{ar['mid'] / aa['mid']:8.4f} {ar['low'] / aa['low']:8.4f} "
              f"{ar['mean'] - aa['mean']:10.2f} {n3:7.4f}")
        losses.append(ar["high"] / aa["high"])
    spread = max(losses) - min(losses)
    check("high-band loss is per-APPLICATION not per-magnitude "
          "(spread over k <= 0.12)", spread <= 0.12,
          f"range {min(losses):.4f}..{max(losses):.4f}  spread {spread:.4f} "
          f"-> THIS IS THE INSTRUMENT'S SYSTEMATIC FLOOR")

    # Window extent.  A window of N output pixels covers N*k SENSOR pixels, so
    # equal PIXEL windows in two arms with different k cover different PHYSICAL
    # areas -- visible above as ncc falling to 0.92 and the low band rising to
    # 1.15 at k=0.9046, neither of which a rescale can do to matched content.
    # The real comparison must lift N_B = N_A * k_A / k_B.  That only works if
    # the PSD estimate is invariant to window size, so check that too.
    print("\nC5 WINDOW-SIZE INVARIANCE of the PSD estimate (same content)")
    base = tri.band_amp(np.ascontiguousarray(y[cy:cy + 512, cx:cx + 512]), 1.0)
    for n2 in (478, 496, 512, 544):
        o = (512 - n2) // 2
        b2 = tri.band_amp(
            np.ascontiguousarray(y[cy + o:cy + o + n2, cx + o:cx + o + n2]), 1.0)
        print(f"       N={n2:4d}: high {b2['high']:7.3f} DN "
              f"(x{b2['high'] / base['high']:.4f})  "
              f"mid x{b2['mid'] / base['mid']:.4f}  "
              f"mean {b2['mean'] - base['mean']:+7.2f} DN")
        if n2 == 478:
            check("PSD stable across the window sizes matched k demands",
                  abs(b2["high"] / base["high"] - 1.0) < 0.08,
                  f"N=478 vs 512 -> x{b2['high'] / base['high']:.4f}")

    print("\nC6 WINDOWED RESCALE == the corresponding slice of the FULL rescale")
    small = np.ascontiguousarray(y[1000:1000 + 900, 2000:2000 + 900])
    for kk in (0.9321, 0.99):
        full_s = tri.catmull_rom_scale(small, kk)
        wy, wx, wn = 200, 300, 256
        winw = tri.catmull_rom_scale(small, kk, (wy, wx, wn, wn))
        ref = full_s[wy:wy + wn, wx:wx + wn]
        assert not np.allclose(ref, small[wy:wy + wn, wx:wx + wn], atol=1e-3), \
            f"rescale k={kk} did not land -- the equivalence check is vacuous"
        check(f"windowed == full slice at k={kk}",
              float(np.abs(winw - ref).max()) == 0.0,
              f"max|diff| = {np.abs(winw - ref).max():.9f} DN")

    print("\n" + ("COMMISSIONED: all checks pass" if not FAIL
                  else f"NOT COMMISSIONED: {len(FAIL)} failed -> {FAIL}"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
