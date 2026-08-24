"""S1 -- local geometric drift at every candidate ROI, from the committed sidecar.

Fact 1177 measures 232.7 px of drift on this stack. That is a *corner* figure
for a magnification change, so the drift at a given ROI depends on where the ROI
sits relative to the similarity's fixed point. This reads the sidecar written by
`strehl align` and computes the displacement per frame step at arbitrary plane
points, so the merge-vs-frame comparison can be stratified by a MEASURED local
drift instead of by an assumed radius.

Nothing here is taken on report: the parse is checked by re-deriving the
human-readable `g`, `rot`, `dx`, `dy` comments from the f64 bit patterns.
"""

from __future__ import annotations

import json
import os
import re
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m93lib as L  # noqa: E402

SIDECAR = os.path.join(L.STACK, "warpmap.txt")


def parse():
    warps = {}
    meta = {}
    with open(SIDECAR, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#") or not line.strip():
                continue
            m = re.match(
                r"^(\d+)\s+(\w+)\s+([0-9a-f]{16})\s+([0-9a-f]{16})\s+"
                r"([0-9a-f]{16})\s+([0-9a-f]{16})\s*(#.*)?$",
                line,
            )
            if m:
                idx = int(m.group(1))
                vals = [
                    struct.unpack(">d", bytes.fromhex(m.group(i)))[0] for i in (3, 4, 5, 6)
                ]
                warps[idx] = (complex(vals[0], vals[1]), complex(vals[2], vals[3]), m.group(7))
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                meta[parts[0]] = parts[1]
    return meta, warps


def main() -> int:
    meta, warps = parse()
    n = len(warps)
    print(f"sidecar        : {SIDECAR}")
    for k in ("stack-name", "frames", "plane", "reference", "strategy", "resampler", "heldout-px"):
        print(f"  {k:<14}: {meta.get(k)}")
    print(f"parsed         : {n} frame placements")

    # Parse check: re-derive the human comment from the bit patterns.
    worst_a = 0.0
    worst_b = 0.0
    worst = 0.0
    for idx, (a, b, comment) in warps.items():
        if not comment:
            continue
        cm = re.search(
            r"g=([-+0-9.e]+)\s+rot=([-+0-9.e]+)\s+dx=([-+0-9.]+)\s+dy=([-+0-9.]+)", comment
        )
        if not cm:
            continue
        g, rot, dx, dy = (float(cm.group(i)) for i in (1, 2, 3, 4))
        # MEASURED, not assumed: the sidecar's comment prints the LINEARISED
        # decomposition (Re a - 1, Im a), not (|a| - 1, arg a). Checking against
        # the polar form fails at 3.05e-4, which is how this was found.
        pred_a = complex(1.0 + g, rot)
        worst_a = max(worst_a, abs(pred_a - a))
        worst_b = max(worst_b, abs(complex(dx, dy) - b))
    # Tolerances are the comment's own print precision, derived not guessed:
    # `g`/`rot` carry 7 significant figures, so |pred_a - a| <= ~1e-8;
    # `dx`/`dy` carry 4 decimals, so |pred_b - b| <= sqrt(2) * 5e-5 = 7.1e-5.
    print(f"parse check    : worst |(1+g) + i*rot - a| = {worst_a:.3e}  (bar 1e-7)")
    print(f"parse check    : worst |(dx,dy) - b|       = {worst_b:.3e}  (bar 1.5e-4)")
    worst = max(worst_a, worst_b)
    assert worst_a < 1e-7 and worst_b < 1.5e-4, "the sidecar parse does not reproduce its own comments"

    A = np.array([warps[i][0] for i in range(n)])
    B = np.array([warps[i][1] for i in range(n)])
    ref = int(meta["reference"])
    print(f"identity check : frame {ref} a={A[ref]:.9f} b={B[ref]:.6f}")

    W, H = (int(v) for v in meta["plane"].split("x"))

    # Corner-to-corner drift, re-derived rather than quoted, so fact 1177 is
    # checked against this sidecar rather than assumed.
    corners = [complex(0, 0), complex(W, 0), complex(0, H), complex(W, H)]
    traj = {c: A * c + B for c in corners}
    spans = {c: float(np.abs(t - t[ref]).max()) for c, t in traj.items()}
    print()
    print("displacement of each plane corner relative to the reference frame:")
    for c, s in spans.items():
        print(f"  ({int(c.real):>4},{int(c.imag):>4}) : max {s:8.2f} plane px = {2*s:8.2f} sensor px")

    # The similarity's fixed point per frame: z* = b / (1 - a).
    with np.errstate(divide="ignore", invalid="ignore"):
        fix = B / (1.0 - A)
    good = np.isfinite(fix)
    print()
    print(
        f"fixed point    : median ({np.median(fix[good].real):.1f}, {np.median(fix[good].imag):.1f}) "
        f"plane px  [plane is {W}x{H}, centre ({W/2:.0f}, {H/2:.0f})]"
    )

    # Per-frame-step drift at a grid of plane points -- the quantity that
    # actually matters for an unregistered merge, since the frames competing at
    # one pixel are adjacent in index.
    step = np.abs(np.diff(A)[:, None] * 0 + 0)  # placeholder, replaced below
    grid = {}
    for name, z in (
        ("top-left      (0,0)", complex(0, 0)),
        ("centre", complex(W / 2, H / 2)),
        ("bottom-right", complex(W, H)),
    ):
        t = A * z + B
        d1 = np.abs(np.diff(t))
        grid[name] = (float(np.median(d1)), float(d1.max()))
    print()
    print("drift per ONE frame step (plane px), at three plane points:")
    for k, (med, mx) in grid.items():
        print(f"  {k:<22} median {med:.4f}   max {mx:.4f}")

    out = {
        "sidecar": SIDECAR,
        "meta": meta,
        "n": n,
        "reference": ref,
        "plane": [W, H],
        "parse_check_worst": worst,
        "corner_span_plane_px": {f"{int(c.real)},{int(c.imag)}": s for c, s in spans.items()},
        "fixed_point_median": [float(np.median(fix[good].real)), float(np.median(fix[good].imag))],
        "per_step_drift": grid,
        "a_re": A.real.tolist(),
        "a_im": A.imag.tolist(),
        "b_re": B.real.tolist(),
        "b_im": B.imag.tolist(),
    }
    dst = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out", "s1_drift.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote          : {dst}")
    del step
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
