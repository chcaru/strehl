"""M5 — C1, the synthetic positive control.  RUN THIS FIRST.

Plants a *known* diffraction cutoff into a broadband image, samples it exactly
the way the sensor does, adds white noise of a known sigma, and asks the
unmodified estimator to recover the cutoff. If it cannot recover a cutoff we
put in ourselves, it cannot measure one we did not.

Forward model, deliberately faithful to the real acquisition:

  1. 1/f^alpha random field on a grid F = 4x finer than the sensor, so that
     frequencies up to 2.0 sensor cyc/px exist and can alias.
  2. Multiply by the incoherent diffraction MTF of a circular pupil at the
     planted cutoff.
  3. Box-average F fine pixels — the 100%-fill photosite aperture.
  4. Decimate to the sensor grid. Aliasing above 0.5 sensor cyc/px is real
     and is kept.
  5. Add i.i.d. Gaussian noise per photosite, add black level, quantise to
     uint16.
  6. Read G1 / G2 / GQ out of that array with the production code path.

Run: python m5_synthetic.py            (full sweep, ~3 min)
     python m5_synthetic.py --quick    (a third of the cases)
"""

from __future__ import annotations

import sys
import time

import numpy as np

import m5_lib as L

SENSOR_N = 1280  # synthetic sensor image side, px
FINE = 4  # fine grid oversampling relative to the sensor grid
ROI = 512
TILE = 256
CENTRE = 640


def make_scene(f_c_sensor, sigma_dn, alpha, seed, level=2000.0, contrast=0.22,
               psf="airy"):
    """Return a uint16 full-CFA array carrying a known cutoff."""
    rng = np.random.default_rng(seed)
    n = SENSOR_N * FINE
    field = rng.normal(size=(n, n))
    F = np.fft.rfft2(field)
    fy = np.fft.fftfreq(n, d=1.0 / FINE)[:, None]  # sensor cyc/px
    fx = np.fft.rfftfreq(n, d=1.0 / FINE)[None, :]
    r = np.hypot(fy, fx)
    shape = np.zeros_like(r)
    nz = r > 0
    shape[nz] = r[nz] ** (-alpha / 2.0)
    if psf == "airy":
        otf = L.mtf_diffraction(r, f_c_sensor)
    elif psf == "gauss":
        # Gaussian with the same 10% MTF point as the Airy at f_c_sensor:
        # MTF_d(0.1) is reached at s ~ 0.8262 -> match exp(-2 pi^2 s_g^2 f^2).
        f10 = 0.8262 * f_c_sensor
        sg = np.sqrt(np.log(10.0) / 2.0) / (np.pi * f10)
        otf = np.exp(-2.0 * np.pi**2 * sg**2 * r**2)
    else:
        raise ValueError(psf)
    img = np.fft.irfft2(F * shape * otf, s=(n, n))
    img /= img.std()
    img = level * (1.0 + contrast * img)
    # photosite aperture: box-average FINE fine pixels, then decimate
    img = img.reshape(SENSOR_N, FINE, SENSOR_N, FINE).mean(axis=(1, 3))
    img = img + rng.normal(0.0, sigma_dn, img.shape)
    img = np.clip(img + L.BLACK_LEVEL, 1, L.WHITE_LEVEL)
    return np.rint(img).astype(np.uint16)


def run_case(f_c_true, sigma, alpha, seed, psf="airy", window="hann", lattices=L.LATTICES):
    a = make_scene(f_c_true, sigma, alpha, seed, psf=psf)
    out = {}
    for lat in lattices:
        patch = L.crop_lattice(a, lat, CENTRE, CENTRE, ROI, bounds=(SENSOR_N, SENSOR_N))
        f, p, n = L.spectrum(patch, lat, tile=TILE, window=window)
        k = L.knee(f, p, n, TILE, ROI, lat, window)
        m = L.knee_model_fit(f, p, n)
        out[lat] = {
            "reach": L.lattice_nyquist_sensor(lat),
            "cross": k,
            "fit": m,
            "floor_sigma": float(np.sqrt(max(k["floor"], 0.0))),
        }
    return out


