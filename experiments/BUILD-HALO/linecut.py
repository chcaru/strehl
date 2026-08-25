"""Raw line cuts across an occluding boundary. No mask, no segmentation.

Why this exists
---------------
The radial profile says the background near the lavender subject is DARKER
than the far field by ~8.7 backdrop sd.  ORCH and I both LOOK at that frame and
see a BRIGHT aura.  Those cannot both be right about the same pixels, and the
standing rule for this build is that when the pictures and the number disagree,
the pictures are right -- so the number is what has to be re-examined.

The most likely explanation is that both are true of different pixels: a narrow
BRIGHT rim sitting on top of a broad DARK depression, with the segmentation's
boundary falling outside the rim so the profile only ever saw the depression.

A raw line cut cannot have that failure mode, because it has no boundary to get
wrong.  It reads the actual DN along an actual row of the actual file, for
every arm, on one axis.  Whatever is there will be there.
"""

import argparse
import pathlib

import numpy as np
import tifffile


def read_linear(path):
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, help="NAME=path.tif")
    ap.add_argument("--row", type=int, action="append", required=True)
    ap.add_argument("--x0", type=int, required=True)
    ap.add_argument("--x1", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    arms = {}
    for spec in args.arm:
        name, _, p = spec.partition("=")
        arms[name] = read_linear(pathlib.Path(p))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = args.row
    fig, axes = plt.subplots(len(rows), 1, figsize=(12, 3.4 * len(rows)), dpi=130,
                             squeeze=False)
    xs = np.arange(args.x0, args.x1)
    for ax, y in zip(axes[:, 0], rows):
        for name, luma in arms.items():
            cut = luma[y, args.x0:args.x1]
            # Normalise each arm by its own BACKDROP level, taken from the
            # start of the cut, so arms with different overall exposure sit on
            # one axis and the SHAPE is what is compared.
            #
            # An earlier version referenced the FAR end of the cut, which on
            # these rows lands inside the subject: every curve was then divided
            # by a subject value and "1.0" meant nothing. The cuts are written
            # backdrop-first for exactly this reason.
            ref = float(np.median(cut[:120]))
            ax.plot(xs, cut / ref, lw=1.2, label=f"{name}")
        ax.axhline(1.0, color="k", lw=0.7, ls=":")
        ax.set_ylabel(f"row {y}\n(backdrop at x0 = 1.0)")
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8, ncol=2)
    axes[0, 0].set_title(args.title or "raw line cuts across the boundary")
    axes[-1, 0].set_xlabel("x (px, native)")
    fig.tight_layout()
    out = pathlib.Path(args.out)
    fig.savefig(out)
    assert out.read_bytes()[:4] == b"\x89PNG", f"{out} is not a PNG"
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
