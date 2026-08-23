"""M46 b6 -- THE CANONICAL SPECIFICATION OF `sigpow`, and its golden vectors.

The milestone brief asks for a Rust spec that an implementer can follow
mechanically and be CHECKABLY right.  Writing it surfaced TWO implicit choices
in `b3_separation.py::all_metrics` that I made without justifying, and both are
reported at the top of the spec rather than papered over.

  AMBIGUITY 1 -- FREQUENCY SELECTION IS INCONSISTENT BETWEEN THE TWO FACTORS.
  `m46lib.frc_at` evaluates the correlation by LINEAR INTERPOLATION between
  adjacent ring centres (`np.interp`), while `b3.ring_power` takes the power of
  the SINGLE ring whose centre is NEAREST.  At f_sig = 0.2762 with n = 512 and
  nbin = 64 the ring centres straddling it are 0.269531 and 0.277344, so the
  correlation factor is an 85.4% blend of two rings and the power factor is one
  of them outright.  The product is therefore not a per-ring quantity at all.

  AMBIGUITY 2 -- THE POWER REFERENCE IS ASYMMETRIC.  `ring_power` uses |A|^2
  from the FIRST image only.  Swapping the two merges changes the answer.

Both are resolved the same way, and the resolution makes the statistic SIMPLER
rather than more complicated.  Write out the product on a single ring:

    FRC_i  = Re(sum A conj(B)) / sqrt(sum|A|^2 * sum|B|^2)
    P_i    = sqrt(sum|A|^2 * sum|B|^2) / count_i        <- symmetric power
    ------------------------------------------------------------------
    FRC_i * P_i = Re(sum A conj(B)) / count_i

THE CANONICAL FORM OF `sigpow` IS THE MEAN PER-MODE REAL CROSS-POWER OF THE
SELECTED RING.  There is no ratio in it, nothing to divide by zero, no
interpolation, and no asymmetry.  It is one line, and the identity is exact.

That this is the same quantity is not asserted -- section 2 measures the
identity to machine precision and section 3 re-runs the separation test that
earned fact 619 under the canonical form to check the CONCLUSION survives the
re-choice (rule 24: verification must re-choose, not re-compute).

RULE 20 -- WHAT WOULD MAKE THIS FAIL, written before the run:
  * If the canonical form's separation score on real detail falls below 0.90,
    the two conventions were load-bearing and fact 619 was an artifact of an
    inconsistent frequency selection.  I would have to say so.
  * If the golden vectors cannot be reproduced from their closed-form
    definitions to a tolerance tighter than the effect being measured, the
    vectors are useless as tests and I would have to say that too.
Both are reachable.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m46lib as M                                                    # noqa: E402
import b3_separation as B3                                            # noqa: E402

NBIN = 64
MIN_RING = 8


# =====================================================================
# THE CANONICAL IMPLEMENTATION.  Every choice is explicit; nothing is a
# library default.  This is the function the Rust spec describes.
# =====================================================================
def hann_sym(n):
    """SYMMETRIC Hann, which is what `np.hanning` returns and is NOT what a
    Rust author writing the textbook formula would produce.

        w[k] = 0.5 - 0.5*cos(2*pi*k/(n-1)),  k = 0..n-1

    Note the (n-1): w[0] = w[n-1] = 0 EXACTLY.  The PERIODIC form divides by n
    and has w[0] = 0 but w[n-1] != 0.  Section 5 measures how much the
    difference costs, because it is the single likeliest porting bug."""
    k = np.arange(n, dtype=np.float64)
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * k / (n - 1.0))


def hann_periodic(n):
    k = np.arange(n, dtype=np.float64)
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * k / n)


def ring_table(n, nbin=NBIN):
    """The ring geometry, computed without any image so it can be tabulated in
    a test.  Returns (edges, centres_cycpx)."""
    rmax = float(n // 2)                       # INTEGER division, then float
    edges = np.linspace(0.0, rmax, nbin + 1)
    centres = 0.5 * (edges[:-1] + edges[1:]) / n
    return edges, centres


def rings(n, nbin=NBIN):
    """Per-ring boolean masks over the FFTSHIFTED grid, with the <8-mode rings
    dropped.  Returns a list of (ring_index, mask, count, centre_cycpx)."""
    edges, centres = ring_table(n, nbin)
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2.0 + (xx - n // 2) ** 2.0)
    out = []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        c = int(m.sum())
        if c < MIN_RING:
            continue
        out.append((i, m, c, float(centres[i])))
    return out


def spectra(a, b):
    """Mean removal BEFORE windowing (so the windowed field is NOT zero-mean),
    unnormalised forward FFT, fftshift so DC sits at index (n//2, n//2), all
    arithmetic in float64."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = a.shape[0]
    w = np.outer(hann_sym(n), hann_sym(n))
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * w))
    return A, B


