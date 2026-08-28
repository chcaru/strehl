r"""V-ADJ13: freeze the 13 re-adjudicated subjects into the gate's baseline.

`orch_printready.py` reads its acquittal records from
experiments/V-REVIEW/vr_baseline.json and from nowhere else. An adjudication
that is not written there is an opinion in a document; written there, it is the
gate's own verdict on the next run. This merges the 13 records produced by
vadj_source.py into that file, in the format vr_freeze.py established.

Two rules this script obeys, both of them the reason it exists as a script and
not as a hand edit:

  * The ten SHIP-V3 records already in the file are preserved. Six of them are
    for subjects I re-adjudicated; those are not deleted but carried inside the
    new record as `superseded_record`, verbatim, together with the reason the
    old one expired. A baseline that forgets what it used to say cannot be
    audited, and the expiry mechanism exists precisely so that nobody has to
    trust an unexamined number.
  * Nothing in `gate_rule` is touched. Not ACQUIT_TOL, not elevated_multiple,
    not the review thresholds -- those live in the gate and in this rule block,
    and moving either to clear a subject is the one edit that would make this
    lane worthless.

The file is copied to %TEMP% before it is written, because `git checkout --`
is forbidden on this tree and a bad write must be recoverable without it.

usage: python vadj_freeze.py [--write] [--scoped-copy]
"""
import datetime
import json
import os
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
BASELINE = HERE.parent / "V-REVIEW" / "vr_baseline.json"
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\V-ADJ13")

BLOTCH_REVIEW = 0.02
CHROMA_REVIEW = 0.015
ELEVATED = 1.3

# Why each of the six acquittals expired, as the gate reported it, and what the
# master-only probe (vadj_master.py) measured at the OLD window. Banked here so
# the record carries the finding and not just the number.
EXPIRY = {
    "112MSDCF": ("chroma 0.03485 -> 0.02896 (16.9% > 5%)",
                 "MIXED: chroma window moved 872 px (2616,1458)->(1744,1458); at the "
                 "recorded window today's master reads 0.03268, -6.23%, so ~6% is a "
                 "same-window move and the other ~11% is the window. Gate could not "
                 "say so: verdict() never puts chroma_window_yx in meas."),
    "113MSDCF": ("chroma 0.02538 -> 0.02395 (5.6% > 5%)",
                 "RENDER CHANGE: chroma window unchanged (1744,1458); at that window "
                 "today's master reads 0.02395, -5.64%. Not a window move. Direction "
                 "is an improvement."),
    "coffee-bubbles": ("blotch window [38, 14] -> [54, 14]",
                       "WINDOW MOVE: at the recorded window today's master reads "
                       "0.09900 vs 0.09892 recorded, +0.08%."),
    "couch-fibers-cpl": ("blotch window [558, 6110] -> [3422, 2334]",
                         "WINDOW MOVE: at the recorded window today's master reads "
                         "0.04508 vs 0.04512 recorded, -0.09%."),
    "flower-inner-edge-cpl": ("blotch window [3670, 3150] -> [3710, 3150]",
                              "WINDOW MOVE: at the recorded window today's master reads "
                              "0.09979 vs 0.09922 recorded, +0.58%."),
    "foam": ("chroma 0.03250 -> 0.03065 (5.7% > 5%)",
             "WINDOW MOVE: chroma window moved 872 px (872,2916)->(0,2916); at the "
             "recorded window today's master reads 0.03212, -1.19%, inside tolerance. "
             "The gate printed this as value drift because verdict() never puts "
             "chroma_window_yx in meas, so check_acquittal's moved-window branch "
             "cannot fire for chroma."),
}


def g(x):
    """8 significant figures, as a float. Matches the existing records' width."""
    return float("%.8g" % float(x))


def flagged_for(blotch, chroma):
    hi = []
    if blotch > BLOTCH_REVIEW:
        hi.append("blotch")
    if chroma > CHROMA_REVIEW:
        hi.append("chroma")
    if len(hi) == 2:
        return "both"
    return hi[0] if hi else "none"


