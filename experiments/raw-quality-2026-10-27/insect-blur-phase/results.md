# Even-power phase: real-stack coverage failure

2026-10-27. **MEASURED / independently VERIFIED:** the fixed p1/p2 matcher cannot
produce a complete299-source weevil map. p1 leaves67 frames unplaced and p2
leaves73. This recipe is closed without rendering incomplete stacks. There is
no photographic improvement, physical placement accuracy claim or SOTA advance.
This does not reject all blur-invariant registration or explain current softness.

The published even-power cross-spectrum removes sign inversions of symmetric
real transfer functions. Our fixed original-CFA implementation uses separate
physical G1/G2 lattices, the single injected noise model and f32/complex64 GPU
batches. The prior held map proposes integer patch origins only; no fallback
edge is inserted. Source, coordinate, confidence and ambiguity contracts remain
in brief.md, implementation-notes.md and full/brief.md.

Independent40-pair generated controls pass, including the sign-changing disk
distinction, six flat/noise/rank refusals and wrong-sign/pitch/phase foils. P2
maximum errors stay below0.057native pixels. Half-period ambiguity remains
unidentifiable without a valid seed. These results establish the narrow
mechanism, not actual physical accuracy or general occlusion handling.

All2340 actual pairs,224640 tiles and898560 phase/power records are retained.
All patches are supported, but p1/p2 accept only12063/12501 combined tiles.
Even before fitting, optimistic anchor components reach only232/226 frames.
The unchanged native one-pass MAD/global solver cannot recover missing coverage.

| Arm | Fitted edges | Anchor vertices | Anchor edges | Cycle rank | Unplaced |
| --- | ---: | ---: | ---: | ---: | ---: |
| p1 | 610 | 232 | 586 | 355 | 67 |
| p2 | 603 | 226 | 589 | 364 | 73 |

Cycle floors0.31183/0.27446 guide pixels cannot establish improvement over the
held map: populations differ and held-out values are null. Gauge is reference149,
guide3516x2344, pitch2native pixels. Both maps explicitly record unplaced frames
and false render eligibility. Native commissioning reproduces every original
fit/refusal/MAD mask and the exact2314-edge/299-frame held map.

## Execution and evidence

Root ran these commands from the worktree with Python3.12 and fourCPU workers,
one Torch interop thread, TF32off, RTX5090 for the reader. Each invocation saves
resolved environment, hashes, bounds and host load. All below exit clean0.

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/run-controls.py --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/run-actual-controls.py
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/run.py cost --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/run.py actual --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/recover-build.py
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/run.py graph-controls --iteration 1 --build-iteration 3
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/run.py graph-replay --iteration 1 --build-iteration 3
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-blur-phase/full/run.py graph-candidate --iteration 1 --build-iteration 3 --actual-iteration 1
```

| Stage | Wall seconds | Peak owned-job committed bytes |
| --- | ---: | ---: |
| Mechanism controls | 9.844 | 2935906304 |
| Physical coordinate controls | 0.141 | 14135296 |
| Six-pair cost | 33.266 | 3031764992 |
| Complete2340 observation | 233.969 | 3030605824 |
| Cached build recovery | 0.906 | 81186816 |
| Native graph controls | 0.297 | 3215360 |
| Native exact replay | 1.672 | 11563008 |
| Native candidate solve | 0.422 | 8269824 |

These are operational observations, not competitive full-workflow timings.
Full reader GPU peak allocation/reservation is141712896/178257920bytes.
All299 cache bytes are rehashed before/after; original ARW metadata is checked,
with earlier export content identities inherited explicitly. No RAW decode,
source modification or aligned-frame volume occurs.

`full/run.py build --iteration 1` failed digest formatting. Build2 fixes only
that formatting and freshly compiles, but times out at900s while draining one
unidentified owned descendant. The harness terminates its own job; build2 stays
failed and has no admitted timing. Build3 binds the current target executable
before/after a clean cached Cargo confirmation, not a nonexistent build2-exit
hash. Recovered executable SHA256 is
`9e3637fe2fa9fb9f185df28b8a721ddc8b3d3bde3e967d8ccc9e3afa97c26c9e`.
All graph jobs run afterward with natural clean terminal exits.

[Independent full audit](full/independent-actual-review.md) rehashes23 actual-run
references1.470GB, verifies every rich/compact measurement/refusal join, then
1448 graph/build references330.5MB and exact components. Candidate receipt SHA256
`b48fc0e38d61f17b6b539fa986d1eba6cb5fcb75aec21be96c0c4d711906b76c`;
reader receipt `1aefde8c64f59abcabf7bdde5c3a6a2bbc87d9639e95a7bd92a09b53a7f3bab7`.
Raw evidence remains under the corresponding insect-blur-phase-* output folders.
No default or SYNTHESIS fold is changed. The next photographic/native questions
are separately allocated; broader insect quality remains unresolved.
