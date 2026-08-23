"""M55 E1 -- rho from DARK FRAMES: the independent route fact 610 never took.

PRE-REGISTERED (PR1, PR2) before this file existed.  See the M55 report.

Fact 610 says rho = 0.3094 is "fixed-pattern variance as a fraction of
single-frame noise variance", solved from an FRC reading on a lit 'flat' ROI.
At that ROI's level (median 106.3 DN, model single-frame sd 7.892 DN in the
green-quad plane) rho = 0.3094 implies

    sigma_FPN = sqrt(0.3094) * 7.892 = 4.390 DN   (variance 19.27 DN^2)

M4/M50 measured this sensor's per-pixel dark FPN at ISO 500 as 0.3943 DN
(fact 561, verified twice, two estimators, two decoders).  This script measures
it AGAIN, on the same ROI geometry M46 used, with the same green-quad plane
construction, and asks whether 4.390 DN is reachable.

ESTIMATORS (two, deliberately different from each other):
  1. cross-half covariance of two disjoint frame-half averages -- temporal noise
     contributes ZERO in expectation and the estimator is free to return a
     negative number (M50's design, fact 559).
  2. spatial variance of the full average minus sigma_temporal^2/N -- the
     bias-corrected route, which is M4's.
They use the same pixels, so they are not independent evidence of the LOADER;
that is what the pooled-RMS temporal sigma print is for (rule 32 / fact 562).

RULE 10: every sigma here is either explicitly temporal (across frames, per
pixel) or explicitly a fixed-pattern spatial sd of a TEMPORALLY AVERAGED frame,
in which the temporal component has been removed or corrected for.  They are
never compared without that correction.

RULE 32: raw_image_visible is copied INSIDE the with block.
"""
import os, sys, glob, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
os.makedirs(OUT, exist_ok=True)

BLACK = 512
G = 1.14469          # DN/e- at ISO 500, M41's constant, unchanged
RN_E = 1.47
F_SIG = 0.2762
NBIN = 64
DROP = 2             # M50's convention: first two frames are stabilisation shots

# M46 b1's ROIs, in green-quad plane coordinates, verbatim from out/b1_pair.log
ROIS = {"m46_flat": (2747, 32, 512, 512),
        "m46_detail": (1671, 1373, 512, 512)}

DARKS = {50: "122MSDCF", 100: "118MSDCF", 200: "123MSDCF", 250: "126MSDCF",
         400: "119MSDCF", 500: "125MSDCF", 640: "124MSDCF", 800: "120MSDCF",
         1000: "127MSDCF", 1600: "121MSDCF", 2000: "128MSDCF"}
ROOT = r"D:\macro-dark-frames"


def load_quad(files, roi):
    """Green quad plane (0.5*(g1+g2) - BLACK), same construction as
    m46lib.quad_green / m41lib.load_cube.  Rule 32: copy inside the with."""
    import rawpy
    x, y, w, h = roi
    out = np.empty((len(files), h, w), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2 * y:2 * (y + h):2, 2 * x + 1:2 * (x + w) + 1:2].astype(np.float32)
            g2 = v[2 * y + 1:2 * (y + h) + 1:2, 2 * x:2 * (x + w):2].astype(np.float32)
        out[i] = 0.5 * (g1 + g2) - BLACK
    return out


def hann2(n):
    w1 = np.hanning(n)
    return np.outer(w1, w1)


def ring_masks(n, nbin=NBIN):
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    out = []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        if m.sum() < 8:
            continue
        out.append((0.5 * (edges[i] + edges[i + 1]) / n, m))
    return out


def cross_ring_spectrum(a, b, rings, w, wsum2):
    """Re<A conj(B)> per ring, divided by sum(w^2) so that for two fields whose
    COMMON component is white with variance s^2 the answer is s^2 in DN^2, and
    for independent noise it is zero in expectation.  Calibrated, not asserted:
    the caller runs white_reference() and checks it."""
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * w))
    return np.array([float(np.real(np.sum(A[m] * np.conj(B[m]))) / m.sum() / wsum2)
                     for _, m in rings])


def auto_ring_spectrum(a, rings, w, wsum2):
    A = np.abs(np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))) ** 2
    return np.array([float(A[m].mean() / wsum2) for _, m in rings])


