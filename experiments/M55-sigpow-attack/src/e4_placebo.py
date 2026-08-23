"""M55 E4 -- WHY does the per-ring common power C rise when the noise falls?
Two placebos (rule 11), pre-registered before the run.

E3 MEASURED, on real merges of 112MSDCF, that C_direct -- the per-ring common
power, which fact 619's derivation says IS sigpow and which "should not move"
under a change to the independent noise -- rises +27% (detail) and +812% (flat)
when the frame count doubles.  Three candidate mechanisms:

  M1  NONLINEAR MERGE.  arm_A's acceptance set is chosen from a NOISY focus
      field.  At 9 frames the selection is partly noise-driven, so the two
      half-merges deliver DIFFERENT scenes; as n grows the selection stabilises
      and the two delivered scenes converge, raising the common power.
      PLACEBO: a plain MEAN over the same frame subsets is linear and has no
      selection at all.  If C is flat under the mean, M1 is the mechanism.
  M2  FOCUS SAMPLING.  E0 = frames 0,8,16..., E1 = frames 1,9,17...; a quarter
      merge sees 2 of the 8 focus phases and a half merge 4.  Denser focus
      sampling is a REAL resolution gain, not a noise effect.  The mean placebo
      shares this confound, so M1 and M2 are separated by the second control.
  M3  ESTIMATOR BIAS.  C_direct = Re<A conj(B)>/M is unbiased only if the two
      images' noise is independent.  CONTROL: take the HALF-stack pair (the
      shipped configuration of fact 620) and add INDEPENDENT synthetic Gaussian
      noise to each until the total noise matches the eighth-stack pair.  The
      delivered scene is untouched by construction, so C must not move.  If it
      falls, C_direct is noise-biased and M3 is live.

DECIDING RULE, fixed before the run:
  * mean-placebo C flat within +-5% across the ladder            -> M1 confirmed
  * mean-placebo C rises by >=50% of arm_A's rise                -> M2 dominant
  * noise-add control moves C by more than 10%                   -> M3 live
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

STACK = r"D:\personal\macro\112MSDCF"
ROIS = {"detail": (1671, 1373, 512, 512), "flat": (2747, 32, 512, 512)}
PAD, NFR, NPART = 32, 72, 8
G, RN_E = 1.14469, 1.47
F_SIG, NBIN, N = M.F_SIG, 64, 512
CACHE = os.path.join(OUT, "e4_parts.npz")

W = np.outer(np.hanning(N), np.hanning(N))


def rings_of(n, nbin=NBIN):
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    out = []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        if m.sum() >= 8:
            out.append((0.5 * (edges[i] + edges[i + 1]) / n, m))
    return out


RINGS = rings_of(N)
FF = np.array([f for f, _ in RINGS])
I_NEAR = int(np.argmin(np.abs(FF - F_SIG)))
MASK = RINGS[I_NEAR][1]
NMODE = int(MASK.sum())


def stats(a, b):
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * W))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * W))
    num = float(np.real(np.sum(A[MASK] * np.conj(B[MASK]))))
    pa = float((np.abs(A[MASK]) ** 2).mean())
    pb = float((np.abs(B[MASK]) ** 2).mean())
    return dict(c=num / NMODE, pa=pa, pb=pb, frc=num / max(NMODE * np.sqrt(pa * pb), 1e-30),
                sigpow_b3=M.frc_at(a, b) * pa, hp_sd=M.hp_sd(a))


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
            d[f"A_{rname}_{j}"] = m[PAD:-PAD, PAD:-PAD].astype(np.float32)
            d[f"A_{rname}_{j}_neff"] = np.float32(nn.mean())
            d[f"MEAN_{rname}_{j}"] = sub.mean(0)[PAD:-PAD, PAD:-PAD].astype(np.float32)
        del cube
    np.savez(CACHE, **d)
    return d


def ladder(E):
    return {"1/8": (E[0], E[1]),
            "1/4": (0.5 * (E[0] + E[4]), 0.5 * (E[1] + E[5])),
            "1/2": (0.25 * (E[0] + E[2] + E[4] + E[6]),
                    0.25 * (E[1] + E[3] + E[5] + E[7]))}


def main():
    t0 = time.time()
    d = dict(np.load(CACHE)) if os.path.exists(CACHE) else build()
    print("=" * 78)
    print("M55 E4 -- placebos for the rise of C (M1 selection / M2 focus / M3 bias)")
    print("=" * 78)
    print(f"   ring {I_NEAR} centre {FF[I_NEAR]:.5f} cyc/px, {NMODE} modes")
    res = {}
    for rname in ROIS:
        print("\n" + "=" * 78)
        print(f"ROI {rname}")
        print("=" * 78)
        res[rname] = {}
        for tag, pref in (("arm_A (selector+estimator)", "A"), ("PLAIN MEAN (linear)", "MEAN")):
            E = [d[f"{pref}_{rname}_{j}"] for j in range(NPART)]
            L = ladder(E)
            print(f"\n   {tag}")
            print("     arm    C(f_sig)      P_a         P_b       P_a/P_b   FRC     "
                  "hp_sd    C / C(1/8)")
            c0 = None
            row = {}
            for k, (a, b) in L.items():
                s = stats(a, b)
                c0 = s["c"] if c0 is None else c0
                print(f"     {k:<5s} {s['c']:11.5g} {s['pa']:11.5g} {s['pb']:11.5g}  "
                      f"{s['pa']/s['pb']:7.4f} {s['frc']:7.4f} {s['hp_sd']:8.3f}   "
                      f"{s['c']/c0:8.4f}")
                row[k] = s
            res[rname][pref] = row

        # ---- M3 control: put the noise BACK into the shipped half-stack pair
        E = [d[f"A_{rname}_{j}"] for j in range(NPART)]
        L = ladder(E)
        h1, h2 = L["1/2"]
        b1, b2 = L["1/8"]
        s_half, s_base = stats(h1, h2), stats(b1, b2)
        # noise variance to add so the half pair's ring power matches the 1/8 pair
        add_pa = max(s_base["pa"] - s_half["pa"], 0.0)
        add_pb = max(s_base["pb"] - s_half["pb"], 0.0)
        wsum2 = float((W ** 2).sum())
        sd_a, sd_b = np.sqrt(add_pa / wsum2), np.sqrt(add_pb / wsum2)
        rng = np.random.default_rng(5504)
        print(f"\n   M3 CONTROL -- add {sd_a:.3f} / {sd_b:.3f} DN of INDEPENDENT white")
        print("   noise to the shipped 1/2 pair.  The delivered scene is untouched by")
        print("   construction, so C must not move.")
        accs = []
        for r in range(4):
            n1 = rng.standard_normal(h1.shape).astype(np.float32) * sd_a
            n2 = rng.standard_normal(h2.shape).astype(np.float32) * sd_b
            accs.append(stats(h1 + n1, h2 + n2))
        cm = float(np.mean([s["c"] for s in accs]))
        pm = float(np.mean([s["pa"] for s in accs]))
        frm = float(np.mean([s["frc"] for s in accs]))
        print(f"     1/2 pair            C {s_half['c']:11.5g}  P_a {s_half['pa']:11.5g}"
              f"  FRC {s_half['frc']:7.4f}")
        print(f"     1/2 + noise (x4)    C {cm:11.5g}  P_a {pm:11.5g}"
              f"  FRC {frm:7.4f}")
        print(f"     1/8 pair            C {s_base['c']:11.5g}  P_a {s_base['pa']:11.5g}"
              f"  FRC {s_base['frc']:7.4f}")
        print(f"     C moved by {100*(cm - s_half['c'])/s_half['c']:+7.3f}%  "
              f"(M3 is live if |.| > 10%)")
        res[rname]["m3"] = dict(half=s_half, noisy=dict(c=cm, pa=pm, frc=frm),
                                base=s_base, sd_a=float(sd_a), sd_b=float(sd_b))
    with open(os.path.join(OUT, "e4_placebo.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/e4_placebo.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
