"""BUILD-VEILMAP core: drift model + per-block through-focus response.

The response is exactly V-VEILCLAW's: mean |laplacian| of the CFA green
sub-lattice `raw_image_visible[0::2, 1::2]`, no demosaic, no tone curve, no
black subtraction (a laplacian kills the constant anyway).  If this measured
anything else the potency test against the claw would be meaningless.

What is added is block *tracking*.  There is ~13% magnification breathing
across a deep bracket; within one frame the registration shift differs by more
than 150 px between regions and grows with radius, which is the signature of a
scale term rather than rigid motion.  A fixed pixel box therefore sweeps
through scene content, and content passing through a box produces two sharpness
peaks with no occlusion anywhere.  So every frame gets a direct three-parameter
similarity fit against the master,

    q = a_k * p + t_k          (p in master/2 px, q in green-lattice px)

and every block is gathered at its own a_k.  Nothing is composed frame to frame
(AGENTS rule 6): each fit is direct against one fixed reference.

Both arms are computed in the same decode pass and stored side by side --
tracked and untracked -- because the difference between them *is* the drift
control, and re-deriving it from two separate runs would let decode-order or
parameter drift in.
"""
import pathlib

import numpy as np
import rawpy

RAWROOT = pathlib.Path(r"D:\personal\macro")        # read-only, never write
MASTERS = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")

# ---------------------------------------------------------------------------
# response
# ---------------------------------------------------------------------------


def green_lattice(path):
    """One CFA green sub-lattice, float32, no demosaic. V-VEILCLAW's slice."""
    with rawpy.imread(str(path)) as r:
        return np.array(r.raw_image_visible[0::2, 1::2], dtype=np.float32,
                        copy=True)


def frames(subject):
    return sorted((RAWROOT / subject).glob("*.ARW"))


def load_ref(subject, lat_shape):
    """Master green at green-lattice scale, cropped to the lattice grid.

    Masters are 7032 or 7040 px wide against a 7028 px visible raw, so
    master/2 overhangs the lattice by 1..3 px.  Left uncropped that overhang
    can change a pyramid level's block count -- 3520//8 = 440 against
    3514//8 = 439 -- and the FFT ladder then fails outright on exactly the
    subjects with the wider master.  Cropping at the origin is right because
    master and raw share their top-left corner, and the few px of residual
    origin uncertainty are absorbed by the model's free translation.
    """
    import tifffile
    m = tifffile.imread(str(MASTERS / f"{subject}.tiff"))
    assert m.dtype == np.uint16, f"master is {m.dtype}; corpus requires uint16"
    ref = block_mean_down(m[:, :, 1].astype(np.float32), 2)
    return np.ascontiguousarray(ref[:lat_shape[0], :lat_shape[1]])


def abs_lap(g):
    """|laplacian| of the green lattice, same 5-point stencil as probe.py.

    Returned at the same shape as `g` with a 1 px zero border, so a summed-area
    table over it indexes in lattice coordinates directly.
    """
    out = np.zeros_like(g)
    out[1:-1, 1:-1] = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1]
                             - g[1:-1, :-2] - g[1:-1, 2:])
    return out


def sat(a):
    """Summed-area table, float64, shape (h+1, w+1)."""
    s = np.zeros((a.shape[0] + 1, a.shape[1] + 1), np.float64)
    np.cumsum(np.cumsum(a, axis=0, dtype=np.float64), axis=1, out=s[1:, 1:])
    return s


def rect_mean(s, y0, y1, x0, x1):
    """Mean over [y0:y1, x0:x1] from a summed-area table. Vectorised."""
    tot = (s[y1, x1] - s[y0, x1] - s[y1, x0] + s[y0, x0])
    n = np.maximum((y1 - y0) * (x1 - x0), 1)
    return tot / n


# ---------------------------------------------------------------------------
# drift: direct similarity fit of each frame against one fixed reference
# ---------------------------------------------------------------------------