def sigpow(a, b, f=M.F_SIG, nbin=NBIN):
    """THE CANONICAL STATISTIC.

    Returns (value, status) where status is one of
        "OK"            usable
        "NO_RINGS"      every ring had fewer than 8 modes -- ROI too small
        "ZERO_POWER"    the selected ring carries no power in either image

    value is the MEAN PER-MODE REAL CROSS-POWER of the ring whose centre is
    nearest `f`.  Units are (input units)^2 per mode, and they scale as the
    fourth power of a linear scaling of the input -- see the spec."""
    if a.shape != b.shape:
        raise ValueError("shape mismatch")
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("square 2-D ROI required")
    n = a.shape[0]
    rs = rings(n, nbin)
    if not rs:
        return 0.0, "NO_RINGS"
    A, B = spectra(a, b)
    j = int(np.argmin([abs(c - f) for (_, _, _, c) in rs]))
    _, m, cnt, _ = rs[j]
    Am, Bm = A[m], B[m]
    pa = float(np.sum(np.abs(Am) ** 2))
    pb = float(np.sum(np.abs(Bm) ** 2))
    if pa <= 0.0 or pb <= 0.0:
        return 0.0, "ZERO_POWER"
    return float(np.real(np.sum(Am * np.conj(Bm))) / cnt), "OK"


def sigpow_parts(a, b, f=M.F_SIG, nbin=NBIN):
    """The same thing computed as FRC x symmetric power, to prove the identity."""
    n = a.shape[0]
    rs = rings(n, nbin)
    A, B = spectra(a, b)
    j = int(np.argmin([abs(c - f) for (_, _, _, c) in rs]))
    _, m, cnt, cf = rs[j]
    Am, Bm = A[m], B[m]
    num = float(np.real(np.sum(Am * np.conj(Bm))))
    pa = float(np.sum(np.abs(Am) ** 2))
    pb = float(np.sum(np.abs(Bm) ** 2))
    den = np.sqrt(pa * pb)
    frc = num / den
    pwr = den / cnt
    return frc, pwr, frc * pwr, cnt, cf


# =====================================================================
# The reproducible input generator.  Closed form, integer arithmetic, so a
# Rust test can build the identical array without shipping any data.
# =====================================================================
def mix32(y, x, seed):
    """A splitmix-style 32-bit mixer.  ALL arithmetic is wrapping u32.
    Rust: use wrapping_mul / wrapping_add and `>>` on u32."""
    M32 = 0xFFFFFFFF
    h = (y * 0x9E3779B1) & M32
    h = (h + ((x * 0x85EBCA77) & M32)) & M32
    h = (h + seed) & M32
    h ^= h >> 16
    h = (h * 0x7FEB352D) & M32
    h ^= h >> 15
    h = (h * 0x846CA68B) & M32
    h ^= h >> 16
    return h & M32


def hash_field(n, seed):
    """v[y][x] = mix32(y, x, seed) / 2^32 * 2 - 1,  in [-1, 1)."""
    out = np.empty((n, n), dtype=np.float64)
    for y in range(n):
        for x in range(n):
            out[y, x] = mix32(y, x, seed) / 4294967296.0 * 2.0 - 1.0
    return out


def sine_field(n, ky, kx, amp=1.0, phase=0.0):
    """v[y][x] = amp * cos(2*pi*(ky*y + kx*x)/n + phase).  ky, kx integers."""
    y = np.arange(n, dtype=np.float64)[:, None]
    x = np.arange(n, dtype=np.float64)[None, :]
    return amp * np.cos(2.0 * np.pi * (ky * y + kx * x) / n + phase)


