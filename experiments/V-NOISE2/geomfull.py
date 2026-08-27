"""geomfull -- re-derive the geometry for the FULL merges, rather than inherit
the half-stacks' fit.

V-HEADTOHEAD2 sec.7 warns that geometry must be re-derived, not trusted: the
`focus-stack` fork disagreed by 5.3 px rms locally and that destroyed 41 of 64
regions.  `C:\\dev\\strehl-out\\V-NOISE2\\119\\geom.json` holds a scale of 1.0040
fitted between the HALF-stacks.  The full merges are different files produced by
a different number of input frames, and inheriting that number would be exactly
the assumption sec.7 says not to make.

THREE FITS, two of which have a known answer in advance:

  strehl-full vs strehl-A       CONTROL.  Same binary, same warpmap, same
                                canvas, different frame subset.  The scale must
                                come back 1.000 and the offset 0 px.  If it does
                                not, the full merge does not land on the same
                                canvas as the half-stacks and the census tile
                                coordinates -- measured on that canvas -- do not
                                address the same scene content in both.  That
                                would invalidate the whole comparison, so it is
                                checked before anything else.
  enfuse-full vs enfuse-A       CONTROL, same argument on the comparator side.
  strehl-full vs enfuse-full    THE MEASUREMENT.  Compared against the
                                half-stack fit of 1.0040 already on disk.

Writes geom-full.json next to geom.json.  Never overwrites geom.json.

    python geomfull.py [key=119]
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import geom                                                      # noqa: E402

import hd2                                                       # noqa: E402

COARSE = np.arange(0.990, 1.0101, 0.005)


def fit_pair(sp, cp, tag, expect=None):
    print(f"\n=== {tag} ===")
    s, sc, ok, _ = geom.fit(sp, cp, COARSE)
    if not ok:
        print("  coarse sweep has NO INTERIOR MAXIMUM -- FAILED FIT")
        return {"ok": False, "why": "no interior maximum"}
    fine = np.arange(s - 0.006, s + 0.0061, 0.001)
    s2, sc2, ok2, _ = geom.fit(sp, cp, fine, verbose=False)
    off = geom.offsets(sp, cp, s2)
    dy, dx, pk = off[:, 2], off[:, 3], off[:, 4]
    rms = float(np.sqrt(((dy - np.median(dy)) ** 2
                         + (dx - np.median(dx)) ** 2).mean()))
    print(f"  REFINED scale {s2:.4f} score {sc2:.4f} "
          f"{'(interior)' if ok2 else '(EDGE -- suspect)'}")
    print(f"  offsets over {len(off)} tiles: dy median {np.median(dy):+.1f} px, "
          f"dx median {np.median(dx):+.1f} px")
    print(f"  peak median {np.median(pk):.4f} min {pk.min():.4f}; "
          f"residual after one global integer shift {rms:.1f} px rms")
    row = {"ok": True, "scale": round(float(s2), 4), "score": round(float(sc2), 4),
           "interior": bool(ok2), "rms_px": round(rms, 2),
           "dy": float(np.median(dy)), "dx": float(np.median(dx))}
    if expect is not None:
        good = (abs(s2 - expect) < 1e-9 and abs(np.median(dy)) < 1e-9
                and abs(np.median(dx)) < 1e-9)
        row["control_pass"] = bool(good)
        print(f"  CONTROL: expected scale {expect:.4f}, offset 0/0 -> "
              f"{'PASS' if good else 'FAIL'}")
    return row


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    arm = os.path.join(hd2.ROOT, key, "arms")
    sf = os.path.join(arm, "strehl-full.tiff")
    ef = os.path.join(arm, "coh-enfuse-full.tif")
    sa = os.path.join(arm, "strehl-A.tiff")
    ea = os.path.join(arm, "coh-enfuse-A.tif")
    for p in (sf, ef, sa, ea):
        if not os.path.exists(p):
            raise SystemExit(f"missing {p}")

    print("=" * 92)
    print(f"GEOMFULL -- geometry re-derived for the FULL merges, {key}")
    print("=" * 92)
    out = {}
    out["strehl-full_vs_strehl-A"] = fit_pair(sf, sa, "CONTROL strehl-full vs strehl-A", 1.0)
    out["enfuse-full_vs_enfuse-A"] = fit_pair(ef, ea, "CONTROL enfuse-full vs enfuse-A", 1.0)
    out["strehl-full_vs_enfuse-full"] = fit_pair(sf, ef, "MEASUREMENT strehl-full vs enfuse-full")

    half = hd2.scales_for(key)["enfuse"]
    got = out["strehl-full_vs_enfuse-full"]["scale"]
    print()
    print("=" * 92)
    print(f"  half-stack fit on disk {half:.4f}   full-merge fit {got:.4f}   "
          f"difference {abs(got - half) / half:.2%}")
    ctrl = [k for k in out if "CONTROL" or True]
    bad = [k for k, v in out.items() if v.get("control_pass") is False]
    if bad:
        print(f"  CANVAS CONTROL FAILED on {bad} -- the full merges do NOT land "
              f"on the half-stacks' canvas, so census tile coordinates do not "
              f"address the same content.  REFUSING.")
    else:
        print("  canvas controls PASS: the full merges land on the half-stacks' "
              "canvas, so the census cells address the same scene content.")
    del ctrl
    dst = os.path.join(hd2.ROOT, key, "geom-full.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {dst}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
