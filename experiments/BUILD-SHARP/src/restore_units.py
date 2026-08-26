"""Settle the suspected units collision in restore.rs BY MEASUREMENT.

V-DEMOSAIC's hypothesis (relayed by ORCH, item 3): `design_fir` fits `cfg.gain(f, .)`
over f in (0, 0.5) using a basis whose lags `k` index samples of the plane, while
`cfg.gain`/`knee` treat `f` as an OUTPUT frequency.  If the plane's sample spacing is
2 output px, the shipped correction would land at half the output frequency it was
designed for.

This does not reason about it.  It plants pure tones at known frequencies of the
ARRAY THAT IS RESTORED, runs the real shipped Rust (`examples/restore-plane.rs`, which
calls `strehl_core::restore::restore_plane` itself -- no Python reimplementation), and
measures the realised gain.  It then scores the measurement against TWO rival
predictions:

    H0 (no collision)  realised(phi) == fir_response(taps, phi)
    H1 (collision)     realised(phi) == fir_response(taps, 2*phi)

Reporting H0 only would be worthless: a test that cannot express the defect cannot
find it absent.  Both residuals are printed, and the run is declared VACUOUS unless
the two predictions actually differ -- an agreement is only evidence if a
disagreement was possible.

Second, independent discriminator at array Nyquist.  When grid_factor > 1, `roll_off`
drives the EXCESS gain to exactly zero at f = 0.5 in the design axis, so:

    if the applied axis IS the design axis   -> realised(0.5) ~ 1.0 (the taper's zero)
    if the applied axis is HALF the design   -> array Nyquist sits at design f = 0.25,
                                                which is the KNEE, i.e. maximum boost

Those two predictions are far apart, which is what makes the discriminator sharp.

Both grid_factor modes are exercised.  grid_factor = 1.0 is what the shipped path
actually uses (`restore.rs:1321` in `RestorePlan::config`, consumed at
`merge_cmd.rs:6000-6001`); grid_factor = 2.0 is the mode where a collision, if the
hypothesis were right, would be largest -- so it serves as the positive control on
the instrument's ability to see one.
"""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
EXE = ROOT / "target" / "release" / "examples" / "restore-plane.exe"
TMP = Path(r"C:\dev\strehl-out\BUILD-SHARP\restore-units")

N = 256
MARGIN = 24          # >> the 4-tap half-filter, so borders cannot reach the window
PEDESTAL = 8000.0
AMP = 1000.0
SIGMA2 = 100.0
GAIN_CAP = 4.0


def write_raw(path: Path, a: np.ndarray) -> None:
    h, w = a.shape
    with open(path, "wb") as f:
        f.write(struct.pack("<II", w, h))
        f.write(a.astype("<f4").tobytes())


def read_raw(path: Path) -> np.ndarray:
    b = path.read_bytes()
    w, h = struct.unpack("<II", b[:8])
    return np.frombuffer(b[8:], dtype="<f4").reshape(h, w).astype(np.float64)


def tone(phi: float) -> np.ndarray:
    x = np.arange(N)
    row = PEDESTAL + AMP * np.cos(2.0 * np.pi * phi * x)
    return np.tile(row, (N, 1))


def amp_at(a: np.ndarray, phi: float) -> float:
    """Amplitude of the phi component, measured in the interior only.

    DC is removed before projection.  Omitting it is exactly the defect V-DEMOSAIC
    found in compose_price.py's amp_at, and it biases every amplitude here by
    Dirichlet leakage off the 8000 DN pedestal.
    """
    row = a[MARGIN:-MARGIN, MARGIN:-MARGIN].mean(axis=0)
    row = row - row.mean()
    n = row.size
    x = np.arange(n)
    c = 2.0 * (row * np.cos(2.0 * np.pi * phi * x)).mean()
    s = 2.0 * (row * np.sin(2.0 * np.pi * phi * x)).mean()
    if abs(phi - 0.5) < 1e-12:
        return abs((row * np.cos(np.pi * x)).mean())
    return float(np.hypot(c, s))


