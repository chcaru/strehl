"""Tables and inline values for section 9.26, generated from the records.

Same contract as `vn_rep25.py` and `vn_rep2511.py`: nothing in the section is
typed by hand, and every inline value is anchored on a neighbouring literal so
that a presence check cannot be satisfied by a duplicate of the number
elsewhere in the file.

The ratios are emitted at FOUR decimals throughout, deliberately. At three,
`1.014` is a substring of `1.0148` and a presence check for the rogue step
would be satisfied by the worst null sitting two lines above it. That is the
short-token decoy defect this lane has already been bitten by once (`65x`
inside `3017665x`, section 9.25.11).

Records read:
  shipfr.json                 the CURRENT pin, --limit 44/45/46/47
  shipfr-pin-9b05d0b7.json    the archived run on the superseded pin
  shipalign.json              placed/refused for every aligned subject
"""
import io
import json
import os

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\dilute"
SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"

NEW_COMMIT = "9bbb7a1c"
OLD_COMMIT = "9b05d0b7"
UNREG = "highly-angled-ruler-mm-cpl"


def rec(name, where=OUT):
    p = os.path.join(where, name)
    if not os.path.exists(p):
        raise SystemExit("REFUSED: no record at %s" % p)
    return json.load(io.open(p, encoding="utf-8"))


def values():
    new = rec("shipfr.json")
    old = rec("shipfr-pin-9b05d0b7.json")
    al = rec("shipalign.json")

    if new["pin"] == old["pin"]:
        raise SystemExit("REFUSED: both arms carry pin %s -- the re-run did "
                         "not use a different binary, so it re-measures "
                         "nothing" % new["pin"][:16])

    v = {}
    v["new_sha"] = new["pin"][:16]
    v["old_sha"] = old["pin"][:16]
    v["new_commit"] = NEW_COMMIT
    v["old_commit"] = OLD_COMMIT
    for tag, r in (("new", new), ("old", old)):
        v[tag + "_rogue"] = "%.4f" % r["rogue_step"]
        v[tag + "_null"] = "%.4f" % r["worst_null"]
        v[tag + "_sep"] = "%.4f" % r["separation"]

    placed = sum(x["placed"] for x in al)
    refused = sum(x["refused"] for x in al)
    v["n_aligned"] = len(al)
    v["placed"] = "{:,}".format(placed)
    v["refused"] = refused
    v["unreg_frames"] = 299
    v["total_frames"] = "{:,}".format(placed + 299)
    v["n_total"] = len(al) + 1
    v["deepest"] = max(x["frames"] for x in al)

    ca = rec("clipaudit.json")
    s = ca["summary"]
    v["clip_files"] = s["blown"] + s["clean"] + s["unreadable"]
    v["clip_blown"] = s["blown"]
    v["clip_unread"] = s["unreadable"]
    v["worst_master"] = "%.2f" % s["worst_master"]
    wm = max(ca["masters"]["rows"], key=lambda r: r["clip_pct"])
    v["worst_master_subject"] = wm["file"].replace("--LIN.tiff", "")
    v["worst_head_render"] = "%.2f" % s["worst_head_render"]
    hm, om = s["head_median"], s["old_median"]
    v["median_gap"] = "%.3f" % (100.0 * max(
        abs(a - b) / b for a, b in zip(hm, om)))
    return v


def tables():
    new = rec("shipfr.json")
    old = rec("shipfr-pin-9b05d0b7.json")
    al = rec("shipalign.json")
    t = {}

    rows = ["| pin | commit | pyramid.rs at that commit | the accused step, L5 "
            "| worst null, L5 | separation |",
            "|---|---|---|---:|---:|---:|"]
    for tag, r, c, note in (("superseded", old, OLD_COMMIT, "as reported in 9.25.11"),
                            ("current", new, NEW_COMMIT, "re-measured here")):
        rows.append("| `%s` | `%s` | %s | %.4fx | %.4fx | %.4fx |"
                    % (r["pin"][:16], c, note,
                       r["rogue_step"], r["worst_null"], r["separation"]))
    t["pins"] = "\n".join(rows)

    rows = ["| frames stacked | one frame added | kind | L4 | L5 | L6 |",
            "|---|---|---|---:|---:|---:|"]
    for s in new["steps"]:
        rr = s["ratio"]
        kind = "**the accused**" if s["kind"] == "ROGUE" else "null"
        rows.append("| %d -> %d | `DSC%05d.ARW` | %s | %.4f | %.4f | %.4f |"
                    % (s["frm"], s["to"], s["to"], kind, rr[4], rr[5], rr[6]))
    t["steps"] = "\n".join(rows)

    deep = sorted(al, key=lambda x: -x["frames"])[:5]
    rows = ["| subject | frames | placed | refused |",
            "|---|---:|---:|---:|"]
    for x in deep:
        rows.append("| `%s` | %d | %d | **%d** |"
                    % (x["subject"], x["frames"], x["placed"], x["refused"]))
    rows.append("| `%s` | %d | *alignment REFUSED -- merged unregistered* | -- |"
                % (UNREG, 299))
    t["align"] = "\n".join(rows)
    return t


