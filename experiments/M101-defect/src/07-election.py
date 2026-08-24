"""M101 script 07 - the election, reimplemented independently.

There is no CLI flag that dumps strehl's winner-index map, so the deciding
measurement needs an independent implementation of the decision path. Every
constant here is read from the shipped source, not re-derived:

  focus.rs      SOBEL_RADIUS=1, WINDOW_RADIUS=13, SIGMA_EPS=1e-3, 0.125 scaling,
                replicate-clamped borders on both the Sobel and the box mean
  merge.rs      REGULARISER_RADIUS=8, argmax with ties to the LOWER frame index
  plane.rs      green_luma = 0.5*((G1-black)+ + (G2-black)+)
  noise.rs      green_luma_sigma(L) = sqrt(0.25*(var_G1(L)+var_G2(L)))
  profile.rs    gain = max(ISO,100)/436.8, RN = 4.20 e- below ISO 400
  align.rs      Similarity::apply_at, reference -> frame, centre (w/2, h/2)

Three arms, selected by --arm:
  warped    the shipped default since 885e9f7: frames warped by the committed
            M86 sidecar before the focus measure
  identity  the same election with every warp forced to identity. This is the
            control for the trail: a defect cannot smear if nothing moves
  plant     warped, plus synthetic hot pixels of known amplitude at coordinates
            absent from the defect map. Discipline 615: the plant runs in its
            own arm so it cannot perturb the mechanism the real arm measures
            through

Reads  : D:\\personal\\macro\\<stack> (READ ONLY), the M86 sidecar, defectmap-*.npz
Writes : C:\\dev\\strehl-out\\M101\\election-<stack>-<arm>.npz
"""
from __future__ import annotations

import argparse
import json
import struct
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import rawpy

OUT = Path(r"C:\dev\strehl-out\M101")
REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")

BLACK = 512.0
GAIN_DIVISOR = 436.8
RN_E_LOW, RN_E_HIGH, SECOND_BASE_ISO = 4.20, 1.2392, 400
SIGMA_EPS = 1e-3
WINDOW_RADIUS = 13
REGULARISER_RADIUS = 8
PLANE_OFF = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}
PLANT_SEED = 7331


def parse_warpmap(path: Path):
    hdr, rows = {}, {}
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        t = line.split("#")[0].split()
        if t[0] == "strehl-warpmap":
            continue
        if t[0].isdigit():
            idx, state = int(t[0]), t[1]
            if state != "placed":
                rows[idx] = None
                continue
            a_re, a_im, b_re, b_im = (
                struct.unpack(">d", bytes.fromhex(v))[0] for v in t[2:6])
            rows[idx] = (complex(a_re, a_im), complex(b_re, b_im))
        else:
            hdr[t[0]] = " ".join(t[1:])
    return hdr, rows


def catmull_weights(f):
    f2, f3 = f * f, f * f * f
    return (
        0.5 * (-f3 + 2 * f2 - f),
        0.5 * (3 * f3 - 5 * f2 + 2),
        0.5 * (-3 * f3 + 4 * f2 + f),
        0.5 * (f3 - f2),
    )


def warp_gather(src, qx, qy, fill):
    """Catmull-Rom backward warp; `fill` outside the source support."""
    h, w = src.shape
    x0 = np.floor(qx).astype(np.int32)
    y0 = np.floor(qy).astype(np.int32)
    fx, fy = (qx - x0).astype(np.float32), (qy - y0).astype(np.float32)
    ok = (x0 >= 1) & (x0 <= w - 3) & (y0 >= 1) & (y0 <= h - 3)
    wx, wy = catmull_weights(fx), catmull_weights(fy)
    xb = np.clip(x0 - 1, 0, w - 4)
    yb = np.clip(y0 - 1, 0, h - 4)
    acc = np.zeros(src.shape, dtype=np.float32)
    for j in range(4):
        row = np.zeros(src.shape, dtype=np.float32)
        base = (yb + j) * w
        for i in range(4):
            row += wx[i] * src.reshape(-1)[base + xb + i]
        acc += wy[j] * row
    return np.where(ok, acc, np.float32(fill))


