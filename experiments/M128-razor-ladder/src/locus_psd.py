r"""M128 / locus_psd — feasibility probe for a third, ESF-free reduction.

THE IDEA. For small-amplitude edge wander, the measured 50%-crossing locus is
the true edge locus convolved with the along-edge marginal of the PSF:

    y_meas(x) = (y_true * h)(x)   =>   Y_meas(k) = Y_true(k) * H(k)

so the locus power spectrum is

    P_meas(k) = P_true(k) * |MTF(k)|^2

and the ratio between two apertures on the SAME blade cancels the unknown
P_true(k) exactly:

    P_A(k) / P_B(k) = MTF_A(k)^2 / MTF_B(k)^2

That turns the ragged edge -- which has been the obstacle for this entire lane
-- into a broadband random test target. It needs no ESF, no half-width choice,
no deramping, and it is immune to the bevel ridge and the veiling glare,
because it never looks at the profile shape at all, only at where the edge is.

WHY THIS PROBE EXISTS. src\across.py measured that the locus residual patterns
correlate at 0.9794 between the two green sublattices of ONE frame, 0.9816
between three adjacent focus frames at ONE aperture, but only 0.8035-0.9154
ACROSS apertures -- and f/8 and f/11 resemble each other (0.9154) far more than
either resembles f/5.6 (0.807, 0.804). The SHARPEST aperture is the outlier.
Noise cannot do that; noise is worst at f/11. Real blur can, and does: at f/5.6
the system resolves fine wander that f/11 smooths away. That is the signal this
probe is trying to read.

THE NOISE PROBLEM, AND ITS EXACT SOLUTION. Estimation noise adds a broadly
white floor to P_meas(k), which would masquerade as a flatter MTF. The two
green sublattices of one frame see the SAME blade with INDEPENDENT photon
noise, so their CROSS-spectrum has zero expected noise contribution. Using
Re<Y_G1(k) conj(Y_G2(k))> in place of |Y(k)|^2 removes the floor by
construction rather than by subtracting an estimate of it.

This script only asks whether the effect is measurable. It does not measure
anything for the record; nothing here is a registered result.

    python src\locus_psd.py f5.6=<frame> f8=<frame> f11=<frame>
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

M88 = Path(__file__).resolve().parents[2] / "M88-optical-ceiling" / "src"
sys.path.insert(0, str(M88))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402
import geom  # noqa: E402
import across  # noqa: E402

SUB_PITCH_MM = 2.0 * 5.12e-3          # green sublattice pitch in mm
NYQ_CYMM = 1.0 / (2.0 * SUB_PITCH_MM)  # 48.828125 cy/mm


def locus_pair(path, band_half, bright_first):
    """The locus residual on BOTH green sublattices of one frame."""
    out = {}
    for plane in ("G1", "G2"):
        out[plane] = across.load_locus(path, plane, band_half, bright_first)
    return out


def common_grid(resids, seg0, seg1):
    """Interpolate each residual onto a common contiguous column grid.

    Gaps are filled by linear interpolation. A gap is a column where the
    crossing was rejected; leaving NaNs would prevent any spectral estimate,
    and interpolation across a short gap is spectrally mild at the low and mid
    frequencies this probe is reading. The gap fraction is reported so the
    effect can be judged rather than assumed.
    """
    x = np.arange(seg0, seg1)
    out, gaps = [], []
    for r in resids:
        v = r[seg0:seg1].copy()
        good = np.isfinite(v)
        gaps.append(1.0 - good.mean())
        if good.sum() < 64:
            return None, None
        v = np.interp(x, x[good], v[good])
        v = v - v.mean()
        out.append(v)
    return np.array(out), gaps


def spectra(sig, detrend_order=3):
    n = len(sig)
    x = np.linspace(-1, 1, n)
    p = np.polyfit(x, sig, detrend_order)
    s = sig - np.polyval(p, x)
    w = np.hanning(n)
    F = np.fft.rfft(s * w)
    k = np.fft.rfftfreq(n, d=SUB_PITCH_MM)   # cycles per mm along the edge
    return k, F


def band_average(k, v, edges):
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (k >= a) & (k < b)
        out.append(float(np.mean(v[m])) if m.sum() else float("nan"))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="+", help="label=path")
    ap.add_argument("--band-half", type=int, default=60)
    ap.add_argument("--seg", nargs=2, type=int, default=[1400, 3400],
                    help="contiguous along-edge column range to analyse")
    ap.add_argument("--dark-first", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    specs = [f.split("=", 1) for f in args.frames]
    seg0, seg1 = args.seg
    print(f"segment columns {seg0}..{seg1}  ({seg1 - seg0} columns = "
          f"{(seg1 - seg0) * SUB_PITCH_MM:.2f} mm along the edge)")
    print(f"green sublattice pitch {SUB_PITCH_MM * 1000:.2f} um, "
          f"along-edge Nyquist {NYQ_CYMM:.3f} cy/mm")

    pairs = {}
    for lab, path in specs:
        pairs[lab] = locus_pair(path, args.band_half, not args.dark_first)
        print(f"  loaded {lab:>6}  {Path(path).name}")

    edges = np.array([2.0, 4.0, 6.0, 9.0, 13.0, 18.0, 25.0, 34.0, 48.828125])
    ctr = 0.5 * (edges[:-1] + edges[1:])

    cross, autos, gapfrac = {}, {}, {}
    for lab in pairs:
        sig, gaps = common_grid([pairs[lab]["G1"]["resid"],
                                 pairs[lab]["G2"]["resid"]], seg0, seg1)
        if sig is None:
            print(f"  {lab}: too few crossings in the segment")
            continue
        gapfrac[lab] = gaps
        k, F1 = spectra(sig[0])
        _, F2 = spectra(sig[1])
        # Cross-spectrum: the noise floor cancels in expectation because the
        # two sublattices carry independent photon noise over the same blade.
        cross[lab] = band_average(k, np.real(F1 * np.conj(F2)), edges)
        autos[lab] = band_average(k, 0.5 * (np.abs(F1) ** 2 + np.abs(F2) ** 2),
                                  edges)

    labs = [s[0] for s in specs if s[0] in cross]
    print("\ngap fraction filled by interpolation, per plane:")
    for lab in labs:
        print(f"  {lab:>6}  G1 {gapfrac[lab][0]:.3f}  G2 {gapfrac[lab][1]:.3f}")

    print("\nLocus cross-power per along-edge frequency band, arbitrary units.")
    print("Cross-power is the noise-free estimate; auto-power carries the "
          "noise floor and is shown so the floor's size is visible.")
    hdr = "".join(f"{c:>10.1f}" for c in ctr)
    print(f"  {'cy/mm':>8}{hdr}")
    for lab in labs:
        print(f"  {lab + ' X':>8}" + "".join(f"{v:10.3e}" for v in cross[lab]))
    for lab in labs:
        print(f"  {lab + ' A':>8}" + "".join(f"{v:10.3e}" for v in autos[lab]))
    print(f"  {'X/A f5.6':>8}" + "".join(
        f"{cross[labs[0]][i] / autos[labs[0]][i]:10.3f}"
        for i in range(len(ctr))) + "   <- 1.0 means noise-free, 0 means "
        "all noise")

    if len(labs) >= 2:
        print("\nTHE PROBE. Ratio of cross-power to the f/5.6 reference. If "
              "the locus carries the MTF, this must FALL with frequency, and "
              "fall further for the smaller aperture.")
        print(f"  {'cy/mm':>8}{hdr}")
        ref = cross[labs[0]]
        for lab in labs[1:]:
            r = cross[lab] / ref
            print(f"  {lab + '/' + labs[0]:>8}" + "".join(
                f"{v:10.3f}" for v in r))
            print(f"  {'sqrt':>8}" + "".join(
                f"{np.sqrt(max(v, 0.0)):10.3f}" for v in r)
                + "   <- MTF ratio, if the model holds")

        print("\nVERDICT OF THE PROBE, stated as a question this cannot "
              "answer on its own: does the sqrt row fall monotonically and "
              "smoothly from ~1 at low frequency? If yes, the method is worth "
              "building and commissioning. If it is flat, or noisy, or rises, "
              "it is not.")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            {"frames": dict(specs), "seg": [seg0, seg1],
             "band_edges_cymm": edges.tolist(),
             "band_centres_cymm": ctr.tolist(),
             "gap_fraction": gapfrac,
             "cross": {l: cross[l].tolist() for l in labs},
             "auto": {l: autos[l].tolist() for l in labs}},
            indent=1, default=float))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