def build(doc):
    old_subs = doc.get("subjects") or {}
    made = []
    for p in sorted(SCRATCH.glob("source_*.json")):
        d = json.load(open(p, encoding="utf-8"))
        subj, m = d["subject"], d["master"]
        rat = d["ratio"]
        flag = flagged_for(m["blotch"], m["chroma"])
        worst = max(rat["blotch"], rat["chroma"])
        reason = (
            "blotch %.3fx source max (band DN %.3fx; the window's own mean DN is "
            "%.3fx the source median, so the excess sits in the denominator), "
            "chroma %.3fx source max; worst statistic %.3fx of the frames the "
            "master was built from, under the %.1fx elevated multiple. "
            "%d of %d sampled frames registered at NCC >= %.2f."
            % (rat["blotch"], rat["blotch_band_dn"],
               m["blotch_mean_dn"] / d["src_mean_med"], rat["chroma"], worst,
               ELEVATED, d["n_ok"], len(d["rows"]), d["ncc_min"]))
        rec = {
            "flagged_for": flag,
            "verdict": "ACQUIT",
            "reason": reason,
            "n_source_frames_registered": d["n_ok"],
            "master": {
                "blotch": g(m["blotch"]),
                "blotch_band_dn": g(m["blotch_band_dn"]),
                "blotch_mean_dn": g(m["blotch_mean_dn"]),
                "blotch_window_yx": list(m["blotch_window_yx"]),
                "chroma": g(m["chroma"]),
                "chroma_window_yx": list(m["chroma_window_yx"]),
            },
            "source_frame_max": {
                "blotch": g(d["src_blotch_max"]),
                "blotch_band_dn": g(d["src_band_max"]),
                "chroma": g(d["src_chroma_max"]),
            },
            "ratio": {
                "blotch": g(rat["blotch"]),
                "blotch_band_dn": g(rat["blotch_band_dn"]),
                "chroma": g(rat["chroma"]),
            },
            # --- keys below are V-ADJ13 additions; the gate ignores them -----
            "adjudicated_by": "V-ADJ13",
            "arm": d["arm"],
            "binary": d["exe"],
            "binary_sha256": d["exe_sha256"],
            "master_sha256": d["master_sha256"],
            "report": "docs/research/V-ADJ13.md",
            "source_frame_argmax": {"blotch": d["src_blotch_argmax"],
                                    "chroma": d["src_chroma_argmax"]},
            "source_frames_available": d["n_frames"],
            "source_frames_sampled": len(d["rows"]),
            "master_cover": g(d["master_cover"]),
            "master_cover_source": d["master_cover_source"],
            "ratio_vs_median_source": {
                "blotch": g(rat["blotch_vs_median_source"]),
                "chroma": g(rat["chroma_vs_median_source"]),
            },
        }
        prev = old_subs.get(subj)
        if prev is not None and prev.get("adjudicated_by") == "V-ADJ13":
            # Re-running --write must not nest this lane's own record inside
            # itself: the SHIP-V3 record it superseded would sink a level on
            # every run and the file would stop being readable as history.
            # Carry the original supersession forward unchanged instead.
            if "superseded_record" in prev:
                rec["superseded_record"] = prev["superseded_record"]
        elif prev is not None:
            gate_said, finding = EXPIRY.get(subj, ("(not expired)", ""))
            rec["superseded_record"] = {
                "arm": doc.get("arm"),
                "binary": (doc.get("provenance") or {}).get("binary"),
                "report": (doc.get("provenance") or {}).get("report"),
                "gate_expiry_reason": gate_said,
                "v_adj13_finding": finding,
                "record": prev,
            }
        made.append((subj, rec))
    return made


def main(argv):
    write = "--write" in argv
    doc = json.load(open(BASELINE, encoding="utf-8"))

    if "--scoped-copy" in argv:
        # A self-check scope, not a gate input: vr_recheck.py's --only filters
        # its master re-derivation but hands bind_report the WHOLE baseline, so
        # binding this lane's report against the shared store reports V-REVIEW's
        # own subjects as unstated. Pointing --baseline at this copy scopes both
        # halves to the 13 subjects this lane adjudicated.
        mine = {p.name[len("source_"):-len(".json")]
                for p in SCRATCH.glob("source_*.json")}
        scoped = dict(doc)
        scoped["subjects"] = {k: v for k, v in (doc.get("subjects") or {}).items()
                              if k in mine}
        scoped["arm"] = ("DELIVER-V6 (13 subjects, V-ADJ13) -- SCOPED COPY of "
                         "vr_baseline.json, read by no gate")
        out = SCRATCH / "vr_baseline_vadj13.json"
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(scoped, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("scoped copy -> %s (%d of %d subjects)"
              % (out, len(scoped["subjects"]), len(doc.get("subjects") or {})))
        if not write:
            return 0

    before = sorted((doc.get("subjects") or {}).keys())
    made = build(doc)
    if len(made) != 13:
        sys.exit("expected 13 source_*.json in %s, found %d" % (SCRATCH, len(made)))

    print("baseline %s" % BASELINE)
    print("  before: %d subject(s): %s" % (len(before), ", ".join(before)))
    print("  adding/updating %d:" % len(made))
    for subj, rec in made:
        print("    %-30s %-6s %-7s blotch %.3fx chroma %.3fx  %s"
              % (subj, rec["flagged_for"], rec["verdict"], rec["ratio"]["blotch"],
                 rec["ratio"]["chroma"],
                 "SUPERSEDES SHIP-V3 record" if "superseded_record" in rec else "new"))
    doc.setdefault("subjects", {}).update(dict(made))
    doc["arm"] = "SHIP-V3 (10 subjects, V-REVIEW) + DELIVER-V6 (13 subjects, V-ADJ13)"
    prov = doc.setdefault("provenance", {})
    prov["binary_v_adj13"] = (r"C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe"
                              " sha256 2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7")
    prov["report_v_adj13"] = "docs/research/V-ADJ13.md"
    after = sorted(doc["subjects"].keys())
    print("  after:  %d subject(s)" % len(after))
    for k in before:
        if k not in after:
            sys.exit("REFUSING: would drop existing record %s" % k)

    if not write:
        print("\nDRY RUN. Re-run with --write to commit this to disk.")
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = pathlib.Path(os.environ["TEMP"]) / ("vr_baseline.%s.bak.json" % stamp)
    shutil.copy2(BASELINE, backup)
    print("\nbacked up to %s" % backup)
    with open(BASELINE, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %s (%d bytes)" % (BASELINE, BASELINE.stat().st_size))
    json.load(open(BASELINE, encoding="utf-8"))
    print("re-read OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
