"""M6 — what the 0.6-1.3 px alignment residual is, and how big the halo is.

This module is the estimator. Everything else in the directory is a driver.

Two independent jobs live here because they share one input, the per-frame
similarity fits that `m3-drift --m6` writes:

1. **Cause discrimination** (SYNTHESIS §10 q6). Regress the per-tile alignment
   residual against a per-tile depth proxy under a two-way fixed-effects model
   whose only free parameter is the *interaction* between a tile's own depth and
   where in the stack the aligned frame pair sits. That interaction is zero
   under depth-dependent magnification and positive under blur-induced
   correlation bias. See `s1_gamma`.

2. **Halo arithmetic** (SYNTHESIS §10 q10). Pure geometry on the fitted
   similarities: the source-frame bounding box of every output tile over every
   frame of the stack. See `halo_table`.

Labelling discipline (AGENTS.md rule 8) is enforced by the callers; nothing here
prints a number without one.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Constants. Fixed in source, identical for the synthetic controls, the null
# and all three real stacks. Nothing is tuned per stack.
# ---------------------------------------------------------------------------

#: Tile edge used by the aligner's fine stage, in plane px.
TILE_PX = 128
#: Canonical grid shape written by `m3-drift --m6`.
GRID_NX, GRID_NY = 12, 8
#: Sensor plane geometry (active area halved). MEASURED, M1.
PLANE_W, PLANE_H = 3516, 2344
#: Plane px -> sensor px.
SENSOR_SCALE = 2.0
#: Minimum focus-profile contrast for a tile to carry a usable depth label.
#: A tile whose sharpest and blurriest frames differ by less than this fraction
#: has no depth information; fact 20 warns that such tiles exist.
PEAKINESS_MIN = 0.10
#: Permutation draws for the plain null.
N_PERM = 999
#: RNG seed. Fixed so every number in the report is reproducible.
SEED = 20260822


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _read_csv(path: str) -> dict[str, list[str]]:
    with open(path, newline="") as f:
        r = csv.reader(f)
        header = next(r)
        cols: dict[str, list[str]] = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def _f(col: list[str]) -> np.ndarray:
    return np.array([float(v) if v != "" else np.nan for v in col], dtype=np.float64)


def _i(col: list[str]) -> np.ndarray:
    return np.array([int(v) for v in col], dtype=np.int64)


@dataclass
class Tiles:
    """Per-tile alignment records for one case, one row per (pair, tile)."""

    case: np.ndarray
    ref: np.ndarray
    mov: np.ndarray
    delta: np.ndarray
    tile_id: np.ndarray
    tx: np.ndarray
    ty: np.ndarray
    ux: np.ndarray
    uy: np.ndarray
    dx: np.ndarray
    dy: np.ndarray
    ex: np.ndarray
    ey: np.ndarray
    peak: np.ndarray
    contrast: np.ndarray
    status: np.ndarray
    kept: np.ndarray

    @property
    def res(self) -> np.ndarray:
        return np.hypot(self.ex, self.ey)

    @property
    def ok(self) -> np.ndarray:
        return self.status == "ok"

    def select(self, mask: np.ndarray) -> "Tiles":
        return Tiles(**{k: getattr(self, k)[mask] for k in self.__dataclass_fields__})


def load_tiles(prefix: str, case: str | None = None) -> Tiles:
    c = _read_csv(f"{prefix}-tiles.csv")
    t = Tiles(
        case=np.array(c["case"]),
        ref=_i(c["ref"]),
        mov=_i(c["mov"]),
        delta=_i(c["delta"]),
        tile_id=_i(c["tile_id"]),
        tx=_i(c["tx"]),
        ty=_i(c["ty"]),
        ux=_f(c["ux"]),
        uy=_f(c["uy"]),
        dx=_f(c["dx"]),
        dy=_f(c["dy"]),
        ex=_f(c["ex"]),
        ey=_f(c["ey"]),
        peak=_f(c["peak"]),
        contrast=_f(c["contrast"]),
        status=np.array(c["status"]),
        kept=_i(c["kept"]).astype(bool),
    )
    return t.select(t.case == case) if case is not None else t


@dataclass
class Fits:
    case: np.ndarray
    grid: np.ndarray
    ref: np.ndarray
    mov: np.ndarray
    delta: np.ndarray
    g: np.ndarray
    rot: np.ndarray
    ax: np.ndarray
    ay: np.ndarray
    rms: np.ndarray
    used: np.ndarray
    plane_w: np.ndarray
    plane_h: np.ndarray

    def select(self, mask: np.ndarray) -> "Fits":
        return Fits(**{k: getattr(self, k)[mask] for k in self.__dataclass_fields__})


def load_fits(prefix: str, case: str | None = None, grid: str = "m3") -> Fits:
    c = _read_csv(f"{prefix}-fits.csv")
    f = Fits(
        case=np.array(c["case"]),
        grid=np.array(c["grid"]),
        ref=_i(c["ref"]),
        mov=_i(c["mov"]),
        delta=_i(c["delta"]),
        g=_f(c["g"]),
        rot=_f(c["rot"]),
        ax=_f(c["ax"]),
        ay=_f(c["ay"]),
        rms=_f(c["rms"]),
        used=_i(c["used"]),
        plane_w=_i(c["plane_w"]),
        plane_h=_i(c["plane_h"]),
    )
    m = f.grid == grid
    if case is not None:
        m &= f.case == case
    return f.select(m)


def load_focus(prefix: str, case: str | None = None):
    c = _read_csv(f"{prefix}-focus.csv")
    caseA = np.array(c["case"])
    m = np.ones(len(caseA), bool) if case is None else caseA == case
    return {
        "tile_id": _i(c["tile_id"])[m],
        "frame": _i(c["frame"])[m],
        "tx": _i(c["tx"])[m],
        "ty": _i(c["ty"])[m],
        "ring": _f(c["ring"])[m],
        "hp": _f(c["hp"])[m],
    }


def load_truth(prefix: str, case: str) -> dict[int, float]:
    if not os.path.exists(f"{prefix}-truth.csv"):
        return {}
    c = _read_csv(f"{prefix}-truth.csv")
    out = {}
    for cs, tid, d in zip(c["case"], c["tile_id"], c["depth_truth"]):
        if cs == case:
            out[int(tid)] = float(d)
    return out


# ---------------------------------------------------------------------------
# Depth proxy: the per-tile winner index
# ---------------------------------------------------------------------------


def winner_index(focus: dict, key: str = "ring") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-tile focus peak, sub-frame refined.

    Returns `(w, peakiness, n_frames)`:
      * `w[i]` — the frame index at which tile `i` is sharpest, parabolically
        refined between the two neighbours of the argmax. Continuous, so it can
        be used as a regressor.
      * `peakiness[i]` — `(max - min) / max` of the tile's focus profile. A tile
        with a flat profile has no depth information at all, which is exactly
        what fact 20 says about parts of this scene. Tiles below
        `PEAKINESS_MIN` are labelled but flagged.
    """
    ids = np.unique(focus["tile_id"])
    n = int(focus["frame"].max()) + 1
    w = np.full(ids.max() + 1, np.nan)
    pk = np.full(ids.max() + 1, np.nan)
    prof = np.full((ids.max() + 1, n), np.nan)
    for i in ids:
        m = focus["tile_id"] == i
        prof[i, focus["frame"][m]] = focus[key][m]
        v = prof[i]
        if not np.all(np.isfinite(v)):
            continue
        k = int(np.argmax(v))
        pk[i] = (v[k] - v.min()) / v[k] if v[k] > 0 else 0.0
        if 0 < k < len(v) - 1:
            a, b, c = v[k - 1], v[k], v[k + 1]
            den = a - 2 * b + c
            off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
            off = float(np.clip(off, -1.0, 1.0))
        else:
            off = 0.0
        w[i] = k + off
    return w, pk, prof


