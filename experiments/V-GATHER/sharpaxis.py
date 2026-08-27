r"""Sharpness axis: the master against the PER-SITE FOCUS CEILING.

WHY NOT AGAINST A COMPARATOR. Comparing two renders answers "which is sharper",
which is a question about two programs. The owner's question is whether the
print is as sharp as it could be, and the only honest ceiling is the one the
data itself contains: at each location, the best any input frame achieves there.
A focus stack that returns less than its own best input at a site has lost
detail that was present in the material.

THE DEFICIT REPORTED HERE IS A LOWER BOUND, AND THE REASON IS ARITHMETIC. The
ceiling is a MAX over a SAMPLE of frames, and a max over fewer samples can only
sit lower, so a sampled ceiling understates the true ceiling and the deficit
against it understates the true deficit. This is the same correction V-NEVERWORSE
applied in the opposite direction to a sampled `min`. It is stated rather than
corrected because correcting it would require rendering every frame of every
bracket.

GAUGE. Both sides are rendered `--linear-srgb --demosaic` by the sealed shipping
binary, and the lattice is read from the file rather than inferred from the
flags -- `--linear-srgb` alone yields a binned half-resolution image on which
every spatial-frequency quantity silently changes meaning. The statistic is a
BANDPASS contrast, normalised by local mean, so it is invariant to a linear
gain; raw DN is never compared across the two renders.

NOISE. The band is taken between sigma 1.0 and 2.5 rather than at the pixel
scale. A max-over-frames ceiling is exactly the statistic that a noisier frame
wins spuriously, because photon noise is broadband and lands hardest at the
pixel scale. Excluding that octave costs a little resolution and removes the
mechanism by which noise could manufacture a deficit.

REGISTRATION. Source frames are NOT emitted in the reference grid -- measured
drift is about 0.9 px per frame -- so each site is registered by an integer-only
FFT shift before measurement. Integer only: sub-pixel resampling would blur the
very band being measured.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402

OUT = os.path.join(HERE, "sharp.json")
WIN = 512
NSITE = 40
NFRAME = 12
# Recovery tolerance, in pixels, for the localisability test. EXACT recovery was
# tried first and admitted only 3 of 16 sites on 109MSDCF; the rejected ones were
# missing by one or two pixels, not failing to localise. The tolerance is safe
# because the measurand is a bandpass contrast computed over a 512 px window
# rather than a per-pixel difference, so displacing the window by two pixels
# changes which 0.4% of its area is included and nothing else. rimcheck of that
# claim is arm REGTOL in sharpcommission.py, which measures the statistic's
# actual response to a 2 px displacement instead of assuming it is small.
REG_TOL = 2
REG_HALF = 512
# DERIVED, NOT TYPED, and derived from this axis's own floor rather than from
# any published figure. sharpcommission.py arm REGTOL measures what a REG_TOL
# misregistration does to the statistic on real content: 0.771%. That is the
# smallest deficit the axis can distinguish from registration jitter, so the
# FAIL threshold is set at four times it. Arm FIRE then confirms the conjunction
# is reachable (a sigma 2.4 blur reads 41.2%) and arm NOTALWAYS that it is not
# automatic (the unmodified base reads 0.000%). Arm RESOLUTION records the blind
# spot this leaves: softness below about blur sigma 0.6 is not resolvable here,
# and a PASS on this axis is silence about it.
SHARP_MAX = 0.032
MAX_RENDER = 56
CONVERGE = 0.02
# The ceiling must be shown to have CONVERGED, not merely sampled. A max over a
# sparse sweep is not a ceiling: on bee-1-cpl, 299 frames sampled 12 times gave a
# "deficit" of -317.8%, meaning the master beat its own ceiling by 4.2x. Adding a
# bracketing test moved it to -100.9%, which is still not a ceiling. The axis
# therefore refines around each site's peak until the best value stops improving
# by more than CONVERGE, and REFUSES the subject if it has not settled inside the
# render budget. A negative deficit is not reported as a pass; it is the
# instrument saying it never found the ceiling.
SIG_LO, SIG_HI = 1.0, 2.5
COVER_MIN = 0.60
MAX_DRIFT = 600
PLANT = (23, -17)

# NO CONFIDENCE THRESHOLD. The first draft gated sites on est_shift's peak
# prominence at MIN_CONF = 6.0, a typed number, and refused 16 of 16 sites on a
# subject whose registration was demonstrably working -- measured shifts of
# (0,0) and (-1,0) on a 22-frame bracket. confderive.py then measured whether
# the statistic could gate at all, by comparing the population it must ACCEPT
# (a site against a copy of itself displaced by a known shift) against the one
# it must REJECT (the same site against independent noise):
#
#     RECOVERABLE    conf: min 1.76  median 3.20  max 5.94
#     UNLOCALISABLE  conf: min 2.69  median 3.21  max 4.02
#
# The two medians are 3.20 and 3.21. The statistic does not separate them, so no
# threshold on it is a gate, and tuning one would have been choosing a number to
# get a population rather than to exclude a failure. It is replaced by a direct
# test of the property actually required: can this site's own content recover a
# known displacement? A site that cannot is not registerable and is excluded.


def band(lum):
    """Bandpass contrast, normalised by local mean -> invariant to linear gain."""
    a = lum.astype(np.float32)
    b = ndimage.gaussian_filter(a, SIG_LO) - ndimage.gaussian_filter(a, SIG_HI)
    m = float(np.mean(a))
    if m <= 1e-6:
        return None
    return float(np.std(b) / m)


def lum(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def localisable(m_lum, y, x, half=768):
    """Can a known displacement be recovered from this site's own content?

    Direct test of the property the axis needs, replacing a confidence threshold
    that was measured not to separate. Cheap: one extra correlation per site per
    subject, not per frame.
    """
    cy, cx = y + WIN // 2, x + WIN // 2
    my, mx = abs(PLANT[0]), abs(PLANT[1])
    y0, x0, y1, x1 = cy - half, cx - half, cy + half, cx + half
    if (y0 - my < 0 or x0 - mx < 0
            or y1 + my > m_lum.shape[0] or x1 + mx > m_lum.shape[1]):
        return False
    a = m_lum[y0:y1, x0:x1]
    b = m_lum[y0 - PLANT[0]:y1 - PLANT[0], x0 - PLANT[1]:x1 - PLANT[1]]
    dy, dx, _ = cm.est_shift(a, b)
    return (abs(-dy - PLANT[0]) <= REG_TOL and abs(-dx - PLANT[1]) <= REG_TOL)


def pick_sites(m_lum, n=NSITE, seed=3):
    """Textured, well-separated sites. A flat site has no sharpness to compare
    and no localisable registration peak; it must be excluded before measuring,
    not silently assigned a shift of (0, 0)."""
    h, w = m_lum.shape
    step = WIN
    cand = []
    for y in range(step, h - WIN - step, step):
        for x in range(step, w - WIN - step, step):
            t = m_lum[y:y + WIN:4, x:x + WIN:4]
            cand.append((float(np.std(t)), y, x))
    cand.sort(reverse=True)
    out = []
    for _, y, x in cand:
        if all(abs(y - a) >= 2 * WIN or abs(x - b) >= 2 * WIN for a, b in out):
            out.append((y, x))
        if len(out) >= n:
            break
    return out


def _verify_tags(path, expect):
    """Same refusals as cm.read_rgb -- tone stage and lattice -- but without
    pulling 198 MB through the decoder for a 512 px window."""
    with tifffile.TiffFile(path) as t:
        pg = t.pages[0]
        w, h = pg.tags["ImageWidth"].value, pg.tags["ImageLength"].value
        desc = str(pg.tags["ImageDescription"].value) if "ImageDescription" in pg.tags else ""
        comp = pg.compression
    if "Tone rendering" in desc:
        raise SystemExit("REFUSED: %s carries a fitted tone stage" % path)
    if (w, h) != expect:
        raise SystemExit("REFUSED: lattice %dx%d != master %dx%d"
                         % (w, h, expect[0], expect[1]))
    return int(getattr(comp, "value", comp))


def _render_and_measure(s, d, k, ml, lat, sites, store):
    """Render one frame and read only the windows the sites need.

    The full frame is 198 MB and the sites occupy a few percent of it. Reading
    the whole array once per frame per subject dominated the cost and bounded how
    densely the focus ceiling could be sampled -- which is what made the ceiling
    unconverged in the first place. These TIFFs are uncompressed, so a memmap
    slice reads only the requested rows.
    """
    sp = os.path.join(d, "sharp-src.tiff")
    got, err, _ = cm.render(s, sp, only_frame=k)
    if not got:
        return False
    try:
        _verify_tags(sp, lat)
    except SystemExit:
        os.remove(sp)
        return False
    mm = tifffile.memmap(sp, mode="r")
    H, W = mm.shape[0], mm.shape[1]
    for i, (y, x) in enumerate(sites):
        cy, cx = y + WIN // 2, x + WIN // 2
        y0, x0 = max(0, cy - REG_HALF), max(0, cx - REG_HALF)
        y1, x1 = min(H, cy + REG_HALF), min(W, cx + REG_HALF)
        sw = lum(np.asarray(mm[y0:y1, x0:x1, :3], dtype=np.float32))
        mw = ml[y0:y1, x0:x1]
        if sw.shape != mw.shape:
            continue
        dy, dx, _ = cm.est_shift(mw, sw)
        dy, dx = -dy, -dx
        if abs(dy) > MAX_DRIFT or abs(dx) > MAX_DRIFT:
            continue
        yy, xx = y + dy, x + dx
        if yy < 0 or xx < 0 or yy + WIN > H or xx + WIN > W:
            continue
        v = band(lum(np.asarray(mm[yy:yy + WIN, xx:xx + WIN, :3],
                                dtype=np.float32)))
        if v is not None:
            store[i][k] = v
    del mm
    os.remove(sp)
    return True


def measure_subject(s, nframe=NFRAME):
    """Coarse sweep, then a REFINEMENT pass around each site's own focus peak.

    WHY THE REFINEMENT IS NOT OPTIONAL. The first version took a fixed
    linspace of 12 frames and called the max over them the focus ceiling. On
    bee-1-cpl -- 299 frames, so a spacing of 27 -- that returned a deficit of
    -317.8%, i.e. the master reading 4.2x sharper than its own "ceiling". The
    ceiling was not a ceiling: no sampled frame was in focus at those sites, so
    the max was taken over a set of defocused frames. A denominator that can be
    beaten by a factor of four is not measuring the quantity it names, and the
    negative sign is what exposed it -- a deficit statistic bounded below by zero
    would have reported a comfortable 0% and been believed.

    A site is only admitted if its sharpness-versus-frame curve has an INTERIOR
    LOCAL MAXIMUM over the frames actually measured. That is the observable
    signature of the focus peak having been bracketed. A site whose maximum sits
    at either end of the sweep has its true focus outside the sample and is
    refused rather than scored against whatever the endpoint happened to be.
    """
    d = os.path.join(cm.WORK, s)
    os.makedirs(d, exist_ok=True)
    mp = os.path.join(d, "sharp-master.tiff")
    got, err, _ = cm.render(s, mp)
    if not got:
        return {"refused": "master render failed: %s" % err.strip()[:160]}
    mrgb, lat = cm.read_rgb(mp)
    ml = lum(mrgb)
    del mrgb
    os.remove(mp)

    allsites = pick_sites(ml)
    sites = [(y, x) for (y, x) in allsites if localisable(ml, y, x)]
    n_unloc = len(allsites) - len(sites)
    if not sites:
        return {"refused": "no site of %d could recover a planted shift"
                           % len(allsites), "n_sites_offered": len(allsites)}
    mband = [band(ml[y:y + WIN, x:x + WIN]) for y, x in sites]

    n_raw = len([f for f in os.listdir(os.path.join(cm.RAW, s))
                 if f.lower().endswith(".arw")])
    if n_raw < 5:
        return {"refused": "only %d raw frames; a focus peak cannot be "
                           "bracketed" % n_raw}
    coarse = sorted(set(int(round(v)) for v in
                        np.linspace(0, n_raw - 1, min(nframe, n_raw))))
    store = [dict() for _ in sites]
    used = [k for k in coarse if _render_and_measure(s, d, k, ml, lat, sites, store)]
    if not used:
        return {"refused": "no source frame rendered"}

    refined, rounds, converged = 0, 0, False
    while len(used) < MAX_RENDER:
        prev = [max(st.values()) if st else 0.0 for st in store]
        want = set()
        for st in store:
            if len(st) < 3:
                continue
            ks = sorted(st)
            j = ks.index(max(ks, key=lambda k: st[k]))
            for a, b in ((j - 1, j), (j, j + 1)):
                if 0 <= a and b < len(ks):
                    mid = (ks[a] + ks[b]) // 2
                    if mid not in st and 0 <= mid < n_raw:
                        want.add(mid)
        want = sorted(want)[:MAX_RENDER - len(used)]
        if not want:
            converged = True
            break
        for k in want:
            if _render_and_measure(s, d, k, ml, lat, sites, store):
                refined += 1
                used.append(k)
        rounds += 1
        gain = max((max(st.values()) - p) / p if st and p > 0 else 0.0
                   for st, p in zip(store, prev))
        if gain < CONVERGE:
            converged = True
            break

    rec = {"n_raw": n_raw, "n_frames_used": len(used), "n_coarse": len(coarse),
           "n_refined": refined, "rounds": rounds, "converged": converged, "n_sites": len(sites),
           "n_sites_offered": len(allsites), "n_unlocalisable": n_unloc,
           "lattice": list(lat), "sites": [], "win": WIN}
    defs = []
    n_unbracketed = 0
    for i, (y, x) in enumerate(sites):
        st = store[i]
        cov = len(st) / float(len(used)) if used else 0.0
        e = {"y": y, "x": x, "master": mband[i], "cover": cov, "n": len(st)}
        ks = sorted(st)
        bracketed = False
        if len(ks) >= 3:
            kbest = max(ks, key=lambda k: st[k])
            j = ks.index(kbest)
            bracketed = 0 < j < len(ks) - 1
            e["peak_frame"] = kbest
            e["peak_index"] = j
            e["n_measured"] = len(ks)
        e["bracketed"] = bracketed
        if not bracketed:
            n_unbracketed += 1
        if bracketed and cov >= COVER_MIN and mband[i] is not None:
            e["ceiling"] = max(st.values())
            e["deficit"] = 1.0 - mband[i] / e["ceiling"]
            defs.append(e["deficit"])
        rec["sites"].append(e)
    rec["n_qualified"] = len(defs)
    rec["n_unbracketed"] = n_unbracketed
    if len(defs) < 4:
        rec["refused"] = ("%d of %d offered sites could not recover a planted "
                          "shift; %d of the remaining %d never bracketed a focus "
                          "peak; only %d qualified, fewer than 4"
                          % (n_unloc, len(allsites), n_unbracketed, len(sites),
                             len(defs)))
        return rec
    if not converged:
        rec["refused"] = ("focus ceiling did not converge within %d renders "
                          "(%d rounds); the max over sampled frames is a lower "
                          "bound on the ceiling, so the deficit against it is "
                          "not a measurement" % (MAX_RENDER, rounds))
        return rec
    if float(np.median(defs)) < 0:
        rec["deficit_median_raw"] = float(np.median(defs))
        rec["refused"] = ("median deficit %.1f%% is negative: the master exceeds "
                          "the best frame found at most sites, so the ceiling "
                          "was never reached and softness cannot be assessed"
                          % (100 * float(np.median(defs))))
        return rec
    rec["deficit_median"] = float(np.median(defs))
    rec["deficit_p90"] = float(np.percentile(defs, 90))
    rec["deficit_worst"] = float(np.max(defs))
    return rec


def main():
    cm.check_binary()
    os.makedirs(cm.WORK, exist_ok=True)
    doc = {}
    if os.path.exists(OUT):
        doc = json.load(io.open(OUT, encoding="utf-8"))
    subs = cm.subjects()
    only = sys.argv[1:] or subs
    for i, s in enumerate(subs, 1):
        if s in doc or s not in only:
            continue
        rec = measure_subject(s)
        doc[s] = rec
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        if "refused" in rec:
            print("[%2d/%d] %-38s REFUSED %s" % (i, len(subs), s, rec["refused"][:70]))
        else:
            print("[%2d/%d] %-38s fr %2d(+%2d)  sites %2d qual /%2d loc /%2d off"
                  "  unbr %2d  deficit med %+.1f%% p90 %+.1f%%"
                  % (i, len(subs), s, rec["n_coarse"], rec["n_refined"],
                     rec["n_qualified"], rec["n_sites"], rec["n_sites_offered"],
                     rec["n_unbracketed"], 100 * rec["deficit_median"],
                     100 * rec["deficit_p90"]))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
