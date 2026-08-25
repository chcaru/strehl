"""O2 -- the elector, the oracle, and the noise model, all measured not assumed.

THE ELECTOR, reproduced from crates/strehl-core/src/focus.rs:1-8

    g(p)     = sqrt(Gx^2 + Gy^2)          3x3 Sobel, scaled by 1/8
    focus(p) = box_mean_13(g)(p) / max(sigma_L(p), EPS)

THE ORACLE

    O(p) = box27( |grad I|^2 )(p) - box27( E|grad n|^2 )(p)

For zero-mean noise independent of the scene, E|grad(s+n)|^2 = |grad s|^2 +
E|grad n|^2 exactly -- the cross term vanishes. So the noise contribution to the
ENERGY is additive and exactly removable, which is what the rectified MAGNITUDE
the product elects on does not permit. This is the entire structural difference
between the two rules and it is why the oracle is not the same measure renamed.

The Sobel noise kernel, derived here rather than quoted. With taps

    Wx = [[-1,0,1],[-2,0,2],[-1,0,1]]/8      Wy = Wx^T

and independent per-pixel variance v, E[Gx^2] = sum_d Wx(d)^2 v(p+d), likewise
Gy, so

    E|grad n|^2 (p) = sum_d K(d) v(p+d),  K = [[2,4,2],[4,0,4],[2,4,2]] / 64

which sums to 24/64 = 0.375. `test_sobel_noise_kernel` checks that number by
Monte Carlo against the closed form rather than trusting the algebra.

THE NOISE MODEL is measured from this capture, not read from noise.rs. G1 and G2
are two independent samples of the same scene, so var(G1-G2)/2 is a photon
transfer curve, free and in-band. It is fitted on low-gradient pixels so that
scene structure between the two green sites does not inflate it.
"""

from __future__ import annotations

import numpy as np

SOBEL_X = np.array([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]]) / 8.0
SOBEL_Y = SOBEL_X.T.copy()
NOISE_K = np.array([[2.0, 4.0, 2.0], [4.0, 0.0, 4.0], [2.0, 4.0, 2.0]]) / 64.0
BOX_R = 13
EPS = 1e-6


def conv3(img: np.ndarray, k: np.ndarray) -> np.ndarray:
    """Valid-shrink 3x3 correlation. Output is (H-2, W-2)."""
    h, w = img.shape
    out = np.zeros((h - 2, w - 2), dtype=np.float64)
    for dy in range(3):
        for dx in range(3):
            c = k[dy, dx]
            if c != 0.0:
                out += c * img[dy:dy + h - 2, dx:dx + w - 2]
    return out


def sobel_mag2(img: np.ndarray):
    """Returns (|grad|, |grad|^2) on the valid interior, product tap scaling."""
    gx = conv3(img, SOBEL_X)
    gy = conv3(img, SOBEL_Y)
    e = gx * gx + gy * gy
    return np.sqrt(e), e


def box_mean(img: np.ndarray, r: int = BOX_R) -> np.ndarray:
    """Mean over a (2r+1)^2 window, valid only. Integral image, float64."""
    h, w = img.shape
    s = np.zeros((h + 1, w + 1), dtype=np.float64)
    np.cumsum(np.cumsum(img, axis=0), axis=1, out=s[1:, 1:])
    n = 2 * r + 1
    oh, ow = h - 2 * r, w - 2 * r
    tot = s[n:, n:] - s[:oh, n:] - s[n:, :ow] + s[:oh, :ow]
    return tot / float(n * n)


class Noise:
    """Affine photon transfer curve: var(signal) = gain * signal + floor, in DN^2."""

    def __init__(self, gain: float, floor: float, black: float):
        self.gain = float(gain)
        self.floor = float(floor)
        self.black = float(black)

    def var(self, dn: np.ndarray) -> np.ndarray:
        s = np.maximum(np.asarray(dn, dtype=np.float64) - self.black, 0.0)
        return self.gain * s + self.floor

    def sigma(self, dn: np.ndarray) -> np.ndarray:
        return np.sqrt(self.var(dn))

    def __repr__(self):
        return f"Noise(gain={self.gain:.6f}, floor={self.floor:.3f}, black={self.black:.1f})"


