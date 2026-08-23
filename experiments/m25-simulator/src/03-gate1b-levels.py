"""03 -- Gate 1b: do the *levels* of facts 19 and 23 come out?

Fact 19: naive argmax over 22 frames is **1.253x** one unstacked frame on a
flat ROI; a plain **mean gives 0.534x**; a placebo selector with the identical
winner histogram gives **0.981x**.
Fact 23: regularising the focus field 17x17 drops noise **1.253x -> 1.075x**
and speckle **34.4% -> 0.868%**.

Gate 1a asks whether the *mechanism* is right.  This asks the harder and much
more circularity-prone question of whether the *levels* are right, and it is
deliberately reported second.

**The circularity, stated up front (rule 17).**  The m9 harness's `ratio` is
`sigma(merged) / sigma(single)` where `sigma` is the plain spatial standard
deviation of the ROI -- scene structure *and* noise, not noise alone.  Fact 19
says so itself: 1.253x raw, "~1.48x structure-corrected".  So the level
depends on the scene's texture contrast, which is FITTED here, and on the
inter-frame drift, which for 109MSDCF is **not published** and is therefore a
generator convenience.  Two of the five axes are consequently not independent
tests.  They are reported anyway, labelled, because a gross miss would still
be informative.

What is *not* fitted and is a real test:
  * `coc_px_per_frame` -- swept.
  * the *shape* of the ratio-versus-width curve, and where its floor sits.
  * the placebo's ratio, which shares the winner histogram and therefore
    cancels the histogram-shaped part of the structure term.
  * speckle, which is a property of the winner field alone and has no
    radiometric content whatsoever.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/03-gate1b-levels.py
"""

from __future__ import annotations

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
OUT = os.path.join(HERE, "..", "data", "gate1b-levels.txt")
REAL = r"C:\dev\macro\test\109MSDCF"
REAL_ROI = S.Roi(2272, 1344, 256, 256)

WIDTHS = [1, 3, 5, 7, 9, 13, 17, 21, 25, 33, 41, 49, 65, 81, 97]
ROI_HW = 256
SUPERSAMPLE = 3
COC_SWEEP = [0.25, 0.5, 1.0, 2.0, 4.0]
# 109MSDCF's own drift is unpublished.  Fact 1 gives -1.012 % over 33 frames on
# 119MSDCF and -1.835 % on another stack, and rules out a low-order polynomial
# in frame index -- so this is a *bracket over plausible rigs*, not a model.
DRIFTS = {"none": 0.0, "119-rate": -0.01012 * 21.0 / 32.0, "2x": -0.01012 * 42.0 / 32.0}
MEASURE = "ring-1-3"

TARGETS = {
    "argmax_w1":  (1.2527, 0.05, "m9 ring-1-3 w=1, four flat ROIs pooled"),
    "mean":       (0.534,  0.05, "fact 19, M2 (different harness)"),
    "placebo":    (0.981,  0.05, "fact 19, M2 (different harness)"),
    "argmax_w17": (1.075,  0.05, "fact 23, M2-verification (different harness)"),
    "speckle_w17_pp": (0.868, 2.0, "fact 23, percentage points"),
}
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def plain_mean_ratio(value, single_sigma):
    _, sig = F.mean_and_sigma(value.mean(axis=0))
    return sig / single_sigma


def placebo_ratio(value, idx, single_sigma, seed):
    """M2's placebo: keep the winner *histogram* exactly, destroy its spatial
    correlation with the noise.  Anything the histogram alone can explain
    survives; only noise-coupled selection does not."""
    rg = np.random.default_rng(seed)
    flat = idx.reshape(-1).copy()
    rg.shuffle(flat)
    perm = flat.reshape(idx.shape)
    out = np.take_along_axis(value, perm[None, ...], axis=0)[0]
    _, sig = F.mean_and_sigma(out)
    return sig / single_sigma


