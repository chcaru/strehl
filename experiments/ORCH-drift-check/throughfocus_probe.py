"""Through-focus probe: did ANY input frame ever see this region sharply?

Answers the one question that decides whether a soft region in a merged master
is a MERGE defect (some frame had it, we lost it) or a CAPTURE limit (no frame
ever had it, and no algorithm can invent it).

Reads the CFA green channel directly from the raws -- no demosaic, no
alignment, no tone curve -- and reports mean |laplacian| in a fixed window per
frame. The absolute value is meaningless; only the SHAPE of the curve matters:

  clear interior peak      -> some frame had it sharp   -> MERGE defect
  monotone / peak at end   -> bracket ran out           -> CAPTURE limit
  flat, no peak            -> never resolved at all     -> CAPTURE limit
  two peaks                -> two-layer occlusion       -> veiling, needs unmixing

A CONTROL WINDOW is mandatory and not optional. A window that reports "flat"
proves nothing on its own: a broken reader, a wrong crop, or a stuck index all
produce flat. The control is placed on known-sharp structure in the same frames,
and it must produce a clear peak. If the control is flat, the instrument is
broken and the probe window's flatness is uninterpretable.

Usage:
  python throughfocus_probe.py <rawdir> --win y0 y1 x0 x1 --ctl y0 y1 x0 x1
                               [--step N] [--out out.csv]
"""
import sys
import pathlib
import numpy as np
import rawpy


def parse4(argv, flag):
    i = argv.index(flag)
    return tuple(int(v) for v in argv[i + 1:i + 5])


def sharp(plane):
    """Mean |laplacian| -- a blur-monotone detail measure."""
    p = plane.astype(np.float32)
    lap = np.abs(4 * p[1:-1, 1:-1] - p[:-2, 1:-1] - p[2:, 1:-1] - p[1:-1, :-2] - p[1:-1, 2:])
    return float(lap.mean())


