"""M68 step 00 - the algebra of the dark-sigma observable, derived and then
checked against a simulated signal chain. NO CORPUS DATA IS READ BY THIS SCRIPT.

Rule 40 prior work read before writing this: M61 (in full), M48c, M48, M4,
M25 fact 200, crates/strehl-core/src/profile.rs. See the report for the list.

--------------------------------------------------------------------------
WHY THIS SCRIPT EXISTS
--------------------------------------------------------------------------
M61 question 10 names an observable - the ISO dependence of the dark-sigma
ratio between B and green - and forecasts its behaviour:

    "A **sensor** conversion gain predicts the ratio pinned at 0.84 and
     **flat in ISO**; an **analog attenuation** predicts it above 0.84 and
     **falling toward 0.84 as ISO rises**."

M68's brief instructs me to verify that reasoning from first principles
before relying on it. This script writes the algebra down and then plants
each mechanism in a simulated chain to check that the algebra is right.

--------------------------------------------------------------------------
THE CHAIN
--------------------------------------------------------------------------
One pixel, one read, in order. Noise is injected at three places and they
are in three different units, which is the whole point:

  electrons          voltage at the             DN
  in the well        source follower

  S + D              --[ q/C ]-->   V           --[ A(ISO) ]-->  --[ c ]-->  DN
     + n_e                             + n_V                        + n_D

    n_e : electron-domain noise. Photon shot noise, dark-current shot
          noise. Unit: electrons.
    n_V : voltage-domain noise generated at or after the sense node and
          before the programmable gain. Pixel source-follower thermal and
          1/f noise, the dominant read-noise term in a modern CMOS at gain.
          Unit: volts.
    n_D : DN-domain noise generated after the programmable gain. Column
          ADC noise plus quantisation (1/12 DN^2, which is downstream of
          every analog stage by construction). Unit: DN.

  A(ISO) is the programmable analog gain, proportional to ISO within a
  gain mode. c is the ADC's V->DN scale. The overall conversion gain that
  a PTC measures is

        g = (q/C) * A * c      DN per electron.

  So the DN variance of a dark frame (S = 0, D tiny) is

        sigma^2(ISO) = g^2 * var(n_e)  +  (A c)^2 var(n_V)  +  var(n_D)
                     = alpha * G^2     +  delta                          (1)

  with G = A/k = max(ISO, base_iso) - both of the first two terms are
  proportional to A^2 and therefore to ISO^2, and the third is not. That
  is a two-parameter model per plane: a slope alpha and a floor delta.
  Equation (1) is why M4's sigma_DN/ISO falls slightly with ISO inside a
  gain mode instead of being exactly flat: sigma/G = sqrt(alpha + delta/G^2).

--------------------------------------------------------------------------
WHERE THE 0.84 CAN SIT, AND WHAT EACH POSITION DOES TO (alpha, delta)
--------------------------------------------------------------------------
A multiplicative per-plane scale s = 0.84 scales every noise term
GENERATED UPSTREAM OF IT and no term generated downstream. That single
sentence is the entire discriminator. Four positions:

  P1  charge domain  - the sense-node capacitance C differs per plane, so
      (q/C) differs. This is what "sensor conversion gain" means in the
      narrow, physical sense.
        scales: n_e            (electron domain, upstream of q/C)
        leaves: n_V, n_D
        => alpha_B/alpha_G = (s^2 var(n_e) + var(n_V)) / (var(n_e) + var(n_V))
           delta_B/delta_G = 1
      In a DARK frame at 1/100 s, var(n_e) is dark-current shot noise and
      is negligible against source-follower noise, so
        => alpha ratio -> 1.00, delta ratio -> 1.00.   NO EFFECT IN DARKS.

  P2  analog, after the source follower, before the ADC - a per-channel
      analog attenuator or a per-channel programmable gain.
        scales: n_e, n_V
        leaves: n_D
        => alpha_B/alpha_G = s^2,  delta_B/delta_G = 1.

  P3  analog, immediately before the ADC, with a negligible n_D. This is
      the limiting case of P2 as var(n_D) -> 0. It is NOT a separate
      mechanism, it is P2 with no lever arm.
        => alpha ratio = s^2, delta ratio = 1, but delta itself ~ 0 so
           the ratio sigma_B/sigma_G is flat at s at every ISO.

  P4  post-ADC digital scale.
        scales: everything already quantised, THEN re-quantises
        => alpha_B/alpha_G = s^2
           delta_B/delta_G : NOT ANALYTIC. Measured from the plant below
                             at ~2.8, i.e. a large POSITIVE excess.
      REFUTED by M61 facts 53/54/55 (no code-occupancy comb, B reaches
      16383, linkage excluded on two arms).

      I GOT THIS ROW WRONG TWICE AND THE SIMULATION CAUGHT BOTH. Version
      one said delta_B/delta_G = s^2, forgetting that a digital scale adds
      a fresh quantisation downstream of itself. Version two said
      s^2 + (1/12)/delta_G ~ 1.04, treating that fresh quantisation as
      additive uniform noise. It is not. The input to a post-ADC scale is
      already an INTEGER, and rint(s*n) for integer n is a deterministic
      sawtooth in n, not an independent dither. Over a distribution only a
      few DN wide the map is locally slope 1 with occasional skips, so the
      variance ratio is near 1 at low ISO and only approaches s^2 once the
      distribution is many codes wide. That is M61 fact 53's comb, seen in
      the variance domain instead of the occupancy domain. Consequence:
      P4 predicts a LARGE delta excess and a strongly non-flat sigma
      ratio, so the delta ratio is a real fourth vote against it after all
      - but a lattice-dependent one, and M61's comb and ceiling tests stay
      the primary evidence.

--------------------------------------------------------------------------
WHERE I DISAGREE WITH M61
--------------------------------------------------------------------------
M61 says a sensor conversion gain "refers the read noise generated in the
pixel through the same lower gain" so "B's dark sigma scales by exactly
0.84". That is true only if the read noise is generated UPSTREAM of the
charge-to-voltage conversion, i.e. in the electron domain. The dominant
read-noise term in a modern CMOS sensor is source-follower noise, which is
a VOLTAGE noise at the sense node and is therefore DOWNSTREAM of q/C. A
sense-node capacitance difference does not touch it.

Read noise quoted in electrons is sigma_DN/g. If C_B > C_G so that
g_B = 0.84 g_G, the same source-follower volts correspond to MORE
electrons on B, so RN_e(B) = RN_e(G)/0.84 and sigma_DN is UNCHANGED.
Concretely: P1 predicts a dark-sigma ratio of 1.00, not 0.84.

So M61's forecast is half right. The falling-with-ISO signature it derives
for an analog attenuation is correct algebra (P2 above), and I agree with
it. The flat-at-0.84 signature it attributes to a sensor conversion gain
is NOT what a charge-domain conversion gain does; flat-at-0.84 is P3/P4,
which are the analog-attenuator limit and the refuted digital scale.

Consequence for what the observable can decide: this observable measures
WHERE THE SCALE SITS RELATIVE TO THE DARK-NOISE SOURCES. It does not
measure whether the mechanism deserves the word "sensor".

--------------------------------------------------------------------------
A FIFTH CANDIDATE M61 DID NOT ENUMERATE
--------------------------------------------------------------------------
M61 fact 50 offers three hypotheses (sensor-or-analog / in-camera digital
/ decoder) and fact 51 correctly kills QE. All five of those are SCALES:
something multiplies the blue signal. The hypothesis space is not closed,
because the measured object is a var/mean deficit and there is a family of
mechanisms that suppress variance WITHOUT scaling the mean at all.

  P5  mean-preserving charge sharing. Lateral charge diffusion and optical
      crosstalk redistribute a photo-electron over several pixels. If a
      photon absorbed in a pixel deposits weight (1-b) there and b/4 into
      each of four neighbours, and the neighbours see the same flux, then

          mean_i = lambda(1-b) + 4 lambda (b/4) = lambda        (conserved)
          var_i  = lambda(1-b)^2 + 4 lambda (b/4)^2
          var/mean = (1-b)^2 + b^2/4                            (2)

      so var/mean < 1 with the mean untouched. Solving (2) = 0.84 gives
      b = 0.0844: about 8% of blue charge landing on neighbours reproduces
      M61's number exactly. This is wavelength dependent - in a BSI sensor
      blue is absorbed within a few tenths of a micron of the back surface,
      farthest from the collection well, so it diffuses most.

      P5 is NOT a QE difference. QE changes mean and variance together and
      leaves var/mean alone (M61 fact 51, and I agree). P5 changes variance
      and leaves the mean alone. It passes every test M61 ran: it is
      pre-quantisation, it leaves no comb, and it lets B reach 16383
      because it does not touch the mean.

      In darks there are no photons, so P5 predicts NO EFFECT: alpha ratio
      1.00, delta ratio 1.00 - identical to P1.

  => My observable CANNOT separate P1 from P5. Both predict a null. What
     separates them is stated in the report; it is not a dark-frame
     measurement.

--------------------------------------------------------------------------
PREDICTION TABLE - this is what the measurement is against
--------------------------------------------------------------------------
  hypothesis                    alpha_B/alpha_G   delta_B/delta_G   sigma ratio vs ISO
  P1 charge-domain gain               1.00              1.00        flat at 1.00
  P2 analog, ADC noise downstream     s^2 = 0.705       1.00        falls 1.00 -> 0.84
  P3 analog, no downstream noise      s^2 = 0.705       1.00 (~0)   flat at 0.84
  P4 digital post-ADC (refuted)       s^2 = 0.705       ~2.8 (plant) 0.99 -> 0.85
  P5 charge sharing                   1.00              1.00        flat at 1.00

P2 and P3 are the same mechanism at two values of delta, so the honest
report of a P2 outcome is a fitted UPSTREAM FRACTION rather than a verdict.

WHAT THE OBSERVABLE CAN AND CANNOT SEPARATE, stated before it is run:
  CAN  {P1, P5} from {P2, P3, P4}. This is the headline discrimination and
       it lives entirely in the ALPHA ratio, which is 1.00 on one side and
       s^2 = 0.705 on the other. There is no overlap, and no choice of
       delta moves either side.
  CAN  P2 from P3, as a fitted downstream-variance fraction, provided
       delta_G is resolved above zero.
  CAN  P4 from P2, weakly, on the delta ratio (~2.8 against ~1.0). This is
       a lattice effect and it is a corroboration of M61's comb test, not
       an independent kill.
  CANNOT  P1 from P5. Both predict an exact null in darkness. Nothing
       measured on a dark frame can tell a charge-domain conversion gain
       from mean-preserving charge sharing. Naming what separates THEM is
       part of M68's deliverable and it is not a dark-frame measurement.

--------------------------------------------------------------------------
WHAT THIS SCRIPT CHECKS
--------------------------------------------------------------------------
Rule 20: an argument that cannot fail is not evidence. So the table above
is planted in a simulated chain - actual random numbers pushed through
actual q/C, gain, attenuator and ADC stages in the stated order - and the
recovered (alpha, delta) ratios are compared against the table. If the
simulation disagrees with my algebra, the algebra is wrong and I say so.
"""

