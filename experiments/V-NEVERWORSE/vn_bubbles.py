"""Convict or acquit `coffee-bubbles` -- the one subject where a merge
regression is cleanly provable.

WHY THIS SUBJECT. Of the four subjects whose band excess exceeds the bounded
detail gain (RESULT.md 6.5), three are deep stacks measured through a 21-frame
subsample, so their `min` is a minimum over 12-18 draws standing in for one
over 105-299 -- and a minimum over a small sample is biased HIGH, which
manufactures excess. `coffee-bubbles` is 19 frames deep, all 19 sampled, all 19
admitted. There is no sampling to object to.

THE THREE HYPOTHESES, AND WHY THEY ARE SEPARABLE RATHER THAN WEIGHABLE.

`blotch` is std(band)/mean where band is a 50-400 px bandpass. That scale is
the key to the whole question:

  (a) GENUINE REGRESSION. The merge stitched a patchwork whose seams live at
      exactly this scale. Then the master's band structure is present in NO
      single frame, and the excess is spatially localised at the seams.
  (b) CHARGED FOR RESOLVED DETAIL. The explanation that covered 20 of 24
      subjects. But detail is a HIGH-frequency claim and this is a 50-400 px
      statistic, so mechanistically this explanation should barely reach it.
      If (b) is true the excess should be diffuse and correlate with sharpness.
  (c) STATISTIC ARTIFACT. The master's band matches the frames' band closely
      and the ratio is riding on something other than structure.

The discriminator is that a 50-400 px band is nearly INVARIANT to defocus: a
few-pixel blur kernel does not move structure two orders of magnitude coarser.
So on a static subject every frame should carry near-identical band structure,
and disagreement between frames at this scale means THE SUBJECT MOVED. Bubble
films drift. That makes the motion hypothesis directly measurable rather than
speculative, and it separates (a) into two very different products: a merge
that fabricates structure, versus a merge that faithfully selects real content
that happens to have moved -- an outlier-rejection failure.

MEASUREMENTS, all on the master's own blotch window, all in master space, all
on `--linear-srgb --demosaic` (RESULT.md 1):

  1. per-frame blotch, reproducing the recorded run exactly;
  2. INTER-FRAME BAND DISAGREEMENT, the motion test: per-pixel spread of the
     normalised band across the 19 registered frames;
  3. TILE EXCESS: where in the window the master beats the best frame;
  4. ATTRIBUTION: at the worst tile, is the master's band reproduced by any
     single frame? Fabricated structure correlates with none of them.

  python vn_bubbles.py --commission     # planted defects, both directions
  python vn_bubbles.py                  # the real measurement
  python vn_bubbles.py --crops          # 1:1 crops at the worst-excess site
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "ORCH-drift-check"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "V-REVIEW"))

import vn_lib as L                                             # noqa: E402
from orch_blotch import boxblur, lum_of, LO_R, HI_R, WIN       # noqa: E402

SUBJ = "coffee-bubbles"
OUT = os.path.join(L.OUT, "bubbles")
TILE = 300          # >= the top of the band, so a tile can hold one blob
STRIDE = 150


def nband(lum):
    """The normalised band: exactly the field whose std IS `blotch`.

    blotch_ratio returns std(band)/mean, so std(band/mean) is the same number
    and the per-pixel field behind it. Dividing by the mean is what makes the
    two arms comparable across the pipeline's per-image gain (RESULT.md 1).
    """
    band = boxblur(lum, LO_R // 2) - boxblur(lum, HI_R // 2)
    return band / max(float(np.mean(lum)), 1e-9)


def tiles():
    for y in range(0, WIN - TILE + 1, STRIDE):
        for x in range(0, WIN - TILE + 1, STRIDE):
            yield y, x


def tile_std(f):
    return np.array([float(np.std(f[y:y + TILE, x:x + TILE]))
                     for y, x in tiles()])


def corr(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else 0.0


def loo_min(a):
    """a[k, t] -> out[k, t] = min over j != k of a[j, t].

    The master is compared against the min of ALL n frames; a frame can only
    be compared against the other n-1. Comparing a min-over-19 to a
    min-over-18 charges the master for one extra draw. This is what makes the
    null CANDIDATE-COUNT MATCHED instead of merely similar.
    """
    n, m = a.shape
    idx = np.argsort(a, axis=0)
    cols = np.arange(m)
    lo, lo2 = a[idx[0], cols], a[idx[1], cols]
    out = np.repeat(lo[None, :], n, axis=0)
    out[idx[0], cols] = lo2
    return out


def overlap_corr(a, b, dy, dx):
    """corr(a, b) with b translated by (dy, dx), on the overlap only."""
    h, w = a.shape
    y0, y1 = max(0, dy), min(h, h + dy)
    x0, x1 = max(0, dx), min(w, w + dx)
    if y1 - y0 < 64 or x1 - x0 < 64:
        return 0.0
    return corr(a[y0:y1, x0:x1], b[y0 - dy:y1 - dy, x0 - dx:x1 - dx])


def best_shift(a, b, maxs=140):
    """The rigid shift of `b` that best matches `a`, and the correlation there.

    Separates the two explanations for frames disagreeing at mid scale:
    a residual MISREGISTRATION is a rigid shift and correlation recovers when
    it is undone; content that genuinely moved independently does not recover.
    The peak is located by FFT but the reported correlation is evaluated
    DIRECTLY on the overlap, so a wrong peak cannot inflate it. `maxs` is
    returned alongside so a search pinned at its own cap cannot be read as a
    measurement -- commissioning saw 40.0 reported for a planted 200px roll.
    """
    A, B = a - a.mean(), b - b.mean()
    c = np.fft.irfft2(np.fft.rfft2(A) * np.conj(np.fft.rfft2(B)), s=A.shape)
    h, w = A.shape
    ys = np.r_[np.arange(0, maxs + 1), np.arange(h - maxs, h)]
    xs = np.r_[np.arange(0, maxs + 1), np.arange(w - maxs, w)]
    sub = c[np.ix_(ys, xs)]
    iy, ix = np.unravel_index(int(np.argmax(sub)), sub.shape)
    dy = int(ys[iy] - h) if ys[iy] > maxs else int(ys[iy])
    dx = int(xs[ix] - w) if xs[ix] > maxs else int(xs[ix])
    cap = (abs(dy) >= maxs) or (abs(dx) >= maxs)
    return dy, dx, overlap_corr(a, b, dy, dx), cap


def ghost_peak(t, excl=18, maxr=140):
    """Strongest off-centre self-similarity peak ABOVE the radial baseline.

    A merge that stitches a feature in from two frames in which it sat at
    different places leaves that feature TWICE, and a duplicate at offset d
    puts a secondary peak at d in the autocorrelation.

    The obvious form of this -- max autocorrelation outside a central
    exclusion -- does not work, and commissioning is what established that.
    A 50-400 px band is smooth by construction, so its own autocorrelation is
    still 0.91 at lag 12 and the max is always pinned near the exclusion
    radius: clean master 0.9521, master with a duplicate planted at +55 px
    0.9468. The planted defect read LOWER than the placebo. The duplication
    bump sits at lag 55 where the radial median is 0.37 and never becomes the
    maximum. Subtracting the median at the SAME radius removes the smooth
    structure the statistic was accidentally measuring and leaves the bump.
    """
    A = t - t.mean()
    h, w = A.shape
    A = A * (np.hanning(h)[:, None] * np.hanning(w)[None, :])
    P = np.zeros((2 * h, 2 * w), np.float64)
    P[:h, :w] = A
    c = np.fft.irfft2(np.abs(np.fft.rfft2(P)) ** 2, s=P.shape)
    c = np.fft.fftshift(c / max(float(c[0, 0]), 1e-12))
    yy, xx = np.mgrid[:2 * h, :2 * w]
    r = np.hypot(yy - h, xx - w)
    ri = np.rint(r).astype(int)
    m = (r > excl) & (r <= maxr)
    resid = np.full(c.shape, -1.0)
    for rr in range(int(excl), int(maxr) + 1):
        sel = ri == rr
        if sel.any():
            resid[sel] = c[sel] - np.median(c[sel])
    return float(resid[m].max()) if m.any() else 0.0


def analyse(mlum, flums, labels):
    """Everything the verdict rests on, from the master and registered frames."""
    mb = nband(mlum)
    fb = [nband(f) for f in flums]

    per = [float(np.std(x)) for x in fb]
    mstd = float(np.std(mb))
    best = int(np.argmin(per))

    # 2. motion: per-pixel spread of the band ACROSS frames
    stack = np.stack(fb, 0)
    inter = stack.std(0)
    # how big is that against the structure itself?
    motion = float(np.median(inter)) / max(float(np.median(np.abs(mb))), 1e-12)

    # 3. tile excess vs the best frame per tile (the strongest denominator)
    mt = tile_std(mb)
    ft = np.stack([tile_std(x) for x in fb], 0)
    tmin = ft.min(0)
    exc = mt / np.maximum(tmin, 1e-12)
    w = int(np.argmax(exc))
    ty, tx = list(tiles())[w]

    # 4. attribution at the worst tile
    m_t = mb[ty:ty + TILE, tx:tx + TILE]
    ft_t = [x[ty:ty + TILE, tx:tx + TILE] for x in fb]
    cs = [corr(m_t, x) for x in ft_t]
    kbest = int(np.argmax(cs))
    # How well do FRAMES agree with each other in that tile? The reference
    # scale for "well correlated" -- without it a bare 0.41 means nothing.
    # attr_best_corr is a MAX over n candidates, so the matched null is each
    # frame's max over the others, NOT the median pair correlation. Comparing
    # a max against a median is the same shape error as comparing a
    # min-over-19 against a min-over-18.
    n = len(fb)
    cm = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            cm[i, j] = cm[j, i] = corr(ft_t[i], ft_t[j])
    pair = cm[np.triu_indices(n, 1)]
    bo = np.array([np.max(np.delete(cm[i], i)) for i in range(n)])

    # 5. leave-one-out nulls, candidate-count matched. THE decisive control:
    # is the master unusual, or is "beats the min of the others" simply what
    # any object scores on a subject whose frames disagree at this scale?
    pw = np.array(per)[:, None]
    lw = loo_min(pw)
    f_loo = (pw / np.maximum(lw, 1e-12))[:, 0]
    m_loo = (mstd / np.maximum(lw[:, 0], 1e-12))
    lt = loo_min(ft)
    f_texc = np.median(ft / np.maximum(lt, 1e-12), axis=1)
    m_texc = np.median(mt[None, :] / np.maximum(lt, 1e-12), axis=1)
    f_wexc = ft[:, w] / np.maximum(lt[:, w], 1e-12)
    m_wexc = mt[w] / np.maximum(lt[:, w], 1e-12)

    # 6. is the disagreement a rigid shift (misregistration) or not (motion)?
    sh = [best_shift(m_t, x) for x in ft_t]
    raw = np.array([corr(m_t, x) for x in ft_t])
    rec = np.array([s[2] for s in sh])
    mag = np.array([float(np.hypot(s[0], s[1])) for s in sh])
    # ... and the same question asked WITHOUT the master in it. If consecutive
    # frames need a large shift to agree, the subject moved during capture,
    # and that is a fact about the shoot rather than about the merge.
    fp = [best_shift(ft_t[i], ft_t[i + 1]) for i in range(n - 1)]
    fmag = np.array([float(np.hypot(s[0], s[1])) for s in fp])
    fraw = np.array([corr(ft_t[i], ft_t[i + 1]) for i in range(n - 1)])
    frec = np.array([s[2] for s in fp])
    # 7. ghosting: does the master carry a feature twice over?
    g_m = ghost_peak(m_t)
    g_f = np.array([ghost_peak(x) for x in ft_t])
    return dict(
        master_blotch=mstd, per_frame=per, best_frame=best,
        best_blotch=per[best], ratio=mstd / max(per[best], 1e-12),
        motion=motion, inter_med=float(np.median(inter)),
        mb_absmed=float(np.median(np.abs(mb))),
        tile_exc_max=float(exc[w]), tile_exc_med=float(np.median(exc)),
        worst_tile=[ty, tx], labels=list(labels),
        attr_best_frame=int(kbest), attr_best_corr=float(cs[kbest]),
        attr_corrs=[float(c) for c in cs],
        pair_corr_med=float(np.median(pair)),
        pair_corr_min=float(np.min(pair)),
        pair_corr_max=float(np.max(pair)),
        bestother_med=float(np.median(bo)), bestother_max=float(np.max(bo)),
        f_loo_med=float(np.median(f_loo)), f_loo_max=float(np.max(f_loo)),
        m_loo_med=float(np.median(m_loo)),
        f_texc_med=float(np.median(f_texc)), f_texc_max=float(np.max(f_texc)),
        m_texc_med=float(np.median(m_texc)),
        f_wexc_med=float(np.median(f_wexc)), f_wexc_max=float(np.max(f_wexc)),
        m_wexc_med=float(np.median(m_wexc)),
        texc_rank=int(np.sum(f_texc >= np.median(m_texc))),
        shift_absmax=float(np.max(mag)), shift_absmed=float(np.median(mag)),
        shift_capped=bool(any(s[3] for s in sh)),
        shift_dy=[int(s[0]) for s in sh], shift_dx=[int(s[1]) for s in sh],
        corr_raw_med=float(np.median(raw)), corr_rec_med=float(np.median(rec)),
        corr_gain=float(np.median(rec) - np.median(raw)),
        fp_shift_med=float(np.median(fmag)), fp_shift_max=float(np.max(fmag)),
        fp_corr_raw=float(np.median(fraw)), fp_corr_rec=float(np.median(frec)),
        ghost_master=float(g_m), ghost_frame_med=float(np.median(g_f)),
        ghost_frame_max=float(np.max(g_f)),
        ghost_z=float((g_m - np.median(g_f))
                      / max(1.4826 * np.median(np.abs(g_f - np.median(g_f))),
                            1e-6)),
    )


def synth(rng, n=6, size=WIN):
    """A static synthetic subject: identical band structure in every frame."""
    base = 8000.0
    coarse = rng.normal(0, 1, (size // 100 + 2, size // 100 + 2)).astype(np.float32)
    yy = np.linspace(0, coarse.shape[0] - 1.001, size)
    xx = np.linspace(0, coarse.shape[1] - 1.001, size)
    gi, gj = yy.astype(int), xx.astype(int)
    fy, fx = (yy - gi)[:, None], (xx - gj)[None, :]
    blob = (coarse[np.ix_(gi, gj)] * (1 - fy) * (1 - fx)
            + coarse[np.ix_(gi + 1, gj)] * fy * (1 - fx)
            + coarse[np.ix_(gi, gj + 1)] * (1 - fy) * fx
            + coarse[np.ix_(gi + 1, gj + 1)] * fy * fx).astype(np.float32)
    blob = blob / max(float(np.std(blob)), 1e-6) * 60.0
    frames = [base + blob + rng.normal(0, 40, (size, size)).astype(np.float32)
              for _ in range(n)]
    master = base + blob + rng.normal(0, 40 / np.sqrt(n),
                                      (size, size)).astype(np.float32)
    return master, frames, blob


def commission():
    rng = np.random.default_rng(7)
    master, frames, blob = synth(rng, n=12)
    labels = ["f%d" % i for i in range(len(frames))]
    base = analyse(master, frames, labels)
    print("COMMISSIONING  synthetic static subject, %d frames\n" % len(frames))
    print("%-34s %9s %9s %9s %9s  %s"
          % ("arm", "ratio", "tile exc", "motion", "attr r", "required"))
    print("%-34s %9.4f %9.4f %9.4f %9.4f  %s"
          % ("BASE (unperturbed)", base["ratio"], base["tile_exc_max"],
             base["motion"], base["attr_best_corr"], "-- reference --"))

    rows = []

    def arm(name, m, fs, req, test):
        a = analyse(m, fs, labels[:len(fs)])
        ok = test(a)
        rows.append((name, a["ratio"], a["tile_exc_max"], a["motion"],
                     a["attr_best_corr"], req, ok))
        print("%-34s %9.4f %9.4f %9.4f %9.4f  %s  %s"
              % (name, a["ratio"], a["tile_exc_max"], a["motion"],
                 a["attr_best_corr"], req, "ok" if ok else "**FAIL**"))
        return a

    arm("null: master = a frame", frames[0].copy(), frames, "ratio ~ 1",
        lambda a: abs(a["ratio"] - 1.0) < 0.05)

    # DEGRADATION: fabricate mid-scale structure only the master has
    fake = rng.normal(0, 1, (WIN // 120 + 2, WIN // 120 + 2)).astype(np.float32)
    yy = np.linspace(0, fake.shape[0] - 1.001, WIN)
    xx = np.linspace(0, fake.shape[1] - 1.001, WIN)
    gi, gj = yy.astype(int), xx.astype(int)
    fy, fx = (yy - gi)[:, None], (xx - gj)[None, :]
    patch = (fake[np.ix_(gi, gj)] * (1 - fy) * (1 - fx)
             + fake[np.ix_(gi + 1, gj)] * fy * (1 - fx)
             + fake[np.ix_(gi, gj + 1)] * (1 - fy) * fx
             + fake[np.ix_(gi + 1, gj + 1)] * fy * fx).astype(np.float32)
    patch = patch / max(float(np.std(patch)), 1e-6) * 60.0
    arm("degrade: fabricated band in master", master + patch, frames,
        "ratio UP", lambda a: a["ratio"] > base["ratio"] * 1.2)

    # the attribution arm: fabricated structure must NOT correlate with frames
    a_fab = analyse(master + patch * 3.0, frames, labels)
    ok = a_fab["attr_best_corr"] < base["attr_best_corr"] - 0.2
    rows.append(("attribution: heavy fabrication", a_fab["ratio"],
                 a_fab["tile_exc_max"], a_fab["motion"],
                 a_fab["attr_best_corr"], "attr r DOWN", ok))
    print("%-34s %9.4f %9.4f %9.4f %9.4f  %s  %s"
          % ("attribution: heavy fabrication", a_fab["ratio"],
             a_fab["tile_exc_max"], a_fab["motion"], a_fab["attr_best_corr"],
             "attr r DOWN", "ok" if ok else "**FAIL**"))

    # IMPROVEMENT: the metric must be able to fall, not only rise
    smooth = boxblur(master, HI_R // 2) + (master - boxblur(master, LO_R // 2))
    arm("improve: master band removed", smooth, frames, "ratio DOWN",
        lambda a: a["ratio"] < base["ratio"] * 0.8)

    # DENOMINATOR perturbation: degrade the reference, ratio must fall
    noisier = [f + patch * 1.5 for f in frames]
    arm("denominator: band added to sources", master, noisier, "ratio DOWN",
        lambda a: a["ratio"] < base["ratio"] * 0.95)

    # DENOMINATOR thinning. THE DIRECTION HERE IS THE OPPOSITE OF WHAT I
    # ASSERTED TO ORCH, and this arm is what caught it. The minimum of a SMALL
    # sample is biased HIGH relative to the population minimum, so it is a
    # LARGER denominator, so master/min comes out SMALLER. Subsampling
    # SUPPRESSES measured excess; it cannot manufacture it. Every subsampled
    # ratio in RESULT.md is therefore a LOWER bound on its full-stack value --
    # which is what RESULT.md 6.1 already said, and what my summary to ORCH
    # contradicted.
    arm("denominator: thinned to 3 frames", master, frames[:3],
        "ratio DOWN", lambda a: a["ratio"] < base["ratio"] * 0.999)

    # MOTION: shift the blob in half the frames. motion must rise.
    moved = []
    for i, f in enumerate(frames):
        moved.append(np.roll(f, 40 * (i % 3), axis=1))
    arm("motion: subject shifted per frame", master, moved, "motion UP",
        lambda a: a["motion"] > base["motion"] * 3)

    # PLACEBO: high-frequency only. Outside the 50-400 px band; must not move.
    hf = rng.normal(0, 120, (WIN, WIN)).astype(np.float32)
    arm("placebo: high-frequency noise only", master + hf, frames,
        "ratio ~ unchanged",
        lambda a: abs(a["ratio"] / base["ratio"] - 1) < 0.02)

    commission2(master, frames, blob, base, patch, rows)
    nref = refused(master, frames, blob, base)

    bad = [r for r in rows if not r[6]]
    print("")
    print("%d ok + %d failed = %d arms;  %d statistic refused, unused"
          % (len(rows) - len(bad), len(bad), len(rows), nref))
    if bad:
        print("NOT COMMISSIONED:")
        for r in bad:
            print("  %s (required %s)" % (r[0], r[5]))
    return 0 if not bad else 1


def commission2(master, frames, blob, base, patch, rows):
    """The three DISCRIMINATORS get their own plants. They are what the verdict
    turns on -- the ratio only says "worse", these say "worse HOW" -- so
    certifying them on the arms above, which were built to move the ratio,
    would be certifying them by association."""
    labels = ["f%d" % i for i in range(len(frames))]
    print("")
    print("DISCRIMINATORS  each planted against its own mechanism")
    print("")
    print("%-36s %7s %7s %6s %7s %7s %6s  %s"
          % ("arm", "m_texc", "f_texc", "shift", "c_raw", "c_rec", "ghostz",
             "required"))

    def row2(name, a, req, ok):
        rows.append((name, a["m_texc_med"], a["f_texc_med"],
                     a["shift_absmax"], a["ghost_z"], req, ok))
        print("%-36s %7.4f %7.4f %6.1f %7.4f %7.4f %6.2f  %s  %s"
              % (name, a["m_texc_med"], a["f_texc_med"], a["shift_absmax"],
                 a["corr_raw_med"], a["corr_rec_med"], a["ghost_z"], req,
                 "ok" if ok else "**FAIL**"))
        return a

    # The LOO null must separate master from frames only when the master is
    # genuinely unusual. On an unperturbed master the margin must be ~0: if it
    # is not, the null is not a null and every excess it reports is its own.
    row2("null: LOO margin on clean master", base, "margin ~ 0",
         abs(base["m_texc_med"] - base["f_texc_med"]) < 0.15)
    a = analyse(master + patch, frames, labels)
    row2("degrade: LOO margin must open", a, "margin UP",
         (a["m_texc_med"] - a["f_texc_med"])
         > (base["m_texc_med"] - base["f_texc_med"]) + 0.3)

    # A DENOMINATOR perturbation for the null itself: dirtying the frames must
    # raise the FRAME null, not merely lower the ratio. If f_texc cannot move,
    # the control is decorative and the margin is the master's alone.
    a = analyse(master,
                [f + patch * 1.5 * (i % 2) for i, f in enumerate(frames)],
                labels)
    row2("denominator: half the frames dirtied", a, "f_texc UP",
         a["f_texc_med"] > base["f_texc_med"] * 1.2)

    # A rigid shift must be recovered, and correlation must recover WITH it.
    # The plant is required to be POTENT first: a recovery test run on an
    # undamaged correlation certifies nothing, and the arm this replaced was
    # rejected for exactly that -- a 25 px roll on a subject whose band has a
    # ~100 px correlation length moved corr by 0.14, under my own threshold.
    a = analyse(np.roll(master, 25, axis=0), frames, labels)
    row2("misregistration: master rolled 25px", a, "found, corr restored",
         abs(a["shift_absmax"] - 25) <= 2 and not a["shift_capped"]
         and a["corr_raw_med"] < base["corr_raw_med"] - 0.10
         and a["corr_rec_med"] > base["corr_raw_med"] - 0.05)

    # Independent motion must NOT be repairable by any rigid shift -- and must
    # have done damage in the first place. The first form of this arm rolled
    # 120 px patches at stride 260, which left c_raw at 0.9990: the patches
    # never overlapped the tile being measured, so "does not recover" was
    # satisfied by a plant that had not perturbed anything. Dense tiling is
    # what makes the arm potent.
    mv = master.copy()
    for i in range(0, WIN, 150):
        for j in range(0, WIN, 150):
            k = (i // 150 + 2 * (j // 150)) % 5
            mv[i:i + 150, j:j + 150] = np.roll(
                np.roll(mv[i:i + 150, j:j + 150], 45 + 20 * k, axis=1),
                30 - 15 * (k % 3), axis=0)
    a = analyse(mv, frames, labels)
    row2("independent motion: patchwise rolls", a, "damages, NO recovery",
         a["corr_raw_med"] < base["corr_raw_med"] - 0.10
         and a["corr_rec_med"] < base["corr_raw_med"] - 0.05)
    return rows


def refused(master, frames, blob, base):
    """The duplication ("ghosting") statistic, which I could not commission.

    It is reported here rather than deleted, because a statistic that quietly
    disappears between drafts is indistinguishable from one that passed.
    """
    labels = ["f%d" % i for i in range(len(frames))]
    a = analyse(master + np.roll(blob, 55, axis=1), frames, labels)
    print("")
    print("REFUSED  1 statistic, measured and excluded from the verdict")
    print("  ghost duplication (autocorrelation secondary peak)")
    print("    placebo, clean master        ghost z %+7.2f" % base["ghost_z"])
    print("    planted duplicate at +55 px  ghost z %+7.2f" % a["ghost_z"])
    print("    required: planted > placebo + 3.0. Measured: it is LOWER.")
    print("    Cause, measured not assumed: a 50-400 px band inside a 900 px")
    print("    window carries only ~10-80 independent cells, so the")
    print("    autocorrelation is lumpy by chance at the same magnitude as a")
    print("    planted duplicate. An earlier raw-max form failed harder still:")
    print("    the planted defect read 0.9468 against a placebo of 0.9521.")
    print("    The duplication question is therefore answered at 1:1, not by")
    print("    this number, and no ghost figure appears in the verdict.")
    return 1


def _png(a, path):
    from PIL import Image
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path)


def crops(mrgb, frgb, res, bw):
    """The worst-excess tile at native resolution, master against frames.

    ONE display mapping is derived from the master tile and applied unchanged
    to every panel. A per-panel mapping would make the crops a picture of the
    mapping -- the same defect, in the visual domain, as the sRGB gauge error
    that section 1 of RESULT.md is about.
    """
    os.makedirs(OUT, exist_ok=True)
    ty, tx = res["worst_tile"]
    k0, kb = res["best_frame"], res["attr_best_frame"]

    def tile(rgb):
        return rgb[ty:ty + TILE, tx:tx + TILE, :].astype(np.float64)

    lo = float(np.percentile(tile(mrgb), 0.5))
    hi = float(np.percentile(tile(mrgb), 99.5))
    gam = 2.2

    arms = [("master", mrgb),
            ("f%02d-lowest-blotch" % k0, frgb[k0]),
            ("f%02d-best-match" % kb, frgb[kb])]
    panels = []
    for name, rgb in arms:
        v = (tile(rgb) - lo) / max(hi - lo, 1e-9)
        img = np.clip(v, 0, 1) ** (1.0 / gam) * 255.0
        _png(img, os.path.join(OUT, "tile-%s.png" % name))
        panels.append(img)

    # the band field behind the statistic, on ONE symmetric scale for all arms
    bt = [nband(lum_of(rgb))[ty:ty + TILE, tx:tx + TILE] for _, rgb in arms]
    s = float(np.percentile(np.abs(bt[0]), 99.0))
    for (name, _), b in zip(arms, bt):
        img = np.repeat(((0.5 + 0.5 * np.clip(b / max(s, 1e-12), -1, 1))
                         * 255.0)[:, :, None], 3, axis=2)
        _png(img, os.path.join(OUT, "band-%s.png" % name))
        panels.append(img)

    g, h, w = 10, TILE, TILE
    sheet = np.full((2 * h + g, 3 * w + 2 * g, 3), 32.0)
    for i, p in enumerate(panels):
        r, c = divmod(i, 3)
        sheet[r * (h + g):r * (h + g) + h, c * (w + g):c * (w + g) + w] = p
    _png(sheet, os.path.join(OUT, "coffee-bubbles-worst-tile.png"))

    with open(os.path.join(OUT, "crops-README.txt"), "w",
              encoding="utf-8") as f:
        f.write("coffee-bubbles, worst-excess tile, native resolution."
                "  No resampling.\n")
        f.write("window (y=%d,x=%d) 900x900;  tile offset (+%d,+%d) %dx%d\n"
                % (bw[0], bw[1], ty, tx, TILE, TILE))
        f.write("absolute master pixels  y %d..%d  x %d..%d\n"
                % (bw[0] + ty, bw[0] + ty + TILE, bw[1] + tx,
                   bw[1] + tx + TILE))
        f.write("\nTop row:    master;  f%02d (lowest blotch of the 19);"
                "  f%02d (best match here)\n" % (k0, kb))
        f.write("Bottom row: the 50-400 px band field whose std IS blotch,"
                " same three arms\n")
        f.write("\nDISPLAY MAPPING, identical for every panel:\n")
        f.write("  linear DN, black %.1f, white %.1f (0.5/99.5 percentiles"
                " OF THE MASTER TILE), gamma %.1f\n" % (lo, hi, gam))
        f.write("  band panels: signed, symmetric, full scale %.4g"
                " (99th pct of |master band|), mid grey = 0\n" % s)
        f.write("Every arm was rendered --linear-srgb --demosaic by the same"
                " pinned binary, so the\npanels are comparable as pixels and"
                " not merely as pictures.\n")
    print("  wrote 7 files to %s" % OUT)
    return 0


def gather():
    """Render and register all 19 frames; return master + frame luminances."""
    os.makedirs(OUT, exist_ok=True)
    L.check_pin()
    mp = L.ensure_linear_master(SUBJ)
    mrgb = L.read_rgb(mp)
    mlum = lum_of(mrgb)
    bw, cw = L.choose_windows(mrgb)
    km = L.master_cover(SUBJ)
    n = L.n_frames(SUBJ)
    print("subject %s  frames %d  blotch window (y=%d,x=%d) %dx%d  cover %.4f"
          % (SUBJ, n, bw[0], bw[1], WIN, WIN, km))

    keep, rows = [], []
    for k in range(n):
        row = L.measure_source_frame(SUBJ, k, mlum, bw, cw, km, keep=keep)
        rows.append(row)
        print("  f%02d %-14s ncc %.3f  blotch %s"
              % (k, row.get("state"), row.get("ncc_b") or 0.0,
                 ("%.5f" % row["blotch"]) if "blotch" in row else "-"))
    got = {k: wb for k, wb, _ in keep}
    if len(got) != n:
        raise SystemExit("FATAL: kept %d of %d windows; refusing to report a "
                         "full-stack result on a partial stack" % (len(got), n))
    mwin = mlum[bw[0]:bw[0] + WIN, bw[1]:bw[1] + WIN]
    mrgb_win = mrgb[bw[0]:bw[0] + WIN, bw[1]:bw[1] + WIN, :]
    flums = [lum_of(got[k]) for k in range(n)]
    return mwin, flums, rows, bw, mrgb_win, [got[k] for k in range(n)]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    ap.add_argument("--crops", action="store_true")
    a = ap.parse_args(argv)
    if a.commission:
        return commission()

    mwin, flums, rows, bw, mrgb_win, frgb = gather()
    res = analyse(mwin, flums, ["f%d" % i for i in range(len(flums))])

    # reproduce the recorded run: this analysis must agree with vn_run
    rec = L.jload(os.path.join(L.OUT, "ratio", "%s.json" % SUBJ))
    dmax = max(abs(res["per_frame"][r["frame"]] - r["blotch"])
               for r in rec["rows"] if "blotch" in r)
    print("\nreproduction vs the recorded run: max |d blotch| = %.3e" % dmax)
    if dmax > 1e-6:
        raise SystemExit("FATAL: does not reproduce the recorded per-frame "
                         "blotch; the arms are not the same measurement")

    print("\nALL 19 SOURCES, no subsampling")
    print("  master blotch            %.6f" % res["master_blotch"])
    print("  best (min) source        %.6f  (f%d)"
          % (res["best_blotch"], res["best_frame"]))
    print("  ratio master/best        %.4fx" % res["ratio"])
    print("\nMOTION TEST  spread of the normalised band across the 19 frames")
    print("  median inter-frame spread %.3e" % res["inter_med"])
    print("  median |band| of master   %.3e" % res["mb_absmed"])
    print("  motion / structure        %.3f" % res["motion"])
    print("\nTILE EXCESS  %dpx tiles, stride %d, master vs best frame per tile"
          % (TILE, STRIDE))
    print("  median tile excess        %.4fx" % res["tile_exc_med"])
    print("  worst tile excess         %.4fx at (y=%d,x=%d) within the window"
          % (res["tile_exc_max"], res["worst_tile"][0], res["worst_tile"][1]))
    print("ATTRIBUTION at the worst tile")
    print("  best-matching frame       f%d, r = %.4f"
          % (res["attr_best_frame"], res["attr_best_corr"]))
    print("  matched null: each frame's best OTHER frame, median r = %.4f"
          % res["bestother_med"])
    print("  frame-to-frame agreement  median r = %.4f, min %.4f, max %.4f"
          % (res["pair_corr_med"], res["pair_corr_min"], res["pair_corr_max"]))
    print("")
    print("LEAVE-ONE-OUT NULL  is the excess unusual, or is it what any")
    print("object scores against the min of the others on this subject?")
    print("  window   master vs min-of-18   %.4fx" % res["m_loo_med"])
    print("           frames vs min-of-18   median %.4fx  max %.4fx"
          % (res["f_loo_med"], res["f_loo_max"]))
    print("  tiles    master, median tile   %.4fx" % res["m_texc_med"])
    print("           frames, median tile   median %.4fx  max %.4fx"
          % (res["f_texc_med"], res["f_texc_max"]))
    print("  worst tile  master %.4fx   frames median %.4fx  max %.4fx"
          % (res["m_wexc_med"], res["f_wexc_med"], res["f_wexc_max"]))
    print("  frames scoring at or above the master: %d of %d"
          % (res["texc_rank"], len(flums)))
    print("")
    print("RIGID OR NOT  at the worst tile. Commissioned scale: a planted")
    print("pure misregistration recovers to 98%% of the clean baseline,")
    print("planted independent motion only to 77%%.")
    print("  master vs frames  r %.4f -> %.4f after a shift of %.0f px "
          "(median %.0f)%s"
          % (res["corr_raw_med"], res["corr_rec_med"], res["shift_absmax"],
             res["shift_absmed"], "  CAPPED" if res["shift_capped"] else ""))
    print("  frame vs frame    r %.4f -> %.4f after a shift of %.0f px "
          "(median %.0f)"
          % (res["fp_corr_raw"], res["fp_corr_rec"], res["fp_shift_max"],
             res["fp_shift_med"]))
    res["window"] = list(bw)
    L.jdump(res, os.path.join(OUT, "bubbles.json"))
    print("")
    print("wrote %s" % os.path.join(OUT, "bubbles.json"))
    if a.crops:
        crops(mrgb_win, frgb, res, bw)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
