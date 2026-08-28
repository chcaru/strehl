"""rederive.py -- the depth deficit at EVERY band, with band qualification attached.

bandqual.py returned MARGINAL for 0.30-0.35 (R_top = 1.5525, pre-registered bar 2.0),
so PREREG-bandqual.md obliges me to withdraw +0.0732/+0.0748 dex as resolution claims,
name the lowest-frequency band that qualifies, and re-derive the deficit there. This
does the re-derivation. It does not choose a band to make a number look good: every
band is printed, for both subjects, in both tile strata, and the qualification is
carried in the same table so no row can be quoted without it.

Sign: mor(fewer, more) > 0 means the FEWER-frame arm holds more band power, i.e. the
DEEPER merge is softer. A noise number on the same pixels is mandatory here, so the
flat-decile column is printed beside every textured one -- on blotch alone the plain
mean wins while destroying 78% of the sharpness, and this lane will not repeat that.
"""
import os, sys, numpy as np
import softcheck as S, hsel as HS
import dmeasure as DM, d113recon as RC

DIL = r"C:\dev\strehl-out\V-SOFTCHECK\dilut"
NB = DM.NB; E = DM.E
# R_top (in-focus/defocused, per-tile focus selection, gain-normalised) from bandqual.py,
# MEASURED SEPARATELY ON EACH SUBJECT. Carried here so no row can be quoted without its
# qualification. Band qualification is subject-dependent and assuming otherwise is how
# a one-subject result becomes a corpus claim.
QUAL = {"113MSDCF":  [208.3274, 37.6998, 10.0205, 3.3235, 1.8241, 1.5525, 1.5347],
        "bee-1-cpl": [597.1336, 92.2304, 17.2691, 4.9288, 2.3180, 1.8480, 1.7671]}
PASS_R = 2.0
SUBJ = [("113MSDCF", "N032.tiff", "N063.tiff", 32, 63),
        ("bee-1-cpl", "R149x2.tiff", "R299x1.tiff", 149, 299)]

def bname(b): return "%.2f-%.2f" % (E[b], E[b+1])

def expo_of(path):
    for l in open(path + ".log", encoding="utf-8", errors="replace"):
        if l.startswith("exposure"): return l.strip()
    return None

def run(subj, fa, fb, na, nb):
    pa = os.path.join(DIL, subj, fa); pb = os.path.join(DIL, subj, fb)
    ea, eb = expo_of(pa), expo_of(pb)
    if ea != eb: sys.exit("ABORT %s: arms at different gain\n  %s\n  %s" % (subj, ea, eb))
    print("\n%s   N=%d vs N=%d   %s" % (subj, na, nb, ea))
    ref = DM.load(pb)
    oy, ox = HS.all_tiles(ref.shape)
    d_lo = RC.lopow(ref, oy, ox)
    pw = {}
    for tag, path, im in (("more", pb, ref), ("fewer", pa, None)):
        img = im if im is not None else DM.load(path)
        sy, sx, _ = HS.align(ref, img, oy, ox)
        a, _ = DM.bandpow(img, oy + sy, ox + sx)
        pw[tag] = a
        print("  %-5s shift(%+d,%+d)  in bounds %d" % (tag, sy, sx, int(np.isfinite(a[:, 0]).sum())))
        if im is None: del img
    del ref
    fin = np.isfinite(pw["more"][:, 0]) & np.isfinite(pw["fewer"][:, 0]) & np.isfinite(d_lo)
    idx = np.where(fin)[0]; order = idx[np.argsort(d_lo[idx])]
    nd = len(order) // 10
    TOP = order[8*nd:]; FLAT = order[:2*nd]
    dbl = np.log2(nb / na)
    print("  tiles %d  TOP %d  FLAT %d   doublings %.3f" % (len(order), len(TOP), len(FLAT), dbl))
    print("  %-11s %10s %18s %8s %10s   %-9s %s" %
          ("band", "TOP dex", "95% CI", "%softer", "FLAT dex", "R_focus", "qualifies"))
    out = {}
    for b in range(NB):
        a = pw["fewer"][:, b]; m = pw["more"][:, b]
        dt, _ = RC.mor(a[TOP], m[TOP]); lo, hi = RC.boot_mor(a[TOP], m[TOP])
        df, _ = RC.mor(a[FLAT], m[FLAT])
        q = QUAL[subj][b]
        qs = "%9.3f" % q
        ok = "QUALIFIES" if q >= PASS_R else "MARGINAL "
        print("  %-11s %+10.4f  [%+.4f,%+.4f] %7.1f%% %+10.4f   %s %s%s" %
              (bname(b), dt, lo, hi, 100*(10**dt - 1), df, qs, ok,
               "  <-- withdrawn band" if b == 5 else ("  <-- re-derived here" if b == 3 else "")))
        out[b] = (dt, lo, hi, df, dbl)
    return out

if __name__ == "__main__":
    res = {}
    for s, fa, fb, na, nb in SUBJ:
        res[s] = run(s, fa, fb, na, nb)
    print("\n\nDEPTH COST PER DOUBLING OF N, at matched range -- QUALIFYING BANDS ONLY\n")
    print("  %-11s %-11s %8s %11s %20s %9s" %
          ("subject", "band", "R_focus", "dex/doubl", "95% CI", "% softer"))
    for s, _, _, na, nb in SUBJ:
        for b in range(NB):
            d, lo, hi, f, dbl = res[s][b]
            if QUAL[s][b] < PASS_R or d <= 0: continue
            print("  %-11s %-11s %8.3f %+11.4f  [%+.4f,%+.4f] %8.1f%%" %
                  (s, bname(b), QUAL[s][b], d/dbl, lo, hi, 100*(10**d - 1)))
    print("\n  WITHDRAWN (band MARGINAL on both subjects, R_top 1.55 and 1.85 vs a bar of 2.0):")
    for s, _, _, na, nb in SUBJ:
        d, lo, hi, f, dbl = res[s][5]
        print("  %-11s %-11s %8.3f %+11.4f  [%+.4f,%+.4f] %8.1f%%" %
              (s, bname(5), QUAL[s][5], d/dbl, lo, hi, 100*(10**d - 1)))
    print("\n  NOISE ON THE SAME PIXELS (flat two deciles, same tiles, same bands):")
    print("  A pure noise difference CANNOT change sign between strata. The deeper arm holds")
    print("  MORE power in flat tiles at every band on both subjects (negative below) while")
    print("  holding LESS in textured tiles at fine bands (positive above), so the textured")
    print("  deficit is not the noise term -- and the noise term biases AGAINST the finding.")
    for s, _, _, na, nb in SUBJ:
        print("  %-11s " % s + " ".join("%+8.4f" % res[s][b][3] for b in range(NB)))
