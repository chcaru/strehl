"""Arm 8 -- adjudicate the coverage-rescale bar in ONE harness.

The orchestrator has priced the rescale twice, at +0.2392 and +0.1789 dex, both
times by measuring a gather and attributing the cost to the scale. Arm 7 priced
the change the fix would actually make -- removing k from strehl's *composed*
mapping -- at +0.0143 dex.

Rather than argue about which model is right, this runs all three measurements
side by side on the same tiles with the same metric:

  ISO(k)   identity frame warp, coverage scale k only     the scale ALONE
  COMP(k)  real frame warps (a, b) with k composed on     WHAT STREHL DOES
  ADD      a second gather at 1.073537 on a gathered tile M104'S PLANT

If ADD is expensive while COMP(0.9315) - COMP(1.0) is not, then the expensive
thing is *a gather*, strehl has exactly one, and removing k does not remove it.

Bars and controls are in ../PRE-REGISTRATION.md and were fixed before this ran.
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
OUT = Path(__file__).resolve().parents[1] / "out" / "y1_dose.json"

K_COVER = 0.9315
ENLARGE = 1.073537  # the factor M104 planted; 1/0.9315 to 6 places is 1.073537
NFRAMES = 24

# Swept both sides of unity so a monotone dose response would be unmistakable.
SWEEP = [0.80, 0.90, 0.9315, 0.98, 1.00, 1.02, 1.10, 1.25]


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


def gather_tile(img, ty, tx, a, bx, by, kc):
    """One composed gather, exactly as x8_fix.arm does it.

    Returns (base, out, step) or None when the tile falls off the plane.
    `base` is the unresampled source tile the output is scored against.
    """
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    step = a * kc
    o0y = round(cy + (ty - cy) / step)
    o0x = round(cx + (tx - cx) / step)
    sy = step * (o0y - cy) + cy + by
    sx = step * (o0x - cx) + cx + bx
    ci = int(np.floor(sy + (M.TILE - 1) * step / 2.0))
    cj = int(np.floor(sx + (M.TILE - 1) * step / 2.0))
    y0, x0 = ci - M.PAD // 2, cj - M.PAD // 2
    if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
        return None
    reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
    i = np.arange(M.TILE, dtype=np.float64)
    t = M.gather_1d(reg, (sy - y0) + i * step, 0)
    out = M.gather_1d(t, (sx - x0) + i * step, 1)
    base = img[ci - M.TILE // 2 : ci + M.TILE // 2, cj - M.TILE // 2 : cj + M.TILE // 2]
    if base.shape != (M.TILE, M.TILE):
        return None
    return base, out, step


def cost_arm(img, tiles, warps, kc):
    """Mean band-power loss of one composed gather at coverage factor kc."""
    vals = []
    for ty, tx in tiles:
        for _, a_re, a_im, b_re, b_im in warps:
            a = np.hypot(a_re, a_im)
            g = gather_tile(img, ty, tx, a, b_re * 2.0, b_im * 2.0, kc)
            if g is None:
                continue
            base, out, step = g
            vals.append(M.band_ratio(base, 1.0) - M.band_ratio(out, step))
    return np.array(vals)


def cost_add(img, tiles, warps):
    """M104's experiment: the cost of a SECOND gather on an already-gathered tile.

    The first gather is strehl's real composed mapping, so the input to the
    second gather is render-like rather than raw -- which is precisely the
    correction M104 made to the orchestrator's round-1 proxy.
    """
    vals = []
    for ty, tx in tiles:
        for _, a_re, a_im, b_re, b_im in warps:
            a = np.hypot(a_re, a_im)
            g = gather_tile(img, ty, tx, a, b_re * 2.0, b_im * 2.0, K_COVER)
            if g is None:
                continue
            _, out, step = g
            # a second, independent resample of the finished tile by 1/ENLARGE
            second = M.gather(out, 1.0 / ENLARGE, 0.0, 0.0, n_out=M.TILE)
            vals.append(M.band_ratio(out, step) - M.band_ratio(second, step / ENLARGE))
    return np.array(vals)


def stat(v):
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v))), int(len(v))


def main():
    if not B0.exists() or not (MAP.exists() or MAP_ALT.exists()):
        sys.exit("missing inputs")
    img = M.load_luma(B0)
    plane, rows, src = read_warps()
    tiles = M.pick_tiles(img)
    idx = np.linspace(0, len(rows) - 1, min(NFRAMES, len(rows))).round().astype(int)
    warps = [rows[i] for i in sorted(set(idx.tolist()))]
    ident = [(0, 1.0, 0.0, 0.0, 0.0)]

    print(f"source : {B0.name}  {img.shape[1]}x{img.shape[0]}")
    print(f"warpmap: {src}")
    print(f"warps  : {len(rows)} placed, using {len(warps)}; tiles {len(tiles)}")
    print(f"enlarge: {ENLARGE}  (coverage k = {K_COVER})\n")
    res = {"k_cover": K_COVER, "enlarge": ENLARGE, "sweep": SWEEP,
           "n_tiles": len(tiles), "n_frames": len(warps),
           "warpmap": str(src), "n_placed": len(rows)}

    # ------------------------------------------------------------- controls
    print("--- CONTROLS (pre-registered; no arm prints unless all pass) ---")
    k12 = cost_arm(img, tiles, ident, 1.0)
    m12, s12, n12 = stat(k12)
    ok12 = abs(m12) < 0.005
    print(f"K12 NULL      identity warp, k=1      {m12:+.6f} dex  "
          f"{'PASS' if ok12 else 'FAIL'}  (n={n12})")

    blur = []
    for ty, tx in tiles:
        base = img[ty : ty + M.TILE, tx : tx + M.TILE]
        if base.shape != (M.TILE, M.TILE):
            continue
        blur.append(M.band_ratio(base, 1.0) - M.band_ratio(M.fourier_blur(base, 1.0), 1.0))
    m13, s13, n13 = stat(np.array(blur))
    ok13 = m13 >= 0.20
    print(f"K13 RESPONSE  planted sigma=1.0 px    {m13:+.6f} dex  "
          f"{'PASS' if ok13 else 'FAIL'}  (n={n13})")

    add = cost_add(img, tiles, warps)
    m_add, s_add, n_add = stat(add)
    sep = abs(m_add - m12)
    ok14 = sep >= 0.10
    print(f"K14 SEPARATE  |ADD - NULL|            {sep:.6f} dex  "
          f"{'PASS' if ok14 else 'FAIL'}")
    res["K12_null"] = {"mean": m12, "sem": s12, "n": n12, "pass": ok12}
    res["K13_response"] = {"mean": m13, "sem": s13, "n": n13, "pass": ok13}
    res["K14_separation"] = {"sep": float(sep), "pass": ok14}
    res["ADD"] = {"mean": m_add, "sem": s_add, "n": n_add}

    if not (ok12 and ok13 and ok14):
        print("\nCONTROL FAILED -- reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    # ----------------------------------------------------------- the sweeps
    print("\n--- THE SWEEPS ---")
    print(f"{'k':>8} {'ISO(k) scale alone':>20} {'COMP(k) as shipped':>20}")
    iso, comp = {}, {}
    for k in SWEEP:
        vi = cost_arm(img, tiles, ident, k)
        vc = cost_arm(img, tiles, warps, k)
        mi, si, ni = stat(vi)
        mc, sc, nc = stat(vc)
        iso[f"{k}"] = {"mean": mi, "sem": si, "n": ni}
        comp[f"{k}"] = {"mean": mc, "sem": sc, "n": nc}
        print(f"{k:>8.4f} {mi:>+14.4f} +-{si:<4.4f} {mc:>+14.4f} +-{sc:<4.4f}")
    res["ISO"] = iso
    res["COMP"] = comp

    print(f"\nADD  second gather at {ENLARGE} on a gathered tile  "
          f"{m_add:+.4f} +-{s_add:.4f} dex   (M104's plant, reproduced)")

    # ------------------------------------------------------------ the bars
    now = comp[f"{K_COVER}"]["mean"]
    fix = comp["1.0"]["mean"]
    rec = now - fix
    cvals = [v["mean"] for v in comp.values()]
    spread = max(cvals) - min(cvals)
    ivals = [(abs(float(k) - 1.0), v["mean"]) for k, v in iso.items()]
    ivals.sort()
    off = [m for d, m in ivals if d > 1e-9]
    iso_mono = all(off[i] <= off[i + 1] + 1e-9 for i in range(len(off) - 1))

    print("\n--- REGISTERED BARS ---")
    print(f"COMP({K_COVER}) = {now:+.4f}   COMP(1.0) = {fix:+.4f}   "
          f"recovery = {rec:+.4f} dex ({100 * rec / now:.1f}%)")
    b13 = rec >= 0.10
    b14 = (rec < 0.03) and (m_add >= 0.10) and (abs(m12) < 0.005)
    b15 = spread < 0.05
    print(f"B13 orchestrator right (recovery >= 0.10)      "
          f"{'FIRES' if b13 else 'does not fire'}")
    print(f"B14 gather-not-scale   (rec<0.03, ADD>=0.10)   "
          f"{'FIRES' if b14 else 'does not fire'}")
    print(f"B15 threshold not dose (COMP spread < 0.05)    "
          f"{'FIRES' if b15 else 'does not fire'}   spread={spread:.4f}")
    if 0.03 <= rec < 0.10:
        print("B16 MIDDLE -- recovery is partial and is reported as partial.")
    print(f"P13 ISO monotone in |k-1| off-lattice?         "
          f"{'MONOTONE' if iso_mono else 'NOT monotone (flat-ish)'}")
    res["bars"] = {"now": now, "fix": fix, "recovery_dex": rec,
                   "recovery_pct": 100 * rec / now, "comp_spread": spread,
                   "B13_orchestrator": bool(b13), "B14_gather_not_scale": bool(b14),
                   "B15_threshold_not_dose": bool(b15),
                   "B16_middle": bool(0.03 <= rec < 0.10),
                   "P13_iso_monotone": bool(iso_mono)}

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
