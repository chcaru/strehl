"""M122 — the blotch response A/B, per stack.

`experiments/ORCH-drift-check/photometric_ab.py` generalised to any stack, with
its STATISTIC and its WINDOW-SELECTION RULE unchanged (that instrument is cited
by SYNTHESIS fact 1637 and is not edited in place). What is added here:

  * every stack in the corpus rather than M116's three;
  * a TEXTURED window set and its ratio `T12` -- the blur control, which the
    published instrument did not compute;
  * a POWER PLANT for that blur control (a real gaussian blur must make it
    fire), because a control that cannot fail is arithmetic, not evidence
    (AGENTS.md rule 20);
  * per-window records, so overlap and spatial spread are visible in the data.

  A0 = default merge            (--gate 4)
  A1 = default merge + --photometric  (--gate 4), on the SAME frozen warp map

Windows come from the SYMMETRIC MEAN of the two arms, so neither arm chooses the
pixels it is judged on (SYNTHESIS discipline 831, fact 1630).

Commissioned in-run with three controls per stack:
  NULL    A0 vs A0            must be exactly 1.0000
  PLANT+  A0+voronoi vs A0    must be > 1.30
  PLANT-  A0 vs A0+voronoi    must be < 0.77   <- the direction under test
PLANT- is the one that matters: the claim is a REDUCTION, and an instrument that
can only detect an increase cannot support it.

Reads only. Writes only under C:\\dev\\strehl-out\\M122. Never touches D:\\.
"""

import json
import os

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

ROOT = r"C:\dev\strehl-out\M122\measure"
OUT = r"C:\dev\strehl-out\M122"

S = 256
BORDER = 400
STRIDE = 128
NWIN = 12
BLUR_SIGMA = 0.5


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, "%s read as %s, expected uint16 -- refusing" % (p, a.dtype)
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def hf(win):
    lap = (
        -4 * win[1:-1, 1:-1]
        + win[:-2, 1:-1]
        + win[2:, 1:-1]
        + win[1:-1, :-2]
        + win[1:-1, 2:]
    )
    return float(np.sqrt((lap ** 2).mean()))


_YY, _XX = np.mgrid[0:S, 0:S]
_B = np.stack([np.ones(S * S), _XX.ravel(), _YY.ravel()], axis=1)
_PINV = np.linalg.pinv(_B)


def sdd(win):
    """sd after removing a best-fit plane: plateau offsets, not the overall ramp."""
    f = win.ravel()
    return float((f - _B @ (_PINV @ f)).std())


def voronoi_plant(win, amp, seed=20260826):
    """Patchy per-region level offsets -- the shape the mechanism predicts."""
    rng = np.random.default_rng(seed)
    cx, cy = rng.integers(0, S, 40), rng.integers(0, S, 40)
    lab = ((_XX[..., None] - cx) ** 2 + (_YY[..., None] - cy) ** 2).argmin(axis=2)
    return win + rng.normal(0, amp, 40)[lab]


def scan(mean_img):
    """Every candidate window: (mean, smoothness, x, y). Unchanged from ORCH's rule."""
    H, W = mean_img.shape
    allw = []
    for y in range(BORDER, H - S - BORDER, STRIDE):
        for x in range(BORDER, W - S - BORDER, STRIDE):
            w = mean_img[y:y + S, x:x + S]
            allw.append((float(w.mean()), float(w[::8, ::8].std()), x, y))
    return allw


def smooth_set(allw):
    """ORCH's published rule: brightest 20%, then the NWIN smoothest of those."""
    bar = float(np.percentile([a[0] for a in allw], 80))
    pool = [a for a in allw if a[0] >= bar]
    pool.sort(key=lambda t: t[1])
    return [(t[2], t[3]) for t in pool[:NWIN]], bar


def textured_set(allw, min_sep=0):
    """The NWIN most textured windows. No brightness gate -- texture may be dark.

    `min_sep > 0` greedily enforces a centre separation, so the set cannot be
    NWIN shifted copies of one spot.
    """
    order = sorted(allw, key=lambda t: -t[1])
    chosen = []
    for _, _, x, y in order:
        if min_sep and any(max(abs(x - a), abs(y - b)) < min_sep for a, b in chosen):
            continue
        chosen.append((x, y))
        if len(chosen) == NWIN:
            break
    return chosen


def ratios(A, Bimg, wins):
    rh, rs, base_hf, dhf = [], [], [], []
    rec = []
    for x, y in wins:
        a = A[y:y + S, x:x + S]
        b = Bimg[y:y + S, x:x + S]
        h0, h1 = hf(a), hf(b)
        s0, s1 = sdd(a), sdd(b)
        rh.append(h1 / h0)
        rs.append(s1 / s0)
        base_hf.append(h0)
        dhf.append(h0 - h1)
        rec.append({"x": x, "y": y, "hf0": h0, "hf1": h1, "hf_ratio": h1 / h0,
                    "sdd0": s0, "sdd1": s1, "sdd_ratio": s1 / s0,
                    "lvl_ratio": float(b.mean() / a.mean())})
    return rh, rs, base_hf, dhf, rec


