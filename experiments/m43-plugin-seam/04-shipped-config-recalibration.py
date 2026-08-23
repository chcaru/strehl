"""M43 step 4 - what the M17+M42 edit does to the gate, and who moves it.

M17 says ship `tenengrad-sq`. M42 says ship it at `WINDOW_RADIUS = 11`, and
that the two must land as ONE edit because a window optimum belongs to the
operator/window pair (discipline 259). Both are right and both are incomplete:
M43 established that the merge gate is denominated in `FOCUS_NOISE_SD`, and
`merge.rs` states that constant "is a function of WINDOW_RADIUS and
REGULARISER_RADIUS" -- to which fact 439 adds: and of the OPERATOR. The shipped
0.015214 was measured for `|grad|` at w13. **Both halves of the proposed edit
move it.** So the edit is a triple, not a pair.

This is not a new mechanism. It is fact 436 (tol is exactly linear in
FOCUS_NOISE_SD) meeting the project's own first operator change, and it is the
first time M43's hole is load-bearing on a real pending commit rather than on a
hypothetical third-party plugin.

PRE-REGISTERED, before running (rule 12; the direction is the falsifiable part):

  1. `k` rises above 1. Squaring measured k = 1.367 at w13 (fact 439), and
     narrowing the box from w13 to w11 averages fewer taps, which raises the SD
     again. Both halves push the same way.
  2. Therefore k_total > 1.367, and the effective gate falls below 0.731.
  3. The two halves are NOT independent and must not be multiplied: the
     operator changes the field's marginal distribution and the box changes how
     that field is averaged. I predict the product of the single-factor ks
     OVERSTATES the joint k, because the squared field is more heavily
     correlated tap-to-tap than the magnitude field, so shrinking the box costs
     it less than it costs the magnitude. Registered as a direction only.

WHAT WOULD FALSIFY THIS ENTIRELY: k_total within the crate's own tolerance of
1.0 (0.5%). Then the constant is portable across this edit, no re-measurement
is needed, and the "triple" framing is wrong. That is a real possible outcome
-- squaring raises the SD and it is not impossible that a narrower box, by
truncating a heavy tail, lowers it by a compensating amount.

Reuses the calibration of `02b-operator-noise-spread.py` unchanged (rule 15:
that script is not edited; its two-target gate is reproduced here so this
script also refuses to report if the instrument has drifted).
"""

import json
import pathlib

import numpy as np

FOCUS_NOISE_SD = 0.015214  # regularised, |grad| @ w13 - crates/strehl-core/src/merge.rs
FOCUS_NOISE_SD_TOL = 0.000075
FINE_FOCUS_NOISE_SD = 0.090400  # unregularised, w2 - through_focus.rs
SHIPPED_RADIUS = 13
PROPOSED_RADIUS = 11  # M42's recommendation
FINE_WINDOW_RADIUS = 2
REGULARISER_RADIUS = 8

SIDE = 2048
SEEDS = 8


def replicate(a, dy, dx):
    out = a
    if dy:
        out = np.roll(out, -dy, axis=0)
        if dy > 0:
            out[-dy:, :] = a[-1, :]
        else:
            out[:-dy, :] = a[0, :]
    if dx:
        s = np.roll(out, -dx, axis=1)
        if dx > 0:
            s[:, -dx:] = out[:, -1][:, None]
        else:
            s[:, :-dx] = out[:, 0][:, None]
        out = s
    return out


def box_mean(a, r):
    if r == 0:
        return a.copy()
    pad = np.pad(a, ((r, r), (r, r)), mode="edge")
    c = np.cumsum(pad, axis=0)
    c = np.vstack([np.zeros((1, c.shape[1])), c])
    a = (c[2 * r + 1 :, :] - c[: -(2 * r + 1), :]) / (2 * r + 1)
    c = np.cumsum(a, axis=1)
    c = np.hstack([np.zeros((c.shape[0], 1)), c])
    return (c[:, 2 * r + 1 :] - c[:, : -(2 * r + 1)]) / (2 * r + 1)


def sobel(a):
    gx = 0.125 * (
        replicate(a, -1, 1)
        + 2.0 * replicate(a, 0, 1)
        + replicate(a, 1, 1)
        - replicate(a, -1, -1)
        - 2.0 * replicate(a, 0, -1)
        - replicate(a, 1, -1)
    )
    gy = 0.125 * (
        replicate(a, 1, -1)
        + 2.0 * replicate(a, 1, 0)
        + replicate(a, 1, 1)
        - replicate(a, -1, -1)
        - 2.0 * replicate(a, -1, 0)
        - replicate(a, -1, 1)
    )
    return gx, gy


def op_magnitude(a):
    gx, gy = sobel(a)
    return np.sqrt(gx * gx + gy * gy)


def op_squared(a):
    gx, gy = sobel(a)
    return gx * gx + gy * gy


def one(rng, op, radius, regularise):
    a = rng.standard_normal((SIDE, SIDE))
    f = box_mean(op(a), radius)
    m = radius + 2
    if regularise:
        f = box_mean(f, REGULARISER_RADIUS)
        m += REGULARISER_RADIUS
    return float(np.std(f[m:-m, m:-m], ddof=1))


def measure(op, radius, regularise, seeds=SEEDS):
    v = [one(np.random.default_rng(20260810 + s), op, radius, regularise) for s in range(seeds)]
    return float(np.mean(v)), float(np.std(v, ddof=1) / np.sqrt(len(v)))