def real_crop_control(arw_path):
    """C1b — plant a known cutoff into a *real* crop.

    A real ROI already carries real subject statistics, real noise and real
    sensor artefacts. Blurring it further with a known MTF whose cutoff is
    well below whatever the optics delivered makes the planted cutoff
    dominant, so the estimator must recover it.

    Caveat, stated because it is real: content that was already aliased in the
    original crop is attenuated here at its *folded* frequency rather than its
    true one, which the optics would not do. This is a robustness probe on
    real texture, not a substitute for the forward-modelled control above.
    """
    print("\n" + "=" * 100)
    print("C1b  POSITIVE CONTROL ON REAL TEXTURE — planted cutoff, real crop")
    print("=" * 100)
    print(f"source: {arw_path}")
    a = L.load_active(arw_path)
    print(f"{'lattice':>7} {'ROI':>13} {'base dyn':>9} {'planted':>8} {'cross':>8} "
          f"{'err%':>7} {'fit':>8} {'err%':>7} {'resid':>7} {'oob':>5}")
    errs_c, errs_m = [], []
    for lat in ("G1", "GQ"):
        reach = L.lattice_nyquist_sensor(lat)
        for (rc, cc) in ((2344, 3514), (1400, 2000), (3400, 5000)):
            base = L.crop_lattice(a, lat, rc, cc, 512)
            fb, pb, nb = L.spectrum(base, lat, tile=256, window="hann")
            base_dyn = L.knee(fb, pb, nb, 256, 512, lat)["dynamic_range"]
            for planted in (0.10, 0.14, 0.18):
                if planted > 0.9 * reach:
                    continue
                blurred = _blur_sensor_mtf(base, lat, planted)
                f, p, n = L.spectrum(blurred, lat, tile=256, window="hann")
                k = L.knee(f, p, n, 256, 512, lat)
                m = L.knee_model_fit(f, p, n)
                c = k["f_c"]
                oob = bool(m.get("above_reach"))
                mf = m["f_c"] if (m["ok"] and not oob) else None
                ec = 100 * (c / planted - 1) if c else float("nan")
                em = 100 * (mf / planted - 1) if mf else float("nan")
                errs_c.append(ec)
                if mf:
                    errs_m.append(em)
                print(f"{lat:>7} {f'{rc},{cc}':>13} {base_dyn:9.1f} "
                      f"{planted:8.3f} {fmt(c,8)} {ec:7.1f} {fmt(mf,8)} "
                      f"{em:7.1f} {m.get('resid_rms', float('nan')):7.4f} "
                      f"{str(oob):>5}")
    ec = np.array(errs_c)
    em = np.array(errs_m)
    print(f"\n   crossing  bias {np.nanmean(ec):+6.1f}%  "
          f"[{np.nanmin(ec):+.1f}, {np.nanmax(ec):+.1f}]  n={np.sum(~np.isnan(ec))}")
    print(f"   model fit bias {np.nanmean(em):+6.1f}%  "
          f"[{np.nanmin(em):+.1f}, {np.nanmax(em):+.1f}]  n={np.sum(~np.isnan(em))}")


def _blur_sensor_mtf(patch, lattice, f_c_sensor):
    """Apply a diffraction MTF of known sensor-frequency cutoff to a lattice
    patch, keeping the noise that was already there and adding none."""
    n = patch.shape[0]
    fu = np.fft.fftfreq(n)[:, None] * np.ones((1, n))
    fv = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    if lattice in ("G1", "G2"):
        fx, fy = fv / 2.0, fu / 2.0
    else:
        fx, fy = (fu - fv) / 2.0, (fu + fv) / 2.0
    r = np.hypot(fx, fy)
    mean = patch.mean()
    out = np.fft.ifft2(np.fft.fft2(patch - mean) * L.mtf_diffraction(r, f_c_sensor)).real
    # Put back a noise floor: blurring removed the original white noise too,
    # so add fresh white noise at the level the original crop carried.
    sigma = L.immerkaer_sigma(patch)
    rng = np.random.default_rng(3)
    return out + mean + rng.normal(0.0, sigma, out.shape)


def fmt(x, w=6, d=4):
    return " " * w if x is None else f"{x:{w}.{d}f}"


