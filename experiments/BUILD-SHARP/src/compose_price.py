"""Do the gather loss and the demosaic loss compose as the naive product?

ORCH asked for this with "same dimensionality on both sides". Having checked my
own harness, there are TWO dimensionality traps here, not one, and the second is
the dangerous one.

  1. AXES. `demosaic_price.py:94` builds a HORIZONTAL sinusoid, constant in y.
     So the 23.3 % green loss at f = 0.35 is a PER-AXIS (1-D) figure, directly
     comparable to the gather's per-axis 0.8211 and NOT to the 2-D 0.69776.
     Malvar is a 5x5 cross-channel filter and is not separable, so the 2-D
     demosaic factor cannot be obtained by squaring the 1-D one.

  2. SAMPLING GRID, and this one silently invalidated a product I published.
     The gather runs on the four CFA planes, each at HALF sensor resolution.
     The demosaic runs on the interleaved mosaic at FULL sensor resolution. A
     feature at f cycles per SENSOR pixel is at 2f cycles per CFA sample. My
     BUILD-SHARP.md 22.4 multiplied gather(0.35) by demosaic(0.35) as though
     those were the same frequency. They are not: one is 0.35 cyc/CFA-sample,
     the other 0.35 cyc/sensor-px. This is exactly what `RestoreConfig`'s
     `grid_factor` field exists to prevent (`restore.rs:208`).

So rather than argue the units, this measures the composition end to end
through the SHIPPED Rust demosaic, in one consistent frequency variable:
cycles per SENSOR pixel.

  D(f)   demosaic alone            interleave truth planes  -> Malvar
  G(f)   gather alone              CR-resample the CFA planes, measure there
  GD(f)  gather THEN demosaic      the real pipeline order

and asks whether GD == G * D.

Commissioning, because a composition test that cannot fail is worthless:
  NULL   phase 0 is an integer shift: G must be 1.0 and GD must equal D.
  PLANT  --plant t applies a known [t, 1-2t, t] blur to each CFA plane on top
         of the gather; both G and GD must move by the closed-form factor.
"""

from __future__ import annotations

import argparse
import struct
import subprocess
import tempfile
from pathlib import Path

import numpy as np

EXE = Path("target/release/examples/demosaic-plane.exe")
N = 512
MARGIN = 24


def write_raw(path: Path, a: np.ndarray) -> None:
    a = np.ascontiguousarray(a, dtype="<f4")
    with open(path, "wb") as f:
        f.write(struct.pack("<II", a.shape[1], a.shape[0]))
        f.write(a.tobytes())


def read_rgb(path: Path) -> np.ndarray:
    b = path.read_bytes()
    w, h = struct.unpack("<II", b[:8])
    return np.frombuffer(b[8:], dtype="<f4").reshape(h, w, 3).astype(np.float64)


