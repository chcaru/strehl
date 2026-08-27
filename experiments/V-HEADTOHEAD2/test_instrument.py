"""Two instrument-level tests whose answers are known in advance.

TEST 1 -- TONE.  h2.to_linear is a transcription of image_out.rs::develop_pixel
run backwards.  Transcription is exactly the kind of thing that is wrong and
still looks plausible, so it needs a ground truth that does not come from the
same source as the transcription.

  Two renders of the SAME merge (same frames, same pre-solved warpmap, same
  gather) at --exposure 2.34 and --exposure 1.34.  --exposure is one multiply
  in linear light BEFORE the tone curve, so the light entering the curve
  differs by exactly 2^1.00 = 2.  The tool's own auto-tone then picks
  DIFFERENT curves from the scaled histogram, and it printed them:

      2.34 EV  black 0.02520  white 1.01550
      1.34 EV  black 0.01260  white 0.50775

  which are exactly halved -- a first, free confirmation that exposure really
  is a pure pre-curve multiply.  PREDICTION: inverting each render with its own
  printed tone and forming ratio = linear(2.34) / linear(1.34) must give 2.000,
  FLAT across the tonal range.  If s_curve, the toe, or the luma coupling is
  mis-transcribed, the ratio bends with level.  A bend is a failure.

  The falsification arm: repeat with the tone deliberately NOT removed (compare
  raw u16), which must bend badly.  A test that only ever passes is not a test.

TEST 2 -- REGISTRATION.  integer_shift must recover a planted integer offset.
"""
import sys

import numpy as np

import h2
import rois

R = r"C:\dev\strehl-out\V-H2H2\renders"
L = r"C:\dev\strehl-out\V-H2H2\logs"


def load(tag):
    return h2.Render(rf"{R}\{tag}.tiff", log=rf"{L}\{tag}.log", name=tag)


def decile_ratio(hi, lo, scale, label, nbin=12):
    """Ratio hi/(lo*scale) binned by level of `lo`.  Flatness is the test."""
    m = (lo > 0) & (hi > 0)
    hi, lo = hi[m], lo[m]
    q = np.quantile(lo, np.linspace(0.02, 0.98, nbin + 1))
    print(f"  {label}:  bin   level(lo)      ratio      n")
    ratios = []
    for i in range(nbin):
        sel = (lo >= q[i]) & (lo < q[i + 1])
        if sel.sum() < 50:
            continue
        r = float(np.median(hi[sel] / (lo[sel] * scale)))
        ratios.append(r)
        print(f"            {i:2d}   {q[i]:10.5f}   {r:8.5f}   {int(sel.sum())}")
    ratios = np.array(ratios)
    spread = ratios.max() / ratios.min()
    print(f"    -> median {np.median(ratios):.5f}   max/min across bins "
          f"{spread:.5f}   (flat == 1.00000)")
    return float(np.median(ratios)), float(spread)


