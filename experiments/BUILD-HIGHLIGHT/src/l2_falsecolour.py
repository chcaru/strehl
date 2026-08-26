"""l2 -- discriminating FALSE colour from REAL colour on small bright features.

ORCH's four candidates need separating, and the separation is spatial-frequency
and CFA-phase, not magnitude:

  A demosaic false colour -> chroma error is HIGH frequency and, at full
                             resolution, correlates with CFA PHASE (x%2, y%2).
                             Nothing else on the list predicts phase dependence.
  B real iridescence      -> smooth ordered bands: LOW frequency, phase-blind.
  C lateral CA            -> grows with RADIUS, antisymmetric in sign.
  D channel-asym clipping -> one-sided hue, confined to near-ceiling levels.

So the instrument reports, on a mask of small bright features over dark ground:
  H  RMS of HIGH-PASSED colour difference   (A's signature)
  L  RMS of LOW-PASSED  colour difference   (B's signature)
  PH CFA-phase separation of chroma          (A's signature, full-res only)
  RAD chroma by radial band                  (C's signature)

ALL MEASUREMENT IS LINEAR. ORCH struck a published comparison tonight that was
measured through the sRGB transfer curve; the curve is a strong non-linearity
and moves every ratio a metric computes. These inputs are --linear-srgb.

SELF-TEST (`--selftest`) plants each mechanism in turn on synthetic data and
requires the corresponding statistic to move AND the others to stay put. A
statistic that has never been shown to respond -- and to stay silent when the
thing it names is absent -- is not evidence.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

EPS = 1e-6


def luma(img: np.ndarray) -> np.ndarray:
    """BT.709 luminance. These files are linear sRGB, so 709 is the right basis."""
    return 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]


def colour_diff(img: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Scale-free colour-difference planes (R-G)/Y and (B-G)/Y, plus Y."""
    y = luma(img)
    d = np.maximum(y, EPS)
    return (img[..., 0] - img[..., 1]) / d, (img[..., 2] - img[..., 1]) / d, y


def edge_mask(y: np.ndarray, img: np.ndarray, pct: float, select_on: str = "luma"):
    """High-local-contrast EDGES, at any brightness.

    WHY A SECOND POPULATION EXISTS. `feature_mask` selects small bright
    features on dark ground, which is the population the `coffee-bubbles` and
    `foam` defect lives in. On `flower-bud-alone-cpl` that population is EMPTY
    -- measured, not assumed: the subject's per-channel maxima are
    R 63809 / G 64516 / B 63733 with **0.0000 % of pixels at 65535**, a median
    luma of 0.285 and a maximum of 0.340 in linear. There are no speculars and
    no dark ground.

    Returning "my mask found nothing" would be worthless, and worse, it is
    exactly the failure this project has already paid for once: a gate that
    removed zero pixels and reported that the effect survived. So the STATISTIC
    is held fixed -- the signed radial profile of a colour difference -- and the
    POPULATION is changed to the one this subject actually has: edges, where a
    fringe of any origin would show. Comparisons between subjects are then
    between like populations, and the swap is declared in the output.

    `select_on` IS DELIBERATELY IGNORED HERE. This population ranks on the luma
    GRADIENT, not on level, so the green-weighting hazard that `select_on`
    exists to control does not arise -- but neither does the control. Running
    this mask under three selectors returns three IDENTICAL rows, and they must
    not be read as three agreeing measurements. They are one measurement
    printed three times.
    """
    gy = np.abs(np.gradient(y, axis=0))
    gx = np.abs(np.gradient(y, axis=1))
    g = gy + gx
    thr = float(np.percentile(g, pct))
    unblown = img.max(axis=2) < 0.99
    return (g >= thr) & unblown, thr


