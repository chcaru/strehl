"""M95 arm 11 - POST-HOC interpretation of B28.

LABELLED POST-HOC. B28 was registered in ADDENDUM 3 (commit 42a0c7c) with the
consequence "if a kernel's flat-region gain is of the same order as its
detail-region gain, its sharpness number is noise amplification and I must say
so." It fired: the flat gain matched the detail gain to within 2% for every
kernel. This script exists to work out WHY, and it is not a registered bar. No
bar is moved by anything here.

Two readings of that equality, and they have opposite consequences:

  (a) the gain is noise amplification -- the kernel is passing sensor noise
      through, and the detail-region number is inflated by the same mechanism;
  (b) the metric is content-independent -- band_ratio after a resample measures
      the KERNEL's transfer function, in which the scene's own spectrum largely
      cancels between the two bands, so it reads the same on any content.

The discriminator is a scene with NO noise in it at all. If a noise-free
synthetic field with genuine high-frequency structure shows the same gain, then
the gain is available on real detail and (a) is wrong as a general claim. If a
pure-noise field ALSO shows it, then the kernel is content-blind, which is what
a linear filter must be, and the honest statement is (b) plus the rider that on
noise-dominated ground the recovered energy IS noise.
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np

from x2_pairs import TILE, band_ratio
from x3_kernel import PAD, resample, resample_bspline

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

NAMES = ["catmullrom", "mitchell", "lanczos2", "lanczos3", "bspline"]
PHASES = [(0.5, 0.0), (0.0, 0.5), (0.5, 0.5), (0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)]
N = TILE + 2 * PAD


def bandlimited_field(rng, slope, fmax=0.5):
    """A noise-FREE deterministic field: random phases on a 1/f^slope amplitude
    envelope, strictly band-limited below fmax so it is fully sampled and contains
    no aliasing. 'Noise-free' means no sensor noise process -- every component is
    a resolvable structure of the scene."""
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.fftfreq(N)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    amp = np.where((r > 0) & (r < fmax), 1.0 / np.maximum(r, 1e-6) ** slope, 0.0)
    ph = rng.uniform(0, 2 * np.pi, size=(N, N))
    f = amp * np.exp(1j * ph)
    a = np.fft.ifft2(f).real
    a = a / a.std() * 300.0 + 2000.0
    return a


def white_noise(rng):
    return rng.normal(2000.0, 300.0, size=(N, N))


def ladder(tiles):
    base = float(np.mean([band_ratio(t[PAD:-PAD, PAD:-PAD], 1.0) for t in tiles]))
    out = {}
    for name in NAMES:
        vals = []
        for dy, dx in PHASES:
            for t in tiles:
                r = resample_bspline(t, dy, dx) if name == "bspline" else resample(t, dy, dx, name)
                vals.append(band_ratio(r[PAD:-PAD, PAD:-PAD], 1.0))
        out[name] = float(np.mean(vals) - base)
    return base, out


def main():
    rng = np.random.default_rng(20260824)
    j = {}

    scenes = {
        "noise-free detail (1/f)": [bandlimited_field(rng, 1.0) for _ in range(8)],
        "noise-free detail (flat spectrum)": [bandlimited_field(rng, 0.0) for _ in range(8)],
        "pure white noise": [white_noise(rng) for _ in range(8)],
    }

    print("=" * 78)
    print("POST-HOC: does the dex gain need noise in the scene to appear?")
    print("=" * 78)
    print(f"  band_ratio bands: hi 0.30-0.48 cyc/px, lo 0.02-0.10 cyc/px; {N}x{N} fields\n")
    print(f"  {'scene':36s} " + " ".join(f"{n:>10s}" for n in NAMES))
    for label, tiles in scenes.items():
        _, g = ladder(tiles)
        rel = {n: g[n] - g["catmullrom"] for n in NAMES}
        j[label] = rel
        print(f"  {label:36s} " + " ".join(f"{rel[n]:>+10.4f}" for n in NAMES))

    print("\n  (values are dex gain vs catmullrom, phase-averaged over 7 non-zero phases)")

    l3 = [j[k]["lanczos3"] for k in scenes]
    spread = max(l3) - min(l3)
    print(f"\n  lanczos3 gain across scene types: {min(l3):+.4f} .. {max(l3):+.4f}  spread {spread:.4f} dex")
    if spread < 0.02:
        print("  -> the gain does NOT depend on scene content: it is the kernel's transfer")
        print("     function, and it appears in full on a scene with no noise process in it.")
        print("     Reading (a) 'the number is noise amplification' is WRONG as a general claim.")
        print("     Reading (b) holds, with the rider that on noise-dominated ground the")
        print("     recovered high-band energy IS noise, because a linear kernel cannot choose.")
    else:
        print("  -> the gain DOES depend on scene content; reading (b) is wrong and the")
        print("     detail-region number needs re-deriving on a noise-free scene.")
    j["lanczos3_spread_dex"] = float(spread)
    j["content_independent"] = bool(spread < 0.02)

    print("\n  -- power control: this comparison must be able to separate scenes at all --")
    print("     If every scene type read the same for a kernel that is genuinely different,")
    print("     the harness would be insensitive to content by construction.")
    mit = [j[k]["mitchell"] for k in scenes]
    l2 = [j[k]["lanczos2"] for k in scenes]
    print(f"     mitchell across scenes : {min(mit):+.4f} .. {max(mit):+.4f}")
    print(f"     lanczos2 across scenes : {min(l2):+.4f} .. {max(l2):+.4f}")
    sep = abs(np.mean(mit) - np.mean(l3))
    print(f"     mitchell vs lanczos3 separation: {sep:.4f} dex  "
          f"{'PASS' if sep > 0.1 else 'FAIL'} (harness distinguishes kernels)")
    j["kernel_separation_dex"] = float(sep)

    with open(os.path.join(OUT, "x8_content.json"), "w", encoding="utf-8") as fh:
        json.dump(j, fh, indent=1)
    print(f"\nwrote {os.path.join(OUT, 'x8_content.json')}")
    print("END OF X8 -- reaching this line is part of the contract")


if __name__ == "__main__":
    main()
