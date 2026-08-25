"""E3 -- the elected-index read, on an index map PROVEN to be the shipped path.

PROVENANCE FIRST (discipline 830, which exists because an arm was mistaken for
the shipped path).  M96's `elected-index.tif` is uint8 RGB -- a colour-mapped
PREVIEW, not raw indices -- and M111's NPY dumps are a different subject with
alignment ON.  Neither can be used.  So this milestone re-rendered
`bee-3-cpl` at gate 4.0 with alignment off and `--index-map`, and the merged
TIFF it produced is BYTE-IDENTICAL to the shipped `armM4-gate4-binlin.tif`
(sha256 e6132cd07b1348c4...).  The index map beside it is therefore the shipped
path's own election, not an approximation of it.

    invocation: C:\\dev\\strehl-out\\M121\\e3\\invocation.txt
    log:        C:\\dev\\strehl-out\\M121\\e3\\render.log

THE PREDICTION.  Under ORCH's mechanism a pixel within one focus-measure window
radius of a strong edge does not elect the frame its OWN depth favours; it
inherits the edge's election, because the windowed focus measure at that pixel
is dominated by the edge.  So walking outward along the edge normal, the
elected index should agree with the edge's own election out to about
WINDOW_RADIUS = 13 px (focus.rs:83) and then break away.

WHAT WOULD FALSIFY IT (rule 13/20).  Election that agrees with the edge only
right at the edge and decorrelates within a pixel or two; or agreement that
extends far past 22 px, which is the largest radius any constant in the merge
can produce (SOBEL 1 + WINDOW 13 + REGULARISER 8).

THE CONTROL THAT MAKES IT MEAN ANYTHING.  Agreement decays outward at ANY edge
for a trivial reason: neighbouring pixels of a real object are at similar
depths, so they elect similar frames anyway.  The control is to measure the
same agreement profile along a direction with NO edge -- random orientations
from the same seed points -- and quote the DIFFERENCE.  Without that, a decay
length is just the depth map's autocorrelation length.

Run:  python experiments/M121-halo-polarity/e3_election.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from e2_polarity import (  # noqa: E402
    FLAT_TOL, GRAD_PCT, ISO, MAX_EDGES, MIN_AMPLITUDE, WINDOW_RADIUS,
    commissioned_max_rise, focus_field, make_classifier,
)
from m121_io import FRAMES, OUT, arm_path, load_u16, luma  # noqa: E402
from runner import scan  # noqa: E402

E3 = pathlib.Path(r"C:\dev\strehl-out\M121\e3")
IDX = E3 / "index.tif"
REPRO = E3 / "armM4-repro.tif"
DMAX = 40.0
DSTEP = 1.0
TOL = 1                 # frames; |i - i_edge| <= TOL counts as "same election"


def bilinear_idx(idx, y, x):
    """Nearest-neighbour read.  The index map is CATEGORICAL -- interpolating
    frame numbers would invent frames that were never elected."""
    h, w = idx.shape
    yy = np.clip(np.rint(y).astype(int), 0, h - 1)
    xx = np.clip(np.rint(x).astype(int), 0, w - 1)
    return idx[yy, xx]


def walk(idx, edges, rng, randomise=False, flat_seeds=None):
    """Agreement-with-the-start profile, walking outward along +normal.

    Returns agreement with the START election and with the FAR election, so
    the crossover between them is visible: under the mechanism a surround
    pixel elects the EDGE's frame while the edge is inside its focus window,
    and its own frame after that.
    """
    d = np.arange(0.0, DMAX + 1e-9, DSTEP)
    keep_edge, keep_far = [], []
    src = flat_seeds if flat_seeds is not None else edges
    for row in src:
        y, x = float(row[0]), float(row[1])
        if flat_seeds is None:
            gx, gy = float(row[2]), float(row[3])
            n = np.hypot(gx, gy)
            if n == 0:
                continue
            nx, ny = gx / n, gy / n
        else:
            nx = ny = 0.0
        if randomise or flat_seeds is not None:
            a = rng.uniform(0, 2 * np.pi)
            nx, ny = np.cos(a), np.sin(a)
        line = bilinear_idx(idx, y + d * ny, x + d * nx)
        ok = line != 65535
        if not ok.all():
            continue
        i0 = int(line[0])
        i_far = int(line[-1])
        keep_edge.append((np.abs(line.astype(np.int32) - i0) <= TOL).astype(np.float64))
        keep_far.append((np.abs(line.astype(np.int32) - i_far) <= TOL).astype(np.float64))
    if not keep_edge:
        return d, np.zeros_like(d), np.zeros_like(d), 0
    return (d, np.stack(keep_edge).mean(axis=0), np.stack(keep_far).mean(axis=0),
            len(keep_edge))


def half_width(d, a, frac):
    """Distance at which `a` first falls below `frac` of its d=0 value."""
    target = frac * a[0]
    for i in range(1, len(d)):
        if a[i] < target:
            t = (a[i - 1] - target) / max(a[i - 1] - a[i], 1e-12)
            return float(d[i - 1] + t * (d[i] - d[i - 1]))
    return float("nan")


def main():
    if not IDX.exists():
        raise SystemExit(f"missing {IDX} -- run the E3 render first")

    import tifffile
    idx = tifffile.imread(IDX)
    assert idx.dtype == np.uint16, f"index map is {idx.dtype}, expected uint16"
    print(f"index map {IDX}: {idx.shape} {idx.dtype} "
          f"range {idx[idx != 65535].min()}..{idx[idx != 65535].max()} "
          f"no-frame={100*np.mean(idx == 65535):.3f}%")

    import hashlib
    ha = hashlib.sha256(REPRO.read_bytes()).hexdigest()
    hb = hashlib.sha256(pathlib.Path(arm_path("armM4-gate4-binlin")).read_bytes()).hexdigest()
    print(f"repro sha256   {ha[:16]}")
    print(f"shipped sha256 {hb[:16]}")
    if ha != hb:
        raise SystemExit("repro is NOT byte-identical to the shipped arm -- "
                         "this index map cannot be attributed to the shipped path")
    print("  -> BYTE-IDENTICAL: this index map IS the shipped path's election\n")

    max_rise = commissioned_max_rise()
    merged = luma(load_u16(arm_path("armM4-gate4-binlin")))
    frames = {n: luma(load_u16(arm_path(n))) for n in FRAMES}
    fmax = np.max(np.stack([focus_field(f) for f in frames.values()]), axis=0)
    classify = make_classifier(fmax)

    r = scan(merged, label="E3 edges", grad_percentile=GRAD_PCT,
             max_edges=MAX_EDGES, isolation_frac=ISO, flat_tol=FLAT_TOL,
             classify=classify, max_rise=max_rise, min_amplitude=MIN_AMPLITUDE,
             collect_edges=True, verbose=False)
    edges = r["kept_edges"]
    print(f"{edges.shape[0]} accepted sharp silhouette edges (the E2 donor list)")

    rng = np.random.default_rng(4242)
    d, a_edge, a_far, n1 = walk(idx, edges, rng, randomise=False)

    # THE CONTROL.  Election also decorrelates with distance for a trivial
    # reason: real depth varies smoothly, so nearby pixels elect nearby frames
    # anyway.  Seeding in FLAT BACKGROUND (no edge within the window) and
    # walking a random direction measures that depth-map autocorrelation
    # length on its own.  If the edge-driven fall-off is NOT much shorter than
    # this, E3's number is the depth map's length scale and not the window's.
    from scipy.ndimage import uniform_filter
    gm = uniform_filter(np.abs(np.diff(merged, axis=1, prepend=merged[:, :1])), size=33)
    h, w = idx.shape
    b = int(DMAX) + 8
    ys = rng.integers(b, h - b, size=8000)
    xs = rng.integers(b, w - b, size=8000)
    sel = gm[ys, xs] < np.percentile(gm, 10)
    flat_seeds = np.stack([ys[sel][:400], xs[sel][:400]], axis=1).astype(np.float64)
    _, c_flat, _, n_flat = walk(idx, edges, rng, flat_seeds=flat_seeds)

    res = {"window_radius_focus_rs": WINDOW_RADIUS, "tol_frames": TOL,
           "n_edges": int(n1), "n_flat_control": int(n_flat), "d": d.tolist(),
           "agree_with_edge": a_edge.tolist(),
           "agree_with_far": a_far.tolist(),
           "agree_flat_control": c_flat.tolist()}

    print("\n=== election agreement walking outward along the edge normal ===")
    print("  d(px)   agree w/ EDGE   agree w/ FAR   flat-bg control")
    for i, dd in enumerate(d):
        if dd % 2 == 0 and dd <= 30:
            print(f"  {dd:5.0f}       {a_edge[i]:.4f}         {a_far[i]:.4f}        {c_flat[i]:.4f}")

    cross = np.nan
    for i in range(1, len(d)):
        if a_far[i] > a_edge[i]:
            cross = float(d[i])
            break
    for frac, key in ((0.5, "w50"), (0.1, "w10")):
        res[f"edge_{key}"] = half_width(d, a_edge, frac)
        res[f"flat_{key}"] = half_width(d, c_flat, frac)
    res["crossover"] = cross

    print(f"\n  agreement-with-edge half-width : {res['edge_w50']:.2f} px")
    print(f"  agreement-with-edge 10% width  : {res['edge_w10']:.2f} px")
    print(f"  crossover (far overtakes edge) : {cross:.2f} px")
    print(f"  FLAT-BG CONTROL half-width     : {res['flat_w50']:.2f} px  (n={n_flat})")
    print(f"  FLAT-BG CONTROL 10% width      : {res['flat_w10']:.2f} px")
    print(f"\n  focus.rs:83 WINDOW_RADIUS      : {WINDOW_RADIUS} px")
    print(f"  DERIVED total spill            : 22 px (SOBEL 1 + WINDOW 13 + REGULARISER 8)")
    print(f"  E2 measured rim w50 / cutoff   : 10.00 / 13.25 px")

    (OUT / "e3-election.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT / 'e3-election.json'}")


if __name__ == "__main__":
    main()