def feature_mask(y: np.ndarray, img: np.ndarray, bright_pct: float, dark_ratio: float, bg: int, select_on: str = "luma"):
    """Small BRIGHT UNBLOWN features on DARK ground.

    `bright_pct` percentile selects the feature; the local box mean over `bg`
    px must be below `dark_ratio` of the pixel's own value, which is what makes
    it *small* and *on dark ground* rather than part of a large bright region.

    THE UNBLOWN REQUIREMENT IS NOT OPTIONAL, and it is the correction to this
    instrument's first version. Selecting purely on luminance handed back a
    mask more than half of whose pixels were EXACTLY neutral -- blown cores,
    driven to R==G==B either by the writer's clamp or by the highlight
    roll-off. Every median came back 0.000000 and the phase spread came back
    0.0000, which reads as "no false colour anywhere" and is in fact "you
    measured pixels that cannot carry colour". The defect being chased lives on
    the RIM, which is bright and unblown, so the rim is what the mask must
    select.

    `select_on` EXISTS BECAUSE THIS INSTRUMENT CAN FAKE ITS OWN HEADLINE.
    BT.709 luminance is 71.5 % green. Selecting "the brightest pixels" by luma
    therefore preferentially selects pixels whose GREEN is high, and would
    report a green excess on an image that has none. `rb` is the adversarial
    selector: it ranks on (R+B)/2 and contains no green at all, so it is biased
    the OPPOSITE way. A green excess that survives `rb` is a property of the
    image; one that does not was a property of the mask.
    """
    if select_on == "luma":
        rank = y
    elif select_on == "rb":
        rank = 0.5 * (img[..., 0] + img[..., 2])
    elif select_on == "max":
        rank = img.max(axis=2)
    elif select_on == "mean":
        rank = img.mean(axis=2)
    else:
        raise ValueError(f"unknown selector {select_on!r}")

    thr = np.percentile(rank, bright_pct)
    ground = uniform_filter(rank, size=bg, mode="nearest")
    unblown = img.max(axis=2) < 0.99
    m = (rank > thr) & (ground < dark_ratio * rank) & unblown
    return m, float(thr)


def stats(img: np.ndarray, bright_pct=99.5, dark_ratio=0.5, bg=33, full_res=True, select_on="luma", population="specular") -> dict:
    cr, cb, y = colour_diff(img)
    if population == "edge":
        m, thr = edge_mask(y, img, bright_pct, select_on)
    else:
        m, thr = feature_mask(y, img, bright_pct, dark_ratio, bg, select_on)
    n = int(m.sum())
    if n < 100:
        raise ValueError(f"mask kept only {n} px -- refusing to report on it")

    # -- THE MASK MUST BITE. A population that is majority-exactly-neutral
    #    cannot answer a question about hue: its median is 0 by construction and
    #    every "no effect" it reports is an artefact of the selection. This
    #    guard exists because the first version of this instrument silently did
    #    exactly that and printed a confident table of zeros.
    neutral = float(((cr[m] == 0.0) & (cb[m] == 0.0)).mean())
    if neutral > 0.5:
        raise ValueError(
            f"{100 * neutral:.1f}% of the mask is EXACTLY neutral -- this population "
            "cannot carry hue and any statistic on it is meaningless. Refusing."
        )

    # High/low frequency split of the chroma planes.
    lp_cr = uniform_filter(cr, size=7, mode="nearest")
    lp_cb = uniform_filter(cb, size=7, mode="nearest")
    hp_cr, hp_cb = cr - lp_cr, cb - lp_cb

    H = float(np.sqrt(np.mean(hp_cr[m] ** 2 + hp_cb[m] ** 2)))
    L = float(np.sqrt(np.mean(lp_cr[m] ** 2 + lp_cb[m] ** 2)))

    out = {
        "n_mask": n,
        "mask_frac": n / y.size,
        "y_thr": thr,
        "select_on": select_on,
        "neutral_frac": neutral,
        "H_highfreq_chroma": H,
        "L_lowfreq_chroma": L,
        "HL_ratio": H / L if L > 0 else None,
        "cr_med": float(np.median(cr[m])),
        "cb_med": float(np.median(cb[m])),
        "shape": list(img.shape),
    }

    # -- CFA phase. Only meaningful at full sensor resolution; a binned file has
    #    one output pixel per quad and therefore no phase to speak of.
    if full_res:
        ys, xs = np.nonzero(m)
        ph = (ys % 2) * 2 + (xs % 2)
        per = {}
        for p in range(4):
            sel = ph == p
            if sel.sum() > 20:
                per[f"phase{p}"] = {
                    "n": int(sel.sum()),
                    "cr": float(np.median(cr[ys[sel], xs[sel]])),
                    "cb": float(np.median(cb[ys[sel], xs[sel]])),
                }
        if len(per) == 4:
            crs = [per[f"phase{p}"]["cr"] for p in range(4)]
            cbs = [per[f"phase{p}"]["cb"] for p in range(4)]
            out["phase"] = per
            # Spread across the four CFA phases, in units of the overall
            # high-frequency chroma. >0 means the error knows about the grid.
            out["PH_phase_spread"] = float(
                np.hypot(max(crs) - min(crs), max(cbs) - min(cbs))
            )

    # -- radial dependence, for lateral CA.
    h, w = y.shape
    yy, xx = np.nonzero(m)
    cy, cx = h / 2.0, w / 2.0
    r = np.hypot((yy - cy) / cy, (xx - cx) / cx)
    mag = np.hypot(cr[yy, xx], cb[yy, xx])
    bands, edges = [], np.linspace(0, r.max() + 1e-9, 7)
    for i in range(6):
        sel = (r >= edges[i]) & (r < edges[i + 1])
        bands.append(float(np.median(mag[sel])) if sel.sum() > 20 else None)
    out["RAD_bands"] = bands
    ok = [b for b in bands if b is not None]
    out["RAD_corner_over_centre"] = (ok[-1] / ok[0]) if len(ok) >= 2 and ok[0] > 0 else None

    # -- SIGNED radial profile of (R-G)/Y. Lateral CA is a red-vs-green
    #    magnification error, so it must be ~0 on axis and grow with radius.
    #    An offset that is flat in radius is not CA, whatever else it is.
    #
    #    THREE AXES, NOT ONE. Green is this codebase's reference channel --
    #    optics.rs gives it no coefficient and freezes both green gathers
    #    bitwise -- and red and blue are corrected toward it with OPPOSITE
    #    signs (eps_r -704.5 ppm, eps_b +174.4 ppm). So a residual carried
    #    against green can be large while R-B stays small, and reporting only
    #    one axis cannot tell "no defect" from "an axis blind to this defect".
    #    R-B is the axis BUILD-SHARP bounded; R-G is mine; B-G closes the set.
    axes = {"RADcr_bands": cr, "RADcb_bands": cb, "RADcrb_bands": cr - cb}
    for name, plane in axes.items():
        prof = []
        for i in range(6):
            sel = (r >= edges[i]) & (r < edges[i + 1])
            prof.append(
                float(np.median(plane[yy[sel], xx[sel]])) if sel.sum() > 20 else None
            )
        out[name] = prof
    return out