def winner_from_index_map(tiff_path: str, tx: np.ndarray, ty: np.ndarray, tile: int = TILE_PX):
    """Per-tile median of the CLI's winner-index map.

    The map is `strehl stack --index-map`: literal per-pixel argmax frame index
    at plane resolution, from an **unaligned** stack. Drift therefore smears it
    radially by up to ~39 plane px at the corner, so it is a cross-check on the
    registered per-tile focus profile, not a replacement for it.
    """
    import tifffile

    img = tifffile.imread(tiff_path)
    out = np.full(len(tx), np.nan)
    for i, (x, y) in enumerate(zip(tx, ty)):
        patch = img[y : y + tile, x : x + tile]
        if patch.size:
            out[i] = float(np.median(patch))
    return out


# ---------------------------------------------------------------------------
# Geometry: the scale centre, and the radial/tangential split
# ---------------------------------------------------------------------------


def scale_centre(fits: Fits) -> tuple[float, float]:
    """Offset of the scale centre from the plane centre, in plane px.

    A constant offset `o` shows up as translation `-g*o`, so regress the fitted
    translation against the fitted scale over the direct fits (M3 §5).
    """
    m = fits.ref == 0
    g, ax, ay = fits.g[m], fits.ax[m], fits.ay[m]
    den = float(np.sum(g * g))
    if den <= 0:
        return 0.0, 0.0
    return -float(np.sum(ax * g)) / den, -float(np.sum(ay * g)) / den


def radial_tangential(ex, ey, ux, uy, ox=0.0, oy=0.0):
    """Split residual vectors into radial and tangential components about `o`."""
    rx, ry = ux - ox, uy - oy
    r = np.hypot(rx, ry)
    r = np.where(r > 1e-6, r, np.nan)
    e_rad = (ex * rx + ey * ry) / r
    e_tan = (-ex * ry + ey * rx) / r
    return e_rad, e_tan, r


# ---------------------------------------------------------------------------
# S1 — the discriminating statistic
# ---------------------------------------------------------------------------


@dataclass
class GammaResult:
    gamma: float
    se_cluster: float
    n: int
    n_tiles: int
    n_pairs: int
    p_perm: float
    perm_mean: float
    perm_sd: float
    p_torus: float
    torus_sd: float
    r2: float
    ident: float
    extra: dict

    @property
    def identified(self) -> bool:
        """Is the depth regressor separable from the frame-pair fixed effect?"""
        return self.ident >= 0.02

    @property
    def fires(self) -> bool:
        """Positive, identified, and beyond the stricter of the two nulls."""
        return self.identified and self.gamma > 0 and self.p_torus <= 0.05


