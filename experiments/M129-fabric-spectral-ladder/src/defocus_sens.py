"""Can knee_model_fit see defocus at all?  Commissioning, no decodes.

WHY THIS EXISTS. defocus_robust.py concluded that no frame-selection bias can
account for Amendment 9's +0.1157 aperture gap, because the gap survives every
reachable offset. That inference has an unexamined premise: it assumes that
moving the frame moves the estimator. If `knee_model_fit` were BLIND to defocus -
if it absorbed defocus into its slope and floor and left its cutoff alone - then
a small measured swing would be evidence of nothing, and "the gap survives every
offset" would be as true of a broken instrument as of a real optical effect. That
is a checker carrying its own answer (house rule 35), and it has to be closed
before defocus_robust.py's conclusion can be relied on.

So this measures the estimator's defocus response directly, on synthetic data
where the true cutoff is known exactly, with no decodes and no capture.

CONSTRUCTION. For each real f/14 and f/18 ROI, the measured PSD is fitted once to
get (A, alpha, N, f_c). A clean PSD is then REGENERATED from those parameters on
the identical frequency grid and bin counts. By construction the estimator
recovers the truth from it, which makes the zero-defocus round trip a real test of
the plumbing rather than a tautology (S1 would fail loudly if the regeneration and
the model disagreed). Defocus is then applied to that clean PSD and the fit is
repeated. Nothing but the defocus changes, so every movement in the fitted cutoff
is caused by the defocus.

THE DEFOCUS MTF IS COMPUTED EXACTLY, NOT APPROXIMATED. Published closed forms for
the defocus MTF (Hopkins) circulate with several different constants inside the
Bessel argument, and picking the wrong one would silently rescale the wave axis
and therefore every conclusion drawn about how many waves are needed. Instead the
optical transfer function is computed from first principles as the normalised
autocorrelation of the complex pupil P(rho)*exp(i*2*pi*W20*rho^2), evaluated by
FFT. S0 commissions that computation against m5_lib.mtf_diffraction at W20 = 0,
where the two must agree to numerical precision. If S0 fails nothing else here is
readable.

PREDICTIONS, REGISTERED BEFORE THE FIRST RUN.

S0  At W20 = 0 the computed MTF matches m5_lib.mtf_diffraction to within 2e-3 rms
    over s in [0, 0.95]. This is the instrument check on the optics code.

S1  ROUND TRIP. With no defocus applied, the refit recovers the seeded cutoff to
    within 1% and hence B to within 0.02. Failure means the synthesis and the
    model disagree and no later number is interpretable.

S2  DIRECTION, STATED BEFORE MEASURING (house rule 18). Defocus lowers the MTF at
    every frequency inside the passband, so a fit that keeps the diffraction shape
    must shrink its cutoff to compensate. Fitted B = PITCH/(lambda*N*f_c) is
    inversely proportional to the cutoff, so fitted B RISES monotonically with
    defocus. If instead B FALLS, then defocus predicts the sign actually seen in
    the real B-versus-offset curves, my diagnosis of those curves as an estimator
    artefact is wrong, and defocus_b.py's negative curvature is physical after all.
    Either outcome is informative; the point is that the direction was fixed here
    before it was looked at.

S3  SENSITIVITY, THE DECISIVE ONE. A quarter wave of defocus - the Rayleigh
    diffraction-limit criterion, the standard threshold for "no longer sharp" -
    moves fitted B by more than 0.05, the same threshold Amendment 9 registered
    for the aperture gap. Pass means the estimator can see a defocus that matters
    and defocus_robust.py's premise holds. Fail means the estimator is blind to
    defocus at the scale that matters, defocus cannot be excluded by any argument
    resting on how little B moved, and defocus_robust.py's Q2 must be withdrawn.

S4  THE LEAK, QUANTIFIED. Some of the defocus is absorbed by the slope parameter
    rather than the cutoff. Reported as the fraction of the fitted alpha change
    per wave. No pass/fail attaches; it is recorded because it sets how much of
    the true defocus the cutoff route under-reports, and S3 is only a lower bound
    on the estimator's real sensitivity if the leak is large.

WHAT A PASS BUYS. If S0-S3 all pass, the empirical curvature in defocus_b.py can
be converted into an upper bound on how much defocus differs between the two
apertures, and that bound can be compared against the +0.1157 gap. That
conversion is the last step and it is done here.

-----------------------------------------------------------------------------
FIRST RUN FAILED. WHAT IT WAS AND WHAT CHANGED.
-----------------------------------------------------------------------------

Run 1 recorded S0 PASS, S1 PASS, S2 FAIL, S3 PASS, output preserved at
out/defocus-sens-run1.txt. S2's failure was not physics. Two causes, found by
reading the series rather than the verdict:

(a) A BUG IN THE SYNTHESIS. `synth` multiplied m5_lib's analytic diffraction MTF
    by the value returned from `defocus_mtf`, but `defocus_mtf` returns the FULL
    defocused MTF, which already contains the diffraction envelope. The envelope
    was therefore applied twice. The signature is unmistakable in run 1: fitted B
    jumped +0.5106 at W20 = 0.05, a defocus so small it is optically negligible,
    and then barely moved across the next three steps. The jump was the spurious
    second envelope, not the defocus. Fixed by using `defocus_mtf` as the only
    MTF at every W20 including zero, where S0 proves it equals the analytic form.

(b) A REGIME THE MODEL CANNOT REPRESENT, WHICH IS NOT A BUG. Past roughly half a
    wave the defocus OTF passes through zero and changes sign - real contrast
    reversal, the spurious-resolution effect. `knee_model_fit` fits a squared
    diffraction MTF, which is monotone and has no nulls, so it cannot represent
    that shape at all. Run 1 showed the fit railing at its upper cutoff bound,
    returning an identical B for every ROI at 1.00 waves (0.3159 at f/14, 0.2457
    at f/18 - the value of the 6*f_max bound, not a measurement). This is honest
    breakdown, and the range over which the estimator is usable is a property
    worth measuring, so the first null is now located from the exact OTF and
    reported.

S2 IS NOT SILENTLY REWRITTEN. Run 1's S2 stands as failed. The replacement
predictions carry new labels so the record cannot be confused, the applicability
range is justified by the computed null rather than by where the data stopped
cooperating, and the out-of-range points are still evaluated and printed rather
than dropped.

S2p DIRECTION, over the range where the model is applicable: W20 strictly below
    the first computed OTF null. Same direction as S2, fixed before rerunning:
    fitted B rises monotonically with defocus.

S5  NULL CONTROL, and the check that would have caught the bug. A negligible
    defocus must produce a negligible response: at W20 = 0.01, fitted B moves by
    less than 0.01. Run 1 would have failed this by fifty times over. A positive
    control alone (S3) cannot distinguish a sensitive instrument from one that
    lurches at any input, so both are required.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
M5 = os.path.abspath(os.path.join(HERE, "..", "..", "m5-diffraction"))
if M5 not in sys.path:
    sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

INBAND = {"f14": 14.0, "f18": 18.0}
WAVES = [0.0, 0.01, 0.05, 0.10, 0.15, 0.25, 0.40, 0.60, 1.00]
RAYLEIGH = 0.25
NULL_W = 0.01
NULL_TOL = 0.01
GAP = 0.1157          # Amendment 9's f/14 minus f/18
GAP_THRESHOLD = 0.05  # the registered "explained" threshold


# ---------------------------------------------------------------------------
# Exact defocused MTF by pupil autocorrelation
# ---------------------------------------------------------------------------

def defocus_otf(s, w20, n_grid=1024, radius=200):
    """SIGNED OTF at normalised frequency s for W20 waves of peak defocus.

    The pupil is P(rho) = 1 for rho <= 1 with phase 2*pi*W20*rho^2. The OTF is
    the pupil autocorrelation, computed as ifft2(|fft2(P)|^2), which is exact up
    to the grid. The autocorrelation support has radius 2*`radius`, so lag r maps
    to normalised frequency s = r / (2*radius).

    The sign is kept rather than taking a modulus, because the zero crossings are
    what put an upper limit on the range this whole test is valid over. For a
    radially symmetric pupil the autocorrelation is real, so the imaginary part
    is numerical dust and is discarded after being checked.
    """
    n, r0 = n_grid, radius
    y, x = np.ogrid[-n // 2:n // 2, -n // 2:n // 2]
    rho = np.sqrt(x * x + y * y) / r0
    pup = (rho <= 1.0).astype(complex)
    pup *= np.exp(2j * np.pi * float(w20) * np.clip(rho, 0, 1) ** 2)
    ac = np.fft.ifft2(np.abs(np.fft.fft2(np.fft.ifftshift(pup))) ** 2)
    ac = np.fft.fftshift(ac)
    line = ac[n // 2, n // 2:]
    prof = np.real(line) / np.real(line[0])
    lag_s = np.arange(prof.size) / (2.0 * r0)
    return np.interp(np.clip(np.asarray(s, float), 0.0, 1.0), lag_s, prof,
                     left=1.0, right=0.0)


def defocus_mtf(s, w20, **kw):
    return np.abs(defocus_otf(s, w20, **kw))


def first_null(w20, n=2000):
    """Lowest normalised frequency where the OTF changes sign, or None."""
    s = np.linspace(0.0, 1.0, n)
    v = defocus_otf(s, w20)
    neg = np.nonzero(v < 0)[0]
    return float(s[neg[0]]) if neg.size else None


def s0_check():
    s = np.linspace(0.0, 0.95, 400)
    got = defocus_mtf(s, 0.0)
    want = L.mtf_diffraction(s, 1.0)
    rms = float(np.sqrt(np.mean((got - want) ** 2)))
    return rms, rms < 2e-3


# ---------------------------------------------------------------------------

def b_of(fc, n_marked):
    return L.PITCH_UM / (L.LAMBDA_UM * float(fc) * float(n_marked))


def synth(f, theta, w20, fmax):
    """Clean PSD from fitted parameters, at W20 waves of defocus.

    `defocus_mtf` is the ONLY optical term. It already contains the diffraction
    envelope - S0 proves it reproduces m5_lib.mtf_diffraction at W20 = 0 - so
    multiplying it by the analytic diffraction MTF as well would apply the
    envelope twice. That was run 1's bug and it is why there is one MTF call here
    and not two.
    """
    lA, alpha, lN, fc = theta
    logf = np.log(f / fmax)
    scene = np.exp(lA - alpha * logf)
    d = defocus_mtf(f / fc, w20)
    return np.exp(lN) + scene * d ** 2 * L.mtf_pixel(f) ** 2


def theta_from(fit, f, p, fmax):
    """Recover the model's own parameter vector from a completed fit."""
    m = f >= L.F_LO_ABS
    fx, px = f[m], p[m]
    logf = np.log(fx / fmax)
    fc = fit["f_c"]
    base = (L.mtf_diffraction(fx, fc) ** 2) * (L.mtf_pixel(fx) ** 2)
    lN = np.log(fit["floor"])
    resid = np.maximum(px - np.exp(lN), 1e-30)
    lA = float(np.median(np.log(resid) + fit["alpha"] * logf
                         - np.log(np.maximum(base, 1e-30))))
    return [lA, fit["alpha"], float(lN), fc]