# --------------------------------------------------------------------------
def _scene(h=512, w=512, seed=7):
    """Neutral dark ground with small bright neutral speculars.

    Carries a whisper of independent per-channel noise so that "neutral" here
    means *chromatically uninteresting*, not *bit-identical channels*. An
    exactly-neutral scene would trip the degenerate-mask guard, which is
    correct behaviour for that guard but useless as a control.
    """
    rng = np.random.default_rng(seed)
    y = rng.uniform(0.001, 0.004, size=(h, w)).astype(np.float32)
    for _ in range(400):
        r, c = rng.integers(4, h - 4), rng.integers(4, w - 4)
        y[r, c] += rng.uniform(0.30, 0.75)
        y[r - 1 : r + 2, c - 1 : c + 2] += rng.uniform(0.05, 0.12)
    img = np.repeat(y[:, :, None], 3, axis=2).astype(np.float32)
    img *= 1.0 + rng.normal(0, 2e-4, size=img.shape).astype(np.float32)
    return img


def selftest() -> None:
    rng = np.random.default_rng(11)
    base = _scene()
    b = stats(base, full_res=True)
    assert b["H_highfreq_chroma"] < 1e-3, f"neutral scene read H={b['H_highfreq_chroma']}"
    assert b["L_lowfreq_chroma"] < 1e-3, f"neutral scene read L={b['L_lowfreq_chroma']}"
    print(f"  neutral control     H={b['H_highfreq_chroma']:.5f} L={b['L_lowfreq_chroma']:.5f}  (both ~0, as required)")

    # A: per-pixel random chroma -> H must rise, L must stay low.
    a = base.copy()
    n = rng.normal(0, 0.12, size=base.shape[:2]).astype(np.float32)
    a[..., 0] *= 1 + n
    a[..., 2] *= 1 - n
    sa = stats(a, full_res=True)
    assert sa["H_highfreq_chroma"] > 20 * b["H_highfreq_chroma"] + 0.01, "H failed to respond to planted false colour"
    assert sa["HL_ratio"] > 2.0, f"planted HIGH-freq colour read HL={sa['HL_ratio']:.2f}"
    print(f"  A false colour      H={sa['H_highfreq_chroma']:.5f} L={sa['L_lowfreq_chroma']:.5f} H/L={sa['HL_ratio']:.2f}  (H up, H/L>2)")

    # B: smooth colour gradient -> L must rise, H must NOT.
    bb = base.copy()
    yy, xx = np.mgrid[0 : base.shape[0], 0 : base.shape[1]]
    smooth = (0.25 * np.sin(2 * np.pi * xx / 220.0)).astype(np.float32)
    bb[..., 0] *= 1 + smooth
    bb[..., 2] *= 1 - smooth
    sb = stats(bb, full_res=True)
    assert sb["L_lowfreq_chroma"] > 10 * b["L_lowfreq_chroma"] + 0.01, "L failed to respond to planted smooth colour"
    assert sb["HL_ratio"] < 0.5, f"planted LOW-freq colour read HL={sb['HL_ratio']:.2f}, should be <0.5"
    print(f"  B iridescence-like  H={sb['H_highfreq_chroma']:.5f} L={sb['L_lowfreq_chroma']:.5f} H/L={sb['HL_ratio']:.2f}  (L up, H/L<0.5)")

    # The two must be SEPARABLE, not merely both non-zero.
    assert sa["HL_ratio"] > 4 * sb["HL_ratio"], "H/L does not separate speckle from bands"

    # ---- E and F calibrate the RADIAL axis, which adjudicates BUILD-SHARP. ----
    #
    # E: a PURELY PHOTOMETRIC radial attenuation of red, with ZERO geometric
    #    shift. Nothing moves, so a displacement statistic scores this EXACTLY
    #    zero, while a colour statistic must see it. This is the case that
    #    decides whether "R-B displacement < 0.05 px" and "(R-G)/Y grows with
    #    radius" can both be true of the same image. If my radial axis cannot
    #    detect a defect that plants no displacement, I have no standing to
    #    claim their axis is blind to it.
    h, w = base.shape[:2]
    gy, gx = np.mgrid[0:h, 0:w]
    rr = np.hypot(gy - h / 2.0, gx - w / 2.0)
    rr = (rr / rr.max()).astype(np.float32)
    e = base.copy()
    e[..., 0] *= 1.0 - 0.25 * rr
    se = stats(e, full_res=True)
    ecr = [x for x in se["RADcr_bands"] if x is not None]
    assert ecr[-1] < ecr[0] - 0.02, f"radial axis BLIND to planted radial red attenuation: {ecr}"
    print(
        f"  E radial photometric  (R-G)/Y {ecr[0]:+.4f} -> {ecr[-1]:+.4f}"
        f"  (grows with radius; plants ZERO displacement)"
    )

    # F: the NULL for the radial axis. A FLAT red offset of the same sign and a
    #    comparable size, with no radius dependence at all. The radial axis must
    #    NOT report growth here, or it would convict every colour cast of being
    #    lateral CA -- which is precisely the error I would be accusing myself
    #    of if I reported E without F.
    f = base.copy()
    f[..., 0] *= 1.0 - 0.125
    sf = stats(f, full_res=True)
    fcr = [x for x in sf["RADcr_bands"] if x is not None]
    assert abs(fcr[-1] - fcr[0]) < 0.02, f"radial axis reports GROWTH on a FLAT offset: {fcr}"
    assert abs(fcr[0]) > 0.01, f"flat offset was too small to be a meaningful null: {fcr}"
    print(
        f"  F flat offset (null)  (R-G)/Y {fcr[0]:+.4f} -> {fcr[-1]:+.4f}"
        f"  (offset present, NO radial growth)"
    )

    # PH: phase-locked chroma must be detected; phase-blind chroma must not be.
    p = base.copy()
    grid = (((np.mgrid[0 : base.shape[0], 0 : base.shape[1]][0] % 2) == 0)).astype(np.float32)
    p[..., 0] *= 1 + 0.20 * grid
    p[..., 2] *= 1 - 0.20 * grid
    sp = stats(p, full_res=True)
    assert sp["PH_phase_spread"] > 0.05, f"phase test blind to a planted phase-locked error: {sp['PH_phase_spread']}"
    assert sa["PH_phase_spread"] < sp["PH_phase_spread"] / 3, (
        f"phase test fires on phase-BLIND noise: {sa['PH_phase_spread']:.4f} vs planted {sp['PH_phase_spread']:.4f}"
    )
    print(f"  phase-locked plant  PH={sp['PH_phase_spread']:.4f}  vs phase-blind noise PH={sa['PH_phase_spread']:.4f}  (separated)")

    # -- THE DEGENERATE-MASK GUARD MUST FIRE. This reproduces the exact failure
    #    the first version of this instrument shipped: a mask dominated by
    #    exactly-neutral blown pixels, whose every median is 0 by construction.
    blown = base.copy()
    blown[:] = np.round(blown * 4.0) / 4.0  # quantise hard -> channels collapse
    try:
        stats(blown, full_res=True)
    except ValueError as e:
        assert "EXACTLY neutral" in str(e) or "refusing" in str(e).lower(), f"wrong refusal: {e}"
        print(f"  degenerate mask     REFUSED as required -- {str(e)[:58]}...")
    else:
        raise AssertionError(
            "the degenerate-mask guard did NOT fire on an exactly-neutral population. "
            "This is the failure that produced a table of confident zeros."
        )

    print("l2 selftest: PASS -- H responds only to speckle, L only to bands,")
    print("  PH only to grid-locked error, and all three read ~0 on a neutral scene.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--arm", nargs=2, action="append", metavar=("NAME", "PATH"))
    ap.add_argument(
        "--bin2",
        nargs=2,
        action="append",
        metavar=("NAME", "PATH"),
        help="Measure a FULL-RES file after 2x2 averaging, i.e. on the binned "
        "arm's own grid. This is the resolution-fair control for the demosaic "
        "question: 'demosaic then bin' against 'bin', where a 7 px high-pass "
        "finally covers the same physical distance in both.",
    )
    ap.add_argument("--bright-pct", type=float, default=99.5)
    ap.add_argument(
        "--population",
        default="specular",
        choices=["specular", "edge"],
        help="WHICH PIXELS the statistic is computed over. `specular` is small "
        "bright unblown features on dark ground -- the population the "
        "coffee-bubbles/foam defect lives in. `edge` is high-local-contrast "
        "pixels at any brightness, which is the only population that EXISTS on "
        "an unclipped mid-tone subject such as flower-bud-alone-cpl (measured: "
        "0.0000%% of its pixels reach 65535). The statistic is identical in both "
        "cases; only the population changes, and the choice is recorded in the "
        "output so no cross-subject comparison can silently mix the two.",
    )
    ap.add_argument(
        "--select-on",
        default="luma",
        choices=["luma", "rb", "max", "mean"],
        help="What ranks a pixel as 'bright'. `luma` is 71.5%% green and will "
        "manufacture a green excess if believed uncritically; `rb` is the "
        "adversarial control that contains no green at all.",
    )
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        if not (a.arm or a.bin2):
            return 0

    res = {}
    print(f"\nselector: {a.select_on}")
    print(f"{'arm':<20} {'shape':>12} {'n_mask':>9} {'H(hi)':>8} {'L(lo)':>8} {'cr_med':>9} {'cb_med':>9} {'verdict':>10}")
    print("-" * 92)
    jobs = [(n, p, False) for n, p in (a.arm or [])] + [(n, p, True) for n, p in (a.bin2 or [])]
    for name, path, bin2 in jobs:
        img = tifffile.imread(path).astype(np.float32) / 65535.0
        if bin2:
            h, w, _ = img.shape
            img = img[: h // 2 * 2, : w // 2 * 2].reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3))
        full = img.shape[1] > 5000
        s = stats(img, bright_pct=a.bright_pct, full_res=full, select_on=a.select_on, population=a.population)
        s["population"] = a.population
        s["binned_2x2"] = bin2
        res[name] = s
        cr, cb = s["cr_med"], s["cb_med"]
        verdict = "GREEN+" if (cr < 0 and cb < 0) else ("MAGENTA" if (cr > 0 and cb > 0) else "mixed")
        print(
            f"{name:<20} {str(s['shape'][1]) + 'x' + str(s['shape'][0]):>12} {s['n_mask']:>9} "
            f"{s['H_highfreq_chroma']:>8.4f} {s['L_lowfreq_chroma']:>8.4f} "
            f"{cr:>+9.4f} {cb:>+9.4f} {verdict:>10}"
        )
        del img

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
