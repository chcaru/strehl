"""Reference metrics.  These exist ONLY to give the battery power (rule 39)
and to prove it is passable at all.  None is a recommendation.

  REF_SIGPOW     M46's canonical Re(sum A conj B)/count.  Known-bad: must die
                 on B1 and B2 or the battery has no power.
  REF_CONST      returns a constant.  Known-bad: must die on B4.  It is
                 deliberately included because it PASSES B1 -- a constant is
                 trivially monotone -- which proves B1 alone is insufficient.
  REF_NOISEPOW   ring power of the mean image.  Known-bad.
  REF_BANDRATIO  a two-frequency cross-power ratio.  Included ONLY as a
                 passability probe.  NOT a candidate and NOT a design
                 proposal; see the report's note on the do-not-design rule.
"""
import numpy as np
from spec_v1 import (Candidate, ring_at, spec2, F_SIG, NBIN)


class RefSigpow(Candidate):
    name, version = "sigpow-canonical", "M46-AppendixA"
    consumes_calibration = ()
    uses_ground_truth = False
    declared_range = (0.0, float("inf"))       # A.4.2 reads the sign as if positive
    no_claim_floor = 0.0005                    # A.4.2
    decision_threshold = 0.003                 # A.4.2
    failure_direction = "positive"             # d > 0 means the test lost signal
    nuisances = {"split": ["parity", "contiguous", "block-4"],
                 "nbin": [32, 64, 128], "ring_offset": [-1, 0, 1]}
    property_tests = "NONE -- b6_spec.py has golden vectors only (fact 711)"
    nbin = NBIN
    ring_offset = 0

    def value(self, a, b, ctx=None):
        n = a.shape[0]
        from spec_v1 import rings
        rs = rings(n, self.nbin)
        j = int(np.argmin([abs(c - F_SIG) for (_, _, c) in rs]))
        j = min(max(j + self.ring_offset, 0), len(rs) - 1)
        m, cnt, _ = rs[j]
        A, B = spec2(a), spec2(b)
        pa, pb = float(np.sum(np.abs(A[m]) ** 2)), float(np.sum(np.abs(B[m]) ** 2))
        if pa <= 0 or pb <= 0:
            return 0.0, "ZeroPower"
        return float(np.real(np.sum(A[m] * np.conj(B[m]))) / cnt), "Ok"


class RefConst(Candidate):
    name, version = "constant", "1"
    consumes_calibration = ()
    uses_ground_truth = False
    declared_range = (0.0, 2.0)
    no_claim_floor, decision_threshold = 0.0005, 0.003
    failure_direction = "positive"
    nuisances = {}
    property_tests = "n/a"

    def value(self, a, b, ctx=None):
        return 1.0, "Ok"


class RefNoisePow(Candidate):
    name, version = "ring-power-of-mean", "1"
    consumes_calibration = ()
    uses_ground_truth = False
    declared_range = (0.0, float("inf"))
    no_claim_floor, decision_threshold = 0.0005, 0.003
    failure_direction = "positive"
    nuisances = {}
    property_tests = "n/a"

    def value(self, a, b, ctx=None):
        m, cnt, _ = ring_at(a.shape[0])
        A = spec2(0.5 * (a + b))
        return float(np.sum(np.abs(A[m]) ** 2) / cnt), "Ok"


class RefBandRatio(Candidate):
    """Cross-power at f_sig divided by cross-power at a low reference band.
    Bilinear over bilinear, so degree 0 in every scaling and swap-symmetric.
    PASSABILITY PROBE ONLY."""
    name, version = "band-ratio-PROBE", "0"
    consumes_calibration = ()
    uses_ground_truth = False
    declared_range = (-10.0, 10.0)
    no_claim_floor, decision_threshold = 0.0005, 0.003
    failure_direction = "positive"
    nuisances = {"nbin": [32, 64, 128], "f_ref": [0.05, 0.08, 0.12]}
    property_tests = "n/a -- probe"
    nbin = NBIN
    f_ref = 0.08

    def _c(self, A, B, f):
        m, cnt, _ = ring_at(A.shape[0], f=f, nbin=self.nbin)
        return float(np.real(np.sum(A[m] * np.conj(B[m]))) / cnt)

    def value(self, a, b, ctx=None):
        A, B = spec2(a), spec2(b)
        den = self._c(A, B, self.f_ref)
        if den <= 0:
            return 0.0, "ZeroReference"
        return self._c(A, B, F_SIG) / den, "Ok"

    def compare(self, ref, test):
        return (ref - test) / abs(ref) if ref != 0 else float("nan")


ALL = [RefSigpow(), RefConst(), RefNoisePow(), RefBandRatio()]
KNOWN_BAD = {"sigpow-canonical", "constant", "ring-power-of-mean"}


def _summary():
    """Print what each reference is FOR.  These are not candidates."""
    for c in ALL:
        tag = "KNOWN-BAD" if c.name in KNOWN_BAD else "PROBE"
        print("%-22s v%-14s %-10s range=%s thr=%s nuisances=%s"
              % (c.name, c.version, tag, c.declared_range,
                 c.decision_threshold, sorted(c.nuisances)))
    print("\nThree are KNOWN-BAD by construction and exist only to give the battery")
    print("power (rule 39): a battery that nothing fails has not been shown to work.")
    print("The fourth is a passability probe, NOT a design proposal.")
    print("Scoring lives in calibrate.py; this module declares only.")


if __name__ == "__main__":
    _summary()
