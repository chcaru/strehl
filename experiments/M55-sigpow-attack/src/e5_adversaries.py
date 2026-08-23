"""M55 E5 -- adversarial merges M46 did not build, plus the tautology check on
fact 610's "out-of-sample confirmation".  PR3, PR4, PR5, PR6, PR7.

All pre-registered.  Everything here runs on M46's OWN plant, with M46's own
rho, seeds, sources and matched-cost machinery re-implemented (b3 is frozen,
rule 15), so arm 0 must reproduce b3's published numbers before any adversary
is believed.  If it does not, nothing below is evidence.

PR3  fact 610 confirms rho = 0.3094 by planting FPN at rho and measuring
     FRC(0.45) against rho/(rho + 1/n_eff).  That formula is the algebraic
     INVERSE of rho = FRC/(1-FRC)/n_eff, the equation rho was solved from.
     Sweep the PLANTED rho.  If the formula tracks the measurement at every
     planted value, the check cannot reject any rho (rules 20, 21, 34).
PR4  sigpow is homogeneous of degree 2 in image amplitude.  Apply a gain
     (1+eps) to the SMOOTH arm only and find eps* where S falls to 0.500.
PR5  RULE 18 -- what direction can sigpow be fooled in?  M46 states none.
     PM_M: destroy real detail (sb = 1.0 px) AND add a fixed high-frequency
     texture COMMON to both half-merges, amplitude matched so hp_sd equals the
     baseline.  Manufactured structure is common-mode, so it enters C.
PR6  PM_E: a contrast-restoring low-pass, y = gamma * blur(L+P+N, sb) with
     gamma = 1/|H(f_sig)|.  A merge that low-passes and then renormalises.
PR7  sweep the smoothing factor k; re-solve the matched blur each time.
"""
import os, sys, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
M46OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m46-detail-metric", "out")
M46SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m46-detail-metric", "src")
M41SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m41-r3-kill", "src")
for p in (M46SRC, M41SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
import m46lib as M
import m41lib as L1
import m41lib3 as L3

N, SEED_FPN, REPS = 512, 46046, 8
F_SIG, NBIN = M.F_SIG, 64


def ring_power(a, f=F_SIG, nbin=NBIN):
    """b3_separation.ring_power, re-implemented verbatim in behaviour."""
    n = a.shape[0]
    w = np.outer(np.hanning(n), np.hanning(n))
    A = np.abs(np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))) ** 2
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    centres = 0.5 * (edges[:-1] + edges[1:]) / n
    i = int(np.argmin(np.abs(centres - f)))
    m = (rr >= edges[i]) & (rr < edges[i + 1])
    return float(A[m].mean())


def oracle_mtf(y, latent, f=F_SIG, nbin=NBIN):
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
    return None if den < 1e-30 else float(np.real(np.sum(Y[m] * np.conj(Lz[m]))) / den)


def all_metrics(y1, y2, latent):
    fr = M.frc_at(y1, y2)
    pw = ring_power(y1)
    return dict(frc2_at_fsig=fr, hp_sd=M.hp_sd(y1), p_ratio=M.p_ratio(y1),
                mean_grad=M.mean_grad(y1), ringpow=pw, sigpow_fsig=fr * pw,
                oracle_mtf=oracle_mtf(y1, latent))


def bank(drawer, reps=REPS, base_seed=1):
    acc = {}
    for r in range(reps):
        y1, y2, lat = drawer(base_seed + 1000 * r + 7)
        for k, v in all_metrics(y1, y2, lat).items():
            acc.setdefault(k, []).append(v)
    return {k: float(np.mean(v)) for k, v in acc.items()}


def sep(base, arm_b, arm_s, key):
    b, u, s = base[key], arm_b[key], arm_s[key]
    db, ds = (b - u) / abs(b), (b - s) / abs(b)
    tot = abs(db) + abs(ds)
    return db, ds, (abs(db) / tot if tot > 1e-12 else None)


