"""Held-out patch placement: does the drift model put a block on its content?

This is the test the map actually depends on. A global scale scalar can agree
with another global scale scalar and both be wrong; what a per-block statistic
consumes is *per-frame placement of a local window*, so that is what gets
measured (AGENTS discipline 699: name the consumer and check the bar measures
its input).

Method, deliberately independent of the fitter:
  - pick N master windows by local variance so every one has something to lock
    onto, spread over the frame;
  - for each frame in a ladder, find each window's TRUE position in the green
    lattice by cv2.matchTemplate over a search box wide enough to contain the
    uncorrected error;
  - report the residual of the drift model and, side by side, the residual of
    doing nothing. The gap between those two columns is the size of the
    confound this map has to control.
"""
import argparse
import json
import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import veilcore as vc  # noqa: E402

RAWROOT = pathlib.Path(r"D:\personal\macro")
MASTERS = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")


def n01(z):
    lo, hi = np.percentile(z, [0.5, 99.5])
    return np.clip((z - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)


def pick_windows(ref, n, half=64, margin=340):
    """N high-variance windows, spread, in reference (master/2) coords."""
    h, w = ref.shape
    cand = []
    ys = np.linspace(margin + half, h - margin - half, 7).astype(int)
    xs = np.linspace(margin + half, w - margin - half, 9).astype(int)
    for y in ys:
        for x in xs:
            p = ref[y - half:y + half, x - half:x + half]
            cand.append((float(p.std()), int(y), int(x)))
    cand.sort(key=lambda t: -t[0])
    out = []
    for s, y, x in cand:
        if all(abs(y - b) > 300 or abs(x - c) > 300 for _, b, c in out):
            out.append((s, y, x))
        if len(out) >= n:
            break
    return out


def locate(gl, ref, y, x, half, py, px, pad):
    """True (y, x) of the master window in the lattice, near prediction."""
    tpl = n01(ref[y - half:y + half, x - half:x + half])
    sy0 = int(max(0, round(py - half - pad)))
    sx0 = int(max(0, round(px - half - pad)))
    sy1 = int(min(gl.shape[0], round(py + half + pad)))
    sx1 = int(min(gl.shape[1], round(px + half + pad)))
    if sy1 - sy0 < 2 * half + 4 or sx1 - sx0 < 2 * half + 4:
        return None
    src = n01(gl[sy0:sy1, sx0:sx1])
    r = cv2.matchTemplate(cv2.GaussianBlur(src, (0, 0), 3),
                          cv2.GaussianBlur(tpl, (0, 0), 3), cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    return sy0 + loc[1] + half, sx0 + loc[0] + half, float(mx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="bee-3-cpl")
    ap.add_argument("--nwin", type=int, default=6)
    ap.add_argument("--half", type=int, default=64)
    ap.add_argument("--pad", type=int, default=230)
    ap.add_argument("--ks", default="")
    ap.add_argument("--minncc", type=float, default=0.45)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    m = tifffile.imread(str(MASTERS / f"{a.subject}.tiff"))
    assert m.dtype == np.uint16
    ref = vc.block_mean_down(m[:, :, 1].astype(np.float32), 2)
    del m
    files = sorted((RAWROOT / a.subject).glob("*.ARW"))
    n = len(files)
    ks = ([int(v) for v in a.ks.split(",")] if a.ks
          else sorted({int(round(t)) for t in np.linspace(0, n - 1, 9)}))

    wins = pick_windows(ref, a.nwin, a.half)
    print(f"subject {a.subject}  frames {n}  lattice {ref.shape}")
    print("windows (master coords, y x):  "
          + "  ".join(f"({2 * y},{2 * x})" for _, y, x in wins))

    fit = vc.DriftFitter(ref)
    rows = []
    print(f"\n{'k':>5}{'a':>9}{'ty':>8}{'tx':>8}{'ncc':>7}"
          f"{'n_ok':>6}{'model resid':>14}{'no-corr resid':>16}"
          f"{'max no-corr':>13}")
    for k in ks:
        gl = vc.green_lattice(files[k])
        r = fit.fit(gl)
        res_m, res_0 = [], []
        for _, y, x in wins:
            py, px = vc.map_point(y, x, r["a"], r["ty"], r["tx"])
            got = locate(gl, ref, y, x, a.half, py, px, a.pad)
            if got is None or got[2] < a.minncc:
                continue
            ty, tx, _ = got
            res_m.append(np.hypot(ty - py, tx - px))
            res_0.append(np.hypot(ty - y, tx - x))
        if not res_m:
            print(f"{k:>5}  no window locked")
            continue
        rm = 2.0 * float(np.median(res_m))     # master px
        r0 = 2.0 * float(np.median(res_0))
        r0mx = 2.0 * float(np.max(res_0))
        rows.append(dict(k=k, a=r["a"], ty=r["ty"], tx=r["tx"], ncc=r["ncc"],
                         n_ok=len(res_m), resid_model_master_px=rm,
                         resid_nocorr_master_px=r0,
                         resid_nocorr_max_master_px=r0mx))
        print(f"{k:>5}{r['a']:9.5f}{r['ty']:8.1f}{r['tx']:8.1f}{r['ncc']:7.3f}"
              f"{len(res_m):6d}{rm:14.1f}{r0:16.1f}{r0mx:13.1f}")
        sys.stdout.flush()

    if rows:
        mm = max(x["resid_model_master_px"] for x in rows)
        m0 = max(x["resid_nocorr_master_px"] for x in rows)
        print(f"\nworst median placement error, master px:"
              f"  drift-corrected {mm:.1f}   uncorrected {m0:.1f}")
        print("PLACEMENT: " + ("PASS" if mm < 24 else "FAIL")
              + "  (bar: < 24 master px = 1/8 of the 192 px block)")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(
            dict(subject=a.subject, half=a.half, rows=rows), indent=1),
            encoding="utf-8")
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
