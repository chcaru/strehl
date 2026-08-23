r"""M48 script 09 -- measure the fixed-pattern variance fraction rho from darks.

SYNTHESIS question 142. M46 obtained rho = 0.3094 by SOLVING it from a residual
correlation on one illuminated flat ROI (`FRC_flat/(1-FRC_flat)/n_eff`). Dark
frames separate the two variance components arithmetically, with no fit:

    x[i,t] = mu[i] + eps[i,t]

  * `mu[i]`, the per-pixel temporal mean, varies pixel-to-pixel by the FIXED
    PATTERN. Its pixel variance is the FPN variance.
  * `eps[i,t]`, the scatter about that mean, is the TEMPORAL noise (read, plus
    dark-current shot, which is negligible at these exposures).

Both are measured on the same pixels, at each ISO, from the same 242 darks used
by scripts 01-02.

Two independent estimators of the FPN variance are computed and compared,
because a single estimator of a difference of two large numbers is not
trustworthy:

  E1 (bias-corrected plug-in)
      Var_pix(mean over T frames) over-states FPN by exactly V_temporal/T,
      because the temporal noise does not fully average away in T = 20 frames.
      V_FPN = Var_pix(m) - V_temporal/T.

  E2 (split-half cross-covariance) -- the cleaner one
      Split the frames into two disjoint halves A and B by parity of frame
      index. Their temporal noise is independent, so
          Cov_pix(mean_A, mean_B) -> Var_pix(mu)
      with NO bias term to subtract. Parity rather than first-half/second-half,
      so that any slow drift across the sequence is shared by both halves
      rather than separating them.

Black level is never subtracted: variance and covariance are invariant to a
constant offset, so this measurement does not depend on the 512 assumption.

Hot pixels are a fixed pattern, so they land in the FPN term by construction.
This project treats static defects as a separate concern (M29, and the map in
experiments/m22-hot-pixels), so rho is reported BOTH raw and after censoring
them, and the censored fraction is reported. Which of the two is comparable to
M46's number is argued in the report, not assumed here.

D:\macro-dark-frames is read-only source data. This script only reads it.
"""

import json
import os

import numpy as np
import rawpy

ROOT = r"D:\macro-dark-frames"
DROP_STABILISATION = 2  # the owner's first two frames per set
PLANES = (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1))
TILES = 8  # 8x8 grid, for a spatial error bar
HOT_MAD = 5.0  # censor pixels above median + 5 robust sd of the mean map

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "fpn-rho.json")


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def stats(a, b, sumsq, t_total):
    """FPN and temporal variance from half-sums and the total sum of squares.

    `a` and `b` are SUMS over each half (not means). Returns a dict in DN^2.
    """
    n_half = t_total // 2
    total = a + b
    m = total / t_total
    # Per-pixel temporal variance, then averaged over pixels.
    var_t = (sumsq - total.astype(np.float64) ** 2 / t_total) / (t_total - 1)
    np.clip(var_t, 0, None, out=var_t)
    v_temporal = float(var_t.mean())

    ma = a / n_half
    mb = b / n_half
    # E2: cross-covariance of the two half-means. Unbiased for Var_pix(mu).
    v_fpn_cross = float(np.mean((ma - ma.mean()) * (mb - mb.mean())))
    # E1: plug-in variance of the full mean, minus the known temporal leak.
    v_fpn_plug = float(m.var() - v_temporal / t_total)
    return {
        "v_temporal": v_temporal,
        "v_fpn_cross": v_fpn_cross,
        "v_fpn_plug": v_fpn_plug,
        "mean_map": m,
        "var_t": var_t,
    }


def rho_of(v_fpn, v_temporal):
    """Fraction of a SINGLE DARK FRAME's variance that is fixed-pattern."""
    tot = v_fpn + v_temporal
    return float(v_fpn / tot) if tot > 0 else float("nan")


def tile_rhos(ma, mb, var_t, t_total):
    """rho per tile, for a spatial error bar."""
    h, w = ma.shape
    th, tw = h // TILES, w // TILES
    out = []
    for ty in range(TILES):
        for tx in range(TILES):
            sy, sx = slice(ty * th, (ty + 1) * th), slice(tx * tw, (tx + 1) * tw)
            aa, bb = ma[sy, sx], mb[sy, sx]
            vt = float(var_t[sy, sx].mean())
            vf = float(np.mean((aa - aa.mean()) * (bb - bb.mean())))
            out.append(rho_of(vf, vt))
    return np.array(out, dtype=np.float64)


