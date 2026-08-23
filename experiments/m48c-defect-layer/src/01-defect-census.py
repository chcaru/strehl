r"""M48c script 01 -- a defect census from the 242 darks, criterion PRE-REGISTERED.

=============================== PRE-REGISTRATION ===============================
Written and committed BEFORE the numbers were looked at. The brief asks for a
criterion defined against the CALIBRATED NOISE MODEL rather than a fixed
threshold, and for the false-positive rate it implies.

THE MODEL (crates/strehl-core/src/profile.rs, as of M48):
    g(ISO)      = max(ISO, 100) / 436.8            DN per electron
    RN_e(ISO)   = 4.20   for ISO < 400
                = 1.2392 for ISO >= 400
    sigma_frame = RN_e * g                          DN, one frame, S = 0

THE STATISTIC. Per CFA plane, per ISO group:
    m[i]     = per-pixel temporal mean over T frames (stabilisation dropped)
    b[i]     = median of the 8 SAME-PLANE neighbours of i (3x3, centre removed)
    e[i]     = m[i] - b[i]                          the local excess

The local median removes any large-scale dark gradient and is robust to up to
4 of the 8 neighbours being themselves defective, which matters for clusters.

WHAT THE MODEL PREDICTS FOR e UNDER THE NULL. m[i] has sd sigma_frame/sqrt(T).
The median of 8 iid normals has variance ~ pi/(2*8) = 0.1963 of one sample, and
the neighbours are independent of the centre, so

    sigma_pred = sqrt(1+0.1963) * sigma_frame/sqrt(T) = 1.0938*sigma_frame/sqrt(T)

*** THE PART I EXPECT TO FAIL, STATED IN ADVANCE. ***
This prediction OMITS FIXED-PATTERN NOISE, because the shipped model omits it
(M48b fact 674 -- correctly, for its purpose). But DSNU does not average away
with T: it is the same every frame. M48b measured DSNU at 0.38-0.87 DN, while
sigma_frame/sqrt(T) at ISO 50 is 0.96/sqrt(20) = 0.215 DN. So the fixed pattern
should DOMINATE the spread of e by a factor of a few, and a threshold built on
sigma_pred should over-flag grossly. I predict F = sigma_obs/sigma_pred > 1 at
every ISO. If F ~ 1 instead, my M48b DSNU measurement is wrong and I want that.

SO THE CRITERION IS TWO-PART, AND BOTH PARTS ARE REPORTED:
    A (naive, model-only):  flag if |e - med(e)| > K * sigma_pred
    B (shipped-usable):     flag if |e - med(e)| > K * sigma_obs
where sigma_obs is the robust spread of e itself, 1.4826 * MAD(e), measured per
plane per ISO. F = sigma_obs/sigma_pred is reported at every ISO and IS the
measurement of how far the model is from describing a per-pixel mean.

K = 6, one-sided. Under a Gaussian null p = 9.866e-10, and with N = 8,236,816
pixels per plane that is
    0.0081 false positives per plane per ISO
    0.358  false positives over all 4 planes x 11 ISO groups
for hot, and the same again for cold. So under the null, criterion B should
produce essentially NO isolated flags. Any large single-group population is
therefore a real non-Gaussian tail, not threshold slop -- which is the whole
point of stating the rate in advance.

RECURRENCE IS THE DISCRIMINATOR, NOT THE THRESHOLD. M22 (fact 160) established
this and it is retained deliberately so the two maps are comparable: a pixel is
a DEFECT only if flagged in >= 6 of the 11 ISO groups. The 11 groups are 11
independent captures, so this is a free replication test.

COLD PIXELS ARE FLAGGED TOO. M22 measured only positive excess and recorded
23,710 low-side flags at ISO 1600 as explicitly untested for recurrence. The
cold side here is symmetric with the hot side by construction.

COORDINATE FRAME (SYNTHESIS fact 691 -- the two decoders disagree by two plane
columns, rawler 3516x2344 vs rawpy 3514x2344). THE CANONICAL FRAME FOR THIS MAP
IS rawpy's `raw_image_visible`, and the map carries its own geometry: the raw
visible shape, the plane shape and the CFA offsets are written into the output
so that a consumer reading it in the other decoder's frame can DETECT the
mismatch rather than silently mis-index by two columns.
================================================================================

D:\macro-dark-frames is read-only source data. This script only reads it.
"""

