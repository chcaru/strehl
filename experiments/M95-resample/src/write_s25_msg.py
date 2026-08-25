import io
import os

MSG = """M95 s25: audit my own reports for prefix grafts, and find the bug in the auditor

ORCH discipline 768: a prefix-anchored edit silently grafts the unmatched tail of
the line onto the new text, with no error and no lint violation. Section 24.9
records that M95 edited a hash cell in the section 24 results table this session,
so the hazard is live for this report specifically and no existing gate covers it:
verify_s24 asserts values are present, not that nothing trails them.

Built a detector rather than reasoning about it. x20_graftcheck.py, three checks
over both M95-owned reports, six positive controls that must all fire before it
will report on the subject at all.

RESULT: clean. 3121 lines of M95-kernel.md and 706 of
M95-merge-vs-frame-sharpness.md, check A 0, check B 0, check C 0. The section 24
hash edit landed correctly and there is no graft in either report.

The audit found nothing wrong with its subject and two things wrong with M95's
own instruments:

1. check A split table rows on every pipe including the ESCAPED one, so rows
   using \\| counted phantom cells. Worse, the inflated rows moved the block
   majority, so the check then accused the CORRECT rows. 9 hits -> 0 after the
   fix. Control G-A3 requires silence on the clean version of the same table, so
   the fix is shown to have corrected the count rather than muted the check.

2. verify_s24 sliced the report from the section 24 heading to END OF FILE, so
   appending section 25 gave it a second line matching "| C1 |" and it exited 2.
   Its docstring promised a line in section 24; it searched section 24 plus
   everything ever appended below. A verifier of that shape passes every run
   until the next section is added. Slice now bounded at the next top-level
   heading; the section 25 controls renamed G-A1..G-B2 so the token cannot recur.

The gate FAILED CLOSED - exit 2, tool failure, refusing to report on a table it
could not uniquely identify, rather than exit 0 or 1. That behaviour was
installed in 24.9 after a measured miss and this is the first time it has paid.

Guard against the fix being a weakening: negctl_s24 re-run after bounding the
slice still catches 7/7 subject defects and 2/2 tool defects and restores the
report byte-exact. Narrower, no less sensitive.

Also audited, nothing invalidated: zero Select-Object -First in any M95 script,
so the narrowed fact-1507 rule clears every M95 gate without a re-run; zero M95
scratch anywhere on D:\\ (m106-scratch and strehl-scratch-m98 are other lanes').

Gates, each exit code captured on the line immediately after its process:
  verify_s23 0 (76/76 GREEN)      negctl_s23 0 (7/7 + 2/2, restore byte-exact)
  verify_s24 0 (29/29 GREEN)      negctl_s24 0 (7/7 + 2/2, restore byte-exact)
  verify_report 0 (all merge-vs-frame numbers verified)
  x20_graftcheck 0 (6/6 controls fired, 0/0/0)
  corpus_lint 1 - one C3 against experiments/M123-robustness-mask, ZERO in any
  M95-owned file. Not M95's lane; reported, not touched.
"""

path = os.path.join(os.environ["TEMP"], "m95_s25_commit.txt")
with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(MSG)
ctrl = [c for c in MSG if ord(c) < 32 and c not in "\r\n\t"]
print(f"wrote {len(MSG)} chars to {path}")
print(f"control bytes: {len(ctrl)}")
