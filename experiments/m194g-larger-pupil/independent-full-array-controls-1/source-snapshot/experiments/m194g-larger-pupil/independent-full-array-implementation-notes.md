# Complete-array reader implementation notes

2026-09-07. Source-only implementation under the committed full-array design
and accepted authority schema. No numerical import, private-control execution
or complete-array reader command has run for this pair. The exact source
hashes and syntax-only command are in `independent-full-array-static-1.json`.

The new reader imports only the separately pinned independent component
reader's file/schema/provenance utilities, after the external execution gate.
It imports neither optical implementation. Full-author work validation is
explicitly separate from the component batch's cumulative budget: each frame
starts with zero current point/node counters, increments must match cumulative
deltas, and the five-frame totals and clocks do not reset. Reference counts
remain cumulative under the existing reference budget. Refined diagnostic
ceilings follow the frozen integrator arm; indicator sum and cell-delta
consistency are checked independently of scalar error.

All25 scalar files and every author's branch/index/four-column diagnostic
payload are opened through bounded same-buffer NPY reads. Actual file
identities across the entire25 are distinct; equal bytes in distinct files
remain admissible. Every released supplemental input stays in the same live
hash ledger as the deciding data through final publication. The reader keeps
one frame index's five method arrays at a time and uses a weak unique-backing
ledger for named arrays. That ledger is not a process-RSS measurement.

`compare_population` is the actual five-frame/three-author-arm schedule used
both by verify's streaming loader and by the private pooling destroyers.
`validate_frame_work` is likewise shared by the actual frame reader and the
reset/delta controls. Root caught earlier test-only loops and a standalone
zero-current-counter check that did not exercise these real choices; those
were corrected before execution. Root also caught the initially discarded
bootstrap input ledger, incomplete cross-arm alias check and unbounded private
release bootstrap read. The source now handles each explicitly.

The private suite has an expected79 checks, including the genuine component
entry companion, separate max/RMS faults, actual NPY files, coherent invalid
diagnostics, the shared population/reset paths, typed metadata, clock/backing
limits, all25 file-identity aliases and publication failure. This is a static
count, not an observed pass. Private publication cases contain nonexistent
optical child paths and an explicit private notice; they only commission the
writer/schema/refusal mechanism. They must never be supplied as genuine float
authority.

The actual success comparison has closed top-level fields:
`schema`, `status`, `admitted_inputs`, `render_results`, `comparisons`,
`refinements`, `descriptive_subsets`, `frame_populations`, `private_controls`,
`band`, `authority_scope`, `error`, `finalization_errors`, `invocation`,
`execution_release`, `sources_before`, `sources_after`, `input_bindings`,
`resources`. The emitter-facing `admitted_inputs` and `render_results`
subrecords follow the accepted authority supplement exactly. The corresponding
authority points to the comparison; the comparison never points back to the
authority. A failed final persistence check revokes the actual success child
and authority, while preserving the failed publication attempt and original
error. Partial numerical results cannot issue authority.

The new commands use execution scopes `full-array-reader-controls` and
`full-array-reader`, within the existing execution-release record schema.
Controls require the genuine component-verification path/hash and their
execution-release path/hash. The complete reader also requires all five
role-specific actual result paths/hashes and the completed new private-control
record path/hash. Root freezes the exact command arrays and actual external
digests before execution. No old reader or numerical source is edited by this
implementation.
