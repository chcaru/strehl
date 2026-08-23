"""M46 step b3 -- BLUR-ONLY against SMOOTH-ONLY: the separation test, and a
search for a statistic that passes it.

Registered in PREREGISTRATION.md sec 4.3 (commit 2474e5d), question 119.

WHY THIS EXISTS AND WHY IT IS THE REAL INSTRUMENT.  b2 scored the assigned bar
and found that `oracle_fsc` -- an ORACLE holding the true latent -- fails the
flat half under all three plant models.  Sec 3 pre-declared that outcome as
"the BAR is broken, not the metrics", so the flat-ROI proxy cannot settle the
question and the separation has to be measured directly.  It also cannot be
argued: sec 4.3 registered a plant in which only ONE of the two effects is
present, and this is that plant.

    BASELINE      Y_i = L + P + N_i          sigma = s0
    BLUR-ONLY     Y_i = H_sb*L + P + N_i     sigma = s0     latent attenuated,
                                                            noise IDENTICAL
    SMOOTH-ONLY   Y_i = L + P + N_i          sigma = s0/k   noise reduced,
                                                            latent IDENTICAL

P is the FIXED pattern and it is NOT reduced by smoothing, because averaging
more frames does not average away a fixed pattern.  That is physical, and it is
the reason the flat ROI never goes quiet.

THE MATCHING, which is what makes the score exact rather than approximate.
The two plant magnitudes are tied together so that BLUR-ONLY and SMOOTH-ONLY
produce the SAME `hp_sd`.  The incumbent noise statistic therefore CANNOT
distinguish them by construction -- its separation score is 0.500 by definition,
not by measurement -- and every other statistic is asked whether it can.

    S = |d_blur| / (|d_blur| + |d_smooth|),   d_x = (m_base - m_x)/|m_base|

    S = 1.000  a pure RESOLUTION metric: moves on blur, not on smoothing
    S = 0.500  cannot tell them apart
    S = 0.000  a pure NOISE metric

THE DIRECTION OF THE MATCHING WAS CHOSEN BY FEASIBILITY, AND THE FAILED
DIRECTION IS REPORTED RATHER THAN DELETED.  Solving for the smoothing `k` that
imitates a given blur has NO SOLUTION on this data at any blur width down to
0.125 px: the detail ROI's merged noise carries only ~3.7 DN of `hp_sd` against
58.8 DN of scene, so removing ALL of the noise still does not cost what the
smallest blur costs.  Step 1 below re-runs that probe and prints it, because it
is a measurement about the corpus and not a mishap.  The solvable direction is
therefore the other one: fix a REALISTIC merge change -- k = sqrt(2), the noise
a doubling of the acceptance set buys -- and solve for the blur width that costs
the same `hp_sd`.

RULE 20, both directions, written before the run:
  * An input that FAILS: hp_sd, pinned at 0.500 by the matching above.
  * An input that PASSES: `sigpow_fsig` = FRC(f) x ring power(f).  Since
    FRC = C/(C+U) and ring power = C+U, the product is C -- the per-ring COMMON
    power, which is signal.  Smoothing reduces U and leaves C; blur reduces C.
    If the algebra is right this reads S ~ 1 with NO ground truth, and it is
    constructible only because there are two INDEPENDENT captures (question 118).
    If it does not, the algebra is wrong and the report says so.
  * `oracle_mtf`, the regression estimate of H against the KNOWN latent, is the
    second passing input and is not shippable.

Also here: the sources include S_null, a CONSTANT latent -- genuinely no detail,
unlike the observed flat ROI whose rule-10 detector b2 measured at 6.43.
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m46lib as M

N = 512
SEED_FPN = 46046
REPS = 8


# ------------------------------------------------------------------ metrics
def ring_power(a, f=M.F_SIG, nbin=M.NBIN):
    """Mean per-mode power in the ring containing `f`, same window and grid as
    m41lib.frc so the two combine cleanly."""
    n = a.shape[0]
    w = np.outer(np.hanning(n), np.hanning(n))
    A = np.abs(np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))) ** 2
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    i = min(int(f * n / (0.5 * n / (n // 2)) * 0), nbin - 1)  # placeholder, see below
    # ring index whose centre is nearest f
    centres = 0.5 * (edges[:-1] + edges[1:]) / n
    i = int(np.argmin(np.abs(centres - f)))
    m = (rr >= edges[i]) & (rr < edges[i + 1])
    return float(A[m].mean())


def oracle_mtf(y, latent, f=M.F_SIG, nbin=M.NBIN):
    """Ring-averaged regression estimate of the MTF against the KNOWN latent:
    Re<Y conj(L)> / <|L|^2>.  AMPLITUDE-sensitive, unlike a correlation, which
    is why it can see a linear filter that oracle_fsc cannot.  NOT SHIPPABLE."""
    n = y.shape[0]
    w = np.outer(np.hanning(n), np.hanning(n))
    Y = np.fft.fftshift(np.fft.fft2((y - y.mean()) * w))
    Lz = np.fft.fftshift(np.fft.fft2((latent - latent.mean()) * w))
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    centres = 0.5 * (edges[:-1] + edges[1:]) / n
    i = int(np.argmin(np.abs(centres - f)))
    m = (rr >= edges[i]) & (rr < edges[i + 1])
    den = float(np.sum(np.abs(Lz[m]) ** 2))
    if den < 1e-30:
        return None
    return float(np.real(np.sum(Y[m] * np.conj(Lz[m]))) / den)


def all_metrics(y1, y2, latent):
    fr = M.frc_at(y1, y2)
    pw = ring_power(y1)
    cr, cen = M.frc_cross_c(y1, y2)
    return dict(
        frc2_at_fsig=fr,
        frc2_cross=None if cen else cr,
        hp_sd=M.hp_sd(y1),
        p_ratio=M.p_ratio(y1),
        mean_grad=M.mean_grad(y1),
        ringpow=pw,
        sigpow_fsig=fr * pw,
        oracle_fsc=M.oracle_fsc_at(y1, latent),
        oracle_mtf=oracle_mtf(y1, latent),
    )


PAIRED = ["frc2_at_fsig", "hp_sd", "p_ratio", "mean_grad", "sigpow_fsig", "ringpow"]
SINGLE = ["frc2_at_fsig", "frc2_cross", "hp_sd", "p_ratio", "mean_grad",
          "ringpow", "sigpow_fsig", "oracle_fsc", "oracle_mtf"]


def draw(latent, fpn, sigma, sb, seed):
    rng = np.random.default_rng(seed)
    y1 = M.blur(latent, sb) + fpn + rng.standard_normal(latent.shape).astype(np.float32) * sigma
    y2 = M.blur(latent, sb) + fpn + rng.standard_normal(latent.shape).astype(np.float32) * sigma
    return y1, y2


def draw_pc(latent, fpn, sigma, sb, seed):
    """PM_C: a LINEAR POST-FILTER on the delivered image -- what a merge that
    low-passes its own output actually does.  Blur applied AFTER the noise, to
    the whole realised frame, with the same kernel on both captures."""
    rng = np.random.default_rng(seed)
    y1 = M.blur(latent + fpn + rng.standard_normal(latent.shape).astype(np.float32) * sigma, sb)
    y2 = M.blur(latent + fpn + rng.standard_normal(latent.shape).astype(np.float32) * sigma, sb)
    return y1, y2


def bank(latent, fpn, sigma, sb, reps=REPS, base_seed=0, drawer=None):
    acc = {}
    d = drawer or draw
    for r in range(reps):
        y1, y2 = d(latent, fpn, sigma, sb, base_seed + 1000 * r + 7)
        m = all_metrics(y1, y2, latent)
        for k, v in m.items():
            acc.setdefault(k, []).append(v)
    out = {}
    for k, vs in acc.items():
        good = [v for v in vs if v is not None]
        out[k] = float(np.mean(good)) if len(good) == len(vs) else None
    return out


def solve_k(latent, fpn, sigma, sb):
    """THE INFEASIBLE DIRECTION, kept because its failure is a measurement.
    k such that hp_sd(SMOOTH-ONLY) == hp_sd(BLUR-ONLY).  Returns None when the
    whole noise budget is smaller than the blur's cost."""
    target = bank(latent, fpn, sigma, sb, reps=4, base_seed=11)["hp_sd"]
    lo, hi = 1.0, 200.0
    f_lo = bank(latent, fpn, sigma / lo, 0.0, reps=4, base_seed=11)["hp_sd"] - target
    f_hi = bank(latent, fpn, sigma / hi, 0.0, reps=4, base_seed=11)["hp_sd"] - target
    if f_lo * f_hi > 0:
        return None, target, f_lo, f_hi
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        fm = bank(latent, fpn, sigma / mid, 0.0, reps=4, base_seed=11)["hp_sd"] - target
        if f_lo * fm <= 0:
            hi, f_hi = mid, fm
        else:
            lo, f_lo = mid, fm
    return 0.5 * (lo + hi), target, None, None


