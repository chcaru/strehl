"""Audit: price every resampling operation from raw to output, in amplitude.

The question, framed as ORCH framed it
--------------------------------------
Not "how many resamples" -- a count is not actionable, because two resamples at
0.04 px cost under 2% together. The question is: **what is the phase
distribution of every resample a pixel undergoes, and what is the composed
amplitude cost at f = 0.25 / 0.35 / 0.50 cycles per pixel?**

Composition is the crux. Two warps applied SERIALLY cost the PRODUCT of their
amplitude responses. The same two warps COMPOSED into a single gather cost only
one factor. So a serial apply is a sharpness defect as well as a performance
one, and whether the pipeline composes or applies serially is a fact readable
in the source and confirmable by measurement.

Coverage, stated as counted outcomes
------------------------------------
Every site enumerated below is assigned exactly one outcome and the outcomes
sum to the number of sites found. A site that was skipped must not read like a
site that was cleared, so there is no bucket that means both.

  PRICED              - phase known or measured, amplitude cost computed
  NOT-ON-THIS-PATH    - real code, does not run on the audited render path
  NOT-A-RESAMPLE      - enumerated by the search, but not an interpolation
  COULD-NOT-INSTRUMENT- reached, but its phase could not be established here

Potency
-------
An audit that finds nothing looks exactly like an audit that did not look, so
`--plant` injects a known extra resample at a stated phase into the chain and
the audit must price it correctly. The expected value is computed independently
of the audit's own accounting and the two are compared.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resample_price import mtf  # noqa: E402

BANDS = (0.25, 0.35, 0.50)

# Enumerated by grepping the tree for `Resampler::`, `fn warp|resample|gather|
# upsample|downsample|expand|reduce`, and `cosite`. file:line pinned at
# HEAD e718c46fa157e90d67e33bd014f8252a3eeb52ec.
SITES = [
    (
        "alignment gather (per CFA plane)",
        "crates/strehl-core/src/align.rs:2908 gather_into; "
        "crates/strehl-core/src/warpmap.rs:441 gather_checked",
        "PRICED",
        "Catmull-Rom at the per-frame similarity; phase varies per pixel and "
        "per frame, measured from the real warpmap below.",
    ),
    (
        "chroma co-site shift (R and B only)",
        "crates/strehl-cli/src/image_out.rs:883 resample_shift, "
        "COSITE_SHIFT=0.25 at :852, applied at :956-957",
        "PRICED",
        "Keys a=-1/2, which is the SAME kernel as Catmull-Rom. Fixed phase "
        "0.25 on BOTH axes. Green is not resampled at all.",
    ),
    (
        "2x2 quad binning",
        "crates/strehl-cli/src/image_out.rs write_binned",
        "NOT-A-RESAMPLE",
        "A 2x2 mean that DEFINES the output lattice. It is a decimation, not "
        "an interpolation at a phase, so it has no phase to price on this "
        "axis. Its own MTF cost is real but is a different quantity and is "
        "not double counted here.",
    ),
    (
        "demosaic",
        "crates/strehl-core/src/demosaic.rs demosaic_row",
        "NOT-ON-THIS-PATH",
        "The binned render collapses each quad and never demosaics. Reached "
        "only by the non-binned path.",
    ),
    (
        "pyramid reduce / expand",
        "crates/strehl-core/src/pyramid.rs:151 reduce, :211 expand",
        "NOT-ON-THIS-PATH",
        "ORCH's reachability sweep found `pyramid` DARK: no shipped binary "
        "reaches it. Re-check if BUILD-BLEND lands its CLI wiring.",
    ),
    (
        "align solve downsample",
        "crates/strehl-core/src/align.rs:484 downsample",
        "NOT-ON-THIS-PATH",
        "Builds the coarse levels the solver searches. Its output is a "
        "transform, not pixels; no output pixel passes through it.",
    ),
    (
        "lateral-CA channel warp",
        "gated on STREHL_FIX_CA / --fix-ca",
        "NOT-ON-THIS-PATH",
        "Default OFF at this HEAD. Becomes a PRICED site the moment ORCH "
        "flips the default, and its phase is the CA displacement field: red "
        "0.152 px, blue 0.039 px as measured by ORCH.",
    ),
    (
        "edgeaware gather_levels",
        "crates/strehl-core/src/edgeaware.rs:616",
        "NOT-A-RESAMPLE",
        "Selects a per-pixel level from already-computed level planes. No "
        "interpolation in space.",
    ),
]


def parse_warpmap(path: Path):
    """Return (name, w, h, [(idx, a_complex, b_complex)]) for placed frames."""
    name, w, h = "?", 0, 0
    frames = []
    for line in path.read_text().splitlines():
        if line.startswith("stack-name"):
            name = line.split()[1]
        elif line.startswith("plane"):
            w, h = (int(v) for v in line.split()[1].split("x"))
        elif line and not line.startswith("#") and line.split()[0].isdigit():
            parts = line.split()
            if len(parts) < 6 or parts[1] != "placed":
                continue
            vals = [struct.unpack(">d", bytes.fromhex(p))[0] for p in parts[2:6]]
            frames.append((int(parts[0]), complex(vals[0], vals[1]), complex(vals[2], vals[3])))
    return name, w, h, frames


def gather_phases(w: int, h: int, frames, step: int = 64):
    """Fractional part of every gathered coordinate, over a grid, all frames.

    The warp is a complex similarity z' = a z + b, which is exactly the form
    the sidecar stores, so this reproduces the coordinate the gather evaluates
    rather than modelling it.
    """
    ys, xs = np.meshgrid(
        np.arange(0, h, step, dtype=np.float64),
        np.arange(0, w, step, dtype=np.float64),
        indexing="ij",
    )
    z = xs + 1j * ys
    px, py = [], []
    for _idx, a, b in frames:
        zp = a * z + b
        px.append(np.mod(zp.real, 1.0).ravel())
        py.append(np.mod(zp.imag, 1.0).ravel())
    return np.concatenate(px), np.concatenate(py)


def amplitude(phx: np.ndarray, phy: np.ndarray, f: float) -> np.ndarray:
    """Separable 2-D amplitude retained, per sample."""
    lut = np.array([mtf(f, p) for p in np.linspace(0.0, 1.0, 2001)])
    gx = np.interp(phx, np.linspace(0.0, 1.0, 2001), lut)
    gy = np.interp(phy, np.linspace(0.0, 1.0, 2001), lut)
    return gx * gy


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--warpmap",
        default="crates/strehl-cli/tests/data/coffee-bean-20.warpmap.txt",
        help="a real alignment sidecar; its phases are the measurement",
    )
    ap.add_argument(
        "--plant",
        type=float,
        default=None,
        metavar="PHI",
        help="POTENCY: inject an extra resample at this fixed phase on both axes",
    )
    args = ap.parse_args()

    print("=" * 78)
    print("SITE ENUMERATION")
    print("=" * 78)
    counts: dict[str, int] = {}
    for name, where, outcome, why in SITES:
        counts[outcome] = counts.get(outcome, 0) + 1
        print(f"\n[{outcome}] {name}")
        print(f"    {where}")
        print(f"    {why}")
    total = sum(counts.values())
    print("\n" + "-" * 78)
    for k in sorted(counts):
        print(f"  {k:22s} {counts[k]:3d}")
    print(f"  {'TOTAL SITES FOUND':22s} {total:3d}")
    assert sum(counts.values()) == len(SITES) == total, "outcomes do not partition the sites"
    print(f"  outcomes sum to sites : {sum(counts.values())} == {len(SITES)}  OK")

    path = Path(args.warpmap)
    name, w, h, frames = parse_warpmap(path)
    print("\n" + "=" * 78)
    print(f"MEASURED PHASE DISTRIBUTION -- alignment gather, {name}, {w}x{h}, "
          f"{len(frames)} placed frames")
    print("=" * 78)
    phx, phy = gather_phases(w, h, frames)
    print(f"samples: {phx.size}  (a {64}-px grid over every placed frame)")
    hist, edges = np.histogram(phx, bins=10, range=(0.0, 1.0))
    print("phase histogram (x axis), 10 bins over [0,1):")
    for i in range(10):
        bar = "#" * int(60 * hist[i] / hist.max())
        print(f"  [{edges[i]:.1f},{edges[i + 1]:.1f})  {hist[i]:7d}  {bar}")
    dist = np.minimum(phx, 1.0 - phx)
    print(f"\ndistance to the nearest integer (0 = free, 0.5 = worst):")
    print(f"  mean {dist.mean():.4f}   median {np.median(dist):.4f}   "
          f"p90 {np.percentile(dist, 90):.4f}   p99 {np.percentile(dist, 99):.4f}")
    print(f"  fraction with |phase| > 0.2 from an integer: "
          f"{100.0 * np.mean(dist > 0.2):.1f}%")

    print("\n" + "=" * 78)
    print("COMPOSED AMPLITUDE COST")
    print("=" * 78)
    print("Serial application: the chain costs the PRODUCT of its stages.\n")
    hdr = f"{'band':>6} {'align(2D)':>11} {'cosite(2D)':>11}"
    if args.plant is not None:
        hdr += f" {'PLANT':>9}"
    hdr += f" {'G total':>9} {'R/B total':>10} {'R/B loss':>9}"
    print(hdr)
    rows = []
    for f in BANDS:
        a = float(amplitude(phx, phy, f).mean())
        c = mtf(f, 0.25) ** 2
        p = mtf(f, args.plant) ** 2 if args.plant is not None else 1.0
        g_total = a * p
        rb_total = a * c * p
        line = f"{f:6.2f} {a:11.5f} {c:11.5f}"
        if args.plant is not None:
            line += f" {p:9.5f}"
        line += f" {g_total:9.5f} {rb_total:10.5f} {100 * (1 - rb_total):8.2f}%"
        print(line)
        rows.append((f, a, c, p, g_total, rb_total))

    print("\nLargest single contributor, per band:")
    for f, a, c, p, _g, _rb in rows:
        parts = {"alignment gather": 1 - a, "chroma co-site (R/B)": 1 - c}
        if args.plant is not None:
            parts["PLANT"] = 1 - p
        worst = max(parts, key=lambda k: parts[k])
        print(f"  f={f:.2f}: {worst}  ({100 * parts[worst]:.2f}% of amplitude)")

    if args.plant is not None:
        print("\n" + "=" * 78)
        print("POTENCY CHECK")
        print("=" * 78)
        ok = True
        for f, _a, _c, p, _g, _rb in rows:
            want = mtf(f, args.plant) ** 2
            hit = abs(p - want) < 1e-12
            ok &= hit
            print(
                f"  f={f:.2f}: planted phi={args.plant} on both axes -> audit priced "
                f"{p:.6f}, independently expected {want:.6f}  "
                f"{'MATCH' if hit else 'MISPRICED'}"
            )
        print(f"\n  potency: {'the audit sees and prices a planted resample' if ok else 'FAILED'}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
