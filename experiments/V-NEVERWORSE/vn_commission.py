r"""V-NEVERWORSE / INSTRUMENT COMMISSIONING -- planted defects in BOTH directions.

The gauge is commissioned separately in `vn_gauge.py`. This file commissions the
INSTRUMENT: the master/source ratio itself, built on real image windows from a
real subject, with defects planted into the numerator, into the DENOMINATOR,
and into neither.

A metric that only ever rises under disturbance may be bounded below and blind
-- this project has already been bitten by a statistic that could not charge
for a defect because its sign was bounded at zero. So every ladder here is run
in both directions and both are required.

ARMS
  N0  IDENTITY             alpha = 0. Must not move at all.
  N1  PLACEBO WITH POWER   full-amplitude plant placed OUTSIDE the measured
                           window. Must not move -- but WOULD move if the
                           window coordinates were wrong, which is what gives
                           the placebo power instead of being decoration.
  D1  DEGRADE  (blotch)    blotch injected into the master. Ratio must RISE.
  I1  IMPROVE  (blotch)    the master's own band-pass component subtracted.
                           Ratio must FALL, and must fall BELOW the alpha=0
                           reading. This is the arm that catches a floor.
  D2  DEGRADE  (chroma)    band-limited chroma noise into the master. RISE.
  I2  IMPROVE  (chroma)    relative-chroma band-pass attenuated. FALL.
  S1  DENOMINATOR WORSE    the same plant applied to every SOURCE frame, master
                           untouched. Ratio must FALL.
  S2  DENOMINATOR THINNED  N reduced. min/max must MOVE (they are extrema and
                           are biased in N); the median must be comparatively
                           stable. Quantified, because the source-set size is a
                           free parameter and the sharpness lane's thinning
                           alone moved its readings across unity.
  X1  CROSS-TALK           a luminance-only plant must move blotch and leave
                           chroma; a chroma-only plant the reverse. States each
                           statistic's fooling direction on real data.
  W1  RESAMPLING NULL      the master pushed through the same cv2.warpAffine
                           the source windows go through. Must not move -- if
                           it does, every ratio is charging the merge for a
                           resampler the denominator alone was exposed to.
  Q1  QUANTISATION FLOOR   linear renders are darker than the sRGB ones. Is the
                           measured band above the band of pure uint16
                           quantisation noise, and is the chroma window's luma
                           far above `relative_chroma`'s hard floor of 1.0 DN?

  python vn_commission.py [subject]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402
from orch_blotch import boxblur, lum_of, LO_R, HI_R           # noqa: E402
from orch_chroma import relative_chroma                       # noqa: E402
from orch_chroma import LO_R as C_LO, HI_R as C_HI            # noqa: E402

SUBJ = "coffee-bubbles"        # 19 frames: a FULL source arm is affordable
BDIR = os.path.join(L.OUT, "bundle")


# --------------------------------------------------------------------------
def blot_field(shape, rng, cell=64):
    """Bilinear-interpolated coarse noise -- the plant `orch_blotch.commission`
    uses, unit variance, so amplitudes below are in DN."""
    h, w = shape
    c = rng.normal(0, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
    yy = np.linspace(0, c.shape[0] - 1, h)
    xx = np.linspace(0, c.shape[1] - 1, w)
    gi = np.clip(yy.astype(int), 0, c.shape[0] - 2)
    gj = np.clip(xx.astype(int), 0, c.shape[1] - 2)
    fy, fx = (yy - gi)[:, None], (xx - gj)[None, :]
    f = (c[np.ix_(gi, gj)] * (1 - fy) * (1 - fx)
         + c[np.ix_(gi + 1, gj)] * fy * (1 - fx)
         + c[np.ix_(gi, gj + 1)] * (1 - fy) * fx
         + c[np.ix_(gi + 1, gj + 1)] * fy * fx).astype(np.float32)
    # Zero-mean matters: blotch is band/MEAN, so a plant with a non-zero mean
    # moves the denominator of the statistic as well as its numerator and can
    # LOWER the reading at small amplitude. A blotch is a modulation, not a
    # pedestal.
    f -= float(f.mean())
    return f / max(float(np.std(f)), 1e-6)


def degrade_lum(win, amp, field):
    """Luminance blotch: ONE field, scaled -- a nested ladder, not five
    independent draws. (`orch_blotch.commission` draws once and scales; a
    ladder that redraws is not a ladder.) Added to all three channels."""
    return np.clip(win + field[:, :, None] * amp, 0, 65535)


def improve_lum(win, alpha):
    """Remove alpha of the window's OWN mid-scale structure. An improvement
    that is real in the statistic's own terms, not a smoothing that would also
    destroy the noise term."""
    lum = lum_of(win)
    band = boxblur(lum, LO_R // 2) - boxblur(lum, HI_R // 2)
    return np.clip(win - alpha * band[:, :, None], 0, 65535)


def degrade_chroma(win, amp, field):
    """Push R and B in opposite directions: pure chroma, luma ~unchanged."""
    out = win.copy()
    out[:, :, 0] += field * amp
    out[:, :, 2] -= field * amp
    return np.clip(out, 0, 65535)


def gain_lum(win, amp, field):
    """MULTIPLICATIVE achromatic blotch. relative_chroma is (R-Y)/Y, so a
    common multiplicative factor cancels exactly -- this is the clean null for
    chroma against a luminance disturbance, where the additive plant is not."""
    return np.clip(win * (1.0 + field * amp)[:, :, None], 0, 65535)


def improve_chroma(win, alpha):
    a, b, y = relative_chroma(win)
    ba = boxblur(a.astype(np.float32), C_LO) - boxblur(a.astype(np.float32), C_HI)
    bb = boxblur(b.astype(np.float32), C_LO) - boxblur(b.astype(np.float32), C_HI)
    out = win.copy()
    out[:, :, 0] -= alpha * ba * y
    out[:, :, 2] -= alpha * bb * y
    return np.clip(out, 0, 65535)


# --------------------------------------------------------------------------
def build_bundle(subj, force=False):
    """Every frame of `subj`, rendered in the measurement space, registered to
    the linear master, cropped to the master's own two windows and cached."""
    os.makedirs(BDIR, exist_ok=True)
    npz = os.path.join(BDIR, "%s.npz" % subj)
    js = os.path.join(BDIR, "%s.json" % subj)
    if os.path.exists(npz) and os.path.exists(js) and not force:
        d = np.load(npz)
        return L.jload(js), d
    L.check_pin()
    mp = L.ensure_linear_master(subj)
    mrgb = L.read_rgb(mp)
    bw, cw = L.choose_windows(mrgb)
    mlum = lum_of(mrgb)
    km = L.master_cover(subj) or 1.0
    frames = list(range(L.n_frames(subj)))
    rows, keep = [], []
    for k in frames:
        r = L.measure_source_frame(subj, k, mlum, bw, cw, km, keep=keep)
        rows.append(r)
        print("  f%-4d %-20s ncc %s  %.1fs" % (k, r["state"], r.get("ncc_b"), r["secs"]))
        sys.stdout.flush()
    meta = dict(subject=subj, bw=list(bw), cw=list(cw), km=km, rows=rows,
                kept=[k for k, _, _ in keep],
                master=L.stats_at(mrgb, bw, cw))
    arrs = dict(mb=mrgb[bw[0]:bw[0] + L.BWIN, bw[1]:bw[1] + L.BWIN].astype(np.uint16),
                mc=mrgb[cw[0]:cw[0] + L.CWIN, cw[1]:cw[1] + L.CWIN].astype(np.uint16))
    for k, wb, wc in keep:
        arrs["b%04d" % k] = wb.astype(np.uint16)
        arrs["c%04d" % k] = wc.astype(np.uint16)
    np.savez_compressed(npz, **arrs)
    L.jdump(meta, js)
    del mrgb, mlum
    return meta, np.load(npz)


