# Night checkpoint: user-requested pause

The user requested a stopping point, a remote branch push and local disk cleanup.
The overall multi-stack objective is **paused, not complete**. All research lanes
are stopped; no new image or geometry experiment is scheduled. Resume only when
the user asks. The implementation is on `codex/multi-stack`. Remote `main` was
fetched again and remains `c149e52834fc1c86c2af0fe022713c39fa25f33c`, the base used
for this work. The prior source checkpoint was `ef65505013585abcc86b1410e4bf902bf34ed479`.

## Current implementation and validation

Core/CLI/UI changes include multi-stack modes, optional primary selection for
simple modes, independent views, contribution/focus evidence, bounded original-CFA
reconstruction and guarded mosaic support. The ordinary stacking route remains
separate. Public documentation is `docs/multi-stack.md`; the detailed outcome
matrix is `completion/review/requirements-completion.md`. Functioning controls do
not by themselves close the still-unrealized photographic outcomes.

Product17 is the last archived release build. Its CLI SHA256 is
`036042897ce3bf4034f8c97db9859ebdb1b7b175aac7f246ba1602e54f86355f`; UI is
`2578c1a7a377e6fb8d52a6cdb0b284936b4b49e1264bc096371072f18916d632`.
Source archive and build identity are in `outputs/multi-stack/completion/product-17`.
The final source adds native sensor export and the research omission control
after that archive. **Product18 has not been built or photographically tested.**

MEASURED final source checks:

- `cargo test --locked -p strehl-cli -p strehl-ui session -- --test-threads=4`:
  fresh compilation,160 CLI tests and64 UI tests passed. Receipt
  `outputs/multi-stack/completion/night-session-controls-01`,57.806s,
  sampled6.941GB private,4Cargo workers. This includes actual cache-reader poison,
  missing-cache and omission controls, native stripe/binding tests, and UI reopen
  and tamper controls.
- Unchanged current core source: `cargo test --locked -p strehl-core --
  --test-threads=4`,955 passed/4ignored. Receipt `product17-core-full-01`,73.662s.
- Scoped `rustfmt --check --edition 2024 --config skip_children=true` passed for
  the final consumer, cohort, command, native-output, binding and UI import files.
- Strict CLI clippy was executed and **does not pass**:30 diagnostics map to
  unchanged remote-main spans and1 to unchanged prior multi-stack code; no new
  source diagnostic. See `night-cli-clippy-01` and
  `completion/review/night-cli-lint-audit-01.json`. Strict core similarly retains
  43 remote-main diagnostics. The UI strict run retained an unchanged unused
  function diagnostic and an incremental-cache hardlink/copy infrastructure
  warning; it is not reported as a clean strict pass.
- `git diff --cached --check` passed after removing two final blank lines.
  `python scripts/corpus_lint.py` reports 16 existing violations in unchanged
  research documents (seven table-width, seven table-code-pipe and two missing
  final-newline findings). These documents are identical to `origin/main`.

## Latest useful photographic result

Three complete7004x4668 bee photographs compare legacy4pair grouping, broader
geometry proposals16pairs, and32singletons. Original identities, calibration and
geometry match exactly. The full legacy photograph and linear-master pixel bits
match product16. All full TIFFs are finite and all publication bindings verify.
Independent review covered complete scenes, all27 fixed384pixel witnesses and
the existing two single-pass references. No new conspicuous seam, color break or
hair/facet erasure was found in those views.

A separately frozen baseline-only shadow display shows visibly less fine color
grain in both preselected background witnesses for the broader-pair result.
This is a bounded appearance benefit, **not** measured temporal sigma/SNR, PSF
equivalence or permission to broaden generic focus groups by default. Synthetic
PSF and unequal-noise counterexamples remain. The proposal flag is still hidden
research functionality. Full results reside at
`outputs/multi-stack/overflow/repeat-proposals-17`, physically on D:.
See `completion/review/repeat-proposals-17-photographic-review.md`.