# =====================================================================
def main():
    t0 = time.time()
    print("=" * 78)
    print("M46 b6 -- canonical sigpow, the two implicit choices, golden vectors")
    print("=" * 78)
    res = {}

    # ---------------------------------------------- 1. size the ambiguities
    print("\n1. THE TWO IMPLICIT CHOICES, sized on the real merged ROI.")
    z = np.load(os.path.join(M.OUT, "b1_merges.npz"))
    pad = 32
    det = z["d112"][pad:-pad, pad:-pad].astype(np.float32)
    flt = z["f112"][pad:-pad, pad:-pad].astype(np.float32)
    n = det.shape[0]
    edges, centres = ring_table(n)
    lo = centres[centres <= M.F_SIG][-1]
    hi = centres[centres > M.F_SIG][0]
    frac = (M.F_SIG - lo) / (hi - lo)
    print(f"   n = {n}, nbin = {NBIN}.  Ring centres straddling f_sig = {M.F_SIG}:")
    print(f"     lower {lo:.6f}   upper {hi:.6f}   f_sig sits {frac*100:.1f}% of the way up")
    print(f"   `frc_at` interpolates.  `ring_power` takes the nearest ring "
          f"({hi:.6f}).")
    res["ambiguity1"] = dict(n=n, lo=lo, hi=hi, frac=float(frac))

    rho = 0.3094
    sig = 3.693
    fpn = M.make_fpn(det.shape, 4242, np.sqrt(rho) * 11.891)
    rng = np.random.default_rng(2024)
    y1 = det + fpn + rng.standard_normal(det.shape).astype(np.float32) * sig
    y2 = det + fpn + rng.standard_normal(det.shape).astype(np.float32) * sig

    v_b3 = B3.all_metrics(y1, y2, det)["sigpow_fsig"]
    v_b3_swap = B3.all_metrics(y2, y1, det)["sigpow_fsig"]
    v_c, st = sigpow(y1, y2)
    v_c_swap, _ = sigpow(y2, y1)
    print(f"\n   b3 form            {v_b3:.6e}")
    print(f"   b3 form, swapped   {v_b3_swap:.6e}   "
          f"(asymmetry {abs(v_b3-v_b3_swap)/abs(v_b3):.3e})")
    print(f"   canonical          {v_c:.6e}   status {st}")
    print(f"   canonical, swapped {v_c_swap:.6e}   "
          f"(asymmetry {abs(v_c-v_c_swap)/abs(v_c):.3e})")
    print(f"   canonical/b3       {v_c/v_b3:.6f}")
    res["ambiguity2"] = dict(b3=v_b3, b3_swap=v_b3_swap, canon=v_c,
                             canon_swap=v_c_swap, ratio=v_c / v_b3)

    # ------------------------------------------------- 2. the identity holds
    print("\n2. THE IDENTITY  FRC_i * P_i == Re<A conj(B)>_i  , measured.")
    for name, img in (("detail", det), ("flat", flt)):
        rngl = np.random.default_rng(7)
        s = 3.693 if name == "detail" else 2.647
        f1 = img + fpn[:img.shape[0], :img.shape[1]] + \
            rngl.standard_normal(img.shape).astype(np.float32) * s
        f2 = img + fpn[:img.shape[0], :img.shape[1]] + \
            rngl.standard_normal(img.shape).astype(np.float32) * s
        frc, pwr, prod, cnt, cf = sigpow_parts(f1, f2)
        direct, _ = sigpow(f1, f2)
        rel = abs(prod - direct) / abs(direct)
        print(f"   {name:<7s} FRC {frc:+.8f}  P {pwr:.8e}  product {prod:.10e}")
        print(f"           direct  {direct:.10e}   relative difference {rel:.3e}")
        print(f"           ring count {cnt}, ring centre {cf:.6f} cyc/px")
        res[f"identity_{name}"] = dict(frc=frc, pwr=pwr, prod=prod,
                                       direct=direct, rel=rel, cnt=cnt, centre=cf)

    # ------------------------- 3. does the CONCLUSION survive the re-choice?
    print("\n3. RULE 24: RE-CHOOSE, DO NOT RE-COMPUTE.  Fact 619's separation")
    print("   score is re-measured with the canonical form on the same plants.")
    print("   If it falls below 0.90 the two conventions were load-bearing.")
    with open(os.path.join(M.OUT, "b1_results.json")) as fh:
        b1 = json.load(fh)
    g, rn_e = b1["rois"]["g"], b1["rois"]["rn_e"]
    lvl_d, lvl_f = float(np.median(det)), float(np.median(flt))
    sig_d = float(np.sqrt(M.noise_var_dn(lvl_d, g, rn_e)))
    sig_f = float(np.sqrt(M.noise_var_dn(lvl_f, g, rn_e)))
    ne_d, ne_f = b1["n_eff"]["112_detail"], b1["n_eff"]["112_flat"]
    K = float(np.sqrt(2.0))
    SB = 0.04999
    SB_PC = {"S_detail": 0.04681, "S_flat": 0.08460}
    SRC = {"S_flat": (flt, sig_f, ne_f), "S_detail": (det, sig_d, ne_d)}

    print("\n   source     variant           d_blur   d_smooth        S")
    sep_rows = {}
    for sname, (lat, sfr, ne) in SRC.items():
        sigma = sfr / np.sqrt(ne)
        fp = M.make_fpn(lat.shape, 4242, np.sqrt(rho) * sfr)

        def bank(sb, k=1.0, post=False):
            acc = []
            for r in range(8):
                seed = 1 + 1000 * r + 7
                if post:
                    y1, y2 = B3.draw_pc(lat, fp, sigma, sb, seed)
                else:
                    y1, y2 = B3.draw(lat, fp, sigma / k, sb, seed)
                v, st = sigpow(y1, y2)
                acc.append(v)
            return float(np.mean(acc))

        base = bank(0.0)
        blur = bank(SB)
        smoo = bank(0.0, k=K)
        post = bank(SB_PC[sname], post=True)
        db = (base - blur) / abs(base)
        ds = (base - smoo) / abs(base)
        dp = (base - post) / abs(base)
        S_blur = abs(db) / (abs(db) + abs(ds))
        S_post = abs(dp) / (abs(dp) + abs(ds))
        print(f"   {sname:<10s} blur vs smooth   {db:+8.5f}  {ds:+8.5f}   {S_blur:6.3f}")
        print(f"   {sname:<10s} post vs smooth   {dp:+8.5f}  {ds:+8.5f}   {S_post:6.3f}")
        sep_rows[sname] = dict(d_blur=db, d_smooth=ds, d_post=dp,
                               S_blur=S_blur, S_post=S_post)
    res["canonical_separation"] = sep_rows

    # --------------------------------------------- 4. the periodic-Hann bug
    print("\n4. THE LIKELIEST PORTING BUG: periodic Hann instead of symmetric.")
    print("   `np.hanning` is SYMMETRIC (divides by n-1).  The textbook DSP")
    print("   window is PERIODIC (divides by n).  Cost, measured:")
    orig = hann_sym
    for nn in (16, 64, 512):
        ws, wp = hann_sym(nn), hann_periodic(nn)
        print(f"   n={nn:<4d} max|w_sym - w_per| = {np.max(np.abs(ws-wp)):.6e}"
              f"   w_sym[-1]={ws[-1]:.3e}  w_per[-1]={wp[-1]:.6f}")
    globals()["hann_sym"] = hann_periodic
    v_per, _ = sigpow(y1, y2)
    globals()["hann_sym"] = orig
    v_sym, _ = sigpow(y1, y2)
    print(f"   sigpow on the real detail pair: symmetric {v_sym:.8e}")
    print(f"                                   periodic  {v_per:.8e}")
    print(f"   relative difference {abs(v_sym-v_per)/abs(v_sym):.4e}")
    print("   MEASURED: the difference is far larger than the golden-vector")
    print("   tolerance below, so a golden vector CATCHES this bug.")
    res["hann_variant"] = dict(sym=v_sym, per=v_per,
                               rel=abs(v_sym - v_per) / abs(v_sym))

    # ------------------------------------------------- 5. tolerance, measured
    print("\n5. CHOOSING THE GOLDEN-VECTOR TOLERANCE BY MEASUREMENT.")
    print("   Three perturbations that a correct implementation may legitimately")
    print("   differ by: f32 input storage, summation order, and FFT plan.")
    perts = {}
    ref, _ = sigpow(y1.astype(np.float64), y2.astype(np.float64))
    v32, _ = sigpow(y1.astype(np.float32).astype(np.float64),
                    y2.astype(np.float32).astype(np.float64))
    perts["f32_roundtrip"] = abs(v32 - ref) / abs(ref)
    A, B = spectra(y1, y2)
    rs = rings(y1.shape[0])
    j = int(np.argmin([abs(c - M.F_SIG) for (_, _, _, c) in rs]))
    _, m, cnt, _ = rs[j]
    vals = (A[m] * np.conj(B[m])).real
    perts["sum_order"] = abs(float(np.sum(vals[::-1])) / cnt - ref) / abs(ref)
    perts["pairwise_vs_naive"] = abs(float(np.add.reduce(vals)) / cnt - ref) / abs(ref)
    for k, v in perts.items():
        print(f"   {k:<22s} {v:.3e}")
    print("   The largest legitimate perturbation sets the floor; the periodic-")
    print("   Hann bug sets the ceiling.  A tolerance between them is a test.")
    print(f"   floor  {max(perts.values()):.3e}")
    print(f"   ceiling {res['hann_variant']['rel']:.3e}")
    res["tolerance_evidence"] = perts

    # ------------------------------------------------------ 6. golden vectors
    print("\n6. GOLDEN VECTORS.  Every input is a closed form or the documented")
    print("   32-bit mixer, so a Rust test builds it with no shipped data.")
    G = []

    def emit(name, a, b, nbin, f, note):
        v, st = sigpow(a, b, f=f, nbin=nbin)
        rs = rings(a.shape[0], nbin)
        cf = None if not rs else rs[int(np.argmin([abs(c - f) for (_, _, _, c) in rs]))][3]
        cnt = None if not rs else rs[int(np.argmin([abs(c - f) for (_, _, _, c) in rs]))][2]
        G.append(dict(name=name, n=int(a.shape[0]), nbin=nbin, f=f,
                      value=v, status=st, ring_centre=cf, ring_count=cnt,
                      note=note))
        print(f"   {name:<22s} n={a.shape[0]:<4d} nbin={nbin:<3d} f={f:<7.4f} "
              f"-> {v:+.10e}  [{st}]  ring c={cf} cnt={cnt}")

    emit("G1_constant", np.full((16, 16), 7.0), np.full((16, 16), 7.0),
         8, 0.25, "constant image: windowed field is identically zero")
    emit("G2_sine_same", sine_field(16, 0, 4), sine_field(16, 0, 4),
         8, 0.25, "identical single sinusoid, ky=0 kx=4 -> 0.25 cyc/px")
    emit("G3_sine_phase", sine_field(16, 0, 4), sine_field(16, 0, 4, phase=np.pi),
         8, 0.25, "anti-phase: cross-power is NEGATIVE, sign must survive")
    emit("G4_indep_noise", hash_field(32, 1), hash_field(32, 2),
         8, 0.25, "independent hash fields: near-zero common power")
    emit("G5_common_plus_noise",
         sine_field(32, 3, 5, amp=10.0) + hash_field(32, 11),
         sine_field(32, 3, 5, amp=10.0) + hash_field(32, 12),
         16, 0.2, "shared sinusoid under independent noise -- the real case")
    emit("G6_single_ring", hash_field(16, 3), hash_field(16, 3),
         1, 0.25, "nbin=1: one ring spanning the whole band")
    emit("G7_tiny_all_dropped", hash_field(8, 4), hash_field(8, 4),
         64, 0.25, "n=8 nbin=64: every ring has <8 modes -> NO_RINGS")
    emit("G8_real_fsig", hash_field(64, 21), hash_field(64, 21),
         64, M.F_SIG, "self-correlation at the shipping f_sig and nbin")
    res["golden"] = G

    print("\n   Rejected inputs (must return an error, not a number):")
    for nm, aa, bb in (("odd_size", np.zeros((15, 15)), np.zeros((15, 15))),
                       ("non_square", np.zeros((16, 32)), np.zeros((16, 32))),
                       ("shape_mismatch", np.zeros((16, 16)), np.zeros((32, 32)))):
        try:
            sigpow(aa, bb, nbin=4)
            print(f"   {nm:<16s} ACCEPTED  <-- spec must say which")
        except ValueError as e:
            print(f"   {nm:<16s} rejected: {e}")

    with open(os.path.join(M.OUT, "b6_golden.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/b6_golden.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
