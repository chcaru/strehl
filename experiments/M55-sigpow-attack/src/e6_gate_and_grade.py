"""M55 E6 -- (a) the PM_M fooling is graded, not an extreme-amplitude artefact;
(b) M46's proposed USE 3 for sigpow, run on real data: score the merge GATE
with it.

PRE-REGISTERED (PR10, PR11) before this file ran.

PR10  Sweep PM_M's blur over 0.25 / 0.5 / 1.0 / 2.0 px, each time solving the
      common fake-texture amplitude that restores hp_sd to baseline.  If sigpow
      reads AT OR ABOVE baseline at every width while oracle_mtf falls
      monotonically, PR5's result is a property of the statistic, not of one
      amplitude.

PR11  M46 sec 8 proposes sigpow to test "that gate width trades noise against
      resolution as claimed".  MECHANISM under test: E4 measured that the
      per-ring common power C rises when a merge's selection becomes less
      noise-driven.  A WIDER GATE accepts more frames per pixel, so it both
      averages more noise away AND stabilises the acceptance set -- while
      necessarily admitting more defocused frames, which must cost resolution.
      OBSERVABLE: sigpow(gate) on real disjoint half-stack merges of 112MSDCF,
      against hp_sd(gate) and against the merged noise proxy.  Reported with no
      expected direction (discipline 305).

`arm_A_gated` below is a COPY of m41lib.arm_A with GATE lifted to a parameter.
m41lib is not edited (rule 15).  At gate = 0.5 it must reproduce arm_A exactly
and that is asserted, not assumed (rule 36).
"""
import os, sys, glob, json, time
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

N, SEED_FPN, REPS = 512, 46046, 8
F_SIG, NBIN = M.F_SIG, 64
STACK = r"D:\personal\macro\112MSDCF"
ROIS = {"detail": (1671, 1373, 512, 512), "flat": (2747, 32, 512, 512)}
PAD, NFR = 32, 72
G, RN_E = 1.14469, 1.47

W = np.outer(np.hanning(N), np.hanning(N))
_yy, _xx = np.mgrid[0:N, 0:N]
_rr = np.sqrt((_yy - N // 2) ** 2 + (_xx - N // 2) ** 2)
_edges = np.linspace(0, N // 2, NBIN + 1)
_centres = 0.5 * (_edges[:-1] + _edges[1:]) / N
I_NEAR = int(np.argmin(np.abs(_centres - F_SIG)))
MASK = (_rr >= _edges[I_NEAR]) & (_rr < _edges[I_NEAR + 1])
NMODE = int(MASK.sum())


def ring_power(a):
    A = np.abs(np.fft.fftshift(np.fft.fft2((a - a.mean()) * W))) ** 2
    return float(A[MASK].mean())


def c_direct(a, b):
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * W))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * W))
    return float(np.real(np.sum(A[MASK] * np.conj(B[MASK]))) / NMODE)


def oracle_mtf(y, latent):
    Y = np.fft.fftshift(np.fft.fft2((y - y.mean()) * W))
    Lz = np.fft.fftshift(np.fft.fft2((latent - latent.mean()) * W))
    den = float(np.sum(np.abs(Lz[MASK]) ** 2))
    return None if den < 1e-30 else float(np.real(np.sum(Y[MASK] * np.conj(Lz[MASK]))) / den)


