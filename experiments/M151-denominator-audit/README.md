# M151 denominator-provenance audit

This lane inventories and reviews every direct-child Markdown file matching:

- `docs/research/*.md`
- `docs/proposals/*.md`

The scanner is deterministic, uses only the Python standard library, and does
not parse Markdown away. Prose, tables, block quotes, and fenced blocks are all
scanned. Nested files and non-`.md` suffixes are out of scope.

The path `D:\personal\macro\requests\7-aperture-pairs` and every descendant are
rejected lexically, before path resolution or filesystem access.

## Commands

Run from the Strehl repository root:

```powershell
python -B experiments/M151-denominator-audit/test_denominator_audit.py

python -B experiments/M151-denominator-audit/denominator_audit.py scan `
  --repo-root . `
  --out experiments/M151-denominator-audit/out

python -B experiments/M151-denominator-audit/commission.py --repo-root .
```

Validate completed reviewer ledgers:

```powershell
python -B experiments/M151-denominator-audit/denominator_audit.py validate-ledgers `
  --manifest experiments/M151-denominator-audit/out/corpus-manifest.json `
  --candidates experiments/M151-denominator-audit/out/candidates.jsonl `
  --shards experiments/M151-denominator-audit/out/shards `
  --ledgers <ledger-01.jsonl> <ledger-02.jsonl> `
  --repo-root .
```

Validate the final report alone:

```powershell
python -B experiments/M151-denominator-audit/denominator_audit.py validate-report `
  --manifest experiments/M151-denominator-audit/out/corpus-manifest.json `
  --report <final-report.md> `
  --repo-root .
```

Validate every artifact together:

```powershell
python -B experiments/M151-denominator-audit/denominator_audit.py check `
  --manifest experiments/M151-denominator-audit/out/corpus-manifest.json `
  --candidates experiments/M151-denominator-audit/out/candidates.jsonl `
  --shards experiments/M151-denominator-audit/out/shards `
  --ledgers <ledger-01.jsonl> <ledger-02.jsonl> `
  --report <final-report.md> `
  --repo-root .
```

Commands return `0` for green, `1` for a review/report validation failure, and
`2` for malformed or forbidden input.

Assemble the exact final ledger after all snapshot-bound review overlays exist:

```powershell
python -B experiments/M151-denominator-audit/finalize_ledger.py `
  --snapshot experiments/M151-denominator-audit/out-final
