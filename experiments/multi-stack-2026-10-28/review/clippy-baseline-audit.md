# Independent Clippy baseline audit

Date: 2026-10-28. Baseline: c149e52834fc1c86c2af0fe022713c39fa25f33c.
This review parsed scheduled build output; it did not run Cargo or Clippy.
Both JSONL inputs contain build-finished success=true, but contain warnings.
They do not establish that the strict -D warnings command passes.

## Counts

| Log | Warning records | Unique diagnostic sites | Inherited source causes | New sites in that log |
| --- | ---: | ---: | ---: | ---: |
| core-clippy-2.jsonl | 74 | 49 | 49 | 0 |
| frontends-clippy.jsonl | 164 | 109 | 106 | 3 |

A diagnostic site is keyed by canonical repository source path, primary line and
column ranges, diagnostic code and message. Repeated library/test/example
compilations are deduplicated. Different warnings at different columns on one
line remain separate. Included source aliases containing ../ are normalized
before deduplication and before git show lookup.

The core count of 43 is correct only for source under crates/strehl-core/.
Six additional inherited sites are compiled from included experiments:
noise-floor-oracle, alignment-quadratic-peak consumer-tests, and the two
pyramid-accumulator-range control files. The total all-target source count is 49.
The frontend unique sites include 94 crate-source and 15 experiment-source sites.

## Source evidence and exceptions

VERIFIED: every core diagnostic's exact offending source text exists at the
baseline revision and maps either to an entirely unchanged file or an unchanged
baseline/current diff block. This includes the two align.rs locations shifted
by the newly added APIs and the pyramid.rs locations shifted by module inclusion.
The same evidence establishes 105 of the frontend sites as inherited.

DERIVED from unchanged source causes: the remaining inherited frontend warning
is clippy::large_enum_variant on Command. Its primary span covers the entire enum,
so adding Session makes a whole-span comparison fail. The diagnostic still names
Stack as largest (at least 644 bytes) and Align as second-largest (232 bytes).
The complete Stack variant is byte-for-byte equal as text to baseline; the Align
variant and the entire align_cmd.rs defining AlignArgs are unchanged. The added
Session variant is neither named size cause. This is not classified merely from
the filename or because an enum existed before.

Three new frontend sites in the older log (five repeated compiler records):

| Diagnostic | Reported source | Current replacement inspected |
| --- | --- | --- |
| clippy::precedence | session-align.rs:1831 | (4 * 128) << 20 |
| clippy::chunks_exact_to_as_chunks | session-cache.rs:519 | as_chunks::<2>().0.iter() |
| clippy::chunks_exact_to_as_chunks | session-cache.rs:665 | as_chunks_mut::<2>().0.iter_mut() at current line 667 |

Their flagged original statements are absent from current source. This verifies
the source edits, not the compiler result after those edits. A scheduled frontend
rerun is still required, and this older frontend log does not cover the newly
added transfer cache, photometry module or later UI changes.

## Reproduction and retained evidence

Ran, with Python exit code 0 captured immediately after each invocation:

```powershell
python -B experiments/multi-stack-2026-10-28/review/lint-audit.py
python -B experiments/multi-stack-2026-10-28/review/lint-diff-map.py
```

The scripts invoke read-only git -C ROOT --work-tree=ROOT show BASE:PATH.
They write only review/lint-span-audit.json. That machine-readable artifact keeps
all diagnostic messages and source snippets, baseline/current locations, reviewed
current file SHA256 values, and unchanged-diff-block evidence. Product files are
not modified. Baseline compiler output was not regenerated, so source inheritance
is the supported conclusion, not reproduction on an older toolchain.

Input SHA256:

- core-clippy-2.jsonl: ecb1065b98ce027a3a6433c66a60b2ddb0074821eadc438df0b2033b66555012
- frontends-clippy.jsonl: a0bf04fac797a71e45e651d1491f500c3309c9d9a6a37d5cf9560913076970a2