def _demean(v, ti, pi, cnt_t, cnt_p, iters=200, tol=1e-11):
    """Two-way within transformation by alternating projections.

    Absorbing the tile and pair fixed effects by explicit dummy columns would
    make the design 96 + 400 columns wide and put a 38000 x 500 least squares
    inside a 999-draw permutation loop. Frisch-Waugh-Lovell says the coefficient
    on the regressor of interest is unchanged if both sides are first projected
    off the dummies, and alternating group-mean removal does that in O(n) per
    sweep. `_selftest.py` checks the two agree to 1e-9 on a small case.
    """
    v = np.asarray(v, dtype=np.float64).copy()
    for _ in range(iters):
        tm = np.bincount(ti, v, minlength=len(cnt_t)) / cnt_t
        v -= tm[ti]
        pm = np.bincount(pi, v, minlength=len(cnt_p)) / cnt_p
        v -= pm[pi]
        if np.max(np.abs(pm)) < tol:
            break
    return v


class TwoWay:
    """A two-way fixed-effects design that can be re-fitted cheaply.

    The tile and pair labels are fixed; only the regressor of interest changes
    between permutation draws, so the group indices and counts are built once.
    """

    def __init__(self, tile, pair):
        self.tiles = np.unique(tile)
        self.pairs = np.unique(pair)
        self.ti = np.searchsorted(self.tiles, tile)
        self.pi = np.searchsorted(self.pairs, pair)
        self.cnt_t = np.bincount(self.ti, minlength=len(self.tiles)).astype(float)
        self.cnt_p = np.bincount(self.pi, minlength=len(self.pairs)).astype(float)
        self.n_absorbed = len(self.tiles) + len(self.pairs) - 1

    def demean(self, v):
        return _demean(v, self.ti, self.pi, self.cnt_t, self.cnt_p)

    def fit(self, yd, Xd):
        beta, *_ = np.linalg.lstsq(Xd, yd, rcond=None)
        return beta, yd - Xd @ beta

    def cluster_se(self, Xd, resid, idx):
        """Standard error of coefficient `idx`, clustered on tile.

        Residuals from one tile are correlated across every frame pair it
        appears in; a plain OLS standard error would understate the uncertainty
        by roughly sqrt(n_pairs). The finite-sample correction counts the
        absorbed fixed effects as estimated parameters.
        """
        XtX_inv = np.linalg.pinv(Xd.T @ Xd)
        k = Xd.shape[1]
        meat = np.zeros((k, k))
        for c in range(len(self.tiles)):
            m = self.ti == c
            if not m.any():
                continue
            u = Xd[m].T @ resid[m]
            meat += np.outer(u, u)
        ng = len(self.tiles)
        n = len(resid)
        kk = self.n_absorbed + k
        corr = (ng / max(ng - 1, 1)) * ((n - 1) / max(n - kk, 1))
        V = XtX_inv @ meat @ XtX_inv * corr
        return float(np.sqrt(max(V[idx, idx], 0.0)))


def _twoway_fe(y, tile, pair, x_cols):
    """Convenience wrapper: fit `y ~ tile FE + pair FE + x_cols`.

    Returns `(coefs, resid, demeaned_design, index_of_first_x)`. The index is 0
    because the fixed effects are absorbed rather than represented as columns.
    """
    tw = TwoWay(tile, pair)
    yd = tw.demean(y)
    Xd = np.column_stack([tw.demean(x_cols[:, j]) for j in range(x_cols.shape[1])])
    beta, resid = tw.fit(yd, Xd)
    return beta, resid, Xd, 0, tw