def main():
    t0 = time.time()
    n = 512
    w = hann2(n)
    wsum2 = float((w ** 2).sum())
    rings = ring_masks(n)
    ff = np.array([f for f, _ in rings])

    print("=" * 78)
    print("M55 E1 -- rho measured from DARK FRAMES (PR1, PR2)")
    print("=" * 78)

    # ---- calibration of the ring-spectrum normalisation (rule 20: it must be
    # possible for this to come out wrong, and it is checked against 1.0)
    rng = np.random.default_rng(55055)
    s_ref = 3.7
    ra = rng.standard_normal((n, n)).astype(np.float32) * s_ref
    rb = rng.standard_normal((n, n)).astype(np.float32) * s_ref
    common = rng.standard_normal((n, n)).astype(np.float32) * s_ref
    p_auto = auto_ring_spectrum(ra, rings, w, wsum2)
    p_cross_ind = cross_ring_spectrum(ra, rb, rings, w, wsum2)
    p_cross_com = cross_ring_spectrum(ra + common, rb + common, rings, w, wsum2)
    print(f"\n0. CALIBRATION of the DN^2 normalisation, white field sd {s_ref}")
    print(f"   auto spectrum   mean {p_auto.mean():9.4f} DN^2   expect {s_ref**2:.4f}"
          f"   ratio {p_auto.mean()/s_ref**2:.5f}")
    print(f"   cross, INDEPENDENT   mean {p_cross_ind.mean():+9.4f} DN^2   expect 0")
    print(f"   cross, SHARED white  mean {p_cross_com.mean():9.4f} DN^2   expect "
          f"{s_ref**2:.4f}   ratio {p_cross_com.mean()/s_ref**2:.5f}")

    res = {"calib": dict(auto=float(p_auto.mean()), cross_ind=float(p_cross_ind.mean()),
                         cross_common=float(p_cross_com.mean()), expect=s_ref ** 2),
           "freqs": ff.tolist(), "iso": {}}

    for iso in (500, 100, 2000):
        d = os.path.join(ROOT, DARKS[iso])
        files = sorted(glob.glob(os.path.join(d, "*.ARW")))[DROP:]
        print("\n" + "-" * 78)
        print(f"ISO {iso}  ({DARKS[iso]}, {len(files)} frames after dropping {DROP})")
        print("-" * 78)
        res["iso"][iso] = {}
        for rname, roi in ROIS.items():
            cube = load_quad(files, roi)
            N = cube.shape[0]
            # rule 32 loader proof: pooled-RMS temporal sigma, printed every time
            tvar = cube.var(axis=0, ddof=1)
            sig_t = float(np.sqrt(tvar.mean()))
            mean_all = cube.mean(axis=0)
            A = cube[0::2].mean(axis=0)
            B = cube[1::2].mean(axis=0)
            cov = float(np.mean((A - A.mean()) * (B - B.mean())))
            var_mean = float(np.var(mean_all))
            fpn_var_corr = var_mean - sig_t ** 2 / N
            lvl = float(np.median(mean_all))
            print(f"  {rname:<11s} level {lvl:+8.3f} DN   sigma_temporal(1 frame) "
                  f"{sig_t:7.4f} DN")
            print(f"              cross-half cov      FPN var {cov:9.5f} DN^2  "
                  f"sd {np.sqrt(max(cov,0)):7.4f} DN")
            print(f"              bias-corrected      FPN var {fpn_var_corr:9.5f} DN^2  "
                  f"sd {np.sqrt(max(fpn_var_corr,0)):7.4f} DN")
            print(f"              rho_dark = FPNvar / sigma_t^2 = "
                  f"{cov/sig_t**2:8.5f}")
            spec = cross_ring_spectrum(A, B, rings, w, wsum2)
            band = (ff >= 0.05) & (ff <= 0.49)
            sb = spec[band]
            print(f"              ring cross-spectrum over 0.05-0.49 cyc/px: "
                  f"mean {sb.mean():8.5f}  min {sb.min():8.5f}  max {sb.max():8.5f}"
                  f"  max/min {sb.max()/max(sb.min(),1e-9):6.2f}")
            i_sig = int(np.argmin(np.abs(ff - F_SIG)))
            i_45 = int(np.argmin(np.abs(ff - 0.45)))
            print(f"              at f_sig {spec[i_sig]:.5f} DN^2   at 0.45 "
                  f"{spec[i_45]:.5f} DN^2   flat-field white check "
                  f"{spec[i_45]/max(spec[i_sig],1e-12):.3f}")
            res["iso"][iso][rname] = dict(
                level=lvl, sigma_t=sig_t, n=N, fpn_var_cross=cov,
                fpn_var_biascorr=fpn_var_corr, rho_dark=cov / sig_t ** 2,
                spec=spec.tolist(), at_fsig=float(spec[i_sig]), at_45=float(spec[i_45]))
            del cube

    # -------------------------------------------------- the confrontation
    print("\n" + "=" * 78)
    print("1. PR1 VERDICT -- can rho = 0.3094 be fixed-pattern noise?")
    print("=" * 78)
    lvl_flat, lvl_det = 106.34375, 203.11111
    for nm, lvl in (("M46 flat ROI", lvl_flat), ("M46 detail ROI", lvl_det)):
        sig1 = np.sqrt(0.5 * (G * lvl + (RN_E * G) ** 2))
        need_sd = np.sqrt(0.3094) * sig1
        d500 = res["iso"][500]["m46_flat"]
        have_sd = np.sqrt(max(d500["fpn_var_cross"], 0.0))
        prnu_needed = np.sqrt(max(need_sd ** 2 - have_sd ** 2, 0.0)) / lvl * 100.0
        print(f"   {nm:<15s} level {lvl:7.2f} DN   model single-frame sd {sig1:6.3f} DN")
        print(f"       rho=0.3094 REQUIRES sigma_FPN = {need_sd:6.3f} DN "
              f"(var {need_sd**2:8.3f} DN^2)")
        print(f"       measured dark FPN (quad plane, ISO 500) = {have_sd:6.4f} DN "
              f"(var {have_sd**2:8.5f} DN^2)")
        print(f"       shortfall: {need_sd/max(have_sd,1e-9):8.2f}x in sd, "
              f"{need_sd**2/max(have_sd**2,1e-12):9.1f}x in VARIANCE")
        print(f"       a multiplicative PRNU term would have to be "
              f"{prnu_needed:6.3f}% of signal to close it")
        res.setdefault("confront", {})[nm] = dict(
            level=lvl, sigma1=float(sig1), need_sd=float(need_sd),
            have_sd=float(have_sd), prnu_pct_needed=float(prnu_needed))

    with open(os.path.join(OUT, "e1_dark_rho.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/e1_dark_rho.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
