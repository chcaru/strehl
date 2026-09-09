# Common-TIFF dimensions v2: implementation contract (draft)

2026-09-08. SOURCE ONLY. Root adopted this software scope after the completed
three-frame consumer and sampler repair. No fixture generation, build, test or
render is released here. The draft patch remains outside crates until root
closes the sampler's final current-source audit. Independent fixture/checker
authorship and a separate finite execution grant are required.

## Authority, migration and exact nonchanges

CLI stays: strehl-common-input --stack-manifest PATH --manifest-sha256 HEX
--report PATH --observer off|on|placebo. Non-stack M165 mode and its source file
remain byte-unchanged. The seven manifest keys remain schema, grid, color,
noise, merge, inputs, output; unknown fields remain errors.

- common-tiff-stack-v1: exactly three inputs and128x96, input cap256KiB,
  writer cap128KiB, final/stage cap64KiB. No previously forbidden count/grid is
  silently admitted. The old TIFF description/software strings, profile,
  quantization and sampling/merge order remain literal; the legacy positive
  must retain whole-TIFF bytes. Executable/path references in receipts naturally
  differ. Invalid array cardinality becomes an explicit bounded count refusal
  after JSON parsing, rather than serde's fixed-array length error.
- common-tiff-stack-v2: exactly2..8 inputs, each axis64..512 inclusive,
  checked pixels<=262144. A checked product and exactly four level_sizes(...,3)
  entries are required before image decode/folding. N0/1/9, invalid schema,
  bounds/overflow and wrong channels/coordinates refuse before input decode.
- Both use channels RGB, identity-common-rgb-pixels, the exact admitted548-byte
  linear-ProPhoto/D50 ICC, RGB16 finite-clamp-round-half-away-v1 output,
  unchanged input provenance schema common-tiff-stack-input-v1, duplicate
  id/path/whole-file rejection, and the existing explicit Merge::fixed.
- Both admit only synthetic-noiseless-v1 and
  synthetic-independent-rademacher8-v1. Covariance is RGB16-code-squared:
  zero or diagonal64, with actual proxy variance0 or24. The proxy remains
  (R+2G+B)/4. Same white BandGain values are injected; no local scene estimate,
  new band count, resampling, alignment, exposure, profile conversion or RAW
  intake. Core, parser, native writer, Cargo and defaults are untouched.

Manifest JSON remains64KiB; existing path/id/hash/argv bounds remain unchanged.
Resolve declared paths/metadata before visits, but open/parse each TIFF on its
own visit. Late last-frame shape/hash failure must retain exactly N-1 prior
fold receipts and refuse output admission. Do not pre-read the full pixel
population to simplify failure handling.

## Finite byte contract

P=checked(width*height), N=admitted count. For v2:
- Per input TIFF extent<=6P+65536 bytes, with a positive declared FileRef.
  Aggregate declared input extents are checked before visits against
  N*(6P+65536). Maximum per file1638400; maximum aggregate13107200 bytes.
  This is a file extent bound, not a promise that every TIFF at that size is
  structurally valid. Existing strict parser and32-entry preflight still apply.
- Encoded output and its simultaneous stage each<=6P+65536. RGB16 payload
  alone is6P, at most1572864 bytes. Bound the actual writer's seeks/writes;
  do not only inspect the final buffer.
- Eight frame receipts maximum, each16KiB; canonical final and simultaneous
  JSON stage each192KiB; initial incomplete4KiB. Manifest input64KiB, ICC548B
  and actual executable128MiB caps are retained separately.
- Worst owned output family:2*1638400 +8*16384 +2*196608 +4096 =3805184 bytes.
  Raw stdout adds at most196608, total4001792, leaving192512 below4MiB.
  This subtotal excludes input fixtures, executable, sources, outer process
  evidence and raw stderr. The release ledger must allocate those separately;
  it must not call this subtotal a complete execution budget.
