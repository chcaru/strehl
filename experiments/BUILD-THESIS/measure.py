"""Estimation vs selection, measured on resolved detail at matched sites.

ONE BINARY renders both arms (see render_arms.ps1). This script never renders
anything; it only measures what that binary wrote.

THE FOUR RULES THIS OBEYS

1. ONE BINARY. Asserted here, not assumed: every arm's provenance sidecar must
   carry the same sha256 or this refuses to run.

2. NEVER ACROSS A TONE CURVE. Both arms are linear 16-bit camera RGB. Nothing
   in this file applies a transfer function. The .png crops it writes are
   marked "look only" and no statistic is ever computed from them.

3. GREEN PLANE ONLY. `stack` applies a lateral-CA correction and
   `argmax-baseline` does not. CA correction moves R and B radially against G;
   green is the reference channel and is untouched by it. Measuring green only
   removes that confound completely rather than arguing it is small. It is also
   the plane ORCH's instrument uses.

4. MATCHED SITES, CHOSEN BY NEITHER ARM. The two arms are NOT on the same
   sampling grid: `stack` aligns and then scales the field of view so every
   frame covers every pixel, and `argmax-baseline` does not align at all. So
   this registers them, builds the pixelwise MEAN of the two, and picks tiles
   on the mean. Neither arm gets to nominate the ground it is judged on.

   The tiles are then cut from each arm's OWN NATIVE PIXELS -- the registration
   is used to locate them, never to resample the thing being measured. The
   argmax tile is cut `s` times smaller so it spans the same scene content.

WHAT ELSE IS MEASURED, BECAUSE IT WOULD OTHERWISE BE ASSUMED

  argmax_geom  the argmax tile put through the SAME coverage rescale the merge
               arm paid: magnify by 1/s through a bicubic and back to size.
               The merge is handicapped by an interpolation the baseline never
               pays; this charges the baseline for it too, so the difference
               between the two comparisons is the price of coverage rather
               than a guess about it.

  sigma        Donoho's robust noise sigma per arm, on the flattest tile of the
               mean. S1 is known to RISE on noise (commission.py), so the arms'
               actual noise difference sets how much of any S1 gap is bias.

  S1 bias      measured directly: the merge tile with noise added until its
               sigma matches the argmax arm's. Whatever S1 moves by is what S1
               would report for a pure noise difference and no detail at all.
"""
import json
import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stats import STATS, noise_sigma  # noqa: E402

TILE = 800
NTILES = 6
MIN_MATCH = 0.50   # below this the two arms do not hold the same scene content
DS = 4          # registration downsample
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS")
RENDERS = OUT / "renders"
RNG = np.random.default_rng(11235)


# --------------------------------------------------------------- helpers

def green(path):
    img = tifffile.imread(str(path))
    assert img.dtype == np.uint16, f"{path}: {img.dtype}, expected uint16"
    assert img.ndim == 3 and img.shape[2] == 3, f"{path}: shape {img.shape}"
    return img[:, :, 1].astype(np.float64)


def fov_scale_from_log(p):
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf8", errors="replace").splitlines():
        if "field of view scaled to" in line:
            return float(line.split("field of view scaled to")[1].split()[0])
    return None


def _prep(g):
    s = cv2.resize(g.astype(np.float32), None, fx=1.0 / DS, fy=1.0 / DS,
                   interpolation=cv2.INTER_AREA)
    s = s - cv2.blur(s, (9, 9))          # kill illumination / gain differences
    return s / (s.std() + 1e-9)


def register(g_merge, g_argmax, s_hint):
    """Affine warp W with argmax_coord = W @ merge_coord, fitted by ECC.

    Fitted, not taken from the log: the log states the field-of-view scale but
    not the alignment translation, and a scale read off a log is a claim about
    what the code intended rather than a measurement of what it produced.
    """
    tm, ti = _prep(g_merge), _prep(g_argmax)
    h, w = tm.shape
    cy, cx = h / 2.0, w / 2.0
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 400, 1e-7)
    best = None
    seeds = [1.0]
    if s_hint:
        seeds += [s_hint, 1.0 / s_hint]
    for s0 in seeds:
        W = np.array([[s0, 0.0, cx * (1 - s0)],
                      [0.0, s0, cy * (1 - s0)]], dtype=np.float32)
        try:
            cc, W = cv2.findTransformECC(tm, ti, W, cv2.MOTION_AFFINE, crit, None, 5)
        except cv2.error:
            continue
        if best is None or cc > best[0]:
            best = (float(cc), W.copy())
    if best is None:
        raise RuntimeError("ECC registration failed on every seed")
    cc, W = best
    A = W.astype(np.float64).copy()
    A[:, 2] *= DS                                  # translations back to full res
    return cc, A


