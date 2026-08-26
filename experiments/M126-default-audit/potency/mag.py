"""Magnitude of a gate's effect, in LINEAR 16-bit, scored on ORCH's taxonomy.

DEAD  = byte-identical
TOKEN = differs, peak <= 2 DN of 65535 -- a receipt for an effect no pixel carries
LIVE  = differs, peak > 2 DN

Hard tifffile import + uint16 assert: PIL.Image.open silently downconverts
16-bit RGB TIFFs to 8-bit and has corrupted 241 measurements in this project.
"""
import sys
import numpy as np
import tifffile  # HARD import -- never fall back to PIL for pixels

FS = 65535.0


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: dtype {a.dtype}, expected uint16"
    return a.astype(np.int32)


def verdict(pct, peak):
    if pct == 0.0:
        return "DEAD"
    return "TOKEN" if peak <= 2 else "LIVE"


def main():
    root = sys.argv[1]
    base = sys.argv[2]
    others = sys.argv[3].split(",")

    b = load(rf"{root}\{base}.tif")
    print(f"root {root}\n  base {base}   shape {b.shape}   mean {b.mean():.1f} DN\n")
    print(f"{'arm':10s} {'%differ':>9s} {'peak DN':>9s} {'peak %FS':>9s} "
          f"{'rms DN':>9s} {'verdict':>8s}")
    print("-" * 62)
    for name in others:
        a = load(rf"{root}\{name}.tif")
        assert a.shape == b.shape, f"{name}: shape {a.shape} != {b.shape}"
        d = np.abs(a - b)
        pct = 100.0 * float((d > 0).sum()) / d.size
        peak = int(d.max())
        rms = float(np.sqrt((d.astype(np.float64) ** 2).mean()))
        print(f"{name:10s} {pct:9.4f} {peak:9d} {100.0*peak/FS:9.4f} "
              f"{rms:9.4f} {verdict(pct, peak):>8s}")


if __name__ == "__main__":
    main()