def main():
    t0 = time.time()
    say("Gate 1b -- levels of facts 19 and 23 on simulated stacks")
    say(f"measure {MEASURE}; widths {WIDTHS}")
    say("NOTE (rule 17): the harness ratio is sigma(merged)/sigma(single) on")
    say("  the RAW ROI -- structure AND noise.  Texture contrast is FITTED and")
    say("  109MSDCF's drift is UNPUBLISHED, so the 'argmax_w1' and 'mean' axes")
    say("  are partly circular.  'placebo', the curve shape and speckle are not.")
    say()

    ms_all = F.design(True)
    reach = F.max_support(ms_all)
    margin = max((x - 1) // 2 for x in WIDTHS) + reach
    tile = ROI_HW + 2 * margin
    say(f"reach {reach}; margin {margin}; green tile {tile} -> sensor {2 * tile}")

    raw = S.load_real(REAL)
    iso = S.iso_of(REAL)
    _, rval = S.tiles(raw, REAL_ROI, margin)
    ref = rval[raw.shape[0] // 2]
    base_e, contrast_e = B.fit_radiometry(ref, iso)
    beta = B.fit_beta(ref)
    del raw
    nm = F.NoiseModel.for_iso(iso)
    say(f"fitted: base {base_e:.1f} e-, contrast {contrast_e:.1f} e-, "
        f"beta {beta:.3f}   (real ROI mean {ref.mean():.2f}, "
        f"sd {ref.std():.4f} DN)")

    B.set_supersample(SUPERSAMPLE)
    hw = (2 * tile, 2 * tile)
    target_struct = contrast_e * nm.gain_dn_per_e
    contrast_e = B.calibrate_contrast(B.cfg_109(1.0, seed=1, channels="green"),
                                      hw, base_e, contrast_e, beta, 101,
                                      target_struct, iso)
    say(f"calibrated latent contrast {contrast_e:.1f} e- sd "
        f"(in-focus green structure sd -> {target_struct:.3f} DN)")
    say()

    meas = [m for m in F.design(False) if m.name == MEASURE][0]
    rows = []
    for dname, drift in DRIFTS.items():
        for coc in COC_SWEEP:
            cfg = B.cfg_109(coc, seed=1, channels="green")
            cfg.breathing = dataclasses.replace(cfg.breathing,
                                                total_scale_change=drift)
            sc = B.flat_scene(cfg, hw, base_e, contrast_e, beta,
                              focus_index=11.0, seed=101)
            tr = time.time()
            st = render_stack(sc, cfg)
            roi = S.Roi(margin, margin, ROI_HW, ROI_HW)
            luma, val = S.tiles(st.frames, roi, margin)
            single = val[val.shape[0] // 2]
            srows = F.sweep_measure(meas, luma, val, single, nm, margin, WIDTHS)
            rr = np.array([r["ratio"] for r in srows])
            i17 = WIDTHS.index(17)
            ss = srows[0]["single_sigma"]
            r = dict(
                drift=dname, coc=coc,
                argmax_w1=float(rr[0]),
                argmax_w17=float(rr[i17]),
                floor=float(rr.min()),
                speckle_w1_pp=100.0 * srows[0]["speckle"],
                speckle_w17_pp=100.0 * srows[i17]["speckle"],
                winners_w1=srows[0]["distinct_winners"],
                mean=plain_mean_ratio(val, ss),
                placebo=placebo_ratio(val, srows[0]["index"], ss, 4242),
                sd=float(single.std()), render_s=time.time() - tr)
            rows.append(r)
            say(f"drift {dname:<9} coc {coc:<5} : argmax(1) {r['argmax_w1']:.4f}"
                f"  argmax(17) {r['argmax_w17']:.4f}  floor {r['floor']:.4f}"
                f"  mean {r['mean']:.4f}  placebo {r['placebo']:.4f}"
                f"  speckle {r['speckle_w1_pp']:.2f}% -> "
                f"{r['speckle_w17_pp']:.3f}%  [{r['render_s']:.0f}s]")

    say()
    say("=" * 78)
    say("per-axis best over the sweep (a single configuration must satisfy all "
        "five to PASS)")
    say(f"  {'axis':<16} {'target':>8} {'tol':>6} {'best':>8} {'at':>22}  ok")
    per_axis = {}
    for k, (tgt, tol, _src) in TARGETS.items():
        best = min(rows, key=lambda r: abs(r[k] - tgt))
        ok = abs(best[k] - tgt) <= tol
        per_axis[k] = ok
        say(f"  {k:<16} {tgt:>8.4f} {tol:>6.3f} {best[k]:>8.4f} "
            f"{best['drift'] + '/coc' + str(best['coc']):>22}  "
            f"{'yes' if ok else 'NO'}")

    say()
    joint = [r for r in rows
             if all(abs(r[k] - t) <= tol for k, (t, tol, _) in TARGETS.items())]
    say(f"configurations satisfying ALL five axes at once: {len(joint)}")
    for r in joint:
        say(f"  drift {r['drift']}, coc {r['coc']}")
    n_axes = sum(per_axis.values())
    verdict = ("PASS" if joint else
               ("PARTIAL" if n_axes >= 3 else "FAIL"))
    say(f"GATE 1b: {verdict} ({n_axes}/5 axes reachable, "
        f"{len(joint)} joint)  [{time.time() - t0:.0f}s]")
    for k, ok in per_axis.items():
        if not ok:
            say(f"  axis MISSED: {k} (target {TARGETS[k][0]}, "
                f"{TARGETS[k][2]})")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
        fh.write("\ncsv\n")
        keys = ["drift", "coc", "argmax_w1", "argmax_w17", "floor", "mean",
                "placebo", "speckle_w1_pp", "speckle_w17_pp", "winners_w1",
                "sd"]
        fh.write(",".join(keys) + "\n")
        for r in rows:
            fh.write(",".join(str(r[k]) for k in keys) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
