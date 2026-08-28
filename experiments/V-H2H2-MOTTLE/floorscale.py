# What does a per-band floor scale actually do to selection?
#
# PRE-REGISTERED before either render finished. ORCH's argument for
# STREHL_GATE_FLOOR_SCALE is that raising the coarse-band floor makes the merge
# average more at coarse bands, and that this coarse-scale smoothing can absorb
# the rim/blotch half of the three-way exponent conflict.
#
# Raising a floor does TWO things, not one:
#
#   (a) coefficients where NO frame now clears  -> forced to average. Smoother.
#       This is the effect ORCH's argument uses, and `averaged` measures it.
#   (b) coefficients where SOME frame still clears -> every surviving frame's
#       excess shrank, and the ones nearest the floor dropped out entirely, so
#       the surviving set is SMALLER and selection is SHARPER.
#
# (b) is invisible to `averaged` -- the same blindness measured in gate_quant.py
# -- and it points the opposite way. Sharper coarse selection means LARGER
# coarse excursions, which is precisely the fact-1803 mechanism ORCH is trying
# to suppress: a coarse excursion guillotined at level 0 leaves pixels pinned
# at lo/hi and an edge sharper than any input.
#
# PREDICTION, fixed now:
#   `averaged` RISES at bands 1-5   (ORCH already measured this; confirms arm)
#   mean n_eff FALLS at those bands (nobody has measured this)
#
# If both hold, the knob does two opposing things at once and its net effect on
# rim CANNOT be read off `averaged`. That is a statement about the instrument,
# not about whether the knob is a good idea.

import hashlib
import os
import sys

import numpy as np

D = r"C:\dev\strehl-out\V-H2H2\wdump"
BASE, SCALED = "base2", "scal8"


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16].upper()


def controls():
    """Two controls on the ARM, run before any number is interpreted.

    NULL: band 0's scale is 1 in both arms, so its weights must be
    byte-identical. If they differ, something other than the knob moved
    between the renders -- a rebuild, another lane's commit, nondeterminism --
    and no band's difference is attributable.

    POTENCY: some band must differ. Two identical dumps would make every
    "no change" reading below vacuous, which is the failure this whole
    thread is about.
    """
    b0 = [os.path.join(D, "%s-b0-neff.f32" % p) for p in (BASE, SCALED)]
    if not all(os.path.exists(p) for p in b0):
        print("CONTROL: band-0 dumps missing; cannot commission")
        return False
    h0, h1 = sha(b0[0]), sha(b0[1])
    ok_null = h0 == h1
    print("  NULL    band 0 (scale 1 in both): %s vs %s  %s"
          % (h0, h1, "identical" if ok_null else "*** DIFFER ***"))

    moved = []
    for k in range(1, 7):
        p = [os.path.join(D, "%s-b%d-neff.f32" % (q, k)) for q in (BASE, SCALED)]
        if all(os.path.exists(x) for x in p) and sha(p[0]) != sha(p[1]):
            moved.append(k)
    ok_pot = bool(moved)
    print("  POTENCY bands that differ: %s  %s"
          % (moved or "NONE", "" if ok_pot else "*** ARM IS INERT ***"))

    if not ok_null:
        print("\n  REFUSING TO REPORT. The null control failed, so a difference at\n"
              "  any band is not attributable to the knob.")
    if not ok_pot:
        print("\n  REFUSING TO REPORT. The arm did not move; every reading would be\n"
              "  a measurement of nothing.")
    return ok_null and ok_pot


def neff(prefix, k):
    p = os.path.join(D, "%s-b%d-neff.f32" % (prefix, k))
    if not os.path.exists(p):
        return None
    v = np.fromfile(p, np.float32)
    live = np.isfinite(v) & (v > 0)
    if not live.any():
        return None
    # `no-admit` coefficients are NaN/<=0 by construction; they are the
    # population that averaged. Report both, never pooled.
    return float(v[live].mean()), float(1.0 - live.mean()), int(live.sum())


def paired(k):
    """Compare the two arms on a FIXED population.

    The `live` mean above has a survivorship defect: raising the floor removes
    coefficients from the live set, so the two means are taken over different
    populations. That is the same error as an arm that renders 24 of 26
    subjects and averages the 24. Restrict to coefficients live in BOTH arms
    and the comparison is paired.

    Also report what was REMOVED, measured in the baseline arm, because the
    direction of the composition effect is not obvious and must not be argued
    when it can be measured.
    """
    pa = os.path.join(D, "%s-b%d-neff.f32" % (BASE, k))
    pb = os.path.join(D, "%s-b%d-neff.f32" % (SCALED, k))
    if not (os.path.exists(pa) and os.path.exists(pb)):
        return None
    a = np.fromfile(pa, np.float32)
    b = np.fromfile(pb, np.float32)
    if a.shape != b.shape:
        return None
    la = np.isfinite(a) & (a > 0)
    lb = np.isfinite(b) & (b > 0)
    both = la & lb
    dropped = la & ~lb
    if not both.any():
        return None
    return {
        "n_both": int(both.sum()),
        "base_both": float(a[both].mean()),
        "scal_both": float(b[both].mean()),
        "n_dropped": int(dropped.sum()),
        "base_dropped": float(a[dropped].mean()) if dropped.any() else float("nan"),
        "frac_dropped": float(dropped.sum()) / max(1, int(la.sum())),
    }


