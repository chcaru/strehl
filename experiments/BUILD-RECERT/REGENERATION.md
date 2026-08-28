# BUILD-RECERT scratch: what was deleted, and what can be got back

The heavy scratch under `D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\` was deleted at
session wind-down to return disk to the owner's render. Every number this lane
reported was banked as text first, under `banked/`, and the three report
verifiers were repointed to read it from there. They no longer need `D:` and no
longer need any machine-specific path.

    python experiments\BUILD-RECERT\verify_s12.py     73 checks
    python experiments\BUILD-RECERT\verify_s13.py     53 checks
    python experiments\BUILD-RECERT\verify_s14.py     67 checks
    python experiments\BUILD-RECERT\negctl_report.py  9 arms

`banked/` is 231 files and 1.671 MB: every `.json` scoring output, every render
log, every per-master `.provenance.txt`, and both arm manifests. No image was
banked and none needed to be -- the statistics were already reduced.

## The two arms that were deleted, and their status

### `DEF-2f858c62` -- REGENERABLE

    git commit    2f858c624f897c8dde140e06fe6b6cb8643454c8
    binary sha256 A058F737DFE695F711DBACB077B118ED10A5B85C556FE888EE7F929F10397542
    built by      git archive of that commit + clean release build
    library       D:\personal\macro   (owner's read-only originals, still present)
    flags         --srgb --auto-exposure, identical on every subject
    scope         26 subjects, 4825 frames
    size          4.79 GB

Rebuild the pin at that commit, then re-run `recert.py` against the same
library. `banked/arms/DEF-2f858c62/manifest.tsv` lists every subject and
`*.provenance.txt` records each master's own render parameters, so a rebuilt arm
can be checked against the deleted one without the deleted one existing.

Section 13 is measured on this arm. It is, as far as this lane knows, the only
full-corpus render carrying the exposure fix.

### `SC-BASE-bc6fa3c7` -- **NOT REGENERABLE, AND THIS IS A DEFECT IN MY OWN WORK**

    binary sha256 BC6FA3C787A18CAA13A9DB7FD0E447C62CB371DD2B7533D8CDBE9935FBD6B0BC
    git commit    UNATTRIBUTED
    tree at build b3ed9800383cc08bc60de23bf1678aa4f430c644 WITH UNCOMMITTED CHANGES
    scope         6 subjects, 463 frames
    size          1.11 GB

`banked/arms/SC-BASE-bc6fa3c7/RUN.txt` records the binary as operator-supplied
and states plainly that it "may not match any commit". The hash identifies the
executable; it does not reconstruct it. The tree it came from had uncommitted
changes, so **no commit can be checked out that reproduces this binary**, and
that was true before the pixels were deleted -- deleting them did not cause it.

What this costs, stated exactly:

* Every number section 14 and `bandqual.json` report is **banked and still
  checkable** -- `verify_s14.py` reads them from `banked/logs/` and passes.
* The pairings were **internally valid**: both sides of every comparison came
  from this same binary, and `SC-NULL` was verified byte-identical to `SC-BASE`
  on 6 of 6 subjects by SHA-256, which is what licensed the arm at all.
* What is gone is the ability to derive a **new** statistic from these pixels.
  Section 14's numbers can be re-read; they cannot be re-derived.

If section 14 ever needs to carry weight beyond this lane, it should be re-run
on an attributable pin rather than repaired. An unattributable baseline is not
made attributable by keeping its output.

## One more thing a reader will otherwise misread

`banked/arms/DEF-2f858c62/RUN.txt` says `subjects: 1/1 rendered` and
`PARTIAL ARM -- couch-fibers-cpl`. That is not the arm's scope; the arm was
filled incrementally and `RUN.txt` was overwritten by the **last** invocation.
The arm's real scope is `manifest.tsv` and the 26 `*.provenance.txt` files
beside it. The same applies to `SC-BASE-bc6fa3c7/RUN.txt`, which happens to
record all six because the six were rendered in one call.
