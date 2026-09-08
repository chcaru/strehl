# Independent source review: explicit camera-channel white authority

Status: VERIFIED source correspondence and prospective control design. No
blocking source defect found in the held successor. No successor helper,
control, RAW read, TIFF parse, native child or registration was executed by
this review. The two previous native attempts remain REFUSED; this is not
an admission of their images or a successful future nine-frame result.

## Held sources

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `independent-sensor-white-derivative-read.py` | 76,606 | `6a318b439d1b9c5cb460808fc1388c7723d66a5adaf63b3303a6c791568a4bb8` |
| `native-sensor-white-derivative-run.py` | 54,522 | `da1afc635851eaa8b60e29c1a6e677493b782d9e5e9cad19bad509d543de3ea1` |
| `sensor-white-reader-preregister.md` | 13,341 | `715c53c13002d3f4bb1cebaca0ca841459cda352599a202042d969d488fabb23` |

Comparison bases are the held sensor reader `eeed1ea3c45927f81e34d99ca31dc57715f898b718dfef26dcf0ea2cddf3fbe7`
and sensor parent `10ec80290bc7bb5c2e7fc140cb831d539e517844281b40b372055b409113a1ed`.
The reviewer read both complete diffs, the full new specification, the added
helpers and their actual caller, the parent result checks, the existing
refusal-record helper, and the owned primary level-selection/normalization
source. No forbidden third-party implementation was opened.

## Independent basis for the authority choice