def s1_gamma(
    t: Tiles,
    w: np.ndarray,
    controls: tuple[str, ...] = (),
    rng_seed: int = SEED,
    n_perm: int = N_PERM,
    grid_nx: int = GRID_NX,
    grid_ny: int = GRID_NY,
    keep_tiles: np.ndarray | None = None,
) -> GammaResult:
    """The discriminating statistic, stated before it was computed.

    Model, fitted on every successfully correlated tile of every frame pair:

        res[i, j] = alpha[i] + beta[j] + gamma * |c[j] - w[i]| + eps

    where `alpha[i]` is a tile fixed effect (absorbing texture, contrast and
    field position), `beta[j]` is a frame-pair fixed effect (absorbing the
    baseline, the drift rate, and any global "this pair aligns badly" effect),
    `c[j]` is the midpoint of the aligned frame pair and `w[i]` is the tile's own
    best-focus frame.

    `gamma` is therefore identified **only** from the interaction between a
    tile's own depth and where in the stack the pair sits.

      * **Blur-induced correlation bias (cause b) predicts gamma > 0**: a tile
        aligns best when the two frames being matched straddle its own focus.
      * **Depth-dependent magnification (cause a) predicts gamma ~ 0**: which
        pair a tile fits worst has nothing to do with the tile's own sharpness,
        only with geometry, which `beta[j]` already absorbs.

    Two nulls, both on the real residuals:
      * `p_perm` — plain permutation of the depth labels across tiles.
      * `p_torus` — cyclic shift of the depth labels over the 12x8 tile grid,
        which preserves the *spatial autocorrelation* of the depth field while
        destroying its alignment with the residual field. This is the stricter
        null: it cannot be passed by any smooth spatial confounder.

    **Identification.** `|c[j] - w[i]|` is only distinguishable from the pair
    fixed effect through the spread of `w` across tiles. If every tile has the
    same winner, `|c - w|` is a pure function of `j` and the pair dummies absorb
    it entirely, leaving gamma unidentified and numerically wild. `ident` in the
    result is the fraction of the regressor's variance that survives the two-way
    demeaning; below about 0.02 the number should not be read at all. The
    planted-cause controls exercise exactly this failure.
    """
    m = t.ok & np.isfinite(t.res) & np.isfinite(w[t.tile_id])
    if keep_tiles is not None:
        m &= keep_tiles[t.tile_id]
    tt = t.select(m)
    wi = w[tt.tile_id]
    c = 0.5 * (tt.ref + tt.mov)
    y = tt.res
    d = np.abs(c - wi)

    cols = [d]
    names = ["defocus"]
    for name in controls:
        if name == "logcontrast":
            cols.append(np.log10(np.maximum(tt.contrast, 1e-3)))
        elif name == "peak":
            cols.append(tt.peak)
        elif name == "radius":
            cols.append(np.hypot(tt.ux, tt.uy) / 1000.0)
        else:
            raise ValueError(name)
        names.append(name)
    X = np.column_stack(cols)

    pair = tt.ref * 10000 + tt.mov
    tw = TwoWay(tt.tile_id, pair)
    yd = tw.demean(y)
    Xd = np.column_stack([tw.demean(X[:, j]) for j in range(X.shape[1])])
    beta, resid = tw.fit(yd, Xd)
    gamma = float(beta[0])
    se = tw.cluster_se(Xd, resid, 0)
    ss_tot = float(np.sum(yd**2))
    r2 = 1.0 - float(np.sum(resid**2)) / ss_tot if ss_tot > 0 else np.nan
    # Residual scale after the fixed effects, for reading gamma as a fraction of
    # what is actually left to explain.
    sd_within = float(np.std(yd))

    def refit(dcol):
        Xp = Xd.copy()
        Xp[:, 0] = tw.demean(dcol)
        bp, _ = tw.fit(yd, Xp)
        return float(bp[0])

    ids = np.unique(tt.tile_id)
    rng = np.random.default_rng(rng_seed)
    perm = np.empty(n_perm)
    wp = w.copy()
    for b in range(n_perm):
        vals = w[ids].copy()
        rng.shuffle(vals)
        wp[ids] = vals
        perm[b] = refit(np.abs(c - wp[tt.tile_id]))

    torus = []
    for sx in range(grid_nx):
        for sy in range(grid_ny):
            if sx == 0 and sy == 0:
                continue
            ws = np.full_like(w, np.nan)
            for tid in range(len(w)):
                gx, gy = tid % grid_nx, tid // grid_nx
                if gy >= grid_ny:
                    continue
                src = ((gy + sy) % grid_ny) * grid_nx + ((gx + sx) % grid_nx)
                ws[tid] = w[src]
            if not np.all(np.isfinite(ws[ids])):
                continue
            torus.append(refit(np.abs(c - ws[tt.tile_id])))
    torus = np.array(torus)

    p_perm = float((np.sum(perm >= gamma) + 1) / (n_perm + 1))
    p_torus = float((np.sum(torus >= gamma) + 1) / (len(torus) + 1)) if len(torus) else np.nan

    return GammaResult(
        gamma=gamma,
        se_cluster=se,
        n=len(y),
        n_tiles=len(ids),
        n_pairs=len(np.unique(pair)),
        p_perm=p_perm,
        perm_mean=float(perm.mean()),
        perm_sd=float(perm.std(ddof=1)),
        p_torus=p_torus,
        torus_sd=float(torus.std(ddof=1)) if len(torus) > 1 else np.nan,
        r2=r2,
        ident=float(np.var(Xd[:, 0]) / max(np.var(X[:, 0]), 1e-30)),
        extra={
            "coef_names": names,
            "coefs": [float(b) for b in beta],
            "perm": perm,
            "torus": torus,
            "sd_within": sd_within,
            "mean_res": float(np.mean(y)),
            "d_range": (float(d.min()), float(d.max())),
            "d_sd_within": float(np.std(Xd[:, 0])),
        },
    )


# ---------------------------------------------------------------------------
# S2 — is the residual a depth-organised *scale* anomaly?
# ---------------------------------------------------------------------------


def _torus_labels(w: np.ndarray, grid_nx: int = GRID_NX, grid_ny: int = GRID_NY):
    """All non-identity cyclic shifts of a per-tile field over the tile grid.

    A shifted copy has the same marginal distribution *and* the same spatial
    autocorrelation as the real depth field, but no causal coupling to the
    residual field. That is the placebo SYNTHESIS §5 item 6 asks for: it cannot
    be passed by "both fields happen to be smooth in x".
    """
    out = []
    for sx in range(grid_nx):
        for sy in range(grid_ny):
            if sx == 0 and sy == 0:
                continue
            ws = np.full_like(w, np.nan)
            for tid in range(len(w)):
                gx, gy = tid % grid_nx, tid // grid_nx
                if gy >= grid_ny:
                    continue
                src = ((gy + sy) % grid_ny) * grid_nx + ((gx + sx) % grid_nx)
                ws[tid] = w[src]
            out.append(ws)
    return out


