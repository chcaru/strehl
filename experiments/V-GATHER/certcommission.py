r"""Commission the coverage ratio BEFORE believing it, with an improvement arm.

WHY AN IMPROVEMENT ARM IS NOT OPTIONAL HERE. This project shipped a print-
readiness verdict (BUILD-TRIAGE, d6e5a809) in which every term was a magnitude
bounded below by zero, so a haloed merge could only ever score at or ABOVE a
clean one. Its commissioning never caught it because every planted defect made
the image worse and they checked the number went down.

    A metric can be BLIND to a defect (reads nothing) or PERVERSE on it (reads
    better). Planting only degradations cannot separate those, because both
    present as a pass. Only a planted IMPROVEMENT, required to read BETTER,
    distinguishes a live instrument from one whose error sign is bounded.

THE TWO ARMS THAT ARE NOT ABOUT THE NUMERATOR:

  DENOMINATOR. `best source frame` is an argmin over frames. Every instrument
  convicted in this lane tonight shared one un-perturbed reference across all
  its arms, which is exactly why an otherwise exemplary commissioning was blind.
  So one arm holds the master FIXED and moves only the sources.

  DEFOCUS ORACLE. Blur lowers mid-scale band energy. If the argmin selects the
  most defocused frame, the denominator IS defocus and the ratio is measuring
  focus, not blotch. A ratio used as an argmax over a focus stack has already
  been caught selecting defocus in this project. This arm plants a heavily
  blurred frame and requires the selector to REFUSE it.
"""
import os
import sys

import numpy as np

ORCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ORCH-drift-check")
sys.path.insert(0, os.path.abspath(ORCH))
from orch_blotch import blotch_ratio                       # noqa: E402

WIN = 900
RNG = np.random.default_rng(20260827)


def boxblur2(a, r):
    """Box blur with EDGE padding, via summed-area.

    The first version used np.convolve(..., "same"), which ZERO-pads. At r=200
    on a 900px window that corrupts a 200px border -- 60% of the area -- pulling
    the local mean toward zero there. `blotch = band/mean`, so a depressed mean
    inflates the statistic, and the harness manufactured a ratio of 359 for an
    image it had just repaired. The planted-improvement arm caught it on its
    first run. Recorded rather than quietly fixed: the defect was in my
    instrument, not in the statistic under test, and that is the ordinary case.
    """
    if r < 1:
        return a.copy()
    w = 2 * r + 1
    out = a.astype(np.float64)
    for ax in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[ax] = (r, r)
        q = np.pad(out, pad, mode="edge")
        c = np.cumsum(q, axis=ax)
        c = np.concatenate([np.zeros_like(np.take(c, [0], axis=ax)), c], axis=ax)
        n = out.shape[ax]
        hi = np.take(c, np.arange(w, w + n), axis=ax)
        lo = np.take(c, np.arange(0, n), axis=ax)
        out = (hi - lo) / w
    return out.astype(np.float32)


def scene(seed):
    """A flat-ish patch: base level, fine subject texture, sensor noise."""
    g = np.random.default_rng(seed)
    base = 8000.0
    tex = boxblur2(g.normal(0, 1, (WIN, WIN)).astype(np.float32), 3) * 120.0
    noise = g.normal(0, 45, (WIN, WIN)).astype(np.float32)
    return base + tex + noise