def box_mean(a, r):
    """Replicate-clamped separable box mean, matching boxfilter.rs."""
    n = 2 * r + 1
    p = np.pad(a.astype(np.float64), ((0, 0), (r, r)), mode="edge")
    c = np.cumsum(p, axis=1)
    h = (c[:, n - 1:] - np.concatenate(
        [np.zeros((a.shape[0], 1)), c[:, :-n]], axis=1)) / n
    p = np.pad(h, ((r, r), (0, 0)), mode="edge")
    c = np.cumsum(p, axis=0)
    v = (c[n - 1:, :] - np.concatenate(
        [np.zeros((1, a.shape[1])), c[:-n, :]], axis=0)) / n
    return v.astype(np.float32)


def sobel_mag(l):
    p = np.pad(l, 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]
          - p[:-2, :-2] - 2 * p[1:-1, :-2] - p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]
          - p[:-2, :-2] - 2 * p[:-2, 1:-1] - p[:-2, 2:])
    gx *= 0.125
    gy *= 0.125
    return np.sqrt(gx * gx + gy * gy, dtype=np.float32)


_CTX = None


def _init(ctx):
    global _CTX
    _CTX = ctx


def frame_focus(args):
    """Return (regularised focus, green luma) for one frame in reference coords."""
    k, path = args
    c = _CTX
    with rawpy.imread(str(path)) as raw:
        v = raw.raw_image_visible.astype(np.float32)  # rule 32
    W, H = c["w"], c["h"]
    planes = {}
    for pk in ("G1", "G2"):
        oy, ox = PLANE_OFF[pk]
        pl = v[oy::2, ox::2]
        if pl.shape[1] < W:  # rawpy 3514 -> rawler 3516, leading columns (M48c fact 33)
            pl = np.pad(pl, ((0, 0), (0, W - pl.shape[1])), mode="edge")
        planes[pk] = pl[:H, :W]
    if c["arm"] == "plant":
        py, px, pa = c["plant"]
        planes["G2"][py, px] += pa

    sim = c["warps"].get(k)
    if c["arm"] == "identity" or sim is None:
        g1, g2 = planes["G1"], planes["G2"]
    else:
        a, b = sim
        cx, cy = W * 0.5, H * 0.5
        yy, xx = np.mgrid[0:H, 0:W]
        pxr = xx.astype(np.float64) - cx
        pyr = yy.astype(np.float64) - cy
        qx = a.real * pxr - a.imag * pyr + b.real + cx
        qy = a.imag * pxr + a.real * pyr + b.imag + cy
        g1 = warp_gather(planes["G1"], qx, qy, BLACK)
        g2 = warp_gather(planes["G2"], qx, qy, BLACK)

    luma = 0.5 * (np.maximum(g1 - BLACK, 0) + np.maximum(g2 - BLACK, 0))
    var = c["gain"] * np.maximum(luma, 0) + (c["rn_e"] * c["gain"]) ** 2
    sigma = np.maximum(np.sqrt(0.5 * var), SIGMA_EPS).astype(np.float32)
    focus = box_mean(sobel_mag(luma), WINDOW_RADIUS) / sigma
    return k, box_mean(focus, REGULARISER_RADIUS), luma.astype(np.float32)


