"""flowers-cpl renders as mush. Whose fault is it?

The boundary probe found 33.74% of flowers-cpl pixels elect a frame at the edge
of the bracket, against 0.12% for leaf-2-cpl -- a 281x separation on a number
the tool already prints. That is consistent with under-bracketing, but it is not
proof, and it does not say whether the MERGE destroyed detail that the capture
contained.

That question has a decisive form, and it is the same one thesis_demo.py used:

  --gate 0 is pure selection. Every output pixel is exactly one input frame's
  pixel, unaveraged (verified: mean n_eff 1.000, 100.00% at n_eff=1). So gate 0
  is an upper bound on what SELECTION can show. If gate 0 is ALSO mush, then no
  single frame had detail there and the merge is exonerated -- the capture never
  contained it. If gate 0 is sharp and gate 2 is mush, the merge ate it.

Both arms run at the SAME fixed --exposure, so the merge is the only variable.

Third hypothesis tested at the same time: saturation. A blown white petal has no
focus signal at any depth, which would produce mush with no one at fault but the
exposure. Measured on the linear render, where clipping is unambiguous, rather
than on the exposed one where the gain itself can clip.

Crops are fixed in advance at the frame centre -- the region the eye was drawn
to in the gallery -- so neither arm selects its own view.
"""
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile

EXE = Path(r"C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch\release\strehl.exe")
SRC = r"D:\personal\macro\flowers-cpl"
OUT = Path(r"C:\dev\strehl-out\ORCH-flowers")
OUT.mkdir(parents=True, exist_ok=True)

EXPOSURE = None  # resolved from an --auto-exposure probe, then FIXED for both arms
CROP = 900       # centre crop side, in full-resolution pixels


def run(args, tag):
    p = subprocess.run([str(EXE), "stack", SRC] + args,
                       capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        print(f"{tag}: FAILED rc={p.returncode}\n{p.stderr[-1500:]}")
        sys.exit(1)
    return p.stdout + p.stderr


def main():
    global EXPOSURE

    # --- 1. resolve the exposure once, and read it off the tool's own report ---
    print("resolving exposure ...")
    blob = run(["--gate", "2", "--srgb", "--auto-exposure",
                "-o", str(OUT / "probe.tif")], "probe")
    m = re.search(r"--exposure[= ]([+-]?[0-9.]+)", blob)
    if not m:
        print("could not read back --exposure=N; candidate lines:")
        for line in blob.splitlines():
            if "exposure" in line.lower():
                print("  |", line)
        sys.exit(1)
    EXPOSURE = float(m.group(1))
    assert -6.0 <= EXPOSURE <= 8.0, f"implausible exposure {EXPOSURE}"
    print(f"  fixed exposure = {EXPOSURE:+.2f} stops (both arms)")

    # --- 2. saturation, on the LINEAR render where clipping is unambiguous ---
    print("linear render for clipping check ...")
    run(["--gate", "2", "-o", str(OUT / "linear.tif")], "linear")
    lin = tifffile.imread(OUT / "linear.tif").astype(np.float64)
    lin /= lin.max() if lin.max() > 0 else 1.0
    h, w = lin.shape[:2]
    c = CROP // 2  # linear render is binned -> half resolution
    ly0, lx0 = h // 2 - c // 2, w // 2 - c // 2
    lcrop = lin[ly0:ly0 + c, lx0:lx0 + c]
    clip = float((lcrop >= 0.99).mean())
    print(f"  linear centre crop: max {lcrop.max():.4f}  "
          f"fraction >= 0.99 of max: {100 * clip:.3f}%")

    # --- 3. the decisive arm pair, both at the SAME fixed exposure ---
    arms = {}
    for gate, tag in ((0, "gate0-selection"), (2, "gate2-estimation")):
        print(f"rendering {tag} ...")
        blob = run(["--gate", str(gate), "--srgb", "--exposure", str(EXPOSURE),
                    "-o", str(OUT / f"{tag}.tif")], tag)
        row = re.search(
            r"^\s*[0-9.]+\s+[0-9.eE+-]+\s+([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%",
            blob, re.M)
        neff, neff1, bnd = (float(x) for x in row.groups())
        assert 1.0 <= neff <= 400.0, f"n_eff out of range: {neff}"
        print(f"  n_eff {neff:.3f}   n_eff=1 {neff1:.2f}%   boundary {bnd:.2f}%")
        img = tifffile.imread(OUT / f"{tag}.tif")
        arms[tag] = dict(img=img, neff=neff, neff1=neff1, bnd=bnd)

    # --- 4. same crop, both arms, fixed at centre ---
    a = arms["gate0-selection"]["img"]
    b = arms["gate2-estimation"]["img"]
    assert a.shape == b.shape, f"shape mismatch {a.shape} vs {b.shape}"
    H, W = a.shape[:2]
    y0, x0 = H // 2 - CROP // 2, W // 2 - CROP // 2

    ca = a[y0:y0 + CROP, x0:x0 + CROP].astype(np.float64) / 65535.0
    cb = b[y0:y0 + CROP, x0:x0 + CROP].astype(np.float64) / 65535.0

    def texture(x):
        """High-frequency energy: std of the Laplacian, on luminance."""
        g = x.mean(axis=2) if x.ndim == 3 else x
        lap = (4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1]
               - g[1:-1, :-2] - g[1:-1, 2:])
        return float(lap.std())

    ta, tb = texture(ca), texture(cb)
    print()
    print("=" * 74)
    print(f"centre {CROP}x{CROP} crop, both arms at --exposure={EXPOSURE:+.2f}")
    print(f"  gate 0 (selection)   high-freq energy: {ta:.6f}")
    print(f"  gate 2 (estimation)  high-freq energy: {tb:.6f}")
    print(f"  ratio gate2/gate0  : {tb / ta if ta else float('nan'):.4f}")
    print()
    if clip > 0.02:
        print(f"SATURATION: {100*clip:.2f}% of the centre is within 1% of max --")
        print("            a blown petal has no focus signal at any depth.")
    else:
        print(f"SATURATION: ruled out ({100*clip:.3f}% clipped).")
    print()
    print("VERDICT: if gate 0 is ALSO featureless, the capture never held the")
    print("         detail and the merge is exonerated. Look at the picture.")

    sbs = np.concatenate([ca, cb], axis=1)
    sbs = (np.clip(sbs, 0, 1) * 255).astype(np.uint8)
    import PIL.Image
    PIL.Image.fromarray(sbs).save(OUT / "SBS-centre-gate0-vs-gate2.png")
    print(f"\nwrote {OUT / 'SBS-centre-gate0-vs-gate2.png'}  (left gate0, right gate2)")


if __name__ == "__main__":
    sys.exit(main())
