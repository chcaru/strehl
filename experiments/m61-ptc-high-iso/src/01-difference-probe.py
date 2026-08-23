"""01 -- exploratory: what does an adjacent-frame temporal difference look like?

Not a measurement.  This probe exists to answer three design questions BEFORE
the estimator in `02-*.py` is pre-registered:

  1. Are the new `bee-*` / `wrapped-text-*` stacks focus sweeps (frames differ
     a lot) or near-static bursts (frames differ only by noise)?  A near-static
     burst across the ISO-400 dual-gain switch at a matched DN level would be
     the strongest differential available in the corpus.
  2. Does ISO / exposure vary WITHIN a stack (auto-ISO)?  If it does, a stack
     cannot be treated as one ISO.
  3. How large is the residual scene-change term in a first temporal difference
     compared with the shot noise the model predicts?  This sets whether a
     structure covariate is enough or whether a second difference is needed.

For (3) it prints, per stack, the ratio

    sqrt( var(F_k - F_k+1) / 2 )  /  model sigma

pooled over the whole plane and over the smoothest 10% of 8x8 tiles.  A ratio
near 1 on the smooth tiles means the scene term is controllable.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m61-ptc-high-iso/src/01-difference-probe.py
"""

from __future__ import annotations

import glob
import os
import time

import numpy as np

CORPUS = r"D:\personal\macro"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data",
                   "difference-probe.txt")
BLACK = 512.0
WHITE = 15360.0
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
RN_LOW = 4.20
RN_HIGH = 1.2392
TILE = 8
STACKS = ["109MSDCF", "112MSDCF", "113MSDCF", "119MSDCF", "coffee-bean",
          "coffee-bubbles", "foam", "bee-1", "bee-2", "bee-3",
          "wrapped-text-1", "wrapped-text-2"]
LINES: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LINES.append(s)


def model_sigma(iso: float, m_dn: np.ndarray) -> np.ndarray:
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW
    return np.sqrt(np.maximum(g * m_dn, 0.0) + (rn * g) ** 2)


def exif_all(paths: list[str]) -> list[tuple[str, str]]:
    import exifread

    out = []
    for p in paths:
        with open(p, "rb") as fh:
            t = exifread.process_file(fh, details=False)
        out.append((str(t.get("EXIF ISOSpeedRatings", "?")),
                    str(t.get("EXIF ExposureTime", "?"))))
    return out


def g1_of(path: str) -> np.ndarray:
    import rawpy

    with rawpy.imread(path) as rr:
        return np.asarray(rr.raw_image_visible[0::2, 1::2],
                          dtype=np.float32).copy()


def tiles(a: np.ndarray, fn) -> np.ndarray:
    h, w = a.shape
    h -= h % TILE
    w -= w % TILE
    b = a[:h, :w].reshape(h // TILE, TILE, w // TILE, TILE)
    return fn(b)


def main() -> int:
    t0 = time.time()
    say("M61 difference probe -- exploratory, no measurement here")
    say()
    for name in STACKS:
        d = os.path.join(CORPUS, name)
        fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
        if not fs:
            say(f"!! {name}: no frames")
            continue
        sample = [fs[0], fs[len(fs) // 2], fs[-1]]
        ex = exif_all(sample)
        isos = {e[0] for e in ex}
        exps = {e[1] for e in ex}
        iso = float(ex[0][0])
        say(f"=== {name:<16} n={len(fs):>4}  ISO(first/mid/last) {sorted(isos)}"
            f"  exp {sorted(exps)}")

        k = len(fs) // 2
        a = g1_of(fs[k]) - BLACK
        b = g1_of(fs[k + 1]) - BLACK
        ok = (a + BLACK < WHITE) & (b + BLACK < WHITE)
        dd = (a - b)
        ss = 0.5 * (a + b)
        v_all = float(np.var(dd[ok], ddof=1) / 2.0)
        m_all = float(np.mean(ss[ok]))
        pred_all = float(model_sigma(iso, np.array([m_all]))[0])
        say(f"    whole-plane: mean {m_all:>8.1f} DN   "
            f"sigma_diff/sqrt2 {np.sqrt(v_all):>8.2f} DN   "
            f"model {pred_all:>7.2f}   ratio {np.sqrt(v_all) / pred_all:>7.3f}")

        vt = tiles(dd, lambda z: z.var(axis=(1, 3), ddof=1) / 2.0).ravel()
        mt = tiles(ss, lambda z: z.mean(axis=(1, 3))).ravel()
        ut = tiles(ss, lambda z: z.var(axis=(1, 3), ddof=1)).ravel()
        okt = tiles(ok.astype(np.float32),
                    lambda z: z.mean(axis=(1, 3))).ravel() > 0.999
        vt, mt, ut = vt[okt], mt[okt], ut[okt]
        thr = np.percentile(ut, 10.0)
        sel = ut <= thr
        pred_t = model_sigma(iso, mt[sel])
        rat = np.sqrt(vt[sel]) / pred_t
        say(f"    smoothest 10% of {TILE}x{TILE} tiles (n={sel.sum()}): "
            f"mean level {mt[sel].mean():>8.1f} DN   "
            f"median ratio {np.median(rat):>6.3f}   "
            f"p10 {np.percentile(rat, 10):>6.3f} "
            f"p90 {np.percentile(rat, 90):>6.3f}")
        say(f"    all tiles (n={vt.size}): median ratio "
            f"{np.median(np.sqrt(vt) / model_sigma(iso, mt)):>6.3f}")
        say()
    say(f"[{time.time() - t0:.0f}s]")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
