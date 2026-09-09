# Direct consumed-plane results

2026-09-09. MEASURED on current RAW production path. Rounded arithmetic, native timing and the fixed precision comparison are complete. Rounded is exact and remains an experimental speed option. Float precision has no demonstrated improvement under the fixed acceptance rule and is not promoted. No SOTA bar moves.

## Independent arithmetic and delivered-output controls

Command run: python -I -B experiments/native-green-probe/run-controls.py --direct-planes, runner53f22d4fe43f136d51ef49f1e4def581ac77b719. All12 separate processes passed (Malvar/directional × fullres/fallback × off/rounded/float). Each exercises1308 literal/arithmetic assertions,2304 old-scalar comparisons,144 existing actual warp fixtures and a changed-fractional witness (2858 Malvar sites;2857 directional sites). These are repeated fixtures under different environments, not12 independent scientific populations. Rounded matches the off anchor's measured beta and complete whole/crop TIFFs. Float matches off on fallback; its fullres delivered output changes. Independent-results.md contains the separately decoded comparisons and verifies mode fields directly.

Explicit gathered-plane controls preserve original sourceu16 storage and crops. Build1 does not capture the actual complete merge's collapsedf32 output or count entry into its actual direct branches. Build2 and the completed eleven-bundle comparison below now discharge those narrower gaps. A complete TIFF identity alone cannot establish intermediatef32 identity. Control success is arithmetic/routing evidence, not photographic quality.

## Fixed native timing

Command run: python -I -B experiments/native-probe-fill/run-native.py --direct-planes-109, runner/allocation128feccdb1a0ff3b5cdd4d33de7cd1a10d1244ef. Original22 RAW frames of109MSDCF, full7032×4688 RGB16 output, existing unchanged canonical placements. Completed process wall seconds:

| Arm | Seconds | Owned CPU seconds | Peak job GiB |
| --- | ---: | ---: | ---: |
| 1-old | 11.157 | 69.796875 | 2.790314 |
| 2-candidate | 10.890 | 66.265625 | 2.790947 |
| 3-candidate | 10.860 | 67.093750 | 2.790592 |
| 4-old | 11.266 | 70.703125 | 2.790497 |
| 5-off-control | 11.000 | 67.125000 | 2.791523 |

Old/candidate minima11.157/10.860s give2.662% less wall time (1.02735× throughput). Both adjacent order comparisons improve. Same-binary off is11.000s, so direct is only1.000–1.273% faster than that control; the same-binary off is itself1.407% faster than the held old minimum. This is a modest observed improvement. The full2.662% old/new difference is not assigned only to the sink.

The consumed-plane extraction/luma interval falls from0.2700–0.2738 to0.1279–0.1344s; same-binary off is0.2692s. These leaf intervals support eliminated reread work but do not replace complete process costs, and a leaf sum cannot be stitched into a different full render. OwnedCPU minima fall69.796875→66.265625s (5.059%); the same-binary offCPU is67.125s. Peak job commit remains approximately2.792GiB. Input is warm, whole-machine load is recorded but not exclusive interference attribution, and this five-run window does not establish cold-cache or broad-machine speed.

All five complete TIFFs have197798267bytes and SHA256 84f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851; all decoded197796096-byte RGB16 payloads have1bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1. Every writer/process exited normally with complete job accounting. No new alignment solve is included;112's earlier solve time is not assigned to109. Keep these outputs and do not rerun for a better number.

Sourcef290b6145c091b68482b6cbb76fcc1533331c7bf; release build1 fresh Compiling strehl-cli,92.062seconds, CLI95e5c82d8940e87dc2e5e790a71aea4f5def69b03abbf1478a93b80087ca0236. Test executablea9dfbaa53f13bb777ad8c63d910883ce68b9e13e99cb22f08028f6b1b69bcd40. The held old CLI is4fe5443366c628029f9ea64faf6c239bb1769953f5ee505a7d629f5e22f4e2b8.

## Precision decision and whole-consumer verification

Commands run: python -I -B experiments/native-direct-planes/run-matrix.py --scene flat, then score.py --scene flat --input-dir experiments/native-direct-planes/run-flat-1 --output-dir experiments/native-direct-planes/score-flat-1; after its refusal, the same runner/scorer --scene detail generated and scored only the four off/rounded detail outputs. Full arguments and source bindings are preserved in the run directories. Render runner8e23d97d; bridge730542ab; final scorer65ee8120, SHA faa3de1227a4b80da4364847b2bc060d37d50a7fc1c9a6bed5fb447d7571e46c.

Exactly31 primary TIFFs and one observer-off placebo were produced from the existing eleven nine-frame M194b bundles. All11 off/rounded pairs preserve the actual consumed four planes, luma, per-frame beta, collapsedf32 values, complete TIFF and decoded samples. The actual/probe branch counters establish both direct paths were exercised; explicit helper calls alone cannot set those counters. Hashes capture all99 consumed original indices per mode across the eleven bundles. The single flat/noise-off off-mode observer-on/off placebo has identical complete TIFF and pixels, with empty off captures/counters. No retained aligned image stack was added.

Float fails6 of15 flat nonregression components. R/G temporal variance changes189.3840→189.7314 and187.9409→187.9730DN², while B changes201.9904→201.9815. Relative changes are+0.1834%,+0.0171% and−0.00445%. Repeat-mean MSE increases23.8381→23.8870,23.3778→23.4303 and25.1876→25.3079DN². The G absolute repeat-mean bias rises0.3030→0.3042DN; noise-off delivered output is identical. These are small changes: paired variance differences0.34735/0.03214/−0.00899DN² have jackknife SE0.19454/0.19294/0.25615. None demonstrates the required1% supported variance benefit, and none is a greater-than-two-SE variance worsening. The strict prospective rule rejects the arm; do not describe this as evidence of visible or significant photographic degradation. Live fractional inputs and changed delivered noisy TIFF pixels rule out an ignored precision path.

The flat decision withheld the two float plane/colour renders; only exact off/rounded detail pairs ran. Thus float detail quality remains unmeasured. There is no threshold, fixture or precision-policy rescue. Rounded's small exact speed result remains separately valid and opt-in; the default is unchanged.

Build2 compiled fresh in91.266seconds, test SHA58873b3ce09843c013b05195020f1b1b0696930c5f6e370f86db8f48485dc544. The64 plan/render child processes cost3.671875CPU-seconds in total, below the fixed60-second budget, and all completed normally. Tiny-scene costs do not predict native throughput.

The first scorer attempt stopped before image metrics because Rust's canonical Windows path prefix and the ordinary index path failed a lexical comparison. score-flat-attempt-1.json preserves it. The independently reviewed three-line samefile correction kept hashes, sizes, writer semantics and every quality threshold unchanged; existing images were rescored without rerendering. Root's simultaneous suspicion of an obsolete output-software literal was a false alarm and was withdrawn: the CameraLinear writer intentionally uses the package-only tag, while the plan includes revision.

## Next product decision

Close this finite precision population and retain the rounded implementation as an experimental option. Do not spend another promotion/retest cycle chasing its approximately1% same-binary timing difference. The next priority is a fresh actual coffee-bean development-stack workflow comparison against the existing runnable MIT fork, to expose remaining visible defects. Existing Lightroom TIFFs and original RAWs are different upstream processing histories, so this practical comparison is not a common-linear or formalSOTA score. No original RAW is modified.
