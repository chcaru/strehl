"""BUILD-PYRNOISE -- measure every arm's flat-ROI noise and detail, externally.

ROI SELECTION. Chosen on the MEAN of the arms, never on one arm, because a ROI
chosen on one arm picks that arm as the winner. The mean is taken over the
MATCHED-SITE family only -- the arms that sit on the raw plane grid with no
resampling anywhere (`geometry.py` measures that family's mutual displacement as
exactly 0.000 px). The aligned arms are then read at the same ROI mapped through
the magnification the alignment applies.

DENOMINATOR. The README's column is "against a single unstacked frame", and the
existing table's denominator is frame 11 of the 22-frame bracket -- which is also
the frame the aligner picks as its own reference. Fact 441 measured a single
number moving 1.60x over the free choice of denominator frame, so the frame-11
ratio is reported WITH the full distribution over every single frame beside it.

DETAIL IS A BOUND, NOT A VALUE. `detail_bakeoff.py` ran eight candidate detail
statistics against pre-registered bars and NONE passed: on this content, noise
immunity and blur sensitivity trade off against each other and no candidate
reaches the 3%-noise / 15%-blur corner. `f50(f_lo=0.05)` is used anyway, but
only as a BOUND, because it has the best discrimination ratio of the eight
(10.9x: it moves 2.03% on a 1 px blur and at most 0.19% on noise plants up to
+100%) and its contrast invariance is exact. Its readings are converted into
EQUIVALENT GAUSSIAN BLUR PIXELS against a per-subject calibration, so the
resolution of the instrument is visible in the same units as the answer:
roughly +/-0.09 px. Any arm difference below that is NOT interpretable.
"""

import json
import pathlib
import sys

import numpy as np
from scipy.ndimage import gaussian_filter, zoom

import pyrnoise as pn
import admission

RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")

# Arms that live on the raw plane grid: no alignment, no interpolation.
MATCHED = ["pyr_default_noalign", "pyr_g4p5_noalign", "est_g2_noalign", "argmax"]
# Arms the alignment has resampled. Read at the mapped ROI.
ALIGNED = ["pyr_default", "pyr_g4p5", "est_g2"]

M2_ROI = (2272, 1344, 256, 256)          # the ROI fact 19 and M53 were measured on
ROI_SIZE = 256
BORDER = 200                              # keep clear of the alignment coverage edge
TOPK = 5                                  # headline ratio is the median over this many windows
F_LO = 0.05                               # frozen in commissioning, before any arm was read
BLUR_LADDER = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)


def fov_scale(err_path):
    """The magnification the run applied, read from the run's OWN banner."""
    for line in pathlib.Path(err_path).read_text(encoding="utf8", errors="replace").splitlines():
        if "field of view scaled to" in line:
            return 1.0 / float(line.split("field of view scaled to")[1].split()[0])
    return 1.0


def map_roi(roi, shape, s):
    """Map a ROI from the unaligned grid to the aligned grid: p' = c + s*(p - c)."""
    H, W = shape
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    x, y, w, h = roi
    mx = cx + s * (x + w / 2.0 - cx)
    my = cy + s * (y + h / 2.0 - cy)
    return (int(round(mx - w / 2.0)), int(round(my - h / 2.0)), w, h)


def choose_rois(mean_img, s, size=ROI_SIZE, stride=64):
    """Flattest and most-detailed windows of `mean_img`, with guards.

    The flat ROI is the argmin of high-pass energy, but an unguarded argmin
    lands on dead black or on a blown highlight -- regions where the statistic
    is quantisation or clipping rather than noise. Both are excluded, and the
    guards are reported so the choice can be checked.

    A candidate must clear the border on BOTH grids: a window that is legal on
    the raw plane can map, under the alignment magnification, into the aligned
    arm's extrapolated edge, and would then compare a real region against a
    manufactured one.
    """
    H, W = mean_img.shape
    hp = mean_img - pn.uniform_filter(mean_img, size=pn.BOX, mode="reflect")
    lo, hi = np.percentile(mean_img, [2.0, 99.5])
    cands = []
    for y in range(BORDER, H - size - BORDER + 1, stride):
        for x in range(BORDER, W - size - BORDER + 1, stride):
            ax, ay, _, _ = map_roi((x, y, size, size), (H, W), s)
            if not (BORDER <= ax <= W - size - BORDER and BORDER <= ay <= H - size - BORDER):
                continue
            tile = mean_img[y:y + size, x:x + size]
            if tile.min() < lo or tile.max() > hi:
                continue
            e = float(np.abs(hp[y:y + size, x:x + size]).mean())
            cands.append((e, x, y, float(tile.mean())))
    if not cands:
        raise RuntimeError("no candidate ROI survived the guards")
    cands.sort()
    flat = cands[0]
    det = cands[-1]
    flat_k = [(c[1], c[2], size, size) for c in cands[:TOPK]]
    return ((flat[1], flat[2], size, size), flat[0], flat[3],
            (det[1], det[2], size, size), det[0], det[3], len(cands), flat_k)


