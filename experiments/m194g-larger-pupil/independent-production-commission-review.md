# Independent twelve-output controller review

2026-09-07. Static source/design review only. No import, child, build, image,
control or quality calculation was executed by this reviewer. The previously
reviewed launcher, its design and its review were not edited.

Reviewed `production-commission.py` SHA256
`2bb9a7c66f78eb20f123c8dcb2c2a693ef08a9d0bec0b3b11711d9dd528997b4`
and `next-production-commission-design.md`
`fdfce0d8482a76209c67e13b7475253ae16d782f43ab4c24569833a00f0fa4e1`.
The launcher dependency at this read was
`756a9c71da8c5f6dfaf3231e386ec09c83902c8f2aedb1ec23b5eb01b764635c`.

## Rechosen consuming boundaries

The literal loops reproduce the design's exact twelve rows: eight scene/state/
admission combinations, textured701 HardFloor count/placebo, then textured
noise-off HardFloor original0 and original4. Row6 is the shared off companion
for rows8/9. Observer mode is part of the identity and is sent explicitly in
both child phases. There are no retries or a completion path for a subset.

All24 exact command/environment records are persisted before the first child.
The only deferred render value is its own actual plan SHA. The controller
completes and reopens all twelve plans, checks their actual scene/seed/subset,
original/local/probe indices, coordinate gauge, mode and executable binding,
and checks common output geometry before reaching the first render loop.
Each actual launch's argv/environment must match the predeclaration; a planned
label cannot replace the actual child record. The render consumes the exact
saved plan through the shared Rust/launcher path.

The externally pinned release is checked before the command dependency's bytes
are compiled and executed. `recheck()` combines the complete released source/
input recheck, actual `Build.finish()` and the externally bound noise gate.
The same function is used by each child and by final publication. Thus the
copied/original executable and actual compiled source/include set are checked
again through the final twelve-output index write. Root supplies the passed
private bridge read as an additional exact released input; this controller
rehashes it but does not independently reinterpret its scientific/control
status. There is intentionally no final bridge gate dependency yet.

`work.failed_launch` is assigned as soon as a child observation returns, before
status, artifact, command/environment, geometry, floor-log or identity checks.
It is cleared only when that full row's checks finish. Earlier completed plan
and image rows are preserved. A child exit0 followed by artifact refusal keeps
the actual launch and separate parent error. If a failure occurs before a
child can be launched, no nonexistent child completion is invented.

Every rendered row's measured-floor prefix must be finite/nonempty, have at
most two printed values and carry the actual selected-frame contribution
count. This is a terminal witness, not a reconstructed full-precision beta or
calibration. Distinct actual file identities are required across plan,
plan-launch, receipt, TIFF, render log and render-launch refs. Shared launcher
checks bind the returned TIFF's actual path/hash/length to its receipt.
Independent TIFF pixels, observer equality, coordinate oracles and eventual
bridge admission remain root's separate consumer work.

## Separate late launcher finding

During this reread Zeno identified that standalone `production-command.main`
passed only `authorize.recheck` to final publication, whereas this twelve-row
controller already includes `Build.finish()` in its final `recheck`. I confirmed
that distinction; my prior launcher source review missed the standalone gap.
The actual23 private launcher controls remain evidence of what they exercised,
not a discharge of that missing final executable/include-set check. Any narrow
standalone repair and its affected release remain separate from this review.
No held launcher file was edited here, and the gap does not occur in the
twelve-row controller's finalization path.

## Disposition

No additional blocker was found in this fixed twelve-output controller. It is
ready for root's exact source/command release once the intended prerequisites
are bound. This is a static release-readiness judgment, not an executed matrix,
bridge, noise, image-quality or SOTA claim. The distinct38 quality population
and its association adapter are outside this verdict.
