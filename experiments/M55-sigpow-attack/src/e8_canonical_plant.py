"""M55 E8 -- attack the CANONICAL sigpow (M46 Appendix A, a632e46).

PRE-REGISTERED as PR14, PR15, PR16, PR20, PR21 before this file ran.

canon() below is MY OWN implementation of Appendix A.1, written from the prose.
It does not import b6_spec or b3_separation.  A.6's checklist is followed
literally: mean-remove then symmetric Hann, unnormalised full complex fft2,
fftshift, rmax = n//2, linspace edges, [lo,hi), drop count<8, compact, nearest
surviving centre, return Re(sum A conj(B))/count.
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

F_SIG, NBIN, SEED_FPN, REPS = M.F_SIG, 64, 46046, 8


# ----------------------------------------------------------------- Appendix A
def _rings(n, nbin):
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    out = []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        c = int(m.sum())
        if c < 8:
            continue                                   # A.1.8 drop + compact
        out.append((m, c, 0.5 * (edges[i] + edges[i + 1]) / n))
    return out


def _spectra(a, b, periodic=False, norm=None):
    n = a.shape[0]
    k = np.arange(n)
    w1 = (0.5 - 0.5 * np.cos(2 * np.pi * k / n) if periodic
          else 0.5 - 0.5 * np.cos(2 * np.pi * k / (n - 1)))   # A.1.4 symmetric
    w = np.outer(w1, w1)
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * w, norm=norm))  # A.1.3/.5/.6
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * w, norm=norm))
    return A, B


def canon(a, b, f=F_SIG, nbin=NBIN, **kw):
    """CANONICAL sigpow, A.1.10.  Returns (value, status)."""
    rs = _rings(a.shape[0], nbin)
    if not rs:
        return 0.0, "NO_RINGS"
    A, B = _spectra(a, b, **kw)
    j = int(np.argmin([abs(c - f) for (_, _, c) in rs]))       # A.1.9
    m, cnt, _ = rs[j]
    Am, Bm = A[m], B[m]
    pa, pb = float(np.sum(np.abs(Am) ** 2)), float(np.sum(np.abs(Bm) ** 2))
    if pa <= 0.0 or pb <= 0.0:
        return 0.0, "ZERO_POWER"
    return float(np.real(np.sum(Am * np.conj(Bm))) / cnt), "OK"


def factors(a, b, f=F_SIG, nbin=NBIN, **kw):
    """The two factors A.0.3 says multiply to canon()."""
    rs = _rings(a.shape[0], nbin)
    A, B = _spectra(a, b, **kw)
    j = int(np.argmin([abs(c - f) for (_, _, c) in rs]))
    m, cnt, _ = rs[j]
    Am, Bm = A[m], B[m]
    num = float(np.real(np.sum(Am * np.conj(Bm))))
    mag = float(np.abs(np.sum(Am * np.conj(Bm))))
    den = float(np.sqrt(np.sum(np.abs(Am) ** 2) * np.sum(np.abs(Bm) ** 2)))
    old_p = float(np.mean(np.abs(Am) ** 2))          # b3's ring_power: |A|^2 only
    return dict(frc_re=num / den, frc_mag=mag / den, p_geo=den / cnt,
                p_old=old_p, cnt=cnt, num=num, den=den)


res = {}
t0 = time.time()
print("=" * 78)
print("M55 E8 (PR14) -- is A.0.3's identity a measurement or algebra?")
print("=" * 78)
print("   A.0.3 verifies FRC_i * P_i == Re(sum A conj B)/count to 1.4e-16.")
print("   DERIVED: FRC_i = num/den and P_i = den/count, so the product is")
print("   num/count for ANY complex A,B with den > 0.  The den cancels.  This")
print("   is cancellation of a common factor, not a property of images.")
print("   Testing whether ANY of the conventions the spec agonises over can")
print("   break it.  If none can, the 1.4e-16 has no power (rule 21).\n")
rng = np.random.default_rng(5150)
cases = {
    "ordinary real, n=64":      (rng.standard_normal((64, 64)), rng.standard_normal((64, 64))),
    "ODD n=65":                 (rng.standard_normal((65, 65)), rng.standard_normal((65, 65))),
    "anti-correlated (neg)":    None,
    "1e8 dynamic range":        (rng.standard_normal((64, 64)) * 1e8, rng.standard_normal((64, 64)) * 1e-4),
    "COMPLEX-valued input":     (rng.standard_normal((64, 64)) + 1j * rng.standard_normal((64, 64)),
                                 rng.standard_normal((64, 64)) + 1j * rng.standard_normal((64, 64))),
    "identical a is b":         None,
}
s = rng.standard_normal((64, 64))
cases["anti-correlated (neg)"] = (s, -s + 0.01 * rng.standard_normal((64, 64)))
cases["identical a is b"] = (s, s)
print("   case                        Re-form FRC*P vs canon   MAG-form FRC*P vs canon")
pr14 = {}
for name, (a, b) in cases.items():
    for kw, tag in (({}, ""), ({"periodic": True}, " +periodic Hann"),
                    ({"norm": "ortho"}, " +ortho FFT")):
        if tag and name != "ordinary real, n=64":
            continue
        fx = factors(a, b, **kw)
        v = canon(a, b, **kw)[0]
        re_rel = abs(fx["frc_re"] * fx["p_geo"] - v) / max(abs(v), 1e-300)
        mg_rel = abs(fx["frc_mag"] * fx["p_geo"] - v) / max(abs(v), 1e-300)
        print(f"   {name+tag:<28} {re_rel:>13.3e}          {mg_rel:>13.3e}"
              + ("   <-- MAG-form BREAKS" if mg_rel > 1e-9 else ""))
        pr14[name + tag] = dict(re_rel=re_rel, mag_rel=mg_rel, value=v)
res["pr14"] = pr14
print("\n   The Re-form identity is exact under EVERY convention including odd n,")
print("   complex input, ortho FFT and the wrong window.  It is algebra.")
print("   The MAGNITUDE form of FRC -- the other standard convention, and the")
print("   one m41lib's docstring describes -- BREAKS it wherever cross-power")
print("   is negative.  That is an UNSTATED CONDITION on A.0.3.")

# ------------------------------------------------------------------ PR21
print("\n" + "=" * 78)
print("M55 E8 (PR21) -- b6_spec.py:129 says 'fourth power'.  Measure it.")
print("=" * 78)
a0, b0 = cases["ordinary real, n=64"]
v0 = canon(a0, b0)[0]
print("      lam    both inputs scaled     exponent      one input scaled   exponent")
pr21 = {}
for lam in (2.0, 3.0, 10.0):
    vb = canon(a0 * lam, b0 * lam)[0]
    vo = canon(a0 * lam, b0)[0]
    eb = np.log(vb / v0) / np.log(lam)
    eo = np.log(vo / v0) / np.log(lam)
    print(f"    {lam:6.1f}    {vb/v0:18.12f}   {eb:8.5f}   {vo/v0:16.12f}   {eo:8.5f}")
    pr21[lam] = dict(both=vb / v0, e_both=eb, one=vo / v0, e_one=eo)
res["pr21"] = pr21

# ------------------------------------------------------------------ plant
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
N = det.shape[0]

Wl = np.outer(np.hanning(N), np.hanning(N))
_y, _x = np.mgrid[0:N, 0:N]
_r = np.sqrt((_y - N // 2) ** 2 + (_x - N // 2) ** 2)
_e = np.linspace(0, N // 2, NBIN + 1)
_c = 0.5 * (_e[:-1] + _e[1:]) / N
_I = int(np.argmin(np.abs(_c - F_SIG)))
_MK = (_r >= _e[_I]) & (_r < _e[_I + 1])


def old_sigpow(y1, y2):
    Aa = np.abs(np.fft.fftshift(np.fft.fft2((y1 - y1.mean()) * Wl))) ** 2
    return M.frc_at(y1, y2) * float(Aa[_MK].mean())


def oracle_mtf(y):
    Y = np.fft.fftshift(np.fft.fft2((y - y.mean()) * Wl))
    Lz = np.fft.fftshift(np.fft.fft2((det - det.mean()) * Wl))
    return float(np.real(np.sum(Y[_MK] * np.conj(Lz[_MK]))) / np.sum(np.abs(Lz[_MK]) ** 2))


def bank(drawer, reps=REPS, base=1):
    acc = {}
    for r in range(reps):
        y1, y2 = drawer(base + 1000 * r + 7)
        m = dict(canon=canon(y1, y2)[0], old=old_sigpow(y1, y2),
                 hp_sd=M.hp_sd(y1), oracle_mtf=oracle_mtf(y1))
        for k, v in m.items():
            acc.setdefault(k, []).append(v)
    return {k: float(np.mean(v)) for k, v in acc.items()}


def plain(sb=0.0, k=1.0, gain=1.0, post=0.0, gam=1.0, amp=0.0, T=None):
    def d(seed):
        rng = np.random.default_rng(seed)
        o = []
        for _ in range(2):
            y = M.blur(det, sb) + fpn + rng.standard_normal(det.shape).astype(np.float32) * (sigma / k)
            if amp:
                y = y + amp * T
            if post:
                y = gam * M.blur(y, post)
            o.append((y * gain).astype(np.float32))
        return o
    return d


def S(base, blur, smooth, key):
    db = (base[key] - blur[key]) / abs(base[key])
    ds = (base[key] - smooth[key]) / abs(base[key])
    return abs(db) / (abs(db) + abs(ds) + 1e-300), db, ds


def solve_sb(target_hp, k=1.0, lo=0.0, hi=1.5):
    for _ in range(34):
        mid = 0.5 * (lo + hi)
        if bank(plain(sb=mid), reps=3, base=11)["hp_sd"] > target_hp:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


print("\n" + "=" * 78)
print("M55 E8 (PR15) -- canonical vs old separation, ONE independent harness")
print("=" * 78)
b = bank(plain())
pr15 = {}
for k in (1.05, 1.414, 2.0, 8.0):
    sm = bank(plain(k=k))
    sb = solve_sb(sm["hp_sd"])
    bl = bank(plain(sb=sb))
    sc, dbc, dsc = S(b, bl, sm, "canon")
    so, dbo, dso = S(b, bl, sm, "old")
    if abs(k - 1.414) < 1e-6:
        pf = bank(plain(post=sb))
        spc = S(b, pf, sm, "canon")[0]
        spo = S(b, pf, sm, "old")[0]
        print(f"   matched sb = {sb:.5f} px   (b3 published 0.04999)")
        print(f"   k=sqrt2  S(canon) {sc:.3f}   S(old) {so:.3f}"
              f"   |  post-filter: S(canon) {spc:.3f}  S(old) {spo:.3f}")
        print(f"            d_blur(canon) {dbc:+.5f}  d_smooth(canon) {dsc:+.5f}")
        pr15["postfilter"] = dict(canon=spc, old=spo)
    else:
        print(f"   k={k:<6} sb={sb:.5f}  S(canon) {sc:.3f}   S(old) {so:.3f}")
    pr15[k] = dict(sb=sb, canon=sc, old=so, d_blur=dbc, d_smooth=dsc)
res["pr15"] = pr15

print("\n" + "=" * 78)
print("M55 E8 (PR16) -- does the canonical form fix the rule-18 inversion?")
print("=" * 78)
rngT = np.random.default_rng(31337)
T = rngT.standard_normal((N, N)).astype(np.float32)
T = ((T - M.blur(T, 1.5)) / (T - M.blur(T, 1.5)).std()).astype(np.float32)
print("   PM_M: destroy resolution, add fixed structure COMMON to both halves,")
print("   amplitude re-solved so hp_sd returns to baseline.  d per A.4.1.")
print("   A.4.2: |d|<0.0005 no claim | d>+0.003 lost signal | d<-0.003 MORE signal")
print("\n      sb    fake amp   hp_sd    true MTF    d(canon)     d(old)    A.4.2 says")
pr16 = {}
for sb in (0.25, 0.5, 1.0, 2.0):
    lo, hi = 0.0, 400.0
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        if bank(plain(sb=sb, amp=mid, T=T), reps=3, base=11)["hp_sd"] < b["hp_sd"]:
            lo = mid
        else:
            hi = mid
    bm = bank(plain(sb=sb, amp=0.5 * (lo + hi), T=T))
    dc = (b["canon"] - bm["canon"]) / abs(b["canon"])
    do = (b["old"] - bm["old"]) / abs(b["old"])
    verdict = ("MORE signal" if dc < -0.003 else
               "lost signal" if dc > 0.003 else "no claim")
    print(f"    {sb:5.2f}  {0.5*(lo+hi):9.3f}  {bm['hp_sd']:8.4f}  {bm['oracle_mtf']:8.4f}"
          f"  {dc:+10.5f}  {do:+9.5f}    {verdict}")
    pr16[sb] = dict(amp=0.5 * (lo + hi), mtf=bm["oracle_mtf"], d_canon=dc, d_old=do)
res["pr16"] = pr16

print("\n" + "=" * 78)
print("M55 E8 (PR20) -- A.4.2's thresholds against degree-2 gain sensitivity")
print("=" * 78)
print("   DERIVED: gain (1+eps) on the test merge gives d = 1-(1+eps)^2 ~ -2eps.")
print("      eps      d(measured)   saturates which A.4.2 threshold")
pr20 = {}
for eps in (0.00025, 0.0005, 0.0015, 0.003, 0.01, 0.117):
    bg = bank(plain(gain=1 + eps))
    d = (b["canon"] - bg["canon"]) / abs(b["canon"])
    lab = ("exceeds the +-0.003 DECISION threshold" if abs(d) > 0.003 else
           "exceeds the 0.0005 no-claim floor" if abs(d) > 0.0005 else "below the floor")
    print(f"   {eps:8.5f}   {d:+11.6f}   {lab}")
    pr20[eps] = d
res["pr20"] = pr20
print("   PR11 MEASURED real merge-gate configurations differ in median level by")
print("   up to 11.7 %.  The last row is that case.")

with open(os.path.join(OUT, "e8_canonical.json"), "w") as fh:
    json.dump(res, fh, indent=2, default=float)
print(f"\nwrote out/e8_canonical.json  ({time.time()-t0:.1f}s)")
