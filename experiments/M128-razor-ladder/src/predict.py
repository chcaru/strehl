"""M128 / predict — the registered predictions, recomputed from their sources.

Every number in PREREGISTRATION.md section 2 comes from this script. Run it and
diff the output against the document; a mismatch is a defect in the document.

Sources, all quoted rather than re-derived here:
  a = 1009.41 um*cy/mm, b = 7.19 um   M88 dense calibration, rise(f_c) =
                                      sqrt((a/f_c)^2 + b^2), max residual 0.99 um
  m = 2.7198 +/- 0.0051               M84b, MEASURED
  lambda = 550 nm                     M5 s10 wavelength assumption; M5 records
                                      that 500 nm moves B by about +0.3
  N in {5.6, 8, 11}                   marked f-number, EXIF FNumber, which M5
                                      established is NOT bellows-corrected
Chain: f_c -> N_eff = 1/(lambda*f_c) -> B = N_eff/N -> p = m/(B-1).
"""

import numpy as np

A_UM_CYMM = 1009.41
B_FLOOR_UM = 7.19
M_MAG = 2.7198
M_MAG_SD = 0.0051
LAMBDA_MM = 550e-6
PITCH_UM = 5.12

HYPOTHESES = [
    ("H1  fact 1149", 87.0),
    ("H2  fact 1152 lo", 105.54),
    ("H3  fact 1152 hi", 135.17),
]
APERTURES = [5.6, 8.0, 11.0]
N_REF = 5.6


def rise_um(fc_cymm, c_um=0.0):
    return float(np.sqrt((A_UM_CYMM / fc_cymm) ** 2 + B_FLOOR_UM ** 2 + c_um ** 2))


def invert(fc_cymm, n_marked, m=M_MAG):
    n_eff = 1.0 / (LAMBDA_MM * fc_cymm)
    b = n_eff / n_marked
    p = m / (b - 1.0)
    return n_eff, b, p


