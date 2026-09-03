"""Independent implementation of the V-HEADTOHEAD3 estimator.

Deliberate independence from ordinal.py:
* mid-ranks use numpy.unique rather than scipy.stats.rankdata;
* registration uses skimage.registration.phase_cross_correlation;
* geometry resampling uses skimage.transform.resize;
* spectra use a correctly weighted real FFT rather than a full complex FFT;
* bootstrap seed differs.

It prints its own answer and carries no author result to compare against.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np
import tifffile
from skimage.filters import gaussian
from skimage.registration import phase_cross_correlation
from skimage.transform import resize


BANDS = (
    (0.02, 0.05),
    (0.05, 0.10),
    (0.10, 0.20),
    (0.20, 0.25),
    (0.25, 0.30),
    (0.30, 0.40),
)
BAND_NAMES = tuple(f"{a:.2f}-{b:.2f}" for a, b in BANDS)
PATHS = {
    "113": (
        Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff"),
        Path(r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"),
        "Zerene Stacker PMax",
    ),
    "cb": (
        Path(r"C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff"),
        Path(r"C:\dev\macro\out\coffee-bean\stack.tif"),
        "focus-stack fork",
    ),
}


def ranks(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a)
    values, inverse, counts = np.unique(
        x.ravel(), return_inverse=True, return_counts=True
    )
    del values
    ends = np.cumsum(counts, dtype=np.int64)
    starts = ends - counts
    average_one_based = (starts + 1 + ends) / 2.0
    n = x.size
    return ((average_one_based[inverse] - (n + 1) / 2.0) / n).reshape(x.shape)


def shares(a: np.ndarray, scale: float = 1.0) -> np.ndarray:
    q = ranks(a)
    q -= q.mean()
    q *= np.hanning(q.shape[0])[:, None] * np.hanning(q.shape[1])[None, :]
    power = np.abs(np.fft.rfft2(q)) ** 2
    if q.shape[1] % 2 == 0:
        power[:, 1:-1] *= 2.0
    else:
        power[:, 1:] *= 2.0
    fy = np.fft.fftfreq(q.shape[0])[:, None]
    fx = np.fft.rfftfreq(q.shape[1])[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    p = np.asarray(
        [
            np.sum(power[(radius >= lo * scale) & (radius < hi * scale)])
            for lo, hi in BANDS
        ],
        np.float64,
    )
    if not np.sum(p) > 0:
        raise ValueError("zero checker spectrum")
    return p / np.sum(p)


def correlation(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, np.float64).ravel()
    y = np.asarray(b, np.float64).ravel()
    x -= x.mean()
    y -= y.mean()
    den = math.sqrt(float(x @ x) * float(y @ y))
    return float((x @ y) / den) if den else float("nan")


def overlap(
    reference: np.ndarray, moving: np.ndarray, shift: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    dy, dx = shift
    h, w = reference.shape
    return (
        reference[max(0, dy) : min(h, h + dy), max(0, dx) : min(w, w + dx)],
        moving[
            max(0, -dy) : min(h, h - dy), max(0, -dx) : min(w, w - dx)
        ],
    )


def correction(reference: np.ndarray, moving: np.ndarray) -> tuple[int, int]:
    shift, _, _ = phase_cross_correlation(
        reference,
        moving,
        upsample_factor=1,
        normalization="phase",
    )
    return int(round(float(shift[0]))), int(round(float(shift[1])))


def resized_rank(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    return resize(
        ranks(a),
        shape,
        order=1,
        mode="reflect",
        anti_aliasing=False,
        preserve_range=True,
    )


def sampled(path: Path, step: int = 8) -> np.ndarray:
    a = tifffile.memmap(path)
    return ranks(np.asarray(a[::step, ::step, 1]))


def scale_score(s: np.ndarray, c: np.ndarray, scale: float) -> tuple[float, np.ndarray]:
    shape = (int(round(c.shape[0] * scale)), int(round(c.shape[1] * scale)))
    moved = resize(
        c,
        shape,
        order=1,
        mode="reflect",
        anti_aliasing=False,
        preserve_range=True,
    )
    tile = 128
    high_y = min(s.shape[0], moved.shape[0]) - tile
    high_x = min(s.shape[1], moved.shape[1]) - tile
    ys = np.linspace(tile // 2, high_y - tile // 2, 6).astype(int)
    xs = np.linspace(tile // 2, high_x - tile // 2, 6).astype(int)
    rows = []
    for y in ys:
        for x in xs:
            a = s[y : y + tile, x : x + tile]
            b = moved[y : y + tile, x : x + tile]
            dy, dx = correction(a, b)
            if abs(dy) > tile // 4 or abs(dx) > tile // 4:
                continue
            aa, bb = overlap(a, b, (dy, dx))
            rows.append((dy, dx, correlation(aa, bb)))
    if not rows:
        return float("-inf"), np.empty((0, 3))
    arr = np.asarray(rows, np.float64)
    return float(np.median(arr[:, 2])), arr


def geometry(sp: Path, cp: Path) -> dict:
    s = sampled(sp)
    c = sampled(cp)
    coarse = np.arange(0.96, 1.081, 0.005)
    scores = [scale_score(s, c, float(x))[0] for x in coarse]
    ci = int(np.argmax(scores))
    coarse_interior = 0 < ci < len(coarse) - 1
    fine = np.arange(float(coarse[ci]) - 0.006, float(coarse[ci]) + 0.0061, 0.001)
    values = [scale_score(s, c, float(x)) for x in fine]
    fi = int(np.argmax([x[0] for x in values]))
    scale = float(fine[fi])
    offsets = values[fi][1]
    global_shift = np.median(offsets[:, :2], axis=0) * 8
    return {
        "scale": scale,
        "score": values[fi][0],
        "coarse_interior": coarse_interior,
        "fine_interior": 0 < fi < len(fine) - 1,
        "global_correction": global_shift.tolist(),
    }


def centred(a: np.ndarray, y: float, x: float, side: int) -> np.ndarray | None:
    y0 = int(round(y - side / 2))
    x0 = int(round(x - side / 2))
    if y0 < 0 or x0 < 0 or y0 + side > a.shape[0] or x0 + side > a.shape[1]:
        return None
    return np.asarray(a[y0 : y0 + side, x0 : x0 + side])


def rail_fraction(a: np.ndarray) -> float:
    if np.issubdtype(a.dtype, np.integer):
        info = np.iinfo(a.dtype)
        return float(np.mean((a == info.min) | (a == info.max)))
    return float(np.mean((a == 0.0) | (a == 1.0)))


def null_gate(a: np.ndarray, b: np.ndarray) -> float:
    a = a[::4, ::4]
    b = b[::4, ::4]
    rng = np.random.default_rng(0xC0FFEE)
    values = []
    while len(values) < 64:
        dy = int(rng.integers(16, a.shape[0] - 16))
        dx = int(rng.integers(16, a.shape[1] - 16))
        dy *= -1 if rng.integers(2) else 1
        dx *= -1 if rng.integers(2) else 1
        values.append(correlation(a, np.roll(b, (dy, dx), (0, 1))))
    return float(np.quantile(values, 0.999))


def one_roi(sg: np.ndarray, cg: np.ndarray, centre: tuple[int, int], g: dict) -> dict:
    scale = g["scale"]
    gy, gx = g["global_correction"]
    y, x = centre
    sc = centred(sg, y, x, 512)
    side = int(round(512 / scale))
    c0 = centred(cg, y / scale, x / scale, side)
    cg0 = centred(cg, (y - gy) / scale, (x - gx) / scale, side)
    if sc is None or c0 is None or cg0 is None:
        return {"centre": centre, "reason": "bounds"}
    sr = ranks(sc)
    initial = resized_rank(cg0, sr.shape)
    dy, dx = correction(sr, initial)
    if abs(dy) > 64 or abs(dx) > 64:
        return {"centre": centre, "reason": "registration-null"}
    cy = (y - gy - dy) / scale
    cx = (x - gx - dx) / scale
    cc = centred(cg, cy, cx, side)
    if cc is None:
        return {"centre": centre, "reason": "bounds"}
    cr = resized_rank(cc, sr.shape)
    none = resized_rank(c0, sr.shape)
    corr_none = correlation(sr[::4, ::4], none[::4, ::4])
    corr_fixed = correlation(sr[::4, ::4], cr[::4, ::4])
    gate = null_gate(sr, cr)
    reason = None
    if corr_fixed <= gate:
        reason = "registration-null"
    elif corr_fixed - corr_none < 0.02:
        reason = "registration-gain"
    elif rail_fraction(sc) > 0.01 or rail_fraction(cc) > 0.01:
        reason = "rail"
    row = {
        "centre": list(centre),
        "reason": reason,
        "corr_none": corr_none,
        "corr_fixed": corr_fixed,
    }
    if reason is None:
        ss = shares(sc)
        cs = shares(cc, scale)
        row["log_ratio"] = np.log(ss / cs).tolist()
        row["texture"] = float(
            math.sqrt(float(np.sum(ss[:3])) * float(np.sum(cs[:3])))
        )
    return row


def bootstrap(detail: np.ndarray, flat: np.ndarray) -> dict:
    rng = np.random.default_rng(20260903)
    dd = np.empty((10_000, 6))
    ff = np.empty((10_000, 6))
    for i in range(10_000):
        dd[i] = np.mean(
            detail[rng.integers(0, len(detail), len(detail))], axis=0
        )
        ff[i] = np.mean(flat[rng.integers(0, len(flat), len(flat))], axis=0)
    dlo, dhi = np.quantile(dd, [0.025, 0.975], axis=0)
    flo, fhi = np.quantile(ff, [0.025, 0.975], axis=0)
    return {
        "r_detail": np.exp(np.mean(detail, axis=0)).tolist(),
        "detail_ci_low": np.exp(dlo).tolist(),
        "detail_ci_high": np.exp(dhi).tolist(),
        "r_flat": np.exp(np.mean(flat, axis=0)).tolist(),
        "flat_ci_low": np.exp(flo).tolist(),
        "flat_ci_high": np.exp(fhi).tolist(),
    }


def checker_fixture(n: int = 384) -> np.ndarray:
    rng = np.random.default_rng(710)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    phase = np.exp(2j * np.pi * rng.random((n, n)))
    texture = np.fft.ifft2(
        phase / np.maximum(radius, 1.0 / n)
    ).real
    texture = (texture - texture.mean()) / texture.std()
    yy, xx = np.mgrid[:n, :n]
    x = (
        0.25 * texture
        + 0.32 * np.sin(2 * np.pi * 0.18 * xx + 0.3)
        + 0.22 * np.sin(2 * np.pi * 0.27 * (0.8 * xx + 0.6 * yy) + 1.1)
        + 0.15 * np.sin(2 * np.pi * 0.35 * yy + 0.7)
        + 0.35 * (xx > n * 0.37)
        - 0.21 * (yy > n * 0.63)
    )
    return (x - x.min()) / (x.max() - x.min())


def sensitivity() -> tuple[list[float], list[bool]]:
    x = checker_fixture()
    base = shares(x)
    blurred = shares(gaussian(x, sigma=2.0, preserve_range=True))
    move = np.abs(blurred / base - 1.0)
    return move.tolist(), (move >= 0.05).tolist()


def verdict(e: dict, k: int, sensitive: bool = True) -> str:
    if not sensitive:
        return "NOT SENSITIVE"
    if e["detail_ci_low"][k] > 1.05:
        primary = "LEADS"
    elif e["detail_ci_high"][k] < 1 / 1.05:
        primary = "TRAILS"
    else:
        primary = "UNRESOLVED"
    if e["flat_ci_low"][k] > 1.05:
        flat = "LEADS"
    elif e["flat_ci_high"][k] < 1 / 1.05:
        flat = "TRAILS"
    else:
        flat = "UNRESOLVED"
    return "UNRESOLVED (FLAT VETO)" if primary == flat != "UNRESOLVED" else primary


def robustness_downgrade(current: str, label: str, triggered: bool) -> str:
    if not triggered or current == "NOT SENSITIVE":
        return current
    return label


def run(key: str) -> dict:
    sp, cp, label = PATHS[key]
    g = geometry(sp, cp)
    print(
        f"CHECK {key} geometry scale={g['scale']:.4f} score={g['score']:.6f} "
        f"interior={g['coarse_interior'] and g['fine_interior']} "
        f"correction={g['global_correction']}",
        flush=True,
    )
    sg = tifffile.memmap(sp)[:, :, 1]
    cg = tifffile.memmap(cp)[:, :, 1]
    centres = [
        (y, x)
        for y in range(512, sg.shape[0] - 383, 512)
        for x in range(512, sg.shape[1] - 383, 512)
    ]
    rows = []
    for i, centre in enumerate(centres, 1):
        rows.append(one_roi(sg, cg, centre, g))
        if i % 12 == 0 or i == len(centres):
            print(f"checker progress {i}/{len(centres)}", flush=True)
    reasons = collections.Counter(r["reason"] or "eligible" for r in rows)
    good = [r for r in rows if r["reason"] is None]
    if len(good) < 24:
        raise RuntimeError(f"checker {key}: only {len(good)} eligible ROIs")
    textures = np.asarray([r["texture"] for r in good])
    fc = float(np.quantile(textures, 0.25))
    dc = float(np.quantile(textures, 0.50))
    flat = np.asarray([r["log_ratio"] for r in good if r["texture"] <= fc])
    detail_rows = [r for r in good if r["texture"] >= dc]
    detail = np.asarray([r["log_ratio"] for r in detail_rows])
    e = bootstrap(detail, flat)
    blur_move, sensitive = sensitivity()
    classes = [verdict(e, k, sensitive[k]) for k in range(6)]
    provisional = [
        "LEADS"
        if e["detail_ci_low"][k] > 1.05
        else "TRAILS"
        if e["detail_ci_high"][k] < 1 / 1.05
        else "UNRESOLVED"
        for k in range(6)
    ]

    loo_reversal = []
    for k, primary in enumerate(provisional):
        opposite = (
            "TRAILS"
            if primary == "LEADS"
            else "LEADS"
            if primary == "TRAILS"
            else None
        )
        reversed_k = False
        if opposite:
            for i in range(len(detail)):
                ratio = float(np.exp(np.mean(np.delete(detail, i, axis=0), axis=0)[k]))
                cls = (
                    "LEADS"
                    if ratio > 1.05
                    else "TRAILS"
                    if ratio < 1 / 1.05
                    else "UNRESOLVED"
                )
                reversed_k |= cls == opposite
        loo_reversal.append(reversed_k)
        classes[k] = robustness_downgrade(
            classes[k], "UNRESOLVED (LOO REVERSAL)", reversed_k
        )

    quadrants = []
    for qy in range(2):
        for qx in range(2):
            selected = [
                r
                for r in detail_rows
                if (r["centre"][0] >= sg.shape[0] / 2) == bool(qy)
                and (r["centre"][1] >= sg.shape[1] / 2) == bool(qx)
            ]
            if selected:
                arr = np.asarray([r["log_ratio"] for r in selected])
                quadrants.append(np.exp(np.mean(arr, axis=0)).tolist())
    quadrant_opposition = []
    for k, primary in enumerate(provisional):
        if primary == "LEADS":
            opposite_count = sum(q[k] < 1.0 for q in quadrants)
        elif primary == "TRAILS":
            opposite_count = sum(q[k] > 1.0 for q in quadrants)
        else:
            opposite_count = 0
        opposed = opposite_count >= 2
        quadrant_opposition.append(opposed)
        classes[k] = robustness_downgrade(
            classes[k], "UNRESOLVED (QUADRANT)", opposed
        )
    for k, name in enumerate(BAND_NAMES):
        print(
            f"CHECK {name}: R_detail={e['r_detail'][k]:.4f} "
            f"[{e['detail_ci_low'][k]:.4f},{e['detail_ci_high'][k]:.4f}] "
            f"R_flat={e['r_flat'][k]:.4f} "
            f"[{e['flat_ci_low'][k]:.4f},{e['flat_ci_high'][k]:.4f}] "
            f"=> {classes[k]}"
        )
    return {
        "pair": key,
        "label": label,
        "geometry": g,
        "reasons": dict(reasons),
        "eligible_count": len(good),
        "detail_count": len(detail),
        "flat_count": len(flat),
        "effect": e,
        "blur_move": blur_move,
        "sensitive": sensitive,
        "provisional_classes": provisional,
        "loo_reversal": loo_reversal,
        "quadrant_opposition": quadrant_opposition,
        "classes": classes,
    }


def self_test() -> None:
    x = np.array([[4, 1, 1], [0, 2, 8], [7, 3, 6]], np.float64)
    expected = np.array([[6, 2.5, 2.5], [1, 4, 9], [8, 5, 7]], np.float64)
    expected = (expected - 5) / 9
    if not np.array_equal(ranks(x), expected):
        raise RuntimeError("checker independent rank oracle failed")
    rng = np.random.default_rng(4)
    source = rng.normal(size=(96, 96))
    moving = np.roll(source, (3, -2), axis=(0, 1))
    got = correction(source, moving)
    a, b = overlap(source, moving, got)
    if got != (-3, 2) or not np.array_equal(a, b):
        raise RuntimeError(f"checker registration sign failed: {got}")
    if (
        robustness_downgrade(
            "NOT SENSITIVE", "UNRESOLVED (QUADRANT)", True
        )
        != "NOT SENSITIVE"
    ):
        raise RuntimeError("checker robustness precedence failed")
    print("CHECK SELF-TEST GREEN: external ranks and shift correction (-3,+2)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", nargs="*", choices=tuple(PATHS), default=None)
    args = parser.parse_args(argv)
    self_test()
    output = {key: run(key) for key in (args.pairs or list(PATHS))}
    print("CHECK_JSON=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
