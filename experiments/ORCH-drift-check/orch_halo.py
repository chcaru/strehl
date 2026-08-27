"""Objective halo metric: the edge overshoot profile, with edge-attachment commissioned.

The user's judgement on the shipped masters was that the halo is "horrendous" and the
output "entirely unusable". That is the correct judgement and it is an eyeball one. Before
any lane claims to have fixed it, the project needs a number that (a) is comparable across
renders, so a fix can be shown to reduce it, and (b) was verified by someone other than the
author of the fix.

A focus-stack halo is an overshoot ring at an occluding edge: near a sharp foreground
boundary the background picks up a bright or dark band tens of pixels wide, because no
frame contains clean background there and the merge composites a veiled observation. So the
metric is the classic edge-overshoot profile, sampled perpendicular to strong boundaries:

  1. Heavily blur, take gradient magnitude -> object boundaries, not texture.
  2. At sampled edge points, walk the gradient normal +/- HALF px, bilinear.
  3. Normalise each profile to a 0->1 step using its two far ends.
  4. Average. Overshoot beyond [0,1] in the 8..HALF band IS the halo.

COMMISSIONING has three arms and, per SS92, only one of them varies amplitude:

  SYNTH   - a synthetic step with a KNOWN overshoot pushed through the identical profile
            machinery. Certifies the measurement chain end to end against ground truth.
  SHUFFLE - real masters, same edge detection, but profiles taken at random positions and
            random orientations. This breaks the structural property the claim rests on
            (that the excursion is ATTACHED to edges) while preserving every statistical
            property of the data. It is the control SS92 says an amplitude ladder cannot
            substitute for.
  NULL    - the real measurement.

A real halo must beat SHUFFLE. A number that does not is measuring the image, not the edge.
"""
import pathlib
import sys

import numpy as np
import tifffile

DS = 2
HALF = 100
BLUR = 9
EDGE_PCT = 99.5
MAX_PROFILES = 4000
BAND = (8, 90)
MIN_STEP_FRAC = 0.08
PLATEAU_FRAC = 0.18


