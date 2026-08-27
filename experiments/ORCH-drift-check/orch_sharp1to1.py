"""At 1:1, is the master sharper than the best frame that went into it?

This is the question a macro photographer actually asks, and no instrument in
this tree has answered it. The halo, blotch, chroma and banding detectors all
ask "is there an artifact"; every one now says no. None of them asks "is it
SHARP", which is the entire point of a focus stacker and the thing the owner
called horrible.

It is also the measurement that prices V-NYQUIST's finding on real data. The
alignment gather runs on half-resolution CFA planes and was measured to lose 51%
of true contrast at 0.20-0.30 cyc/output-px and 88% at 0.30-0.40 on a synthetic
broadband scene. If that carries to real captures, it shows up here: the master
should be sharper than any single frame at coarse scales (it selects the focused
one everywhere) but may be SOFTER at the finest scales, because the gather
filtered them before the election ever ran.

THE BASELINE IS THE FRAME THE SELECTOR WOULD HAVE CHOSEN (section 96). Comparing
a stack against the median input is a strawman that flatters it whenever
selection is working -- that error produced a published halo target that had to
be withdrawn. So: search every sampled source frame for the one sharpest AT THIS
SITE, and compare against that.

Alignment: the master is warped and cropped relative to any frame, so the crops
are registered by integer-shift search over a small range. Integer only -- a
sub-pixel resample would add blur to the very quantity being measured, which is
the one thing this must not do.
"""
import os
import sys
import glob

import numpy as np
import tifffile

from orch_contact import png_rgb, draw_text, LABEL_H

OUT_ROOT = r"C:\dev\strehl-out"
SRC_ROOT = r"D:\personal\macro"

CROP = 560          # rendered at 1:1
SHARE_CLIP_MAX = 0.15   # a source row saturating past this is a display artifact,
                        # not evidence about optics; the column stops being a pair
PATCH = 70          # small enough that ONE frame is in focus across all of it
PATCH_FLOOR = 50.0  # below this in BOTH arms the patch is featureless; skip, count
SEARCH = 48         # integer registration half-range, px
CORR_MIN = 0.50     # below this the crop pair is NOT THE SAME CONTENT; see below
SITE_SHARE = 0.25   # a site below this share of the subject's best site is not
                    # a site: best_site() takes the top N blocks with no floor,
                    # so on a subject with one textured region picks 2 and 3
                    # land in background and the tool scores blown-white master
                    # against read noise. Relative, therefore subject-invariant
                    # by construction -- an absolute floor would just measure
                    # how textured the subject is.
SITE_CLIP_MAX = 0.05  # saturated data has no gradient; a clipped crop cannot be
                      # a sharpness test site at all. Physical, so absolute.


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1]
            + 0.114 * rgb[..., 2]).astype(np.float64)


def detail(y):
    """Gradient energy at two scales, reported separately.

    Reporting one number would hide the whole point: a stacker can win at
    coarse scale (it picked the focused frame) and lose at fine scale (the
    gather filtered it) in the SAME crop, and a single figure averages that
    interesting disagreement away.
    """
    f = np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])
    k = y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2]
    c = np.abs(np.diff(k, axis=1)[:-1, :]) + np.abs(np.diff(k, axis=0)[:, :-1])
    return float(np.mean(f)), float(np.mean(c) / 4.0)


