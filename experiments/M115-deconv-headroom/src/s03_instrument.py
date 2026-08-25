"""M115 s03 -- diagnose the C1 failure, then validate the REPLACEMENT channel.

The pre-registered noise channel was antithetic injection,
    D = (pipeline(Y+n) - pipeline(Y-n)) / 2 .
It FAILED control C1: on a real scene-free capture it reported mid-band SNR
84.9 for a per-pixel selector.  That is not a small error; it is the metric
inventing signal out of noise, which is exactly the failure rule 20 exists to
catch and exactly the failure that discarded ORCH's chromatic-aberration table.

D1 below diagnoses it.  The channel measures d(pipeline)/dY . n with the
election held effectively fixed, so it sees how INJECTED noise propagates given
the weights -- and is blind to noise that the election has already converted
into STRUCTURE.  A per-pixel argmax over a noise cube manufactures spatial
structure at the focus-window scale, which is inside the mid band.  The
injection channel cannot see it, so P_O - P_noise credits it as signal.

The replacement is a SPLIT-STACK channel: two disjoint interleaved halves of
the real stack, each pushed through the whole pipeline with its own weights.

    P_sig   = Re<A conj(B)>      noise independent between halves -> 0
    P_noise = P(A - B) / 2       signal common to both halves -> cancels

No noise model enters it at all, and amplified or selection-sculpted noise
lands in P_noise by construction because it is independent between the halves.

Controls run here, all BEFORE any headroom number exists (rule 9):
  D1  diagnosis of the injection failure, with the two channels side by side
  C1' the null, on the replacement channel
  C6  the fixed-pattern floor -- what the null's residual P_sig actually is
  C2  planted exact Fourier blur: monotone response + recovery ratio
  C3  GAIN INVARIANCE: the headline must not move under post-sharpening
  C3b a real unsharp-mask attack, beside a naive gradient metric that falls for it
  C9  latent mismatch between halves, bounded by a deliberately worse split
  C10 internal consistency, (P(A)+P(B))/2 == P_sig + P_noise
"""
import os, sys, json, glob, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s02_controls_a import null_cube, banner, spec_stats

DF = 0.01
SEED = 20260824
ROIS = json.load(open(os.path.join(L.OUT, "s01_rois.json")))


def load_detail(stack, which="detail"):
    roi = tuple(ROIS[stack][which + "_roi"])          # (x, y, w, h)
    files = L.stack_files(ROIS[stack]["dir"])
    cube = L.load_cube(files, roi)
    iso = L.iso_of(files[0])
    g, rn_e = L.noise_params(iso)
    return cube, g, rn_e, roi[2]


# ------------------------------------------------------------------- D1
def d1_diagnose(log):
    banner("D1 -- why the injection channel failed C1")
    cube, g, rn_e, B = null_cube(24, 0, log)
    rb = L.RadialBins(B, DF)
    crop = L.crop_fn(L.PAD, B)
    mid = rb.band_mask(*L.MIDBAND)
    fine, coarse, reg = L.focus_fields(cube, g, rn_e)
    s_null, _, _ = L.calibrate_s(cube, coarse)

    # how much does the election move between Y+n and Y-n?
    rng = np.random.default_rng(SEED)
    n = L.make_noise(cube, g, rn_e, rng)
    ap = L.run_all_arms(cube + n, g, rn_e, s_null, want=["FRAME_PIX", "FRAME*"])
    am = L.run_all_arms(cube - n, g, rn_e, s_null, want=["FRAME_PIX", "FRAME*"])
    a0 = L.run_all_arms(cube, g, rn_e, s_null, want=["FRAME_PIX", "FRAME*"])
    tile_flip = float(np.mean(ap["_picks"] != am["_picks"]))
    print(f"  tile election differs between Y+n and Y-n on {100*tile_flip:.1f}% of tiles")

    # the two channels, side by side, on the SAME null cube
    arms = L.run_all_arms(cube, g, rn_e, s_null)
    dch = L.noise_channel(cube, g, rn_e, s_null, 3, SEED, crop)
    spl = L.split_channel(cube, g, rn_e, s_null, crop)
    rows = {}
    print(f"\n  {'arm':12s} {'inject SNR':>11s} {'split SNR':>10s} "
          f"{'Pn_inject/Pn_split':>19s}")
    for a in L.ARMS:
        Po, Pn_i, _, snr_i = spec_stats(rb, crop(arms[a]), dch[a])
        Ps, Pn_s, snr_s, Pa = L.split_stats(rb, *spl[a])
        ri = float(np.mean(snr_i[mid]))
        rs = float(np.mean(snr_s[mid]))
        rat = float(np.mean(Pn_i[mid] / np.maximum(Pn_s[mid], 1e-30)))
        rows[a] = dict(inject_snr_mid=ri, split_snr_mid=rs, pn_ratio=rat)
        print(f"  {a:12s} {ri:11.4f} {rs:10.4f} {rat:19.4f}")
    log["D1"] = dict(tile_flip=tile_flip, rows=rows, s=s_null)
    return cube, g, rn_e, B, rb, crop, s_null, spl


