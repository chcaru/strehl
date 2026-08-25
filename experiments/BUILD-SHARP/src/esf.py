"""BUILD-SHARP step 1: the paired ESF rise, arm against arm.

This runs the treatment arm of `docs/research/M88b-merge-sharpness.md`, whose
instrument was BUILT, NULLED and POSITIVELY CONTROLLED but never pointed at a
treatment because M86's alignment wiring was unfinished at the time. It is
wired now.

Why this instrument and not a band-power ratio
----------------------------------------------
M85 retracted the project's standing 0.30-0.48 cyc/px sharpness band after
measuring it at 12.8 % subject detail / 87.2 % noise, with a DARK FRAME reading
the same gain (`ORCH-kernel-decision.md` §9). Every band-power number scored
there is uninterpretable. The 10-90 ESF rise is immune to that failure by
construction: it averages hundreds of pixels ALONG an edge, so noise enters as
variance on the estimate (bounded by M88b's measured 0.67 um floor) and not as
signal. It is also 18,644x more responsive than ring FRC to a planted low-pass
(M88b §2).

Nothing in `m88blib.py` or `m88lib.py` is modified. They are IMPORTED. A copy
can drift from its original; an import cannot.

Rule 18 -- which direction can this be fooled in?
------------------------------------------------
* It reads WIDER when an arm is displaced and the window is not re-located.
  Every comparison here goes through `paired_delta_registered`, whose
  correction is INTEGER (rule 6) and whose applied shift is reported.
* It reads WIDER on an arm whose edge is genuinely lower in contrast, if the
  10/90 thresholds land in the noise. The per-arm contrast is reported beside
  every rise so this is visible rather than assumed.
* It cannot be fooled by injected high-frequency structure that is not ON the
  edge -- unlike mean|grad|, which rises when a merge manufactures detail
  (rule 18). Speckle, election patchwork and independent noise do not narrow
  a 10-90 rise; they widen the error bar.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "experiments" / "M88b-merge-sharpness" / "src"))
sys.path.insert(0, str(REPO / "experiments" / "M88-optical-ceiling" / "src"))

import m88blib as M  # noqa: E402

RENDERS = Path(r"C:\dev\strehl-out\BUILD-SHARP\renders")

# The frozen ROI set, lifted verbatim from
# experiments/M88b-merge-sharpness/out/b03_nulls.json. `admitted` is M88b's
# own N1 gate: 32 noise realisations per ROI, pre-declared bar p95|delta| <=
# 1.0 um. Only admitted ROIs carry a stated floor, so only they are headlined.
NULLS = REPO / "experiments" / "M88b-merge-sharpness" / "out" / "b03_nulls.json"

# M88b named its stacks with short keys. This maps them onto capture folders.
STACK_DIR = {
    "109MSDCF": "109MSDCF",
    "ruler": "highly-angled-ruler-mm-cpl",
    "tweezers": "tweezers-cpl",
    "bee-3-cpl": "bee-3-cpl",
    "bee-2-cpl": "bee-2-cpl",
    "wtext1": "wrapped-text-1",
}


def load_rois():
    d = json.loads(NULLS.read_text())
    admitted = {(r["stack"], r["name"]): r for r in d["N1"]["rows"]}
    out = []
    for r in d["rois"]:
        key = (r["stack"], r["name"])
        a = admitted.get(key, {})
        out.append(dict(stack=r["stack"], name=r["name"], roi=tuple(r["roi"]),
                        axis=r["axis"], admitted=bool(a.get("admitted", False)),
                        floor_um=float(a.get("p95_abs_um", float("nan")))))
    return out


def plane(subject_dir: str, arm: str):
    p = RENDERS / subject_dir / arm / "linear.tif"
    if not p.exists():
        return None
    return M.read_merge_plane(p, "G")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="reference arm (the OFF arm)")
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--stacks", nargs="+", default=["109MSDCF", "ruler", "tweezers"])
    ap.add_argument("--admitted-only", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    rois = load_rois()
    results = []

    print(f"reference arm (OFF) : {a.ref}")
    print("positive delta_um   = the arm is SHARPER than the reference "
          "(its 10-90 rise is shorter)")
    print("M88b instrument floor: worst admitted p95 |delta| = 0.6699 um\n")

    for stack in a.stacks:
        sub = STACK_DIR[stack]
        pref = plane(sub, a.ref)
        if pref is None:
            print(f"[{stack}] reference arm {a.ref} not rendered -- skipped")
            continue
        sel = [r for r in rois if r["stack"] == stack
               and (r["admitted"] or not a.admitted_only)]
        if not sel:
            continue
        print(f"=== {stack} ({sub}) ===")
        hdr = f"{'ROI':>6} {'adm':>4} {'arm':>14} {'rise_ref':>9} {'rise_arm':>9} " \
              f"{'delta_um':>9} {'delta_%':>8} {'shift':>9} {'c_ref':>8} {'c_arm':>8}"
        print(hdr)
        for r in sel:
            for arm in a.arms:
                pon = plane(sub, arm)
                if pon is None:
                    continue
                d = M.paired_delta_registered(pref, pon, r["roi"], r["axis"])
                if d.get("error"):
                    print(f"{r['name']:>6} {str(r['admitted']):>4} {arm:>14} "
                          f"  ERROR {d['error'][:50]}")
                    continue
                dm = d["rise_off_um"] - d["rise_on_um"]
                pct = 100.0 * dm / d["rise_off_um"] if d["rise_off_um"] else float("nan")
                print(f"{r['name']:>6} {str(r['admitted']):>4} {arm:>14} "
                      f"{d['rise_off_um']:9.3f} {d['rise_on_um']:9.3f} "
                      f"{dm:9.3f} {pct:8.2f} "
                      f"{d.get('shift_dy', 0):4d},{d.get('shift_dx', 0):<4d} "
                      f"{d['contrast_off']:8.0f} {d['contrast_on']:8.0f}")
                results.append(dict(stack=stack, roi=r["name"],
                                    admitted=r["admitted"], floor_um=r["floor_um"],
                                    ref=a.ref, arm=arm,
                                    rise_ref_um=d["rise_off_um"],
                                    rise_arm_um=d["rise_on_um"],
                                    delta_um=dm, delta_pct=pct,
                                    shift_dy=d.get("shift_dy", 0),
                                    shift_dx=d.get("shift_dx", 0),
                                    contrast_ref=d["contrast_off"],
                                    contrast_arm=d["contrast_on"]))
        print()

    # pooled summary over ADMITTED ROIs only
    print("=== pooled over ADMITTED ROIs (the only ones with a stated floor) ===")
    print(f"{'arm':>14} {'n':>3} {'mean delta_um':>14} {'sd':>8} {'mean rise_ref':>14} "
          f"{'mean rise_arm':>14}")
    for arm in a.arms:
        rows = [r for r in results if r["arm"] == arm and r["admitted"]]
        if not rows:
            continue
        dv = np.array([r["delta_um"] for r in rows])
        print(f"{arm:>14} {len(rows):3d} {dv.mean():14.4f} {dv.std(ddof=1):8.4f} "
              f"{np.mean([r['rise_ref_um'] for r in rows]):14.3f} "
              f"{np.mean([r['rise_arm_um'] for r in rows]):14.3f}")

    out = Path(a.out) if a.out else (Path(__file__).resolve().parents[1] / "out" /
                                     f"esf-{a.ref}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(ref=a.ref, arms=a.arms, rows=results), indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
