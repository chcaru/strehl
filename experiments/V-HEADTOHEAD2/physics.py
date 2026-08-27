"""physics.py -- invariants that no measurement may violate, as standing asserts.

An independent lane found `aura depression 16557.7 DN` on an image whose median
is `8171.1 DN`.  A range check passes that: 16557.7 is a perfectly ordinary
number for a 16-bit image.  What rejects it is a PHYSICS check -- a depression
is how far below a level something sits, so a depression larger than the level
means the annulus was not on the thing it claimed to be on.

This module exists so that class of error is a hard error in this lane rather
than a large number somebody has to notice.  Two invariants:

    depression_ok(d, level)   a depression cannot exceed the level it is
                              measured against, nor be negative and still be
                              called a depression.

    coherence_ok(PA, PB, C)   THE invariant this lane's published statistic
                              actually has.  V-H2H2 does not compute
                              depressions or annuli at all; its primitive is
                              (P_A, P_B, C) and Cauchy-Schwarz requires

                                  |C| <= sqrt(P_A * P_B)

                              so gamma = C / sqrt(P_A P_B) must lie in [-1, 1].
                              A coherent power exceeding the geometric mean of
                              the two powers it was formed from is exactly as
                              impossible as a depression exceeding its level,
                              and it is the form the error would take here.

Both are commissioned in BOTH directions in commission_physics.py: they must
fire on the known-bad numbers and must not fire on this lane's published ones.

They raise.  A guard that returns a flag somebody may forget to read is the
defect this project keeps shipping.
"""
import numpy as np


class ImpossibleMeasurement(AssertionError):
    """Raised when a number violates an invariant of the quantity it claims to be."""


def depression_ok(depression, level, tag="", tol=1e-9):
    """A depression below `level` must satisfy 0 <= d <= level.

    `level` is the reference the depression is measured DOWN FROM (e.g. the
    median of the ground annulus).  Both are in the same units.
    """
    d = float(depression)
    L = float(level)
    if not np.isfinite(d) or not np.isfinite(L):
        raise ImpossibleMeasurement(
            "%s: non-finite depression %r against level %r" % (tag, d, L))
    if L <= 0:
        raise ImpossibleMeasurement(
            "%s: level %.4f is not positive, so a depression against it has no "
            "meaning" % (tag, L))
    if d > L * (1.0 + tol):
        raise ImpossibleMeasurement(
            "%s: depression %.4f EXCEEDS the level %.4f it is measured against "
            "(%.2fx). A depression cannot be deeper than the thing it is "
            "measured down from -- the region sampled is not the region "
            "claimed." % (tag, d, L, d / L))
    return d


def coherence_ok(pa, pb, c, tag="", tol=1e-6):
    """|C| <= sqrt(P_A * P_B), elementwise. Returns gamma.

    tol is a relative slack for float summation over Fourier bins, not a
    licence: anything past it is an error, not a rounding artefact.
    """
    pa = np.asarray(pa, float)
    pb = np.asarray(pb, float)
    c = np.asarray(c, float)
    if not (np.all(np.isfinite(pa)) and np.all(np.isfinite(pb))
            and np.all(np.isfinite(c))):
        raise ImpossibleMeasurement("%s: non-finite band power" % tag)
    if np.any(pa < 0) or np.any(pb < 0):
        raise ImpossibleMeasurement(
            "%s: negative band POWER (min %.6g / %.6g). |A|^2 cannot be "
            "negative." % (tag, pa.min(), pb.min()))
    denom = np.sqrt(np.maximum(pa * pb, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        gamma = np.where(denom > 0, c / np.maximum(denom, 1e-300), 0.0)
    bad = np.abs(gamma) > 1.0 + tol
    if np.any(bad):
        i = int(np.argmax(np.abs(gamma)))
        raise ImpossibleMeasurement(
            "%s: |gamma| = %.6f > 1 in band %d (C=%.6g, sqrt(PA*PB)=%.6g). "
            "Coherent power cannot exceed the geometric mean of the two powers "
            "it was formed from." % (tag, abs(gamma[i]), i, c[i], denom[i]))
    return gamma


def band_partition_ok(pa, pb, c, tag="", tol=1e-6):
    """Symmetrised incoherent power must be non-negative.

    CAREFUL -- and this is a correction to h2.py's own docstring, found by this
    guard firing on valid published data.  h2.py calls `N_A = P_A - C` "the
    INCOHERENT power of half A", which implies N_A >= 0.  It is not an
    invariant.  Cauchy-Schwarz bounds C by sqrt(P_A P_B), NOT by P_A, so when
    half B carries more power than half A, C may legitimately exceed P_A.
    Measured counterexample from this lane's own published renders:

        113-g0 detail (352,3680) band 0:  P_A = 0.170000, C = 0.170789

    |gamma| there is still <= 1, so nothing is wrong with the measurement.
    What IS an invariant is the symmetric form, because AM-GM gives
    sqrt(P_A P_B) <= (P_A + P_B) / 2:

        N = (P_A + P_B) / 2 - C >= 0

    That is what this checks.  The asymmetric version is not checked because it
    is not true.
    """
    pa = np.asarray(pa, float)
    pb = np.asarray(pb, float)
    c = np.asarray(c, float)
    mean_p = 0.5 * (pa + pb)
    n = mean_p - c
    scale = np.maximum(np.abs(mean_p), 1e-300)
    bad = n < -tol * scale
    if np.any(bad):
        i = int(np.argmin(n / scale))
        raise ImpossibleMeasurement(
            "%s: symmetrised incoherent power (P_A+P_B)/2 - C is negative in "
            "band %d (P_A=%.6g, P_B=%.6g, C=%.6g, N=%.6g). Coherent power "
            "cannot exceed the arithmetic mean of the two powers."
            % (tag, i, pa[i], pb[i], c[i], n[i]))
    return n