- A v2 pre-publication report-size check leaves bounded room for the output
  FileRef/status change. Any encoding, write, final report or stdout failure
  retains the initial incomplete/refused state and actual nonzero disposition.
  A saved image alone cannot certify completion. Existing create-only hardlink
  publication and exact readback remain; no overwrite or unbounded retry.

The final192KiB is a hard ceiling. Independent source/metadata construction
must establish a normal N8 receipt fits before release, including plan, eight
actual consumed rows, eight frame refs, runtime/encoding/observer and bounded
error text. If it does not fit, fix the finite layout before running; do not
silently truncate rows or drop association. No universal filesystem guarantee
is claimed by an allocation bound.

## Storage, execution and receipt semantics

Runtime dimensions feed merge construction, workspace levels, parsed-grid
checks, proxy/variance extents, observer population and TIFF writer. Runtime N
feeds frame paths/collision checks and completion count. The fold order,
workspace.next_frame, actual add_frame_with_gain and fixed two-thread pool
remain unchanged.

At most one encoded input and its u16 decoded frame/f32 preparations live with
the reusable merge/workspaces. The parser temporarily copies payload bytes;
the writer temporarily owns u16 samples, payload bytes and encoded output.
Include those overlaps in the resource review. No all-frame pixel collection
or aligned-frame materialization. Per-frame input/proxy/variance before/after
hashes remain actual. Only bounded metadata grows with N.

The request-level initial incomplete schema remains
common-tiff-stack-incomplete-v1 because it precedes authenticated parsing.
After valid v2 manifest admission, final schema becomes
common-tiff-stack-result-v2 and frame receipts common-tiff-stack-frame-v2.
All existing field meanings remain; plan binds the declared grid/count,
consumed/frame_receipts lengths and merge_frames prove actual complete N,
encoding width/height/ICC prove actual output association. Refusal before
manifest admission retains the initial v1 envelope and the exact bound manifest
when available; do not mistake the envelope version for successful v1 intake.

On observes actual four shared per-level denominator arrays after each fold;
off retains none, placebo allocates the same four-row shape without reading
merge. Level sizes follow ceiling reduction, not floor division. Base is still
excluded from a claimed mixed Laplacian population. Output on/placebo shadow
extent becomes3P, off none. Whole-TIFF/pixel identity must commission both
diagnostics on the independently chosen new geometry.

## Patch boundary and required independent choices

Only common-stack/manifest.rs, mod.rs and writer.rs need a patch. Expected
changes: bounded Vec intake plus schema-specific layout; dynamic frame paths,
core/check/observer counts; bounded schema-specific writer geometry/tags/cap.
files.rs, entry dispatch, core and public parser remain byte-identical.

Independent author chooses exact fixtures/commands and falsifiers. Needed
coverage: N2/interior/N8; odd non-square and minimum/maximum grids; exact
distinct-constant fold result plus all contributor identities; identical
address/color odd-edge full-grid truth; newly shaped mixed-noise off/on/placebo;
N0/1/9 and extent/bounds refusal; late N-1-prefix failure; one archived v1
positive. Do not present arbitrary small N as potency for unrelated native
deep-stack gates. No quality, physical calibration or external comparator
admission follows from these software controls.

## Draft review clarifications

Count is checked before grid validation; Grid.width/height remain u32. A JSON
integer outside u32 fails serde before layout; admitted-axis bounds reject huge
in-range values before the checked multiplication. The overflow guards and
aggregate<=N*per-file-cap check are defensive arithmetic, not independently
exercised controls when all preceding predicates hold. Negative tests must name
the predicate they actually reach.

Only incomplete/stage companions are prechecked during request initialization.
Frame-companion freshness now follows authenticated N in manifest parsing.
This avoids reserving an undeclared frame2 in a v2 two-frame run. A legacy
preexisting-frame refusal may consequently retain an initial incomplete receipt
where the old initializer refused earlier; positive TIFF semantics are unchanged.
The v2 pre-output metadata check is176KiB, reserving16KiB within192KiB for the
bounded output reference, status and error suffix. Independent normal terminal
sizing is still required before release.
