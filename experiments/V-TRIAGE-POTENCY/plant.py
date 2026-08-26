#!/usr/bin/env python3
"""V-TRIAGE-POTENCY: plant a known MERGE-ONLY defect, and prove it landed.

BUILD-TRIAGE reports MERGE-LIMITED = 0 over 26 subjects.  A zero is produced
identically by "nothing was wrong" and by "the detector cannot fire", so this
script manufactures the condition the detector claims to catch:

    the MERGE MASTER is degraded; the SOURCE FRAMES are not touched at all.

A Gaussian blur on arm A alone, against unblurred arm B, IS merge loss by
construction: every DN of detail the blur removes is still present in the
source frames the classifier compares against.

Everything is written into a scratch tree.  BUILD-TRIAGE's own lin/ masters are
opened read-only and never written.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import time

import numpy as np
import tifffile
from scipy import ndimage

BT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE"
sys.path.insert(0, BT)
import tri  # noqa: E402

SRC_LIN = r"C:\dev\strehl-out\BUILD-TRIAGE\lin"
FP_Y, FP_X, FP_N = 2200, 3400, 512   # fixed fingerprint tile, same every rung


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(a: np.ndarray) -> float:
    y = tri.luma(a.astype(np.float32))
    t = np.ascontiguousarray(y[FP_Y:FP_Y + FP_N, FP_X:FP_X + FP_N])
    return tri.edge_slope(t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("sigma", type=float)
    ap.add_argument("dst", help="destination lin/ directory for this rung")
    args = ap.parse_args()

    os.makedirs(args.dst, exist_ok=True)
    src = os.path.join(SRC_LIN, args.subject + ".tiff")
    srclog = os.path.join(SRC_LIN, args.subject + ".log")
    dst = os.path.join(args.dst, args.subject + ".tiff")
    dstlog = os.path.join(args.dst, args.subject + ".log")
    if not os.path.exists(src):
        raise SystemExit(f"ANCHOR MISSING: {src}")

    a = tifffile.imread(src)
    assert a.dtype == np.uint16 and a.ndim == 3, f"unexpected master {a.dtype} {a.shape}"
    f_src = fingerprint(a)
    print(f"SOURCE  {src}")
    print(f"        shape={a.shape} sha256={sha256(src)}")
    print(f"        fingerprint edge_slope = {f_src:.4f} DN/px")

    if args.sigma > 0.0:
        out = np.empty_like(a)
        for c in range(a.shape[2]):
            b = ndimage.gaussian_filter(a[..., c].astype(np.float32), args.sigma)
            out[..., c] = np.clip(np.rint(b), 0, 65535).astype(np.uint16)
    else:
        out = a.copy()

    identical = bool(np.array_equal(out, a))
    if args.sigma > 0.0 and identical:
        raise SystemExit("PLANT DID NOT LAND: blurred array is identical to source")
    if args.sigma == 0.0 and not identical:
        raise SystemExit("NULL CONTROL CORRUPT: sigma=0 changed pixels")

    tifffile.imwrite(dst, out, photometric="rgb")
    # The log carries coverage_k / n_frames / resampler; the plant does not
    # change any of them, so it is copied verbatim.
    shutil.copyfile(srclog, dstlog)
    now = time.time()
    os.utime(dst, (now, now))
    os.utime(dstlog, (now, now))

    back = tifffile.imread(dst)
    if not np.array_equal(back, out):
        raise SystemExit("READ-BACK MISMATCH: what was written is not what was made")
    f_dst = fingerprint(back)
    print(f"PLANTED sigma={args.sigma} -> {dst}")
    print(f"        sha256={sha256(dst)}")
    print(f"        mtime={time.ctime(os.path.getmtime(dst))}")
    print(f"        fingerprint edge_slope = {f_dst:.4f} DN/px "
          f"({f_dst / f_src:.4f}x source)")
    print(f"        max|delta| = {int(np.abs(back.astype(np.int32) - a.astype(np.int32)).max())} DN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
