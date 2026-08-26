"""BUILD-HULL: the out-of-hull instrument for the real pyramid merge.

WHAT IT ANSWERS
    For each output sample, is the merged value inside `[min_k x_k, max_k x_k]`
    taken over the ALIGNED, WARPED input frames as the merge actually saw them?

WHY THIS HULL IS HONEST
    The frames are not raw files, and they are not my own reimplementation of a
    warp. Each is rendered by strehl itself: `STREHL_ONLY_FRAME=k` plus a
    one-frame `STREHL_WARPMAP` sidecar carrying the 205-frame solve's own
    placement for frame k, copied verbatim as f64 bit patterns (warpframes.py).
    Every frame therefore passes through strehl's own gather and its own
    Catmull-Rom kernel and lands on the reference grid the merge lands on. The
    merge itself is rendered under the same sidecar and logs

        alignment : ON (sidecar-override), reference frame 102, 205 placed / 0 refused

    and comes out 2344x3520x3 -- the same geometry as the frames, so the merge
    does not crop relative to the basis. Comparing against unwarped frames --
    the failure mode ORCH named, and the main way this instrument could lie --
    is structurally not what this does.

THE PER-BAND TEST, AND WHY MY LAPLACIAN NEED NOT MATCH THE RUST ONE
    This is the load-bearing argument, so it is stated in full.

    Let `L` be ANY linear operator (my band `b` extractor is one: repeated
    5-tap blur and subtraction, both linear). Suppose the merge were a single
    convex combination with ONE weight vector `w_k >= 0, sum_k w_k = 1` shared
    across all bands, so `O = sum_k w_k F_k`. Then by linearity

        L(O) = L(sum_k w_k F_k) = sum_k w_k L(F_k)

    which is a convex combination of `{L(F_k)}` and therefore lies inside
    `[min_k L(F_k), max_k L(F_k)]`. NECESSARILY. For every band, for every
    linear L, for every pixel.

    So a per-band violation under MY Laplacian is proof that the merge is NOT a
    single convex combination with weights shared across bands. I do not need my
    decomposition to match `pyramid.rs`'s -- I only need it to be linear, and it
    is. This converts "I cannot read the merge's internal coefficients" from a
    limitation into an irrelevance.

    What the per-band numbers do NOT do: identify which internal Rust band
    carries the defect. My band `b` is my own operator, not theirs. The claim is
    about the SPATIAL FREQUENCY of the excursion, not about their array indices.

COMMISSIONING (--commission is not a separate mode; these are separate arms)
    C1  near-uniform-mean merge must read ~zero. `--pyramid-exponent 0` is
        REFUSED by the CLI ("must be finite and positive"), so the reachable
        point is exponent 1e-6 with sharpen 1.0 -- a flat ramp, so every band
        shares one near-uniform weighting, which is the structural property the
        control actually tests.
    C2  single-frame passthrough.
    C3  a planted offset recovered at the right place, sign, and count (--plant).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import tifffile

CHANNELS = ("R", "G", "B")

# ORCH quoted the dark-subject bbox in FULL-RESOLUTION coordinates:
#     y 744..4687, x 1668..5104
# These renders are 2344x3520, which is exactly half of the 4688x7040 full
# frame, so the bbox is halved here. Both forms are printed.
BBOX_FULL = (744, 4687, 1668, 5104)
BBOX = tuple(v // 2 for v in BBOX_FULL)

SPAN_FLOOR = 1.0  # DN; below this a hull is too thin for a ratio to mean much


def load16(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a


def bands_of(a: np.ndarray, levels: int) -> list[np.ndarray]:
    """Laplacian pyramid held at full resolution (no decimation), so every band
    is comparable pixel-for-pixel and the bands sum back to the input exactly.
    Every step is linear -- see the module docstring."""
    k = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32)
    k /= k.sum()
    cur = a.astype(np.float32)
    out = []
    for _ in range(levels):
        lo = cur
        for ax in (0, 1):
            pad = [(0, 0)] * cur.ndim
            pad[ax] = (2, 2)
            p = np.pad(lo, pad, mode="reflect")
            acc = np.zeros_like(lo)
            sl = [slice(None)] * cur.ndim
            for i, w in enumerate(k):
                sl[ax] = slice(i, i + lo.shape[ax])
                acc += w * p[tuple(sl)]
            lo = acc
        out.append(cur - lo)
        cur = lo
    out.append(cur)
    return out


def score(viol: np.ndarray, span: np.ndarray, guard: float) -> dict:
    """Five-outcome partition, asserted to sum. A sample is inside, inside the
    guard band either way, or genuinely below/above."""
    tot = int(viol.size)
    inside = int(np.count_nonzero(viol == 0))
    gb = int(np.count_nonzero((viol < 0) & (viol >= -guard)))
    ga = int(np.count_nonzero((viol > 0) & (viol <= guard)))
    below = int(np.count_nonzero(viol < -guard))
    above = int(np.count_nonzero(viol > guard))
    assert inside + gb + ga + below + above == tot, "partition does not sum"

    bad = (viol < -guard) | (viol > guard)
    thin = int(np.count_nonzero(bad & (span < SPAN_FLOOR)))
    usable = bad & (span >= SPAN_FLOOR)
    if usable.any():
        rel = np.abs(viol[usable]) / span[usable]
        worst, p99 = float(rel.max()), float(np.percentile(rel, 99))
    else:
        worst = p99 = 0.0
    return dict(
        total=tot, inside=inside, guard=gb + ga, below=below, above=above,
        rate=100.0 * (below + above) / tot,
        worst_span=worst, p99_span=p99, thin=thin,
        mean_dn=float(viol[bad].mean()) if bad.any() else 0.0,
        min_dn=float(viol[bad].min()) if bad.any() else 0.0,
        max_dn=float(viol[bad].max()) if bad.any() else 0.0,
    )


HDR = (f"  {'region':<26} {'ch':<4} {'samples':>11} {'inside':>11} {'guard':>7} "
       f"{'below':>9} {'above':>9} {'rate':>9} {'worst/sp':>9} {'p99/sp':>8} "
       f"{'thin':>6} {'meanDN':>8} {'minDN':>8} {'maxDN':>8}")


def row(region: str, ch: str, r: dict) -> str:
    return (f"  {region:<26} {ch:<4} {r['total']:>11} {r['inside']:>11} {r['guard']:>7} "
            f"{r['below']:>9} {r['above']:>9} {r['rate']:>8.4f}% {r['worst_span']:>9.3f} "
            f"{r['p99_span']:>8.3f} {r['thin']:>6} {r['mean_dn']:>8.1f} "
            f"{r['min_dn']:>8.0f} {r['max_dn']:>8.0f}")


def regions_for(shape: tuple) -> dict:
    y0, y1, x0, x1 = BBOX
    return {"whole frame (control)": (slice(None), slice(None)),
            f"bbox y{y0}..{y1} x{x0}..{x1}": (slice(y0, y1 + 1), slice(x0, x1 + 1))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--levels", type=int, default=7)
    ap.add_argument("--guard", type=float, default=1.0)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--bands", action="store_true")
    ap.add_argument("--plant", type=float, default=0.0)
    ap.add_argument("--plant-box", default="1000,1200,1000,1200")
    a = ap.parse_args()

    fdir = Path(a.frames)
    have = sorted(fdir.glob("f*.tiff"))
    print(f"=== BUILD-HULL hull instrument :: {a.tag} ===")
    print(f"  merged            : {a.merged}")
    print(f"  frame basis       : {fdir}  (strehl-rendered, sidecar-warped)")
    print(f"  guard band        : +/- {a.guard:g} DN")
    print(f"  bbox full-res     : y{BBOX_FULL[0]}..{BBOX_FULL[1]} x{BBOX_FULL[2]}..{BBOX_FULL[3]}")
    print(f"  bbox here (half)  : y{BBOX[0]}..{BBOX[1]} x{BBOX[2]}..{BBOX[3]}")
    print(f"  frames requested  : {a.n}")
    print(f"  frames present    : {len(have)}")
    print(f"  frames MISSING    : {a.n - len(have)}")
    assert len(have) >= a.n, "refusing to fold an incomplete frame basis"

    m = load16(Path(a.merged)).astype(np.float32)
    if a.plant:
        py0, py1, px0, px1 = (int(t) for t in a.plant_box.split(","))
        m[py0:py1, px0:px1, :] += a.plant
        print(f"  PLANT             : {a.plant:+.0f} DN into y{py0}:{py1} x{px0}:{px1} "
              f"= {(py1 - py0) * (px1 - px0) * 3} samples")

    print("\n  folding whole-image hull over the warped frames ...")
    lo = hi = None
    for k in range(a.n):
        f = load16(fdir / f"f{k:04d}.tiff")
        if lo is None:
            lo, hi = f.copy(), f.copy()
        else:
            np.minimum(lo, f, out=lo)
            np.maximum(hi, f, out=hi)
        if (k + 1) % 50 == 0:
            print(f"    {k + 1}/{a.n}", flush=True)
    lo = lo.astype(np.float32)
    hi = hi.astype(np.float32)
    span = hi - lo
    viol = np.where(m < lo, m - lo, np.where(m > hi, m - hi, 0.0))

    print(f"\n  --- WHOLE IMAGE, per channel ---\n{HDR}")
    for rname, (ys, xs) in regions_for(m.shape).items():
        for ci, cn in enumerate(CHANNELS + ("all",)):
            if cn == "all":
                v, s = viol[ys, xs, :], span[ys, xs, :]
            else:
                v, s = viol[ys, xs, ci], span[ys, xs, ci]
            print(row(rname, cn, score(v, s, a.guard)))

    if a.bands:
        print(f"\n  --- PER BAND ({a.levels} detail + 1 base, my own linear Laplacian) ---")
        print("  Valid because ANY linear operator applied to a shared-weight convex")
        print("  combination stays in the hull. See module docstring.")
        mb = bands_of(load16(Path(a.merged)), a.levels)
        blo: list = [None] * (a.levels + 1)
        bhi: list = [None] * (a.levels + 1)
        for k in range(a.n):
            for b, v in enumerate(bands_of(load16(fdir / f"f{k:04d}.tiff"), a.levels)):
                if blo[b] is None:
                    blo[b], bhi[b] = v.copy(), v.copy()
                else:
                    np.minimum(blo[b], v, out=blo[b])
                    np.maximum(bhi[b], v, out=bhi[b])
            if (k + 1) % 25 == 0:
                print(f"    band-folded {k + 1}/{a.n}", flush=True)
        print(HDR)
        for b in range(a.levels + 1):
            nm = "base(coarsest)" if b == a.levels else f"detail{b}" + ("=finest" if b == 0 else "")
            sp = bhi[b] - blo[b]
            vv = np.where(mb[b] < blo[b], mb[b] - blo[b],
                          np.where(mb[b] > bhi[b], mb[b] - bhi[b], 0.0))
            for rname, (ys, xs) in regions_for(m.shape).items():
                short = "whole" if rname.startswith("whole") else "bbox"
                for ci, cn in enumerate(CHANNELS):
                    print(row(f"{nm} {short}", cn, score(vv[ys, xs, ci], sp[ys, xs, ci], a.guard)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