def s2_scale_anomaly(t: Tiles, w: np.ndarray, ox: float, oy: float, delta: int | None = None,
                     keep_tiles: np.ndarray | None = None):
    """Per-tile radial scale anomaly, and how it is organised by depth.

    Under depth-dependent magnification the residual is *purely radial* about the
    scale centre and equals `dg[i] * |u[i] - o|`, so `dg[i] = e_rad / |u - o|` is
    an estimate of how much tile `i`'s own depth scales differently from the
    global fit. That anomaly must be a **monotone** function of depth, because
    magnification is monotone in object distance.

    Under blur bias there is no reason for `dg` to be monotone in depth; the
    residual is instead organised by distance from the tile's own best focus,
    which is **V-shaped** about the middle of the frame pair range.

    Returns a dict with the Spearman correlation of both shapes.
    """
    m = t.ok & np.isfinite(t.res)
    if delta is not None:
        m &= t.delta == delta
    if keep_tiles is not None:
        m &= keep_tiles[t.tile_id]
    tt = t.select(m)
    e_rad, e_tan, r = radial_tangential(tt.ex, tt.ey, tt.ux, tt.uy, ox, oy)
    dg = e_rad / r
    # De-mean per pair, so a global scale error in any one pair cannot masquerade
    # as a depth effect.
    pair = tt.ref * 10000 + tt.mov
    for p in np.unique(pair):
        s = pair == p
        dg[s] -= np.nanmean(dg[s])
    ids = np.unique(tt.tile_id)
    mean_dg = np.array([np.nanmean(dg[tt.tile_id == i]) for i in ids])
    mean_res = np.array([np.nanmean(tt.res[tt.tile_id == i]) for i in ids])
    wi = w[ids]
    good = np.isfinite(wi) & np.isfinite(mean_dg)
    mid = 0.5 * (np.nanmin(0.5 * (tt.ref + tt.mov)) + np.nanmax(0.5 * (tt.ref + tt.mov)))
    rho_dg = _spearman(mean_dg[good], wi[good])
    rho_res_absw = _spearman(mean_res[good], np.abs(wi[good] - mid))
    # Torus null on the same statistics: same marginal, same spatial
    # autocorrelation, no causal coupling.
    tor_dg, tor_v = [], []
    for ws in _torus_labels(w):
        wsi = ws[ids][good]
        if not np.all(np.isfinite(wsi)):
            continue
        tor_dg.append(_spearman(mean_dg[good], wsi))
        tor_v.append(_spearman(mean_res[good], np.abs(wsi - mid)))
    tor_dg = np.array([v for v in tor_dg if np.isfinite(v)])
    tor_v = np.array([v for v in tor_v if np.isfinite(v)])
    p_dg = (
        float((np.sum(np.abs(tor_dg) >= abs(rho_dg)) + 1) / (len(tor_dg) + 1))
        if len(tor_dg)
        else np.nan
    )
    p_v = (
        float((np.sum(tor_v >= rho_res_absw) + 1) / (len(tor_v) + 1)) if len(tor_v) else np.nan
    )
    return {
        "ids": ids[good],
        "w": wi[good],
        "mean_dg": mean_dg[good],
        "mean_res": mean_res[good],
        "rho_dg_w": rho_dg,
        "rho_res_w": _spearman(mean_res[good], wi[good]),
        "rho_res_absw": rho_res_absw,
        "p_torus_dg": p_dg,
        "p_torus_v": p_v,
        "torus_dg_sd": float(np.std(tor_dg)) if len(tor_dg) > 1 else np.nan,
        "torus_dg_max": float(np.max(np.abs(tor_dg))) if len(tor_dg) else np.nan,
        "mid": mid,
        "aniso": float(np.nanstd(e_rad) / np.nanstd(e_tan)),
        "sd_rad": float(np.nanstd(e_rad)),
        "sd_tan": float(np.nanstd(e_tan)),
        "n_tiles": int(good.sum()),
    }


def _spearman(a, b):
    if len(a) < 3:
        return np.nan
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    den = np.sqrt(np.sum(ra**2) * np.sum(rb**2))
    return float(np.sum(ra * rb) / den) if den > 0 else np.nan


# ---------------------------------------------------------------------------
# S4 — the censoring channel
# ---------------------------------------------------------------------------


def s4_rejection(t: Tiles, w: np.ndarray):
    """Does the aligner *drop* tiles as a function of defocus?

    A tile that fails the correlation-peak gate contributes no residual at all,
    so a defocus-driven rejection rate censors exactly the tiles cause (b)
    predicts. This measures the censoring rather than assuming it away.
    """
    good = np.isfinite(w[t.tile_id])
    tt = t.select(good)
    wi = w[tt.tile_id]
    c = 0.5 * (tt.ref + tt.mov)
    d = np.abs(c - wi)
    y = (~tt.ok).astype(float)
    edges = np.array([0, 2, 4, 8, 16, 32, 1e9])
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (d >= lo) & (d < hi)
        if m.sum() == 0:
            continue
        rows.append((lo, hi, int(m.sum()), float(y[m].mean())))
    pair = tt.ref * 10000 + tt.mov
    beta, resid, Xd, gi, tw = _twoway_fe(y, tt.tile_id, pair, d[:, None])
    return {
        "bins": rows,
        "slope_per_frame": float(beta[gi]),
        "se": tw.cluster_se(Xd, resid, gi),
        "overall": float(y.mean()),
    }


