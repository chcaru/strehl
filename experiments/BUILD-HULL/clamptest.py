"""Which arm is the 10.1590%, and is my hull the object the clamp enforces?

Scores clamped and unclamped merges against ONE hull -- the cached per-pixel
[min_k, max_k] over the 205 warped co-registered frames -- so the only thing that
differs between the two headline rows is whether the binary contains the clamp.

Two questions, two designs:

  Q1/Q3  Does a CLAMPED render violate MY hull?
         `pyramid.rs:998-1005` folds its hull "from the frames as supplied --
         before any decomposition", per plane at level-0 size. That is the same
         object my cache holds. If it really is the same object, the clamped arm
         must read ~0%, at the level of my null arm (0.0002%), not 10%.
         A clamped arm that still reads ~10% would mean the two hulls are
         different objects and the clamp enforces something I am not measuring.

  BUILD CONTROL  The two binaries differ by a night of other agents' commits, not
         only by the clamp. The estimator backend contains no hull code in either
         build, so if S-estimator and W-estimator are byte-identical the builds
         agree everywhere the clamp is absent, and the pyramid difference is
         attributable to the clamp rather than to the intervening commits.
         This is the control that licenses the causal claim.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np

from bhull2 import BBOX, BBOX_FULL, CHANNELS, HDR, load16, row, score

# (tag, binary, clamp state, note)
ARMS = [
    ("W-pyramid", "VERIFY-WIRE 6E4B3696", "UNCLAMPED", "no hull code in the image at all"),
    ("S-pyramid", "ORCH-SHIP  705C22D5", "CLAMPED", "Hull::InputRange, the product default"),
    ("W-estimator", "VERIFY-WIRE 6E4B3696", "n/a", "build control arm"),
    ("S-estimator", "ORCH-SHIP  705C22D5", "n/a", "build control arm"),
    ("W-uniform", "VERIFY-WIRE 6E4B3696", "UNCLAMPED", "null: weights shared across bands"),
]

PREDICTIONS = [
    "S-pyramid (clamped) reads ~0%, at the level of the null's 0.0002%, if and",
    "  only if pyramid.rs's hull and my cached hull are the same object.",
    "S-estimator == W-estimator byte for byte, since neither build's estimator",
    "  path contains hull code; this bounds the intervening-commit confound.",
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--guard", type=float, default=1.0)
    a = ap.parse_args()

    cache, mdir = Path(a.cache), Path(a.dir)
    lo = np.load(cache / "lo.npy").astype(np.float32)
    hi = np.load(cache / "hi.npy").astype(np.float32)
    span = hi - lo
    y0, y1, x0, x1 = BBOX

    print("=== BUILD-HULL :: CLAMPED vs UNCLAMPED against one hull ===")
    print(f"  hull cache : {cache}  (205 warped co-registered frames)")
    print(f"  guard      : +/- {a.guard:g} DN")
    print("\n  PREDICTIONS, registered before the rows below were computed:")
    for line in PREDICTIONS:
        print(f"    {line}")

    print(f"\n  arms REQUESTED : {len(ARMS)}")
    scored = [t for t, *_ in ARMS if (mdir / f"merge-{t}.tiff").exists()]
    missing = [t for t, *_ in ARMS if not (mdir / f"merge-{t}.tiff").exists()]
    print(f"  arms SCORED    : {len(scored)}  {scored}")
    print(f"  arms MISSING   : {len(missing)}  {missing}")
    assert len(scored) + len(missing) == len(ARMS), "arm partition does not sum"

    print("\n--- provenance ---")
    for tag, binname, clamp, note in ARMS:
        p = mdir / f"merge-{tag}.tiff"
        mark = sha(p) if p.exists() else "MISSING"
        print(f"  {tag:<14} {binname:<22} {clamp:<10} sha256[:16]={mark}  {note}")

    regions = {"whole (control)": (slice(None), slice(None)),
               "bbox": (slice(y0, y1 + 1), slice(x0, x1 + 1))}

    print(f"\n--- vs the warped-frame hull   (bbox = y{y0}..{y1} x{x0}..{x1}, half-res) ---")
    print(HDR)
    got: dict[tuple[str, str], dict] = {}
    for tag, _b, clamp, _n in ARMS:
        p = mdir / f"merge-{tag}.tiff"
        if not p.exists():
            print(f"  {tag:<26} {'--':<4} MISSING -- not scored")
            continue
        m = load16(p).astype(np.float32)
        v = np.where(m < lo, m - lo, np.where(m > hi, m - hi, 0.0))
        for rname, (ys, xs) in regions.items():
            for ci, cn in enumerate(CHANNELS + ("all",)):
                vv = v[ys, xs, :] if cn == "all" else v[ys, xs, ci]
                ss = span[ys, xs, :] if cn == "all" else span[ys, xs, ci]
                r = score(vv, ss, a.guard)
                print(row(f"{tag} [{clamp}] {rname}", cn, r))
                if cn == "all":
                    got[(tag, rname)] = r
        print()

    print("--- BUILD CONTROL: does the clamp explain the difference? ---")
    pe, ue = mdir / "merge-S-estimator.tiff", mdir / "merge-W-estimator.tiff"
    if pe.exists() and ue.exists():
        se, we = load16(pe), load16(ue)
        d = se.astype(np.int32) - we.astype(np.int32)
        ident = sha(pe) == sha(ue)
        print(f"  S-estimator vs W-estimator : identical={ident}  "
              f"max|diff|={int(np.abs(d).max())} DN  differing samples={int((d != 0).sum())}")
        print("    the estimator path contains no hull code in EITHER build, so this is")
        print("    the intervening-commit confound measured rather than assumed.")
    else:
        print("  SKIPPED -- an estimator arm is missing (this is not a pass)")

    sp, wp = mdir / "merge-S-pyramid.tiff", mdir / "merge-W-pyramid.tiff"
    if sp.exists() and wp.exists():
        s, w = load16(sp).astype(np.int32), load16(wp).astype(np.int32)
        d = s - w
        nz = d != 0
        print(f"\n  S-pyramid vs W-pyramid     : differing samples={int(nz.sum())} "
              f"({100.0 * nz.mean():.4f}%)  max={int(d.max())} min={int(d.min())} DN")
        print(f"    zero-valued samples  unclamped={int((w == 0).sum())}  clamped={int((s == 0).sum())}")
        if nz.any():
            print(f"    mean signed change where it changed = {d[nz].mean():+.1f} DN")

    print("\n--- VERDICT ---")
    # score() already returns `rate` in percent; do not scale it again.
    for tag in ("W-pyramid", "S-pyramid", "W-uniform"):
        r = got.get((tag, "whole (control)"))
        if r:
            print(f"  {tag:<12} whole-image out-of-hull = {r['rate']:.4f}%  "
                  f"(below {r['below']}, above {r['above']} of {r['total']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
