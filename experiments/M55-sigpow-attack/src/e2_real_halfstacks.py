"""M55 E2 -- fact 620 end to end on REAL data, with NO plant anywhere, and the
common-power spectrum that says what the common mode actually is (PR2, PR8).

PRE-REGISTERED before this file existed.

M46's separation scores are all measured on a synthetic plant whose "fixed
pattern" is white noise at sqrt(rho)*sigma_single.  Fact 620 asserts the plant's
configuration IS two merges of disjoint half-stacks.  This script builds those
merges from real photons and runs the same contrast with no synthetic noise, no
synthetic fixed pattern and no synthetic blur in the SMOOTH arm.

DESIGN.  112MSDCF, first 76 frames, interleaved by stride 4 -> Q0..Q3, 19 frames
each.  Every quarter spans the SAME depth range, so the delivered scene is the
same and only the noise realisation differs.  Each quarter is merged with
m41lib.arm_A, imported frozen and unmodified.

    BASELINE pair   (Q0, Q1)                    n = 19 frames per merge
    SMOOTH pair     ((Q0+Q2)/2, (Q1+Q3)/2)      n = 38 -- EXACTLY k = sqrt(2)
                                                less independent noise, same
                                                scene, same fixed pattern,
                                                REAL photons
    BLUR pair       (blur(Q0,sb), blur(Q1,sb))  sb solved so hp_sd matches

This is b3's contrast with the plant deleted.  k = sqrt(2) is not chosen to
match b3; it is what disjoint-half averaging gives you, and b3 chose sqrt(2)
for the same reason.

RULE 20 -- the input that makes this FAIL.  A positive control ladder: extra
blur at sb = 0.05, 0.1, 0.2, 0.5 px on the BASELINE pair, with the predicted
sigpow response |H(f_sig)|^2 = exp(-4 pi^2 sb^2 f^2) printed next to the
measurement.  If sigpow does not track it, the instrument is dead and every S
below is meaningless.

RULE 10.  hp_sd here is a SPATIAL sd of a high-passed merged plane and is only
ever compared with another spatial sd of the same kind.  The DN^2 spectra are
calibrated against a white field of known variance (printed).
"""
import os, sys, glob, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
M46SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m46-detail-metric", "src")
M41SRC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m41-r3-kill", "src")
for p in (M46SRC, M41SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
import m46lib as M          # frozen, imported
import m41lib as L1         # frozen, imported
import m41lib3 as L3        # frozen, imported

STACK = r"D:\personal\macro\112MSDCF"
ROIS = {"detail": (1671, 1373, 512, 512), "flat": (2747, 32, 512, 512)}
PAD = 32
NFR = 76
G, RN_E = 1.14469, 1.47
F_SIG = M.F_SIG
NBIN = 64


def hann2(n):
    w1 = np.hanning(n)
    return np.outer(w1, w1)


def ring_masks(n, nbin=NBIN):
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    out = []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        if m.sum() >= 8:
            out.append((0.5 * (edges[i] + edges[i + 1]) / n, m))
    return out


def spectra(a, b, rings, w, wsum2):
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * w))
    cross, auto = [], []
    for _, m in rings:
        cross.append(float(np.real(np.sum(A[m] * np.conj(B[m]))) / m.sum() / wsum2))
        auto.append(float((np.abs(A[m]) ** 2).mean() / wsum2))
    return np.array(cross), np.array(auto)


def ring_power(a, f=F_SIG, nbin=NBIN):
    """b3_separation.ring_power, re-implemented here (b3 is frozen, rule 15).
    Verified against b3's own numbers in the log below."""
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


def metrics(y1, y2):
    fr = M.frc_at(y1, y2)
    pw = ring_power(y1)
    return dict(frc2_at_fsig=fr, hp_sd=M.hp_sd(y1), p_ratio=M.p_ratio(y1),
                mean_grad=M.mean_grad(y1), ringpow=pw, sigpow_fsig=fr * pw)


def sep(base, arm_b, arm_s, key):
    b, u, s = base[key], arm_b[key], arm_s[key]
    db, ds = (b - u) / abs(b), (b - s) / abs(b)
    tot = abs(db) + abs(ds)
    return db, ds, (abs(db) / tot if tot > 1e-12 else None)