def s5_infocus_residual(t: Tiles, w: np.ndarray, near: float = 2.0, far: float = 8.0,
                        n_torus: int = 95):
    """The brief's own discriminating prediction, computed directly.

    Under blur-induced correlation bias, a tile that is **in focus in both
    frames being matched** has no biased peak and should sit at the estimator
    noise floor whatever depth it is at. Under depth-dependent magnification the
    residual is geometry and does not care whether the tile is sharp.

    So: within each baseline separately — because the residual grows with
    baseline for reasons that have nothing to do with focus — compare the mean
    residual of tiles with `|c - w| <= near` against tiles with `|c - w| >= far`.

    The comparison is made within baseline *and* the null is the same torus shift
    of the depth field used by S1, so "sharp tiles happen to be textured tiles"
    cannot produce it.
    """
    m = t.ok & np.isfinite(t.res) & np.isfinite(w[t.tile_id])
    tt = t.select(m)
    d = np.abs(0.5 * (tt.ref + tt.mov) - w[tt.tile_id])

    def contrast(dd):
        rows, num, den = [], 0.0, 0.0
        for dl in np.unique(tt.delta):
            s = tt.delta == dl
            a = s & (dd <= near)
            b = s & (dd >= far)
            if a.sum() < 20 or b.sum() < 20:
                continue
            ra, rb = float(tt.res[a].mean()), float(tt.res[b].mean())
            rows.append((int(dl), int(a.sum()), ra, int(b.sum()), rb, rb - ra))
            num += (rb - ra) * min(a.sum(), b.sum())
            den += min(a.sum(), b.sum())
        return rows, (num / den if den else np.nan)

    def paired_contrast(dd, key):
        """Same contrast, but formed *within* a group so composition cancels.

        `key='pair'` removes any "this frame pair aligns badly" effect; `key='tile'`
        removes texture, contrast and field position exactly. Only groups that
        contain both a near and a far observation contribute.
        """
        g = (tt.ref * 10000 + tt.mov) if key == "pair" else tt.tile_id
        diffs, wts = [], []
        for dl in np.unique(tt.delta):
            s = tt.delta == dl
            for gi in np.unique(g[s]):
                m = s & (g == gi)
                a = m & (dd <= near)
                b = m & (dd >= far)
                if a.sum() < 3 or b.sum() < 3:
                    continue
                diffs.append(float(tt.res[b].mean() - tt.res[a].mean()))
                wts.append(min(a.sum(), b.sum()))
        if not diffs:
            return np.nan, 0
        d_, w_ = np.array(diffs), np.array(wts, float)
        return float(np.sum(d_ * w_) / np.sum(w_)), len(diffs)

    rows, gap = contrast(d)
    gap_pair, n_pair = paired_contrast(d, "pair")
    gap_tile, n_tile = paired_contrast(d, "tile")
    tor, tor_pair, tor_tile = [], [], []
    for ws in _torus_labels(w)[:n_torus]:
        if not np.all(np.isfinite(ws[np.unique(tt.tile_id)])):
            continue
        dd = np.abs(0.5 * (tt.ref + tt.mov) - ws[tt.tile_id])
        _, g_ = contrast(dd)
        if np.isfinite(g_):
            tor.append(g_)
        gp, _ = paired_contrast(dd, "pair")
        if np.isfinite(gp):
            tor_pair.append(gp)
        gt, _ = paired_contrast(dd, "tile")
        if np.isfinite(gt):
            tor_tile.append(gt)
    tor = np.array(tor)
    tor_pair = np.array(tor_pair)
    tor_tile = np.array(tor_tile)

    def pval(obs, null):
        return float((np.sum(null >= obs) + 1) / (len(null) + 1)) if len(null) else np.nan

    return {
        "rows": rows,
        "gap_px": gap,
        "p_torus": pval(gap, tor),
        "torus_sd": float(tor.std(ddof=1)) if len(tor) > 1 else np.nan,
        "gap_within_pair": gap_pair,
        "n_pair_groups": n_pair,
        "p_torus_pair": pval(gap_pair, tor_pair),
        "gap_within_tile": gap_tile,
        "n_tile_groups": n_tile,
        "p_torus_tile": pval(gap_tile, tor_tile),
        "near": near,
        "far": far,
    }


