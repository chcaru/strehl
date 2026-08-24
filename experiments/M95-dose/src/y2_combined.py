"""Arm 8b -- if the gather cannot be removed, can it be made cheaper?

y1 established that removing the coverage scale leaves the gather in place and
recovers ~10% of its cost, because each frame's own similarity keeps the sample
phase off the lattice. The remaining lever is the interpolation kernel.

Arm 7 measured lanczos3 beating catmull-rom by +0.1343 dex on *synthetic*
phases. This asks the same question on the *real* warps and crosses it with the
coverage change, so the two can be attributed separately rather than bundled.

Bars B17/B18/B19 and control K16 are in ../PRE-REGISTRATION.md addendum 1 and
were fixed before this ran.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "M95-coverage" / "src"))
import m95cov as M  # noqa: E402

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
MAP = Path(r"D:\personal\macro\bee-3-cpl\warpmap.txt")
MAP_ALT = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt")
OUT = Path(__file__).resolve().parents[1] / "out" / "y2_combined.json"

K_COVER = 0.9315
NFRAMES = 24


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def read_warps():
    src = MAP if MAP.exists() else MAP_ALT
    rows, plane = [], None
    for line in src.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("plane "):
            plane = tuple(int(v) for v in s.split()[1].split("x"))
        elif s.startswith("#") or not s or s.startswith("end"):
            continue
        else:
            p = s.split()
            if len(p) >= 6 and p[1] == "placed":
                rows.append((int(p[0]), f64(p[2]), f64(p[3]), f64(p[4]), f64(p[5])))
    return plane, rows, src


def cost_arm(img, tiles, warps, kc, kernel):
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    vals = []
    for ty, tx in tiles:
        for _, a_re, a_im, b_re, b_im in warps:
            a = np.hypot(a_re, a_im)
            bx, by = b_re * 2.0, b_im * 2.0
            step = a * kc
            o0y = round(cy + (ty - cy) / step)
            o0x = round(cx + (tx - cx) / step)
            sy = step * (o0y - cy) + cy + by
            sx = step * (o0x - cx) + cx + bx
            ci = int(np.floor(sy + (M.TILE - 1) * step / 2.0))
            cj = int(np.floor(sx + (M.TILE - 1) * step / 2.0))
            y0, x0 = ci - M.PAD // 2, cj - M.PAD // 2
            if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
                continue
            base = img[ci - M.TILE // 2 : ci + M.TILE // 2,
                       cj - M.TILE // 2 : cj + M.TILE // 2]
            if base.shape != (M.TILE, M.TILE):
                continue
            reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
            i = np.arange(M.TILE, dtype=np.float64)
            t = M.gather_1d(reg, (sy - y0) + i * step, 0, kernel)
            out = M.gather_1d(t, (sx - x0) + i * step, 1, kernel)
            vals.append(M.band_ratio(base, 1.0) - M.band_ratio(out, step))
    return np.array(vals)


def stat(v):
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v))), int(len(v))


def main():
    if not B0.exists() or not (MAP.exists() or MAP_ALT.exists()):
        sys.exit("missing inputs")
    print("kernels available:", ", ".join(sorted(M.KERNELS)))
    kname = "lanczos3" if "lanczos3" in M.KERNELS else None
    if kname is None:
        sys.exit("lanczos3 kernel not present in m95cov.KERNELS")

    img = M.load_luma(B0)
    plane, rows, src = read_warps()
    tiles = M.pick_tiles(img)
    idx = np.linspace(0, len(rows) - 1, min(NFRAMES, len(rows))).round().astype(int)
    warps = [rows[i] for i in sorted(set(idx.tolist()))]
    ident = [(0, 1.0, 0.0, 0.0, 0.0)]
    print(f"source : {B0.name}  {img.shape[1]}x{img.shape[0]}")
    print(f"warpmap: {src}  ({len(rows)} placed, using {len(warps)})")
    print(f"tiles  : {len(tiles)}\n")
    res = {"k_cover": K_COVER, "n_tiles": len(tiles), "n_frames": len(warps),
           "warpmap": str(src), "n_placed": len(rows)}

    print("--- CONTROLS ---")
    k12 = cost_arm(img, tiles, ident, 1.0, "catmull-rom")
    m12, _, _ = stat(k12)
    ok12 = abs(m12) < 0.005
    print(f"K12 NULL  catmull-rom, identity, k=1   {m12:+.6f} dex  "
          f"{'PASS' if ok12 else 'FAIL'}")
    k16 = cost_arm(img, tiles, ident, 1.0, kname)
    m16, _, _ = stat(k16)
    ok16 = abs(m16) < 0.005
    print(f"K16 NULL  {kname}, identity, k=1     {m16:+.6f} dex  "
          f"{'PASS' if ok16 else 'FAIL'}")
    res["K12_null"] = m12
    res["K16_null_lanczos"] = m16
    if not (ok12 and ok16):
        print("\nCONTROL FAILED -- reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    print("\n--- THE CROSS ---")
    arms = {
        "TODAY": (K_COVER, "catmull-rom"),
        "NOK": (1.0, "catmull-rom"),
        "KERN": (K_COVER, kname),
        "BOTH": (1.0, kname),
    }
    print(f"{'arm':<7} {'k':>7} {'kernel':<12} {'cost (dex)':>12} {'sem':>8}")
    for name, (kc, kern) in arms.items():
        m, s, n = stat(cost_arm(img, tiles, warps, kc, kern))
        res[name] = {"cost_dex": m, "sem": s, "n": n, "k": kc, "kernel": kern}
        print(f"{name:<7} {kc:>7.4f} {kern:<12} {m:>+12.4f} {s:>8.4f}")

    today = res["TODAY"]["cost_dex"]
    r_nok = today - res["NOK"]["cost_dex"]
    r_kern = today - res["KERN"]["cost_dex"]
    r_both = today - res["BOTH"]["cost_dex"]
    extra = r_both - r_kern

    print("\n--- REGISTERED BARS ---")
    print(f"recovery, coverage only   {r_nok:+.4f} dex")
    print(f"recovery, kernel only     {r_kern:+.4f} dex")
    print(f"recovery, both            {r_both:+.4f} dex")
    print(f"what coverage adds on top of the kernel   {extra:+.4f} dex")
    b17, b18, b19 = r_both >= 0.10, r_kern >= 0.10, extra < 0.01
    print(f"B17 worth landing   (both  >= 0.10)   {'FIRES' if b17 else 'does not fire'}")
    print(f"B18 kernel is lever (kern  >= 0.10)   {'FIRES' if b18 else 'does not fire'}")
    print(f"B19 do not bundle   (extra <  0.01)   {'FIRES' if b19 else 'does not fire'}")
    if r_kern < 0.03:
        print("REGISTERED FALSIFIER FIRES: arm 7's kernel result does not "
              "transfer to the real warps; the M95-cdiff.md §7 patch "
              "recommendation is withdrawn.")
    res["bars"] = {"recovery_coverage": r_nok, "recovery_kernel": r_kern,
                   "recovery_both": r_both, "coverage_on_top": extra,
                   "B17_worth_landing": bool(b17), "B18_kernel_is_lever": bool(b18),
                   "B19_do_not_bundle": bool(b19),
                   "falsifier_kernel_fails": bool(r_kern < 0.03)}
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
