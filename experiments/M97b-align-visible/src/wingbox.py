"""Does the working metric agree with the eye, at the exact crop the eye judged?

width.py's whole-frame answer is 1.0179 -- the metric ranks the aligned render
sharper, all controls pass, and the effect is real but small. The visible
difference at the wing-venation crop is NOT small. Either the metric is
under-reading, or the whole-frame median is diluted by the ~99% of edges where
registration changed nothing.

This distinguishes those two. It runs the same instrument, unchanged, inside
each of the four 640x640 boxes the orchestrator eyeballed and I opened, and
inside a deliberately chosen low-drift box as a spatial control.

Crop origins are recomputed from ORCH-drift-check/crops.py's own arithmetic
(S = W/1400 against a 1400px thumbnail) rather than retyped, so a
transcription error cannot put me on different pixels than the eye judged.

The orchestrator explicitly declined to vouch for the leg-spines crop --
"treat 1.1288 as unverified", because it may contain different content at its
right edge. Co-location is therefore VERIFIED here per box by NCC, and the
verification carries its own plant: a deliberately displaced box must be
rejected, or the check is decorative.
"""

import json
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from width import load, measure, pick_edges  # noqa: E402

N = 640


def ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d else 0.0


def boxes(w):
    s = w / 1400.0
    return {
        "wing-venation": (int(300 * s), int(100 * s)),
        "thorax-hair": (int(800 * s), int(300 * s)),
        "leg-spines": (int(250 * s), int(560 * s)),
        "head-eye": (int(900 * s), int(650 * s)),
    }


def run_box(a, z, x, y, label, rows):
    ca, cz = a[y:y + N, x:x + N], z[y:y + N, x:x + N]
    co = ncc(ca.astype(np.float64), cz.astype(np.float64))
    # Co-location plant: the same box displaced by 60 px must score clearly
    # lower, or NCC here is not actually testing co-location.
    cd = ncc(ca.astype(np.float64),
             z[y + 60:y + 60 + N, x + 60:x + 60 + N].astype(np.float64))
    print(f"\n########## {label}  origin x={x} y={y} ##########")
    print(f"    co-location NCC {co:.4f}   displaced-by-60px plant {cd:.4f}"
          f"   {'OK' if co > cd + 0.05 else 'CO-LOCATION NOT ESTABLISHED'}")
    ys, xs, ny, nx = pick_edges((ca + cz) * 0.5, 4000)
    if ys.size < 200:
        print("    too few edges in this box; skipped")
        return None
    sub = []
    measure(cz, cz, f"{label} PLACEBO", sub, ys, xs, ny, nx)
    measure(gaussian_filter(ca, 1.0), cz, f"{label} DIRECTION PLANT",
            sub, ys, xs, ny, nx)
    t = measure(ca, cz, f"{label} TREATMENT aligned vs zoomnull",
                sub, ys, xs, ny, nx)
    rows.append(dict(box=label, x=x, y=y, ncc=co, ncc_displaced=cd,
                     placebo=sub[0]["median_paired_ratio"],
                     direction_plant=sub[1]["median_paired_ratio"],
                     treatment=t))
    return t


def main(argv):
    d = r"C:\dev\strehl-out\M86-align"
    a = load(rf"{d}\bee-3-ALIGNED.tif")
    z = load(rf"{d}\bee3-zoomnull.tif")
    print("dims", a.shape)
    rows = []
    for label, (x, y) in boxes(a.shape[1]).items():
        run_box(a, z, x, y, label, rows)
    # Spatial control: a box straddling the centre of the similarity, where
    # residual misregistration is near zero by construction and the metric
    # should therefore find nothing.
    run_box(a, z, (a.shape[1] - N) // 2, (a.shape[0] - N) // 2,
            "CENTRE-CONTROL (drift ~0 here by construction)", rows)

    print("\n=== SUMMARY (paired width ratio null/aligned; >1 = aligned sharper) ===")
    print(f"  {'box':<44} {'placebo':>8} {'dir-plant':>10} {'treatment':>10}")
    for r in rows:
        print(f"  {r['box']:<44} {r['placebo']:>8.4f} "
              f"{r['direction_plant']:>10.4f} {r['treatment']:>10.4f}")
    json.dump(rows, open(argv[1], "w"), indent=1)
    print("\nwrote", argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