def s6_signed_bias(t: Tiles, w: np.ndarray, ox: float, oy: float, n_torus: int = 95):
    """Is the defocus effect a peak **bias** or just peak **variance**?

    This distinction decides the architecture, so it cannot be skipped. A
    *symmetric* defocus PSF does not move a correlation peak; it only flattens
    it, which inflates the variance of the estimate. A peak that is actually
    *displaced* requires an asymmetric, field-dependent PSF — which is exactly
    the thing SYNTHESIS §3.4.2 says would justify per-lens computation rather
    than a data file.

    The two are told apart by sign. Define the signed blur asymmetry of a pair
    for tile `i`:

        a[i,j] = |mov[j] - w[i]| - |ref[j] - w[i]|

    positive when the moving frame is the more defocused of the two. Under a
    directional bias the residual flips sign with `a`; under variance inflation
    it does not, because a larger random error has no preferred sign.

    Regressed with the same tile and pair fixed effects as S1, on:
      * the radial residual component about the scale centre, and
      * the tangential component, which serves as the placebo — a radially
        oriented aberration should not produce the same coefficient there.

    Also reports the magnitude regression `|e| ~ a`, which *is* expected to be
    flat under a pure bias and is reported so the two channels can be compared.
    """
    m = t.ok & np.isfinite(t.res) & np.isfinite(w[t.tile_id])
    tt = t.select(m)
    wi = w[tt.tile_id]
    a = np.abs(tt.mov - wi) - np.abs(tt.ref - wi)
    e_rad, e_tan, _r = radial_tangential(tt.ex, tt.ey, tt.ux, tt.uy, ox, oy)
    pair = tt.ref * 10000 + tt.mov
    tw = TwoWay(tt.tile_id, pair)
    ad = tw.demean(a)[:, None]

    def fit(y):
        yd = tw.demean(np.nan_to_num(y))
        b, r = tw.fit(yd, ad)
        return float(b[0]), tw.cluster_se(ad, r, 0)

    b_rad, se_rad = fit(e_rad)
    b_tan, se_tan = fit(e_tan)
    b_x, se_x = fit(tt.ex)
    b_y, se_y = fit(tt.ey)

    tor = []
    for ws in _torus_labels(w)[:n_torus]:
        if not np.all(np.isfinite(ws[np.unique(tt.tile_id)])):
            continue
        aa = np.abs(tt.mov - ws[tt.tile_id]) - np.abs(tt.ref - ws[tt.tile_id])
        Xp = tw.demean(aa)[:, None]
        bp, _ = tw.fit(tw.demean(np.nan_to_num(e_rad)), Xp)
        tor.append(abs(float(bp[0])))
    tor = np.array(tor)

    return {
        "b_rad": b_rad,
        "se_rad": se_rad,
        "b_tan": b_tan,
        "se_tan": se_tan,
        "b_x": b_x,
        "se_x": se_x,
        "b_y": b_y,
        "se_y": se_y,
        "p_torus_rad": float((np.sum(tor >= abs(b_rad)) + 1) / (len(tor) + 1)) if len(tor) else np.nan,
        "torus_sd": float(tor.std(ddof=1)) if len(tor) > 1 else np.nan,
        "n": len(a),
        "a_range": (float(a.min()), float(a.max())),
        "sd_rad": float(np.nanstd(e_rad)),
        "sd_tan": float(np.nanstd(e_tan)),
    }


def s7_bias_variance(t: Tiles, w: np.ndarray, bins=((0, 2), (2, 4), (4, 8), (8, 16), (16, 1e9))):
    """Split the per-tile residual into a repeatable part and a scatter part.

    For each tile and each defocus bin, the residual vectors over the pairs in
    that bin have a mean vector and a scatter about it. `|mean|^2` is inflated
    by `scatter^2 / n`, so that is subtracted before the mean is called a bias.

    Both quantities are averages over the *same* population of pairs, so this is
    not the spatial-versus-temporal comparison the project has been burned by
    twice: nothing here compares a spread across tiles to a spread across
    frames.
    """
    m = t.ok & np.isfinite(t.res) & np.isfinite(w[t.tile_id])
    tt = t.select(m)
    d = np.abs(0.5 * (tt.ref + tt.mov) - w[tt.tile_id])
    rows = []
    for lo, hi in bins:
        sel = (d >= lo) & (d < hi)
        if sel.sum() < 50:
            continue
        bias2, scat2, cnt = 0.0, 0.0, 0
        for tid in np.unique(tt.tile_id[sel]):
            s = sel & (tt.tile_id == tid)
            n = int(s.sum())
            if n < 4:
                continue
            mx, my = float(tt.ex[s].mean()), float(tt.ey[s].mean())
            sc = float(np.mean((tt.ex[s] - mx) ** 2 + (tt.ey[s] - my) ** 2))
            bias2 += max(mx * mx + my * my - sc / n, 0.0)
            scat2 += sc
            cnt += 1
        if cnt:
            rows.append(
                (
                    lo,
                    hi,
                    cnt,
                    math.sqrt(bias2 / cnt),
                    math.sqrt(scat2 / cnt),
                    math.sqrt(bias2 / max(scat2, 1e-30)),
                )
            )
    return rows


def forward_map(g, rot, ax, ay, px, py, cx, cy):
    """Where reference-plane point `(px, py)` lands in frame `k`.

    `m3-drift` fits a displacement field `d(p) = a + g*(p-c) + rot^(p-c)`, so the
    forward map is `F(p) = p + d(p)`. It is exactly affine, so the bounding box
    of a rectangle's image is the bounding box of its four corner images.
    """
    ux, uy = px - cx, py - cy
    return (px + ax + g * ux - rot * uy, py + ay + rot * ux + g * uy)


