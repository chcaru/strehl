"""M71 step 04 -- an ISO 100 dark reference, and the PTC's local slopes.

Two diagnostics that step 03 raised and could not settle from the flats alone.

1. THE NEGATIVE INTERCEPT. All four planes fitted b < 0, which is unphysical as
   a variance floor. A black-level offset K shifts the fitted intercept by
   -g*K and leaves the SLOPE exactly untouched, so this cannot move the gain --
   but it has to be identified rather than waved at. `D:\\macro-dark-frames\\118MSDCF`
   is 22 ISO 100 dark frames on this same body (read-only), so the black offset
   and the read-noise floor can both be measured directly instead of
   extrapolated from a lever arm that starts at 97 DN.

   The comparison target is profile.rs's own DARK_SIGMA_RMS_DN row for ISO 100:
   0.98444 DN pooled RMS over 20 frames and 4 planes (M4 sec 8.1, reproduced
   through rawpy in experiments/m48-noise-floor at 0.99986-0.99998). This
   script must reproduce THAT before its black-offset number is worth anything
   -- it is the negative control on my own decode path (rule 32's second
   clause: every Python RAW decode must be checkable against an independent one).

2. IS THE PTC CURVED? A single fitted slope hides shape. Consecutive-point
   slopes (V_{k+1} - V_k) / (S_{k+1} - S_k) are intercept-free by construction,
   so they separate "constant gain plus a bad intercept" from "gain that varies
   with signal". The B plane's +-4% structured residuals in step 03 make this
   necessary, not decorative.

Dark current is not a confound at the exposures involved: the darks are 1/100 s
and the flats reach 1/5 s, and at room temperature this sensor's dark current
over 0.2 s is well under 1 e-, i.e. under 0.25 DN, against the ~12 DN offset
the flats imply.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent.parent
DARKS = Path(r"D:\macro-dark-frames\118MSDCF")
OUT = HERE / "data" / "04-dark-and-linearity.json"
PLANES = ("R", "G1", "G2", "B")
BLACK = 512.0
DROP = 2          # M4's convention: 22 captured, stabilisation shots dropped, 20 used
PROFILE_DARK_SIGMA_ISO100 = 0.98444     # profile.rs DARK_SIGMA_RMS_DN row for ISO 100


def planes_of(vis):
    return {"R": vis[0::2, 0::2], "G1": vis[0::2, 1::2],
            "G2": vis[1::2, 0::2], "B": vis[1::2, 1::2]}


def measure_darks():
    files = sorted(DARKS.glob("*.ARW"))
    assert len(files) == 22, f"expected 22 darks, found {len(files)}"
    files = files[DROP:]
    n = len(files)
    acc = {p: None for p in PLANES}
    accsq = {p: None for p in PLANES}
    per_frame = []
    for f in files:
        with rawpy.imread(str(f)) as raw:
            vis = raw.raw_image_visible.astype(np.float32)   # rule 32: copy inside
        pl = planes_of(vis)
        rec = {"file": f.name}
        for p in PLANES:
            a = pl[p].astype(np.float64)
            rec[f"mean_{p}"] = float(a.mean())
            if acc[p] is None:
                acc[p] = np.zeros(a.shape, np.float64)
                accsq[p] = np.zeros(a.shape, np.float64)
            acc[p] += a
            accsq[p] += a * a
        per_frame.append(rec)
        del vis, pl

    out = {"n_frames": n, "dropped": DROP, "per_frame": per_frame, "planes": {}}
    sig2 = []
    for p in PLANES:
        mu = acc[p] / n
        var = (accsq[p] - n * mu * mu) / (n - 1)
        var = np.maximum(var, 0.0)
        offset = float(mu.mean()) - BLACK
        # Pooled RMS temporal sigma is sqrt(mean of per-pixel temporal variance):
        # that is the statistic profile.rs's table is on.
        pooled = float(np.sqrt(var.mean()))
        # Robust variant, immune to the hot-pixel tail
        med = float(np.median(var))
        out["planes"][p] = {
            "black_offset_dn": offset,
            "pooled_rms_sigma_dn": pooled,
            "median_sigma_dn": float(np.sqrt(med)),
            "spatial_sd_of_temporal_mean_dn": float(mu.std()),
            "frac_var_gt_10x_median": float((var > 10 * med).mean()),
        }
        sig2.append(var.mean())
        print(f"  {p}: black offset {offset:+8.4f} DN   pooled RMS sigma "
              f"{pooled:.5f} DN   median-based {np.sqrt(med):.5f} DN   "
              f"dark FPN (spatial sd of mean) {mu.std():.4f} DN")
    four_plane = float(np.sqrt(np.mean(sig2)))
    out["four_plane_pooled_rms_sigma_dn"] = four_plane
    out["profile_table_iso100"] = PROFILE_DARK_SIGMA_ISO100
    out["ratio_to_profile_table"] = four_plane / PROFILE_DARK_SIGMA_ISO100
    print(f"\n  4-plane pooled RMS sigma = {four_plane:.5f} DN against "
          f"profile.rs's ISO 100 row {PROFILE_DARK_SIGMA_ISO100:.5f} DN "
          f"-> ratio {four_plane / PROFILE_DARK_SIGMA_ISO100:.5f}")
    mean_offset = float(np.mean([out['planes'][p]['black_offset_dn'] for p in PLANES]))
    out["mean_black_offset_dn"] = mean_offset
    print(f"  mean black offset over 4 planes = {mean_offset:+.4f} DN")
    return out


def local_slopes(ptc):
    print("\n=== consecutive-point slopes (intercept-free)")
    res = {}
    for plane in PLANES:
        pts = sorted(ptc[plane]["points"], key=lambda p: p["S"])
        S = np.array([p["S"] for p in pts])
        V = np.array([p["V"] for p in pts])
        A1 = np.array([p["A1"] for p in pts])
        A2 = np.array([p["A2"] for p in pts])
        b = ptc[plane]["b"]
        # Undo the per-group Jensen coefficients before differencing, so that
        # the difference is between two points on the SAME curve.
        Vc = (V - b * A2) / A1
        sl = np.diff(Vc) / np.diff(S)
        mid = 0.5 * (S[:-1] + S[1:])
        res[plane] = {"S_mid": mid.tolist(), "slope": sl.tolist()}
        print(f"  {plane}:")
        for m, s in zip(mid, sl):
            print(f"     S~{m:8.0f}  dV/dS = {s:.5f}")
    return res


def main():
    print("=== ISO 100 dark reference, D:\\macro-dark-frames\\118MSDCF")
    darks = measure_darks()
    ptc = json.loads((HERE / "data" / "03-ptc.json").read_text(encoding="utf-8"))
    slopes = local_slopes(ptc)

    print("\n=== reconciling step 03's negative intercept")
    b_true = darks["four_plane_pooled_rms_sigma_dn"] ** 2
    print(f"  measured read-noise variance floor b_true = {b_true:.5f} DN^2")
    implied = {}
    for plane in PLANES:
        g = ptc[plane]["g"]
        b = ptc[plane]["b"]
        bp = darks["planes"][plane]["pooled_rms_sigma_dn"] ** 2
        K = (bp - b) / g
        implied[plane] = {"b_fitted": b, "b_dark_measured": bp,
                          "implied_black_offset_dn": K}
        print(f"  {plane}: fitted b = {b:+8.4f}, dark-measured b = {bp:.5f} "
              f"-> implied black offset K = {K:+7.3f} DN "
              f"(darks say {darks['planes'][plane]['black_offset_dn']:+.3f} DN)")

    out = {"darks": darks, "local_slopes": slopes, "implied_black_offset": implied}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
