# Saved-fixture recovery design

SOURCE ONLY,2026-09-08. Proposal for root review; no implementation, imports of
candidate code, control execution, rebuild, generator rerun or product invocation.
The original190-source map and all build2/failed-prepare1 artifacts stay immutable.

## Actual failure and usable evidence

Saved build2 is COMPLETE_STAGE_UNVERIFIED with fresh:false compiler artifact,
features[], build-finished success:true. Its copied executable is3,201,536B,
SHA256172a52135ebee5853169cd3cd8bd8e9c97b4dc6ad5a886c20bfd57ea0a4a0684.
Root preserved successful evidence atae83e07c. No new compile is needed for an
association correction confined to orchestration.

Prepare1 parent remains REFUSED. Its262144-B result has SHA256
8411594fbca4f81d3574e369a2089c2b3cf5d77b4580da8d827d218f5499c1f5.
The retained798-byte traceback ends at run-stage.py:231-233,
"held legacy manifest/output association". Artifacts is still empty: the parent
did not publish a fixture-admission FileRef.

The linked child is independently distinguishable from that parent refusal:
2293B/3aee4d40f23c980989772c46cefcbb967dfae9ffe5090a508285002114870380,
actual exit0, direct exit and EOF, completed drain, no error/cleanup/termination,
terminal Job active0. Its6382-B raw log
b040b37644f5cc3413ac8d4c7e798194402c173d07c7c8fe692bfeb6be93f144
contains PREPARED_UNRUN_FIXTURES,24cases,59files,16,025,258B and an index FileRef.
The index is40481B/
d07f356bdd7b2286b88404a337afd831319130e979b9adc27222d5ad71b1bf98.

A read-only name/extent census matches all58 indexed generated files plus index,
total16,025,258B. This diagnosis did not rehash TIFFs or decode pixels; exact
content admission remains future bounded saved-data work. The actual outer is
1634B/65f109dd5e47252e503ed84cf993cbc8dadf7d59da21493ccadb087f23cfdf9b,
exit1, timeoutfalse,2.9839999999967404wholewall. Tail samples parent0.828125CPU,
child Job1.953125CPU, wall2.9679999999934807 with the inherited2CPU/3wall allowance.
Neither timing nor child success refunds the full failed prepare30CPU/60wall/34MiB.

## Concrete mismatch and prior answer

The held old common-TIFF case00 report(11635B/abc69a25319da0ddb6ce2e9a036d8b37c0e1bcd4c67a9c186e6a647f088b5f9a)
is COMPLETE/subject_complete:true. Its manifest is2905B/
7c764e065a46e33da556ff98daf67f2c027abdbec833da63b742d82620ffd837;
its output is74807B/
1e6c9f9bd3146c0c8f7314c422e26c842eb45ba25d76d12adae8f8d690842f7e.
Both report paths use the Windows verbatim local-drive prefix. The newly saved
index records the same extents/digests using normal absolute/relative spellings.

The two differing predicates are explicit:
- inherited M194h build-and-run.py:368-371 same_ref compares lexical(ROOT/path);
  its lexical uses abspath and preserves the differing prefix;
- current dimensions independent-controls.py:308-332 association_path/same_ref
  already accepts canonical verbatim local-drive spellings, rejects unsupported
  device/UNC forms and requires repository containment plus path/extent/hash.

Only the runner's two legacy report comparisons at232-233 use the first choice.
capture_case has no product-FileRef comparison. The independent checker already
uses the corrected association policy. Therefore changing all file readers or
all same_ref callers would unnecessarily broaden the correction.

The original common-TIFF verification2 precedent is directly relevant, not an
unanswered new path question: verification-2-decision.md and
verification-2-contract.md describe the same spelling defect, a saved-only
additive authority and six powered metadata controls. Source-read
independent-controls-2.py:408-458 implements the predicate/controls; the current
dimensions predicate already carries it. run-verification-2.py keeps an original
producer namespace alongside an execution namespace instead of equating old and
new whole-source maps. That pattern is reusable, although this recovery must
handle a refused preparation parent, which that completed-producer precedent
did not admit.

## Actual unchanged source closure

The exact190-source freeze2 is28634B/
f3778c80df31b6cde6e253797cf497ca2cdfced85f8507ae126ba03ce8563708.
A metadata source read compared every current source buffer to it:190/190 equal,
5,716,711B read. No old source was changed by this diagnosis.

Separately, all118 Rust/manifest/lock/compiled-text entries,4,613,150B, match.
They include103 crate/root entries and15 external Rust include targets. The
canonical source-map hash is
ee02f4b41cfc5cc5c1d501c72d9980f2131fba9b891e6b9aca9412e119ff72a8,
identical to both saved build2 and prepare1 compiled_source_closure records.
This is current-source identity evidence, not a new compile or a claim about
the toolchain cache/native DLL closure.

