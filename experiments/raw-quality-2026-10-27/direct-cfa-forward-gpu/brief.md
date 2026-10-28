# Enable a bounded original-CFA photographic observation

2026-10-27. Root releases implementation of the measurement operator and its
independent controls, not an image-quality claim or a full solver campaign.

The last turn completed the full V3 comparison and rejected promotion. The
source-conditioned MLS sketch is incomplete and is now closed. The earlier
constant-deflated direct-CFA inverse has a real producing operator and finite
outputs, but its generated flat has excess chroma and its fixed64-step solve
refused convergence. Those failures remain unchanged and explicit. The changed
question is whether a faithful, practical GPU route can support a complete
photographic observation of direct-RAW reconstruction instead of ending the
entire route on that synthetic result alone. This is not a higher iteration cap,
regularizer/threshold sweep, or reclassification of that failed test as passing.

The current CPU implementation cannot simply run a full stack: it accepts at
most seven128-square sources, caches sparse A/A-transpose matrices, requires
unclipped inputs and does not define a complete-image streaming solve. A patch
inverse is not an exact tile of the global inverse. Do not stitch independent
patch solves and imply a faithful full-frame observation.

## First executable checkpoint

Cfa-residual owns `measurement-gpu.py` and `operator-notes.md`. Implement the
same nine-node sensor-cell-integrated, normalized Lanczos3 forward A and
adjoint A-transpose as the frozen CPU
`../joint-cfa-local-fit/band-residual/sensor-operator.py` (SHA
`536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac`).
Original RGGB coordinates choose one measured output channel; both physical
green phases map to green. Latent values and arithmetic remain f32. Geometry
may be f64 as in the CPU reference. No per-source RGB reconstruction or
aligned-frame volume. The full-frame implementation must not construct sparse
matrices or a footprint-node cube for every pixel. Generate affine physical
footprint coordinates at consumption from source origin and a declared
source-to-latent2x3 map. Keep all support in bounds; unsupported coordinates
must be refused rather than silently extended/clamped.
The unit-square sensor-cell integration is the inherited model assumption,
not a newly measured Sony pixel response or a calibrated optical PSF.

Use the installed NVRTC/driver path already commissioned by
`../dual-tree-cfa-gpu/ordered-fir.py` (read and adapt the loader, do not edit the
frozen helper). No new package/toolkit install, no fast-math/f16, no model change.
One forward and adjoint pass must support a globally indexed latent field and
streamed original-sensor rectangles. Original u16 samples remain storage;
current forward/adjoint residual buffers are bounded f32 arithmetic scratch.
State atomic/reduction-order nondeterminism honestly; numerical equivalence,
not bit identity, is the proposed contract.

Integration-review owns `controls.py` and `independent-plan.md`. Build independent
small affine queries through the frozen CPU operator, including identity,
fractional translation, rotation/scale, odd source origins, both greens and
rectangular extents. Flat constants first; independent-color structured fields,
adjoint dot products, forward/adjoint CPU comparison, rectangle partition
equivalence and unsupported-support refusal follow. Include wrong-channel and
wrong-coordinate producing-path foils that fail the unchanged fidelity bounds.
Choose and record normalized f32 error bars before execution; distinguish a
forward measurement operator from a reconstruction algorithm. Do not run jobs.

Photo-review owns `input-bridge-audit.md`: locate any retained original-u16
weevil cache and its provenance, or identify the minimal read-only RAW decoding
bridge needed. Bind active-area/CFA phase, original-order299, levels/noise,
held map/ref149 and full native delivery gauge. Search existing artifacts;
no RAW decode, image processing or new numerical jobs under this audit.

Root owns the bounded runner, installed-runtime checks, compilation and all
execution. Initial control bound:300s wall/1200CPU-seconds,8GiB host and8GiB
Torch allocation, four workers. A later full-source forward/adjoint cost pass
needs a separate explicit release after these controls. This allocation does
not release64-step fitting, whole-field assembly, clipping-model changes,
patch-composited photos, another generated quality sweep or a default change.

## Continuation boundary and prior-art lookup

The only purpose of this narrow implementation is to determine whether the
complete native photographic question is feasible. Passing mechanics is not
an improvement. Before full fitting, define one global original-CFA objective,
its boundary coverage, source-streaming state, constant projection, exact
noise/admission and final direct-RGB delivery, with a measured practical cost.
If that is unavailable or impractical, stop this observation route rather than
quietly substituting a source subset or local crop. Preserve the failed flat
and numerical status beside any eventual complete photograph/master.

Root actually ran unified search `matrix-free integrated Lanczos` and the
mechanical checker with that phrase and `original photosite GPU adjoint`.
No exact report was located; retained CPU band-residual/deflation sources,
ordered-FIR NVRTC helper, older native-gather results and pupil-stencil source
were read. The old native GPU gather commissions a different MHC/remosaic
operator and cannot validate this one. No external implementation is consulted.