def blotch_field(amp, seed=7):
    """Mid-scale mottling in the 50-400 px band -- the defect being detected."""
    g = np.random.default_rng(seed)
    c = g.normal(0, 1, (WIN // 100 + 2, WIN // 100 + 2)).astype(np.float32)
    yy = np.clip(np.linspace(0, c.shape[0] - 1, WIN).astype(int), 0, c.shape[0] - 1)
    xx = np.clip(np.linspace(0, c.shape[1] - 1, WIN).astype(int), 0, c.shape[1] - 1)
    f = c[np.ix_(yy, xx)]
    return boxblur2(f, 60) * amp


def stat(img):
    return blotch_ratio(img)[0]


def sharp(img):
    d = img[::4, ::4]
    return float(np.abs(np.diff(d, axis=0)[:, :-1]).mean()
                 + np.abs(np.diff(d, axis=1)[:-1, :]).mean())


FOCUS_FLOOR = 0.50


def best_index(vals, focus):
    """Least-blotch source frame AMONG THOSE IN FOCUS IN THE WINDOW.

    A plain argmin is unusable here and the ORACLE arm proves it. Blur removes
    mid-scale band energy, so the smoothest reading over a focus stack is the
    frame that is least in focus -- and in a focus stack EVERY frame is
    defocused over most of the field by construction, so this is structural, not
    a hazard that happens to bite. The floor is admitted rather than assumed:
    the FOCUS LADDER arm below measures the blur radius at which each selector
    starts failing, so the number has a measured reach instead of a plausible one.
    """
    hi = max(focus)
    keep = [i for i, f in enumerate(focus) if f >= FOCUS_FLOOR * hi]
    if not keep:
        return None
    return min(keep, key=lambda i: vals[i])


def ratio(master, sources, guard=False):
    """master / BEST source. The label is derived from the rule, not typed."""
    vals = [stat(s) for s in sources]
    if not guard:
        return stat(master) / min(vals), vals
    i = best_index(vals, [sharp(s) for s in sources])
    return stat(master) / vals[i], vals


def main():
    sources = [scene(100 + i) for i in range(8)]
    avg = np.mean(sources, axis=0).astype(np.float32)
    rows, ok = [], True

    def arm(name, want, got, test, why):
        nonlocal ok
        good = test(got)
        ok = ok and good
        rows.append((name, want, "%.4f" % got if isinstance(got, float) else str(got),
                     "ok" if good else "WRONG", why))

    # 1 NULL -- the same image both sides. Not "small": EXACTLY 1.
    r, _ = ratio(sources[0], [sources[0]])
    arm("NULL   master IS the only source", "== 1.0000", r,
        lambda v: abs(v - 1.0) < 1e-12, "byte-identical input must read unity exactly")

    # 2 PHYSICS-FIXED -- a master that IS one of its own sources cannot beat the
    #   best of them. This bound is arithmetic, not empirical.
    r_id, _ = ratio(sources[3], sources)
    arm("PHYSICS master is source[3], full set", ">= 1.0000", r_id,
        lambda v: v >= 1.0 - 1e-12, "min over a set containing x cannot exceed x")

    # 3 CLEAN MERGE -- an average. Real improvement: averaging kills noise.
    r_clean, _ = ratio(avg, sources)
    arm("CLEAN  master = mean of sources", "< 1.0000", r_clean,
        lambda v: v < 1.0, "averaging 8 frames must not read blotchier than one")

    # 4 PLANTED DEFECT -- ladder. Each rung must read strictly worse.
    prev, mono = r_clean, True
    for amp in (20.0, 60.0, 180.0):
        r, _ = ratio(avg + blotch_field(amp), sources)
        mono = mono and r > prev
        rows.append(("DEFECT master + %5.0f DN blotch" % amp, "> previous",
                     "%.4f" % r, "ok" if r > prev else "WRONG",
                     "a planted mid-scale field must raise the ratio"))
        ok = ok and r > prev
        prev = r

    # 5 PLANTED IMPROVEMENT -- THE ARM THE SHIPPED GATE DID NOT HAVE.
    #   Take the WORST case and genuinely repair it. The ratio must FALL. A
    #   statistic bounded below by the reference reads this as no change.
    dirty = avg + blotch_field(180.0)
    r_dirty, _ = ratio(dirty, sources)

    # 5a A BLIND repair -- band-stop over the 40..200px scales. It is not told
    #    where the planted field is, so it cannot cheat by subtracting it.
    repaired = dirty - (boxblur2(dirty, 40) - boxblur2(dirty, 200))
    r_rep, _ = ratio(repaired, sources)
    arm("IMPROVE blind band-stop repair of the master", "< %.4f" % r_dirty, r_rep,
        lambda v: v < r_dirty * 0.98,
        "a real repair must SCORE BETTER, not merely not-worse")

    # 5b A GRADED repair -- the defect ladder walked backwards. A statistic can
    #    register the presence of a repair yet be insensitive to its degree;
    #    this requires the ordering to survive as well as the sign.
    prev_up, grad = r_dirty, True
    for frac in (0.75, 0.5, 0.25, 0.0):
        r, _ = ratio(avg + blotch_field(180.0) * frac, sources)
        grad = grad and r < prev_up
        rows.append(("IMPROVE %2.0f%% of the defect left in place" % (frac * 100),
                     "< previous", "%.4f" % r, "ok" if r < prev_up else "WRONG",
                     "partial repair must score partially better"))
        ok = ok and r < prev_up
        prev_up = r

    # 6 DENOMINATOR -- master untouched; only the reference moves.
    worse_src = [s + blotch_field(150.0, seed=200 + i) for i, s in enumerate(sources)]
    r_before, _ = ratio(avg, sources)
    r_after, _ = ratio(avg, worse_src)
    arm("DENOM  sources degraded, master fixed", "< %.4f" % r_before, r_after,
        lambda v: v < r_before * 0.98,
        "if this does not move, no arm perturbs the reference")

    # 7 DEFOCUS ORACLE -- does argmin select the blurred frame?
    blurred = boxblur2(sources[0], 12)
    cand = sources + [blurred]
    vals = [stat(c) for c in cand]
    picked = int(np.argmin(vals))
    sharps = [sharp(c) for c in cand]
    # POSITIVE CONTROL ON THE GUARD. This arm asserts the defect is PRESENT.
    # If the plain argmin were not fooled there would be nothing for the guard
    # to defeat, and the guarded arm below would pass while testing nothing --
    # a probe that has never refused anything is not known to be a probe.
    arm("CONTROL plain argmin IS fooled by the blurred frame",
        "must pick 8", picked, lambda v: v == len(sources),
        "the defect must be live, or the guard's pass is vacuous")

    g = best_index(vals, sharps)
    arm("ORACLE focus-guarded argmin, same set", "must NOT pick 8", g,
        lambda v: v != len(sources), "the guard exists solely to survive this")

    # The guard must not be degenerate -- if it merely returned the sharpest
    # frame it would pass the arm above while measuring nothing about blotch.
    clean_only = [stat(c) for c in sources]
    g2 = best_index(clean_only, [sharp(c) for c in sources])
    arm("ORACLE guarded argmin, no blurred frame present",
        "== plain argmin", g2, lambda v: v == int(np.argmin(clean_only)),
        "with all frames in focus the guard must be inert, not opinionated")

    print("%-46s %-12s %-9s %-6s %s" % ("arm", "want", "got", "", "why"))
    print("-" * 128)
    for n, w, g, v, why in rows:
        print("%-46s %-12s %-9s %-6s %s" % (n, w, g, v, why))

    print("\nDEFOCUS DIAGNOSTIC -- blotch vs sharpness over the candidate set")
    print("  %-6s %10s %10s" % ("idx", "blotch", "sharpness"))
    for i, (v, sh) in enumerate(zip(vals, sharps)):
        tag = "  <-- BLURRED PLANT" if i == len(sources) else ""
        print("  %-6d %10.5f %10.3f%s" % (i, v, sh, tag))
    print("  argmin blotch = idx %d;  argmin sharpness = idx %d;  guarded = %s"
          % (picked, int(np.argmin(sharps)), g))

    # FOCUS LADDER. FOCUS_FLOOR = 0.50 is a choice, and a chosen constant with no
    # measured reach is the same defect as a name standing in for a physical
    # property. This prices it: at which blur radius does each selector break?
    print("\nFOCUS LADDER -- blur radius vs which selector is fooled")
    print("  %-6s %10s %10s %8s %8s" % ("r", "blotch", "sharp", "plain", "guarded"))
    for r_blur in (1, 2, 4, 8, 16, 32):
        c = sources + [boxblur2(sources[0], r_blur)]
        v = [stat(z) for z in c]
        f = [sharp(z) for z in c]
        pl = int(np.argmin(v)) == len(sources)
        gd = best_index(v, f) == len(sources)
        print("  %-6d %10.5f %10.3f %8s %8s"
              % (r_blur, v[-1], f[-1], "FOOLED" if pl else "ok",
                 "FOOLED" if gd else "ok"))

    n = len(rows)
    print("\n%s" % ("COMMISSIONED: %d/%d arms landed on their intended side, "
                    "including a planted IMPROVEMENT that had to score better and "
                    "a reference-only perturbation." % (n, n) if ok else
                    "NOT COMMISSIONED: an arm landed on the wrong side."))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
