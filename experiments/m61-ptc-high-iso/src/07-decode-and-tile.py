"""07 -- rule 32 cross-check: rawler (Rust) against rawpy (LibRaw), and the
B-plane deficit against tile size.

POST HOC.  Two independent things that both bear on whether M61's numbers are
properties of the sensor or properties of my tooling.

PART 1 -- SECOND DECODE.
  Every M61 number came out of `rawpy`, i.e. LibRaw.  `experiments/m61-ptc-
  high-iso/decode-check` decodes the same frames with `strehl-raw`, i.e.
  rawler -- a completely separate implementation of Sony's lossless
  compression, and the one the shipped binary actually uses.  This compares
  a 512x512 active-area patch pixel for pixel, and re-runs the M61 tile
  statistics on the rawler patch pair.

  IF the patches differ: every M61 number is suspect and the report says so.
  IF they match bit for bit: the decode is not the story.

PART 2 -- IS THE B-PLANE DEFICIT A TILE ARTEFACT?
  Script 02 measured slope_B / slope_green = 0.84 at every ISO from 50 to
  1000.  A tile SAMPLE variance under-reports when the noise is spatially
  correlated, and the under-reporting shrinks as the tile grows (the
  correction goes as the tile perimeter over its area).  So if correlation
  causes the deficit, B/green must move materially towards 1.0 between
  TILE=8 and TILE=32.  If it does not move, the deficit is in the data.

  Script 05 tried to answer this by measuring the autocorrelation of the
  frame difference directly and FAILED: on real frames the difference is
  dominated by scene change, not noise, so the measured rho was scene
  structure (foam gave rho ~ 0.8).  That failure is left in the record.
  This is the second attempt, and it uses the estimator's own texture
  rejection instead of trying to measure rho.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m61-ptc-high-iso/src/07-decode-and-tile.py
"""

from __future__ import annotations

import glob
import importlib.util
import os
import struct

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "decode-and-tile.txt")
CORPUS = r"D:\personal\macro"
PLANES = ("R", "G1", "G2", "B")
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


def load_bin(tag):
    with open(os.path.join(DATA, f"rawler-{tag}.bin"), "rb") as fh:
        y0, x0, h, w = struct.unpack("<4I", fh.read(16))
        a = np.frombuffer(fh.read(h * w * 2), dtype="<u2").reshape(h, w)
    return y0, x0, a.copy()


def sub_planes(patch, y0, x0):
    """Split a patch of the ACTIVE area into CFA planes by absolute parity."""
    out = {}
    for name, (dy, dx) in (("R", (0, 0)), ("G1", (0, 1)), ("G2", (1, 0)),
                           ("B", (1, 1))):
        ys = (dy - y0) % 2
        xs = (dx - x0) % 2
        out[name] = patch[ys::2, xs::2]
    return out


