"""Where are flowers-cpl's boundary pixels -- on the subject, or on the backdrop?

captures-needed.md section 23 leaves this open, and the answer changes the
advice given to the owner:

  (1) boundary pixels lie ON THE SUBJECT  -> the sweep did not span it,
      the stack is under-bracketed, and the fix is to re-shoot wider.
  (2) boundary pixels lie on a DISTANT BACKDROP -> expected and unavoidable,
      nothing is wrong with the capture, and section 23 should say so.

176 frames is a long sweep, so (2) is the more economical hypothesis, but
"economical" is not "measured".

PROXY, AND ITS LIMIT: `--index-map` exists only on `argmax-baseline`, so this
reads the NAIVE argmax field, not the regularised winner field the merge
elects. That is acceptable for a question about the SCENE -- whether the
backdrop is reachable by any focus setting is a property of the optics and the
subject, not of the regulariser -- but the percentages here are NOT comparable
to the merge's own 33.74% and must not be quoted as if they were.

PREDICTION, REGISTERED BEFORE RUNNING:
  The centre 900x900 crop is the region that renders as a featureless waxy blob.
  If that crop is mostly boundary-elected, hypothesis (1). If it is mostly
  interior-elected, hypothesis (2) and the mush is a genuinely smooth defocused
  petal that the stack DID cover.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile

EXE = Path(r"C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch\release\strehl.exe")
SRC = r"D:\personal\macro\flowers-cpl"
OUT = Path(r"C:\dev\strehl-out\ORCH-flowers")
OUT.mkdir(parents=True, exist_ok=True)
IDX = OUT / "argmax-index.tif"
CROP = 900


def main():
    n_frames = len(list(Path(SRC).glob("*.ARW")))
    assert n_frames == 176, f"expected 176 frames, found {n_frames}"

    if not IDX.exists():
        print(f"running argmax-baseline on {n_frames} frames ...")
        p = subprocess.run(
            [str(EXE), "argmax-baseline", SRC, "-o", str(OUT / "argmax.tif"),
             "--index-map", str(IDX)],
            capture_output=True, text=True, errors="replace")
        if p.returncode != 0:
            print(f"FAILED rc={p.returncode}\n{p.stderr[-2000:]}")
            return 1
    else:
        print("reusing existing index map")

    idx = tifffile.imread(IDX)
    print(f"index map: {idx.shape} {idx.dtype}  min {idx.min()} max {idx.max()}")

    # The map holds the literal frame index, 0..N-1.
    hi = int(idx.max())
    assert hi <= n_frames - 1, f"index {hi} exceeds frame count {n_frames}"

    boundary = (idx == 0) | (idx == hi)
    whole = float(boundary.mean())

    H, W = idx.shape[:2]
    # The index map is on the binned grid; the crop was specified in
    # full-resolution pixels, so halve it to address the same scene region.
    c = CROP // 2
    y0, x0 = H // 2 - c // 2, W // 2 - c // 2
    centre = boundary[y0:y0 + c, x0:x0 + c]
    centre_frac = float(centre.mean())

    # Frame periphery: an outer ring one eighth of the short side thick.
    t = min(H, W) // 8
    ring = np.zeros_like(boundary)
    ring[:t, :] = ring[-t:, :] = True
    ring[:, :t] = ring[:, -t:] = True
    ring_frac = float(boundary[ring].mean())

    print()
    print("=" * 70)
    print(f"whole frame boundary-elected : {100 * whole:6.2f}%")
    print(f"centre {c}x{c} (the mush)      : {100 * centre_frac:6.2f}%")
    print(f"outer ring (backdrop)         : {100 * ring_frac:6.2f}%")
    print()
    print("index distribution at the two ends:")
    print(f"  elected frame 0     : {100 * float((idx == 0).mean()):6.2f}%")
    print(f"  elected frame {hi:<5}: {100 * float((idx == hi).mean()):6.2f}%")
    print()
    if centre_frac > 0.5:
        print("VERDICT: hypothesis (1) -- the SUBJECT is boundary-elected.")
        print("         The sweep did not span it. Re-shoot wider.")
    elif ring_frac > 2 * centre_frac:
        print("VERDICT: hypothesis (2) -- boundary pixels concentrate on the")
        print("         BACKDROP, not the subject. The stack covered what it")
        print("         could; the mush is a genuinely smooth defocused petal.")
    else:
        print("VERDICT: neither cleanly. Boundary pixels are not concentrated")
        print("         in either region -- report as unresolved, do not guess.")

    # A picture, because discipline 674 says the number is not the verdict.
    vis = np.zeros((H, W, 3), np.uint8)
    g = (255.0 * (idx.astype(np.float64) / max(hi, 1))).astype(np.uint8)
    vis[..., 0] = vis[..., 1] = vis[..., 2] = g
    vis[idx == 0] = (255, 40, 40)      # near end, red
    vis[idx == hi] = (40, 120, 255)    # far end, blue
    import PIL.Image
    PIL.Image.fromarray(vis).save(OUT / "boundary-map.png")
    print(f"\nwrote {OUT / 'boundary-map.png'}  (grey = interior, red = frame 0, blue = last frame)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
