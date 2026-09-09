# Independent interpretation of the native phase run

2026-09-09. MEASURED costs, VERIFIED saved-record consistency, ARGUED next implementation choice. This reviewer did not author the profiler, run the native products, or decode/rehash their approximately 1 GB of TIFFs. Read the saved results, five process/output records, three profiles, execution record, committed plan, and local consumer source. No new experiment or production edit.

The measured gate-floor probe is the largest phase on this fixed eight-frame native prefix. Its rank survives using each run's completed process time rather than the smaller leaf sum as denominator.

| Wall interval | 2-on, seconds | 4-on, seconds |
|---|---:|---:|
| Completed render process | 9.453000 | 9.359000 |
| Probe | 4.889227 | 4.865534 |
| Real gather | 2.201805 | 2.097694 |
| Pyramid add | 0.666173 | 0.669526 |
| Fold decode/validate | 0.508640 | 0.508226 |
| Extraction/luma | 0.104442 | 0.117828 |
| Variance | 0.011378 | 0.011568 |
| Fold interval minus all leaves | 0.485477 | 0.498690 |
| Collapse/write | 0.401816 | 0.419234 |

Probe occupies 51.72%/51.99% of those respective process intervals, or 55.14%/55.49% of their folds. Gather occupies 23.29%/22.41% of process time and pyramid-add 7.05%/7.15%. Do not add enclosing fold time to its leaves or combine minima from different runs into one synthetic fastest run.

Each timed profile has eight calls to decode, gather, probe, extraction/luma, variance and add; defect has zero calls, an unvisited option. Placebo retains the same counts with null leaf durations. The native prologue additionally decodes frame0, taking 0.105410/0.100218 seconds outside the fold decoder timer. These eight-frame renders therefore do not mean only eight total RAW decodes. Standalone alignment took 1.297 seconds separately; the approximately 0.00028-second render alignment intervals load/resolve the reused map, not repeat that solve. The measured internal total leaves another 0.006170/0.005259 seconds outside its named outer intervals. Completed process minus internal total is 0.072178/0.064951 seconds, covering differently bracketed startup/final publication and remaining external work; it is not a measured transfer category.

All five saved process records show exit0, EOF, completed drain, zero active Job processes, no error/cleanup error and no termination intervention. The output records agree on a 197,798,267-byte TIFF hash ba96c63dd56f2729ba2ed25fedc19b291a4a78f9992f6823ce501a1df2a8bdc6 and decoded 7032x4688 RGB16 pixel hash d5fd6969b77fc94334995dea771e434f65f2b3cf782e1d683ca2872639595a1a. This review cross-checked the saved records; the actual large-payload hashing/decoding belongs to the retained root run. It supports observer output preservation for this population, not output quality or equivalence to an uninstrumented-feature build.

Whole process times in off/on/placebo/on/off order are 9.859, 9.453, 9.281, 9.359 and 9.312 seconds. The last off run is substantially faster than the first; this sequence does not identify precise observer overhead or a speedup. Whole-machine busy fractions are 21.72-22.42%; they include this job and are not competing-process utilization. Recorded owned Job CPU is 39.5625-42.0625 seconds per render, distinct from wall intervals. No per-phase CPU, memory-bandwidth or transfer measurement was made.

The probe interval contains frame cloning, deterministic noise filling, a synthetic full-resolution warp, green extraction/centering and pyramid/statistical work. Real gather also includes existing WB/MHC/CA processing. Subtracting real gather from probe cannot identify fill cost because the remaining operations and data differ. Exact row-parallel SplitMix64/Box-Muller filling is consequently a defensible small source-led optimization within the measured bottleneck, with unchanged stream, floor and model required; its isolated cost and actual end-to-end saving remain UNMEASURED here. Pyramid-add itself combines filters, weights, four-plane decomposition/cache, accumulation and bounds, so this result does not select GPU or SIMD hardware from that label alone.

The scope is the committed first eight 112MSDCF frames, native resolution, eight execution threads, fixed reused placements and current default numerical choices. No deep-stack, cold-cache, alignment-accuracy, physical noise-calibration, photographic-quality or SOTA claim follows. Defect/confidence/restoration options were not exercised. The earlier native noise and signed-black populations remain closed.

Evidence: native/results.json, 11,676 bytes, SHA256 133dee60fffb57e6105590b9cf48a00e9ccc43ff04945589f3f9f2cebed73fcb. native/execution.json records revision 90fbbb3b5ae9858e06ad5213b9d0e58cf7fd4a4f and run-native.py; exact product arguments remain in each native/*-process.json and *-invocation.json. Saved metadata were read with isolated stdlib Python; interpretation work has no claimed complete-process CPU measurement. No source population, image or native process was rerun.
