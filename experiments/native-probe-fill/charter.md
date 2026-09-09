# Exact parallel probe fill

Measure one bit-preserving CPU optimization of the current RAW consumer. The fixed profile's two probe intervals are4.8892266 and4.8655336 seconds. This combined stage includes filling synthetic noise, the real full-resolution warp, extraction, pyramid and pooled statistics. It is52% of complete process wall time here; fill alone has no measured cost yet.

Candidate: distribute complete active rows across existing Rayon workers. The active width is even, so each row ends after a Box-Muller pair. SplitMix state can jump exactly by the number of preceding active samples; no RNG family/seed, transcendentals, rounding, pixels or physical decision change is permitted. Do not skip calibration, reduce sample count, cache across different warps, alter any noise coefficients or revive the rejected decode queue.

Failure inputs exist: a wrong row offset, padded stride instead of active width, an odd trailing sensel, and a multi-row source must change the whole-buffer identity predicate. Compare to an independent literal old scalar algorithm, including padding, odd active extents, different seeds, saturation and1/2/8 execution threads. The author does not run their own verification.

Use the fixed eight-frame112 selection and saved direct map. Compare actual original and candidate release binaries, on the same warmed input and complete7032x4688 RGB16 TIFF output. Fixed order original/candidate/candidate/original plus one new scalar control; keep the current seven-leaf observer on for all these timed renders. Reuse existing bounded process controls and complete-file verification. Require exact whole-TIFF and decoded-pixel identity to the held baseline. Report minimum whole-process time per implementation and each paired direction; a flat or reversed comparison means no demonstrated speed benefit. Retain all trials and contemporaneous host busy; do not add leaf minima into a fictional run.

No sharpness score is needed to credit a speed change whose complete image is byte-identical. This identity predicate would reject any changed output, including an all-zero image; baseline nonconstant full-payload verification already passed. This is development-prefix speed only, without competitive, quality, deep-stack, cold-cache or alignment-quality claims. Standalone solve cost remains separate.

Root owns execution. Factor owns gatefloor.rs and implementation-notes.md. Coordinate owns independent-tests.rs/independent-review.md. Sampler independently interprets measured costs. Existing process/observer tools remain unchanged except the build helper may take a fresh output directory.


## Transfer to one different admitted stack

2026-09-09. Fixed transfer-plan-109.json binds the complete22-frame109MSDCF stack and existing canonical direct map, digest b70554b8cfd9b93e. This is a different stack from112, not a directory mirror. Use the already held original/parallel binaries; no rebuild or alignment solve. The current driver accepts only the fixed --transfer-109 follow-up, runs old/candidate/candidate/old, and writes a fresh transfer-109 directory. First old output is only the byte-equality baseline. Any file/map identity mismatch, whole-TIFF mismatch, nonconstant/full-resolution output failure or owned-process failure stops comparison. No protected holdout is used, no corpus write occurs, and none of the closed112 or physical diagnostic populations is rerun. Existing strict-lint/helper failures do not license new tooling work.
