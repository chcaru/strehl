"""Absolute backdrop level in DN, both arms, on ONE pixel population.

WHY THIS EXISTS, AND WHY IT IS NOT rimprofile.py
------------------------------------------------
ORCH's requirement, verbatim: "Report absolute background level in DN, before
and after, not the error and not a ratio."

The reason is a near-miss on this project. BUILD-SHARP measured that an
upper-envelope estimator carries a +0.845 sigma bias, UPWARD, against a defect
that is a DARKENING. At sigma_frame ~ 200 DN that is +169 DN. An estimator with
that bias nulls a veiling metric ARITHMETICALLY without improving the
photograph: the metric is an error or a ratio, the bias moves it toward zero,
and the picture is unchanged. ORCH's own headline recovery figure was impeached
by exactly this, because a -149 DN residual is smaller than the bias that could
be faking it.

A ratio cannot distinguish "the aura was removed" from "everything got
brighter". An absolute level can, because a global lift shows up in the far
field where no aura reaches, and a real local fix does not.

TWO DIFFERENCES FROM rimprofile.py, BOTH LOAD-BEARING
-----------------------------------------------------
1. rimprofile.py builds its subject mask FROM THE IMAGE IT IS PROFILING. Run on
   two arms it therefore scores two different pixel populations, and any
   difference between the arms is confounded with the difference between their
   masks -- which is not small, because the artifact under test lives exactly at
   the silhouette where the threshold cuts. Here the mask and the distance
   transform are computed ONCE, from the CONTROL arm, and both arms are read
   through it. This is the discipline ORCH used in veilpair.py.

2. It reports LEVELS, in DN, for both arms, plus the far-field level for both.
   The difference column is a convenience; the levels are the measurement.

THE DISCRIMINATOR
-----------------
Given the levels, "did the aura get removed" and "did everything get brighter"
separate cleanly:

    far-field shift   pyramid_far - estimator_far        should be ~0
    near-field shift  pyramid_near - estimator_near      should be large
    placebo shift     the same on a no-depth-separation subject, ~0

A fix that is real is LOCAL: it moves the pixels near the silhouette and leaves
the far field and the placebo alone. A fix that is a level shift moves all three
together. The script prints all three and refuses to collapse them into one
number.

USAGE
    python dnlevel.py <control.tif> <treatment.tif> [label]

Both must be LINEAR 16-bit renders (no --srgb). The tone curve is a strong
non-linearity that moves every level a metric computes, and the standing rule on
this project is that quality is never judged on an --srgb render.
"""
import sys

import numpy as np
import tifffile
from scipy import ndimage

if len(sys.argv) < 3:
    sys.exit(__doc__)

CONTROL = sys.argv[1]
TREAT = sys.argv[2]
LABEL = sys.argv[3] if len(sys.argv) > 3 else ""

# Bins: 1-4 px is inside the rim, 100-150 px is the aura's measured peak, and
# 600+ is far field. Chosen to match rimprofile.py's edges so rows line up
# against ORCH's section 12 reference by eye.
EDGES = [0, 4, 8, 12, 16, 20, 25, 30, 40, 50, 65, 80, 100, 125, 150,
         200, 250, 300, 400, 500, 600]
FAR_LO, FAR_HI = 600, 1400
MIN_PX = 500


def load(path):
    im = tifffile.imread(path)
    assert im.dtype == np.uint16, f"{path}: expected uint16 linear, got {im.dtype}"
    # Camera-native linear RGB; an unweighted mean is honest and is all a level
    # measurement needs. Luma weights here would not be colorimetric anyway.
    return im.astype(np.float32).mean(axis=2)


