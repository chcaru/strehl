# Standalone publication executable closure

Prospective correction, 2026-09-07, after root's launcher1 completed its23
registered controls. That run and its source/design/review remain immutable.
The source audit then found that standalone final publication reopened the
released source/input files and build result, but did not call `Build.finish`
to reopen the build's actual executable and include set. Per-child checks and
the38/12 matrix wrappers already called that method. No known changed actual
file or invalid earlier image is inferred; no image has run in this lane.

Standalone `main` now uses `completion_check(source_check, build)` before and
after publication, as well as at its existing child boundaries. The shared
check reopens the released closure and, after construction, the actual Build
closure. No product, input, mode, schedule, numeric bar or child limit changes.

Repeat the original23 controls unchanged in fresh output2. Add a separate
`publication_controls` child to the command result (null for other kinds):
schema `m194g-production-publication-controls-v1`, status
`PASS_PRIVATE_PUBLICATION_CONTROLS_ONLY`, fixture_only true, check_count3 and
checks [{name,pass,evidence}]. The exact order is:

1. `final-publication-valid`: actual Build on a private byte-identical copied
   executable and small cloned build record; successful shared publication.
2. `final-publication-executable-change-refused`: the post-write callback
   changes one byte of that private executable before the real `Build.finish`
   reads it. Require its `bound file changed` refusal on callback2, the first
   complete result retained as rejected and a newly persisted refused result
   with the original error. Restore that one private byte in finally.
3. `final-publication-restored`: the same actual Build and shared publication
   succeed after restoration, with a separate result path.

The unchanged genuine compiler/copied files are never edited. The one private
executable copy is12,767,744 bytes, counted within the original64MiB metadata/
log ceiling; changed/restored one-byte writes and all result bytes also count.
Retaining a result by rename adds no new payload bytes. The existing exact/
overflow logs use32MiB, leaving space under that ceiling. These are source-only
prospective controls until root releases their exact new command and source.
