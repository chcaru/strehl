"""M57 S1 -- the property battery, on plants.

Decides PR1 (monotonicity), PR2 (photometric gain), PR3 (separation at matched
cost WITH its null), PR7 (planted wrong answer), PR8 (real defocus / pillbox),
PR10 (pedestal floor).  PR4/PR5/PR6 need real frames or a drift plant and are
s3/s2.

The plant is M46's, deliberately: latent = the merged 112MSDCF detail ROI from
`m46-detail-metric/out/b1_merges.npz`, rho and n_eff from `b1_results.json`.
Using the same plant is what makes PR1 a like-for-like re-run of fact 703
rather than a new experiment that happens to disagree.

RULE 20 / RULE 13 -- what could make each gate FAIL, checked before running:
  G0   the ring machinery: fed a KNOWN Gaussian blur on a noiseless pair, dsig
       must return that sigma.  It fails if the ring geometry, the |H|^2 power
       convention or the sign is wrong.  A wrong answer is planted (0.20 px
       read against a 0.10 px truth) so the gate demonstrably rejects.
  PR2  fails if any candidate's exponent is non-zero.  sigpow is carried as the
       positive control and MUST read 2.0 / 1.0 (facts 701, 704), otherwise the
       harness is broken.
  PR1  fails if a candidate's sign inverts.  sigpow MUST invert (fact 703),
       otherwise the ladder is not discriminating and PR1 is void.
  PR3  fails if d_blur is not >= 5 se from zero, or d_smooth is >= 3 se from
       zero toward "more detail".
  PR10 fails if the pedestal makes dsig depart from truth by 2x below 0.5 px.

Rule 9: the flat ROI is run for every cell, and it is run FIRST.
Rule 39: every d carries its null and that null's standard error.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m57lib as K  # noqa: E402

N = 512
REPS = 8
SEED_FPN = 20260823


def bank_pairs(draw, reps, base_seed):
    """A list of (pair1, pair2) RingStats for `reps` independent realisations."""
    out = []
    for r in range(reps):
        out.append(draw(base_seed + 1000 * r + 7))
    return out


def agg(vals):
    v = np.array([x for x in vals if np.isfinite(x)], dtype=float)
    if len(v) == 0:
        return np.nan, np.nan, 0
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else np.nan, len(v)


def main():
    t0 = time.time()
    np.set_printoptions(suppress=True)
    m46out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "m46-detail-metric", "out")
    z = np.load(os.path.join(m46out, "b1_merges.npz"))
    b1 = json.load(open(os.path.join(m46out, "b1_results.json")))
    pad = 32
    src = {"flat": z["f112"][pad:-pad, pad:-pad].astype(np.float32),   # rule 9: FIRST
           "detail": z["d112"][pad:-pad, pad:-pad].astype(np.float32)}
    g = b1["rois"]["g"]
    rn_e = b1["rois"]["rn_e"]
    ne = {"detail": b1["n_eff"]["112_detail"], "flat": b1["n_eff"]["112_flat"]}
    rho = b1["twocap"]["flat"]["at_fsig"] / (1 - b1["twocap"]["flat"]["at_fsig"]) / ne["flat"]

    res = {"rho": rho, "band": [K.F_LO, K.F_HI], "n": N, "nbin": K.NBIN,
           "reps": REPS, "profile": {"g_iso500": K.gain_dn_per_e(500),
                                     "rn_e_high": K.RN_E_HIGH}}
    print("=" * 78)
    print("M57 S1 -- property battery for spectral-SHAPE detail metrics")
    print("=" * 78)
    print(f"  plant latent  = M46 b1 merged 112MSDCF ROIs, {N}x{N}")
    print(f"  rho {rho:.4f} (fact 610, DERIVED from b1, not re-picked)   "
          f"g {g:.5f} DN/e-   rn_e {rn_e} e- (m41lib value, frozen)")
    print(f"  band [{K.F_LO}, {K.F_HI}] cyc/px, nbin {K.NBIN}, fixed by PR11")
    ridx = K.band_index(K.ring_grid(N)[1])
    print(f"  rings in band: {len(ridx)}  "
          f"centres {K.ring_grid(N)[1][ridx][0]:.5f} .. {K.ring_grid(N)[1][ridx][-1]:.5f}")

    lvl = {k: float(np.median(v)) for k, v in src.items()}
    sig1 = {k: float(np.sqrt(K.M.noise_var_dn(lvl[k], g, rn_e))) for k in src}
    sigma = {k: sig1[k] / np.sqrt(ne[k]) for k in src}
    fpn = {k: K.M.make_fpn(src[k].shape, SEED_FPN, np.sqrt(rho) * sig1[k]) for k in src}
    for k in ("flat", "detail"):
        print(f"  {k:<7s} level {lvl[k]:8.2f} DN   single-frame sigma {sig1[k]:6.3f}   "
              f"merged sigma {sigma[k]:6.3f}   n_eff {ne[k]:.3f}")

    # ---------------------------------------------------------------- G0
    print("\n" + "=" * 78)
    print("G0 -- does the instrument recover a KNOWN blur, and can it be WRONG?")
    print("=" * 78)
    print("  Noiseless pair, no FPN.  Truth is the planted Gaussian sigma exactly.")
    print("   planted sb   dsig px    slope px^2   se_px(jack)   rel err")
    g0 = {}
    lat = src["detail"]
    rs_ref = K.RingStats(lat, lat)
    for sb in (0.0, 0.02, 0.05, 0.10, 0.20, 0.50, 1.0, 2.0):
        bl = K.M.blur(lat, sb)
        rs_t = K.RingStats(bl, bl)
        d = K.dsig(rs_ref, rs_t)
        rel = (d["px"] - sb) / sb if sb > 0 else np.nan
        print(f"   {sb:10.3f}   {d['px']:+8.5f}   {d['slope']:+10.6f}   "
              f"{d['se_px']:11.2e}   {K.fmt(rel, 7, 4)}")
        g0[f"{sb}"] = d
    res["g0"] = g0
    # planted wrong answer (rule 39): read 0.10 against a claim of 0.20
    d10 = g0["0.1"]
    print(f"\n  RULE 39 planted wrong answer: truth 0.10000 px, measured "
          f"{d10['px']:.5f} px, se {d10['se_px']:.2e}")
    for claim in (0.0, 0.20):
        z_ = abs(d10["px"] - claim) / max(d10["se_px"], 1e-12)
        print(f"    claim sigma = {claim:.2f} px -> rejected at {z_:.1f} sigma"
              if z_ > 3 else f"    claim sigma = {claim:.2f} px -> NOT REJECTED ({z_:.1f}) -- G0 FAILS")
    print("  Geometry cross-check against the reference `rings()` implementation:")
    r_ref = K.rings(N, K.NBIN)
    lab, f_fast, _, nr = K.ring_grid(N, K.NBIN)
    ok_geom = (len(r_ref) == nr) and np.allclose([c for (_, _, c) in r_ref], f_fast)
    cnt_ok = np.allclose([c for (_, c, _) in r_ref], K.ring_grid(N)[2].sum(1))
    print(f"    rings {len(r_ref)} vs {nr}, centres match {ok_geom}, counts match {cnt_ok}")
    res["geometry_ok"] = bool(ok_geom and cnt_ok)

    # ---------------------------------------------------------------- PR2
    print("\n" + "=" * 78)
    print("PR2 -- PHOTOMETRIC GAIN.  d log|m| / d log lambda, measured.")
    print("=" * 78)
    print("  sigpow is the POSITIVE CONTROL: facts 701/704 require 2.000 (both)")
    print("  and 1.000 (one input).  If it does not read that, the harness is bad.")
    pr2 = {}
    for roi in ("flat", "detail"):
        rng = np.random.default_rng(4242)
        a = src[roi] + fpn[roi] + rng.standard_normal(src[roi].shape).astype(np.float32) * sigma[roi]
        b = src[roi] + fpn[roi] + rng.standard_normal(src[roi].shape).astype(np.float32) * sigma[roi]
        a2 = K.M.blur(src[roi], 0.05) + fpn[roi] + rng.standard_normal(src[roi].shape).astype(np.float32) * sigma[roi]
        b2 = K.M.blur(src[roi], 0.05) + fpn[roi] + rng.standard_normal(src[roi].shape).astype(np.float32) * sigma[roi]
        rs1 = K.RingStats(a, b)
        rs2 = K.RingStats(a2, b2)
        base = dict(sigpow=K.sigpow(rs2), dsig=K.dsig(rs1, rs2, jack=False)["px"],
                    rmtf2=K.rmtf2(rs1, rs2), ccent=K.ccent(rs2))
        print(f"\n  ROI {roi}   baseline: sigpow {base['sigpow']:.6e}  "
              f"dsig {base['dsig']:+.6f} px  rmtf2 {base['rmtf2']:.6f}  "
              f"ccent {base['ccent']:.6f}")
        print("     mode              lam    sigpow exp   dsig exp    rmtf2 exp   ccent exp")
        for mode in ("both", "one"):
            for lam in (1.30, 3.0):
                if mode == "both":
                    A2, B2 = lam * a2, lam * b2
                else:
                    A2, B2 = lam * a2, b2
                rs2s = K.RingStats(A2, B2)
                cur = dict(sigpow=K.sigpow(rs2s), dsig=K.dsig(rs1, rs2s, jack=False)["px"],
                           rmtf2=K.rmtf2(rs1, rs2s), ccent=K.ccent(rs2s))
                row = {}
                for kk in ("sigpow", "dsig", "rmtf2", "ccent"):
                    b0, c0 = base[kk], cur[kk]
                    if kk in ("dsig",):
                        # additive-scale statistic: report the ABSOLUTE move, in px
                        row[kk] = c0 - b0
                    else:
                        row[kk] = (np.log(abs(c0)) - np.log(abs(b0))) / np.log(lam)
                print(f"     {mode:<8s} {lam:10.3f}   {row['sigpow']:10.6f}  "
                      f"{row['dsig']:+10.3e}*  {row['rmtf2']:10.6f}  {row['ccent']:10.6f}")
                pr2[f"{roi}_{mode}_{lam}"] = row
        print("     * dsig is in px, not a log ratio: the column is the ABSOLUTE "
              "move in px,\n       which is the quantity its decision rule is "
              "denominated in.")
    res["pr2"] = pr2

    # ---------------------------------------------------------------- PR3
    print("\n" + "=" * 78)
    print("PR3 -- SEPARATION AT MATCHED COST, with its null (rule 39).")
    print("=" * 78)
    print("  BLUR-ONLY vs SMOOTH-ONLY at matched hp_sd, k = sqrt(2).  No `S` is")
    print("  reported (fact 695): d_blur and d_smooth each with a standard error.")
    pr3 = {}
    for roi in ("flat", "detail"):
        s0 = src[roi]
        sg = sigma[roi]
        fp = fpn[roi]

        def draw(seed, sb=0.0, k=1.0):
            rng = np.random.default_rng(seed)
            n1 = rng.standard_normal(s0.shape).astype(np.float32) * (sg / k)
            n2 = rng.standard_normal(s0.shape).astype(np.float32) * (sg / k)
            base = K.M.blur(s0, sb) if sb > 0 else s0
            return base + fp + n1, base + fp + n2

        # match hp_sd of the k=sqrt2 smoothing with a blur width
        tgt = np.mean([K.M.hp_sd(draw(11 + 1000 * r, k=np.sqrt(2.0))[0]) for r in range(4)])
        lo, hi = 0.0, 2.0
        for _ in range(34):
            mid = 0.5 * (lo + hi)
            v = np.mean([K.M.hp_sd(draw(11 + 1000 * r, sb=mid)[0]) for r in range(4)])
            if v > tgt:
                lo = mid
            else:
                hi = mid
        sb_m = 0.5 * (lo + hi)
        print(f"\n  ROI {roi}:  matched blur sb = {sb_m:.5f} px against k = sqrt(2)")
        rows = {}
        for reps in (1, 2, 4, 8, 16, 32):
            db, ds, dn, k0b, k0s, k0n = [], [], [], [], [], []
            for r in range(reps):
                sd = 900 + 1000 * r
                a0, b0 = draw(sd)
                ab, bb = draw(sd, sb=sb_m)
                asm, bsm = draw(sd + 500_000, k=np.sqrt(2.0))
                an, bn = draw(sd + 700_000)          # NULL: identical config,
                rs0 = K.RingStats(a0, b0)            # only the noise draw differs
                db.append(K.dsig(rs0, K.RingStats(ab, bb), jack=False)["px"])
                ds.append(K.dsig(rs0, K.RingStats(asm, bsm), jack=False)["px"])
                dn.append(K.dsig(rs0, K.RingStats(an, bn), jack=False)["px"])
                v0 = K.sigpow(rs0)
                k0b.append((v0 - K.sigpow(K.RingStats(ab, bb))) / abs(v0))
                k0s.append((v0 - K.sigpow(K.RingStats(asm, bsm))) / abs(v0))
                k0n.append((v0 - K.sigpow(K.RingStats(an, bn))) / abs(v0))
            mb, sb_e, _ = agg(db)
            ms, ss_e, _ = agg(ds)
            mn, sn_e, _ = agg(dn)
            qb, qbe, _ = agg(k0b)
            qs, qse, _ = agg(k0s)
            qn, qne, _ = agg(k0n)
            if reps == 1:
                print("     reps   dsig d_blur px   dsig d_smooth px   dsig NULL px "
                      "   | sigpow d_blur   sigpow d_smooth  sigpow NULL")
            print(f"     {reps:4d}   {mb:+8.5f}+-{0 if not np.isfinite(sb_e) else sb_e:7.5f}  "
                  f"{ms:+8.5f}+-{0 if not np.isfinite(ss_e) else ss_e:7.5f}  "
                  f"{mn:+8.5f}+-{0 if not np.isfinite(sn_e) else sn_e:7.5f} | "
                  f"{qb:+9.5f}   {qs:+9.5f}   {qn:+9.5f}")
            rows[reps] = dict(d_blur=mb, se_blur=sb_e, d_smooth=ms, se_smooth=ss_e,
                              d_null=mn, se_null=sn_e, sig_blur=qb, sig_smooth=qs,
                              sig_null=qn)
        r32 = rows[32]
        zb = abs(r32["d_blur"]) / r32["se_blur"]
        zs = abs(r32["d_smooth"]) / r32["se_smooth"]
        zn = abs(r32["d_null"]) / r32["se_null"]
        print(f"     at 32 reps: |d_blur|/se = {zb:.1f},  |d_smooth|/se = {zs:.1f}, "
              f" |d_null|/se = {zn:.1f}")
        print(f"     leverage  |d_blur| / |d_smooth| = "
              f"{abs(r32['d_blur'])/max(abs(r32['d_smooth']),1e-12):.1f}x   "
              f"(sigpow: {abs(r32['sig_blur'])/max(abs(r32['sig_smooth']),1e-12):.1f}x)")
        pr3[roi] = dict(sb_matched=sb_m, rows=rows)
    res["pr3"] = pr3

    # ---------------------------------------------------------------- PR1
    print("\n" + "=" * 78)
    print("PR1 -- MONOTONICITY.  The fact-703 ladder: PM_M destroys resolution")
    print("       AND adds a fixed texture COMMON to both halves, amplitude")
    print("       solved so hp_sd returns to baseline.")
    print("=" * 78)
    pr1 = {}
    for roi in ("flat", "detail"):
        s0, sg, fp = src[roi], sigma[roi], fpn[roi]
        rngT = np.random.default_rng(31337)
        tex = rngT.standard_normal(s0.shape).astype(np.float32)
        tex = tex - K.M.blur(tex, 1.0)                # high-frequency, common
        tex /= tex.std()

        def draw_pm(seed, sb, amp):
            rng = np.random.default_rng(seed)
            base = K.M.blur(s0, sb) if sb > 0 else s0
            a = base + amp * tex + fp + rng.standard_normal(s0.shape).astype(np.float32) * sg
            b = base + amp * tex + fp + rng.standard_normal(s0.shape).astype(np.float32) * sg
            return a, b

        h0 = np.mean([K.M.hp_sd(draw_pm(77 + 1000 * r, 0.0, 0.0)[0]) for r in range(4)])
        print(f"\n  ROI {roi}:  baseline hp_sd = {h0:.4f} DN")
        print("      sb     fake amp    hp_sd    true MTF(f_sig)   sigpow/base   "
              "dsig px      rmtf2      ccent/base")
        rs_base = K.RingStats(*draw_pm(555, 0.0, 0.0))
        v0 = K.sigpow(rs_base)
        cc0 = K.ccent(rs_base)
        rows = {}
        for sb in (0.25, 0.50, 1.00, 2.00):
            lo, hi = 0.0, 400.0
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                v = np.mean([K.M.hp_sd(draw_pm(77 + 1000 * r, sb, mid)[0]) for r in range(4)])
                if v < h0:
                    lo = mid
                else:
                    hi = mid
            amp = 0.5 * (lo + hi)
            hh = np.mean([K.M.hp_sd(draw_pm(77 + 1000 * r, sb, amp)[0]) for r in range(4)])
            mtf = float(K.gauss_mtf(K.F_SIG, sb))
            dv, sv, cv, rv = [], [], [], []
            for r in range(REPS):
                rs_t = K.RingStats(*draw_pm(555 + 1000 * r, sb, amp))
                rs_b = K.RingStats(*draw_pm(555 + 1000 * r, 0.0, 0.0))
                dv.append(K.dsig(rs_b, rs_t, jack=False)["px"])
                sv.append(K.sigpow(rs_t) / K.sigpow(rs_b))
                cv.append(K.ccent(rs_t) / K.ccent(rs_b))
                rv.append(K.rmtf2(rs_b, rs_t))
            md, sd_ = agg(dv)[:2]
            print(f"    {sb:6.2f}  {amp:10.4f}  {hh:8.4f}   {mtf:12.6f}   "
                  f"{agg(sv)[0]:11.5f}   {md:+8.4f}   {agg(rv)[0]:9.5f}   "
                  f"{agg(cv)[0]:9.5f}")
            rows[f"{sb}"] = dict(amp=amp, hp_sd=hh, mtf=mtf, sigpow_ratio=agg(sv)[0],
                                 dsig=md, se_dsig=sd_, rmtf2=agg(rv)[0],
                                 ccent_ratio=agg(cv)[0])
        pr1[roi] = rows
        d = [rows[f"{s}"]["dsig"] for s in (0.25, 0.5, 1.0, 2.0)]
        sgn = [rows[f"{s}"]["sigpow_ratio"] for s in (0.25, 0.5, 1.0, 2.0)]
        print(f"    dsig monotone increasing? {all(d[i] < d[i+1] for i in range(3))}"
              f"   all same sign? {len(set(np.sign(d))) == 1}")
        print(f"    sigpow inverts (control MUST be True)? "
              f"{any(x > 1.0 for x in sgn) and any(x < 1.0 for x in sgn)}")
    res["pr1"] = pr1

    # ---------------------------------------------------------------- PR8
    print("\n" + "=" * 78)
    print("PR8 -- REAL DEFOCUS: a PILLBOX OTF with contrast reversals, not a")
    print("       Gaussian.  M46 section 9 item 5 lists this as unmeasured.")
    print("=" * 78)
    pr8 = {}
    for roi in ("flat", "detail"):
        s0, sg, fp = src[roi], sigma[roi], fpn[roi]
        print(f"\n  ROI {roi}     (first OTF zero of a radius-r pillbox is at "
              f"f = 0.6098/r cyc/px)")
        print("       r px    zeros below f_sig    sigpow/base    dsig px     rmtf2")
        rows = {}
        for r_px in (0.25, 0.5, 1.0, 2.0, 3.0, 5.0):
            nz = int(np.floor(K.F_SIG / (0.6098 / r_px))) if r_px > 0 else 0
            dv, sv, rv = [], [], []
            for rp in range(4):
                rng = np.random.default_rng(1200 + 1000 * rp)
                bb = K.pillbox_blur(s0, r_px)
                a = bb + fp + rng.standard_normal(s0.shape).astype(np.float32) * sg
                b = bb + fp + rng.standard_normal(s0.shape).astype(np.float32) * sg
                rng2 = np.random.default_rng(1200 + 1000 * rp)
                a0 = s0 + fp + rng2.standard_normal(s0.shape).astype(np.float32) * sg
                b0 = s0 + fp + rng2.standard_normal(s0.shape).astype(np.float32) * sg
                rs_b, rs_t = K.RingStats(a0, b0), K.RingStats(a, b)
                dv.append(K.dsig(rs_b, rs_t, jack=False)["px"])
                sv.append(K.sigpow(rs_t) / K.sigpow(rs_b))
                rv.append(K.rmtf2(rs_b, rs_t))
            print(f"     {r_px:6.2f}   {nz:16d}    {agg(sv)[0]:11.5f}   "
                  f"{agg(dv)[0]:+8.4f}   {agg(rv)[0]:9.5f}")
            rows[f"{r_px}"] = dict(nzeros=nz, sigpow=agg(sv)[0], dsig=agg(dv)[0],
                                   rmtf2=agg(rv)[0])
        pr8[roi] = rows
        d = [rows[f"{r}"]["dsig"] for r in (0.25, 0.5, 1.0, 2.0, 3.0, 5.0)]
        print(f"    dsig monotone increasing across the zeros? "
              f"{all(d[i] < d[i+1] for i in range(len(d)-1))}")
    res["pr8"] = pr8

    # ---------------------------------------------------------------- PR10
    print("\n" + "=" * 78)
    print("PR10 -- THE PEDESTAL FLOOR.  A white common-mode pedestal is common")
    print("        power that is not scene, so it must bias dsig DOWNWARD and")
    print("        eventually saturate it.  Where does it depart from truth?")
    print("=" * 78)
    pr10 = {}
    for roi in ("flat", "detail"):
        s0, sg = src[roi], sigma[roi]
        print(f"\n  ROI {roi}     rows are planted rho; columns are TRUE blur")
        print("      rho      pedestal/C(f_sig)" + "".join(
            f"    sb={s:<5.2f}" for s in (0.05, 0.1, 0.2, 0.5, 1.0, 2.0)))
        rows = {}
        for rho_p in (0.0, 0.05, 0.3094, 1.0):
            fp = K.M.make_fpn(s0.shape, SEED_FPN, np.sqrt(rho_p) * sig1[roi]) \
                if rho_p > 0 else np.zeros_like(s0)
            rng = np.random.default_rng(6001)
            a0 = s0 + fp + rng.standard_normal(s0.shape).astype(np.float32) * sg
            b0 = s0 + fp + rng.standard_normal(s0.shape).astype(np.float32) * sg
            rs0 = K.RingStats(a0, b0)
            rs_ped = K.RingStats(fp, fp) if rho_p > 0 else None
            frac = (rs_ped.at(K.F_SIG)[0] / rs0.at(K.F_SIG)[0]) if rho_p > 0 else 0.0
            vals = []
            for sb in (0.05, 0.1, 0.2, 0.5, 1.0, 2.0):
                rng2 = np.random.default_rng(6001)
                bb = K.M.blur(s0, sb)
                a = bb + fp + rng2.standard_normal(s0.shape).astype(np.float32) * sg
                b = bb + fp + rng2.standard_normal(s0.shape).astype(np.float32) * sg
                vals.append(K.dsig(rs0, K.RingStats(a, b), jack=False)["px"])
            print(f"    {rho_p:7.4f}   {frac:16.5f}" + "".join(
                f"   {v:+9.4f}" for v in vals))
            rows[f"{rho_p}"] = dict(pedestal_frac=frac, dsig=vals)
        print("      truth  " + " " * 18 + "".join(
            f"   {s:+9.4f}" for s in (0.05, 0.1, 0.2, 0.5, 1.0, 2.0)))
        pr10[roi] = rows
    res["pr10"] = pr10

    with open(os.path.join(K.OUT, "s1_properties.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/s1_properties.json  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
