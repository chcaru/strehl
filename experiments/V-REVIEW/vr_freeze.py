"""FREEZE the adjudicated numbers into experiments/V-REVIEW/vr_baseline.json.

Records, per adjudicated subject, exactly what section 1 of report.md ruled on:
the master statistic, the source-frame comparison value it was ruled against,
the ratio, and the one-line acquittal reason.  vr_recheck.py re-derives the
master half from a masters directory and reports whether the ruling still
stands.

The source half is FROZEN, not re-derived: re-deriving it costs a full re-render
of every source RAW through the pinned binary (hours).  vr_recheck.py prints
that scope limit on every run so a green light cannot be read as more than it is.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V

HERE = os.path.dirname(os.path.abspath(__file__))

# subject -> (flagged_for, one-line acquittal reason from report.md section 1)
RULING = {
    "112MSDCF": ("both",
        "band DN 0.946x source max; excess is the denominator (mean 0.922x); "
        "chroma absolute DN 0.919x, excess confined to darkest luminance decile"),
    "113MSDCF": ("both",
        "band DN 0.905x source max (mean 0.917x); chroma absolute DN 0.907x, "
        "d1 carries 31.8% of the excess"),
    "coffee-bubbles": ("both",
        "band DN 0.994x source max -- inside the +-17% frame-to-frame band "
        "spread; chroma 0.901x source max outright"),
    "couch-fibers-cpl": ("blotch",
        "master reads below the worst source frame outright (0.811x); band 0.830x"),
    "flat-on-ruler-cpl": ("blotch",
        "master reads below the worst source frame outright (0.921x); band 0.842x"),
    "flower-inner-edge-cpl": ("blotch",
        "band 0.972x; an independent all-in-focus composite of the same frames "
        "reads 0.12097, 1.22x the master"),
    "foam": ("both",
        "band DN 0.527x source max -- the merge halved it; chroma 0.880x outright"),
    "lead-1-cpl": ("chroma",
        "chroma 0.903x source max outright"),
    "leaf-2-cpl": ("chroma",
        "chroma 0.883x source max outright"),
    "109MSDCF": ("none (gate PASS control)",
        "control subject: gate PASSED it, yet its master reads 1.132x its own "
        "best source frame -- which is why the ratio is not a defect marker"),
}

# The gate's own rule, orch_blotch.py:197.  Frozen here so the checker states
# the criterion it applies rather than inventing one.
ELEVATED_X = 1.3
BLOTCH_REVIEW = 0.02
CHROMA_REVIEW = 0.015


def main():
    subjects = sys.argv[1:] or list(RULING)
    out = {"schema": "vr-baseline/1",
           "arm": V.ARM,
           "gate_rule": {"elevated_multiple": ELEVATED_X,
                         "blotch_review": BLOTCH_REVIEW,
                         "chroma_review": CHROMA_REVIEW,
                         "source_baseline": "max over registered source frames"},
           "provenance": {
               "binary": V.EXE,
               "statistics": "imported unmodified from orch_blotch.py / orch_chroma.py",
               "report": "experiments/V-REVIEW/report.md"},
           "subjects": {}}

    for s in subjects:
        p = os.path.join(V.OUT, "source_%s.json" % s)
        if not os.path.exists(p):
            print("SKIP %-22s no source_%s.json" % (s, s))
            continue
        d = json.load(open(p))
        ok = [r for r in d["rows"] if r["state"] == "OK"]
        m = d["master"]
        flagged, why = RULING[s]
        bM, bS = m["blotch"]["contrast"], d["src_blotch_max"]
        cM, cS = m["chroma"]["chroma"], d["src_chroma_max"]
        out["subjects"][s] = {
            "flagged_for": flagged,
            "verdict": "ACQUIT",
            "reason": why,
            "n_source_frames_registered": len(ok),
            "master": {
                "blotch": round(bM, 8), "blotch_band_dn": round(m["blotch"]["band"], 4),
                "blotch_mean_dn": round(m["blotch"]["mean"], 4),
                "blotch_window_yx": [m["blotch"]["y"], m["blotch"]["x"]],
                "chroma": round(cM, 9),
                "chroma_window_yx": [m["chroma"]["y"], m["chroma"]["x"]],
            },
            "source_frame_max": {"blotch": round(bS, 8), "chroma": round(cS, 9),
                                 "blotch_band_dn": round(max(r["band"] for r in ok), 4)},
            "ratio": {"blotch": round(bM / bS, 5), "chroma": round(cM / cS, 5),
                      "blotch_band_dn": round(m["blotch"]["band"] / max(r["band"] for r in ok), 5)},
        }
        print("froze %-22s blotch %.5f (r %.3f)  chroma %.6f (r %.3f)"
              % (s, bM, bM / bS, cM, cM / cS))

    dst = os.path.join(HERE, "vr_baseline.json")
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print("\nwrote %s  (%d subjects)" % (dst, len(out["subjects"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