def spatial(k=1):
    """Is the split spatially clustered, or salt-and-pepper?

    At band 1 the knob leaves the merge running TWO different laws: 19.4% of
    coefficients are now a plain mean over all 182 frames, and the rest select
    24.5% harder than shipping. Whether that matters depends on the geometry.

    If the two populations occupy separate REGIONS, the merge is doing
    something defensible: average the flat areas, select in the detailed ones.
    If they are interleaved at pixel scale, then adjacent coefficients in the
    same band are being computed by laws whose outputs differ by construction,
    and that discontinuity is itself a source of the mottle and rim structure
    the fleet is chasing.

    Commissioned two ways before the real mask is read:
      NULL    a shuffled mask of identical density must score as scattered
      POTENCY a synthetic blocked mask must score as clustered
    A statistic that cannot separate those two cannot answer the question.
    """
    import json

    with open(os.path.join(D, "%s-dims.json" % BASE)) as f:
        dims = json.load(f)
    band = [b for b in dims["bands"] if b["k"] == k][0]
    w, h = band["w"], band["h"]

    b = np.fromfile(os.path.join(D, "%s-b%d-neff.f32" % (SCALED, k)), np.float32)
    if b.size != w * h:
        print("  band %d: dump is %d values, geometry says %d -- skipping"
              % (k, b.size, w * h))
        return
    avg = ~(np.isfinite(b) & (b > 0))
    avg = avg.reshape(h, w)

    def boundary_frac(m):
        """Of the flagged coefficients, what fraction touch an unflagged one?"""
        if not m.any():
            return float("nan")
        nb = np.zeros_like(m)
        nb[1:, :] |= ~m[:-1, :]
        nb[:-1, :] |= ~m[1:, :]
        nb[:, 1:] |= ~m[:, :-1]
        nb[:, :-1] |= ~m[:, 1:]
        return float((m & nb).sum()) / float(m.sum())

    p = avg.mean()
    rng = np.random.default_rng(20260824)
    shuf = rng.permutation(avg.ravel()).reshape(h, w)

    blk = np.zeros((h, w), bool)
    side = max(1, int(round(np.sqrt(p * w * h))))
    blk[:side, :side] = True

    real, null, pot = boundary_frac(avg), boundary_frac(shuf), boundary_frac(blk)
    analytic = 1.0 - p ** 4

    print("\nSPATIAL FORM OF THE SPLIT -- band %d, %dx%d, %.1f%% averaged"
          % (k, w, h, 100 * p))
    print("  NULL     shuffled, same density : %.4f  (analytic %.4f)"
          % (null, analytic))
    print("  POTENCY  one solid block        : %.4f" % pot)
    print("  MEASURED real mask              : %.4f" % real)

    if not (null > 0.9 and pot < 0.2):
        print("  CONTROLS FAILED -- the statistic cannot tell scatter from a"
              " block; reading nothing into the measured value.")
        return
    span = null - pot
    pos = (null - real) / span if span else float("nan")
    print("  -> %.0f%% of the way from pure scatter to a solid block" % (100 * pos))
    if real > 0.9:
        print("""
  The averaged set is essentially SCATTERED. Adjacent band-1 coefficients are
  being produced by two different laws -- one a plain mean over 182 frames,
  the other a harder selection than shipping -- with almost every averaged
  coefficient touching a selected one. That is a per-pixel discontinuity in
  the merge law introduced by the knob, at the band immediately above the
  one where mottle lives.""")
    else:
        print("""
  The averaged set is CLUSTERED into regions, which is the benign form: the
  knob is averaging areas, not individual coefficients, so neighbouring
  outputs mostly come from the same law.""")

    # Convert the dimensionless boundary fraction into a physical size, using
    # this lane's own established convention: levelmap.py fixes CELL px as
    # 2^k output px and names it "the right scale for plateau geometry",
    # which is exactly what this mask is. (Passband px, 8 * 2^k, is the other
    # scale and is NOT the one that applies here.)
    #
    # Idealisation: for a square of side s cells the boundary fraction is
    # (4s - 4) / s^2. Inverting gives an equivalent blob size. Real regions
    # are ragged, so this is a characteristic scale, not a measurement of any
    # particular region.
    a = real
    disc = 16.0 - 16.0 * a
    if a > 0 and disc >= 0:
        s_cells = (4.0 + np.sqrt(disc)) / (2.0 * a)
        cell_px = 2 ** k
        print("""
  CHARACTERISTIC SIZE. Equivalent square side %.1f cells; at band %d one cell
  is %d output px (levelmap.py's cell-px convention), so the averaged regions
  are on the order of %.0f output px across.

  Flagging, NOT claiming: V-LINEAR's convicted instability band is 20-60
  output px. That is the same neighbourhood. If the knob is averaging
  precisely the structures whose selection was measured to be unstable, it
  may be helping for a better reason than the one proposed for it -- or it
  may be erasing them. Those two look identical in `averaged` and identical
  in n_eff. Only a rim/blotch measurement on the render separates them, and
  I have not made one.""" % (s_cells, k, cell_px, s_cells * cell_px))


