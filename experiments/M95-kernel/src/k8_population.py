"""Is the arm-8/arm-9 kernel gain a hostage to the shared sidecar?

## Why this exists

The orchestrator found that `strehl align` writes `<stackdir>/warpmap.txt` by
default, inside the shared read-only capture library, and that seven live
agents have been silently overwriting each other's. On `bee-3-cpl` that file
was observed at 299 placements / reference 149, then at 40 / reference 20, and
M99 saw 299 -> 60 -> 2.

My B22 number (+0.1160 dex kernel gain) was measured through warps read from
that family of files. It resolved to the quarantined copy
`C:\\dev\\strehl-out\\ORCH-quarantine-sidecars\\bee-3-cpl--warpmap.txt`, which
declares `frames 8`, `reference 4`, 8 placed. So the warps behind my headline
came from an **8-frame** solve, not the 299-frame bracket.

The orchestrator's warning is that a control cannot catch this because it
contaminates treatment and control identically. That is exactly right for a
render measurement. It is a different question for mine, and the difference is
worth stating precisely rather than assuming:

* My statistic is a **paired A/B on identical geometry** -- same tiles, same
  warps, one arm Catmull-Rom, one arm Lanczos-3. A wrong sidecar cannot make
  one arm look better than the other, because both arms consume it byte for
  byte.
* But the sidecar supplies the **population of sub-pixel phases**, and the
  resampling cost is a function of phase. So a wrong sidecar could still make
  my number unrepresentative even though it cannot make it biased.

That is a testable claim, so it gets tested instead of argued.

## Registered bar -- written before this script was run

The kernel gain is **population-independent**, and therefore not a hostage to
whatever the sidecar happened to say, if every arm below lands within
**+/- 0.02 dex** of the reported **+0.1160**. That is twice B22's own 0.01 dex
tolerance, chosen so the bar is not simply B22 restated.

**If any arm moves by more than 0.02 dex, my headline is population-dependent,
the sidecar's state matters to it, and I report the number as needing a retake
against a trusted sidecar.** I would rather say that than defend a number.

Arms, in decreasing dependence on the sidecar:

| arm | phases from |
| --- | --- |
| SIDECAR | the quarantined 8-frame sidecar (what I reported) |
| GRID | a deterministic 5x5 grid of sub-pixel offsets, no sidecar |
| RANDOM | 24 uniform-random offsets, fixed seed, no sidecar |
| NOZOOM | 24 random offsets at scale exactly 1.0 -- no coverage zoom |

Control:

* **K25 NULL** -- the same kernel on both sides of every population must read
  exactly 0.0000 dex. If a population can manufacture a difference from
  nothing, nothing that population says about kernels is admissible.

Run: `python experiments/M95-kernel/src/k8_population.py`
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "M95-coverage" / "src"))
import m95cov as M  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out" / "k8_population.json"

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
MAP = Path(r"D:\personal\macro\bee-3-cpl\warpmap.txt")
MAP_ALT = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt")

K_COVER = 0.9315
REPORTED_GAIN = 0.1160
BAR = 0.02


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def read_warps():
    """Read the sidecar, and report which one and what it declares.

    The `MAP if MAP.exists() else MAP_ALT` fallback is the same one arm 8 used.
    Printing the resolved path and its header is the whole point: a sidecar
    that changes under you does not announce itself, so the run must announce
    it instead.
    """
    src = MAP if MAP.exists() else MAP_ALT
    hdr, rows = {}, []
    for line in src.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        p = s.split()
        if len(p) >= 6 and p[1] == "placed":
            rows.append((f64(p[2]), f64(p[3]), f64(p[4]), f64(p[5])))
        elif p[0] in ("frames", "reference", "resampler", "stack-digest", "stack-name", "plane"):
            hdr[p[0]] = p[1] if len(p) > 1 else ""
    return src, hdr, rows


def cost(img, tiles, phases, kernel):
    """Paired band-ratio cost, identical in structure to arm 8's `cost_arm`.

    `phases` is a list of (scale, off_y, off_x). Every arm below differs ONLY
    in how that list is produced, so the comparison isolates the population.
    """
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    vals = []
    for ty, tx in tiles:
        for step, by, bx in phases:
            o0y = round(cy + (ty - cy) / step)
            o0x = round(cx + (tx - cx) / step)
            sy = step * (o0y - cy) + cy + by
            sx = step * (o0x - cx) + cx + bx
            ci = int(np.floor(sy + (M.TILE - 1) * step / 2.0))
            cj = int(np.floor(sx + (M.TILE - 1) * step / 2.0))
            y0, x0 = ci - M.PAD // 2, cj - M.PAD // 2
            if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
                continue
            base = img[ci - M.TILE // 2 : ci + M.TILE // 2, cj - M.TILE // 2 : cj + M.TILE // 2]
            if base.shape != (M.TILE, M.TILE):
                continue
            reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
            i = np.arange(M.TILE, dtype=np.float64)
            t = M.gather_1d(reg, (sy - y0) + i * step, 0, kernel)
            out = M.gather_1d(t, (sx - x0) + i * step, 1, kernel)
            vals.append(M.band_ratio(base, 1.0) - M.band_ratio(out, step))
    return np.asarray(vals, dtype=np.float64)


def stat(v):
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v))), int(len(v))


def main():
    print(__doc__.split("Run:")[0].split("## Registered bar")[1][:0] or "", end="")
    print("K8 -- is the kernel gain a hostage to the shared sidecar?\n")
    print(f"REGISTERED BAR (before this run): every arm within +/-{BAR:.2f} dex of {REPORTED_GAIN:+.4f}\n")

    if not B0.exists():
        sys.exit(f"missing base image {B0}")
    src, hdr, rows = read_warps()
    print("SIDECAR ACTUALLY RESOLVED")
    print(f"  path      {src}")
    print(f"  declares  frames={hdr.get('frames')} reference={hdr.get('reference')} "
          f"resampler={hdr.get('resampler')} digest={hdr.get('stack-digest')}")
    print(f"  placed    {len(rows)} rows")
    print(f"  shared default {MAP} exists: {MAP.exists()}\n")

    img = M.load_luma(B0)
    tiles = M.pick_tiles(img)
    print(f"base {B0.name} {img.shape}  {len(tiles)} tiles\n")

    pops = {}
    pops["SIDECAR"] = [
        (np.hypot(a_re, a_im) * K_COVER, b_im * 2.0, b_re * 2.0) for a_re, a_im, b_re, b_im in rows
    ]
    g = np.linspace(0.0, 1.0, 5, endpoint=False)
    pops["GRID"] = [(K_COVER, float(dy), float(dx)) for dy in g for dx in g]
    rng = np.random.default_rng(20260824)
    pops["RANDOM"] = [(K_COVER, float(dy), float(dx)) for dy, dx in rng.uniform(0, 1, (24, 2))]
    rng2 = np.random.default_rng(11)
    pops["NOZOOM"] = [(1.0, float(dy), float(dx)) for dy, dx in rng2.uniform(0, 1, (24, 2))]

    print("K25 NULL -- same kernel both sides, must be exactly 0")
    nulls = {}
    for name, ph in pops.items():
        a = cost(img, tiles, ph, "catmull-rom")
        b = cost(img, tiles, ph, "catmull-rom")
        d = float((a - b).mean())
        nulls[name] = d
        print(f"  {name:<9} {d:+.6f} dex   {'PASS' if d == 0.0 else 'FAIL'}")

    print("\nGAIN BY POPULATION")
    res = {}
    for name, ph in pops.items():
        cr = cost(img, tiles, ph, "catmull-rom")
        lz = cost(img, tiles, ph, "lanczos3")
        n = min(len(cr), len(lz))
        paired = cr[:n] - lz[:n]
        gm, gs, _ = stat(paired)
        cm, _, _ = stat(cr)
        lm, _, _ = stat(lz)
        res[name] = {"gain": gm, "se": gs, "n": n, "cr": cm, "lz": lm, "phases": len(ph)}
        d = abs(gm - REPORTED_GAIN)
        print(
            f"  {name:<9} phases {len(ph):>3}  n {n:>4}  cr {cm:+.4f}  lz {lm:+.4f}  "
            f"gain {gm:+.4f} +/- {gs:.4f}   |d| {d:.4f}  {'PASS' if d <= BAR else 'FAIL'}"
        )

    worst = max(abs(v["gain"] - REPORTED_GAIN) for v in res.values())
    null_ok = all(v == 0.0 for v in nulls.values())
    ok = worst <= BAR and null_ok
    print(f"\n  worst deviation from {REPORTED_GAIN:+.4f}: {worst:.4f} dex   bar {BAR:.2f}")
    print(f"  K25 null clean on all populations: {null_ok}")
    print(
        "\n"
        + (
            "POPULATION-INDEPENDENT -- the sidecar's state does not reach the headline"
            if ok
            else "POPULATION-DEPENDENT -- the headline needs a retake against a trusted sidecar"
        )
    )

    OUT.write_text(
        json.dumps(
            {
                "sidecar_path": str(src),
                "sidecar_header": hdr,
                "sidecar_placed": len(rows),
                "shared_default_exists": MAP.exists(),
                "reported_gain": REPORTED_GAIN,
                "bar": BAR,
                "nulls": nulls,
                "arms": res,
                "worst_dev": worst,
                "pass": bool(ok),
                "schema": "m95-k8-1",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
