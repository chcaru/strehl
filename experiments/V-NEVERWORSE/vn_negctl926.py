"""Negative control for section 9.26: plant defects, require the verifier to catch each.

A verifier that has never failed is not evidence. This plants defects of both
kinds:

  * DOCUMENT plants -- corrupt a value in RESULT.md. Catches a verifier that
    checks the generator against itself and never reads the document.
  * RECORD plants -- corrupt the JSON the section was generated from. Catches a
    verifier that hardcodes the answer it is supposed to be deriving. This is
    the arm that matters: 24 of the 29 checks re-derive from the records, and
    if they did not, this arm would stay green.

Plus two arms that are not defects:

  * a PLACEBO edit that must stay GREEN, so the harness is not simply failing
    on any modification whatsoever;
  * a REFUSAL arm -- an unreadable record must make the harness exit non-zero
    with a harness error, not silently report zero checks and pass.

Every mutation is anchored on a unique string and hard-errors if it does not
land. A plant that silently fails to apply produces a green run that looks
exactly like a caught defect. This lane has been bitten by that before.

Exit 0 when every plant behaved.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vn_rep926 as R  # noqa: E402

DOC = os.path.join(HERE, "RESULT.md")
OUT = R.OUT
VERIFY = os.path.join(HERE, "vn_verify926.py")
RECORDS = ["shipfr.json", "shipfr-pin-9b05d0b7.json", "shipalign.json",
           "clipaudit.json"]


def run():
    p = subprocess.run([sys.executable, VERIFY], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def bounds(txt):
    i = txt.index("### 9.26 ")
    return i, txt.index("\n## 10. Files", i)


def mutate_doc(anchor, replacement, want=1):
    """Replace inside SECTION 9.26 only.

    The verifier slices the section before counting, so a plant that counts
    document-wide is measuring a different quantity: `9b05d0b7` occurs seven
    times in the whole file and twice in this section. Anchoring on the whole
    document would either refuse to land or corrupt another section.
    """
    txt = io.open(DOC, encoding="utf-8").read()
    i, j = bounds(txt)
    sec = txt[i:j]
    n = sec.count(anchor)
    if n != want:
        raise SystemExit("PLANT DID NOT LAND: anchor occurs %d times in "
                         "section 9.26 (expected %d): %r"
                         % (n, want, anchor[:80]))
    newsec = sec.replace(anchor, replacement, 1)
    # Prove the plant actually damaged the checked property. A mutation that
    # leaves the original still present -- `s + "X"` is the classic -- produces
    # a green run indistinguishable from a caught defect.
    if newsec.count(anchor) != want - 1:
        raise SystemExit("PLANT IS INERT: after mutation the anchor still "
                         "occurs %d times (expected %d): %r"
                         % (newsec.count(anchor), want - 1, anchor[:80]))
    io.open(DOC, "w", encoding="utf-8", newline="").write(
        txt[:i] + newsec + txt[j:])


def bump(s):
    """Perturb a string so the ORIGINAL IS NO LONGER A SUBSTRING of the result.

    The obvious `s + "X"` is inert: the original still occurs inside the
    mutated text, a presence check still finds it, and the plant reports a
    green run that looks exactly like a caught defect. That is how this
    function was first written and the `conclusion` plant caught it.
    """
    for i in range(len(s) - 1, -1, -1):
        if s[i].isdigit():
            return s[:i] + ("0" if s[i] != "0" else "1") + s[i + 1:]
    for i in range(len(s) - 1, -1, -1):
        if s[i].isalpha():
            return s[:i] + ("q" if s[i].lower() != "q" else "z") + s[i + 1:]
    raise SystemExit("PLANT COULD NOT BE BUILT: nothing to perturb in %r" % s)


def main():
    tmp = tempfile.mkdtemp(prefix="vn926-")
    shutil.copy2(DOC, os.path.join(tmp, "RESULT.md"))
    for r in RECORDS:
        shutil.copy2(os.path.join(OUT, r), os.path.join(tmp, r))

    def restore():
        shutil.copy2(os.path.join(tmp, "RESULT.md"), DOC)
        for r in RECORDS:
            shutil.copy2(os.path.join(tmp, r), os.path.join(OUT, r))

    behaved, misbehaved = [], []

    def expect(label, want_rc, note=""):
        rc, _out = run()
        ok = (rc != 0) if want_rc == "nonzero" else (rc == want_rc)
        (behaved if ok else misbehaved).append(
            "%s%s" % (label, "" if ok else "  [rc=%d, wanted %s]"
                      % (rc, want_rc)))
        restore()

    try:
        rc, out = run()
        if rc != 0:
            print("HARNESS: verifier is not green before planting:\n%s" % out)
            return 2

        # ---- DOCUMENT plants -------------------------------------------
        ph = R.phrases()
        TWICE = {"new_sha", "old_sha", "new_commit", "old_commit"}
        for k, s in sorted(ph.items()):
            if k in TWICE:
                continue          # anchored twice; handled below
            mutate_doc(s, bump(s))
            expect("doc plant: phrase %s corrupted" % k, "nonzero")

        for k in sorted(TWICE):
            s = ph[k]
            # corrupt ONE of the two copies: the count goes 2 -> 1 and the
            # exact-count check must notice. This is the defect a ">= 1"
            # presence check would sail straight past.
            mutate_doc(s, bump(s), want=2)
            expect("doc plant: %s corrupted in ONE of its two sites" % k,
                   "nonzero")

        for k, s in sorted(R.tables().items()):
            first = s.split("\n")[2]
            mutate_doc(first, bump(first))
            expect("doc plant: table %s first data row corrupted" % k,
                   "nonzero")

        mutate_doc("no stage anywhere in the shipping pipeline",
                   "every stage in the shipping pipeline")
        expect("doc plant: the outlier-rejection claim inverted", "nonzero")

        # ---- RECORD plants (the oracle arm) -----------------------------
        def edit(rec, fn):
            p = os.path.join(OUT, rec)
            d = json.load(io.open(p, encoding="utf-8"))
            fn(d)
            json.dump(d, io.open(p, "w", encoding="utf-8"), default=float,
                      indent=1)

        def flip_rogue(d):
            d["rogue_step"] = d["worst_null"] * 1.5
        edit("shipfr.json", flip_rogue)
        expect("record plant: accused step made LARGER than the worst null "
               "(the retraction's own claim inverted)", "nonzero")

        edit("shipfr.json", lambda d: d.__setitem__(
            "verdict", "THE SHIPPING BINARY CARRIES IT"))
        expect("record plant: verdict text inverted", "nonzero")

        edit("shipfr.json", lambda d: d.__setitem__("pin", d["pin"]))
        edit("shipfr-pin-9b05d0b7.json", lambda d: d.__setitem__(
            "pin", R.rec("shipfr.json")["pin"]))
        expect("record plant: both arms given the SAME pin (a re-run that "
               "re-measures nothing)", "nonzero")

        edit("shipalign.json", lambda d: d[0].__setitem__("refused", 3))
        expect("record plant: a subject given 3 refused frames", "nonzero")

        edit("shipalign.json", lambda d: d[0].__setitem__("placed",
                                                          d[0]["placed"] - 1))
        expect("record plant: placed no longer equals frames", "nonzero")

        edit("shipalign.json", lambda d: d.pop())
        expect("record plant: a subject dropped (24 aligned, sum breaks)",
               "nonzero")

        for s in list(R.rec("shipfr.json")["steps"]):
            pass
        edit("shipfr.json", lambda d: d["steps"][2].__setitem__("to", 48))
        expect("record plant: the accused step no longer adds frame 47",
               "nonzero")

        edit("shipfr.json", lambda d: d["steps"][0].__setitem__("kind",
                                                                "ROGUE"))
        expect("record plant: two accused steps, no nulls left", "nonzero")

        # --- clip-audit oracle plants ------------------------------------
        edit("clipaudit.json",
             lambda d: d["summary"].__setitem__("blown", 4))
        expect("record plant: 4 blown files (the lane put in ORCH's case 2)",
               "nonzero")

        edit("clipaudit.json",
             lambda d: d["summary"].__setitem__("unreadable", 2))
        expect("record plant: 2 unreadable files (a zero produced by not "
               "looking)", "nonzero")

        def blow_master(d):
            d["masters"]["rows"][0]["clip_pct"] = 92.03
            d["masters"]["rows"][0]["blown"] = True
        edit("clipaudit.json", blow_master)
        expect("record plant: a linear master blown at ORCH's 92.03%",
               "nonzero")

        def blow_head(d):
            d["head_renders"]["rows"][0]["clip_pct"] = 60.0
        edit("clipaudit.json", blow_head)
        expect("record plant: a HEAD render clipped at 60%", "nonzero")

        edit("clipaudit.json",
             lambda d: d["summary"].__setitem__(
                 "head_median", [65535.0] + d["summary"]["head_median"][1:]))
        expect("record plant: a HEAD median pinned at pure white", "nonzero")

        edit("clipaudit.json", lambda d: d["masters"]["rows"].pop())
        expect("record plant: a linear master dropped (25 of 26 examined)",
               "nonzero")

        # ---- PLACEBO: must stay GREEN -----------------------------------
        mutate_doc("ORCH's discipline 34 requires",
                   "ORCH's discipline 34 plainly requires")
        rc, _ = run()
        (behaved if rc == 0 else misbehaved).append(
            "placebo: a neutral wording edit stays GREEN%s"
            % ("" if rc == 0 else "  [rc=%d, wanted 0]" % rc))
        restore()

        # ---- REFUSAL: unreadable record must not read as a pass ---------
        io.open(os.path.join(OUT, "shipfr.json"), "w",
                encoding="utf-8").write("{ not json")
        rc, out = run()
        ok = rc != 0 and "0 failed" not in out
        (behaved if ok else misbehaved).append(
            "refusal: a corrupt record refuses rather than reporting a pass%s"
            % ("" if ok else "  [rc=%d]" % rc))
        restore()

    finally:
        restore()

    for b in behaved:
        print("  ok      %s" % b)
    for m in misbehaved:
        print("  MISBEHAVED %s" % m)
    print("\n%d behaved, %d misbehaved -- %d plants"
          % (len(behaved), len(misbehaved), len(behaved) + len(misbehaved)))

    rc, out = run()
    print("document restored, verifier: rc=%d (%s)"
          % (rc, out.strip().splitlines()[-1] if out.strip() else ""))
    if rc != 0:
        print("HARNESS: failed to restore the document")
        return 2
    return 1 if misbehaved else 0


if __name__ == "__main__":
    sys.exit(main())
