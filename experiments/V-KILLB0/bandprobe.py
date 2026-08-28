"""V-KILLB0 band instrument.  Written from scratch; shares no code with
experiments/ORCH-drift-check/contrast_ms.py.

DESIGN DIFFERENCES, EACH ONE AIMED AT A SPECIFIC WAY contrast_ms.py COULD BE
WRONG:

1. DECOMPOSITION.  contrast_ms.py uses differences of Gaussians at sigma
   0.6366/0.9362/...  A Gaussian difference is a broad, heavily overlapping
   filter: the "0.25-0.5" band and the "0.17-0.25" band share most of their
   support, so energy moved at 0.35 cyc/px leaks into the band being used as
   the acuity criterion and vice versa.  This uses a WINDOWED PERIODOGRAM with
   HARD radial frequency bins.  Bins do not overlap.  Leakage is bounded by the
   Hann window sidelobes (-31 dB first sidelobe, -18 dB/octave rolloff).

2. RESOLUTION INSIDE THE DISPUTED BANDS.  0.25-0.50 is reported in three
   sub-bins and 0.17-0.25 in two, so "the loss is at 0.45" and "the loss is at
   0.26" are distinguishable.  contrast_ms.py cannot tell those apart.

3. NO MEDIAN NORMALISATION.  contrast_ms.py multiplies B by median(A)/median(B)
   before measuring, which converts a real level change into a global gain on
   every band.  Here each tile is mean-removed and windowed, so DC cannot enter,
   and the level change is reported SEPARATELY as a number rather than divided
   out of the thing being measured.

4. PER CHANNEL.  This is a CFA-native pipeline whose selection runs on green
   luma.  A green-only or chroma-only effect is invisible to a single
   0.2126/0.7152/0.0722 projection.  R, G, B and luma are all reported.

5. SITES.  contrast_ms.py takes the 12 lowest- and 12 highest-gradient tiles of
   arm A.  Here the FULL tile census is also reported (every tile, no
   selection), so a site-selection bias cannot hide anything: if the census and
   the selected sites disagree, the selection is the finding.

6. CLIP / BLACK / MEDIAN per site set, because a saturated tile has no
   structure and a difference metric reads "clean" there (fact 1817).
"""
import json
import os
import sys

import numpy as np
import tifffile

TILE = 256

# Hard radial bins in cyc/px.  The three inside 0.25-0.50 and the two inside
# 0.17-0.25 are what let this instrument answer questions contrast_ms.py's two
# broad bands cannot.
BINS = [
    (0.40, 0.50),
    (0.30, 0.40),
    (0.25, 0.30),
    (0.20, 0.25),
    (0.17, 0.20),
    (0.10, 0.17),
    (0.05, 0.10),
    (0.02, 0.05),
]


def load(path):
    a = tifffile.imread(path)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    return a[:, :, :3]


def channels(a):
    f = a.astype(np.float64)
    lum = f @ np.array([0.2126, 0.7152, 0.0722])
    return {"R": f[:, :, 0], "G": f[:, :, 1], "B": f[:, :, 2], "L": lum}


_WIN = None
_MASKS = None


def _win():
    global _WIN
    if _WIN is None:
        w = np.hanning(TILE + 1)[:TILE]
        _WIN = np.outer(w, w)
    return _WIN


def _masks():
    """Hard annular masks on the rfft2 grid, plus each bin's cell count."""
    global _MASKS
    if _MASKS is None:
        fy = np.fft.fftfreq(TILE)[:, None]
        fx = np.fft.rfftfreq(TILE)[None, :]
        r = np.hypot(fy, fx)
        _MASKS = [((r >= lo) & (r < hi)) for lo, hi in BINS]
    return _MASKS


def tile_bands(t):
    """Mean power spectral density per radial bin for one TILExTILE tile.

    Mean removed then Hann windowed, so DC and the tile's own level cannot
    contribute.  Returned as an AMPLITUDE (sqrt of mean power) so the numbers
    are comparable to a standard deviation and the ratios are directly
    comparable to contrast_ms.py's std ratios.
    """
    t = t - t.mean()
    f = np.fft.rfft2(t * _win())
    p = (f.real ** 2 + f.imag ** 2)
    out = np.empty(len(BINS))
    for i, m in enumerate(_masks()):
        out[i] = np.sqrt(p[m].mean())
    return out


def grid(shape):
    h, w = shape
    return h // TILE, w // TILE


def gradient_field(lum):
    """Mid-scale gradient for site selection, deliberately NOT computed from
    the band under test."""
    from scipy.ndimage import gaussian_filter
    m = gaussian_filter(lum, 2.0)
    gy, gx = np.gradient(m)
    return np.hypot(gy, gx)


def tile_means(field, ny, nx):
    return field[: ny * TILE, : nx * TILE].reshape(ny, TILE, nx, TILE).mean(axis=(1, 3))


