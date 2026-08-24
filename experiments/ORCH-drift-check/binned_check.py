"""Is the render carrying genuine full-sensor detail, or 2x-binned detail
stretched back to full dimensions?

M95 reports "the default output is binned -- 8.2 MP from a 32.9 MP capture,
Nyquist at 48.94 cy/mm where the lens still delivers 42-62 % MTF". The render is
7032 x 4688 = 33.0 MP on disk, and each CFA plane is 3516 x 2344 = 8.24 MP. If
the merge estimates one value per 2x2 Bayer quad and the result is scaled back to
sensor dimensions, then the file has 33 MP of PIXELS but only 8.2 MP of
INFORMATION -- a factor of two in linear resolution, which would dwarf every
other softness mechanism measured so far (the gate's radial smear is ~1 px, and
the 0.9315 coverage crop failed to show a band limit at all).

THE TEST. Downsample by 2 and put it back. An image that already contains only
2x-binned information loses nothing, because there is nothing above the binned
Nyquist to lose. An image with genuine full-resolution detail loses a lot.

    R(x) = HF energy of roundtrip2x(x) / HF energy of x

    R ~ 1  =>  x was already binned
    R << 1 =>  x carried real detail above the binned Nyquist

CONTROLS, because a bare ratio proves nothing on its own:
  POSITIVE  R(roundtrip2x(render)) must be ~1. This is the reading the test
            gives on an image KNOWN to be binned, constructed from the very
            same pixels, so it calibrates "binned" on this subject rather than
            against an assumption.
  NEGATIVE  R(white noise) must be far below 1. This is the reading on an image
            known to be full-resolution, and it bounds how small R can get.
  The render's R is then read against those two anchors, not against 1.0 in the
  abstract.
"""
import sys

import numpy as np
import tifffile
from scipy.ndimage import zoom

TILE = 256
HF_LO = 0.28   # above the 2x-binned Nyquist of 0.25 cyc/px


def hf_energy(y):
    f = np.fft.fftfreq(TILE)
    fr = np.sqrt((f[:, None] ** 2) + (f[None, :] ** 2))
    band = fr >= HF_LO
    win = np.outer(np.hanning(TILE), np.hanning(TILE))
    h, w = y.shape
    cy, cx = h // 2, w // 2
    tot, n = 0.0, 0
    for i in range(-3, 4):
        for j in range(-3, 4):
            ty, tx = cy + i * TILE, cx + j * TILE
            if not (0 <= ty < h - TILE and 0 <= tx < w - TILE):
                continue
            t = y[ty:ty + TILE, tx:tx + TILE].astype(np.float64)
            p = np.abs(np.fft.fft2((t - t.mean()) * win)) ** 2
            tot += p[band].mean()
            n += 1
    return tot / n


def roundtrip2x(y):
    """The exact binning operator: 2x2 block mean, then block replication.

    THIS OPERATOR IS IDEMPOTENT and that is the whole point. A first version used
    bilinear zoom out and back, whose positive control read R = 0.3985 instead of
    ~1: bilinear interpolation is itself a low-pass, so a second round trip keeps
    removing energy from content that was already binned, and the test could not
    tell "binned" from "blurred twice". Block mean followed by replication
    satisfies bin(bin(x)) == bin(x) exactly, so a known-binned image reads
    R = 1.0000 by construction and the positive control is trustworthy rather
    than approximate.
    """
    h, w = y.shape
    h2, w2 = h - (h % 2), w - (w % 2)
    b = y[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2).mean(axis=(1, 3))
    out = np.kron(b, np.ones((2, 2), dtype=b.dtype))
    if out.shape != y.shape:
        pad = np.array(y.shape) - np.array(out.shape)
        out = np.pad(out, ((0, pad[0]), (0, pad[1])), mode="edge")
    return out


def R(y):
    return hf_energy(roundtrip2x(y)) / hf_energy(y)


if __name__ == "__main__":
    path = sys.argv[1]
    a = tifffile.imread(path)
    y = (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1]
         + 0.0722 * a[:, :, 2]).astype(np.float32)
    del a
    print(f"{path}  {y.shape}\n")

    r_render = R(y)

    # POSITIVE control: an image we KNOW is 2x-binned, built from these pixels.
    y_binned = roundtrip2x(y).astype(np.float32)
    r_pos = R(y_binned)

    # NEGATIVE control: an image we KNOW is full resolution.
    rng = np.random.default_rng(20260824)
    y_noise = rng.normal(1000, 100, (TILE * 8, TILE * 8)).astype(np.float32)
    r_neg = R(y_noise)

    print(f"{'arm':<42} {'R':>8}")
    print(f"{'NEGATIVE control (white noise, full-res)':<42} {r_neg:>8.4f}")
    print(f"{'the render as shipped':<42} {r_render:>8.4f}")
    print(f"{'POSITIVE control (render, known 2x-binned)':<42} {r_pos:>8.4f}")
    print()

    if not (r_pos > 0.5):
        print("POSITIVE CONTROL DID NOT LAND: a known-binned image did not read")
        print("R ~ 1. The test cannot distinguish binned from not; report nothing.")
        sys.exit(1)
    if not (r_neg < 0.25):
        print("NEGATIVE CONTROL DID NOT LAND: full-resolution noise did not read")
        print("R << 1. The test has no dynamic range; report nothing.")
        sys.exit(1)
    print("both controls landed.\n")

    # Place the render on the interval the two controls define.
    frac = (r_render - r_neg) / (r_pos - r_neg)
    print(f"On the scale where 0 = full sensor resolution and 1 = 2x binned,")
    print(f"the render sits at {frac:.3f}.")
    print()
    if r_render > 1.0:
        print("INCONCLUSIVE -- AND THE READOUT ABOVE IS INVALID.")
        print()
        print("R > 1 means binning the render ADDS high-frequency energy rather")
        print("than removing it: the block replication injects edges at the 2-px")
        print("scale that are stronger than any detail the render held there.")
        print("That is qualitatively consistent with a smooth, already-binned")
        print("render, but it puts the reading 6x above the upper anchor, so")
        print("placing it linearly between the two controls is meaningless and")
        print("the verdict lines below must not be quoted.")
        print()
        print("The flaw is the NEGATIVE control: white noise is not the right")
        print("anchor for 'full resolution'. The correct one is a single")
        print("demosaiced frame from this camera, which is not available to this")
        print("script. Use M95's measurement instead -- it approached the same")
        print("question through the modelled noise sd (G1-G2 carrying 1.78-2.65x")
        print("sigma in focus vs 1.09x defocused) and its controls did land.")
        sys.exit(2)
    if frac > 0.75:
        print("VERDICT: the render is consistent with 2x-BINNED information.")
        print("M95's finding is reproduced independently: the file has 33 MP of")
        print("pixels and far less than 33 MP of detail.")
    elif frac < 0.35:
        print("VERDICT: the render carries genuine detail above the binned")
        print("Nyquist. It is NOT simply 8.2 MP stretched to 33 MP.")
    else:
        print("VERDICT: intermediate -- partial detail above the binned Nyquist.")
        print("Neither 'binned' nor 'full resolution' describes it honestly.")
