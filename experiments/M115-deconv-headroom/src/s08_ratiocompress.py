r"""M115 -- s08: does a common noise floor compress an arm-vs-arm ratio toward 1?

ORCH's correction to the PIL notice adds, adjacent to two numbers I measured, a
claim I did NOT measure:

    "small-over-large ratios compress toward 1 -- they fail *toward* a clean
     null, the hardest error here to catch, because nobody re-examines an arm
     that showed no effect."

That is ARGUED, and it implicates M115 directly: my headline IS a ratio near 1
reporting a null (R_SNR(WIENER)/R_SNR(GATE) = 1.0014 +/- 0.0184).  If the claim
holds in the form stated, my null is exactly the shape an artefact would take.
Rule 12 applies to ORCH.  So: measure it.

DESIGN

A band SNR in this instrument is a power ratio, SNR = P_sig / P_noise.  A common
additive floor q -- which is what quantisation, read noise, or any shared
degradation imposes -- sends P_noise -> P_noise + q.  The ratio between two arms
therefore factorises exactly:

    r(q) = SNR_A/SNR_B = (P_sig_A / P_sig_B) * ((P_noise_B + q) / (P_noise_A + q))
           \___________/   \_________________________________________________/
            SIGNAL factor                  NOISE factor
            (untouched by q)               (-> 1 as q -> inf)

So the analytic prediction is that compression is PARTIAL and SELECTIVE: it acts
only on the noise factor.  A ratio whose two arms differ in noise collapses
toward 1; a ratio whose arms differ in SIGNAL does not compress at all.  Whether
that matters for M115 depends on which factor carries my headline -- which is a
measurement, not an argument.

THREE THINGS ARE RUN, IN THIS ORDER, AND THE MIDDLE ONE IS THE POINT

  NULL          q = 0.  The compression slope must read exactly 1.000.  A slope
                estimator that always returns 1 would pass this perfectly, which
                is why the null alone proves nothing (see AGENTS.md rule 12 and
                ORCH's CA-metric failure).

  POSITIVE      a dose sweep in q.  The slope must FALL MONOTONICALLY.  This is
  CONTROL       what licenses reading the measured point at all: it shows the
                statistic can express compression when compression is present,
                with the right sign.

  MEASUREMENT   the real planted PIL narrowing, from negctl_bitdepth.py, run
                through the identical statistic.  Its slope is then compared
                against the dose the narrowing actually delivers (q_eff, read
                off the measured noise-power inflation) -- an internal
                consistency check that ties the plant to the sweep.

The slope is fit in log space over ALL ORDERED arm pairs (i != j).  That set is
symmetric under inversion, so log r is symmetric about 0 and the intercept is
identically 0; the fit is therefore through the origin and beta is the clean
compression factor.  beta = 1 means no compression, beta = 0 means total
collapse to 1.
"""
import os, sys, json, itertools
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import load_detail, banner
from negctl_bitdepth import narrow8

STACK = "109MSDCF"
DF = 0.01
ARMS = ["BEST1", "FRAME*", "GATE", "MEAN", "MF", "WIENER", "WIENER_UNG"]


def slope(rt, rn):
    """Compression factor beta: log(r_measured) = beta * log(r_true).

    Fit through the origin over all ordered pairs.  beta==1 -> no compression,
    beta<1 -> compression toward 1, beta>1 -> expansion away from 1.
    """
    x = np.log(np.asarray(rt, float))
    y = np.log(np.asarray(rn, float))
    ok = np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 1e-12)
    x, y = x[ok], y[ok]
    return float(np.sum(x * y) / np.sum(x * x)), int(x.size)


def pair_ratios(sig, noi, q=0.0):
    """All ordered-pair band-SNR ratios at common additive noise floor q."""
    out, keys = [], []
    for a, b in itertools.permutations(ARMS, 2):
        ra = (sig[a] / (noi[a] + q)) / (sig[b] / (noi[b] + q))
        out.append(ra)
        keys.append(f"{a}/{b}")
    return np.array(out), keys


def factorise(sig, noi, q=0.0):
    """Split each ordered-pair ratio into its signal and noise factors."""
    s, n = [], []
    for a, b in itertools.permutations(ARMS, 2):
        s.append(sig[a] / sig[b])
        n.append((noi[b] + q) / (noi[a] + q))
    return np.array(s), np.array(n)


def measure(cube, g, rn_e, crop, rb, mid, tag):
    """Band-mean P_sig and P_noise per arm, through the split-stack channel."""
    s0, _, _ = L.calibrate_s(cube, L.focus_fields(cube, g, rn_e)[1])
    sp = L.split_channel(cube, g, rn_e, s0, crop, want=ARMS)
    sig, noi = {}, {}
    for a in ARMS:
        st = L.split_stats(rb, *sp[a])
        sig[a] = float(np.mean(np.maximum(st[0][mid], 0)))
        noi[a] = float(np.mean(np.maximum(st[1][mid], 0)))
    print(f"  [{tag}] s={s0:.4f}")
    for a in ARMS:
        print(f"     {a:12s} P_sig {sig[a]:12.5g}  P_noise {noi[a]:12.5g}  "
              f"SNR {sig[a]/max(noi[a],1e-30):9.3f}")
    return sig, noi, s0