def main():
    subjects = sorted({f.split("__")[0] for f in os.listdir(ROOT) if f.endswith(".tif")})
    rows = []
    for subj in subjects:
        p0 = os.path.join(ROOT, "%s__A0.tif" % subj)
        p1 = os.path.join(ROOT, "%s__A1.tif" % subj)
        if not (os.path.exists(p0) and os.path.exists(p1)):
            print("=== %s ===  MISSING ARM -- excluded (E2)" % subj)
            rows.append({"stack": subj, "excluded": "E2 missing arm"})
            continue
        A0 = load(p0)
        A1 = load(p1)
        if A0.shape != A1.shape:
            print("=== %s ===  GEOMETRY MISMATCH %s vs %s" % (subj, A0.shape, A1.shape))
            rows.append({"stack": subj, "excluded": "geometry mismatch"})
            continue

        allw = scan((A0 + A1) * 0.5)
        if len(allw) < NWIN:
            rows.append({"stack": subj, "excluded": "E5 too few windows"})
            continue
        sm, bar = smooth_set(allw)
        tx = textured_set(allw, min_sep=0)
        txs = textured_set(allw, min_sep=S)

        # ---- commissioning, on this stack's own pixels ---------------------
        w0 = A0[sm[0][1]:sm[0][1] + S, sm[0][0]:sm[0][0] + S]
        amp = max(sdd(w0), 1.0) * 2.0
        wp = voronoi_plant(w0, amp)
        c = {
            "amp": amp,
            "null_hf": hf(w0) / hf(w0), "null_sd": sdd(w0) / sdd(w0),
            "up_hf": hf(wp) / hf(w0), "up_sd": sdd(wp) / sdd(w0),
            "dn_hf": hf(w0) / hf(wp), "dn_sd": sdd(w0) / sdd(wp),
        }
        ok = (abs(c["null_hf"] - 1.0) < 1e-12 and abs(c["null_sd"] - 1.0) < 1e-12
              and c["up_hf"] > 1.3 and c["dn_hf"] < 0.77
              and c["up_sd"] > 1.3 and c["dn_sd"] < 0.77)

        # ---- the measurement ------------------------------------------------
        rh, rs, bhf, dhf, rec_s = ratios(A0, A1, sm)
        th, ts, tbhf, _, rec_t = ratios(A0, A1, tx)
        ths, _, _, _, _ = ratios(A0, A1, txs)

        # ---- blur control power plant (rule 20) -----------------------------
        AB = gaussian_filter(A0, BLUR_SIGMA, mode="nearest")
        bh_s, _, _, _, _ = ratios(A0, AB, sm)
        bh_t, _, _, _, _ = ratios(A0, AB, tx)

        row = {
            "stack": subj,
            "shape": list(A0.shape),
            "n_scanned": len(allw),
            "bright_bar": bar,
            "commissioning": c,
            "commissioning_ok": bool(ok),
            "B12": float(np.median(rh)),
            "B6": float(np.median(rh[:6])),
            "Sdd12": float(np.median(rs)),
            "T12": float(np.median(th)),
            "T12sep": float(np.median(ths)),
            "hf0_smooth_median": float(np.median(bhf)),
            "hf0_textured_median": float(np.median(tbhf)),
            "dHF": float(np.median(dhf)),
            "blur_plant_smooth": float(np.median(bh_s)),
            "blur_plant_textured": float(np.median(bh_t)),
            "smooth_windows": rec_s,
            "textured_windows": rec_t,
        }
        rows.append(row)

        print("=== %s ===  %d windows scanned, brightness bar %.0f" % (subj, len(allw), bar))
        print("  commissioning (plant amp %.1f counts): null hf %.4f sdd %.4f | "
              "plant+ hf %.4f sdd %.4f | plant- hf %.4f sdd %.4f -> %s"
              % (amp, c["null_hf"], c["null_sd"], c["up_hf"], c["up_sd"],
                 c["dn_hf"], c["dn_sd"], "OK" if ok else "FAILED -- NOT INTERPRETABLE"))
        print("  B12 %.4f  B6 %.4f  Sdd12 %.4f | T12 %.4f  T12sep %.4f | "
              "hf0(smooth) %.1f  dHF %+.2f"
              % (row["B12"], row["B6"], row["Sdd12"], row["T12"], row["T12sep"],
                 row["hf0_smooth_median"], row["dHF"]))
        print("  blur plant sigma %.2f: smooth %.4f  textured %.4f  (textured must be <0.90)"
              % (BLUR_SIGMA, row["blur_plant_smooth"], row["blur_plant_textured"]))
        print()

        with open(os.path.join(OUT, "blotch-ab.json"), "w") as fh:
            json.dump(rows, fh, indent=1)

    with open(os.path.join(OUT, "blotch-ab.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    print("wrote %s" % os.path.join(OUT, "blotch-ab.json"))


if __name__ == "__main__":
    main()
