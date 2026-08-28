r"""The hull ladder: measure every rendered subject and test ORCH's predictions.

Sites are chosen ONCE, from the `inputrange` arm, and reused unchanged in every
arm. Reselecting a population per arm is the defect that made an earlier rim
instrument in this lane score a blurred image as ringing more than the master.

P1  PerLevel reduces manufactured detail on the excess subjects  -> band ratio < 1
P2  PerLevel is inert where frames agree (the controls)          -> band ratio == 1
P3  Unclamped raises it                                          -> band ratio > 1

P3 is the potency arm and is reported first. A reduction measured by a gauge
that never demonstrated sensitivity to this axis is not a result.

Every reduction is quoted WITH its acuity ratio on the same pixels, because a
mode that lowers manufactured detail by softening the image has paid for it and
the trade is the finding, not a footnote.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402
import hul_measure as hm                                           # noqa: E402
from lad_measure import finite, WIN                                # noqa: E402

RENDER = os.path.join(HERE, "hull-render.json")
OUT = os.path.join(HERE, "hull.json")
# Byte-identical floor for this gauge: NULL in hul_commission.py gives exactly
# 1.0, so the floor is 0. Any departure from 1.0 is real. A separate question is
# whether it is LARGE, which is what these bands are for.
INERT_BAND = 0.005          # +/-0.5%: what "inert" is allowed to mean


def zero_shift_agreement(ref, arm, sites, half=192):
    """Are the two arms on the same pixel grid? Measured, never assumed."""
    rs = []
    H, W = ref.shape
    for s in sites:
        cy, cx = s["y"] + WIN // 2, s["x"] + WIN // 2
        y0, x0 = max(0, cy - half), max(0, cx - half)
        y1, x1 = min(H, cy + half), min(W, cx + half)
        a, b = ref[y0:y1, x0:x1].ravel(), arm[y0:y1, x0:x1].ravel()
        if a.size != b.size or a.size == 0:
            continue
        sa, sb = float(np.std(a)), float(np.std(b))
        if sa <= 0 or sb <= 0:
            continue
        rs.append(float(np.corrcoef(a, b)[0, 1]))
    return rs


def main():
    # Subjects come from what is ON DISK, not from hull-render.json, which
    # hul_run.py only writes after the LAST subject finishes. Reading the
    # manifest instead made this report examine 0 subjects, sum its partition
    # to 0 == 0, and print "the gauge is NOT sensitive to the hull axis" from
    # n = 0 -- a conclusion manufactured out of no data.
    import hul_run                                                 # noqa: E402
    meta = json.load(open(RENDER)) if os.path.exists(RENDER) else {}
    known = {s: {"prior_excess": p, "control": c} for s, p, c in hul_run.SUBJECTS}
    subjects = [s for s, _, _ in hul_run.SUBJECTS
                if os.path.exists(hm.arm_path(s, "inputrange"))]
    for s in subjects:
        meta.setdefault(s, {}).update(
            {k: v for k, v in known[s].items() if k not in meta.get(s, {})})
        meta[s].setdefault("clamp", {})
    subjects.sort(key=lambda s: -abs(meta[s].get("prior_excess", 0)))
    if not subjects:
        raise SystemExit("NOT EXAMINED: no subject has an inputrange arm on disk. "
                         "Refusing to print verdicts from an empty population.")

    results = {}
    print("=" * 104)
    print("HULL LADDER  --  paired arm ratios at frozen sites, entirely within blend-render")
    print("  band   = DoG(1.0-2.5) contrast / local mean   (manufactured detail)")
    print("  acuity = p99.5|grad| / local mean             (sharpness, same pixels)")
    print("=" * 104)
    hdr = ("%-24s %5s   %-19s %-19s   %-19s %-19s"
           % ("subject", "n", "perlevel band", "perlevel acuity",
              "unclamped band", "unclamped acuity"))
    print(hdr)

    partition = {"measured": 0, "incomplete": 0, "refused": 0}
    for sub in subjects:
        paths = {a: hm.arm_path(sub, a) for a in hm.ARMS}
        if not all(os.path.exists(p) for p in paths.values()):
            partition["incomplete"] += 1
            print("%-24s %5s   %s" % (sub, "-", "INCOMPLETE: an arm has not rendered"))
            continue
        ref, lat = hm.load_lum(paths["inputrange"])
        sites = hm.pick_sites(ref, n=48)
        if not sites:
            partition["refused"] += 1
            print("%-24s %5s   %s" % (sub, 0, "REFUSED: no admissible site"))
            del ref
            continue
        base = hm.measure(ref, sites)
        rec = {"n_sites": len(sites), "lattice": list(lat),
               "control": meta[sub].get("control"), "prior": meta[sub].get("prior_excess"),
               "clamp": meta[sub].get("clamp", {}), "arms": {}}
        cells = []
        for arm in ("perlevel", "unclamped"):
            lum, lat2 = hm.load_lum(paths[arm])
            if tuple(lat2) != tuple(lat):
                rec["arms"][arm] = {"why": "lattice mismatch %s vs %s" % (lat2, lat)}
                cells += ["LATTICE MISMATCH", ""]
                del lum
                continue
            rs = zero_shift_agreement(ref, lum, sites[:12])
            rows = hm.measure(lum, sites)
            rb, ref_b = hm.ratios(base, rows, "band")
            ra, ref_a = hm.ratios(base, rows, "acuity")
            sb, sa_ = hm.summarise(rb), hm.summarise(ra)
            rec["arms"][arm] = {"band": sb, "acuity": sa_, "refused_band": ref_b,
                                "refused_acuity": ref_a,
                                "zero_shift_r_min": min(rs) if rs else None,
                                "zero_shift_r_median": float(np.median(rs)) if rs else None}
            cells.append("%.4f [%.4f,%.4f]" % (sb["median"], sb["min"], sb["max"])
                         if sb["median"] is not None else "REFUSED")
            cells.append("%.4f" % sa_["median"] if sa_["median"] is not None else "REFUSED")
            del lum
        del ref
        partition["measured"] += 1
        results[sub] = rec
        mark = "*" if rec["control"] else " "
        print("%-24s%s%4d   %-19s %-19s   %-19s %-19s"
              % (sub, mark, len(sites), cells[0], cells[1], cells[2], cells[3]))

    print("  * = negative control (was WITHIN its ceiling on the exponent ladder)")
    print("  band/acuity cells are MEDIAN ratio vs the inputrange arm; [min,max] over sites")

    # ---- registration ----------------------------------------------------
    print("\n=== ARE THE ARMS ON THE SAME PIXELS? (zero shift, no registration) ===")
    for sub, rec in results.items():
        for arm, a in rec["arms"].items():
            if a.get("zero_shift_r_median") is not None:
                print("  %-24s %-10s r min %.4f  median %.4f"
                      % (sub, arm, a["zero_shift_r_min"], a["zero_shift_r_median"]))

    # ---- predictions -----------------------------------------------------
    print("\n=== P3 (POTENCY, read first): does --unclamped RAISE manufactured detail? ===")
    up = dn = 0
    for sub, rec in results.items():
        m = rec["arms"].get("unclamped", {}).get("band", {}).get("median")
        if not finite(m):
            continue
        verdict = "RAISES" if m > 1 + INERT_BAND else ("LOWERS" if m < 1 - INERT_BAND else "flat")
        up += m > 1 + INERT_BAND
        dn += m < 1 - INERT_BAND
        print("  %-24s band ratio %.4f  %s" % (sub, m, verdict))
    n_p3 = up + dn
    if n_p3 == 0:
        print("  -> NOT EXAMINED: no admissible unclamped measurement. No sensitivity")
        print("     verdict is available, and 'flat' is NOT one. Refusing to conclude.")
    else:
        print("  -> %d raise, %d lower, over %d measured subjects. The gauge IS"
              % (up, dn, n_p3))
        print("     sensitive to the hull axis.")

    print("\n=== P1: does --per-level REDUCE manufactured detail on the excess subjects? ===")
    for sub, rec in results.items():
        if rec["control"]:
            continue
        b = rec["arms"].get("perlevel", {}).get("band", {}).get("median")
        a = rec["arms"].get("perlevel", {}).get("acuity", {}).get("median")
        if not finite(b, a):
            print("  %-24s REFUSED" % sub)
            continue
        print("  %-24s band %.4f (%+.2f%%)   acuity %.4f (%+.2f%%)   %s"
              % (sub, b, 100 * (b - 1), a, 100 * (a - 1),
                 "reduces" if b < 1 - INERT_BAND else
                 ("RAISES" if b > 1 + INERT_BAND else "flat")))

    print("\n=== P2: is --per-level INERT on the negative controls? ===")
    print("  NOTE: hul_potency.py has already shown --per-level moves 3.79-17.47%% of")
    print("  samples, far above the 0.008%% that made hull_lambda 'wired and inert'.")
    print("  So a flat reading here is inertness OF THE STATISTIC, not dead plumbing.")
    for sub, rec in results.items():
        if not rec["control"]:
            continue
        b = rec["arms"].get("perlevel", {}).get("band", {}).get("median")
        a = rec["arms"].get("perlevel", {}).get("acuity", {}).get("median")
        if not finite(b, a):
            print("  %-24s REFUSED" % sub)
            continue
        print("  %-24s band %.4f (%+.2f%%)   acuity %.4f (%+.2f%%)   %s"
              % (sub, b, 100 * (b - 1), a, 100 * (a - 1),
                 "INERT" if abs(b - 1) <= INERT_BAND else "NOT INERT"))

    total = sum(partition.values())
    print("\n=== COUNTED PARTITION ===")
    for k, v in partition.items():
        print("  %-36s: %d" % (k, v))
    print("  %-36s: %d %s" % ("TOTAL", total, "OK" if total == len(subjects) else "MISMATCH"))
    if total != len(subjects):
        raise SystemExit("partition does not sum")
    if partition["measured"] == 0:
        raise SystemExit("partition sums but NOTHING WAS MEASURED -- a total that "
                         "balances at zero is not a pass")

    json.dump(results, open(OUT, "w"), indent=1)
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()

