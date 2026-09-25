# CLI suite independent failure classification

Read back the root-run cli-suite-fixed-2/process.log:177 passed,35 failed,39 ignored. The suite remains **failed**, not a passing release-suite claim. All35 failure sections are accounted for in cli-suite-fixed-2-independent-classification.json.

- 24 fail because an experiment-specific fresh output directory variable was not supplied. This includes the terse phase_packed_rgb Option::unwrap panic: independent-controls.rs413 unwraps STREHL_PHASE_PACKED_OUT there. Its preceding mechanical assertions had been reached without a reported arithmetic failure, but its writer/control test did not complete.
- 11 fail because the compiled experiment requires an explicit route/environment:9 rounded/full-resolution GPU/probe requirements,2 noise-pupil bridge requirements for STREHL_DEFECT=off.

None of these35 reported failure points is a numerical assertion, comparison tolerance, resource ceiling, or child-process crash. This classification does not establish that these tests would pass under their proper configurations; some are deliberately rejecting experimental quality screens. It only identifies why this indiscriminate suite invocation stopped. No reruns, builds or RAW operations were performed by this reviewer.
