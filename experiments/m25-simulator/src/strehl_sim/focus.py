"""A Python port of the `m9-support` measurement harness.

Why a port and not a call: `m9-support` is a Rust binary that links
`crates/strehl-core`, and this milestone must not build in that tree.  A port
is therefore unavoidable, and **a port is a liability until it is shown to
reproduce the original's committed numbers on the original's data**
(discipline 15/34).  `01-port-check.py` does exactly that against
`experiments/m9-support/data/analysis-109MSDCF-coupled.txt` and
`sensitivity-109MSDCF.csv` before any simulated frame is touched.

Everything here is a transliteration of:
  * `crates/strehl-core/src/boxfilter.rs` -- box mean, window clamped to the
    plane, divided by the clamped count;
  * `crates/strehl-core/src/noise.rs`     -- `variance`, `green_luma_sigma`;
  * `crates/strehl-core/src/stack.rs`     -- `speckle_fraction`, truncated
    (not replicated) 3x3 neighbourhood, upper median at `n/2`;
  * `experiments/m9-support/src/measures.rs` -- the 4x4 crossed design;
  * `experiments/m9-support/src/main.rs`  -- `merge_cell`, `mean_gradient`,
    `sweep`, `sensitivity`.

Failure direction (rule 18): every ratio here is `sigma_stacked /
sigma_single`, so **lower is better** and a broken port that smooths its
output would look like a *win*.  `mean_gradient` is the paired detail metric
and travels with it (rule 9): higher is better, and it is what catches a
merge that bought quietness by blurring.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SIGMA_EPS = 1e-3
DEFAULT_WIDTHS = [1, 3, 5, 7, 9, 13, 17, 21, 25, 33, 41, 49, 65, 81, 97, 129,
                  161, 193, 257]


# ------------------------------------------------------------- noise model

@dataclass(frozen=True)
class NoiseModel:
    gain_dn_per_e: float
    read_noise_e: float

    @classmethod
    def for_iso(cls, iso: float, divisor: float = 436.8) -> "NoiseModel":
        g = iso / divisor
        rn = 1.47 if iso >= 400 else 4.20
        return cls(g, rn)

    def variance(self, signal: np.ndarray) -> np.ndarray:
        floor = (self.read_noise_e * self.gain_dn_per_e) ** 2
        return self.gain_dn_per_e * np.maximum(signal, 0.0) + floor

    def green_luma_sigma(self, luma: np.ndarray) -> np.ndarray:
        v = self.variance(luma)
        return np.sqrt(0.25 * (v + v))


# ------------------------------------------------------------ box filter

def box_mean(img: np.ndarray, radius: int) -> np.ndarray:
    """`(2r+1)^2` mean with the window clamped to the plane and divided by the
    clamped count -- `boxfilter.rs`'s policy exactly, borders included."""
    if radius == 0:
        return img.astype(np.float64, copy=True)
    a = img.astype(np.float64, copy=False)
    h, w = a.shape
    cs = np.zeros((h, w + 1), np.float64)
    np.cumsum(a, axis=1, out=cs[:, 1:])
    x = np.arange(w)
    lo = np.maximum(x - radius, 0)
    hi = np.minimum(x + radius + 1, w)
    hsum = cs[:, hi] - cs[:, lo]
    hcnt = (hi - lo).astype(np.float64)

    cs2 = np.zeros((h + 1, w), np.float64)
    np.cumsum(hsum, axis=0, out=cs2[1:, :])
    y = np.arange(h)
    lo2 = np.maximum(y - radius, 0)
    hi2 = np.minimum(y + radius + 1, h)
    vsum = cs2[hi2, :] - cs2[lo2, :]
    vcnt = (hi2 - lo2).astype(np.float64)
    return vsum / (vcnt[:, None] * hcnt[None, :])


