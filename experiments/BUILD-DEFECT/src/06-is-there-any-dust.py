"""06-is-there-any-dust.py -- the deciding question, asked honestly.

05 measured that the high-pass's edge artefact reaches ~40 quads in and that
beyond it almost nothing survives the recurrence bar.  Two possibilities:

  A. this sensor is essentially clean in the interior, and every "mote" any of
     us has reported is an artefact of the operator's border; or
  B. the bars are set wrong and real dust is being thrown away.

Distinguish them WITHOUT a threshold, by looking at where the structure is:

  1. M71's committed dust mask (2,898 px, -3% cut, "enrichment 2278x, roll
     control PASS") -- how far from an edge does it sit?  If it is in the
     border band, M71 measured the operator and not the sensor, and its roll
     control could not have caught it because rolling moves the shelf.
  2. My own median residual -- what is the deepest interior structure, where,
     and how deep, with NO threshold applied?
  3. Render the interior alone, so it can be looked at rather than argued
     about.
"""

import json
import pathlib
import time

import numpy as np
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


def png(path, arr, lo, hi):
    """Write a grayscale PNG without PIL (AGENTS.md: PIL mis-reads our TIFFs;
    for PNG we simply do not depend on it)."""
    import struct
    import zlib
    a = np.clip((arr - lo) / (hi - lo), 0, 1)
    a = (a * 255).astype(np.uint8)
    h, w = a.shape
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    hdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", hdr)
                     + chunk(b"IDAT", zlib.compress(raw, 6))
                     + chunk(b"IEND", b""))


def main():
    med = np.load(OUT / "dust-median-residual.npy")
    band = np.load(OUT / "dust-band.npy")
    seen = np.load(OUT / "dust-seen.npy")
    h, w = med.shape
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    res = {}

    # ---- 1. where is M71's mask? -----------------------------------------
    m71 = REPO / "experiments" / "M71-flat-fields" / "out" / "cache" / "dust-mask.npy"
    log(f"M71 mask: {m71}  exists={m71.exists()}")
    if m71.exists():
        mask = np.load(m71)
        log(f"    shape {mask.shape} dtype {mask.dtype} sum {int(mask.sum())}")
        if mask.shape == (h, w):
            d = dist[mask.astype(bool)]
            pct = np.percentile(d, [0, 10, 25, 50, 75, 90, 100]).tolist()
            frac40 = float((d < 40).mean())
            frac90 = float((d < 90).mean())
            log(f"    distance-from-edge percentiles {[round(v) for v in pct]}")
            log(f"    fraction within 40 quads of an edge: {frac40*100:.2f}%")
            log(f"    fraction within 90 quads of an edge: {frac90*100:.2f}%")
            # what fraction of the PLANE is within 40?  the null expectation.
            null40 = float((dist < 40).mean())
            null90 = float((dist < 90).mean())
            log(f"    null (area fraction) within 40: {null40*100:.2f}%   "
                f"within 90: {null90*100:.2f}%")
            log(f"    ENRICHMENT toward the border: {frac40/null40:.1f}x (40)  "
                f"{frac90/null90:.1f}x (90)")
            res["m71"] = dict(n=int(mask.sum()), pct=pct, frac40=frac40,
                              frac90=frac90, null40=null40, null90=null90,
                              enrich40=frac40 / null40, enrich90=frac90 / null90)
        else:
            log(f"    shape mismatch against my {w}x{h}; not comparable")
            res["m71"] = dict(shape=list(mask.shape), comparable=False)

    # ---- 2. the deepest interior structure, no threshold ------------------
    log("deepest structure by distance band, NO threshold")
    rows = []
    for lo, hi in ((0, 40), (40, 90), (90, 200), (200, 500), (500, 10 ** 6)):
        m = (dist >= lo) & (dist < hi)
        rows.append(dict(lo=lo, hi=hi, n=int(m.sum()),
                         med_pct=float(np.median(med[m]) * 100),
                         p01_pct=float(np.percentile(med[m], 0.1) * 100),
                         min_pct=float(med[m].min() * 100),
                         band_min_pct=float(band[m].min() * 100),
                         band_p001_pct=float(np.percentile(band[m], 0.01) * 100)))
        r = rows[-1]
        log(f"    d in [{lo:4d},{hi:7d}) n={r['n']:8d}  median {r['med_pct']:+7.4f}%  "
            f"0.1pct {r['p01_pct']:+7.3f}%  min {r['min_pct']:+7.3f}%  |  "
            f"band min {r['band_min_pct']:+7.3f}%  band 0.01pct "
            f"{r['band_p001_pct']:+7.3f}%")
    res["by_distance"] = rows

    # ---- 3. the 20 deepest INTERIOR band-passed spots, with their shape ----
    b = 60
    interior = dist >= b
    log(f"the 20 deepest interior (d>={b}) band-passed spots")
    bi = np.where(interior, band, 0.0)
    spots = []
    tmp = bi.copy()
    for k in range(20):
        i = int(np.argmin(tmp))
        y, x = divmod(i, w)
        v = float(tmp[y, x])
        if v > -0.002:
            break
        # local extent at half depth
        y0, y1 = max(0, y - 60), min(h, y + 61)
        x0, x1 = max(0, x - 60), min(w, x + 61)
        patch = band[y0:y1, x0:x1]
        blob = patch <= v / 2
        lab, _ = ndimage.label(blob)
        area = int((lab == lab[y - y0, x - x0]).sum())
        spots.append(dict(x=x, y=y, band_pct=v * 100,
                          med_pct=float(med[y, x] * 100),
                          seen=int(seen[y, x]), area_halfdepth=area,
                          edge_dist=int(dist[y, x])))
        log(f"    #{k:2d} ({x:5d},{y:5d}) edge {dist[y,x]:4d}  band {v*100:+6.3f}%  "
            f"med {med[y,x]*100:+6.3f}%  seen {seen[y,x]:2d}/18  "
            f"half-depth area {area:5d}")
        tmp[max(0, y - 40):y + 41, max(0, x - 40):x + 41] = 0.0
    res["deepest_interior"] = spots

    # ---- 4. look at it ----------------------------------------------------
    inner = band[b:h - b, b:w - b]
    png(OUT / "interior-band.png", inner[::2, ::2], -0.010, 0.004)
    png(OUT / "interior-med.png", med[b:h - b, b:w - b][::2, ::2], -0.015, 0.006)
    png(OUT / "whole-band.png", band[::2, ::2], -0.010, 0.004)
    log("wrote interior-band.png, interior-med.png, whole-band.png "
        f"(interior {inner.shape[1]//2} x {inner.shape[0]//2})")

    (DATA / "06-dust-reality.json").write_text(json.dumps(res, indent=1),
                                               encoding="utf-8")
    log("wrote data/06-dust-reality.json")


if __name__ == "__main__":
    main()
