"""Check the fitted drift model against evidence it never saw.

Two independent checks, both cheap:

  GROUND TRUTH -- AGENTS.md rule 6 records two hand-measured registration
  shifts at f240 for bee-3-cpl.  The model was fitted from local NCC
  correspondences and has never been shown these numbers.

  TRACK -- a contact sheet of one named block across the bracket.  V-VEILCLAW
  rule 1: look at the pixels.  A residual statistic pooled over ambiguous
  correspondences cannot tell you whether the claw stayed in the box; a
  picture can.
"""
import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402

RAWROOT = pathlib.Path(r"D:\personal\macro")

# master px (y, x) -> required (dy, dx) at f240, from AGENTS.md rule 6.
TRUTH_BEE3_F240 = [((4000, 3400), (-186, 20)), ((3285, 2065), (-94, 152))]

BOXES = {  # master px y0,y1,x0,x1 -- from experiments/V-VEILCLAW/probe.py
    "claw": (2640, 2830, 2080, 2270),
    "ctl": (3120, 3450, 1880, 2250),
    "null": (100, 400, 6500, 6900),
}


def load(subject, out):
    return np.load(pathlib.Path(out) / "drift" / f"{subject}.npz",
                   allow_pickle=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="bee-3-cpl")
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--box", default="claw")
    ap.add_argument("--nsheet", type=int, default=24)
    ap.add_argument("--truth", action="store_true")
    a = ap.parse_args()

    d = load(a.subject, a.out)
    A, Ty, Tx = d["a"], d["ty"], d["tx"]
    n = int(d["n"])
    print(f"{a.subject}: n={n} deg={int(d['deg'])} "
          f"a {A[0]:.5f} -> {A[-1]:.5f}")

    if a.truth:
        print("\nGROUND TRUTH (AGENTS.md rule 6, f240, master px):")
        k = 240
        for (py, px), (dy, dx) in TRUTH_BEE3_F240:
            qy, qx = vc.map_point(py / 2.0, px / 2.0, A[k], Ty[k], Tx[k])
            my, mx = 2 * qy - py, 2 * qx - px
            print(f"  master ({py},{px}): recorded dy={dy:+5d} dx={dx:+5d}"
                  f" | model dy={my:+7.1f} dx={mx:+7.1f}"
                  f" | err {np.hypot(my - dy, mx - dx):6.1f} master px")

    files = vc.frames(a.subject)
    y0, y1, x0, x1 = BOXES[a.box]
    hh, hw = (y1 - y0) // 4, (x1 - x0) // 4       # half-size in lattice px
    cy, cx = (y0 + y1) / 4.0, (x0 + x1) / 4.0     # centre in master/2 px
    ks = sorted({int(round(t)) for t in np.linspace(0, n - 1, a.nsheet)})
    tiles = []
    print(f"\nTRACK box {a.box} {BOXES[a.box]} -> {2 * hh}x{2 * hw} lattice px")
    for k in ks:
        g = vc.green_lattice(files[k])
        qy, qx = vc.map_point(cy, cx, A[k], Ty[k], Tx[k])
        iy, ix = int(round(qy)), int(round(qx))
        t = g[iy - hh:iy + hh, ix - hw:ix + hw]
        tiles.append((k, iy, ix, t))
        print(f"  f{k:03d} -> lattice ({iy},{ix})  "
              f"shift {2 * qy - (y0 + y1) / 2:+7.1f},"
              f"{2 * qx - (x0 + x1) / 2:+7.1f} master px  "
              f"resp {vc.abs_lap(t.astype(np.float32)).mean():8.2f}")
        sys.stdout.flush()

    import cv2
    cols = 6
    rows = (len(tiles) + cols - 1) // cols
    th, tw = 2 * hh, 2 * hw
    sheet = np.zeros((rows * (th + 18), cols * tw, 3), np.uint8)
    for i, (k, _, _, t) in enumerate(tiles):
        v = t.astype(np.float32)
        lo, hi = np.percentile(v, [1, 99])
        v = np.clip((v - lo) / max(hi - lo, 1e-6), 0, 1)
        img = (np.dstack([v, v, v]) * 255).astype(np.uint8)
        r, c = divmod(i, cols)
        sheet[r * (th + 18) + 18:(r + 1) * (th + 18), c * tw:(c + 1) * tw] = img
        cv2.putText(sheet, f"f{k:03d}", (c * tw + 3, r * (th + 18) + 13),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    p = pathlib.Path(a.out) / "track" / f"{a.subject}-{a.box}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), sheet)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
