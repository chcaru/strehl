"""M115 -- s09: why the planted narrowing did NOT behave like a noise floor.

s08 established, with a monotone dose-response positive control, that a common
additive noise floor q does NOT compress an SNR ratio toward 1.  It drives it
toward the SIGNAL-POWER ratio of the two arms:

    SNR_A/SNR_B  ->  P_sig_A / P_sig_B      as q -> inf

In M115's arm set that asymptote is beta = -1.0186: the measured ordering
INVERTS.  Not compression -- sign reversal, with the residual log-spread (+/-
2.810) WIDER than the true one (+/- 1.886).

But s08 also threw an inconsistency that must be resolved before any of this is
reportable.  The real planted narrowing inflated P_noise by 4.66x, which as a
common floor is a dose of q_eff = 3.66 x median P_noise, and the sweep says that
dose gives beta = -0.8515.  The narrowing measured beta = +0.5861.  Those are
not the same number and not even the same sign.  Something in the narrowing is
not a noise floor.

TWO CANDIDATES, AND THEY ARE SEPARABLE

  H1  CALIBRATION CONFOUND.  The narrowing moved the self-calibrated blur scale
      s from 1.0164 to 1.2577 (+23.7%).  s sets every arm's weights, so the
      narrowed arms are not the same estimators as the intact arms.  The spectra
      would then differ for a reason that has nothing to do with added noise.
      ISOLATED BY: re-running the narrowed cube with s FROZEN at the intact
      value.  If beta moves back toward the sweep prediction, H1 carries it.

  H2  QUANTISATION ERROR IS NOT NOISE.  Rounding error is a DETERMINISTIC
      function of the pixel value, not a random draw.  Two frames viewing the
      same scene content receive correlated rounding error.  The split-stack
      channel defines P_sig = Re<A conj(B)> and P_noise = P(A-B)/2, so anything
      correlated between the halves is booked as SIGNAL.  If H2 holds, the
      narrowing does not merely inflate noise -- it FABRICATES signal, and the
      arms' P_sig should rise.  (In s08 they did, 1.25-1.40x.)
      ISOLATED BY: a matched-power dither control.  Measure the actual
      quantisation error field, then add an INDEPENDENT random field of exactly
      the same per-frame power and run the identical statistic.  Random noise of
      matched power is the null; if quantisation departs from it in P_sig, the
      departure is the correlation, measured rather than argued.

The dither control is the load-bearing one, and it is a true null-and-effect
pair: same power, same pipeline, same statistic, differing only in whether the
perturbation is correlated across frames.
"""
import os, sys, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import load_detail, banner
from negctl_bitdepth import narrow8
from s08_ratiocompress import ARMS, slope, pair_ratios

STACK = "109MSDCF"
DF = 0.01
SEED = 115_09


def spectra(cube, g, rn_e, crop, rb, mid, s_fixed=None):
    """Band-mean P_sig / P_noise per arm.  s_fixed pins the calibration."""
    if s_fixed is None:
        s0, _, _ = L.calibrate_s(cube, L.focus_fields(cube, g, rn_e)[1])
    else:
        s0 = s_fixed
    sp = L.split_channel(cube, g, rn_e, s0, crop, want=ARMS)
    sig, noi = {}, {}
    for a in ARMS:
        st = L.split_stats(rb, *sp[a])
        sig[a] = float(np.mean(np.maximum(st[0][mid], 0)))
        noi[a] = float(np.mean(np.maximum(st[1][mid], 0)))
    return sig, noi, s0


def report(tag, sig, noi, s0, r_true, sig0, noi0):
    b, _ = slope(r_true, pair_ratios(sig, noi, 0.0)[0])
    ds = float(np.median([sig[a] / max(sig0[a], 1e-30) for a in ARMS]))
    dn = float(np.median([noi[a] / max(noi0[a], 1e-30) for a in ARMS]))
    print(f"  {tag:34s} s={s0:.4f}  beta={b:+7.4f}  "
          f"P_sig x{ds:5.3f}  P_noise x{dn:6.3f}")
    return dict(beta=b, s=s0, dP_sig=ds, dP_noise=dn)


