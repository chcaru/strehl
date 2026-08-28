"""bandq -- the band licence check.

    python bandq.py <subject> <lo> <hi>

Prints the verdict, R, the 95% CI, the sample size and the commit that measured
it, and EXITS NON-ZERO unless the subject is licensed at that slice.

WHY THIS EXISTS
---------------
ORCH has twice quoted a sharpness figure measured in a band nobody qualified
for that subject.  Neither time was the data missing -- V-LINEAR-BANDS.md had
the answer both times.  The failure was that a lane reaching for a subject had
no cheap way to ask "am I licensed here?", and the default assumption is yes.

A licence check that requires reading a 1200-line document will not be run.  A
licence check that exits non-zero can be wired into a lane's own gate, so this
one is built to be called by a script and not only read by a human.

THE DISTINCTION THIS TOOL EXISTS TO PRESERVE
--------------------------------------------
A subject that FAILED and a subject NOBODY MEASURED are different facts and
must not share a glyph.  `112MSDCF` at 0.30-0.35 is measured noise: R = 1.079,
CI upper 0.379 below MARGINAL.  `leaf-2-cpl` at 0.30-0.35 is *unknown* -- the
slice has never been swept on it.  Reporting both as "not licensed" would be
true and useless; the first is settled and the second is a queue item.

And a THIRD case has to be separated from the second, or the tool lies: a
subject name that does not exist at all.  If a typo returned UNQUALIFIED, then
`python bandq.py bee-1-cpll 0.30 0.35` would refuse the licence and look
exactly like a working check.  That is why ROSTER is here and why a name off
the roster is a loud distinct failure rather than a refusal.

EXIT CODES -- each one is a different fact
------------------------------------------
    0   PASS         licensed at this slice
    1   FAIL(noise)  measured, and it is noise -- not licensed
    2   MARGINAL     measured, on the line -- not licensed by default;
                     --allow-marginal makes this exit 0 for callers who have
                     decided a marginal band is good enough for their purpose
    3   UNQUALIFIED  real subject, this slice never measured -- not licensed,
                     and it is a queue item rather than a settled answer
    4   UNKNOWN      name is not a corpus subject (typo, or a new capture that
                     postdates the roster below)
    5   REFUSED      two records disagree about this cell; the tool will not
                     pick a winner

MEASUREMENT PROVENANCE
----------------------
Everything printed comes from the saved sweep JSON.  This tool does no
measurement of its own and cannot disagree with `bandsweep.py`; if a number
here is wrong, the record is wrong.  The commit shown is the commit that last
touched the record file, so a number quoted from this tool is citable.  An
UNCOMMITTED record is reported as such and is NOT citable.
"""
import json
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# The single-subject reruns are CONTROLS.  Swept alone, they see a different
# bootstrap stream from the same subject swept as one of five (sec.6.1), so
# their CIs differ from the canonical record BY DESIGN.  Their point estimates
# do not differ -- that is the acceptance condition, enforced in
# `commission_redevelop.py`.
#
# They are NOT excluded here the way verify_bands_doc.py excludes them, because
# they are the ONLY records carrying the narrow 0.30-0.35 and 0.35-0.40 slices.
# Excluding them would make this tool answer UNQUALIFIED for the exact cells
# ORCH built it to check.  Instead they are ranked below the canonical record
# when both carry a slice, and a disagreement between them is REFUSED.
CANONICAL_FIRST = ("bandsweep.json", "bandsweep-far20.json", "bandsweep-far8.json")

