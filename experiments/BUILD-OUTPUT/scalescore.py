"""BUILD-OUTPUT: score the STREHL_GATE_FLOOR_SCALE arms on mottle, band by band.

WHAT IS BEING ASKED
ORCH's mechanism: mottle is a coarse-scale selection artifact -- the argmax
flipping between frames across regions with no coarse structure above noise --
so averaging exactly there should be nearly free in sharpness, because low
frequencies survive defocus and differ least between frames. If that is right,
raising the noise floor at coarse bands should cut mottle while `paid` stays
near zero. If it is wrong, the arm is a blur wearing a disguise and `paid` is
what exposes it.

WHY BASE AND NOT SHIP-V4
`recert.py`'s pair stage compares a candidate against `SHIP-V4`, which was
rendered by the shipping pin. Comparing a scale arm against it would report the
env var PLUS thirteen commits PLUS the five that have landed in `crates/` since
`f190a0ea`, with nothing separating them. Every arm here is paired against
`SC-BASE`, rendered by the same binary from the same frames with the variable
unset, so the only difference between the two files is the variable.

THE THREE BANDS ARE REPORTED TOGETHER AND NEVER AVERAGED
`recert.summarise` says why: a candidate that is quieter in `mottle` and softer
in `struct` has made a trade, and a single score is exactly how a trade becomes
invisible. The mottle claim is only interesting if `struct` held.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "BUILD-RECERT"))
sys.path.insert(0, str(HERE))
from recertlib import BANDS, classify, display_crop, measure_crop  # noqa: E402
from mottlewin import (BLUR_FRAC_MAX, WIN_MIN, mottle_win,  # noqa: E402
                       summarise_band)

ARMS = Path(r"C:\dev\strehl-out\BUILD-RECERT\arms")
LOGS = Path(r"C:\dev\strehl-out\BUILD-RECERT\logs")
BASE_ARM = "SC-BASE-bc6fa3c7"
CAND_ARMS = ["SC-NULL-bc6fa3c7", "SC-4-bc6fa3c7", "SC-8-bc6fa3c7",
             "SC-16-bc6fa3c7", "SC-RAMP-bc6fa3c7",
             "SC-D64-bc6fa3c7", "SC-D4096-bc6fa3c7"]
SCALES = {"SC-NULL-bc6fa3c7": "1,1,1,1,1,1,1", "SC-4-bc6fa3c7": "1,4,4,4,4,4,4",
          "SC-8-bc6fa3c7": "1,8,8,8,8,8,8", "SC-16-bc6fa3c7": "1,16,16,16,16,16,16",
          "SC-RAMP-bc6fa3c7": "1,1,4,16,32,32,32",
          "SC-D64-bc6fa3c7": "1,1,1,64,64,64,64",
          "SC-D4096-bc6fa3c7": "1,1,1,4096,4096,4096,4096"}
SUBJECTS = ["coffee-bubbles", "lead-1-cpl", "113MSDCF",
            "flat-on-ruler-cpl", "112MSDCF", "foam"]
CROPS = [(1200, 1200), (2400, 3600), (3600, 2000), (1600, 4800), (2800, 2400),
         (2000, 2800), (3200, 4000), (1400, 3000), (2600, 1600), (3000, 3400)]

# The range in which PAID_MAX has never been tested. ORCH asked for this to be
# named rather than resolved when an arm lands in it: PAID_MAX is 0.25 and the
# nearest measured blur population began at 0.406, so anything between is a
# value the commissioning has no evidence about in either direction.
PAID_UNTESTED = (0.25, 0.406)


def find(arm, subj):
    c = sorted((ARMS / arm).glob(f"{subj}--*.tiff"))
    return c[0] if c else None


def pair(a_path, b_path):
    a = tifffile.imread(str(a_path))
    b = tifffile.imread(str(b_path))
    out = {band: [] for band in BANDS}
    ident = ((0, 0), (1.0, 1.0, 1.0), (0.0, 0.0, 0.0))
    for (y, x) in CROPS:
        try:
            da = display_crop(a, y, x, *ident, 1.0, already_srgb=True)
            db = display_crop(b, y, x, *ident, 1.0, already_srgb=True)
        except ValueError:
            continue
        ma, mb = measure_crop(da), measure_crop(db)
        for band in BANDS:
            c = classify(ma[band], mb[band])
            out[band].append({"verdict": c["verdict"], "d_floor": c["d_floor"],
                              "d_structure": c["d_peak"], "paid": c["paid"],
                              "refused": c["refused"]})
    del a, b
    return out


def main():
    results, all_untested = {}, []
    for arm in CAND_ARMS:
        if not (ARMS / arm).exists():
            print(f"--- {arm}: NOT RENDERED, skipped")
            continue
        # A partial arm must never be scored as a full one. A `--only` run is
        # partial BY DESIGN with respect to the 26-subject corpus, so it writes
        # INCOMPLETE.txt and COMPLETE.txt is the wrong test here -- it is absent
        # on every targeted arm and would skip all of them. `finalpass.ps1`
        # seals each master with a sibling `.tiff.ok` when that subject finishes,
        # so the per-file seal is what completion means for a targeted arm.
        unsealed = [s for s in SUBJECTS
                    if (find(arm, s) is None
                        or not Path(str(find(arm, s)) + ".ok").exists())]
        if unsealed:
            print(f"--- {arm}: INCOMPLETE, {len(unsealed)} unsealed master(s) "
                  f"({', '.join(unsealed)}), skipped")
            continue
        print(f"\n=== {arm}   STREHL_GATE_FLOOR_SCALE={SCALES[arm]} ===")
        print(f"  {'subject':22s} {'band':7s} {'tst':>3s} {'ref':>3s} {'cln':>3s} "
              f"{'blr':>3s} {'d_floor':>9s} {'d_struct':>9s} {'paid':>7s}  verdict")
        arm_res = {}
        for subj in SUBJECTS:
            pa, pb = find(BASE_ARM, subj), find(arm, subj)
            if pa is None or pb is None:
                print(f"  {subj:22s} MISSING master")
                continue
            rows = pair(pa, pb)
            sub = {}
            for band in ("mottle", "struct", "grain"):
                s = summarise_band(rows[band])
                paid = [p for p in s["paid"] if p is not None]
                med_paid = float(np.median(paid)) if paid else None
                # Name, never resolve, a paid value in the untested gap.
                for p in paid:
                    if PAID_UNTESTED[0] <= p <= PAID_UNTESTED[1]:
                        all_untested.append((arm, subj, band, p))
                fired, line = (mottle_win(s) if band == "mottle" else (None, ""))
                sub[band] = {k: v for k, v in s.items() if k != "paid"}
                sub[band]["median_paid"] = med_paid
                sub[band]["mottle_win"] = fired
                sub[band]["mottle_line"] = line
                f = lambda v, p="%+.4f": (p % v) if v is not None else "        -"  # noqa: E731
                tag = ""
                if band == "mottle":
                    tag = "  WIN" if fired else "  " + line[:58]
                print(f"  {subj:22s} {band:7s} {s['tested']:3d} {s['refused']:3d} "
                      f"{s['cleaner']:3d} {s['blur_trade']:3d} "
                      f"{f(s['median_d_floor']):>9s} {f(s['median_d_structure']):>9s} "
                      f"{(('%7.3f' % med_paid) if med_paid is not None else '      -')}{tag}")
            arm_res[subj] = sub
        results[arm] = arm_res

    # ---- corpus-level verdict per arm, over the six subjects ---------------
    print("\n" + "=" * 100)
    print("PER-ARM SUMMARY over the six mottle-convicted subjects")
    print(f"  {'arm':20s} {'mottle wins':>11s} {'med d_floor':>12s} {'med d_struct':>12s} "
          f"{'med paid':>9s}  verdict")
    summary = {}
    for arm, arm_res in results.items():
        wins = sum(1 for s in arm_res.values() if s["mottle"]["mottle_win"])
        mf = [s["mottle"]["median_d_floor"] for s in arm_res.values()
              if s["mottle"]["median_d_floor"] is not None]
        ms = [s["struct"]["median_d_structure"] for s in arm_res.values()
              if s["struct"]["median_d_structure"] is not None]
        mp = [s["mottle"]["median_paid"] for s in arm_res.values()
              if s["mottle"]["median_paid"] is not None]
        # Two-sided and NaN-guarded: a NaN must not read as a win.
        med_f = float(np.median(mf)) if mf else float("nan")
        med_s = float(np.median(ms)) if ms else float("nan")
        med_p = float(np.median(mp)) if mp else float("nan")
        if wins == 0:
            v = "NO MOTTLE CLAIM"
        elif wins < len(arm_res):
            v = f"PARTIAL -- {wins}/{len(arm_res)} subjects"
        else:
            v = f"BETTER ON MOTTLE on all {wins} subjects"
        summary[arm] = {"wins": wins, "n": len(arm_res), "median_d_floor": med_f,
                        "median_d_structure_struct_band": med_s,
                        "median_paid": med_p, "verdict": v}
        g = lambda v: ("%+.4f" % v) if v == v else "     NaN"  # noqa: E731
        print(f"  {arm:20s} {wins:>6d}/{len(arm_res):<4d} {g(med_f):>12s} {g(med_s):>12s} "
              f"{(('%9.3f' % med_p) if med_p == med_p else '      NaN')}  {v}")

    print(f"\n  WIN_MIN={WIN_MIN}  BLUR_FRAC_MAX={BLUR_FRAC_MAX}")
    if all_untested:
        print(f"\n  *** {len(all_untested)} cell(s) landed `paid` in the UNTESTED range "
              f"{PAID_UNTESTED[0]}-{PAID_UNTESTED[1]}. PAID_MAX has no commissioning "
              f"evidence there, in either direction. Named, not resolved:")
        for arm, subj, band, p in all_untested[:20]:
            print(f"        {arm:20s} {subj:22s} {band:7s} paid {p:.3f}")
    else:
        print(f"\n  No cell landed `paid` in the untested {PAID_UNTESTED[0]}-"
              f"{PAID_UNTESTED[1]} range.")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "scalescore.json").write_text(json.dumps(
        {"summary": summary, "per_subject": results,
         "untested_paid": [{"arm": a, "subject": s, "band": b, "paid": p}
                           for a, s, b, p in all_untested]}, indent=1), encoding="utf-8")
    print(f"\n  wrote {LOGS / 'scalescore.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