def main():
    t0 = time.time()
    with open(os.path.join(M46OUT, "b1_results.json")) as fh:
        b1 = json.load(fh)
    z = np.load(os.path.join(M46OUT, "b1_merges.npz"))
    pad = 32
    det = z["d112"][pad:-pad, pad:-pad].astype(np.float32)
    g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]
    lvl_d = float(np.median(det))
    sig_d = float(np.sqrt(M.noise_var_dn(lvl_d, g, rn_e)))
    ne_d = b1["n_eff"]["112_detail"]
    ne_f = b1["n_eff"]["112_flat"]
    rho = b1["twocap"]["flat"]["at_fsig"] / (1 - b1["twocap"]["flat"]["at_fsig"]) / ne_f
    sigma = sig_d / np.sqrt(ne_d)
    fpn = M.make_fpn(det.shape, SEED_FPN, np.sqrt(rho) * sig_d)
    K = float(np.sqrt(2.0))
    print("=" * 78)
    print("M55 E5 -- adversarial merges + the tautology check")
    print("=" * 78)
    print(f"   rho {rho:.4f}  sigma {sigma:.4f} DN  n_eff {ne_d:.3f}  "
          f"latent = M46's merged detail ROI")
    res = dict(rho=rho, sigma=sigma)

    # ---------------------------------------------------------------- PR3
    print("\n" + "=" * 78)
    print("PR3 -- does fact 610's confirmation have any power to reject a rho?")
    print("=" * 78)
    print("   b4 plants FPN at rho and checks FRC(0.45) against rho/(rho+1/n_eff).")
    print("   Sweeping the PLANTED rho.  If every row agrees the check is the")
    print("   algebraic inverse of the equation rho was solved from.")
    lat_bl = M.synth_broadband(N, 4242, cutoff=0.20)
    rng0 = np.random.default_rng(9001)
    print("     planted rho   n_eff    predicted    measured    ratio")
    pr3 = {}
    for rho_p in (0.02, 0.05, 0.1, 0.3094, 1.0, 3.0):
        for nef in (ne_f, ne_d):
            s1 = 1.0
            fp = M.make_fpn((N, N), 777, np.sqrt(rho_p) * s1)
            sg = s1 / np.sqrt(nef)
            vals = []
            for r in range(4):
                rr = np.random.default_rng(300 + r)
                y1 = lat_bl + fp + rr.standard_normal((N, N)).astype(np.float32) * sg
                y2 = lat_bl + fp + rr.standard_normal((N, N)).astype(np.float32) * sg
                vals.append(M.frc_at(y1, y2, f=0.45))
            got = float(np.mean(vals))
            pred = rho_p / (rho_p + 1.0 / nef)
            print(f"     {rho_p:11.4f} {nef:8.3f}    {pred:9.4f}   {got:9.4f}   "
                  f"{got/pred:7.4f}")
            pr3[f"{rho_p}_{nef:.3f}"] = dict(pred=pred, got=got)
    res["pr3"] = pr3

    # ------------------------------------------------- baseline reproduction
    def draw_base(seed, sb=0.0, k=1.0, gain=1.0, post=False, gamma=1.0,
                  add=None):
        rng = np.random.default_rng(seed)
        n1 = rng.standard_normal(det.shape).astype(np.float32) * (sigma / k)
        n2 = rng.standard_normal(det.shape).astype(np.float32) * (sigma / k)
        if post:
            y1 = gamma * M.blur(det + fpn + n1, sb)
            y2 = gamma * M.blur(det + fpn + n2, sb)
        else:
            y1 = gain * (M.blur(det, sb) + fpn + n1)
            y2 = gain * (M.blur(det, sb) + fpn + n2)
        if add is not None:
            y1 = y1 + add
            y2 = y2 + add
        return y1, y2, det

    def solve_sb(k, drawer_factory, hi=4.0):
        tgt = bank(lambda s: draw_base(s, k=k), reps=4, base_seed=11)["hp_sd"]
        lo = 0.0
        f_lo = bank(drawer_factory(0.0), reps=4, base_seed=11)["hp_sd"] - tgt
        f_hi = bank(drawer_factory(hi), reps=4, base_seed=11)["hp_sd"] - tgt
        if f_lo * f_hi > 0:
            return None, tgt
        for _ in range(24):
            mid = 0.5 * (lo + hi)
            fm = bank(drawer_factory(mid), reps=4, base_seed=11)["hp_sd"] - tgt
            if f_lo * fm <= 0:
                hi, f_hi = mid, fm
            else:
                lo, f_lo = mid, fm
        return 0.5 * (lo + hi), tgt

    SB, tgt = solve_sb(K, lambda sb: (lambda s: draw_base(s, sb=sb)))
    base = bank(lambda s: draw_base(s), base_seed=1)
    blur = bank(lambda s: draw_base(s, sb=SB), base_seed=1)
    smoo = bank(lambda s: draw_base(s, k=K), base_seed=1)
    print("\n" + "=" * 78)
    print(f"ARM 0 -- REPRODUCTION of b3 S_detail.  matched sb = {SB:.5f} px")
    print("   b3 published sb = 0.04999 px, S(sigpow) = 0.937, S(hp_sd) = 0.501")
    print("=" * 78)
    print("   metric          baseline      BLUR         SMOOTH     d_blur   d_smooth      S")
    rep = {}
    for key in ("frc2_at_fsig", "hp_sd", "p_ratio", "mean_grad", "ringpow",
                "sigpow_fsig", "oracle_mtf"):
        db, ds, S = sep(base, blur, smoo, key)
        print(f"   {key:<14s} {base[key]:12.5g} {blur[key]:12.5g} {smoo[key]:12.5g} "
              f"{db:+7.4f} {ds:+7.4f}  {S:6.3f}")
        rep[key] = dict(d_blur=db, d_smooth=ds, S=S)
    res["arm0"] = dict(sb=SB, rows=rep)

    # ---------------------------------------------------------------- PR4
    print("\n" + "=" * 78)
    print("PR4 -- photometric sensitivity: gain applied to the SMOOTH arm only")
    print("=" * 78)
    print("     eps        S(sigpow)   S(ringpow)   S(hp_sd)   S(frc)")
    pr4 = {}
    for eps in (0.0, 0.001, 0.002, 0.004, 0.01, 0.02):
        sm = bank(lambda s: draw_base(s, k=K, gain=1.0 + eps), base_seed=1)
        row = {}
        for key in ("sigpow_fsig", "ringpow", "hp_sd", "frc2_at_fsig"):
            row[key] = sep(base, blur, sm, key)[2]
        print(f"     {eps:8.4f}   " + "  ".join(
            f"{row[k]:9.3f}" for k in ("sigpow_fsig", "ringpow", "hp_sd", "frc2_at_fsig")))
        pr4[eps] = row
    res["pr4"] = pr4

    # ---------------------------------------------------------------- PR6
    print("\n" + "=" * 78)
    print("PR6 -- PM_E, a CONTRAST-RESTORING low-pass: y = gamma*blur(L+P+N, sb)")
    print("   with gamma = 1/|H(f_sig)| = exp(+2 pi^2 sb^2 f_sig^2).")
    print("   A merge that low-passes its own output and renormalises.")
    print("=" * 78)
    print("     sb_pc     gamma    d_sigpow   d_ringpow   d_hp_sd  d_oracle_mtf   S(sigpow)")
    pr6 = {}
    for sb_pc in (0.05, 0.1, 0.2, 0.5, 1.0):
        gam = float(np.exp(2 * np.pi ** 2 * sb_pc ** 2 * F_SIG ** 2))
        pe = bank(lambda s: draw_base(s, sb=sb_pc, post=True, gamma=gam), base_seed=1)
        db_s = (base["sigpow_fsig"] - pe["sigpow_fsig"]) / abs(base["sigpow_fsig"])
        db_r = (base["ringpow"] - pe["ringpow"]) / abs(base["ringpow"])
        db_h = (base["hp_sd"] - pe["hp_sd"]) / abs(base["hp_sd"])
        db_o = (base["oracle_mtf"] - pe["oracle_mtf"]) / abs(base["oracle_mtf"])
        S = sep(base, pe, smoo, "sigpow_fsig")[2]
        print(f"     {sb_pc:6.2f}  {gam:8.5f}  {db_s:+9.5f}  {db_r:+9.5f}  "
              f"{db_h:+9.5f}  {db_o:+9.5f}   {S:9.3f}")
        pr6[sb_pc] = dict(gamma=gam, d_sigpow=db_s, d_ringpow=db_r, d_hp=db_h,
                          d_oracle=db_o, S=S)
    res["pr6"] = pr6

    # ---------------------------------------------------------------- PR5
    print("\n" + "=" * 78)
    print("PR5 -- RULE 18: can sigpow be fooled UPWARD?  PM_M destroys real detail")
    print("   (sb = 1.0 px) and adds a FIXED high-frequency texture common to both")
    print("   half-merges, amplitude solved so hp_sd matches the baseline exactly.")
    print("=" * 78)
    rngT = np.random.default_rng(31337)
    T = rngT.standard_normal((N, N)).astype(np.float32)
    T = T - M.blur(T, 1.5)                     # high-pass: pure fake fine structure
    T = (T / T.std()).astype(np.float32)
    tgt_hp = base["hp_sd"]
    lo, hi = 0.0, 200.0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        v = bank(lambda s: draw_base(s, sb=1.0, add=mid * T), reps=3,
                 base_seed=11)["hp_sd"]
        if v < tgt_hp:
            lo = mid
        else:
            hi = mid
    amp = 0.5 * (lo + hi)
    pm = bank(lambda s: draw_base(s, sb=1.0, add=amp * T), base_seed=1)
    pure_blur = bank(lambda s: draw_base(s, sb=1.0), base_seed=1)
    print(f"   fake-texture amplitude solved: {amp:.4f} DN sd "
          f"(hp_sd matched to baseline {tgt_hp:.4f})")
    print("   metric          baseline    blur1.0 only   PM_M (blur+fake)   "
          "d(PM_M)   verdict")
    pr5 = {}
    for key in ("hp_sd", "mean_grad", "p_ratio", "ringpow", "frc2_at_fsig",
                "sigpow_fsig", "oracle_mtf"):
        d = (base[key] - pm[key]) / abs(base[key])
        verdict = "FOOLED UPWARD" if d < -0.01 else ("blind" if abs(d) <= 0.01 else "detects")
        print(f"   {key:<14s} {base[key]:12.5g} {pure_blur[key]:12.5g} "
              f"{pm[key]:14.5g}   {d:+8.4f}   {verdict}")
        pr5[key] = dict(base=base[key], blur_only=pure_blur[key], pm_m=pm[key], d=d)
    res["pr5"] = dict(amp=amp, rows=pr5)

    # ---------------------------------------------------------------- PR7
    print("\n" + "=" * 78)
    print("PR7 -- is S(sigpow) = 0.937 specific to the k = sqrt(2) operating point?")
    print("=" * 78)
    print("       k       matched sb    S(sigpow)  S(ringpow)  S(hp_sd)  S(oracle_mtf)")
    pr7 = {}
    for k in (1.05, 1.1, 1.25, np.sqrt(2), 2.0, 4.0, 8.0):
        sb_k, _ = solve_sb(k, lambda sb: (lambda s: draw_base(s, sb=sb)))
        if sb_k is None:
            print(f"     {k:6.3f}    NO FEASIBLE MATCH")
            continue
        bl = bank(lambda s: draw_base(s, sb=sb_k), base_seed=1)
        sm = bank(lambda s: draw_base(s, k=k), base_seed=1)
        row = {key: sep(base, bl, sm, key)[2] for key in
               ("sigpow_fsig", "ringpow", "hp_sd", "oracle_mtf")}
        print(f"     {k:6.3f}    {sb_k:10.5f}   " + "  ".join(
            f"{row[x]:9.3f}" for x in ("sigpow_fsig", "ringpow", "hp_sd", "oracle_mtf")))
        pr7[k] = dict(sb=sb_k, **row)
    res["pr7"] = pr7

    with open(os.path.join(OUT, "e5_adversaries.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/e5_adversaries.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()

