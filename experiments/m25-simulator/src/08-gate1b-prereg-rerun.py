"""08 -- Gate 1b, the PRE-REGISTERED five axes, rerun with measured placement.

`03-gate1b-levels.py` ran the pre-registered gate and returned PARTIAL: all
five axes individually reachable, none jointly.  The cause was diagnosed and
is mine, not the simulator's -- that script placed the plane's best focus on
frame 11, which is the very frame the m9 harness divides by, so the winner IS
the reference frame and the ratio floors at 1.000 by construction.  The real
ROIs peak at frames 10/10/10/7 and never at 11.

`06-gate1b-measured-placement.py` fixed the placement but scored a DIFFERENT
set of axes (c(1), floor, excess across all 16 measures).  Changing the gate
after seeing the data is exactly what pre-registration exists to prevent, so
that result cannot stand in for this one.  This script is the pre-registered
gate, unchanged, with the placement bug fixed:

    argmax_w1, mean, placebo, argmax_w17, speckle_w17

on m9's own ROI `2272,1344` (which is fact 19's and fact 23's ROI), against
m9's own committed CSV where it has the number and M2's where it does not.
`coc_px_per_frame` is the one free parameter and it is swept, not fitted.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/08-gate1b-prereg-rerun.py
"""

from __future__ import annotations

import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.render import render_stack                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "gate1b-prereg-rerun.txt")
M9CSV = os.path.join(HERE, "..", "..", "m9-support", "data",
                     "sweep-109MSDCF-coupled.csv")
REAL = r"C:\dev\macro\test\109MSDCF"
ROI = (2272, 1344)
ROI_HW = 256
WIDTHS = [1, 3, 5, 7, 9, 13, 17, 21, 25, 33, 41, 49, 65, 81, 97]
SUPERSAMPLE = 3
COC_SWEEP = [0.5, 1.0, 1.5, 2.0, 3.0]
MEASURE = "ring-1-3"
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def m9_row(width):
    for r in csv.DictReader(open(M9CSV)):
        if (r["roi"] == f"{ROI[0]},{ROI[1]},{ROI_HW},{ROI_HW}"
                and r["measure"] == MEASURE and int(r["width"]) == width):
            return r
    raise KeyError(width)


def plain_mean_ratio(value, single_sigma):
    _, sig = F.mean_and_sigma(value.mean(axis=0))
    return sig / single_sigma


def placebo_ratio(value, idx, single_sigma, seed):
    rg = np.random.default_rng(seed)
    flat = idx.reshape(-1).copy()
    rg.shuffle(flat)
    perm = flat.reshape(idx.shape)
    out = np.take_along_axis(value, perm[None, ...], axis=0)[0]
    _, sig = F.mean_and_sigma(out)
    return sig / single_sigma