def resample_control(tile, s):
    """How much noise does the alignment's magnification itself remove?

    The aligned arms are catmull-rom resampled by `s`. Interpolation is a
    low-pass, so it attenuates noise for free -- an aligned arm could win the
    noise column without its merge doing anything. This plants the same
    magnification on a SINGLE FRAME, where there is no merge to help, and
    reports the attenuation. That number is the size of the confound; it is a
    bound, not a correction, because scipy's cubic spline is not the binary's
    catmull-rom (spline interpolation is the sharper of the two, so this
    UNDERSTATES the real attenuation and is the conservative direction).

    Fails loudly in the direction that matters: if this returns a large
    attenuation, the aligned arms' advantage is not attributable to the merge.
    """
    z = zoom(tile.astype(np.float64), s, order=3, mode="reflect", grid_mode=False)
    c = (z.shape[0] - tile.shape[0]) // 2
    z = z[c:c + tile.shape[0], c:c + tile.shape[1]]
    return pn.raw_sd(z) / pn.raw_sd(tile), pn.hp_sd(z) / pn.hp_sd(tile)


def second_detail_roi(mean_img, first, size=ROI_SIZE, stride=64, min_sep=600):
    """A second, well-separated detail window, for replication of the ordering.

    One tile of one photograph is not a result. If the arm ordering flips
    between two disjoint tiles the detail reading is not carrying information
    about the merge, and the report has to say so.
    """
    H, W = mean_img.shape
    hp = mean_img - pn.uniform_filter(mean_img, size=pn.BOX, mode="reflect")
    lo, hi = np.percentile(mean_img, [2.0, 99.5])
    fx, fy = first[0], first[1]
    best = None
    for y in range(BORDER, H - size - BORDER + 1, stride):
        for x in range(BORDER, W - size - BORDER + 1, stride):
            if abs(x - fx) < min_sep and abs(y - fy) < min_sep:
                continue
            tile = mean_img[y:y + size, x:x + size]
            if tile.min() < lo or tile.max() > hi:
                continue
            e = float(np.abs(hp[y:y + size, x:x + size]).mean())
            if best is None or e > best[0]:
                best = (e, x, y)
    return (best[1], best[2], size, size) if best else None


def blur_calibration(tile):
    """f50 as a function of planted Gaussian blur, on this subject's own tile.

    Turns a bare f50 difference into a number with a unit somebody can argue
    with. Returns (sigmas, f50s), monotone decreasing in sigma.
    """
    return (np.array(BLUR_LADDER),
            np.array([pn.f50(gaussian_filter(tile, s) if s > 0 else tile, f_lo=F_LO)
                      for s in BLUR_LADDER]))


def equiv_blur_px(f, sigmas, f50s):
    """Invert the calibration: what blur would move the reference tile to `f`."""
    order = np.argsort(f50s)
    return float(np.interp(f, f50s[order], sigmas[order]))