def usm_match(rgb, target_fine, lo=0.0, hi=6.0, iters=18):
    """Unsharp-mask `rgb` until its fine-detail energy reaches `target_fine`.

    This is the control for the patch result, and it exists because the innocent
    explanation for "the master has more fine detail than any source frame" is
    not reconstruction at all -- it is that something in the pipeline sharpened
    the master. A sharpened frame and a reconstructed frame produce the SAME
    number here. They do not produce the same picture: sharpening manufactures
    its contrast by overshooting edges, so matching the master's number by USM
    alone should ring visibly if that is all the master is.

    Returns (rendered, amount). amount is the USM gain needed; a LARGE amount
    that visibly rings while the master does not is evidence the master's detail
    is real. This control cannot prove reconstruction on its own -- it can only
    fail to explain the number away, which is the most any control does.
    """
    y = luma(rgb.astype(np.float64))
    blur = boxblur2(y, 3)
    hp = y - blur
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        f, _ = detail(y + mid * hp)
        if f < target_fine:
            lo = mid
        else:
            hi = mid
    amt = 0.5 * (lo + hi)
    out = rgb.astype(np.float64) + amt * (rgb.astype(np.float64)
                                          - np.stack([boxblur2(rgb[:, :, c].astype(np.float64), 3)
                                                      for c in range(3)], axis=2))
    return np.clip(out, 0, 65535), amt


def boxblur2(a, k):
    c = np.cumsum(np.pad(a, ((0, 0), (k, k)), mode="edge"), axis=1)
    h = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    c = np.cumsum(np.pad(h, ((k, k), (0, 0)), mode="edge"), axis=0)
    return (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)


def patch_gain(ref, reg, patch=PATCH):
    """Master vs the best single frame ON A PATCH SMALL ENOUGH TO BE ONE DEPTH.

    Why this exists, and why the 560 px figure alone is not honest:

    Across a 560 px crop of a curved compound eye no single frame CAN be in
    focus everywhere, so master/best-frame there is a coverage measurement
    wearing a sharpness measurement's clothes. It would read well above 1.0
    for a pure selector that never sharpened a single pixel. That number is a
    real product of stacking, but it is not evidence for this project's thesis.

    On a patch of PATCH px the depth range is small enough that some frame is
    genuinely in focus across all of it. There the best single frame is a fair
    and hard baseline, and the ratio means what it says:

        ratio ~= 1.0   the merge SELECTS. Correct, unremarkable, and what every
                       competing tool already does.
        ratio  > 1.0   the merge RECONSTRUCTS -- producing detail that no single
                       frame contains. That is this project's actual claim.
        ratio  < 1.0   the merge DESTROYS detail its inputs had, which is the
                       defect this project exists to remove.

    Patches with no detail in either arm are skipped, because a ratio of two
    noise floors is a ratio of two noise floors. The skipped count is printed
    separately and is never folded into the count that passed.
    """
    n = ref.shape[0] // patch
    gains, skipped = [], 0
    for py in range(n):
        for px in range(n):
            sl = (slice(py * patch, (py + 1) * patch),
                  slice(px * patch, (px + 1) * patch))
            mf, _ = detail(ref[sl])
            sf = max((detail(c[sl])[0] for _, c in reg), default=0.0)
            if mf < PATCH_FLOOR and sf < PATCH_FLOOR:
                skipped += 1
                continue
            gains.append(mf / sf if sf > 0 else float("inf"))
    return gains, skipped


def best_site(my, n=3):
    """Pick high-detail windows from the MASTER, spread apart."""
    h, w = my.shape
    step = CROP
    scores = []
    for y in range(step, h - CROP - step, step * 2):
        for x in range(step, w - CROP - step, step * 2):
            blk = my[y:y + CROP:4, x:x + CROP:4]
            scores.append((detail(blk)[0], y, x))
    scores.sort(reverse=True)
    picked = []
    for s, y, x in scores:
        if all(abs(y - py) > CROP * 2 or abs(x - px) > CROP * 2
               for _, py, px in picked):
            picked.append((s, y, x))
        if len(picked) == n:
            break
    return picked


def register(ref, mov):
    """Integer shift maximising normalised correlation. No resampling."""
    r = ref - ref.mean()
    best, at = -2.0, (0, 0)
    for dy in range(-SEARCH, SEARCH + 1, 2):
        for dx in range(-SEARCH, SEARCH + 1, 2):
            m = mov[SEARCH + dy:SEARCH + dy + r.shape[0],
                    SEARCH + dx:SEARCH + dx + r.shape[1]]
            if m.shape != r.shape:
                continue
            m = m - m.mean()
            d = np.sqrt(float(np.sum(r * r)) * float(np.sum(m * m)))
            if d <= 0:
                continue
            c = float(np.sum(r * m)) / d
            if c > best:
                best, at = c, (dy, dx)
    return at, best