def build_mask(lum, path):
    """Subject mask and signed distance, from the CONTROL arm only.

    Refuses rather than guesses. rimprofile.py assumes a dark subject on bright
    ground; run on the inverse (a white flower on grey, e.g. lavendar-cpl) its
    threshold selects the GROUND, the "largest component" is the backdrop, and
    it happily prints a full profile of the wrong region. That silent
    mis-segmentation is why this function raises instead of returning.
    """
    lo, hi = np.percentile(lum, [5, 95])
    thr = 0.5 * (lo + hi)
    subject = lum < thr
    frac = subject.mean()
    lab, n = ndimage.label(subject)
    print(f"  mask: p5={lo:.0f} p95={hi:.0f} thr={thr:.0f} "
          f"dark-fraction={frac*100:.2f}% components={n}")

    if n > 1:
        sizes = ndimage.sum(subject, lab, range(1, n + 1))
        order = np.argsort(sizes)[::-1]
        big = sizes[order[0]]
        second = sizes[order[1]] if n > 1 else 0.0
        subject = lab == (1 + int(order[0]))
        print(f"  kept largest of {n} components: {big:.0f} px "
              f"({subject.mean()*100:.2f}% of frame), 2nd largest {second:.0f} px")
        # A silhouette is one object. Thousands of comparable fragments means
        # the threshold cut texture, not an outline.
        if n > 500 and second > 0.05 * big:
            raise SystemExit(
                f"REFUSED: {n} components with a 2nd-largest at "
                f"{second/big*100:.0f}% of the largest. That is a shredded "
                f"mask, not a silhouette."
            )

    # --- polarity, decided by the border ring rather than by area ------------
    # The first version of this guard refused any mask covering >50% of the
    # frame. MEASURED to be a false positive on coffee-bean, whose bean plus
    # cast shadow is 59.6% of the frame and is unambiguously the subject -- the
    # overlay picture settles it in a second. Area cannot separate "dark ground"
    # from "large dark subject"; the border ring can, because the backdrop is by
    # definition the thing that SURROUNDS, so it dominates all four edges. A
    # subject may run off one or two.
    W = 8
    ring = np.zeros(lum.shape, bool)
    ring[:W, :] = ring[-W:, :] = True
    ring[:, :W] = ring[:, -W:] = True
    cov = {"top": subject[:W, :].mean(), "bottom": subject[-W:, :].mean(),
           "left": subject[:, :W].mean(), "right": subject[:, -W:].mean()}
    touched = [k for k, v in cov.items() if v > 0.25]
    print(f"  border ring: mask covers {subject[ring].mean()*100:.1f}% of it; "
          f"edges >25%: {touched if touched else 'none'} "
          f"({'  '.join(f'{k}={v*100:.0f}%' for k, v in cov.items())})")

    if len(touched) == 4:
        raise SystemExit(
            f"REFUSED: the mask covers >25% of ALL FOUR frame edges, which is "
            f"what a BACKDROP does and what a subject does not.\n"
            f"  {path} looks like a BRIGHT subject on darker ground. This "
            f"instrument assumes the opposite polarity and would otherwise "
            f"report a confident profile of the wrong pixels."
        )

    d_out = ndimage.distance_transform_edt(~subject)
    d_in = ndimage.distance_transform_edt(subject)
    return subject, d_out - d_in


def profile(signed, arms):
    """Absolute median DN per distance bin, every arm on identical pixels."""
    rows = []
    for i in range(len(EDGES) - 1):
        m = (signed >= EDGES[i]) & (signed < EDGES[i + 1])
        n = int(m.sum())
        if n < MIN_PX:
            continue
        rows.append((EDGES[i], EDGES[i + 1], n,
                     [float(np.median(a[m])) for a in arms]))
    return rows


def global_levels(c, t):
    """Absolute levels that need no mask at all.

    Printed for EVERY subject, and before the silhouette profile, because it is
    the part that survives a mask refusal. 109MSDCF is the placebo precisely
    because it has no depth separation and therefore no silhouette -- an
    instrument that could only speak through a distance transform would have
    nothing to say about the one subject whose job is to show the fix does
    nothing. A tile grid is included so a spatially-varying shift cannot hide
    inside an unchanged global median.
    """
    print()
    print("ABSOLUTE LEVELS, WHOLE FRAME (no mask, no distance transform)")
    print("   statistic        control DN   pyramid DN        delta")
    for name, q in [("p1", 1), ("p10", 10), ("median", 50), ("p90", 90),
                    ("p99", 99)]:
        cv, tv = float(np.percentile(c, q)), float(np.percentile(t, q))
        print(f"   {name:<12} {cv:12.0f} {tv:12.0f} {tv-cv:+12.0f}")
    cm, tm = float(c.mean()), float(t.mean())
    print(f"   {'mean':<12} {cm:12.0f} {tm:12.0f} {tm-cm:+12.0f}")

    # Tile grid: a 6x6 of absolute medians, reported as the spread of the
    # per-tile shift. A global no-op that is locally large is not a no-op.
    H, W = c.shape
    gh, gw = H // 6, W // 6
    shifts = []
    for i in range(6):
        for j in range(6):
            sl = (slice(i * gh, (i + 1) * gh), slice(j * gw, (j + 1) * gw))
            shifts.append(float(np.median(t[sl])) - float(np.median(c[sl])))
    shifts = np.array(shifts)
    print(f"   6x6 tile shift: min {shifts.min():+.0f}  median "
          f"{np.median(shifts):+.0f}  max {shifts.max():+.0f}  "
          f"|max| {np.abs(shifts).max():.0f} DN")
    return cm, tm


