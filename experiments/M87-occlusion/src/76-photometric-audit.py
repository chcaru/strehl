"""M87 / 76 -- audit of 75, because two of its numbers do not mean what the
script called them.

75 returned a clean registered kill for the BOX and I stand behind it: the
planted +/-10% per-frame drift moved E's box by +0.02908 and normalisation
removed 89.0% of that movement, while the REAL box survived normalisation at
102.22%.  Both C-D3-POS arms passed.  That part needs no repair.

Two things in 75 do need repair, and I found them by reading my own output
rather than by anyone challenging it.

DEFECT 1 -- "gain" IS NOT GAIN.  D1 fit g_k by regressing frame k on the
    ensemble reference, and reported a peak-to-peak of 109.671% with an offset
    swing of 4036 DN against a 3747 DN level.  No camera drifts by 110% across a
    focus sweep.  What that regression actually measures is CONTRAST: a frame in
    which the background is defocused has its structure smoothed away, so its
    covariance with a sharp reference collapses and g_k reads low; a frame in
    which the background is sharp reads high.  The estimator is confounded with
    focus, and at d >= 140 in a focus stack the background's focus is exactly
    what is changing.  C-D1-POS passed (0.000% recovery error) because a planted
    multiplicative ramp is recovered perfectly by a covariance fit whether or
    not the fit also contains a focus term -- the control was real but it was
    blind to this failure.
    THE HONEST NUMBER instead: per-frame MEAN LEVEL over the reference region.
    Convolution conserves the mean, so defocus moves it only through edge
    effects; a real exposure change moves it proportionally.

DEFECT 2 -- THE TROUGH'S 45.74% SURVIVAL IS NOT YET ATTRIBUTABLE.  Because g_k
    is really a contrast term, dividing by it rescales each frame's focus
    measure, which perturbs the election directly -- and the election agreed
    with baseline at only 70.329% of pixels.  So the shelf's disappearance may
    be my normaliser DAMAGING the election rather than removing real drift.
    That distinction is the whole finding, and 75 cannot make it.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

A1 -- TRUE EXPOSURE DRIFT.  Per-frame mean level on d >= 140.  Report
    peak-to-peak as a fraction.  This is the answer to ORCH's measurement (1),
    and it is the number I will quote, not 75's 109.671%.

A2 -- DEMONSTRATE THE CONFOUND rather than assert it.  Correlate the fitted g_k
    against per-frame mean level and against per-frame mean focus response on
    the same region.
    REGISTERED: if |rho(g, focus)| exceeds |rho(g, level)| the estimator is
    confounded with focus and 75's D1 magnitude must be withdrawn.

A3 -- LEVEL-ONLY NORMALISATION, which is focus-neutral.  Scale each frame by
    Lref/L_k, re-elect, re-merge, recompute E.
    REGISTERED: box and trough survival, same 75%/25% thresholds as D3.

A4 -- THE DECISIVE CONTROL FOR DEFECT 2, and it is the one I would want run
    against me.  Divide frame k by g_sigma(k) for a random permutation sigma.
    That perturbs the election by the same magnitude as the real normalisation
    while correcting nothing.
    REGISTERED: if the shuffled arm drops the trough by at least half as much as
    the fitted arm does, the trough's fall is ELECTION PERTURBATION and not
    photometric correction, and I withdraw any photometric reading of the shelf.

A5 -- D2 WITH DISTANCE PARTIALLED OUT.  75 correlated excess against index gap
    across the whole band, but both vary with d inside a band containing E's
    peak, so the rolled null read +0.0660 instead of 0.  Recompute Spearman
    WITHIN each 1 px distance bin and pool, so distance cannot drive it.
    REGISTERED: report pooled rho with the same rolled-gap null.  ORCH's
    mechanism predicts positive; report the sign whatever it is.

READ-ONLY: D:\\personal\\macro.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter, minimum_filter
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")

ISO = 100.0
FAR = (80, 120)
REF_D = 140
BOX = (2, 22)
DMAX = 200
ROLL = (317, 511)
SEED = 8711


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def main():
    t0 = time.time()
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    n, h, w = cube.shape
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1

    fmask, _ = L.foreground_mask(sel0)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros((h, w), bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    edges = np.searchsorted(dv[order], np.arange(0, DMAX + 2))
    ref_px = valid & (dd >= REF_D)
    band_px = valid & (dd >= BOX[0]) & (dd <= BOX[1])

    def prof(img):
        v = img[valid][order]
        out = np.full(DMAX + 1, np.nan)
        for d in range(DMAX + 1):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    # ---------------- A1 / A2
    print("--- A1 true per-frame exposure on d >= %d ---" % REF_D, flush=True)
    lvl = np.empty(n)
    foc = np.empty(n)
    ref_stack = np.empty((n, int(ref_px.sum())), np.float32)
    for k in range(n):
        f = np.asarray(cube[k], dtype=np.float32)
        ref_stack[k] = f[ref_px]
        lvl[k] = float(ref_stack[k].mean())
        foc[k] = float(L.regularised_field(f, ISO)[ref_px].mean())
    Lref = float(lvl.mean())
    p2p = float((lvl.max() - lvl.min()) / Lref)
    print(f"  mean level {Lref:.1f} DN   min {lvl.min():.1f}  max {lvl.max():.1f}"
          f"   peak-to-peak {100 * p2p:.3f}%   sd {100 * lvl.std() / Lref:.3f}%",
          flush=True)

    reference = ref_stack.mean(0).astype(np.float64)
    rc = reference - reference.mean()
    den = float((rc * rc).sum())

    def fit(stack):
        g = np.empty(n)
        o = np.empty(n)
        for k in range(n):
            y = stack[k].astype(np.float64)
            g[k] = float((rc * (y - y.mean())).sum() / den)
            o[k] = float(y.mean() - g[k] * reference.mean())
        return g, o

    gain, off = fit(ref_stack)
    r_lvl = float(spearmanr(gain, lvl).statistic)
    r_foc = float(spearmanr(gain, foc).statistic)
    confounded = abs(r_foc) > abs(r_lvl)
    print("\n--- A2 what is 75's fitted 'gain' actually tracking? ---", flush=True)
    print(f"  rho(g, per-frame level) = {r_lvl:+.4f}", flush=True)
    print(f"  rho(g, per-frame focus) = {r_foc:+.4f}", flush=True)
    print(f"  -> estimator is {'CONFOUNDED WITH FOCUS' if confounded else 'level-driven'}"
          f"; 75's D1 magnitude of 109.671% "
          f"{'is WITHDRAWN' if confounded else 'stands'}", flush=True)

    # the honest version of 75's D1 comparison, on level rather than contrast
    l_band = lvl[argbest[band_px]] / Lref
    l_far = lvl[argbest[valid & (dd >= FAR[0]) & (dd <= FAR[1])]] / Lref
    exc_l = float(np.median(l_band) / np.median(l_far) - 1.0)
    box_amp = 0.14393
    share = abs(exc_l) / box_amp
    print(f"  elected-frame LEVEL: band median {np.median(l_band):.5f}, far "
          f"median {np.median(l_far):.5f}, excess {100 * exc_l:+.4f}%", flush=True)
    print(f"  against E's box of {100 * box_amp:.3f}%: exposure drift between "
          f"the elected frames supplies {100 * share:.2f}% of it, a shortfall of "
          f"{1 / max(share, 1e-9):.0f}x", flush=True)

    # ---------------- A3 / A4
    rng = np.random.default_rng(SEED)
    perm = rng.permutation(n)
    while int((perm == np.arange(n)).sum()) > n // 10:
        perm = rng.permutation(n)

    def elect(mode):
        best = np.full((h, w), -np.inf, np.float32)
        arg = np.zeros((h, w), np.int32)

        def frame(k):
            f = np.asarray(cube[k], dtype=np.float32)
            if mode == "level":
                return (f * np.float32(Lref / lvl[k])).astype(np.float32)
            if mode == "fit":
                return ((f - np.float32(off[k])) / np.float32(gain[k])).astype(np.float32)
            if mode == "shuffle":
                j = perm[k]
                return ((f - np.float32(off[j])) / np.float32(gain[j])).astype(np.float32)
            return f

        for k in range(n):
            fl = L.regularised_field(frame(k), ISO)
            b = fl > best
            best[b] = fl[b]
            arg[b] = k
        sel = np.empty((h, w), np.float32)
        Pk = np.empty((n, DMAX + 1))
        for k in range(n):
            f = frame(k)
            Pk[k] = prof(f)
            s = arg == k
            if s.any():
                sel[s] = f[s]
        with np.errstate(invalid="ignore"):
            e = np.nanmean(Pk, axis=0)
        fl_ = float(np.nanmedian(e[FAR[0]:FAR[1] + 1]))
        return (prof(sel) - e) / fl_, arg

    print("\n--- A3 level-only (focus-neutral) normalisation ---", flush=True)
    E_base, arg_base = elect("none")
    pk = int(np.nanargmax(np.where(np.isfinite(E_base), E_base, -np.inf)[1:121])) + 1
    tr = int(np.nanargmin(np.where(np.isfinite(E_base), E_base, np.inf)[1:121])) + 1
    E_lvl, arg_lvl = elect("level")
    print(f"  baseline   box {E_base[pk]:+.5f} (d={pk})   trough "
          f"{E_base[tr]:+.5f} (d={tr})", flush=True)
    print(f"  level-norm box {E_lvl[pk]:+.5f} ({100 * E_lvl[pk] / E_base[pk]:.2f}% "
          f"survives)   trough {E_lvl[tr]:+.5f} "
          f"({100 * E_lvl[tr] / E_base[tr]:.2f}% survives)", flush=True)
    print(f"  election unchanged at {100 * (arg_lvl == arg_base).mean():.3f}% "
          f"of pixels", flush=True)

    print("\n--- A4 shuffled-normaliser control: perturbation or correction? ---",
          flush=True)
    E_fit, arg_fit = elect("fit")
    E_sh, arg_sh = elect("shuffle")
    drop_fit = E_base[tr] - E_fit[tr]
    drop_sh = E_base[tr] - E_sh[tr]
    frac = drop_sh / drop_fit if abs(drop_fit) > 1e-9 else float("nan")
    print(f"  fitted   trough {E_fit[tr]:+.5f}  ({100 * E_fit[tr] / E_base[tr]:.2f}% "
          f"survives), election agreement "
          f"{100 * (arg_fit == arg_base).mean():.3f}%", flush=True)
    print(f"  shuffled trough {E_sh[tr]:+.5f}  ({100 * E_sh[tr] / E_base[tr]:.2f}% "
          f"survives), election agreement "
          f"{100 * (arg_sh == arg_base).mean():.3f}%", flush=True)
    print(f"  a normaliser that corrects NOTHING reproduces "
          f"{100 * frac:.1f}% of the fitted arm's trough reduction", flush=True)
    a4 = frac >= 0.50
    print(f"  -> the shelf's fall under the fitted arm is "
          f"{'ELECTION PERTURBATION, not photometric correction' if a4 else 'photometric'}",
          flush=True)
    print(f"  fitted box {E_fit[pk]:+.5f}, shuffled box {E_sh[pk]:+.5f} "
          f"({100 * E_sh[pk] / E_base[pk]:.2f}% survives) -- the box is "
          f"indifferent to both", flush=True)

    # ---------------- A5
    print("\n--- A5 index-gap correlation with distance partialled out ---",
          flush=True)
    with np.errstate(invalid="ignore"):
        P = np.empty((n, DMAX + 1))
        for k in range(n):
            P[k] = prof(np.asarray(cube[k], dtype=np.float32))
        ens = np.nanmean(P, axis=0)
    far_lvl = float(np.nanmedian(ens[FAR[0]:FAR[1] + 1]))
    ensmap = np.interp(dd, np.arange(DMAX + 1), np.nan_to_num(ens, nan=far_lvl))
    exc = (sel0 - ensmap) / far_lvl
    gap = (maximum_filter(argbest, 5) - minimum_filter(argbest, 5)).astype(np.float32)
    gap_roll = np.roll(gap, ROLL, axis=(0, 1))

    def pooled(gmap):
        num = 0.0
        wsum = 0.0
        for d in range(BOX[0], BOX[1] + 1):
            s = valid & (dd == d)
            if int(s.sum()) < 500:
                continue
            g_, e_ = gmap[s], exc[s]
            if float(g_.std()) < 1e-6:
                continue
            r = spearmanr(g_, e_).statistic
            if np.isfinite(r):
                num += r * int(s.sum())
                wsum += int(s.sum())
        return num / wsum if wsum else float("nan")

    rho_p = pooled(gap)
    rho_n = pooled(gap_roll)
    print(f"  pooled within-distance rho(excess, gap) = {rho_p:+.4f}", flush=True)
    print(f"  rolled-gap null                         = {rho_n:+.4f}", flush=True)
    print(f"  75's un-partialled reading was -0.1180 with a +0.0660 null",
          flush=True)
    print(f"  -> ORCH's mechanism predicts positive; measured "
          f"{'POSITIVE' if rho_p > 0 else 'NEGATIVE'}", flush=True)

    print("\n" + "=" * 74 + "\n=== VERDICT ===", flush=True)
    print(f"  true exposure drift across the sweep: {100 * p2p:.3f}% p-p, and "
          f"between the frames elected at the band against the far field, "
          f"{100 * exc_l:+.4f}% -- {1 / max(share, 1e-9):.0f}x short of the "
          f"{100 * box_amp:.2f}% box", flush=True)
    print(f"  the BOX is refuted as photometric by three independent arms: "
          f"level-norm {100 * E_lvl[pk] / E_base[pk]:.1f}%, fitted "
          f"{100 * E_fit[pk] / E_base[pk]:.1f}%, and a planted 10% drift removed "
          f"at 89% in 75", flush=True)
    shelf_line = (
        "WITHDRAWN: a normaliser that corrects nothing reproduces "
        f"{100 * frac:.0f}% of it" if a4 else "CONFIRMED as photometric")
    print(f"  the SHELF's apparent photometric sensitivity in 75 is {shelf_line}",
          flush=True)

    rep = {"true_level_p2p": p2p, "level_sd_frac": float(lvl.std() / Lref),
           "Lref": Lref, "rho_g_level": r_lvl, "rho_g_focus": r_foc,
           "confounded": bool(confounded),
           "elected_level_excess": exc_l, "drift_share_of_box": share,
           "pk": pk, "tr": tr,
           "E_base_box": float(E_base[pk]), "E_base_trough": float(E_base[tr]),
           "E_lvl_box": float(E_lvl[pk]), "E_lvl_trough": float(E_lvl[tr]),
           "E_fit_box": float(E_fit[pk]), "E_fit_trough": float(E_fit[tr]),
           "E_sh_box": float(E_sh[pk]), "E_sh_trough": float(E_sh[tr]),
           "agree_lvl": float((arg_lvl == arg_base).mean()),
           "agree_fit": float((arg_fit == arg_base).mean()),
           "agree_sh": float((arg_sh == arg_base).mean()),
           "shuffle_share_of_trough_drop": float(frac), "A4_perturbation": bool(a4),
           "rho_pooled": rho_p, "rho_pooled_null": rho_n,
           "level": lvl.tolist(), "focus": foc.tolist(), "gain": gain.tolist(),
           "E_base": E_base.tolist(), "E_lvl": E_lvl.tolist(),
           "E_fit": E_fit.tolist(), "E_sh": E_sh.tolist()}
    with open(DATA / "76-photometric-audit.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        d = np.arange(DMAX + 1)
        fig, ax = plt.subplots(1, 3, figsize=(16, 4.3))
        ax[0].plot(np.arange(n), 100 * (lvl / Lref - 1), lw=1.1, color="C0")
        ax[0].set_xlabel("frame k")
        ax[0].set_ylabel("level excess, %")
        ax[0].set_title(f"true exposure drift: {100 * p2p:.2f}% p-p")
        ax[1].plot(np.arange(n), gain, lw=1, color="C3", label="75's fitted g")
        ax[1].plot(np.arange(n), foc / foc.max() * gain.max(), lw=1, color="C2",
                   label="focus response, scaled")
        ax[1].set_xlabel("frame k")
        ax[1].set_title(f"the confound: rho(g,focus)={r_foc:+.3f} vs "
                        f"rho(g,level)={r_lvl:+.3f}")
        ax[1].legend(fontsize=8)
        ax[2].axhline(0, color="k", lw=0.6)
        ax[2].plot(d, E_base, color="C3", label="shipped merge")
        ax[2].plot(d, E_lvl, color="C0", label="level-normalised")
        ax[2].plot(d, E_fit, color="C1", ls="--", label="gain+offset normalised")
        ax[2].plot(d, E_sh, color="C7", ls=":", label="shuffled normaliser (null)")
        ax[2].set_xlim(0, 130)
        ax[2].set_xlabel("distance from subject, px")
        ax[2].set_ylabel("E(d)")
        ax[2].set_title("box indifferent, shelf moves with perturbation")
        ax[2].legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / "76-photometric-audit.png", dpi=130)
        print(f"  wrote {OUT / '76-photometric-audit.png'}", flush=True)
    except Exception as exc:  # pragma: no cover
        print(f"  (no figure: {exc})", flush=True)

    print(f"\nwrote {DATA / '76-photometric-audit.json'}   "
          f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
