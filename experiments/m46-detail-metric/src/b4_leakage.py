"""M46 b4 -- QUESTION 120: why is the `sb = 0` reference censored on EVERY
source, including the analytic channel?

M41 withdrew split-half FRC (fact 476) partly because the crossing was
right-censored everywhere.  M44 measured that a Blackman window and a 9x9
pre-filter each restore an uncensored crossing at `sb = 4`.  If the cause is
SPECTRAL LEAKAGE then the withdrawal is partly reversible, and that must be
known BEFORE FRC is discarded permanently.

THE DECISIVE INPUT, registered in PREREGISTRATION Sec 4.4 before any of this
ran: a latent that is BAND-LIMITED BY CONSTRUCTION.  `synth_broadband(n, seed,
cutoff=0.20)` zeroes every Fourier coefficient above 0.20 cyc/px.  Any ring
power measured at 0.45 cyc/px on it is leakage, 100%, with no modelling
assumption and no nuisance estimator to choose (rule 24).

RULE 20 -- THE INPUT THAT WOULD MAKE THIS FAIL, written before the run:
  * If the band-limited latent shows ring power at 0.45 cyc/px near machine
    zero under the incumbent Hann window, LEAKAGE IS RULED OUT and the
    censoring must come from real content at Nyquist (aliasing / PRNU).  The
    diagnosis would then be "the sensor genuinely has correlated structure to
    Nyquist", and no window change can help.
  * If the leakage floor is high under Hann but falls by orders of magnitude
    under Blackman-Harris, leakage is confirmed AND the fix is identified.
  * A window change that lowers the leakage floor but does NOT un-censor the
    real sources means leakage is present but is not the binding cause.
    That is a third, distinguishable outcome, and it is the one that would
    make the repair worthless.
All three are reachable from the same measurement.  This is not a tautology.

WINDOWING IS A CHOICE, SO IT IS LADDERED, NOT PICKED (rule 24).  The ring
binning, the shift convention and the two-adjacent-ring crossing rule are
IMPORTED unchanged from `m41lib.frc` / `m41lib3.cross` so every number here is
comparable to M41's line by line; only the window and the optional pre-filter
vary.  The FRC body below is a COPY of `m41lib.frc` with the window made a
parameter -- stated explicitly because it is a copy.
"""
import json
import os
import sys
import time

import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m46lib as M                                                    # noqa: E402

L3 = M.L3
N = 512
NBIN = M.NBIN
THR = M.THR
F_HI = 0.45


# --------------------------------------------------------------- windows
def w_rect(n):
    return np.ones(n)


def w_hann(n):
    return np.hanning(n)


def w_blackman(n):
    return np.blackman(n)


def w_bh(n):
    """Blackman-Harris 4-term, -92 dB sidelobes."""
    k = np.arange(n) / (n - 1)
    return (0.35875 - 0.48829 * np.cos(2 * np.pi * k)
            + 0.14128 * np.cos(4 * np.pi * k) - 0.01168 * np.cos(6 * np.pi * k))


WINDOWS = [("rect", w_rect), ("hann", w_hann), ("blackman", w_blackman),
           ("bharris", w_bh)]


def prefilter(a, w=9):
    """The 9x9 high-pass M44 found also un-censors.  Removes the low-frequency
    power that is the SOURCE of the leakage rather than suppressing its
    spreading."""
    return a - uniform_filter(a, w)


# ------------------------------------------------- FRC, window as parameter
def frc_w(a, b, wfun, nbin=NBIN, pre=False):
    """COPY of m41lib.frc with the window parameterised.  Ring edges, the
    fftshift convention, the >=8-pixel ring floor and the mean-removal are
    byte-identical to the frozen original."""
    if pre:
        a, b = prefilter(a), prefilter(b)
    n = a.shape[0]
    w1 = wfun(n)
    w = np.outer(w1, w1)
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * w))
    cy = cx = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - cy) ** 2.0 + (xx - cx) ** 2.0)
    rmax = n / 2.0
    edges = np.linspace(0, rmax, nbin + 1)
    ff, fr, pw = [], [], []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        if m.sum() < 8:
            continue
        Am, Bm = A[m], B[m]
        num = float(np.real(np.sum(Am * np.conj(Bm))))
        den = float(np.sqrt(np.sum(np.abs(Am) ** 2) * np.sum(np.abs(Bm) ** 2)))
        ff.append(0.5 * (edges[i] + edges[i + 1]) / n)
        fr.append(num / den if den > 0 else 0.0)
        pw.append(float(np.mean(np.abs(Am) ** 2)))
    return np.array(ff), np.array(fr), np.array(pw)


def at(ff, fr, f):
    return float(np.interp(f, ff, fr))


def fmtc(c, cen):
    return f"{c:.4f}" + (" [CENSORED]" if cen else "           ")


