"""M55 E3 -- WHY does sigpow behave differently on real merges?  Decompose it.

PRE-REGISTERED ADDENDUM (PR9, written after E2 and before this file ran):
  E2 measured S(sigpow) = 0.523 (detail) / 0.464 (flat) on real disjoint
  half-stack merges, against fact 619's 0.937 / 0.917 on the plant, with
  d_smooth NEGATIVE -- sigpow RISES under noise smoothing on real data.
  Fact 619's derivation says sigpow == C, the per-ring common power, which
  cannot move under a change to the independent noise.  Two candidate causes,
  and they are distinguishable:

  H1  IMPLEMENTATION.  b3 evaluates FRC by INTERPOLATION at f = 0.2762 and
      ring power at the ring whose CENTRE is nearest f (0.27734).  The two
      factors are therefore read at different frequencies.  Where the FRC curve
      is steep the product is not C.  PREDICTION: sigpow / C_direct != 1 at
      baseline, and a same-ring variant sigpow_ring restores S >= 0.9.
  H2  CONCEPT.  The real common power C really does move when the independent
      noise moves -- i.e. the identity sigpow = C fails on real merges for a
      reason that is not an indexing choice.  PREDICTION: C_direct itself moves
      under SMOOTH-ONLY by the same relative amount sigpow does.

  DECIDING RULE, fixed before the run: report H1 if |sigpow_ring/C_direct - 1|
  < 0.02 at every arm AND S(sigpow_ring) >= 0.90 on real detail; report H2 if
  C_direct's d_smooth is within 20% of sigpow's d_smooth.  Both can be true in
  part and the split is reported as measured.

Also here (PR7 on real data): a noise ladder built only from real frames --
eighth-stacks (9 frames), quarter-stacks (k = sqrt(2)), half-stacks (k = 2).
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
import m46lib as M
import m41lib as L1
import m41lib3 as L3

STACK = r"D:\personal\macro\112MSDCF"
ROIS = {"detail": (1671, 1373, 512, 512), "flat": (2747, 32, 512, 512)}
PAD, NFR, NPART = 32, 72, 8
G, RN_E = 1.14469, 1.47
F_SIG, NBIN = M.F_SIG, 64
CACHE = os.path.join(OUT, "e3_eighths.npz")


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


def build():
    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))[:NFR]
    d = {}
    for rname, roi in ROIS.items():
        cube = load_cube(files, roi, PAD)
        for j in range(NPART):
            sub = cube[j::NPART]
            fine, coarse, reg = L1.focus_fields(sub, G, RN_E)
            m, wsel, nn = L1.arm_A(sub, coarse, reg)
            d[f"{rname}_{j}"] = m[PAD:-PAD, PAD:-PAD].astype(np.float32)
            d[f"{rname}_{j}_neff"] = np.float32(nn.mean())
        del cube
    np.savez(CACHE, **d)
    return d


def rings_of(n, nbin=NBIN):
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    out = []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        if m.sum() >= 8:
            out.append((0.5 * (edges[i] + edges[i + 1]) / n, m, i))
    return out


N = 512
W = np.outer(np.hanning(N), np.hanning(N))
WS2 = float((W ** 2).sum())
RINGS = rings_of(N)
FF = np.array([f for f, _, _ in RINGS])
I_NEAR = int(np.argmin(np.abs(FF - F_SIG)))


def pair_stats(a, b):
    """Everything on ONE ring index (I_NEAR) plus b3's interpolated FRC, so the
    two conventions can be compared on identical data."""
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * W))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * W))
    _, m, _ = RINGS[I_NEAR]
    num = float(np.real(np.sum(A[m] * np.conj(B[m]))))
    pa = float((np.abs(A[m]) ** 2).mean())
    pb = float((np.abs(B[m]) ** 2).mean())
    den = float(np.sqrt(np.sum(np.abs(A[m]) ** 2) * np.sum(np.abs(B[m]) ** 2)))
    frc_ring = num / max(den, 1e-30)
    c_direct = num / m.sum()                      # per-mode common power, raw units
    frc_interp = M.frc_at(a, b)                   # b3's convention
    return dict(frc_ring=frc_ring, frc_interp=frc_interp, p_ring=pa, p_ring_b=pb,
                c_direct=c_direct,
                sigpow_b3=frc_interp * pa,        # exactly what b3 computes
                sigpow_ring=frc_ring * pa,        # same-ring variant
                hp_sd=M.hp_sd(a), mean_grad=M.mean_grad(a), p_ratio=M.p_ratio(a))


def sep(base, arm_b, arm_s, key):
    b, u, s = base[key], arm_b[key], arm_s[key]
    db, ds = (b - u) / abs(b), (b - s) / abs(b)
    tot = abs(db) + abs(ds)
    return db, ds, (abs(db) / tot if tot > 1e-12 else None)


def main():
    t0 = time.time()
    if os.path.exists(CACHE):
        d = dict(np.load(CACHE))
        print("   (using cached eighth-stack merges)")
    else:
        d = build()
    print("=" * 78)
    print("M55 E3 -- decomposing sigpow on real merges (H1 vs H2)")
    print("=" * 78)
    print(f"   ring index {I_NEAR}, centre {FF[I_NEAR]:.5f} cyc/px; "
          f"b3 interpolates FRC at f_sig = {F_SIG}")
    print(f"   adjacent ring centres {FF[I_NEAR-1]:.5f} / {FF[I_NEAR]:.5f} / "
          f"{FF[I_NEAR+1]:.5f}")
    res = {}

    for rname in ROIS:
        E = [d[f"{rname}_{j}"] for j in range(NPART)]
        neff = [float(d[f"{rname}_{j}_neff"]) for j in range(NPART)]
        print("\n" + "=" * 78)
        print(f"ROI {rname}   eighth-stack n_eff " +
              " ".join(f"{v:.2f}" for v in neff))
        print("=" * 78)

        # noise ladder from real frames only
        arms = {}
        arms["base(1/8)"] = (E[0], E[1])
        arms["k=sqrt2(1/4)"] = (0.5 * (E[0] + E[4]), 0.5 * (E[1] + E[5]))
        arms["k=2(1/2)"] = (0.25 * (E[0] + E[2] + E[4] + E[6]),
                            0.25 * (E[1] + E[3] + E[5] + E[7]))
        st = {k: pair_stats(*v) for k, v in arms.items()}

        print("\n   REAL NOISE LADDER (no synthetic anything)")
        print("   arm             FRC_ring  FRC_interp   P_ring      C_direct"
              "    sigpow_b3  sigpow_ring   b3/C   ring/C")
        for k, s in st.items():
            print(f"   {k:<15s} {s['frc_ring']:8.4f}  {s['frc_interp']:9.4f}  "
                  f"{s['p_ring']:11.4g}  {s['c_direct']:11.4g}  "
                  f"{s['sigpow_b3']:11.4g}  {s['sigpow_ring']:11.4g}  "
                  f"{s['sigpow_b3']/s['c_direct']:6.3f} "
                  f"{s['sigpow_ring']/s['c_direct']:7.4f}")

        res[rname] = dict(neff=neff, ladder={k: v for k, v in st.items()})

        # matched-cost separation at each k, blur solved on the real image
        for kname, kfac in (("k=sqrt2(1/4)", np.sqrt(2)), ("k=2(1/2)", 2.0)):
            base = arms["base(1/8)"]
            smoo = arms[kname]
            tgt = M.hp_sd(smoo[0])
            lo, hi = 0.0, 4.0
            f_lo = M.hp_sd(base[0]) - tgt
            f_hi = M.hp_sd(M.blur(base[0], hi)) - tgt
            if f_lo * f_hi > 0:
                print(f"\n   {kname}: NO FEASIBLE MATCHED BLUR")
                continue
            for _ in range(30):
                mid = 0.5 * (lo + hi)
                fm = M.hp_sd(M.blur(base[0], mid)) - tgt
                if f_lo * fm <= 0:
                    hi, f_hi = mid, fm
                else:
                    lo, f_lo = mid, fm
            sb = 0.5 * (lo + hi)
            blr = (M.blur(base[0], sb), M.blur(base[1], sb))
            sb_, ss_, sblur = pair_stats(*base), pair_stats(*smoo), pair_stats(*blr)
            print(f"\n   MATCHED-COST SEPARATION at {kname}, matched blur "
                  f"sb = {sb:.5f} px   (|H(f_sig)|^2 = "
                  f"{np.exp(-4*np.pi**2*sb**2*F_SIG**2):.5f})")
            print("   statistic        baseline      BLUR       SMOOTH     "
                  "d_blur   d_smooth      S")
            rows = {}
            for key in ("frc_ring", "frc_interp", "hp_sd", "mean_grad", "p_ratio",
                        "p_ring", "c_direct", "sigpow_b3", "sigpow_ring"):
                db, ds, S = sep(sb_, sblur, ss_, key)
                print(f"   {key:<15s} {sb_[key]:11.5g} {sblur[key]:11.5g} "
                      f"{ss_[key]:11.5g} {db:+8.4f} {ds:+8.4f}  " +
                      ("  --  " if S is None else f"{S:6.3f}"))
                rows[key] = dict(base=sb_[key], blur=sblur[key], smooth=ss_[key],
                                 d_blur=db, d_smooth=ds, S=S)
            res[rname][f"sep_{kname}"] = dict(sb=sb, rows=rows)

    with open(os.path.join(OUT, "e3_decompose.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/e3_decompose.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
