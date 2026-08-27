"""OCCLUSION RIMS, free field: strehl vs enfuse vs focus-stack.

THE HEADLINE IS AN INSTRUMENT LINEAGE, NOT AN ARM RESULT.  Five rim gauges
failed before the one used here, and three of those failures happened on THIS
corpus while this file was being written.  They are re-run below rather than
cited, so the lineage is measured in one pass:

    v3  (V-HEADTOHEAD/rimcmp.py, passed on `coffee-bean`)  -- stage 1
    v4  (rimv4.py, minimum-step gate)                      -- stage 2
    v5  (rimv5.py, shoulder-flatness gate)                 -- stage 2
    v6  (rimv6.py, select on a rim-free reference)         -- stages 3, 4

WHY THESE ARMS.  Every arm is fused from strehl's OWN `--linear-srgb
--demosaic` TIFFs -- paths come from V-NOISE2/hd2.py rather than being restated
here -- so demosaic and white balance are identical on every side and the only
remaining difference is the stacking algorithm.  V-HEADTOHEAD could not say
that: it fed the comparators Lightroom TIFFs and strehl raw.

TWO CONFOUNDS V-HEADTOHEAD CARRIED AND THIS DOES NOT.
  * RESAMPLING.  Its sec.4 measured that a Catmull-Rom upscale ALONE
    manufactures a +19.05% bright rim.  No arm here is resampled; geometry
    selects integer windows only.  The scale arm is still run, to show the
    hazard is live and that this comparison sits outside it.
  * TONE.  All three arms are linear and near-matched in exposure (recon.py:
    mean luma agrees to 7% on 113 and 1.2% on 119), and the statistic is
    normalised by each edge's OWN step, which cancels a smooth curve to first
    order.

THE CONTROL THAT DECIDES THIS MEASUREMENT.  rimv6's self-test shows noise
ALONE, on a synthetic image with no rim, reading +0.642% / +1.816% / +3.728% at
sigma 0.002 / 0.005 / 0.010.  V-NOISE2 measured the comparators noisier than
strehl by 1.54x-3.54x, so the instrument's bias runs TOWARD finding rims in the
comparators -- toward the answer this project wants.  Every comparator is
therefore matched by a noise ladder raising strehl to THAT comparator's
measured sigma, and no arm gap is claimed unless it clears its own ladder.

NOISE IS SIZED ON FLAT TILES.  An earlier form of this file sized the ladder
from a high-pass residual over DETAIL ROIs and got strehl noisier than both
comparators -- the opposite of V-NOISE2.  On detail tiles that residual is
dominated by resolved texture, so it is a sharpness proxy wearing a noise
label, and the ladder it sized added no noise at all.

AND AN IMPROVEMENT ARM.  A defect-only suite cannot separate a statistic that
is BLIND to a rim from one that is PERVERSE on it; this project shipped a
sharpness statistic bounded below by zero that could never charge for a halo.
A de-rimmed image must therefore score strictly BELOW the image it came from.

INVOCATION (rule 47).  Reads the arm files named by V-NOISE2/hd2.py.  Writes
C:\\dev\\strehl-out\\V-H2H2\\rimclip\\rim-<key>.json and prints everything.

    python rim.py [113|119 ...]
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD"))
import ffarms                                                    # noqa: E402
import rimv5                                                     # noqa: E402
import rimv6                                                     # noqa: E402
from rimcmp import rim_stats                                     # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\rimclip"
T = 256
ZONE = "bright t=+2..+7 px, dark t=-7..-2 px from edge centre"


def hp_std(a):
    return float((a - ndimage.uniform_filter(a, 9))[8:-8, 8:-8].std())


def flat_tiles(g, rois, t, keep=0.25):
    """The quietest quarter of the ROI set, by high-pass residual.

    V-NOISE2's principle: noise is measured where there is no detail.  On
    DETAIL tiles a high-pass residual is dominated by resolved texture and a
    sharper arm reads NOISIER, which is how an earlier form of this file
    produced a ladder that added no noise.
    """
    v = np.array([hp_std(g[y:y + t, x:x + t]) for (y, x) in rois])
    k = max(int(len(rois) * keep), 8)
    return [rois[i] for i in np.argsort(v)[:k]]


def sigma_on(g, tiles, t):
    return float(np.median([hp_std(g[y:y + t, x:x + t]) for (y, x) in tiles]))


def line(tag, r, ci=None):
    if r is None:
        print(f"  {tag:<44} NONE -- too few edges")
        return None
    s = f"  {tag:<44} n={r['n']:>6}  bright {r['bright']*100:+7.3f}%"
    if ci:
        s += f" [{ci[0]*100:+6.3f},{ci[1]*100:+6.3f}]"
    s += f"  dark {r['dark']*100:+7.3f}%"
    if ci:
        s += f" [{ci[2]*100:+6.3f},{ci[3]*100:+6.3f}]"
    print(s)
    out = dict(r)
    if ci:
        out["ci"] = list(ci)
    return out


def stage1(arms, rois):
    print("=" * 108)
    print("STAGE 1 -- IS THE INHERITED INSTRUMENT (v3) ADMISSIBLE HERE?")
    print("  v3 passed its controls on `coffee-bean`.  Whether it transfers to")
    print("  a dark linear macro render must be measured, not assumed.")
    print("=" * 108)
    v3 = {}
    for k in ffarms.KEYS:
        a = arms[k]
        real = rim_stats(a.g, a.clip, rois[k], a.tsize(T))
        ctrl = ndimage.gaussian_filter(a.g, 3.0).astype(np.float32)
        clean = rim_stats(ctrl, a.clip, rois[k], a.tsize(T))
        del ctrl
        print(f"\n  ARM {k}  ({a.label})")
        print(f"    v3, arm as-is                bright {real[0]*100:+8.3f}%"
              f"   dark {real[1]*100:+8.3f}%   n={real[2]}")
        print(f"    v3, SAME image SMOOTHED      bright {clean[0]*100:+8.3f}%"
              f"   dark {clean[1]*100:+8.3f}%   n={clean[2]}")
        v3[k] = dict(real_bright=float(real[0]), real_dark=float(real[1]),
                     clean_bright=float(clean[0]), clean_dark=float(clean[1]),
                     admissible=bool(abs(clean[0]) <= 0.02))
    print("\n  A smoothed raster has no rim by construction.  A reading well")
    print("  above zero on those rows is the instrument, not the image.")
    ok = all(v["admissible"] for v in v3.values())
    print(f"  v3 ADMISSIBLE ON THIS CORPUS: {ok}")
    return v3, ok


def stage2(ref, rois_ref, sigma):
    """Reproduce v4's and v5's failures from this subject's own control, then
    choose v6's selection cut on it."""
    print(f"\n{'='*108}")
    print("STAGE 2 -- WHY v4 AND v5 ARE NOT USED, MEASURED ON THIS SUBJECT")
    print("=" * 108)

    ctrl = ndimage.gaussian_filter(ref.g, 3.0).astype(np.float32)
    ec = rimv5.edges(ctrl, ref.clip, rois_ref, ref.tsize(T))
    del ctrl

    print("\n  v4's axis -- MINIMUM STEP, at v3's flatness of 0.20*step.")
    print("  Swept to 40x the image's own high-pass sigma, a RIM-FREE control")
    print("  still reads well above zero.  v4 refused to report.")
    v4tab = []
    for xs in (0, 10, 20, 30, 40):
        r = rimv5.gated(ec, 0.20, xs * sigma)
        v4tab.append((float(xs), None if r is None else r["bright"],
                      0 if r is None else r["n"]))
        b = "  NONE" if r is None else f"{r['bright']*100:+8.3f}%"
        print(f"    min step {xs:>3.0f}x sigma = {xs*sigma:.6f}   "
              f"control bright {b}   n={0 if r is None else r['n']:>6}")

    print("\n  v5's axis -- SHOULDER FLATNESS as a GATE applied at measurement")
    print("  time.  It drives the control to its null, and it also removes the")
    print("  defect it exists to find, because a rim IS shoulder structure:")
    v5tab = []
    for amt, rad in ((0.40, 1.0), (1.00, 2.0), (2.00, 2.0)):
        u = np.clip(ref.g + amt * (ref.g - ndimage.gaussian_filter(ref.g, rad)),
                    0, None).astype(np.float32)
        eu = rimv5.edges(u, ref.clip, rois_ref, ref.tsize(T))
        r = rimv5.gated(eu, 0.04)
        v5tab.append((f"USM({int(amt*100)},r={rad})",
                      None if r is None else r["bright"],
                      0 if r is None else r["n"]))
        b = "NONE -- gated out" if r is None else \
            f"{r['bright']*100:+8.3f}%  n={r['n']}"
        print(f"    v5 gate 0.04 on USM({int(amt*100)}, r={rad}):  {b}")
        del u, eu
    print("  An admissibility criterion correlated with the measurand is not")
    print("  an admissibility criterion.  That is why selection moved off the")
    print("  arm and onto a rim-free reference in v6.")

    print("\n  v6 -- SELECTION CUT, chosen on the rim-free control against its")
    print("  own STRUCTURAL NULL (a monotone edge of finite width reads")
    print("  negative by construction, so zero is the wrong null).")
    cut, table, fl = rimv6.choose_cut(ref.g, ref.clip, rois_ref, ref.tsize(T))
    print(f"    {'cut':>6} {'ctl bright':>12} {'ctl dark':>10} {'w':>5} "
          f"{'n':>7} {'resid b':>9} {'resid d':>9}")
    for c, b, d, n, w, rb, rd in table:
        if b is None:
            print(f"    {c:>6.2f}         NONE")
            continue
        print(f"    {c:>6.2f} {b*100:>11.3f}% {d*100:>9.3f}% {w:>5.1f} "
              f"{n:>7} {rb*100:>8.3f}% {rd*100:>8.3f}%")
    if cut is None:
        raise SystemExit("NO cut leaves enough edges -- refusing to report")
    print(f"\n  CUT = {cut:.2f}, MINIMISING the control's departure from its")
    print("  structural null.  No tolerance is chosen, so there is no")
    print("  tolerance to choose favourably.")
    print(f"  INSTRUMENT FLOOR: bright {fl['bright_residual']*100:+.3f}%   "
          f"dark {fl['dark_residual']*100:+.3f}%   on {fl['n']} edges")
    print("  No arm difference smaller than the floor is claimed below.")
    return cut, table, v4tab, v5tab, fl


