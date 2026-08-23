"""M41 step 11 -- PLANTED POSITIVE CONTROL FOR THE METRICS THEMSELVES.

a5_planted.py is a positive control on the ARMS: it asks whether arm D can beat
arm A where the forward model is true.  It passed (+9.936 dB).  It says nothing
about whether the METRICS used to score the real stacks can see anything.  This
script closes that gap, which is the one rule 20 is about:

    a null is not a kill until the harness has been shown to detect a real
    effect, with the right sign and roughly the right magnitude.

WHAT IS PLANTED.  A Gaussian blur of KNOWN sd sb, applied in the Fourier domain
so the planted MTF is exactly exp(-2 pi^2 sb^2 f^2) with no kernel truncation.
The source is DEFINED as the reference at sb = 0; its own residual blur cancels
in the ratio because the truth channel uses the same source.

THE RECOVERY RATIO, defined before running.  Two definitions are reported side
by side rather than one being chosen after seeing the numbers:

    rec_lin(sb) = ( m_meas(0) - m_meas(sb) ) / ( m_pred(0) - m_pred(sb) )
    rec_log(sb) = ln( m_meas(0)/m_meas(sb) ) / ln( m_pred(0)/m_pred(sb) )

    1.0 = the metric recovers the planted loss;  0.0 = BLIND;  <0 = WRONG SIGN.

rec_lin is defined for a bounded correlation that can reach zero or go negative
(frc_at_fsig); rec_log is the right one for a positive quantity spanning orders
of magnitude (p_ratio).  Where they disagree, both are shown.

The truth channel is the noiseless blurred source for the scalar metrics, and
for the FRC family it is the analytic split-half expectation SNR/(1+SNR) built
from the KNOWN source spectrum and the KNOWN noise sd (m41lib3.frc_pred).

RULE 20 -- written down before the run.
  * The input that makes a metric FAIL here is a metric whose reading does not
    move across the ladder.  I predict frc_cross at 1/7 is exactly that, because
    a10 showed it is right-censored at the ring-grid endpoint on real data.
  * The input that makes it PASS exists too: hp_sd and the band-power ratio must
    recover a 4 px Gaussian, which removes essentially all power above f_sig.
  * If EVERY metric reads the same, the ladder has no discrimination and is void.

RULE 9 -- the flat-ROI control is a SOURCE in the ladder, not a closing check.
The 119MSDCF flat ROI is run FIRST through the identical ladder.  A metric that
recovers the plant equally well there is detecting blur, not resolution.

RULE 13 -- can the plant express the failure?  Source S2 is synthetic broadband
with power to Nyquist by construction, so a metric that reads no loss on S2
cannot blame the scene.  Source S1 is a real macro texture whose optics cut off
at f_sig = 0.2762 (fact 27), so S1 and S2 together separate "the metric is
blind" from "the source has nothing there".

RULE 15 -- m41lib.py, m41lib2.py and every a1..a9 script are frozen and NOT
edited.  New code lives in m41lib3.py and here.
Read-only corpora are never written.
"""
import os, sys, glob, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rawpy
import m41lib as L
import m41lib3 as L3

OUT = L.OUT
N = 512
PAD = 32
SB = (0.0, 0.5, 1.0, 2.0, 4.0)            # planted Gaussian sd, px
RHO = (0.0, 0.5, 0.9)                     # fraction of noise POWER shared by both halves
G, RN_E = 0.11446886446886446, 4.2        # 119MSDCF, ISO 50
NOISE = (("frame", 1.0), ("merged", 1.0 / 4.0))   # single frame, and a 16-frame half
METRICS = ("frc_cross_1_7", "frc_cross_0_5", "frc_at_fsig",
           "hp_sd", "p_ratio", "mean_grad")
MIN_PRED = 0.01     # predicted change below this -> the truth channel says
                    # "nothing to recover"; the ratio is undefined, not zero.


def core(a):
    return a[PAD:-PAD, PAD:-PAD]


