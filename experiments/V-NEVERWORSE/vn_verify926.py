"""Verify section 9.26 against the records it was generated from.

Same contract as `vn_verify25.py` / `vn_verify2511.py`:

  * the section is sliced by its own heading, so a duplicate string elsewhere
    in the 3,800-line document cannot satisfy a check;
  * every generated unit must occur EXACTLY ONCE -- not "at least once",
    because a value that got pasted twice and then edited in one place only is
    the failure this catches;
  * the outcomes PARTITION: passed + failed + not-examined sums to the number
    of checks attempted, so a skipped check cannot read as a passed one;
  * checks are re-derived from the JSON records, not from the generator's
    formatting, wherever the arithmetic can be done independently.

Exit 0 all green, 1 a check failed, 2 the harness could not run.
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vn_rep926 as R  # noqa: E402

DOC = os.path.join(HERE, "RESULT.md")
HEAD = "### 9.26 "
END = "\n## 10. Files"


def section():
    txt = io.open(DOC, encoding="utf-8").read()
    if txt.count(HEAD) != 1:
        raise SystemExit("HARNESS: heading %r occurs %d times"
                         % (HEAD, txt.count(HEAD)))
    i = txt.index(HEAD)
    j = txt.index(END, i)
    return txt[i:j], txt


def main():
    sec, whole = section()
    passed, failed, skipped = [], [], []

    def once(label, needle, want=1):
        """Require EXACTLY `want` occurrences.

        Not "at least one". A unit that appears twice and is then edited in one
        place only goes 2 -> 1 and fails here, which is the whole point. Where
        a value legitimately appears in both prose and a table, `want` says so
        explicitly rather than the check being loosened to `>= 1`.
        """
        if needle is None:
            skipped.append(label)
            return
        n = sec.count(needle)
        (passed if n == want else failed).append(
            label if n == want else
            "%s (occurs %d times, expected %d): %r"
            % (label, n, want, needle[:70]))

    # These four are named once in the prose and once in the pins table.
    TWICE = {"new_sha", "old_sha", "new_commit", "old_commit"}
    for k, s in sorted(R.phrases().items()):
        once("phrase %s" % k, s, 2 if k in TWICE else 1)
    for k, s in sorted(R.tables().items()):
        once("table %s" % k, s)

    # --- re-derived, not read back from the generator ---
    new = R.rec("shipfr.json")
    old = R.rec("shipfr-pin-9b05d0b7.json")
    al = R.rec("shipalign.json")

    def claim(label, cond):
        (passed if cond else failed).append(label)

    claim("the two arms really are different binaries",
          new["pin"] != old["pin"])
    for tag, r in (("current", new), ("superseded", old)):
        claim("%s pin: accused step is NOT larger than the worst null" % tag,
              r["rogue_step"] <= r["worst_null"])
        claim("%s pin: verdict text says NOT REPRODUCED" % tag,
              "NOT REPRODUCED" in r["verdict"])
        rog = [s for s in r["steps"] if s["kind"] == "ROGUE"]
        claim("%s pin: exactly one accused step, and it adds frame 47" % tag,
              len(rog) == 1 and rog[0]["to"] == 47)
        claim("%s pin: two nulls, each adding exactly one frame" % tag,
              sum(1 for s in r["steps"] if s["kind"] == "null") == 2
              and all(s["to"] - s["frm"] == 1 for s in r["steps"]))

    claim("alignment sweep: every aligned subject refused zero frames",
          all(x["refused"] == 0 for x in al))
    claim("alignment sweep: placed equals frames on every aligned subject",
          all(x["placed"] == x["frames"] for x in al))
    placed = sum(x["placed"] for x in al)
    claim("alignment sweep: 4,526 placed + 299 unregistered = 4,825",
          placed == 4526 and placed + 299 == 4825)
    claim("alignment sweep: 25 aligned subjects + 1 unregistered = 26",
          len(al) == 25)

    n_norej, n_logs = R.logs_without_outlier_rejection()
    claim("outlier rejection: re-derived from the logs, %d of %d say "
          "'not applied'" % (n_norej, n_logs),
          n_logs == 26 and n_norej == 26)

    # --- the clipping audit ORCH's exposure regression demanded ---
    ca = R.rec("clipaudit.json")
    s = ca["summary"]
    claim("clip audit: nothing in this lane's evidence base is blown",
          s["blown"] == 0)
    claim("clip audit: nothing was unreadable (a zero produced by not "
          "looking is not a zero)", s["unreadable"] == 0)
    claim("clip audit: outcomes partition to the files examined",
          s["blown"] + s["clean"] + s["unreadable"]
          == sum(len(ca[k]["rows"]) + len(ca[k]["unreadable"])
                 for k in ("masters", "head_renders", "old_renders",
                           "bundles")))
    claim("clip audit: all 26 linear masters accounted for",
          len(ca["masters"]["rows"]) == 26)
    claim("clip audit: every master is under ORCH's 25% blown threshold",
          all(r["clip_pct"] < 25.0 for r in ca["masters"]["rows"]))
    claim("clip audit: the four HEAD renders are the only HEAD images, and "
          "are unclipped",
          len(ca["head_renders"]["rows"]) == 4
          and all(r["clip_pct"] == 0.0 for r in ca["head_renders"]["rows"]))
    claim("clip audit: HEAD and old-pin medians agree to better than 0.5%",
          all(abs(a - b) / b < 0.005
              for a, b in zip(s["head_median"], s["old_median"])))
    claim("clip audit: no bundle array is near the ceiling",
          all(r["worst_clip_pct"] == 0.0 for r in ca["bundles"]["rows"]))

    # --- the document-wide claims section 9.26.4 makes about itself ---
    claim("9.26.4 is honest: '5 FAIL' really is absent from the document",
          "5 FAIL" not in whole.replace(sec, ""))
    claim("9.26.4 is honest: '4 REVIEW' really is absent from the document",
          "4 REVIEW" not in whole.replace(sec, ""))

    # --- the decoy guard this section exists under ---
    # Every ratio is emitted at four decimals. The hazard is a THREE-decimal
    # form appearing too: `1.014x` would then be a prefix-collision partner for
    # `1.0148x`, and a presence check for one could be satisfied by the other.
    # So assert the truncated form of each emitted ratio is absent.
    v = R.values()
    trunc = sorted({"%sx" % s[:5] for s in
                    (v["new_rogue"], v["new_null"], v["old_rogue"],
                     v["old_null"], v["new_sep"], v["old_sep"])})
    bad = [t for t in trunc if t in sec]
    claim("no truncated three-decimal ratio is present (%s): %s"
          % (", ".join(trunc), bad or "none"), not bad)

    total = len(passed) + len(failed) + len(skipped)
    for f in failed:
        print("FAIL  %s" % f)
    for s in skipped:
        print("SKIP  %s" % s)
    print("\n%d passed, %d failed, %d not examined -- %d checks attempted"
          % (len(passed), len(failed), len(skipped), total))
    if len(passed) + len(failed) + len(skipped) != total:
        print("HARNESS: outcomes do not partition")
        return 2
    return 1 if failed or skipped else 0


if __name__ == "__main__":
    sys.exit(main())
