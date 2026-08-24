"""M71 step 10 -- kappa for R and B, which the two-green trick cannot reach.

The headline estimator needs two same-colour planes to difference. R and B
have no partner, so for them the optical term cannot be cancelled and must be
bounded instead. Two routes:

  (a) UPPER BOUND, no assumptions: the whole high-pass residual of the flats,
      minus the temporal noise, is an upper bound on kappa because any
      leftover optical structure only adds.

  (b) POINT ESTIMATE using the greens to calibrate the optical term. In the
      flats the greens measure the common optical power directly: C =
      cov(r_G1, r_G2) is optical structure with the PRNU and the noise
      removed. R and B see the same defocused paper through the same optics,
      differing only by the CFA's spectral response, so C is the right scale
      of the optical term for them too, to the accuracy of that assumption.

Also the cross-CPL-state covariance route applied per plane, which is
assumption-free for the noise but NOT for the optical term: the same paper is
in both halves, so an optical term survives it. That is why (a) and (b) are
the honest bracket and the cross-state number is reported as an upper bound.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "out" / "cache"
OUT = HERE / "data" / "10-rb.json"

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "k5", Path(__file__).resolve().parent / "05-kappa.py")
_k5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_k5)
residual, highpass_response = _k5.residual, _k5.highpass_response

PAIRS = [("e0.004", "1/250"), ("e0.008", "1/125"),
         ("e0.016666666666666666", "1/60"),
         ("e0.03333333333333333", "1/30"), ("e0.05", "1/20")]


def main() -> None:
    F = highpass_response()
    frames = json.loads((HERE / "data" / "02-frames.json").read_text(encoding="utf-8"))
    ptc = json.loads((HERE / "data" / "03-ptc.json").read_text(encoding="utf-8"))
    lvl = {}
    for rec in frames:
        tag = _k5.tag_of(rec["exp"], rec["half"])
        d = lvl.setdefault(tag, {p: [] for p in ("R", "G1", "G2", "B")})
        for p in d:
            d[p].append(rec[f"mean_{p}"])
    lvl = {t: {p: float(np.mean(v)) for p, v in d.items()} for t, d in lvl.items()}

    print("=== kappa per plane. The greens are MEASURED (optical term cancels).")
    print("    R and B are BRACKETED: an assumption-free upper bound from the")
    print("    full residual, and a point estimate that subtracts the greens'")
    print("    own measured optical power.\n")
    res = {}
    for pl in ("R", "G1", "G2", "B"):
        g = ptc[pl]["g"]
        ups, pts, xs = [], [], []
        for base, label in PAIRS:
            row = []
            for half in ("A", "B"):
                tag = f"{base}-{half}"
                S = lvl[tag][pl]
                r = residual(np.load(CACHE / f"{tag}-{pl}-mean.npy"))
                v = float(np.var(r))
                # temporal-mean noise that survives the high pass, 20 frames
                nv = (g * S + 1.0) / (S * S) / 20.0 * F
                row.append((S, v, nv))
            # cross-state covariance kills the noise exactly
            ra = residual(np.load(CACHE / f"{base}-A-{pl}-mean.npy")).ravel()
            rb = residual(np.load(CACHE / f"{base}-B-{pl}-mean.npy")).ravel()
            cov = float(np.mean(ra * rb) - np.mean(ra) * np.mean(rb)) / F
            # the greens' measured common optical power at this exposure
            g1a = residual(np.load(CACHE / f"{base}-A-G1-mean.npy")).ravel()
            g2a = residual(np.load(CACHE / f"{base}-A-G2-mean.npy")).ravel()
            C = float(np.mean(g1a * g2a) - np.mean(g1a) * np.mean(g2a)) / F
            ups.append(np.sqrt(max(cov, 0.0)))
            pts.append(np.sqrt(max(cov - C, 0.0)))
            xs.append(row[0][0])
        up = float(np.sqrt(np.mean(np.square(ups))))
        pt = float(np.sqrt(np.mean(np.square(pts))))
        res[pl] = {"upper_bound": up, "point": pt,
                   "per_exposure_upper": [float(x) for x in ups],
                   "per_exposure_point": [float(x) for x in pts]}
        note = " (MEASURED by the two-green difference: 0.3096%)" if pl.startswith("G") else ""
        print(f"    {pl}:  upper bound {up * 100:.4f}%   "
              f"optical-corrected {pt * 100:.4f}%{note}")
        print(f"         per exposure upper: "
              + " ".join(f"{x * 100:.3f}" for x in ups))
    print("\n    The greens' optical-corrected numbers must reproduce the")
    print("    headline 0.3096% if this route is sound -- that is its control.")
    gm = 0.5 * (res["G1"]["point"] + res["G2"]["point"])
    print(f"    greens by this route: {gm * 100:.4f}%   headline 0.3096%   "
          f"ratio {gm / 0.003096:.4f}")
    print(f"\n    R/green = {res['R']['point'] / gm:.3f}, "
          f"B/green = {res['B']['point'] / gm:.3f}")
    res["greens_control_ratio"] = float(gm / 0.003096)
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
