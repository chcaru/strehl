"""BUILD-HALO -- score arbitrary merged arms with M121's OWN halo instrument.

This file contains no instrument of its own.  It imports `runner.scan` and
`halo_lib` from `experiments/M121-halo-polarity` and calls them with M121's E2
knobs, so every number it prints is in the same units as SYNTHESIS fact 1778
(`w50 = 10.00 px`, cutoff `13.25 px`) and can be compared to it directly.  A
re-implementation would not have been comparable and would have been worthless
for a before/after.

Two readings per arm, and they answer different questions:

  OWN   -- edges detected in that arm.  This is E2's headline protocol
           (`R0_shipped_self`).  It is self-referenced, so it needs no second
           image, but the edge SET moves between arms.
  DONOR -- the baseline arm's accepted edge list, measured in this arm.  Same
           pixels, same normals, same acceptance code.  This is the one that
           licenses a before/after difference; OWN is the one that is
           commensurable with the published number.

Usage:
    python measure.py --baseline w13=<path.tif> --arm w3=<path.tif> ... \
                      [--json out.json] [--sat 64000]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

M121 = pathlib.Path(__file__).resolve().parents[1] / "M121-halo-polarity"
sys.path.insert(0, str(M121))

from e2_polarity import (  # noqa: E402
    FLAT_TOL, GRAD_PCT, ISO, MAX_EDGES, MIN_AMPLITUDE, commissioned_max_rise,
    focus_field, make_classifier, polarity_table,
)
from m121_io import FRAMES, arm_path, load_u16, luma, sha256  # noqa: E402
from runner import scan  # noqa: E402

CACHE = pathlib.Path(r"C:\dev\strehl-out\BUILD-HALO\fmax-classifier.npy")


def classifier():
    """E2's object-side classifier, from the five M93 single frames.

    Cached: the five 49 MB TIFFs and five 27x27 box means cost about a minute,
    and every arm scored tonight uses the identical classifier by construction.
    """
    if CACHE.exists():
        fmax = np.load(CACHE)
    else:
        frames = [luma(load_u16(arm_path(n))) for n in FRAMES]
        fmax = np.max(np.stack([focus_field(f) for f in frames]), axis=0)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        np.save(CACHE, fmax)
    return make_classifier(fmax)


def _pack(r):
    def comp(k):
        c = r.get(k)
        if c is None:
            return None
        return {"peak": c["peak"], "peak_at": c["peak_at"], "w50": c["w50"],
                "w10": c["w10"], "cutoff": c["cutoff"], "d0": c["d0"],
                "n": c["n"], "boot": [c["boot_median"], c["boot_lo95"], c["boot_hi95"]],
                "bands": c["bands"]}
    pol = polarity_table(r)
    return {"n_pair": r["n_pair"], "n_bright": r["n_bright"], "n_dark": r["n_dark"],
            "rise_p90": r["rise_p90"], "C_d0": r["C_d0"],
            "S": comp("S"), "C": comp("C"),
            "bright": comp("bright"), "dark": comp("dark"),
            "polarity": {k: {kk: vv for kk, vv in v.items() if kk != "curve"}
                         for k, v in pol.items() if isinstance(v, dict)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="TAG=PATH; supplies the donor edges")
    ap.add_argument("--arm", action="append", default=[], help="TAG=PATH, repeatable")
    ap.add_argument("--json", default=None)
    ap.add_argument("--sat", type=float, default=None)
    ap.add_argument("--no-donor", action="store_true")
    a = ap.parse_args()

    max_rise = commissioned_max_rise()
    cl = classifier()
    print(f"commissioned envelope: 10-90 rise <= {max_rise:.2f} px")

    def split(spec):
        tag, _, p = spec.partition("=")
        return tag, pathlib.Path(p)

    arms = [split(a.baseline)] + [split(s) for s in a.arm]
    out = {}
    donor = None
    for tag, path in arms:
        img = luma(load_u16(path))
        print(f"\n### {tag}  {path.name}  sha256={sha256(path)[:16]}  {img.shape}")
        r = scan(img, label=f"{tag} OWN", grad_percentile=GRAD_PCT,
                 max_edges=MAX_EDGES, isolation_frac=ISO, flat_tol=FLAT_TOL,
                 classify=cl, min_amplitude=MIN_AMPLITUDE, max_rise=max_rise,
                 collect_edges=(donor is None), sat_level=a.sat)
        rec = {"path": str(path), "sha256": sha256(path), "own": _pack(r)}
        if donor is None:
            donor = r["kept_edges"]
            print(f"  donor edge list: {donor.shape[0]} edges (from {tag})")
        elif not a.no_donor:
            rd = scan(img, label=f"{tag} DONOR", edges=donor, isolation_frac=ISO,
                      flat_tol=FLAT_TOL, classify=cl, min_amplitude=MIN_AMPLITUDE,
                      max_rise=None, sat_level=a.sat)
            rec["donor"] = _pack(rd)
        out[tag] = rec

    print("\n" + "=" * 78)
    print(f"{'arm':16s} {'read':6s} {'C peak':>9s} {'w50':>7s} {'cutoff':>7s} "
          f"{'S peak':>9s} {'n':>5s}")
    for tag, rec in out.items():
        for read in ("own", "donor"):
            if read not in rec:
                continue
            c, s = rec[read]["C"], rec[read]["S"]
            if c is None:
                print(f"{tag:16s} {read:6s}   no usable pairs")
                continue
            print(f"{tag:16s} {read:6s} {c['peak']:+9.5f} {c['w50']:7.2f} "
                  f"{c['cutoff']:7.2f} {s['peak']:+9.5f} {c['n']:5d}")
    print("=" * 78)
    print("M121 published headline (armM4-gate4, bee-3-cpl): C w50 10.00, cutoff 13.25")

    if a.json:
        p = pathlib.Path(a.json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1, default=float))
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