def process(d):
    files = sorted(
        os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".arw")
    )
    iso = iso_of(files[0])
    files = files[DROP_STABILISATION:]
    t_total = len(files)
    if t_total % 2:  # keep the halves exactly equal
        files = files[:-1]
        t_total -= 1

    acc = None
    for idx, f in enumerate(files):
        # `raw_image_visible` is a VIEW into rawpy's internal buffer, which is
        # freed when the context manager exits. Everything that touches it must
        # happen inside the block, and each plane is copied out by `astype`.
        with rawpy.imread(f) as rr:
            raw = rr.raw_image_visible
            if acc is None:
                acc = {}
                for name, dy, dx in PLANES:
                    shp = raw[dy::2, dx::2].shape
                    acc[name] = {
                        "a": np.zeros(shp, np.float32),
                        "b": np.zeros(shp, np.float32),
                        "ss": np.zeros(shp, np.float64),
                    }
            for name, dy, dx in PLANES:
                p = raw[dy::2, dx::2].astype(np.float32)
                acc[name]["a" if idx % 2 == 0 else "b"] += p
                acc[name]["ss"] += p.astype(np.float64) ** 2
            del raw

    res = {"iso": iso, "dir": os.path.basename(d), "frames": t_total, "planes": {}}
    for name, _, _ in PLANES:
        s = stats(acc[name]["a"], acc[name]["b"], acc[name]["ss"], t_total)
        m, var_t = s["mean_map"], s["var_t"]
        n_half = t_total // 2
        ma, mb = acc[name]["a"] / n_half, acc[name]["b"] / n_half

        # Censor hot pixels: a fixed pattern this project handles separately.
        med = float(np.median(m))
        mad = float(np.median(np.abs(m - med))) * 1.4826
        keep = m <= med + HOT_MAD * mad
        hot_frac = float(1.0 - keep.mean())
        mak, mbk = ma[keep], mb[keep]
        v_t_c = float(var_t[keep].mean())
        v_f_c = float(np.mean((mak - mak.mean()) * (mbk - mbk.mean())))

        tr = tile_rhos(ma, mb, var_t, t_total)
        res["planes"][name] = {
            "v_temporal": s["v_temporal"],
            "v_fpn_cross": s["v_fpn_cross"],
            "v_fpn_plug": s["v_fpn_plug"],
            "estimator_ratio_plug_over_cross": (
                s["v_fpn_plug"] / s["v_fpn_cross"] if s["v_fpn_cross"] else None
            ),
            "rho": rho_of(s["v_fpn_cross"], s["v_temporal"]),
            "rho_plug": rho_of(s["v_fpn_plug"], s["v_temporal"]),
            "fpn_sd_dn": float(np.sqrt(max(s["v_fpn_cross"], 0.0))),
            "temporal_sd_dn": float(np.sqrt(s["v_temporal"])),
            "hot_censored_fraction": hot_frac,
            "rho_censored": rho_of(v_f_c, v_t_c),
            "fpn_sd_dn_censored": float(np.sqrt(max(v_f_c, 0.0))),
            "temporal_sd_dn_censored": float(np.sqrt(v_t_c)),
            "rho_tile_mean": float(tr.mean()),
            "rho_tile_sd": float(tr.std(ddof=1)),
            "rho_tile_sem": float(tr.std(ddof=1) / np.sqrt(tr.size)),
            "n_pixels": int(m.size),
        }
        del s, m, var_t, ma, mb
    return res


def main():
    dirs = sorted(
        os.path.join(ROOT, d)
        for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d))
    )
    out = []
    for d in dirs:
        r = process(d)
        out.append(r)
        g1 = r["planes"]["G1"]
        print(
            f"ISO {r['iso']:5d}  T={r['frames']}  G1: "
            f"sd_temporal {g1['temporal_sd_dn']:6.3f}  sd_fpn {g1['fpn_sd_dn']:6.3f}  "
            f"rho {g1['rho']:.4f} +- {g1['rho_tile_sem']:.4f}  "
            f"rho_cens {g1['rho_censored']:.4f}  hot {g1['hot_censored_fraction']*100:.3f}%  "
            f"E1/E2 {g1['estimator_ratio_plug_over_cross']:.4f}"
        )
    out.sort(key=lambda r: r["iso"])
    payload = {
        "_meta": {
            "script": "09-fpn-rho.py",
            "question": "SYNTHESIS 142 -- measure rho rather than fitting it",
            "definition": "rho = V_fpn / (V_fpn + V_temporal) on a DARK frame; "
            "V_temporal is read + dark-current shot, and there is NO "
            "photon shot noise and NO PRNU in either term",
            "estimators": "E2 split-half cross-covariance (primary); "
            "E1 bias-corrected plug-in (cross-check)",
            "black_level": "never subtracted; variance is offset-invariant",
            "drop_stabilisation": DROP_STABILISATION,
            "hot_threshold": f"median + {HOT_MAD} robust sd of the mean map",
        },
        "sets": out,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
