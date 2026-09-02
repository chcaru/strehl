"""M129 registered predictions: where the diffraction cutoff falls at each aperture,
and which apertures can actually see it.

Nothing here touches data. Every number is derived from three measured inputs that
share no common route, each cited to its source:

  m     = 2.7198       magnification. MEASURED by M84b from graduation spacing on a
                       1 mm rule, with no lens model and no EXIF trust.
                       SYNTHESIS fact 1151.
  B     in [2.41, 3.06] bellows factor N_eff/N. MEASURED by M5 from the green-quincunx
                       power spectrum and the marked f-number, taking NEITHER m NOR p
                       as input. SYNTHESIS fact 1152 records that this makes the
                       transfer non-circular.
  pitch = 5.12 um      sensor pixel pitch, Sony ILCE-7CM2, 33 MP full frame.

The hypotheses under test are the endpoints of the corpus's surviving bracket:

  H1  f_c = 87.00 cy/mm at f/5.6   p = 1, SYNTHESIS fact 1149.
      ALREADY REFUTED by fact 1153 (p = 1 demands B = 3.72, exceeding M5's measured
      upper bound 3.064). Carried here only so the ladder can re-refute it, because a
      hypothesis the corpus killed by one route is still a useful falsifier target.
  H2  f_c = 105.54 cy/mm at f/5.6  fact 1152 low  (p = 1.31)
  H3  f_c = 135.17 cy/mm at f/5.6  fact 1152 high (p = 1.94)

H2 vs H3 is the live question. SYNTHESIS fact 1184: the inversion machine is built and
round-trips exactly -- "MACHINE BUILT, NO FUEL". This milestone is the fuel.

WHY THIS LANE EXISTS AND M5 COULD NOT CLOSE IT
M5 section 5 records C3 (monotonicity of f_c in N) as NOT TESTABLE, because at f/8 and
f/5.6 the subject spectrum never reached the noise floor inside the measurable band, so
those knees were texture-limited rather than optics-limited. M5's own limitations list
says in as many words: "C3 (monotonicity) is not tested. This needs a different
subject." M5 had f/5.6, f/8 and f/11 only. The 7-aperture-pairs fabric capture adds f/14
and f/18 on a broadband subject, and this script's whole purpose is to show that the
extra two stops are what move the cutoff inside the band.
"""

import json
import os

# ---------------------------------------------------------------- measured inputs
PITCH_UM = 5.12          # Sony ILCE-7CM2, 35.9 mm / 7008 px
M_MAG = 2.7198           # M84b, SYNTHESIS fact 1151
LAMBDA_UM = 0.550        # assumed; sensitivity reported below, M5 section 10
N_REF = 5.6              # the aperture the hypotheses are quoted at

HYPOTHESES = [
    ("H1 fact 1149 (refuted)", 87.00),
    ("H2 fact 1152 low", 105.54),
    ("H3 fact 1152 high", 135.17),
]

# The five marked f-numbers in D:\personal\macro\requests\7-aperture-pairs, from EXIF.
APERTURES = [5.6, 8.0, 11.0, 14.0, 18.0]


# ---------------------------------------------------------------- lattice reach
# A cutoff can only be measured if it lies below the sampling reach of the lattice the
# spectrum is computed on. Three lattices are available from one Bayer frame.
#
#   G1 / G2  raw[0::2,1::2] and raw[1::2,0::2].  Pitch 2*5.12 um. Square lattice.
#   GQ       both greens on their quincunx lattice, re-indexed B[u,v] = A[u+v, u-v+1].
#            Pitch 5.12*sqrt(2) um. M5 section 2.2 built this and calls it load-bearing:
#            it interpolates nothing, uses exactly the same photosites, and reaches
#            sqrt(2) times further than a single green plane.
def nyquist_cymm(pitch_um):
    """Nyquist frequency of a lattice of the given pitch, in cycles per mm."""
    return 1000.0 / (2.0 * pitch_um)


LATTICES = [
    ("G1 or G2", 2.0 * PITCH_UM),
    ("GQ quincunx", PITCH_UM * 2.0 ** 0.5),
    ("full sensor", PITCH_UM),
]


# ---------------------------------------------------------------- the optical model
def b_from_fc(fc_cymm, n_marked, lam_um=LAMBDA_UM):
    """Bellows factor B = N_eff/N implied by a cutoff at a marked f-number.

    Incoherent diffraction cutoff: f_c = 1/(lambda * N_eff), so N_eff = 1/(lambda*f_c).
    """
    n_eff = 1.0 / ((lam_um / 1000.0) * fc_cymm)
    return n_eff / n_marked, n_eff


