"""Re-derive the shipped pyramid selection arithmetic outside the crate.

Everything here is an INDEPENDENT re-implementation from the quoted source at pin
9b05d0b7, not a call into it, so agreement is evidence and disagreement is a finding.

Source of truth, quoted:

  pyramid.rs:136   pub const DEFAULT_BANDS: usize = 7;
  pyramid.rs:1075  pub const MAX_EXPONENT: f32 = 8.0;
  pyramid.rs:2060  const SNR_REF: f32 = 64.0;
  pyramid.rs:1080-1090  bands: DEFAULT_BANDS, gate: 2.0, exponent: 2.0,
                        sharpen_per_octave: 1.4, select: SelectMode::SoftPower
  pyramid.rs:1050  pub fn exponent_at(&self, k: usize, bands: usize) -> f32 {
                     if self.sharpen_per_octave == 1.0 || bands == 0 { return self.exponent; }
                     let steps = (bands-1) - k.min(bands-1);
                     (self.exponent * self.sharpen_per_octave.powi(steps)).min(MAX_EXPONENT) }
  pyramid.rs:2092  fn select_weight(excess, floor, p) {
                     if excess <= 0.0 { return 0.0; }
                     let r = excess / floor.max(1.0) / SNR_REF;
                     if p == 1.0 { r } else if p == 2.0 { r*r }
                     else { (p * r.ln()).clamp(-80.0, 80.0).exp() } }
  pyramid.rs:1786  out[j] = if den[j] > 0.0 { num[j] / den[j] } else { subgate(j) }
"""
import numpy as np

F = np.float32
BANDS = 7
MAX_EXPONENT = F(8.0)
SNR_REF = F(64.0)
EXPONENT = F(2.0)
SHARPEN = F(1.4)


def exponent_at(k, bands=BANDS, exponent=EXPONENT, sharpen=SHARPEN):
    if sharpen == F(1.0) or bands == 0:
        return exponent
    steps = (bands - 1) - min(k, bands - 1)
    return min(F(exponent * F(sharpen) ** steps), MAX_EXPONENT)


def select_weight(excess, floor, p):
    excess, floor, p = F(excess), F(floor), F(p)
    if excess <= 0.0:
        return F(0.0)
    r = F(F(excess / max(floor, F(1.0))) / SNR_REF)
    if p == F(1.0):
        return r
    if p == F(2.0):
        return F(r * r)
    return F(np.exp(np.clip(F(p * np.log(r)), F(-80.0), F(80.0))))


def ladder():
    print("PER-BAND EXPONENT LADDER, bands=%d (k=0 finest)" % BANDS)
    print("  %-4s %-9s %-8s %s" % ("k", "uncapped", "shipped", "note"))
    out = []
    for k in range(BANDS):
        steps = (BANDS - 1) - min(k, BANDS - 1)
        raw = F(EXPONENT * F(SHARPEN) ** steps)
        p = exponent_at(k)
        out.append(float(p))
        print("  %-4d %-9.3f %-8.3f %s" % (k, raw, p, "CAPPED" if p < raw else ""))
    # The doc comment claims "2, 3, 4, 5, 8, 8, 8 from coarsest to finest".
    claimed = [2.0, 3.0, 4.0, 5.0, 8.0, 8.0, 8.0]
    actual_coarse_first = out[::-1]
    print("\n  doc comment claims (coarsest->finest): %s" % claimed)
    print("  actually computed  (coarsest->finest): %s"
          % [round(v, 3) for v in actual_coarse_first])
    worst = max(abs(a - c) for a, c in zip(actual_coarse_first, claimed))
    print("  max |actual - claimed| = %.3f  -> the comment is ROUNDED, not exact" % worst)
    return out


def snr_ref_cancels():
    """Does SNR_REF cancel in w_i / sum_j w_j? Test, do not assume."""
    print("\nDOES SNR_REF CANCEL IN THE NORMALISED WEIGHT?")
    rng = np.random.default_rng(20260827)
    worst = 0.0
    binds = 0
    trials = 0
    for _ in range(4000):
        nfr = int(rng.integers(2, 40))
        # Realistic spread: band energies over orders of magnitude, floors likewise.
        exc = F(10.0) ** F(rng.uniform(-2, 5, nfr))
        flo = F(10.0) ** F(rng.uniform(-1, 4, nfr))
        p = float(exponent_at(int(rng.integers(0, BANDS))))
        for ref in (SNR_REF, F(1.0), F(1024.0)):
            pass
        def shares(ref):
            ws = []
            for e, f in zip(exc, flo):
                r = F(F(e / max(F(f), F(1.0))) / ref)
                if e <= 0:
                    ws.append(F(0.0)); continue
                if p == 1.0:
                    w = r
                elif p == 2.0:
                    w = F(r * r)
                else:
                    z = F(p * np.log(r))
                    if z > 80.0 or z < -80.0:
                        return None  # the clamp binds; cancellation is not expected
                    w = F(np.exp(np.clip(z, F(-80.0), F(80.0))))
                ws.append(w)
            ws = np.array(ws, dtype=F)
            s = ws.sum(dtype=F)
            return ws / s if s > 0 else None

        a = shares(SNR_REF)
        b = shares(F(1.0))
        c = shares(F(1024.0))
        if a is None or b is None or c is None:
            binds += 1
            continue
        trials += 1
        worst = max(worst, float(np.max(np.abs(a - b))), float(np.max(np.abs(a - c))))
    print("  %d trials where the clamp did not bind; max share difference across"
          % trials)
    print("  SNR_REF in {1, 64, 1024}: %.3e" % worst)
    print("  clamp bound in %d of %d draws (there, cancellation is NOT exact)"
          % (binds, binds + trials))
    verdict = worst < 1e-5
    print("  -> SNR_REF %s an overflow guard, not a threshold"
          % ("IS" if verdict else "IS NOT"))
    return verdict, binds, trials


def selectivity_demo(ps):
    """What does a purely random band-energy fluctuation buy, at each exponent?"""
    print("\nWHAT A RANDOM FLUCTUATION BUYS (weight ratio for an energy ratio)")
    print("  %-6s %-10s %-10s %-10s" % ("p", "x1.3", "x2.0", "x3.0"))
    for k, p in enumerate(ps):
        print("  %-6.2f %-10.1f %-10.1f %-10.1f"
              % (p, 1.3 ** p, 2.0 ** p, 3.0 ** p))


if __name__ == "__main__":
    ps = ladder()
    snr_ref_cancels()
    selectivity_demo(ps)
