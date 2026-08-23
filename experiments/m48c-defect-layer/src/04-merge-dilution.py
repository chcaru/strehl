r"""M48c script 04 -- does the shipped merge dilute a point defect? Measured E2E.

THE QUESTION (brief item 3). A hot pixel is fixed in SENSOR coordinates while
the subject moves under alignment, so in a merged output it should land on
different scene points in different frames and be diluted. M29 priced that for
DUST and got D = 0.999 at n_eff = 3, but its dilution table starts at a defect
radius of sigma_d = 5 px. A hot pixel is a POINT defect, ~1 px, and a 0.15-0.22
px inter-frame displacement is 20% of 1 px against 2% of 10 px. That is a
different regime and M29 did not cover it. M22 section 7 lists smearing under
warp as "not tested at all", and SYNTHESIS section 8 still carries "the
trail-smearing half of the original risk stands unmeasured".

WHAT I READ IN THE CODE BEFORE MEASURING, so the reader can judge the result:
`strehl merge --help` and `main.rs:98` both say "It does not yet align,
deconvolve, reject outliers, or model occlusion." If that is true of the running
binary then D = 1 EXACTLY and by construction, because every frame contributes
the same sensor pixel to the same output pixel. This script exists to test that
against the binary rather than against its documentation -- this project has
been bitten by stale doc comments (fact 581) and by a doc comment describing a
sensor that does not exist.

    D = (excess at defects in the MERGED output, rescaled to DN)
        / (excess at the same defects in the UNALIGNED mean of all frames)

D = 1 means no suppression whatsoever; a selector is D = 1 by definition.

TWO CONFOUNDS I SEPARATE RATHER THAN AVERAGE OVER.

1. CFA BINNING IS NOT ESTIMATOR DILUTION. The output is "binned from one 2x2
   quad per pixel", so its G channel is (G1+G2)/2. A defect living in G1 alone
   therefore arrives at HALF amplitude for a reason that has nothing to do with
   the merge -- it is the demosaic bin, and it would happen with one frame. So
   D is measured on the R and B planes ONLY, where the quad-to-channel map is
   1:1, and the green halving is reported separately as its own mechanism.

2. THE TWO DECODERS DISAGREE (SYNTHESIS fact 691). The pipeline is `rawler` and
   reports 3516 x 2344 per plane; this map is `rawpy` and is 2344 x 3514 -- two
   plane columns apart. The offset is MEASURED here by scanning candidate
   offsets and taking the one that maximises defect contrast, rather than
   assumed. If the map did not carry its own geometry this would be a silent
   two-column mis-index that quietly reports D = 0.

D:\personal\macro is read-only source data. This script only reads it.
"""

import json
import os
import sys

import numpy as np
import rawpy
import tifffile
from scipy.ndimage import median_filter

STACK = r"D:\personal\macro\coffee-bubbles"
PLANES = (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1))
# TIFF channel index for each plane. G1/G2 both bin into channel 1.
CHAN = {"R": 0, "G1": 1, "G2": 1, "B": 2}
BINNED_1TO1 = ("R", "B")
RECUR_MIN = 6
N_ISO = 11
OFFSET_SCAN = range(-4, 5)
RNG = np.random.default_rng(48)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "merge-dilution.json")


def highpass(m):
    fp = np.ones((3, 3), bool)
    fp[1, 1] = False
    return m - median_filter(m, footprint=fp, mode="nearest")


def unaligned_mean(files):
    acc = None
    for f in files:
        with rawpy.imread(f) as rr:
            raw = rr.raw_image_visible
            if acc is None:
                acc = {
                    n: np.zeros(raw[dy::2, dx::2].shape, np.float64)
                    for n, dy, dx in PLANES
                }
            for n, dy, dx in PLANES:
                acc[n] += raw[dy::2, dx::2].astype(np.float64)
            del raw
    for n in acc:
        acc[n] /= len(files)
    return acc


def defect_coords(plane):
    """Recurring hot defects from script 02's bitmask, as (row, col)."""
    m = np.load(os.path.join(DATA, f"hotmask-{plane}.npy"))
    pc = np.array([bin(v).count("1") for v in range(1 << N_ISO)], np.uint8)
    return np.nonzero(pc[m] >= RECUR_MIN)