def commission_reg():
    """Earn CORR_MIN instead of choosing it.

    The gate must reject one thing and accept another, and the two must be far
    enough apart that a single constant separates them:

      REJECT  different content -- the failure that produced the phantom defect
      ACCEPT  the same content, heavily defocused -- the legitimate case, since
              comparing a sharp master against a blurred frame is the entire
              point of this tool and a gate that rejected it would delete the
              measurement it exists to make

    If the accept arm sits below the reject arm, no threshold works and the
    registration gate is the wrong instrument.
    """
    rng = np.random.default_rng(11)
    n = CROP + 900
    # The first version of this arm used sums of sinusoids and the commissioning
    # correctly REFUSED it: a periodic field displaced by 250 px lands on a near
    # repeat of itself and correlated 0.9189, so the reject arm scored like an
    # accept arm and no constant could separate the classes. The field has to be
    # non-periodic to test displacement at all. Multi-scale blurred noise is,
    # and it also keeps the strong low-frequency content that real subjects have
    # -- which is what lets correlation survive heavy defocus, the case the gate
    # must not reject.
    big = np.zeros((n, n))
    for s in (4, 16, 64):
        w = rng.normal(0, 1, (n, n))
        f = np.ones(s) / s
        w = np.apply_along_axis(lambda v: np.convolve(v, f, "same"), 0, w)
        w = np.apply_along_axis(lambda v: np.convolve(v, f, "same"), 1, w)
        big += w * s
    big = np.clip(8000 + 3000 * big / (big.std() + 1e-9), 0, 65535)
    ref = big[450:450 + CROP, 450:450 + CROP]

    def pad_at(oy, ox):
        return big[450 + oy - SEARCH:450 + oy + CROP + SEARCH,
                   450 + ox - SEARCH:450 + ox + CROP + SEARCH]

    def blur(a, k):
        f = np.ones(k) / k
        b = np.apply_along_axis(lambda v: np.convolve(v, f, "same"), 0, a)
        return np.apply_along_axis(lambda v: np.convolve(v, f, "same"), 1, b)

    arms = []
    _, c = register(ref, pad_at(0, 0))
    arms.append(("identical", c, "accept"))
    _, c = register(ref, pad_at(12, -9))
    arms.append(("shifted %d px, inside SEARCH" % 12, c, "accept"))
    _, c = register(blur(ref, 9), pad_at(0, 0))
    arms.append(("defocused 9 px", c, "accept"))
    _, c = register(blur(ref, 21), pad_at(0, 0))
    arms.append(("defocused 21 px", c, "accept"))
    _, c = register(ref, pad_at(250, 250))
    arms.append(("displaced %d px, beyond SEARCH" % 250, c, "reject"))
    _, c = register(ref, rng.normal(8000, 1500, (CROP + 2 * SEARCH,
                                                 CROP + 2 * SEARCH)))
    arms.append(("unrelated content", c, "reject"))

    print("commissioning CORR_MIN = %.2f   (SEARCH = %d px)\n" % (CORR_MIN, SEARCH))
    print("%-34s %8s %8s %s" % ("arm", "corr", "want", "verdict"))
    ok = True
    acc, rej = [], []
    for name, c, want in arms:
        got = "accept" if c >= CORR_MIN else "reject"
        good = got == want
        ok = ok and good
        (acc if want == "accept" else rej).append(c)
        print("%-34s %8.4f %8s %s" % (name, c, want, "ok" if good else "WRONG"))
    print("\naccept arms span %.4f-%.4f; reject arms span %.4f-%.4f"
          % (min(acc), max(acc), min(rej), max(rej)))
    margin = min(acc) - max(rej)
    print("margin between the closest accept and the closest reject: %.4f" % margin)
    if margin <= 0:
        print("NOT COMMISSIONED: the two classes overlap, so no constant "
              "separates them and CORR_MIN cannot be earned by this design.")
        return 1
    print("%s" % ("COMMISSIONED: CORR_MIN sits inside a %.4f-wide gap and "
                 "every arm lands on its intended side." % margin if ok else
                 "NOT COMMISSIONED: an arm landed on the wrong side."))
    return 0 if ok else 1


