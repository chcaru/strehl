# Independent review: preparation 1 refusal and path association

2026-09-08. **VERIFIED operational failure after successful fixture generation.** This saved-result/source audit does not admit a render, the 135 saved checker controls, or TIFF numerical behavior. The planned final dimensions result reader remains paused. No generator, build, image operator, scanner, product or checker was rerun; no frozen source or old evidence was edited.

## Actual outcome

The one retained generator invocation exited **0**, with direct exit and pipe EOF observed, completed drain, final owned-Job active count zero, no child error/cleanup errors and no termination attempt. Its whole Job user+kernel CPU is **1.953125 s**; the raw log is 6,382 bytes, SHA `b040b37644f5cc3413ac8d4c7e798194402c173d07c7c8fe692bfeb6be93f144`.

The parent then **REFUSED**, actual external exit **1**, whole external interval **2.9839999999967404 s**, empty stderr and no timeout. Its terminal artifact map is empty. The full, untruncated 798-byte traceback names `fixture_read` at run-stage.py:231 and ends `ValueError: held legacy manifest/output association`. Finalization errors are empty. The final parent CPU sample is **0.828125 s**; completed-child CPU equals the independently summed Job total and live-child CPU is zero. These are sampled parent plus actual terminal Job operands, not an exact full-parent CPU total.

The generator's actual raw JSON advertises PREPARED_UNRUN_FIXTURES, 24 cases, 59 files and 16,025,258 file bytes. Its index reference matches independently read index.json (40,481 bytes, SHA `d07f356bdd7b2286b88404a337afd831319130e979b9adc27222d5ad71b1bf98`). That index has 58 generated references plus itself, and 24 case rows. An independent bounded metadata census confirms **59 ordinary files / 16,025,258 bytes** in the fixture directory. This audit did not open their TIFF payloads or independently certify all 58 file hashes; those checks remain for the separately released recovery/final review.

The terminal result (262,144 bytes, SHA `8411594fbca4f81d3574e369a2089c2b3cf5d77b4580da8d827d218f5499c1f5`) and parent tail are exactly associated with the outer raw advertisement. The actual release and controller/child commands match their saved references. A successful child is not a successful parent stage; prepare-1 cannot satisfy the current completed-prerequisite predicate.

Build-2 success is parent-provided context, outside this audit's directly read build evidence. The actual prepare release binds executable 3,201,536 bytes / SHA `172a52135ebee5853169cd3cd8bd8e9c97b4dc6ad5a886c20bfd57ea0a4a0684`. No product render or saved checker invocation appears in this prepare-stage execution.

## Exact failing choice

The authenticated historical report is the held 11,635-byte v1 report, SHA `abc69a25319da0ddb6ce2e9a036d8b37c0e1bcd4c67a9c186e6a647f088b5f9a`. Its schema, COMPLETE status and subject_complete=true are all correct. The failure is the first path comparison in the conjunction:

- run-stage.py:232 compares the report's manifest reference with the fixture index's manifest reference.
- run-stage.py:233 compares their output references. This second comparison is short-circuited in the actual failed conjunction but would independently be false under the same path rule.

Both report paths start with the valid local-drive Windows verbatim prefix `\\\\?\\C:\\`. The fixture manifest uses an ordinary absolute path; the fixture output uses the repository-relative spelling. Their saved extents and SHA values match exactly: manifest 2,905 bytes / `7c764e065a46e33da556ff98daf67f2c027abdbec833da63b742d82620ffd837`; output 74,807 bytes / `1e6c9f9bd3146c0c8f7314c422e26c842eb45ba25d76d12adae8f8d690842f7e`.

Held build-and-run.py:368-371 compares `lexical(ROOT/path)` values. Its lexical helper applies abspath and no-reparse/width checks, but keeps the verbatim prefix. An independent standard-library metadata-only check on these exact saved strings confirms both unmodified abspath Path comparisons are **false**. Removing only the valid prefix makes each pair's Path values equal; both pairs also currently have identical device/inode/size. No candidate function was imported or called. This establishes a concrete representation mismatch for this failure, unlike the still-unknown earlier compiler scratch canonical mismatch.

Canonical location must remain one conjunct of FileRef equality together with strictly typed extent and digest. Content equality alone must not identify different contributors. A corrective normalizer should admit only the intended local-drive ordinary/verbatim equivalence, reject device/UNC and malformed verbatim spellings, retain containment and ordinary-file checks, and preserve unchanged wrong-path/extent/hash refusal. This audit does not authorize broad normalization or silent acceptance of arbitrary path aliases.

## Complete later-path audit

This table covers all 13 source lines containing inherited d.same_ref in the current runner, including the multiple comparisons on some lines, plus direct-reader and checker boundaries.