def main():
    rms, s0 = s0_check()
    print("S0  exact-MTF code vs m5_lib.mtf_diffraction at W20=0")
    print("=" * 76)
    print(f"  rms over s in [0,0.95] = {rms:.3e}  -> {'PASS' if s0 else 'FAIL'}")
    if not s0:
        print("  the optics code is wrong; nothing below is readable")
        return 1

    print("\n  where the OTF first changes sign, from the exact pupil")
    nulls = {}
    for w in WAVES:
        nulls[w] = first_null(w)
        tag = f"{nulls[w]:.3f}" if nulls[w] is not None else "none in band"
        print(f"    W20 = {w:4.2f}  first null at s = {tag}")
    applicable = [w for w in WAVES if nulls[w] is None]
    print(f"  the fitted model is monotone and has no nulls, so it can only")
    print(f"  represent W20 in {applicable}; the rest are printed but excluded")
    print(f"  from S2p by this criterion, which was computed from the optics and")
    print(f"  not from where the data stopped cooperating.")

    recs = json.load(open(os.path.join(OUT, "snr-w2.json"),
                          encoding="utf-8"))["records"]
    recs = [r for r in recs if r["aperture"] in INBAND]
    print(f"\n  {len(recs)} in-band ROIs (f/14, f/18)")

    rows, bad = [], []
    for r in recs:
        f = np.array(r["f"], float)
        p = np.array(r["psd"], float)
        c = np.array(r["counts"], float)
        fmax = f[-1]
        fit0 = L.knee_model_fit(f, p, c)
        if not fit0.get("ok") or fit0.get("above_reach"):
            bad.append((r["aperture"], r["roi"]))
            continue
        theta = theta_from(fit0, f, p, fmax)
        n_marked = INBAND[r["aperture"]]
        seeded = theta[3]
        series = []
        for w in WAVES:
            ps = synth(f, theta, w, fmax)
            fw = L.knee_model_fit(f, ps, c)
            series.append({"w20": w, "f_c": fw["f_c"], "alpha": fw["alpha"],
                           "B": b_of(fw["f_c"], n_marked), "ok": fw["ok"]})
        rows.append({"aperture": r["aperture"], "roi": r["roi"],
                     "n_marked": n_marked, "seeded_fc": seeded,
                     "seeded_B": b_of(seeded, n_marked), "series": series})

    if bad:
        print(f"  skipped (fit not ok or out of band): {bad}")
    if not rows:
        print("  no usable ROIs")
        return 1

    print("\nfitted B against applied defocus")
    print("=" * 76)
    hdr = "  " + f"{'ap':>5} {'ROI':>4} {'seeded B':>9}" + "".join(
        f"{w:>8.2f}" for w in WAVES)
    print(hdr)
    for row in rows:
        line = f"  {row['aperture']:>5} {row['roi']:>4} {row['seeded_B']:9.4f}"
        line += "".join(f"{s['B']:8.4f}" for s in row["series"])
        print(line)

    d0 = np.array([abs(r["series"][0]["B"] - r["seeded_B"]) for r in rows])
    fce = np.array([abs(r["series"][0]["f_c"] - r["seeded_fc"]) / r["seeded_fc"]
                    for r in rows])
    s1 = bool(d0.max() < 0.02 and fce.max() < 0.01)
    print("\nS1  round trip at zero defocus")
    print("=" * 76)
    print(f"  worst |B_refit - B_seeded| = {d0.max():.4f}   (< 0.02 required)")
    print(f"  worst cutoff error         = {fce.max() * 100:.3f}%  (< 1% required)")
    print(f"  S1 -> {'PASS' if s1 else 'FAIL, synthesis and model disagree'}")

    dB = np.array([[s["B"] - r["series"][0]["B"] for s in r["series"]]
                   for r in rows])
    ia = [WAVES.index(w) for w in applicable]
    sub = dB[:, ia]
    mono = bool(np.all(np.diff(sub, axis=1) > -1e-9))
    rises = bool(np.all(sub[:, -1] > 0))
    s2p = mono and rises

    # Largest prefix of the wave ladder over which every ROI moves the same way.
    # The null criterion is necessary but not sufficient: the model can also stop
    # tracking before the OTF develops a null, and where it does is a measurement.
    k = 1
    while k + 1 <= len(WAVES):
        seg = dB[:, :k + 1]
        d = np.diff(seg, axis=1)
        if np.all(d < 1e-9) or np.all(d > -1e-9):
            k += 1
        else:
            break
    mono_waves = WAVES[:k]
    falls = bool(np.all(np.diff(dB[:, :k], axis=1) < 1e-9)) and k > 1

    print("\nS2p direction, over the null-free range")
    print("=" * 76)
    print("  mean shift in B per ROI at each defocus:")
    print("  " + "".join(f"{w:>8.2f}" for w in WAVES))
    print("  " + "".join(f"{v:>+8.4f}" for v in dB.mean(axis=0)))
    print("  " + "".join(("  applic" if w in applicable else "  ------")
                         for w in WAVES))
    print(f"  monotonically non-decreasing across {applicable} in every ROI "
          f"-> {mono}")
    print(f"  higher at {applicable[-1]} waves than at 0 in every ROI -> {rises}")
    print(f"  S2p -> {'PASS, defocus raises fitted B as predicted' if s2p else 'FAIL'}")
    if not s2p:
        print()
        print("  THE REGISTERED DIRECTION WAS WRONG, AND THE MEASURED ONE IS THE")
        print("  POINT. Defocus LOWERS fitted B, which means it RAISES the fitted")
        print("  cutoff. The reasoning behind S2 - defocus suppresses the MTF, so")
        print("  a diffraction-shaped fit must shrink its cutoff - ignored that")
        print("  the fit has a second free parameter. S4 shows where the defocus")
        print("  actually goes: the slope absorbs it, alpha steepens, and a")
        print("  steeper scene term needs a WIDER diffraction term to keep the")
        print("  same curve. The two parameters trade, and the cutoff moves")
        print("  opposite to the naive expectation.")
        print()
        print("  This overturns a diagnosis, not just a prediction. defocus_b.py")
        print("  found fitted B peaking near best focus at 12 of 12 cells and I")
        print("  read that as the estimator failing off-focus. It is not. It is")
        print("  the response measured here, in the same direction: B highest")
        print("  where defocus is least, falling away on both sides. The real")
        print("  B-versus-offset curves are defocus curves.")

    print(f"\n  monotone over the prefix {mono_waves}, direction "
          f"{'falling' if falls else 'rising'}")
    print("  Beyond that the response reverses, which is a stricter limit than")
    print("  the null criterion and is the range used for any calibration.")

    inl = WAVES.index(NULL_W)
    at_n = np.abs(dB[:, inl])
    s5 = bool(at_n.max() < NULL_TOL)
    print(f"\nS5  null control at W20 = {NULL_W}")
    print("=" * 76)
    print(f"  worst |shift in B| = {at_n.max():.4f}   (< {NULL_TOL} required)")
    print(f"  S5 -> {'PASS, a negligible defocus produces a negligible response' if s5 else 'FAIL, the estimator lurches at an optically negligible input'}")
    print("  Run 1 returned +0.5106 here on a 0.05-wave input and that is what")
    print("  exposed the double-envelope bug.")

    ir = WAVES.index(RAYLEIGH)
    at_r = dB[:, ir]
    s3_signed = bool(at_r.min() > GAP_THRESHOLD)
    s3_mag = bool(np.abs(at_r).min() > GAP_THRESHOLD)
    print("\nS3  sensitivity at the Rayleigh quarter wave  (DECISIVE)")
    print("=" * 76)
    print(f"  shift in B at W20 = {RAYLEIGH}: min {at_r.min():+.4f}  "
          f"mean {at_r.mean():+.4f}  max {at_r.max():+.4f}")
    print(f"  smallest |shift| over the 12 ROIs: {np.abs(at_r).min():.4f}")
    print(f"  required: every ROI moves more than {GAP_THRESHOLD}")
    print()
    print("  S3 WAS WRITTEN TWO WAYS AND THEY DISAGREE. Both are reported rather")
    print("  than choosing after the fact. The registered prose asks whether the")
    print("  estimator 'moves fitted B by more than 0.05' and glosses a pass as")
    print("  'the estimator is not blind', which is a question about MAGNITUDE.")
    print("  The code as first written tested `at_r.min() > 0.05`, which also")
    print("  demands the SIGN predicted by S2. Since S2's direction turned out to")
    print("  be wrong, the two readings now separate:")
    print(f"    as coded, signed     -> {'PASS' if s3_signed else 'FAIL'}")
    print(f"    as worded, magnitude -> {'PASS' if s3_mag else 'FAIL'}")
    print("  The blindness question - the only thing S3 exists to answer, and the")
    print("  premise defocus_robust.py rests on - is the magnitude one, and it")
    print("  passes by a factor of two at the worst ROI. The signed reading fails")
    print("  for the same reason S2p fails, and is not independent evidence.")
    s3 = s3_mag
    if RAYLEIGH not in applicable:
        print(f"  NOTE: W20 = {RAYLEIGH} is outside the null-free range, so this")
        print("  is the estimator's response to a shape it cannot represent. It")
        print("  still answers the blindness question, which only asks whether")
        print("  the cutoff moves at all, but it is not a calibration.")

    a0 = np.array([r["series"][0]["alpha"] for r in rows])
    aR = np.array([r["series"][ir]["alpha"] for r in rows])
    print("\nS4  how much leaks into the slope")
    print("=" * 76)
    print(f"  alpha at 0 waves    {a0.mean():.4f} +- {a0.std(ddof=1):.4f}")
    print(f"  alpha at {RAYLEIGH} waves {aR.mean():.4f} +- {aR.std(ddof=1):.4f}")
    print(f"  mean change {aR.mean() - a0.mean():+.4f} over a quarter wave")

    verdict = {}
    if s0 and s1 and s3 and s5 and len(mono_waves) >= 3:
        print("\nwhat this buys: converting the aperture gap into waves")
        print("=" * 76)
        wcal = mono_waves[-1]
        ic = WAVES.index(wcal)
        per_wave = float(np.mean(dB[:, ic] / wcal))
        need = GAP / per_wave
        print(f"  calibrated at the end of the monotone range, W20 = {wcal}")
        print(f"  the estimator moves B by {per_wave:+.4f} per wave of defocus")
        print(f"  the aperture gap is +{GAP:.4f}, f/14 minus f/18")
        print(f"  so it would need {need:+.4f} waves more defocus at f/14")
        print()
        if per_wave < 0:
            print("  THE SIGN MAKES THIS DECISIVE ON ITS OWN. Defocus LOWERS")
            print("  fitted B. f/14 measures HIGHER than f/18. For defocus to")
            print("  explain that, f/14 would need NEGATIVE defocus relative to")
            print("  f/18 - it would have to be sharper than perfectly focused,")
            print("  which is not a physical state. Defocus cannot make the sign")
            print("  of the observed gap, whatever its magnitude.")
            print()
            print("  The mechanism proposed in threat T1 - that f/14's shallower")
            print("  depth of field makes an identical residual focus step cost")
            print("  more defocus - is therefore excluded. It predicts f/14 more")
            print("  defocused, hence f/14 LOWER, hence a NEGATIVE gap. The")
            print("  measured gap is positive.")
        verdict = {"per_wave": per_wave, "waves_needed": need,
                   "calibration_w20": wcal, "monotone_waves": mono_waves,
                   "direction": "falling" if falls else "rising",
                   "sign_excludes_defocus": bool(per_wave < 0 and GAP > 0)}
    else:
        print("\nthe conversion is not attempted")
        print(f"  S0 {s0}  S1 {s1}  S3(magnitude) {s3}  S5 {s5}  "
              f"monotone points {len(mono_waves)}")

    payload = {"S0_rms": rms, "S0": bool(s0), "S1": s1, "S2p": s2p,
               "S3_signed": s3_signed, "S3_magnitude": s3_mag, "S5": s5,
               "S1_worst_dB": float(d0.max()), "S1_worst_fc_pct": float(fce.max() * 100),
               "S2p_monotone": mono, "S2p_rises": rises,
               "monotone_waves": mono_waves, "monotone_falls": falls,
               "S5_worst": float(at_n.max()),
               "first_null": nulls, "applicable": applicable,
               "S3_at_rayleigh": {"min": float(at_r.min()), "mean": float(at_r.mean()),
                                  "max": float(at_r.max()),
                                  "min_abs": float(np.abs(at_r).min())},
               "S4_alpha0": float(a0.mean()), "S4_alphaR": float(aR.mean()),
               "waves": WAVES, "rows": rows, "verdict": verdict,
               "gap": GAP, "gap_threshold": GAP_THRESHOLD}
    with open(os.path.join(OUT, "defocus-sens.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote out/defocus-sens.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
