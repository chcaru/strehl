"""B2 -- price the orchestrator's proposed fix directly, using the REAL warps.

The proposal: stop stretching the coverage-cropped field back to sensor
dimensions. Emit 6550x4367 at native sampling instead of 7032x4688.

What that changes, exactly. `fit_to_cover` composes a pure scale `s` onto every
frame's placement `t` and returns `s.then(t)`, so the shipped mapping from an
output pixel p to a source position is

    NOW : a * k * (p - c) + c + b        step ~ |a| * 0.9315
    FIX : a *     (p - c) + c + b        step ~ |a|

with (a, b) the frame's own similarity, read here from the shipped sidecar
D:\\personal\\macro\\bee-3-cpl\\warpmap.txt. The fix removes k. It does NOT
remove the gather, because a and b remain, and w0_warpstats measured their
fractional part to be uniformly distributed (1.3% within 0.05 px of an integer
against 9.8% expected for uniform).

Third arm SNAP is the upper bound on any geometry-only fix: the same frames with
every translation rounded to an integer and the frame scale forced to 1. No real
aligner can do better than that, so if SNAP is cheap the geometry is worth
attacking and if SNAP is expensive nothing in this family will help.

Bars pre-registered in ../PRE-REGISTRATION.md:
  the fix ships if  cost(FIX) < cost(NOW) - 0.10 dex
  the fix is dead if cost(FIX) > cost(NOW) - 0.03 dex
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

import m95cov as M

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
MAP = Path(r"D:\personal\macro\bee-3-cpl\warpmap.txt")
# The orchestrator quarantined the shipped sidecars after this arm first ran.
# The quarantined copy is the same file, moved; prefer the original when it is
# present so the provenance is unchanged, and fall back so the arm stays
# re-runnable. Which one was used is printed.
MAP_ALT = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt")
OUT = Path(__file__).resolve().parents[1] / "out" / "x8_fix.json"

K_COVER = 0.9315
NFRAMES = 24


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def read_warps():
    src = MAP if MAP.exists() else MAP_ALT
    rows = []
    plane = None
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


def arm(img, tiles, warps, use_cover, snap=False):
    """Gather every (tile, frame) pair through the stated mapping.

    The source plane is 3516x2344 CFA but the render is 7032x4688, so warp
    parameters are doubled into render pixels before use.
    """
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    kc = K_COVER if use_cover else 1.0
    out, steps = [], []
    for ty, tx in tiles:
        for _, a_re, a_im, b_re, b_im in warps:
            if snap:
                a, bx, by = 1.0, round(b_re * 2.0), round(b_im * 2.0)
            else:
                a, bx, by = np.hypot(a_re, a_im), b_re * 2.0, b_im * 2.0
            step = a * kc
            # output tile origin, forced to the integer output pixel grid
            o0y = round(cy + (ty - cy) / step)
            o0x = round(cx + (tx - cx) / step)
            sy = step * (o0y - cy) + cy + by
            sx = step * (o0x - cx) + cx + bx
            ci = int(np.floor(sy + (M.TILE - 1) * step / 2.0))
            cj = int(np.floor(sx + (M.TILE - 1) * step / 2.0))
            y0, x0 = ci - M.PAD // 2, cj - M.PAD // 2
            if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
                continue
            reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
            i = np.arange(M.TILE, dtype=np.float64)
            t = M.gather_1d(reg, (sy - y0) + i * step, 0)
            g = M.gather_1d(t, (sx - x0) + i * step, 1)
            base = img[ci - M.TILE // 2 : ci + M.TILE // 2,
                       cj - M.TILE // 2 : cj + M.TILE // 2]
            out.append(M.band_ratio(base, 1.0) - M.band_ratio(g, step))
            steps.append(step)
    return np.array(out), np.array(steps)


def main():
    if not B0.exists() or not (MAP.exists() or MAP_ALT.exists()):
        sys.exit("missing inputs")
    img = M.load_luma(B0)
    plane, rows, src = read_warps()
    # The fallback above now resolves to an EIGHT-frame solve under a different
    # stack digest: the shipped 299-frame sidecar was quarantined and a later,
    # unrelated solve took its place under the same name. Re-running this arm
    # would silently measure 8 frames and print a plausible number. Refuse.
    # M95 section 20.1; k17_crop.py supersedes this arm on a pinned sidecar.
    if len(rows) != 299:
        sys.exit(
            f"REFUSING TO MEASURE: {src} holds {len(rows)} placed frames, not the "
            f"299 this arm was measured on. Use experiments/M95-kernel/src/"
            f"k17_crop.py, which pins its own sidecar."
        )
    tiles = M.pick_tiles(img)
    idx = np.linspace(0, len(rows) - 1, NFRAMES).round().astype(int)
    warps = [rows[i] for i in idx]
    print(f"source : {B0.name}  {img.shape[1]}x{img.shape[0]}")
    print(f"warpmap: {src}")
    print(f"warps  : {len(rows)} placed frames, plane {plane[0]}x{plane[1]}, "
          f"sampling {NFRAMES} of them")
    print(f"tiles  : {len(tiles)}\n")
    res = {"n_tiles": len(tiles), "n_frames": NFRAMES, "k_cover": K_COVER}

    print("--- CONTROL: the same harness with an identity frame and no cover ---")
    ident = [(0, 1.0, 0.0, 0.0, 0.0)]
    c_id, _ = arm(img, tiles, ident, use_cover=False)
    ok_id = abs(c_id.mean()) < 0.005
    print(f"K1 NULL   identity warp, no coverage   {c_id.mean():+.6f} dex   "
          f"{'PASS' if ok_id else 'FAIL'}   ({len(c_id)} tiles)")
    res["K1_null"] = float(c_id.mean())

    c_ic, _ = arm(img, tiles, ident, use_cover=True)
    print(f"K6 COVER  identity warp, coverage on   {c_ic.mean():+.6f} dex   "
          f"(the coverage scale acting alone)")
    res["K6_cover_alone"] = float(c_ic.mean())

    if not ok_id:
        print("\nCONTROL FAILED -- reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    print("\n--- B2: the arms ---")
    rows_out = []
    for name, uc, sn, desc in (
        ("NOW", True, False, "real warp + coverage scale, output 7032x4688"),
        ("FIX", False, False, "real warp, NO coverage scale, output 6550x4367"),
        ("SNAP", False, True, "integer translation, unit scale (geometry floor)"),
    ):
        c, st = arm(img, tiles, warps, use_cover=uc, snap=sn)
        sem = c.std(ddof=1) / np.sqrt(len(c))
        rows_out.append((name, c.mean(), sem, len(c), st.mean(), desc))
        res[name] = {"cost_dex": float(c.mean()), "sem": float(sem),
                     "n": int(len(c)), "mean_step": float(st.mean())}

    print(f"{'arm':<6} {'cost (dex)':>12} {'sem':>8} {'n':>6} {'step':>8}  what")
    for name, m, s, n, st, desc in rows_out:
        print(f"{name:<6} {m:>+12.4f} {s:>8.4f} {n:>6} {st:>8.4f}  {desc}")

    now = res["NOW"]["cost_dex"]
    fix = res["FIX"]["cost_dex"]
    snap = res["SNAP"]["cost_dex"]
    gain = now - fix
    print(f"\n  the fix recovers: {gain:+.4f} dex "
          f"({100 * gain / now:.1f}% of what the gather costs today)")
    print(f"  pre-registered SHIPS  if recovery > 0.10 dex -> "
          f"{'SHIPS' if gain > 0.10 else 'does not ship'}")
    print(f"  pre-registered DEAD   if recovery < 0.03 dex -> "
          f"{'DEAD' if gain < 0.03 else 'not dead'}")
    print(f"\n  geometry floor (SNAP): {snap:+.4f} dex. Even rounding every")
    print(f"  translation to an integer and forcing unit scale leaves "
          f"{100 * snap / now:.1f}% of")
    print(f"  today's cost, because the frames' own scale and rotation are gone")
    print(f"  but the elected-frame mosaic still resamples.")
    res["fix_recovery_dex"] = gain
    res["fix_ships"] = bool(gain > 0.10)
    res["fix_dead"] = bool(gain < 0.03)

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