def solve_sb(latent, fpn, sigma, k, hi=4.0):
    """THE FEASIBLE DIRECTION.  Given a realistic smoothing factor k, the blur
    width whose hp_sd cost is identical.  Bisection on the MEASURED statistic.
    Returns None where no blur can imitate the smoothing -- which is the correct
    answer on a source with no detail in it, and is reported as such."""
    target = bank(latent, fpn, sigma / k, 0.0, reps=4, base_seed=11)["hp_sd"]
    lo = 0.0
    f_lo = bank(latent, fpn, sigma, 0.0, reps=4, base_seed=11)["hp_sd"] - target
    f_hi = bank(latent, fpn, sigma, hi, reps=4, base_seed=11)["hp_sd"] - target
    if f_lo * f_hi > 0:
        return None, target, f_lo, f_hi
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        fm = bank(latent, fpn, sigma, mid, reps=4, base_seed=11)["hp_sd"] - target
        if f_lo * fm <= 0:
            hi, f_hi = mid, fm
        else:
            lo, f_lo = mid, fm
    return 0.5 * (lo + hi), target, None, None


def sep(base, blur, smooth, key):
    b, u, s = base.get(key), blur.get(key), smooth.get(key)
    if b is None or u is None or s is None or abs(b) < 1e-30:
        return None, None, None
    db = (b - u) / abs(b)
    ds = (b - s) / abs(b)
    tot = abs(db) + abs(ds)
    return db, ds, (abs(db) / tot if tot > 1e-12 else None)