def _clamped(img: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """`img` shifted so that output[y, x] == img[clamp(y+dy), clamp(x+dx)]."""
    h, w = img.shape
    ys = np.clip(np.arange(h) + dy, 0, h - 1)
    xs = np.clip(np.arange(w) + dx, 0, w - 1)
    return img[ys][:, xs]


def modified_laplacian(luma: np.ndarray, step: int) -> np.ndarray:
    c = 2.0 * luma
    hx = np.abs(c - _clamped(luma, -step, 0) - _clamped(luma, step, 0))
    hy = np.abs(c - _clamped(luma, 0, -step) - _clamped(luma, 0, step))
    return hx + hy


def tenengrad_magnitude(luma: np.ndarray) -> np.ndarray:
    gx = (_clamped(luma, 1, -1) + 2.0 * _clamped(luma, 1, 0)
          + _clamped(luma, 1, 1) - _clamped(luma, -1, -1)
          - 2.0 * _clamped(luma, -1, 0) - _clamped(luma, -1, 1))
    gy = (_clamped(luma, -1, 1) + 2.0 * _clamped(luma, 0, 1)
          + _clamped(luma, 1, 1) - _clamped(luma, -1, -1)
          - 2.0 * _clamped(luma, 0, -1) - _clamped(luma, 1, -1))
    return 0.125 * np.sqrt(gx * gx + gy * gy)


# --------------------------------------------------------------- measures

@dataclass(frozen=True)
class Measure:
    name: str
    family: str
    role: str
    support_radius: int
    kind: tuple

    @property
    def support_px(self) -> int:
        return 2 * self.support_radius + 1

    def raw_response(self, luma: np.ndarray) -> np.ndarray:
        k = self.kind
        if k[0] == "ring":
            _, inner, outer = k
            return np.abs(box_mean(luma, inner) - box_mean(luma, outer))
        if k[0] == "tenengrad":
            _, window = k
            m = tenengrad_magnitude(luma)
            return m if window == 0 else box_mean(m, window)
        if k[0] == "sml":
            _, window = k
            m = modified_laplacian(luma, 1)
            return m if window == 0 else box_mean(m, window)
        if k[0] == "dsml":
            return modified_laplacian(luma, k[1])
        if k[0] == "ringsm":
            _, inner, outer, extra = k
            r = np.abs(box_mean(luma, inner) - box_mean(luma, outer))
            return r if extra == 0 else box_mean(r, extra)
        raise AssertionError(f"unknown kind {k!r}")

    def compute(self, luma: np.ndarray, noise: NoiseModel) -> np.ndarray:
        out = self.raw_response(luma)
        return out / np.maximum(noise.green_luma_sigma(luma), SIGMA_EPS)


def design(include_controls: bool = True) -> list[Measure]:
    v: list[Measure] = []
    for inner, outer in [(0, 1), (1, 3), (2, 6), (4, 12)]:
        v.append(Measure(f"ring-{inner}-{outer}", "ring", "treatment", outer,
                         ("ring", inner, outer)))
    for window in [0, 2, 5, 11]:
        v.append(Measure(f"tenengrad-w{window}", "tenengrad", "treatment",
                         1 + window, ("tenengrad", window)))
        v.append(Measure(f"sml-w{window}", "sml", "treatment", 1 + window,
                         ("sml", window)))
    for step in [1, 3, 6, 12]:
        v.append(Measure(f"dsml-s{step}", "dsml", "treatment", step,
                         ("dsml", step)))
    if include_controls:
        for declared in [1, 3, 6, 12, 24]:
            v.append(Measure(f"nullctl-d{declared}", "ring", "null", 3,
                             ("ring", 1, 3)))
        for extra in [0, 4, 10, 20, 38]:
            v.append(Measure(f"posctl-e{extra}", "ring", "positive", 3 + extra,
                             ("ringsm", 1, 3, extra)))
    return v


def max_support(ms: list[Measure]) -> int:
    return max(m.support_radius for m in ms)


TREATMENTS = [m for m in design(False)]


# ------------------------------------------------------------ statistics

def mean_and_sigma(v: np.ndarray) -> tuple[float, float]:
    """Population statistics (`/n`), f64 accumulation -- `tile.rs`."""
    a = np.asarray(v, np.float64).ravel()
    m = a.mean()
    return float(m), float(np.sqrt(((a - m) ** 2).mean()))


def mean_gradient(v: np.ndarray) -> float:
    """Mean central-difference gradient magnitude over the interior."""
    h, w = v.shape
    if w < 3 or h < 3:
        return 0.0
    a = np.asarray(v, np.float64)
    dx = 0.5 * (a[1:-1, 2:] - a[1:-1, :-2])
    dy = 0.5 * (a[2:, 1:-1] - a[:-2, 1:-1])
    return float(np.sqrt(dx * dx + dy * dy).mean())


def speckle_fraction(index: np.ndarray, tolerance: int = 2) -> float:
    """`stack.rs::speckle_fraction`, including its truncated border window and
    its upper median at `n/2` of the surviving taps."""
    h, w = index.shape
    a = index.astype(np.int32)
    big = np.iinfo(np.int32).max
    stack = np.full((9, h, w), big, np.int32)
    valid = np.zeros((h, w), np.int32)
    n = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ys = np.arange(h) + dy
            xs = np.arange(w) + dx
            oy = (ys >= 0) & (ys < h)
            ox = (xs >= 0) & (xs < w)
            m = oy[:, None] & ox[None, :]
            src = a[np.clip(ys, 0, h - 1)][:, np.clip(xs, 0, w - 1)]
            stack[n] = np.where(m, src, big)
            valid += m.astype(np.int32)
            n += 1
    stack.sort(axis=0)
    take = valid // 2
    med = np.take_along_axis(stack, take[None, ...], axis=0)[0]
    return float((np.abs(a - med) > tolerance).mean())


# ----------------------------------------------------------------- merge

def merge_cell(focus: np.ndarray, value: np.ndarray, single: np.ndarray,
               radius: int, margin: int) -> dict:
    """`main.rs::merge_cell`.

    `focus` is (K, TH, TW) on the padded tile; `value` is (K, RH, RW) on the
    ROI; `single` is (RH, RW).
    """
    K = focus.shape[0]
    rh, rw = value.shape[1], value.shape[2]
    reg = np.empty((K, rh, rw), np.float64)
    for k in range(K):
        f = box_mean(focus[k], radius) if radius else focus[k]
        reg[k] = f[margin:margin + rh, margin:margin + rw]
    idx = np.argmax(reg, axis=0).astype(np.int32)     # first max wins
    out = np.take_along_axis(value, idx[None, ...], axis=0)[0]

    smean, ssig = mean_and_sigma(out)
    _, single_sigma = mean_and_sigma(single)
    return {
        "stacked_mean": smean,
        "stacked_sigma": ssig,
        "single_sigma": single_sigma,
        "ratio": ssig / single_sigma,
        "distinct_winners": int(np.unique(idx).size),
        "speckle": speckle_fraction(idx, 2),
        "grad_stacked": mean_gradient(out),
        "grad_single": mean_gradient(single),
        "index": idx,
    }


def sweep_measure(m: Measure, luma: np.ndarray, value: np.ndarray,
                  single: np.ndarray, noise: NoiseModel, margin: int,
                  widths=None) -> list[dict]:
    widths = DEFAULT_WIDTHS if widths is None else widths
    focus = np.stack([m.compute(luma[k], noise) for k in range(luma.shape[0])])
    rows = []
    for w in widths:
        c = merge_cell(focus, value, single, (w - 1) // 2, margin)
        c["width"] = w
        c["measure"] = m.name
        rows.append(c)
    return rows


# ------------------------------------------------- centre-tap fraction phi

def phi_for(m: Measure, luma: np.ndarray, noise: NoiseModel, reach: int,
            delta: float = 8.0) -> tuple[float, float, float, int]:
    """`main.rs::sensitivity`, exactly: bump a sparse lattice by `delta`,
    accumulate `|r_bumped - r_base|` into a `(2*reach+1)^2` kernel, and report
    `phi = |dr(0)| / sum |dr(d)|`.

    `phi` is a property of the operator **and** of the data it is measured on,
    because the noise normaliser and the absolute values are non-linear.  It is
    therefore re-measured on every stack, never carried across.
    """
    K, h, w = luma.shape
    spacing = 4 * reach + 2
    ys, xs = [], []
    y = spacing
    while y + spacing < h:
        ys.append(y)
        y += spacing
    x = spacing
    while x + spacing < w:
        xs.append(x)
        x += spacing
    assert ys and xs, "tile too small for the sensitivity lattice"

    n = 2 * reach + 1
    kernel = np.zeros((n, n), np.float64)
    samples = 0
    for k in range(K):
        base = m.compute(luma[k], noise)
        pert = luma[k].copy()
        for yy in ys:
            for xx in xs:
                pert[yy, xx] += delta
        bump = m.compute(pert, noise)
        d = np.abs(bump - base)
        for yy in ys:
            for xx in xs:
                kernel += d[yy - reach:yy + reach + 1,
                            xx - reach:xx + reach + 1]
                samples += 1
    scale = samples * delta
    kernel /= scale
    centre = float(kernel[reach, reach])
    total = float(kernel.sum())
    taps = int((kernel > 1e-6).sum())
    return (centre, total, centre / total if total > 0 else np.nan, taps)
