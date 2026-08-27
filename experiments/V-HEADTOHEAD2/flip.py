"""THE MEASUREMENT.  Pre-flip vs post-flip gather, plus the real-pipeline
nearest-neighbour arm that decides whether the instrument may be believed.

ONE BINARY, TWO ARMS.  Both arms are
  C:\\dev\\strehl-out\\acceptance-pins\\740e7056\\target\\release\\strehl.exe
  sha256 15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0
differing only in STREHL_FULLRES_GATHER=0 vs =1.  The env var is potent (the
outputs differ by hash) and an unrecognised value panics with exit 101 naming
the variable -- the red control, which fired.

GEOMETRY IS PINNED.  {subj}-A-g0 and -A-g1 use ONE pre-solved warpmap; -B-g0
and -B-g1 use ANOTHER.  Whatever residual A<->B misregistration exists is
therefore IDENTICAL in the g0 pair and the g1 pair and divides out of
C_g1/C_g0.  It does NOT divide out of an absolute comparison.

THE NN ARM.  {subj}-A-nn-g1 and -B-nn-g1 use sidecars byte-identical to the
catmull-rom ones except the single token "catmull-rom" -> "nearest", so the
warps are the same f64s and only the gather kernel differs.  The tool confirms
on stderr: "--resampler asked for CatmullRom but the sidecar named by
STREHL_WARPMAP was solved with Nearest ... resampler: Nearest".
Nearest is a REAL DEGRADATION (the help calls nearest and bilinear "cheaper and
worse").  PRE-REGISTERED: C must rate it WORSE.  If C rates it better, C
carries the same defect as the retracted statistic and this milestone's answer
is that no instrument here can decide fine-scale resolution.

ROIs are chosen ONCE and shared by every arm; an ROI that clips in ANY arm is
dropped from ALL of them, so every ratio below is paired.
"""
import sys

import numpy as np
from scipy import ndimage

import h2
import rois

LIN = r"C:\dev\strehl-out\V-H2H2\lin"
T = 256
PAD = 32
FULL = T + 2 * PAD


def load(tag):
    return h2.Render(rf"{LIN}\{tag}.tiff", name=tag, linear=True)


def gather(pairs, roiset, transform=None, fine=False):
    """pairs: {arm: (RenderA, RenderB)}.  Returns arm -> (PA, PB, C) each
    (nroi, nband), over the ROIs that clip in NO arm.  Also a joint census."""
    masks = h2.band_masks(T)
    NBIN = 64
    edges = np.linspace(0.0, 0.5, NBIN + 1)
    fidx = np.clip(np.digitize(h2.radial(T).ravel(), edges) - 1, 0, NBIN - 1)
    norm = (T * T) ** 2 * (h2.window(T) ** 2).mean()
    out = {a: [[], [], []] for a in pairs}
    fout = {a: [np.zeros(NBIN), np.zeros(NBIN), np.zeros(NBIN)] for a in pairs}
    used = 0
    dropped = 0
    for (y, x) in roiset:
        crops = {}
        bad = False
        for a, (A, B) in pairs.items():
            ca, na = A.crop(y - PAD, x - PAD, FULL)
            cb, nbc = B.crop(y - PAD, x - PAD, FULL)
            if na or nbc:
                bad = True
                break
            crops[a] = (ca, cb)
        if bad:
            dropped += 1
            continue
        used += 1
        for a, (ca, cb) in crops.items():
            if transform is not None:
                ca, cb = transform(ca, cb)
            fa = h2.contrast_fft(ca[PAD:PAD + T, PAD:PAD + T])
            fb = h2.contrast_fft(cb[PAD:PAD + T, PAD:PAD + T])
            PA, PB, C = h2.pair_bands(fa, fb, masks, T)
            out[a][0].append(PA); out[a][1].append(PB); out[a][2].append(C)
            if fine:
                fout[a][0] += np.bincount(fidx, (np.abs(fa) ** 2).ravel() / norm, NBIN)
                fout[a][1] += np.bincount(fidx, (np.abs(fb) ** 2).ravel() / norm, NBIN)
                fout[a][2] += np.bincount(fidx, np.real(fa * np.conj(fb)).ravel() / norm, NBIN)
    res = {a: tuple(np.array(v) for v in out[a]) for a in out}
    return res, used, dropped, len(roiset), (0.5 * (edges[:-1] + edges[1:]), fout)


