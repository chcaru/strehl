"""02 -- Gate 1a: does fact 35's mechanism emerge from the simulator?

Fact 35: argmax's noise excess tracks the focus operator's centre-tap
sensitivity fraction phi (rho = +0.918 / +0.894 on two real stacks), **not**
its support radius (rho = -0.170 / -0.243, not significant), and a 3x3 Sobel --
zero centre tap -- shows no excess (0.9952x).

Nothing about phi is built into the simulator.  The forward model knows about
photons, apertures, a Bayer grid and a read chain; it has never heard of a
focus operator.  If the coupling comes out anyway, the noise-plus-focus-volume
machinery is faithful.

`coc_px_per_frame` is SWEPT, not fitted, so the coupling cannot be tuned into
existence.  Two scenes are used because facts 61/62 rule that a fronto-parallel
plant cannot express a spatial-support turnover: the tilted plane is the
control for that.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/02-gate1a-phi.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.render import render_stack                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "gate1a-phi.txt")
REAL = r"C:\dev\macro\test\109MSDCF"
REAL_ROI = S.Roi(2272, 1344, 256, 256)

# Simulated widths stop at 97.  Verified against the committed
# `sweep-109MSDCF-coupled.csv`: for all 16 treatments the minimum ratio over
# widths <= 97 equals the minimum over the full list, so `floor` -- and hence
# `excess` -- is unchanged by the truncation.  Checked, not assumed.
WIDTHS = [1, 3, 5, 7, 9, 13, 17, 21, 25, 33, 41, 49, 65, 81, 97]
ROI_HW = 256
SUPERSAMPLE = 3
COC_SWEEP = [0.25, 0.5, 1.0, 2.0]
SEEDS = [1, 2]

TARGET_RHO_PHI = 0.70
TARGET_TEN_W0_EXCESS = 0.02
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def verify_width_truncation():
    """Discipline: check the claim that stopping at width 97 does not move the
    floor, rather than asserting it."""
    import csv
    p = os.path.join(HERE, "..", "..", "m9-support", "data",
                     "sweep-109MSDCF-coupled.csv")
    by = {}
    for r in csv.DictReader(open(p)):
        if r["roi_kind"] != "flat":
            continue
        by.setdefault(r["measure"], {}).setdefault(int(r["width"]), []) \
          .append(float(r["ratio"]))
    worst = 0.0
    for m, d in by.items():
        pooled = {w: sum(v) / len(v) for w, v in d.items()}
        full = min(pooled.values())
        trunc = min(v for w, v in pooled.items() if w <= max(WIDTHS))
        worst = max(worst, trunc - full)
    return worst


def measure_stack(luma, val, noise, margin, reach, phi_luma):
    treatments = F.design(False)
    out = {}
    for m in treatments:
        _, _, phi, _ = F.phi_for(m, phi_luma, noise, reach)
        rows = F.sweep_measure(m, luma, val, val[val.shape[0] // 2], noise,
                               margin, WIDTHS)
        rr = np.array([r["ratio"] for r in rows])
        out[m.name] = dict(phi=phi, c1=float(rr[0]), floor=float(rr.min()),
                           excess=float(rr[0] - rr.min()),
                           support=m.support_radius,
                           speckle1=rows[0]["speckle"],
                           winners1=rows[0]["distinct_winners"],
                           w17=float(rr[WIDTHS.index(17)]),
                           speckle17=rows[WIDTHS.index(17)]["speckle"])
    return out


def report(tag, res):
    names = sorted(res, key=lambda n: -res[n]["phi"])
    phis = [res[n]["phi"] for n in names]
    exc = [res[n]["excess"] for n in names]
    sup = [res[n]["support"] for n in names]
    rp = stats.spearmanr(phis, exc)
    rs = stats.spearmanr(sup, exc)
    say(f"  {'measure':<14} {'phi':>9} {'c(1)':>8} {'floor':>8} {'excess':>8}")
    for n in names:
        r = res[n]
        say(f"  {n:<14} {r['phi']:>9.5f} {r['c1']:>8.4f} {r['floor']:>8.4f} "
            f"{r['excess']:>8.4f}")
    say(f"  rho(phi, excess)     = {rp.statistic:+.3f}, p = {rp.pvalue:.4f}")
    say(f"  rho(support, excess) = {rs.statistic:+.3f}, p = {rs.pvalue:.4f}")
    t = res["tenengrad-w0"]
    say(f"  tenengrad-w0 (zero centre tap): c(1) = {t['c1']:.4f}, "
        f"excess = {t['excess']:.4f}")
    ok = (rp.statistic >= TARGET_RHO_PHI and rp.pvalue < 0.05
          and t["excess"] < TARGET_TEN_W0_EXCESS
          and not (rs.pvalue < 0.05 and abs(rs.statistic) > 0.5))
    say(f"  {tag}: {'PASS' if ok else 'FAIL'}")
    return ok, float(rp.statistic), float(rp.pvalue), float(rs.statistic), \
        float(rs.pvalue), t["excess"]


def main():
    t0 = time.time()
    say("Gate 1a -- fact 35's phi/excess coupling on simulated stacks")
    say(f"widths {WIDTHS}")
    w = verify_width_truncation()
    say(f"truncating the width sweep at {max(WIDTHS)} moves the real pooled "
        f"floor by at most {w:.6f} (checked against m9's committed CSV)")
    say()

    ms_all = F.design(True)
    reach = F.max_support(ms_all)
    sweep_margin = max((x - 1) // 2 for x in WIDTHS) + reach
    phi_margin = 4 * reach + 2
    margin = max(sweep_margin, phi_margin)
    tile = ROI_HW + 2 * margin
    say(f"reach {reach}; sweep margin {sweep_margin}; phi margin {phi_margin}; "
        f"green tile {tile}x{tile} -> sensor {2 * tile}x{2 * tile}")

    # Fit the three radiometric nuisance parameters on the real ROI.
    raw = S.load_real(REAL)
    iso = S.iso_of(REAL)
    _, rval = S.tiles(raw, REAL_ROI, margin)
    ref = rval[raw.shape[0] // 2]
    base_e, contrast_e = B.fit_radiometry(ref, iso)
    beta = B.fit_beta(ref)
    del raw
    say(f"fitted from real {REAL_ROI}: base {base_e:.1f} e-, "
        f"contrast {contrast_e:.1f} e- sd, beta {beta:.3f}")
    say(f"  (real ROI mean {ref.mean():.2f} DN, sd {ref.std():.4f} DN)")

    B.set_supersample(SUPERSAMPLE)
    hw = (2 * tile, 2 * tile)
    nm0 = F.NoiseModel.for_iso(iso)
    target_struct = contrast_e * nm0.gain_dn_per_e
    tc = time.time()
    contrast_e = B.calibrate_contrast(B.cfg_109(1.0, seed=1, channels="green"),
                                      hw, base_e, contrast_e, beta, 101,
                                      target_struct, iso)
    say(f"calibrated latent contrast {contrast_e:.1f} e- sd so the in-focus "
        f"green structure sd matches {target_struct:.3f} DN "
        f"({time.time() - tc:.0f}s)")
    say()
    grid = []
    for scene_kind in ("flat", "tilt6"):
        for coc in COC_SWEEP:
            for seed in SEEDS:
                cfg = B.cfg_109(coc, seed=seed, channels="green")
                sc = (B.flat_scene(cfg, hw, base_e, contrast_e, beta,
                                   focus_index=11.0, seed=100 + seed)
                      if scene_kind == "flat"
                      else B.tilt_scene(cfg, hw, base_e, contrast_e, beta,
                                        span_frames=6.0, seed=100 + seed))
                tr = time.time()
                st = render_stack(sc, cfg)
                roi = S.Roi(margin, margin, ROI_HW, ROI_HW)
                luma, val = S.tiles(st.frames, roi, margin)
                noise = F.NoiseModel.for_iso(iso)
                o = margin - sweep_margin
                sl = luma[:, o:luma.shape[1] - o, o:luma.shape[2] - o]
                o2 = margin - phi_margin
                pl = luma[:, o2:luma.shape[1] - o2, o2:luma.shape[2] - o2]
                say(f"--- {scene_kind}, coc {coc} px/frame, seed {seed} "
                    f"(render {time.time() - tr:.0f}s) ---")
                say(f"  simulated ROI mean {val[11].mean():.2f} DN, "
                    f"sd {val[11].std():.4f} DN "
                    f"(real {ref.mean():.2f} / {ref.std():.4f})")
                res = measure_stack(sl, val, noise, sweep_margin, reach, pl)
                ok, rp, pp, rs, ps, te = report(
                    f"{scene_kind}/coc{coc}/seed{seed}", res)
                grid.append((scene_kind, coc, seed, ok, rp, pp, rs, ps, te))
                say()

    say("=" * 72)
    say(f"{'scene':<8} {'coc':>5} {'seed':>5} {'rho_phi':>8} {'p':>8} "
        f"{'rho_sup':>8} {'p':>8} {'tenw0':>7}  verdict")
    for (k, c, s, ok, rp, pp, rs, ps, te) in grid:
        say(f"{k:<8} {c:>5} {s:>5} {rp:>+8.3f} {pp:>8.4f} {rs:>+8.3f} "
            f"{ps:>8.4f} {te:>7.4f}  {'PASS' if ok else 'FAIL'}")
    n_pass = sum(1 for g in grid if g[3])
    if n_pass == len(grid):
        v = "PASS"
    elif n_pass:
        v = "PARTIAL"
    else:
        v = "FAIL"
    say(f"GATE 1a: {v} ({n_pass}/{len(grid)} configurations)  "
        f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
