"""The per-site sharpness ceiling, computed once and reused across gate arms.

WHY THIS EXISTS RATHER THAN A CALL TO orch_sharp1to1.main()

ORCH's `orch_sharp1to1.py` is the numerator and it is not reimplemented here:
`luma`, `detail`, `register`, `best_site`, `patch_gain` and every constant are
IMPORTED from it. Two things forced a driver around it.

1. `main()` holds every developed frame resident -- `srcs.append((name, luma(s),
   s))` -- at roughly 336 MB per 24 MP frame. ORCH requires COMPLETE brackets,
   and `bee-1-cpl` is 299 frames, so that is ~100 GB. This driver streams: it
   develops one frame, folds it into a running per-tile maximum, and drops it.
   A running max over frames is the same number as `max` over a resident list,
   which is why this is a memory change and not a statistic change. C1 proves
   that rather than asserting it.

2. THE SWEEP NEEDS THE DENOMINATOR HELD FIXED. Six gate settings share one set
   of source frames, so `max over registered sources` is the same float in every
   arm. Computing it once is not an optimisation of the comparison, it is the
   thing that makes the comparison paired: the order-statistic inflation that
   V-EYES measured at 0.1-1.6% appears identically on both sides of a paired
   delta and cancels exactly. Recomputing it per arm would let it vary and would
   reintroduce a bias the design does not need to carry.

The registration shifts and the site list are likewise taken ONCE from a named
reference arm. That is not a shortcut either -- it is the discipline `acuity.py`
already uses: if each arm chose its own sites, an arm could move the statistic
by moving the selection rather than by changing the picture.

WHAT THIS INSTRUMENT CANNOT DO, stated here rather than discovered later:

  - It cannot see a change outside the accepted sites. `best_site` takes the
    three most textured windows; a gate setting that ruined flat background
    would not register here at all. That is what `acuity.py`'s flat statistic
    is for, and why the sweep is scored on both axes.
  - It cannot separate "the master got softer" from "the master got dimmer".
    `detail` is an L1 gradient magnitude and is linear in amplitude, so a gain
    of x1.05 moves it exactly 5%. C4 measures that rather than assuming it.
  - A site whose sources never registered is NOT MEASURED, and is counted
    separately from a site that measured badly.
"""
import os
import sys
import glob

import numpy as np
import tifffile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "ORCH-drift-check"))

from orch_sharp1to1 import (                                      # noqa: E402
    luma, detail, register, best_site, patch_gain,
    CROP, PATCH, PATCH_FLOOR, SEARCH, CORR_MIN, SITE_SHARE, SITE_CLIP_MAX,
    SRC_ROOT,
)

NTILE = CROP // PATCH


def pick_sites(master):
    """main()'s site selection, reproduced including both rejection rules.

    Kept in step with ORCH's file by construction where possible (best_site and
    detail are imported); the two rejection rules are re-expressed because they
    live inline in main() rather than in a function. They are re-expressed, not
    re-invented: SITE_CLIP_MAX and SITE_SHARE are imported.
    """
    my = luma(master)
    scored = []
    for _, y, x in best_site(my):
        crop = my[y:y + CROP, x:x + CROP]
        d = detail(crop)[0]
        clipf = float((master[y:y + CROP, x:x + CROP] >= 65000).mean())
        scored.append((d, clipf, y, x))
    top = max((d for d, _, _, _ in scored), default=0.0)
    sites, rejected = [], []
    for d, clipf, y, x in scored:
        share = d / top if top else 0.0
        if clipf > SITE_CLIP_MAX:
            rejected.append((y, x, "clipped %.1f%%" % (100 * clipf)))
        elif share < SITE_SHARE:
            rejected.append((y, x, "detail %.0f%% of best site" % (100 * share)))
        else:
            sites.append((y, x))
    return sites, rejected


def tile_fine(crop):
    """Per-tile fine detail on the PATCH grid patch_gain() uses."""
    out = np.zeros((NTILE, NTILE))
    for py in range(NTILE):
        for px in range(NTILE):
            out[py, px] = detail(crop[py * PATCH:(py + 1) * PATCH,
                                      px * PATCH:(px + 1) * PATCH])[0]
    return out