| Boundary | Read source and actual scope |
| --- | --- |
| Prior stage association, lines 177,178,182,184 | Controller-generated source/raw/result/tail references use ordinary absolute or repository-relative spelling. No product-emitted verbatim FileRef is consumed here. Existing actual prepare transport passes independent canonical/extent/hash association. |
| Fixture source/spec and literal legacy records, lines 219,227 | Independent fixture references and literal expected refs use ordinary or relative paths; these completed before the observed failure. |
| Historical report, lines 232,233 | The two verified ordinary/verbatim mismatches above. This is the current defect. |
| Recipe and case manifests, lines 249,261 | Independent generated references remain ordinary. These branches were unvisited after the failure. Preserve their existing extent/hash checks. |
| Reused executable and fixture index, lines 277,282 | Parent-produced references remain ordinary. The failed parent has no admitted fixture_index artifact; recovery needs a new explicit provenance object. |
| Preparation advertisement, line 413 | Generator and parent index references are ordinary. This branch was not reached, although the saved raw advertisement independently matches the actual index. |
| capture_case, lines 358-379 | **There is no d.same_ref call here.** It enumerates its own ordinary-path case files, reads them with their own freshly generated refs, compares raw report/stdout bytes, and requires output presence/absence. It does not inspect product-emitted FileRefs. No same_ref patch in this function is indicated by the current source. |
| Held d.read, lines 111-114 | Expected-ref intake also uses lexical path equality. Do not supply a normalized path and an unnormalized product expected-ref to this primitive during recovery; normalize a validated association separately or keep its operands consistently spelled. The current capture_case gives it its own ordinary references. |
| independent-controls.py, lines 308-330 and product_case | Its distinct association_path already admits a validated local-drive verbatim prefix, rejects malformed components and UNC/device paths, resolves inside ROOT, then combines location/extent/hash. It handles product manifest, incomplete, binary, profile, consumed-input, frame-receipt and output refs. The current checker therefore does not share the runner's missing-prefix normalization. Its actual numerical verification remains unvisited. |

The generator's success is consistent with this source difference: its own legacy_authority uses the independent checker's association helper. There is no evidence here of a product path defect or a reason to change product/numerical predicates.

## Recovery provenance requirements

Correcting only the two equality calls is insufficient to reuse old successful work under a new runner hash. The operational continuation must explicitly account for:

1. runner bundle_read:177 binds a prior executed controller to the **current** runner source hash; :193 requires exact complete source-map equality across stages.
2. prepare-release.py's bundle requires COMPLETE_STAGE_UNVERIFIED, no error and actual exit0; its main also requires each old release's source map to equal the current map.
3. prepare-1 has actual exit1 and an empty admitted-artifact map. Its successful generator child, exact raw advertisement and saved fixture identity must be rebound through a fresh, bounded recovery receipt, while the original REFUSED record remains unchanged.
4. New operational source identities must be linked to the exact historical releases/archive and unchanged compiled-product/checker identities. A new source map cannot retroactively label the old build as compiled by the new controller.
5. Recovery should revalidate the already generated fixed byte population, original case schedule and source/spec bindings without calling prepare again or regenerating TIFFs. It must not invent an ordinary successful prepare child or alter existing paths/output bytes.

These are source findings and requirements for the separately authored recovery design, not approval of unseen recovery code. No failure expectation, pixel threshold or 24-case/135-control population should change.

## Read bounds and provenance

This independent audit has a full nonrefundable **10 CPU / 20 active-wall, 32 MiB read / 1 MiB report** allocation. Bounded saved/source reads total **507,006 actual file bytes**. Source discovery is conservatively charged an additional 1 MiB for its explicitly named source searches, rather than presented as measured zero. Alias comparison adds only stat metadata, no file-content reads. Publication/readbacks fit the remaining grant and are recorded separately. The initial read tool completed exit0 / 0.0863581 s; its CPU sample was quantized to zero and wall sample 0.01600000000325963 s. The alias check also had zero quantized internal samples; these do not establish zero resource cost. Full allocations remain charged, and no new whole-program usage total is inferred.

Source pins audited: runner 33,546 bytes / 442226bd08b128f8bb97460fab6f8ab6280fd0950d1912313b87d583b7a33940; held primitives 40,626 / b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410; checker 65,751 / 8fefa5e31c614595367f644b314ece77da6bf5d4ec54c4edde80816a0e8cee47; preparer 11,863 / 08140b301a73e2e5a8e401d1fa38ecef952a29229006d3ed649abbeee638f231. The companion receipt preserves all 15 file references, actual transport predicates, exact alias evidence and the saved-read source.