def logs_without_outlier_rejection():
    """Count shipping logs whose own header says outlier rejection is not applied.

    Re-derived from the logs on every run. Section 9.26.3 asserts this of all
    26, and an assertion in prose that no check reads back from the source is
    exactly what this lane exists to refuse.
    """
    import glob
    n = tot = 0
    for p in sorted(glob.glob(os.path.join(SHIP, "*.log"))):
        tot += 1
        t = io.open(p, encoding="utf-8", errors="replace").read()
        for line in t.splitlines():
            if "not applied" in line and "outlier rejection" in line:
                n += 1
                break
    return n, tot


def phrases():
    """The checkable inline units.

    Bare counts are NOT checkable: `299` is both the deepest stack and the
    unregistered subject's frame count and appears six times in the alignment
    table, and `0` appears in every `refused` cell. A presence check on either
    would be satisfied by a cell that has nothing to do with the sentence it is
    meant to be guarding. Each unit below is therefore a phrase carrying its own
    anchor, and the verifier requires each to occur EXACTLY ONCE.
    """
    v = values()
    return {
        "new_sha": v["new_sha"],
        "old_sha": v["old_sha"],
        "new_commit": "`%s`" % v["new_commit"],
        "old_commit": "`%s`" % v["old_commit"],
        "rogue_new": "%sx at L5 against a worst null of %sx"
                     % (v["new_rogue"], v["new_null"]),
        "rogue_old": "was %sx against %sx" % (v["old_rogue"], v["old_null"]),
        "sep_new": "separation %sx" % v["new_sep"],
        "refused": "%d refused out of %s frames placed"
                   % (v["refused"], v["placed"]),
        "aligned": "%d of the %d subjects" % (v["n_aligned"], v["n_total"]),
        "corpus": "%s frames" % v["total_frames"],
        "norej": "All %d logs state in their own header that outlier "
                 "rejection is `not applied`" % logs_without_outlier_rejection()[0],
        "conclusion": _conclusion(),
        "clip": "%d blown, %d unreadable, out of %d files examined"
                % (values()["clip_blown"], values()["clip_unread"],
                   values()["clip_files"]),
        "worst_master": "worst is `%s` at %s%%"
                        % (values()["worst_master_subject"],
                           values()["worst_master"]),
        "median_gap": "agree to %s%%" % values()["median_gap"],
        "head_clip": "read %s%% clipped" % values()["worst_head_render"],
        "case": _case(),
    }


def _case():
    """Which of ORCH's three cases this lane is in -- DERIVED, not asserted.

    If any render this lane produced at HEAD were blown, this sentence would
    have to change and the verifier would fail because the document would no
    longer contain the generated text.
    """
    s = rec("clipaudit.json")["summary"]
    if s["blown"] == 0 and s["unreadable"] == 0:
        return ("case 3: rendered at HEAD without `--auto-exposure`, and "
                "measured to be unclipped rather than assumed to be")
    return ("case 2: %d blown file(s) found in this lane's own evidence base"
            % s["blown"])


def _conclusion():
    """The section's conclusion sentence, DERIVED rather than asserted.

    If a single shipping log turned out to apply outlier rejection, this
    sentence would have to change, and the verifier would fail because the
    document would no longer contain the generated text. That is the point: the
    conclusion is not allowed to be typed independently of the measurement it
    rests on.
    """
    n, tot = logs_without_outlier_rejection()
    al = rec("shipalign.json")
    refused = sum(x["refused"] for x in al)
    if n == tot and refused == 0:
        return ("there is no stage anywhere in the shipping pipeline that "
                "would reject a badly-registered frame")
    return ("%d of %d logs apply outlier rejection and %d frames were refused, "
            "so the pipeline does screen frames" % (tot - n, tot, refused))


if __name__ == "__main__":
    v = values()
    for k in sorted(v):
        print("%-14s %s" % (k, v[k]))
    print()
    print("--- anchored phrases ---")
    for k, s in sorted(phrases().items()):
        print("%-11s %s" % (k, s))
    print()
    for k, s in sorted(tables().items()):
        print("--- %s ---" % k)
        print(s)
        print()