A new immutable recovery freeze must contain the literal original190 entries
unchanged plus only a closed list of new operational sources/reviews. Preserve
source-freeze-2, source-1.zip and source-2-delta.zip. A separate recovery delta
contains only added files; reconstruct its base through those two saved archives.
No changed old-path binding, replacement binary or re-created fixture is allowed.

## Smallest useful implementation boundary

Prefer one new recovery-stage adapter reusing the pinned current run-stage.py
definitions, plus a thin independent checker authority adapter and root's
metadata/capture recipe. Existing process, Budget, scanner, child/publication,
case capture and numerical functions stay unchanged. Root fixes the final
source filenames/count before implementation; do not make a new generic runner.

Use separate original-provenance and current-execution namespaces. Keep original
SELF/schema/paths/190 map when authenticating build2 via the existing bundle
reader. The actual old prepare result/outer must be handled by a dedicated
saved-prefix predicate: require the exact named refusal, original release/argv,
clean successful child/log/index association, full terminal accounting and
original producer source/spec. Do not pass it through a COMPLETE-only predicate,
copy a fabricated COMPLETE record, or replace its absent artifacts field.

Create one genuinely new saved-fixture admission receipt in recovery-1. It must
bind the complete failed parent/child/log/tail/outer/stdout/stderr/exit, original
build bundle/release/freeze, existing index, original fixture source/spec, current
recovery source map, exact path controls and all59 newly authenticated file
identities. Empty stderr stays exact named evidence, never a positive source.
Its status should mean SAVED_FIXTURES_ADMITTED, not PREPARE_COMPLETED or software
integration. The original prepare status remains REFUSED in the same receipt.

The saved reader reuses the exact existing fixture_read body with only its two
legacy d.same_ref calls replaced by one scoped legacy association predicate.
Select the already held association_path source definition without executing
the independent generator/checker module; retain typed positive integer extents,
closed three-key FileRefs and exact digests. Reverse the two call-site edits to
the original AST. Do not globally replace d.same_ref or d.read. The latter also
compares lexical spelling: for an actual byte read use one authorized normalized
path/ref pair consistently, while retaining original report spelling separately.
Current code reads the ordinary index-owned refs, so no reader rewrite is needed.

Run the saved fixture reader with original190 source_bindings through a small
read-only provenance view that delegates its check callback to the active budget.
This preserves the original fixture source/spec association while new recovery
source checks use the current extension. No old budget or accounting is reset.

Later render1 and verify1 remain fresh and keep the exact original24 product
commands, expected dispositions and135 saved numerical controls. Their new
versioned release must explicitly bind the recovery receipt. A ten-key release
can retain the existing fields by putting that fixed positive receipt in inputs;
prerequisites retains the original build and failed-prepare bundles as history.
The new prerequisites predicate admits that exact failure only through the new
receipt; it does not weaken generic completion acceptance. Verify additionally
authenticates the actual new render bundle under the current map.

The independent saved checker needs a new thin authority adapter for the changed
controller/release provenance: saved_render_bundle currently names run-stage.py,
v1 release and the original fixture/checker source pairing. Keep its existing
fixture source/spec fixed and reuse every pixel/noise/gate/observer/135-control
body unchanged. New controller/schema association is a declared source delta,
not a reason to rerun or retune any scientific control. Original checker remains
in the190 base; added adapter/source-review bytes belong to the extension.

## Powered metadata controls and finite proposal

Use the actual new two-call predicate at its production call sites, with an
independently authored fixed table. Six precedent groups suffice: ordinary
positive; ordinary/verbatim positive both directions; distinct real file with
identical bytes must reject; same path/wrong extent; same path/wrong digest;
restored positive and both fixture identities unchanged. Add typed-bool extent
and unsupported device/outside-repository groups if the independent author
extends the predicate contract; these are metadata controls, not extra24/135
numerical outcomes. Assert each destroyer was exercised and the final saved
legacy read visits both associations. Never accept identity from hash alone.

Proposed separate admission envelope for root re-choice:10CPU/20wall,64MiB
bounded reads and2MiB retained metadata including controls, result/stage/tail and
external streams; no child, image decode or numerical operation. One new
metadata-construction10CPU/20wall slice may freeze/archive the additive sources
inside the existing32MiB metadata family. Existing unused render180/240/128MiB
and verify60/120/19MiB allocations stay fixed; no rebuild/generator allocation.
All failed build/prepare, successful build, constructor/control/review charges
remain nonrefundable and visible. This memo does not authorize these new slices.

Before release independently check complete metadata sizes and exact source
closure, then run the new admission once. Only an actual admitted receipt permits
the still-unvisited fixed render/check stages. Another failure remains a saved
failure and provides no automatic retry.
