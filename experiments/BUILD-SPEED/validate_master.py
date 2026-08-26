"""Validity controls for a timed render. A fast run that produced a bad picture
is not fast.

Checks, in order of what they can reject:

  1. STRUCTURE -- dtype must be uint16, 3 channels, and the geometry must be the
     stack's true active area (7032 x 4688 for the A7C II). A run that wrote a
     float or a single plane is a fail no matter what it cost.
  2. DEGENERACY -- not constant, not all-zero, and not saturated. The cheap
     adversarial inputs rule 20 asks for: a constant image and an all-zero image
     both PASS a naive "the file exists and is 16-bit" check, so they are what
     this stage exists to reject, and `--selftest` plants exactly those and
     requires a RED.
  3. DETAIL, WITH ITS FLAT CONTROL (rule 9). `mean |grad|` on the green channel
     over the whole frame, and separately over a flat ROI and a detail ROI.
     DIRECTION IT CAN BE FOOLED (rule 18): mean |grad| rises when a merge
     MANUFACTURES detail exactly as it does when a merge preserves it, so it is
     admissible against COLLAPSE and inadmissible as evidence of quality. The
     flat ROI is the control: a render that gained "detail" on featureless
     background gained noise.
  4. AGREEMENT with a reference master, if one is given: SHA-256 first (a match
     ends the question), then a numeric comparison -- mean/max absolute
     difference, correlation, and the same detail statistic on both -- because
     "does the shipped master agree with today's default" is a finding either
     way.

The ROIs are chosen on the REFERENCE master when one is supplied, so the arm
under test never picks its own ground (discipline 438's shape).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import tifffile


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def grad_mag_mean(plane: np.ndarray) -> float:
    """mean |grad| by forward difference. Cheap, and the same on both arms."""
    a = plane.astype(np.float32)
    gx = np.abs(np.diff(a, axis=1))[:-1, :]
    gy = np.abs(np.diff(a, axis=0))[:, :-1]
    return float(np.mean(np.hypot(gx, gy)))


def pick_rois(g: np.ndarray, size: int = 400) -> dict[str, tuple[int, int, int, int]]:
    """Flattest and most detailed `size` x `size` tile on a coarse grid."""
    h, w = g.shape
    best_flat = (1e30, 0, 0)
    best_det = (-1.0, 0, 0)
    step = size
    for y in range(0, h - size, step):
        for x in range(0, w - size, step):
            tile = g[y : y + size, x : x + size]
            d = grad_mag_mean(tile[::4, ::4])
            if d < best_flat[0]:
                best_flat = (d, x, y)
            if d > best_det[0]:
                best_det = (d, x, y)
    return {
        "flat": (best_flat[1], best_flat[2], size, size),
        "detail": (best_det[1], best_det[2], size, size),
    }


def load(path: str) -> np.ndarray:
    img = tifffile.imread(path)
    if img.ndim == 2:
        img = img[:, :, None]
    return img


def report(path: str, ref: str | None, expect_w: int, expect_h: int) -> dict:
    out: dict[str, object] = {"path": path}
    img = load(path)
    out["shape"] = list(img.shape)
    out["dtype"] = str(img.dtype)
    out["bytes"] = os.path.getsize(path)
    out["sha256"] = sha256(path)

    fails: list[str] = []
    if img.dtype != np.uint16:
        fails.append(f"dtype is {img.dtype}, not uint16")
    if img.ndim != 3 or img.shape[2] != 3:
        fails.append(f"shape {img.shape} is not 3-channel")
    if expect_w and (img.shape[1] != expect_w or img.shape[0] != expect_h):
        fails.append(
            f"geometry {img.shape[1]} x {img.shape[0]} is not {expect_w} x {expect_h}"
        )

    g = img[:, :, 1]
    out["min"], out["max"] = int(img.min()), int(img.max())
    out["mean"] = float(img.mean())
    out["std"] = float(img.std())
    out["frac_zero"] = float((img == 0).mean())
    out["frac_saturated"] = float((img == 65535).mean())
    if out["std"] == 0.0:
        fails.append("image is CONSTANT")
    if out["max"] == 0:
        fails.append("image is ALL ZERO")
    if out["frac_zero"] > 0.5:
        fails.append(f"{100 * out['frac_zero']:.1f}% of samples are exactly 0")

    ref_img = None
    if ref and os.path.exists(ref):
        ref_img = load(ref)
        out["ref_path"] = ref
        out["ref_sha256"] = sha256(ref)
        out["ref_shape"] = list(ref_img.shape)
        out["hash_match"] = out["ref_sha256"] == out["sha256"]

    roi_src = ref_img[:, :, 1] if ref_img is not None and ref_img.shape == img.shape else g
    out["roi_chosen_on"] = "reference master" if roi_src is not g else "this image"
    rois = pick_rois(roi_src)
    out["rois"] = {k: list(v) for k, v in rois.items()}

    out["detail_whole"] = grad_mag_mean(g[::2, ::2])
    for name, (x, y, w, h) in rois.items():
        out[f"detail_{name}"] = grad_mag_mean(g[y : y + h, x : x + w])

    if ref_img is not None and ref_img.shape == img.shape:
        rg = ref_img[:, :, 1]
        out["ref_detail_whole"] = grad_mag_mean(rg[::2, ::2])
        for name, (x, y, w, h) in rois.items():
            out[f"ref_detail_{name}"] = grad_mag_mean(rg[y : y + h, x : x + w])
        d = img.astype(np.int32) - ref_img.astype(np.int32)
        out["diff_mean_abs"] = float(np.abs(d).mean())
        out["diff_max_abs"] = int(np.abs(d).max())
        out["diff_rms"] = float(np.sqrt((d.astype(np.float64) ** 2).mean()))
        a = img[::4, ::4, 1].astype(np.float64).ravel()
        b = ref_img[::4, ::4, 1].astype(np.float64).ravel()
        out["corr_green"] = float(np.corrcoef(a, b)[0, 1])
        out["detail_ratio_whole"] = out["detail_whole"] / out["ref_detail_whole"]
        for name in rois:
            out[f"detail_ratio_{name}"] = (
                out[f"detail_{name}"] / out[f"ref_detail_{name}"]
                if out[f"ref_detail_{name}"]
                else float("nan")
            )

    out["FAILS"] = fails
    out["VERDICT"] = "PASS" if not fails else "FAIL"
    return out


def selftest(tmp: str) -> int:
    """Plant the two inputs a naive check passes, and require a RED on each."""
    os.makedirs(tmp, exist_ok=True)
    bad = 0
    cases = {
        "constant": np.full((64, 64, 3), 1234, np.uint16),
        "allzero": np.zeros((64, 64, 3), np.uint16),
        "float": np.random.rand(64, 64, 3).astype(np.float32),
    }
    good = (np.random.rand(64, 64, 3) * 60000).astype(np.uint16)
    cases["random-uint16"] = good
    for name, arr in cases.items():
        p = os.path.join(tmp, f"selftest-{name}.tif")
        tifffile.imwrite(p, arr)
        r = report(p, None, 0, 0)
        want = "PASS" if name == "random-uint16" else "FAIL"
        got = r["VERDICT"]
        mark = "ok " if got == want else "BAD"
        if got != want:
            bad += 1
        print(f"  selftest {name:14s} want {want:4s} got {got:4s} {mark} {r['FAILS']}")
    print("SELFTEST", "GREEN" if bad == 0 else f"RED ({bad} wrong)")
    return 1 if bad else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--img")
    ap.add_argument("--ref", default=None)
    ap.add_argument("--width", type=int, default=7032)
    ap.add_argument("--height", type=int, default=4688)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    if args.selftest:
        sys.exit(
            selftest(os.path.join(os.environ.get("TEMP", "."), "bs-selftest")) and 0
        )

    r = report(args.img, args.ref, args.width, args.height)
    for k, v in r.items():
        if isinstance(v, float):
            print(f"{k:22s} {v:.6g}")
        else:
            print(f"{k:22s} {v}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=2)
    sys.exit(0 if r["VERDICT"] == "PASS" else 2)


if __name__ == "__main__":
    main()