def census(pathA, pathB, nsites=12, chans=("L", "G")):
    A, B = load(pathA), load(pathB)
    assert A.shape == B.shape, f"shape mismatch {A.shape} {B.shape}"
    ca, cb = channels(A), channels(B)
    ny, nx = grid(A.shape[:2])

    g = gradient_field(ca["L"])
    tg = tile_means(g, ny, nx)
    order = np.argsort(tg.ravel())

    top = 65535
    clipA = (A.max(axis=2) >= top).astype(np.float64)
    blackA = (A.min(axis=2) <= 0).astype(np.float64)
    tclip = tile_means(clipA, ny, nx) * 100.0
    tblack = tile_means(blackA, ny, nx) * 100.0
    tmedL = tile_means(ca["L"], ny, nx)

    sites = {
        "FLAT": order[:nsites],
        "EDGE": order[-nsites:],
        "ALL": np.arange(ny * nx),
    }

    res = {
        "A": pathA, "B": pathB, "shape": list(A.shape), "tiles": [ny, nx],
        "bins": BINS,
        "medianA": float(np.median(ca["L"])), "medianB": float(np.median(cb["L"])),
        "meanA": float(ca["L"].mean()), "meanB": float(cb["L"].mean()),
        "clip_pct_A": float(clipA.mean() * 100), "black_pct_A": float(blackA.mean() * 100),
        "clip_pct_B": float((B.max(axis=2) >= top).mean() * 100),
        "black_pct_B": float((B.min(axis=2) <= 0).mean() * 100),
        "sites": {},
    }

    for sname, idx in sites.items():
        entry = {
            "n": int(len(idx)),
            "clip_pct": float(np.mean([tclip.ravel()[i] for i in idx])),
            "black_pct": float(np.mean([tblack.ravel()[i] for i in idx])),
            "levelA": float(np.mean([tmedL.ravel()[i] for i in idx])),
            "chan": {},
        }
        for ch in chans:
            fa, fb = ca[ch], cb[ch]
            accA = np.zeros(len(BINS))
            accB = np.zeros(len(BINS))
            for f in idx:
                ty, tx = divmod(int(f), nx)
                y, x = ty * TILE, tx * TILE
                accA += tile_bands(fa[y:y + TILE, x:x + TILE])
                accB += tile_bands(fb[y:y + TILE, x:x + TILE])
            accA /= len(idx)
            accB /= len(idx)
            entry["chan"][ch] = {
                "A": accA.tolist(), "B": accB.tolist(),
                "ratio": (accB / np.where(accA > 0, accA, np.nan)).tolist(),
            }
        # level change at these sites, in DN, on luma -- reported, not divided out
        lv = []
        for f in idx:
            ty, tx = divmod(int(f), nx)
            y, x = ty * TILE, tx * TILE
            lv.append(cb["L"][y:y + TILE, x:x + TILE].mean()
                      - ca["L"][y:y + TILE, x:x + TILE].mean())
        entry["dlevel_DN"] = float(np.mean(lv))
        res["sites"][sname] = entry
    return res


def fmt(res, title=""):
    out = []
    out.append(f"== {title}")
    out.append(f"   A={os.path.basename(res['A'])}  B={os.path.basename(res['B'])}  "
               f"{res['shape'][1]}x{res['shape'][0]}  tiles={res['tiles'][0]}x{res['tiles'][1]}")
    out.append(f"   whole-image  medianL A={res['medianA']:.0f} B={res['medianB']:.0f}   "
               f"clip% A={res['clip_pct_A']:.2f} B={res['clip_pct_B']:.2f}   "
               f"black% A={res['black_pct_A']:.2f} B={res['black_pct_B']:.2f}")
    for sname in ("FLAT", "EDGE", "ALL"):
        if sname not in res["sites"]:
            continue
        e = res["sites"][sname]
        out.append(f"   -- {sname} (n={e['n']}) clip%={e['clip_pct']:.2f} "
                   f"black%={e['black_pct']:.2f} levelA={e['levelA']:.0f} "
                   f"dlevel={e['dlevel_DN']:+.1f} DN")
        hdr = f"      {'cyc/px':>12s}"
        for ch in e["chan"]:
            hdr += f"  {ch+' A':>10s} {ch+' B':>10s} {'ratio':>7s}"
        out.append(hdr)
        for i, (lo, hi) in enumerate(res["bins"]):
            line = f"      {f'{lo:.2f}-{hi:.2f}':>12s}"
            for ch in e["chan"]:
                d = e["chan"][ch]
                line += f"  {d['A'][i]:10.2f} {d['B'][i]:10.2f} {d['ratio'][i]:7.4f}"
            out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    r = census(sys.argv[1], sys.argv[2])
    print(fmt(r, sys.argv[3] if len(sys.argv) > 3 else ""))
    if len(sys.argv) > 4:
        with open(sys.argv[4], "w") as fh:
            json.dump(r, fh, indent=1)
