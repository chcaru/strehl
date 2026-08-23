"""M46 step b2 -- the planted-blur ladder, three plant models, and the ACCEPTANCE
BAR scored.

Registered in PREREGISTRATION.md secs 2, 3, 4.2 (commit 2474e5d, before any M46
script existed).

THE BAR, verbatim from sec 2:

    A metric is ADMISSIBLE if, on the planted-blur ladder, it achieves
    recovery >= +0.9 on detail AND <= +0.3 on flat.

with fact 477's linear recovery unchanged:

    rec(sb) = ( m(0) - m(sb) ) / ( pred(0) - pred(sb) )

RULE 20, discharged before the run.  The bar is only meaningful if SOMETHING can
pass it.  `oracle_fsc` -- Fourier shell correlation of the observation against
the KNOWN latent -- is included for exactly that reason.  It is not shippable and
is never proposed as a metric.  If the oracle fails the FLAT half, then the bar
is unachievable and the finding is that the GATE is broken, not the metrics.
That check is printed FIRST, before any candidate is scored.

DEVIATION D6, declared here because it was discovered while writing this file
and the pre-registration is not edited after the fact.  Sec 4.2 registered two
plant models and called PM-1 "post-capture".  That name covers two physically
different operations, so PM-1 is SPLIT and all three are run -- an arm added,
never removed:

    PM_A   Y_i = H*L + P + N_i        optical blur, fixed pattern OUTSIDE
    PM_B   Y_i = H*(L + P) + N_i      optical blur, fixed pattern INSIDE
                                       (fact 477's model: its sources were
                                        observed ROIs with the pattern baked in)
    PM_C   Y_i = H*(L + P + N_i)      a LINEAR POST-FILTER on the captured
                                       image -- what a merge that low-passes its
                                       own output actually does

PRE-DECLARED PREDICTION for PM_C, written before the run: every correlation-based
metric must read recovery ~0, because H attenuates the common power and the
independent power by the same |H|^2 and their ratio cannot move.  If a
correlation metric DOES move under PM_C, this model of it is wrong.  hp_sd,
p_ratio and mean|grad| are NOT ratios of the two and are predicted to move.

The fixed-pattern amplitude is not invented.  b1 measured the two-capture FRC of
the FLAT ROI at f_sig = +0.7310 with mean n_eff = 8.784, and
rho = FRC/(1-FRC)/n_eff converts that to the fixed-pattern variance as a
fraction of SINGLE-FRAME noise variance.  That number is computed here from
b1_results.json, not typed in.
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m46lib as M

SB = [0.0, 0.5, 1.0, 2.0, 4.0]
SB_HEAD = 2.0
MODELS = ["PM_A", "PM_B", "PM_C"]
SEED_FPN = 46046
N = 512


def frc_pred_ring(common, sigma, hprof=None, nbin=M.NBIN):
    """Analytic two-realisation FRC per ring: C/(C+U).

    `common` is the noiseless image both realisations share; `sigma` the
    independent per-pixel sd; `hprof` an optional callable f -> |H(f)|^2 giving
    the factor by which the INDEPENDENT noise power is also attenuated (PM_C
    only).  Fact 478 validated this channel against the measured split to within
    4.7% at 17 points, which is why it is trusted here."""
    n = common.shape[0]
    w = np.outer(np.hanning(n), np.hanning(n))
    S = np.abs(np.fft.fftshift(np.fft.fft2((common - common.mean()) * w))) ** 2
    npow0 = sigma * sigma * float((w * w).sum())
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    ff, fr = [], []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        if m.sum() < 8:
            continue
        f = 0.5 * (edges[i] + edges[i + 1]) / n
        u = npow0 * (hprof(f) if hprof else 1.0)
        c = float(S[m].mean())
        ff.append(f); fr.append(c / (c + u))
    return np.array(ff), np.array(fr)


def h2(sb):
    return lambda f: float(np.exp(-4.0 * (np.pi ** 2) * (sb ** 2) * (f ** 2)))


def measure(latent, fpn, sigma, sb, model, rng):
    """Every metric on one (sb, model) point.  Returns dict of value-or-None;
    None means CENSORED or undefined, and a None never becomes a zero."""
    y1 = M.realise(latent, fpn, sigma, sb, model, rng)
    y2 = M.realise(latent, fpn, sigma, sb, model, rng)
    cr, cen = M.frc_cross_c(y1, y2)
    ocr, ocen = M.frc_cross_c(y1, latent)
    return dict(frc2_cross=None if cen else cr,
                frc2_cross_raw=cr, frc2_censored=bool(cen),
                frc2_at_fsig=M.frc_at(y1, y2),
                hp_sd=M.hp_sd(y1),
                p_ratio=M.p_ratio(y1),
                mean_grad=M.mean_grad(y1),
                oracle_fsc=M.oracle_fsc_at(y1, latent),
                oracle_cross=None if ocen else ocr,
                oracle_censored=bool(ocen))


def predict(latent, fpn, sigma, sb, model):
    """The truth channel.  Scalar metrics: evaluated on the NOISELESS source
    under the same model.  FRC-family: the analytic C/(C+U) ring curve, because
    a noiseless pair would correlate at exactly 1.0 everywhere and carry no
    information at all."""
    t = M.truth(latent, fpn, sb, model)
    hp = h2(sb) if model == "PM_C" else None
    ff, fr = frc_pred_ring(t, sigma, hp)
    cr, cen = M.L3.cross(ff, fr)
    at = float(np.interp(M.F_SIG, ff, fr))
    ol = M.blur(latent, sb) if model == "PM_A" else M.blur(latent + fpn, sb)
    if model == "PM_C":
        ol = M.blur(latent + fpn, sb)
    ocr, ocen = M.frc_cross_c(t, latent)
    return dict(frc2_cross=None if cen else cr, frc2_censored=bool(cen),
                frc2_at_fsig=at,
                hp_sd=M.hp_sd(t), p_ratio=M.p_ratio(t), mean_grad=M.mean_grad(t),
                oracle_fsc=M.oracle_fsc_at(t, latent),
                oracle_cross=None if ocen else ocr, oracle_censored=bool(ocen))


METRICS = ["frc2_cross", "frc2_at_fsig", "hp_sd", "p_ratio", "mean_grad",
           "oracle_cross", "oracle_fsc"]


def main():
    t0 = time.time()
    print("=" * 78)
    print("M46 b2 -- PLANTED LADDER, THREE PLANT MODELS, THE BAR SCORED")
    print("=" * 78)

    with open(os.path.join(M.OUT, "b1_results.json")) as fh:
        b1 = json.load(fh)
    z = np.load(os.path.join(M.OUT, "b1_merges.npz"))
    pad = 32
    det = z["d112"][pad:-pad, pad:-pad].astype(np.float32)
    flt = z["f112"][pad:-pad, pad:-pad].astype(np.float32)
    g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]

    # -------------------------------------------------- rho, MEASURED not typed
    frc_flat = b1["twocap"]["flat"]["at_fsig"]
    neff_flat = b1["n_eff"]["112_flat"]
    rho = frc_flat / (1.0 - frc_flat) / neff_flat
    print("\n0. THE FIXED-PATTERN FRACTION, DERIVED FROM b1 (not chosen)")
    print(f"   two-capture FRC of the FLAT ROI at f_sig = {frc_flat:+.4f}, "
          f"mean n_eff = {neff_flat:.3f}")
    print(f"   rho = FRC/(1-FRC)/n_eff = {rho:.4f}  -- fixed-pattern variance as a")
    print("   fraction of SINGLE-FRAME noise variance.  Two INDEPENDENT captures")
    print("   of the same subject on the same body still share this.")

    lvl_d, lvl_f = float(np.median(det)), float(np.median(flt))
    sig_d = float(np.sqrt(M.noise_var_dn(lvl_d, g, rn_e)))
    sig_f = float(np.sqrt(M.noise_var_dn(lvl_f, g, rn_e)))
    neff_d = b1["n_eff"]["112_detail"]
    print(f"\n   detail ROI level {lvl_d:.1f} DN -> frame sigma {sig_d:.3f} DN, "
          f"merged {sig_d/np.sqrt(neff_d):.3f}")
    print(f"   flat   ROI level {lvl_f:.1f} DN -> frame sigma {sig_f:.3f} DN, "
          f"merged {sig_f/np.sqrt(neff_flat):.3f}")
    print(f"   rule 10 detector, hp_sd/model_sigma on the MERGED plane: "
          f"detail {M.hp_sd(det)/ (sig_d/np.sqrt(neff_d)):.2f}, "
          f"flat {M.hp_sd(flt)/(sig_f/np.sqrt(neff_flat)):.2f}")
    print("   (near 1.0 means noise-dominated, which is what a flat ROI must be)")

    syn = M.synth_broadband(N, 4611)
    syn = (syn * det.std() + lvl_d).astype(np.float32)

    SRC = {"S_flat": (flt, sig_f, neff_flat),
           "S_detail": (det, sig_d, neff_d),
           "S_synth": (syn, sig_d, neff_d)}

    res = dict(rho=rho, sig_d=sig_d, sig_f=sig_f, neff=dict(d=neff_d, f=neff_flat),
               ladder={}, bar={}, rho_sweep={}, levels=dict(lvl_d=lvl_d, lvl_f=lvl_f))

    # ------------------------------------------------------------ the ladder
    for noise_tag in ("merged", "frame"):
        for model in MODELS:
            print("\n" + "-" * 78)
            print(f"LADDER  model={model}  noise={noise_tag}  rho_fpn={rho:.4f}")
            print("-" * 78)
            for sname, (lat, sfr, ne) in SRC.items():
                sigma = sfr / np.sqrt(ne) if noise_tag == "merged" else sfr
                fpn = M.make_fpn(lat.shape, SEED_FPN, np.sqrt(rho) * sfr)
                rng = np.random.default_rng(hash((sname, model, noise_tag)) % (2**31))
                mm, pp = {}, {}
                for sb in SB:
                    mm[sb] = measure(lat, fpn, sigma, sb, model, rng)
                    pp[sb] = predict(lat, fpn, sigma, sb, model)
                print(f"  {sname}   sigma={sigma:.3f} DN")
                hdr = "    metric        " + "".join(f"  sb={s:<6.1f}" for s in SB)
                print(hdr)
                for met in METRICS:
                    row = f"    {met:<14s}"
                    for sb in SB:
                        v = mm[sb][met]
                        row += "     --    " if v is None else f"  {v:9.4f}"
                    print(row + "   MEASURED")
                    row = f"    {'  (truth)':<14s}"
                    for sb in SB:
                        v = pp[sb][met]
                        row += "     --    " if v is None else f"  {v:9.4f}"
                    print(row)
                    row = f"    {'  REC':<14s}"
                    for sb in SB:
                        r = M.rec_lin(mm[0.0][met], mm[sb][met],
                                      pp[0.0][met], pp[sb][met])
                        row += "     --    " if r is None else f"  {r:+9.4f}"
                    print(row)
                key = f"{model}|{noise_tag}|{sname}"
                res["ladder"][key] = dict(
                    meas={str(s): {k: v for k, v in mm[s].items()} for s in SB},
                    pred={str(s): {k: v for k, v in pp[s].items()} for s in SB},
                    rec={met: {str(s): M.rec_lin(mm[0.0][met], mm[s][met],
                                                 pp[0.0][met], pp[s][met]) for s in SB}
                         for met in METRICS},
                    sigma=float(sigma))

    # ------------------------------------------------------- score the bar
    print("\n" + "=" * 78)
    print("THE ACCEPTANCE BAR, SCORED.  recovery >= +0.90 on detail AND <= +0.30 on flat")
    print(f"at the headline point sb={SB_HEAD}, noise='merged' -- the best case available")
    print("to every metric.  Fact 477's linear recovery, unchanged.")
    print("=" * 78)
    for model in MODELS:
        print(f"\n  plant model {model}")
        print("    metric          rec(detail)   rec(flat)    ADMISSIBLE?")
        rows = {}
        for met in METRICS:
            rd = res["ladder"][f"{model}|merged|S_detail"]["rec"][met][str(SB_HEAD)]
            rf = res["ladder"][f"{model}|merged|S_flat"]["rec"][met][str(SB_HEAD)]
            if rd is None or rf is None:
                v = "NO -- undefined (censored)"
            elif rd >= 0.90 and rf <= 0.30:
                v = "*** YES ***"
            elif rd < 0.90 and (rf is not None and rf <= 0.30):
                v = "no -- fails DETAIL half"
            elif rd >= 0.90:
                v = "no -- fails FLAT half"
            else:
                v = "no -- fails BOTH halves"
            print(f"    {met:<14s} {M.fmt(rd, 9, 4)}   {M.fmt(rf, 9, 4)}   {v}")
            rows[met] = dict(rec_detail=rd, rec_flat=rf, verdict=v)
        res["bar"][model] = rows

    print("\n  RULE 20 CHECK ON THE GATE ITSELF (printed before any conclusion):")
    for model in MODELS:
        o = res["bar"][model]["oracle_fsc"]
        ok = o["verdict"].startswith("***")
        print(f"    {model}: oracle_fsc {'PASSES' if ok else 'FAILS'} the bar "
              f"({M.fmt(o['rec_detail'],7,3)} detail, {M.fmt(o['rec_flat'],7,3)} flat)")
    print("    If the oracle FAILS the flat half under a model, the BAR is")
    print("    unachievable under that model and the finding is about the gate.")

    # --------------------------------------------------------- rho sweep
    print("\n" + "=" * 78)
    print("MECHANISM -- rho_fpn sweep, PM_A, sb=2, merged noise")
    print("=" * 78)
    print("    rho     source      frc2_at_fsig REC   frc2_cross REC   oracle_fsc REC")
    for r in (0.0, 0.1, rho, 0.3, 0.5, 1.0):
        for sname, (lat, sfr, ne) in SRC.items():
            sigma = sfr / np.sqrt(ne)
            fpn = M.make_fpn(lat.shape, SEED_FPN, np.sqrt(r) * sfr)
            rng = np.random.default_rng(97)
            m0 = measure(lat, fpn, sigma, 0.0, "PM_A", rng)
            m2 = measure(lat, fpn, sigma, SB_HEAD, "PM_A", rng)
            p0 = predict(lat, fpn, sigma, 0.0, "PM_A")
            p2 = predict(lat, fpn, sigma, SB_HEAD, "PM_A")
            vals = [M.rec_lin(m0[k], m2[k], p0[k], p2[k])
                    for k in ("frc2_at_fsig", "frc2_cross", "oracle_fsc")]
            print(f"    {r:5.3f}   {sname:<10s}  " +
                  "      ".join(M.fmt(v, 8, 4) for v in vals))
            res["rho_sweep"][f"{r:.3f}|{sname}"] = [v for v in vals]

    with open(os.path.join(M.OUT, "b2_results.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/b2_results.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
