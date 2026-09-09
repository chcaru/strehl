# Independent source review — native GPU gather

Status: source-reviewed for the fixed first control run; no numerical pass, speed or photographic-quality claim.
Reviewer performed no build, test, GPU execution or RAW decode. Root owns execution.

The oracle calls the current fullres MHC, sample_checked and u16 writeback body with an explicit test-only CA seam; it does not call the GPU descriptor builder.
Ordinary production calls retain gear resolution. The optional dependency/workspace exclusion and cfg(test, feature) glue add no production GPU dispatch or default change.
The reviewed shader preserves signed black subtraction, supplied CPU inverse WB, MHC tap order, Catmull x-then-y sums, active-relative RGGB and parity-reflected reconstruction boundaries.
CPU f64 support/cell decisions remain distinct from shader interpolation. Shader contraction can still change rounded output; only actual exact comparisons can settle that.
One invocation owns both output u16 halves; invalid plans return rounded black without coverage and GREEN_ONLY preserves original R/B halves. Strip tails and readback extents are bounded.
The quantizer uses integer truncation then the fractional comparison, avoiding premature rounding from adding 0.5; its actual shader entry is checked at exact halves and adjacent f32 values.
M7's approximate ring-focus arithmetic result is not equivalence evidence for this consumer. No reduction or noise-model result transfers from it.

The fixed18 cases compare every consumed u16 and coverage bit/count against the actual CPU result, with poisoned padded/odd storage and source identity checks.
Case4 must expose actual half ties; cases5/17 must expose signed excursions and clipping. Thus literal-table success cannot substitute for live gather behavior.
Boundary cases independently distinguish f64 support and floor, including values that collapse to the same f32 coordinate. The synthetic CA check fixes composition direction separately from CPU/GPU agreement.
Three live descriptor mutations challenge source address, green phase and coverage; the nonconstant colour fixture and repeated GPU-object use can reject stale/incorrect outputs.
Compact GPU output is scattered into a clone only by these controls: this is not yet a production consumer integration, writer or full-render equivalence result.
Cases1/16 compare complete-storage hashes for ordinary CPU, actual-operand observer and fixed-sentinel observer. Sentinel values differ from the live trace while actual writeback remains shared.
The early failure return now retains these observer receipts. Initialization/per-case failures are saved, and numerical mismatches do not stop visitation of the remaining primary cases.

The runner uses the exact ignored test, a fresh run-1, compiled executable/source bindings before and after, and the existing bounded child-process helper.
Its120s wall/120s aggregate child CPU/4GiB Job commit/4MiB log bounds match execution-1.md; the compile uses600s/1800CPU/8GiB/two workers, locked/offline, and demands a fresh Compiling strehl-cli line.
DeviceType::DiscreteGpu is explicitly required before device creation and reported with backend. My earlier contrary comment relied on an earlier source reading and is withdrawn; no eligibility change was needed.
No remaining source-review blocker to root's fixed run was identified. GPU validation, exact equivalence and mutation power remain unexecuted at this checkpoint.

Reviewed SHA-256 bindings (the build/runner also bind their full source/protocol lists):
- src/lib.rs: a1ca049442902d01a5ca98afffeba67ddf73e5c5e613fe803f00cc88f098c504
- src/gather.wgsl: 75d68800c14789ac4982ff32a2cfa35edbc11b731b9158a83e44ad12a62a40ff
- cpu-bridge.rs: d87515250211d04a5e51656b451d0d59ef61b98f2c87d77c0f25700754c7359c
- independent-tests.rs: cb45570e9c8f5c75f09530c2cddf365bb17ccf29f18e6a39abadf49ac6bf0af7
- independent-design.md: 735f8be97698898e315a1c002a420dea6a6120a8e8168341f78e6dd2d39cd4c6
- run.py: aedf7ccfe0119a334e4f066bd09bd3d8a4184dd494c546ca284d6e82254937e7
- execution-1.md: 65d091714e63dbf533d09d45ea2b7173bdd62dedb683c1e6fc4e4ae8308fb27a
- ../native-pyramid-profile/build.py: b24764d9daf08169354908fd24870637d870697812c93bb7a722200ba30efe9f