def main():
    print(f"=== absolute backdrop level, DN {('-- ' + LABEL) if LABEL else ''} ===")
    print(f"  control  : {CONTROL}")
    print(f"  treatment: {TREAT}")
    c = load(CONTROL)
    t = load(TREAT)
    assert c.shape == t.shape, (
        f"arms are not on a common pixel grid: {c.shape} vs {t.shape}. "
        "A level comparison between differently-framed renders is meaningless."
    )
    print(f"  grid     : {c.shape} (shared)")

    global_levels(c, t)

    print()
    try:
        subject, signed = build_mask(c, CONTROL)
    except SystemExit as e:
        print(e)
        print()
        print("  The silhouette profile is skipped. The absolute levels above")
        print("  are unaffected by that refusal -- they use no mask.")
        return

    far = (signed > FAR_LO) & (signed < FAR_HI)
    if far.sum() < MIN_PX:
        raise SystemExit(
            f"REFUSED: only {far.sum()} px in the far field "
            f"({FAR_LO}-{FAR_HI} px out). Without a far-field anchor this "
            f"cannot separate a local fix from a global level shift, which is "
            f"the entire purpose of the measurement."
        )
    c_far = float(np.median(c[far]))
    t_far = float(np.median(t[far]))

    print()
    print("BACKDROP, ABSOLUTE median DN, outward from the silhouette.")
    print("Both arms read through the CONTROL arm's mask, so every row scores")
    print("an identical pixel population.")
    print()
    print("   d (px)       px    control DN   pyramid DN        delta")
    rows = profile(signed, [c, t])
    for lo, hi, n, (cv, tv) in rows:
        print(f"  {lo:4d}-{hi:<4d} {n:9d} {cv:12.0f} {tv:12.0f} {tv-cv:+12.0f}")

    print()
    print(f"  far field {FAR_LO}-{FAR_HI} px  "
          f"{int(far.sum()):9d} {c_far:12.0f} {t_far:12.0f} {t_far-c_far:+12.0f}")

    # Whole-frame level: the crudest possible global check, and the one a
    # ratio-based metric can least afford to omit.
    c_all, t_all = float(np.median(c)), float(np.median(t))
    print(f"  whole frame       {c.size:9d} {c_all:12.0f} {t_all:12.0f} "
          f"{t_all-c_all:+12.0f}")

    # --- the discriminator ---------------------------------------------------
    vals = np.array([r[3] for r in rows], dtype=float)
    ds = np.array([0.5 * (r[0] + r[1]) for r in rows], dtype=float)
    # Aura zone: the measured peak sits near d~117 px. Read the deficit there
    # rather than at a single bin, so one noisy bin cannot carry the verdict.
    aura = (ds >= 80) & (ds <= 200)
    print()
    print("--- levels, not ratios -------------------------------------------")
    if aura.any():
        c_aura = float(vals[aura, 0].mean())
        t_aura = float(vals[aura, 1].mean())
        print(f"  aura zone (d 80-200 px)  control {c_aura:8.0f} DN   "
              f"pyramid {t_aura:8.0f} DN")
        print(f"    deficit against own far field: "
              f"control {c_aura - c_far:+.0f} DN, pyramid {t_aura - t_far:+.0f} DN")
    print(f"  far-field shift (pyramid - control) : {t_far - c_far:+.0f} DN")
    print(f"  whole-frame shift                   : {t_all - c_all:+.0f} DN")
    print()
    print("  A real local fix moves the near-silhouette rows and leaves the far")
    print("  field alone. A global level shift moves the far field and the whole")
    print("  frame with it, and would null a veiling ERROR metric without")
    print("  improving the photograph. Read the far-field shift before the")
    print("  aura numbers: if it is large, the aura numbers mean nothing.")


if __name__ == "__main__":
    main()
