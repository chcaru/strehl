"""Where does each arm put the subject's edge, and is the merge's edge real?

The line cut showed the merge's silhouette transition sitting far outside every
single frame's. That is a strong claim, so it needs a number and it needs its
confounds shot.

The number: the x at which each arm crosses 50% of its own backdrop level.
Defocus spreads an occluding edge symmetrically and leaves the 50% point near
the true geometric edge, so the 50% crossing is comparable ACROSS arms of
different sharpness in a way that "where does it start to go dark" is not.

Confound 1 -- a sharp render is legitimately darker than a blurred one on fine
dark structure. Shot by the arm ordering: the frame in which the subject is
SHARPEST is the one reading flat backdrop where the merge reads structure. Real
anatomy would appear most in the sharpest frame, not least.

Confound 2 -- registration. If the merge's common coordinate system differed
from the identity-warped single frames, every edge would shift together. Shot
by the far field: all five arms agree to <1% out to x=450, and the three single
frames agree with EACH OTHER to within a few tens of px at the edge while the
merge sits far outside all of them. A global warp cannot produce that.

Confound 3 -- the subject is 3D, so a given part is sharp in only one frame.
Shot by amplitude: a dark object at x=650 that were merely defocused in f149
would still DARKEN f149 at x=650, because that is exactly the veiling this
whole investigation is about. f149 reads 1.00 there. There is no object.
"""

import argparse
import pathlib

import numpy as np
import tifffile


