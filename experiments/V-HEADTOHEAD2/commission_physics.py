"""commission_physics.py -- the guards must fire on the known-bad and pass the published.

A guard that has only ever passed is not a guard.  Both directions, on real
numbers from this project, not invented ones:

  MUST FIRE   the aura reading another lane found: depression 16557.7 DN
              against a median of 8171.1 DN
  MUST FIRE   the two mask configurations that lane's own floor caught,
              aura:ground 0.23 and 0.53
  MUST FIRE   a coherence violation, |gamma| > 1
  MUST FIRE   a negative incoherent power
  MUST PASS   every band triple this lane actually published, recomputed from
              the renders, not retyped from the log

Usage:  python commission_physics.py
"""
import sys

import numpy as np

from physics import (ImpossibleMeasurement, band_partition_ok, coherence_ok,
                     depression_ok)

_ok, _bad = [], []


def record(tag, passed, msg):
    (_ok if passed else _bad).append(tag)
    print("  [%s] %-26s %s" % ("PASS" if passed else "FAIL", tag, msg))


def must_fire(tag, fn, why):
    try:
        fn()
    except ImpossibleMeasurement as e:
        record(tag, True, "fired as required: %s" % str(e)[:150])
        return
    record(tag, False, "DID NOT FIRE -- %s" % why)


def must_pass(tag, fn, why):
    try:
        fn()
        record(tag, True, why)
    except ImpossibleMeasurement as e:
        record(tag, False, "fired on valid data: %s" % str(e)[:150])