def paired_ratio(num, den, reps=4000, seed=5):
    n = num.shape[0]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, (reps, n))
    ns = num[idx].sum(1)
    ds = den[idx].sum(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        bs = np.where(ds != 0, ns / ds, np.nan)
    return (num.sum(0) / den.sum(0),
            np.nanpercentile(bs, 2.5, axis=0),
            np.nanpercentile(bs, 97.5, axis=0))


def row(label, pt, lo, hi, mark=None):
    cells = []
    for p, l, h in zip(pt, lo, hi):
        s = f"{p:6.3f}[{l:5.3f},{h:6.3f}]"
        if mark is not None:
            s += "*" if mark(l, h) else " "
        cells.append(s)
    print(f"  {label:<24} " + " ".join(cells))


def blur03(a, b):
    return (ndimage.gaussian_filter(a, 0.3, mode="reflect"),
            ndimage.gaussian_filter(b, 0.3, mode="reflect"))


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "113"
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    print("=" * 100)
    print(f"PRE-FLIP vs POST-FLIP GATHER : {subj}   (linear sRGB, full sensor "
          f"resolution, BT.709 luma, no transfer curve)")
    print("=" * 100)
    pairs = {
        "g0": (load(f"{subj}-A-g0"), load(f"{subj}-B-g0")),
        "g1": (load(f"{subj}-A-g1"), load(f"{subj}-B-g1")),
        "nn": (load(f"{subj}-A-nn-g1"), load(f"{subj}-B-nn-g1")),
    }
    ref = pairs["g1"][0]
    detail, flat, counts = rois.census(ref, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(7)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]
    fl = [flat[i] for i in rng.permutation(len(flat))[:min(nroi, len(flat))]]

    hdr = " ".join(f"{a:.2f}-{b:.2f}".center(20) for a, b in h2.BANDS)
    print(f"\n  {'':<24} {hdr}")

    res, used, dropped, tot, (fc, fine) = gather(pairs, det, fine=True)
    print(f"\n  DETAIL ROIs: {tot} offered = {used} used in ALL THREE arms + "
          f"{dropped} dropped (clipped in at least one arm)")
    assert used + dropped == tot

    print("\n--- FLOOR (a) byte-identical: the same files measured twice ---")
    res2, _, _, _, _ = gather(pairs, det)
    d = np.abs(res2["g1"][2] - res["g1"][2]).max()
    print(f"  max |C - C'| over {used} ROIs x {len(h2.BANDS)} bands: {d:.3e}"
          f"   ({'EXACT -- floor is 0' if d == 0 else 'NOT REPRODUCIBLE'})")

    print("\n--- FLOOR (b) ROI sampling: two DISJOINT halves of the ROI set ---")
    oo = np.arange(0, used, 2)
    ee = np.arange(1, used, 2)
    r1 = res["g1"][2][oo].sum(0) / res["g0"][2][oo].sum(0)
    r2 = res["g1"][2][ee].sum(0) / res["g0"][2][ee].sum(0)
    print("  odd  ROIs C_g1/C_g0  " + " ".join(f"{v:20.3f}" for v in r1))
    print("  even ROIs C_g1/C_g0  " + " ".join(f"{v:20.3f}" for v in r2))
    print("  half-to-half spread  " + " ".join(
        f"{max(a, b) / min(a, b):20.3f}" for a, b in zip(r1, r2)))

    print("\n--- FLOOR (c) POTENCY: sigma=0.3 px blur, the smallest disturbance claimed visible ---")
    resb, _, _, _, _ = gather(pairs, det, transform=blur03)
    pt, lo, hi = paired_ratio(resb["g1"][2], res["g1"][2])
    row("C(blur 0.3) / C", pt, lo, hi)

    print("\n--- ARM THAT DECIDES: real nearest-neighbour gather vs catmull-rom ---")
    print("    PRE-REGISTERED: must be < 1 above 0.10, or C is unusable.")
    pt, lo, hi = paired_ratio(res["nn"][2], res["g1"][2])
    row("C_nearest / C_catmull", pt, lo, hi)
    verdict = all(h < 1.0 for b, h in zip(h2.BANDS, hi) if b[0] >= 0.10)
    print("    NN ARM: " + ("PASS -- C charges for a real degradation"
                            if verdict else "FAIL -- C rewards a degradation"))
    ptp, lop, hip = paired_ratio(0.5 * (res["nn"][0] + res["nn"][1]),
                                 0.5 * (res["g1"][0] + res["g1"][1]))
    row("P_nearest / P_catmull", ptp, lop, hip)
    vp = all(h < 1.0 for b, h in zip(h2.BANDS, hip) if b[0] >= 0.10)
    print("    same arm on the RETRACTED statistic P: " +
          ("pass" if vp else "FAIL -- this is the documented +29%/+42% defect"))

    print("\n=== RESULT: coherent power, post-flip / pre-flip (* = CI excludes 1) ===")
    pt, lo, hi = paired_ratio(res["g1"][2], res["g0"][2])
    row("C_g1 / C_g0  DETAIL", pt, lo, hi, mark=lambda l, h: l > 1 or h < 1)
    for arm in ("g0", "g1", "nn"):
        PA, PB, C = res[arm]
        g = C.sum(0) / np.sqrt(PA.sum(0) * PB.sum(0))
        print(f"  {'gamma ' + arm:<24} " + " ".join(f"{v:20.4f}" for v in g))
    g0 = res["g0"][2].sum(0) / np.sqrt(res["g0"][0].sum(0) * res["g0"][1].sum(0))
    g1 = res["g1"][2].sum(0) / np.sqrt(res["g1"][0].sum(0) * res["g1"][1].sum(0))
    print(f"  {'gamma g1/g0':<24} " + " ".join(f"{a / b:20.4f}" for a, b in zip(g1, g0)))

    print("\n--- the RETRACTED statistic P on the same data, for contrast ---")
    pt, lo, hi = paired_ratio(0.5 * (res["g1"][0] + res["g1"][1]),
                              0.5 * (res["g0"][0] + res["g0"][1]))
    row("P_g1 / P_g0  DETAIL", pt, lo, hi)

    print("\n=== SPECIFICITY: FLAT ROIs (bottom 10% of local contrast) ===")
    resf, usedf, dropf, totf, _ = gather(pairs, fl)
    print(f"  FLAT ROIs: {totf} offered = {usedf} used in all arms + {dropf} dropped")
    pt, lo, hi = paired_ratio(resf["g1"][2], resf["g0"][2])
    row("C_g1 / C_g0  FLAT", pt, lo, hi)
    print("\n  ABSOLUTE coherent power -- the question is not whether flat ROIs")
    print("  move, it is whether their level can account for the detail result:")
    print(f"  {'C_g1 DETAIL (per ROI)':<24} " +
          " ".join(f"{v:20.4e}" for v in res["g1"][2].mean(0)))
    print(f"  {'C_g1 FLAT   (per ROI)':<24} " +
          " ".join(f"{v:20.4e}" for v in resf["g1"][2].mean(0)))
    print(f"  {'FLAT / DETAIL':<24} " +
          " ".join(f"{a / b:20.4f}" for a, b in zip(resf["g1"][2].mean(0),
                                                    res["g1"][2].mean(0))))

    print("\n--- fine spectrum (DETAIL).  MECHANISM: the pre-flip gather runs on")
    print("    CFA planes at 3516x2344 against a 7032x4688 output, putting plane")
    print("    Nyquist at f = 0.25 cyc/output px.  The gain must be ~1 well below")
    print("    0.25 and rise through it.  A uniform gain would be a gain artefact.")
    print("     f       C_g0        C_g1       C_nn     C_g1/C_g0  C_nn/C_g1  gam_g0  gam_g1")
    for i in range(len(fc)):
        if fc[i] > 0.49 or fc[i] < 0.02:
            continue
        c0 = fine["g0"][2][i]; c1 = fine["g1"][2][i]; cn = fine["nn"][2][i]
        ga = c0 / np.sqrt(max(fine["g0"][0][i] * fine["g0"][1][i], 1e-300))
        gb = c1 / np.sqrt(max(fine["g1"][0][i] * fine["g1"][1][i], 1e-300))
        print(f"   {fc[i]:.3f}  {c0:.3e}  {c1:.3e}  {cn:.3e}  "
              f"{c1 / c0:9.4f}  {cn / c1:9.4f}  {ga:+.4f}  {gb:+.4f}")


if __name__ == "__main__":
    sys.exit(main())