def tile_halo(fits: Fits, tile: int, cx: float, cy: float, w: int, h: int):
    """Required source halo per output tile, in plane px.

    For output tile `T` in reference coordinates, the samples a gather-at-
    consumption kernel needs from frame `k` occupy `F_k(T)`. The halo is the
    symmetric expansion of `T` that contains `F_k(T)` for **every** `k` in the
    stack, which is what a `source_roi(out, warp)` call would have to return.

    Returns `(centres_x, centres_y, halo_px, radius_from_scale_centre)`.
    """
    # Cover the whole plane. Truncating to whole tiles would leave the last 60 px
    # of a 3516 px plane out of the grid and understate the corner halo, which is
    # precisely the number the interface argument turns on.
    nx = -(-w // tile)
    ny = -(-h // tile)
    gs = np.concatenate([[0.0], fits.g])
    rs = np.concatenate([[0.0], fits.rot])
    axs = np.concatenate([[0.0], fits.ax])
    ays = np.concatenate([[0.0], fits.ay])

    cxs, cys, halos = [], [], []
    for j in range(ny):
        for i in range(nx):
            x0, y0 = i * tile, j * tile
            x1, y1 = min(x0 + tile, w), min(y0 + tile, h)
            corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
            hmax = 0.0
            for g, r, ax, ay in zip(gs, rs, axs, ays):
                xs, ys = [], []
                for px, py in corners:
                    fx, fy = forward_map(g, r, ax, ay, px, py, cx, cy)
                    xs.append(fx)
                    ys.append(fy)
                hmax = max(
                    hmax,
                    x0 - min(xs),
                    max(xs) - x1,
                    y0 - min(ys),
                    max(ys) - y1,
                )
            cxs.append(0.5 * (x0 + x1))
            cys.append(0.5 * (y0 + y1))
            halos.append(max(hmax, 0.0))
    return np.array(cxs), np.array(cys), np.array(halos)


def corner_halo_point(fits: Fits, w: int = PLANE_W, h: int = PLANE_H) -> float:
    """Halo required at the exact plane corner, in plane px.

    SYNTHESIS §3.4.1 B1 quotes "roughly 39 plane pixels at the frame corner",
    which is a statement about a *point*, not about a tile. This is the directly
    comparable number: the largest distance any of the four plane corners moves
    over the stack.
    """
    cx, cy = w / 2.0, h / 2.0
    best = 0.0
    for g, r, ax, ay in zip(fits.g, fits.rot, fits.ax, fits.ay):
        for px, py in [(0.0, 0.0), (float(w), 0.0), (0.0, float(h)), (float(w), float(h))]:
            fx, fy = forward_map(g, r, ax, ay, px, py, cx, cy)
            best = max(best, abs(fx - px), abs(fy - py))
    return best


def halo_table(fits: Fits, tile: int, ox: float, oy: float, w: int = PLANE_W, h: int = PLANE_H):
    """Halo statistics for one stack at one tile size."""
    cx, cy = w / 2.0, h / 2.0
    tcx, tcy, halo = tile_halo(fits, tile, cx, cy, w, h)
    rad = np.hypot(tcx - (cx + ox), tcy - (cy + oy))
    order = np.argsort(rad)
    # Area a gather actually needs, tile by tile, versus what one scalar halo
    # sized for the worst tile would make every tile pay.
    area_need = (tile + 2 * halo) ** 2
    area_scalar = (tile + 2 * halo.max()) ** 2
    # Radial profile in eight equal-count bins, for the report's halo-vs-radius
    # table. Reported rather than fitted: the relation is only linear when the
    # halo is dominated by the scale term.
    nb = 8
    qs = np.quantile(rad, np.linspace(0, 1, nb + 1))
    prof = []
    for lo, hi in zip(qs[:-1], qs[1:]):
        m = (rad >= lo) & (rad <= hi if hi == qs[-1] else rad < hi)
        if m.sum():
            prof.append((float(rad[m].mean()), float(halo[m].mean()), float(halo[m].max()), int(m.sum())))
    return {
        "tile": tile,
        "n_tiles": len(halo),
        "halo": halo,
        "radius": rad,
        "centre_halo": float(halo[np.argmin(rad)]),
        "corner_halo": float(halo[np.argmax(rad)]),
        "max_halo": float(halo.max()),
        "min_halo": float(halo.min()),
        "mean_halo": float(halo.mean()),
        "median_halo": float(np.median(halo)),
        "ratio_corner_centre": float(halo[np.argmax(rad)] / max(halo[np.argmin(rad)], 1e-9)),
        "ratio_max_median": float(halo.max() / max(np.median(halo), 1e-9)),
        "ratio_max_mean": float(halo.max() / max(halo.mean(), 1e-9)),
        "scalar_halo_px": float(halo.max()),
        "area_waste": float(area_scalar / area_need.mean()),
        "area_waste_median": float(area_scalar / np.median(area_need)),
        "profile": prof,
        "sorted_radius": rad[order],
        "sorted_halo": halo[order],
        "slope_px_per_px": float(np.polyfit(rad, halo, 1)[0]),
        "intercept_px": float(np.polyfit(rad, halo, 1)[1]),
    }


def max_drift_corner(fits: Fits, w: int = PLANE_W, h: int = PLANE_H) -> float:
    """Largest corner displacement over the stack, in plane px. A cross-check on
    the halo: the corner halo cannot exceed it by more than the tile's own
    scale change."""
    cx, cy = w / 2.0, h / 2.0
    best = 0.0
    for g, r, ax, ay in zip(fits.g, fits.rot, fits.ax, fits.ay):
        for px, py in [(0, 0), (w, 0), (0, h), (w, h)]:
            fx, fy = forward_map(g, r, ax, ay, px, py, cx, cy)
            best = max(best, math.hypot(fx - px, fy - py))
    return best
