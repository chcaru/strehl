"""06 -- Gate 1b, second attempt: measure the scene's placement, don't assume it.

The first attempt (`03-gate1b-levels.py`) put the flat plane's best focus on
the *reference frame* (frame 11, the one m9 divides by).  That made the merged
image's floor exactly 1.000 by construction, while the real corpus floors at
1.065.  The construction was leaking a 1.0 into the answer.

The real stack says where its ROIs actually sit.  Measured here, on
109MSDCF's four m9 flat ROIs:

  * the frame at which the ring-1-3 focus response peaks (the ROI's depth),
  * the per-frame mean level over the ROI (fact 180's photometric drift, as a
    measured series rather than a model),
  * the through-focus spatial-sd curve (the defocus MTF's signature).

Only ONE parameter is fitted: `coc_px_per_frame`, by least squares against
that sd curve.  That curve is radiometric.  Everything Gate 1b then scores --
c(1), the floor, the excess, speckle -- is a noise-selection property, so the
fit and the test do not share a channel.

The comparison is m9's own pooled table: four ROIs, sixteen measures, the same
widths, the same harness (`01-port-check.py` proves the port reproduces m9's
committed numbers on real files).

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/06-gate1b-measured-placement.py
"""

from __future__ import annotations

import collections
import csv
import dataclasses
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
OUT = os.path.join(HERE, "..", "data", "gate1b-measured-placement.txt")
M9CSV = os.path.join(HERE, "..", "..", "m9-support", "data",
                     "sweep-109MSDCF-coupled.csv")
REAL = r"C:\dev\macro\test\109MSDCF"
ROIS = ["2272,1344", "2505,441", "2665,1513", "329,1353"]
ROI_HW = 256
WIDTHS = [1, 3, 5, 7, 9, 13, 17, 21, 25, 33, 41, 49, 65, 81, 97]
SUPERSAMPLE = 3
COC_GRID = np.round(np.arange(0.05, 1.51, 0.05), 3)
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def real_pooled():
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in csv.DictReader(open(M9CSV)):
        if r["roi_kind"] != "flat":
            continue
        by[r["measure"]][int(r["width"])].append(
            (float(r["ratio"]), float(r["speckle"])))
    out = {}
    for m, d in by.items():
        p = {w: (float(np.mean([a for a, _ in v])),
                 float(np.mean([b for _, b in v]))) for w, v in d.items()}
        ws = sorted(p)
        out[m] = dict(c1=p[1][0], speckle1=100 * p[1][1], w17=p[17][0],
                      speckle17=100 * p[17][1],
                      floor=min(p[w][0] for w in ws),
                      floor_trunc=min(p[w][0] for w in ws if w <= max(WIDTHS)))
        out[m]["excess"] = out[m]["c1"] - out[m]["floor_trunc"]
    return out


