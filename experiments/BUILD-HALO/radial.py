"""Radial profile of the aura, outward from a FROZEN silhouette.

The question this exists to answer
----------------------------------
ORCH looked at a full frame of `lavendar-cpl` and saw a bright aura that
looked far wider than our focus window could explain, and proposed that we
have been treating a two-mechanism problem as one mechanism:

  (i)  window-support contamination -- a background pixel within
       SOBEL_RADIUS + WINDOW_RADIUS of a depth edge has foreground content
       inside its focus window, so it elects the frame where the FOREGROUND is
       sharp.  Radius set by OUR window.  Ours to fix.

  (ii) defocus spill -- in frames where the background is sharp, the near
       subject is heavily defocused and its light spreads OUTWARD over the
       defocus blur radius.  Radius set by OPTICS.  Present in every frame, so
       no selector can remove it.

Why this measurement can decide it without any PSF model
--------------------------------------------------------
Mechanism (i) has a HARD CEILING.  The focus measure is a box mean of radius
WINDOW_RADIUS over a gradient of radius SOBEL_RADIUS, so a pixel further than
SOBEL_RADIUS + WINDOW_RADIUS from a depth edge has NO foreground content in its
window at all.  Mechanism (i) cannot reach past that distance -- not weakly,
not at reduced amplitude, but at all.

So: if the aura extends materially beyond that ceiling, mechanism (i) is not
its whole cause, and this follows from the operator's construction rather than
from a fitted number.  That is the entire argument, and it needs no estimate of
the lens's blur circle.

THE EDGE SET IS FROZEN.  V-HALO killed this build's previous dose-response
slope because the rim estimator re-detected edges per arm, so the arms were not
paired and the "slope" partly measured edge-set drift.  Here the silhouette is
computed ONCE, from ONE nominated reference arm, and every arm is profiled
against those same distance bins.  `--mask-from` names that arm in the output
so it can never be silently different between runs.
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import tifffile

# The operator's own reach, from crates/strehl-core/src/focus.rs.
SOBEL_RADIUS = 1
WINDOW_RADIUS = 13
CEILING_I = SOBEL_RADIUS + WINDOW_RADIUS


def read_linear(path):
    """A 16-bit linear RGB render, as float luma. Never PIL: it mangles 16-bit."""
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] == 3, f"{path}: expected HxWx3, got {a.shape}"
    a = a.astype(np.float32)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def subject_mask(luma):
    """Segment the subject from the backdrop, sign-agnostically.

    The bee is dark on white and the lavender is white on grey, so a fixed
    threshold direction would work on one and invert on the other.  Instead the
    backdrop level is read from the image corners -- which are background on
    every subject in the plan -- and the subject is whatever departs from it,
    in EITHER direction.
    """
    h, w = luma.shape
    c = max(h, w) // 12
    corners = np.concatenate(
        [
            luma[:c, :c].ravel(),
            luma[:c, -c:].ravel(),
            luma[-c:, :c].ravel(),
            luma[-c:, -c:].ravel(),
        ]
    )
    bg = float(np.median(corners))
    # A robust spread of the backdrop itself, so the threshold is in units of
    # backdrop variation rather than of absolute DN.
    sd = float(np.median(np.abs(corners - bg))) * 1.4826
    sd = max(sd, 1e-6)
    m = np.abs(luma - bg) > 12.0 * sd

    # Close pinholes and drop speckle: the silhouette wanted here is the gross
    # outline of the subject, not its internal texture.
    try:
        from scipy import ndimage

        m = ndimage.binary_closing(m, np.ones((9, 9)))
        m = ndimage.binary_opening(m, np.ones((5, 5)))
        lab, n = ndimage.label(m)
        if n > 1:
            sizes = ndimage.sum(m, lab, range(1, n + 1))
            m = lab == (1 + int(np.argmax(sizes)))
        m = ndimage.binary_fill_holes(m)
    except ImportError:
        sys.exit("scipy is required (distance transform + morphology)")
    return m, bg, sd


def distance_outward(mask):
    """Euclidean distance from each background pixel to the nearest subject pixel."""
    from scipy import ndimage

    return ndimage.distance_transform_edt(~mask)


def profile(luma, dist, mask, edges):
    """Mean background luma in each distance annulus. Subject pixels excluded."""
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (~mask) & (dist > lo) & (dist <= hi)
        n = int(sel.sum())
        out.append((float(luma[sel].mean()) if n else np.nan, n))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True,
                    help="NAME=path.tif, repeatable")
    ap.add_argument("--mask-from", required=True,
                    help="which arm NAME defines the frozen silhouette")
    ap.add_argument("--far", type=float, default=200.0,
                    help="distance treated as clean background (reference level)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    arms = {}
    for spec in args.arm:
        name, _, p = spec.partition("=")
        arms[name] = read_linear(pathlib.Path(p))
    shapes = {a.shape for a in arms.values()}
    assert len(shapes) == 1, f"arms differ in shape: {shapes}"
    assert args.mask_from in arms, f"--mask-from {args.mask_from} is not an arm"

    # ---- FROZEN: one mask, one distance field, shared by every arm ----
    mask, bg, sd = subject_mask(arms[args.mask_from])
    dist = distance_outward(mask)
    print(f"mask from {args.mask_from!r}: subject {100*mask.mean():.2f}% of plane, "
          f"backdrop level {bg:.1f} DN, backdrop sd {sd:.2f} DN")

    edges = np.concatenate([np.arange(0, 60, 2.0), np.arange(60, 260, 10.0)])
    far = (~mask) & (dist > args.far)
    assert far.sum() > 10000, "not enough far-field background to reference against"

    rows, results = [], {}
    for name, luma in arms.items():
        ref = float(luma[far].mean())
        pr = profile(luma, dist, mask, edges)
        # Excess over the arm's OWN far field, in units of the backdrop's own
        # noise -- so arms with different overall exposure stay comparable and
        # the y axis says "how many sigma of backdrop is this aura".
        results[name] = dict(
            ref=ref,
            centres=[(lo + hi) / 2 for lo, hi in zip(edges[:-1], edges[1:])],
            excess=[(v - ref) / sd if np.isfinite(v) else np.nan for v, _ in pr],
            counts=[n for _, n in pr],
        )
        rows.append((name, ref))

    for name, ref in rows:
        r = results[name]
        # Where does the aura fall to a tenth of its peak?
        ex = np.array(r["excess"])
        ce = np.array(r["centres"])
        pk = np.nanmax(np.abs(ex[ce < 100]))
        w10 = np.nan
        for c, e in zip(ce, ex):
            if np.isfinite(e) and abs(e) <= 0.10 * pk:
                w10 = c
                break
        r["peak_sigma"] = float(pk)
        r["extent_10pct_px"] = float(w10)
        print(f"  {name:22s} far-field {ref:9.1f} DN   peak |excess| {pk:6.2f} sd   "
              f"falls to 10% at {w10:6.1f} px   (mechanism (i) ceiling {CEILING_I} px)")

    payload = dict(
        mask_from=args.mask_from,
        ceiling_mechanism_i=CEILING_I,
        backdrop_sd=sd,
        subject_fraction=float(mask.mean()),
        arms=results,
    )
    outp = pathlib.Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(payload, indent=1))
    print(f"wrote {outp}")

    plot(payload, outp.with_suffix(".png"), args.title)


def plot(payload, png, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6), dpi=130)
    for name, r in payload["arms"].items():
        ax.plot(r["centres"], r["excess"], marker=".", ms=3, lw=1.4, label=name)
    ax.axhline(0, color="k", lw=0.7)
    c = payload["ceiling_mechanism_i"]
    ax.axvspan(0, c, color="tab:green", alpha=0.10)
    ax.axvline(c, color="tab:green", ls="--", lw=1.6,
               label=f"(a) mechanism (i) HARD ceiling = SOBEL+WINDOW = {c} px")
    ax.set_xscale("symlog", linthresh=20)
    ax.set_xlabel("distance outward from the frozen silhouette (px, native)")
    ax.set_ylabel("background excess over the arm's own far field (backdrop sd)")
    ax.set_title(title or "aura radial profile")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(png)
    assert png.read_bytes()[:4] == b"\x89PNG", f"{png} is not a PNG"
    print(f"wrote {png}")


if __name__ == "__main__":
    main()