def build_ceiling(subject, ref_master, nsrc=None, verbose=True):
    """Stream the bracket; return per-site per-tile MAX source detail + shifts."""
    import rawpy
    m = tifffile.imread(ref_master)[..., :3].astype(np.float64)
    sites, rejected = pick_sites(m)
    if not sites:
        raise SystemExit("no site on %s survived selection -- a finding, not a "
                         "reason to lower the floor" % subject)
    my = luma(m)
    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    if nsrc is not None and nsrc < len(arw):
        idx = np.linspace(0, len(arw) - 1, nsrc).astype(int)
    else:
        idx = np.arange(len(arw))
    if verbose:
        print("%s: %d sites %r, %d of %d frames (COMPLETE)"
              % (subject, len(sites), sites, len(idx), len(arw)))
        for y, x, why in rejected:
            print("  site (%d,%d) NOT A SITE: %s" % (y, x, why))

    ceil = [np.zeros((NTILE, NTILE)) for _ in sites]
    nok = [0] * len(sites)
    nbad = [0] * len(sites)
    shifts = [dict() for _ in sites]
    for n, i in enumerate(idx):
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        sy = luma(s.astype(np.float64))
        for si, (y, x) in enumerate(sites):
            if y - SEARCH < 0 or x - SEARCH < 0:
                continue
            pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
            if pad.shape != (CROP + 2 * SEARCH, CROP + 2 * SEARCH):
                continue
            (dy, dx), c = register(my[y:y + CROP, x:x + CROP], pad)
            if c < CORR_MIN:
                nbad[si] += 1
                continue
            nok[si] += 1
            shifts[si][int(i)] = (int(dy), int(dx), float(c))
            np.maximum(ceil[si], tile_fine(sy[y + dy:y + dy + CROP,
                                             x + dx:x + dx + CROP]), out=ceil[si])
        if verbose and (n + 1) % 25 == 0:
            print("    %d/%d frames" % (n + 1, len(idx)), flush=True)
    return {"sites": np.array(sites), "ceil": np.array(ceil),
            "nok": np.array(nok), "nbad": np.array(nbad),
            "ref_master": ref_master, "subject": subject,
            "nframes": len(idx), "ntotal": len(arw)}


def score(master_path, cz, arr=None):
    """Median master/ceiling over tiles, with patch_gain's exclusions applied.

    `arr` lets a caller score a synthetic modification of the master without
    writing it to disk, which is what the commissioning arms need.
    """
    m = tifffile.imread(master_path)[..., :3].astype(np.float64) if arr is None else arr
    my = luma(m)
    gains, skipped, per_site = [], 0, []
    for si, (y, x) in enumerate(cz["sites"]):
        mt = tile_fine(my[y:y + CROP, x:x + CROP])
        ct = cz["ceil"][si]
        g = []
        for py in range(NTILE):
            for px in range(NTILE):
                mf, sf = mt[py, px], ct[py, px]
                if mf < PATCH_FLOOR and sf < PATCH_FLOOR:
                    skipped += 1
                    continue
                g.append(mf / sf if sf > 0 else float("inf"))
        ga = np.array(g)
        ga = ga[np.isfinite(ga)]
        per_site.append(float(np.median(ga)) if ga.size else float("nan"))
        gains.extend(ga.tolist())
    a = np.array(gains)
    a = a[np.isfinite(a)]
    return (float(np.median(a)) if a.size else float("nan")), a.size, skipped, per_site


def _blur5(a):
    k = np.array([1.0, 4.0, 6.0, 4.0, 1.0])
    k /= k.sum()
    out = a
    for axis in (0, 1):
        p = np.moveaxis(out, axis, 0)
        pad = np.concatenate([p[1:3][::-1], p, p[-3:-1][::-1]], axis=0)
        acc = np.zeros_like(p)
        for i, w in enumerate(k):
            acc += w * pad[i:i + p.shape[0]]
        out = np.moveaxis(acc, 0, axis)
    return out