# The corpus roster, so that a typo is distinguishable from an unmeasured
# subject.  MEASURED by directory listing of D:\personal\macro on 2026-08-27:
#     Get-ChildItem D:\personal\macro -Directory | ForEach-Object { $_.Name }
# `flat-fields` is a container, so its three children are listed instead, and
# `paper-sweep` is this lane's alias for one of them (see bandsweep.py:132).
#
# A static roster goes stale silently, which is the same class of defect this
# tool exists to prevent.  So `roster_drift()` below re-lists the corpus when
# the drive is present and reports any difference LOUDLY rather than trusting
# this list.
ROSTER = {
    "109MSDCF", "112MSDCF", "113MSDCF", "119MSDCF",
    "bee-1-cpl", "bee-2-cpl", "bee-3-cpl",
    "chia-seeds-cpl", "coffee-bean", "coffee-bubbles", "couch-fibers-cpl",
    "dime-flat-narrow-slices-cpl", "dry-erase-marker-head-cpl",
    "duck-tape-side-layers-cpl", "flat-on-ruler-cpl", "flower-bud-alone-cpl",
    "flower-bud-with-background-fern-cpl", "flower-inner-edge-cpl",
    "flowers-cpl", "foam", "highly-angled-ruler-mm-cpl", "lavendar-cpl",
    "lead-1-cpl", "leaf-2-cpl", "maldon-sea-salt-cpl", "medication-pill-cpl",
    "pencil-flatter-angle-cpl", "pencil-steep-angle-cpl",
    "pottery-art-glazed-cpl", "tweezers-cpl",
    "unpopped-popcorn-kernels-cpl", "wrapped-text-1", "wrapped-text-2",
    # flat-fields children
    "flat-fields", "subject-focus-sweep-no-cpl", "subject-focus-sweep-with-cpl",
    # this lane's alias
    "paper-sweep",
}

MACRO = os.environ.get("BANDQ_MACRO", r"D:\personal\macro")
# BANDQ_MACRO exists so `commission_bandq.py` can point the drift detector at a
# synthetic corpus.  D:\personal\macro is READ-ONLY, so drift cannot be
# commissioned by creating or deleting a real capture directory, and a drift
# detector nobody has ever seen fire is an assumption rather than a check.
# Unset in normal use.

PASS, FAIL, MARGINAL, UNQUALIFIED, UNKNOWN, REFUSED = 0, 1, 2, 3, 4, 5


def roster_drift():
    """Re-list the corpus and report drift from ROSTER.  READ-ONLY."""
    if not os.path.isdir(MACRO):
        return None
    live = set()
    for name in os.listdir(MACRO):
        if not os.path.isdir(os.path.join(MACRO, name)):
            continue
        if name == "flat-fields":
            sub = os.path.join(MACRO, name)
            for child in os.listdir(sub):
                if os.path.isdir(os.path.join(sub, child)):
                    live.add(child)
        else:
            live.add(name)
    return live


def commit_of(path):
    """The commit that last touched `path`, or a loud marker if uncommitted.

    An uncommitted record is not citable: another agent cannot fetch it and a
    fact banked from it cannot be checked later.  Saying so is the point.
    """
    rel = os.path.relpath(path, HERE)
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--", rel],
                               cwd=HERE, capture_output=True).stdout.decode()
        if dirty.strip():
            return "UNCOMMITTED (not citable)"
        out = subprocess.run(["git", "log", "-1", "--format=%h", "--", rel],
                             cwd=HERE, capture_output=True).stdout.decode().strip()
        return out or "NOT IN GIT (not citable)"
    except OSError:
        return "git unavailable"


