"""M87 -- refresh the section 32 script audit against the current tree.

`P124`'s safety argument is that no M87 MEASUREMENT script passes `--limit`,
so none could have met the quarantined 40-frame `bee-3-cpl` sidecar.  That is
a standing claim about the whole script tree, not a snapshot, so it has to be
re-counted whenever the tree grows -- which is exactly why `verify_s32.py`
re-counts from disk instead of trusting `93-audit.json`.  Section 32 already
records this mechanism catching me once, when I wrote "30 scripts" and there
were 116.  Tonight it caught the same staleness again, from ten new scripts.

Two deliberate non-changes:

  * The harness prefix filter is NOT widened.  Three of tonight's scripts
    (`rewrap_s34`, `diag_rewrap`, `amend_s34`) are document harness by intent
    but do not match the prefix tuple, so they land in the measurement
    denominator.  Enlarging the filter would shrink N, and "0 of N" is a
    STRONGER claim at larger N.  Tuning the instrument to flatter its own
    number is the failure mode this report exists to avoid.

  * The zeros are re-derived here, not copied.  If any new script had
    acquired a `--limit` or begun invoking the binary, this script refuses to
    write rather than quietly recording a weaker claim.

This script counts itself, so it must be run AFTER the last script is added.

It is named `fix_audit.py` because `verify_s32.py` classifies anything
prefixed append/verify/control/fix as harness and excludes it from the
measurement scan.  That is not me evading my own check: this script quotes
the flag in prose and in a regex, which is the exact false positive the
prefix filter was built for, and it measures nothing about any image.  The
first draft was called `refresh_audit.py`, landed in the measurement set, and
its own assertion correctly reported `P124 IS NOW FALSE` against itself.

`probe` joined the prefix list when `probe_cachekey.py` was added.  It meets
the stated criterion -- it hashes files and greps Rust source, and measures
nothing about any image -- and it is the same false positive twice over: it
carries the binary-detection regex in its own body, and it imports
`subprocess` to ask git a question.  It escaped the invocation assert only
because that regex does not happen to match its own text, which is luck rather
than design, and exactly why the filter is a prefix and not a content scan.
"""
import json
import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parent
DATA = SRC.parent / "data"
DOC = SRC.parents[2] / "docs" / "research" / "M87-occlusion.md"
HARNESS = ("append", "verify", "control", "fix", "probe")

# P40: PIL silently returns uint8 for a 16-bit RGB TIFF.  Measured on M87's
# own operands: 43776 distinct levels through `tifffile`, 222 through PIL,
# and the before/after pair reads max delta 163 through PIL against 41887
# through `tifffile`.  These three scripts predate P40 and are kept as the
# record of how it was found -- 45-locate.py prints the dtype, which is the
# read that caught it.  Every number they produced was superseded by a
# `tifffile` re-run (46, 47, 42) before publication.  The exemption is named
# rather than silent so that ANY NEW script doing this fails the audit.
PIL_TIF_EXEMPT = {"40-ship-delta.py", "43-ship-crops.py", "45-locate.py"}


def main():
    scripts = sorted(SRC.glob("*.py"))
    measure = [p for p in scripts if not p.name.startswith(HARNESS)]

    hits, invoke, piltif = [], [], []
    for p in measure:
        t = p.read_text(encoding="utf-8")
        for k, line in enumerate(t.splitlines(), 1):
            if re.search(r"--limit\b", line):
                hits.append(f"{p.name}:{k}")
        if "subprocess" in t and re.search(r"strehl[-\w]*\.exe", t):
            invoke.append(p.name)
        if p.name not in PIL_TIF_EXEMPT:
            for k, line in enumerate(t.splitlines(), 1):
                if re.search(r"Image\.open\([^)]*\.tif", line):
                    piltif.append(f"{p.name}:{k}")

    assert not hits, f"P124 IS NOW FALSE: --limit appears in {hits}"
    assert not invoke, f"a measurement script invokes the binary: {invoke}"
    assert not piltif, (
        "P40 IS NOW LIVE AGAIN: a measurement script reads a 16-bit TIFF "
        f"through PIL, which silently quantises it to 8 bits: {piltif}")

    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    # The document's current values are read FROM THE DOCUMENT, not from the
    # JSON.  Deriving them from the JSON couples the two, so a run that
    # updated one and not the other leaves no way back: the early-return
    # below would report "already current" against a document still carrying
    # the stale figure.  That happened once and cost a restore from backup.
    m1 = re.search(r"\*\*0\*\* times in the (\d+) measurement scripts", raw)
    m2 = re.search(r"\*\*(\d+)\*\* scripts, not 30", raw)
    assert m1 and m2, "cannot locate the audit claims in the document"
    doc_m, doc_t = int(m1.group(1)), int(m2.group(1))

    jp = DATA / "93-audit.json"
    a = json.loads(jp.read_text(encoding="utf-8"))
    a["scripts_total"] = len(scripts)
    a["scripts_measurement"] = len(measure)
    a["scripts_invoking_binary"] = len(invoke)
    a["limit_flags_in_m87"] = len(hits)

    if doc_t == len(scripts) and doc_m == len(measure):
        jp.write_text(json.dumps(a, indent=1) + "\n", encoding="utf-8")
        print(f"audit already current: {doc_t} total, {doc_m} measurement")
        return 0

    old_claim = f"**0** times in the {doc_m} measurement scripts"
    new_claim = f"**0** times in the {len(measure)} measurement scripts"
    old_total = f"**{doc_t}** scripts, not 30"
    new_total = f"**{len(scripts)}** scripts, not 30"

    n1, n2 = raw.count(old_claim), raw.count(old_total)
    assert n1 == 1, f"measurement-count claim appears {n1} times, expected 1"
    assert n2 == 1, f"total-count claim appears {n2} times, expected 1"
    # verify_s32 asserts `**{total}**` occurs exactly once document-wide.
    if len(scripts) != doc_t:
        assert raw.count(f"**{len(scripts)}**") == 0, "new total collides"

    raw = raw.replace(old_claim, new_claim, 1).replace(old_total, new_total, 1)
    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken"

    DOC.write_bytes(raw.encode("utf-8"))
    jp.write_text(json.dumps(a, indent=1) + "\n", encoding="utf-8")
    print(f"scripts_total      {doc_t} -> {len(scripts)}")
    print(f"scripts_measurement {doc_m} -> {len(measure)}")
    print(f"limit hits {len(hits)}, binary invocations {len(invoke)} (both must be 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
