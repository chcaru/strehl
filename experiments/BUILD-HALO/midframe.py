"""ORCH's end-frame trap, tested: add the MIDDLE frame to section 15.2's arms.

The claim under test
--------------------
Section 15.2 compared `off`, `on`, `frame000` and `frame298` across the
backdrop of `lavendar-cpl`, found all four superimposed within noise over
470 px, and concluded the wide feature is the scene's own illumination field
because two of the arms contain no election at all.

ORCH's objection is structural and it is a good one: BOTH single-frame arms are
END frames, and the end of a bracket is exactly where the subject is furthest
from focus and therefore spilling hardest onto the backdrop. A merge that
elects end-like frames, compared against two end frames, would agree with them
for the worst possible reason. The reference that discriminates is the MIDDLE
frame, where the subject is near focus and spills least -- and that is the one
arm section 15.2 did not render.

So: same pinned binary, same flags, same rows, same normalisation, one arm
added. If f149 is dramatically cleaner than f000/f298 the conclusion falls. If
f149 lies on top of them the conclusion stands.

Two things this script does that the original did not
-----------------------------------------------------
1. It prints every arm's RAW far-field DN before normalising anything. The
   arms have different exposures (this bracket's sibling drifts 18.3%), and a
   normalisation whose divisor is never shown is a normalisation nobody can
   check. Section 23.2 was written because that exact omission produced a
   wrong answer.

2. It reports the profile as a RATIO to each arm's own backdrop, which is
   exactly gain-invariant, AND as raw DN, so a reader can see which
   conclusions depend on the normalisation and which do not.
"""

import argparse
import hashlib
import pathlib

import numpy as np
import tifffile


def read_linear(path):
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def sha12(path):
    h = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    return h[:12].upper()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, help="NAME=path.tif")
    ap.add_argument("--row", type=int, action="append", required=True)
    ap.add_argument("--x0", type=int, required=True)
    ap.add_argument("--x1", type=int, required=True)
    ap.add_argument("--probe", type=int, action="append", required=True,
                    help="x positions to tabulate")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    arms = {}
    digests = {}
    for spec in args.arm:
        name, _, p = spec.partition("=")
        arms[name] = read_linear(pathlib.Path(p))
        digests[name] = sha12(p)

    # CONTROL: every arm must be a distinct file. Three renders of one command
    # produced three different files earlier in this build because other agents
    # were landing commits mid-run; the reverse failure -- two arms that are
    # secretly the same file -- would make any comparison trivially agree.
    print("=== arms (control: all digests must differ) ===")
    for name, d in digests.items():
        print(f"  {name:8s}  {d}")
    if len(set(digests.values())) != len(digests):
        print("  ** FAIL: two arms are byte-identical **")
    else:
        print(f"  OK: {len(digests)} arms, {len(set(digests.values()))} distinct digests")
    print()

    names = list(arms)
    shp = {arms[n].shape for n in names}
    assert len(shp) == 1, f"arms differ in shape: {shp}"
    h, w = shp.pop()
    print(f"image {w}x{h}, rows {args.row}, x {args.x0}..{args.x1}")
    print()

    # Raw levels first, before any normalisation, so the divisor is visible.
    print("=== RAW backdrop DN at the far end of each cut (the divisor) ===")
    raw_ref = {}
    for n in names:
        vals = [float(np.median(arms[n][y, args.x0:args.x0 + 120])) for y in args.row]
        raw_ref[n] = float(np.mean(vals))
        print(f"  {n:8s}  {raw_ref[n]:9.1f} DN")
    lo, hi = min(raw_ref.values()), max(raw_ref.values())
    print(f"  spread {hi - lo:.1f} DN = {100.0 * (hi - lo) / lo:.2f}% "
          f"-- ratios below are gain-invariant, raw DN below is not")
    print()

    for y in args.row:
        print(f"=== row {y}: ratio to each arm's OWN backdrop (gain-invariant) ===")
        hdr = "  x        " + "".join(f"{n:>10s}" for n in names)
        print(hdr)
        for x in args.probe:
            if not (args.x0 <= x < args.x1):
                continue
            cells = []
            for n in names:
                cut = arms[n][y, args.x0:args.x1]
                ref = float(np.median(cut[:120]))
                v = float(np.median(arms[n][y, max(x - 6, 0):x + 7]))
                cells.append(f"{v / ref:10.3f}")
            print(f"  {x:<9d}" + "".join(cells))
        print()

    # The decisive scalar: near-backdrop level relative to far backdrop, per
    # arm. If the middle frame is materially higher than the end frames, the
    # end frames were veiled and section 15.2's references were contaminated.
    print("=== DECISIVE: near-backdrop ratio, averaged over rows ===")
    near_lo, near_hi = args.probe[-2], args.probe[-1]
    print(f"  near band x={near_lo}..{near_hi}, far reference x={args.x0}..{args.x0 + 120}")
    for n in names:
        rs = []
        for y in args.row:
            cut = arms[n][y]
            ref = float(np.median(cut[args.x0:args.x0 + 120]))
            near = float(np.median(cut[near_lo:near_hi]))
            rs.append(near / ref)
        print(f"  {n:8s}  {np.mean(rs):8.4f}")
    print()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = args.row
    fig, axes = plt.subplots(len(rows), 1, figsize=(12, 3.4 * len(rows)), dpi=130,
                             squeeze=False)
    xs = np.arange(args.x0, args.x1)
    style = {"f149": dict(lw=2.4, color="crimson", zorder=5)}
    for ax, y in zip(axes[:, 0], rows):
        for n in names:
            cut = arms[n][y, args.x0:args.x1]
            ref = float(np.median(cut[:120]))
            kw = dict(lw=1.2)
            kw.update(style.get(n, {}))
            ax.plot(xs, cut / ref, label=n, **kw)
        ax.axhline(1.0, color="k", lw=0.7, ls=":")
        ax.set_ylabel(f"row {y}\n(own backdrop = 1.0)")
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8, ncol=3)
    axes[0, 0].set_title(args.title or "section 15.2 arms, plus the middle frame")
    axes[-1, 0].set_xlabel("x (px, native)")
    fig.tight_layout()
    out = pathlib.Path(args.out)
    fig.savefig(out)
    assert out.read_bytes()[:4] == b"\x89PNG", f"{out} is not a PNG"
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