def main():
    print("=" * 74)
    print("TEST 1  TONE INVERSION vs a render with a KNOWN 2.000x light ratio")
    print("=" * 74)
    hi = load("tone-e2p34")
    lo = load("tone-e1p34")
    print(f"  hi {hi.tone}")
    print(f"  lo {lo.tone}")
    print(f"  black ratio {hi.tone.black/lo.tone.black:.6f}   "
          f"white ratio {hi.tone.white/lo.tone.white:.6f}   (both must be 2.000000)")

    # a broad, deterministic sample of the frame, not a lucky crop
    ys = range(200, hi.h - 456, 512)
    xs = range(200, hi.w - 456, 512)
    HL, LL, HU, LU = [], [], [], []
    nclip = 0
    for y in ys:
        for x in xs:
            a = hi.raw_crop(y, x, 128)
            b = lo.raw_crop(y, x, 128)
            if a.max() >= 65535 or b.max() >= 65535 or a.min() == 0 or b.min() == 0:
                nclip += 1
                continue
            HL.append(h2.to_linear(a, hi.tone)[:, :, 1].ravel())
            LL.append(h2.to_linear(b, lo.tone)[:, :, 1].ravel())
            HU.append(a[:, :, 1].astype(np.float64).ravel())
            LU.append(b[:, :, 1].astype(np.float64).ravel())
    n_used = len(HL)
    print(f"  sample tiles: {n_used} used, {nclip} dropped for clipping, "
          f"{n_used + nclip} examined")
    HL = np.concatenate(HL); LL = np.concatenate(LL)
    HU = np.concatenate(HU); LU = np.concatenate(LU)

    print("\n  ARM A (the test): tone REMOVED with each render's own printed tone")
    ra, sa = decile_ratio(HL, LL, 2.0, "linear")
    print("\n  ARM B (falsification): tone NOT removed, raw u16 compared directly")
    rb, sb = decile_ratio(HU, LU, 1.0, "u16   ")

    print(f"\n  VERDICT: tone-removed spread {sa:.5f} vs raw-u16 spread {sb:.5f}")
    passed = (sa < 1.02) and (sb > 1.10) and (0.98 < ra < 1.02)
    print(f"  TEST 1 {'PASS' if passed else 'FAIL'}  "
          f"(pass = removed ratio in [0.98,1.02] AND removed spread < 1.02 "
          f"AND raw spread > 1.10)")

    print()
    print("=" * 74)
    print("TEST 2  integer_shift recovers a PLANTED offset")
    print("=" * 74)
    ref = load("113-A-g1")
    detail, flat, counts = rois.census(ref, t=256, pad=32, verbose=False)
    rng = np.random.default_rng(3)
    tot_ok = tot_n = 0
    allfails = []
    for i in rng.permutation(len(detail))[:8]:
        y, x = detail[i]
        ok, n, fails = h2.commission_shift(ref, y, x)
        tot_ok += ok; tot_n += n; allfails += [(y, x) + f for f in fails]
    print(f"  DETAIL ROIs: {tot_ok}/{tot_n} planted offsets recovered exactly")
    for f in allfails[:10]:
        print(f"    MISS at {f[0]},{f[1]}: planted {f[2]} got {f[3]} peak {f[4]:.4f}")
    fl_ok = fl_n = 0
    flfails = []
    for i in rng.permutation(len(flat))[:8]:
        y, x = flat[i]
        ok, n, fails = h2.commission_shift(ref, y, x)
        fl_ok += ok; fl_n += n; flfails += [(y, x) + f for f in fails]
    print(f"  FLAT   ROIs: {fl_ok}/{fl_n} planted offsets recovered exactly "
          f"(featureless ROIs are where registration SHOULD struggle)")
    for f in flfails[:6]:
        print(f"    MISS at {f[0]},{f[1]}: planted {f[2]} got {f[3]} peak {f[4]:.4f}")
    print(f"  TEST 2 {'PASS' if tot_ok == tot_n else 'FAIL'} on DETAIL "
          f"(the ROI class every comparison is made on)")

    print()
    print("=" * 74)
    print("TEST 3  measured A->B residual offset on the real half-pair")
    print("=" * 74)
    for subj in ("113", "cb"):
        A = load(f"{subj}-A-g1"); B = load(f"{subj}-B-g1")
        det, fl, _ = rois.census(A, t=256, pad=32, verbose=False)
        sh = []
        for i in rng.permutation(len(det))[:30]:
            y, x = det[i]
            ca = A.crop(y, x, 256)[0]
            cb = B.crop(y, x, 256)[0]
            sh.append(h2.integer_shift(ca, cb)[:2])
        sh = np.array(sh)
        u, c = np.unique(sh, axis=0, return_counts=True)
        print(f"  {subj}: {len(sh)} ROIs -> " +
              ", ".join(f"{tuple(uu)}x{cc}" for uu, cc in zip(u.tolist(), c.tolist())))


if __name__ == "__main__":
    sys.exit(main())
