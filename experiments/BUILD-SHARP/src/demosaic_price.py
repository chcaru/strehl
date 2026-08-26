"""Price the demosaic on the delivered pixels.

Why this is the right thing to measure
--------------------------------------
The shipped render is NOT a quad collapse. Verified from the artefact rather
than from a comment: `SHIP-V1/*.tiff` read (4688, 7032, 3) uint16, which is full
sensel resolution, where a quad collapse would be (2344, 3516, 3). So the merge
estimates four CFA sites per quad, re-interleaves them into a Bayer mosaic, and
Malvar-He-Cutler reconstructs three full-resolution planes from it. That last
step is the final resampling-like operation the delivered pixels pass through
and nothing in this project has ever priced it.

The information ceiling, stated before any measurement
------------------------------------------------------
Red is known at ONE site per quad, so in output (sensel) coordinates red is
sampled on a lattice of period 2 and its Nyquist is **0.25 cyc/px**. Above that
frequency no red detail was measured. Anything a demosaic delivers there is
inferred from green under the slowly-varying-chroma assumption. That is not
automatically wrong -- green is sampled at quincunx density and carries real
luminance detail to 0.5 -- but it is inference, and whether it helps depends
entirely on whether the scene's chroma really is slowly varying.

So a single number is the wrong summary again. Two scene families bracket it:

  neutral  R = G = B          chroma EXACTLY constant: the assumption holds
                              perfectly. This is Malvar's best case.
  chroma   R varies, G,B flat chroma varies at the signal frequency: the
                              assumption is maximally violated. Worst case.

Real subjects live between them, and reporting only one would be advocacy.

Arms
----
  malvar     the shipping path (strehl_core::demosaic)
  bilinear   demosaic.rs's own reference arm, the "direct upsample" of ORCH's
             question (a)
  ceiling    ORCH's question (b): the information present in the merged planes
             BEFORE re-interleaving, reconstructed ideally from the red lattice
             alone. Above 0.25 this arm ALIASES, which is the point -- it shows
             what red-only information is actually worth.

Metrics
-------
  gain    amplitude delivered at the signal frequency / true amplitude. This is
          MTF.
  false   rms of everything in the output that is NOT at the signal frequency,
          as a fraction of true amplitude. A demosaic can deliver gain 1.0 and
          still be wrong, by putting the energy in an alias or a zipper, and a
          gain-only report would call that a success.
"""

from __future__ import annotations

import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

EXE = Path("target/release/examples/demosaic-plane.exe")
N = 512
MARGIN = 24  # keep the mirror border out of every measurement


def write_raw(path: Path, a: np.ndarray) -> None:
    a = np.ascontiguousarray(a, dtype="<f4")
    with open(path, "wb") as f:
        f.write(struct.pack("<II", a.shape[1], a.shape[0]))
        f.write(a.tobytes())


def read_rgb(path: Path) -> np.ndarray:
    b = path.read_bytes()
    w, h = struct.unpack("<II", b[:8])
    return np.frombuffer(b[8:], dtype="<f4").reshape(h, w, 3).astype(np.float64)


def run_arm(mosaic: np.ndarray, arm: str) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        i, o = Path(d) / "in.raw", Path(d) / "out.raw"
        write_raw(i, mosaic)
        r = subprocess.run([str(EXE), str(i), str(o), arm], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"{arm}: {r.stderr.strip()}")
        return read_rgb(o)


def scene(f: float, kind: str):
    """Full-resolution truth planes for a horizontal sinusoid at f cyc/px."""
    x = np.arange(N)
    s = np.sin(2 * np.pi * f * x)[None, :] * np.ones((N, 1))
    base = 0.5
    amp = 0.2
    if kind == "neutral":
        r = g = b = base + amp * s
    elif kind == "chroma":
        r = base + amp * s
        g = np.full((N, N), base)
        b = np.full((N, N), base)
    else:
        raise ValueError(kind)
    return np.asarray(r), np.asarray(g), np.asarray(b)


def mosaic_from(r, g, b) -> np.ndarray:
    """RGGB: (0,0)=R  (1,0)=G  (0,1)=G  (1,1)=B, indices (x%2, y%2)."""
    m = g.copy()
    m[0::2, 0::2] = r[0::2, 0::2]
    m[1::2, 1::2] = b[1::2, 1::2]
    return m


