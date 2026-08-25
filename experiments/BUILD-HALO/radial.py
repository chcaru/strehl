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
    """Segment the subject from the backdrop by LOCAL TEXTURE, not brightness.

    Two earlier attempts failed here, and both failed *silently*, which is why
    this docstring is long and why `maskcheck.py` exists to draw the result.

    1. Thresholding at a multiple of the backdrop's spread, with the spread
       pooled over all four corners.  The frame has an illumination gradient,
       so the pooled spread measured the difference BETWEEN corners (3377 DN)
       rather than noise within one.  The threshold landed outside the data
       range and selected 0.00% of the plane.

    2. Otsu on the luma.  The backdrop is not uniform -- it is brighter on the
       right than the left by more than the subject-to-backdrop step in places
       -- so Otsu split the BACKDROP'S OWN GRADIENT and labelled the entire
       right half of the empty background as subject.  It reported a plausible
       49.32% and drawing the contour showed it running through open sky.

    Brightness cannot separate these classes because the illumination gradient
    is confounded with them.  Texture can: every subject in this plan is
    intensely detailed (hairs, trichomes, chitin) and every backdrop is a
    smooth sweep.  Local standard deviation is invariant to any additive
    low-frequency gradient, so it is immune to the thing that broke both
    earlier attempts.

    It also fails in the RIGHT direction for this measurement.  The halo is a
    smooth glow with no texture, so it lands on the backdrop side -- which is
    what makes "distance 0" the silhouette rather than the outer edge of the
    thing being measured.
    """
    from scipy import ndimage

    # Local sd over an 11x11 window, via the E[x^2] - E[x]^2 identity.
    k = 11
    mean = ndimage.uniform_filter(luma, k)
    meansq = ndimage.uniform_filter(luma * luma, k)
    sd_local = np.sqrt(np.maximum(meansq - mean * mean, 0.0))

    # Threshold in units of the BACKDROP's own texture, read from the corners.
    # The corners are backdrop on every subject in the plan; that is a far
    # weaker assumption than a polarity or a uniform illumination field.
    h, w = luma.shape
    c = max(h, w) // 12
    corner_sd = np.concatenate([
        sd_local[:c, :c].ravel(), sd_local[:c, -c:].ravel(),
        sd_local[-c:, :c].ravel(), sd_local[-c:, -c:].ravel(),
    ])
    base = float(np.median(corner_sd))
    m = sd_local > 6.0 * max(base, 1e-6)

    # Close across the smooth interior of a bud, drop isolated dust specks,
    # keep the one big blob, fill it.
    m = ndimage.binary_closing(m, np.ones((15, 15)))
    m = ndimage.binary_opening(m, np.ones((7, 7)))
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (1 + int(np.argmax(sizes)))
    m = ndimage.binary_fill_holes(m)
    # The local-sd operator reports texture over its own window, so it dilates
    # the subject by half a window.  Take that back, or "distance 0" sits ~5 px
    # outside the silhouette and the first bins measure nothing.
    m = ndimage.binary_erosion(m, np.ones((2 * (k // 2) + 1, 2 * (k // 2) + 1)))

    bg = float(np.median(luma[~m]))
    # Backdrop noise from ONE corner patch, never pooled across corners.
    patch = luma[:c, :c]
    sd = float(np.median(np.abs(patch - np.median(patch)))) * 1.4826
    assert 0.02 < m.mean() < 0.80, (
        f"segmentation implausible: subject is {100*m.mean():.2f}% of the plane"
    )
    return m, bg, max(sd, 1e-6)


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

    arms = payload["arms"]
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(11, 9), dpi=130, sharex=True)
    for name, r in arms.items():
        ax.plot(r["centres"], r["excess"], marker=".", ms=3, lw=1.4, label=name)
    ax.axhline(0, color="k", lw=0.7)
    c = payload["ceiling_mechanism_i"]
    for a in (ax, bx):
        a.axvspan(0, c, color="tab:green", alpha=0.10)
        a.axvline(c, color="tab:green", ls="--", lw=1.6)
        a.grid(alpha=0.3)
    ax.set_ylabel("excess over the arm's own far field (backdrop sd)")
    ax.set_title(title or "aura radial profile")
    ax.legend(fontsize=8, loc="best")
    ax.text(c * 1.15, ax.get_ylim()[1] * 0.92,
            f"mechanism (i) HARD ceiling\nSOBEL+WINDOW = {c} px",
            fontsize=8, color="tab:green", va="top")

    # The paired difference. Both arms are profiled at IDENTICAL pixels in
    # IDENTICAL bins, so this curve isolates what the ELECTION changed, with
    # the optics -- which are common to both -- differenced away exactly.
    if "off" in arms and "on" in arms:
        d = np.array(arms["off"]["excess"]) - np.array(arms["on"]["excess"])
        bx.plot(arms["off"]["centres"], d, color="crimson", marker=".", ms=3, lw=1.6,
                label="off - on  (what the election changed)")
        bx.axhline(0, color="k", lw=0.7)
        bx.legend(fontsize=8)
    bx.set_xscale("symlog", linthresh=20)
    bx.set_xlabel("distance outward from the frozen silhouette (px, native)")
    bx.set_ylabel("off - on (backdrop sd)")

    fig.tight_layout()
    fig.savefig(png)
    assert png.read_bytes()[:4] == b"\x89PNG", f"{png} is not a PNG"
    print(f"wrote {png}")


if __name__ == "__main__":
    main()