def main():
    t0 = time.time()
    say("Gate 1b -- PRE-REGISTERED five axes, rerun with MEASURED placement")
    say(f"ROI {ROI[0]},{ROI[1]}; measure {MEASURE}; widths {WIDTHS}")
    say()

    ms_all = F.design(True)
    reach = F.max_support(ms_all)
    margin = max((x - 1) // 2 for x in WIDTHS) + reach
    tile = ROI_HW + 2 * margin
    hw = (2 * tile, 2 * tile)

    raw = S.load_real(REAL)
    iso = S.iso_of(REAL)
    K = raw.shape[0]
    nm = F.NoiseModel.for_iso(iso)
    luma_r, val_r = S.tiles(raw, S.Roi(ROI[0], ROI[1], ROI_HW, ROI_HW), margin)
    meas = [m for m in F.design(False) if m.name == MEASURE][0]
    fr = np.array([meas.compute(luma_r[k], nm)[margin:-margin,
                                               margin:-margin].mean()
                   for k in range(K)])
    peak = int(np.argmax(fr))
    level = np.array([val_r[k].mean() for k in range(K)])
    ref = val_r[K // 2]
    del raw, luma_r, val_r
    base_e, contrast_e = B.fit_radiometry(ref, iso)
    beta = B.fit_beta(ref)
    gain = level / level[K // 2]

    r1, r17 = m9_row(1), m9_row(17)
    targets = {
        "argmax_w1": (float(r1["ratio"]), 0.05,
                      "m9 CSV, this ROI (like-for-like)"),
        "mean": (0.534, 0.05, "fact 19, M2 (different harness)"),
        "placebo": (0.981, 0.05, "fact 19, M2 (different harness)"),
        "argmax_w17": (float(r17["ratio"]), 0.05,
                       "m9 CSV, this ROI (like-for-like)"),
        "speckle_w17_pp": (100.0 * float(r17["speckle"]), 2.0,
                           "m9 CSV, this ROI (like-for-like)"),
    }
    say("MEASURED on the real stack (scene placement, not physics):")
    say(f"  focus peak frame {peak} (m9 divides by frame {K // 2}); "
        f"mean {ref.mean():.2f} DN; sd {ref.std():.4f} DN; "
        f"level p-p {100 * (gain.max() - gain.min()):.3f}%")
    say(f"  fitted base {base_e:.1f} e-, contrast {contrast_e:.1f} e-, "
        f"beta {beta:.3f}")
    say("targets:")
    for k, (t, tol, src) in targets.items():
        say(f"  {k:<16} {t:>9.4f} +/- {tol:<5} [{src}]")
    say()

    B.set_supersample(SUPERSAMPLE)
    target_struct = contrast_e * nm.gain_dn_per_e
    rows = []
    for coc in COC_SWEEP:
        cfg = B.cfg_109(coc, n_frames=K, seed=1, channels="green")
        ce = B.calibrate_contrast(cfg, hw, base_e, contrast_e, beta, 101,
                                  target_struct, iso)
        tr = time.time()
        sc = B.flat_scene(cfg, hw, base_e, ce, beta,
                          focus_index=float(peak), seed=101)
        st = render_stack(sc, cfg, gain_series=gain)
        roi = S.Roi(margin, margin, ROI_HW, ROI_HW)
        luma, val = S.tiles(st.frames, roi, margin)
        single = val[K // 2]
        srows = F.sweep_measure(meas, luma, val, single, nm, margin, WIDTHS)
        rr = np.array([r["ratio"] for r in srows])
        i17 = WIDTHS.index(17)
        ss = srows[0]["single_sigma"]
        r = dict(coc=coc, argmax_w1=float(rr[0]), argmax_w17=float(rr[i17]),
                 floor=float(rr.min()),
                 speckle_w1_pp=100.0 * srows[0]["speckle"],
                 speckle_w17_pp=100.0 * srows[i17]["speckle"],
                 winners_w1=srows[0]["distinct_winners"],
                 mean=plain_mean_ratio(val, ss),
                 placebo=placebo_ratio(val, srows[0]["index"], ss, 4242),
                 mean_dn=float(single.mean()), sd=float(single.std()),
                 secs=time.time() - tr)
        n_ok = sum(1 for k, (t, tol, _) in targets.items()
                   if abs(r[k] - t) <= tol)
        r["n_ok"] = n_ok
        rows.append(r)
        say(f"coc {coc:<5}: argmax(1) {r['argmax_w1']:.4f}  "
            f"argmax(17) {r['argmax_w17']:.4f}  floor {r['floor']:.4f}  "
            f"mean {r['mean']:.4f}  placebo {r['placebo']:.4f}  "
            f"speckle {r['speckle_w1_pp']:.2f}% -> {r['speckle_w17_pp']:.3f}%"
            f"  [{n_ok}/5]  [{r['secs']:.0f}s]")

    say()
    say("=" * 78)
    say(f"  {'axis':<16} {'target':>9} {'tol':>6} {'best':>9} {'at':>8}  ok")
    per_axis = {}
    for k, (tgt, tol, _s) in targets.items():
        best = min(rows, key=lambda r: abs(r[k] - tgt))
        ok = abs(best[k] - tgt) <= tol
        per_axis[k] = ok
        say(f"  {k:<16} {tgt:>9.4f} {tol:>6.3f} {best[k]:>9.4f} "
            f"{'coc' + str(best['coc']):>8}  {'yes' if ok else 'NO'}")
    joint = [r for r in rows if r["n_ok"] == 5]
    say()
    say(f"configurations satisfying ALL five axes at once: {len(joint)}"
        + (f"  (coc {[r['coc'] for r in joint]})" if joint else ""))
    best = max(rows, key=lambda r: r["n_ok"])
    say(f"best single configuration: coc {best['coc']} at {best['n_ok']}/5")
    for k, (t, tol, _s) in targets.items():
        d = best[k] - t
        say(f"    {k:<16} sim {best[k]:>9.4f} vs {t:>9.4f}  "
            f"delta {d:+.4f}  {'ok' if abs(d) <= tol else 'MISS'}")
    n_axes = sum(per_axis.values())
    verdict = "PASS" if joint else ("PARTIAL" if best["n_ok"] >= 3 else "FAIL")
    say(f"GATE 1b (pre-registered axes): {verdict} "
        f"({n_axes}/5 reachable, best joint {best['n_ok']}/5)  "
        f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    keys = ["coc", "argmax_w1", "argmax_w17", "floor", "mean", "placebo",
            "speckle_w1_pp", "speckle_w17_pp", "winners_w1", "mean_dn", "sd",
            "n_ok"]
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n\ncsv\n" + ",".join(keys) + "\n")
        for r in rows:
            fh.write(",".join(f"{r[k]}" for k in keys) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