def apply_affine(A, x, y):
    return (A[0, 0] * x + A[0, 1] * y + A[0, 2],
            A[1, 0] * x + A[1, 1] * y + A[1, 2])


def pick_tiles(mean_img, tile, n, margin=80, second=None, rule="mean"):
    """Top-n non-overlapping tiles by |laplacian|, plus the flattest tile.

    rule="mean": score on the MEAN of the two arms, so neither arm chooses the
    ground on its own.

    rule="min": score on the pixelwise MINIMUM of the two arms' |laplacian|, so
    a site must carry detail in BOTH arms to be nominated. This exists because
    the mean rule has a demonstrated hazard: on flowers-cpl, `argmax-baseline`
    renders smooth out-of-focus ground as hard-edged patchwork, that patchwork
    is the highest-|laplacian| thing in a very low-contrast frame, and it
    therefore nominated sites that hold no real detail at all in either arm.
    The min rule cannot be led there by one arm's invented structure. It is
    still symmetric -- it favours neither arm -- and it is conservative,
    because it will also decline a site where one arm genuinely resolves
    something the other does not.
    """
    g = mean_img

    def lapf(a):
        return np.abs(4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1]
                      - a[1:-1, :-2] - a[1:-1, 2:])

    if rule == "min" and second is not None:
        score_field = np.minimum(lapf(second[0]), lapf(second[1]))
    else:
        score_field = lapf(g)
    h, w = g.shape
    lap = score_field
    step = tile // 2
    cands = []
    for y in range(margin, h - tile - margin, step):
        for x in range(margin, w - tile - margin, step):
            cands.append((float(lap[y:y + tile, x:x + tile].mean()), y, x))
    cands.sort(reverse=True)
    picked = []
    for sc, y, x in cands:
        if all(abs(y - py) >= tile or abs(x - px) >= tile for _, py, px in picked):
            picked.append((sc, y, x))
        if len(picked) >= n:
            break
    flat = min(cands)
    return [(y, x) for _, y, x in picked], (flat[1], flat[2])


def geom_handicap(t, s):
    """Magnify by 1/s through a bicubic and back to size: the merge's rescale.

    `stack` scales the field of view to s and then upsamples to the original
    output dimensions, with a CatmullRom resampler. OpenCV's INTER_CUBIC is a
    Keys bicubic with a = -0.75 against CatmullRom's a = -0.5, so this is an
    ESTIMATE of the cost and is labelled as one, not a reproduction of it.
    """
    h, w = t.shape
    ch, cw = int(round(h * s)), int(round(w * s))
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    sub = t[y0:y0 + ch, x0:x0 + cw]
    return cv2.resize(sub.astype(np.float32), (w, h),
                      interpolation=cv2.INTER_CUBIC).astype(np.float64)


SEARCH = 72