def fir_response(taps: list[float], f: float) -> float:
    g = taps[0]
    for k, t in enumerate(taps[1:], start=1):
        g += 2.0 * t * np.cos(2.0 * np.pi * f * k)
    return float(g)


def run(grid_factor: float, phi: float) -> tuple[float, list[float], dict]:
    TMP.mkdir(parents=True, exist_ok=True)
    src, dst = TMP / "in.raw", TMP / "out.raw"
    a = tone(phi)
    write_raw(src, a)
    p = subprocess.run(
        [str(EXE), str(src), str(dst), str(grid_factor), str(SIGMA2), str(GAIN_CAP)],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise SystemExit(f"restore-plane failed: {p.stderr}")
    rep = json.loads(p.stdout)
    b = read_raw(dst)
    before = amp_at(a, phi)
    after = amp_at(b, phi)
    if before <= 0:
        raise SystemExit(f"planted tone at phi={phi} has zero amplitude -- test is broken")
    return after / before, rep["taps"], rep


def sweep(grid_factor: float) -> None:
    print(f"\n=== grid_factor = {grid_factor} ===")
    print(f"{'phi':>6} {'realised':>10} {'H0 fir(phi)':>12} {'H1 fir(2phi)':>13} "
          f"{'|r-H0|':>9} {'|r-H1|':>9}")
    r0 = []
    r1 = []
    sep = []
    for phi in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]:
        realised, taps, _ = run(grid_factor, phi)
        h0 = fir_response(taps, phi)
        h1 = fir_response(taps, 2.0 * phi)
        d0, d1 = abs(realised - h0), abs(realised - h1)
        r0.append(d0)
        r1.append(d1)
        sep.append(abs(h0 - h1))
        print(f"{phi:6.2f} {realised:10.5f} {h0:12.5f} {h1:13.5f} {d0:9.5f} {d1:9.5f}")
    print(f"  worst |realised - H0(no collision)| : {max(r0):.5f}")
    print(f"  worst |realised - H1(collision)|    : {max(r1):.5f}")
    print(f"  max separation between H0 and H1    : {max(sep):.5f}")
    if max(sep) < 0.02:
        print("  *** VACUOUS: the two hypotheses are not distinguishable here ***")
    else:
        verdict = "H0 -- NO COLLISION" if max(r0) < max(r1) else "H1 -- COLLISION"
        print(f"  VERDICT: {verdict}")


def nyquist_discriminator(grid_factor: float) -> None:
    """Independent of the sweep: uses the roll_off taper's zero, not the taps."""
    realised, taps, rep = run(grid_factor, 0.5)
    at_half = fir_response(taps, 0.5)
    at_knee = max(fir_response(taps, f) for f in np.linspace(0.0, 0.5, 1001))
    print(f"\n--- array-Nyquist discriminator, grid_factor = {grid_factor} ---")
    print(f"  realised gain at array Nyquist       : {realised:.5f}")
    print(f"  predicted if applied axis IS design  : {at_half:.5f}  (fir at 0.5)")
    print(f"  predicted if applied axis is HALF    : {at_knee:.5f}  (peak boost)")
    print(f"  reported gain_at_nyquist             : {rep['gain_at_nyquist']:.5f}")
    if abs(at_half - at_knee) < 0.02:
        print("  *** VACUOUS: the two predictions coincide ***")
    else:
        pick = "applied axis IS the design axis" if abs(realised - at_half) < abs(realised - at_knee) else "applied axis is HALF the design axis"
        print(f"  VERDICT: {pick}")


def main() -> int:
    if not EXE.exists():
        raise SystemExit(f"missing {EXE}; build it first")
    # grid_factor 1.0 is the SHIPPED value (restore.rs:1321 -> merge_cmd.rs:6000).
    # grid_factor 2.0 is the mode in which the alleged collision would be largest,
    # and therefore the positive control on the instrument.
    for gf in (1.0, 2.0):
        sweep(gf)
        nyquist_discriminator(gf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