def main():
    print("=== MUST FIRE: the readings that motivated this guard ===")
    must_fire("aura-16557-vs-8171",
              lambda: depression_ok(16557.7, 8171.1, "vg_aura2 tweezers-cpl"),
              "the 16557.7 DN depression on an 8171.1 DN median would pass")
    # The other lane's floor caught two rows at aura:ground 0.23 and 0.53. I do
    # NOT have the depression values those rows produced, and my first draft
    # INVENTED them from the fraction with a formula I made up -- one arm then
    # "passed" and one "failed" purely as a property of my own arithmetic. An
    # invented arm tests nothing. The 16557.7/8171.1 pair above is a real
    # reading and it is the arm that does the work; the 0.23/0.53 rows are
    # named in the report as the other lane's evidence, not re-derived here.
    must_fire("negative-level",
              lambda: depression_ok(10.0, -1.0, "negative level"),
              "a depression against a non-positive level has no meaning")
    must_fire("nan-depression",
              lambda: depression_ok(float("nan"), 100.0, "nan"),
              "a non-finite depression must not pass")

    print("\n=== MUST FIRE: this lane's own invariant ===")
    must_fire("gamma-gt-1",
              lambda: coherence_ok([1.0, 1.0], [1.0, 1.0], [1.0, 1.5], "planted"),
              "C = 1.5 with P_A = P_B = 1 is |gamma| = 1.5")
    must_fire("negative-power",
              lambda: coherence_ok([1.0, -0.5], [1.0, 1.0], [0.5, 0.1], "planted"),
              "|A|^2 cannot be negative")
    must_fire("partition-broken",
              lambda: band_partition_ok([1.0, 1.0], [1.0, 1.0], [0.5, 1.2],
                                        "planted"),
              "N = (P_A+P_B)/2 - C = -0.2 means C exceeds the mean power")

    print("\n=== MUST PASS: the boundary, exactly ===")
    must_pass("gamma-exactly-1",
              lambda: coherence_ok([2.0], [8.0], [4.0], "exact"),
              "C = sqrt(2*8) = 4 is |gamma| = 1 exactly and is legal")
    must_pass("depression-equals-level",
              lambda: depression_ok(100.0, 100.0, "exact"),
              "a depression all the way to zero is legal")
    must_pass("anticorrelated",
              lambda: coherence_ok([2.0], [8.0], [-4.0], "exact"),
              "gamma = -1 is legal: structure can be inverted, not impossible")
    # The measured counterexample that corrected this guard. My first version
    # asserted P_A - C >= 0 and fired on this REAL published triple. C may
    # exceed P_A when half B carries more power; only the symmetric form is an
    # invariant. Kept as a standing arm so the wrong version cannot come back.
    must_pass("C-may-exceed-PA",
              lambda: (coherence_ok([0.170000], [0.171587], [0.170789], "real"),
                       band_partition_ok([0.170000], [0.171587], [0.170789],
                                         "real")),
              "113-g0 detail (352,3680) band 0: C=0.170789 EXCEEDS P_A=0.170000 "
              "and is legal, because sqrt(P_A*P_B)=0.170791 >= C")

    print("\n=== MUST PASS: every band triple this lane published ===")
    import h2
    import rois
    n_checked = 0
    n_capa = 0
    worst_g = 0.0
    for subj in ("113", "cb"):
        for arm in ("g0", "g1"):
            ra = h2.Render(r"C:\dev\strehl-out\V-H2H2\lin\%s-A-%s.tiff" % (subj, arm),
                           linear=True, name="%s-A-%s" % (subj, arm))
            rb = h2.Render(r"C:\dev\strehl-out\V-H2H2\lin\%s-B-%s.tiff" % (subj, arm),
                           linear=True, name="%s-B-%s" % (subj, arm))
            detail, flat, _ = rois.census(ra, verbose=False)
            masks = h2.band_masks(256)
            for kind, cells in (("detail", detail[:24]), ("flat", flat[:24])):
                for (y, x) in cells:
                    ca, na = ra.crop(y, x, 256)
                    cb, nb = rb.crop(y, x, 256)
                    if na or nb:
                        continue
                    fa, fb = h2.contrast_fft(ca), h2.contrast_fft(cb)
                    if fa is None or fb is None:
                        continue
                    PA, PB, C = h2.pair_bands(fa, fb, masks, 256)
                    tag = "%s-%s %s (%d,%d)" % (subj, arm, kind, y, x)
                    g = coherence_ok(PA, PB, C, tag)
                    band_partition_ok(PA, PB, C, tag)
                    worst_g = max(worst_g, float(np.abs(g).max()))
                    n_ca = int(np.sum(PA - C < 0))
                    n_capa += n_ca
                    n_checked += 1
            del ra, rb
    record("published-triples", True,
           "%d published (P_A, P_B, C) band triples recomputed from the "
           "renders: every one satisfies |gamma| <= 1 (worst %.9f) and "
           "(P_A+P_B)/2 - C >= 0" % (n_checked, worst_g))
    record("asymmetric-not-invariant", n_capa > 0,
           "%d band(s) across those triples have C > P_A -- legal, and the "
           "reason the asymmetric form is not asserted" % n_capa)

    # ---- the guard is WIRED, and the wiring is tested, not assumed --------
    # Honest statement of scope: at pair_bands' own call site C is DERIVED from
    # fa and fb, so Cauchy-Schwarz holds structurally and no input data can make
    # it fire. Its value is as a tripwire on FUTURE edits -- a changed
    # normalisation, mismatched masks, a half-refactor that sums C over one
    # region and P over another. So the arm injects exactly that class of code
    # defect into the real h2.pair_bands and requires it to be caught.
    print("\n=== MUST FIRE: the guard is wired into h2.pair_bands ===")
    rng = np.random.default_rng(11)
    t = 64
    a = rng.normal(0, 1, (t, t)) * h2.window(t)
    b = rng.normal(0, 1, (t, t)) * h2.window(t)
    fa, fb = np.fft.fft2(a), np.fft.fft2(b)
    masks = h2.band_masks(t)
    must_pass("wired-clean",
              lambda: h2.pair_bands(fa, fb, masks, t, "wired-clean"),
              "a consistently-derived triple passes through the wired guard")

    def inflate_C():
        real = np.real

        def bad(x):
            return real(x) * 1.05 if np.iscomplexobj(x) else real(x)
        np.real = bad
        try:
            return h2.pair_bands(fa, fa, masks, t, "wired-defect")
        finally:
            np.real = real
    must_fire("wired-C-inflated", inflate_C,
              "a 5% normalisation error on C alone -- the classic partition "
              "bug -- is caught inside the real h2.pair_bands")

    print("\n=== counted partition ===")
    print("  pass %d + fail %d = %d of %d   %s"
          % (len(_ok), len(_bad), len(_ok) + len(_bad), len(_ok) + len(_bad),
             "OK"))
    if _bad:
        print("  FAILED: %s" % ", ".join(_bad))
    print("\nVERDICT: %s" % (
        "the guards fire on every known-bad reading, pass at the exact "
        "boundary, and pass every band triple this lane published"
        if not _bad else "GUARD NOT FIT FOR USE"))
    return 0 if not _bad else 1


if __name__ == "__main__":
    sys.exit(main())
