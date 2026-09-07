# Independent production-controller source review

2026-09-07. Read-only source review by the bridge author acting as a separate
reviewer of Zeno's Python launcher/controller. Root separately verifies the
bridge and its actual output. No module import, child, control, or matrix was
executed in this review. The K0 verifier and compiled bridge remain held.

## Initial snapshot and actual choice points

The first complete read covered `production-command.py` SHA256
`7a5ebc5673fabb07546472e80463de696e1ff84cbb5a832adc8e528a23348c24`
and `production-matrix.py`
`00169575fbf78ef4897670112c0c8359fd606d35aef39abdb2e1f4cdba733391`.
The author continued editing during review; these are initial source findings,
not claims about a later frozen revision or executed failures.

The launcher observes its own child exit, captures a combined stdout/stderr
pipe through a bounded queue, checks the log limit during writes, and kills
only that child on its prospectively stated timeout/overflow. Success requires
both actual integer exit0 and one anchored exact test summary. The existing
private controls use actual Python child processes for zero/nonzero exit,
zero/duplicate summaries, exact16MiB/overflow logs and timeout. Their outcomes
are explicitly private launcher evidence, never production-image authority.
Build entry reopens the copied/original executables, exact eight listed bridge
tests and actual current compiler/include source set. Matrix scheduling is
flat then textured, noise-off then eight fixed seeds, alternating admission
order, with two endpoint outputs appended; all38 plans precede pixels.

These are source-observed mechanisms only. Their actual execution and deciding
private results remain required before release of the intended population.

## Concrete corrections sent to root and author

1. `invoke()` read the successful Rust receipt and separately adopted the
   returned TIFF without comparing `receipt.output.path/sha256/bytes` with
   that actual file. A changed/swapped image after child completion could be
   recorded under its new hash while its receipt still described prior bytes.
   Bind those exact file fields; leave independent TIFF pixel mathematics to
   root/Curie's reader. A private changed-output companion should reach this
   boundary under a coherently updated file ref.
2. A post-child missing/malformed plan, receipt or TIFF could raise inside
   `invoke()` before it returned the launch reference. The matrix's
   `work.failed_launch` then remained null even though launch/log files existed.
   Preserve and link the completed parent observation before refusing its
   postprocessing. Keep actual exit0 distinct from a parent validation failure.
3. The initial matrix imported `production-command.py` through the normal
   bytecode loader before checking its source/release binding. Load the actual
   bounded source bytes, verify their released digest, and compile those bytes;
   do not rely on current `.py` hashes alone to identify previously imported code.
4. `next-production-controller-design.md` was named as a required dependency
   but absent during the initial read. This is a source-ready/release condition,
   not an executed failure or a claim that an unfinished document was omitted
   from a completed run.

The first14 private launcher controls exercise source changes through a
private `Build.finish()` that watches one text file. That powers the shared
before/after call, but does not itself exercise the real Build parser's missing
include-source, mismatched executable-artifact or test-list boundaries.
Economical additions are rehashed private copies of the actual build metadata
that omit an included source, mismatch two artifact refs or omit one test name,
with the genuine build as restored companion. A poisoned-parent environment
control should also reach the actual environment constructor. These need no
extra genuine render and no second general evidence framework.

## Disposition

Initial source review was conditional on the corrections and final frozen-source
reread. No executed controller or matrix admission is issued here, and no
product, noise, target, seed, mask, threshold or scientific score is changed.

## Frozen launcher reread

The narrow follow-up read checked `production-command.py` SHA256
`756a9c71da8c5f6dfaf3231e386ec09c83902c8f2aedb1ec23b5eb01b764635c`
and `next-production-controller-design.md`
`cada40fba5339a56a3c792f268e7fdb89187f3a5b4be3dcf8a059cf51789ba44`.
No source import, child, control or build was executed by this reviewer.

`output_binding` now checks the actual resolved path and typed length/hash;
it handles the local-drive extended path emitted by Rust explicitly. `invoke`
retains the actual launch and separately records postprocessing failures, and
the public wrapper retains that child before refusing its artifact error.
The original child exit0 is not rewritten into a fictitious nonzero exit.
The build helper is compiled from bytes checked against its recorded source.

The exact23 private controls now include actual `Build` calls on rehashed
metadata copies with a missing source, a mismatched copied artifact and a
missing test-list entry, followed by the genuine restored build metadata.
Each refusal must match its named error. Actual environment construction is
called with poisoned inherited overrides and after restoration. The output
association helper has valid/stale-hash/restored companions on a small private
file; this checks association rather than pretending to decode a TIFF.
The original process/log/source-change controls remain intact. The timeout
control intentionally includes interpreter startup and checks the operational
deadline, without claiming the sleeping body was reached.

I checked the actual build2 test listing. My earlier inferred namespace
`merge_cmd::production_truth::known_scene_benchmark` was wrong; the compiled
namespace is `merge_cmd::known_scene_benchmark::noise_pupil_bridge`. The held
launcher and new controller design use that actual namespace. This correction
preceded launcher execution and is separate from the earlier two Rust compile
errors already preserved in build1.

**Source-review disposition:** ready for root's exact released23 private
launcher controls and the separate compiled private commands. No additional
launcher blocker was found. This is permission to commission those controls,
not a claim that they passed. The fixed38 matrix and its association adapter
remain a separate review/execution scope; the launcher verdict does not admit
them, any image result or any quality comparison.