def main() -> int:
    L = load_ladder()
    say("M61 script 07 -- second decode (rawler vs rawpy) and the B-plane")
    say("deficit vs tile size (POST HOC)")
    say()
    say("=" * 78)
    say("PART 1 -- rawler (strehl-raw, the shipped decoder) vs rawpy (LibRaw)")
    say("=" * 78)
    pairs = [("109-a", "109MSDCF", 0), ("109-b", "109MSDCF", 1),
             ("112-a", "112MSDCF", 0), ("112-b", "112MSDCF", 1)]
    got = {}
    for tag, stack, idx in pairs:
        fs = sorted(glob.glob(os.path.join(CORPUS, stack, "*.ARW")))
        y0, x0, rl = load_bin(tag)
        rp_full = L.read_raw(fs[idx])
        rp = rp_full[y0:y0 + rl.shape[0], x0:x0 + rl.shape[1]]
        same = int(np.count_nonzero(rl == rp))
        n = rl.size
        d = rl.astype(np.int64) - rp.astype(np.int64)
        say(f"  {tag:<7} {os.path.basename(fs[idx]):<14} patch "
            f"{rl.shape[0]}x{rl.shape[1]} at ({y0},{x0})  identical "
            f"{same}/{n} = {100 * same / n:.4f}%   max|diff| "
            f"{int(np.abs(d).max())}   rawpy shape "
            f"{rp_full.shape[0]}x{rp_full.shape[1]}")
        got[tag] = (y0, x0, rl, rp)
    say()
    say("  the two decoders' geometry: rawler reports the active area as")
    say("  7032x4688, rawpy's raw_image_visible gives 7028x4688 -- rawpy is")
    say("  4 columns narrower. M61 used rawpy throughout, so it measured a")
    say("  strict subset of the active area.")
    say()
    say("  same tile statistics computed on each decoder's patch pair:")
    say(f"  {'plane':<6} {'decoder':<8} {'mean-blk':>9} {'var(d)/2':>10} "
        f"{'ntiles':>7}")
    for stack, ta, tb in (("109MSDCF", "109-a", "109-b"),
                          ("112MSDCF", "112-a", "112-b")):
        y0, x0, rla, rpa = got[ta]
        _, _, rlb, rpb = got[tb]
        for p in PLANES:
            row = []
            for dec, A, B in (("rawler", rla, rlb), ("rawpy", rpa, rpb)):
                pa = sub_planes(A, y0, x0)[p]
                pb = sub_planes(B, y0, x0)[p]
                m, v, u, ok = L.tile_stats(pa, pb)
                row.append((float(m[ok].mean()), float(v[ok].mean()),
                            int(ok.sum())))
            say(f"  {p:<6} {'rawler':<8} {row[0][0]:>9.2f} "
                f"{row[0][1]:>10.4f} {row[0][2]:>7d}   [{stack}]")
            say(f"  {p:<6} {'rawpy':<8} {row[1][0]:>9.2f} "
                f"{row[1][1]:>10.4f} {row[1][2]:>7d}")
    say()

    say("=" * 78)
    say("PART 2 -- B/green PTC slope ratio vs tile size")
    say("=" * 78)
    say("  if short-range noise correlation caused the deficit, the ratio")
    say("  must climb towards 1.0 as the tile grows.")
    say(f"  {'stack':<12} {'ISO':>5} {'tile':>5} " +
        " ".join(f"{p:>9}" for p in PLANES) + f" {'B/green':>9} "
        f"{'R/green':>9}")
    for name, iso in (("109MSDCF", 160.0), ("112MSDCF", 500.0),
                      ("bee-3", 100.0), ("foam", 1000.0)):
        fs = sorted(glob.glob(os.path.join(CORPUS, name, "*.ARW")))
        starts = np.unique(np.linspace(0, len(fs) - 2,
                                       min(8, len(fs) - 1)).astype(int))
        frames = {}
        for k in starts:
            frames[k] = L.read_raw(fs[k])
            frames[k + 1] = L.read_raw(fs[k + 1])
        for tile in (8, 16, 32):
            old = L.TILE
            L.TILE = tile
            try:
                gs = {}
                for p in PLANES:
                    ms, vs, us = [], [], []
                    for k in starts:
                        pa = L.plane_of(frames[k], p)
                        pb = L.plane_of(frames[k + 1], p)
                        ma = float(pa.mean()) - L.BLACK
                        mb = float(pb.mean()) - L.BLACK
                        if ma <= 0 or mb <= 0 or abs(ma / mb - 1) > \
                                L.PAIR_LEVEL_TOL:
                            continue
                        m, v, u, ok = L.tile_stats(pa, pb)
                        ms.append(m[ok])
                        vs.append(v[ok])
                        us.append(u[ok])
                    m = np.concatenate(ms)
                    v = np.concatenate(vs)
                    u = np.concatenate(us)
                    est = L.bin_estimates(m, v, u,
                                          float(np.percentile(m, 1.0)),
                                          float(np.percentile(m, 99.5)))
                    gs[p] = L.fit_ptc([(e[0], e[1], e[2]) for e in est])[0]
            finally:
                L.TILE = old
            gm = 0.5 * (gs["G1"] + gs["G2"])
            say(f"  {name:<12} {iso:>5.0f} {tile:>5d} " +
                " ".join(f"{gs[p]:>9.5f}" for p in PLANES) +
                f" {gs['B'] / gm:>9.4f} {gs['R'] / gm:>9.4f}")
        del frames
    say()
    os.makedirs(DATA, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
