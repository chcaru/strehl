"""M84b step 19 -- cross-check the measured magnification against M5's measured
bellows factor, and propagate the consequence into SYNTHESIS fact 1149.

Sources read at source (rule 40), quoted with line numbers:

  docs/research/M5-diffraction-measured.md:65
      "Combined bracket (DERIVED): B in [2.41, 3.06] at lambda = 550 nm."
  docs/research/M5-diffraction-measured.md:57
      "109MSDCF | f/11 | ... | B <= 3.064 (MEASURED->DERIVED)"
  docs/research/M5-diffraction-measured.md:62
      "f_c <~ 0.3508 => B >~ 2.412 (ARGUED)"
  docs/research/SYNTHESIS.md fact 1147
      MaxApertureValue == FNumber == 5.6 -> f/5.6 is WIDE OPEN with the TC fitted.
  docs/research/SYNTHESIS.md fact 1149
      N_eff = N(1+m) = 21.07 at p = 1, Airy 28.3 um, f_c 86.3 cy/mm,
      sensor Nyquist 97.7 cy/mm, binned Nyquist 48.8 cy/mm.
      Explicitly DERIVED with "p = 1 assumed".

M84b's own MEASURED input is m, from out/15-closure.json. Nothing here re-measures
anything; this step is arithmetic on two measurements from two milestones.

No file outside experiments/M84b-ruler-metrology/ is written.
"""

import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "out"

LAMBDA_UM = 0.55  # M5's stated wavelength, docs/research/M5-diffraction-measured.md:65
PX_UM = 5.12      # F-camera-lens-optics.md:91, DERIVED, +/-0.3%
N_MARKED = 5.6    # MEASURED from EXIF on both M84b stacks; wide open per fact 1147

# M5's bracket, namespaced. Both endpoints quoted at source above.
B_LO = 2.412
B_HI = 3.064

# Fact 1149's published figures, for explicit comparison.
F1149 = dict(m=2.762, N_eff=21.07, airy_um=28.3, f_c=86.3,
             nyq_sensor=97.7, nyq_binned=48.8)


def airy_diameter_um(n_eff, lam=LAMBDA_UM):
    """Diameter of the Airy disc to the first zero."""
    return 2.44 * lam * n_eff


def cutoff_cy_per_mm(n_eff, lam=LAMBDA_UM):
    """Incoherent diffraction MTF cutoff, image-referred."""
    return 1000.0 / (lam * n_eff)


def diffraction_mtf(nu, f_c):
    """Incoherent diffraction MTF of a circular pupil at spatial frequency nu."""
    if nu >= f_c:
        return 0.0
    phi = math.acos(nu / f_c)
    return (2.0 / math.pi) * (phi - math.cos(phi) * math.sin(phi))


def dof_total_um(n_eff, m, c_um):
    """Total depth of field at the subject, thin-lens macro form 2*c*N_eff/m^2."""
    return 2.0 * c_um * n_eff / (m * m)


