"""V-DILUTE metrics.

Rule 3 of the brief: never a sharpness number without a noise number on the same
pixels, with band, subject and frame count named. So every row this module emits
carries detail AND noise, measured on tile sets that are chosen ONCE from a fixed
reference render and reused byte-for-byte across every arm.

Rule 5: comparisons are on decoded arrays, never file digests.

Magnification correction. `strehl` aligns by default and shrinks the field of view
so every frame covers every output pixel, then upsamples back to fixed output
dimensions. The shrink depends on the frame set, so two arms built from different
frames can differ in MAGNIFICATION even though the TIFFs are the same size. A
feature at sensor frequency f lands at f*s in an arm whose log reports
"field of view scaled to s". To compare at matched SENSOR bandwidth, each arm's
band edges are multiplied by its own s.
"""

import os
import re
import numpy as np
import tifffile

TILE = 128
UNREACHED = 65535


def read_rgb(path):
    a = tifffile.imread(path)
    assert a.ndim == 3 and a.shape[2] == 3, f"{path}: expected HxWx3, got {a.shape}"
    return a


def green(path):
    return read_rgb(path)[:, :, 1].astype(np.float64)


def fov_scale(logpath, fallback=None):
    """The alignment FOV scale s for this arm, from its own run log.

    The scale is a property of the FRAME SET (it is whatever makes every frame
    cover every output pixel), not of the merge flags, so arms sharing a stack
    share a scale. `fallback` supplies a directly observed value for arms
    rendered before the queue existed and therefore having no log.
    """
    if not os.path.exists(logpath):
        if fallback is None:
            raise FileNotFoundError(logpath)
        return fallback
    txt = open(logpath, "r", errors="replace").read()
    m = re.search(r"field of view scaled to ([0-9.]+)", txt)
    return float(m.group(1)) if m else 1.0


def averaged_row(logpath):
    txt = open(logpath, "r", errors="replace").read()
    m = re.search(r"^averaged\s*:(.*)$", txt, re.M)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------- tiles

def tile_grid(shape, tile=TILE):
    h, w = shape
    ys = range(0, h - tile + 1, tile)
    xs = range(0, w - tile + 1, tile)
    return [(y, x) for y in ys for x in xs]


def select_tiles(ref, n_each=120, tile=TILE):
    """Textured and flat tile coordinates, chosen ONCE from a fixed reference.

    Textured = highest gradient energy, flat = lowest. Returned as coordinate
    lists so that every arm is measured on identical pixels.
    """
    gy, gx = np.gradient(ref)
    g = gy * gy + gx * gx
    coords = tile_grid(ref.shape, tile)
    energy = np.array([g[y:y + tile, x:x + tile].mean() for (y, x) in coords])
    order = np.argsort(energy)
    flat = [coords[i] for i in order[:n_each]]
    textured = [coords[i] for i in order[-n_each:]]
    return textured, flat


# ---------------------------------------------------------------- spectra

_WIN = np.hanning(TILE)[:, None] * np.hanning(TILE)[None, :]
_FY = np.fft.fftfreq(TILE)[:, None]
_FX = np.fft.fftfreq(TILE)[None, :]
_R = np.sqrt(_FY ** 2 + _FX ** 2)


def tile_spectrum(t):
    t = t.astype(np.float64)
    t = t - t.mean()
    F = np.fft.fft2(t * _WIN)
    return (np.abs(F) ** 2) / (_WIN ** 2).sum()


def band_power(img, coords, f1, f2, tile=TILE):
    """Mean spectral power in [f1,f2) cyc/px over the given tiles."""
    m = (_R >= f1) & (_R < f2)
    vals = []
    for (y, x) in coords:
        P = tile_spectrum(img[y:y + tile, x:x + tile])
        vals.append(P[m].mean())
    return float(np.mean(vals))


def measure(img, textured, flat, s=1.0):
    """Detail and noise for one arm, at matched SENSOR bandwidth (band edges
    scaled by this arm's own FOV scale s).

    `noise_hf_tex` is the PRIMARY noise number and is deliberately measured on
    the SAME tiles as the detail number, which is what rule 3 asks for. The
    flat-tile number is kept only as a secondary diagnostic, because flat tiles
    turn out to be exactly where NO frame clears the noise gate, so the merge
    falls back to an unweighted mean there under EVERY select mode and the
    statistic is structurally unable to separate the arms. Measured: at N=22
    hard-max and the default read 8404.5 vs 8442.8 on flat tiles, a ratio of
    1.005, while differing plainly elsewhere.
    """
    return {
        "detail_20_25": band_power(img, textured, 0.20 * s, 0.25 * s),
        "detail_30_35": band_power(img, textured, 0.30 * s, 0.35 * s),
        "noise_hf_tex": band_power(img, textured, 0.40 * s, 0.50 * s),
        "noise_40_50": band_power(img, flat, 0.40 * s, 0.50 * s),
        "fov_scale": s,
    }


# ---------------------------------------------------------------- confidence

def confidence_stats(path, thresholds=(800, 900)):
    a = tifffile.imread(path)
    a = a.reshape(-1)
    reached = a[a != UNREACHED].astype(np.float64)
    out = {
        "n": int(reached.size),
        "unreached": int((a == UNREACHED).sum()),
        "mean": float(reached.mean()),
        "p10": float(np.percentile(reached, 10)),
        "p50": float(np.percentile(reached, 50)),
        "p90": float(np.percentile(reached, 90)),
    }
    for t in thresholds:
        out[f"frac_ge_{t}"] = float((reached >= t).mean())
    return out


def confidence_mean_masked(path, mask):
    a = tifffile.imread(path)
    v = a[mask & (a != UNREACHED)].astype(np.float64)
    return float(v.mean()), int(v.size)


def null_confidence(n):
    """Analytic reading of a merge that averages IDENTICALLY at every depth.

    below/seen -> Binomial(n,1/2)/n, so E[v] = 1 - E|2(B/n - 1/2)|. This RISES
    with n purely from rank sampling noise, which is the direction the dilution
    hypothesis also predicts -- hence the bracketing arms.
    """
    from math import comb
    k = np.arange(n + 1)
    logp = (np.array([np.log(float(comb(n, int(i)))) for i in k]) - n * np.log(2.0))
    p = np.exp(logp)
    v = 1.0 - 2.0 * np.abs(k / n - 0.5)
    return float((p * v).sum() * 1000.0)
