"""M60 shared library. Read-only against the corpus; writes only under experiments/M60-bimodality.

Everything here is deliberately independent of `crates/` (which is read-only for
this milestone and is being edited concurrently by four other agents). The noise
model is transcribed from `crates/strehl-core/src/{noise.rs,profile.rs}` and is
asserted against those constants in `00-selftest.py`.
"""

import os
import glob
import numpy as np

BLACK = 512.0
WHITE = 15360.0          # usable white level, M1 (NOT the 16383 container max)
CONTAINER_MAX = 16383.0

# --- calibrated noise model, transcribed from crates/strehl-core -------------
# sigma^2(S) = g*S + (RN_e*g)^2   with S black-subtracted DN
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
READ_NOISE_E_LOW = 4.20
READ_NOISE_E_HIGH = 1.2392


def gain_dn_per_e(iso):
    return max(float(iso), BASE_ISO) / GAIN_DIVISOR


def read_noise_e(iso):
    return READ_NOISE_E_HIGH if float(iso) >= SECOND_BASE_ISO else READ_NOISE_E_LOW


def sigma_dn(signal_dn, iso):
    """Per-sample noise sd in DN at a black-subtracted signal level."""
    g = gain_dn_per_e(iso)
    s = np.maximum(signal_dn, 0.0)
    rn = read_noise_e(iso) * g
    return np.sqrt(g * s + rn * rn)


# --- corpus ------------------------------------------------------------------
CORPUS = r"D:\personal\macro"


def frames(stack):
    fs = sorted(glob.glob(os.path.join(CORPUS, stack, "*.ARW")))
    if not fs:
        raise RuntimeError("no frames for %s" % stack)
    return fs


def exif_iso(path):
    """ISO from the ARW, via rawpy's LibRaw metadata."""
    import rawpy
    with rawpy.imread(path) as r:
        return float(r.other.iso_speed)


def load_green(path, crop=None):
    """Green sublattice (G1: rows 0::2, cols 1::2 of an RGGB CFA), black-subtracted, f32.

    rule 32: `raw_image_visible` is a view into LibRaw's buffer. Allocate AND copy
    inside the `with`.
    """
    import rawpy
    with rawpy.imread(path) as r:
        g = r.raw_image_visible[0::2, 1::2].astype(np.float32)
    g = g - BLACK
    if crop is not None:
        y0, y1, x0, x1 = crop
        g = g[y0:y1, x0:x1]
    return np.ascontiguousarray(g)


def load_green_raw(path, crop=None):
    """Same but WITHOUT black subtraction, for clip / level diagnostics."""
    import rawpy
    with rawpy.imread(path) as r:
        g = r.raw_image_visible[0::2, 1::2].astype(np.float32)
    if crop is not None:
        y0, y1, x0, x1 = crop
        g = g[y0:y1, x0:x1]
    return np.ascontiguousarray(g)


# --- focus operator ----------------------------------------------------------
def sobel_mag(g):
    """Sobel gradient magnitude on a 2-D plane.

    rule 23: scipy.ndimage.sobel smooths every axis except `axis`. This function
    takes a 2-D plane ONLY and asserts it, so a cube can never be passed in.
    """
    assert g.ndim == 2, "sobel_mag takes a 2-D plane, never a cube (AGENTS rule 23)"
    from scipy.ndimage import sobel
    gx = sobel(g, axis=1, mode="reflect") / 8.0
    gy = sobel(g, axis=0, mode="reflect") / 8.0
    return np.sqrt(gx * gx + gy * gy)


def focus(g, R):
    """Box mean of Sobel magnitude at radius R. The project's focus measure family."""
    from scipy.ndimage import uniform_filter
    return uniform_filter(sobel_mag(g), 2 * R + 1, mode="reflect")


def focus_cube(G, R):
    """Focus response for a (frames, y, x) cube, one plane at a time (rule 23)."""
    return np.stack([focus(G[k], R) for k in range(G.shape[0])])


# --- Monte-Carlo noise sd of the focus response ------------------------------
def focus_sigma_mc(g, R, iso, reps, rng):
    """Predicted sampling sd of `focus(g,R)` under the calibrated noise model.

    Noise is drawn at the OBSERVED signal level, which is the only level
    available on real data. This is the same construction M32 arm N used.

    NOTE (AGENTS rule 34 / fact 599): this draws its noise from `g` and is
    therefore blind to `g` itself being wrong. It validates the operator's noise
    sensitivity, never the calibration.
    """
    acc = np.zeros(g.shape, np.float64)
    acc2 = np.zeros(g.shape, np.float64)
    sd = sigma_dn(g, iso)
    for _ in range(reps):
        f = focus(g + rng.normal(0.0, 1.0, g.shape).astype(np.float32) * sd, R)
        acc += f
        acc2 += f.astype(np.float64) ** 2
    m = acc / reps
    v = np.maximum(acc2 / reps - m * m, 0.0)
    return np.sqrt(v * reps / max(reps - 1, 1)).astype(np.float32)


