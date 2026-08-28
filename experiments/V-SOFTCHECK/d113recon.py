"""Why does my own standing 0.114 not reproduce?  Reconciling two functionals.

THE PUBLISHED NUMBER (docs/research/V-SOFTCHECK-nyquist.md, fact 1789) is a
DIFFERENCE OF MEDIANS OF PER-ARM RATIOS:

    median_t(S32_t/D_t) - median_t(S63_t/D_t) = 0.7203 - 0.6063 = 0.1140

THE NEW NUMBER (d113measure.py) is a MEDIAN OF PER-TILE RATIOS:

    median_t(S32_t/S63_t) = 1.0016,  i.e. -0.0007 dex

D cancels EXACTLY in the second and does NOT cancel in the first.  median(u)/median(v)
is evaluated at two different tiles and depends on the joint distribution of
(S32, S63, D).  The old instrument justified itself with "the denominator is identical
between arms and every difference is the merge".  That sentence is true of a per-tile
ratio and FALSE of a ratio of medians.

This script needs NO reference frames: it measures how much of the 0.114 is explained
by (a) the tile set and (b) the aggregation functional, using the two masters alone.
The 63-frame arm here is BYTE-IDENTICAL to the one the 0.114 was measured on
(sha256 3C097FBA746B9955...), so the pixels are not in question.

CONTROLS.  Two nulls that must read exactly zero, one planted uniform scaling that
both functionals must recover, and -- the load-bearing one -- a planted ratio field
whose true per-tile median is exactly 1.000 by construction but which is correlated
with D.  A functional that reports a deficit there is reporting the denominator.
"""
import os, sys, json, numpy as np, softcheck as S, hsel as HS
import dmeasure as DM

DIR = r"C:\dev\strehl-out\V-SOFTCHECK\dilut\113MSDCF"
A32 = os.path.join(DIR, "N032.tiff")
A63 = os.path.join(DIR, "N063.tiff")
CACHE = os.path.join(S.ROOT, "cache", "113MSDCF--lin--T128.npz")
T = DM.T
NT_OLD = 300
PUB32, PUB63 = 0.7203, 0.6063

f1 = np.fft.fftfreq(T)
RR = np.hypot(*np.meshgrid(f1, f1, indexing="ij"))
LOM = (RR >= 0.02) & (RR < 0.05)

def lopow(img, oy, ox):
    """Low-band (0.02-0.05 cyc/px) tile energy -- the old tile-selection statistic."""
    H, W = img.shape[:2]
    out = np.full(len(oy), np.nan)
    for i in range(len(oy)):
        y = int(oy[i]); x = int(ox[i])
        if y < 0 or x < 0 or y + T > H or x + T > W: continue
        t = img[y:y+T, x:x+T]
        F = np.fft.fft2((t - t.mean()) * DM.WIN)
        out[i] = (F.real**2 + F.imag**2)[LOM].mean()
    return out

def mor(a, b):
    """Median of per-tile ratios, in dex.  D-free by construction."""
    g = (a > 0) & (b > 0) & np.isfinite(a) & np.isfinite(b)
    return float(np.median(np.log10(a[g] / b[g]))), int(g.sum())

def rom(a, b, d):
    """Ratio of medians of per-arm ratios to a COMMON denominator d, in dex.
    This is the published functional.  d is identical between arms; the question is
    whether that is sufficient for it to cancel."""
    g = (a > 0) & (b > 0) & np.isfinite(a) & np.isfinite(b) & np.isfinite(d) & (d > 0)
    ma = np.median(a[g] / d[g]); mb = np.median(b[g] / d[g])
    return float(np.log10(ma / mb)), float(ma), float(mb), int(g.sum())

def boot_mor(a, b, B=2000, seed=7):
    g = (a > 0) & (b > 0) & np.isfinite(a) & np.isfinite(b)
    v = np.log10(a[g] / b[g]); r = np.random.default_rng(seed); n = len(v)
    return np.percentile([np.median(v[r.integers(0, n, n)]) for _ in range(B)], [2.5, 97.5])

