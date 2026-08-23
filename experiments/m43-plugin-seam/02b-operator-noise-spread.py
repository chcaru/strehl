"""M43 step 2b - the realistic spread of `k`, with the regulariser in place.

Supersedes `02-operator-noise-spread.py`, which is kept because its failure is
the useful part. That script modelled the coarse field as `box_mean(|grad|, 13)`
and reproduced `FINE_FOCUS_NOISE_SD` to 0.20% while reading 24.26% high against
`FOCUS_NOISE_SD`. The split localised the fault exactly: the two constants
differ in the regulariser, and only the coarse one has it.

    FOCUS_NOISE_SD      = SD of regularise(box_mean(|grad|, 13))   <- 17x17 box
    FINE_FOCUS_NOISE_SD = SD of box_mean(|grad|, 2)                <- no box

That is what `merge.rs` says on the constant ("It is a function of
WINDOW_RADIUS and REGULARISER_RADIUS") and what the two tests do. The one-pass
model was simply the wrong operator for the coarse arm.

This is the two-target calibration working as intended, and it is why step A
refuses to report step B: a single target could have been matched by a wrong
implementation with a compensating error, and this one nearly was.

Reported as a side result: the regularised/unregularised ratio at w13 is an
independent check on fact 432, which claimed the composed 27-box-then-17-box
has a variance-equivalent single-box width of 31.89 taps.
"""

import json
import pathlib

import numpy as np

FOCUS_NOISE_SD = 0.015214  # regularised, crates/strehl-core/src/merge.rs
FOCUS_NOISE_SD_TOL = 0.000075
FINE_FOCUS_NOISE_SD = 0.090400  # unregularised, through_focus.rs
WINDOW_RADIUS = 13
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


def op_tenengrad(a):
    gx, gy = sobel(a)
    return np.sqrt(gx * gx + gy * gy)


def op_tenengrad_sq(a):
    gx, gy = sobel(a)
    return gx * gx + gy * gy


def op_brenner(a):
    return np.abs(replicate(a, 0, 2) - a)


def op_laplacian(a):
    return np.abs(
        4.0 * a
        - replicate(a, 0, 1)
        - replicate(a, 0, -1)
        - replicate(a, 1, 0)
        - replicate(a, -1, 0)
    )


def op_sml(a):
    return np.abs(2.0 * a - replicate(a, 0, 1) - replicate(a, 0, -1)) + np.abs(
        2.0 * a - replicate(a, 1, 0) - replicate(a, -1, 0)
    )


def op_ring13(a):
    return np.abs(box_mean(a, 1) - box_mean(a, 3))


def op_local_variance(a):
    m = box_mean(a, 1)
    return box_mean(a * a, 1) - m * m


OPERATORS = {
    "tenengrad |grad|  (SHIPPED)": op_tenengrad,
    "tenengrad-squared |grad|^2": op_tenengrad_sq,
    "brenner |I(x+2)-I(x)|": op_brenner,
    "laplacian |4I - N4|": op_laplacian,
    "sum-modified-laplacian": op_sml,
    "ring(1,3)": op_ring13,
    "local variance (3x3)": op_local_variance,
}


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
print("STEP A - calibrate against BOTH of the crate's constants, each in its own")
print("         configuration. Step B is not printed unless both match.")
print("=" * 78)
print(f"  {SEEDS} seeds x {SIDE}x{SIDE} unit-variance white Gaussian noise\n")

cal, ok = {}, True
targets = [
    ("FOCUS_NOISE_SD", WINDOW_RADIUS, True, FOCUS_NOISE_SD, FOCUS_NOISE_SD_TOL),
    ("FINE_FOCUS_NOISE_SD", FINE_WINDOW_RADIUS, False, FINE_FOCUS_NOISE_SD, None),
]
for label, radius, reg, target, tol in targets:
    sd, sem = measure(op_tenengrad, radius, reg)
    lim = tol if tol is not None else target * (FOCUS_NOISE_SD_TOL / FOCUS_NOISE_SD)
    hit = abs(sd - target) <= lim
    ok &= hit
    cal[label] = {"python": sd, "sem": sem, "crate": target, "match": hit}
    cfg = f"w{radius}{' + reg' + str(REGULARISER_RADIUS) if reg else ', no reg'}"
    print(
        f"  {label:<22}{cfg:>14}   crate {target:.6f}   python {sd:.6f} +/- {sem:.6f}"
        f"   dev {(sd - target) / target:+.2%}   {'MATCH' if hit else 'MISMATCH'}"
    )

print()
if not ok:
    print("  CALIBRATION FAILED - refusing to report step B.")
    raise SystemExit(1)
print("  CALIBRATED on two independent targets in two configurations.\n")

# Side result: an independent check on fact 432's composed-scale claim.
sd_unreg, _ = measure(op_tenengrad, WINDOW_RADIUS, False)
sd_reg = cal["FOCUS_NOISE_SD"]["python"]
print("=" * 78)
print("SIDE RESULT - independent check on fact 432 (the composed scale)")
print("=" * 78)
print(f"  w13 unregularised SD      {sd_unreg:.6f}")
print(f"  w13 + reg8 SD             {sd_reg:.6f}")
print(f"  variance ratio            {(sd_unreg / sd_reg) ** 2:.4f}")
print(f"  fact 432 predicts         84.667 / 60.667 = {84.667 / 60.667:.4f}")
print("  (equal only if the composition were of independent boxes; the gap is")
print("   the correlation the crate's own doc prices at 5.3x against naive")
print("   independence, so this is a direction check, not an identity.)\n")

print("=" * 78)
print("STEP B - k for operators someone would plausibly contribute")
print("=" * 78)
print(f"  configuration: operator -> box w{WINDOW_RADIUS} -> regulariser r{REGULARISER_RADIUS}")
print(f"  k = SD_operator / {FOCUS_NOISE_SD};  a plugin inheriting the host constant")
print(f"  runs at effective gate = intended / k\n")
print(f"  {'operator':<30}{'SD':>13}{'k':>10}{'eff. gate @1.0':>17}")
print("  " + "-" * 72)

rows = []
for name, op in OPERATORS.items():
    sd, sem = measure(op, WINDOW_RADIUS, True, seeds=4)
    k = sd / FOCUS_NOISE_SD
    rows.append({"operator": name, "sd": sd, "sem": sem, "k": k, "eff_gate": 1.0 / k})
    print(f"  {name:<30}{sd:>13.6f}{k:>10.3f}{1.0 / k:>17.4f}")

ks = [r["k"] for r in rows]
print()
print(f"  k spans {min(ks):.3f} to {max(ks):.3f}  =  {max(ks) / min(ks):.1f}x across")
print(f"  seven textbook focus operators, none of them adversarial.")
print(f"  M43 step 1 priced the damage at k = 5.942.")

out = pathlib.Path(__file__).with_name("02b-operator-noise-spread.json")
out.write_text(
    json.dumps(
        {
            "calibration": cal,
            "focus_noise_sd": FOCUS_NOISE_SD,
            "side": SIDE,
            "regulariser_radius": REGULARISER_RADIUS,
            "window_radius": WINDOW_RADIUS,
            "w13_unregularised_sd": sd_unreg,
            "rows": rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"\n  wrote {out.name}")
