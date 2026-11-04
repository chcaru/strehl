"""Held-out raw-sample prediction: does joint multi-frame reconstruction from
original CFA samples carry more real scene information than the engine's
per-frame demosaic + warp + average?

For each ROI (reference sensor coordinates) the in-focus frames of one pass are
found; each in turn is held out, both arms are built from the rest, and both
predict the held-out frame's own raw samples at their exact registered
positions. Real information lowers that error toward the held-out frame's noise
floor; sharpening alone cannot, because a fitted linear filter (the "fitted"
columns, cross-validated on alternate tiles) is offered to both arms.

Arms
  A   engine emulation: per-frame MHC demosaic, Catmull-Rom pull, mean
  B   joint: per channel, least squares for a full-res grid whose Catmull-Rom
      interpolation matches every original sample of that channel (+ small
      Laplacian ridge)
  Bp  placebo: B with every sample snapped to its nearest same-colour site of
      the reference lattice (destroys sub-pixel phase, keeps density)
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

sys.path.insert(0, str(Path(__file__).parent))
from common import (BLACK, GAIN_DN_PER_E, READ_E, cfa_channel, channel_transform, cr_matrix_rows,
                    cr_sample, decode_many, frame_to_ref, load_alignment, mhc, ref_to_frame)

CH = "rgb"


def frame_box(t, roi, centre, margin):
    x0, y0, s = roi
    xs = np.array([x0, x0 + s, x0, x0 + s], float)
    ys = np.array([y0, y0, y0 + s, y0 + s], float)
    fx, fy = ref_to_frame(t, xs, ys, centre)
    bx0 = int(np.floor(fx.min())) - margin
    by0 = int(np.floor(fy.min())) - margin
    bx1 = int(np.ceil(fx.max())) + margin
    by1 = int(np.ceil(fy.max())) + margin
    bx0 -= bx0 & 1  # keep CFA parity: patch origin on an even site
    by0 -= by0 & 1
    return (bx0, by0, bx1, by1)


def focus_score(patch):
    g = patch[0::2, 1::2].astype(np.float64) - BLACK
    lap = 4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    noise = 20 * (GAIN_DN_PER_E * np.maximum(g[1:-1, 1:-1], 0) + (GAIN_DN_PER_E * READ_E) ** 2)
    return float(np.mean(np.maximum(lap * lap - noise, 0)) / max(np.mean(g) ** 2, 1.0))


def samples(frame, ch, use_ca, centre, snap=False, jitter=None):
    """All original samples of channel ch in a frame patch, positioned in reference sensor coords."""
    patch, (bx0, by0), t, wb, gain = frame
    h, w = patch.shape
    yy, xx = np.mgrid[by0:by0 + h, bx0:bx0 + w]
    c = cfa_channel(xx, yy)
    m = c == ch
    tc = channel_transform(t, CH[ch], use_ca)
    rx, ry = frame_to_ref(tc, xx[m].astype(float), yy[m].astype(float), centre)
    if jitter is not None:
        rx, ry = rx + jitter[0], ry + jitter[1]
    if snap:
        if ch == 1:
            # nearest green (quincunx) site: x+y odd
            fx, fy = np.round(rx), np.round(ry)
            bad = ((fx + fy) % 2) == 0
            dx, dy = rx - fx, ry - fy
            fx = np.where(bad & (np.abs(dx) >= np.abs(dy)), fx + np.sign(dx + 1e-9), fx)
            fy = np.where(bad & (np.abs(dx) < np.abs(dy)), fy + np.sign(dy + 1e-9), fy)
            rx, ry = fx, fy
        else:
            ox, oy = (0, 0) if ch == 0 else (1, 1)
            rx = 2 * np.round((rx - ox) / 2) + ox
            ry = 2 * np.round((ry - oy) / 2) + oy
    v = (patch[m].astype(np.float64) - BLACK) * wb[ch] * gain
    return rx, ry, v


def arm_a(frames, grid, use_ca, centre):
    gx0, gy0, gw, gh = grid
    yy, xx = np.mgrid[gy0:gy0 + gh, gx0:gx0 + gw].astype(float)
    acc = np.zeros((3, gh, gw))
    n = np.zeros((3, gh, gw))
    for patch, (bx0, by0), t, wb, gain in frames:
        h, w = patch.shape
        yi, xi = np.mgrid[by0:by0 + h, bx0:bx0 + w]
        mos = (patch.astype(np.float64) - BLACK) * wb[cfa_channel(xi, yi)] * gain
        rgb = mhc(mos, bx0, by0)
        for ch in range(3):
            tc = channel_transform(t, CH[ch], use_ca)
            fx, fy = ref_to_frame(tc, xx, yy, centre)
            v = cr_sample(rgb[ch], fx - bx0, fy - by0)
            ok = np.isfinite(v)
            acc[ch][ok] += v[ok]
            n[ch][ok] += 1
    return acc / np.maximum(n, 1)


def arm_b(frames, grid, use_ca, centre, lam, snap=False, jitters=None):
    gx0, gy0, gw, gh = grid
    out = np.zeros((3, gh, gw))
    npx = gw * gh
    # Laplacian ridge (second differences) on the grid
    def d2(n):
        return sp.diags([1, -2, 1], [-1, 0, 1], shape=(n - 2, n))
    Dx = sp.kron(sp.eye(gh), d2(gw))
    Dy = sp.kron(d2(gh), sp.eye(gw))
    R = (Dx.T @ Dx + Dy.T @ Dy).tocsr()
    for ch in range(3):
        rows, cols, vals, obs = [], [], [], []
        for k, f in enumerate(frames):
            j = None if jitters is None else jitters[k]
            rx, ry, v = samples(f, ch, use_ca, centre, snap=snap, jitter=j)
            ok, c, w = cr_matrix_rows(rx, ry, gx0, gy0, gw, gh)
            c, w, v = c[ok], w[ok], v[ok]
            base = sum(len(o) for o in obs)
            rows.append(np.repeat(np.arange(base, base + len(v)), 16))
            cols.append(c.ravel())
            vals.append(w.ravel())
            obs.append(v)
        A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                          shape=(sum(len(o) for o in obs), npx))
        y = np.concatenate(obs)
        # sample density differs per channel; scale ridge by mean samples per grid px
        density = len(y) / npx
        N = (A.T @ A + lam * density * R).tocsr()
        rhs = A.T @ y
        x0 = np.full(npx, y.mean())
        sol, info = spl.cg(N, rhs, x0=x0, rtol=1e-7, maxiter=3000)
        out[ch] = sol.reshape(gh, gw)
    return out


def _channel_rows(frames, ch, use_ca, centre, grid, weights=None):
    gx0, gy0, gw, gh = grid
    rows, cols, vals, obs = [], [], [], []
    base = 0
    for k, f in enumerate(frames):
        rx, ry, v = samples(f, ch, use_ca, centre)
        ok, c, w = cr_matrix_rows(rx, ry, gx0, gy0, gw, gh)
        c, w, v = c[ok], w[ok], v[ok]
        if weights is not None:
            ix = np.clip(np.round(rx[ok] - gx0).astype(int), 0, gw - 1)
            iy = np.clip(np.round(ry[ok] - gy0).astype(int), 0, gh - 1)
            sw = np.sqrt(weights[k][iy, ix])
            keep = sw > 1e-3
            c, w, v = c[keep], w[keep] * sw[keep, None], v[keep] * sw[keep]
        rows.append(np.repeat(np.arange(base, base + len(v)), 16))
        cols.append(c.ravel())
        vals.append(w.ravel())
        obs.append(v)
        base += len(v)
    return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                         shape=(base, gw * gh)), np.concatenate(obs)


def arm_c(frames, grid, use_ca, centre, base, lam_luma=0.02, lam_chroma=2.0, lam_stay=1e-3, weights=None):
    """Joint correction of a base RGB estimate (arm A) from every original sample.

    u_c = base_c + d_c; data: Catmull-Rom interpolation of u_c at each original
    sample of channel c; prior: small curvature on d_G, strong gradient penalty
    on the chroma corrections d_R - d_G and d_B - d_G, tiny ridge toward the base.
    """
    gx0, gy0, gw, gh = grid
    n = gw * gh

    def d1(m):
        return sp.diags([-1.0, 1.0], [0, 1], shape=(m - 1, m))

    def d2(m):
        return sp.diags([1.0, -2.0, 1.0], [-1, 0, 1], shape=(m - 2, m))

    G1 = sp.vstack([sp.kron(sp.eye(gh), d1(gw)), sp.kron(d1(gh), sp.eye(gw))])
    G2 = sp.vstack([sp.kron(sp.eye(gh), d2(gw)), sp.kron(d2(gh), sp.eye(gw))])
    L1 = (G1.T @ G1).tocsr()
    L2 = (G2.T @ G2).tocsr()
    I = sp.eye(n, format="csr")
    blocks = [[None] * 3 for _ in range(3)]
    rhs = []
    dens = []
    As = []
    for ch in range(3):
        A, y = _channel_rows(frames, ch, use_ca, centre, grid, weights)
        As.append((A, y))
        dens.append(len(y) / n)
    dmean = float(np.mean(dens))
    for ch in range(3):
        A, y = As[ch]
        blocks[ch][ch] = A.T @ A + lam_stay * dmean * I
        rhs.append(A.T @ (y - A @ base[ch].ravel()))
    blocks[1][1] = blocks[1][1] + lam_luma * dmean * L2
    # chroma: ||G1 (d_R - d_G)||^2 + ||G1 (d_B - d_G)||^2
    c = lam_chroma * dmean
    for ch in (0, 2):
        blocks[ch][ch] = blocks[ch][ch] + c * L1
        blocks[1][1] = blocks[1][1] + c * L1
        blocks[ch][1] = -c * L1
        blocks[1][ch] = -c * L1
    N = sp.bmat(blocks, format="csr")
    sol, info = spl.cg(N, np.concatenate(rhs), rtol=1e-7, maxiter=4000)
    return base + sol.reshape(3, gh, gw)


def predict_holdout(img, frame, grid, use_ca, centre, inner):
    """Predict every raw sample of the held-out frame lying inside the inner ROI.
    Returns per channel: observed, predicted (centre), stencil (5x5 at 1 px), tile id, noise var."""
    gx0, gy0, gw, gh = grid
    res = {}
    for ch in range(3):
        rx, ry, v = samples(frame, ch, use_ca, centre)
        ix0, iy0, s = inner
        m = (rx >= ix0) & (rx < ix0 + s) & (ry >= iy0) & (ry < iy0 + s)
        rx, ry, v = rx[m], ry[m], v[m]
        stencil = []
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                stencil.append(cr_sample(img[ch], rx + dx - gx0, ry + dy - gy0))
        st = np.stack(stencil, 1)
        wb, gain = frame[3][ch], frame[4]
        raw_dn = v / (wb * gain)
        noise = (GAIN_DN_PER_E * np.maximum(raw_dn, 0) + (GAIN_DN_PER_E * READ_E) ** 2) * (wb * gain) ** 2
        tile = ((np.floor((rx - ix0) / 32) + np.floor((ry - iy0) / 32)) % 2).astype(int)
        res[ch] = (v, st, tile, noise)
    return res


def score(pred):
    out = {}
    for ch, (v, st, tile, noise) in pred.items():
        ok = np.all(np.isfinite(st), 1)
        v, st, tile, noise = v[ok], st[ok], tile[ok], noise[ok]
        raw = st[:, 12]
        mse = float(np.mean((v - raw) ** 2))
        # fitted linear filter (25 taps + bias), cross-validated on alternate tiles
        X = np.concatenate([st, np.ones((len(v), 1))], 1)
        err = np.zeros(len(v))
        for k in (0, 1):
            tr, te = tile == k, tile != k
            coef, *_ = np.linalg.lstsq(X[tr], v[tr], rcond=None)
            err[te] = v[te] - X[te] @ coef
        out[CH[ch]] = {"n": int(len(v)), "mse": mse, "mse_fitted": float(np.mean(err ** 2)),
                       "noise": float(np.mean(noise)), "signal": float(np.mean(v))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alignment", required=True)
    ap.add_argument("--pass-range", required=True, help="first,last global frame index of one pass")
    ap.add_argument("--roi", action="append", required=True, help="x0,y0,size in reference sensor px")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lam", type=float, default=0.02)
    ap.add_argument("--window-frac", type=float, default=0.5)
    ap.add_argument("--max-window", type=int, default=9)
    ap.add_argument("--ca", type=int, default=1)
    ap.add_argument("--c", type=float, nargs=3, default=[0.02, 0.5, 0.001])
    ap.add_argument("--cross-pass", help="first,last of another pass: predict its sharpest frame per ROI from the full window")
    ap.add_argument("--no-folds", action="store_true")
    ap.add_argument("--variants", nargs="*", default=None, help="ca:lam_luma:lam_chroma:lam_stay; save full-window images only")
    ap.add_argument("--jitter-placebo", type=float, default=0.0)
    args = ap.parse_args()
    t0 = time.time()
    place, paths, (gw, gh) = load_alignment(args.alignment)
    centre = complex(gw * 0.5, gh * 0.5)
    first, last = map(int, args.pass_range.split(","))
    rois = [tuple(map(int, r.split(","))) for r in args.roi]
    margin = 24
    frames_idx = [i for i in range(first, last + 1) if place[i] is not None]
    jobs = [(paths[i], [frame_box(place[i], roi, centre, margin) for roi in rois]) for i in frames_idx]
    cross_idx = []
    if args.cross_pass:
        c0, c1 = map(int, args.cross_pass.split(","))
        cross_idx = [i for i in range(c0, c1 + 1) if place[i] is not None]
        jobs_c = [(paths[i], [frame_box(place[i], roi, centre, margin) for roi in rois]) for i in cross_idx]
    decoded = decode_many(jobs + (jobs_c if args.cross_pass else []))
    decoded, decoded_c = decoded[:len(jobs)], decoded[len(jobs):]
    print(f"decoded {len(jobs)} frames in {time.time() - t0:.1f}s", flush=True)
    report = {"alignment": args.alignment, "pass_range": [first, last], "lam": args.lam,
              "ca": bool(args.ca), "rois": []}
    rng = np.random.default_rng(7)
    for r, roi in enumerate(rois):
        frames_all = []
        for k, i in enumerate(frames_idx):
            patch = decoded[k][0][r]
            box = jobs[k][1][r]
            frames_all.append((patch, (box[0], box[1]), place[i], decoded[k][1], 1.0))
        scores = np.array([focus_score(f[0]) for f in frames_all])
        peak = int(np.argmax(scores))
        lo = hi = peak
        while lo - 1 >= 0 and scores[lo - 1] >= args.window_frac * scores[peak] and hi - lo + 1 < args.max_window:
            lo -= 1
            if hi + 1 < len(scores) and scores[hi + 1] >= args.window_frac * scores[peak] and hi - lo + 1 < args.max_window:
                hi += 1
        while hi + 1 < len(scores) and scores[hi + 1] >= args.window_frac * scores[peak] and hi - lo + 1 < args.max_window:
            hi += 1
        window = list(range(lo, hi + 1))
        # photometric gain per frame: green mean ratio to the window's peak frame
        g_ref = np.mean(frames_all[peak][0][0::2, 1::2].astype(float) - BLACK)
        frames = []
        for k in window:
            p, o, t, wb, _ = frames_all[k]
            gain = g_ref / np.mean(p[0::2, 1::2].astype(float) - BLACK)
            frames.append((p, o, t, wb, gain))
        x0, y0, s = roi
        border = 6
        grid = (x0 - border, y0 - border, s + 2 * border, s + 2 * border)
        inner = (x0 + 8, y0 + 8, s - 16)
        # sub-pixel phase diversity: offsets of the roi centre across the window, in sensor px
        cx, cy = np.array([x0 + s / 2]), np.array([y0 + s / 2])
        offs = [ref_to_frame(f[2], cx, cy, centre) for f in frames]
        fx = np.array([o[0][0] for o in offs])
        fy = np.array([o[1][0] for o in offs])
        roi_rep = {"roi": roi, "window": [frames_idx[k] for k in window], "peak": frames_idx[peak],
                   "focus": scores[window].round(5).tolist(),
                   "phase_x": (fx - fx[0]).round(3).tolist(), "phase_y": (fy - fy[0]).round(3).tolist(),
                   "gains": [round(f[4], 4) for f in frames], "folds": []}
        print(f"roi {roi}: window {roi_rep['window'][0]}..{roi_rep['window'][-1]} ({len(window)}), "
              f"phase spread x {np.ptp(fx):.2f} y {np.ptp(fy):.2f} sensor px", flush=True)
        if len(frames) < 3:
            report["rois"].append(roi_rep)
            continue
        for h in range(0 if args.no_folds else len(frames)):
            train = [f for k, f in enumerate(frames) if k != h]
            fold = {"held_out": roi_rep["window"][h]}
            imgs = {
                "A": arm_a(train, grid, bool(args.ca), centre),
                "B": arm_b(train, grid, bool(args.ca), centre, args.lam),
                "Bp": arm_b(train, grid, bool(args.ca), centre, args.lam, snap=True),
            }
            imgs["C"] = arm_c(train, grid, bool(args.ca), centre, imgs["A"], *args.c)
            if args.jitter_placebo > 0:
                jit = [tuple(rng.uniform(-args.jitter_placebo, args.jitter_placebo, 2)) for _ in train]
                imgs["Bj"] = arm_b(train, grid, bool(args.ca), centre, args.lam, jitters=jit)
            for name, img in imgs.items():
                fold[name] = score(predict_holdout(img, frames[h], grid, bool(args.ca), centre, inner))
            roi_rep["folds"].append(fold)
            line = " ".join(
                f"{n}:" + "/".join(f"{fold[n][c]['mse_fitted'] / fold[n][c]['noise']:.3f}" for c in CH)
                for n in imgs)
            print(f"  hold {fold['held_out']}: fitted mse/noise (r/g/b) {line}", flush=True)
            if h == len(frames) // 2:
                np.save(Path(args.out).with_suffix("") .as_posix() + f"-roi{r}-imgs.npy",
                        np.stack([imgs["A"], imgs["B"], imgs["C"]]))
        if args.variants is not None:
            out = [arm_a(frames, grid, bool(args.ca), centre)]
            for v in args.variants:
                ca, ll, lc, ls = v.split(":")
                base = arm_a(frames, grid, bool(int(ca)), centre)
                out.append(arm_c(frames, grid, bool(int(ca)), centre, base, float(ll), float(lc), float(ls)))
            np.save(Path(args.out).with_suffix("").as_posix() + f"-roi{r}-variants.npy", np.stack(out))
            print("  saved variants", flush=True)
        if cross_idx:
            cf = []
            for k, i in enumerate(cross_idx):
                box = jobs_c[k][1][r]
                cf.append((decoded_c[k][0][r], (box[0], box[1]), place[i], decoded_c[k][1], 1.0))
            cs = np.array([focus_score(f[0]) for f in cf])
            kk = int(np.argmax(cs))
            p, o, t, wb, _ = cf[kk]
            held = (p, o, t, wb, g_ref / np.mean(p[0::2, 1::2].astype(float) - BLACK))
            imgs = {"A": arm_a(frames, grid, bool(args.ca), centre)}
            imgs["C"] = arm_c(frames, grid, bool(args.ca), centre, imgs["A"], *args.c)
            imgs["B"] = arm_b(frames, grid, bool(args.ca), centre, args.lam)
            fold = {"held_out": cross_idx[kk], "cross_pass": True}
            for name, img in imgs.items():
                fold[name] = score(predict_holdout(img, held, grid, bool(args.ca), centre, inner))
            roi_rep["cross"] = fold
            line = " ".join(f"{n}:" + "/".join(f"{fold[n][c]['mse_fitted'] / fold[n][c]['noise']:.3f}" for c in CH) for n in imgs)
            print(f"  cross-pass {cross_idx[kk]}: fitted mse/noise (r/g/b) {line}", flush=True)
        report["rois"].append(roi_rep)
    report["elapsed_s"] = time.time() - t0
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