def main():
    print("M128 registered predictions")
    print(f"a = {A_UM_CYMM} um*cy/mm, b = {B_FLOOR_UM} um, m = {M_MAG} "
          f"+/- {M_MAG_SD}, lambda = {LAMBDA_MM * 1e6:.0f} nm")
    print(f"sensor pitch {PITCH_UM} um, green sublattice pitch "
          f"{2 * PITCH_UM} um, sensor Nyquist "
          f"{1000.0 / (2 * PITCH_UM):.5f} cy/mm\n")

    print("2.1  round trip: each hypothesis' f_c at f/5.6 back to p")
    print(f"{'hypothesis':>18} {'f_c cy/mm':>10} {'N_eff':>8} {'B':>8} {'p':>8}")
    for name, fc in HYPOTHESES:
        n_eff, b, p = invert(fc, N_REF)
        print(f"{name:>18} {fc:10.2f} {n_eff:8.3f} {b:8.4f} {p:8.4f}")

    print("\n2.2  predicted 10-90% rise, um, negligible subject term (c = 0)")
    hdr = "".join(f"{f'f/{n:g}':>12}" for n in APERTURES)
    print(f"{'hypothesis':>18}{hdr}")
    table = {}
    for name, fc in HYPOTHESES:
        row = []
        for n in APERTURES:
            fcn = fc * N_REF / n
            row.append(rise_um(fcn))
        table[name] = row
        print(f"{name:>18}" + "".join(f"{v:12.3f}" for v in row))

    print("\n2.3  the same rises in green-plane px (10.24 um), which is what the "
          "ESF is binned in")
    for name, _ in HYPOTHESES:
        row = table[name]
        print(f"{name:>18}" + "".join(f"{v / (2 * PITCH_UM):12.4f}" for v in row))

    print("\n2.4  separation: worst-case adjacent-hypothesis gap per aperture")
    for j, n in enumerate(APERTURES):
        vals = [table[k][j] for k, _ in HYPOTHESES]
        gaps = [abs(vals[i] - vals[i + 1]) for i in range(len(vals) - 1)]
        rel = min(gaps) / max(vals) * 100.0
        print(f"  f/{n:g}: rises {['%.3f' % v for v in vals]}  "
              f"min gap {min(gaps):.3f} um = {rel:.2f}% of the largest")

    print("\n2.5  the ladder: rise^2(N) = s^2 N^2 + c^2 under each hypothesis, "
          "and what a shared subject term does to it")
    for c in (0.0, 10.0, 20.0, 30.0):
        print(f"  subject softness c = {c:5.1f} um")
        for name, fc in HYPOTHESES:
            rs = [rise_um(fc * N_REF / n, c) for n in APERTURES]
            # recover s and c by least squares on rise^2 vs N^2
            nn = np.array(APERTURES) ** 2
            rr = np.array(rs) ** 2
            Amat = np.column_stack([nn, np.ones(3)])
            coef, res, *_ = np.linalg.lstsq(Amat, rr, rcond=None)
            s_rec = float(np.sqrt(max(coef[0], 0.0)))
            c_rec = float(np.sqrt(max(coef[1], 0.0)))
            b_rec = s_rec / (A_UM_CYMM * LAMBDA_MM)
            p_rec = M_MAG / (b_rec - 1.0)
            print(f"    {name:>18} rises {['%.3f' % v for v in rs]}  "
                  f"-> s {s_rec:7.4f} c {c_rec:7.3f} B {b_rec:7.4f} "
                  f"p {p_rec:7.4f}")

    print("\n2.6  M5's measured bracket, re-expressed with M84b's measured m")
    for tag, b in (("M5 upper B = 3.064", 3.064), ("M5 lower B = 2.412", 2.412)):
        p = M_MAG / (b - 1.0)
        fc = 1.0 / (LAMBDA_MM * b * N_REF)
        print(f"  {tag:>20}: p = {p:.4f}, implied f_c at f/5.6 = {fc:.2f} cy/mm")
    print("  fact 1149 (p = 1) needs B = "
          f"{1.0 + M_MAG / 1.0:.4f}, which M5's upper bound "
          f"{'excludes' if 1.0 + M_MAG > 3.064 else 'admits'}")

    print("\n2.7  HOW GOOD DOES THE MEASUREMENT HAVE TO BE")
    print("  Monte Carlo on the SECONDARY reduction, the rise ladder. Truth is")
    print("  H2 with a subject term c = 20 um, the pessimistic end of what the")
    print("  bevel could contribute. Each of the three rises is perturbed by")
    print("  independent Gaussian error of SD sigma_r, the ladder is refit, and")
    print("  B is recovered. The three hypotheses sit at B = 3.7319 / 3.0763 /")
    print("  2.4020, so adjacent gaps are about 0.66. 'assigned' is the fraction")
    print("  of trials whose recovered B is nearest the true hypothesis; that is")
    print("  the quantity the lane's verdict actually rests on.")
    rng = np.random.default_rng(20260817)
    ntrial = 20000
    nn = np.array(APERTURES) ** 2
    Amat = np.column_stack([nn, np.ones(3)])
    truth_fc, truth_c = 105.54, 20.0
    b_hyp = np.array([invert(fc, N_REF)[1] for _, fc in HYPOTHESES])
    truth_rise = np.array([rise_um(truth_fc * N_REF / n, truth_c)
                           for n in APERTURES])
    gap = float(np.min(np.abs(np.diff(b_hyp))))
    print(f"\n  truth: f_c(f/5.6) = {truth_fc} cy/mm, c = {truth_c} um, "
          f"rises {['%.3f' % v for v in truth_rise]} um")
    print(f"  hypothesis B values {['%.4f' % v for v in b_hyp]}, "
          f"min adjacent gap {gap:.4f}")
    print(f"  {'sigma_r um':>11} {'rel %':>7} {'B sd':>8} {'gap/sd':>8} "
          f"{'assigned':>9} {'neg s^2':>8}")
    for sigma in (0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 1.00, 2.00):
        obs = truth_rise[None, :] + rng.normal(0.0, sigma, (ntrial, 3))
        coef, *_ = np.linalg.lstsq(Amat, (obs ** 2).T, rcond=None)
        s2 = coef[0]
        neg = float(np.mean(s2 <= 0.0))
        b_rec = np.sqrt(s2[s2 > 0.0]) / (A_UM_CYMM * LAMBDA_MM)
        sd = float(np.std(b_rec))
        nearest = np.argmin(np.abs(b_rec[:, None] - b_hyp[None, :]), axis=1)
        assigned = float(np.mean(nearest == 1))
        rel = sigma / truth_rise.mean() * 100.0
        print(f"  {sigma:11.2f} {rel:7.2f} {sd:8.4f} {gap / max(sd, 1e-9):8.2f} "
              f"{assigned * 100:8.1f}% {neg * 100:7.1f}%")
    print("\n  REGISTERED PRECISION REQUIREMENT (secondary reduction): the")
    print("  per-aperture 10-90% rise must be measured to 1 sigma <= 0.35 um,")
    print("  which is about 1.4% of the rise, for a 4-sigma separation between")
    print("  adjacent hypotheses. Above 0.5 um the ladder degrades quickly")
    print("  because it is a difference of squares of three similar numbers.")

    print("\n2.8  THE PRIMARY REDUCTION IS BETTER CONDITIONED, AND HERE IS WHY")
    print("  m88lib.fit_fc fits A * diffraction(f_c) * pixel * gauss(sigma) to")
    print("  the measured SFR. It separates the cutoff from the subject term by")
    print("  the SHAPE of the MTF rolloff, not by its width alone, so sigma")
    print("  absorbs bevel softness and residual defocus while f_c stays free.")
    print("  That gives one f_c per aperture directly, and the test becomes")
    print("  f_c(N) * N = const, which is a mean of three ratios rather than a")
    print("  difference of squares.")
    print(f"  {'rel err on f_c':>15} {'implied B sd':>13} {'gap/sd':>8}")
    for eps in (0.005, 0.01, 0.02, 0.03, 0.05, 0.10):
        # B = 1/(lambda * N * f_c); relative error passes straight through,
        # and averaging three independent apertures divides by sqrt(3).
        sd = b_hyp[1] * eps / np.sqrt(3.0)
        print(f"  {eps * 100:14.1f}% {sd:13.4f} {gap / sd:8.2f}")
    print("\n  REGISTERED PRECISION REQUIREMENT (primary reduction): f_c must be")
    print("  measured to 5% relative per aperture. That buys 7.4 sigma between")
    print("  adjacent hypotheses, and even a poor 10% still buys 3.7 sigma. The")
    print("  headroom is deliberate: it is there to be spent on the systematic")
    print("  errors listed in section 4, which are the real threat here, not")
    print("  statistical scatter. This is a far weaker demand than the rise")
    print("  ladder's 1.4%, which is why fit_fc is registered as primary and the")
    print("  rise ladder as an independent cross-check on it, not the reverse.")


if __name__ == "__main__":
    main()