def read_linear(path):
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def cross(profile, xs, ref, frac):
    """FIRST x at which the profile falls below frac*ref.

    An earlier version returned the LAST crossing -- the first x after which
    the profile never recovers. On a monotone single-frame edge the two agree.
    On the merge they do not, because the merge's profile is NOT monotone: it
    dives at x~700, recovers to 0.65 at x~980, and dives again. The last-
    crossing version reported 970 for a row the plot plainly crosses at 700,
    and reported the merge's edge as being OUTSIDE the single frames' when the
    picture shows the opposite. Non-monotonicity is the finding, not a nuisance.
    """
    v = profile / ref
    below = np.flatnonzero(v < frac)
    if below.size == 0:
        return None
    return float(xs[below[0]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--row", type=int, action="append", required=True)
    ap.add_argument("--x0", type=int, required=True)
    ap.add_argument("--x1", type=int, required=True)
    ap.add_argument("--crop", required=True, help="output side-by-side PNG")
    ap.add_argument("--crop-arms", default="off,f149")
    ap.add_argument("--crop-box", required=True, help="x0,y0,x1,y1")
    args = ap.parse_args()

    arms = {}
    for spec in args.arm:
        name, _, p = spec.partition("=")
        arms[name] = read_linear(pathlib.Path(p))
    names = list(arms)
    xs = np.arange(args.x0, args.x1)

    print("=== 50% crossing of each arm's own backdrop (px, native) ===")
    print("  row     " + "".join(f"{n:>10s}" for n in names))
    cross_tab = {n: [] for n in names}
    for y in args.row:
        cells = []
        for n in names:
            cut = arms[n][y, args.x0:args.x1].astype(np.float64)
            sm = np.convolve(cut, np.ones(9) / 9.0, mode="same")
            ref = float(np.median(cut[:120]))
            c = cross(sm, xs, ref, 0.5)
            cross_tab[n].append(c)
            cells.append(f"{c:10.0f}" if c is not None else f"{'--':>10s}")
        print(f"  {y:<8d}" + "".join(cells))
    print()
    print("  mean    " + "".join(
        f"{np.mean([c for c in cross_tab[n] if c is not None]):10.0f}" for n in names))
    print()

    single = [n for n in names if n.startswith("f")]
    if single and "off" in names:
        sm_mean = np.mean([np.mean([c for c in cross_tab[n] if c is not None])
                           for n in single])
        off_mean = np.mean([c for c in cross_tab["off"] if c is not None])
        print(f"  single-frame mean edge : {sm_mean:8.0f} px")
        print(f"  merge edge             : {off_mean:8.0f} px")
        print(f"  MERGE EDGE DISPLACED   : {sm_mean - off_mean:8.0f} px "
              f"into the backdrop")
        spread = [np.mean([c for c in cross_tab[n] if c is not None]) for n in single]
        print(f"  spread among the single frames themselves: "
              f"{max(spread) - min(spread):.0f} px "
              f"-- the merge is outside this by {sm_mean - off_mean:.0f} px")
    print()

    # POINTWISE HULL TEST. No edge-fitting, no threshold, no segmentation: at
    # every x along the cut, is the merge darker than the DARKEST single frame?
    # A weighted average cannot be. Everything is a ratio to each arm's own
    # backdrop, so the 17.6% exposure spread between arms cannot reach this.
    print("=== pointwise hull: is the merge below EVERY single frame? ===")
    print("  (ratio space, so exposure drift between arms cannot produce it)")
    for y in args.row:
        ref = {}
        prof = {}
        for n in names:
            cut = arms[n][y, args.x0:args.x1].astype(np.float64)
            sm = np.convolve(cut, np.ones(9) / 9.0, mode="same")
            ref[n] = float(np.median(cut[:120]))
            prof[n] = sm / ref[n]
        lo = np.min([prof[n] for n in single], axis=0)
        hi = np.max([prof[n] for n in single], axis=0)
        viol = prof["off"] < lo - 0.02
        # Restrict to pixels the SHARPEST frame calls open backdrop. That is
        # the confound-free zone: no scene object is there, in the one view
        # best able to show one.
        openbd = prof["f149"] > 0.95
        both = viol & openbd
        n_open = int(openbd.sum())
        if n_open == 0:
            continue
        run = np.flatnonzero(both)
        span = f"x={xs[run[0]]}..{xs[run[-1]]}" if run.size else "none"
        worst = float((lo - prof["off"])[both].max()) if run.size else 0.0
        print(f"  row {y:<5d} open backdrop {n_open:4d}px | "
              f"merge below all frames on {int(both.sum()):4d}px ({span}) | "
              f"worst {worst * 100:5.1f}% below the darkest frame")
        # The deficit against the BEST available frame, on open backdrop only.
        d = float((hi - prof["off"])[openbd].max())
        xd = int(xs[openbd][np.argmax((hi - prof["off"])[openbd])])
        print(f"           worst deficit vs the BRIGHTEST frame on open "
              f"backdrop: {d * 100:5.1f}% at x={xd}")
    print()

    # The picture: the same crop from the merge and from the sharpest frame,
    # stretched identically, so the smear is visible rather than argued.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cx0, cy0, cx1, cy1 = (int(v) for v in args.crop_box.split(","))
    ca = [n.strip() for n in args.crop_arms.split(",")]
    fig, axes = plt.subplots(1, len(ca), figsize=(6.2 * len(ca), 5.6), dpi=140)
    if len(ca) == 1:
        axes = [axes]
    # One shared stretch for every panel, taken from the union, so a difference
    # on screen is a difference in the data.
    stack = np.concatenate([arms[n][cy0:cy1, cx0:cx1].ravel() for n in ca])
    lo, hi = np.percentile(stack, [0.5, 99.5])
    for ax, n in zip(axes, ca):
        sub = arms[n][cy0:cy1, cx0:cx1]
        ax.imshow(np.clip((sub - lo) / (hi - lo), 0, 1) ** (1 / 2.2),
                  cmap="gray", vmin=0, vmax=1,
                  extent=[cx0, cx1, cy1, cy0], interpolation="nearest")
        ax.set_title(n, fontsize=13)
        ax.set_xlabel("x (px, native)")
    fig.suptitle("same crop, same stretch: the merge draws structure the "
                 "sharpest frame says is empty backdrop", fontsize=11)
    fig.tight_layout()
    out = pathlib.Path(args.crop)
    fig.savefig(out)
    assert out.read_bytes()[:4] == b"\x89PNG", f"{out} is not a PNG"
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
