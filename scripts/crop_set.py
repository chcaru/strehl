#!/usr/bin/env python3
"""Print-worthiness instrument: 100% crops, at frozen coordinates, from LINEAR renders.

This project has a documented history of green metrics sitting on top of bad
images, so the deliverable here is pictures. Numbers are emitted alongside, but
they are supporting evidence and the verdict is made by looking.

Three crop classes, because three different defects live in three different
places:

  edge    occluding boundaries, where halo lives
  flat    low-texture regions, where merge noise lives
  detail  the sharpest available structure, where any "fix" that is secretly a
          blur will show up immediately

THE COORDINATES ARE FROZEN. They are chosen once from a baseline render and
written to a JSON plan, then reused unchanged for every later render of that
subject. Re-choosing them per render would let a change move the crop to
flattering ground, which is the exact failure this instrument exists to catch.

MEASUREMENT IS IN LINEAR. Input must be the linear render -- the default
`strehl stack --out` file, camera-native RGB with no transfer curve. Results in
this project have been retracted for being measured on an --srgb render. The
sRGB curve is applied here only on the way to an 8-bit PNG for human eyes, with
a gain that is itself frozen in the plan so that two renders are displayed
identically.

16-bit RGB TIFFs are read with tifffile and asserted to be uint16. PIL silently
downconverts multi-channel 16-bit TIFFs to 8 bits and has corrupted results in
this project before; it is used here only to WRITE 8-bit PNGs.

Usage
-----
    # Freeze a plan and emit the baseline crop set
    python scripts/crop_set.py plan  --renders C:\\dev\\strehl-out\\baseline
    python scripts/crop_set.py crops --renders C:\\dev\\strehl-out\\baseline --label baseline

    # Later, after a code change, with the same frozen coordinates
    python scripts/crop_set.py crops   --renders C:\\dev\\strehl-out\\cand --label cand
    python scripts/crop_set.py compare --baseline C:\\dev\\strehl-out\\baseline \\
                                       --candidate C:\\dev\\strehl-out\\cand
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

# 100% crop size, in output pixels. Big enough to judge a halo's full extent
# and small enough that several fit on a screen side by side.
CROP = 384

# Crops per class per subject.
N_PER_CLASS = 3

# Keep away from the frame edge: the alignment path shrinks the field of view
# and upsamples back to the original dimensions, so the border carries
# resampling artifacts that are not merge defects.
MARGIN = 256

DISPLAY_PCT = 99.5
DISPLAY_TARGET = 0.90

# ILCE-7CM2, XYZ (D65) -> camera RGB. This is the same characterisation the
# binary uses; it is duplicated here rather than imported because the harness
# has to be able to develop a stored TIFF with no RAW file beside it.
# Cross-checked against the binary by `strehl colorspace`; see BUILD-RENDER.md.
A7C2_XYZ_TO_CAM = np.array(
    [
        [0.7460, -0.2365, -0.0588],
        [-0.5687, 1.3442, 0.2474],
        [-0.0624, 0.1156, 0.6584],
    ],
    dtype=np.float64,
)

# Linear sRGB / BT.709-6 primaries -> CIE XYZ, D65. Derived from the standard's
# chromaticities by the NPM construction, matching color.rs's SRGB_TO_XYZ_D65.
SRGB_TO_XYZ_D65 = np.array(
    [
        [0.4123908, 0.3575843, 0.1804808],
        [0.2126390, 0.7151687, 0.0721923],
        [0.0193308, 0.1191948, 0.9505322],
    ],
    dtype=np.float64,
)


def camera_to_srgb(xyz_to_cam: np.ndarray) -> np.ndarray:
    """White-balanced camera RGB -> linear sRGB (BT.709 primaries, D65).

    A direct port of `strehl_core::color::camera_to_srgb`, step for step, so
    that what the harness displays is what the binary would render:

      1. cam_from_srgb = xyz_to_cam @ SRGB_TO_XYZ_D65
      2. row-normalise to sum 1 -- this is the step that says "the input is
         already white balanced". Skipping it produces a matrix that inverts
         the white balance that was already applied, and the result is a strong
         cast.
      3. invert.

    Because step 2 makes cam_from_srgb @ (1,1,1) = (1,1,1), the inverse maps
    neutral to neutral exactly. That means this transform cannot introduce or
    remove a global cast, and so cannot be validated on a grey patch -- only
    off-neutral colours move.
    """
    cam_from_srgb = xyz_to_cam @ SRGB_TO_XYZ_D65
    cam_from_srgb = cam_from_srgb / cam_from_srgb.sum(axis=1, keepdims=True)
    return np.linalg.inv(cam_from_srgb)


A7C2_CAM_TO_SRGB = camera_to_srgb(A7C2_XYZ_TO_CAM)


def read_linear(path: Path) -> np.ndarray:
    """Read a 16-bit linear RGB TIFF as float32 in [0, 1].

    Asserts the on-disk dtype. A silent 8-bit downconversion here would make
    every noise number below meaningless, and would look like a quality result.
    """
    arr = tifffile.imread(str(path))
    if arr.dtype != np.uint16:
        raise SystemExit(
            f"{path}: dtype is {arr.dtype}, expected uint16. "
            "Refusing to measure a downconverted image."
        )
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise SystemExit(f"{path}: shape {arr.shape}, expected (H, W, 3).")
    return arr.astype(np.float32) / 65535.0


def luma(lin: np.ndarray) -> np.ndarray:
    """Green channel. On a CFA sensor green carries the luminance detail and is
    the channel every focus measure in this project is computed on, so the crop
    chooser looks at the same signal the merge did."""
    return lin[..., 1]


def _score_fields(g: np.ndarray) -> dict[str, np.ndarray]:
    """Edge / flat / detail score fields, all computed in linear light."""
    # Coarse gradient magnitude. An occluding boundary is a strong step that
    # survives blurring; fine texture is not.
    gx = ndimage.sobel(g, axis=1, mode="reflect")
    gy = ndimage.sobel(g, axis=0, mode="reflect")
    grad = np.hypot(gx, gy)
    edge = ndimage.uniform_filter(grad, size=33)

    # Local contrast range over a window comparable to a halo's reach. A true
    # occluding edge separates two regions of genuinely different luminance.
    hi = ndimage.maximum_filter(g, size=65)
    lo = ndimage.minimum_filter(g, size=65)
    span = hi - lo

    # Fine high-pass energy: what a blur destroys first.
    lap = ndimage.laplace(g)
    detail = ndimage.uniform_filter(np.abs(lap), size=33)

    # Local standard deviation, for flatness.
    m1 = ndimage.uniform_filter(g, size=33)
    m2 = ndimage.uniform_filter(g * g, size=33)
    var = np.maximum(m2 - m1 * m1, 0.0)
    sd = np.sqrt(var)

    # OCCLUSION, not merely contrast. A halo needs a sharp subject edge with a
    # SMOOTH, largely defocused background on one side of it -- that is what an
    # occluding boundary is, and it is where the merge has to decide between a
    # sharp foreground and a blurred background that disagree.
    #
    # Gradient strength alone does not find it. On bee-1-cpl the strongest
    # coarse gradient in the frame is the compound eye, which is high-contrast
    # texture surrounded by more texture and carries no halo at all. Weighting
    # by the fraction of the neighbourhood that is FLAT is what separates "busy
    # detail" from "subject against background": at the bee's silhouette
    # roughly half the window is smooth backdrop, at the eye almost none is.
    flat_ind = (sd < np.percentile(sd, 25)).astype(np.float32)
    flat_frac = ndimage.uniform_filter(flat_ind, size=65)

    return {
        "edge": edge * span * flat_frac,
        "flat": sd,
        "detail": detail,
        "mean": m1,
    }


def _pick(score: np.ndarray, n: int, largest: bool, mask: np.ndarray) -> list[tuple[int, int]]:
    """Greedy non-maximum suppression: take the best cell, then forbid every
    cell within one crop of it, and repeat. Guarantees the crops do not
    overlap, so they are n independent looks rather than n views of one spot."""
    h, w = score.shape
    s = score.copy().astype(np.float64)
    bad = -np.inf if largest else np.inf
    s[~mask] = bad
    s[:MARGIN, :] = bad
    s[-MARGIN:, :] = bad
    s[:, :MARGIN] = bad
    s[:, -MARGIN:] = bad

    out: list[tuple[int, int]] = []
    for _ in range(n):
        idx = np.argmax(s) if largest else np.argmin(s)
        y, x = np.unravel_index(idx, s.shape)
        if not np.isfinite(s[y, x]):
            break
        out.append((int(x) - CROP // 2, int(y) - CROP // 2))
        y0, y1 = max(0, y - CROP), min(h, y + CROP)
        x0, x1 = max(0, x - CROP), min(w, x + CROP)
        s[y0:y1, x0:x1] = bad
    return out


def plan_subject(lin: np.ndarray) -> dict:
    """Choose the frozen crop coordinates and the frozen display gain."""
    g = luma(lin)
    f = _score_fields(g)

    # Exclude pixels that are near black or near clipped from every class: a
    # crop of the noise floor or of a blown highlight teaches nothing about the
    # merge, and both would otherwise win the "flattest" contest outright.
    ok = (f["mean"] > 0.01) & (f["mean"] < 0.92)

    rois = {
        "edge": _pick(f["edge"], N_PER_CLASS, True, ok),
        "detail": _pick(f["detail"], N_PER_CLASS, True, ok),
        # Flat also requires being off an occluding edge, or the "flattest" spot
        # can sit just inside a large smooth object whose boundary is in the
        # crop. The comparison must be <=, not <: the occlusion score is
        # identically zero across most of a frame (a pixel is either not on an
        # edge or not near flat ground), so its 40th percentile is 0 and a
        # strict < excludes every candidate and returns nothing.
        "flat": _pick(
            f["flat"], N_PER_CLASS, False,
            ok & (f["edge"] <= np.percentile(f["edge"], 40)),
        ),
    }

    # Frozen display gain: put a high percentile of linear green at 0.90. Chosen
    # once, from the baseline, and reused -- otherwise a change in image
    # brightness would be re-normalised away and made invisible.
    p = float(np.percentile(g, DISPLAY_PCT))
    gain = DISPLAY_TARGET / p if p > 1e-6 else 1.0

    return {
        "shape": [int(lin.shape[0]), int(lin.shape[1])],
        "crop": CROP,
        "display_gain": gain,
        "display_percentile": DISPLAY_PCT,
        "rois": {k: [[int(x), int(y)] for x, y in v] for k, v in rois.items()},
    }


def srgb_encode(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def to_display(patch: np.ndarray, gain: float, matrix: np.ndarray | None) -> np.ndarray:
    """Linear camera RGB -> 8-bit display. Display only; never measure on this.

    Order, and every step of it is load-bearing:

      neutralise pinned highlights -> gain -> colour matrix -> clamp -> curve

    The gain is a single multiply in LINEAR light, before the transfer curve,
    because the curve is not homogeneous: a gain applied to encoded values
    scales the channels by different amounts in linear light and shifts the hue
    of every non-neutral pixel instead of changing the exposure. (Where the gain
    sits relative to the matrix is free -- the matrix is linear, so the two
    commute exactly.)

    The highlight neutralisation is M109's fix, reconstructed. The matrix has a
    green row near [-0.115, +1.489, -0.374], so feeding it a triple whose green
    is pinned while red and blue are not renders neutral white as MAGENTA. The
    binary avoids this with a per-channel ceiling derived from the container
    maximum and the white-balance gains. That ceiling is NOT RECOVERABLE from
    the linear TIFF -- the writer has already clamped post-white-balance values
    to [0, 1], so every channel's ceiling reads back as exactly 1.0 and the
    per-channel information is gone. The best available reconstruction is to
    treat any pixel with a channel at the container top as pinned and pull all
    three down to its minimum channel. See BUILD-RENDER.md; this is a defect in
    the output path, not in this harness.
    """
    v = patch.astype(np.float64)
    pinned = np.any(v >= (65534.0 / 65535.0), axis=-1)
    if pinned.any():
        v = v.copy()
        v[pinned] = np.min(v[pinned], axis=-1, keepdims=True)
    v = v * gain
    if matrix is not None:
        v = v @ matrix.T
    return (srgb_encode(v) * 255.0 + 0.5).astype(np.uint8)


def resolve_matrix(name: str) -> np.ndarray | None:
    """Which colorimetric target the display crops are rendered to.

    `a7c2` is the default and is the honest one: every stack in the library is
    from the ILCE-7CM2, and camera-native RGB shown raw is grey-green and
    useless for judging a picture. `none` emits camera-native, which is what
    the file actually holds.
    """
    if name == "none":
        return None
    if name == "a7c2":
        return A7C2_CAM_TO_SRGB
    raise SystemExit(f"unknown --matrix {name!r}; use a7c2 or none")


def robust_sd(x: np.ndarray) -> float:

    """MAD-based sigma. Median-absolute-deviation rather than the plain SD so
    that one hot pixel or one speck of real structure in a 'flat' patch does
    not set the noise number."""
    med = np.median(x)
    return float(1.4826 * np.median(np.abs(x - med)))


def crop_stats(patch: np.ndarray, kind: str) -> dict:
    """Supporting numbers, computed in LINEAR. Not the verdict."""
    g = patch[..., 1]
    st = {"mean": float(g.mean())}
    if kind == "flat":
        # High-pass first, so scene shading does not read as noise.
        hp = g - ndimage.uniform_filter(g, size=9)
        st["noise_sd"] = robust_sd(hp)
    elif kind == "detail":
        st["hp_energy"] = float(np.std(ndimage.laplace(g)))
    elif kind == "edge":
        # Halo signature: how far the brighter side over-shoots its own plateau
        # near the boundary. Positive excursion above the 90th percentile of the
        # patch, measured only within a few pixels of the strongest gradient.
        gx = ndimage.sobel(g, axis=1, mode="reflect")
        gy = ndimage.sobel(g, axis=0, mode="reflect")
        near = ndimage.maximum_filter(np.hypot(gx, gy), size=17)
        band = near > np.percentile(near, 90)
        plateau = float(np.percentile(g, 90))
        st["edge_overshoot"] = float(np.max(g[band]) - plateau) if band.any() else 0.0
        st["hp_energy"] = float(np.std(ndimage.laplace(g)))
    return st


def label(img: Image.Image, text: str) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + 18), (16, 16, 16))
    out.paste(img, (0, 18))
    ImageDraw.Draw(out).text((4, 4), text, fill=(235, 235, 235))
    return out


def subjects_in(root: Path) -> list[Path]:
    return sorted(d for d in root.iterdir() if d.is_dir() and (d / "linear.tif").exists())


def cmd_plan(a: argparse.Namespace) -> int:
    root = Path(a.renders)
    plans_path = Path(a.plan)
    plans = json.loads(plans_path.read_text()) if plans_path.exists() and not a.force else {}
    for d in subjects_in(root):
        if d.name in plans and not a.force:
            print(f"keep   {d.name} (already planned)")
            continue
        lin = read_linear(d / "linear.tif")
        plans[d.name] = plan_subject(lin)
        n = sum(len(v) for v in plans[d.name]["rois"].values())
        print(f"plan   {d.name}: {n} ROIs, display gain {plans[d.name]['display_gain']:.3f}")
    plans_path.parent.mkdir(parents=True, exist_ok=True)
    plans_path.write_text(json.dumps(plans, indent=1))
    print(f"\nfrozen {plans_path}  ({len(plans)} subjects)")
    return 0


def cmd_crops(a: argparse.Namespace) -> int:
    root = Path(a.renders)
    plans = json.loads(Path(a.plan).read_text())
    outdir = Path(a.out) if a.out else root / "crops"
    outdir.mkdir(parents=True, exist_ok=True)
    mat = resolve_matrix(a.matrix)
    rows = []

    for d in subjects_in(root):
        plan = plans.get(d.name)
        if plan is None:
            print(f"SKIP   {d.name}: no frozen plan. Run `plan` first.")
            continue
        lin = read_linear(d / "linear.tif")
        if list(lin.shape[:2]) != plan["shape"]:
            print(
                f"SKIP   {d.name}: render is {lin.shape[:2]}, plan is {plan['shape']}. "
                "Frozen coordinates do not transfer across grids."
            )
            continue
        c = plan["crop"]
        sub = outdir / d.name
        sub.mkdir(parents=True, exist_ok=True)
        for kind, rois in plan["rois"].items():
            for i, (x, y) in enumerate(rois):
                patch = lin[y : y + c, x : x + c]
                st = crop_stats(patch, kind)
                png = sub / f"{kind}{i}.png"
                Image.fromarray(to_display(patch, plan["display_gain"], mat)).save(png)
                rows.append(
                    {"subject": d.name, "kind": kind, "i": i, "x": x, "y": y, "label": a.label, **st}
                )
        print(f"crops  {d.name}: {sum(len(v) for v in plan['rois'].values())} -> {sub}")

    tsv = outdir / f"crop-stats-{a.label}.tsv"
    if rows:
        keys = sorted({k for r in rows for k in r})
        head = ["subject", "kind", "i", "x", "y", "label"]
        keys = head + [k for k in keys if k not in head]
        with tsv.open("w", encoding="utf-8") as fh:
            fh.write("\t".join(keys) + "\n")
            for r in rows:
                fh.write("\t".join(str(r.get(k, "")) for k in keys) + "\n")
        print(f"\nstats  {tsv}")
    return 0


def cmd_compare(a: argparse.Namespace) -> int:
    """Side-by-side composites: baseline on the left, candidate on the right,
    identical crop coordinates and identical display gain. Any difference in
    the pair is a difference in the pixels."""
    base, cand = Path(a.baseline), Path(a.candidate)
    plans = json.loads(Path(a.plan).read_text())
    outdir = Path(a.out) if a.out else cand / "compare"
    outdir.mkdir(parents=True, exist_ok=True)
    mat = resolve_matrix(a.matrix)
    n = 0

    for d in subjects_in(cand):
        bt = base / d.name / "linear.tif"
        plan = plans.get(d.name)
        if plan is None or not bt.exists():
            print(f"SKIP   {d.name}: no baseline render or no frozen plan.")
            continue
        lb, lc = read_linear(bt), read_linear(d / "linear.tif")
        if lb.shape != lc.shape or list(lc.shape[:2]) != plan["shape"]:
            print(f"SKIP   {d.name}: shape mismatch {lb.shape} vs {lc.shape}.")
            continue
        c, gain = plan["crop"], plan["display_gain"]
        sub = outdir / d.name
        sub.mkdir(parents=True, exist_ok=True)
        for kind, rois in plan["rois"].items():
            for i, (x, y) in enumerate(rois):
                pb = to_display(lb[y : y + c, x : x + c], gain, mat)
                pc = to_display(lc[y : y + c, x : x + c], gain, mat)
                lft = label(Image.fromarray(pb), f"{a.baseline_label}  {kind}{i} @{x},{y}")
                rgt = label(Image.fromarray(pc), f"{a.candidate_label}  {kind}{i} @{x},{y}")
                comp = Image.new("RGB", (lft.width * 2 + 8, lft.height), (16, 16, 16))
                comp.paste(lft, (0, 0))
                comp.paste(rgt, (lft.width + 8, 0))
                comp.save(sub / f"{kind}{i}.png")
                n += 1
        print(f"cmp    {d.name}")
    print(f"\nwrote  {n} composites under {outdir}")
    return 0


def cmd_full(a: argparse.Namespace) -> int:
    """Whole-frame previews, downsampled, with the crop boxes drawn on.

    The crops answer "is the detail right". This answers "is the PICTURE
    right" -- gross misregistration, a black border from the field-of-view
    shrink, a colour disaster, a merge that fell apart across half the frame.
    Those are invisible at 100% and obvious here, and they are the first thing
    to rule out when someone says a stack is unusable.
    """
    root = Path(a.renders)
    plans = json.loads(Path(a.plan).read_text()) if Path(a.plan).exists() else {}
    outdir = Path(a.out) if a.out else root / "full"
    outdir.mkdir(parents=True, exist_ok=True)
    mat = resolve_matrix(a.matrix)

    for d in subjects_in(root):
        lin = read_linear(d / "linear.tif")
        plan = plans.get(d.name)
        gain = plan["display_gain"] if plan else DISPLAY_TARGET / max(
            float(np.percentile(luma(lin), DISPLAY_PCT)), 1e-6
        )
        img = Image.fromarray(to_display(lin, gain, mat))
        if plan and list(lin.shape[:2]) == plan["shape"]:
            dr = ImageDraw.Draw(img)
            colours = {"edge": (255, 64, 64), "flat": (64, 160, 255), "detail": (255, 220, 0)}
            c = plan["crop"]
            for kind, rois in plan["rois"].items():
                for i, (x, y) in enumerate(rois):
                    dr.rectangle([x, y, x + c, y + c], outline=colours.get(kind, (255, 255, 255)), width=6)
                    dr.text((x + 10, y + 10), f"{kind}{i}", fill=colours.get(kind, (255, 255, 255)))
        img.thumbnail((a.width, a.width), Image.Resampling.LANCZOS)
        img.save(outdir / f"{d.name}.png")
        print(f"full   {d.name}  {lin.shape[1]}x{lin.shape[0]} -> {img.width}x{img.height}")
    print(f"\nwrote  previews under {outdir}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plan", default="C:/dev/strehl-out/roi-plan.json",
                   help="frozen ROI plan; created by `plan`, consumed by everything else")
    sp = p.add_subparsers(dest="cmd", required=True)

    q = sp.add_parser("plan", help="freeze crop coordinates from a baseline render set")
    q.add_argument("--renders", required=True)
    q.add_argument("--force", action="store_true", help="re-plan subjects that already have one")
    q.set_defaults(fn=cmd_plan)

    q = sp.add_parser("crops", help="emit 100%% crops at the frozen coordinates")
    q.add_argument("--renders", required=True)
    q.add_argument("--out")
    q.add_argument("--label", default="run")
    q.add_argument("--matrix", default="a7c2", choices=["a7c2", "none"],
                   help="colorimetric target for DISPLAY only; measurement stays linear camera RGB")
    q.set_defaults(fn=cmd_crops)

    q = sp.add_parser("compare", help="baseline vs candidate side-by-side composites")
    q.add_argument("--baseline", required=True)
    q.add_argument("--candidate", required=True)
    q.add_argument("--out")
    q.add_argument("--baseline-label", default="BASELINE")
    q.add_argument("--candidate-label", default="CANDIDATE")
    q.add_argument("--matrix", default="a7c2", choices=["a7c2", "none"])
    q.set_defaults(fn=cmd_compare)

    q = sp.add_parser("full", help="whole-frame previews with the crop boxes drawn on")
    q.add_argument("--renders", required=True)
    q.add_argument("--out")
    q.add_argument("--width", type=int, default=1600)
    q.add_argument("--matrix", default="a7c2", choices=["a7c2", "none"])
    q.set_defaults(fn=cmd_full)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