def worker(chunk):
    best_f, best_i, best_l = None, None, None
    for args in chunk:
        k, reg, luma = frame_focus(args)
        if best_f is None:
            best_f = reg
            best_i = np.full(reg.shape, k, dtype=np.int16)
            best_l = luma
        else:
            m = reg > best_f  # strict: ties keep the earlier index
            best_f = np.where(m, reg, best_f)
            best_i = np.where(m, np.int16(k), best_i)
            best_l = np.where(m, luma, best_l)
    return best_f, best_i, best_l


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", default=r"D:\personal\macro\bee-3-cpl")
    ap.add_argument("--warpmap", default=str(
        REPO / "experiments/M86-alignment/out/warpmap-bee-3-cpl.txt"))
    ap.add_argument("--arm", choices=("warped", "identity", "plant"), default="warped")
    ap.add_argument("--iso", type=float, default=100.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    stack = Path(a.stack)
    files = sorted(stack.glob("*.ARW"))
    hdr, warps = parse_warpmap(Path(a.warpmap))
    W, H = (int(x) for x in hdr["plane"].split("x"))
    if a.limit:
        files = files[:a.limit]
    print(f"{stack.name}: {len(files)} frames, plane {W}x{H}, arm={a.arm}", flush=True)
    print(f"  sidecar: {hdr['stack-digest']} ref={hdr['reference']} "
          f"placed={sum(1 for v in warps.values() if v)}/{hdr['frames']}", flush=True)

    gain = max(a.iso, 100) / GAIN_DIVISOR
    rn = RN_E_HIGH if a.iso >= SECOND_BASE_ISO else RN_E_LOW

    plant = None
    if a.arm == "plant":
        rng = np.random.default_rng(PLANT_SEED)
        dm = np.load(OUT / "defectmap-final.npz")
        sh = tuple(dm["shape_G2"])
        occupied = np.unpackbits(dm["G2-defect"],
                                 count=sh[0] * sh[1]).astype(bool).reshape(sh)
        ys, xs, amps = [], [], []
        for amp in (2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0):
            n = 0
            while n < 40:
                y = int(rng.integers(200, min(sh[0], H) - 200))
                x = int(rng.integers(200, min(sh[1], W) - 200))
                if occupied[y, x] or not occupied[max(y - 3, 0):y + 4,
                                                  max(x - 3, 0):x + 4].sum() == 0:
                    continue
                ys.append(y)
                xs.append(x)
                amps.append(amp)
                n += 1
        plant = (np.array(ys), np.array(xs), np.array(amps, dtype=np.float32))
        np.savez(OUT / f"plant-{stack.name}.npz", y=plant[0], x=plant[1], amp=plant[2])
        print(f"  planted {len(ys)} synthetic hot pixels, "
              f"amplitudes {sorted(set(amps))} DN", flush=True)

    ctx = {"w": W, "h": H, "warps": warps, "arm": a.arm,
           "gain": np.float32(gain), "rn_e": np.float32(rn), "plant": plant}
    jobs = [(k, f) for k, f in enumerate(files)]
    chunks = [jobs[i::a.workers] for i in range(a.workers)]

    t0 = time.time()
    best_f = best_i = best_l = None
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(ctx,)) as ex:
        for n, (bf, bi, bl) in enumerate(ex.map(worker, chunks)):
            if best_f is None:
                best_f, best_i, best_l = bf, bi, bl
            else:
                m = (bf > best_f) | ((bf == best_f) & (bi < best_i))
                best_f = np.where(m, bf, best_f)
                best_i = np.where(m, bi, best_i)
                best_l = np.where(m, bl, best_l)
            print(f"  reduced chunk {n+1}/{a.workers} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    uniq = np.unique(best_i)
    meta = {"stack": stack.name, "arm": a.arm, "n_frames": len(files),
            "plane": [W, H], "digest": hdr["stack-digest"],
            "distinct_winners": int(uniq.size),
            "median_winner": int(np.median(best_i)),
            "winner_response_p10": float(np.percentile(best_f, 10)),
            "winner_response_p50": float(np.percentile(best_f, 50)),
            "winner_response_p90": float(np.percentile(best_f, 90)),
            "elapsed_s": round(time.time() - t0, 1)}
    np.savez_compressed(OUT / f"election-{stack.name}-{a.arm}.npz",
                        winner=best_i, focus=best_f.astype(np.float32),
                        luma=best_l.astype(np.float32),
                        meta=np.array([json.dumps(meta)]))
    print(json.dumps(meta, indent=1), flush=True)


if __name__ == "__main__":
    main()