def _smooth(v, k=7):
    """Boxcar with edge padding. Peak detection on an unsmoothed noisy curve
    finds noise, so smoothing is not cosmetic here -- it is what makes the
    prominence test mean anything."""
    if k <= 1 or len(v) < k:
        return v
    ker = np.ones(k) / k
    return np.convolve(np.pad(v, k // 2, mode="edge"), ker, mode="valid")[: len(v)]


def _peaks(v, floor, min_prom=0.10, min_sep=15):
    """Local maxima ranked by prominence, expressed as a fraction of `floor`.

    Prominence is measured against the highest saddle separating this peak from
    a higher one -- NOT against the global minimum on each side. The global-min
    form is more permissive and inflates the prominence of a small bump that
    happens to sit near a deep valley, which on a through-focus curve is the
    normal situation at the ends of a bracket. Using the saddle costs nothing
    and is the definition that will not manufacture a second layer.
    """
    n = len(v)
    cand = [i for i in range(1, n - 1) if v[i] >= v[i - 1] and v[i] > v[i + 1]]
    out = []
    for i in cand:
        higher_l = [j for j in cand if j < i and v[j] > v[i]]
        higher_r = [j for j in cand if j > i and v[j] > v[i]]
        left = v[: i + 1].min() if not higher_l else v[higher_l[-1] : i + 1].min()
        right = v[i:].min() if not higher_r else v[i : higher_r[0] + 1].min()
        prom = (v[i] - max(left, right)) / max(floor, 1e-9)
        out.append((i, float(v[i]), float(prom)))
    out.sort(key=lambda t: -t[2])
    kept = []
    for i, val, prom in out:
        if prom < min_prom:
            continue
        if any(abs(i - j) < min_sep for j, _, _ in kept):
            continue
        kept.append((i, val, prom))
    return sorted(kept)


def verdict(vals):
    """Classify a through-focus response curve.

    This function previously took the argmax and asked only whether it was
    interior. That cannot express the two-layer case -- which this probe's own
    docstring names as the case that matters most -- and on the flagship's
    occluded claw it returned INTERIOR-PEAK for the *foreground* peak and would
    have reported a merge defect where the truth was veiling. A statistic that
    reports where the maximum is cannot report that there were two.
    """
    v = np.asarray(vals, dtype=np.float64)
    n = len(v)
    if n < 5:
        return "TOO-FEW-FRAMES"
    lo, hi = float(v.min()), float(v.max())
    contrast = (hi - lo) / max(lo, 1e-9)
    if contrast < 0.15:
        return f"FLAT (peak/floor={1 + contrast:.3f}) -> never resolved"

    s = _smooth(v, 7)
    floor = float(np.percentile(s, 10))

    # The end-of-bracket test reads the SMOOTHED curve. Near any maximum a
    # smooth function is flat, so the argmax of a noisy curve wanders by several
    # samples -- which is enough to move it off the last two and turn "the
    # bracket ran out" into "a frame had it". The original implementation tested
    # the raw argmax and failed exactly this way on a monotone rising curve.
    k = int(np.argmax(s))
    if k <= 1 or k >= n - 2:
        return f"PEAK-AT-END frame#{k}/{n - 1} (ratio {1 + contrast:.2f}) -> bracket ran out"

    pk = _peaks(s, floor)
    if not pk:
        return "FLAT (no peak with prominence >= 0.10 of floor) -> never resolved"

    desc = "  ".join(f"frame#{i} prom={p:.2f}" for i, _, p in pk)
    if len(pk) == 1:
        return f"SINGLE-PEAK {desc} (ratio {1 + contrast:.2f}) -> one layer, a frame HAD it"
    if len(pk) == 2:
        sep = abs(pk[1][0] - pk[0][0])
        return (
            f"TWO-PEAK {desc} separation={sep} frames (ratio {1 + contrast:.2f})"
            " -> TWO LAYERS share this pixel; veiling, not a merge defect"
        )
    return (
        f"{len(pk)}-PEAK {desc} (ratio {1 + contrast:.2f})"
        " -> multiple layers share this pixel"
    )


def main():
    argv = sys.argv
    if "--win" not in argv or "--ctl" not in argv:
        print(__doc__)
        return 2
    rawdir = pathlib.Path(argv[1])
    wy0, wy1, wx0, wx1 = parse4(argv, "--win")
    cy0, cy1, cx0, cx1 = parse4(argv, "--ctl")
    step = int(argv[argv.index("--step") + 1]) if "--step" in argv else 6

    files = sorted(rawdir.glob("*.ARW"))
    if not files:
        print(f"no .ARW in {rawdir}")
        return 2
    sel = files[::step]
    print(f"{len(files)} frames, probing every {step} -> {len(sel)}")
    print(f"probe window  y[{wy0}:{wy1}] x[{wx0}:{wx1}]")
    print(f"control window y[{cy0}:{cy1}] x[{cx0}:{cx1}]")

    win, ctl, names = [], [], []
    for i, f in enumerate(sel):
        with rawpy.imread(str(f)) as r:
            v = r.raw_image_visible
            # RGGB: green at (0,1) and (1,0); take the (0,1) lattice, stride 2
            g = v[0::2, 1::2]
            hh, ww = g.shape
            a = g[max(0, wy0 // 2):min(hh, wy1 // 2), max(0, wx0 // 2):min(ww, wx1 // 2)]
            b = g[max(0, cy0 // 2):min(hh, cy1 // 2), max(0, cx0 // 2):min(ww, cx1 // 2)]
            if a.size < 100 or b.size < 100:
                print(f"window empty at frame {f.name}: g={g.shape}")
                return 2
            win.append(sharp(a))
            ctl.append(sharp(b))
            names.append(f.name)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(sel)}")

    print()
    print(f"{'frame':<16}{'probe':>12}{'control':>12}")
    for nm, a, b in zip(names, win, ctl):
        print(f"{nm:<16}{a:12.2f}{b:12.2f}")
    print()
    cv = verdict(ctl)
    print(f"CONTROL  : {cv}")
    if not cv.startswith("SINGLE-PEAK"):
        print("INSTRUMENT NOT COMMISSIONED -- control did not resolve to exactly")
        print("one interior peak. The probe result below is UNINTERPRETABLE.")
        print("A control that is FLAT proves nothing about the probe's ability to")
        print("respond; a control that is itself TWO-PEAK is not a control, it is a")
        print("second probe. Move the control onto structure known to be sharp in")
        print("exactly one place in the middle of the bracket.")
    print(f"PROBE    : {verdict(win)}")

    if "--out" in argv:
        p = pathlib.Path(argv[argv.index("--out") + 1])
        p.write_text(
            "frame,probe,control\n"
            + "".join(f"{nm},{a:.4f},{b:.4f}\n" for nm, a, b in zip(names, win, ctl)),
            encoding="utf-8",
        )
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