def measure_subject(subject):
    d = RENDERS / subject
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    if not frames:
        raise RuntimeError(f"no single-frame renders in {d}")

    imgs = {}
    for tag in MATCHED + ALIGNED + frames:
        p = d / f"{tag}.tif"
        if p.exists():
            imgs[tag] = pn.green(p)
    shape = imgs[MATCHED[0]].shape

    s = fov_scale(d / "pyr_default.err")

    # --- ROI chosen on the MEAN of the matched-site arms -------------------
    pool = [t for t in MATCHED if t in imgs] + [frames[len(frames) // 2]]
    mean_img = np.mean([imgs[t] for t in pool], axis=0)
    (flat_roi, flat_e, flat_mean, det_roi, det_e, det_mean,
     ncand, flat_k) = choose_rois(mean_img, s)

    flat_roi_a = map_roi(flat_roi, shape, s)
    det_roi_a = map_roi(det_roi, shape, s)
    m2_roi_a = map_roi(M2_ROI, shape, s)
    det2_roi = second_detail_roi(mean_img, det_roi)
    det2_roi_a = map_roi(det2_roi, shape, s) if det2_roi else None

    print(f"\n{'=' * 78}\n{subject}\n{'=' * 78}")
    print(f"ROI pool (mean of arms) : {', '.join(pool)}")
    print(f"candidate windows       : {ncand} of size {ROI_SIZE} on stride 64, guarded")
    print(f"FLAT ROI  (unaligned)   : {flat_roi}   mean {flat_mean:8.1f} DN   hp|.| {flat_e:.3f}")
    print(f"FLAT ROI  (aligned)     : {flat_roi_a}   (magnification {s:.6f} from the run's own banner)")
    print(f"DETAIL ROI(unaligned)   : {det_roi}   mean {det_mean:8.1f} DN   hp|.| {det_e:.3f}")
    print(f"DETAIL ROI(aligned)     : {det_roi_a}")
    print(f"DETAIL ROI 2 (replicate): {det2_roi}")

    ref = "frame011" if "frame011" in imgs else frames[len(frames) // 2]
    sig, f50s = blur_calibration(pn.crop(imgs[ref], det_roi))
    print(f"blur calibration on {ref}: f50 " +
          " ".join(f"{a:.4f}@{b:.2f}px" for b, a in zip(sig, f50s)))

    rs_raw, rs_hp = resample_control(pn.crop(imgs[ref], flat_roi), s)
    print(f"RESAMPLE CONTROL        : magnifying {ref}'s flat ROI by {s:.6f} alone moves "
          f"raw_sd {rs_raw:.4f}x, hp_sd {rs_hp:.4f}x")
    print("  (a single frame, no merge. An aligned arm's advantage BEYOND this is the merge's;")
    print("   the part at or above it is interpolation. scipy's cubic spline is sharper than")
    print("   catmull-rom, so this UNDERSTATES the confound -- the conservative direction.)")

    print()
    adm_ok, adm_r = admission.report(imgs, frames, flat_roi, "chosen")
    adm_k = [admission.admission(imgs, frames, w)[0] for w in flat_k]
    print(f"  same test at all {TOPK} flattest windows: " +
          " ".join(f"{v:.2f}" for v in adm_k) +
          f"   -> {sum(v <= admission.BAR for v in adm_k)}/{TOPK} admissible")

    rows = {}
    for tag, img in imgs.items():
        aligned = tag in ALIGNED
        fr = flat_roi_a if aligned else flat_roi
        dr = det_roi_a if aligned else det_roi
        dr2 = (det2_roi_a if aligned else det2_roi)
        mr = m2_roi_a if aligned else M2_ROI
        st = pn.roi_stats(img, fr)
        st["m2_raw_sd"] = pn.raw_sd(pn.crop(img, mr))
        st["m2_hp_sd"] = pn.hp_sd(pn.crop(img, mr, pn.BOX))
        # fact 1441: a zoomed arm's spectrum is compressed by the magnification,
        # which reads as sharpness. Put every arm in SCENE frequency units.
        k = s if aligned else 1.0
        st["f50_detail"] = pn.f50(pn.crop(img, dr), f_lo=F_LO) * k
        st["f50_detail2"] = pn.f50(pn.crop(img, dr2), f_lo=F_LO) * k if dr2 else np.nan
        st["f50_flat"] = pn.f50(pn.crop(img, fr), f_lo=F_LO) * k      # rule 9 control
        st["aligned"] = aligned
        rows[tag] = st
    for tag in rows:
        rows[tag]["blur_px"] = equiv_blur_px(rows[tag]["f50_detail"], sig, f50s)
        rows[tag]["blur_px2"] = equiv_blur_px(rows[tag]["f50_detail2"], sig, f50s)

    # --- denominators ------------------------------------------------------
    fr_raw = np.array([rows[f]["raw_sd"] for f in frames])
    fr_hp = np.array([rows[f]["hp_sd"] for f in frames])
    fr_f50 = np.array([rows[f]["f50_detail"] for f in frames])

    print(f"\nsingle-frame denominators, n={len(frames)}  (reference frame for the ratio: {ref})")
    print(f"  raw_sd : {ref} {rows[ref]['raw_sd']:8.3f} DN | median {np.median(fr_raw):8.3f} "
          f"[{fr_raw.min():.3f} .. {fr_raw.max():.3f}]  spread {fr_raw.max()/fr_raw.min():.3f}x")
    print(f"  hp_sd  : {ref} {rows[ref]['hp_sd']:8.3f} DN | median {np.median(fr_hp):8.3f} "
          f"[{fr_hp.min():.3f} .. {fr_hp.max():.3f}]  spread {fr_hp.max()/fr_hp.min():.3f}x")
    print(f"  f50    : {ref} {rows[ref]['f50_detail']:8.5f} c/px | median {np.median(fr_f50):8.5f} "
          f"[{fr_f50.min():.5f} .. {fr_f50.max():.5f}]")

    hdr = (f"\n{'arm':<22} {'algn':>4} {'raw_sd':>9} {'LEGACY':>8} {'hp_sd':>9} {'HP':>8} "
           f"{'f50':>9} {'blurpx':>7} {'blurpx2':>8} {'f50flat':>8}")
    print(hdr)
    print("-" * (len(hdr) - 1))
    order = MATCHED + ALIGNED + [ref]
    for tag in order:
        if tag not in rows:
            continue
        r = rows[tag]
        print(f"{tag:<22} {'Y' if r['aligned'] else '.':>4} "
              f"{r['raw_sd']:9.3f} {r['raw_sd']/rows[ref]['raw_sd']:7.3f}x "
              f"{r['hp_sd']:9.3f} {r['hp_sd']/rows[ref]['hp_sd']:7.3f}x "
              f"{r['f50_detail']:9.5f} {r['blur_px']:7.2f} {r['blur_px2']:8.2f} "
              f"{r['f50_flat']:8.5f}")
    print("  blurpx = equivalent Gaussian blur of the REFERENCE FRAME that would give this")
    print("  f50. Larger = softer. Instrument resolution ~0.09 px; blurpx2 replicates on a")
    print("  second, disjoint tile. The statistic FAILED its registered blur bar -- read")
    print("  these as bounds, and read a RISE in detail as uninterpretable (rule 18).")

    # --- robustness: the headline must not depend on ONE window ------------
    print(f"\nROBUSTNESS -- the same ratio at each of the {TOPK} flattest guarded windows.")
    print("A headline that only survives at the argmin window is a headline about that window.")
    swept = {}
    for tag in MATCHED + ALIGNED:
        if tag not in imgs:
            continue
        vals_raw, vals_hp = [], []
        for w in flat_k:
            ww = map_roi(w, shape, s) if tag in ALIGNED else w
            wr = w  # the denominator is always read on the raw plane
            vals_raw.append(pn.raw_sd(pn.crop(imgs[tag], ww)) / pn.raw_sd(pn.crop(imgs[ref], wr)))
            vals_hp.append(pn.hp_sd(pn.crop(imgs[tag], ww, pn.BOX)) /
                           pn.hp_sd(pn.crop(imgs[ref], wr, pn.BOX)))
        swept[tag] = {"raw": vals_raw, "hp": vals_hp}
    print(f"  {'arm':<22} {'LEGACY median':>14} {'[min .. max]':>18} "
          f"{'HP median':>10} {'[min .. max]':>18}")
    for tag in MATCHED + ALIGNED:
        if tag not in swept:
            continue
        a, b = np.array(swept[tag]["raw"]), np.array(swept[tag]["hp"])
        print(f"  {tag:<22} {np.median(a):13.3f}x  [{a.min():.3f} .. {a.max():.3f}]     "
              f"{np.median(b):9.3f}x  [{b.min():.3f} .. {b.max():.3f}]")
    print(f"  windows: {', '.join(str(w[:2]) for w in flat_k)}")

    print(f"\nM2's historical ROI {M2_ROI}, legacy raw sd ratio vs {ref}:")
    m2_ok, m2_r = admission.report(imgs, frames, M2_ROI, "M2 ROI")
    for tag in order:
        if tag not in rows:
            continue
        print(f"  {tag:<22} {rows[tag]['m2_raw_sd']:9.3f} DN  "
              f"{rows[tag]['m2_raw_sd']/rows[ref]['m2_raw_sd']:7.3f}x   "
              f"hp {rows[tag]['m2_hp_sd']/rows[ref]['m2_hp_sd']:7.3f}x")

    out = {
        "subject": subject, "flat_roi": flat_roi, "flat_roi_aligned": flat_roi_a,
        "flat_windows_topk": flat_k, "swept": swept,
        "resample_control": {"raw_sd": rs_raw, "hp_sd": rs_hp},
        "admission": {"ratio": adm_r, "passed": bool(adm_ok), "topk": adm_k,
                      "bar": admission.BAR, "m2_ratio": m2_r, "m2_passed": bool(m2_ok)},
        "detail_roi": det_roi, "detail_roi_aligned": det_roi_a, "detail_roi2": det2_roi,
        "fov_scale": s, "ref_frame": ref, "n_frames_measured": len(frames),
        "blur_calibration": {"sigma_px": list(sig), "f50": list(f50s)},
        "frame_raw_sd": {f: rows[f]["raw_sd"] for f in frames},
        "frame_hp_sd": {f: rows[f]["hp_sd"] for f in frames},
        "rows": {k: {kk: (float(vv) if isinstance(vv, (int, float, np.floating)) else vv)
                     for kk, vv in v.items()} for k, v in rows.items()},
    }
    (RENDERS / subject / "_measured.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    subs = sys.argv[1:] or ["109MSDCF"]
    for s in subs:
        measure_subject(s)