def measure_real(raw, iso, margin):
    m13 = [x for x in F.design(False) if x.name == "ring-1-3"][0]
    nm = F.NoiseModel.for_iso(iso)
    obs = {}
    for roi in ROIS:
        x, y = (int(v) for v in roi.split(","))
        luma, val = S.tiles(raw, S.Roi(x, y, ROI_HW, ROI_HW), margin)
        r = np.array([m13.compute(luma[k], nm)[margin:-margin,
                                               margin:-margin].mean()
                      for k in range(luma.shape[0])])
        lv = np.array([val[k].mean() for k in range(val.shape[0])])
        sd = np.array([val[k].std() for k in range(val.shape[0])])
        obs[roi] = dict(focus_peak=int(np.argmax(r)), level=lv, sd=sd,
                        mean=float(lv[val.shape[0] // 2]),
                        ref_sd=float(sd[val.shape[0] // 2]))
    return obs


def sim_sd_curve(cfg, hw, base_e, contrast_e, beta, peak, seed):
    sc = B.flat_scene(cfg, hw, base_e, contrast_e, beta,
                      focus_index=float(peak), seed=seed)
    st = render_stack(sc, cfg)
    return np.array([S.green_value(st.frames[k]).std()
                     for k in range(st.frames.shape[0])]), st


def main():
    t0 = time.time()
    say("Gate 1b (second attempt) -- measured scene placement, one fitted "
        "parameter")
    say()
    reach = F.max_support(F.design(True))
    margin = max((x - 1) // 2 for x in WIDTHS) + reach
    tile = ROI_HW + 2 * margin
    say(f"reach {reach}; margin {margin}; green tile {tile} -> sensor "
        f"{2 * tile}; widths {WIDTHS}")

    raw = S.load_real(REAL)
    iso = S.iso_of(REAL)
    K = raw.shape[0]
    obs = measure_real(raw, iso, margin)
    nm = F.NoiseModel.for_iso(iso)
    say()
    say("MEASURED on the real stack (this is scene placement, not physics):")
    say(f"  {'ROI':<12} {'peak':>5} {'mean DN':>9} {'sd@ref':>7} "
        f"{'sd@peak':>8} {'level p-p':>10}")
    for roi in ROIS:
        o = obs[roi]
        say(f"  {roi:<12} {o['focus_peak']:>5} {o['mean']:>9.2f} "
            f"{o['ref_sd']:>7.3f} {o['sd'][o['focus_peak']]:>8.3f} "
            f"{100 * (o['level'].max() - o['level'].min()) / o['level'].mean():>9.3f}%")
    say(f"  the m9 reference frame is {K // 2}; NO ROI peaks there, which is "
        f"why a plane placed at the reference frame floors at 1.000")

    # --- fit the single free parameter to the through-focus sd curve -------
    B.set_supersample(SUPERSAMPLE)
    hw = (2 * tile, 2 * tile)
    roi0 = ROIS[0]
    ref = obs[roi0]
    base_e, contrast0 = B.fit_radiometry(
        S.tiles(raw, S.Roi(*(int(v) for v in roi0.split(",")), ROI_HW,
                           ROI_HW), 0)[1][K // 2], iso)
    beta = B.fit_beta(S.tiles(raw, S.Roi(*(int(v) for v in roi0.split(",")),
                                         ROI_HW, ROI_HW), 0)[1][K // 2])
    del raw
    say()
    say(f"fitted radiometry on {roi0}: base {base_e:.1f} e-, "
        f"contrast {contrast0:.1f} e-, beta {beta:.3f}")

    say()
    say("fitting coc_px_per_frame to the through-focus sd curve "
        "(the ONE free parameter):")
    target = ref["sd"] / ref["sd"][ref["focus_peak"]]
    best = None
    small = (2 * (ROI_HW + 2 * 8),) * 2          # cheap: no sweep margin needed
    for coc in COC_GRID:
        cfg = B.cfg_109(float(coc), n_frames=K, seed=1, channels="green",
                        margin_px=24)
        cfg.shot = cfg.read = cfg.fpn = False
        sc = B.flat_scene(cfg, small, base_e, contrast0 * 2, beta,
                          focus_index=float(ref["focus_peak"]), seed=101)
        st = render_stack(sc, cfg)
        sd = np.array([S.green_value(st.frames[k]).std() for k in range(K)])
        curve = sd / sd[ref["focus_peak"]]
        err = float(np.sqrt(np.mean((curve - target) ** 2)))
        if best is None or err < best[1]:
            best = (float(coc), err, curve)
    coc, err, curve = best
    say(f"  best coc = {coc} px/frame, RMS shape error {err:.4f} "
        f"(curve normalised at the peak frame)")
    say("  frame:   " + " ".join(f"{k:5d}" for k in range(K)))
    say("  real :   " + " ".join(f"{v:5.3f}" for v in target))
    say("  sim  :   " + " ".join(f"{v:5.3f}" for v in curve))
    say("  NOTE: the real curve is structure+noise, the fit curve is "
        "noise-free structure only; the residual is dominated by that.")

    # --- the actual gate: m9's pooled table, like for like ----------------
    say()
    say("=" * 78)
    say(f"rendering four ROIs with MEASURED placement at coc = {coc}")
    real = real_pooled()
    pooled = collections.defaultdict(lambda: collections.defaultdict(list))
    for i, roi in enumerate(ROIS):
        o = obs[roi]
        cfg = B.cfg_109(coc, n_frames=K, seed=1 + i, channels="green")
        gain = o["level"] / o["level"][K // 2]
        b_e = o["mean"] / nm.gain_dn_per_e
        struct = np.sqrt(max(o["ref_sd"] ** 2
                             - 0.5 * (nm.gain_dn_per_e * o["mean"]
                                      + (nm.read_noise_e
                                         * nm.gain_dn_per_e) ** 2), 1.0))
        ce = struct / nm.gain_dn_per_e
        # The ROI is defocused by |ref - peak| frames at the reference frame,
        # so a contrast fitted from the observed sd under-shoots.  One render
        # measures the attenuation; the correction is exact to first order
        # because the optical chain is linear in contrast.
        tr = time.time()
        sc = B.flat_scene(cfg, hw, b_e, ce, beta,
                          focus_index=float(o["focus_peak"]), seed=200 + i)
        st = render_stack(sc, cfg, gain_series=gain)
        got = float(S.green_value(st.frames[K // 2]).std())
        k2 = np.sqrt(max(o["ref_sd"] ** 2 - 0.5 * (
            nm.gain_dn_per_e * o["mean"]
            + (nm.read_noise_e * nm.gain_dn_per_e) ** 2), 1.0)
            / max(got ** 2 - 0.5 * (nm.gain_dn_per_e * o["mean"] + (
                nm.read_noise_e * nm.gain_dn_per_e) ** 2), 1.0))
        sc = B.flat_scene(cfg, hw, b_e, ce * k2, beta,
                          focus_index=float(o["focus_peak"]), seed=200 + i)
        st = render_stack(sc, cfg, gain_series=gain)
        r = S.Roi(margin, margin, ROI_HW, ROI_HW)
        luma, val = S.tiles(st.frames, r, margin)
        single = val[K // 2]
        say(f"  {roi:<12} sim ref-frame mean {single.mean():7.2f} sd "
            f"{single.std():6.3f}  (real {o['mean']:7.2f} / {o['ref_sd']:6.3f})"
            f"  [{time.time() - tr:.0f}s]")
        for m in F.design(False):
            rows = F.sweep_measure(m, luma, val, single, nm, margin, WIDTHS)
            for row in rows:
                pooled[m.name][row["width"]].append(
                    (row["ratio"], row["speckle"]))

    say()
    say(f"  {'measure':<14} {'c(1) sim':>9} {'real':>8} {'floor sim':>10} "
        f"{'real':>8} {'exc sim':>8} {'real':>8} {'spk1 sim':>9} {'real':>7}")
    rows_out = []
    for m in sorted(pooled, key=lambda n: -real[n]["c1"]):
        p = {w: (float(np.mean([a for a, _ in v])),
                 float(np.mean([b for _, b in v])))
             for w, v in pooled[m].items()}
        ws = sorted(p)
        c1 = p[1][0]
        fl = min(p[w][0] for w in ws)
        rr = real[m]
        rows_out.append((m, c1, rr["c1"], fl, rr["floor_trunc"], c1 - fl,
                         rr["excess"], 100 * p[1][1], rr["speckle1"],
                         p[17][0], rr["w17"], 100 * p[17][1],
                         rr["speckle17"]))
        say(f"  {m:<14} {c1:>9.4f} {rr['c1']:>8.4f} {fl:>10.4f} "
            f"{rr['floor_trunc']:>8.4f} {c1 - fl:>8.4f} {rr['excess']:>8.4f} "
            f"{100 * p[1][1]:>8.2f}% {rr['speckle1']:>6.2f}%")

    say()
    c1s = np.array([r[1] for r in rows_out])
    c1r = np.array([r[2] for r in rows_out])
    exs = np.array([r[5] for r in rows_out])
    exr = np.array([r[6] for r in rows_out])
    fls = np.array([r[3] for r in rows_out])
    flr = np.array([r[4] for r in rows_out])
    say(f"c(1):    median |sim-real| = {np.median(np.abs(c1s - c1r)):.4f}, "
        f"max {np.max(np.abs(c1s - c1r)):.4f}")
    say(f"floor:   median |sim-real| = {np.median(np.abs(fls - flr)):.4f}, "
        f"max {np.max(np.abs(fls - flr)):.4f}")
    say(f"excess:  median |sim-real| = {np.median(np.abs(exs - exr)):.4f}, "
        f"max {np.max(np.abs(exs - exr)):.4f}")
    from scipy import stats as st_
    say(f"excess:  sim-vs-real Spearman rho = "
        f"{st_.spearmanr(exs, exr).statistic:+.3f}, "
        f"Pearson r = {st_.pearsonr(exs, exr).statistic:+.3f}, "
        f"slope = {np.polyfit(exr, exs, 1)[0]:.3f}")
    ok_c1 = float(np.median(np.abs(c1s - c1r))) <= 0.05
    ok_ex = float(np.median(np.abs(exs - exr))) <= 0.05
    ok_fl = float(np.median(np.abs(fls - flr))) <= 0.05
    say(f"axes: c(1) {'ok' if ok_c1 else 'MISS'}, "
        f"floor {'ok' if ok_fl else 'MISS'}, "
        f"excess {'ok' if ok_ex else 'MISS'}  "
        f"(tolerance: median absolute deviation <= 0.05 ratio units)")
    n = sum([ok_c1, ok_ex, ok_fl])
    say(f"GATE 1b (measured placement): "
        f"{'PASS' if n == 3 else 'PARTIAL' if n else 'FAIL'} ({n}/3)  "
        f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
        fh.write("\ncsv\nmeasure,c1_sim,c1_real,floor_sim,floor_real,"
                 "excess_sim,excess_real,speckle1_sim,speckle1_real,"
                 "w17_sim,w17_real,speckle17_sim,speckle17_real\n")
        for r in rows_out:
            fh.write(",".join(str(x) for x in r) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
