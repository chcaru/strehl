"""bandqual.py -- does 0.30-0.35 cyc/output px carry focus-dependent signal on MY data?

Written by V-SOFTCHECK. NOT derived from V-LINEAR's noisefloor.py or V-LINEAR2's
bandsignal.py. Neither had been read when this was written or when it produced its
numbers; both were read afterwards, to verify an attribution, per the standing rule
that a borrowed instrument makes agreement meaningless. My pre-registered PASS
condition (R >= 2.0 and CI low > 1.5) turned out to be identical to the one
bandsignal.py encodes -- convergence, not copying. Decision rule and
kill condition are in PREREG-bandqual.md, committed at 11ede945 before this file ran.

THE MEASUREMENT. Defocus is a low-pass filter, so in a badly defocused tile whatever
fine-band power remains is the noise floor. Per tile, pick the probe frame where that
tile is most in focus and the one where it is least, and take the ratio of band power
between them. A band carrying scene structure gives a large ratio; a noise band gives 1.

THE TRAP, WHICH IS THE WHOLE DESIGN PROBLEM. Choosing the in-focus frame by the SAME
band being measured is an order statistic: the max over 32 draws of a pure noise field
beats the min over 32 draws by a wide margin, so a noise band would read R >> 1 and
qualify itself. That is how this measurement falsely passes. So focus is selected on a
band DISJOINT from the one being measured, and the residual inflation is measured by
three separate nulls rather than assumed to be zero.
"""
import os, sys, numpy as np
import softcheck as S, hsel as HS, hcoh as HC
import dmeasure as DM, d113recon as RC, ncurve as NC

T = DM.T; NB = DM.NB; E = DM.E
B_MEAS = 5                     # 0.30-0.35 cyc/output px -- where +0.0732 dex was measured
SEL = [1, 2]                   # 0.10-0.20 selection band, disjoint from B_MEAS
SEL_ALT = [0]                  # 0.05-0.10, robustness
D_ = r"C:\dev\strehl-out\V-SOFTCHECK\dilut"
SUBJECTS = {"113MSDCF":  (D_ + r"\113MSDCF\probe",  D_ + r"\113MSDCF\N063.tiff",  "2.33", 63),
            "bee-1-cpl": (D_ + r"\bee-1-cpl\probe", D_ + r"\bee-1-cpl\R299x1.tiff", "1.50", 299)}
SUBJ = sys.argv[1] if len(sys.argv) > 1 else "113MSDCF"
PDIR, REF, EXPO, NFRAMES = SUBJECTS[SUBJ]
MAX_SHIFT = T // 2
PASS_R, PASS_LO, NULL_MAX, FAIL_R = 2.0, 1.5, 1.3, 1.2   # from the pre-registration

def bname(b): return "%.2f-%.2f" % (E[b], E[b+1])