import json
import os

import numpy as np
import rawpy
from scipy.ndimage import median_filter

ROOT = r"D:\macro-dark-frames"
DROP_STABILISATION = 2
PLANES = (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1))
K = 6.0
RECUR_MIN = 6  # of 11 groups, M22's bar

GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
RN_E_LOW = 4.20
RN_E_HIGH = 1.2392

# Median of 8 iid normals: var ~ pi/(2n). Centre is independent of neighbours.
C_MED = float(np.sqrt(1.0 + np.pi / 16.0))

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "defect-census.json")
MAPDIR = os.path.join(HERE, "data")


def sigma_frame_dn(iso):
    """The shipped model's one-frame dark sigma in DN. S = 0, so sigma = RN_e*g."""
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = RN_E_HIGH if iso >= SECOND_BASE_ISO else RN_E_LOW
    return rn * g


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def load_mean(files):
    """Per-pixel temporal mean per plane, plus the raw visible geometry."""
    acc = None
    geom = None
    for f in files:
        # raw_image_visible is a VIEW into libraw's buffer, freed on __exit__.
        # Every touch happens inside the block and astype() copies out.
        with rawpy.imread(f) as rr:
            raw = rr.raw_image_visible
            if acc is None:
                geom = {"raw_visible_shape": [int(raw.shape[0]), int(raw.shape[1])]}
                acc = {
                    n: np.zeros(raw[dy::2, dx::2].shape, np.float64)
                    for n, dy, dx in PLANES
                }
            for n, dy, dx in PLANES:
                acc[n] += raw[dy::2, dx::2].astype(np.float64)
            del raw
    for n in acc:
        acc[n] /= len(files)
    return acc, geom


def excess(m):
    """m minus the median of its 8 same-plane neighbours."""
    fp = np.ones((3, 3), bool)
    fp[1, 1] = False
    return m - median_filter(m, footprint=fp, mode="nearest")