def fit_noise(g1: np.ndarray, g2: np.ndarray, black: float, nbin: int = 24,
              grad_pct: float = 40.0):
    """Photon transfer curve from the two green sites of the same frames.

    var(G1 - G2) = var(G1) + var(G2) = 2v when the two sites see the same scene.
    They do not exactly -- they sit one pixel apart -- so the difference also
    carries scene gradient. Restricting the fit to the lowest `grad_pct` of
    pixels by local gradient keeps that term small; `sens_*` in o5 varies the
    result to show the conclusion does not rest on it.
    """
    g1 = g1.astype(np.float64)
    g2 = g2.astype(np.float64)
    lvl = 0.5 * (g1 + g2)
    d = g1 - g2
    gy = np.abs(np.diff(lvl, axis=0))[:, :-1]
    gx = np.abs(np.diff(lvl, axis=1))[:-1, :]
    gm = gx + gy
    lvl = lvl[:-1, :-1]
    d = d[:-1, :-1]
    keep = gm <= np.percentile(gm, grad_pct)
    lvl, d = lvl[keep], d[keep]
    s = lvl - black
    edges = np.linspace(np.percentile(s, 1.0), np.percentile(s, 99.0), nbin + 1)
    xs, ys, ns = [], [], []
    for i in range(nbin):
        m = (s >= edges[i]) & (s < edges[i + 1])
        if m.sum() < 500:
            continue
        xs.append(float(s[m].mean()))
        ys.append(float(d[m].var(ddof=1) * 0.5))
        ns.append(int(m.sum()))
    xs, ys = np.asarray(xs), np.asarray(ys)
    A = np.vstack([xs, np.ones_like(xs)]).T
    gain, floor = np.linalg.lstsq(A, ys, rcond=None)[0]
    pred = A @ np.array([gain, floor])
    ss = 1.0 - np.sum((ys - pred) ** 2) / max(np.sum((ys - ys.mean()) ** 2), 1e-30)
    return Noise(gain, max(floor, 1e-6), black), dict(
        x=xs.tolist(), y=ys.tolist(), n=ns, r2=float(ss))


def elector_score(img: np.ndarray, noise: Noise) -> np.ndarray:
    """focus.rs: box27(|grad|) / max(sigma_L, EPS). Valid interior only."""
    mag, _ = sobel_mag2(img)
    num = box_mean(mag)
    sig = np.maximum(noise.sigma(img[1:-1, 1:-1]), EPS)
    den = box_mean(sig)
    return num / np.maximum(den, EPS)


def oracle_score(img: np.ndarray, noise: Noise) -> np.ndarray:
    """box27(|grad|^2) minus the exactly-computable noise energy."""
    _, e = sobel_mag2(img)
    v = noise.var(img)
    nz = conv3(v, NOISE_K)
    return box_mean(e) - box_mean(nz)


def hann2(n: int) -> np.ndarray:
    w = np.hanning(n + 2)[1:-1]
    return np.outer(w, w)


def recover_sigma(a: np.ndarray, b: np.ndarray) -> float:
    """Gaussian sigma separating two images, from the windowed spectral ratio.

    The window is not cosmetic. o3's first version of this fit used a bare FFT
    of an unwindowed crop and read sigma LOW by 6.9-10.3 %, worsening with
    sigma, which failed control K2. Blurring mixes in content from outside the
    crop and an unwindowed non-periodic crop leaks spectrally; both bias the
    ratio. With the Hann window and an interior-only crop the same fit recovers
    0.25 / 0.50 / 1.00 / 1.50 px to within 0.07 % (o3b TEST 2), and o3c control
    C3 shows it still MEASURES rather than echoes: handed a sigma=1.0 blur
    against a sigma=0.5 reference it returns 0.8655 for a true sqrt(0.75) =
    0.8660, where an echoing estimator would have returned 1.0000.
    """
    n = a.shape[0]
    w = hann2(n)
    fa = np.fft.fft2((a - a.mean()) * w)
    fb = np.fft.fft2((b - b.mean()) * w)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    q = fy * fy + fx * fx
    m = (q > 1e-4) & (q < 0.02)
    ratio = np.abs(fb[m]) ** 2 / np.maximum(np.abs(fa[m]) ** 2, 1e-12)
    y = -np.log(np.maximum(ratio, 1e-12))
    x = 4.0 * (np.pi ** 2) * q[m]
    return float(np.sqrt(max(np.sum(x * y) / np.sum(x * x), 0.0)))


def test_sobel_noise_kernel(seed: int = 7, n: int = 900, reps: int = 240) -> dict:
    """Monte Carlo the closed form. The algebra is only a claim until it is run."""
    rng = np.random.default_rng(seed)
    v = 3.75
    acc = 0.0
    for _ in range(reps):
        z = rng.normal(0.0, np.sqrt(v), size=(n, n))
        _, e = sobel_mag2(z)
        acc += float(e.mean())
    got = acc / reps
    want = 0.375 * v
    return dict(measured=got, closed_form=want, ratio=got / want)
