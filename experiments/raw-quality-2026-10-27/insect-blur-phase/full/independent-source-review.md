# Independent full-workflow source review

2026-10-27. **VERIFIED source; numerical and photographic results pending.**
This review permits the bounded geometry controls, native replay and six-pair
cost observation. It does not establish physical placement error or authorize
a successful-image claim. Root alone schedules execution.

## Reviewed source identity

| Source | SHA256 |
| --- | --- |
| `actual.py` | `e3ce897a8b2adcf225e18d262d713d50ba8ebcf8434fccb5ac57a7fd79f1fb9c` |
| `graph.rs` | `ca3173d92bb1df74f48e04471a741f4866053a0adc6a5557155474fa6b24d521` |
| `render.rs` | `25e0e6ce89f95b0ec476bf86ba66d4b20968b6b073f10aeb4c89568f2d94d4a0` |
| `run.py` | `338fd6c552d7825ea3c3fedbf044fb9fcd9719c09b8da63861625ffbd577715b` |
| `actual-controls.py` | `d5e4a9d14cd4e41565b73d141a2cce76c373f575c240f00a6aad3d4a83fb47a8` |
| `full-control-plan.md` | `ef93b8895f9ca85ceb47163c809bff1b1d0b4c6ce3b681feb60a4820c46bd1e3` |

The geometry controls are integration-review authored, so this review of their
source is not independent verification of their conclusions. The producer is
cross-reviewing those controls. Only AST parsing was performed here; no image
data, Torch, RAW decoder, fit, Cargo or numerical campaign was executed.

## Resolved source issues

The retained observer is lexicographic in `(i,j)`, not span-major. Reading its
first four JSONL identities gave `(0,1),(0,2),(0,4),(0,8)`. The initial reader
would have refused ordinal1; it now sorts the complete requested population
before validation. All2340 pairs and96 tile slots are retained, including old
refusals, without outcome-based selection.

The renderer initially inherited GPU/direct-plane settings from another
experiment. It now requires both `STREHL_GPU_GATHER=off` and
`DirectPlaneMode::Off`, matching the held baseline's actual full-resolution
CPU gather/remosaic path even when optional backends are compiled. This avoids
assuming baseline-map backend parity generalizes to different candidate maps.

The fractional held prediction is not the center of the reader's fixed box.
The producer now retains the rounded-origin remainder and exact per-axis
held-relative interval `[-2-remainder,2-remainder]`. Reader radius, spacing,
window, powers and gates remain frozen.

## Producing-path checks

`actual.py` binds the exact ordered299 original-cache identities, active area,
u16 payload/header, physical CFA phases, held map and injected noise bits.
Complete cache bytes and source dependencies are hashed before and after;
original ARWs receive metadata checks only, with their earlier export hashes
explicitly identified as reused evidence. There are no new RAW decodes. Only
two source memmaps and bounded copied green patches are live per pair.

The relative map is `Mj composed with inverse(Mi)` in native centered units,
with translation doubled from guide units. Original G1/G2 patch centroids are
their first sensel plus127native pixels. The mean centroid therefore becomes
`(tx+63.75,ty+63.75)` guide pixels, a quarter guide pixel below/left of the old
nominal fit center. Integer origins preserve CFA parity. The reader returns
total origin-plus-local displacement; the combiner averages measured vectors
at their mean point and does not add the held slope to them. Both phases must
pass and their held-relative residuals must agree within0.20native pixels.
Missing support, a refused phase or disagreement yields null; no NCC, held-edge
or single-phase fallback is present. The boundary to Rust is explicitly f32.

`graph.rs` calls the actual core similarity fit and preserves literal original
one-pass MAD, residual, survivor, lever and peak arithmetic. Replay compares
initial fit/residuals, median/MAD/cutoff/keep, final residuals and complete
StageFit/refusal, then requires the complete held map text bytes. Candidate
parsing requires all2340x96 slots, finite observations and exact new center
bits. Both powers use the shared measured-component global solve with the
existing unit weights, reference149, smooth1/huber1 and all original spans.
Phase scores remain diagnostic. Connectedness, cycle rank and unplaced frames
are reported rather than repaired using the initializer.

`render.rs` validates every candidate placement against the same fixed native
crop `(68,46,6896,4596)` before folding. All299 originals are decoded once and
fed to three ordinary workers; the canonical75/75/75/74 chunk order, noise
probes, gates, CA-off gather, held development and writer remain shared. Full
baseline CFA/RGB16/developed-linear payload and material-metadata parity are
required. Container provenance may differ. The float master is developed
linear RGB, not recoverable original camera RGB; the receipt does not invent
such a master. The legacy per-source MHC/remosaic limitation remains explicit.

## Release and interpretation limits

The root wrapper uses fresh directories, source/executable bindings, bounded
owned jobs and exact scientific statuses/counts. Candidate graph input is
bound to the completed full-reader artifacts. The reviewed wrapper is a
dispatcher, not an autonomous cost-to-full promotion rule: root must enforce
the separately specified controls, exact replay and practical-cost sequence.
Its render scheduling remains separate.

For projection, use the recorded whole pair-campaign interval, which includes
both phases/powers, census, serialization and flushing. Individual pair timers
exclude serialization. Charge binding/setup and final verification separately;
six chosen pairs cannot guarantee full graph acceptance, support or cache cost.

This changes the initializer and tile center as well as the phase estimator.
Only the complete paired p1/p2 images can isolate a useful power-specific
effect relative to their common changed workflow. Phase agreement and global
fit consistency are not physical truth: scale/window/visibility bias may be
shared. A complete null or regression closes this fixed recipe. Complete
outputs, fixed native witnesses and external workflow comparators remain the
photographic decision, not the control scores or graph residuals.