def locate(tm, ga, s, ax, ay, Ta):
    """Find the argmax tile that actually holds the same scene content.

    A single global affine cannot register these two arms, and that is a
    property of the BASELINE, not a limitation of this script. `stack` aligns
    every frame to one reference, so its output has one consistent geometry.
    `argmax-baseline` does not align at all, so each output pixel carries the
    geometry of whichever frame happened to win there; where the stack drifted,
    neighbouring regions of the argmax render sit on different grids. There is
    no global warp that matches all of it at once.

    So the global affine is used only to get within SEARCH pixels, and each
    tile is then located by normalised cross-correlation. The correlation runs
    on a RESAMPLED COPY of the merge tile; the pixels that are measured are cut
    from each arm's native grid at integer offsets and are never resampled.

    Returns (tile, score, x, y) or None if the site cannot be matched.
    """
    h, w = ga.shape
    y0 = int(np.clip(ay - SEARCH, 0, h - Ta - 2 * SEARCH))
    x0 = int(np.clip(ax - SEARCH, 0, w - Ta - 2 * SEARCH))
    reg = ga[y0:y0 + Ta + 2 * SEARCH, x0:x0 + Ta + 2 * SEARCH]
    if reg.shape[0] < Ta or reg.shape[1] < Ta:
        return None
    tpl = cv2.resize(tm.astype(np.float32), (Ta, Ta), interpolation=cv2.INTER_AREA)
    r = cv2.matchTemplate(reg.astype(np.float32), tpl, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(r)
    fx, fy = x0 + loc[0], y0 + loc[1]
    return ga[fy:fy + Ta, fx:fx + Ta], float(score), int(fx), int(fy)


def stretch_pair(a, b):
    """One shared display stretch for both arms. FOR LOOKING ONLY."""
    both = np.concatenate([a.ravel(), b.ravel()])
    lo, hi = np.percentile(both, 0.5), np.percentile(both, 99.7)
    def f(t):
        v = np.clip((t - lo) / max(hi - lo, 1e-9), 0, 1)
        return (np.power(v, 1 / 2.2) * 255).astype(np.uint8)
    return f(a), f(b)


# --------------------------------------------------------------- per subject

def measure(subject, rule="mean"):
    d = RENDERS / subject
    mp, ap = d / "merge.tif", d / "argmax.tif"
    if not (mp.exists() and ap.exists()):
        return None

    provs = [json.loads((d / f"{a}.provenance.json").read_text(encoding="utf8"))
             for a in ("merge", "argmax")]
    shas = {p["sha256"] for p in provs}
    assert len(shas) == 1, f"{subject}: arms came from different binaries: {shas}"
    sha = shas.pop()
    assert all(p["exit"] == 0 for p in provs), f"{subject}: an arm exited non-zero"

    gm, ga = green(mp), green(ap)
    assert gm.shape == ga.shape, f"{subject}: {gm.shape} vs {ga.shape}"

    hint = fov_scale_from_log(d / "merge.err")
    cc, A = register(gm, ga, hint)
    s = float(np.sqrt(abs(np.linalg.det(A[:, :2]))))

    # mean of both arms, in the merge frame, FOR SITE SELECTION ONLY
    h, w = gm.shape
    warped = cv2.warpAffine(ga.astype(np.float32), A, (w, h),
                            flags=cv2.WARP_INVERSE_MAP | cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REPLICATE).astype(np.float64)
    mean_img = 0.5 * (gm + warped)

    tiles, flat = pick_tiles(mean_img, TILE, NTILES, second=(gm, warped), rule=rule)
    Ta = int(round(TILE * s))

    # per-arm noise, on the flattest tile the MEAN nominates
    fy, fx = flat
    fax, fay = apply_affine(A, fx + TILE / 2, fy + TILE / 2)
    tm_flat = gm[fy:fy + TILE, fx:fx + TILE]
    loc = locate(tm_flat, ga, s, int(round(fax - Ta / 2)), int(round(fay - Ta / 2)), Ta)
    sig_m = noise_sigma(tm_flat)
    sig_a = noise_sigma(loc[0]) if loc else float("nan")

    rows = []
    crops = []
    dropped = 0
    for i, (y, x) in enumerate(tiles):
        axf, ayf = apply_affine(A, x + TILE / 2, y + TILE / 2)
        tm = gm[y:y + TILE, x:x + TILE]
        loc = locate(tm, ga, s, int(round(axf - Ta / 2)), int(round(ayf - Ta / 2)), Ta)
        if loc is None or loc[1] < MIN_MATCH:
            dropped += 1
            continue
        ta, score, ax, ay = loc
        tg = geom_handicap(ta, s)
        r = dict(subject=subject, tile=i, merge_xy=[x, y], argmax_xy=[ax, ay],
                 match=score, tile_px_merge=TILE, tile_px_argmax=Ta)
        for k, fn in STATS.items():
            vm, va, vg = fn(tm), fn(ta), fn(tg)
            r[f"{k}_merge"] = vm
            r[f"{k}_argmax"] = va
            r[f"{k}_argmax_geom"] = vg
            r[f"{k}_gain"] = vm / va if va else float("nan")
            r[f"{k}_gain_geom"] = vm / vg if vg else float("nan")
        rows.append(r)
        crops.append((i, tm, ta))

    # measured S1 noise bias: raise the merge tile's noise to the argmax arm's
    bias = {}
    if rows and sig_a > sig_m:
        add = float(np.sqrt(max(sig_a ** 2 - sig_m ** 2, 0.0)))
        y, x = rows[0]["merge_xy"][1], rows[0]["merge_xy"][0]
        tm = gm[y:y + TILE, x:x + TILE]
        tn = tm + RNG.normal(0.0, add, tm.shape)
        for k, fn in STATS.items():
            b = fn(tm)
            bias[k] = fn(tn) / b if b else float("nan")
        bias["_sigma_added_DN"] = add

    return dict(subject=subject, site_rule=rule, sha256=sha, ecc=cc, scale=s,
                fov_scale_logged=hint, shape=[int(h), int(w)],
                tiles_kept=len(rows), tiles_dropped_unmatchable=dropped,
                sigma_merge_DN=sig_m, sigma_argmax_DN=sig_a,
                sigma_ratio_argmax_over_merge=sig_a / max(sig_m, 1e-9),
                flat_tile_merge_xy=[fx, fy],
                s1_noise_bias_at_real_delta=bias,
                tiles=rows), crops


def write_crops(subject, crops, size=512, rule="mean"):
    cd = OUT / "crops" / (subject if rule == "mean" else f"{subject}-siteMIN")
    cd.mkdir(parents=True, exist_ok=True)
    for i, tm, ta in crops:
        # centre `size` px of each, native pixels, one shared stretch
        def ctr(t):
            h, w = t.shape
            y, x = (h - size) // 2, (w - size) // 2
            return t[y:y + size, x:x + size]
        a, b = stretch_pair(ctr(tm), ctr(ta))
        cv2.imwrite(str(cd / f"tile{i}-merge.png"), a)
        cv2.imwrite(str(cd / f"tile{i}-argmax.png"), b)
        pair = np.full((size, size * 2 + 8), 255, np.uint8)
        pair[:, :size] = a
        pair[:, size + 8:] = b
        cv2.imwrite(str(cd / f"tile{i}-SIDEBYSIDE-merge-left-argmax-right.png"), pair)


def main():
    rule = "mean"
    argv = list(sys.argv[1:])
    if argv and argv[0].startswith("--rule="):
        rule = argv.pop(0).split("=", 1)[1]
    subjects = argv
    if not subjects:
        subjects = sorted(p.name for p in RENDERS.iterdir() if p.is_dir())
    out = []
    for s in subjects:
        r = measure(s, rule)
        if r is None:
            print(f"skip {s}: missing an arm")
            continue
        res, crops = r
        write_crops(s, crops, rule=rule)
        out.append(res)
        print(f"\n=== {s}  (ECC {res['ecc']:.4f}, scale {res['scale']:.4f}, "
              f"logged FOV {res['fov_scale_logged']}, "
              f"tiles {res['tiles_kept']} kept / {res['tiles_dropped_unmatchable']} dropped, "
              f"sigma argmax/merge {res['sigma_ratio_argmax_over_merge']:.3f})")
        if not res["tiles"]:
            print("   NO MATCHABLE SITES")
            continue
        print(f"   median site match NCC "
              f"{np.median([t['match'] for t in res['tiles']]):.3f}")
        for k in STATS:
            g = [t[f"{k}_gain"] for t in res["tiles"]]
            gg = [t[f"{k}_gain_geom"] for t in res["tiles"]]
            print(f"   {k:<10} merge/argmax {np.median(g):6.3f}x  "
                  f"(range {min(g):.3f}-{max(g):.3f})   "
                  f"geometry-matched {np.median(gg):6.3f}x")
    (OUT / f"measure-{rule}.json").write_text(json.dumps(out, indent=1), encoding="utf8")
    print(f"\nwrote {OUT / f'measure-{rule}.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


