"""accept2.py -- the acceptance gate, rebuilt around three measured failures of accept.py.

accept.py judged the pyramid merge a FAILURE (acuity 89.8% / 91.3%). Measured
tonight, on a clean protocol with null controls, that verdict was an artifact of
the instrument in three separate ways. Each is fixed here, and accept.py is left
untouched so every number already in the record stays reproducible.

FAILURE 1 -- a global scalar cannot adjudicate a localised defect.
  accept.py reports one frame-wide acuity. On flower-bud that single number
  averaged 1528 tiles at 0.98 together with 6 tiles at 0.4495 where the merge
  had annihilated the subject outline. One number cannot separate "1% softer
  everywhere" from "the silhouette is destroyed". Third instance of this shape
  in one night, after M122's HF energy statistic and trend.py's gradient RMS.
  FIX: amplitude ratio is reported per reference-amplitude quintile and the
  gate binds on the WORST quintile, not the mean.

FAILURE 2 -- |Laplacian| is a top-octave detector, and the top octave is the
  one band this rig's optics have already destroyed.
  The 3x3 Laplacian's frequency response rises monotonically to its maximum at
  Nyquist, so accept.py's acuity is dominated by the last octave. Measured on
  couch-fibers, the pyramid merge's amplitude ratio against frequency runs
  1.046 / 1.175 / 1.315 / 1.341(peak, half-Nyquist) / 1.061 / 0.940 / 0.972:
  a band-pass GAIN of +34% through the mid-band with a ~5% deficit confined to
  the top octave. accept.py saw only the deficit. Per facts 12 and 28 the top
  octave carries almost no optical information here (marked f/11 is effectively
  f/33; MTF@Nyquist 0.036 at f/5.6 at m=2.0), so weighting it hardest is
  precisely backwards.
  FIX: the gate binds on the MID-BAND (0.2-0.7 f/Nyq). The top octave is
  reported, and deliberately does not bind.

FAILURE 3 -- one clip% conflates populations that need different fixes.
  All of flower-bud's 1.4015% is black-rail and all of it is in the dark
  population; the lit population and the white rail are clean at 0.0000%. A
  global black-point lift would move the headline number without fixing
  anything. Counting them together also hid that the clipping sits at the
  silhouette boundary.
  FIX: clipping is split rail x population into four counted cells that sum to
  the total, so a skipped or displaced defect cannot read as a fixed one.

COMMISSIONING. --self runs every arm against ITSELF. A gate that cannot return
exactly 1.0000 on identical input is not measuring what it claims, and this
refuses to print a verdict until that passes.

Usage:
  python accept2.py <dir> --ref ctrl              # <subject>--<arm>.tiff
  python accept2.py <dir> --ref ctrl --self       # commission only
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import tifffile

TILE = 128
CLIP_MAX = 0.02      # percent, per cell, rise over reference
QUINTILE_MIN = 0.98  # worst reference-amplitude quintile
MIDBAND_MIN = 0.98   # 0.2-0.7 f/Nyq
P1_MAX_RISE = 0.02   # fraction of full range
NBIN = 24
MAX_PSD_TILES = 150  # subsample for speed; the estimate is an average anyway


def load(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path.name}: expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] >= 3, f"{path.name}: shape {a.shape}"
    return a


def clip_cells(a: np.ndarray, lit: np.ndarray) -> dict:
    lo = (a == 0).any(axis=2)
    hi = (a == 65535).any(axis=2)
    n = a.shape[0] * a.shape[1]
    return {
        "black_lit": 100.0 * np.logical_and(lo, lit).sum() / n,
        "black_dark": 100.0 * np.logical_and(lo, ~lit).sum() / n,
        "white_lit": 100.0 * np.logical_and(hi, lit).sum() / n,
        "white_dark": 100.0 * np.logical_and(hi, ~lit).sum() / n,
    }


def lap_rms(g: np.ndarray) -> float:
    lap = 4.0 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(np.sqrt((lap.astype(np.float64) ** 2).mean()))


# Difference-of-Gaussians matched to the same 0.2-0.7 f/Nyq band the gate binds
# on. A Gaussian of std s has response exp(-2*pi^2*s^2*f^2) with f in cycles per
# pixel, so its half-power point sits at s = sqrt(ln2/(2*pi^2))/f = 0.1874/f.
# Nyquist is 0.5 c/px, so the band is 0.1-0.35 c/px and s = 1.874 and 0.535.
#
# This exists because the first version of this gate used lap_rms per tile and
# then failed wrapped-text-1 on its FLATTEST quintile (0.9309) while that same
# file measured 0.9996 in the mid-band. The Laplacian is top-octave weighted, so
# a per-tile Laplacian statistic reproduces, at tile scale, precisely the defect
# this gate was written to remove from accept.py. A gate must not be built from
# the instrument it replaces.
DOG_LO, DOG_HI = 0.535, 1.874


def dog(g: np.ndarray) -> np.ndarray:
    from scipy.ndimage import gaussian_filter

    return gaussian_filter(g, DOG_LO) - gaussian_filter(g, DOG_HI)


def tile_rms(a: np.ndarray, t: int) -> np.ndarray:
    ny, nx = a.shape[0] // t, a.shape[1] // t
    v = a[: ny * t, : nx * t].reshape(ny, t, nx, t)
    return np.sqrt((v.astype(np.float32) ** 2).mean(axis=(1, 3), dtype=np.float64))


def radial_psd(tile: np.ndarray, idx: np.ndarray, win: np.ndarray) -> np.ndarray:
    t = (tile - tile.mean()) * win
    F = np.fft.fftshift(np.fft.fft2(t))
    P = F.real**2 + F.imag**2
    out = np.zeros(NBIN)
    for b in range(NBIN):
        m = idx == b
        out[b] = P[m].mean() if m.any() else np.nan
    return out


def _psd_index():
    c = TILE // 2
    y, x = np.ogrid[:TILE, :TILE]
    r = np.sqrt((y - c) ** 2 + (x - c) ** 2)
    idx = np.clip((r / c * NBIN).astype(int), 0, NBIN - 1)
    w = np.hanning(TILE)
    return idx, w[:, None] * w[None, :]


def compare(pref: Path, ptest: Path) -> dict:
    R, T = load(pref), load(ptest)
    assert R.shape == T.shape, f"shape mismatch {R.shape} vs {T.shape} -- refusing"
    gr = R[:, :, 1].astype(np.float32)
    gt = T[:, :, 1].astype(np.float32)

    thr = float(np.percentile(gr, 20.0))
    lit = gr > thr

    clipped_px = np.logical_or((T == 0).any(axis=2), (T == 65535).any(axis=2))

    bp_r = tile_rms(dog(gr), TILE)
    bp_t = tile_rms(dog(gt), TILE)

    h, w = gr.shape
    ny, nx = h // TILE, w // TILE
    recs = []
    for iy in range(ny):
        for ix in range(nx):
            sl = (slice(iy * TILE, (iy + 1) * TILE), slice(ix * TILE, (ix + 1) * TILE))
            if lit[sl].mean() < 0.9:
                continue
            hr = lap_rms(gr[sl])
            if hr <= 0 or bp_r[iy, ix] <= 0:
                continue
            recs.append(
                (
                    hr,
                    lap_rms(gt[sl]) / hr,
                    iy,
                    ix,
                    bool(clipped_px[sl].any()),
                    float(bp_t[iy, ix] / bp_r[iy, ix]),
                )
            )
    if not recs:
        raise SystemExit(f"{ptest.name}: no fully-lit tiles to judge")

    recs.sort(key=lambda r: r[0])
    refamp = np.array([r[0] for r in recs])
    ratio = np.array([r[1] for r in recs])
    dirty = np.array([r[4] for r in recs])
    bpr = np.array([r[5] for r in recs])

    quint = []
    for i in range(5):
        s = slice(i * len(recs) // 5, (i + 1) * len(recs) // 5)
        cl = ~dirty[s]
        quint.append(
            (
                float(refamp[s].mean()),
                float(ratio[s].mean()),
                float(ratio[s][cl].mean()) if cl.any() else float("nan"),
                s.stop - s.start,
                int((~cl).sum()),
                float(bpr[s].mean()),
                float(bpr[s][cl].mean()) if cl.any() else float("nan"),
            )
        )

    # Band-resolved amplitude over the sharpest quintile, where detail lives.
    # Computed twice: over every sharp tile, and over clip-free sharp tiles
    # only. The clamp and the veil are separate defects with separate owners,
    # and a single pooled band number cannot give either of them a clean target.
    idx, win = _psd_index()
    f = (np.arange(NBIN) + 0.5) / NBIN
    sharp = recs[len(recs) * 4 // 5 :]

    def bands(tiles):
        if not tiles:
            return {"low": float("nan"), "mid": float("nan"),
                    "high": float("nan"), "n": 0}
        step = max(len(tiles) // MAX_PSD_TILES, 1)
        sel = tiles[::step]
        pr = np.zeros(NBIN)
        pt = np.zeros(NBIN)
        for r in sel:
            iy, ix = r[2], r[3]
            sl = (slice(iy * TILE, (iy + 1) * TILE), slice(ix * TILE, (ix + 1) * TILE))
            pr += radial_psd(gr[sl], idx, win)
            pt += radial_psd(gt[sl], idx, win)
        with np.errstate(invalid="ignore", divide="ignore"):
            amp = np.sqrt(pt / pr)
        b = lambda a_, b_: float(np.nanmean(amp[(f >= a_) & (f < b_)]))
        return {"low": b(0.0, 0.2), "mid": b(0.2, 0.7),
                "high": b(0.7, 1.01), "n": len(sel)}

    all_b = bands(sharp)
    clean_b = bands([r for r in sharp if not r[4]])

    return {
        "clip_ref": clip_cells(R, lit),
        "clip_test": clip_cells(T, lit),
        "quint": quint,
        "worst_quint": min(q[1] for q in quint),
        "worst_bp": min(q[5] for q in quint),
        "worst_bp_clean": min(
            (q[6] for q in quint if not np.isnan(q[6])), default=float("nan")
        ),
        "worst_quint_clean": min(
            (q[2] for q in quint if not np.isnan(q[2])), default=float("nan")
        ),
        "overall": float(ratio.mean()),
        "low": all_b["low"],
        "mid": all_b["mid"],
        "high": all_b["high"],
        "mid_clean": clean_b["mid"],
        "low_clean": clean_b["low"],
        "high_clean": clean_b["high"],
        "n_psd": all_b["n"],
        "n_psd_clean": clean_b["n"],
        "n_dirty": int(dirty.sum()),
        "p1_ref": float(np.percentile(gr, 1.0)),
        "p1_test": float(np.percentile(gt, 1.0)),
        "acuity_legacy": float(
            np.abs(
                4.0 * gt[1:-1, 1:-1] - gt[:-2, 1:-1] - gt[2:, 1:-1]
                - gt[1:-1, :-2] - gt[1:-1, 2:]
            )[lit[1:-1, 1:-1]].mean()
            / np.abs(
                4.0 * gr[1:-1, 1:-1] - gr[:-2, 1:-1] - gr[2:, 1:-1]
                - gr[1:-1, :-2] - gr[1:-1, 2:]
            )[lit[1:-1, 1:-1]].mean()
        ),
        "tiles": len(recs),
    }


def verdict(m: dict):
    fails = []
    for k in ("black_lit", "black_dark", "white_lit", "white_dark"):
        rise = m["clip_test"][k] - m["clip_ref"][k]
        if rise > CLIP_MAX:
            fails.append(f"clip {k} +{rise:.4f}%")
    if m["worst_bp"] < QUINTILE_MIN:
        fails.append(f"worst bandpass quintile {m['worst_bp']:.4f}")
    if m["mid"] < MIDBAND_MIN:
        fails.append(f"midband {m['mid']:.4f}")
    if m["p1_test"] - m["p1_ref"] > P1_MAX_RISE * 65535:
        fails.append(f"p1 +{(m['p1_test'] - m['p1_ref']) / 65535:.1%}")
    return fails


def show(name: str, m: dict):
    print(f"\n  --- {name} ---")
    print(f"    tiles judged {m['tiles']}   psd tiles {m['n_psd']}")
    print(f"    {'clip cell':<14}{'ref %':>10}{'test %':>10}{'rise':>10}")
    tot_r = tot_t = 0.0
    for k in ("black_lit", "black_dark", "white_lit", "white_dark"):
        r, t = m["clip_ref"][k], m["clip_test"][k]
        tot_r += r
        tot_t += t
        print(f"    {k:<14}{r:10.4f}{t:10.4f}{t - r:+10.4f}")
    print(f"    {'TOTAL':<14}{tot_r:10.4f}{tot_t:10.4f}{tot_t - tot_r:+10.4f}")
    print(f"    {'quintile':<10}{'refAmp':>9}{'BANDPASS':>10}{'bpClipFree':>11}"
          f"{'lapRMS':>9}{'nTiles':>8}{'nDirty':>8}")
    for i, (ra, rr, rc, n, nd, bp, bpc) in enumerate(m["quint"]):
        bs = f"{bpc:11.4f}" if not np.isnan(bpc) else f"{'--':>11}"
        print(f"    q{i:<9d}{ra:9.1f}{bp:10.4f}{bs}{rr:9.4f}{n:8d}{nd:8d}")
    print(f"    band ALL sharp tiles ({m['n_psd']:>3})   low {m['low']:.4f}"
          f"   MID {m['mid']:.4f}   high {m['high']:.4f}")
    print(f"    band CLIP-FREE only  ({m['n_psd_clean']:>3})   low {m['low_clean']:.4f}"
          f"   MID {m['mid_clean']:.4f}   high {m['high_clean']:.4f}"
          f"   <- the veil's target, clamp excluded")
    print(f"    (high band does not bind: this rig's optics have already zeroed it)")
    print(f"    overall {m['overall']:.4f}   p1 {m['p1_ref']:.0f} -> {m['p1_test']:.0f}"
          f"   accept.py acuity would read {m['acuity_legacy']:.4f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--ref", default="ctrl")
    ap.add_argument("--self", dest="selftest", action="store_true")
    a = ap.parse_args()

    d = Path(a.dir)
    groups = defaultdict(dict)
    for p in sorted(d.glob("*--*.tiff")):
        subj, arm = p.stem.rsplit("--", 1)
        groups[subj][arm] = p
    if not groups:
        print(f"no <subject>--<arm>.tiff in {d}")
        return 2

    print(f"accept2 gate   clip rise<={CLIP_MAX}%/cell   worst quintile>={QUINTILE_MIN}"
          f"   midband>={MIDBAND_MIN}   p1 rise<={P1_MAX_RISE:.0%}")
    print(f"reference arm: {a.ref}")

    # --- commissioning ---
    print("\n=== COMMISSIONING: every arm against itself, must be exactly 1.0000 ===")
    bad = 0
    for subj, arms in groups.items():
        if a.ref not in arms:
            continue
        m = compare(arms[a.ref], arms[a.ref])
        dev = max(abs(m["overall"] - 1), abs(m["mid"] - 1),
                  abs(m["worst_quint"] - 1), abs(m["worst_bp"] - 1))
        f = verdict(m)
        status = "OK" if dev < 1e-9 and not f else f"BROKEN dev={dev:.2e} {f}"
        print(f"  {subj:<26} self-vs-self max|dev| {dev:.2e}   {status}")
        if dev >= 1e-9 or f:
            bad += 1
    if bad:
        print(f"\n{bad} arm(s) failed commissioning -- NOT reading any real result")
        return 3
    print("  gate commissioned")
    if a.selftest:
        return 0

    npass = nfail = nskip = 0
    for subj in sorted(groups):
        arms = groups[subj]
        print(f"\n{subj}")
        if a.ref not in arms:
            print(f"  SKIP: no '{a.ref}' arm (have {sorted(arms)})")
            nskip += 1
            continue
        for arm in sorted(arms):
            if arm == a.ref:
                continue
            m = compare(arms[a.ref], arms[arm])
            f = verdict(m)
            show(f"{arm}  =>  {'PASS' if not f else 'FAIL: ' + '; '.join(f)}", m)
            if f:
                nfail += 1
            else:
                npass += 1

    total = npass + nfail + nskip
    print(f"\n=== {npass} pass, {nfail} fail, {nskip} skipped = {total} groups ===")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