I independently opened the official
[RawPy API documentation](https://letmaik.github.io/rawpy/api/rawpy.RawPy.html#rawpy.RawPy.camera_white_level_per_channel).
It describes camera-channel white as four integer saturation values from RAW
metadata, with `None` when unavailable. It describes generic `white_level`
separately. Neither description prescribes a precedence rule or requires the
two properties to agree. The page reports version0.27.1; the held runtime
remains0.27.0. This documentation check is not an execution-runtime change.

The successor therefore makes a defensible, explicit method choice: compare
the existing primary scalar to complete independently exposed camera-channel
metadata, requiring a common value at all used CFA indices. This chooses an
authority by its declared metadata role, rather than accepting whichever
property happens to equal15,360. It is stricter than accepting a generic
fallback, ignoring disagreeing channels, or treating absent metadata as a
match. The public API alone does not prove this comparison is a physical
calibration, so the returned physical-calibration and primary-metadata-
presence claims correctly remain false.

Owned `strehl-raw/src/lib.rs` selects the first resolved primary white value
and can default to u16 maximum. The unchanged derivative consumes that f32
scalar in its existing normalization. This review does not establish the
primary decoder's underlying metadata presence or infer its internal
selection semantics from a matching number. Requiring camera metadata here
does not change the primary's pixels, scalar, normalization or fallback rule.

## Typed consumer and unchanged arithmetic

`native_white_authority` requires a four-element list of actual integer CFA
indices in0..3 before deriving the used set. It requires the retained generic
white to be an actual positive integer within u16 range. Camera metadata must
be a four-element list whose entries are actual positive integers within that
range; `None`, bool, float, zero, negative, missing/short and malformed values
cannot be repaired by conversion. The native acquisition path now retains
the public properties without the old `int()` and `list()` coercions.

All used channels must equal the selected value, which must exactly equal
the already validated primary scalar. The selected value is taken from the
used set only after its nonempty index contract; equality across the used
set prevents a first-value reduction from hiding disagreement. An unused
channel remains structurally required and typed, but is not falsely called
a consumed channel. The current four-index RGGB records use every entry.
Source white still goes through the inherited finite real-number and
positive-range checks; bools are not accepted as primary scalars.

The explicit eleven-field witness retains generic, camera, selected and
primary values, the actual used indices, the generic-match boolean, method
and selection identifiers, forbidden fallback and both false claim flags.
The boolean is descriptive, not an alternate acceptance branch.

`validate_native_metadata` keeps exact black equality at used channels and
the same R/G1/B gains, local-G1 division and
`2**-20 * max(1, abs(target))` WB predicate. AST comparison confirmed that
the black loop and every WB statement through its comparison are copied
unchanged. White authority is checked earlier in this new helper, so an input
with several independent metadata faults need not fail in the old order;
this is not a claim of identical multi-fault exception ordering. On accepted
metadata, black/WB arithmetic and thresholds are unchanged.

The original `validate_independent_metadata` remains byte-structure identical
and continues to serve the old private branch. Its previously missed generic
white requirement is preserved as historical source, not relabeled as the
new method. The native path calls only the newly named helper.

## Failure power of the fixed controls

There are ten ordered groups and23 intended calls to the actual
`validate_native_metadata` helper: seven single-call groups plus malformed
camera8, generic5 and CFA-index3. Their literal source/metadata values are
independent of the failed image: camera/primary12,000, black64 and WB
`[3,2,5,2]`, giving `[1.5,1,2.5]`. This is a source count and prospective
design review, not an observed executed count.

The valid and restored cases use generic16,383 while requiring the full
literal camera-authority witness with selected12,000. Retaining the old
generic equality would fail these positives. The critical opposite case
sets generic12,000, exactly matching the primary, while all camera channels
are11,000. It must refuse specifically at selected-camera equality. Generic
rescue or an either-property-match rule would return normally and fail this
control. The mixed used-channel case keeps three channels12,000 and makes
one12,001, requiring the distinct mixed-channel refusal before scalar
comparison; a minimum, first or any-match reduction is insufficient.

Absent camera metadata has a named no-fallback refusal. The eight camera
shape/type/range rechoices, five retained-generic rechoices and three index
rechoices all enter the real helper, not a separate imitation validator.
Black and WB faults begin with valid camera authority and therefore reach
their preserved predicates. Source and metadata deep copies are compared
in a `finally` block on successful and refusing calls. Mutation of either
input or a budget error cannot be accepted under an unrelated expected
metadata-refusal message.

`rejected` catches only the subject invocation's ValueError and requires the
exact expected message. Its assertion that an expected refusal did not occur
is outside that exception handler. The outer unchanged `control_call` is
invoked with no expected refusal; an error from a failed internal expectation
therefore remains a failed group. This avoids the earlier class of control
that accidentally treated its own failed expectation as successful subject
refusal. A group row is attached before calling it, so a failed group and
the original exception survive; successful malformed groups retain all their
ordered attempts. No new TIFF fixture or statistical population is needed
for these scalar metadata checks.

The native caller runs the unchanged eight domain controls, then these ten
white groups, before obtaining snapshot bytes for rawpy. They use the same
budget, with no reset. Future actual evidence must show all groups and
their nested attempts; this source verdict does not manufacture those PASS
records or predict what the remaining eight real files contain.

## Parent, request and result agreement

The new release/scope, native request, per-frame result and parent result are
explicitly versioned `sensor-white` identities. The parent requires the exact
new reader filename and source binding. Its complete reader result adds
`white_controls` to the closed key set and requires ordered exact11 native,
8 domain and10 white group IDs, true PASS fields and dictionary evidence.
The reader's and parent's literal tuples were mechanically compared and
are equal. Native check6 is now truthfully `scalar-black-camera-white`;
the other ten native IDs and all domain IDs are unchanged.

Actual source/runtime/request/argv associations remain the inherited strict
boundary. The new specification is required by both sources and copied with
the reader's small execution-source snapshots. Other file refs and mixed
repository/absolute path conventions are unchanged. A failed result may
retain only its actual completed prefix; the parent cannot admit it without
the exact complete populations and successful child exit.

The parent still reuses only original0's original historical primary after
the same full-nine-plan byte/content comparison and three reuse controls.
It does not reuse either failed independent reader. The other eight primary
outputs and all nine readers would be fresh, if the next attempt completes.
First refusal still aborts the remainder, retains historical files and
reports unvisited inputs. Source/input/dependency observation, cumulative
resource accounting and terminal publication are unchanged. The new controls
and extra retained source/spec bytes are charged within those limits.

## Mechanical checks and disposition

Read-only `git diff --no-index` was run for both old/new source pairs. An
additional stdlib-only AST/hash script ran on stdin using the pinned Python
with `-B -`; it never executed a subject AST or imported a subject module.
The reader changes only existing definitions `release_entry`, `native_run`,
`initial_result` and `main`, and adds exactly `native_white_authority`,
`validate_native_metadata` and `run_white_controls`. Its other43 definitions
are identical, including the old validator, private helpers, domain helper,
runtime, bounded readers, Budget and finalization. The parent changes only
`reader_authority`, `independent_result`, `run_one` and `main`; its other24
definitions, including reuse and file/budget/process helpers, are identical.
The `run_one` body differs only in the new request schema string.

No source repair is requested. Root still owns the prospective exact release
and actual execution, including full prior cost from both refusals and the
probe. Old native and sensor-native failures stay REFUSED. This successor
does not grant existing coverage readers compatibility with its new result
schema, certify a common-TIFF route, assert alignment accuracy, or qualify a
physical sensor saturation level. Those are outside this source review.
