"""Parse the real 299-frame warp sidecar and report the sub-pixel phase it imposes.

INPUT DATA ONLY. This reads the aligner's own output and reports what geometry
the merge actually applies. It measures nothing about sharpness, so running it
before pre-registration does not contaminate anything.

Why it matters: the orchestrator's proposed fix removes the coverage SCALE but
keeps the per-frame WARP. If the per-frame warps happen to be near-integer, the
fix works. If they are uniformly distributed in phase, it cannot, because a
Catmull-Rom gather at a non-integer phase costs the same whatever put it there.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

MAP = Path(r"D:\personal\macro\bee-3-cpl\warpmap.txt")
OUT = Path(__file__).resolve().parents[1] / "out" / "w0_warpstats.json"


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def main():
    if not MAP.exists():
        sys.exit(f"missing {MAP}")
    plane_w = plane_h = ref = None
    rows = []
    for line in MAP.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("plane "):
            plane_w, plane_h = (int(v) for v in s.split()[1].split("x"))
        elif s.startswith("reference "):
            ref = int(s.split()[1])
        elif s.startswith("#") or not s:
            continue
        else:
            p = s.split()
            if len(p) >= 6 and p[1] == "placed":
                rows.append((int(p[0]), f64(p[2]), f64(p[3]), f64(p[4]), f64(p[5])))

    print(f"plane {plane_w}x{plane_h}   reference {ref}   placed {len(rows)}")
    res = {"plane": [plane_w, plane_h], "reference": ref, "placed": len(rows)}

    cx, cy = plane_w * 0.5, plane_h * 0.5
    probes = {"centre": (cx, cy), "mid-radius": (cx + plane_w * 0.25, cy)}

    scale = np.array([np.hypot(a_re, a_im) for _, a_re, a_im, _, _ in rows])
    print(f"\nper-frame scale-1 : min {scale.min() - 1:+.3e}  "
          f"max {scale.max() - 1:+.3e}")
    res["scale_minus_1_min"] = float(scale.min() - 1)
    res["scale_minus_1_max"] = float(scale.max() - 1)

    for pname, (px, py) in probes.items():
        fx, fy, dxs = [], [], []
        for _, a_re, a_im, b_re, b_im in rows:
            dx = a_re * (px - cx) - a_im * (py - cy) + cx + b_re - px
            dy = a_im * (px - cx) + a_re * (py - cy) + cy + b_im - py
            dxs.append((dx, dy))
            fx.append(dx - np.floor(dx))
            fy.append(dy - np.floor(dy))
        fx, fy = np.array(fx), np.array(fy)
        dist = np.maximum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
        near = float((dist < 0.05).mean())
        mag = np.array([np.hypot(a, b) for a, b in dxs])
        print(f"\n{pname}: displacement of the reference grid into each frame")
        print(f"  |displacement| : mean {mag.mean():.2f} px, max {mag.max():.2f} px")
        print(f"  frac(dx) mean {fx.mean():.4f}  sd {fx.std():.4f}")
        print(f"  frac(dy) mean {fy.mean():.4f}  sd {fy.std():.4f}")
        print(f"  distance to nearest integer: mean {dist.mean():.4f} px, "
              f"median {np.median(dist):.4f} px")
        print(f"  fraction within 0.05 px of integer: {100 * near:.1f}%  "
              f"(uniform phase would give 9.8%)")
        h = np.histogram(fx, bins=10, range=(0, 1))[0]
        print(f"  frac(dx) histogram over [0,1) in 10 bins: {list(h)}")
        res[pname] = {
            "disp_mean_px": float(mag.mean()), "disp_max_px": float(mag.max()),
            "fx_mean": float(fx.mean()), "fx_sd": float(fx.std()),
            "fy_mean": float(fy.mean()), "fy_sd": float(fy.std()),
            "dist_to_int_mean_px": float(dist.mean()),
            "dist_to_int_median_px": float(np.median(dist)),
            "frac_within_0p05_px": near,
            "fx_hist10": [int(v) for v in h],
        }

    for k, tag in ((0.9315, "299-frame merge"), (0.9974, "one-frame stack")):
        cycles_field = plane_w * 2 * abs(1 / k - 1)
        print(f"\ncoverage k={k} ({tag}): the scale alone sweeps "
              f"{cycles_field:.1f} full phase cycles across the output width")
        res[f"phase_cycles_k_{k}"] = float(cycles_field)

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
