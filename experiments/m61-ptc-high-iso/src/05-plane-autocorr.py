"""05 -- is the B-plane deficit a real per-plane gain, or my estimator?

POST HOC.  Script 02 measured, at every ISO from 50 to 1000, that the PTC
slope of the B plane is ~0.83 x the slope of the two green planes, while G1
and G2 agree with each other to 0.1%.  Two readings:

  (a) B really has a lower conversion gain (or a digital per-channel scale
      below 1), which would make `profile.rs`'s single gain-for-all-planes
      wrong; or
  (b) my estimator under-reports B, because a tile SAMPLE variance about the
      tile mean is biased low when the noise is spatially CORRELATED --
      E[s^2] = sigma^2 * (n/(n-1)) * (1 - (1/n^2) * sum_ij rho_ij) -- and if
      B's temporal difference has positive short-lag autocorrelation and the
      greens' does not, (a) is an artefact of (b).

This distinguishes them.  On a smooth region of a real pair difference, per
plane, measure the 2-D autocorrelation rho(dy,dx) of the temporal difference
at small lags, then evaluate the exact 8x8-tile bias factor implied by it and
ask whether correcting for it makes B agree with green.

  IF rho ~ 0 for all four planes: the tile variance is unbiased, reading (b)
  is dead and the B deficit is a property of the sensor, not of me.
  IF rho > 0 for B specifically: the B deficit is my estimator, and the
  correct claim is that B's noise is spatially correlated, not that its gain
  is lower.

Either way the headline is untouched: the deficit is the same at ISO 50 and
at ISO 1000, so it cancels in r_high / r_low.  This is about labelling the
side-finding honestly.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m61-ptc-high-iso/src/05-plane-autocorr.py
"""

from __future__ import annotations

import glob
import importlib.util
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "plane-autocorr.txt")
CORPUS = r"D:\personal\macro"
PLANES = ("R", "G1", "G2", "B")
LAG = 4
TILE = 8
LINES: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LINES.append(s)


def load_ladder():
    spec = importlib.util.spec_from_file_location(
        "ladder", os.path.join(HERE, "02-ptc-ladder.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def autocorr(d: np.ndarray, lag: int) -> np.ndarray:
    """rho(dy,dx) for 0<=dy,dx<=lag on a mean-removed difference field."""
    x = d - d.mean()
    v = float((x * x).mean())
    out = np.zeros((lag + 1, lag + 1))
    for dy in range(lag + 1):
        for dx in range(lag + 1):
            a = x[dy:, dx:] if dx else x[dy:, :]
            b = x[: x.shape[0] - dy if dy else None,
                  : x.shape[1] - dx if dx else None]
            out[dy, dx] = float((a * b).mean()) / v
    return out


def tile_bias(rho: np.ndarray, n: int = TILE) -> float:
    """E[sample var] / sigma^2 for an n x n tile with this correlation."""
    tot = 0.0
    for dy in range(-(n - 1), n):
        for dx in range(-(n - 1), n):
            r = rho[abs(dy), abs(dx)] if (abs(dy) < rho.shape[0]
                                          and abs(dx) < rho.shape[1]) else 0.0
            tot += (n - abs(dy)) * (n - abs(dx)) * r
    nn = n * n
    return (nn / (nn - 1.0)) * (1.0 - tot / (nn * nn))


def smooth_block(p: np.ndarray, d: np.ndarray, size: int = 512):
    """Pick the block of `size` where the pair-mean is flattest."""
    h, w = d.shape
    best, bb = None, None
    for y in range(0, h - size, size):
        for x in range(0, w - size, size):
            sub = p[y:y + size, x:x + size].astype(np.float64)
            lap = float(np.abs(np.diff(sub, axis=1)).mean()
                        + np.abs(np.diff(sub, axis=0)).mean())
            if best is None or lap < best:
                best, bb = lap, (y, x)
    y, x = bb
    return d[y:y + size, x:x + size], best


def main() -> int:
    L = load_ladder()
    say("M61 script 05 -- per-plane spatial autocorrelation of the temporal")
    say("difference (POST HOC; testing whether the B deficit is mine)")
    say()
    grand = {p: [] for p in PLANES}
    for name, iso in (("109MSDCF", 160), ("112MSDCF", 500), ("foam", 1000),
                      ("bee-3", 100)):
        fs = sorted(glob.glob(os.path.join(CORPUS, name, "*.ARW")))
        say(f"--- {name}  ISO {iso}  ({len(fs)} frames) ---")
        say(f"  {'plane':<6} {'level DN':>9} {'sd(d)':>8} {'rho(0,1)':>9} "
            f"{'rho(1,0)':>9} {'rho(1,1)':>9} {'rho(0,2)':>9} "
            f"{'tile bias':>10} {'corr x':>8}")
        acc = {}
        for k in (0, len(fs) // 2):
            if k + 1 >= len(fs):
                continue
            a = L.read_raw(fs[k])
            b = L.read_raw(fs[k + 1])
            for p in PLANES:
                pa = L.plane_of(a, p).astype(np.float64)
                pb = L.plane_of(b, p).astype(np.float64)
                d = pa - pb
                s = 0.5 * (pa + pb) - L.BLACK
                blk, flat = smooth_block(s, d)
                acc.setdefault(p, []).append(
                    (float(s.mean()), float(blk.std(ddof=1)),
                     autocorr(blk, LAG)))
            del a, b
        for p in PLANES:
            lvl = np.mean([t[0] for t in acc[p]])
            sd = np.mean([t[1] for t in acc[p]])
            rho = np.mean([t[2] for t in acc[p]], axis=0)
            bias = tile_bias(rho)
            grand[p].append(bias)
            say(f"  {p:<6} {lvl:>9.1f} {sd:>8.3f} {rho[0, 1]:>9.4f} "
                f"{rho[1, 0]:>9.4f} {rho[1, 1]:>9.4f} {rho[0, 2]:>9.4f} "
                f"{bias:>10.4f} {1 / bias:>8.4f}")
        say()
    say("=" * 70)
    say("tile-variance bias factor averaged over the four stacks")
    say(f"  {'plane':<6} {'bias':>8} {'implied correction to slope':>30}")
    gb = np.mean(grand["G1"] + grand["G2"])
    for p in PLANES:
        b = float(np.mean(grand[p]))
        say(f"  {p:<6} {b:>8.4f} {gb / b:>30.4f}")
    say()
    say("  Measured B/green PTC slope ratio (script 02): 0.83.")
    say(f"  Correlation would have to supply a factor of "
        f"{gb / float(np.mean(grand['B'])):.4f} to explain it.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