# -------------------------------------------------------------------- C6
def c6_fpn_floor(log, cube, g, rn_e, B, rb, crop, s_null):
    """Is the null's residual P_sig the fixed-pattern floor, or a metric bug?

    REGISTERED BEFORE RUNNING.  Fixed-pattern non-uniformity is the SAME pattern
    in both halves, so it is common-mode and lands in P_sig by construction --
    the split channel cannot separate a static sensor pattern from a static
    scene, and nothing that uses one capture of one sensor can.  If that is what
    the residual is, then as the half size N grows:

        P_sig(N)   INVARIANT            the pattern is not averaged away
        P_noise(N) proportional to 1/N  for MEAN, which averages
        SNR(N)     proportional to N

    A metric defect has no reason to produce that exact scaling.  The
    discriminator is the SLOPE of log SNR against log N: 1.0 for a real floor.
    """
    banner("C6 -- is the null residual the fixed-pattern floor?")
    print("Registered prediction: P_sig invariant in N, SNR proportional to N")
    print("(log-log slope 1.0 +/- 0.25).  A metric defect need not scale at all.\n")
    mid = rb.band_mask(*L.MIDBAND)
    Ns = [2, 4, 8, 12]
    rows = {}
    for arm in ["MEAN", "WIENER_UNG"]:
        ps, pn, sn = [], [], []
        for N in Ns:
            sub = cube[:2 * N]
            sp = L.split_channel(sub, g, rn_e, s_null, crop, want=[arm])
            Ps, Pn, snr, _ = L.split_stats(rb, *sp[arm])
            ps.append(float(np.mean(Ps[mid])))
            pn.append(float(np.mean(Pn[mid])))
            sn.append(float(np.mean(Ps[mid]) / np.mean(Pn[mid])))
            print(f"  {arm:11s} N={N:3d}  P_sig {ps[-1]:11.4g}  "
                  f"P_noise {pn[-1]:11.4g}  SNR {sn[-1]:8.4f}")
        lg = np.polyfit(np.log(Ns), np.log(np.maximum(sn, 1e-30)), 1)[0]
        pv = float(np.max(ps) / max(np.min(ps), 1e-30))
        rows[arm] = dict(N=Ns, psig=ps, pnoise=pn, snr=sn,
                         loglog_slope=float(lg), psig_spread=pv)
        print(f"  {arm:11s} log-log slope of SNR in N = {lg:.3f}   "
              f"P_sig spread {pv:.3f}x\n")
    ok = bool(all(abs(rows[a]["loglog_slope"] - 1.0) < 0.25 for a in ["MEAN"]))
    print(f"  C6: {'PASS' if ok else 'FAIL'} -- MEAN's residual scales as a static "
          f"pattern, i.e. it is the sensor floor, not a metric defect.")
    log["C6"] = dict(rows=rows, passed=ok)
    return ok, rows


# ------------------------------------------------------------------- C1'
def c1_null(log, rb, spl):
    banner("C1' -- the null, on the split-stack channel")
    print("FAILS IF: any arm reports mid-band signal power above the")
    print("fixed-pattern floor.  Such an input exists -- this cube has no scene.\n")
    mid = rb.band_mask(*L.MIDBAND)
    out = {}
    print(f"  {'arm':12s} {'mean SNR mid':>13s} {'max SNR mid':>12s}   verdict")
    for a in L.ARMS:
        Ps, Pn, snr, Pa = L.split_stats(rb, *spl[a])
        v, mx = float(np.mean(snr[mid])), float(np.max(snr[mid]))
        out[a] = dict(mean=v, mx=mx, Ps=Ps.tolist(), Pn=Pn.tolist(), Pa=Pa.tolist())
        print(f"  {a:12s} {v:13.4f} {mx:12.4f}   "
              f"{'ok' if mx < 0.25 else 'READS SIGNAL WHERE THERE IS NONE'}")
    ok = bool(all(out[a]["mx"] < 0.25 for a in L.ARMS))
    print(f"\n  C1': {'PASS' if ok else 'FAIL'}  (bar: max mid-band SNR < 0.25)")
    log["C1p"] = dict(arms=out, passed=ok, bar=0.25, centres=rb.centres.tolist())
    return ok