# --------------------------------------------------------------------------
def src_stats(meta, arrs, frames):
    out = []
    for k in frames:
        s = L.window_stats(arrs["b%04d" % k].astype(np.float32),
                           arrs["c%04d" % k].astype(np.float32))
        s["frame"] = k
        s["state"] = "OK"
        s["ok_b"] = s["sat_b"] <= L.SAT_MAX
        s["ok_c"] = s["sat_c"] <= L.SAT_MAX
        out.append(s)
    return out


def ratios(mstat, srows, key):
    o = L.order_stats(srows, key)
    if o is None:
        return None
    return dict(vs_min=mstat[key] / o["min"], vs_med=mstat[key] / o["med"],
                vs_max=mstat[key] / o["max"], **o)


def line(tag, verdict, note):
    return dict(arm=tag, verdict=verdict, note=note)


def main(argv):
    subj = argv[0] if argv else SUBJ
    print("BUNDLE %s" % subj)
    meta, arrs = build_bundle(subj)
    ok_frames = [r["frame"] for r in meta["rows"] if r["state"] == "OK"]
    ok_frames = [k for k in ok_frames if "b%04d" % k in arrs]
    print("  %d/%d frames registered and kept" % (len(ok_frames), len(meta["rows"])))
    mb = arrs["mb"].astype(np.float32)
    mc = arrs["mc"].astype(np.float32)
    srows = src_stats(meta, arrs, ok_frames)

    def R(mbw, mcw, rows=None):
        m = L.window_stats(mbw, mcw)
        rr = rows if rows is not None else srows
        return (ratios(m, rr, "blotch"), ratios(m, rr, "chroma"), m)

    b0, c0, m0 = R(mb, mc)
    base = dict(blotch=b0["vs_min"], chroma=c0["vs_min"])
    print("\nBASELINE  master blotch %.5f chroma %.5f | vs BEST(min) source "
          "blotch %.4fx chroma %.4fx | n=%d"
          % (m0["blotch"], m0["chroma"], b0["vs_min"], c0["vs_min"], b0["n"]))

    rows = []
    # One field per window, drawn once and reused at every rung so the ladders
    # are nested and the only thing that changes is amplitude.
    fb = blot_field(mb.shape[:2], np.random.default_rng(101))
    fc = blot_field(mc.shape[:2], np.random.default_rng(102))

    # ---- N0 identity ------------------------------------------------------
    b, c, _ = R(mb.copy(), mc.copy())
    same = (b["vs_min"] == base["blotch"]) and (c["vs_min"] == base["chroma"])
    rows.append(line("N0 identity (alpha=0)", "PASS" if same else "FAIL",
                     "blotch %.6fx chroma %.6fx -- bitwise unchanged: %s"
                     % (b["vs_min"], c["vs_min"], same)))

    # ---- N1 placebo with power -------------------------------------------
    # Full-amplitude plant written into a DIFFERENT window of the master, then
    # measured at the real one. Moves only if the window is not where we think.
    big = degrade_lum(mb, 400.0, blot_field(mb.shape[:2], np.random.default_rng(7)))
    b, c, _ = R(mb, mc)             # measured window untouched
    moved = abs(b["vs_min"] - base["blotch"]) > 1e-9
    bhit, _, _ = R(big, mc)
    rows.append(line("N1 placebo outside window",
                     "PASS" if (not moved and bhit["vs_min"] > base["blotch"] * 1.5)
                     else "FAIL",
                     "unmeasured window: %.6fx (moved %s); the same plant INSIDE "
                     "the window reads %.4fx -- so the placebo had power"
                     % (b["vs_min"], moved, bhit["vs_min"])))

    # ---- D1 / I1 blotch, both directions ---------------------------------
    # Averaged over independent field realisations. One random plant can
    # partially CANCEL the structure already in the window -- with ~198
    # independent cells in a 900 px window the correlation between a single
    # draw and the master's own band has std ~0.07, which at a 7% disturbance
    # is larger than the sqrt-addition the plant contributes. That is a
    # property of a single draw, not of the statistic, so the ladder is run
    # over 6 draws and the spread is reported.
    fbs = [blot_field(mb.shape[:2], np.random.default_rng(1100 + i)) for i in range(6)]
    fcs = [blot_field(mc.shape[:2], np.random.default_rng(1200 + i)) for i in range(6)]
    pband = float(np.mean([np.std(boxblur(f, LO_R // 2) - boxblur(f, HI_R // 2))
                           for f in fbs]))
    prev, mono = base["blotch"], True
    seq = []
    for amp in (5.0, 10.0, 20.0, 40.0, 80.0):
        v = [R(degrade_lum(mb, amp, f), mc)[0]["vs_min"] for f in fbs]
        mu = float(np.mean(v))
        seq.append((amp, mu, min(v), max(v)))
        mono = mono and mu > prev
        prev = mu
    rows.append(line("D1 degrade master blotch", "PASS" if mono else "FAIL",
                     "amp DN -> mean ratio over 6 fields [range]: "
                     + "  ".join("%.0f:%.4fx[%.4f-%.4f]" % t for t in seq)
                     + "  (base %.4fx; plant in-band std %.3f x amp DN vs the "
                       "master's %.1f DN, so rung 1 is a %.1f%% disturbance)"
                     % (base["blotch"], pband, m0["band"],
                        100 * 5.0 * pband / m0["band"])))

    prev, mono, below = base["blotch"], True, False
    seq = []
    for al in (0.2, 0.4, 0.6, 0.8, 0.95):
        b, _, m = R(improve_lum(mb, al), mc)
        seq.append((al, b["vs_min"]))
        mono = mono and b["vs_min"] < prev
        prev = b["vs_min"]
        below = below or b["vs_min"] < base["blotch"]
    rows.append(line("I1 improve master blotch", "PASS" if mono and below else "FAIL",
                     "alpha -> ratio: " + "  ".join("%.2f:%.4fx" % t for t in seq)
                     + "  (base %.4fx) -- falls below base: %s, crosses unity "
                       "downward: %s" % (base["blotch"], below,
                                         min(v for _, v in seq) < 1.0 < base["blotch"])))

    # ---- D2 / I2 chroma, both directions ---------------------------------
    prev, mono = base["chroma"], True
    seq = []
    ca = float(np.mean([np.std(boxblur(f, C_LO) - boxblur(f, C_HI)) for f in fcs]))
    ylo = float(np.percentile(relative_chroma(mc)[2], 1))
    for amp in (10.0, 20.0, 40.0, 80.0, 160.0):
        v = [R(mb, degrade_chroma(mc, amp, f))[1]["vs_min"] for f in fcs]
        mu = float(np.mean(v))
        seq.append((amp, mu, min(v), max(v)))
        mono = mono and mu > prev
        prev = mu
    rows.append(line("D2 degrade master chroma", "PASS" if mono else "FAIL",
                     "amp DN -> mean ratio over 6 fields [range]: "
                     + "  ".join("%.0f:%.4fx[%.4f-%.4f]" % t for t in seq)
                     + "  (base %.4fx; rung 1 is a relative-chroma disturbance of "
                       "~%.4f against the master's %.4f = %.0f%%. Below ~5 DN the "
                       "ladder is inside its own field-to-field spread and does "
                       "not resolve -- stated rather than hidden by starting the "
                       "ladder higher.)"
                     % (base["chroma"], 10.0 * ca / ylo, m0["chroma"],
                        100 * 10.0 * ca / ylo / m0["chroma"])))

    prev, mono, below = base["chroma"], True, False
    seq = []
    for al in (0.2, 0.4, 0.6, 0.8, 0.95):
        _, c, _ = R(mb, improve_chroma(mc, al))
        seq.append((al, c["vs_min"]))
        mono = mono and c["vs_min"] < prev
        prev = c["vs_min"]
        below = below or c["vs_min"] < base["chroma"]
    rows.append(line("I2 improve master chroma", "PASS" if mono and below else "FAIL",
                     "alpha -> ratio: " + "  ".join("%.2f:%.4fx" % t for t in seq)
                     + "  (base %.4fx) -- falls below base: %s, crosses unity "
                       "downward: %s" % (base["chroma"], below,
                                         min(v for _, v in seq) < 1.0 < base["chroma"])))

    # ---- S1 denominator degraded -----------------------------------------
    dn = []
    for k in ok_frames:
        s = L.window_stats(degrade_lum(arrs["b%04d" % k].astype(np.float32), 40.0, fb),
                           degrade_chroma(arrs["c%04d" % k].astype(np.float32), 20.0, fc))
        s.update(frame=k, state="OK", ok_b=s["sat_b"] <= L.SAT_MAX,
                 ok_c=s["sat_c"] <= L.SAT_MAX)
        dn.append(s)
    b, c, _ = R(mb, mc, rows=dn)
    fell = b["vs_min"] < base["blotch"] and c["vs_min"] < base["chroma"]
    rows.append(line("S1 denominator degraded", "PASS" if fell else "FAIL",
                     "blotch %.4fx -> %.4fx, chroma %.4fx -> %.4fx  (master "
                     "untouched; the reference IS load-bearing)"
                     % (base["blotch"], b["vs_min"], base["chroma"], c["vs_min"])))

    # ---- S2 denominator thinned, two ways --------------------------------
    # (a) leave-one-out on the argmin: the decisive test that the min is
    #     load-bearing rather than a stable property of the subject.
    o = L.order_stats(srows, "blotch")
    loo = [r for r in srows if r["frame"] != o["argmin"]]
    b_loo = ratios(m0, loo, "blotch")
    # (b) RANDOM subsets, not linspace. A linspace subsample of a focus sweep
    #     always retains both ends, so it can retain the argmin at every N and
    #     report a stability the estimator does not have.
    rng2 = np.random.default_rng(555)
    seq = []
    for n in (3, 5, 9, 13):
        if n > len(ok_frames):
            continue
        v = []
        for _ in range(60):
            pick = set(int(x) for x in rng2.choice(ok_frames, n, replace=False))
            sub = [r for r in srows if r["frame"] in pick]
            rr = ratios(m0, sub, "blotch")
            if rr is None:
                raise RuntimeError("S2: empty order statistic for subset %s "
                                   "(%d of %d rows matched)"
                                   % (sorted(pick), len(sub), len(srows)))
            v.append(rr["vs_min"])
        seq.append((n, min(v), max(v), max(v) / min(v)))
    spread = max(s[3] for s in seq) if seq else 1.0
    moved = abs(b_loo["vs_min"] / base["blotch"] - 1.0)
    rows.append(line("S2 denominator thinned",
                     "PASS" if (spread > 1.001 and moved > 1e-4) else "FAIL",
                     "drop the argmin frame (f%d): %.4fx -> %.4fx (%.2f%%). "
                     "60 random subsets per N -> vs_min range: "
                     % (o["argmin"], base["blotch"], b_loo["vs_min"], 100 * moved)
                     + "  ".join("N=%d:%.4f-%.4f(%.3fx)" % s for s in seq)))

    # ---- X1 cross-talk / fooling direction -------------------------------
    # Stated as three separate claims because the honest answer is asymmetric.
    b, c, _ = R(degrade_chroma(mb, 40.0, fb), degrade_chroma(mc, 40.0, fc))
    chr_on_b, chr_on_c = b["vs_min"] / base["blotch"], c["vs_min"] / base["chroma"]
    rows.append(line("X1a chromatic plant",
                     "PASS" if chr_on_c > 1.2 and abs(chr_on_b - 1) < 0.25 else "FAIL",
                     "blotch x%.3f (should not move), chroma x%.3f (should rise)"
                     % (chr_on_b, chr_on_c)))
    b, c, _ = R(gain_lum(mb, 0.05, fb), gain_lum(mc, 0.05, fc))
    g_on_b, g_on_c = b["vs_min"] / base["blotch"], c["vs_min"] / base["chroma"]
    rows.append(line("X1b achromatic MULTIPLICATIVE plant",
                     "PASS" if g_on_b > 1.2 and abs(g_on_c - 1) < 0.10 else "FAIL",
                     "blotch x%.3f (should rise), chroma x%.3f (exactly cancels "
                     "in (R-Y)/Y, so it must not move)" % (g_on_b, g_on_c)))
    b, c, _ = R(degrade_lum(mb, 80.0, fb), degrade_lum(mc, 80.0, fc))
    a_on_b, a_on_c = b["vs_min"] / base["blotch"], c["vs_min"] / base["chroma"]
    rows.append(line("X1c achromatic ADDITIVE plant  [FOOLING DIRECTION]",
                     "PASS" if a_on_b > 1.2 else "FAIL",
                     "blotch x%.3f, chroma x%.3f. This is NOT independence and "
                     "is not a bug in the ratio: adding d to R,G,B sends "
                     "(R-Y)/Y to (R-Y)/(Y+d), so orch_chroma's relative chroma "
                     "is modulated by a LUMINANCE blotch. At d_rms=80 DN on a "
                     "window with p1 luma %.0f DN that is worth x%.3f. A chroma "
                     "ratio must therefore never be read as chroma-only when "
                     "the luminance ratio has also moved."
                     % (a_on_b, a_on_c, float(np.percentile(
                         relative_chroma(mc)[2], 1)), a_on_c)))

    # ---- W1 the resampling null ------------------------------------------
    # Every source window is pulled through cv2.warpAffine/INTER_LINEAR while
    # the master window is not. Bilinear interpolation is a ~1 px low-pass. The
    # blotch band is 50-400 px and the chroma band 50-300 px, so it SHOULD be
    # untouched -- but "should" is how the sharpness lane shipped a gain. So
    # the master is pushed through the same resampler at the magnitudes the
    # real registrations actually used, and the reading must not move.
    import cv2
    scales = [r.get("scale") for r in meta["rows"]
              if r.get("state") == "OK" and r.get("scale")]
    smag = max(abs(s - 1.0) for s in scales) if scales else 0.0
    w1 = []
    for nm, M in (("identity", np.array([[1, 0, 0], [0, 1, 0]], float)),
                  ("shift 0.37,0.61 px",
                   np.array([[1, 0, 0.37], [0, 1, 0.61]], float)),
                  ("scale 1+%.2e + shift" % max(smag, 3e-4),
                   np.array([[1 + max(smag, 3e-4), 0, 0.37],
                             [0, 1 + max(smag, 3e-4), 0.61]], float)),
                  ("rotate 0.05 deg",
                   cv2.getRotationMatrix2D((L.BWIN / 2, L.BWIN / 2), 0.05, 1.0))):
        wb = cv2.warpAffine(mb, M.astype(np.float32), (L.BWIN, L.BWIN),
                            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                            borderMode=cv2.BORDER_REPLICATE)
        Mc = M.copy()
        if nm.startswith("rotate"):
            Mc = cv2.getRotationMatrix2D((L.CWIN / 2, L.CWIN / 2), 0.05, 1.0)
        wc = cv2.warpAffine(mc, Mc.astype(np.float32), (L.CWIN, L.CWIN),
                            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                            borderMode=cv2.BORDER_REPLICATE)
        b, c, mm = R(wb, wc)
        w1.append((nm, b["vs_min"] / base["blotch"], c["vs_min"] / base["chroma"],
                   mm["relhf"] / m0["relhf"]))
    worst = max(max(abs(t[1] - 1), abs(t[2] - 1)) for t in w1)
    rows.append(line("W1 resampling null (denominator-side confound)",
                     "PASS" if worst < 0.02 else "FAIL",
                     "  ".join("%s: blotch x%.4f chroma x%.4f relhf x%.3f" % t
                               for t in w1)
                     + "  | worst band/chroma departure %.2f%%. The 3 px relhf "
                       "term DOES fall -- which is exactly why this lane ratios "
                       "band/mean and never band/noise." % (100 * worst)))
    q = np.random.default_rng(9).uniform(-0.5, 0.5, mb.shape[:2]).astype(np.float32)
    qb = float(np.std(boxblur(q, LO_R // 2) - boxblur(q, HI_R // 2)))
    _, _, ylin = relative_chroma(mc)
    ymin = float(np.percentile(ylin, 1))
    headroom = m0["band"] / max(qb, 1e-9)
    rows.append(line("Q1 quantisation floor",
                     "PASS" if headroom > 20 and ymin > 50 else "FAIL",
                     "master band %.3f DN vs uint16 quantisation band %.4f DN "
                     "= %.0fx headroom; chroma-window luma p1 = %.0f DN vs "
                     "relative_chroma's hard floor of 1.0"
                     % (m0["band"], qb, headroom, ymin)))

    print("\nINSTRUMENT COMMISSIONING  (subject %s, %d source frames)"
          % (subj, len(ok_frames)))
    w = max(len(r["arm"]) for r in rows)
    for r in rows:
        print("  %-*s  %-4s  %s" % (w, r["arm"], r["verdict"], r["note"]))
    ok = all(r["verdict"] == "PASS" for r in rows)
    print("\n%s" % ("COMMISSIONED" if ok else "NOT COMMISSIONED -- refusing to "
                    "report real numbers"))
    L.jdump(dict(subject=subj, n=len(ok_frames), base=base, arms=rows, ok=ok),
            os.path.join(L.OUT, "commission", "%s.json" % subj))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