def commission(g, sel, t, sigma, rng, ladder, label):
    """Every arm below is measured at the SAME pre-selected pixels as the real
    comparison, so a difference between rows is a difference in the image and
    not in what was sampled.  Returns (dict, all_passed)."""
    out, ok = {}, True

    def M(img):
        return rimv6.measure(img, sel, t)

    base_e = M(g)
    base_r = rimv6.stats(base_e)
    base = base_r["bright"]
    print(f"  {'THIS ARM, unmodified':<44} n={base_r['n']:>6}  "
          f"bright {base*100:+7.3f}%  dark {base_r['dark']*100:+7.3f}%")
    out["base"] = dict(base_r)

    print("\n  -- NULL: the arm against a byte-identical clone")
    b = rimv6.stats(M(g.copy()))
    out["null"] = line("clone", b)
    same = b is not None and b["bright"] == base and b["n"] == base_r["n"]
    print(f"     identical: {same}")
    ok &= bool(same)

    print("\n  -- NEGATIVE CONTROL: a rim-free image must score its null")
    ctrl = ndimage.gaussian_filter(g, 3.0).astype(np.float32)
    ec = M(ctrl)
    r = rimv6.stats(ec)
    out["clean"] = line("smoothed (no rim by construction)", r)
    w = rimv6.edge_width(ec)
    nn = rimv6.try_null(w) if w else None
    if nn is None:
        lo_w, hi_w = rimv6.null_range()
        print(f"     width {w if w else float('nan'):.1f} px is OUTSIDE the "
              f"null table's covered range [{lo_w:.2f}, {hi_w:.2f}] px.")
        print("     No null exists for this edge population, so no residual")
        print("     can be formed and this arm is NOT commissioned.  Reported")
        print("     rather than clamped: np.interp would have answered with")
        print("     the endpoint value for a width it never evaluated.")
        out["clean_out_of_domain"] = True
        ok = False
    else:
        nb, nd, _ = nn
        resid = None if r is None else r["bright"] - nb
        print(f"     width {w:.1f} px, structural null {nb*100:+.3f}% "
              f"=> residual {resid*100:+.3f}%")
        clean_ok = resid is not None and abs(resid) <= 0.03
        print(f"     residual within +/-3.0%: {clean_ok}")
        ok &= bool(clean_ok)

    print("\n  -- NEGATIVE CONTROL + NOISE: noise alone must not create a rim")
    for m in (1.0, 2.0):
        n = (ctrl + rng.normal(0.0, sigma * m, ctrl.shape)).astype(np.float32)
        out[f"clean_noise{m}"] = line(f"smoothed + noise {m:.1f}x arm sigma",
                                      rimv6.stats(M(n)))
        del n
    del ctrl

    print("\n  -- DEGRADATION LADDER: unsharp mask, rising strength")
    print("     v3's admissibility rule (RULE 20), inherited.  n must NOT fall")
    print("     as the rim grows -- that fall is what condemned v5.")
    lad = []
    for amt, rad in ((0.40, 1.0), (1.00, 2.0), (2.00, 2.0)):
        u = np.clip(g + amt * (g - ndimage.gaussian_filter(g, rad)),
                    0, None).astype(np.float32)
        r3 = rimv6.stats(M(u))
        lad.append(None if r3 is None else r3["bright"])
        out[f"usm{int(amt*100)}r{rad}"] = line(f"USM({int(amt*100)}, r={rad})",
                                              r3)
        del u
    strong = [v for v in lad if v is not None]
    rose = len(strong) == 3 and all(
        strong[i] < strong[i + 1] for i in range(2)) and strong[0] > base
    print(f"     monotone in USM strength AND above the arm "
          f"({base*100:+.3f}%): {rose}")
    ok &= rose

    print("\n  -- IMPROVEMENT: a de-rimmed image must score STRICTLY BELOW")
    print("     Without this arm a statistic BLIND to rims passes every line")
    print("     above.  A rim is planted, then removed; the removal must be")
    print("     scored as an improvement, not merely ignored.")
    hi = np.clip(g + 1.00 * (g - ndimage.gaussian_filter(g, 2.0)),
                 0, None).astype(np.float32)
    r_hi = rimv6.stats(M(hi))
    fx = ndimage.gaussian_filter(hi, 1.2).astype(np.float32)
    r_fx = rimv6.stats(M(fx))
    out["improve_from"] = line("rimmed (USM 100, r=2.0)", r_hi)
    out["improve_to"] = line("de-rimmed (the same image)", r_fx)
    improved = (r_hi is not None and r_fx is not None
                and r_fx["bright"] < r_hi["bright"])
    print(f"     de-rimming scored as an improvement: {improved}")
    ok &= bool(improved)
    del hi, fx

    print("\n  -- SCALE CONFOUND: resampling ALONE moves this statistic")
    print("     V-HEADTOHEAD sec.4 measured +19.05% from a Catmull-Rom upscale")
    print("     and no arm here is resampled, so this is reported to show the")
    print("     hazard is live.  It is a DIAGNOSTIC, not a pass/fail: rimv6's")
    print("     self-test 4 shows the sign depends on the source's own")
    print("     sharpness (+1.410% sharp, +0.030% as-is, -0.323% blurred),")
    print("     because a resample both adds ringing and removes resolution.")
    h, w2 = g.shape
    up = ndimage.zoom(g[:h - h % 2, :w2 - w2 % 2][::2, ::2], 2.0,
                      order=3).astype(np.float32)
    up = np.pad(up, ((0, max(0, h - up.shape[0])),
                     (0, max(0, w2 - up.shape[1]))), mode="edge")[:h, :w2]
    r_up = rimv6.stats(M(up))
    out["scale"] = line("downsample + cubic upsample", r_up)
    if r_up is not None:
        print(f"     moves this arm {(r_up['bright']-base)*100:+.3f}%")
    del up

    print("\n  -- NOISE LADDER: the decisive control")
    print(f"     arm sigma {sigma:.6f}, measured on FLAT tiles.  Noise")
    print("     inflates a max-based excursion, and V-NOISE2 measured the")
    print("     comparators noisier, so this bias runs toward the answer this")
    print("     project wants.  Each rung raises THIS arm to a named sigma.")
    noise = {}
    for tag, target in ladder:
        mult = target / sigma if sigma else 1.0
        add = sigma * float(np.sqrt(max(mult * mult - 1.0, 0.0)))
        n = (g + rng.normal(0.0, add, g.shape)).astype(np.float32)
        r_n = rimv6.stats(M(n))
        noise[tag] = line(f"raised to {tag} sigma {target:.6f} "
                          f"({mult:.2f}x, added {add:.6f})", r_n)
        del n
    out["noise"] = noise
    return out, ok


