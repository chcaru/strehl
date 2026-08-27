"""PRE-REGISTRATION: what band does the softness ratio actually integrate over?

The restoration's gain is strongly frequency dependent -- it peaks at the gather
plane's Nyquist (0.25 cyc/output px for a demosaiced merge) and its excess is
tapered to exactly ZERO at output Nyquist by `roll_off`. So whether it can move
my ratio at all depends entirely on where my statistic's energy actually sits.
Predicting that from the nominal sigma would be a guess; this measures it.

TWO THINGS ARE MEASURED, NOT ASSUMED.

|H(f)|^2, the high-pass response. `detail()` is `f - GaussianBlur(f, 1.5)`, whose
textbook transfer is `1 - exp(-2 pi^2 sigma^2 f^2)`. But OpenCV uses a truncated,
discretised kernel and the textbook form is not what runs. So H is measured by
pushing white noise through the ACTUAL operation and taking the ratio of power
spectra. Whatever cv2 really does is then in the answer.

S(f), the image power spectrum. Natural-image PSD falls steeply, roughly 1/f^2,
which drags the energy-weighted centre of any high-pass statistic DOWN, often far
below where the filter's response is nominally flat. This is the term that decides
the prediction, and it is the one an argument from sigma alone gets wrong.

The product `|H|^2 * S` is the density the ratio integrates. Its centroid is where
the statistic actually lives, and the restoration's gain must be read THERE.

Usage:
  python band_probe.py <subject> [size]
"""

import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from corpus_softness import SCRATCH, luma32, pick_tile  # noqa: E402
from softness_verdict3 import HP_SIGMA  # noqa: E402


def radial(p, nbins=128):
    """Radially average a 2-D power spectrum onto cycles/px in [0, 0.5].

    DC is EXCLUDED. Subtracting the tile mean before windowing does not remove
    it -- multiplying by a non-uniform window reintroduces a mean, and the
    resulting DC term is many orders of magnitude above the high-frequency
    power. The first version of this probe left it in and reported a median band
    of 0.0201 cyc/px, which failed the blur check below by a factor of ~5.
    """
    h, w = p.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    fr = np.sqrt(fy ** 2 + fx ** 2)
    edges = np.linspace(0.0, 0.5, nbins + 1)
    idx = np.clip(np.digitize(fr.ravel(), edges) - 1, 0, nbins - 1)
    ok = (fr.ravel() <= 0.5) & (fr.ravel() > 0.0)
    num = np.bincount(idx[ok], weights=p.ravel()[ok], minlength=nbins)
    cnt = np.bincount(idx[ok], minlength=nbins).astype(float)
    centres = 0.5 * (edges[:-1] + edges[1:])
    return centres, np.where(cnt > 0, num / np.maximum(cnt, 1), 0.0), cnt