def fc_at(fc_ref, n_marked, n_ref=N_REF):
    """The cutoff scales as 1/N at fixed B, so f_c(N) = f_c(N_ref) * N_ref / N.

    This 1/N scaling IS the ladder's hypothesis. It is what makes the measurement
    over-determined: five apertures give five estimates of one constant B.
    """
    return fc_ref * n_ref / n_marked


def pupil(b, m=M_MAG):
    """p = m/(B-1). Fact 1152's inversion."""
    return m / (b - 1.0)


def main():
    out = {"inputs": {"pitch_um": PITCH_UM, "m": M_MAG, "lambda_um": LAMBDA_UM,
                      "n_ref": N_REF},
           "hypotheses": {}, "ladder": {}, "reach": {}, "separation": {}}

    print(f"sensor pitch {PITCH_UM} um, magnification m = {M_MAG} (M84b), "
          f"lambda = {LAMBDA_UM * 1000:.0f} nm\n")

    print("Lattice reach -- the ceiling on what any spectral method can see:")
    print(f"  {'lattice':>14} {'pitch um':>10} {'Nyquist cy/mm':>15}")
    for name, pit in LATTICES:
        nyq = nyquist_cymm(pit)
        out["reach"][name] = {"pitch_um": pit, "nyquist_cymm": nyq}
        print(f"  {name:>14} {pit:10.4f} {nyq:15.3f}")
    gq_reach = nyquist_cymm(PITCH_UM * 2.0 ** 0.5)
    g1_reach = nyquist_cymm(2.0 * PITCH_UM)

    print("\nHypotheses, inverted to B and p:")
    print(f"  {'hypothesis':>24} {'f_c@f/5.6':>10} {'N_eff':>8} {'B':>8} {'p':>8}")
    for name, fc in HYPOTHESES:
        b, n_eff = b_from_fc(fc, N_REF)
        p = pupil(b)
        out["hypotheses"][name] = {"fc_ref_cymm": fc, "n_eff": n_eff, "B": b, "p": p}
        print(f"  {name:>24} {fc:10.2f} {n_eff:8.3f} {b:8.4f} {p:8.4f}")

    print("\nThe ladder: predicted f_c in cy/mm at each marked aperture.")
    print("  IN  = below the GQ quincunx reach, so measurable on this sensor.")
    print("  out = above it, so the spectrum is texture-limited and the knee is not "
          "the optics.")
    hdr = f"  {'N':>5}"
    for name, _ in HYPOTHESES:
        hdr += f" {name.split()[0]:>16}"
    print(hdr)
    for n in APERTURES:
        row = f"  {n:5.1f}"
        rec = {}
        for name, fc_ref in HYPOTHESES:
            fc = fc_at(fc_ref, n)
            tag = "IN " if fc < gq_reach else "out"
            rec[name.split()[0]] = {"fc_cymm": fc, "in_band_gq": fc < gq_reach,
                                    "in_band_g1": fc < g1_reach}
            row += f" {fc:11.2f} {tag:>4}"
        out["ladder"][f"f/{n}"] = rec
        print(row)

    print(f"\n  GQ reach {gq_reach:.2f} cy/mm, single green plane reach "
          f"{g1_reach:.2f} cy/mm.")

    print("\nDiscrimination: the H2-H3 gap at each aperture, and its margin under GQ.")
    print(f"  {'N':>5} {'H2 cy/mm':>10} {'H3 cy/mm':>10} {'gap':>8} {'gap %':>8} "
          f"{'H3 vs GQ':>10}")
    for n in APERTURES:
        f2 = fc_at(HYPOTHESES[1][1], n)
        f3 = fc_at(HYPOTHESES[2][1], n)
        gap = f3 - f2
        pct = 100.0 * gap / f2
        margin = gq_reach - f3
        out["separation"][f"f/{n}"] = {"h2": f2, "h3": f3, "gap_cymm": gap,
                                       "gap_pct": pct, "h3_margin_under_gq": margin}
        print(f"  {n:5.1f} {f2:10.2f} {f3:10.2f} {gap:8.2f} {pct:8.2f} {margin:10.2f}")

    print("\nWavelength sensitivity (M5 section 10 carries this as a stated systematic).")
    print(f"  {'lambda nm':>10} {'B at H2':>10} {'B at H3':>10}")
    for lam in (0.500, 0.550, 0.600):
        b2, _ = b_from_fc(HYPOTHESES[1][1], N_REF, lam)
        b3, _ = b_from_fc(HYPOTHESES[2][1], N_REF, lam)
        out.setdefault("lambda_sensitivity", {})[f"{lam * 1000:.0f}nm"] = {
            "B_h2": b2, "B_h3": b3}
        print(f"  {lam * 1000:10.0f} {b2:10.4f} {b3:10.4f}")

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest = os.path.join(here, "out", "predict.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