def controls(s32, s63, d):
    print("COMMISSIONING THE TWO FUNCTIONALS")
    ok = True
    if np.allclose(s63, s63[0]):
        sys.exit("  ABORT: band power array is constant -- a null on it would be trivial")
    print("    key non-trivial: %d distinct tile values, spread %.3f dex"
          % (len(np.unique(np.round(s63, 6))),
             float(np.log10(np.nanmax(s63) / np.nanmin(s63[s63 > 0])))))
    m, _ = mor(s63, s63); r, _, _, _ = rom(s63, s63, d)
    print("    NULL identical arm      mor %+.6f dex   rom %+.6f dex   (both must be 0)" % (m, r))
    ok &= abs(m) < 1e-12 and abs(r) < 1e-12
    m, _ = mor(1.10 * s63, s63); r, _, _, _ = rom(1.10 * s63, s63, d)
    print("    SCALE uniform x1.10     mor %+.6f dex   rom %+.6f dex   (both must be %+.6f)"
          % (m, r, np.log10(1.10)))
    ok &= abs(m - np.log10(1.10)) < 1e-9 and abs(r - np.log10(1.10)) < 1e-9
    # The load-bearing control.  A per-tile ratio field whose median is EXACTLY 1.000
    # by construction, assigned by rank in D so that it is correlated with the
    # denominator.  Truth: the arms are equally sharp.  mor must say so.
    n = len(s63); ordr = np.argsort(np.where(np.isfinite(d), d, -np.inf))
    rat = np.ones(n); third = n // 3
    rat[ordr[:third]] = 1.0 / 1.5
    rat[ordr[n - third:]] = 1.5
    tru = float(np.median(rat))
    m, _ = mor(rat * s63, s63); r, _, _, _ = rom(rat * s63, s63, d)
    print("    PLANT median-1 ratio    mor %+.6f dex   rom %+.6f dex   (true median ratio %.4f)"
          % (m, r, tru))
    if abs(tru - 1.0) > 1e-12:
        sys.exit("  ABORT: plant is not median-1 by construction (%.6f) -- control is void" % tru)
    ok &= abs(m) < 1e-12
    print("    -> mor recovers the truth; rom reports %+.6f dex of pure denominator effect" % r)
    print("  COMMISSIONING %s\n" % ("PASSED" if ok else "FAILED"))
    if not ok: sys.exit("ABORT: functionals failed commissioning")

def deciles(p32, p63, d_lo):
    """Is the tile-set difference CONTRAST, or is it tile POSITION?

    The old tile set came from a T=128 cache and its tiles overlap; the new one is a
    uniform non-overlapping grid.  If the effect is a property of scene contrast then
    the high-contrast deciles of the UNIFORM grid must reproduce it on their own, with
    no help from the old positions.  Deciles are cut on low-band (0.02-0.05 cyc/px)
    energy of the N063 master only -- a scene property, disjoint from every reported
    band, and computed on one arm so it cannot prefer tiles where either arm is sharp.

    A noise number on the same pixels, as required: the flat deciles are where the
    63-arm carries MORE band power, which is a defect pointing the other way and is
    exactly why the all-tile average reads zero."""
    a = p32[:, DM.B_MAIN]; b = p63[:, DM.B_MAIN]
    ap = p32[:, DM.B_PROM]; bp = p63[:, DM.B_PROM]
    g = (a > 0) & (b > 0) & np.isfinite(a) & np.isfinite(b) & np.isfinite(d_lo)
    idx = np.where(g)[0]
    order = idx[np.argsort(d_lo[idx])]
    k = len(order) // 10
    print("  CONTRAST STRATIFICATION of the uniform grid (%d tiles, deciles of low-band energy)"
          % len(order))
    print("    decile  n   median lowband      0.30-0.35 dex   S32>S63    0.20-0.25 dex")
    rows = []
    for dd in range(10):
        sl = order[dd*k:(dd+1)*k] if dd < 9 else order[9*k:]
        m = float(np.median(np.log10(a[sl] / b[sl])))
        mp = float(np.median(np.log10(ap[sl] / bp[sl])))
        fr = float((a[sl] > b[sl]).mean())
        lo = float(np.median(d_lo[sl]))
        print("      %2d  %3d   %14.1f      %+.4f        %5.1f%%     %+.4f"
              % (dd, len(sl), lo, m, 100*fr, mp))
        rows.append(dict(decile=dd, n=len(sl), lowband=lo, d_main=m, sign=fr, d_prom=mp))
    top = order[8*k:]
    m = float(np.median(np.log10(a[top] / b[top])))
    fr = float((a[top] > b[top]).mean())
    print("    top two deciles (%d tiles): %+.4f dex, %.1f%% of tiles S32>S63" % (len(top), m, 100*fr))
    print("    -> if this matches the OLD-300 reading, the tile-set gap is CONTRAST, not position")
    return rows

