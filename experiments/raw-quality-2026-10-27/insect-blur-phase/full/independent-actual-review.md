# Independent complete measurement and graph audit

2026-10-27. **VERIFIED: the fixed experiment is complete, but both candidate
graphs are incomplete.** p1 leaves67/299 frames unplaced; p2 leaves73/299.
Neither satisfies the allocated complete-stack render contract. No renderer
was run, and no photographic improvement is established. Do not fill missing
edges from the initializer, relax gates, or present a partial stack as success.

## Integrity and actual execution

Root's recorded child command was Python3.12 with `-B -X faulthandler`:

```text
experiments/raw-quality-2026-10-27/insect-blur-phase/full/actual.py --mode full --out outputs/raw-quality-2026-10-27/insect-blur-phase-actual-1/output
```

The invocation/process receipts retain the absolute executable and paths.
Process exit0, terminal accounting, EOF, zero active/terminated descendants and
no cleanup errors are verified. Wall233.969s, peak owned-job committed
memory3,030,605,824bytes; Torch allocated141,712,896/reserved178,257,920bytes.
FourCPU/one interop threads, TF32off,6GiB allocator and1500s/16GiB job bounds
were preserved. Initial binding took12.7211s; complete pair work, census and
serialization206.2219s; worker total232.8058s. These are measurement-workflow
costs, not a full stack/render speed. Host observations span0-18.7% CPU
(mean13.88%), minimum44.63GB available RAM; native build/drain activity was
separate and these are not controlled competitive timing measurements.

Freshly verified23 unique actual-run bindings,1,469,822,102bytes, including the
complete1.285GB rich JSONL, compact JSONL, sources, completion artifacts and
retained observer. All source bindings, reader metadata, noise and0.20-native
phase agreement are identical to cost1; no threshold retune occurred.
The299 cache-content/ARW-metadata snapshots match before/after and cost1.
This audit did not repeat the20GB cache rehash. The worker did hash every cache;
original ARWs received metadata checks, with earlier export content hashes
explicitly reused. No RAW decode or original-file write occurred.

| Actual artifact | SHA256 |
| --- | --- |
| Scientific receipt | `1aefde8c64f59abcabf7bdde5c3a6a2bbc87d9639e95a7bd92a09b53a7f3bab7` |
| Completion | `0315debcac2d2282823047cd77926917c7767feecb1f0a50a16e9681f6857f8c` |
| Process | `0f6fb944162489a33e6b8cb557905ce5ff7d5f585f0a2c662d306d505567aab8` |
| Compact observations | `e4996a3357c18b8e04f0cc91137faed7fb4610d33b0fc3a82e40aecca39e3238` |
| Rich observations | `6daa629882286921a8d9f41c270a196151693475aa0410faaac6f78f9fff6d6f` |

## Complete population and support

Streamed every rich/compact row: exact lexicographic2340 pairs,96 fixed tiles
each,224640 tiles,449280 original-green slots and898560 phase-power records.
All original patches were in bounds. Verified physical phase parity, original
centroids, zero local seeds and the exact compact/rich join. Recomputed all
449280 combination decisions from saved individual acceptance and displacement;
phase disagreements match exactly, every accepted f32 observation matches,
and every refusal remains null. All six census categories reconcile.
No new FFT, fit or pixel operation was performed in this audit.

| Span | Requested pairs | p1 accepted tiles | p2 accepted tiles | p1 final fitted edges | p2 final fitted edges |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 298 | 4890 | 4764 | 245 | 229 |
| 2 | 297 | 4337 | 4306 | 221 | 223 |
| 4 | 295 | 2486 | 2369 | 144 | 145 |
| 8 | 291 | 251 | 562 | 0 | 6 |
| 16 | 283 | 64 | 315 | 0 | 0 |
| 32 | 267 | 20 | 179 | 0 | 0 |
| 64 | 235 | 6 | 4 | 0 | 0 |
| 96 | 203 | 7 | 2 | 0 | 0 |
| 128 | 171 | 2 | 0 | 0 | 0 |

p1 accepts12063/224640 combined tiles; p2 accepts12501. More accepted tiles
does not mean more useful graph coverage. Before fitting/MAD, even granting
every pair with at least8 tiles produces only616/609 possible edges and
anchor149 components232/226. Thus the coverage failure was already determined
by the frozen observations. Individually accepted phases disagree in22637 p1
and17339 p2 cases; other disagreement counts include already-refused phases.
Refusal flags overlap and must not be summed as disjoint categories. In-bounds
support is not evidence of sharp/shared structure; working-white rejection is
not proof of physical clipping.

## Native graph verification

Clean cached recovery build3 records executable
`9e3637fe2fa9fb9f185df28b8a721ddc8b3d3bde3e967d8ccc9e3afa97c26c9e`.
Its0.906s is cached artifact confirmation, not fresh compilation speed; the
receipt identifies prior build2 compilation and its timed-out descendant.
The controls, replay and candidate jobs then complete cleanly in0.297,1.672
and0.422s. Freshly verified1448 graph/build references,330,501,022bytes.
The executable runs these exact tests:

```text
align_cmd::insect_blur_phase_graph::graph_input_and_centroid_controls --exact --nocapture
align_cmd::insect_blur_phase_graph::fit_and_solve_weevil_phase_maps --ignored --exact --nocapture
```

The second command runs with separate replay/candidate bound configs and an
isolated `STREHL_WARPMAP`. Independently compared every replay StageFit/refusal,
initial/final residual, fit, MAD scalar and keep mask with the retained
observer. The2314-edge/299-frame map is byte-identical to held SHA`4a76cd0c...`.
Replay receipt SHA`6287d628ce4981677bd948d267b3d6ab9dc4e72dd90c2243faddc36a088bb6be`.

Joined every candidate fitted/refused pair to its exact compact tile IDs;
recomputed connected components from saved fitted edges, cycle counts and
unplaced map states without refitting. Candidate receipt
SHA`b48fc0e38d61f17b6b539fa986d1eba6cb5fcb75aec21be96c0c4d711906b76c` agrees:

| Arm | All fitted edges | Anchor component edges | Placed | Cycle rank | Unplaced | Render eligible |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| p1 | 610 | 586 | 232 | 355 | 67 | false |
| p2 | 603 | 589 | 226 | 364 | 73 | false |

Cycle floors0.3118/0.2745 guide pixels are not evidence of improved physical
placement versus the replay's1.554: the populations and coverage differ
drastically, and candidate held-out values are null. This closes the fixed
reader/initializer recipe as a complete-stack candidate. It does not prove
that centrally symmetric blur invariance is useless in every setting, nor
identify a cause of the current photograph's softness. No additional search,
gate variation or partial-stack rendering is justified by these measurements.
