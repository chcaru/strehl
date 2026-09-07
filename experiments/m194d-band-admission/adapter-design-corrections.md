# M194d adapter review corrections

All entries below precede any M194d image output.

- The first `run-matrix.py` draft globbed all local Python files for provenance.
  Independent review identified that this would bind unrelated review scripts
  and prevent useful concurrent verification. It now binds six explicit root
  adapters/readout helpers. Included external Rust files remain bound.
- The first draft checked source bytes at entry and batch completion, while
  the preregistration requires each invocation. A shared source-map guard now
  runs immediately before and after every child invocation. Changed sources
  cannot leave a successful complete matrix. Failed child logs remain recorded.
- The original M194b numerical `score.py` is imported from its unchanged path.
  The versioned reader adds the exact admission mode/schema/environment/test
  entry and parent-driver bindings, plus prospective sparse residual summaries.
  It does not remove candidate fields before validation or rewrite records as
  legacy outputs. `adapter-lineage.json` retains each original byte hash and
  the initial mechanical edits; later edits are visible in the final source.
- Explicit hard-floor execution is called off-mode identity. Actual default
  resolution is checked separately in Rust, and one original M194b entry is
  rendered separately. The forty explicit off-mode outputs alone do not prove
  that an unselected default was exercised.
- The root sparse reader uses its registered linear quantiles. The independent
  reviewer may compare a predeclared nearest-rank convention; their expected
  difference is not a calculation defect or another independent noise repeat.