from __future__ import annotations

import numpy as np

RNG = np.random.default_rng(20260823)

# Sensor-ish constants, pinned to this body so the simulation sits in the
# same regime as the measurement. Two-point solve of eq (1) on M4 section 8.1's
# published green rows (ISO 400 and ISO 2000) gives alpha_G ~ 7.9e-6 and
# delta_G ~ 0.25 DN^2, i.e. an input-referred upstream noise of 1.23 e- and a
# post-gain floor of ~0.50 DN. The FIRST version of this script used arbitrary
# constants that put the electron-domain term 136x above the source-follower
# term and the whole green sigma at half its real value, and both P1 and P4
# then came out wrong. Rule 13: the plant has to be able to express the answer.
QC_GREEN = 1.0  # arbitrary volts per electron
ADC_C = 1.0  # DN per volt after the programmable gain
SIGMA_E = 0.10  # electron-domain dark noise (dark-current shot at 1/100 s), e-
SIGMA_V = 1.2254  # source-follower voltage noise, in the same "volts" as q/C*e-
SIGMA_D = 0.4082  # post-gain DN-domain ADC noise, DN (quantisation is separate)
S = 0.84  # the measured per-plane scale
ISOS = np.array([400.0, 500.0, 640.0, 800.0, 1000.0, 1600.0, 2000.0])
K_GAIN = 1.0 / 436.8  # A = ISO / gain_divisor, matching profile.rs
NPIX = 2_000_000