print("=" * 78)
print("STEP A - the same two-target calibration as 02b. No result is printed")
print("         unless the instrument still reproduces BOTH crate constants.")
print("=" * 78)

cal, ok = {}, True
for label, radius, reg, target, tol in [
    ("FOCUS_NOISE_SD", SHIPPED_RADIUS, True, FOCUS_NOISE_SD, FOCUS_NOISE_SD_TOL),
    ("FINE_FOCUS_NOISE_SD", FINE_WINDOW_RADIUS, False, FINE_FOCUS_NOISE_SD, None),
]:
    sd, sem = measure(op_magnitude, radius, reg)
    lim = tol if tol is not None else target * (FOCUS_NOISE_SD_TOL / FOCUS_NOISE_SD)
    hit = abs(sd - target) <= lim
    ok &= hit
    cal[label] = {"python": sd, "crate": target, "match": hit}
    print(
        f"  {label:<22} crate {target:.6f}  python {sd:.6f}"
        f"  dev {(sd - target) / target:+.2%}   {'MATCH' if hit else 'MISMATCH'}"
    )

print()
if not ok:
    print("  CALIBRATION FAILED - refusing to report.")
    raise SystemExit(1)
print("  CALIBRATED.\n")

print("=" * 78)
print("STEP B - attribute the shift: operator alone, radius alone, both")
print("=" * 78)
print(f"  all arms: operator -> box -> regulariser r{REGULARISER_RADIUS} (unchanged by the edit)")
print(f"  k = SD / {FOCUS_NOISE_SD} (the constant the crate would keep if nobody re-measured)")
print(f"  effective gate = intended gate / k          [fact 436: tol is exactly linear]\n")

arms = [
    ("|grad|      @ w13   SHIPPED", op_magnitude, SHIPPED_RADIUS),
    ("|grad|      @ w11   radius only", op_magnitude, PROPOSED_RADIUS),
    ("|grad|^2    @ w13   operator only", op_squared, SHIPPED_RADIUS),
    ("|grad|^2    @ w11   PROPOSED (M17+M42)", op_squared, PROPOSED_RADIUS),
]

print(f"  {'arm':<40}{'SD':>12}{'k':>9}{'eff. gate @1.0':>17}")
print("  " + "-" * 78)
res = {}
for name, op, radius in arms:
    sd, sem = measure(op, radius, True)
    k = sd / FOCUS_NOISE_SD
    res[name] = {"sd": sd, "sem": sem, "k": k, "eff_gate": 1.0 / k}
    print(f"  {name:<40}{sd:>12.6f}{k:>9.3f}{1.0 / k:>17.4f}")

k_rad = res["|grad|      @ w11   radius only"]["k"]
k_op = res["|grad|^2    @ w13   operator only"]["k"]
k_both = res["|grad|^2    @ w11   PROPOSED (M17+M42)"]["k"]

print()
print("=" * 78)
print("STEP C - scoring the pre-registered predictions")
print("=" * 78)
p1 = k_both > 1.0
p2 = k_both > 1.367
p3 = k_rad * k_op > k_both
print(f"  1. k_total > 1                       k = {k_both:.3f}      {'HELD' if p1 else 'FALSIFIED'}")
print(f"  2. k_total > 1.367 (fact 439 at w13) k = {k_both:.3f}      {'HELD' if p2 else 'FALSIFIED'}")
print(
    f"  3. product overstates the joint      {k_rad:.3f} x {k_op:.3f} = {k_rad * k_op:.3f}"
    f" vs {k_both:.3f}   {'HELD' if p3 else 'FALSIFIED'}"
)
print(f"     (separability error {(k_rad * k_op) / k_both - 1.0:+.2%})")
print()
print(f"  FALSIFIER: k_total within 0.5% of 1.0 -> constant is portable, framing wrong.")
print(f"     |k - 1| = {abs(k_both - 1.0):.3f} = {abs(k_both - 1.0) * 100:.1f}%   "
      f"{'NOT TRIGGERED' if abs(k_both - 1.0) > 0.005 else 'TRIGGERED - THE TRIPLE FRAMING IS WRONG'}")
print()
print("=" * 78)
print("STEP D - the consequence for the pending commit")
print("=" * 78)
print(f"  If M17+M42 land WITHOUT re-measuring FOCUS_NOISE_SD:")
print(f"    `--gate 1.0` silently becomes an effective gate of {1.0 / k_both:.4f}")
print(f"    every gate the owner has ever measured moves by the same factor {1.0 / k_both:.4f}x")
print(f"    the log, the exit code and the calibration block are UNCHANGED (fact 438)")
print(f"  The correct constant to ship alongside the edit:")
print(f"    FOCUS_NOISE_SD = {res['|grad|^2    @ w11   PROPOSED (M17+M42)']['sd']:.6f}"
      f"  (+/- {res['|grad|^2    @ w11   PROPOSED (M17+M42)']['sem']:.6f} sem, {SEEDS} seeds)")
print(f"  NOTE: this is a Python-instrument value calibrated to 0.2% against the")
print(f"  crate's own two constants. It is a CROSS-CHECK, not a substitute for")
print(f"  re-running the crate's own calibration test at the new configuration.")

out = pathlib.Path(__file__).with_name("04-shipped-config-recalibration.json")
out.write_text(
    json.dumps(
        {
            "calibration": cal,
            "shipped_focus_noise_sd": FOCUS_NOISE_SD,
            "arms": res,
            "predictions": {"k_gt_1": p1, "k_gt_1p367": p2, "product_overstates": p3},
            "seeds": SEEDS,
            "side": SIDE,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"\n  wrote {out.name}")
