"""Rank the corpus by CHANNEL DISPLACEMENT, with a coherence requirement.

WHY THIS EXISTS. corpus_scan.py ranks by counting magenta pixels near edges.
That statistic passed a planted-displacement commissioning -- it detects a real
1 px shift -- but it FAILED external validation against the only ground truth
available, a human survey of all 26 masters: it ranked 109MSDCF, which has no
radial organisation at all (r2 = -0.013), seven times above the subject the eye
actually flagged. Counting coloured pixels cannot tell a displacement from
noise, because noise in a low-signal channel crosses any fixed ratio threshold.

So this ranks by the quantity that has a null and a ground truth -- the fitted
radial displacement in pixels -- and REQUIRES the fit to be coherent before the
magnitude is allowed to mean anything:

  r2 > R2_MIN          the radial model must beat a constant. Lateral CA is
                       radial by definition; a displacement that is not radial
                       is not lateral CA and may not be scored as it.
  rad_rms > tan_rms    lateral CA cannot produce a tangential component, so a
                       subject whose tangential term dominates is measuring
                       something else, usually noise.

A subject failing either guard is UNSCORED, never CLEAN. That is the whole
point of the guard: it converts "I cannot tell" into an explicit verdict
instead of silently into a pass.

Usage:
    python corpus_shift.py <dir-of-masters> [--visible 0.5]
"""

import argparse
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from chromashift import field  # noqa: E402

R2_MIN = 0.05


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--visible", type=float, default=0.5,
                    help="|radial px at corner| at or above which a subject is VISIBLE")
    ap.add_argument("--tile", type=int, default=512)
    args = ap.parse_args()

    rows = []
    for p in sorted(pathlib.Path(args.dir).glob("*.tiff")):
        img = np.asarray(tifffile.imread(str(p))).astype(np.float64)
        if img.ndim == 2:
            img = np.dstack([img] * 3)
        recs = field(img[:, :, :3], args.tile, 97.0)
        if not recs:
            rows.append((p.stem, None))
            print(f"{p.stem:36} UNSCORED (no usable tiles)", flush=True)
            continue
        r = np.array([q["r"] for q in recs])
        out = {}
        for ch in ("R", "B"):
            rad = np.array([q[ch + "rad"] for q in recs])
            tan = np.array([q[ch + "tan"] for q in recs])
            slope = float((r * rad).sum() / max((r * r).sum(), 1e-30))
            pred = slope * r
            ss = float(((rad - pred) ** 2).sum())
            st = float(((rad - rad.mean()) ** 2).sum())
            out[ch] = {
                "corner": slope * float(r.max()),
                "r2": 1.0 - ss / max(st, 1e-30),
                "rad": float(np.sqrt((rad ** 2).mean())),
                "tan": float(np.sqrt((tan ** 2).mean())),
            }
        rows.append((p.stem, out))
        print(f"{p.stem:36} R {out['R']['corner']:+7.3f}px r2={out['R']['r2']:+6.3f} "
              f"rad/tan={out['R']['rad'] / max(out['R']['tan'], 1e-9):5.2f}   "
              f"B {out['B']['corner']:+7.3f}px r2={out['B']['r2']:+6.3f} "
              f"rad/tan={out['B']['rad'] / max(out['B']['tan'], 1e-9):5.2f}", flush=True)

    print("\n=== RANKED by |R radial at corner|, coherence-gated ===")
    counts = {"VISIBLE": 0, "MEASURED": 0, "CLEAN": 0, "UNSCORED": 0}
    scored = []
    for name, out in rows:
        if out is None:
            scored.append((0.0, name, "UNSCORED", None))
            continue
        coherent = (out["R"]["r2"] > R2_MIN) and (out["R"]["rad"] > out["R"]["tan"])
        mag = abs(out["R"]["corner"])
        if not coherent:
            v = "UNSCORED"
        elif mag >= args.visible:
            v = "VISIBLE"
        elif mag >= 0.1:
            v = "MEASURED"
        else:
            v = "CLEAN"
        scored.append((mag, name, v, out))
    for mag, name, v, out in sorted(scored, key=lambda t: -t[0]):
        extra = ""
        if out is not None:
            extra = (f"  R={out['R']['corner']:+.3f}px r2={out['R']['r2']:+.3f} "
                     f"rad/tan={out['R']['rad'] / max(out['R']['tan'], 1e-9):.2f}"
                     f"  same-sign(R,B)="
                     f"{'YES' if out['R']['corner'] * out['B']['corner'] > 0 else 'no'}")
        print(f"{name:36} {v:9}{extra}")
        counts[v] += 1
    print(f"\nVISIBLE={counts['VISIBLE']}  MEASURED={counts['MEASURED']}  "
          f"CLEAN={counts['CLEAN']}  UNSCORED={counts['UNSCORED']}  "
          f"TOTAL={sum(counts.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