# -------------------------------------------------------------------- C2
def c2_blur(log, stack):
    banner(f"C2 -- planted exact Fourier blur on {stack} detail ROI")
    print("FAILS IF: P_sig does not fall monotonically with planted blur, or")
    print("the recovery ratio leaves [0.90, 1.10].  A metric reading scene hue")
    print("rather than sharpness would fail -- that is how ORCH's CA table died.\n")
    cube, g, rn_e, B = load_detail(stack)
    rb = L.RadialBins(B, DF)
    crop = L.crop_fn(L.PAD, B)
    mid = rb.band_mask(*L.MIDBAND)
    fc = rb.centres[mid]
    fine, coarse, reg = L.focus_fields(cube, g, rn_e)
    s0, _, _ = L.calibrate_s(cube, coarse)
    sbs = [0.0, 0.5, 1.0, 1.5, 2.0]
    res = {}
    for arm in ["MEAN", "FRAME*"]:
        curves, recs = [], []
        base = None
        for sb in sbs:
            cb = L.blur_cube(cube, sb)
            sp = L.split_channel(cb, g, rn_e, s0, crop, want=[arm])
            Ps, Pn, snr, Pa = L.split_stats(rb, *sp[arm])
            v = Ps[mid]
            curves.append(float(np.mean(v)))
            if sb == 0.0:
                base = v.copy()
            else:
                pred = np.exp(-4.0 * np.pi ** 2 * sb ** 2 * fc ** 2)
                meas = np.maximum(v, 1e-30) / np.maximum(base, 1e-30)
                keep = (pred > 1e-3) & (base > 0)
                r = float(np.mean(np.log(meas[keep]) / np.log(pred[keep])))
                recs.append(r)
            print(f"  {arm:8s} sb={sb:.1f}  mean P_sig(mid) = {curves[-1]:12.4g}"
                  + (f"   recovery {recs[-1]:6.4f}" if sb > 0 else "   (reference)"))
        mono = bool(all(curves[i] > curves[i + 1] for i in range(len(curves) - 1)))
        okr = bool(all(0.90 <= r <= 1.10 for r in recs))
        print(f"  {arm:8s} monotone decreasing: {mono}   recovery in [0.90,1.10]: {okr}")
        res[arm] = dict(sbs=sbs, mean_psig=curves, recovery=recs,
                        monotone=mono, recovery_ok=okr)
    ok = bool(all(res[a]["monotone"] and res[a]["recovery_ok"] for a in res))
    print(f"\n  C2: {'PASS' if ok else 'FAIL'}")
    log.setdefault("C2", {})[stack] = dict(res=res, passed=ok, s=s0)
    return ok, cube, g, rn_e, B, rb, crop, s0


# ------------------------------------------------------------- C3 / C3b
def c3_gain(log, stack, cube, g, rn_e, B, rb, crop, s0):
    banner(f"C3 -- gain invariance on {stack}: can the headline be bought?")
    print("FAILS IF: applying a known post-filter to an arm's OUTPUT moves the")
    print("SNR headline.  A contrast-only metric fails this by construction --")
    print("that is precisely why the headline is SNR and not contrast.\n")
    mid = rb.band_mask(*L.MIDBAND)
    sp = L.split_channel(cube, g, rn_e, s0, crop, want=["FRAME*"])
    A, Bo = sp["FRAME*"]
    Ps0, Pn0, snr0, _ = L.split_stats(rb, A, Bo)

    gains = {
        "flat x3":       lambda f: np.full_like(f, 3.0),
        "unsharp 1+2f":  lambda f: 1.0 + 2.0 * f / L.F_SIG,
        "unsharp 1+6f":  lambda f: 1.0 + 6.0 * f / L.F_SIG,
        "inverse taper": lambda f: 1.0 / np.maximum(L.otf_diffraction(f), 0.05),
    }
    rows = {}
    print(f"  {'post-filter':16s} {'contrast gain':>14s} {'SNR ratio':>11s} "
          f"{'naive grad gain':>16s}")
    for name, af in gains.items():
        Ag, Bg = L.freq_gain(A, af), L.freq_gain(Bo, af)
        Ps, Pn, snr, _ = L.split_stats(rb, Ag, Bg)
        cg = float(np.sqrt(np.mean(Ps[mid]) / np.mean(Ps0[mid])))
        sr = float(np.mean(snr[mid]) / np.mean(snr0[mid]))
        gy0 = float(np.mean(np.gradient(A.astype(np.float64))[0] ** 2
                            + np.gradient(A.astype(np.float64))[1] ** 2))
        gy1 = float(np.mean(np.gradient(Ag)[0] ** 2 + np.gradient(Ag)[1] ** 2))
        ng = float(np.sqrt(gy1 / gy0))
        rows[name] = dict(contrast_gain=cg, snr_ratio=sr, naive_grad_gain=ng)
        print(f"  {name:16s} {cg:14.4f} {sr:11.4f} {ng:16.4f}")
    ok = bool(all(abs(r["snr_ratio"] - 1.0) < 0.02 for r in rows.values()))
    fooled = max(r["naive_grad_gain"] for r in rows.values())
    print(f"\n  C3: {'PASS' if ok else 'FAIL'}  (bar: |SNR ratio - 1| < 0.02)")
    print(f"  C3b: the naive gradient metric was moved up to {fooled:.2f}x by a")
    print(f"       post-filter that added no information whatsoever.")
    log.setdefault("C3", {})[stack] = dict(rows=rows, passed=ok, max_naive=fooled)
    return ok


