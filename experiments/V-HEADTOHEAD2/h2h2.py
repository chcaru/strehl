"""THE HEAD-TO-HEAD, re-run with the gather flip in place.

WHAT CAN AND CANNOT BE DONE HERE, STATED FIRST
----------------------------------------------
The instrument commissioned in commission.py needs TWO observations of one
scene with INDEPENDENT noise.  For strehl those exist: two renders from
disjoint halves of the bracket.  For Zerene and for the fork they do not and
cannot -- I can read their output, I cannot re-run them on half a bracket.  So
the noise-immune statistic C is available on ONE SIDE of this comparison only.

That asymmetry is not fatal, because it runs the right way for a bound:

    C_strehl(f)  is strehl's COHERENT power: noise contributes zero to it.
    P_comp(f)    is the comparator's TOTAL power: signal PLUS its own noise,
                 therefore an UPPER BOUND on the comparator's signal.

    C_strehl(f) > P_comp(f)  =>  strehl carries more real structure at f.
                                 RIGOROUS, one-sided.
    C_strehl(f) <= P_comp(f) =>  INCONCLUSIVE.  The comparator's excess may be
                                 signal or may be noise and this cannot tell.

The bound is conservative in three further ways, all of which cost strehl:
  * C_strehl comes from HALF the frames, so twice the focus step.  Less real
    detail than the full stack, not more.
  * Any residual A<->B misregistration DEPRESSES C.  It is measured below.
  * The comparators were fed Lightroom-developed TIFFs (Sharpness=0, but
    Contrast2012=+100 on 113MSDCF) while strehl reads RAW.  A contrast grade
    RAISES the comparator's local contrast, and therefore raises P_comp.

Second, a NON-rigorous estimate is also reported, because a bound that is
inconclusive everywhere is not useful: subtract each render's own noise floor,
measured on its own flat ROIs, from its detail-ROI band power.  This has an
assumption -- noise stationarity across the frame -- and unlike the bound it
can be wrong.  It is CALIBRATED on the one arm where the truth is known: for
strehl, P_full - N_flat can be checked against C from the halves.  If the
estimator cannot reproduce C on strehl, it is not applied to the comparator.

GEOMETRY.  Measured by geom.py, not assumed: cb/fork scale 1.0340 (interior
maximum, median tile peak 0.5212), 113/Zerene scale 1.0020 (0.5811).  NOTHING
IS RESAMPLED.  Each arm reads an INTEGER box in its own grid, sized T/scale so
the two boxes cover the same scene area, and each arm's band edges are scaled
into its own grid so every band is defined in SCENE units.
"""
import sys

import numpy as np
import tifffile

import h2
import rois

LIN = r"C:\dev\strehl-out\V-H2H2\lin"
T = 256
PAD = 32

COMP = {
    "cb": dict(path=r"C:\dev\macro\out\coffee-bean\stack.tif",
               label="focus-stack fork", scale=1.0340,
               weights=(0.2627, 0.6780, 0.0593),  # Rec.2020 luma
               linear=True),
    "113": dict(path=r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif",
                label="Zerene Stacker PMax", scale=1.0020,
                weights=(0.2126, 0.7152, 0.0722),
                linear=False),
}


def load(tag):
    return h2.Render(rf"{LIN}\{tag}.tiff", name=tag, linear=True)


class Comp:
    def __init__(self, cfg):
        self.cfg = cfg
        a = tifffile.imread(cfg["path"])
        w = cfg["weights"]
        self.g = (w[0] * a[:, :, 0].astype(np.float64)
                  + w[1] * a[:, :, 1].astype(np.float64)
                  + w[2] * a[:, :, 2].astype(np.float64))
        self.top = float(a[:, :, :3].max())
        self.h, self.w = self.g.shape
        self.lut = None

    def fit_tone(self, ref_vals, own_vals, nq=512):
        """Monotone histogram match: comparator level -> strehl level.

        The comparator's TIFF is a graded viewing render (Zerene's inputs were
        Lightroom-developed with Contrast2012=+100).  A tone curve multiplies
        local contrast by its own local slope, so band power taken through it
        is not comparable to band power taken in linear light.  This estimates
        the curve empirically from co-located samples and inverts it.  The
        exponent range printed by `report_tone` is the diagnostic: a curve that
        needed no inversion would come out flat at 1.0."""
        q = np.linspace(0.2, 99.8, nq)
        xs = np.percentile(own_vals, q)
        ys = np.percentile(ref_vals, q)
        keep = np.concatenate([[True], np.diff(xs) > 0])
        self.lut = (xs[keep], ys[keep])
        return self.lut

    def report_tone(self):
        xs, ys = self.lut
        m = (xs > xs[0]) & (ys > 0)
        lx = np.log(xs[m]); ly = np.log(ys[m])
        sl = np.diff(ly) / np.maximum(np.diff(lx), 1e-9)
        sl = sl[np.isfinite(sl)]
        print(f"    fitted tone map, d(log strehl)/d(log comparator): "
              f"median {np.median(sl):.3f}  10-90% "
              f"[{np.percentile(sl,10):.3f},{np.percentile(sl,90):.3f}]"
              f"   (1.000 everywhere == already linear)")

    def crop(self, y0, x0, t):
        blk = self.g[y0:y0 + t, x0:x0 + t]
        if blk.shape != (t, t):
            return None, 1
        nclip = int((blk >= self.top * 0.9999).sum() + (blk <= 0).sum())
        if self.lut is not None:
            blk = np.interp(blk, self.lut[0], self.lut[1])
        return blk, nclip


