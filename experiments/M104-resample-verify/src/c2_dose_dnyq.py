"""M104 C2 -- the responsiveness control for D_nyq, and the cost law.

D_nyq carries bars B6', B6" and B7', and until now it had NO responsiveness
control.  That is exactly the gap that killed M97's tile-wise sharpness metric
(fact 1273): a metric that has never been shown to move by a known amount when
a known amount of the thing is planted cannot return a PASS.  A bar resting on
an uncontrolled metric is decoration.

METHOD.  Take the reference render -- STREHL_ALIGN=0, gate 0, native sampling,
no warp -- and plant enlargements of known size through a TRUE Catmull-Rom
separable gather, the same kernel `warpmap.rs:349` says the aligner writes.
Then read D_nyq exactly as the baseline reads it, including the object-space
band correction by the measured magnification.

  NULL   s = 1.000000 must give D_nyq = 0 to machine precision and mag = 1
         exactly.  A gather at unit scale still runs every tap, so this also
         proves the kernel is interpolating rather than smoothing.
  DOSE   D_nyq must rise monotonically with s.
  LAW    the cost law measured on a real photograph, which settles whether
         extrapolating a 3.01% cost to 7.35% linearly is even legitimate.

THE ADJUDICATION THIS BUYS EARLY.  Prediction (j) turns on two extrapolations
that disagree: my ruler's 3.01% cost scaled linearly predicts +0.344 dex at
7.35%, the orchestrator's synthetic gather predicts +0.239 dex.  Planting
7.35% directly on a real photograph answers it without waiting for M95.

CLOSURE TEST.  If planting 3.01% on the reference render reproduces the
+0.1408 dex measured between the real ALN and A0 renders, then the entire
near-Nyquist deficit on this subject IS the resample, with nothing left over
for the warp, the merge, or the decoder.  If the planted cost is smaller, the
remainder is real and belongs to something the fix will NOT remove -- which
would cap how much M95 can possibly deliver.  Either way it is a number worth
having before the verdict.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m104lib as L

OUT = Path(__file__).resolve().parent.parent / "out"
BASE = Path(L.RENDERS) / "flat-on-ruler-cpl-PRE-A0-g0.tif"
COLS, ROWS = 8, 6

# 1.030078 and 1.073537 are the two stacks' actual 1/k.
DOSES = [1.000000, 1.010000, 1.030078, 1.073537, 1.150000]

# The measured ALN-vs-A0 deficit this is trying to account for.
MEASURED_ALN = 0.1623
MEASURED_ALN_SE = 0.0060  # D_nyq* = 0.1408 + 2log10(1.025027)

log = []


def say(s=""):
    print(s)
    log.append(s)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    L.ROI = 384
    a = L.green(BASE)
    seed = L.seed_combs(a, cols=COLS, rows=ROWS)

    say("=" * 78)
    say("M104 C2 -- D_nyq responsiveness control and the measured cost law")
    say(f"  base   : {BASE.name}  ({a.shape[1]} x {a.shape[0]})")
    say("  kernel : TRUE Catmull-Rom separable 4-tap gather (warpmap.rs:349)")
    say(f"  band   : [{L.NYQ_LO}, {L.NYQ_HI}] cyc/px, object-corrected by the")
    say("           measured magnification of each planted arm")
    say("=" * 78)
    say()
    say(f"{'planted':>10} {'mag':>10} {'D_nyq':>10} {'SE':>8} {'sigma':>8} "
        f"{'power':>8} {'dex/%':>8}  n")

    rows_out, prev = [], None
    monotone = True
    for s in DOSES:
        b = L.catmull_rom_scale(a, s)
        rr = L.measure_pair(a, b, seed, COLS, ROWS)
        mag, mag_se, n = L.gmean_se([r["mag"] for r in rr])
        dn = [r["d_nyq_star"] for r in rr if np.isfinite(r["d_nyq_star"])]
        m = float(np.mean(dn))
        se = float(np.std(dn, ddof=1) / np.sqrt(len(dn))) if len(dn) > 1 else 0.0
        sig = m / se if se > 0 else float("inf") if m != 0 else 0.0
        per = m / ((s - 1) * 100) if s != 1.0 else float("nan")
        if prev is not None and not (m > prev):
            monotone = False
        prev = m
        say(f"{s:10.6f} {mag:10.6f} {m:+10.5f} {se:8.5f} {sig:8.2f} "
            f"{10**m:8.4f} {per:8.5f} {n:3d}")
        rows_out.append(dict(planted=s, mag=mag, mag_se=mag_se,
                             d_nyq_star=m, se=se, sigma=sig, per_pct=per, n=n))
    say()

    null = rows_out[0]
    ok_null = abs(null["d_nyq_star"]) < 1e-12 and abs(null["mag"] - 1.0) < 1e-12
    say(f"NULL   s = 1.000000 -> D_nyq = {null['d_nyq_star']:+.3e}, "
        f"mag = {null['mag']:.12f}")
    say(f"       bar: both exactly 0 / 1 to machine precision -> "
        f"{'GREEN' if ok_null else 'RED'}")
    say(f"DOSE   monotone increasing: {monotone} -> "
        f"{'GREEN' if monotone else 'RED'}")
    say()

    # ------------------------------------------------------- CLOSURE
    at30 = [r for r in rows_out if abs(r["planted"] - 1.030078) < 1e-9][0]
    diff = MEASURED_ALN - at30["d_nyq_star"]
    dse = np.hypot(MEASURED_ALN_SE, at30["se"])
    say("-" * 78)
    say("CLOSURE -- how much of the real ALN deficit is the resample alone?")
    say(f"  real ALN vs A0, measured        : {MEASURED_ALN:+.4f} "
        f"+/- {MEASURED_ALN_SE:.4f} dex")
    say(f"  planted 1.030078 on the A0 arm  : {at30['d_nyq_star']:+.4f} "
        f"+/- {at30['se']:.4f} dex")
    say(f"  unexplained remainder           : {diff:+.4f} +/- {dse:.4f} dex "
        f"({abs(diff)/dse if dse>0 else 0:.2f} sigma)")
    frac = at30["d_nyq_star"] / MEASURED_ALN if MEASURED_ALN else float("nan")
    say(f"  fraction of the deficit that IS the resample : {frac:.1%}")
    say()

    # ------------------------------------------------- PREDICTION (j)
    at73 = [r for r in rows_out if abs(r["planted"] - 1.073537) < 1e-9][0]
    lin = at30["d_nyq_star"] * (1.073537 - 1) / (1.030078 - 1)
    say("-" * 78)
    say("PREDICTION (j) -- what the resample costs at bee-3-cpl's 7.35%")
    say(f"  measured directly, planted 1.073537 : {at73['d_nyq_star']:+.4f} "
        f"+/- {at73['se']:.4f} dex")
    say(f"  linear extrapolation from 3.01%     : {lin:+.4f} dex")
    say(f"  orchestrator's synthetic gather     : +0.2392 dex  (fact 1287)")
    say(f"  linearity error                     : "
        f"{lin - at73['d_nyq_star']:+.4f} dex")
    say(f"  -> post-fix bee-3-cpl D_nyq should fall by "
        f"{at73['d_nyq_star']:.4f} dex from -0.0343, i.e. to "
        f"{-0.0343 - at73['d_nyq_star']:+.4f}")
    say("-" * 78)

    res = dict(doses=rows_out, null_ok=ok_null, monotone=monotone,
               closure=dict(measured=MEASURED_ALN, planted=at30['d_nyq_star'],
                            remainder=diff, sigma=float(abs(diff) / dse) if dse else 0,
                            fraction=frac),
               prediction_j=dict(direct=at73["d_nyq_star"], linear=lin,
                                 orchestrator=0.2392,
                                 post_fix_bee3=-0.0343 - at73["d_nyq_star"]))
    (OUT / "c2_dose_dnyq.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (OUT / "c2_dose_dnyq.log").write_text("\n".join(log), encoding="utf-8")


if __name__ == "__main__":
    main()