def downsample(a, f):
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def boxblur(a, win):
    r = win // 2
    pad = np.pad(a, ((r, r), (r, r)), mode="edge")
    c = np.cumsum(np.cumsum(pad, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    s = (c[win:win + h, win:win + w] - c[0:h, win:win + w]
         - c[win:win + h, 0:w] + c[0:h, 0:w])
    return s / (win * win)


def bilinear(img, ys, xs):
    h, w = img.shape
    ys = np.clip(ys, 0, h - 1.001)
    xs = np.clip(xs, 0, w - 1.001)
    y0 = ys.astype(np.int32)
    x0 = xs.astype(np.int32)
    fy = ys - y0
    fx = xs - x0
    return (img[y0, x0] * (1 - fy) * (1 - fx) + img[y0 + 1, x0] * fy * (1 - fx)
            + img[y0, x0 + 1] * (1 - fy) * fx + img[y0 + 1, x0 + 1] * fy * fx)


def profiles(img, pts, gy, gx, rng, min_step, shuffle=False):
    """Median normalised 0->1 edge profile over sampled points.

    Two defences, both added after the first version produced overshoots of 359 STEP
    UNITS on real masters while passing a synthetic commissioning at 97% recovery:

    min_step -- each profile is divided by its own step height, so a sample point sitting
        on a ridge or a texture crest rather than a genuine step has a near-zero
        denominator and explodes. The synthetic arm could not expose this because a
        synthetic step image contains no degenerate edges by construction. Profiles whose
        step is smaller than min_step are DISCARDED and counted, never rescued.

    median -- one surviving near-degenerate profile can dominate a mean of thousands. The
        median cannot be moved by a minority however extreme, at the cost of nothing that
        matters here since a halo is a property of the typical edge, not the worst one.

    Returns (profile, n_used, n_rejected) so the discard rate is visible in the output
    rather than hidden -- a metric computed from 3 surviving profiles out of 4000 is not
    the same measurement as one computed from 3800.
    """
    t = np.arange(-HALF, HALF + 1, dtype=np.float32)
    keep = []
    rejected = 0
    for (py, px) in pts:
        if shuffle:
            ang = rng.uniform(0, 2 * np.pi)
            ny, nx = np.sin(ang), np.cos(ang)
            py = int(rng.integers(HALF + 2, img.shape[0] - HALF - 2))
            px = int(rng.integers(HALF + 2, img.shape[1] - HALF - 2))
        else:
            g = np.hypot(gy[py, px], gx[py, px])
            if g <= 0:
                rejected += 1
                continue
            ny, nx = gy[py, px] / g, gx[py, px] / g
        v = bilinear(img, py + t * ny, px + t * nx)
        lo = float(v[:15].mean())
        hi = float(v[-15:].mean())
        step = abs(hi - lo)
        if step < min_step:
            rejected += 1
            continue
        # Plateau flatness. A step has two flat asymptotes; a thin bright line crossed
        # perpendicular does not, and its two far ends can still differ enough to clear
        # min_step by chance. Reading the actual profiles showed lead-1-cpl and
        # leaf-2-cpl were dominated by exactly that -- 1.94 at +12px collapsing to 0.33
        # at +48px and never reaching the 1.0 plateau the normalisation assumes. Require
        # each side's inner and outer quarter to agree to within a fraction of the step.
        lf = abs(float(v[:20].mean()) - float(v[20:40].mean()))
        rf = abs(float(v[-20:].mean()) - float(v[-40:-20].mean()))
        if max(lf, rf) > PLATEAU_FRAC * step:
            rejected += 1
            continue
        p = (v - lo) / (hi - lo)
        if hi < lo:
            p = p[::-1]
        keep.append(p)
    if not keep:
        return np.zeros(t.size), 0, rejected
    return np.median(np.stack(keep), axis=0), len(keep), rejected


def overshoot(mean_p, clamp=True):
    """Peak excursion outside [0,1] in the halo band, both sides, in step units.

    clamp=False returns the SIGNED excursion. The control needs this: clamped, a shuffled
    control can only ever report "0 or more", and it reported exactly 0.00000 on all 26
    masters from thousands of surviving profiles. That is a zero-variance reading and
    tonight has taught that a statistic which cannot vary is indistinguishable from one
    that is not being computed. Signed, the control reports how far INSIDE [0,1] it sits,
    which is a margin rather than a floor.
    """
    c = HALF
    a, b = BAND
    hi_side = mean_p[c + a:c + b]
    lo_side = mean_p[c - b:c - a]
    over_hi = float(np.max(hi_side) - 1.0)
    over_lo = float(0.0 - np.min(lo_side))
    if clamp:
        return max(over_hi, 0.0), max(over_lo, 0.0)
    return over_hi, over_lo


def edge_points(lum, rng):
    b = boxblur(lum, BLUR)
    gy = np.zeros_like(b)
    gx = np.zeros_like(b)
    gy[1:-1, :] = (b[2:, :] - b[:-2, :]) * 0.5
    gx[:, 1:-1] = (b[:, 2:] - b[:, :-2]) * 0.5
    mag = np.hypot(gy, gx)
    m = np.zeros(mag.shape, bool)
    m[HALF + 2:-HALF - 2, HALF + 2:-HALF - 2] = True
    thr = float(np.percentile(mag[m], EDGE_PCT))
    ys, xs = np.nonzero((mag >= thr) & m)
    if ys.size > MAX_PROFILES:
        k = rng.choice(ys.size, MAX_PROFILES, replace=False)
        ys, xs = ys[k], xs[k]
    return list(zip(ys.tolist(), xs.tolist())), gy, gx, thr


def robust_step(img):
    """Minimum step height a profile must span to count as an edge, in DN.

    Set from the image's own tonal range so it adapts to subject and exposure, rather
    than a global DN constant that would be permissive on a high-key subject and
    prohibitive on a low-key one.
    """
    lo, hi = np.percentile(img, (1.0, 99.0))
    return MIN_STEP_FRAC * float(hi - lo)


def synth_arm(rng, amp, degenerate=False, spikes=False):
    """Known step with known overshoot through the identical machinery.

    degenerate=True adds low-contrast ridges -- crests with EQUAL values on both sides,
    which is the structure that produced 359-step-unit readings before the min_step gate.

    spikes=True adds THIN BRIGHT LINES, whose two far ends can differ enough to clear
    min_step by chance while never reaching a plateau. This is the confound found by
    reading the real profiles rather than the real numbers: lead-1-cpl showed 1.94 at
    +12px collapsing to 0.33 at +48px and 0.62 at +180px, where the normalisation assumes
    1.0. It is a harder case than the ridges because it survives the first gate.
    """
    h = w = 700
    img = np.zeros((h, w), np.float32)
    img[:, w // 2:] = 1000.0
    t = np.arange(w) - w // 2
    ring = amp * 1000.0 * np.exp(-((np.abs(t) - 30.0) ** 2) / (2 * 12.0 ** 2))
    ring[t < 0] *= -1.0
    img += ring[None, :]
    if degenerate:
        for cx in (90, 170, 250, 470, 560, 640):
            d = np.arange(w) - cx
            img += (18.0 * np.exp(-(d ** 2) / (2 * 5.0 ** 2)))[None, :]
        for cy in (110, 300, 520):
            d = np.arange(h) - cy
            img += (14.0 * np.exp(-(d ** 2) / (2 * 4.0 ** 2)))[:, None]
    if spikes:
        for cx, ht in ((120, 900.0), (215, 700.0), (300, 800.0),
                       (430, -600.0), (525, 850.0), (610, -750.0)):
            d = np.arange(w) - cx
            img += (ht * np.exp(-(d ** 2) / (2 * 6.0 ** 2)))[None, :]
        for cy, ht in ((160, 800.0), (390, -700.0), (600, 750.0)):
            d = np.arange(h) - cy
            img += (ht * np.exp(-(d ** 2) / (2 * 5.0 ** 2)))[:, None]
    img += rng.normal(0, 2.0, img.shape).astype(np.float32)
    pts, gy, gx, _ = edge_points(img, rng)
    mp, n, rej = profiles(img, pts, gy, gx, rng, robust_step(img))
    oh, ol = overshoot(mp)
    return max(oh, ol), n, rej


def main(argv):
    rng = np.random.default_rng(31337)
    print("commissioning ARM SYNTH (known overshoot, CLEAN steps):")
    print(f"  {'planted':>9s} {'measured':>9s} {'ratio':>8s} {'used':>7s} {'rej':>7s}")
    synth = []
    for amp in (0.00, 0.05, 0.10, 0.20, 0.40):
        got, n, rej = synth_arm(rng, amp)
        synth.append((amp, got))
        r = (got / amp) if amp > 0 else float("nan")
        print(f"  {amp:9.3f} {got:9.4f} {r:8.3f} {n:7d} {rej:7d}")
    base = synth[0][1]
    mono = all(synth[i][1] < synth[i + 1][1] for i in range(len(synth) - 1))
    resp = synth[-1][1] - base
    ok_synth = mono and resp > 0.15

    print("\ncommissioning ARM DEGEN (same, but with equal-sided ridges mixed in --")
    print("  this is the structure that gave 359-step-unit readings before the gate):")
    print(f"  {'planted':>9s} {'measured':>9s} {'ratio':>8s} {'used':>7s} {'rej':>7s}")
    degen = []
    for amp in (0.00, 0.10, 0.40):
        got, n, rej = synth_arm(rng, amp, degenerate=True)
        degen.append((amp, got))
        r = (got / amp) if amp > 0 else float("nan")
        print(f"  {amp:9.3f} {got:9.4f} {r:8.3f} {n:7d} {rej:7d}")
    d_err = max(abs(degen[i][1] - synth[[0, 2, 4][i]][1]) for i in range(3))
    ok_degen = d_err < 0.05 and degen[0][1] < 0.05
    print(f"  max deviation from the clean-step arm: {d_err:.4f}  "
          f"{'PASS' if ok_degen else 'FAIL'}")

    print("\nARM SPIKE — sensitivity FLOOR, not a pass/fail gate. Thin lines parallel to")
    print("  an edge sit at a fixed offset from it in every profile, which is the same")
    print("  geometry a halo has, so no aggregation can separate them in principle. The")
    print("  honest response is to measure what clutter alone reads and refuse to")
    print("  interpret anything below it, rather than tune a gate until the number")
    print("  looks acceptable:")
    print(f"  {'planted':>9s} {'measured':>9s} {'used':>7s} {'rej':>7s}")
    spike = []
    for amp in (0.00, 0.10, 0.40):
        got, n, rej = synth_arm(rng, amp, spikes=True)
        spike.append((amp, got))
        print(f"  {amp:9.3f} {got:9.4f} {n:7d} {rej:7d}")
    FLOOR = spike[0][1]
    print(f"  FLOOR = {FLOOR:.4f} step units — clutter with NO planted halo reads this.")
    print(f"  Readings at or below {FLOOR:.4f} on real masters are UNDETERMINED.")

    print(f"\n  ARM SYNTH  monotone {mono}, response {resp:.4f}, floor {base:.4f}  "
          f"{'PASS' if ok_synth else 'FAIL'}")
    print(f"  ARM DEGEN  equal-sided ridges do not corrupt the reading  "
          f"{'PASS' if ok_degen else 'FAIL'}")
    print(f"  ARM SPIKE  reported as a floor of {FLOOR:.4f}, not a gate")
    if not (ok_synth and ok_degen):
        print("\nNOT COMMISSIONED — the census below certifies nothing")
        return 1
    print("  COMMISSIONED, with a stated floor")

    d = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")
    paths = [p for p in sorted(d.iterdir()) if p.suffix.lower() == ".tiff"]
    if argv:
        want = set(argv)
        paths = [p for p in paths if any(w in p.stem for w in want)]
    print(f"\nmeasuring {len(paths)} masters "
          f"(DS={DS}, half-width {HALF}px -> {HALF * DS}px in master coords)\n")
    print(f"{'subject':38s} {'halo+':>8s} {'halo-':>8s} {'shuffle':>8s} "
          f"{'ratio':>7s} {'used':>6s} {'rej%':>6s} {'ctrlN':>6s}")
    print("-" * 98)
    rows = []
    for p in paths:
        a = tifffile.imread(str(p))
        rgb = a[:, :, :3].astype(np.float32)
        del a
        lum = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
        del rgb
        img = downsample(lum, DS).astype(np.float32)
        del lum
        ms = robust_step(img)
        pts, gy, gx, _ = edge_points(img, rng)
        if len(pts) < 200:
            print(f"{p.stem[:38]:38s} {'too few edges':>50s}")
            continue
        mp, n, rej = profiles(img, pts, gy, gx, rng, ms)
        if n < 100:
            print(f"{p.stem.replace('--SHIP-V2','')[:38]:38s} "
                  f"{'only %d profiles survived the step gate' % n:>50s}")
            del img
            continue
        oh, ol = overshoot(mp)
        sp, sn, srej = profiles(img, pts, gy, gx, rng, ms, shuffle=True)
        if sn < 100:
            sh = None
            ratio = None
        else:
            sh = max(overshoot(sp, clamp=False))
            real = max(oh, ol)
            ratio = real / sh if sh > 1e-9 else float("inf")
        rows.append((p.stem.replace("--SHIP-V2", ""), oh, ol, sh, ratio, n, mp, sn))
        shtxt = "  N/A   " if sh is None else f"{sh:8.4f}"
        rtxt = ("  N/A  " if ratio is None
                else ("    inf" if not np.isfinite(ratio) else f"{ratio:7.2f}"))
        print(f"{p.stem.replace('--SHIP-V2','')[:38]:38s} {oh:8.4f} {ol:8.4f} "
              f"{shtxt} {rtxt} {n:6d} {100.0 * rej / (n + rej):5.1f}% {sn:6d}")
        del img

    print()
    dead = [r for r in rows if r[4] is None]
    live = [r for r in rows if r[4] is not None and r[4] > 2.0
            and max(r[1], r[2]) > FLOOR]
    undet = [r for r in rows if r[4] is not None and r[4] > 2.0
             and max(r[1], r[2]) <= FLOOR]
    weak = [r for r in rows if r[4] is not None and r[4] <= 2.0]
    print(f"masters measured                        : {len(rows)}")
    print(f"halo CERTIFIED (> floor {FLOOR:.3f}, > 2x control) : {len(live)}")
    print(f"UNDETERMINED (at or below the floor)    : {len(undet)}  "
          f"{[r[0] for r in undet] if undet else ''}")
    print(f"NOT beyond control (uninformative here) : {len(weak)}  "
          f"{[r[0] for r in weak] if weak else ''}")
    print(f"CONTROL DID NOT RUN (<100 profiles)     : {len(dead)}  "
          f"{[r[0] for r in dead] if dead else ''}")
    print(f"partition sums to {len(live) + len(undet) + len(weak) + len(dead)} "
          f"of {len(rows)}")
    if dead:
        print("  a master in the last row has NO control; its severity number is")
        print("  uncertified and must not be compared against the others.")
    if live:
        live.sort(key=lambda r: -max(r[1], r[2]))
        print("\nranked by halo severity (step units; 0.10 = a 10% overshoot at the")
        print("typical strong edge, measured 16-180px out in master coordinates):")
        for stem, oh, ol, sh, ratio, n, _, sn in live:
            side = "bright" if oh >= ol else "dark"
            rs = (f"{ratio:.1f}x control" if np.isfinite(ratio)
                  else f"control sits {abs(sh):.4f} INSIDE the step")
            print(f"   {max(oh, ol):7.4f}  {side:6s}  {stem:40s} ({rs}, {sn} ctrl prof)")
        np.save(r"C:\dev\strehl-out\halo_profiles.npy",
                np.stack([r[6] for r in live]))
        pathlib.Path(r"C:\dev\strehl-out\halo_names.txt").write_text(
            "\n".join(r[0] for r in live), encoding="utf-8")
        print("\n  saved median profiles -> C:\\dev\\strehl-out\\halo_profiles.npy")
        print("\nmedian edge profile, worst three (columns are px from the edge in")
        print("master coords; a flat 1.0 plateau is correct, a bump is the halo):")
        for stem, oh, ol, sh, ratio, n, mp, sn in live[:3]:
            print(f"\n  {stem}   peak {max(oh, ol):.3f} step units")
            for off in range(0, 96, 6):
                v = mp[HALF + off]
                bar = "#" * max(0, int(round((v - 1.0) * 60)))
                print(f"    +{off * DS:4d}px  {v:7.4f} {bar}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