def band_power(crop, edges_lo, edges_hi):
    """Contrast variance in each PHYSICAL band, on this arm's own grid."""
    t = crop.shape[0]
    f = h2.contrast_fft(crop)
    if f is None:
        return None
    r = h2.radial(t)
    norm = (t * t) ** 2 * (h2.window(t) ** 2).mean()
    p = (np.abs(f) ** 2) / norm
    return np.array([p[(r >= a) & (r < b)].sum()
                     for a, b in zip(edges_lo, edges_hi)])


def cross_power(ca, cb):
    t = ca.shape[0]
    fa = h2.contrast_fft(ca)
    fb = h2.contrast_fft(cb)
    if fa is None or fb is None:
        return None, None
    masks = h2.band_masks(t)
    PA, PB, C = h2.pair_bands(fa, fb, masks, t)
    return 0.5 * (PA + PB), C


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "113"
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    cfg = COMP[subj]
    S = cfg["scale"]
    TC = int(round(T / S))
    print("=" * 104)
    print(f"HEAD-TO-HEAD (post-flip) : {subj}  strehl vs {cfg['label']}")
    print("=" * 104)
    print(f"  scale {S:.4f} (measured, geom.py) -> strehl box {T}px, "
          f"comparator box {TC}px, same scene area")
    print(f"  band edges are PHYSICAL: band [a,b] cyc/strehl-px is read at "
          f"[{S:.4f}a,{S:.4f}b] cyc/comparator-px")

    A = load(f"{subj}-A-g1"); B = load(f"{subj}-B-g1")
    F = load(f"{subj}-full-g1")
    F0 = load(f"{subj}-full-g0")
    C = Comp(cfg)
    print(f"  strehl {F.w}x{F.h}   comparator {C.w}x{C.h}")

    detail, flat, counts = rois.census(F, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(7)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]
    fl = [flat[i] for i in rng.permutation(len(flat))[:min(nroi, len(flat))]]

    # ---- global alignment: one integer offset, refined at full resolution
    print("\n--- registration (integer only; nothing is resampled) ---")
    probe = det[:12]
    offs = []
    for (y, x) in probe:
        cs, _ = F.crop(y, x, T)
        cc, ncl = C.crop(int(round(y / S)), int(round(x / S)), TC)
        if cc is None:
            continue
        # compare on the strehl grid ONLY to find the offset: use the coarse
        # block means, which are integer-exact and add no ringing
        d = 4
        ta, tb = T // d * d, TC // d * d
        a = cs[:ta, :ta].reshape(ta // d, d, ta // d, d).mean((1, 3))
        b2 = cc[:tb, :tb].reshape(tb // d, d, tb // d, d).mean((1, 3))
        n = min(a.shape[0], b2.shape[0])
        dy, dx, pk = h2.integer_shift(a[:n, :n], b2[:n, :n], maxshift=6)
        offs.append((dy * d, dx * d, pk))
    offs = np.array(offs)
    OY, OX = int(np.median(offs[:, 0])), int(np.median(offs[:, 1]))
    print(f"  {len(offs)} probe ROIs -> median comparator offset "
          f"(dy,dx) = ({OY:+d},{OX:+d}) comparator px, "
          f"peak median {np.median(offs[:,2]):.4f}, "
          f"spread dy [{offs[:,0].min():+.0f},{offs[:,0].max():+.0f}] "
          f"dx [{offs[:,1].min():+.0f},{offs[:,1].max():+.0f}]")

    # ---- tone: fit the comparator's grade out, from co-located samples
    if not cfg["linear"]:
        print("\n--- tone: the comparator is a graded render; fitting it out ---")
        rv, ov = [], []
        for (y, x) in det[:20]:
            cs, _ = F.crop(y, x, T)
            cc, _ = C.crop(int(round(y / S)) + OY, int(round(x / S)) + OX, TC)
            if cc is None:
                continue
            rv.append(cs[::4, ::4].ravel()); ov.append(cc[::4, ::4].ravel())
        C.fit_tone(np.concatenate(rv), np.concatenate(ov))
        C.report_tone()
    else:
        print("\n--- tone: comparator is already linear "
              "(float32, linear Rec.2020); no inversion applied ---")

    lo = np.array([b[0] for b in h2.BANDS])
    hi = np.array([b[1] for b in h2.BANDS])

    def run(roiset, label):
        accC = []; accPs = []; accPc = []; accPf0 = []
        used = 0; drop_s = 0; drop_c = 0
        for (y, x) in roiset:
            ca, na = A.crop(y, x, T)
            cb, nb = B.crop(y, x, T)
            cf, nf = F.crop(y, x, T)
            cf0, nf0 = F0.crop(y, x, T)
            if na or nb or nf or nf0:
                drop_s += 1
                continue
            cc, ncl = C.crop(int(round(y / S)) + OY, int(round(x / S)) + OX, TC)
            if cc is None or ncl:
                drop_c += 1
                continue
            Pab, Cab = cross_power(ca, cb)
            if Cab is None:
                drop_s += 1
                continue
            ps = band_power(cf, lo, hi)
            ps0 = band_power(cf0, lo, hi)
            pc = band_power(cc, lo * S, hi * S)
            if pc is None:
                drop_c += 1
                continue
            accC.append(Cab); accPs.append(ps); accPc.append(pc); accPf0.append(ps0)
            used += 1
        tot = len(roiset)
        print(f"\n  {label} ROIs: {tot} offered = {used} used + {drop_s} dropped "
              f"(strehl clipped) + {drop_c} dropped (comparator clipped/out of frame)")
        assert used + drop_s + drop_c == tot
        return (np.array(accC), np.array(accPs), np.array(accPc),
                np.array(accPf0), used)

    Cd, Psd, Pcd, Ps0d, nd = run(det, "DETAIL")
    Cf, Psf, Pcf, Ps0f, nf = run(fl, "FLAT (noise floor)")

    hdr = " ".join(f"{a:.2f}-{b:.2f}".center(11) for a, b in h2.BANDS)
    print(f"\n  {'':<30} {hdr}")

    def prow(label, v, fmt="{:11.4e}"):
        print(f"  {label:<30} " + " ".join(fmt.format(x) for x in v))

    mC = Cd.mean(0); mPs = Psd.mean(0); mPc = Pcd.mean(0); mPs0 = Ps0d.mean(0)
    nS = Psf.mean(0); nC = Pcf.mean(0)
    print("\n=== raw contrast variance per band, DETAIL ROIs (mean over ROIs) ===")
    prow("strehl C  (coherent, post-flip)", mC)
    prow("strehl P  (total, post-flip)", mPs)
    prow("strehl P  (total, PRE-flip)", mPs0)
    prow(f"{cfg['label'][:22]} P (total)", mPc)

    print("\n=== noise floor from each arm's own FLAT ROIs ===")
    prow("strehl  N", nS)
    prow("comparator N", nC)
    print("  (flat-ROI band power is signal+noise too, so these are UPPER "
          "bounds on the noise; subtracting them is conservative for the arm "
          "being corrected)")

    print("\n=== CALIBRATION: does P - N reproduce C on the arm where C is known? ===")
    est = mPs - nS
    prow("strehl P - N", est)
    prow("strehl C  (truth)", mC)
    prow("ratio (P-N)/C", est / mC, "{:11.4f}")
    ok = np.all((est / mC > 0.5) & (est / mC < 2.0))
    print(f"  estimator {'USABLE' if ok else 'NOT USABLE'} "
          f"(pass = within 2x of the truth in every band)")

    print("\n=== THE RIGOROUS ONE-SIDED BOUND ===")
    prow("C_strehl / P_comp", mC / mPc, "{:11.4f}")
    print("  > 1 : strehl carries MORE REAL STRUCTURE there, rigorously.")
    print("  < 1 : INCONCLUSIVE -- the comparator's excess may be its own noise.")
    win = [f"{a:.2f}-{b:.2f}" for (a, b), r in zip(h2.BANDS, mC / mPc) if r > 1]
    print(f"  rigorous strehl wins: {win if win else 'none'}")

    print("\n=== THE ESTIMATE (assumes noise stationarity; can be wrong) ===")
    sc = mPc - nC
    prow("comparator P - N", sc)
    prow("C_strehl / (P-N)_comp", mC / sc, "{:11.4f}")
    prow("(P-N)_strehl / (P-N)_comp", est / sc, "{:11.4f}")

    print("\n=== the RETRACTED statistic, for the record ===")
    prow("P_strehl_postflip / P_comp", mPs / mPc, "{:11.4f}")
    prow("P_strehl_PREflip  / P_comp", mPs0 / mPc, "{:11.4f}")
    print("  This is the number the README's retracted table reports.  It is")
    print("  reproduced here ONLY to show what the flip did to it; the same")
    print("  statistic rates a real nearest-neighbour gather up to 88% BETTER")
    print("  than catmull-rom on this very corpus (flip.py), so it decides")
    print("  nothing.")


if __name__ == "__main__":
    sys.exit(main())