# --- the bimodality statistic ------------------------------------------------
def second_peak(V):
    """Per-pixel two-peak decomposition of a through-focus cube V[k,y,x].

    Returns a dict of maps:
      k1   index of the global maximum
      k2   index of the tallest interior local maximum that is NOT in k1's own
           monotone basin (i.e. separated from k1 by a strict dip)
      kd   index of the minimum between k1 and k2
      f1,f2,fd  the response values there
      prom = f2 - fd    the smaller peak's prominence over the dip
      has2 whether any such k2 exists

    No smoothing along the frame axis: a frame-axis smoother correlates
    neighbouring samples and would make the noise propagation below wrong.
    """
    n = V.shape[0]
    k1 = np.argmax(V, axis=0)
    idx = np.arange(n)[:, None, None]
    # dip[k] = min of V over the closed interval between k and k1. Built by two
    # running minima anchored at k1: forward for k > k1, backward for k < k1.
    ge = idx >= k1[None]
    le = idx <= k1[None]
    big = np.float32(np.inf)
    fwd = np.minimum.accumulate(np.where(ge, V, big), axis=0)
    bwd = np.minimum.accumulate(np.where(le, V, big)[::-1], axis=0)[::-1]
    dip = np.where(ge, fwd, bwd).astype(np.float32)
    del fwd, bwd

    interior = np.zeros(V.shape, bool)
    interior[1:-1] = (V[1:-1] > V[:-2]) & (V[1:-1] > V[2:])
    interior &= (idx != k1[None])
    # a candidate must be strictly lower than the dip is deep, i.e. real prominence
    prom_all = np.where(interior, V - dip, -np.inf)
    k2 = np.argmax(prom_all, axis=0)
    best = np.take_along_axis(prom_all, k2[None], 0)[0]
    has2 = np.isfinite(best) & (best > 0)

    f1 = np.take_along_axis(V, k1[None], 0)[0]
    f2 = np.take_along_axis(V, k2[None], 0)[0]
    fd = np.take_along_axis(dip, k2[None], 0)[0]
    return dict(k1=k1, k2=k2, f1=f1, f2=f2, fd=fd,
                prom=np.where(has2, f2 - fd, 0.0).astype(np.float32),
                has2=has2)


def dip_index(V, k1, k2):
    """Frame index of the minimum on the closed interval between k1 and k2."""
    n = V.shape[0]
    idx = np.arange(n)[:, None, None]
    lo = np.minimum(k1, k2)[None]
    hi = np.maximum(k1, k2)[None]
    m = (idx >= lo) & (idx <= hi)
    Vm = np.where(m, V, np.float32(np.inf))
    return np.argmin(Vm, axis=0)


def prominence_z(V, S, res):
    """Prominence in units of the PREDICTED noise sd of the same difference.

    S[k,y,x] is the Monte-Carlo sd of the focus response in frame k. Frames are
    independent captures, so Var(f2 - fd) = S[k2]^2 + S[kd]^2 when k2 != kd.

    Reports the numerator and the denominator separately as well as the ratio
    (AGENTS rule 39 / discipline 338: never publish only a ratio).
    """
    kd = dip_index(V, res["k1"], res["k2"])
    s2 = np.take_along_axis(S, res["k2"][None], 0)[0]
    sd_ = np.take_along_axis(S, kd[None], 0)[0]
    denom = np.sqrt(s2 * s2 + sd_ * sd_)
    same = kd == res["k2"]
    z = np.where(same, 0.0, res["prom"] / np.maximum(denom, 1e-12))
    return z.astype(np.float32), res["prom"], denom.astype(np.float32), kd


def normalised_entropy(V, T):
    """Posterior over frame-of-best-focus, p_k ∝ exp((f_k - max f)/T), and H/log n."""
    n = V.shape[0]
    z = (V - V.max(axis=0, keepdims=True)) / np.maximum(T, 1e-12)
    np.clip(z, -700.0, 0.0, out=z)
    p = np.exp(z)
    p /= p.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -(p * np.log(np.where(p > 0, p, 1.0))).sum(axis=0)
    return (h / np.log(n)).astype(np.float32), p


if __name__ == "__main__":
    print("m60lib is a library; run the numbered scripts.")