def realised_far(n, far_req):
    """The `far` actually used, DERIVED from bandsweep.py's own guard.

    The record's `far_real` field stores the REQUESTED value, not the realised
    one: `coffee-bubbles` reads 20 but ran at 6, because 19 frames cannot give
    two 20-frame halves.  Recomputing it here closes that reporting gap rather
    than propagating it, and it is labelled DERIVED wherever it is printed.
    """
    if n - 2 * far_req < 6:
        return max(2, (n - 6) // 2)
    return far_req


def load_all():
    """Every sweep record, keyed (subject, slice, far) -> list of sources.

    `far` IS PART OF THE CELL'S IDENTITY.  The first version of this function
    keyed on (subject, slice) alone and pooled every protocol together, which
    made four cells look like contradictions when they are simply different
    measurements: `112MSDCF` 0.02-0.05 reads 10.1256 PASS at far=20 and 1.8763
    MARGINAL at far=8, and neither is wrong.

    The evidence that this is a protocol split and not disagreement is that
    records sharing a `far` agree EXACTLY -- `bee-1-cpl` 0.02-0.05 reads
    31.6714 in all three far=20 files, to the last digit -- while records at
    different `far` differ everywhere.  Verified over 134 multi-record cells.

    Found by `verify_bands_doc.py`, which reads the raw JSON independently and
    refused to certify the sec.14 grid.
    """
    cells = {}
    for path in sorted(glob.glob(os.path.join(HERE, "bandsweep*.json"))):
        base = os.path.basename(path)
        try:
            recs = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print("  cannot read %s: %s" % (base, exc), file=sys.stderr)
            continue
        rank = CANONICAL_FIRST.index(base) if base in CANONICAL_FIRST else 99
        for rec in recs:
            far = rec.get("far_real", -1)
            for slice_key, band in rec["bands"].items():
                cells.setdefault((rec["key"], slice_key, far), []).append(
                    (rank, base, rec, band))
    for v in cells.values():
        v.sort(key=lambda t: t[0])
    return cells


# The matched protocol.  sec.3, sec.9 and sec.13 are all far=20, so it is what
# a lane quoting this document is quoting unless it says otherwise.
CANON_FAR = 20


def pick(cells, subject, slice_key, want_far=None):
    """Choose the protocol to answer with.  Never silently.

    Returns (far, hits, note) or (None, None, reason).
    """
    fars = sorted({f for (k, s, f) in cells
                   if k == subject and s == slice_key})
    if not fars:
        return None, None, "no record"
    if want_far is not None:
        if want_far not in fars:
            return None, None, ("far=%d not measured here; measured at %s"
                                % (want_far, ", ".join(str(f) for f in fars)))
        return want_far, cells[(subject, slice_key, want_far)], ""
    if CANON_FAR in fars:
        note = ""
        if len(fars) > 1:
            note = ("also measured at far=%s; far=%d quoted because sec.3, "
                    "sec.9 and sec.13 are all far=%d"
                    % (", ".join(str(f) for f in fars if f != CANON_FAR),
                       CANON_FAR, CANON_FAR))
        return CANON_FAR, cells[(subject, slice_key, CANON_FAR)], note
    if len(fars) == 1:
        return fars[0], cells[(subject, slice_key, fars[0])], (
            "NOT the canonical protocol: this cell exists only at far=%d"
            % fars[0])
    return None, None, ("measured at far=%s but not at the canonical far=%d; "
                        "pick one with --far"
                        % (", ".join(str(f) for f in fars), CANON_FAR))


def fmt_slice(lo, hi):
    return "%.2f-%.2f" % (lo, hi)


def query(subject, lo, hi, allow_marginal=False, quiet=False, want_far=None):
    def say(*a):
        if not quiet:
            print(*a)

    live = roster_drift()
    if live is not None and live != ROSTER - {"paper-sweep"}:
        extra = live - (ROSTER - {"paper-sweep"})
        gone = (ROSTER - {"paper-sweep"}) - live
        if extra or gone:
            say("  ROSTER DRIFT -- the committed roster no longer matches the "
                "corpus on disk.")
            if extra:
                say("    on disk but not in ROSTER: %s" % ", ".join(sorted(extra)))
            if gone:
                say("    in ROSTER but not on disk: %s" % ", ".join(sorted(gone)))
            say("    Update ROSTER in bandq.py.  Until then an UNKNOWN verdict "
                "may be a stale roster rather than a typo.")
            say("")

    if subject not in ROSTER:
        say("  UNKNOWN SUBJECT: %r is not a corpus subject." % subject)
        near = [s for s in sorted(ROSTER)
                if s.startswith(subject[:4]) or subject.startswith(s[:4])]
        if near:
            say("    did you mean: %s" % ", ".join(near[:6]))
        say("    This is NOT the same answer as UNQUALIFIED.  A name that does "
            "not exist cannot be licensed or refused; it is a typo.")
        return UNKNOWN

    slice_key = fmt_slice(lo, hi)
    cells = load_all()
    far_used, hits, why = pick(cells, subject, slice_key, want_far)

    if not hits:
        measured = sorted({s for (k, s, _f) in cells if k == subject},
                          key=slice_sort_key)
        say("  UNQUALIFIED: %s has never been measured at %s cyc/px%s."
            % (subject, slice_key,
               "" if want_far is None else " at far=%d" % want_far))
        if why and why != "no record":
            say("    %s" % why)
        if measured:
            say("    measured slices for this subject: %s" % " ".join(measured))
        else:
            say("    this subject has never been band-qualified at ANY slice.")
        say("    UNQUALIFIED is NOT a failure.  Nothing is known about this "
            "cell in either direction, so no sharpness, softening or acuity "
            "claim may be made here -- but the band is not established to be "
            "noise either.  It is a queue item: ask ORCH for a sweep.")
        return UNQUALIFIED

    verdicts = {h[3]["verdict"] for h in hits}
    if len(verdicts) > 1:
        say("  REFUSED: %d records at the SAME protocol (far=%d) disagree "
            "about %s at %s." % (len(hits), far_used, subject, slice_key))
        for _, base, rec, band in hits:
            say("    %-40s R=%.4f  %s" % (base, band["R"], band["verdict"]))
        say("    The tool will not pick a winner.  Resolve the records first.")
        return REFUSED

    rank, base, rec, band = hits[0]
    verdict = band["verdict"]
    n = rec["n_real"]
    far_req = rec.get("far_real", -1)
    far_got = realised_far(n, far_req) if far_req > 0 else -1

    say("  subject   : %s" % subject)
    say("  slice     : %s cyc/px" % slice_key)
    say("  verdict   : %s" % verdict)
    say("  R         : %.4f" % band["R"])
    say("  95%% CI    : [%.4f, %.4f]" % (band["lo"], band["hi"]))
    say("  N         : %d frames (step %s, decim %s)"
        % (n, rec.get("step", "?"), rec.get("decim", 1)))
    if far_req > 0:
        note = "" if far_got == far_req else "   <- REQUESTED %d, GUARD REDUCED IT" % far_req
        say("  far       : %d (DERIVED from the frame-count guard)%s" % (far_got, note))
    say("  tiles     : %s kept, %s confirmed"
        % (rec.get("kept", "?"), rec.get("confirmed", "?")))
    say("  record    : %s" % base)
    say("  commit    : %s" % commit_of(os.path.join(HERE, base)))
    if why:
        say("  protocol  : %s" % why)
    if len(hits) > 1:
        say("  note      : %d records carry this cell at far=%d and they "
            "AGREE; the canonical one is quoted." % (len(hits), far_used))

    if verdict == "PASS":
        say("  -> LICENSED.  Sharpness, softening and acuity claims are "
            "quotable here if the band and this qualification are named.")
        return PASS
    if verdict == "MARGINAL":
        say("  -> MARGINAL.  On the line.  A difference measured here is not "
            "quotable as evidence without saying so in the same sentence.")
        return PASS if allow_marginal else MARGINAL
    say("  -> NOT LICENSED.  This band is measured noise on this subject. "
        "A sharpness difference measured here is a difference in grain.")
    return FAIL


def main(argv):
    want_far = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--far":
            i += 1
            if i >= len(argv):
                print("  --far needs a value")
                return REFUSED
            try:
                want_far = int(argv[i])
            except ValueError:
                print("  --far needs an integer")
                return REFUSED
        else:
            rest.append(a)
        i += 1

    args = [a for a in rest if not a.startswith("--")]
    allow_marginal = "--allow-marginal" in rest
    quiet = "--quiet" in rest

    if len(args) == 1 and args[0] == "table":
        return print_table(markdown="--markdown" in rest)
    if len(args) != 3:
        print(__doc__)
        return REFUSED
    subject = args[0]
    try:
        lo, hi = float(args[1]), float(args[2])
    except ValueError:
        print("  lo and hi must be numbers in cyc/px, e.g. 0.30 0.35")
        return REFUSED
    return query(subject, lo, hi, allow_marginal, quiet, want_far)


def slice_sort_key(s):
    """Sort by (lo, hi).  Sorting on `lo` alone put 0.10-0.20 before
    0.11-0.14 and, worse, 0.30-0.40 before 0.30-0.35 -- so the wide slice and
    the narrow slice ORCH conflated tonight appeared in the wrong order in the
    very table built to separate them."""
    lo, hi = s.split("-")
    return (float(lo), float(hi))


def print_table(markdown=False):
    """The whole corpus x slice grid, with UNQUALIFIED visually distinct.

    `--markdown` emits the same grid as a Markdown table for
    V-LINEAR-BANDS.md sec.14.  The document's table is GENERATED from this
    function rather than typed, so the published table and the tool other
    lanes call cannot drift apart -- which is the failure this whole section
    exists to prevent.
    """
    cells = load_all()
    subs = sorted(ROSTER - {"flat-fields", "subject-focus-sweep-no-cpl",
                            "subject-focus-sweep-with-cpl"})
    slices = sorted({s for (_, s, _f) in cells}, key=slice_sort_key)
    nq = sum(1 for s in subs if not any(k == s for (k, _, _f) in cells))

    def cell_verdict(s, sl):
        """The canonical-protocol verdict, or None.  Uses the same picker the
        query path uses, so the grid cannot say something the tool would
        refuse to say."""
        far, hits, _why = pick(cells, s, sl)
        if not hits:
            return None
        vs = {h[3]["verdict"] for h in hits}
        return vs.pop() if len(vs) == 1 else "REFUSED"

    if markdown:
        glyph = {"PASS": "**PASS**", "MARGINAL": "marg", "FAIL(noise)": "FAIL",
                 "REFUSED": "??"}
        print("| subject | " + " | ".join(slices) + " |")
        print("| --- |" + " --- |" * len(slices))
        for s in subs:
            row = ["`%s`" % s]
            for sl in slices:
                v = cell_verdict(s, sl)
                row.append("--" if v is None else glyph.get(v, "?"))
            print("| " + " | ".join(row) + " |")
        print()
        print("`--` = UNQUALIFIED (never measured). %d of %d corpus subjects "
              "have never been band-qualified at any slice." % (nq, len(subs)))
        return 0

    glyph = {"PASS": "PASS", "MARGINAL": "marg", "FAIL(noise)": "FAIL",
             "REFUSED": "??"}
    width = max(len(s) for s in subs) + 2

    print("  BAND QUALIFICATION, per subject and per slice.")
    print("  Canonical protocol far=%d (sec.3, sec.9 and sec.13 are all "
          "far=%d)." % (CANON_FAR, CANON_FAR))
    print("  PASS = licensed    marg = on the line    FAIL = measured noise")
    print("  ---- = UNQUALIFIED: never measured.  NOT a failure, and NOT clean.")
    print()
    for i, s in enumerate(slices, 1):
        print("    [%2d] %s cyc/px" % (i, s))
    print()
    print("  %-*s%s" % (width, "subject",
                        "".join("%-5s" % ("[%d]" % i)
                                for i in range(1, len(slices) + 1))))
    for s in subs:
        row = "  %-*s" % (width, s)
        for sl in slices:
            v = cell_verdict(s, sl)
            row += "%-5s" % ("----" if v is None else glyph.get(v, "?"))
        print(row)
    print()
    print("  %d of %d corpus subjects have never been band-qualified at any "
          "slice." % (nq, len(subs)))
    print("  Those rows are UNQUALIFIED, not clean.  A lane scoring sharpness "
          "on one of them is unlicensed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
