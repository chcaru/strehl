"""ORCH-owned. Build a viewable 1:1 contact sheet folder for all delivered masters.

For each subject, emit TWO crops at native 1:1:
  BEST  -- the maximum-gradient-energy window (where the stack most succeeded)
  WORST -- the lowest-energy window still on the subject (>=55th pct)

Both are emitted deliberately. Veiling 129: showing only the BEST crop answers
"how good is the best part", not "how good is the image". The pair is the
honest unit. A viewer who sees only one of these is being sold something.
"""
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

SRC = Path(r"C:\dev\strehl-out\DELIVER-V5\full-resolution")
DST = Path(r"C:\dev\strehl-out\DELIVER-V5\crops-1to1")
DST.mkdir(parents=True, exist_ok=True)

CROP = 400
GRID = 24


def main() -> int:
    rows = []
    names = sorted(p.stem for p in SRC.glob("*.png"))
    for name in names:
        im = Image.open(SRC / f"{name}.png")
        a = np.asarray(im)
        g = a[..., :3].astype(np.float32).mean(axis=2) if a.ndim == 3 else a.astype(np.float32)
        m = int(min(g.shape) * 0.05)
        sub = g[m:-m, m:-m]
        h, w = sub.shape
        gy = np.abs(np.diff(sub, axis=0))[:, : w - 1]
        gx = np.abs(np.diff(sub, axis=1))[: h - 1, :]
        e = gy + gx

        ws = []
        for y in np.linspace(0, max(0, e.shape[0] - CROP - 1), GRID).astype(int):
            for x in np.linspace(0, max(0, e.shape[1] - CROP - 1), GRID).astype(int):
                ws.append((int(y), int(x), float(e[y : y + CROP, x : x + CROP].mean())))
        ws.sort(key=lambda t: t[2])
        floor = np.percentile([t[2] for t in ws], 55)
        worst = next(t for t in ws if t[2] >= floor)
        best = ws[-1]

        for tag, (y, x, v) in (("BEST", best), ("WORST", worst)):
            out = DST / f"{name}__{tag}.png"
            im.crop((x + m, y + m, x + m + CROP, y + m + CROP)).save(out)
        rows.append((name, best[2], worst[2], best[2] / max(worst[2], 1e-9)))
        print(f"{name:42s} best={best[2]:8.3f}  worst={worst[2]:8.3f}")

    with open(DST / "INDEX.md", "w", encoding="utf-8") as f:
        f.write("# 1:1 crops — best and worst site per subject\n\n")
        f.write("400x400 pixels at native resolution. **1:1 is the only scale at\n")
        f.write("which a sharpness verdict is valid** — every halo complaint on this\n")
        f.write("project so far has been a downscaling artifact, so please judge here\n")
        f.write("and not from a gallery thumbnail.\n\n")
        f.write("`BEST` is the highest-gradient-energy window; `WORST` is the lowest\n")
        f.write("that is still on the subject rather than on empty backdrop. Both are\n")
        f.write("shown on purpose: `BEST` alone answers *how good is the best part*,\n")
        f.write("which is not the question. **Judge the tool by the `WORST` files.**\n\n")
        f.write("| subject | best site energy | worst site energy | ratio |\n")
        f.write("|---|---|---|---|\n")
        for n, b, w, r in rows:
            f.write(f"| `{n}` | {b:.3f} | {w:.3f} | {r:.2f}x |\n")
    print(f"\n{len(rows)} subjects -> {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
