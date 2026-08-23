"""M41 step 3 -- POSITIVE CONTROL: planted synthetic, latent known.

Section 8.4 named experiments/m25-simulator as the planted control.  The M41
brief forbids touching that tree (a live agent owns it), so a self-contained
plant is built here instead -- deviation D3 in PREREGISTRATION.md.

This is deliberately an INVERSE CRIME: the frames are generated with exactly the
OTF model the arms invert.  That is the point.  It is a control on the HARNESS,
not on realism.  If arm D cannot beat arm A where the forward model is true by
construction, the implementation is broken and no real-data reading from it
means anything -- PREREGISTRATION.md section 2 calls that outcome VOID.

Rule 13: the plant is first checked to be able to express the FAILURE as well as
the success -- the sigma sweep must contain a sigma at which D loses to A.
"""
import os, sys, glob, json
import numpy as np
import rawpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L
from scipy.ndimage import sobel

OUT = L.OUT
N = 512


def latent():
    """A real macro texture, used as the known latent image.  Taken from the
    sharpest frame of 119MSDCF's detail ROI.  It is NOT assumed to be sharp --
    it is simply DEFINED as the ground truth that the simulated frames are
    generated from, so its own residual blur is irrelevant to the control."""
    with open(os.path.join(OUT, "rois_b.json")) as fh:
        rois = json.load(fh)
    info = rois["119MSDCF"]
    files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
    x, y, w, h = info["detail_roi"]
    x, y = max(32, x), max(32, y)
    best, bs = None, -1.0
    for f in files[::3]:
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2*y:2*(y+N):2, 2*x+1:2*(x+N)+1:2].astype(np.float32)
            g2 = v[2*y+1:2*(y+N)+1:2, 2*x:2*(x+N):2].astype(np.float32)
        q = 0.5 * (g1 + g2) - L.BLACK
        gx = sobel(q, axis=1); gy = sobel(q, axis=0)
        sc = float((gx*gx + gy*gy).mean())
        if sc > bs:
            bs, best = sc, q
    return best


def blur(img, r, use_diff=True):
    n = img.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    FX = np.broadcast_to(fx, (n, n // 2 + 1)).copy()
    FY = np.broadcast_to(fy, (n, n // 2 + 1)).copy()
    H = L.otf_defocus(r, FX, FY)
    if use_diff:
        H = H * L.otf_diffraction(FX, FY)
    return np.fft.irfft2(np.fft.rfft2(img) * H, s=(n, n)).astype(np.float32)


def grad_corr(a, b):
    ax, ay = sobel(a, axis=1), sobel(a, axis=0)
    bx, by = sobel(b, axis=1), sobel(b, axis=0)
    u = np.concatenate([ax.ravel(), ay.ravel()])
    v = np.concatenate([bx.ravel(), by.ravel()])
    u = u - u.mean(); v = v - v.mean()
    return float((u @ v) / max(np.sqrt((u @ u) * (v @ v)), 1e-30))


def psnr(a, b, peak):
    return float(10.0 * np.log10(peak * peak / max(float(((a - b) ** 2).mean()), 1e-12)))


def main():
    Lt = latent()
    Lt = Lt - Lt.min()
    peak = float(np.percentile(Lt, 99.9))
    log = open(os.path.join(OUT, "a3_planted.log"), "w", encoding="utf-8")

    def p(m):
        print(m); log.write(m + "\n"); log.flush()

    p("M41 POSITIVE CONTROL -- planted synthetic, forward model exactly true.")
    p(f"latent {Lt.shape}, mean {Lt.mean():.1f} DN, p99.9 {peak:.1f} DN")
    nfr, s_true = 22, 0.45
    g, rn_e = 0.11447, 4.20                 # 119MSDCF's calibration (ISO 50)
    kstar = nfr // 2
    res = {}
    # Rule 13: sweep sigma so that the plant CAN express D losing to A.
    for scale in (0.25, 1.0, 4.0, 16.0):
        rng = np.random.default_rng(7)
        cube = np.empty((nfr, N, N), np.float32)
        for k in range(nfr):
            b = blur(Lt, abs(k - kstar) * s_true, True)
            sig = np.sqrt(scale * 0.5 * (g * np.maximum(b, 0) + (rn_e * g) ** 2))
            cube[k] = b + rng.normal(0, 1, b.shape).astype(np.float32) * sig
        sig_med = float(np.median(np.sqrt(scale * 0.5 *
                        (g * np.maximum(cube[kstar], 0) + (rn_e * g) ** 2))))
        _, coarse, reg = L.focus_fields(cube, g * scale, rn_e * np.sqrt(scale))
        arms = {
            "A": L.arm_A(cube, coarse, reg)[0],
            "B": L.arm_B(cube, L.focus_fields(cube, g * scale, rn_e * np.sqrt(scale))[0])[0],
            "C": L.arm_C(cube),
            "D": L.arm_wiener(cube, reg, g * scale, rn_e * np.sqrt(scale), s_true, True, True),
            "D'": L.arm_wiener(cube, reg, g * scale, rn_e * np.sqrt(scale), s_true, False, True),
            "E": L.arm_wiener(cube, reg, g * scale, rn_e * np.sqrt(scale), s_true, True, False),
        }
        p(f"\n--- noise x{scale:g} (median modelled sigma {sig_med:.2f} DN) ---")
        row = {}
        for k, v in arms.items():
            c = v[32:-32, 32:-32]; t = Lt[32:-32, 32:-32]
            row[k] = dict(psnr=psnr(c, t, peak), gc=grad_corr(c, t))
            p(f"    {k:2s}: PSNR {row[k]['psnr']:7.3f} dB   grad-corr {row[k]['gc']:.4f}")
        d_minus_a = row["D"]["psnr"] - row["A"]["psnr"]
        p(f"    D - A = {d_minus_a:+.3f} dB PSNR, "
          f"{row['D']['gc'] - row['A']['gc']:+.4f} grad-corr")
        res[str(scale)] = row
    # the sigma at which D stops beating A is the proof the control has power
    wins = [(k, v["D"]["psnr"] - v["A"]["psnr"]) for k, v in res.items()]
    p("\nRULE 13 -- can the plant express the failure? D-A across the sweep: "
      + ", ".join(f"x{k}: {d:+.2f} dB" for k, d in wins))
    with open(os.path.join(OUT, "a3_results.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    log.close()


if __name__ == "__main__":
    main()