def main():
    banner("s08 -- does a common noise floor compress an arm ratio toward 1?")
    cube, g, rn_e, B = load_detail(STACK)
    crop = L.crop_fn(L.PAD, B)
    rb = L.RadialBins(B, DF)
    mid = rb.band_mask(*L.MIDBAND)

    sig, noi, s_int = measure(cube, g, rn_e, crop, rb, mid, "intact")
    r_true, keys = pair_ratios(sig, noi, 0.0)
    print(f"\n  {len(keys)} ordered pairs; true log-ratio spread "
          f"[{np.log(r_true).min():+.3f}, {np.log(r_true).max():+.3f}]")

    res = {"stack": STACK, "arms": ARMS, "s_intact": s_int,
           "P_sig": sig, "P_noise": noi}

    # ---- NULL -------------------------------------------------------------
    b0, n0 = slope(r_true, r_true)
    print(f"\n  NULL          q=0  ->  beta = {b0:.6f}  ({n0} pairs)")
    assert abs(b0 - 1.0) < 1e-9, "slope estimator is not unbiased at q=0"
    res["null_beta"] = b0

    # ---- POSITIVE CONTROL: dose sweep in q --------------------------------
    print("\n  POSITIVE CONTROL -- common additive noise floor, dose sweep")
    print("  (a slope that cannot fall here cannot detect compression at all)")
    nref = float(np.median([noi[a] for a in ARMS]))
    doses, betas, sfac, nfac = [], [], [], []
    for mult in [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 32.0, 128.0]:
        q = mult * nref
        rq, _ = pair_ratios(sig, noi, q)
        b, _ = slope(r_true, rq)
        sf, nf = factorise(sig, noi, q)
        bs, _ = slope(r_true, sf)
        bn, _ = slope(r_true, nf)
        doses.append(mult); betas.append(b); sfac.append(bs); nfac.append(bn)
        print(f"     q = {mult:6.2f} x median P_noise   beta = {b:7.4f}   "
              f"[signal factor {bs:6.4f} + noise factor {bn:7.4f}]")
    mono = all(betas[i + 1] <= betas[i] + 1e-9 for i in range(len(betas) - 1))
    print(f"\n     monotone non-increasing in dose: {mono}   "
          f"-> {'PASS' if mono else 'FAIL'}")
    print(f"     beta falls {betas[0]:.4f} -> {betas[-1]:.4f}; the signal factor "
          f"is INVARIANT at {sfac[-1]:.4f}")
    assert mono, "positive control failed: slope is not monotone in dose"
    assert betas[-1] < betas[0] - 0.05, "positive control inert: slope never moved"
    res["sweep"] = dict(dose=doses, beta=betas, beta_signal=sfac, beta_noise=nfac)

    # asymptote: where does the ratio actually land?
    sf_inf, _ = factorise(sig, noi, 1e30)
    b_inf, _ = slope(r_true, sf_inf)
    print(f"\n     as q -> inf the ratio tends to the SIGNAL ratio, not to 1:")
    print(f"     beta(q->inf) = {b_inf:.4f}, and the residual signal-ratio "
          f"spread is [{np.log(sf_inf).min():+.3f}, {np.log(sf_inf).max():+.3f}]")
    res["beta_asymptote"] = b_inf

    # ---- MEASUREMENT: the real planted narrowing --------------------------
    print("\n  MEASUREMENT -- the actual planted PIL narrowing")
    nar = narrow8(cube)
    assert np.unique(nar).size <= 256, "the plant did not land"
    print(f"  distinct levels: intact {np.unique(cube).size} -> "
          f"narrowed {np.unique(nar).size}")
    sig_n, noi_n, s_nar = measure(nar, g, rn_e, crop, rb, mid, "narrowed")
    r_nar, _ = pair_ratios(sig_n, noi_n, 0.0)
    b_nar, _ = slope(r_true, r_nar)
    infl = float(np.median([noi_n[a] / max(noi[a], 1e-30) for a in ARMS]))
    q_eff = (infl - 1.0) * nref
    rq, _ = pair_ratios(sig, noi, q_eff)
    b_pred, _ = slope(r_true, rq)
    print(f"\n     measured beta under narrowing      = {b_nar:.4f}")
    print(f"     narrowing inflates P_noise by        {infl:.2f}x "
          f"(=> q_eff = {infl-1:.2f} x median P_noise)")
    print(f"     beta predicted by the sweep at q_eff = {b_pred:.4f}")
    print(f"     s self-calibration {s_int:.4f} -> {s_nar:.4f} "
          f"({100*(s_nar/s_int-1):+.1f}%)")
    res.update(beta_narrowed=b_nar, noise_inflation=infl,
               beta_predicted_at_qeff=b_pred, s_narrowed=s_nar,
               pairs={k: [float(a), float(b)] for k, a, b in
                      zip(keys, r_true, r_nar)})

    # ---- what this says about M115's own headline -------------------------
    print("\n  WHAT THIS SAYS ABOUT THE M115 HEADLINE")
    hs = sig["WIENER"] / sig["GATE"]
    hn = noi["GATE"] / noi["WIENER"]
    print(f"     R_SNR(WIENER)/R_SNR(GATE) = {hs*hn:.4f}")
    print(f"       = signal factor {hs:.4f}  x  noise factor {hn:.4f}")
    print(f"     Compression acts ONLY on the noise factor.  The most it can do")
    print(f"     to this ratio is drive it to the signal factor {hs:.4f}.")
    res["headline"] = dict(ratio=hs * hn, signal_factor=hs, noise_factor=hn)

    json.dump(res, open(os.path.join(L.OUT, "s08_ratiocompress.json"), "w"),
              indent=2)
    print("\n  -> s08_ratiocompress.json")


if __name__ == "__main__":
    main()