def load_plane(stack, key):
    """One frame of one ROI, green quad, active area only (rule 7)."""
    with open(os.path.join(OUT, "rois_b.json")) as fh:
        rois = json.load(fh)
    info = rois[stack]
    files = sorted(glob.glob(os.path.join(info["dir"], "*.ARW")))
    x, y, _, _ = info[key]
    x, y = max(PAD, x), max(PAD, y)
    f = files[len(files) // 2]
    with rawpy.imread(f) as r:
        v = r.raw_image_visible
        g1 = v[2 * y:2 * (y + N):2, 2 * x + 1:2 * (x + N) + 1:2].astype(np.float32)
        g2 = v[2 * y + 1:2 * (y + N) + 1:2, 2 * x:2 * (x + N):2].astype(np.float32)
    return 0.5 * (g1 + g2) - L.BLACK


def synth_broadband(seed=41):
    """Random-phase field with a 1/f amplitude spectrum, populated to Nyquist,
    plus hard-edged discs.  Power at every ring by construction -- rule 13's
    escape hatch from 'the source had nothing there'."""
    rng = np.random.default_rng(seed)
    FY = np.broadcast_to(np.fft.fftfreq(N)[:, None], (N, N // 2 + 1))
    FX = np.broadcast_to(np.fft.rfftfreq(N)[None, :], (N, N // 2 + 1))
    f = np.maximum(np.sqrt(FX * FX + FY * FY), 1.0 / N)
    img = np.fft.irfft2((1.0 / f) * np.exp(1j * rng.uniform(0, 2 * np.pi, f.shape)),
                        s=(N, N))
    img = img / img.std()
    yy, xx = np.mgrid[0:N, 0:N]
    for _ in range(60):
        cy, cx = rng.integers(20, N - 20, 2)
        rr = rng.uniform(4, 22)
        img = img + 2.5 * (((yy - cy) ** 2 + (xx - cx) ** 2) < rr * rr)
    img = img - img.min()
    return (img * (1200.0 / max(img.std(), 1e-6))).astype(np.float32)


def sigma_map(plane, scale):
    return np.sqrt(np.maximum(scale * scale * 0.5 *
                              (G * np.maximum(plane, 0.0) + (RN_E * G) ** 2), 1e-12))


def split_pair(blurred, scale, rho, rng):
    """Two half-merge realisations sharing a fraction `rho` of their noise POWER.
    rho = 0 is the ideal independent split; rho -> 1 is the common-mode limit that
    a8/a10 measured on real halves of one capture."""
    sig = sigma_map(blurred, scale)
    shared = rng.normal(0, 1, blurred.shape).astype(np.float32)
    ea = rng.normal(0, 1, blurred.shape).astype(np.float32)
    eb = rng.normal(0, 1, blurred.shape).astype(np.float32)
    ca, cb = np.sqrt(rho), np.sqrt(1.0 - rho)
    return (blurred + sig * (ca * shared + cb * ea),
            blurred + sig * (ca * shared + cb * eb))


def measure(a, b):
    """All six metrics on one split pair.  Every FRC crossing carries its
    censoring flag; a censored crossing is a LOWER BOUND, never a value."""
    ff, fr, _ = L.frc(a.astype(np.float64), b.astype(np.float64), nbin=64)
    x17, c17 = L3.cross(ff, fr, 1.0 / 7.0)
    x50, c50 = L3.cross(ff, fr, 0.5)
    return {"frc_cross_1_7": (x17, c17),
            "frc_cross_0_5": (x50, c50),
            "frc_at_fsig": (float(np.interp(L.F_SIG, ff, fr)), False),
            "hp_sd": (L.hp_sd(a), False),
            "p_ratio": (L3.p_ratio(a), False),
            "mean_grad": (L3.mean_grad(a), False)}


def predict(latent, sigma_scalar):
    """Truth channel.  Scalars: the metric on the NOISELESS blurred source.
    FRC family: the analytic split-half expectation from the known spectrum."""
    ff, fr = L3.frc_pred(latent, sigma_scalar, nbin=64)
    x17, c17 = L3.cross(ff, fr, 1.0 / 7.0)
    x50, c50 = L3.cross(ff, fr, 0.5)
    return {"frc_cross_1_7": (x17, c17),
            "frc_cross_0_5": (x50, c50),
            "frc_at_fsig": (float(np.interp(L.F_SIG, ff, fr)), False),
            "hp_sd": (L.hp_sd(latent), False),
            "p_ratio": (L3.p_ratio(latent), False),
            "mean_grad": (L3.mean_grad(latent), False)}


def recoveries(m0, ms, p0, ps):
    """(rec_lin, rec_log, note).  Censoring in either channel makes both
    undefined -- a censored crossing is a bound and bounds do not divide."""
    (v0, c0), (vs, cs), (q0, d0), (qs, ds) = m0, ms, p0, ps
    if (c0 or cs) and (d0 or ds):
        return None, None, "both-censored"
    if c0 or cs:
        return None, None, "meas-censored"
    if d0 or ds:
        return None, None, "truth-censored"
    dp = q0 - qs
    lin = None
    if abs(dp) >= MIN_PRED * max(abs(q0), 1e-30):
        lin = float((v0 - vs) / dp)
    lg = None
    if v0 > 0 and vs > 0 and q0 > 0 and qs > 0 and abs(np.log(q0 / qs)) >= MIN_PRED:
        lg = float(np.log(v0 / vs) / np.log(q0 / qs))
    note = "" if (lin is not None or lg is not None) else "no-pred-change"
    return lin, lg, note


def fmt(v, cens=False, w=10):
    if v is None:
        return f"{'--':>{w}s}"
    s = f"{v:.4g}" if (v == 0 or abs(v) >= 1e-3) else f"{v:.2e}"
    return f"{(s + ('C' if cens else '')):>{w}s}"


def main():
    fh = open(os.path.join(OUT, "a11_metric_power.log"), "w", encoding="utf-8")

    def p(m):
        print(m); fh.write(m + "\n"); fh.flush()

    p("M41 step 11 -- planted-blur POSITIVE CONTROL ON THE METRICS.")
    p("  rec_lin = (m(0)-m(sb)) / (pred(0)-pred(sb));   "
      "rec_log = ln(m(0)/m(sb)) / ln(pred(0)/pred(sb))")
    p("  1.0 recovers the planted loss, 0.0 is BLIND, <0 is the WRONG SIGN.")
    p("  'C' marks a CENSORED reading (>= the ring-grid endpoint).  A censored "
      "value is a BOUND,")
    p("  so no ratio involving it is defined -- that is reported, not rounded to "
      "a number.")
    p("  Rule 9: the FLAT source is run FIRST, before either detail source.")

    sources = [("S3-flat-119", load_plane("119MSDCF", "flat_roi")),
               ("S1-real-119", load_plane("119MSDCF", "detail_roi")),
               ("S2-synth", synth_broadband())]
    res = {}
    for sname, src in sources:
        src = np.asarray(src, np.float32)
        p(f"\n{'='*96}\nSOURCE {sname}: mean {src.mean():.1f} DN, sd {src.std():.1f} DN, "
          f"hp_sd {L.hp_sd(src):.2f} DN, P(>f_sig)/P(<f_sig) {L3.p_ratio(src):.3e}")
        res[sname] = {}
        blurs = {sb: L3.gauss_blur(src, sb) for sb in SB}
        hdr = "      " + f"{'metric':16s}" + "".join(f"{'sb=%g' % sb:>10s}" for sb in SB)
        for nname, scale in NOISE:
            sig_med = float(np.median(sigma_map(src, scale)))
            p(f"\n  --- noise '{nname}' (x{scale:g} single-frame, median modelled "
              f"sigma {sig_med:.2f} DN) ---")
            pred = {sb: predict(core(blurs[sb]), sig_med) for sb in SB}
            p("    TRUTH CHANNEL (noiseless source; analytic SNR/(1+SNR) for FRC):")
            p(hdr)
            for mk in METRICS:
                p("      " + f"{mk:16s}" +
                  "".join(fmt(pred[sb][mk][0], pred[sb][mk][1]) for sb in SB))
            for rho in RHO:
                rng = np.random.default_rng(1041)
                meas = {sb: measure(*[core(z) for z in
                                      split_pair(blurs[sb], scale, rho, rng)])
                        for sb in SB}
                key = f"{nname}|rho={rho:g}"
                res[sname][key] = {}
                p(f"\n    MEASURED, shared-noise fraction rho = {rho:g}")
                p(hdr)
                for mk in METRICS:
                    p("      " + f"{mk:16s}" +
                      "".join(fmt(meas[sb][mk][0], meas[sb][mk][1]) for sb in SB))
                p("    RECOVERY   rec_lin / rec_log")
                for mk in METRICS:
                    cells = []
                    for sb in SB[1:]:
                        lin, lg, note = recoveries(meas[0.0][mk], meas[sb][mk],
                                                   pred[0.0][mk], pred[sb][mk])
                        res[sname][key].setdefault(mk, {})[str(sb)] = dict(
                            lin=lin, log=lg, note=note,
                            meas=meas[sb][mk][0], meas_cens=bool(meas[sb][mk][1]),
                            pred=pred[sb][mk][0], pred_cens=bool(pred[sb][mk][1]))
                        if lin is None and lg is None:
                            cells.append(f"{'(' + note + ')':>20s}")
                        else:
                            a_ = f"{lin:+.3f}" if lin is not None else "  --  "
                            b_ = f"{lg:+.3f}" if lg is not None else "  --  "
                            cells.append(f"{a_ + '/' + b_:>20s}")
                    p("      " + f"{mk:16s}" + "".join(cells))

    # ------------------------------------------------------------ summary
    p("\n" + "=" * 96)
    p("SUMMARY -- rec_lin at sb = 2.0 px, 'merged' noise, rho = 0.  This is the BEST")
    p("case available to every metric: independent noise, no common mode at all.")
    p(f"  {'metric':16s} {'S3-flat':>13s} {'S1-real':>13s} {'S2-synth':>13s}   verdict")
    verdicts = {}
    for mk in METRICS:
        row = [res[s_]["merged|rho=0"][mk]["2.0"]["lin"] for s_, _ in sources]
        note = res[sources[1][0]]["merged|rho=0"][mk]["2.0"]["note"]
        good = [x for x in row[1:] if x is not None]
        if not good:
            v = f"NO POWER -- undefined on both detail sources ({note})"
        elif max(good) > 0.4:
            v = "HAS POWER"
            if row[0] is not None and row[0] > 0.4:
                v += "; fires on the FLAT source too (rule 9)"
        elif min(good) < 0:
            v = "WRONG SIGN"
        else:
            v = "WEAK (<0.4)"
        verdicts[mk] = v
        p(f"  {mk:16s} " +
          " ".join(f"{('%+.3f' % x) if x is not None else '--':>13s}" for x in row)
          + f"   {v}")
    res["verdicts"] = verdicts

    p("\nCENSORING LADDER -- how much blur must be planted before the 1/7 crossing")
    p("stops being a bound and becomes a value?  rho = 0 throughout.")
    lad = {}
    for sname, _ in sources:
        for nname, _ in NOISE:
            k = f"{nname}|rho=0"
            r0 = res[sname][k]["frc_cross_1_7"]
            firstu = "never"
            for sb in SB[1:]:
                if not r0[str(sb)]["meas_cens"]:
                    firstu = f"sb={sb:g}"
                    break
            ref_cens = any(r0[str(sb)]["note"] in ("meas-censored", "both-censored")
                           for sb in SB[1:] if r0[str(sb)]["meas_cens"] is False)
            lad[f"{sname}|{nname}"] = firstu
            p(f"  {sname:12s} {nname:7s}: blurred arm first uncensored at {firstu}; "
              f"the sb=0 REFERENCE is {'CENSORED' if ref_cens else 'censored'}"
              f" -> no ratio to a reference can be formed")
    res["censoring_ladder"] = lad

    p("\nMECHANISM -- the shared-noise sweep on the one FRC statistic that is never")
    p("censored (frc_at_fsig), rec_lin at sb = 2.0, 'merged' noise:")
    for sname, _ in sources:
        line = []
        for rho in RHO:
            r = res[sname][f"merged|rho={rho:g}"]["frc_at_fsig"]["2.0"]
            line.append(f"rho={rho:g}: " +
                        (f"{r['lin']:+.3f}" if r["lin"] is not None else "  --  "))
        p(f"  {sname:12s} " + "   ".join(line))

    with open(os.path.join(OUT, "a11_results.json"), "w") as g1:
        json.dump(res, g1, indent=2)
    p("\nwrote out/a11_results.json")
    fh.close()


if __name__ == "__main__":
    main()