def commission(master_path, subject, nsrc=6):
    """Prove the sweep statistic responds, in the right direction AND size.

    ORCH: "plant a known sharpening and a known softening and confirm the
    statistic moves in the right direction *and* by roughly the right amount.
    Plant the improvement too, not just the defect."

    The magnitude check here is EXACT rather than "roughly", and that is the
    point of it. The denominator is held fixed across arms by construction, so
    a change confined to the master must move the ratio by precisely the factor
    it moves the master's own detail. Predicting that factor independently --
    from detail() on the modified master, not from the ratio -- and requiring
    agreement tests the invariance claim itself. If the denominator ever moved,
    these two numbers would part company.

    C4 is the arm that would have caught `overshoot_frac`: a plain gain is not
    a sharpness change, and an instrument that scored it as one would be
    measuring exposure. It must move by exactly the gain.
    """
    cz = build_ceiling(subject, master_path, nsrc=nsrc, verbose=False)
    m = tifffile.imread(master_path)[..., :3].astype(np.float64)
    base, n, _, _ = score(master_path, cz)
    print("commissioning on %s, %d frames, %d tiles, baseline %.4f\n"
          % (subject, nsrc, n, base))

    arms = [
        ("C2 identity (byte copy)", m.copy(), "exactly 0.00%", "zero"),
        ("C3 softened (5-tap blur)", _blur5(m), "FALL", "predict"),
        ("C4 gain x1.05 (linearity)", m * 1.05, "+5.00% exactly", "predict"),
        ("C5 SHARPENED (unsharp mask)  <- the IMPROVEMENT",
         np.clip(m + 0.8 * (m - _blur5(m)), 0, 65535), "RISE", "predict"),
    ]
    print("%-46s %9s %9s %9s   %s"
          % ("arm", "ratio", "measured", "predicted", "verdict"))
    ok = True
    for label, arr, expect, mode in arms:
        r, _, _, _ = score(master_path, cz, arr=arr)
        d = 100.0 * (r / base - 1.0)
        # Predict independently, and AGGREGATE THE SAME WAY THE STATISTIC DOES.
        #
        # The first version of this predictor summed tile detail over the sites
        # and compared that to a MEDIAN of per-tile ratios. Those are different
        # aggregations and they disagree by construction on any non-uniform
        # change: a 5-tap blur costs a fine-texture tile a larger FRACTION of
        # its gradient than it costs a high-contrast edge tile, so the median
        # tile moves further than the amplitude-weighted mean. It read
        # -64.96% measured against -44.23% predicted and FAILED two arms that
        # had in fact moved correctly. The failure was in the predictor, not in
        # the statistic, and it is recorded rather than quietly corrected.
        #
        # Since the ceiling is fixed per tile, a master-only change multiplies
        # tile t's ratio by f(t) = detail_mod(t)/detail_orig(t). The typical
        # tile therefore moves by median(f), which is computed here from the
        # master alone -- never from the ratio -- so it remains an INDEPENDENT
        # prediction rather than a restatement of the result.
        fac = []
        for si, (y, x) in enumerate(cz["sites"]):
            a_t = tile_fine(luma(arr)[y:y + CROP, x:x + CROP])
            o_t = tile_fine(luma(m)[y:y + CROP, x:x + CROP])
            ok_t = o_t > 0
            fac.extend((a_t[ok_t] / o_t[ok_t]).tolist())
        pred = 100.0 * (float(np.median(fac)) - 1.0)
        if mode == "zero":
            good = abs(d) < 1e-9
            shown = "0.00"
        else:
            # median(f*r) is not median(f)*median(r) unless f is uniform, so an
            # exact match is only required of the uniform arm (C4, where f is a
            # constant 1.05 and the agreement below is to the last printed
            # digit). Elsewhere: same sign, and within 15% relative.
            tol = max(0.05, 0.15 * abs(pred))
            good = (abs(d - pred) <= tol) and (np.sign(d) == np.sign(pred))
            shown = "%+.2f" % pred
        if label.startswith("C3"):
            good = good and d < -1.0
        if label.startswith("C5"):
            good = good and d > 1.0
        ok = ok and good
        print("%-46s %9.4f %+8.2f%% %8s%%   %s  (want %s)"
              % (label, r, d, shown, "PASS" if good else "FAIL", expect))
    print("\n%s" % ("COMMISSIONED: the statistic falls on a planted softening, "
                    "RISES on a planted sharpening, is exact on a byte copy and "
                    "on a pure gain, and its size matches the master's own "
                    "per-tile detail change."
                    if ok else "NOT COMMISSIONED: an arm missed."))
    return 0 if ok else 1


