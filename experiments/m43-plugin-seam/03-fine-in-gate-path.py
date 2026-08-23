"""M43 step 3 - the honest k for the fine operator, and a correction to step 1.

`M43-plugin-calibration-seam.md` priced the damage using

    k = FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD = 0.090400 / 0.015214 = 5.942

and described the two as "two real operators already in this codebase differing
only in window radius". Step 2b establishes that this is wrong, because the two
published constants are not the same kind of quantity:

    FOCUS_NOISE_SD      = SD of regularise(box_mean(|grad|, 13))   <- with r8
    FINE_FOCUS_NOISE_SD = SD of           box_mean(|grad|,  2)     <- without

They differ in window radius AND in whether the 17x17 regulariser was applied.
The ratio therefore conflates the two, and 5.942 is not the number that
describes the scenario step 1 claimed to price.

The scenario itself is still real, and it is the one that matters for the
plugin seam: `merge::regularise` is applied by the HOST to whatever field the
operator returns. So a contributed fine-window operator does get regularised,
and its true k is

    k = SD(regularise(box_mean(op, 2))) / FOCUS_NOISE_SD

which this measures. The direction of the error is predictable in advance and
worth stating before the number appears, so the prediction can fail: a small
window leaves more high-frequency power for the regulariser to remove than a
large one does, so regularising the fine field should cost it proportionally
more than it costs the coarse field, and the honest k should come out BELOW
5.942. If it comes out above, the reasoning here is wrong.

The primitives are copied from `02b-operator-noise-spread.py` rather than
imported, because rule 15 forbids modifying that script now that it has
reported. The copy is not taken on trust: step A below re-runs both calibration
targets, so a divergent copy fails loudly before anything is reported.
"""

import json
import pathlib

import numpy as np

FOCUS_NOISE_SD = 0.015214
FOCUS_NOISE_SD_TOL = 0.000075
FINE_FOCUS_NOISE_SD = 0.090400
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


def tenengrad(a):
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
    return np.sqrt(gx * gx + gy * gy)


def measure(radius, regularise, seeds=SEEDS):
    v = []
    for s in range(seeds):
        a = np.random.default_rng(20260810 + s).standard_normal((SIDE, SIDE))
        f = box_mean(tenengrad(a), radius)
        m = radius + 2
        if regularise:
            f = box_mean(f, REGULARISER_RADIUS)
            m += REGULARISER_RADIUS
        v.append(float(np.std(f[m:-m, m:-m], ddof=1)))
    return float(np.mean(v)), float(np.std(v, ddof=1) / np.sqrt(len(v)))


print("STEP A - re-verify the copied primitives against both crate constants\n")
ok = True
for label, radius, reg, target in [
    ("FOCUS_NOISE_SD", WINDOW_RADIUS, True, FOCUS_NOISE_SD),
    ("FINE_FOCUS_NOISE_SD", FINE_WINDOW_RADIUS, False, FINE_FOCUS_NOISE_SD),
]:
    sd, sem = measure(radius, reg)
    lim = target * (FOCUS_NOISE_SD_TOL / FOCUS_NOISE_SD)
    hit = abs(sd - target) <= lim
    ok &= hit
    print(
        f"  {label:<22} crate {target:.6f}  python {sd:.6f}  dev "
        f"{(sd - target) / target:+.2%}  {'MATCH' if hit else 'MISMATCH'}"
    )
if not ok:
    print("\n  CALIBRATION FAILED - the copy diverged. Refusing to report.")
    raise SystemExit(1)
print("\n  copy verified.\n")

print("STEP B - the honest k for the fine operator in the gate path\n")
fine_reg, fine_reg_sem = measure(FINE_WINDOW_RADIUS, True)
k_honest = fine_reg / FOCUS_NOISE_SD
k_claimed = FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD

print(f"  step 1 claimed        k = {k_claimed:.3f}   (0.090400 / 0.015214)")
print(f"  regularised fine SD     = {fine_reg:.6f} +/- {fine_reg_sem:.6f}")
print(f"  honest k                = {k_honest:.3f}")
print(f"  prediction was k < {k_claimed:.3f}: "
      f"{'HELD' if k_honest < k_claimed else 'FAILED'}")
print(f"  step 1 overstated this pair by {k_claimed / k_honest:.2f}x")
print()
print(f"  effective gate at intended 1.0: {1.0 / k_honest:.4f} (step 1 said "
      f"{1.0 / k_claimed:.4f})")
print()
print("  Step 2b's seven-operator survey is unaffected - every row there was")
print("  measured in the shipped configuration (operator -> w13 -> r8), so the")
print("  10.4x spread and the k = 6.68 worst case stand. The correction moves")
print("  only the illustrative pair step 1 used, and it moves it in the")
print("  direction that makes step 1's example weaker while leaving the")
print("  measured survey's worst case stronger than the example ever was.")

out = pathlib.Path(__file__).with_name("03-fine-in-gate-path.json")
out.write_text(
    json.dumps(
        {
            "fine_regularised_sd": fine_reg,
            "fine_regularised_sem": fine_reg_sem,
            "k_honest": k_honest,
            "k_claimed_in_step1": k_claimed,
            "overstatement": k_claimed / k_honest,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"\n  wrote {out.name}")