def simulate(iso: float, where: str, s: float = S, n: int = NPIX) -> np.ndarray:
    """Push n independent dark reads through the chain and return DN.

    `where` places the per-plane scale s:
        'none'    - no scale (the green plane)
        'charge'  - P1, on q/C
        'analog'  - P2/P3, between the source follower and the ADC
        'digital' - P4, after quantisation
    """
    a = K_GAIN * iso
    qc = QC_GREEN * (s if where == "charge" else 1.0)

    n_e = RNG.normal(0.0, SIGMA_E, n)  # electrons
    volts = n_e * qc  # charge -> voltage
    volts = volts + RNG.normal(0.0, SIGMA_V, n)  # source follower
    volts = volts * a  # programmable gain
    if where == "analog":
        volts = volts * s  # attenuator ahead of the ADC
    dn = volts * ADC_C + RNG.normal(0.0, SIGMA_D, n)  # ADC noise
    dn = np.rint(dn)  # quantisation, the last analog->digital step
    if where == "digital":
        dn = np.rint(dn * s)  # post-ADC per-channel scale
    return dn


def fit_alpha_delta(isos: np.ndarray, var: np.ndarray) -> tuple[float, float]:
    """sigma^2 = alpha * G^2 + delta, ordinary least squares in G^2."""
    g2 = isos**2
    design = np.column_stack([g2, np.ones_like(g2)])
    alpha, delta = np.linalg.lstsq(design, var, rcond=None)[0]
    return float(alpha), float(delta)