def main():
    banner("s09 -- is the planted narrowing a noise floor, or something else?")
    cube, g, rn_e, B = load_detail(STACK)
    crop = L.crop_fn(L.PAD, B)
    rb = L.RadialBins(B, DF)
    mid = rb.band_mask(*L.MIDBAND)

    sig0, noi0, s_int = spectra(cube, g, rn_e, crop, rb, mid)
    r_true, _ = pair_ratios(sig0, noi0, 0.0)
    res = {"stack": STACK, "s_intact": s_int}
    print()
    res["intact"] = report("intact (reference)", sig0, noi0, s_int,
                           r_true, sig0, noi0)

    # ---- the perturbations, all at matched power --------------------------
    nar = narrow8(cube)
    err = nar - cube                      # the true quantisation error field
    p_err = float(np.mean(err.astype(np.float64) ** 2))
    rng = np.random.default_rng(SEED)
    dither = cube + rng.normal(0.0, np.sqrt(p_err),
                               size=cube.shape).astype(np.float32)
    p_dit = float(np.mean((dither - cube).astype(np.float64) ** 2))
    print(f"\n  perturbation power   quantisation {p_err:.4g}   "
          f"matched dither {p_dit:.4g}   ratio {p_dit/p_err:.4f}")
    assert abs(p_dit / p_err - 1.0) < 0.02, "dither power is not matched"

    # correlation of the perturbation across the two split halves, measured
    # directly on the error field rather than inferred from the arms
    ha, hb = err[0::2], err[1::2]
    n = min(len(ha), len(hb))
    ha, hb = ha[:n].ravel(), hb[:n].ravel()
    r_q = float(np.corrcoef(ha, hb)[0, 1])
    da = (dither - cube)[0::2][:n].ravel()
    db = (dither - cube)[1::2][:n].ravel()
    r_d = float(np.corrcoef(da, db)[0, 1])
    print(f"  cross-half correlation of the perturbation:")
    print(f"     quantisation error  r = {r_q:+.4f}")
    print(f"     matched dither      r = {r_d:+.4f}   (independent by "
          f"construction)")
    res["p_err"] = p_err
    res["corr_quant"] = r_q
    res["corr_dither"] = r_d

    print()
    res["narrowed_free"] = report("narrowed, s free  (H1 + H2)", *spectra(
        nar, g, rn_e, crop, rb, mid), r_true, sig0, noi0)
    res["narrowed_pinned"] = report("narrowed, s pinned to intact  (H2)", *spectra(
        nar, g, rn_e, crop, rb, mid, s_fixed=s_int), r_true, sig0, noi0)
    res["dither_pinned"] = report("matched dither, s pinned  (null)", *spectra(
        dither, g, rn_e, crop, rb, mid, s_fixed=s_int), r_true, sig0, noi0)

    # ---- verdict ----------------------------------------------------------
    print("\n  VERDICT")
    h1 = abs(res["narrowed_free"]["beta"] - res["narrowed_pinned"]["beta"])
    print(f"     H1 calibration confound: pinning s moves beta by {h1:.4f}")
    qs = res["narrowed_pinned"]["dP_sig"]
    ds = res["dither_pinned"]["dP_sig"]
    print(f"     H2 correlated error:     at IDENTICAL perturbation power,")
    print(f"        quantisation raises P_sig x{qs:.3f} but matched random "
          f"dither x{ds:.3f}")
    print(f"        -> quantisation fabricates {100*(qs/ds-1):+.1f}% more "
          f"'signal' than random noise of the same power")
    qn = res["narrowed_pinned"]["dP_noise"]
    dn = res["dither_pinned"]["dP_noise"]
    print(f"        and raises P_noise x{qn:.3f} vs dither x{dn:.3f}")
    verdict = ("H2 CONFIRMED" if qs > ds * 1.05 else "H2 NOT SUPPORTED")
    print(f"     {verdict}")
    res["verdict"] = verdict

    json.dump(res, open(os.path.join(L.OUT, "s09_quanterror.json"), "w"),
              indent=2)
    print("\n  -> s09_quanterror.json")


if __name__ == "__main__":
    main()