def main():
    tif_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not tif_path or not os.path.exists(tif_path):
        raise SystemExit("usage: 04-merge-dilution.py <merged.tiff>")
    img = tifffile.imread(tif_path).astype(np.float64)
    print(f"merged TIFF {img.shape} {img.dtype}")

    files = sorted(
        os.path.join(STACK, f)
        for f in os.listdir(STACK)
        if f.lower().endswith(".arw")
    )
    print(f"decoding {len(files)} frames for the unaligned mean ...")
    means = unaligned_mean(files)
    print(f"rawpy plane {means['R'].shape}, rawler/TIFF plane {img.shape[:2]}")

    res = {
        "stack": os.path.basename(STACK),
        "frames": len(files),
        "tiff_shape": list(img.shape),
        "rawpy_plane_shape": list(means["R"].shape),
        "planes": {},
    }

    # ---- 1. MEASURE the decoder column offset instead of assuming it. ----
    r_rows, r_cols = defect_coords("R")
    hp_out_r = highpass(img[:, :, 0])
    h, w = means["R"].shape
    scan = {}
    for off in OFFSET_SCAN:
        c = r_cols + off
        ok = (c >= 0) & (c < hp_out_r.shape[1]) & (r_rows < hp_out_r.shape[0])
        scan[off] = float(np.median(hp_out_r[r_rows[ok], c[ok]]))
    best = max(scan, key=lambda k: scan[k])
    print("\ncolumn-offset scan (median defect highpass in merged R):")
    for off in OFFSET_SCAN:
        print(f"   offset {off:+d}: {scan[off]:9.3f}" + ("   <-- best" if off == best else ""))
    res["column_offset_scan"] = {str(k): v for k, v in scan.items()}
    res["column_offset_measured"] = best

    # ---- 2. D, on the 1:1 planes only. ----
    for name in BINNED_1TO1:
        rows, cols = defect_coords(name)
        c = cols + best
        ok = (c >= 0) & (c < img.shape[1]) & (rows < img.shape[0])
        rows, c, cols = rows[ok], c[ok], cols[ok]

        hp_out = highpass(img[:, :, CHAN[name]])
        hp_mean = highpass(means[name])

        # Scale between TIFF units and DN: robust least squares on a subsample
        # of ordinary pixels, out = a*mean + b, matched through the offset.
        n = 200_000
        ry = RNG.integers(1, h - 1, n)
        rx = RNG.integers(4, w - 5, n)
        x = means[name][ry, rx]
        y = img[ry, rx + best, CHAN[name]]
        a, b = np.polyfit(x, y, 1)

        ctrl_r = RNG.integers(1, h - 1, rows.size)
        ctrl_c = RNG.integers(4, w - 5, rows.size)

        e_out = hp_out[rows, c] / a
        e_mean = hp_mean[rows, cols]
        e_out_ctrl = hp_out[ctrl_r, ctrl_c + best] / a
        e_mean_ctrl = hp_mean[ctrl_r, ctrl_c]

        d_mean = float(np.mean(e_out) - np.mean(e_out_ctrl)) / float(
            np.mean(e_mean) - np.mean(e_mean_ctrl)
        )
        d_med = float(np.median(e_out) - np.median(e_out_ctrl)) / float(
            np.median(e_mean) - np.median(e_mean_ctrl)
        )
        res["planes"][name] = {
            "n_defects": int(rows.size),
            "tiff_per_dn": float(a),
            "tiff_offset": float(b),
            "merged_excess_dn_mean": float(np.mean(e_out)),
            "merged_excess_dn_median": float(np.median(e_out)),
            "merged_control_mean": float(np.mean(e_out_ctrl)),
            "unaligned_excess_dn_mean": float(np.mean(e_mean)),
            "unaligned_excess_dn_median": float(np.median(e_mean)),
            "unaligned_control_mean": float(np.mean(e_mean_ctrl)),
            "D_mean": d_mean,
            "D_median": d_med,
        }
        p = res["planes"][name]
        print(
            f"\nplane {name}: n={p['n_defects']}, TIFF/DN scale a={a:.4f}\n"
            f"  merged   excess {p['merged_excess_dn_mean']:8.4f} DN "
            f"(control {p['merged_control_mean']:7.4f})\n"
            f"  unaligned excess {p['unaligned_excess_dn_mean']:8.4f} DN "
            f"(control {p['unaligned_control_mean']:7.4f})\n"
            f"  D(mean) = {d_mean:.4f}   D(median) = {d_med:.4f}"
        )

    # ---- 3. The green binning, reported as a SEPARATE mechanism. ----
    g_rows, g_cols = defect_coords("G1")
    c = g_cols + best
    ok = (c >= 0) & (c < img.shape[1]) & (g_rows < img.shape[0])
    hp_out_g = highpass(img[:, :, 1])
    hp_g1 = highpass(means["G1"])
    n = 200_000
    ry = RNG.integers(1, h - 1, n)
    rx = RNG.integers(4, w - 5, n)
    ag, _ = np.polyfit(means["G1"][ry, rx], img[ry, rx + best, 1], 1)
    ctrl_r = RNG.integers(1, h - 1, int(ok.sum()))
    ctrl_c = RNG.integers(4, w - 5, int(ok.sum()))
    g_out = float(
        np.mean(hp_out_g[g_rows[ok], c[ok]]) / ag
        - np.mean(hp_out_g[ctrl_r, ctrl_c + best]) / ag
    )
    g_in = float(
        np.mean(hp_g1[g_rows[ok], g_cols[ok]]) - np.mean(hp_g1[ctrl_r, ctrl_c])
    )
    res["green_binning"] = {
        "n_defects_G1": int(ok.sum()),
        "merged_G_excess_dn": g_out,
        "unaligned_G1_excess_dn": g_in,
        "ratio": g_out / g_in if g_in else None,
        "note": "expected ~0.5 from (G1+G2)/2 binning alone, NOT estimator "
        "dilution; a G1-only defect is halved by the CFA bin",
    }
    print(
        f"\nGREEN BINNING (separate mechanism): merged {g_out:.4f} DN vs "
        f"G1 {g_in:.4f} DN, ratio {res['green_binning']['ratio']:.4f} "
        f"(~0.5 expected from the quad bin, not from the merge)"
    )

    res["_meta"] = {
        "script": "04-merge-dilution.py",
        "D_definition": "merged defect excess / unaligned-mean defect excess, "
        "both local-8-neighbour-median highpassed, both control-subtracted",
        "why_R_and_B_only": "the TIFF G channel bins G1+G2, which halves a "
        "single-plane green defect for reasons unrelated to the estimator",
        "decoder_note": "SYNTHESIS fact 691; column offset measured, not assumed",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