def main() -> None:
    print("M68 step 00 - derivation checked against a simulated chain")
    print(f"planted s = {S}, s^2 = {S * S:.4f}")
    print()

    # Sanity: equation (2), the charge-sharing root.
    b = 0.0844
    print(f"eq (2) check: b={b} -> var/mean = {(1 - b) ** 2 + b * b / 4:.4f} (target 0.84)")
    print()

    green = np.array([simulate(i, "none").var(ddof=1) for i in ISOS])
    a_g, d_g = fit_alpha_delta(ISOS, green)
    print(f"green plant: sigma@400 = {np.sqrt(green[0]):.4f} DN, "
          f"sigma@2000 = {np.sqrt(green[-1]):.4f} DN "
          f"(M4 measures 1.2266/1.2403 and 5.6165/5.6883)")
    print(f"green fit:   alpha = {a_g:.4e}, delta = {d_g:.4f} DN^2")
    print()

    rows = [("green (no scale)", a_g, d_g, 1.0, 1.0, 1.0, 1.0)]
    for where, label in [
        ("charge", "P1 charge-domain"),
        ("analog", "P2/P3 analog pre-ADC"),
        ("digital", "P4 digital post-ADC"),
    ]:
        var = np.array([simulate(i, where).var(ddof=1) for i in ISOS])
        alpha, delta = fit_alpha_delta(ISOS, var)
        rows.append((label, alpha, delta, alpha / a_g, delta / d_g,
                     float(np.sqrt(var[0] / green[0])),
                     float(np.sqrt(var[-1] / green[-1]))))

    hdr = (f"{'hypothesis':24s} {'alpha':>11s} {'delta':>9s} {'a_B/a_G':>8s} "
           f"{'d_B/d_G':>8s} {'r@400':>7s} {'r@2000':>7s}")
    print(hdr)
    print("-" * len(hdr))
    for label, alpha, delta, ar, dr, r_lo, r_hi in rows:
        print(f"{label:24s} {alpha:11.4e} {delta:9.4f} {ar:8.4f} {dr:8.4f} {r_lo:7.4f} {r_hi:7.4f}")

    print()
    print("expected from the derivation:")
    print(f"  P1  alpha ratio {(S * S * SIGMA_E**2 + SIGMA_V**2) / (SIGMA_E**2 + SIGMA_V**2):.4f}"
          f"  (~1.00: dark electron-domain noise is {SIGMA_E**2 / (SIGMA_E**2 + SIGMA_V**2):.2%}"
          f" of the upstream variance), delta ratio 1.00")
    print(f"  P2  alpha ratio {S * S:.4f}, delta ratio 1.00, sigma ratio falls toward {S:.2f}")
    print(f"  P4  alpha ratio {S * S:.4f}, delta ratio NOT ANALYTIC (lattice); "
          f"sigma ratio near 1 at low ISO, toward {S:.2f} at high ISO")


if __name__ == "__main__":
    main()