def malvar(mosaic: np.ndarray) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        i, o = Path(d) / "in.raw", Path(d) / "out.raw"
        write_raw(i, mosaic)
        r = subprocess.run([str(EXE), str(i), str(o), "malvar"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip())
        return read_rgb(o)


def cr_taps(phase: float) -> np.ndarray:
    a = -0.5

    def k(x: float) -> float:
        x = abs(x)
        if x < 1:
            return (a + 2) * x ** 3 - (a + 3) * x ** 2 + 1
        if x < 2:
            return a * x ** 3 - 5 * a * x ** 2 + 8 * a * x - 4 * a
        return 0.0

    return np.array([k(n - phase) for n in (-1, 0, 1, 2)])


def resample_x(plane: np.ndarray, phase: float, extra: float = 0.0) -> np.ndarray:
    """Catmull-Rom gather along x, optionally with a planted [t,1-2t,t] blur."""
    out = np.zeros_like(plane)
    for t, w in zip((-1, 0, 1, 2), cr_taps(phase)):
        out += w * np.roll(plane, -t, axis=1)
    if extra:
        out = (extra * np.roll(out, 1, axis=1)
               + (1 - 2 * extra) * out
               + extra * np.roll(out, -1, axis=1))
    return out


def amp_at(img: np.ndarray, f: float, step: int = 1) -> float:
    """Least-squares amplitude of the f component along x, on a lattice of
    spacing `step` sensor pixels.

    DC is removed per row before projecting. `truth` carries a 0.5 pedestal and
    the window is a finite rectangle, so without this the pedestal's Dirichlet
    leakage lands in the projection and biases every amplitude here by up to
    +2.3% -- which is not a constant factor across D, G and GD and therefore
    manufactured an apparent interaction term in the factorisation. This
    omission was the defect V-DEMOSAIC found; the sibling estimator in
    `demosaic_price.py:project` had always removed the mean.
    """
    m = img[MARGIN:-MARGIN, MARGIN:-MARGIN]
    m = m - m.mean(axis=1, keepdims=True)
    x = np.arange(m.shape[1]) * step + MARGIN
    s, c = np.sin(2 * np.pi * f * x), np.cos(2 * np.pi * f * x)
    a_s = 2.0 * (m * s).mean(axis=1)
    a_c = 2.0 * (m * c).mean(axis=1)
    return float(np.hypot(a_s.mean(), a_c.mean()))


def truth(f: float):
    x = np.arange(N)
    s = np.sin(2 * np.pi * f * x)[None, :] * np.ones((N, 1))
    return 0.5 + 0.2 * s


def cfa_planes(full: np.ndarray):
    """The four CFA sub-lattices, RGGB, each at half sensor resolution."""
    return {
        "R": full[0::2, 0::2].copy(),
        "G1": full[0::2, 1::2].copy(),
        "G2": full[1::2, 0::2].copy(),
        "B": full[1::2, 1::2].copy(),
    }


def interleave(p) -> np.ndarray:
    m = np.zeros((N, N))
    m[0::2, 0::2] = p["R"]
    m[0::2, 1::2] = p["G1"]
    m[1::2, 0::2] = p["G2"]
    m[1::2, 1::2] = p["B"]
    return m


def green_gain(rgb: np.ndarray, f: float) -> float:
    return amp_at(rgb[:, :, 1], f) / 0.2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plant", type=float, default=0.0)
    ap.add_argument("--phases", type=int, default=16)
    args = ap.parse_args()
    if not EXE.exists():
        print(f"missing {EXE}; run from the crate root")
        return 2

    freqs = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    phases = np.arange(args.phases) / args.phases

    print("Frequency variable: cycles per SENSOR pixel. Green channel, per-axis")
    print("(horizontal). Gather phases averaged over a uniform grid, matching the")
    print("near-uniform phase histogram measured from the real warpmap in s20.")
    if args.plant:
        print(f"PLANT ACTIVE: extra [{args.plant},{1-2*args.plant},{args.plant}] blur per CFA plane")
    print()
    print(f"{'f':>6}{'D':>10}{'G':>10}{'GD':>10}{'G*D':>10}{'GD/(G*D)':>11}")

    rows = []
    for f in freqs:
        full = truth(f)
        base = cfa_planes(full)

        d = green_gain(malvar(interleave(base)), f)

        g_acc, gd_acc = [], []
        for ph in phases:
            warped = {k: resample_x(v, ph, args.plant) for k, v in base.items()}
            # G measured on the CFA plane itself, in sensor-frequency terms: the
            # G1 lattice has spacing 2 sensor px, so the same f is read there
            # with step=2. This is the unit conversion done by measurement
            # instead of by assumption.
            g_acc.append(amp_at(warped["G1"], f, step=2) / max(amp_at(base["G1"], f, step=2), 1e-12))
            gd_acc.append(green_gain(malvar(interleave(warped)), f))
        g = float(np.mean(g_acc))
        gd = float(np.mean(gd_acc))
        prod = g * d
        rows.append((f, d, g, gd, prod))
        print(f"{f:6.2f}{d:10.4f}{g:10.4f}{gd:10.4f}{prod:10.4f}"
              f"{(gd / prod if prod > 1e-9 else float('nan')):11.4f}")

    print()
    print("NULL (phase 0, an integer shift: G must be 1.0 and GD must equal D)")
    for f in (0.20, 0.35):
        full = truth(f)
        base = cfa_planes(full)
        d = green_gain(malvar(interleave(base)), f)
        w = {k: resample_x(v, 0.0, 0.0) for k, v in base.items()}
        g = amp_at(w["G1"], f, step=2) / max(amp_at(base["G1"], f, step=2), 1e-12)
        gd = green_gain(malvar(interleave(w)), f)
        print(f"  f={f:.2f}  G={g:.6f} (want 1.000000)   GD={gd:.6f}  D={d:.6f}  "
              f"diff={abs(gd - d):.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
