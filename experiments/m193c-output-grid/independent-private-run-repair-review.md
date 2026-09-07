# M193c private producer and build — independent repair reread

2026-09-07. **SOURCE ONLY / UNEXECUTED.** This note independently rereads the
root's repairs against Curie's held `independent-private-run-review.md` and
the previously reviewed process/build sources. No producer/helper import,
child process, build, precision calculation, private image or RAW operation
was executed. Neither the earlier review nor its original-source findings
are rewritten.

| Final source | Bytes | SHA256 |
| --- | ---: | --- |
| experiments/m193c-output-grid/private-grid-run.py | 22358 | 4361b01a2d7a6b8a1eba0d6cd2c06b08abfd270184b3e0eec18bf721f39195cd |
| experiments/m193c-output-grid/bridge-build.py | 14682 | c1c3439266a9720137a280822e065f4b193372dd599cf8398d78ed1e0ec73261 |
| crates/strehl-cli/src/merge_cmd/production-truth.rs | 12917 | 11aab6eb649ee6dacd67abe7083b1e4ea7dfda40f6191ae476170e2448094c44 |

The derivative include itself is separately reviewed at Rust SHA256
`db2a4d0c36d3f0778481e8a9837feef1c2651258865799bbd143b6bb0840eecd`
in `independent-derivative-source-repair-review.md`. The unchanged process
helper is `1dba8d87c8818aecf98078d1a926e5ff9c059a7d242cf5c46fcc962f14dfc5ab`;
its actual eleven-control evidence is independently inspected in
`controller-controls-3-independent-read.md`.

## Producer repairs and additional findings

Curie's original R1 is corrected: `Attempt.track` checks actual bytes and
constructs the ledger from the supplied expected SHA/length, rather than
replacing that expectation with a second file read. `Attempt.read` retains
the same bounded parsed-buffer binding. Recursive finite checks now reject
overflow JSON numbers as well as named nonfinite tokens and duplicate keys.

R2 is addressed within the producer's explicitly limited budget scope.
Inventory visits the owned output tree, including hidden/partial child files,
and records observed growth separately from immutable completed FileRefs.
The active launch record is attached before the child call, so a later
failure saving its receipt leaves that command/observation available in the
negative parent record. Missing/nonterminal child accounting sets an
explicit incomplete flag and cannot silently supply a full CPU remainder.

This reread found that the first repair still assigned successful children
to `failed_launch`. A later plan or receipt parse failure could therefore
mislabel the successful child. The final source uses `last_launch` for every
saved child and assigns `failed_launch` only for a failed child status. If
receipt persistence itself fails, `active_launch` remains attached. These
distinctions preserve the observed child result separately from a later
parent interpretation/persistence failure.

R3 now renames an existing canonical index to `run-index.json.rejected`
before attempting negative publication. Original errors and finalization
errors remain in the negative record; secondary refusal-publication errors
are retained on stderr if the file cannot be saved. No successful revocation
is claimed when the rename itself fails. The parent must still reject an
actual nonzero exit and preserve its log.

The first version of that fallback bypassed the normal 4 MiB JSON bound and
write reservation. This reread reported the gap. The final source checks the
same finite JSON bound, inventories the retained tree and reserves the new
negative write before attempting it. A refusal at this stage remains a
parent-log outcome, rather than permitting an unbounded fallback file.

R4 is corrected: the declared receipt output goes through `Attempt.track`
before normalized path comparison to the independently collected TIFF.
Thus a false declared SHA or length is not replaced by an actual-file hash.
The receipt's plan object, SHA and byte length are all compared to the
actual saved plan. No pixel-reader result is inferred from these checks.

This reread also found a release-entry variant of R1: the initial validated
release buffer was followed by fresh `ref(a.release)` reads when constructing
the result and ledger. The final source constructs that FileRef from the
already checked raw SHA/length and resolved path, then rechecks that fixed
identity through closure. A changed release cannot be silently rebound at
ledger creation.