def load_cube(files, roi, pad):
    import rawpy
    x, y, w, h = roi
    x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
    out = np.empty((len(files), y1 - y0, x1 - x0), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
            g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
        out[i] = 0.5 * (g1 + g2) - M.BLACK
    return out


def main():
    t0 = time.time()
    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))[:NFR]
    n = 512
    w = hann2(n)
    wsum2 = float((w ** 2).sum())
    rings = ring_masks(n)
    ff = np.array([f for f, _ in rings])
    print("=" * 78)
    print("M55 E2 -- fact 620 on REAL disjoint half-stacks, no plant (PR2, PR8)")
    print("=" * 78)
    print(f"   {len(files)} frames of 112MSDCF, stride 4 -> 4 quarters of "
          f"{len(files)//4} frames")

    rng = np.random.default_rng(5502)
    ref = rng.standard_normal((n, n)).astype(np.float32) * 3.7
    ref2 = rng.standard_normal((n, n)).astype(np.float32) * 3.7
    c0, a0 = spectra(ref, ref2, rings, w, wsum2)
    print(f"   DN^2 calibration: auto {a0.mean():.4f} (expect 13.690), cross-indep "
          f"{c0.mean():+.4f} (expect 0)")

    res = {"freqs": ff.tolist(), "rois": {}}

    for rname, roi in ROIS.items():
        print("\n" + "=" * 78)
        print(f"ROI {rname}  {roi}")
        print("=" * 78)
        cube = load_cube(files, roi, PAD)
        lvl = float(np.median(cube))
        sig1 = float(np.sqrt(0.5 * (G * lvl + (RN_E * G) ** 2)))
        print(f"   level {lvl:.2f} DN   model single-frame sd {sig1:.3f} DN")
        Q, NEFF = [], []
        for j in range(4):
            sub = cube[j::4]
            fine, coarse, reg = L1.focus_fields(sub, G, RN_E)
            m, wsel, nn = L1.arm_A(sub, coarse, reg)
            Q.append(m[PAD:-PAD, PAD:-PAD].astype(np.float32))
            NEFF.append(float(nn.mean()))
            print(f"   Q{j}: {sub.shape[0]} frames  mean n_eff {NEFF[-1]:.3f}  "
                  f"median {np.median(Q[-1]):.2f} DN")
        del cube

        base1, base2 = Q[0], Q[1]
        smo1, smo2 = 0.5 * (Q[0] + Q[2]), 0.5 * (Q[1] + Q[3])

        # ---- what IS the common mode?  (PR2)
        cross, auto = spectra(base1, base2, rings, w, wsum2)
        print("\n   COMMON-POWER SPECTRUM of the two quarter-merges, DN^2 per mode")
        print("   (a white common component of variance s^2 reads s^2 at every f)")
        print("      f      C(f) DN^2     P(f) DN^2     FRC(f)   C(f)/FPN_dark")
        FPN_DARK = 0.08341     # E1, ISO 500 dark, quad plane, cross-half covariance
        for target in (0.05, 0.10, 0.20, 0.2762, 0.35, 0.45, 0.49):
            i = int(np.argmin(np.abs(ff - target)))
            print(f"    {ff[i]:6.4f}  {cross[i]:12.4f}  {auto[i]:12.4f}   "
                  f"{cross[i]/auto[i]:+8.4f}   {cross[i]/FPN_DARK:12.1f}x")
        res["rois"][rname] = dict(level=lvl, sigma1=sig1, n_eff=NEFF,
                                  cross=cross.tolist(), auto=auto.tolist())

        # ---- rule 20 positive control: does sigpow track |H|^2 ?
        print("\n   RULE 20 POSITIVE CONTROL -- planted blur on the BASELINE pair.")
        print("   predicted sigpow ratio = |H(f_sig)|^2 = exp(-4 pi^2 sb^2 f^2)")
        m_base = metrics(base1, base2)
        ctrl = {}
        for sb in (0.05, 0.10, 0.20, 0.50, 1.00):
            mb = metrics(M.blur(base1, sb), M.blur(base2, sb))
            pred = float(np.exp(-4 * np.pi ** 2 * sb ** 2 * F_SIG ** 2))
            got = mb["sigpow_fsig"] / m_base["sigpow_fsig"]
            print(f"     sb={sb:4.2f} px   predicted {pred:.5f}   measured "
                  f"{got:.5f}   ratio {got/pred:.4f}")
            ctrl[sb] = dict(pred=pred, got=got)
        res["rois"][rname]["blur_control"] = ctrl

        # ---- the matched cost, solved on the REAL images
        tgt = M.hp_sd(smo1)
        lo, hi = 0.0, 4.0
        f_lo = M.hp_sd(base1) - tgt
        f_hi = M.hp_sd(M.blur(base1, hi)) - tgt
        sb = None
        if f_lo * f_hi <= 0:
            for _ in range(30):
                mid = 0.5 * (lo + hi)
                fm = M.hp_sd(M.blur(base1, mid)) - tgt
                if f_lo * fm <= 0:
                    hi, f_hi = mid, fm
                else:
                    lo, f_lo = mid, fm
            sb = 0.5 * (lo + hi)
        print(f"\n   MATCHED COST: hp_sd(baseline) {M.hp_sd(base1):.4f} -> "
              f"hp_sd(SMOOTH) {tgt:.4f}")
        print(f"   matched blur sb = " + ("NONE FEASIBLE" if sb is None else f"{sb:.5f} px"))
        if sb is None:
            res["rois"][rname]["sb"] = None
            continue
        blr1, blr2 = M.blur(base1, sb), M.blur(base2, sb)
        m_blur = metrics(blr1, blr2)
        m_smoo = metrics(smo1, smo2)
        print("\n   metric          baseline      BLUR-ONLY    SMOOTH-ONLY   "
              "d_blur   d_smooth      S")
        rows = {}
        for key in ("frc2_at_fsig", "hp_sd", "p_ratio", "mean_grad", "ringpow",
                    "sigpow_fsig"):
            db, ds, S = sep(m_base, m_blur, m_smoo, key)
            print(f"   {key:<14s} {m_base[key]:12.5g} {m_blur[key]:12.5g} "
                  f"{m_smoo[key]:12.5g} {db:+7.4f} {ds:+7.4f}  " +
                  ("  --  " if S is None else f"{S:6.3f}"))
            rows[key] = dict(base=m_base[key], blur=m_blur[key], smooth=m_smoo[key],
                             d_blur=db, d_smooth=ds, S=S)
        res["rois"][rname].update(sb=sb, rows=rows)

    with open(os.path.join(OUT, "e2_real.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/e2_real.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
