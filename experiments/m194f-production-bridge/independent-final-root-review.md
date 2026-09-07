# M194f independent final report and scope review

2026-09-07. **Bounded pass: no required correction found in the reviewed
report, rule checklist or M194f program paragraph.** This is a source,
provenance and claim review; it does not replace Zeno's actual-pixel oracle
or create another optical or quality admission.

## Frozen material reviewed

| Material | SHA256 |
| --- | --- |
| Root report, `docs/research/M194f-production-bridge.md` | `02524dfeb50dae71171aeed6ca34f5cef3d328cdb2a08335b3996bcadb798a6a` |
| `rule-checklist.md` | `4f82504d3c1b240a78858fa8f1292bf3a03f003c532d1db555adf6af6d673159` |
| September program, M194f paragraph reviewed | `f7d3cd64237e5253749100e61efed03c149796136bb2d2434405b965c2489464` |
| Zeno's `independent-final-report.md` | `9ca026635b610fdbe7af6549d89ae7caab7182802797b22a8cd1d4cf164dfece` |

The final actual result is `independent-delivered-read-1/result.json`, SHA
`87ecaec21d5e2a927660d26fe53bb31b7e7bcfbd4ac3a342dbb6b163f40ef8cf`.
Its externally pinned population index is
`29a30879638f4198b3ec02a09d2120d33d5b713ae357c6d2aeb5cb4dcc1bfc2c`;
build4 is
`b1930156c50817df7d801f3ff6585fb9f6b965f047adfdcc61e8520192c362bd`.
These hashes were read from actual files, not copied without comparison.

## Re-chosen checks and findings

**Population and repeated counts.** I reopened all eleven actual TIFF files,
checked their complete byte hashes against the final result and decoded their
IFD width/height fields directly with Python `struct`. All eleven hashes and
dimensions agree; all eleven resolved paths are distinct. The population is
five44x34 RGB files, one22x17 Gray file, three48x32 private RGB files and
two16x8 private Gray files. Four RGB files intentionally have the same bytes.
This is eleven files, not eleven independent scenes or noise repetitions.
The five private images were preflighted and then read again in the final
eleven-file pass; they are not ten distinct private images. The reports
correctly say that the focused and CLI executions repeat the same192
independent assertions rather than claiming384 independent cases.

**WB choice and actual null mechanism.** I compared the two complete
`baseline-count` and `red-wb-double-count` plans, choosing matching count-mode
arms rather than an off-versus-count comparison. Their only value differences
are `/wb_mode` and `/wb_f32/0`, from1.3333333730697632 to2.6666667461395264.
Frame WB, all input bindings, crop, geometry, noise and other configuration
are equal. This supports the intended single-setting intervention.
The recorded actual success counts/hook calls are off0/0, count1-per-frame/5,
placebo0/5, confidence2-per-frame/10 and red-double1-per-frame/5. Thus the
byte-identical baseline outputs accompany distinct active observer/reread
work, with an appropriate inert mode; they are not merely duplicate names.

The report correctly limits the WB acceptance predicate to each measured CFA
component and separately records large interpolated-component changes. Its
374/374/374/374 parity populations agree with the actual44x34 extent and
native offset(10,8). The positive/unclipped red ranges and signed one-code
residual are retained. The sampled-site predicate alone cannot prove WB
ordering. Our actual DN-valued MHC witness demonstrates why the rejected
all-pixel rule fails; it is explicitly a component test, not another TIFF or
an optical-quality score. No reported interpolated movement is relabeled an
image defect or accepted under a newly fitted tolerance.

**Confidence scope.** Genuine Gray output is reported as the permitted
input-rank codes, not calibrated optical confidence or independent depth
truth. Exact below/seen and sentinel behavior is tested by the separate
private rank fixtures. The manually unseen sentinel is not portrayed as a
measured missing-coverage event in the genuine stack. The root table and
checklist preserve this distinction.

**Source and timing.** All109 source-map entries still match their actual
file bytes. `git diff 9da113f5..77fc14bf -- crates` shows the new adapter and
only seven added lines declaring its test-only child in the existing
known-scene module. It does not show a production arithmetic/default change.
The original preregistration and amendment precede their implementations.
The amended build ran15:57:54–15:58:01 UTC, followed by focused/CLI controls;
source checkpoint77fc14bf is16:00:36 UTC. Private rendering began16:00:47,
private independent preflight16:01:28, genuine rendering16:02:05, and the
eleven-file read16:02:41. The report correctly says the checkpoint precedes
the final population. It must not be strengthened to say that this checkpoint
preceded compilation: the exact source-bound build came first.

**Commands and retained failures.** All four `python` command argument
suffixes printed in the root report match the actual records' interpreter
arguments exactly; the human-readable command uses `python` in place of the
recorded absolute interpreter path. Exact executable, cache options and
environment remain in the records and Zeno's reproduction section. The
first six launcher false acceptances, scheduler false acceptances, macro
failure, path-reader failure, unsupported exposure population and diagnostic
versus strict-clippy distinction remain explicit. Fresh cache prefixes are
recorded execution choices, not a general proof against every cache race.

## Accepted breadth and remaining limits

The report and program paragraph support a small admitted-CFA-to-shared-writer
integration pass. The actual22x17 and11x9 levels provide one Laplacian band
plus its base, and the analysis-grid probe has no measured floor band. The
source-defined fixed fallback is not mistaken for a commissioned measured
floor or three-band admission comparison. No noisy-repeat population was
run. The larger boundary fixture and independent noise-law commissioning
remain prospective; M194f does not clear M25 physical/optics gates or establish
occlusion-halo quality, alignment, calibration, noise reduction, performance
or SOTA. The constant/affine80-site value windows are not presented as full
optical-truth comparisons of the genuine scene.

The concrete read-only checks used Python `-B` to parse the named JSON files,
rehash all eleven referenced TIFFs and109 source entries, directly inspect
TIFF IFD dimensions, diff the two complete count-mode plans, and compare the
four printed command suffixes with `interpreter_argv`/`orig_argv`. Git history
checks used `git show -s --format='%h %cI %s'` on9da113f5, b0b55909,
b0bf94eb,77fc14bf and dfadf356, and the scoped crate diff above. Their outputs
were inspected without truncating the deciding populations. No frozen
source, prior result, compiled binary, CFA or TIFF was edited or rerun.