def main():
    closure = json.loads((OUT / "15-closure.json").read_text(encoding="utf-8"))
    focus = json.loads((OUT / "16-focusaxis.json").read_text(encoding="utf-8"))

    m = closure["solution"]["m"]
    m_sd = closure["bootstrap"]["m"]["sd"]
    px_syst = 0.003  # +/-0.3% on the imported pixel pitch
    m_lo = m * (1 - px_syst) - 2 * m_sd
    m_hi = m * (1 + px_syst) + 2 * m_sd

    res = {"inputs": {}, "pupil": {}, "diffraction": {}, "fact_1149_check": {},
           "dof": {}, "attribution": {}}

    res["inputs"] = dict(
        m_measured=m, m_sd_stat=m_sd, pixel_pitch_syst_frac=px_syst,
        m_interval_95_plus_syst=[m_lo, m_hi],
        B_M5_lo=B_LO, B_M5_hi=B_HI, N_marked=N_MARKED,
        lambda_um=LAMBDA_UM, pixel_pitch_um=PX_UM,
    )

    # ---- pupil magnification: p = m / (B - 1) ------------------------------
    # Larger B  -> smaller p.  Pair the extremes to bracket p honestly.
    p_lo = m_lo / (B_HI - 1.0)
    p_hi = m_hi / (B_LO - 1.0)
    p_mid = m / (0.5 * (B_LO + B_HI) - 1.0)

    # The p = 1 hypothesis demands B = 1 + m.  Is that inside M5's bracket?
    B_required_for_p1 = 1.0 + m
    B_required_lo = 1.0 + m_lo
    p1_excluded = B_required_lo > B_HI

    res["pupil"] = dict(
        p_interval=[p_lo, p_hi], p_midpoint=p_mid,
        B_required_for_p_equals_1=B_required_for_p1,
        B_required_for_p1_lower_edge=B_required_lo,
        M5_upper_bound_on_B=B_HI,
        margin_above_M5_upper_bound=B_required_lo - B_HI,
        p_equals_1_excluded=bool(p1_excluded),
        note=("p = m/(B-1). M5's B is measured from the cutoff frequency and the "
              "marked N and takes no m as input, so B is independent of this "
              "milestone's measurement and the transfer is not circular."),
    )

    # ---- diffraction at the captures' own aperture -------------------------
    # M5 measured B at f/11; B = 1 + m/p is aperture-independent, so it transfers
    # to the f/5.6 at which both M84b stacks were shot.
    rows = []
    for label, B in (("M5 lower (B=2.412)", B_LO),
                     ("M5 upper (B=3.064)", B_HI),
                     ("fact 1149's p=1 (B=1+m)", B_required_for_p1)):
        n_eff = N_MARKED * B
        rows.append(dict(
            case=label, B=B, N_eff=n_eff,
            airy_um=airy_diameter_um(n_eff),
            airy_sensor_px=airy_diameter_um(n_eff) / PX_UM,
            f_c_image_cy_mm=cutoff_cy_per_mm(n_eff),
            f_c_subject_cy_mm=cutoff_cy_per_mm(n_eff) * m,
        ))
    nyq_sensor = 1000.0 / (2.0 * PX_UM)
    nyq_binned = 1000.0 / (2.0 * 2.0 * PX_UM)
    for r in rows:
        r["mtf_at_sensor_nyquist"] = diffraction_mtf(nyq_sensor, r["f_c_image_cy_mm"])
        r["mtf_at_binned_nyquist"] = diffraction_mtf(nyq_binned, r["f_c_image_cy_mm"])
    res["diffraction"] = dict(cases=rows, nyquist_sensor_cy_mm=nyq_sensor,
                              nyquist_binned_cy_mm=nyq_binned)

    # ---- does fact 1149's "MTF at Nyquist is exactly zero" survive? --------
    fc_lo = cutoff_cy_per_mm(N_MARKED * B_HI)   # worst case for the claim
    fc_hi = cutoff_cy_per_mm(N_MARKED * B_LO)
    res["fact_1149_check"] = dict(
        published=F1149,
        m_attributed_to_M84b=F1149["m"],
        m_measured_by_M84b=m,
        m_discrepancy_frac=(F1149["m"] - m) / m,
        m_attributed_inside_M84b_interval=bool(m_lo <= F1149["m"] <= m_hi),
        f_c_interval_using_M5_B=[fc_lo, fc_hi],
        f_c_published_p1=F1149["f_c"],
        nyquist_sensor=nyq_sensor,
        cutoff_below_sensor_nyquist_at_M5_upper=bool(fc_lo < nyq_sensor),
        cutoff_below_sensor_nyquist_at_M5_lower=bool(fc_hi < nyq_sensor),
        verdict=("fact 1149's 'MTF at Nyquist is identically zero' holds only "
                 "under its assumed p = 1, which M84b's measured m combined "
                 "with M5's measured B excludes."),
    )

    # ---- is the focus sweep sampling finer than the depth of field? -------
    dof_rows = []
    for c_label, c_um in (("c = 1 sensor px", PX_UM), ("c = 1 quad px", 2 * PX_UM)):
        for B_label, B in (("M5 lower", B_LO), ("M5 upper", B_HI)):
            dof_rows.append(dict(circle=c_label, c_um=c_um, B_case=B_label,
                                 dof_um=dof_total_um(N_MARKED * B, m, c_um)))
    step_mean = focus["um_per_frame"]
    seg = focus["segment_um_per_frame"]
    res["dof"] = dict(
        cases=dof_rows, step_mean_um=step_mean,
        step_min_um=min(seg), step_max_um=max(seg),
        note=("A focus step larger than the depth of field means the stack is "
              "under-sampled in focus; the comparison depends entirely on the "
              "chosen circle of confusion, which is a convention, not a "
              "measurement."),
    )

    res["attribution"] = dict(
        teleconverter=("SYNTHESIS fact 1147 (MEASURED): the converter is a 2x "
                       "Viltrox, NOT the SEL20TC that F-camera-lens-optics.md:66 "
                       "names. The 2.8x ceiling survives because any true 2x "
                       "gives 1.4x2, and EXIF confirms an electronically "
                       "communicating 2x, but the cited source is false. M84b "
                       "therefore cites the ceiling, not the converter model."),
        aperture=("SYNTHESIS fact 1147 (MEASURED): MaxApertureValue == FNumber "
                  "== 5.6 on this rig, so both M84b stacks were shot WIDE OPEN. "
                  "The dispatch's 'f/5.6 marked' is right; there was no slower "
                  "or faster option available."),
    )

    (OUT / "19-m5-crosscheck.json").write_text(
        json.dumps(res, indent=1), encoding="utf-8")

    # ---- report -----------------------------------------------------------
    print("M84b step 19 -- M5 cross-check and fact 1149 propagation")
    print()
    print(f"  m (M84b, MEASURED)        = {m:.4f} +/- {m_sd:.4f} stat, +/-0.3% syst")
    print(f"  m 95%+syst interval       = [{m_lo:.4f}, {m_hi:.4f}]")
    print(f"  B (M5, namespaced)        = [{B_LO:.3f}, {B_HI:.3f}]")
    print()
    print("  PUPIL MAGNIFICATION")
    print(f"    p = m/(B-1)             = [{p_lo:.3f}, {p_hi:.3f}]  (mid {p_mid:.3f})")
    print(f"    p = 1 would need B      = {B_required_for_p1:.3f}"
          f"  (lower edge {B_required_lo:.3f})")
    print(f"    M5's measured ceiling   = {B_HI:.3f}")
    print(f"    p = 1 EXCLUDED          = {p1_excluded}"
          f"   by {B_required_lo - B_HI:.3f} in B")
    print()
    print("  DIFFRACTION AT THE CAPTURES' OWN f/5.6 (wide open, fact 1147)")
    print(f"    {'case':<26}{'B':>7}{'N_eff':>8}{'Airy um':>9}"
          f"{'Airy px':>9}{'f_c img':>9}{'f_c subj':>10}{'MTF@Nyq':>9}{'MTF@bin':>9}")
    for r in rows:
        print(f"    {r['case']:<26}{r['B']:>7.3f}{r['N_eff']:>8.2f}"
              f"{r['airy_um']:>9.1f}{r['airy_sensor_px']:>9.2f}"
              f"{r['f_c_image_cy_mm']:>9.1f}{r['f_c_subject_cy_mm']:>10.1f}"
              f"{r['mtf_at_sensor_nyquist']:>9.4f}{r['mtf_at_binned_nyquist']:>9.4f}")
    print(f"    sensor Nyquist          = {nyq_sensor:.1f} cy/mm")
    print(f"    binned Nyquist          = {nyq_binned:.1f} cy/mm")
    print()
    print("  FACT 1149 CHECK")
    print(f"    m it attributes to M84b = {F1149['m']:.4f}")
    print(f"    m M84b actually measured= {m:.4f}"
          f"   ({100*(F1149['m']-m)/m:+.2f}%)")
    print(f"    inside M84b's interval  = {m_lo <= F1149['m'] <= m_hi}")
    print(f"    its f_c (p=1 assumed)   = {F1149['f_c']:.1f} cy/mm  < Nyquist"
          f" {nyq_sensor:.1f} -> 'MTF at Nyquist exactly zero'")
    print(f"    f_c using M5's B        = [{fc_lo:.1f}, {fc_hi:.1f}] cy/mm")
    print(f"    still below Nyquist?    = upper-B {fc_lo < nyq_sensor}"
          f", lower-B {fc_hi < nyq_sensor}")
    print()
    print("  FOCUS SAMPLING vs DEPTH OF FIELD")
    for d in dof_rows:
        print(f"    {d['circle']:<18}{d['B_case']:<12}DoF = {d['dof_um']:7.1f} um")
    print(f"    measured step            = {step_mean:.2f} um/frame"
          f"  (drifts {min(seg):.1f} -> {max(seg):.1f})")
    print()
    print(f"  wrote {OUT / '19-m5-crosscheck.json'}")


if __name__ == "__main__":
    main()
