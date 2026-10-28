# Independent geometry and six-pair receipt audit

2026-10-27. **VERIFIED saved evidence; no new pixel, FFT, RAW or fitting job.**
The completed geometry controls and cost observation support one unchanged
full2340-pair census within its1500s bound. They do not establish that either
arm can place all299 frames, improve placement, or improve a photograph.

## Commands and integrity

Root executed Python3.12 with `-B -X faulthandler`:

```text
experiments/raw-quality-2026-10-27/insect-blur-phase/full/actual-controls.py --out outputs/raw-quality-2026-10-27/insect-blur-phase-actual-controls-1/output
experiments/raw-quality-2026-10-27/insect-blur-phase/full/actual.py --mode cost --out outputs/raw-quality-2026-10-27/insect-blur-phase-cost-1/output
```

The invocation/process receipts retain the actual absolute paths. Both jobs
exit0 with terminal accounting, zero active/terminated children, pipe EOF and
no cleanup errors. Freshly hashed27 unique bound references,177,716,717bytes,
including all completion artifacts, source bindings and retained observer
JSONL; all agree. The input snapshots contain299 cache identities and299 ARW
metadata records and are identical before/after. This audit does not repeat
the worker's approximately20GB cache census. Original ARW content hashes were
verified by the earlier export, not newly reread by this cost job.

| Receipt | SHA256 |
| --- | --- |
| Geometry scientific | `295299a92e53476a2839b58342f0ff69589d247195e0d93c456124358f64859e` |
| Geometry completion | `826f257cc3fbbdd4cb9dcfbe7ba9bf9fe69b3eda44b586e77ecc3e5b8be87d62` |
| Geometry process | `f3c1add749f49f1fd3a0a2e7955946bfc51a18a79e0d4535c0dd736e90b58982` |
| Cost scientific | `e48dfe80e523f675ec719e37f2fd92bfee530406db37a4bf8f2b7d517907ccae` |
| Cost completion | `d473c8b8b2c65f933513d915f0d7814d06a72e52b63ca542bd87bb932760c749` |
| Cost process | `608eea6689807c1ba9a8d112d024c4ded5f87a38ed3bfe00a9ab678d51a706f5` |

Producer remains actual.py`e3ce897a...`, frozen phase.py`99bca095...`, and
geometry controls`d5e4a9d1...`, as bound in the source review. These controls
were authored by this reviewer and independently source-reviewed by the
producer; this receipt audit is not an independent recreation of their math.

## Geometry and actual-record checks

The pixel-free controls passed in0.141s. Identity and tie cases have zero
geometry error; the independent noncentral2x2 composition differs by at most
9.095e-13native pixels, below1e-9. The largest f32 observation error is
1.419e-7guide pixels, below2e-5. Wrong inverse/native pitch/origin/centroid
scorers refuse; wrong center produces0.25guide error. Missing/refused or
disagreeing green phases yield null, and a missing phase dictionary refuses.
This establishes interface mechanics, not physical matching accuracy.

All six fixed pairs,576 tiles,1152 physical phase slots and2304 phase-power
records are present. All original patches are supported. The audit joined
every compact slot to its rich observation, independently recomputed all1152
phase-agreement/acceptance states from saved displacement and held prediction,
and checked every accepted f32 observation. Agreement differences recompute
exactly; nulls and census agree. No old refusal selected the population.

| Pair | p1 accepted tiles | p2 accepted tiles |
| --- | ---: | ---: |
| 0,1 | 7 | 3 |
| 0,128 | 0 | 0 |
| 104,105 | 20 | 18 |
| 148,149 | 29 | 25 |
| 149,181 | 0 | 5 |
| 170,298 | 0 | 0 |

Only two pairs in each arm even meet the eight-tile minimum before the native
MAD/refit. This is poor observed support. Multiple refusal reasons can attach
to one tile; their counts are not disjoint and phase disagreement also records
already-refused individual estimates. Working-white refusals are not evidence
of physical sensor clipping. No all-frame connectedness follows from these
six pairs, and p2 is not uniformly more permissive.

## Practicality and release boundary

The cost job took33.266s, peak owned-job commit3,031,764,992bytes. Torch
allocated141,712,896/reserved178,257,920bytes; these are allocator high-water
figures, not whole-device use. FourCPU threads/one interop, TF32off and the
fixed6GiB CUDA cap are recorded. No new RAW decoding occurred.

The pair campaign, including census/JSON serialization/flushing, took
0.9173327s. Scaling that interval by2340/6 gives357.7598s. Observed worker
overhead outside it is31.7995s, including15.2070s initial binding and final
cache verification/setup; charging it once gives389.5593s. The first pair's
warmup is conservatively multiplied in that simple projection. This remains
a conditional estimate: IO/cache state, full output volume and pair support
can differ. It is comfortably within1500s and justifies the one fixed census,
not a speed claim or a radius/gate change.

The full graph must retain every pair/tile, verify the native replay, report
all unplaced frames/cycles and refuse an unsupported render. No seed-map or
NCC fallback may fill gaps. Only complete baseline/p1/p2 photographs and the
fixed native witnesses can establish a useful result.

## Presentation-source check

Read-only reviewed full/views.py`e5a40b33eed14d42dcc26c516d0a498e5294bfa423a155d45b03436e9904aaa2`
against renderer`25e0e6ce...`: root path, three own masters, receipt/frame/support
joins, whole RGB16 pixel/ICC/description checks and exact rounded257 nativePNG
readbacks are consistent. JPEG98/subsampling0 is a full-size display, not a
lossless master. Float/CFA artifacts are file-bound, not reverse-transformed.
The helper explicitly delegates clean process completion to the root wrapper.
Native and Helicon geometry/development differences remain disclosed. This is
a source check only; no presentation has yet been executed or viewed here.