Required source names now include the actual producer, process helper,
build loader and Job helper. The compiled source map must be included in
the execution release and agree with the actual current include scan.
Controller prerequisites require the exact eleven mode identities/order,
passing terminal zero-active observations and source equality; their bound
release, artifact files and source bytes are reopened. Build prerequisites
require both compiler and listing process success with terminal zero-active
accounting, actual original/copied executable identity and the expected
test names in the actual listing. These are bounded prerequisite bindings;
they do not independently rerun the original process commission.

The original ten-plan, then precision-component, then ten-render schedule
remains intact. All actual plans are retained before the component and
pixel phases; individual saved plan identity is consumed at each render.
There is no implicit retry, favorable subset, extra product output or
changed numerical tolerance in these repairs.

## Explicit encompassing-budget requirement

The parent's accepted R5 disposition is a separate outer private campaign,
with one encompassing Windows Job and one 600 CPU-second / 1200 wall-second
epoch across this producer, the independent readers and the derivative
private children. It must inspect the complete 128 MiB artifact inventory,
including failed/partial products and its own terminal records. This
encompassing campaign is required before final private-stage admission.

The reviewed producer has local safety checks only. Its emitted work scope
explicitly says final admission requires that encompassing Job and inventory.
Its local byte figure combines observed child-file growth with full parent
write reservations, including failed writes. It is not an exact count of
all historical bytes written or an encompassing retained-file total; the
`byte_accounting` text declares this distinction despite the legacy field
name `cumulative_written_bytes`. Its CPU/wall values are sampled before
final persistence, not at process exit. None can reset the outer allowance
or replace the outer terminal observation.

Consequently the producer's `COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED` means its
fixed output population completed and passed these local checks. It cannot
admit the private campaign, a derivative or the later native stage. A failed
or incomplete accounting record cannot be carried as a trustworthy remaining
budget. The outer source/command implementation and actual run remain
separate work; this source review does not claim they already exist or pass.

## Build/include delta

The new `m193c_registration_derivative` module includes the reviewed Rust
file through the same explicit `CARGO_MANIFEST_DIR` form handled by the
build source scanner. The parent module is test-only; this adds the two
ignored derivative entry points under the planned namespace without changing
the product CLI. The scanner's recursive known include/include-bytes forms
must bind the derivative's included protocol bytes as well as its Rust source.
It remains an explicit-source scanner, not a general Rust/cfg parser.

The build now requires terminal zero-active Job accounting for both actual
compile and actual copied-executable listing. It retains the zero-exit,
visible `Compiling strehl-cli`, exact package/main/manifest/test-artifact
association and exact unique listed-test requirements. Original and copied
executable identities and final source/input/log bindings remain mandatory.

An existing positive build result is renamed to `result.json.rejected`
before a fallible refused replacement. The original finalization cause is
kept and secondary persistence failure is logged, with nonzero final exit.
This reread found the same initial release-rebinding pattern in the build
controller; its final source likewise records the authenticated raw SHA and
length rather than hashing anew to establish the accepted release identity.

The added software context requires one actual compiler-log
`build-script-executed` message for the same exact `strehl-cli` package and
one `STREHL_BUILD_ID` value matching twelve lowercase hex characters with an
optional `-dirty` suffix. The build record retains that complete message and
derives `strehl 0.0.0 (stamp)` from it. I separately read the owned `main.rs`
`SOFTWARE` expression and its package/build-ID concatenation. This supplies
an expected software context from compiler evidence, rather than learning it
from a subject plan. It does not make the build hermetic or replace source
and executable hashes. Output-mode-specific TIFF stamping must still be
checked against the actual writer contract rather than assumed from the
plan's build string.

**Disposition:** no further blocking source defect found in these final
producer/build/include deltas. They are ready for the parent's exact source
and build-command freeze. Actual compilation/listing, producer metadata
fault controls, private pixels and encompassing campaign admission are not
established by this reread. No image or RAW execution is authorized by this
document alone.
