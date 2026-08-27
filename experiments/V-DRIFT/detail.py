#!/usr/bin/env python3
"""Detail retention across the dose ladder, measured with BUILD-TRIAGE's instrument.

The instrument is IMPORTED, not reimplemented.  `tri.spectrum` / `tri.band_amp`
already carry the two corrections this comparison needs and that a fresh
implementation would silently omit:

  * bands are defined in SENSOR frequency and evaluated at `f*k` in each arm's
    own output grid, because a merge crops the field of view to `k` and
    upsamples back, so "0.35 cycles per output sample" is a DIFFERENT PHYSICAL
    FREQUENCY in every render.  The arms here have different `k` -- a stack
    planted with 20 px of displacement must be cropped harder than the shipped
    one -- so comparing at equal OUTPUT frequency would hand the more heavily
    planted arm an easier question, i.e. would flatter the damage.
  * the metric is the magnitude of a windowed Fourier transform, which is
    shift-invariant, so residual sub-pixel misplacement of the tile itself
    cannot move the answer.

SITE SELECTION IS DELIBERATELY NOT THE MEASURED BAND.  Sites are chosen on the
BASELINE arm's MID band (0.15-0.25 c/s) and the verdict is read in the HIGH
band (0.30-0.45 c/s).  Choosing sites on the same band that is then reported
would regress toward the selecting arm and manufacture an advantage for it.

PARTNER WINDOWS ARE LOCATED, NOT ASSUMED.  Arms differ in `k` by up to ~1%,
which is ~18 px at the frame edge, so equal coordinates do not show equal
content.  Each arm's window is found by normalised cross-correlation against
the baseline tile before anything is measured.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "BUILD-TRIAGE"))
import tri  # noqa: E402

ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
TILE = 256
SEARCH = 64


def ncc_offset(ref: np.ndarray, hay: np.ndarray) -> tuple[int, int, float]:
    """Locate `ref` inside `hay` by normalised cross-correlation.

    Brute force over the offset grid via FFT correlation of the mean-removed
    template, then normalised by the local energy of the haystack so a bright
    region cannot win on level alone.
    """
    n = ref.shape[0]
    r = ref - ref.mean()
    H, W = hay.shape
    fh = np.fft.rfft2(hay, s=(H, W))
    fr = np.fft.rfft2(r[::-1, ::-1], s=(H, W))
    num = np.fft.irfft2(fh * fr, s=(H, W))[n - 1:, n - 1:]

    ones = np.ones((n, n))
    fo = np.fft.rfft2(ones[::-1, ::-1], s=(H, W))
    s1 = np.fft.irfft2(np.fft.rfft2(hay, s=(H, W)) * fo, s=(H, W))[n - 1:, n - 1:]
    s2 = np.fft.irfft2(np.fft.rfft2(hay * hay, s=(H, W)) * fo, s=(H, W))[n - 1:, n - 1:]
    var = np.maximum(s2 - s1 * s1 / (n * n), 1e-6)
    score = num / np.sqrt(var * (r * r).sum() + 1e-12)

    dy, dx = np.unravel_index(np.argmax(score), score.shape)
    return int(dy), int(dx), float(score[dy, dx])


def pick_sites(base: np.ndarray, k: float, n_sites: int, tile: int) -> list[tuple[int, int]]:
    """Detail-rich, non-overlapping sites, chosen on the MID band."""
    H, W = base.shape
    m = SEARCH + 8
    step = tile // 2
    cand = []
    for y in range(m, H - tile - m, step):
        for x in range(m, W - tile - m, step):
            t = base[y:y + tile, x:x + tile]
            cand.append((tri.band_amp(t, k)["mid"], y, x))
    cand.sort(reverse=True)
    taken: list[tuple[int, int]] = []
    for _, y, x in cand:
        if all(abs(y - a) >= tile or abs(x - b) >= tile for a, b in taken):
            taken.append((y, x))
        if len(taken) == n_sites:
            break
    return taken


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*", default=["d0", "walk20", "iid20", "iid2", "walk60"])
    ap.add_argument("--baseline", default="d0")
    ap.add_argument("--sites", type=int, default=24)
    ap.add_argument("--tile", type=int, default=TILE)
    ap.add_argument("--out", default=str(ROOT / "detail-bee3.json"))
    ap.add_argument("--ksfile", default=str(ROOT / "dose-bee3.jsonl"),
                    help="jsonl carrying each arm's coverage crop factor k")
    a = ap.parse_args()

    ks = {}
    for line in Path(a.ksfile).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        ks[r["arm"]] = r
    ks.setdefault("d0", {"k": 0.9321, "shape": "none", "amp_px": 0.0,
                         "abs_max_px": 0.0, "local_rel_px": {}})

    imgs = {}
    for arm in a.arms:
        p = ROOT / "merge" / f"{arm}.tif"
        if not p.exists():
            print(f"  (skip {arm}: no merge)")
            continue
        imgs[arm] = tri.luma(tri.load16(str(p)))
        print(f"  {arm:8s} {imgs[arm].shape[1]}x{imgs[arm].shape[0]}  "
              f"k={ks[arm]['k']}  mean={imgs[arm].mean():.1f} DN")

    base_arm = a.baseline
    base = imgs[base_arm]
    sites = pick_sites(base, ks[base_arm]["k"], a.sites, a.tile)
    print(f"\n{len(sites)} sites, {a.tile}px tiles, chosen on {base_arm} mid band\n")

    res: dict[str, dict] = {}
    for arm, img in imgs.items():
        highs, mids, slopes = [], [], []
        for (y, x) in sites:
            ref = base[y:y + a.tile, x:x + a.tile]
            if arm == base_arm:
                t = ref
            else:
                m = SEARCH
                hay = img[y - m:y + a.tile + m, x - m:x + a.tile + m]
                dy, dx, _ = ncc_offset(ref, hay)
                t = img[y - m + dy:y - m + dy + a.tile, x - m + dx:x - m + dx + a.tile]
            ba = tri.band_amp(t, ks[arm]["k"])
            highs.append(ba["high"])
            mids.append(ba["mid"])
            slopes.append(tri.edge_slope(t))
        res[arm] = {
            "high": highs, "mid": mids, "slope": slopes,
            "k": ks[arm]["k"], "shape": ks[arm]["shape"],
            "abs_max_px": ks[arm]["abs_max_px"],
            "sep1": ks[arm]["local_rel_px"].get("1", ks[arm]["local_rel_px"].get(1, 0.0)),
        }

    b = res[base_arm]
    print(f"{'arm':9s} {'shape':6s} {'abs':>7s} {'sep1':>7s} {'k':>7s} "
          f"{'high':>9s} {'vs d0':>8s} {'mid':>9s} {'vs d0':>8s} {'slope':>8s} {'vs d0':>8s}")
    print("-" * 100)
    for arm in a.arms:
        if arm not in res:
            continue
        r = res[arm]
        rh = float(np.median([x / y for x, y in zip(r["high"], b["high"])]))
        rm = float(np.median([x / y for x, y in zip(r["mid"], b["mid"])]))
        rs = float(np.median([x / y for x, y in zip(r["slope"], b["slope"])]))
        r["ratio_high"], r["ratio_mid"], r["ratio_slope"] = rh, rm, rs
        print(f"{arm:9s} {r['shape']:6s} {r['abs_max_px']:7.2f} {r['sep1']:7.3f} "
              f"{r['k']:7.4f} {np.median(r['high']):9.1f} {rh:8.4f} "
              f"{np.median(r['mid']):9.1f} {rm:8.4f} "
              f"{np.median(r['slope']):8.2f} {rs:8.4f}")

    Path(a.out).write_text(json.dumps(
        {"sites": sites, "tile": a.tile, "baseline": base_arm, "arms": res},
        indent=1), encoding="utf-8")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
