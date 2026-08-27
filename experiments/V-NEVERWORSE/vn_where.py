"""Does the master's band excess sit where the subject MOVED?

ORCH's point 3: coffee-bubbles has bubble motion between frames. If the excess
localises to the moving sites, the mechanism is a robustness failure -- content
that moved was not rejected -- which is a product defect. If the excess is
spread indifferently across the window, the mechanism is something else and
motion is a bystander.

That is a spatial question and it is measurable, so I measure it rather than
looking at a crop and forming an impression. The window is cut into tiles; each
tile gets an excess (master band vs the frames' own leave-one-out null, so the
comparison is candidate-count matched) and a motion score (how much the frames
disagree with each other at band scale). The statistic is the rank correlation
between the two maps.

COMMISSIONING, four arms, and it perturbs in both directions:
  - excess injected WHERE MOTION IS HIGH   -> correlation must RISE
  - excess injected WHERE MOTION IS LOW    -> correlation must FALL below zero
  - excess injected UNIFORMLY (placebo)    -> correlation must NOT move
  - motion map shuffled (denominator)      -> correlation must collapse to ~0
An instrument that only ever rises under disturbance cannot tell a localised
defect from a global one.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_bubbles as B  # noqa: E402
import vn_lib as L  # noqa: E402
import vn_mech as M  # noqa: E402

T = 100
STRIDE = 100


def tiles(n):
    r = range(0, n - T + 1, STRIDE)
    return [(y, x) for y in r for x in r]


def stds(mlum, flums):
    """Per-tile band std for the master and every frame, plus motion. Computed
    once; the excess maps are then cheap re-combinations of it."""
    mb = B.nband(mlum)
    fb = np.stack([B.nband(f) for f in flums])
    ms, fs, mo, ij = [], [], [], []
    for (y, x) in tiles(mlum.shape[0]):
        ms.append(float(mb[y:y + T, x:x + T].std()))
        fs.append([float(b[y:y + T, x:x + T].std()) for b in fb])
        p = fb[:, y:y + T, x:x + T].reshape(len(fb), -1)
        p = p - p.mean(1, keepdims=True)
        nn = np.linalg.norm(p, axis=1)
        ok = nn > 1e-12
        p = p[ok] / nn[ok][:, None]
        c = p @ p.T
        iu = np.triu_indices(len(p), 1)
        mo.append(1.0 - float(np.median(c[iu])) if len(p) > 1 else 0.0)
        ij.append((y, x))
    return np.array(ms), np.array(fs), np.array(mo), ij


def excess(ms, fs, drop=None):
    """Per-tile excess of one target against the minimum over a reference set.

    `drop` names a frame to serve as the target, and that frame is removed from
    its own reference set. This is what makes the master's z comparable to a
    frame's z: motion inflates any min-based excess, because a wider spread of
    frame band-std pushes the min down, so a positive reading is EXPECTED on a
    moving subject even from a blameless merge. Referencing the master against
    the frames' own z values divides that structural term out.
    """
    if drop is None:
        tgt, ref = ms, fs
    else:
        tgt = fs[:, drop]
        ref = np.delete(fs, drop, axis=1)
    return tgt / np.maximum(ref.min(axis=1), 1e-12)


def maps(mlum, flums):
    ms, fs, mo, ij = stds(mlum, flums)
    return excess(ms, fs), mo, ij




def score(ex, mo, nperm=4000, seed=7):
    """Is excess higher in the tiles that moved? Two groups, split at the
    median motion, scored as a z against a LABEL PERMUTATION null.

    The first design correlated excess against motion across tiles and could
    not be commissioned. The reason is worth recording because it is the same
    wall that refused ghost_peak: a 50-400 px band inside a 900 px window holds
    only a few tens of independent cells, so a rank correlation over tiles has
    a null spread near 0.19 and no plant clears it. Overlapping the tiles does
    not help -- measured, the null spread was 0.190 at 121 overlapping tiles
    and 0.183 at 36 disjoint ones, because overlapping tiles are not
    independent samples and the effective count never rose. The fix is not more
    tiles but fewer parameters: one group difference, and an empirical null
    built by permuting the motion labels over the SAME spatially correlated
    excess map, so the null inherits exactly the dependence the statistic has.
    """
    if len(ex) < 8:
        return 0.0, 0
    q = np.median(mo)
    hi, lo = mo > q, mo <= q
    if hi.sum() < 4 or lo.sum() < 4:
        return 0.0, int(hi.sum())
    obs = float(np.median(ex[hi]) - np.median(ex[lo]))
    rng = np.random.default_rng(seed)
    null = np.empty(nperm)
    idx = np.arange(len(ex))
    for i in range(nperm):
        rng.shuffle(idx)
        s = ex[idx]
        null[i] = np.median(s[hi]) - np.median(s[lo])
    sd = float(null.std())
    return (obs - float(null.mean())) / sd if sd > 0 else 0.0, int(hi.sum())


def synth(n=600, nf=12, seed=3):
    """A fixture with a baseline near zero, so BOTH directions have room.

    The first draft used an averaging master and pinned the baseline at -0.695:
    averaging mechanically suppresses band energy wherever the frames disagree,
    so excess was already almost perfectly anticorrelated with motion and the
    "inject where motion is LOW" arm had nowhere to fall. That is a ceiling in
    the fixture, not a property of the statistic, and moving the threshold to
    accommodate it would have certified an instrument that could only ever read
    one direction. A selecting master keeps the moving structure, so excess
    starts uncorrelated with motion and a plant can push it either way.
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    base = 900 + 260 * np.sin(yy / 71.0) * np.cos(xx / 83.0)
    frames = []
    for _ in range(nf):
        f = base.copy()
        for cy in range(60, n, 120):
            for cx in range(60, n // 2, 120):
                dy, dx = rng.normal(0, 26, 2)
                r = np.hypot(yy - cy - dy, xx - cx - dx)
                f += 620 * np.exp(-(r / 34.0) ** 2)
        frames.append(f + rng.normal(0, 6, (n, n)))
    m = frames[0] + rng.normal(0, 6, (n, n))
    return m, frames


def blob(n, ij, amp, rng):
    o = np.zeros((n, n))
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    for (y, x) in ij:
        o += amp * np.exp(-(((yy - y - T / 2) / 42.0) ** 2 +
                            ((xx - x - T / 2) / 42.0) ** 2))
    return o


def commission():
    m, fr = synth()
    n = m.shape[0]
    rng = np.random.default_rng(11)
    ms0, fs0, mo0, ij = stds(m, fr)
    zf = np.array([score(excess(ms0, fs0, drop=k), mo0)[0]
                   for k in range(fs0.shape[1])])
    zmed, zsd = float(np.median(zf)), float(np.std(zf)) + 1e-9

    def rel_of(mm):
        ms, _, _, _ = stds(mm, fr)
        return (score(excess(ms, fs0), mo0)[0] - zmed) / zsd

    s0 = rel_of(m)
    order = np.argsort(mo0)
    hi = [ij[i] for i in order[-10:]]
    lo = [ij[i] for i in order[:10]]
    A = 900.0

    arms = []
    v_hi = rel_of(m + blob(n, hi, A, rng))
    arms.append(("excess injected where motion is HIGH", v_hi, "> +2", v_hi > 2.0))
    v_lo = rel_of(m + blob(n, lo, A, rng))
    arms.append(("excess injected where motion is LOW", v_lo, "< -2", v_lo < -2.0))
    draws = []
    for _ in range(8):
        pick = [ij[i] for i in rng.choice(len(ij), 10, replace=False)]
        draws.append(rel_of(m + blob(n, pick, A, rng)))
    v_pl = float(np.mean(draws))
    sd = float(np.std(draws)) + 1e-6
    arms.append(("same injection at RANDOM sites (placebo)", v_pl,
                 "|v| < 2", abs(v_pl) < 2.0))
    arms.append(("HIGH beats placebo by > 2 sd (sd %.2f)" % sd, v_hi - v_pl,
                 "> 2 sd", v_hi - v_pl > 2 * sd))
    sh = mo0.copy()
    rng.shuffle(sh)
    zfs = np.array([score(excess(ms0, fs0, drop=k), sh)[0]
                    for k in range(fs0.shape[1])])
    v_sh = (score(excess(ms0, fs0), sh)[0] - float(np.median(zfs))) \
        / (float(np.std(zfs)) + 1e-9)
    arms.append(("motion map SHUFFLED (denominator)", v_sh,
                 "|v| < 2", abs(v_sh) < 2.0))
    sep = v_hi - v_lo
    arms.append(("HIGH and LOW are separated", sep, "> 4", sep > 4.0))

    print("")
    print("COMMISSIONING  vn_where  (%d tiles, %d frames)" % (len(ij), fs0.shape[1]))
    print("  the statistic is the master's moved-vs-still permutation z,")
    print("  expressed in sd of the 19 frames' OWN z values -- so the")
    print("  structural inflation that motion gives ANY min-based excess")
    print("  cancels, and the undisturbed baseline sits near zero.")
    print("  frame family z: median %+.2f  sd %.2f" % (zmed, zsd))
    print("  undisturbed master %+.3f sd" % s0)
    print("")
    print("  %-42s %8s  %-9s %s" % ("arm", "sd", "required", ""))
    ok = 0
    bad = []
    for name, v, req, p in arms:
        ok += bool(p)
        if not p:
            bad.append((name, req))
        print("  %-42s %+8.3f  %-9s %s" % (name, v, req, "ok" if p else "FAILED"))
    print("")
    print("  %d ok + %d failed = %d arms" % (ok, len(bad), len(arms)))
    for name, req in bad:
        print("  NOT COMMISSIONED: %s (required %s)" % (name, req))
    return 0 if not bad else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args(argv)
    if a.commission:
        return commission()
    print("REFUSED  spatial localisation is not commissioned and is not used.")
    print("")
    print("  The question was ORCH's: does coffee-bubbles' band excess sit")
    print("  where the bubbles moved? If it did, the mechanism would be a")
    print("  robustness failure -- content that moved was merged instead of")
    print("  rejected -- which is a better finding than a statistic")
    print("  disagreement. I could not measure it to a standard I trust.")
    print("")
    print("  Five designs, each failing for a reason I could measure:")
    print("    rank correlation over tiles      null spread 0.183, no plant clears it")
    print("    the same, tiles overlapped       null spread 0.190 -- overlapping")
    print("                                     tiles are not independent samples,")
    print("                                     so 121 of them bought no power")
    print("                                     over 36")
    print("    averaging-master fixture         baseline pinned at -0.695, the LOW")
    print("                                     arm had nowhere to fall")
    print("    two-group permutation z          5 of 6 arms, but the baseline sat")
    print("                                     at +3.36 because motion inflates")
    print("                                     ANY min-based excess")
    print("    z referenced to the frames' own  baseline -0.60 (the structural")
    print("                                     term does cancel), but see below")
    print("")
    print("  The final design is asymmetric, and that is the disqualifying")
    print("  measurement rather than an impression:")
    print("    injected where motion is LOW    -4.26 sd   detected")
    print("    injected at random sites        -2.68 sd   also moves")
    print("    injected where motion is HIGH   -0.44 sd   NOT detected")
    print("  It reads DE-localisation well and localisation barely. Since my")
    print("  real question is whether excess IS localised to motion, the one")
    print("  direction I need is the one it cannot read, and a green result")
    print("  from it would have been unearned.")
    print("")
    print("  Root cause, and it is the same wall that refused ghost_peak: a")
    print("  50-400 px band inside a 900 px window holds only a few tens of")
    print("  independent cells. The band scale and the window size jointly cap")
    print("  what ANY spatial analysis of blotch can resolve at this size.")
    print("  Answering this would need a larger window or a narrower band, and")
    print("  both change the statistic under test.")
    print("")
    print("  What stands without it: the excess is mid-scale (survival 0.995),")
    print("  it matches no frame (0 of 19 at or above the master), and the")
    print("  subject moved heavily (0.452 against a 0.0287 static baseline).")
    print("  Where inside the window it sits is unmeasured, and RESULT.md")
    print("  counts it as unmeasured.")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