def main():
    quick = "--quick" in sys.argv
    real = None
    for i, a in enumerate(sys.argv):
        if a == "--real-crop" and i + 1 < len(sys.argv):
            real = sys.argv[i + 1]
    t0 = time.time()

    print("=" * 100)
    print("C1  SYNTHETIC POSITIVE CONTROL — recover a planted diffraction cutoff")
    print("=" * 100)
    print(f"scene {SENSOR_N}x{SENSOR_N} sensor px from a {SENSOR_N*FINE}^2 fine grid, "
          f"ROI {ROI} lattice px, Welch tiles {TILE}, Hann window")
    print("'reach' is the isotropic frequency limit of that lattice; a planted cutoff "
          "above it\nis unmeasurable by construction and the estimator must say so "
          "rather than invent a knee.\n")

    fcs = [0.10, 0.13, 0.169, 0.20, 0.233, 0.282, 0.30, 0.332, 0.388, 0.554]
    if quick:
        fcs = [0.13, 0.20, 0.282, 0.388]
    sigmas = [20.0] if quick else [5.0, 20.0, 60.0]

    rows = []
    for sigma in sigmas:
        print(f"\n--- planted noise sigma = {sigma:.0f} DN, alpha = 2.0 "
              f"------------------------------------")
        print(f"{'f_c true':>9} | {'lattice':>7} {'reach':>6} {'dyn':>7} "
              f"{'cross':>7} {'err%':>7} | {'fit':>7} {'err%':>7} | "
              f"{'floor sd':>8} {'flrslope':>9} {'rising':>7}")
        for fc in fcs:
            res = run_case(fc, sigma, 2.0, seed=1234)
            for lat in L.LATTICES:
                r = res[lat]
                c = r["cross"]["f_c"]
                mfit = r["fit"]["f_c"] if r["fit"]["ok"] else None
                inband = fc <= r["reach"]
                cerr = 100 * (c / fc - 1) if c else None
                merr = 100 * (mfit / fc - 1) if mfit else None
                note = "" if inband else "  (above reach)"
                sl = r["cross"]["floor_slope"]
                guard = bool(r["fit"].get("above_reach"))
                print(f"{fc:9.3f} | {lat:>7} {r['reach']:6.3f} "
                      f"{r['cross']['dynamic_range']:7.1f} "
                      f"{fmt(c)} {fmt(cerr, 7, 1)} | {fmt(mfit)} {fmt(merr, 7, 1)} | "
                      f"{r['floor_sigma']:8.2f} {fmt(sl, 9, 2)} "
                      f"{str(guard):>7}{note}")
                rows.append((sigma, fc, lat, inband, c, mfit,
                             r["cross"]["dynamic_range"], r["floor_sigma"],
                             guard, r["fit"].get("resid_rms")))

    # ---- summary: bias of each estimator, in band only -------------------
    print("\n" + "=" * 100)
    print("C1 SUMMARY")
    print("=" * 100)
    for lat in L.LATTICES:
        sel = [r for r in rows if r[2] == lat and r[3]]
        cerr = [100 * (r[4] / r[1] - 1) for r in sel if r[4]]
        merr = [100 * (r[5] / r[1] - 1) for r in sel if r[5]]
        miss = sum(1 for r in sel if r[4] is None)
        print(f"{lat}: in-band cases {len(sel)}, crossing missed {miss}")
        if cerr:
            print(f"   crossing  bias {np.mean(cerr):+6.1f}%  "
                  f"range [{min(cerr):+.1f}, {max(cerr):+.1f}]%")
        if merr:
            print(f"   model fit bias {np.mean(merr):+6.1f}%  "
                  f"range [{min(merr):+.1f}, {max(merr):+.1f}]%")

    # ---- the aliasing guard ---------------------------------------------
    print("\nOUT-OF-BAND GUARD — the model fit's own `above_reach` flag must fire "
          "when, and only\nwhen, the planted cutoff is above the lattice's reach. "
          "(The floor-slope test was\ntried first and does not work: see "
          "m5_lib.floor_flatness.)")
    tp = sum(1 for r in rows if not r[3] and r[8])
    fn = sum(1 for r in rows if not r[3] and not r[8])
    fp = sum(1 for r in rows if r[3] and r[8])
    tn = sum(1 for r in rows if r[3] and not r[8])
    print(f"   cutoff ABOVE reach: fired {tp}, missed {fn}")
    print(f"   cutoff IN   band  : fired {fp} (false alarms), silent {tn}")

    # ---- floor recovers the planted sigma (this is the H4 estimator) -----
    print("\nfloor -> sigma recovery (H4's estimator, on data where sigma is known);\n"
          "restricted to in-band cases where the floor is genuinely noise-only:")
    for sigma in sigmas:
        sel = [r for r in rows if r[0] == sigma and r[3] and not r[8]]
        if not sel:
            continue
        got = np.array([r[7] for r in sel])
        print(f"   planted {sigma:5.1f} DN  ->  recovered mean {got.mean():6.2f} DN "
              f"({100*(got.mean()/sigma-1):+.1f}%), sd {got.std():.2f}, n={len(got)}")
    sel = [r for r in rows if not r[3]]
    if sel:
        infl = np.array([r[7] / r[0] for r in sel])
        print(f"   out-of-band cases inflate the recovered sigma by "
              f"{infl.mean():.2f}x (range {infl.min():.2f}-{infl.max():.2f}x) — "
              f"aliased signal is not noise")

    # ---- crossing bias vs dynamic range ---------------------------------
    print("\nCROSSING BIAS vs SPECTRAL DYNAMIC RANGE (in-band, flat-floor cases).\n"
          "This is the correction that must be applied to the real stacks.")
    sel = [r for r in rows if r[3] and not r[8] and r[4]]
    sel.sort(key=lambda r: r[6])
    for lo, hi in ((0, 100), (100, 400), (400, 1200), (1200, 1e9)):
        s = [r for r in sel if lo <= r[6] < hi]
        if not s:
            continue
        e = [100 * (r[4] / r[1] - 1) for r in s]
        print(f"   dyn {lo:>5}-{hi if hi < 1e9 else 'inf':>5}: n={len(s):2d}  "
              f"crossing bias {np.mean(e):+6.1f}% "
              f"[{min(e):+.1f}, {max(e):+.1f}]")

    # ---- misspecification probe: a Gaussian PSF has no hard cutoff -------
    print("\nMISSPECIFICATION PROBE — Gaussian PSF (no hard cutoff at all).")
    print("The MTF is matched to the Airy's 10% point; a well-behaved estimator "
          "should\nreport something near that point and must not report a "
          "confident hard cutoff.")
    print(f"{'airy f_c':>9} {'10% pt':>8} | {'lattice':>7} {'cross':>7} {'fit':>7} "
          f"{'fit resid':>10}")
    for fc in ([0.13, 0.20] if quick else [0.13, 0.169, 0.20, 0.233]):
        res = run_case(fc, 20.0, 2.0, seed=99, psf="gauss")
        resa = run_case(fc, 20.0, 2.0, seed=99, psf="airy")
        for lat in L.LATTICES:
            r = res[lat]
            print(f"{fc:9.3f} {0.8262*fc:8.3f} | {lat:>7} "
                  f"{fmt(r['cross']['f_c'])} "
                  f"{fmt(r['fit']['f_c'] if r['fit']['ok'] else None)} "
                  f"{r['fit'].get('resid_rms', float('nan')):10.4f}  "
                  f"(airy resid {resa[lat]['fit'].get('resid_rms', float('nan')):.4f})")

    # ---- window control (Trap 2) ----------------------------------------
    print("\nTRAP 2 — windowing control. Same scene, three windows.")
    print("A boxcar's sinc sidelobes decay as 1/f and can fake a plateau.")
    print(f"{'f_c true':>9} {'lattice':>7} | " +
          " | ".join(f"{w:>16}" for w in L.WINDOWS))
    for fc in ([0.169, 0.282] if quick else [0.13, 0.169, 0.233, 0.282]):
        for lat in L.LATTICES:
            cells = []
            for win in L.WINDOWS:
                res = run_case(fc, 20.0, 2.0, seed=5, window=win, lattices=(lat,))
                r = res[lat]
                cells.append(f"{fmt(r['cross']['f_c'])} sd{r['floor_sigma']:6.1f}")
            print(f"{fc:9.3f} {lat:>7} | " + " | ".join(f"{c:>16}" for c in cells))

    if real:
        real_crop_control(real)

    print(f"\nelapsed {time.time()-t0:.1f} s")


if __name__ == "__main__":
    main()