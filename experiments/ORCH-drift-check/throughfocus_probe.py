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


def verdict(vals):
    v = np.asarray(vals, dtype=np.float64)
    n = len(v)
    if n < 5:
        return "TOO-FEW-FRAMES"
    k = int(np.argmax(v))
    lo, hi = float(v.min()), float(v.max())
    contrast = (hi - lo) / max(lo, 1e-9)
    edge = k <= 1 or k >= n - 2
    if contrast < 0.15:
        return f"FLAT (peak/floor={1+contrast:.3f}) -> never resolved"
    if edge:
        return f"PEAK-AT-END frame#{k}/{n - 1} (ratio {1 + contrast:.2f}) -> bracket ran out"
    return f"INTERIOR-PEAK frame#{k}/{n - 1} (ratio {1 + contrast:.2f}) -> a frame HAD it"


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
    if not cv.startswith("INTERIOR-PEAK"):
        print("INSTRUMENT NOT COMMISSIONED -- control did not peak in the interior.")
        print("The probe result below is UNINTERPRETABLE. Move the control onto")
        print("structure known to be sharp somewhere in the middle of the bracket.")
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