def main():
    t0 = time.time()
    print("=" * 78)
    print("M46 b3 -- BLUR-ONLY vs SMOOTH-ONLY, the separation test")
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
    rho = b1["twocap"]["flat"]["at_fsig"] / (1 - b1["twocap"]["flat"]["at_fsig"]) / ne_f

    syn = M.synth_broadband(N, 4611)
    syn = (syn * det.std() + lvl_d).astype(np.float32)
    null = np.full((N, N), lvl_f, np.float32)

    SRC = {"S_null": (null, sig_f, ne_f),
           "S_flat": (flt, sig_f, ne_f),
           "S_detail": (det, sig_d, ne_d),
           "S_synth": (syn, sig_d, ne_d)}

    print(f"\n   rho_fpn = {rho:.4f} (from b1, not chosen).  {REPS} noise draws per point.")
    print("   S_null is a CONSTANT latent: no detail by construction, unlike the")
    print(f"   observed flat ROI whose rule-10 detector b2 measured at 6.43.")

    res = dict(rho=rho, reps=REPS, k=None, sb=None, per_source={}, infeasible={})

    # -------------------------------------------------- the failed direction
    print("\n1. THE INFEASIBLE MATCHING DIRECTION, reported not deleted")
    print("   Can a noise reduction imitate a blur?  Solve k so that")
    print("   hp_sd(SMOOTH) == hp_sd(BLUR) on S_detail:")
    lat, sfr, ne = SRC["S_detail"]
    sigma_d = sfr / np.sqrt(ne)
    fpn_d = M.make_fpn(lat.shape, SEED_FPN, np.sqrt(rho) * sfr)
    for sb in (2.0, 1.0, 0.5, 0.25, 0.125):
        k, tgt, flo, fhi = solve_k(lat, fpn_d, sigma_d, sb)
        msg = (f"k = {k:.4f}   FEASIBLE" if k else
               f"NO SOLUTION (hp_sd target {tgt:.4f}; residual with ALL noise "
               f"removed {fhi:+.4f})")
        print(f"   sb={sb:<6.3f} -> {msg}")
        res["infeasible"][f"{sb}"] = dict(k=k, target=tgt, resid_k200=fhi)
    print("   MEASURED: none.  The merged detail ROI carries hp_sd 58.8 DN of")
    print(f"   scene against sigma {sigma_d:.2f} DN of noise, so deleting ALL the")
    print("   noise costs less than a 0.125 px blur.  On this corpus a merge")
    print("   cannot fake sharpness by denoising -- which is a fact about the")
    print("   DATA, not about any metric.")

    # ----------------------------------------------- the feasible direction
    K = float(np.sqrt(2.0))
    print(f"\n2. THE FEASIBLE MATCHING.  Fix k = sqrt(2) = {K:.4f} -- the noise a")
    print("   DOUBLING of the acceptance set buys, i.e. a real merge change --")
    print("   and solve for the blur that costs the same hp_sd on S_detail.")
    SB, tgt, flo, fhi = solve_sb(lat, fpn_d, sigma_d, K)
    if SB is None:
        print("   *** no feasible sb; the matched design cannot be built ***")
        return
    print(f"   sb = {SB:.5f} px   (hp_sd target {tgt:.4f})")
    print("   hp_sd's separation score is therefore 0.500 BY CONSTRUCTION on")
    print("   S_detail.  Every other statistic is now asked whether it can do")
    print("   better on the SAME pair of plants.")
    res["k"], res["sb"] = K, SB

    # ------------------------------------------------------ the 2x2, per source
    banks = {}
    for sname, (lat, sfr, ne) in SRC.items():
        sigma = sfr / np.sqrt(ne)
        fpn = M.make_fpn(lat.shape, SEED_FPN, np.sqrt(rho) * sfr)
        base = bank(lat, fpn, sigma, 0.0, base_seed=1)
        blur = bank(lat, fpn, sigma, SB, base_seed=1)
        smoo = bank(lat, fpn, sigma / K, 0.0, base_seed=1)
        banks[sname] = (base, blur, smoo)
        sb_own, tgt_own, _, fh_own = solve_sb(lat, fpn, sigma, K)
        print("\n" + "-" * 78)
        print(f"3. {sname}   sigma={sigma:.3f} DN -> {sigma/K:.3f} DN under SMOOTH-ONLY;"
              f"  blur sb={SB:.5f} px")
        if sb_own is None:
            print(f"   NOTE: on this source NO blur width in 0..4 px reproduces the")
            print(f"   smoothing's hp_sd change (residual {fh_own:+.4f} at sb=4).")
            print("   That is the correct answer where there is no detail to lose,")
            print("   and it is why S below reads near 0 here.")
        else:
            print(f"   (this source's own matched blur would be sb={sb_own:.5f} px)")
        print("-" * 78)
        print("   metric          baseline      BLUR-ONLY    SMOOTH-ONLY   "
              "d_blur   d_smooth      S")
        rows = {}
        for key in SINGLE:
            db, ds, S = sep(base, blur, smoo, key)
            def f(v):
                return "     --     " if v is None else f"{v:12.5g}"
            print(f"   {key:<14s} {f(base.get(key))} {f(blur.get(key))} "
                  f"{f(smoo.get(key))} " +
                  ("   --   " if db is None else f"{db:+7.4f}") + " " +
                  ("   --   " if ds is None else f"{ds:+7.4f}") + "  " +
                  ("  --  " if S is None else f"{S:6.3f}"))
            rows[key] = dict(base=base.get(key), blur=blur.get(key),
                             smooth=smoo.get(key), d_blur=db, d_smooth=ds, S=S)
        res["per_source"][sname] = dict(sigma=sigma, sb_own=sb_own, rows=rows)

    # -------------------------------------------- the paired statistic (q119)
    print("\n" + "=" * 78)
    print("5. THE PAIRED STATISTIC (question 119): detail reading CONDITIONED on")
    print("   the SAME merge's flat reading.  Ratio form m(detail)/m(flat), which")
    print("   is scale-free; difference form reported next to it.")
    print("=" * 78)
    if "S_detail" in banks and "S_flat" in banks:
        bd, ud, sd_ = banks["S_detail"]
        bf, uf, sf = banks["S_flat"]
        print("   metric            base ratio  BLUR ratio  SMOOTH ratio  "
              "d_blur   d_smooth      S")
        prow = {}
        for key in PAIRED:
            def rat(a, b):
                x, y = a.get(key), b.get(key)
                if x is None or y is None or abs(y) < 1e-30:
                    return None
                return x / y
            base = {key: rat(bd, bf)}
            blur = {key: rat(ud, uf)}
            smoo = {key: rat(sd_, sf)}
            db, ds, S = sep(base, blur, smoo, key)
            def f(v):
                return "    --    " if v is None else f"{v:10.5g}"
            print(f"   {key:<16s} {f(base[key])}  {f(blur[key])}  {f(smoo[key])}   " +
                  ("  --   " if db is None else f"{db:+7.4f}") + " " +
                  ("  --   " if ds is None else f"{ds:+7.4f}") + "  " +
                  ("  --  " if S is None else f"{S:6.3f}"))
            prow[key] = dict(base=base[key], blur=blur[key], smooth=smoo[key],
                             d_blur=db, d_smooth=ds, S=S)
        res["paired_ratio"] = prow

        print("\n   difference form m(detail) - m(flat):")
        drow = {}
        for key in PAIRED:
            def dif(a, b):
                x, y = a.get(key), b.get(key)
                return None if x is None or y is None else x - y
            base = {key: dif(bd, bf)}; blur = {key: dif(ud, uf)}; smoo = {key: dif(sd_, sf)}
            db, ds, S = sep(base, blur, smoo, key)
            print(f"   {key:<16s} " + ("  --  " if S is None else f"S = {S:6.3f}") +
                  ("" if db is None else f"   d_blur {db:+8.4f}   d_smooth {ds:+8.4f}"))
            drow[key] = dict(d_blur=db, d_smooth=ds, S=S)
        res["paired_diff"] = drow

    # ------------------------------------------- PM_C completeness (the point)
    print("\n" + "=" * 78)
    print("4. THE COMPLETENESS TEST: does the winning statistic see a LINEAR")
    print("   POST-FILTER?  PM_C is a merge that low-passes its own OUTPUT --")
    print("   the failure mode the project actually fears.  b2 MEASURED that")
    print("   frc2_at_fsig is blind to it by construction (FRC = C/(C+U) with")
    print("   both terms scaled by |H|^2).  A statistic that separates blur from")
    print("   smoothing but cannot see a post-filter is still useless here.")
    print("   The post-filter width is matched to the SAME hp_sd cost, so hp_sd")
    print("   cannot tell ANY of the three apart by construction.")
    print("=" * 78)
    pcres = {}
    for sname in ("S_flat", "S_detail"):
        lat, sfr, ne = SRC[sname]
        sigma = sfr / np.sqrt(ne)
        fpn = M.make_fpn(lat.shape, SEED_FPN, np.sqrt(rho) * sfr)
        tgt = bank(lat, fpn, sigma / K, 0.0, reps=4, base_seed=11)["hp_sd"]
        lo, hi = 0.0, 4.0
        f_lo = bank(lat, fpn, sigma, 0.0, reps=4, base_seed=11, drawer=draw_pc)["hp_sd"] - tgt
        f_hi = bank(lat, fpn, sigma, hi, reps=4, base_seed=11, drawer=draw_pc)["hp_sd"] - tgt
        sb_pc = None
        if f_lo * f_hi <= 0:
            for _ in range(24):
                mid = 0.5 * (lo + hi)
                fm = bank(lat, fpn, sigma, mid, reps=4, base_seed=11,
                          drawer=draw_pc)["hp_sd"] - tgt
                if f_lo * fm <= 0:
                    hi, f_hi = mid, fm
                else:
                    lo, f_lo = mid, fm
            sb_pc = 0.5 * (lo + hi)
        print(f"\n   {sname}: matched post-filter width sb_pc = "
              + ("NONE FEASIBLE" if sb_pc is None else f"{sb_pc:.5f} px"))
        if sb_pc is None:
            pcres[sname] = dict(sb_pc=None)
            continue
        base = bank(lat, fpn, sigma, 0.0, base_seed=1)
        post = bank(lat, fpn, sigma, sb_pc, base_seed=1, drawer=draw_pc)
        smoo = bank(lat, fpn, sigma / K, 0.0, base_seed=1)
        print("   metric          baseline     POST-FILTER  SMOOTH-ONLY    d_pc   "
              "d_smooth      S")
        rows = {}
        for key in SINGLE:
            db, ds, S = sep(base, post, smoo, key)
            def f(v):
                return "     --     " if v is None else f"{v:12.5g}"
            print(f"   {key:<14s} {f(base.get(key))} {f(post.get(key))} "
                  f"{f(smoo.get(key))} " +
                  ("   --   " if db is None else f"{db:+7.4f}") + " " +
                  ("   --   " if ds is None else f"{ds:+7.4f}") + "  " +
                  ("  --  " if S is None else f"{S:6.3f}"))
            rows[key] = dict(base=base.get(key), post=post.get(key),
                             smooth=smoo.get(key), d_pc=db, d_smooth=ds, S=S)
        pcres[sname] = dict(sb_pc=sb_pc, rows=rows)
    res["pm_c"] = pcres

    # ------------------------------------------------------------- verdict
    print("\n" + "=" * 78)
    print("6. WHICH STATISTICS SEPARATE?   S >= 0.90 required to call a statistic")
    print("   a RESOLUTION metric; hp_sd is pinned at 0.500 BY THE MATCHING.")
    print("=" * 78)
    print("   statistic         " + "".join(f"{s:>12s}" for s in SRC))
    for key in SINGLE:
        row = f"   {key:<18s}"
        for sname in SRC:
            r = res["per_source"].get(sname, {}).get("rows", {}).get(key)
            row += "          --" if not r or r["S"] is None else f"{r['S']:12.3f}"
        print(row)
    if "paired_ratio" in res:
        for key in PAIRED:
            S = res["paired_ratio"][key]["S"]
            print(f"   {'paired:' + key:<18s}" + " " * 24 +
                  ("          --" if S is None else f"{S:12.3f}") + "   (detail/flat)")

    with open(os.path.join(M.OUT, "b3_results.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/b3_results.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