def project(img: np.ndarray, f: float):
    """Return (amplitude at f, rms of the residual after removing it)."""
    m = img[MARGIN:-MARGIN, MARGIN:-MARGIN]
    m = m - m.mean()
    x = np.arange(m.shape[1])
    s, c = np.sin(2 * np.pi * f * x), np.cos(2 * np.pi * f * x)
    # least-squares amplitude of the f component, per row then pooled
    a_s = 2.0 * (m * s).mean(axis=1)
    a_c = 2.0 * (m * c).mean(axis=1)
    fit = a_s[:, None] * s[None, :] + a_c[:, None] * c[None, :]
    amp = float(np.hypot(a_s.mean(), a_c.mean()))
    resid = float(np.sqrt(((m - fit) ** 2).mean()))
    return amp, resid


def ceiling_arm(r: np.ndarray, f: float):
    """Ideal reconstruction of red from the red lattice alone (period 2).

    Zero-order held onto the full grid then ideally low-passed is equivalent, for
    a pure tone, to evaluating the tone the lattice actually saw -- which aliases
    to |f - 0.5| above f = 0.25. Implemented by direct band-limited resynthesis
    from the samples so the aliasing is produced, not asserted.
    """
    x = np.arange(N)
    samp = r[0::2, 0::2]  # red at its own lattice
    xs = np.arange(0, N, 2)
    m = samp - samp.mean()
    s, c = np.sin(2 * np.pi * f * xs), np.cos(2 * np.pi * f * xs)
    a_s = 2.0 * (m * s).mean()
    a_c = 2.0 * (m * c).mean()
    return float(np.hypot(a_s, a_c))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plant", type=float, default=None,
                    help="POTENCY: blur the demosaiced red with a [t,1-2t,t] kernel")
    args = ap.parse_args()

    if not EXE.exists():
        print(f"missing {EXE}; cargo build -p strehl-core --release --example demosaic-plane")
        return 2

    freqs = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
    print("Red channel, output (sensel) coordinates. Red's own Nyquist is 0.25.")
    print("gain = MTF at the signal frequency; false = rms of everything else,")
    print("both as a fraction of the true amplitude.\n")

    for kind in ("neutral", "chroma"):
        print("=" * 78)
        print(f"SCENE: {kind}" + ("   (chroma exactly constant -- Malvar's best case)"
                                  if kind == "neutral" else
                                  "   (chroma varies at the signal -- worst case)"))
        print("=" * 78)
        print(f"{'f':>6} | {'malvar gain':>11} {'false':>7} | {'bilin gain':>10} {'false':>7} "
              f"| {'red-only':>8}")
        for f in freqs:
            r, g, b = scene(f, kind)
            m = mosaic_from(r, g, b)
            truth_amp, _ = project(r, f)
            out_m = run_arm(m, "malvar")[:, :, 0]
            out_b = run_arm(m, "bilinear")[:, :, 0]
            if args.plant is not None:
                t = args.plant
                for arr in (out_m, out_b):
                    arr[:, 1:-1] = (t * arr[:, :-2] + (1 - 2 * t) * arr[:, 1:-1]
                                    + t * arr[:, 2:])
            gm, fm = project(out_m, f)
            gb, fb = project(out_b, f)
            ceil = ceiling_arm(r, f)
            print(f"{f:6.2f} | {gm / truth_amp:11.4f} {fm / truth_amp:7.4f} "
                  f"| {gb / truth_amp:10.4f} {fb / truth_amp:7.4f} "
                  f"| {ceil / truth_amp:8.4f}")
        print()

    if args.plant is not None:
        t = args.plant
        print("=" * 78)
        print("POTENCY")
        print("=" * 78)
        print(f"planted separable blur [{t}, {1 - 2 * t}, {t}] on the demosaiced red.")
        print("Its closed-form response is 1 - 2t(1 - cos 2*pi*f); the table above")
        print("must be that factor below the unplanted table:")
        for f in (0.15, 0.25, 0.35):
            print(f"  f={f:.2f}  expected factor {1 - 2 * t * (1 - np.cos(2 * np.pi * f)):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