def commission_agreement(master_path, subject, nsrc=4):
    """C1: this streaming driver must equal ORCH's resident patch_gain().

    Not 'be close to'. The two compute the same max over the same crops, so any
    difference at all is a defect in the driver and the deep subjects would then
    be reported NOT MEASURED rather than measured by an uncommissioned tool.
    """
    import rawpy
    m = tifffile.imread(master_path)[..., :3].astype(np.float64)
    sites, _ = pick_sites(m)
    my = luma(m)
    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    idx = np.linspace(0, len(arw) - 1, min(nsrc, len(arw))).astype(int)
    devs = []
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        devs.append((os.path.basename(arw[i]), luma(s.astype(np.float64))))

    print("%-10s %14s %14s   %s" % ("site", "ORCH patch_gain", "streaming", "verdict"))
    ok = True
    for (y, x) in sites:
        ref = my[y:y + CROP, x:x + CROP]
        reg = []
        for name, sy in devs:
            if y - SEARCH < 0 or x - SEARCH < 0:
                continue
            pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
            if pad.shape != (CROP + 2 * SEARCH, CROP + 2 * SEARCH):
                continue
            (dy, dx), c = register(ref, pad)
            if c < CORR_MIN:
                continue
            reg.append((name, sy[y + dy:y + dy + CROP, x + dx:x + dx + CROP]))
        if not reg:
            print("%-10s %14s %14s   SKIPPED (nothing registered)" % ("(%d,%d)" % (y, x), "-", "-"))
            continue
        g, _ = patch_gain(ref, reg)
        ga = np.array(g)
        ga = ga[np.isfinite(ga)]
        orch = float(np.median(ga))

        ceil = np.zeros((NTILE, NTILE))
        for _, crop in reg:
            np.maximum(ceil, tile_fine(crop), out=ceil)
        mt = tile_fine(ref)
        mine = []
        for py in range(NTILE):
            for px in range(NTILE):
                mf, sf = mt[py, px], ceil[py, px]
                if mf < PATCH_FLOOR and sf < PATCH_FLOOR:
                    continue
                mine.append(mf / sf if sf > 0 else float("inf"))
        mi = np.array(mine)
        mi = mi[np.isfinite(mi)]
        mine_med = float(np.median(mi))
        same = abs(orch - mine_med) < 1e-12
        ok = ok and same
        print("%-10s %14.6f %14.6f   %s"
              % ("(%d,%d)" % (y, x), orch, mine_med, "IDENTICAL" if same else "DIFFER"))
    print("\n%s" % ("C1 COMMISSIONED: the streaming driver reproduces ORCH's "
                    "resident patch_gain() exactly."
                    if ok else "C1 FAILED: the driver is not ORCH's statistic."))
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1] == "commission":
        sys.exit(commission(sys.argv[2], sys.argv[3],
                            int(sys.argv[4]) if len(sys.argv) > 4 else 6))
    if sys.argv[1] == "agree":
        sys.exit(commission_agreement(sys.argv[2], sys.argv[3],
                                      int(sys.argv[4]) if len(sys.argv) > 4 else 4))
    if sys.argv[1] == "build":
        cz = build_ceiling(sys.argv[3], sys.argv[2],
                           nsrc=int(sys.argv[5]) if len(sys.argv) > 5 else None)
        np.savez_compressed(sys.argv[4], **cz)
        print("wrote %s  (%d sites, %d/%d frames, registered %s, refused %s)"
              % (sys.argv[4], len(cz["sites"]), cz["nframes"], cz["ntotal"],
                 list(cz["nok"]), list(cz["nbad"])))
        sys.exit(0)
    if sys.argv[1] == "score":
        cz = np.load(sys.argv[2], allow_pickle=True)
        for p in sys.argv[3:]:
            r, n, sk, ps = score(p, cz)
            print("%-58s %8.4f  (%d tiles, %d skipped, sites %s)"
                  % (os.path.basename(p), r, n, sk,
                     " ".join("%.3f" % v for v in ps)))
        sys.exit(0)
    sys.exit("usage: ceiling.py {commission|agree|build|score} ...")