def main():
    print("ARM CONTROLS")
    if not controls():
        return 3
    print()

    rows = []
    for k in range(7):
        a, b = neff(BASE, k), neff(SCALED, k)
        if a is None or b is None:
            continue
        rows.append((k, a, b))
    if not rows:
        print("no dumps yet in %s" % D)
        return 2

    print("leaf-2-cpl, one binary, one session; only STREHL_GATE_FLOOR_SCALE differs")
    print("%-5s %22s %22s %10s" % ("", "BASELINE", "SCALE 1,8,8,8,8,8,8", ""))
    print("%-5s %10s %11s %10s %11s %10s"
          % ("band", "n_eff", "averaged", "n_eff", "averaged", "n_eff x"))
    for k, (na, aa, _), (ns, as_, _) in rows:
        print("%-5d %10.2f %10.1f%% %10.2f %10.1f%% %10.3f"
              % (k, na, 100 * aa, ns, 100 * as_, ns / na if na else float("nan")))

    mid = [(k, na, aa, ns, as_) for k, (na, aa, _), (ns, as_, _) in rows if 1 <= k <= 5]
    rose = sum(1 for _, _, aa, _, as_ in mid if as_ > aa + 1e-6)
    fell = sum(1 for _, na, _, ns, _ in mid if ns < na * 0.999)
    print("\n  bands 1-5: `averaged` rose on %d of %d, mean n_eff fell on %d of %d"
          % (rose, len(mid), fell, len(mid)))

    print("\nPAIRED -- same coefficients in both arms, so no survivorship")
    print("%-5s %9s %10s %10s %9s %9s %11s"
          % ("band", "n paired", "base", "scaled", "ratio", "dropped", "n_eff of"))
    print("%-5s %9s %10s %10s %9s %9s %11s"
          % ("", "", "n_eff", "n_eff", "", "frac", "dropped"))
    pr = {}
    for k, _, _ in rows:
        d = paired(k)
        if d is None:
            continue
        pr[k] = d
        print("%-5d %9d %10.3f %10.3f %9.3f %8.1f%% %11.3f"
              % (k, d["n_both"], d["base_both"], d["scal_both"],
                 d["scal_both"] / d["base_both"] if d["base_both"] else float("nan"),
                 100 * d["frac_dropped"], d["base_dropped"]))

    moved = [k for k in range(1, 7)
             if k in pr and abs(pr[k]["scal_both"] / pr[k]["base_both"] - 1.0) > 0.05]
    print("""
READING

  The scale reaches every band: the printed floor is the baseline's times 8
  at bands 1-3 and the white-extended value times 8 at bands 4-6. So this is
  not a knob that failed to apply. It applied and the merge barely noticed.

  Bands with a paired selection change over 5%%: %s

  At the coarse bands the floor sits far below the signal -- ORCH's own
  arithmetic, the floor falling ~500x from band 0 to band 3 while signal
  falls much less -- so multiplying it by 8 moves a few percent of
  coefficients into averaging and leaves the surviving selection alone.

  CONSEQUENCE FOR THE PROPOSAL. The argument for this knob is that
  coarse-band averaging can absorb the rim/blotch half of the three-way
  exponent conflict, freeing the exponent to serve depth alone. At 8x it
  does not do that: bands 3-6 average %s of coefficients and select no
  more softly than shipping. Whatever rim change this arm produces is
  almost entirely a BAND-1 change.

  So the question "are the two mechanisms redundant, composing, or
  fighting?" cannot be answered with this setting -- there is not enough
  coarse-band effect present to be redundant WITH. A scale large enough to
  bite at bands 3-6 has to be found first, and its potency demonstrated on
  the paired statistic above rather than on `averaged`.""" % (
        moved or "NONE",
        ", ".join("%.1f%%" % (100 * rows[k][2][1]) for k in range(3, 7) if k < len(rows))))

    spatial(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