```

Later overlays take precedence over earlier ledgers only for stable occurrence
IDs or exact file paths. The finalizer hard-errors on duplicate keys within a
source, missing final records, stale source lines, stale file hashes,
noncanonical shards, and malformed records. It rebinds the validation
`reviewer` field to the final canonical shard owner while
`final-ledger-provenance.json` commits the ordered source ledgers, their hashes,
the original source reviewers, and the complete selection digest.

## Scanner outputs

`scan` atomically writes:

- `corpus-manifest.json`: every file's repository-relative path, raw-byte
  SHA-256, line count, byte count, Git porcelain state, candidate count, corpus
  digest, candidate-JSONL digest, and totals;
- `candidates.jsonl`: one canonical JSON object per candidate occurrence;
- `shards/shard-01.json` through `shard-08.json`: a complete partition of
  files and candidate IDs.

Files are sorted by repository-relative POSIX path. Candidate occurrences are
sorted by path, line, column, detector kind, and ID. No timestamp or host path
enters an artifact. A rescan removes obsolete numbered shard manifests such as
`shard-09.json`.

Sharding keeps files whole so a reviewer can attest a complete file. It uses
deterministic greedy longest-processing-time assignment by candidate count:
the next heaviest file goes to the lowest-load reviewer, with stable path and
reviewer-number tie breaks. The manifest records all eight loads and their
spread.

Each occurrence ID is the truncated SHA-256 of the repository path, detector
kind, complete source line, matched text, and duplicate ordinal. It therefore
survives unrelated line insertions while changing when the reviewed claim
changes. The complete file SHA-256 remains the authoritative snapshot binding.

## Candidate recall

Every line is searched for overlapping semantic categories:

- numeric percentages, using `%`, `percent`, or `percentage`;
- numeric fractions such as `17/20`;
- numeric `N of M` and `N out of M` forms;
- occurrences of rate, coverage, pass, success, eligible, qualified,
  admitted, admission/admissions, and their common inflections.

A line such as `95% success` deliberately emits both a percentage occurrence
and a success-claim occurrence. False positives are dispositions, not scanner
deletions; this keeps the inventory high recall.

## Ledger contract

Ledgers are ASCII JSONL. Blank lines and unknown record types fail closed.
Across all supplied ledgers, every candidate must have **exactly one**
`disposition` and every corpus file must have **exactly one**
`file_attestation`. With shard validation enabled, each record's reviewer must
own that candidate or complete file.

Disposition example:

```json
{"record_type":"disposition","occurrence_id":"den-0123456789abcdef01234567","reviewer":"reviewer-01","classification":"population","denominator_chain":["all decoded sites","eligible sites after frozen mask","reported passing sites"],"evidence_label":"MEASURED","consequence":"The complete eligible population is reported.","source_line":42,"resolution_status":"verified"}
```

Required fields:

- `classification`: exactly one of `population`, `fixed_subsample`, `cap`,
  `fixture`, `unstated`, or `out_of_scope`;
- `denominator_chain`: a non-empty list of non-empty provenance steps;
- `evidence_label`: one of `MEASURED`, `VERIFIED`, `DERIVED`, `ARGUED`, or
  `UNVERIFIED`;
- `consequence`: non-empty text;
- `source_line`: the integer line recorded by the candidate;
- `resolution_status`: one of `open`, `unresolved`, `needs_repair`, `repaired`,
  `resolved`, `verified`, `accepted`, or `not_applicable`.

Even `unstated` and `out_of_scope` dispositions require a denominator chain;
the chain should state where provenance stops or why the expression has no
audit denominator.

Complete-file attestation example:

```json
{"record_type":"file_attestation","file":"docs/research/example.md","reviewer":"reviewer-01","sha256":"<64 lowercase hex digits from the manifest>","complete":true}
```

The checker rejects missing, duplicate, unknown, wrong-owner, stale-hash, and
partial attestations. Validation also performs a fresh scan of `--repo-root`
and rejects a manifest or candidate set that no longer exactly represents the
live corpus. Internally inconsistent inventory totals, corpus digests, and
noncanonical/unbalanced shard assignments fail closed even if an attacker
recomputes their envelope hashes.

## Final report contract

The first non-empty line must be exactly one of these three forms:

```text
VERDICTS FLIP: <non-negative count> <U+2014 EM DASH> <axes or documents affected>
NO VERDICT FLIPS: <non-negative count> unstated denominators found, none load-bearing
AUDIT BLOCKED: <what you need>
```

In the first form, `<U+2014 EM DASH>` means the single Unicode character
U+2014 (rendered as &#x2014;), with one ASCII space on each side. A hyphen or
en dash is not accepted. The count is parsed from the report; it is not a
hard-coded expected value.

Blank lines may precede the lead. There is no mandatory Markdown title or
manifest-derived `Lead:` line. The manifest and live corpus are still
validated by `validate-report` and `check`.

After the lead, each claim-bearing prose paragraph, list item, blockquote
paragraph, and data table row must begin with exactly one of:

```text
**VERIFIED BY RUNNING:**
**INFERRED BY READING:**
```

The label must have non-empty claim content. Wrapped lines may continue the
same labelled paragraph, but another label cannot be hidden on a continuation
line; use a blank line to begin another paragraph. Unknown labels, empty
labels, and unlabelled content fail closed.

Normal ATX and setext headings, thematic breaks, blank lines, and Markdown
table header/separator rows are neutral. Closed backtick or tilde fenced
command/output blocks are literal and need no claim labels; an unclosed fence
fails closed. For example:

```text
NO VERDICT FLIPS: 3 unstated denominators found, none load-bearing

## Result

**VERIFIED BY RUNNING:** The complete synthetic ledger validates.

- **INFERRED BY READING:** The remaining denominator is not load-bearing.

| Finding | Document |
| --- | --- |
| **VERIFIED BY RUNNING:** Reproduced | docs/research/example.md |
```

## Commissioning

`commission.py` hashes the real corpus before and after but never writes it. In
a temporary synthetic corpus it:

1. generates a complete ledger and labelled report and proves the baseline
   green;
2. requires the report-label plant anchor to occur exactly once in memory,
   removes that label in the temporary report, and proves the unlabelled claim
   is red;
3. proves missing and duplicate report-label anchors both hard-error;
4. requires the denominator plant anchor to occur exactly once;
5. adds an unreviewed `9 out of 10 ... passed` denominator claim;
6. proves the unchanged baseline ledger is red, including at least one missing
   disposition;
7. retains the missing and duplicate denominator-anchor hard-error controls;
   and
8. proves every real-corpus file hash is unchanged.

Any failed commissioning invariant makes the script exit nonzero.