## Ready source; execution still due

The optional native CFA master is now emitted with contribution diagnostics.
It preserves the exact signed f32 native merge before demosaicing, white balance,
display exposure or later RGB reconstruction. The typed fourth output is sealed
and verified on UI import/reopen; legacy three-file simple and eight-file mosaic
contracts remain supported. Actual new-binary export on/off photo/master equality
and a real desktop import/reopen still need execution.

The hidden `--omit-acquisition` research control is implemented and tested.
The next conditional reference comparison omits globals
17,18,21,22,25,26,29,30: **16A+8B retained**, not12+12. All32 originals retain
identity/metadata checks and their saved geometry ancestry. Retained pixels load
only from existing CFA cache; no RAW decoding, omitted-source gather, focus,
precision, reconstruction or reproducibility path is allowed. Full-cohort scale
hint parity is checked before the research adapter recomputes retained hints.
`session-align.rs` remains byte-identical to archived product17, SHA256
`a805c794a2b2dc40b4b25721ca2302b4582512ad20c6f42f1ff7c6b4a857c4f7`.
The proposed24-source comparison has **not run**. Its output would be conditional
empirical agreement with withheld acquisition values, not unbiased risk, because
the geometry previously used all32 captures. See the frozen
`completion/review/repeat-proposal-withheld-plan.md` and cohort source review.

## Other active research checkpoints

Mosaic remains unqualified on the current real marigold pair. Focus-based held
nomination increased independent native held sites1→11, but placement errors and
coverage still fail the unchanged bars. Focus-matched FIT and mixed controls
remain negative. A dense-FIT research test harness compiled at the stopping
boundary; its six new controls and experiment were **not run**. No mosaic photo
was fabricated or accepted from these failures. See
`completion/mosaic/checkpoint-2026-10-29-night.md`.

The original-sampling forward observer has controlled synthetic positives and
adversarial failures. Recorded bee geometry still has0/8 completely qualified
synthetic cohorts under the fixed variance bound. It has read no new real pixels
and grants no product/SR admission. Preserve all failed spline and cosine model
results. See `completion/sr/repeat-forward-results.md` and
`completion/review/sr-next-instrument-review.md`.

Useful aperture, appearance-layer, independent-view and interleave outcomes from
earlier complete-image reviews remain retained. Stronger HDR, stitching and SR
outcomes remain open. The preceding ordinary299 regression was fully pixel-exact;
repeat it with the eventual final release, after outstanding integration changes.

## Storage and restart

The task owns a D: output root at `D:/codex-work/multi-stack-2026-10-28`, exposed
through `outputs/multi-stack/overflow`. Night cleanup verifies every byte of the
85.3GB mosaic cache copy by SHA256 before replacing its original C: path with a
junction. It also removes only four obsolete prefetch benchmark caches and
`target/debug/incremental`; keep their run receipts and all photographic outputs.
The explicit script is `completion/night-cleanup.ps1`; the operation's full
per-file verification and actual disk-space change are recorded in
`outputs/multi-stack/night-checkpoint/cleanup.json`, with a versioned copy at
`completion/night-cleanup-receipt.json`.

MEASURED cleanup completed successfully: all 1,298 relocated files were verified,
and C: gained 103,263,285,248 bytes (96.17 GiB). C: had 140,617,965,568 bytes
(130.96 GiB) free at completion; D: had 493,696,581,632 bytes (459.79 GiB) free.
The saved receipt is authoritative; a final console-only summary initially
printed null values because it selected properties from an ordered dictionary.
That display conversion is now fixed, without rerunning the cleanup.

Keep original input copies/stamps, captures, primary source caches, prepared
mosaic maps/focus/guides, native masters, failed outcomes, source snapshots,
release libraries and experiment receipts. Captures remain read-only. Do not
rerun cleanup blindly or rebuild over frozen research libraries before checking
the lane's archived source and dependency bindings.