# -------------------------------------------------------------- C9 / C10
def c9_latent(log, stack, cube, g, rn_e, rb, crop, s0):
    banner(f"C9 -- how much signal does the latent mismatch between halves cost?")
    print("The interleaved split assumes the two halves share a latent.  A")
    print("first-half/second-half split deliberately breaks that assumption;")
    print("if the interleaved reading sat near the broken one, P_sig would be")
    print("dominated by mismatch rather than by scene.\n")
    mid = rb.band_mask(*L.MIDBAND)
    out = {}
    for mode in ["oddeven", "halves"]:
        sp = L.split_channel(cube, g, rn_e, s0, crop, mode=mode, want=["MEAN", "FRAME*"])
        for a in ["MEAN", "FRAME*"]:
            Ps, Pn, snr, Pa = L.split_stats(rb, *sp[a])
            out[f"{mode}/{a}"] = dict(psig=float(np.mean(Ps[mid])),
                                      snr=float(np.mean(snr[mid])),
                                      consistency=float(np.mean(Pa[mid] /
                                                        np.maximum(Ps[mid] + Pn[mid], 1e-30))))
            print(f"  {mode:8s} {a:8s} P_sig(mid) {out[f'{mode}/{a}']['psig']:12.4g}   "
                  f"SNR {out[f'{mode}/{a}']['snr']:9.3f}   "
                  f"consistency {out[f'{mode}/{a}']['consistency']:6.4f}")
    ratio = out["oddeven/FRAME*"]["psig"] / max(out["halves/FRAME*"]["psig"], 1e-30)
    cons = [v["consistency"] for v in out.values()]
    okc = bool(all(abs(c - 1.0) < 0.05 for c in cons))
    print(f"\n  C9: interleaved P_sig is {ratio:.3f}x the deliberately-mismatched split")
    print(f"  C10: consistency (P(A)+P(B))/2 vs P_sig+P_noise = "
          f"{min(cons):.4f}..{max(cons):.4f}  -> {'PASS' if okc else 'FAIL'}")
    log.setdefault("C9", {})[stack] = dict(rows=out, ratio=ratio, c10_passed=okc)
    return okc


def main():
    t0 = time.time()
    log = {}
    cube, g, rn_e, B, rb, crop, s_null, spl = d1_diagnose(log)
    ok1 = c1_null(log, rb, spl)
    ok6, fpn = c6_fpn_floor(log, cube, g, rn_e, B, rb, crop, s_null)
    log["fpn_floor_psig_mid"] = float(np.mean(
        L.split_stats(rb, *spl["MEAN"])[0][rb.band_mask(*L.MIDBAND)]))
    log["fpn_floor_level_dn"] = float(cube.mean())
    stack = "109MSDCF"
    ok2, dcube, dg, drn, dB, drb, dcrop, ds = c2_blur(log, stack)
    ok3 = c3_gain(log, stack, dcube, dg, drn, dB, drb, dcrop, ds)
    ok9 = c9_latent(log, stack, dcube, dg, drn, drb, dcrop, ds)
    log["summary"] = dict(C1p=ok1, C6=ok6, C2=ok2, C3=ok3, C10=ok9)
    json.dump(log, open(os.path.join(L.OUT, "s03_instrument.json"), "w"), indent=2)
    print(f"\nelapsed {time.time()-t0:.1f}s -> s03_instrument.json")
    print(f"\nSUMMARY  C1' {'PASS' if ok1 else 'FAIL'}   C6 {'PASS' if ok6 else 'FAIL'}"
          f"   C2 {'PASS' if ok2 else 'FAIL'}"
          f"   C3 {'PASS' if ok3 else 'FAIL'}   C10 {'PASS' if ok9 else 'FAIL'}")


if __name__ == "__main__":
    main()