def arm_A_gated(cube, coarse, reg, gate):
    """COPY of m41lib.arm_A with GATE as a parameter.  m41lib is not edited."""
    w = np.argmax(reg, axis=0)
    peak = np.take_along_axis(coarse, w[None], 0)[0]
    acc = coarse >= (gate * peak)[None]
    acc[w, np.arange(cube.shape[1])[:, None], np.arange(cube.shape[2])[None]] = True
    n = acc.sum(0).astype(np.float32)
    s = (cube * acc).sum(0)
    return s / np.maximum(n, 1.0), w, n


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
    res = {}
    # ------------------------------------------------------------ PR10
    with open(os.path.join(M46OUT, "b1_results.json")) as fh:
        b1 = json.load(fh)
    z = np.load(os.path.join(M46OUT, "b1_merges.npz"))
    det = z["d112"][32:-32, 32:-32].astype(np.float32)
    g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]
    sig_d = float(np.sqrt(M.noise_var_dn(float(np.median(det)), g, rn_e)))
    ne_d, ne_f = b1["n_eff"]["112_detail"], b1["n_eff"]["112_flat"]
    rho = b1["twocap"]["flat"]["at_fsig"] / (1 - b1["twocap"]["flat"]["at_fsig"]) / ne_f
    sigma = sig_d / np.sqrt(ne_d)
    fpn = M.make_fpn(det.shape, SEED_FPN, np.sqrt(rho) * sig_d)
    rngT = np.random.default_rng(31337)
    T = rngT.standard_normal((N, N)).astype(np.float32)
    T = T - M.blur(T, 1.5)
    T = (T / T.std()).astype(np.float32)

    def draw(seed, sb, amp):
        rng = np.random.default_rng(seed)
        y1 = M.blur(det, sb) + fpn + rng.standard_normal(det.shape).astype(np.float32) * sigma + amp * T
        y2 = M.blur(det, sb) + fpn + rng.standard_normal(det.shape).astype(np.float32) * sigma + amp * T
        return y1, y2

    def bank(sb, amp, reps=REPS, base=1):
        acc = {}
        for r in range(reps):
            y1, y2 = draw(base + 1000 * r + 7, sb, amp)
            m = dict(hp_sd=M.hp_sd(y1), ringpow=ring_power(y1),
                     sigpow=M.frc_at(y1, y2) * ring_power(y1),
                     c_direct=c_direct(y1, y2), mean_grad=M.mean_grad(y1),
                     oracle_mtf=oracle_mtf(y1, det))
            for k, v in m.items():
                acc.setdefault(k, []).append(v)
        return {k: float(np.mean(v)) for k, v in acc.items()}

    b0 = bank(0.0, 0.0)
    print("=" * 78)
    print("M55 E6a (PR10) -- PM_M across blur widths.  Fake texture amplitude is")
    print("   solved at each width so hp_sd returns EXACTLY to baseline.")
    print("=" * 78)
    print(f"   baseline hp_sd {b0['hp_sd']:.4f}  sigpow {b0['sigpow']:.5g}  "
          f"oracle_mtf {b0['oracle_mtf']:.4f}")
    print("     sb    fake amp   hp_sd     oracle_mtf   sigpow/base  c_direct/base"
          "  mean_grad/base")
    pr10 = {}
    for sb in (0.25, 0.5, 1.0, 2.0):
        lo, hi = 0.0, 400.0
        for _ in range(28):
            mid = 0.5 * (lo + hi)
            if bank(sb, mid, reps=3, base=11)["hp_sd"] < b0["hp_sd"]:
                lo = mid
            else:
                hi = mid
        amp = 0.5 * (lo + hi)
        bm = bank(sb, amp)
        print(f"   {sb:5.2f}  {amp:9.3f}  {bm['hp_sd']:8.4f}  {bm['oracle_mtf']:10.4f}"
              f"   {bm['sigpow']/b0['sigpow']:11.4f}  {bm['c_direct']/b0['c_direct']:12.4f}"
              f"  {bm['mean_grad']/b0['mean_grad']:13.4f}")
        pr10[sb] = dict(amp=amp, **bm)
    res["pr10"] = dict(base=b0, rows=pr10)

    # ------------------------------------------------------------ PR11
    print("\n" + "=" * 78)
    print("M55 E6b (PR11) -- score the merge GATE with sigpow, on real data")
    print("=" * 78)
    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))[:NFR]
    GATES = [0.0, 0.25, 0.5, 0.75, 0.9, 0.99]
    for rname, roi in ROIS.items():
        cube = load_cube(files, roi, PAD)
        halves = [cube[0::2], cube[1::2]]
        ff = [L1.focus_fields(h, G, RN_E) for h in halves]
        print(f"\n   ROI {rname}: two disjoint half-stacks of {halves[0].shape[0]} "
              f"frames (fact 620's shipped configuration)")
        print("     gate   n_eff    level DN    hp_sd     P_ring      C_direct"
              "     sigpow    sigpow/gate0.5")
        rows = {}
        ref = None
        for gate in GATES:
            ms = []
            neffs = []
            for h, (fine, coarse, reg) in zip(halves, ff):
                m, wsel, nn = arm_A_gated(h, coarse, reg, gate)
                ms.append(m[PAD:-PAD, PAD:-PAD].astype(np.float32))
                neffs.append(float(nn.mean()))
            if gate == 0.5:
                mref, _, _ = L1.arm_A(halves[0], ff[0][1], ff[0][2])
                same = np.array_equal(mref[PAD:-PAD, PAD:-PAD].astype(np.float32), ms[0])
                print(f"     (rule 36 check: arm_A_gated(0.5) == m41lib.arm_A -> {same})")
                assert same, "gated copy diverges from m41lib.arm_A at gate=0.5"
            sp = M.frc_at(*ms) * ring_power(ms[0])
            cd = c_direct(*ms)
            lvl = float(np.median(ms[0]))
            if ref is None and gate == 0.5:
                ref = sp
            rows[gate] = dict(neff=neffs, level=lvl, hp_sd=M.hp_sd(ms[0]),
                              p_ring=ring_power(ms[0]), c_direct=cd, sigpow=sp)
            print(f"     {gate:5.2f}  {np.mean(neffs):6.3f}  {lvl:10.3f}  "
                  f"{M.hp_sd(ms[0]):8.3f}  {ring_power(ms[0]):11.5g}  {cd:11.5g}"
                  f"  {sp:11.5g}", end="")
            print("" if ref is None else f"  {sp/ref:15.4f}")
        # fix the ratio column for rows printed before gate 0.5
        for gate in GATES:
            rows[gate]["sigpow_rel"] = rows[gate]["sigpow"] / rows[0.5]["sigpow"]
        print("     sigpow relative to gate 0.5: " +
              "  ".join(f"{g}:{rows[g]['sigpow_rel']:.4f}" for g in GATES))
        print("     level  relative to gate 0.5: " +
              "  ".join(f"{g}:{rows[g]['level']/rows[0.5]['level']:.5f}" for g in GATES))
        res.setdefault("pr11", {})[rname] = rows
        del cube, halves, ff

    with open(os.path.join(OUT, "e6_gate.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/e6_gate.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
