# Final style and corpus baseline audit

2026-10-28; reviewer root/corpus. Baseline remote-tracking origin/main resolves
locally to c149e52834fc1c86c2af0fe022713c39fa25f33c. This lane inspected the final
root-scheduled logs and read current/baseline source; it ran no Cargo, formatter,
RAW job or network fetch and made no product edits.

VERIFIED: these final logs contain zero introduced warning sites and zero
introduced formatting hunks. The remaining corpus diagnostics are inherited.
This establishes source inheritance, not a strict lint/format/corpus pass.

## Frontend Clippy

Input: outputs/multi-stack/frontend-clippy-4.jsonl.
SHA256: 71eb812008b01d5898607c0a9af29faaec060e8b823ceeedf62b5b8c46614e7e.

159 compiler warning records deduplicate to 106 diagnostic sites and 53 repeats;
there are no error records, and build-finished reports success=true. There are
91 crate-source sites and 15 experiment-include sites. All 106 diagnostic
signatures match the previous final frontend audit: zero new or removed sites.
The signature comparison excludes line displacement, and the enum-size exception
uses its reviewed cause rather than the changed whole-enum span.

105 exact diagnostic spans map to unchanged baseline text or unchanged diff
blocks. The remaining large_enum_variant still names Stack (644 bytes) and Align
(232 bytes). Stack's entire field definition is unchanged; the Align variant
and defining align_cmd.rs have unchanged source content. Session is not the
reported size cause. The JSON retains each span, baseline/current locations,
current source hashes, mappings, classifications and duplicate count.

The JSON's successful build is warning-enabled success. It does not establish
that a command with -D warnings passes.

## Engine formatting

Input: outputs/multi-stack/checks/engine-fmt-2.log.
SHA256: 9064bac7da0fb432aab3fef65f91e1baa540f6c4363dcf93c3f1fb00cc7a63c1.

645 hunks across 49 files remain: 642 are in files with unchanged baseline text;
three remove only unchanged baseline lines inside modified files. Every current
hunk matches a hunk previously classified as inherited. The four earlier new
hunks representing three logical formatting issues have disappeared. No hunk
from the new modules appears in this log.

Ten end-of-file hunks include rustfmt's virtual empty context line after the
final newline. The parser explicitly accounts for that display line, and still
verifies the surrounding old text against both current and baseline source.
The other 635 hunks require no such adjustment. The receipt retains every hunk
and its classification. Engine-wide cargo fmt remains failing on inherited
formatting; no engine-wide formatting pass is claimed.

## Corpus lint

The root's corpus-lint-1.log reported 19 diagnostics. The completed rerun,
outputs/multi-stack/corpus-lint-2.log, reports 16: S1=7, S3=2, S6=7. The three
new S2 blank ledger-row diagnostics are absent. The remaining 16 diagnostics
are in seven unique files:

| Research source | Diagnostics |
| --- | ---: |
| M-PHASE0-SPLIT.md | 2 |
| M-PHASE0-SPLIT2.md | 4 |
| M135-detail-instrument.md | 2 |
| M169-comparator-requirement-audit.md | 2 |
| M182-kernel-trade.md | 4 |
| M185-flat-retraction.md | 1 |
| M186-m10-definition-audit.md | 1 |

Each complete file is byte-identical to its git-show origin/main blob after
only CRLF-to-LF conversion. Literal worktree-byte equality is false because the
checkout uses CRLF and those Git blobs use LF. The receipt preserves both raw
hashes, the newline-normalized hash, CRLF counts and the exact comparison result;
no whitespace trimming or content normalization hides differences. The two
missing final newlines are present in the baseline too. The corpus check still
fails with these 16 inherited violations.

## Reproduction and evidence

MEASURED command, final exit code 0 captured immediately:

```powershell
python -X faulthandler -I experiments/multi-stack-2026-10-28/sampling/final-style-audit.py
```

The script adapts review/lint-audit-3.py, lint-diff-map-3.py and
audit-engine-format.py into one receipt without overwriting historical results.
It uses read-only git -C ROOT --work-tree=ROOT show BASE:PATH, checks the current
origin/main ref, and stores input-log and prior-audit hashes. Two preliminary
script checks exposed checkout newline conversion and virtual EOF context; both
were corrected explicitly before the final successful audit.

Reproducer: [final-style-audit.py](final-style-audit.py).
Detailed receipt: [final-style-audit.json](final-style-audit.json).
Prior independent source audits remain under ../review/ unchanged. Conclusions
apply to these retained logs and the source hashes recorded in the receipt;
future source changes require their own scheduled check.
