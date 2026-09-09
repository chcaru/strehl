# Parallel preparation and batched GPU handoff

The first six native112 TIFFs are exact, including both output paths and numeric
log off/on/placebo. In the verbose pilot, RGB CPU coordinates cost281-294ms out
of362-398ms per GPU library call; green coordinates cost152-161ms out of226-245ms.
These are observed host intervals, not a formal alternating speed comparison.
Do not spend the first109 allocation timing that identified serial bottleneck.

Use the same per-sensel geometry expressions and WGSL, with disjoint-row parallel
CPU descriptor preparation/validation and256-row transfers. Keep Serial32 as an
explicit same-binary reference. No float reduction or noise/merge change.
The library uses the existing Rayon pool; renderer continues8workers.

Build-native-2 and run4 repeat the fixed18 controls under existing build/test
limits; report the actual schedule. Native112 then compares CPU/rounded,
GPU/Serial32/rounded/logoff, GPU/Parallel256/rounded/logon: exactly3 outputs.
All must match the independently held whole-TIFF and decoded pixel hashes.
The existing six-input log identity remains evidence for unchanged logging code.

Only after those3 pass, run109 CPU/GPU/GPU/CPU with rounded, Parallel256 and
logs off fixed. Both order comparisons and per-arm minima, all output hashes,
complete process costs and actual route evidence are required. No multiplication
of older gains. Reuse the same per-child native bounds180wall/900CPU/8GiB/2MiBlog.
Increase the retained-image allocation to3GiB for the six original112,three new
112 andfour109 outputs; all13 remain local with receipt hashes. No original RAW
file is changed. First failure preserves evidence and stops later arms.

This is an optimization of a measured host bottleneck, not a claim that256 is
an optimum or that the whole stacker is SOTA. The complete pipeline speed and
general photographic quality still determine promotion.