def ratio(P, idx, sel, meas, invert=False):
    """Median over tiles of P_meas(in-focus)/P_meas(defocused), as a linear ratio."""
    Sb = P[:, idx, :][:, :, sel].sum(axis=2)
    Mb = P[:, idx, meas]
    if invert: Sb = -Sb
    ti = np.arange(Sb.shape[1])
    best = Mb[np.argmax(Sb, axis=0), ti]; worst = Mb[np.argmin(Sb, axis=0), ti]
    g = np.isfinite(best) & np.isfinite(worst) & (best > 0) & (worst > 0)
    if g.sum() < 10: return np.nan, (np.nan, np.nan), int(g.sum())
    v = np.log10(best[g] / worst[g])
    r = np.random.default_rng(5); n = len(v)
    bs = [np.median(v[r.integers(0, n, n)]) for _ in range(2000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(10**np.median(v)), (float(10**lo), float(10**hi)), int(g.sum())

def fixed_ratio(P, idx, meas, ka, kb):
    """True ratio between two FIXED frames -- no selection, so no order statistic."""
    a = P[ka, idx, meas]; b = P[kb, idx, meas]
    g = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    return float(10**np.median(np.log10(a[g] / b[g])))

def gnorm(P, g):
    """Remove per-frame gain. Band power goes as gain^2 and the tile mean as gain^1,
    so a frame that is merely BRIGHTER has more power in every band at once and gets
    picked as 'in focus' by any band. Measured: this alone inflated the pure-noise
    null to 1.35 and would have qualified a noise band."""
    return P / (g[:, None, None] ** 2)

def stack_pow(frames, oy, ox):
    return np.stack([DM.bandpow(f, oy, ox)[0] for f in frames])

def synth_tiles(shape, step=T):
    H, W = shape[:2]
    ys = list(range(0, H - T, step)); xs = list(range(0, W - T, step))
    oy = []; ox = []
    for y in ys:
        for x in xs: oy.append(y); ox.append(x)
    return np.array(oy), np.array(ox)

def annulus(shape, lo, hi):
    fy = np.fft.fftfreq(shape[0]); fx = np.fft.fftfreq(shape[1])
    rr = np.hypot(*np.meshgrid(fy, fx, indexing="ij"))
    return (rr >= lo) & (rr < hi)

def band_scale(img, lo, hi, s):
    """Scale ONE annulus of a real image. A pixel-domain plant, not a scalar multiply:
    a scalar multiply shifts every band by log10(1/s) regardless of content and is the
    kind of control that cannot fail."""
    F = np.fft.fft2(img); F[annulus(img.shape, lo, hi)] *= s
    return np.real(np.fft.ifft2(F)).astype(np.float32)

def commission(ref, jit):
    print("COMMISSIONING bandqual -- four nulls and two signed controls\n")
    print("  per-frame gain jitter is MEASURED from the real probes, not invented: %.4f rel sd\n" % jit)
    ok = True
    H, W = ref.shape[:2]
    crop = ref[H//2-1024:H//2+1024, W//2-1024:W//2+1024].astype(np.float32)
    oy, ox = synth_tiles(crop.shape)
    sd = float(crop.std()); rng = np.random.default_rng(4242)
    K = 32
    print("  crop %dx%d, %d tiles, %d synthetic frames, sd %.1f" % (crop.shape[0], crop.shape[1], len(oy), K, sd))

    # C3 NOISE-STACK NULL -- pure noise, per-frame gain jitter. True R = 1.
    g = 1.0 + jit * rng.standard_normal(K)
    base = 1000.0
    fr = [((rng.standard_normal(crop.shape).astype(np.float32) * sd * 0.1 + base) * g[k]) for k in range(K)]
    if np.array_equal(fr[0], fr[1]): sys.exit("  COMMISSION FAIL: noise frames identical -- INERT")
    Pn_raw = stack_pow(fr, oy, ox)
    Pn = gnorm(Pn_raw, np.array([float(f.mean()) for f in fr]))
    idx = np.arange(len(oy))
    r_raw, _, _ = ratio(Pn_raw, idx, SEL, B_MEAS)
    r, ci, n = ratio(Pn, idx, SEL, B_MEAS)
    bad = not (r < NULL_MAX)
    print("  C3 NOISE-STACK NULL      R = %.4f  CI [%.4f, %.4f]  (true 1.000)  %s"
          % (r, ci[0], ci[1], "FAIL" if bad else "ok")); ok &= not bad
    print("     WITHOUT gain normalisation it reads %.4f -- a pure noise stack passing" % r_raw)
     
    print("     itself off as focus response, which is why the statistic is normalised.")
    same = ratio(Pn, idx, [B_MEAS], B_MEAS)[0]
    print("     same-band selection   R = %.4f  <- the trap I pre-registered: selecting on" % same)
    print("                                       the MEASURED band inflates pure noise by %.0f%%," % (100*(same-1)))
    print("                                       which is why selection is on a disjoint band.")
    del fr, Pn, Pn_raw

    # C4 BAND-INVARIANT NULL -- selection band varies hugely, measured band untouched.
    a = np.linspace(0.3, 1.0, K)
    fr = [band_scale(crop, E[SEL[0]], E[SEL[-1]+1], a[k]) +
          rng.standard_normal(crop.shape).astype(np.float32) * sd * 0.02 for k in range(K)]
    Pb = stack_pow(fr, oy, ox)
    sv = Pb[:, :, SEL].sum(axis=2).mean(axis=1)
    r, ci, n = ratio(Pb, idx, SEL, B_MEAS)
    bad = not (r < NULL_MAX)
    print("  C4 BAND-INVARIANT NULL   R = %.4f  CI [%.4f, %.4f]  (true 1.000)  %s"
          % (r, ci[0], ci[1], "FAIL" if bad else "ok")); ok &= not bad
    print("     selection band really did move: %.3f .. %.3f (%.2fx), measured band untouched"
          % (sv.min(), sv.max(), sv.max()/sv.min()))
    if sv.max()/sv.min() < 1.5: sys.exit("  COMMISSION FAIL: C4 selection did not move -- INERT plant"); 
    del fr, Pb

    # C5 KNOWN-RATIO POSITIVE CONTROL -- blur ladder, truth computed without selection.
    sig = np.linspace(0.0, 2.5, K)
    fr = [(crop if sig[k] == 0 else NC.gauss(crop, sig[k])) +
          rng.standard_normal(crop.shape).astype(np.float32) * sd * 0.005 for k in range(K)]
    Pk = stack_pow(fr, oy, ox)
    truth = fixed_ratio(Pk, idx, B_MEAS, 0, K-1)
    r, ci, n = ratio(Pk, idx, SEL, B_MEAS)
    err = abs(r - truth) / truth
    bad = not (err < 0.15 and r > PASS_R)
    print("  C5 KNOWN-RATIO POSITIVE  R = %.4f  vs TRUE %.4f  (err %.1f%%)  %s"
          % (r, truth, 100*err, "FAIL" if bad else "ok")); ok &= not bad
    print("     commissioned for MAGNITUDE, not merely direction")

    # C6 SIGNED CONTROL -- selection-sharp frame is deliberately band-SOFT. True R < 1.
    fr2 = [band_scale(band_scale(crop, E[SEL[0]], E[SEL[-1]+1], 0.3 + 0.7*k/(K-1)),
                      E[B_MEAS], E[B_MEAS+1], 1.0 - 0.7*k/(K-1)) +
           rng.standard_normal(crop.shape).astype(np.float32) * sd * 0.005 for k in range(K)]
    Ps = stack_pow(fr2, oy, ox)
    r, ci, n = ratio(Ps, idx, SEL, B_MEAS)
    bad = not (r < 1.0)
    print("  C6 SIGNED CONTROL        R = %.4f  CI [%.4f, %.4f]  (true < 1)  %s"
          % (r, ci[0], ci[1], "FAIL" if bad else "ok")); ok &= not bad
    print("     R is not bounded below by 1, so a non-responding band CAN be reported")
    del fr, Pk, fr2, Ps

    # C2 ALIGNER -- a wrong shift compares different scene content and lowers R.
    print("  C2 ALIGNER on this subject (planted roll -> recovered offset):")
    nf = 0
    for py, px in [(7, 11), (-5, 3), (0, 0)]:
        rr = np.roll(np.roll(crop, py, 0), px, 1)
        ry, rx = NC.align_int(crop, rr)
        good = (ry, rx) == (py, px); nf += 0 if good else 1
        print("     planted %+4d,%+4d  recovered %+4d,%+4d  %s" % (py, px, ry, rx, "ok" if good else "FAIL"))
    ok &= (nf == 0)
    print("\n  COMMISSIONING %s\n" % ("PASSED" if ok else "FAILED"))
    if not ok: sys.exit("ABORT: instrument not commissioned; no verdict is reportable")
    return True

def main():
    ref = DM.load(REF)
    oy, ox = HS.all_tiles(ref.shape)
    d_lo = RC.lopow(ref, oy, ox)
    ks = sorted(int(f[1:4]) for f in os.listdir(PDIR) if f.startswith("F") and f.endswith(".tiff"))
    print("PROBES: %d single frames, %s ... %s, step %d" % (len(ks), ks[0], ks[-1], ks[1]-ks[0]))
    Ps = []; gs = []; kept = []
    for k in ks:
        im = DM.load(os.path.join(PDIR, "F%03d.tiff" % k))
        sy, sx, _ = HS.align(ref, im, oy, ox)
        if abs(sy) > MAX_SHIFT or abs(sx) > MAX_SHIFT:
            print("  probe %3d shift(%+d,%+d) EXCEEDS T/2 -- rejected" % (k, sy, sx)); del im; continue
        a, mu = DM.bandpow(im, oy + sy, ox + sx)
        Ps.append(a); gs.append(float(np.nanmedian(mu))); kept.append((k, int(sy), int(sx))); del im
    P_raw = np.stack(Ps); gv = np.array(gs)
    jit = float(gv.std() / gv.mean())
    print("  per-frame level: %.1f .. %.1f, rel sd %.4f (%.2fx spread)"
          % (gv.min(), gv.max(), jit, gv.max()/gv.min()))
    P = gnorm(P_raw, gv)
    commission(ref, max(jit, 1e-4))
    print("  kept %d/%d probes; shifts %s" % (len(kept), len(ks),
          ", ".join("%d:(%+d,%+d)" % t for t in kept[:6]) + " ..."))
    fin = np.isfinite(P[:, :, 0]).all(axis=0) & np.isfinite(d_lo)
    idx = np.where(fin)[0]
    order = idx[np.argsort(d_lo[idx])]
    nd = len(order) // 10
    TOP = order[8*nd:]; FLAT = order[:2*nd]; ALL = order
    print("  tiles: %d valid, TOP(2 deciles) %d, FLAT(2 deciles) %d\n" % (len(order), len(TOP), len(FLAT)))

    print("QUALIFICATION -- in-focus / defocused band power, per-tile focus selection")
    print("  subject %s (N=%d), develop: --srgb --exposure %s, pin 44C2F2CD2E5B2894, no --auto-exposure\n"
          % (SUBJ, NFRAMES, EXPO))
    print("  %-11s %10s %10s %10s   %s" % ("band", "TOP", "FLAT", "ALL", "verdict(TOP)"))
    res = {}
    for b in range(NB):
        rt, cit, _ = ratio(P, TOP, SEL, b)
        rf, _, _ = ratio(P, FLAT, SEL, b)
        ra, _, _ = ratio(P, ALL, SEL, b)
        v = "PASS" if (rt >= PASS_R and cit[0] > PASS_LO and rf < NULL_MAX) else ("FAIL" if rt < FAIL_R else "MARGINAL")
        res[b] = (rt, cit, rf, ra, v)
        print("  %-11s %10.4f %10.4f %10.4f   %s%s" % (bname(b), rt, rf, ra, v,
              "   <-- MY OPERATING BAND" if b == B_MEAS else ""))
    rt, cit, rf, ra, v = res[B_MEAS]
    print("\n  %s: R_top = %.4f  CI [%.4f, %.4f]   R_flat = %.4f  (null, must be < %.2f)"
          % (bname(B_MEAS), rt, cit[0], cit[1], rf, NULL_MAX))
    Sb = P[:, TOP, :][:, :, SEL].sum(axis=2)
    pk = np.argmax(Sb, axis=0); interior = (pk > 0) & (pk < P.shape[0] - 1)
    TOPi = TOP[interior]
    ri, cii, _ = ratio(P, TOPi, SEL, B_MEAS)
    print("     interior-peak tiles only (%d/%d)   R_top = %.4f  CI [%.4f, %.4f]"
          % (len(TOPi), len(TOP), ri, cii[0], cii[1]))
    print("     TOP/FLAT scene-response ratio        %.4f" % (rt / rf))
    rr, _, _ = ratio(P_raw, TOP, SEL, B_MEAS)
    print("     without gain normalisation           R_top = %.4f" % rr)
    for tag, sel in [("0.10-0.20 (primary)", SEL), ("0.05-0.10 (robustness)", SEL_ALT)]:
        r2, c2, _ = ratio(P, TOP, sel, B_MEAS)
        print("     selection band %-24s R_top = %.4f  CI [%.4f, %.4f]" % (tag, r2, c2[0], c2[1]))
    print("\n  PRE-REGISTERED VERDICT for 0.30-0.35: %s" % v)
    if v == "PASS":
        print("  -> band carries focus-dependent signal on this develop path.")
        print("     +0.0732 dex (113MSDCF) and +0.0748 dex (bee) STAND, now qualified.")
    else:
        print("  -> +0.0732 / +0.0748 dex are WITHDRAWN as resolution claims.")
        low = [b for b in range(NB) if res[b][4] == "PASS"]
        print("     lowest qualifying band: %s" % (bname(min(low)) if low else "NONE"))
    np.savez(os.path.join(PDIR, "..", "bandqual-%s.npz" % SUBJ), P=P, P_raw=P_raw, gv=gv, d_lo=d_lo, oy=oy, ox=ox,
             TOP=TOP, FLAT=FLAT, ks=np.array([k for k, _, _ in kept]))

if __name__ == "__main__":
    main()