def main():
    print("PRE-REGISTERED CRITERION")
    print(f"  K = {K}, one-sided; C_MED = {C_MED:.4f}")
    print("  implied FPR/plane/ISO under a Gaussian null = 0.0081 px")
    print(f"  defect = flagged in >= {RECUR_MIN} of 11 ISO groups")
    print("  canonical frame = rawpy raw_image_visible\n")

    dirs = sorted(
        os.path.join(ROOT, d)
        for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d))
    )

    hot_count = None
    cold_count = None
    per_iso = []
    geom = None

    for d in dirs:
        files = sorted(
            os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".arw")
        )
        iso = iso_of(files[0])
        files = files[DROP_STABILISATION:]
        t_n = len(files)
        means, g = load_mean(files)
        if geom is None:
            geom = g
            shp = means["R"].shape
            hot_count = {n: np.zeros(shp, np.uint8) for n, _, _ in PLANES}
            cold_count = {n: np.zeros(shp, np.uint8) for n, _, _ in PLANES}

        s_pred = C_MED * sigma_frame_dn(iso) / np.sqrt(t_n)
        rec = {
            "iso": iso,
            "dir": os.path.basename(d),
            "frames": t_n,
            "sigma_frame_model_dn": sigma_frame_dn(iso),
            "sigma_pred_dn": float(s_pred),
            "planes": {},
        }
        for n, _, _ in PLANES:
            e = excess(means[n])
            med = float(np.median(e))
            s_obs = float(np.median(np.abs(e - med)) * 1.4826)
            d_e = e - med
            hot_a = int(np.count_nonzero(d_e > K * s_pred))
            cold_a = int(np.count_nonzero(d_e < -K * s_pred))
            hb = d_e > K * s_obs
            cb = d_e < -K * s_obs
            hot_count[n] += hb
            cold_count[n] += cb
            rec["planes"][n] = {
                "sigma_obs_dn": s_obs,
                "F_obs_over_pred": s_obs / float(s_pred),
                "median_excess_dn": med,
                "flag_A_hot": hot_a,
                "flag_A_cold": cold_a,
                "flag_B_hot": int(hb.sum()),
                "flag_B_cold": int(cb.sum()),
                "n_pixels": int(e.size),
            }
            del e, hb, cb, d_e
        g1 = rec["planes"]["G1"]
        print(
            f"ISO {iso:5d} T={t_n}  s_pred {s_pred:6.4f}  "
            f"s_obs {g1['sigma_obs_dn']:6.4f}  F {g1['F_obs_over_pred']:6.2f}  "
            f"A hot {g1['flag_A_hot']:8d}  B hot {g1['flag_B_hot']:7d}  "
            f"B cold {g1['flag_B_cold']:7d}"
        )
        per_iso.append(rec)
        del means

    per_iso.sort(key=lambda r: r["iso"])

    recur = {}
    for n, _, _ in PLANES:
        hh = np.bincount(hot_count[n].ravel(), minlength=12)[:12]
        cc = np.bincount(cold_count[n].ravel(), minlength=12)[:12]
        recur[n] = {
            "hot_by_groups": [int(v) for v in hh],
            "cold_by_groups": [int(v) for v in cc],
            "hot_defects": int(hh[RECUR_MIN:].sum()),
            "cold_defects": int(cc[RECUR_MIN:].sum()),
            "hot_all11": int(hh[11]),
            "cold_all11": int(cc[11]),
        }
        np.save(os.path.join(MAPDIR, f"hotcount-{n}.npy"), hot_count[n])
        np.save(os.path.join(MAPDIR, f"coldcount-{n}.npy"), cold_count[n])

    tot_px = per_iso[0]["planes"]["R"]["n_pixels"] * 4
    tot_hot = sum(recur[n]["hot_defects"] for n, _, _ in PLANES)
    tot_cold = sum(recur[n]["cold_defects"] for n, _, _ in PLANES)
    print(
        f"\nDEFECTS (>= {RECUR_MIN}/11): hot {tot_hot} "
        f"({100*tot_hot/tot_px:.4f}%)  cold {tot_cold} "
        f"({100*tot_cold/tot_px:.4f}%)  of {tot_px} px"
    )

    payload = {
        "_meta": {
            "script": "01-defect-census.py",
            "preregistered": True,
            "criterion_A": "|e - med(e)| > K*C_MED*(RN_e*g)/sqrt(T)  [model only]",
            "criterion_B": "|e - med(e)| > K*1.4826*MAD(e)           [robust]",
            "K": K,
            "C_MED": C_MED,
            "implied_fpr_per_plane_per_iso_gaussian": 0.0081,
            "recurrence_min_groups": RECUR_MIN,
            "model": {
                "gain_divisor": GAIN_DIVISOR,
                "base_iso": BASE_ISO,
                "second_base_iso": SECOND_BASE_ISO,
                "read_noise_e_low": RN_E_LOW,
                "read_noise_e_high": RN_E_HIGH,
            },
            "geometry": {
                **(geom or {}),
                "plane_shape": list(hot_count["R"].shape),
                "cfa_offsets": {n: [dy, dx] for n, dy, dx in PLANES},
                "canonical_decoder": "rawpy raw_image_visible",
                "note": "SYNTHESIS fact 691: rawler reports a 2-column-wider "
                "visible area. A consumer in rawler's frame must check "
                "plane_shape before indexing this map.",
            },
        },
        "per_iso": per_iso,
        "recurrence": recur,
        "totals": {
            "hot_defects": tot_hot,
            "cold_defects": tot_cold,
            "sensor_pixels": tot_px,
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