# ----------------------------------------------------------------- sources
def sources():
    """The analytic channel is BAND-LIMITED at 0.20 cyc/px by construction.
    The real ROIs come from b1's merged planes -- the same arrays b2 and b3
    used, loaded from the frozen artifact, not re-derived."""
    src = {}
    z = np.load(os.path.join(M.OUT, "b1_merges.npz"))
    pad = 32
    for key, tag in (("d112", "detail"), ("f112", "flat")):
        a = z[key][pad:-pad, pad:-pad].astype(np.float32)
        src["real_" + tag] = a[:N, :N].copy()
    src["bandlimited"] = M.synth_broadband(N, 4242, cutoff=0.20) * 40.0
    src["broadband"] = M.synth_broadband(N, 4242, cutoff=None) * 40.0
    return src


def main():
    t0 = time.time()
    print("=" * 78)
    print("M46 b4 -- question 120: is the sb=0 censoring SPECTRAL LEAKAGE?")
    print("=" * 78)
    res = {}
    SRC = sources()
    rho = 0.3094

    # ------------------------------------------------------- 1. leakage floor
    print("\n1. THE LEAKAGE FLOOR, measured with no modelling assumption.")
    print("   `bandlimited` has EXACTLY ZERO Fourier power above 0.20 cyc/px.")
    print("   Ring power measured at 0.45 cyc/px is therefore leakage, 100%.")
    print("   Reported as dB below the peak ring; noiseless, so nothing else")
    print("   can be putting power there.")
    lat = SRC["bandlimited"]
    print("\n   window      P(0.45)/P_peak      dB      P(0.45)/P(0.20)")
    lk = {}
    for wn, wf in WINDOWS:
        ff, _, pw = frc_w(lat, lat, wf)
        p_hi = float(np.interp(F_HI, ff, pw))
        p_pk = float(pw.max())
        p_cut = float(np.interp(0.20, ff, pw))
        db = 10.0 * np.log10(max(p_hi / p_pk, 1e-300))
        print(f"   {wn:<10s} {p_hi/p_pk:16.4e} {db:8.1f}   {p_hi/max(p_cut,1e-300):14.4e}")
        lk[wn] = dict(p_hi=p_hi, p_peak=p_pk, p_cut=p_cut, db=db)
    ff, _, pw = frc_w(lat, lat, w_hann, pre=True)
    p_hi = float(np.interp(F_HI, ff, pw)); p_pk = float(pw.max())
    print(f"   {'hann+pre9':<10s} {p_hi/p_pk:16.4e} "
          f"{10*np.log10(max(p_hi/p_pk,1e-300)):8.1f}")
    lk["hann_pre9"] = dict(p_hi=p_hi, p_peak=p_pk,
                           db=float(10 * np.log10(max(p_hi / p_pk, 1e-300))))
    res["leakage_floor"] = lk

    # -------------------------------- 2. does leakage produce a false crossing?
    print("\n2. DOES THE LEAKED POWER CARRY FALSE CORRELATION?")
    print("   Two independent noisy captures of the BAND-LIMITED latent.  Above")
    print("   0.20 cyc/px the only true correlation is the fixed pattern; every")
    print("   other correlated thing up there is leaked from below the cutoff.")
    print("   TRUE FRC above the cutoff, with FPN excluded, is 0 by construction.")
    sfr = 11.891
    sigma = sfr / np.sqrt(10.366)
    rows = {}
    for tag, use_fpn in (("no_FPN", False), ("with_FPN", True)):
        fpn = M.make_fpn(lat.shape, 909, np.sqrt(rho) * sfr) if use_fpn else 0.0
        rng = np.random.default_rng(31337)
        y1 = lat + fpn + rng.standard_normal(lat.shape).astype(np.float32) * sigma
        y2 = lat + fpn + rng.standard_normal(lat.shape).astype(np.float32) * sigma
        print(f"\n   {tag}:   window       FRC(0.45)   FRC(0.2762)   crossing")
        for wn, wf in WINDOWS:
            ff, fr, _ = frc_w(y1, y2, wf)
            c, cen = L3.cross(ff, fr, thr=THR)
            print(f"              {wn:<12s} {at(ff,fr,F_HI):+9.4f} {at(ff,fr,M.F_SIG):+13.4f}"
                  f"   {fmtc(c,cen)}")
            rows[f"{tag}/{wn}"] = dict(frc_hi=at(ff, fr, F_HI),
                                       frc_fsig=at(ff, fr, M.F_SIG),
                                       cross=c, censored=cen)
        ff, fr, _ = frc_w(y1, y2, w_hann, pre=True)
        c, cen = L3.cross(ff, fr, thr=THR)
        print(f"              {'hann+pre9':<12s} {at(ff,fr,F_HI):+9.4f} "
              f"{at(ff,fr,M.F_SIG):+13.4f}   {fmtc(c,cen)}")
        rows[f"{tag}/hann_pre9"] = dict(frc_hi=at(ff, fr, F_HI),
                                        frc_fsig=at(ff, fr, M.F_SIG),
                                        cross=c, censored=cen)
    res["bandlimited_frc"] = rows

    # ---------------------------------------- 3. does the fix reach real data?
    print("\n3. DOES THE REPAIR CARRY TO THE REAL SOURCES?")
    print("   The window ladder x a blur ladder on the observed ROIs.  A repair")
    print("   that only works on the analytic channel is not a repair.")
    real = {}
    for sname in ("real_detail", "real_flat", "broadband"):
        base = SRC[sname]
        s = 11.891 if sname != "real_flat" else 7.846
        ne = 10.366 if sname != "real_flat" else 8.784
        sig = s / np.sqrt(ne)
        fpn = M.make_fpn(base.shape, 909, np.sqrt(rho) * s)
        print(f"\n   {sname}")
        print("      sb     " + "".join(f"{wn:>17s}" for wn, _ in WINDOWS) +
              f"{'hann+pre9':>17s}")
        for sb in (0.0, 1.0, 2.0, 4.0):
            lb = M.blur(base, sb)
            rng = np.random.default_rng(555)
            y1 = lb + fpn + rng.standard_normal(base.shape).astype(np.float32) * sig
            y2 = lb + fpn + rng.standard_normal(base.shape).astype(np.float32) * sig
            line = f"      {sb:<5.1f}  "
            for wn, wf in WINDOWS:
                ff, fr, _ = frc_w(y1, y2, wf)
                c, cen = L3.cross(ff, fr, thr=THR)
                line += f"{c:11.4f}{'  [C]' if cen else '     '} "
                real[f"{sname}/{sb}/{wn}"] = dict(cross=c, censored=cen)
            ff, fr, _ = frc_w(y1, y2, w_hann, pre=True)
            c, cen = L3.cross(ff, fr, thr=THR)
            line += f"{c:11.4f}{'  [C]' if cen else '     '}"
            real[f"{sname}/{sb}/hann_pre9"] = dict(cross=c, censored=cen)
            print(line)
    res["real_ladder"] = real

    # ------------------------------- 4. would an uncensored crossing be useful?
    print("\n4. IF THE CROSSING UN-CENSORS, DOES IT BECOME A USABLE METRIC?")
    print("   An uncensored number is not automatically an informative one.")
    print("   Recovery ratio on the planted ladder, per window, computed only")
    print("   where BOTH the sb=0 reference and the sb=2 plant are uncensored.")
    print("   The analytic prediction is the SAME frc_pred the M41 harness uses.")
    use = {}
    for sname in ("real_detail", "real_flat", "broadband"):
        base = SRC[sname]
        s = 11.891 if sname != "real_flat" else 7.846
        ne = 10.366 if sname != "real_flat" else 8.784
        sig = s / np.sqrt(ne)
        fpn = M.make_fpn(base.shape, 909, np.sqrt(rho) * s)
        print(f"\n   {sname}   window        cross(sb=0)   cross(sb=2)   recovery")
        for wn, wf in list(WINDOWS) + [("hann+pre9", None)]:
            vals, cens = [], []
            for sb in (0.0, 2.0):
                lb = M.blur(base, sb)
                rng = np.random.default_rng(555)
                y1 = lb + fpn + rng.standard_normal(base.shape).astype(np.float32) * sig
                y2 = lb + fpn + rng.standard_normal(base.shape).astype(np.float32) * sig
                if wn == "hann+pre9":
                    ff, fr, _ = frc_w(y1, y2, w_hann, pre=True)
                else:
                    ff, fr, _ = frc_w(y1, y2, wf)
                c, cen = L3.cross(ff, fr, thr=THR)
                vals.append(c); cens.append(cen)
            if any(cens):
                print(f"            {wn:<12s} {vals[0]:11.4f}{'[C]' if cens[0] else '   '} "
                      f"{vals[1]:11.4f}{'[C]' if cens[1] else '   '}    "
                      f"UNSCORABLE (censored)")
                use[f"{sname}/{wn}"] = dict(c0=vals[0], c2=vals[1], cens=cens, rec=None)
                continue
            rec = (vals[0] - vals[1]) / max(vals[0], 1e-12)
            print(f"            {wn:<12s} {vals[0]:11.4f}    {vals[1]:11.4f}    "
                  f"{rec:+8.4f}  (fractional drop)")
            use[f"{sname}/{wn}"] = dict(c0=vals[0], c2=vals[1], cens=cens, rec=rec)
    res["usability"] = use

    with open(os.path.join(M.OUT, "b4_results.json"), "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    print(f"\nwrote out/b4_results.json  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