def main():
    print("EXPOSURE AUDIT")
    seen = {}
    for k, p in (("N032", A32), ("N063", A63)):
        line = [l.strip() for l in open(p + ".log", encoding="utf-8", errors="replace")
                if l.startswith("exposure")]
        if not line: sys.exit("ABORT: %s has no exposure line" % k)
        print("  %s  %s" % (k, line[0])); seen[k] = line[0]
    if len(set(seen.values())) != 1: sys.exit("ABORT: arms at different gain")
    print("  identical -- ratios are gain-free\n")

    ref = DM.load(A63); img = DM.load(A32)
    sy, sx, _ = HS.align(ref, img, *HS.all_tiles(ref.shape))
    print("N032 aligns to N063 at shift (%+d,%+d)\n" % (sy, sx))

    z = np.load(CACHE)
    sel = np.argsort(z["m_lo"])[::-1][:NT_OLD]
    oy_old = (z["oy"][sel] * 2).astype(int); ox_old = (z["ox"][sel] * 2).astype(int)
    oy_all, ox_all = HS.all_tiles(ref.shape)
    print("tile sets:  OLD %d tiles (top-%d by low-band, from the T=128 cache, doubled)"
          % (len(oy_old), NT_OLD))
    print("            ALL %d tiles (uniform grid, the new instrument)\n" % len(oy_all))

    out = {}
    for tag, oy, ox in (("OLD-300", oy_old, ox_old), ("ALL-486", oy_all, ox_all)):
        p63, _ = DM.bandpow(ref, oy, ox)
        p32, _ = DM.bandpow(img, oy + sy, ox + sx)
        d_lo = lopow(ref, oy, ox)
        print("=" * 72)
        print("TILE SET %s" % tag)
        if tag == "OLD-300":
            controls(p32[:, DM.B_MAIN], p63[:, DM.B_MAIN], d_lo)
        for band, bname in ((DM.B_MAIN, "0.30-0.35"), (DM.B_PROM, "0.20-0.25")):
            a = p32[:, band]; b = p63[:, band]
            m, nm = mor(a, b); ci = boot_mor(a, b)
            r1, ma1, mb1, n1 = rom(a, b, np.ones_like(b))
            r2, ma2, mb2, n2 = rom(a, b, d_lo)
            g = (a > 0) & (b > 0) & np.isfinite(a) & np.isfinite(b)
            frac = float((a[g] > b[g]).mean())
            print("  band %s   (%d tiles)" % (bname, nm))
            print("    median-of-ratios   %+.4f dex  CI [%+.4f,%+.4f]   N=32 is %+.1f%% %s"
                  % (m, ci[0], ci[1], abs(100 * (10**m - 1)), "sharper" if m > 0 else "softer"))
            print("    sign test          %.1f%% of tiles have S32 > S63   (50%% = no effect)"
                  % (100 * frac))
            print("    ratio-of-medians   D=1     %+.4f dex" % r1)
            print("    ratio-of-medians   D=lowband %+.4f dex   <- same D on both arms" % r2)
            print("    -> the two ratio-of-medians differ by %+.4f dex on IDENTICAL pixels,"
                  % (r2 - r1))
            print("       which is the size of the denominator effect the functional admits.")
            out["%s|%s" % (tag, bname)] = dict(mor=m, ci=list(ci), sign_frac=frac,
                                               rom_D1=r1, rom_lo=r2, tiles=nm)
        if tag == "ALL-486":
            out["deciles"] = deciles(p32, p63, d_lo)
        print()
    pubdex = float(np.log10(PUB32 / PUB63))
    print("=" * 72)
    print("PUBLISHED  0.7203 / 0.6063 = %+.4f dex  (ratio of medians, per-site-max D)" % pubdex)
    print("MEASURED   median-of-ratios on the OLD tile set: %+.4f dex"
          % out["OLD-300|0.30-0.35"]["mor"])
    print("MEASURED   median-of-ratios on ALL tiles:        %+.4f dex"
          % out["ALL-486|0.30-0.35"]["mor"])
    p = os.path.join(DIR, "d113recon.json"); json.dump(out, open(p, "w"), indent=1, default=float)
    print("\nmachine-readable: %s" % p)

if __name__ == "__main__":
    main()
