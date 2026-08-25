"""E2d -- P-POLARITY on a subject that HAS the missing class.

E2b's depth-split killed the bee-3 bright-object row: of 18 accepted
bright-object edges only 5 straddle a depth discontinuity at all.  On a bee,
"bright thing on a dark background" is nearly always a pale hair lying ON the
dark body -- same depth, no occlusion -- so the row tested nothing.  Reporting
a P-POLARITY verdict from it would be exactly the setup error that has cost
this project six times tonight (fact 1632: every one of ORCH's errors was in
what was compared to what, none in the measurement).

`tweezers-cpl` has the missing class as its main subject: bright metal against
a dark, deeply defocused ground.  This milestone rendered it at the shipped
settings and dumped the index map, so the object side can be decided by real
elected depth rather than by a texture proxy.

    C:\\dev\\strehl-out\\M121\\tweezers\\invocation.txt      (merged + index map)
    C:\\dev\\strehl-out\\M121\\tweezers\\invocation-1f.txt   (single frame, N1)

THE CLASSIFIER, AND WHY IT CHANGED.  bee-3's object side came from the max
over five single frames of the merge's own windowed gradient.  There are no
matched single frames for tweezers, so here the object side is decided from
the INDEX MAP: the side whose elected frame sits at the near end of the sweep
is the object.  That is a stronger classifier, not a weaker one -- it is the
merge's own depth decision rather than a texture proxy -- but it is a DIFFERENT
classifier, so this script first cross-checks it against the five-frame
classifier on bee-3 and prints the agreement rate.  A verdict from a
classifier that disagrees with the one the headline used is not comparable.

FAILURE DIRECTIONS.
  * If the two classifiers disagree on bee-3, neither row here is comparable
    to the headline and this script says so.
  * N1 (the single unmerged tweezers frame) must read nothing.  If it reads a
    rim, the tweezers instrument is measuring edges and the rows are void.

Run:  python experiments/M121-halo-polarity/e2d_tweezers.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from e2_polarity import (  # noqa: E402
    FLAT_TOL, GRAD_PCT, ISO, MAX_EDGES, MIN_AMPLITUDE, NEAR_MAX, WINDOW_RADIUS,
    commissioned_max_rise, focus_field, make_classifier, polarity_table,
)
from m121_io import FRAMES, OUT, arm_path, load_u16, luma  # noqa: E402
from runner import _boot_ci, scan  # noqa: E402

TW = pathlib.Path(r"C:\dev\strehl-out\M121\tweezers")
PROBE = 20.0        # px along the normal, matching bee-3's classifier
SAT_DEFAULT = 0.995 * 65535.0


def load_idx(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a


def index_classifier(idx, near_is_low):
    """+1 if the BRIGHT side is the object, -1 if the DARK side is, 0 if the
    two sides elected the same depth (no discontinuity -- not a silhouette)."""
    h, w = idx.shape

    def f(e):
        y, x, nx, ny = e["y"], e["x"], e["nx"], e["ny"]
        vals = []
        for s in (+1, -1):                       # +1 = bright side
            yy = min(max(int(round(y + s * PROBE * ny)), 0), h - 1)
            xx = min(max(int(round(x + s * PROBE * nx)), 0), w - 1)
            v = idx[yy, xx]
            vals.append(np.nan if v == 65535 else float(v))
        b, d = vals
        if not np.isfinite(b) or not np.isfinite(d) or abs(b - d) < 2:
            return 0
        bright_nearer = (b < d) if near_is_low else (b > d)
        return +1 if bright_nearer else -1
    return f


def rows(r, tag, res):
    pt = polarity_table(r)
    res[tag] = {"read_band": pt.get("read_band"), "out_of_band": pt.get("out_of_band"),
                "rise_median": r["rise_median"], "rise_p90": r["rise_p90"],
                "C_d0": r["C_d0"]}
    print(f"  {tag}: rise med/p90 = {r['rise_median']:.2f}/{r['rise_p90']:.2f}  "
          f"band {pt.get('read_band', [np.nan, np.nan])[0]:.2f}-"
          f"{pt.get('read_band', [np.nan, np.nan])[1]:.2f} px")
    for cls in ("dark_object_bright_surround", "bright_object_dark_surround"):
        blk = pt.get(cls, {})
        if not isinstance(blk, dict) or blk.get("n", 0) < 8 \
                or not np.isfinite(blk.get("surround_rim", np.nan)):
            print(f"      {cls:30s} n={blk.get('n', 0) if isinstance(blk, dict) else 0:<4d} (no reading)")
            res[tag][cls] = {"n": blk.get("n", 0) if isinstance(blk, dict) else 0}
            continue
        res[tag][cls] = {k: blk[k] for k in
                         ("n", "surround_rim", "lo95", "hi95", "frac_positive",
                          "w50", "w10", "cutoff")}
        print(f"      {cls:30s} n={blk['n']:<4d} rim={blk['surround_rim']:+.4f} "
              f"[{blk['lo95']:+.4f},{blk['hi95']:+.4f}] +ve={100*blk['frac_positive']:.0f}% "
              f"w50={blk['w50']:.2f} cut={blk['cutoff']:.2f}")
    return pt


def main():
    max_rise = commissioned_max_rise()
    res = {"max_rise": max_rise, "window_radius_focus_rs": WINDOW_RADIUS}
    print(f"commissioned envelope: 10-90 rise <= {max_rise:.2f} px\n")

    # --- classifier cross-check on bee-3 -------------------------------------
    print("=== classifier cross-check on bee-3 (five-frame vs index-map) ===")
    bee = luma(load_u16(arm_path("armM4-gate4-binlin")))
    bee_idx = load_idx(pathlib.Path(r"C:\dev\strehl-out\M121\e3\index.tif"))
    frames = {n: luma(load_u16(arm_path(n))) for n in FRAMES}
    fmax = np.max(np.stack([focus_field(f) for f in frames.values()]), axis=0)
    five = make_classifier(fmax)

    agree = {}
    for near_is_low in (True, False):
        ic = index_classifier(bee_idx, near_is_low)

        def both(e, ic=ic):
            return (five(e), ic(e))
        r = scan(bee, label="xcheck", grad_percentile=GRAD_PCT, max_edges=MAX_EDGES,
                 isolation_frac=ISO, flat_tol=FLAT_TOL, classify=five,
                 max_rise=max_rise, min_amplitude=MIN_AMPLITUDE,
                 extra=lambda e, ic=ic: ic(e), verbose=False)
        s = r["bright"]
        a = np.asarray(s["obj"])
        b = np.asarray(s["dz"])
        both_signed = (a != 0) & (b != 0)
        rate = float(np.mean(a[both_signed] == b[both_signed])) if both_signed.any() else np.nan
        agree[f"near_is_low={near_is_low}"] = {"n": int(both_signed.sum()), "agreement": rate}
        print(f"  near_is_low={near_is_low!s:5s}  n={int(both_signed.sum()):4d}  "
              f"agreement={100*rate:.1f}%")
    res["classifier_crosscheck"] = agree
    near_is_low = agree["near_is_low=True"]["agreement"] >= agree["near_is_low=False"]["agreement"]
    print(f"  -> using near_is_low={near_is_low} "
          f"({100*max(v['agreement'] for v in agree.values()):.1f}% agreement)")
    res["near_is_low"] = bool(near_is_low)
    if max(v["agreement"] for v in agree.values()) < 0.6:
        print("  WARNING: the two classifiers disagree; tweezers rows are NOT comparable "
              "to the bee-3 headline.")

    # --- tweezers ------------------------------------------------------------
    print("\n=== tweezers-cpl, shipped gate 4.0 ===")
    tw = luma(load_u16(TW / "tweezers-gate4.tif"))
    tw_idx = load_idx(TW / "index.tif")
    t1 = luma(load_u16(TW / "tweezers-1f.tif"))
    # The metal reaches the 16-bit ceiling.  A clipped plateau is not a
    # plateau, and the first run of this script proved it: the dark-object row
    # read +1.47, twenty times the edge amplitude.  Reject any profile that
    # touches the ceiling, in BOTH the merged image and the control, so the
    # two are scored by the same rule.
    SAT = SAT_DEFAULT
    print(f"  merged {tw.shape}  luma {tw.min():.0f}..{tw.max():.0f}  "
          f"at-ceiling {100*np.mean(tw >= SAT):.3f}%")
    print(f"  1-frame {t1.shape}  luma {t1.min():.0f}..{t1.max():.0f}  "
          f"at-ceiling {100*np.mean(t1 >= SAT):.3f}%")
    print(f"  saturation rejection: any profile with a plateau or >2% of samples "
          f">= {SAT:.0f} DN is dropped")
    print(f"  index  {tw_idx.shape}  {tw_idx[tw_idx != 65535].min()}.."
          f"{tw_idx[tw_idx != 65535].max()}")
    res["sat_level"] = SAT
    tc = index_classifier(tw_idx, near_is_low)

    rt = scan(tw, label="TW merged", grad_percentile=GRAD_PCT, max_edges=MAX_EDGES,
              isolation_frac=ISO, flat_tol=FLAT_TOL, classify=tc,
              max_rise=max_rise, min_amplitude=MIN_AMPLITUDE, sat_level=SAT,
              collect_edges=True, verbose=False)
    rows(rt, "TW_merged_gate4", res)

    print("\n=== N1 CONTROL: single unmerged tweezers frame, own edges ===")
    print("    FAILURE DIRECTION: no merge, so no rim.  A rim here voids the rows above.")
    r1 = scan(t1, label="TW 1f", grad_percentile=GRAD_PCT, max_edges=MAX_EDGES,
              isolation_frac=ISO, flat_tol=FLAT_TOL, classify=tc,
              max_rise=max_rise, min_amplitude=MIN_AMPLITUDE, sat_level=SAT,
              verbose=False)
    rows(r1, "TW_single_frame", res)

    print("\n=== N1b CONTROL: single frame AT THE MERGED ARM'S OWN EDGES ===")
    print("    Same pixels, same normals, same acceptance -- the matched-pixel form.")
    r1b = scan(t1, label="TW 1f donor", edges=rt["kept_edges"], isolation_frac=ISO,
               flat_tol=FLAT_TOL, classify=tc, max_rise=None,
               min_amplitude=MIN_AMPLITUDE, sat_level=SAT, verbose=False)
    rows(r1b, "TW_single_frame_donor_edges", res)

    (OUT / "e2d-tweezers.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT / 'e2d-tweezers.json'}")


if __name__ == "__main__":
    main()