def main():
    subject = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 2048

    # ---- the density, measured DIRECTLY on the high-pass output -------------
    # The first two versions estimated |H|^2 as a ratio of two noisy spectra and
    # multiplied it by the image PSD. At low f the true response is ~1e-8, so
    # that ratio measured float rounding noise, and multiplying noise by an
    # enormous low-frequency PSD parked the density at 0.002 cyc/px. The
    # commissioning arm rejected it at 240% error.
    #
    # H does not need estimating separately: the high-pass OUTPUT already
    # contains it. By Parseval the radial energy of `hp` IS the density the
    # statistic integrates, with no ratio and no cancellation of large numbers.
    # Done in float64 so the transform is not competing with float32 epsilon.
    mtif = SCRATCH / subject / "MASTER.tiff"
    if not mtif.exists():
        print(f"no cached master at {mtif}")
        return 1
    a = luma32(tifffile.imread(str(mtif)))
    tx, ty = pick_tile(a, size)
    raw = a[ty:ty + size, tx:tx + size].astype(np.float32)

    hp64 = (raw - cv2.GaussianBlur(raw, (0, 0), HP_SIGMA)).astype(np.float64)
    win = np.outer(np.hanning(size), np.hanning(size))
    P = np.abs(np.fft.fft2(hp64 * win)) ** 2
    f, Pr, cnt = radial(P)
    dens = np.where(np.isfinite(Pr), Pr, 0.0) * cnt
    tot = dens.sum()
    if tot <= 0:
        print("degenerate spectrum")
        return 1
    w = dens / tot
    cdf = np.cumsum(w)

    def q(p):
        return float(np.interp(p, cdf, f))

    centroid = float((f * w).sum())
    print(f"{subject}  tile ({tx},{ty}) {size}x{size}, HP_SIGMA={HP_SIGMA}")
    print("\n  energy-weighted band of the ratio statistic:")
    print(f"    centroid            {centroid:.4f} cyc/px")
    print(f"    median (P50)        {q(0.50):.4f} cyc/px")
    print(f"    P10 / P90           {q(0.10):.4f} / {q(0.90):.4f} cyc/px")
    print(f"    P25 / P75           {q(0.25):.4f} / {q(0.75):.4f} cyc/px")
    for k in (0.25, 0.30, 0.40):
        frac = float(w[f > k].sum())
        print(f"    energy above {k:.2f}     {100 * frac:6.2f}%")
    frac_knee = float(w[f <= 0.25].sum())
    print(f"    energy AT OR BELOW the 0.25 knee  {100 * frac_knee:6.2f}%")

    # ORCH's question (a), answered as a number rather than a description.
    # V-HEADTOHEAD2 §3b / V-LINEAR measured that a tile IN FOCUS carries the
    # same 0.20-0.48 cyc/px power as the same tile TWENTY FRAMES OUT OF FOCUS
    # (ratios 1.015, 1.043, 1.004, 1.138). If my statistic lives inside that
    # band, then the quantity I have been ranking merges by is one that defocus
    # itself cannot move on this corpus, and the deficit is misnamed.
    lo, hi = 0.20, 0.48
    inside = float(w[(f >= lo) & (f <= hi)].sum())
    below = float(w[f < lo].sum())
    above = float(w[f > hi].sum())
    print(f"\n  OVERLAP WITH V-LINEAR'S DISPUTED BAND {lo:.2f}-{hi:.2f} cyc/px:")
    print(f"    inside it          {100 * inside:6.2f}%")
    print(f"    below {lo:.2f}         {100 * below:6.2f}%")
    print(f"    above {hi:.2f}         {100 * above:6.2f}%")

    # The 0.20-0.48 block above answers the question as it was ASKED, but that
    # framing is already superseded. V-LINEAR2 §1/Q2 resolves the same span into
    # sub-bands and finds it is NOT uniform: per-tile focus selection recovers
    # 2.419 at 0.20-0.25 where V-LINEAR's four whole-frame pairs reported 1.0,
    # and only 0.25 upward actually fails. So the honest allocation of my
    # statistic is against V-LINEAR2's PASS/MARGINAL/FAIL verdicts, not against
    # a single 0.20-0.48 block that averages a passing band with a failing one.
    vl2 = [((0.00, 0.05), "below probe"), ((0.05, 0.10), "18.193 PASS"),
           ((0.10, 0.20), "10.083 PASS"), ((0.20, 0.25), "2.419 PASS"),
           ((0.25, 0.30), "1.387 MARGINAL"), ((0.30, 0.40), "1.149 FAIL"),
           ((0.40, 0.48), "1.105 FAIL"), ((0.48, 0.51), "above probe")]
    print("\n  ALLOCATION AGAINST V-LINEAR2 §1's PER-TILE VERDICTS:")
    print(f"    {'band':<14} {'my energy':>10}   {'V-LINEAR2 in/out of focus':<26}")
    acc = {"PASS": 0.0, "MARGINAL": 0.0, "FAIL": 0.0, "probe": 0.0}
    for (a_, b_), verdict in vl2:
        e = float(w[(f >= a_) & (f < b_)].sum())
        print(f"    {a_:.2f}-{b_:.2f}    {100 * e:9.2f}%   {verdict:<26}")
        for k in acc:
            if k in verdict:
                acc[k] += e
    print(f"    {'':14} {'':10}   {'':26}")
    print(f"    carries focus-dependent signal (PASS)   {100 * acc['PASS']:6.2f}%")
    print(f"    marginal                                {100 * acc['MARGINAL']:6.2f}%")
    print(f"    certified noise (FAIL)                  {100 * acc['FAIL']:6.2f}%")
    print(f"    outside the probe's own 0.05-0.48 span  {100 * acc['probe']:6.2f}%")
    tot_chk = sum(acc.values())
    print(f"    partition sums to                       {100 * tot_chk:6.2f}%"
          f"  (must be 100.00)")
    assert abs(tot_chk - 1.0) < 1e-6, "allocation does not partition the energy"

    # ---- COMMISSION THE BAND, or it cannot be used to predict ---------------
    # A density that says where the statistic's energy lives must be able to
    # predict what a KNOWN filter does to that statistic. Gaussian blur is the
    # ideal probe: its transfer is exactly exp(-2 pi^2 s^2 f^2), it is the same
    # family used for the visibility staircase, and the answer can be measured
    # directly on the same tile. If predicted and measured retention disagree,
    # this probe is wrong and no prediction built on it is worth anything.
    #
    # This is the arm the first version failed: it predicted 0.79 retention at
    # sigma=1.27 where the direct measurement gives ~0.40, because DC leakage
    # had parked most of the density below 0.01 cyc/px where blur does nothing.
    print("\n  COMMISSIONING -- predict a known blur's effect on the statistic:")
    print("    sigma    predicted   measured    ratio")
    hp0 = raw - cv2.GaussianBlur(raw, (0, 0), HP_SIGMA)
    e0 = float((hp0.astype(np.float64) ** 2).mean())
    worst = 0.0
    for s in (0.53, 0.83, 1.27, 1.79):
        pred = float((w * np.exp(-2.0 * np.pi ** 2 * s ** 2 * f ** 2) ** 2).sum())
        b = cv2.GaussianBlur(raw, (0, 0), s)
        hpb = b - cv2.GaussianBlur(b, (0, 0), HP_SIGMA)
        meas = float((hpb.astype(np.float64) ** 2).mean()) / e0
        worst = max(worst, abs(pred - meas) / max(meas, 1e-9))
        print(f"    {s:.2f}     {pred:.4f}      {meas:.4f}     {pred / meas:.3f}")
    ok = worst < 0.15
    print(f"\n  worst relative error {100 * worst:.1f}%  -> "
          f"{'COMMISSIONED' if ok else 'NOT COMMISSIONED - do not predict with this'}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