def block_mean_down(a, d):
    if d == 1:
        return a.astype(np.float32)
    h = (a.shape[0] // d) * d
    w = (a.shape[1] // d) * d
    return a[:h, :w].reshape(h // d, d, w // d, d).mean(axis=(1, 3)).astype(
        np.float32)


def prep(a):
    """Remove DC and window, so correlation is driven by structure."""
    a = a - a.mean()
    hy = np.hanning(a.shape[0]).astype(np.float32)
    hx = np.hanning(a.shape[1]).astype(np.float32)
    return (a * hy[:, None] * hx[None, :]).astype(np.float32)


def _scale_about_centre(img, a):
    """Scale `img` about its own centre by `a`. BORDER_REFLECT, not zeros: a
    zero border changes the image's energy with `a` and tilts the ladder."""
    import cv2
    h, w = img.shape
    cy, cx = (h - 1) * 0.5, (w - 1) * 0.5
    m = np.array([[a, 0.0, (1.0 - a) * cx], [0.0, a, (1.0 - a) * cy]],
                 np.float32)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REFLECT)


def _parab(ym1, y0, yp1):
    """Sub-sample offset of the vertex of the parabola through three points."""
    den = (ym1 - 2.0 * y0 + yp1)
    if abs(den) < 1e-12:
        return 0.0
    return float(np.clip(0.5 * (ym1 - yp1) / den, -1.0, 1.0))


def _xcorr_peak(FA, ea, B, FB=None):
    """Peak NCC of A (given as rfft2 `FA`, energy `ea`) against B.

    Returns (score, dy, dx) where a point at coordinate p in A lands at p + (dy,
    dx) in B.  Sign convention is fixed by the plant in commission.py, not by
    this docstring.  Normalising by both energies matters: warping the
    reference by a < 1 leaves a zero border and drops its energy, so an
    unnormalised score would slope across the scale ladder and bias the fit.
    """
    if FB is None:
        FB = np.fft.rfft2(B)
    c = np.fft.irfft2(FA * np.conj(FB), s=B.shape)
    k = int(np.argmax(c))
    uy, ux = np.unravel_index(k, c.shape)
    peak = float(c[uy, ux])
    # sub-sample refinement on the correlation surface
    sy = _parab(float(c[(uy - 1) % c.shape[0], ux]), peak,
                float(c[(uy + 1) % c.shape[0], ux]))
    sx = _parab(float(c[uy, (ux - 1) % c.shape[1]]), peak,
                float(c[uy, (ux + 1) % c.shape[1]]))
    fy = uy + sy
    fx = ux + sx
    if fy > c.shape[0] / 2:
        fy -= c.shape[0]
    if fx > c.shape[1] / 2:
        fx -= c.shape[1]
    nb = float(np.sqrt((B * B).sum()))
    return peak / max(ea * nb, 1e-9), -fy, -fx


class DriftFitter:
    """Direct (a, ty, tx) fit of a frame's green lattice against a reference.

    `ref` is the reference image at green-lattice scale (master green channel
    downsampled by 2).  Coarse scale ladder at `dc`, fine ladder at `df`.
    """

    def __init__(self, ref, dc=8, df=4, alo=0.80, ahi=1.12, astep=0.002):
        self.dc, self.df = dc, df
        # NOTE: window AFTER the warp, not before. Warping an already-windowed
        # reference shrinks its aperture while the target keeps a full one, and
        # a scale ladder judged through two different apertures is biased.
        self.refc = block_mean_down(ref, dc)
        self.reff = block_mean_down(ref, df)
        self.grid = np.arange(alo, ahi + 1e-9, astep)
        self._cache = {}

    def _coarse_fft(self, i):
        f = self._cache.get(i)
        if f is None:
            w = prep(_scale_about_centre(self.refc, float(self.grid[i])))
            f = (np.fft.rfft2(w).astype(np.complex64),
                 float(np.sqrt((w * w).sum())))
            self._cache[i] = f
        return f

    def fit(self, g, seed=None, span=12):
        """Return dict(a, ty, tx, ncc). g is a full-res green lattice."""
        gc = prep(block_mean_down(g, self.dc))
        gf = prep(block_mean_down(g, self.df))
        Fgc = np.fft.rfft2(gc)
        Fgf = np.fft.rfft2(gf)
        if seed is None:
            idxs = range(len(self.grid))
        else:
            j = int(np.argmin(np.abs(self.grid - seed)))
            idxs = range(max(0, j - span), min(len(self.grid), j + span + 1))
        best = (-1e9, None)
        for i in idxs:
            F, e = self._coarse_fft(i)
            s, _, _ = _xcorr_peak(F, e, gc, Fgc)
            if s > best[0]:
                best = (s, i)
        i0 = best[1]
        # fine ladder around the coarse winner, at the finer pyramid level
        a0 = float(self.grid[i0])
        step = float(self.grid[1] - self.grid[0])
        fine = np.linspace(a0 - step, a0 + step, 17)
        vals, shifts = [], []
        for a in fine:
            w = prep(_scale_about_centre(self.reff, float(a)))
            s, dy, dx = _xcorr_peak(np.fft.rfft2(w).astype(np.complex64),
                                    float(np.sqrt((w * w).sum())), gf, Fgf)
            vals.append(s)
            shifts.append((dy, dx))
        j = int(np.argmax(vals))
        a = float(fine[j])
        if 0 < j < len(fine) - 1:
            a += _parab(vals[j - 1], vals[j], vals[j + 1]) * (fine[1] - fine[0])
        dy, dx = shifts[j]
        # The shifts are measured at level df, on an image scaled about its own
        # centre. Level-df index u sits at green-lattice coordinate
        # p = df*u + (df-1)/2, so the scale centre lifts to (df*h - 1)/2.
        h, w_ = self.reff.shape
        cy, cx = (self.df * h - 1) * 0.5, (self.df * w_ - 1) * 0.5
        ty = (1.0 - a) * cy + dy * self.df
        tx = (1.0 - a) * cx + dx * self.df
        return dict(a=a, ty=float(ty), tx=float(tx), ncc=float(vals[j]))


def map_point(y, x, a, ty, tx):
    """Reference (master/2) coordinate -> green-lattice coordinate of frame k."""
    return a * y + ty, a * x + tx


# ---------------------------------------------------------------------------
# drift, second stage: per-frame similarity fitted to LOCAL correspondences
# ---------------------------------------------------------------------------
#
# The whole-frame scale ladder above is honest in the middle of a bracket and
# unreliable at its ends, where most of the frame is defocused and the ladder
# is judging a sharp master against a blurred frame -- the same blur-mismatch
# that makes AGENTS rule 6's per-span scale response peak at 0.659 and never
# reach 1.0. Measured on bee-3-cpl it placed held-out patches to 30 px at f186
# and 334 px at f000.
#
# A local translation estimate does not have that failure: blur is symmetric,
# so it costs precision, not accuracy. So the shipped model is a similarity
# least-squares fit to a set of local NCC correspondences against the master,
# with outlier rejection, seeded outward from mid-bracket. Each frame is still
# fitted DIRECTLY to the master; only the search window is seeded from a
# neighbour, so nothing is composed (AGENTS rule 6).


def _n01(z):
    lo, hi = np.percentile(z, [0.5, 99.5])
    return np.clip((z - lo) / max(hi - lo, 1e-6), 0.0, 1.0).astype(np.float32)


def pick_windows(ref, n, half, margin=260, ny=9, nx=13, minsep=240):
    """`n` high-variance, well-spread reference windows, as (y, x) centres."""
    h, w = ref.shape
    cand = []
    for y in np.linspace(margin + half, h - margin - half, ny).astype(int):
        for x in np.linspace(margin + half, w - margin - half, nx).astype(int):
            p = ref[y - half:y + half, x - half:x + half]
            cand.append((float(p.std()), int(y), int(x)))
    cand.sort(key=lambda t: -t[0])
    out = []
    for _, y, x in cand:
        if all(max(abs(y - b), abs(x - c)) > minsep for b, c in out):
            out.append((y, x))
        if len(out) >= n:
            break
    return out


class TrackFitter:
    """Per-frame similarity from local NCC correspondences against `ref`.

    The gate that matters is NOT the NCC, and it is not peak distinctiveness
    either (measured on bee-3-cpl f150: good matches median 0.033, wrong
    matches median 0.010 -- overlapping, useless). The master is all-in-focus
    and a frame is defocused nearly everywhere, so most templates are matched
    against featureless blur, and two smooth gradients correlate at NCC 0.99.

    What does separate them is whether the patch the matcher landed on has
    detail comparable to the template's: `lapratio`, the mean |laplacian| of
    the contrast-normalised matched patch over the same for the template. On
    that same frame every correct match sat in 0.34-0.95 and every blank-paper
    match -- master smooth, frame shot noise -- sat at 1.0-39.6. The admitted
    band is [0.30, 2.00]: below that the frame patch is far softer than the
    sharpest available rendition of the same content, so there is nothing to
    lock onto; above it the "structure" is noise, and 2.0 is already generous
    because the merge is known to render detail at ~0.50x a resolving frame's
    amplitude (ORCH-veiling 59.3), which is the largest honest excess.

    This is V-VEILCLAW/drift.py's stated precondition -- "windows where that
    window's content is at or near its own focus peak, so NCC has something to
    lock onto" -- enforced by the instrument instead of chosen by hand.

    The absolute band does NOT transfer across subjects, and this was measured,
    not guessed: on leaf-2-cpl at f045 the whole-frame seed is already accurate
    to a median 1.9 lattice px -- i.e. essentially every window is a correct
    match -- and yet the ratios run 1.9 to 10.4 and the band rejects 17 of 20.
    The reason is that the master is a merge of many frames and has had its
    noise averaged down, while a single raw frame has not; on a smooth subject
    the normalised frame patch's laplacian is dominated by shot noise and the
    ratio is large everywhere. So when the absolute band admits nothing, the
    gate falls back to a WITHIN-FRAME quantile: keep the windows with the
    lowest ratios in that frame, which are the ones whose content is nearest
    its own focus, and let RANSAC discard the rest. The absolute band is tried
    first, so subjects where it works are unaffected.
    """

    def __init__(self, ref, half=56, pad=48, sigmas=(3.0,), minncc=0.35,
                 lap_lo=0.30, lap_hi=2.00, lap_q=0.5):
        import cv2
        self.ref = ref
        self.half, self.pad, self.minncc = half, pad, minncc
        self.lap_lo, self.lap_hi, self.lap_q = lap_lo, lap_hi, lap_q
        self.sigmas = tuple(sigmas)
        self._cv2 = cv2
        self._tpl = {}
        self.last_gate = "abs"

    def _template(self, y, x):
        t = self._tpl.get((y, x))
        if t is None:
            h = self.half
            base = _n01(self.ref[y - h:y + h, x - h:x + h])
            lap = float(np.abs(self._cv2.Laplacian(base, self._cv2.CV_32F)
                               ).mean())
            t = ([self._cv2.GaussianBlur(base, (0, 0), s) for s in self.sigmas],
                 max(lap, 1e-6))
            self._tpl[(y, x)] = t
        return t

    def correspond(self, gl, wins, seed):
        """Locate each window in `gl` near the seed model. -> list of rows."""
        cv2 = self._cv2
        h, p = self.half, self.pad
        rows = []
        for (y, x) in wins:
            py, px = map_point(y, x, *seed)
            sy0 = int(max(0, round(py - h - p)))
            sx0 = int(max(0, round(px - h - p)))
            sy1 = int(min(gl.shape[0], round(py + h + p)))
            sx1 = int(min(gl.shape[1], round(px + h + p)))
            if sy1 - sy0 < 2 * h + 3 or sx1 - sx0 < 2 * h + 3:
                continue
            raw = _n01(gl[sy0:sy1, sx0:sx1])
            tpls, tlap = self._template(y, x)
            best = None
            for t, s in zip(tpls, self.sigmas):
                r = cv2.matchTemplate(cv2.GaussianBlur(raw, (0, 0), s), t,
                                      cv2.TM_CCOEFF_NORMED)
                _, mx, _, loc = cv2.minMaxLoc(r)
                if best is None or mx > best[0]:
                    best = (float(mx), loc, r.shape)
            mx, loc, rs = best
            if mx < self.minncc:
                continue
            qy, qx = sy0 + loc[1] + h, sx0 + loc[0] + h
            yy = int(np.clip(qy, h, gl.shape[0] - h))
            xx = int(np.clip(qx, h, gl.shape[1] - h))
            flap = float(np.abs(cv2.Laplacian(
                _n01(gl[yy - h:yy + h, xx - h:xx + h]), cv2.CV_32F)).mean())
            ratio = flap / tlap
            edge = (loc[1] <= 0 or loc[0] <= 0
                    or loc[1] >= rs[0] - 1 or loc[0] >= rs[1] - 1)
            rows.append((y, x, qy, qx, float(mx), bool(edge), float(ratio)))
        keep = [r for r in rows if self.lap_lo <= r[6] <= self.lap_hi]
        self.last_gate = "abs"
        if len(keep) < 5 and len(rows) >= 5:
            hi = float(np.quantile([r[6] for r in rows], self.lap_q))
            keep = [r for r in rows if r[6] <= hi]
            self.last_gate = f"q{self.lap_q:g}<={hi:.2f}"
        return keep

    @staticmethod
    def solve(rows, thresh=8.0, trials=400, alo=0.75, ahi=1.15, seed_rng=12345):
        """RANSAC (a, ty, tx) over correspondences, refined on the inliers.

        A trimmed least squares is not enough here. Opening the intermediate on
        bee-3-cpl f150 showed roughly half the windows locking onto the wrong
        structure at NCC up to 0.99 -- confident, and 100+ lattice px away --
        while the windows that do agree agree to under 12 px. At that outlier
        rate an initial least squares is already dragged off before any MAD
        threshold is computed, so the fit has to start from a minimal sample.
        """
        rows = [r for r in rows if not r[5]]
        if len(rows) < 4:
            return None
        p = np.array([[r[0], r[1]] for r in rows], np.float64)
        q = np.array([[r[2], r[3]] for r in rows], np.float64)
        n = len(rows)
        rng = np.random.default_rng(seed_rng)
        best = (-1, None)
        for _ in range(trials):
            i, j = rng.integers(0, n, 2)
            dp = p[i] - p[j]
            if float(np.hypot(*dp)) < 400.0:
                continue
            a = float((q[i] - q[j]) @ dp) / float(dp @ dp)
            if not (alo <= a <= ahi):
                continue
            t = q[i] - a * p[i]
            res = np.hypot(*(q - (a * p + t)).T)
            k = int((res <= thresh).sum())
            if k > best[0]:
                best = (k, (a, t[0], t[1]))
        if best[1] is None:
            return None
        a, ty, tx = best[1]
        keep = np.hypot(*(q - (a * p + np.array([ty, tx]))).T) <= thresh
        for _ in range(3):
            if keep.sum() < 3:
                break
            pp, qq = p[keep], q[keep]
            pm, qm = pp.mean(0), qq.mean(0)
            den = float(((pp - pm) ** 2).sum())
            a = float(((pp - pm) * (qq - qm)).sum()) / max(den, 1e-12)
            ty, tx = qm[0] - a * pm[0], qm[1] - a * pm[1]
            nk = np.hypot(*(q - (a * p + np.array([ty, tx]))).T) <= thresh
            if nk.sum() < 3 or (nk == keep).all():
                break
            keep = nk
        res = np.hypot(*(q - (a * p + np.array([ty, tx]))).T)
        return dict(a=float(a), ty=float(ty), tx=float(tx),
                    n_in=int(keep.sum()), n_all=n,
                    rms=float(np.sqrt((res[keep] ** 2).mean())),
                    med=float(np.median(res[keep])))