def run(key, rng):
    print("=" * 108)
    print(f"SUBJECT {key} = {ffarms.SUBJECTS[key]['name']}   "
          f"OCCLUSION RIM, free field")
    print(f"ZONE: {ZONE}   tile {T} px")
    print("=" * 108)

    arms = ffarms.build(key)
    ref = arms["strehl"]
    grid = ffarms.detail_grid(ref.g, T=T)
    print(f"  detail ROIs on the common grid: {len(grid)}")
    print("  The grid is computed ONCE on strehl and reused by every arm.")
    print("  Letting each arm pick its own detail tiles would compare")
    print("  different edge populations and call it an algorithm difference.")

    print("\n  -- GEOMETRY, measured not assumed (integer windows only)")
    offs = {}
    for k in ffarms.KEYS:
        a = arms[k]
        if k == "strehl":
            print(f"  {k:<10} scale 1.000000  offset ( +0, +0)  reference   "
                  f"{a.w}x{a.h} {a.bits}-bit")
            continue
        (dy, dx), pk, far = ffarms.measure_offset(ref.g, a.g, a.scale)
        offs[k] = (dy, dx)
        a.off = (dy, dx)
        print(f"  {k:<10} scale {a.scale:.6f}  offset ({dy:+3d},{dx:+3d})  "
              f"corr {pk:.4f} vs {far:.4f} at 24 px   {a.w}x{a.h} {a.bits}-bit")

    rois = {k: arms[k].rois_for(grid, T) for k in ffarms.KEYS}
    ftiles = {k: flat_tiles(arms[k].g, rois[k], arms[k].tsize(T))
              for k in ffarms.KEYS}
    sig = {k: sigma_on(arms[k].g, ftiles[k], arms[k].tsize(T))
           for k in ffarms.KEYS}
    dsig = {k: sigma_on(arms[k].g, rois[k], arms[k].tsize(T))
            for k in ffarms.KEYS}
    print("\n  sigma on FLAT tiles (what sizes the ladder):   " +
          "  ".join(f"{k} {sig[k]:.6f}" for k in ffarms.KEYS))
    print("  sigma on DETAIL tiles (a SHARPNESS proxy, NOT noise): " +
          "  ".join(f"{k} {dsig[k]:.6f}" for k in ffarms.KEYS))
    print("  If those two disagree in ORDER, the detail figure is measuring")
    print("  resolved texture.  An earlier form of this file sized its ladder")
    print("  from the detail figure and added no noise at all.")

    v3, v3_ok = stage1(arms, rois)
    cut, gtab, v4tab, v5tab, fl = stage2(ref, rois["strehl"], sig["strehl"])

    print(f"\n{'='*108}")
    print("  NOISE ALONE, on a rim-free SYNTHETIC step: no texture, no scene.")
    print("=" * 108)
    nfl = {}
    for s in sorted({0.0, sig["strehl"], max(sig.values())}):
        r = rimv6.noise_floor(s)
        nfl[f"{s:.6f}"] = dict(bright=r["bright"], dark=r["dark"])
        print(f"  synthetic step, noise sigma {s:.6f}   "
              f"bright {r['bright']*100:+7.3f}%   dark {r['dark']*100:+7.3f}%")

    print(f"\n{'='*108}")
    print("STAGE 3 -- COMMISSIONING v6 ON THIS SUBJECT, per arm")
    print("  Re-run per arm rather than inherited: an instrument commissioned")
    print("  on one arm and applied to another is the defect this lane has")
    print("  now found six times in six lanes.")
    print("=" * 108)
    ladder = [(k, sig[k]) for k in ffarms.KEYS if k != "strehl"]
    sel, comm = {}, {}
    for k in ffarms.KEYS:
        a = arms[k]
        ctrl = ndimage.gaussian_filter(a.g, 3.0).astype(np.float32)
        sel[k] = rimv6.select(ctrl, a.clip, rois[k], a.tsize(T), cut)
        del ctrl
        print(f"\n{'-'*108}\nCOMMISSIONING ARM {k}   flat sigma {sig[k]:.6f}   "
              f"{len(sel[k])} edges selected on the rim-free reference")
        comm[k], ok = commission(a.g, sel[k], a.tsize(T), sig[k], rng,
                                 ladder, a.label)
        comm[k]["passed"] = bool(ok)
        comm[k]["n_selected"] = len(sel[k])
        print(f"\n  ARM {k} COMMISSIONING: {'PASS' if ok else 'FAIL'}")

    print(f"\n{'='*108}")
    print(f"STAGE 4 -- THE MEASUREMENT.  selection cut {cut:.2f}, {ZONE}")
    print("=" * 108)
    res, E, widths = {}, {}, {}
    for k in ffarms.KEYS:
        a = arms[k]
        E[k] = rimv6.measure(a.g, sel[k], a.tsize(T))
        res[k] = line(f"{k}  ({a.label})", rimv6.stats(E[k]),
                      rimv6.boot_ci(E[k]))
        widths[k] = rimv6.edge_width(E[k])

    print("\n  EDGE WIDTHS of the measured edges, 10-90 in px, from the central")
    print("  slope of the median profile.  The structural null is STEEP in")
    print("  width, so it is not assumed to cancel: each arm is corrected by")
    print("  the null at its OWN width, and the residual difference between")
    print("  those nulls is carried into the bar below as a systematic term.")
    nulls = {}
    for k in ffarms.KEYS:
        nn = rimv6.try_null(widths[k]) if widths[k] else None
        if nn is None:
            lo_w, hi_w = rimv6.null_range()
            nulls[k] = None
            print(f"  {k:<12} width {widths[k]:>5.2f} px   OUTSIDE the null "
                  f"table's range [{lo_w:.2f}, {hi_w:.2f}] px -- NO CORRECTED "
                  f"VALUE")
            continue
        nb, nd, _ = nn
        nulls[k] = (nb, nd)
        print(f"  {k:<12} width {widths[k]:>5.2f} px   null bright "
              f"{nb*100:+7.3f}% dark {nd*100:+7.3f}%   => corrected "
              f"bright {(res[k]['bright']-nb)*100:+7.3f}% "
              f"dark {(res[k]['dark']-nd)*100:+7.3f}%")
    wv = [w for w in widths.values() if w]
    same_w = bool(wv) and (max(wv) - min(wv) <= 0.5)
    print(f"  widths within 0.5 px of each other: {same_w}")

    print("\n  ARM DIFFERENCES, comparator MINUS strehl, BOTH axes.")
    print("  Positive bright means the comparator OVERSHOOTS more.  Positive")
    print("  dark means the comparator UNDERSHOOTS more; a negative dark is an")
    print("  edge that never dips below its own dark plateau, which is the")
    print("  good direction.  Both axes are reported because on this subject")
    print("  they do not agree, and reporting only the axis an author expected")
    print("  to move is the same defect as a one-directional gate.")
    print("  The interval is unpaired: the arms have their own selections,")
    print("  because a 1.005x scale drifts 1.3 px across a 256 px tile and")
    print("  correcting it would mean resampling, which adds blur to the very")
    print("  quantity being measured.")
    diffs = {}
    for k in ffarms.KEYS:
        if k == "strehl":
            continue
        dd = rimv6.boot_diff(E[k], E["strehl"])
        if dd is None:
            print(f"  {k:<12} NONE")
            continue
        sl = comm["strehl"]["noise"].get(k)
        rec = {}
        print(f"  {k}")
        if nulls.get(k) is None or nulls.get("strehl") is None:
            print("    NO NULL for one of these arms -- its edge width is")
            print("    outside the null table's covered range.  A difference")
            print("    cannot be null-corrected and is NOT reported.")
            diffs[k] = dict(out_of_domain=True)
            continue
        for ax, ai in (("bright", 0), ("dark", 1)):
            d = dd[ax]
            sb = res["strehl"][ax]
            lad = 0.0 if sl is None else abs(sl[ax] - sb)
            floor_a = abs(fl["bright_residual"] if ax == "bright"
                          else fl["dark_residual"])
            dnull = abs(nulls[k][ai] - nulls["strehl"][ai])
            bar = max(lad, floor_a, dnull)
            corrected = ((res[k][ax] - nulls[k][ai])
                         - (sb - nulls["strehl"][ai]))
            surv = bool(d[1] > bar or d[2] < -bar)
            who = ("comparator worse" if d[0] > 0 else "STREHL WORSE")
            print(f"    {ax:<7} raw {d[0]*100:+7.3f}%  [{d[1]*100:+7.3f}, "
                  f"{d[2]*100:+7.3f}]   null-corrected {corrected*100:+7.3f}%")
            print(f"    {'':<7} bar = max(ladder {lad*100:.3f}%, floor "
                  f"{floor_a*100:.3f}%, null gap {dnull*100:.3f}%) "
                  f"= {bar*100:.3f}%   => "
                  f"{'RESOLVED, ' + who if surv else 'UNRESOLVED'}")
            rec[ax] = dict(diff=d[0], lo=d[1], hi=d[2],
                           corrected=float(corrected), ladder_move=float(lad),
                           floor=float(floor_a), null_gap=float(dnull),
                           bar=float(bar), resolved=surv,
                           strehl_worse=bool(surv and d[0] < 0))
        diffs[k] = rec

    all_pass = all(comm[k]["passed"] for k in ffarms.KEYS)
    print(f"\n  ALL ARMS COMMISSIONED: {all_pass}")
    if not all_pass:
        print("  The table above is NOT a result while any arm is "
              "uncommissioned.")

    payload = dict(key=key, subject=ffarms.SUBJECTS[key], n_rois=len(grid),
                   zone=ZONE, offsets=offs, sigma_flat=sig, sigma_detail=dsig,
                   cut=cut, cut_table=gtab, v4_step_table=v4tab,
                   v5_usm_table=v5tab, noise_floor=nfl, instrument_floor=fl,
                   widths=widths, widths_match=same_w, nulls=nulls, v3=v3,
                   v3_admissible=bool(v3_ok), measured=res, diffs=diffs,
                   commissioning=comm, all_pass=bool(all_pass),
                   scales={k: arms[k].scale for k in ffarms.KEYS},
                   bits={k: arms[k].bits for k in ffarms.KEYS})
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"rim-{key}.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print(f"\n  wrote {os.path.join(OUT, f'rim-{key}.json')}")
    return payload


def main(argv):
    keys = [a for a in argv if a in ffarms.SUBJECTS] or ["113", "119"]
    rng = np.random.default_rng(31)
    for k in keys:
        run(k, rng)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