def commission():
    """Prove the patch statistic can say SELECTION, DEFECT and RECONSTRUCTION.

    A verdict function that has only ever been observed to emit one of its three
    verdicts is not known to be able to emit the other two. Each arm below is
    constructed so the correct answer is known before the number is read.
    """
    rng = np.random.default_rng(7)
    lat = rng.normal(8000, 1500, (CROP, CROP))
    lat = np.clip(lat + 4000 * np.sin(np.arange(CROP) / 3.0)[None, :], 0, 65535)

    def blur(a, k):
        if k <= 1:
            return a.copy()
        c = np.cumsum(np.pad(a, ((0, 0), (k, k)), mode="edge"), axis=1)
        h = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
        c = np.cumsum(np.pad(h, ((k, k), (0, 0)), mode="edge"), axis=0)
        return (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)

    srcs = [("k%d" % k, blur(lat, k)) for k in (2, 3, 4, 5)]
    sharpest = srcs[0][1]
    arms = [("SELECTION   (master == sharpest source)", sharpest, 1.0),
            ("DEFECT      (master blurred past every source)", blur(lat, 8), 0.0),
            ("RECONSTRUCT (master == unblurred latent)", lat, 2.0)]
    print("%-46s %10s %10s   %s" % ("arm", "median", "expect", "verdict"))
    print("-" * 82)
    ok = True
    for label, master, expect in arms:
        gains, skipped = patch_gain(master, srcs)
        g = np.array(gains)
        g = g[np.isfinite(g)]
        med = float(np.median(g)) if g.size else float("nan")
        if expect == 1.0:
            good, want = 0.95 < med < 1.05, "~1.0"
        elif expect == 0.0:
            good, want = med < 0.95, "<1.0"
        else:
            good, want = med > 1.05, ">1.0"
        ok = ok and good
        print("%-46s %10.4f %10s   %s  (%d patches, %d skipped)"
              % (label, med, want, "PASS" if good else "FAIL", g.size, skipped))
    print("\n%s" % ("COMMISSIONED: all three verdicts are reachable."
                    if ok else "NOT COMMISSIONED: a verdict the tool claims to "
                               "emit could not be produced on data built to force it."))
    return 0 if ok else 1


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else "bee-1-cpl"
    nsrc = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    import rawpy

    # The arm was frozen as "SHIP-V2" here too. Same defect as the two gates
    # fixed in 643b719d: this one at least raises SystemExit rather than
    # certifying the wrong corpus, but it still cannot be pointed at a newer
    # render. STREHL_ARM names the subdirectory under OUT_ROOT.
    arm = os.environ.get("STREHL_ARM", "SHIP-V2")
    armdir = os.path.join(OUT_ROOT, arm)
    if not os.path.isdir(armdir):
        armdir = os.path.join(OUT_ROOT, "acceptance", arm)
    if not os.path.isdir(armdir):
        raise SystemExit("no such arm directory for STREHL_ARM=%s" % arm)
    cand = [p for p in glob.glob(os.path.join(armdir, "*.tiff"))
            if os.path.basename(p).startswith(subject)]
    if not cand:
        raise SystemExit("no master for %s in %s" % (subject, armdir))
    m = tifffile.imread(cand[0])[..., :3].astype(np.float64)   # tifffile, not PIL
    my = luma(m)
    sites = best_site(my)
    # Reject sites the picker had no business returning. best_site() takes the
    # top N blocks by detail and returns them unconditionally; on a subject
    # whose textured area is smaller than N blocks it therefore returns
    # background. That is the same failure this lane fixed in orch_smoothcrop.py
    # earlier tonight -- a search that cannot fail returns its least-bad
    # candidate and calls it a find -- and here it manufactured two phantom
    # DEFECT verdicts (flower-bud-alone-cpl 0.285x, pencil-steep-angle-cpl
    # 0.157x) by scoring a blown-white master crop against source read noise.
    scored = []
    for s, y, x in sites:
        crop = my[y:y + CROP, x:x + CROP]
        d = detail(crop)[0]
        clipf = float((m[y:y + CROP, x:x + CROP] >= 65000).mean())
        scored.append((d, clipf, y, x))
    top = max(d for d, _, _, _ in scored) if scored else 0.0
    sites, rejected = [], []
    for d, clipf, y, x in scored:
        share = d / top if top else 0.0
        if clipf > SITE_CLIP_MAX:
            rejected.append((y, x, "clipped %.1f%% > %.0f%%"
                             % (100 * clipf, 100 * SITE_CLIP_MAX)))
        elif share < SITE_SHARE:
            rejected.append((y, x, "detail %.0f is %.0f%% of the best site's %.0f"
                             % (d, 100 * share, top)))
        else:
            sites.append((d, y, x))
    print("master %s  sites %r" % (os.path.basename(cand[0]),
                                   [(y, x) for _, y, x in sites]))
    for y, x, why in rejected:
        print("  site (%d,%d) NOT A SITE: %s" % (y, x, why))
    if not sites:
        raise SystemExit(
            "every candidate site was rejected -- this subject has no region "
            "textured enough to test sharpness, and that is a finding, not a "
            "reason to lower the floor")

    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    idx = np.linspace(0, len(arw) - 1, min(nsrc, len(arw))).astype(int)
    print("scanning %d of %d source frames for the sharpest AT EACH SITE\n"
          % (len(idx), len(arw)))

    srcs = []
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        srcs.append((os.path.basename(arw[i]), luma(s.astype(np.float64)), s))

    rows = []
    patchstats = []
    unregistered = []
    print("%-8s %-14s %10s %10s   %10s %10s   %s"
          % ("site", "best frame", "M_fine", "S_fine", "M_coarse", "S_coarse", "corr"))
    for si, (_, y, x) in enumerate(sites):
        ref = my[y:y + CROP, x:x + CROP]
        mf, mc = detail(ref)
        best = None
        reg = []
        nok = 0
        nbad = 0
        for name, sy, s in srcs:
            if (y + CROP + SEARCH > sy.shape[0]) or (x + CROP + SEARCH > sy.shape[1]):
                continue
            pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
            if pad.shape[0] < CROP + 2 * SEARCH or pad.shape[1] < CROP + 2 * SEARCH:
                continue
            (dy, dx), c = register(ref, pad)
            # The registration correlation was printed by this tool from the
            # start and NOTHING EVER CONDITIONED ON IT. That is the same defect
            # -- a number reported but not tested -- that this lane flagged in
            # its own print-readiness gate an hour earlier, so it is a habit and
            # not an accident.
            #
            # It matters here because focus breathing scales each frame about
            # the optical centre, so displacement grows with radius. Near a
            # frame edge it can exceed SEARCH, registration then fails, and the
            # crop that comes back is DIFFERENT CONTENT. On flower-bud-alone-cpl
            # that put blown-white background in the master row against
            # near-black bud in the source row, and the source's read noise --
            # amplified by the gamma the raw path applies and the master's
            # highlight does not -- scored as "detail", handing the site a
            # 0.283x DEFECT verdict that the merge had no part in.
            #
            # A crop that fails this gate is not a bad measurement. It is not a
            # measurement.
            if c < CORR_MIN:
                nbad += 1
                continue
            nok += 1
            crop = sy[y + dy:y + dy + CROP, x + dx:x + dx + CROP]
            reg.append((name, crop))
            sf, sc = detail(crop)
            if best is None or sf > best[1]:
                best = (name, sf, sc, dy, dx, c, s)
        if best is None:
            unregistered.append((si, nbad))
            print("site %-3d UNREGISTERED  %d of %d source frames correlated "
                  "below %.2f -- NOT MEASURED, not scored"
                  % (si, nbad, nbad + nok, CORR_MIN))
            continue
        patchstats.append((si, patch_gain(ref, reg)))
        name, sf, sc, dy, dx, c, s = best
        print("%-8d %-14s %10.2f %10.2f   %10.2f %10.2f   %.3f  (%d/%d frames "
              "registered)" % (si, name[:14], mf, sf, mc, sc, c, nok, nok + nbad))
        rows.append((si, y, x, m[y:y + CROP, x:x + CROP],
                     s[y + dy:y + dy + CROP, x + dx:x + dx + CROP],
                     name, mf, sf, mc, sc))

    if not rows:
        raise SystemExit("nothing to render")
    print("\nM_fine  = master gradient energy, 1 px scale")
    print("S_fine  = SHARPEST SOURCE FRAME at that site, 1 px scale")
    print("M/S at fine scale is the number V-NYQUIST's gather finding predicts")
    print("should be WEAK; at coarse scale the master should win outright.")
    for si, _, _, _, _, name, mf, sf, mc, sc in rows:
        print("  site %d   fine %.3fx   coarse %.3fx   (vs %s)"
              % (si, mf / sf if sf else 0, mc / sc if sc else 0, name))

    print("\n=== THE HONEST NUMBER: %d px patches, one depth each ===" % PATCH)
    print("Above, no single frame can be in focus across 560 px of a curved")
    print("subject, so that ratio rewards COVERAGE. A pure selector scores well")
    print("on it. Below, some frame IS in focus across the whole patch, so the")
    print("best single frame is a fair baseline and >1.0 means RECONSTRUCTION.")
    for si, (gains, skipped) in patchstats:
        if not gains:
            print("  site %d: %d patches, all below the detail floor -- NOT MEASURED"
                  % (si, skipped))
            continue
        g = np.array(gains, dtype=np.float64)
        finite = g[np.isfinite(g)]
        won = int((finite > 1.0).sum())
        print("  site %d   median %.3fx   p10 %.3fx   p90 %.3fx   "
              "master sharper on %d/%d   (%d skipped, no detail)"
              % (si, float(np.median(finite)), float(np.percentile(finite, 10)),
                 float(np.percentile(finite, 90)), won, finite.size, skipped))
    allg = np.array([v for _, (gs, _) in patchstats for v in gs], dtype=np.float64)
    allg = allg[np.isfinite(allg)]
    nmeas = sum(1 for _, (gs, _) in patchstats if gs)
    nfloor = sum(1 for _, (gs, _) in patchstats if not gs)
    print("\n  sites: %d measured, %d unregistered, %d below the detail floor, "
          "%d total" % (nmeas, len(unregistered), nfloor,
                        nmeas + len(unregistered) + nfloor))
    if len(unregistered) + nfloor:
        print("  An unregistered site is NOT a soft site. It is a site where the")
        print("  master and the source were not shown the same content, and no")
        print("  verdict below covers it.")
    if allg.size:
        med = float(np.median(allg))
        print("\n  ALL SITES  median %.3fx over %d measured patches" % (med, allg.size))
        if med > 1.05:
            print("  -> RECONSTRUCTION: the master carries detail no single frame has.")
        elif med > 0.95:
            print("  -> SELECTION: the master matches its best input and does not")
            print("     exceed it. Correct, but it is what every competitor does.")
        else:
            print("  -> DEFECT: the master is SOFTER than the best single frame.")

    th = CROP + LABEL_H
    canvas = np.zeros((3 * th, len(rows) * CROP, 3), dtype=np.uint8)
    clipreport = []
    for cx, (si, _, _, mc_img, sc_img, name, mf, sf, _, _) in enumerate(rows):
        # ONE window covering BOTH arms. Taking it from the master alone crushed
        # the source row at ~20% saturation, which makes the source look softer
        # for a display reason and flatters the master. A union window is still a
        # single linear map, so the contrast RATIO between the rows is preserved
        # exactly -- which a per-row stretch would destroy (section 91).
        both = np.concatenate([luma(mc_img).ravel(), luma(sc_img).ravel()])
        lo = float(np.percentile(both, 1))
        hi = float(np.percentile(both, 99))
        # The innocent explanation for a 2.8x patch ratio is that the master is
        # simply SHARPENED, not reconstructed. Unsharp-mask the best source until
        # its fine-detail energy matches the master's, then look at all three:
        # if matching the master's number takes visible ringing that the master
        # does not have, the master is not a sharpened frame.
        usm_img, amt = usm_match(sc_img, mf)
        for ry, (img, tag) in enumerate((
                (mc_img, "MASTER  detail %.1f" % mf),
                (sc_img, "%s  %.1f" % (name[:11], sf)),
                (usm_img, "SOURCE+USM x%.2f  (control)" % amt))):
            raw = (luma(img).astype(np.float64) - lo) / max(hi - lo, 1e-9)
            clipfrac = float(((raw < 0.0) | (raw > 1.0)).mean())
            t = np.clip((img.astype(np.float64) - lo) / max(hi - lo, 1e-9), 0, 1)
            y0, x0 = ry * th, cx * CROP
            canvas[y0:y0 + CROP, x0:x0 + CROP] = (t * 255).astype(np.uint8)
            draw_text(canvas, tag, y0 + CROP + 4, x0 + 4)
            clipreport.append((si, ("master", "source", "usm")[ry], clipfrac))

    out = os.path.join(OUT_ROOT, "ORCH-CONTACT", "sharp-1to1-%s.png" % subject)
    png_rgb(canvas, out)
    print("\nwrote %s  %dx%d" % (out, canvas.shape[1], canvas.shape[0]))
    print("ONE STATED WINDOW per column, taken from the master, applied to both")
    print("rows -- a per-tile stretch would make the pair incomparable (section 91).")
    # A shared window is necessary but not sufficient: if it saturates one row,
    # that row's texture is destroyed by the display and the pair is no longer a
    # fair comparison of sharpness. The master's ~2% is the 1-99 percentile by
    # construction; the source row's figure is the free variable, so print it.
    print("\nclipped fraction under that shared window (the master's ~2%% is the")
    print("1-99 percentile by construction; the SOURCE row is the free variable):")
    bad = 0
    for si, which, cf in clipreport:
        mark = ""
        if which != "master" and cf > SHARE_CLIP_MAX:
            mark = "  <== SATURATED, this column is not a fair pair"
            bad += 1
        print("  site %d  %-6s  %6.2f%%%s" % (si, which, cf * 100, mark))
    if bad:
        print("*** %d row(s) saturated above %.0f%%: display, not optics. ***"
              % (bad, SHARE_CLIP_MAX * 100))
    else:
        print("No row saturates above %.0f%%; every column above is a fair pair."
              % (SHARE_CLIP_MAX * 100))
    print("\nROW 3 is the control: the best source frame unsharp-masked until its")
    print("fine-detail energy EQUALS the master's. It has the master's number by")
    print("construction. If it rings and the master does not, the master's detail")
    print("is not sharpening. If they look alike, this result explains nothing.")


if __name__ == "__main__":
    if "commission" in sys.argv:
        sys.exit(commission())
    if "commission-reg" in sys.argv:
        sys.exit(commission_reg())
    main()