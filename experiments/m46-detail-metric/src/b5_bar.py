"""M46 b5 -- THE ASSIGNED BAR, scored for the two statistics b3 found.

b2 scored the bar for the incumbent corpus and every metric failed the flat
half INCLUDING the oracle, which is the pre-declared signature (PREREGISTRATION
Sec 3) of a broken GATE rather than broken metrics.  b3 then found two statistics
that separate blur from smoothing:

    sigpow_fsig = FRC(f_sig) * ringpow(f_sig)     -- shippable, needs the PAIR
    oracle_mtf                                    -- needs the truth, control only

This script does two things b2 could not, because b2 is frozen and predates them:

  (1) Scores the ASSIGNED bar -- "recovery >= +0.9 on detail AND <= +0.3 on
      flat" -- for these two, in the SAME recovery_ratio arithmetic (`rec_lin`,
      imported unchanged) and against the SAME plant models and sources, so the
      row drops straight into b2's table.

  (2) Scores the REPAIRED bar.  b2 MEASURED why the assigned one cannot be met:
      the observed "flat" ROI is not featureless -- its rule-10 detector reads
      6.43, and fact 469 already measured ~99% of such an ROI's variance as
      residual scene -- so blurring it destroys real content and an HONEST
      metric must fire.  The repaired bar puts the second half on a source that
      IS featureless by construction and on the operation that actually worries
      the project:

        R1  recovery >= +0.9   on S_detail under an optical blur
        R2  |response| <= 0.3  on S_null, a CONSTANT latent: no detail exists,
                               so any reading is a false alarm
        R3  |response to SMOOTH-ONLY| <= 0.3 relative to its blur response
                               on S_detail  -- i.e. b3's S >= 0.77
        R4  recovery >= +0.9   under PM_C, a post-filter on the delivered
                               image, which is the failure mode being claimed
                               against

      R2 is the honest replacement for the assigned flat half; R3 and R4 are
      strictly HARDER than anything the assigned bar asked for.  The repair is
      not a relaxation and the deviation is declared, not slipped in.

RULE 20 -- WHAT WOULD MAKE THIS FAIL, written before the run:
  * sigpow_fsig fails R1 if the FRC term saturates: on a very clean source
    FRC ~ 1 everywhere, sigpow -> ringpow, and ringpow is an absolute-power
    statistic that b3 measured at S = 0.587 on S_detail.  If the recovery on
    S_detail comes in below +0.9 this fails and I report it.
  * sigpow_fsig fails R2 if the fixed pattern is itself attenuated by the
    plant -- which is exactly what PM_B does.  PM_B blurs (L+P) together, so on
    S_null the ONLY thing to lose is the pattern, and sigpow SHOULD fire.  If it
    does, the metric is a pattern detector on featureless ground and R2 fails
    under PM_B.  This is a real and likely failure and it is registered here
    BEFORE the run.
  * Both are reachable.  Neither is a tautology.

Rule 15: b2 is frozen and is not touched.  Rule 24: the recovery arithmetic, the
sources, the noise level, rho, the ring grid and f_sig are all IMPORTED from the
frozen artifacts rather than re-chosen here.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m46lib as M                                                    # noqa: E402
import b3_separation as B3                                            # noqa: E402

REPS = 8
SEED_FPN = 4242


def metrics_pair(y1, y2, latent):
    return B3.all_metrics(y1, y2, latent)


def bank_model(latent, fpn, sigma, sb, model, reps=REPS, base_seed=0):
    """A bank of realisations under one plant model, two independent captures
    per realisation.  PM_C's post-filter is applied to BOTH captures with the
    same kernel, because a merge delivers one filtered image per capture."""
    acc = {}
    for r in range(reps):
        rng = np.random.default_rng(base_seed + 1000 * r + 7)
        y1 = M.realise(latent, fpn, sigma, sb, model, rng)
        y2 = M.realise(latent, fpn, sigma, sb, model, rng)
        for k, v in metrics_pair(y1, y2, latent).items():
            acc.setdefault(k, []).append(v)
    out = {}
    for k, vs in acc.items():
        good = [v for v in vs if v is not None]
        out[k] = float(np.mean(good)) if len(good) == len(vs) else None
    return out


def truth_pair(latent, fpn, sb, model):
    """Truth channel: the NOISELESS image under the same model, measured with
    the same statistics.  For a correlation term against a noiseless duplicate
    the FRC is 1 by construction, which is stated rather than hidden -- it is
    why the truth channel for sigpow reduces to its ring-power term, and why
    that term is the right denominator: it is the signal power actually
    delivered."""
    t = M.truth(latent, fpn, sb, model)
    return metrics_pair(t, t, latent)


KEYS = ["frc2_at_fsig", "hp_sd", "p_ratio", "mean_grad", "ringpow",
        "sigpow_fsig", "oracle_fsc", "oracle_mtf"]


def main():
    t0 = time.time()
    print("=" * 78)
    print("M46 b5 -- the assigned bar and the repaired bar, for b3's statistics")
    print("=" * 78)

    with open(os.path.join(M.OUT, "b1_results.json")) as fh:
        b1 = json.load(fh)
    z = np.load(os.path.join(M.OUT, "b1_merges.npz"))
    pad = 32
    det = z["d112"][pad:-pad, pad:-pad].astype(np.float32)
    flt = z["f112"][pad:-pad, pad:-pad].astype(np.float32)
    g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]
    lvl_d, lvl_f = float(np.median(det)), float(np.median(flt))
    sig_d = float(np.sqrt(M.noise_var_dn(lvl_d, g, rn_e)))
    sig_f = float(np.sqrt(M.noise_var_dn(lvl_f, g, rn_e)))
    ne_d, ne_f = b1["n_eff"]["112_detail"], b1["n_eff"]["112_flat"]
    null = np.full(flt.shape, lvl_f, dtype=np.float32)
    syn = M.synth_broadband(det.shape[0], 4242) * float(det.std())

    SRC = {"S_null": (null, sig_f, ne_f),
           "S_flat": (flt, sig_f, ne_f),
           "S_detail": (det, sig_d, ne_d),
           "S_synth": (syn, sig_d, ne_d)}
    rho = 0.3094
    SB = 2.0

    res = dict(rho=rho, sb=SB, assigned={}, repaired={})

    # ------------------------------------------------ 1. the assigned bar
    print("\n1. THE ASSIGNED BAR, verbatim:")
    print('   "recovery >= +0.9 on detail AND <= +0.3 on flat"')
    print(f"   Planted optical blur sb = {SB} px, merged noise level, rho = {rho:.4f}.")
    print("   Recovery ratio is `rec_lin` imported unchanged from b2.")
    for model in ("PM_A", "PM_B", "PM_C"):
        print(f"\n   {model}")
        print("      metric            rec(detail)   rec(flat)    assigned bar")
        rows = {}
        recs = {}
        for sname in ("S_detail", "S_flat"):
            lat, sfr, ne = SRC[sname]
            sigma = sfr / np.sqrt(ne)
            fpn = M.make_fpn(lat.shape, SEED_FPN, np.sqrt(rho) * sfr)
            m0 = bank_model(lat, fpn, sigma, 0.0, model, base_seed=1)
            ms = bank_model(lat, fpn, sigma, SB, model, base_seed=1)
            p0 = truth_pair(lat, fpn, 0.0, model)
            ps = truth_pair(lat, fpn, SB, model)
            recs[sname] = {k: M.rec_lin(m0.get(k), ms.get(k), p0.get(k), ps.get(k))
                           for k in KEYS}
        for k in KEYS:
            rd, rf = recs["S_detail"][k], recs["S_flat"][k]
            ok = (rd is not None and rf is not None and rd >= 0.9 and abs(rf) <= 0.3)
            print(f"      {k:<16s} {M.fmt(rd, 9, 4)}   {M.fmt(rf, 9, 4)}    "
                  + ("PASS" if ok else
                     "undefined" if rd is None or rf is None else "FAIL"))
            rows[k] = dict(detail=rd, flat=rf, pass_=ok)
        res["assigned"][model] = rows

    # ------------------------------------------------ 2. the repaired bar
    print("\n" + "=" * 78)
    print("2. THE REPAIRED BAR.  Second half moved from the observed flat ROI")
    print("   (rule-10 detector 6.43 -- it HAS content, so an honest metric must")
    print("   fire on it) to S_null, a constant latent with no content at all.")
    print("   R1 rec(S_detail, PM_A blur) >= +0.90")
    print("   R2 |rec(S_null)|            <= 0.30   -- false alarm on nothing")
    print("   R3 b3 separation S          >= 0.77   -- blur vs smoothing")
    print("   R4 rec(S_detail, PM_C)      >= +0.90  -- sees a post-filter")
    print("=" * 78)

    rep = {}
    for k in KEYS:
        rep[k] = {}
    for model in ("PM_A", "PM_B", "PM_C"):
        for sname in ("S_null", "S_detail"):
            lat, sfr, ne = SRC[sname]
            sigma = sfr / np.sqrt(ne)
            fpn = M.make_fpn(lat.shape, SEED_FPN, np.sqrt(rho) * sfr)
            m0 = bank_model(lat, fpn, sigma, 0.0, model, base_seed=1)
            ms = bank_model(lat, fpn, sigma, SB, model, base_seed=1)
            p0 = truth_pair(lat, fpn, 0.0, model)
            ps = truth_pair(lat, fpn, SB, model)
            for k in KEYS:
                rep[k][f"{model}/{sname}"] = M.rec_lin(m0.get(k), ms.get(k),
                                                       p0.get(k), ps.get(k))
    res["repaired_recoveries"] = rep

    with open(os.path.join(M.OUT, "b3_results.json")) as fh:
        b3 = json.load(fh)
    Ssep = {k: b3["per_source"]["S_detail"]["rows"].get(k, {}).get("S") for k in KEYS}
    Snull = {k: b3["per_source"]["S_null"]["rows"].get(k, {}).get("S") for k in KEYS}

    print("\n   metric              R1 rec_det   R2 |rec_null|   R3 sep S   "
          "R4 rec_PM_C   VERDICT")
    verdict = {}
    for k in KEYS:
        r1 = rep[k]["PM_A/S_detail"]
        r2 = rep[k]["PM_A/S_null"]
        r3 = Ssep.get(k)
        r4 = rep[k]["PM_C/S_detail"]
        ok = (r1 is not None and r1 >= 0.90
              and r2 is not None and abs(r2) <= 0.30
              and r3 is not None and r3 >= 0.77
              and r4 is not None and r4 >= 0.90)
        why = []
        if r1 is None or r1 < 0.90:
            why.append("R1")
        if r2 is None or abs(r2) > 0.30:
            why.append("R2")
        if r3 is None or r3 < 0.77:
            why.append("R3")
        if r4 is None or r4 < 0.90:
            why.append("R4")
        print(f"   {k:<18s} {M.fmt(r1,9,4)}   {M.fmt(None if r2 is None else abs(r2),11,4)}"
              f"   {'   --  ' if r3 is None else f'{r3:7.3f}'}   {M.fmt(r4,9,4)}   "
              + ("PASS" if ok else "fails " + ",".join(why)))
        verdict[k] = dict(R1=r1, R2=r2, R3=r3, R4=r4, pass_=ok, fails=why)
    res["repaired_verdict"] = verdict

    # -------------------------------------- 3. PM_B, the registered failure
    print("\n3. THE REGISTERED FAILURE MODE.  Under PM_B the plant blurs (L+P)")
    print("   TOGETHER, so on S_null the only thing that can be lost is the")
    print("   fixed pattern, and a pattern detector will fire on nothing.")
    print("   metric              rec(PM_B, S_null)   rec(PM_C, S_null)")
    for k in KEYS:
        print(f"   {k:<18s} {M.fmt(rep[k]['PM_B/S_null'],13,4)}       "
              f"{M.fmt(rep[k]['PM_C/S_null'],13,4)}")

    with open(os.path.join(M.OUT, "b5_results.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/b5_results.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
