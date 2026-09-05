# M172: the D9 negative control fires

**Status:** VERIFIED BY RUNNING.

**Verdict:** the pre-D9 product is observably worker-count dependent, both in
the delivered uint16 pixels and in the f32 planes immediately after
`BandMerge::finish`. The original N=16, W1-versus-W16 gate was a structurally
inert worker pair, not evidence that the defect had disappeared. At the same
N=16 and with every other setting unchanged, W1 versus W2 fires. Keeping the
W1/W16 pair instead, raising N by one frame to N=17 fires. The post-D9 product
is byte-identical across W1/W2/W4/W8/W16 on the registered N=33 aligned arm.

The clamped resampler is outside this report. Every run explicitly selected
ordinary `catmull-rom`.

## 1. Frozen provenance

The existing throughput driver, verifier, and failed N=16 record were secured
first at `09b4dccff4c60ef5414d8150d53a21e08ffa16d9`.

The output-control matrix was committed before measurement at
`32dd0cd37ff8ece812b1e2c06d1432b4df8376e8`. The f32 observer and its protocol
were committed before either diagnostic build at
`ee3e85d6e7733f6eb69975a01d187338027d49aa`.

| Arm | Source commit | Unmodified binary SHA-256 |
|:--|:--|:--|
| pre-D9 | `1a6fd10c94dcb4b780f6af78c46c62a156c39b71` | `5C87BE23B654373192B4A561C232779A870ED1614C0BDD69EF9284376D854A93` |
| post-D9 plus bounded memory | `a97275817c58e164f75c7cd3d80ca99444a2a145` | `0EC15D05CCA90352101BC07088A29D75E64450DC678C5607BA90A778D0BF4E96` |

Every product run used the first N lexicographically sorted native ARWs in
`D:\personal\macro\bee-1-cpl`, read-only, with:

```text
strehl.exe stack D:\personal\macro\bee-1-cpl --limit N --out OUT.tiff --merge pyramid --pyramid-gate 2.0 --resampler catmull-rom --cover scale --linear-srgb --demosaic
```

Alignment-off runs set `STREHL_ALIGN=0`. Alignment-on runs named M139's
registered N=33 sidecar through `STREHL_WARPMAP`; its SHA-256 is
`A4B99B954EF98C0065FC35A36203545AEEF9A50997BC6B53F68BF859D9CE79DF`.
Every run used an isolated `STREHL_CACHE_DIR`. No automatic retry ran.

## 2. What the original gate got wrong

At `1a6fd10c`, `run_pyramid` resolves `workers`, sets
`per_chunk = ceil(frame_count / workers)`, folds each chunk sequentially into a
fresh `BandMerge`, collects the partials in frame order, then calls
`BandMerge::absorb` left-to-right. `BandMerge::absorb` adds the partial
`num`, `usum`, and `den` arrays with ordinary f32 addition.

For N=16/W16, `per_chunk` is one. Each partial therefore contains exactly one
frame. Absorbing those one-frame partials in order reconstructs the same
left-to-right addition tree as W1. This predicts equality before any
quantization. Both the f32 and uint16 observations confirm it.

For N=16, the requested worker counts produce chunk lengths 16, 8, 4, 2, and 1.
Only the endpoints reconstruct the same tree; W2/W4/W8 regroup additions.
For N=17/W16 the chunk length becomes two, so even the endpoint pair is no
longer equivalent.

## 3. Delivered-pixel control

### 3.1 Worker spread, N=16, alignment off

| Workers | Pixel SHA-256 |
|---:|:--|
| 1 | `A197B0704EE39983D67264C2823CF50695E9DE1C44B834D32257612FC2004185` |
| 2 | `3A31F9D0DC45429849F88540FE6AFCD6DF5765FB428C6161D2795C8851914541` |
| 4 | `3AC49AEA332E44406703C2EBA3A3B219CF49C70DE76BA129686D81884FA98EF3` |
| 8 | `03A81E625F48606259601B20223CD780518689C52759C0CD4F3DE36299935E22` |
| 16 | `A197B0704EE39983D67264C2823CF50695E9DE1C44B834D32257612FC2004185` |

**Result:** four distinct hashes. The smallest configuration repair is to keep
N=16 and compare W1 with W2 instead of W16. No input, kernel, alignment, output
format, or source commit changes.

### 3.2 Frame count, alignment off

| N | W1 pixel SHA-256 | W16 pixel SHA-256 | Distinct |
|---:|:--|:--|---:|
| 16 | `A197B0704EE39983D67264C2823CF50695E9DE1C44B834D32257612FC2004185` | `A197B0704EE39983D67264C2823CF50695E9DE1C44B834D32257612FC2004185` | 1 |
| 17 | `BFE7586860BACAF272ABEAC16487C3D1F6E98E6EE772CA04B9EDF6463D939DBF` | `DD2687FD69ED68E571EF322F6D366014F56D31B2F6F2F3CB4A6AA108C332CE92` | 2 |
| 33 | `1B028B8EF37F5D360814E8EDF45836A91235037319D0ADF25BBD9E6B915820D0` | `102E034881B13991928DD413938D79C638D451B704C40C13A95FF8BE57034F11` | 2 |

**Result:** if W1/W16 must be retained, adding one frame is the smallest tested
change and makes the negative control fire.

### 3.3 Alignment, N=33

Alignment is not required to expose the defect: unaligned W1/W16 already
differ. With the registered sidecar enabled, all five pre-D9 worker counts
produce distinct pixel hashes:

| Workers | Pre-D9 aligned pixel SHA-256 |
|---:|:--|
| 1 | `D42D0552A5FB5710BA4AE33C305721F8E98C695B11C89CDFB34859B7982B9F1D` |
| 2 | `78D78FC0A8C284C343EAB7472B34A3990BC3D8E18D21DDCFEF70A39E3BCBBB45` |
| 4 | `6EFC261E892DCDB5D492AD3FD79BDC7E5A208D93D0227A41B258FB3B900F9B89` |
| 8 | `2E397E4DD5D5BC1ECD0AC652C446D4700DAE872F55FF50C99694B8392CC9EF8F` |
| 16 | `A9913288AE46442E553E598347150026AD503E94F5EB5DDD8EA2375E6FE9C88D` |

Alignment changes the operands and the resulting hashes, but it is not the
cause of worker dependence. The cause is the chunk-dependent addition tree.

## 4. Before quantization

`float-witness.patch` adds a read-only observer immediately after
`BandMerge::finish`, before demosaic and uint16 encoding. It hashes the plane
count, plane lengths, and every `f32::to_bits()` value in plane-major order
with FNV-1a-128. Every observed arm covered 32,966,016 f32 samples.

| Workers | Pre-D9 N=16, alignment-off f32 fingerprint |
|---:|:--|
| 1 | `2D57F3FA0432B536138CCFA850D8BE90` |
| 2 | `70283E61417CDB2F506275B8F5D87ECB` |
| 4 | `C5EF68EA7D2EC1C5E665C62B849BF259` |
| 8 | `D57C8A1E148386C72688778D530B9ABB` |
| 16 | `2D57F3FA0432B536138CCFA850D8BE90` |

The f32 population has the same four-class pattern as the delivered pixels.
Therefore final quantization did not hide the W2/W4/W8 differences, and it did
not manufacture the W1/W16 equality. That endpoint pair is already equal at
the highest-precision merge output.

On the registered N=33 aligned stimulus, pre-D9 W1 and W16 differ:

- W1: `A7D21BD42D9E4652922952965CDAE3DB`
- W16: `DF86127B483FE65139B7BE0778187A0C`

Post-D9 W1 and W16 both read
`A38952442C2F4FF206A49DBE75808717`.

## 5. Repaired arm and observer controls

The post-D9 N=33 aligned product produced one pixel hash across all five worker
counts:

`6EFC261E892DCDB5D492AD3FD79BDC7E5A208D93D0227A41B258FB3B900F9B89`

and one full TIFF hash:

`9CCF896743B08E68AB08E4437EC4E3EAF2AAD8D37884170E95067577C80286B5`.

That output equals the pre-D9 W4 output, which is the canonical four-chunk
arithmetic lattice D9 deliberately retained.

The observer was built from both exact source commits, using the corresponding
source commit as `STREHL_BUILD_ID`. Diagnostic binary SHA-256 values were:

- pre: `D08C68EFEA6395D485735F6F33F4D51FD74F44AEDD8F0EDA20C6FB190D9E80B7`
- post: `8B4D020F4DD33B6C2F15708F9B8BE3517C559B3162CFD12EBA4951F7C51FFDC4`

At pre N=16/W4, probe on and off both reproduced the unmodified product's pixel
hash `3AC49AEA332E44406703C2EBA3A3B219CF49C70DE76BA129686D81884FA98EF3`
and full TIFF hash
`64470B13900ED3B73C2521448CFCC41E3615D8AB65A9CA80F4BE09F0D9BF6940`.
Every other diagnostic run also reproduced its unmodified product reference
exactly.

`verify_negative_control.py --self-test` independently re-derived both records
and rejected five plants: an inert pre arm, divergent post pixels, divergent
post f32 planes, observer perturbation, and record corruption.

## 6. Consequence

The pre-D9 negative control is real and cheap. The D9 repair is now supported
by a bidirectional product result on one registered stimulus: five distinct
pre-D9 hashes become one post-D9 hash, with the same result before
quantization.

The old throughput campaign's N=16 W1/W16 gate remains an intentional failed
record and must not be reinterpreted as evidence. Any resumed timing protocol
must either compare all five workers at N=16 or retain W1/W16 and use N>=17.
No timed throughput pairs were run under the powerless gate.

## 7. Retained evidence

- `experiments/M172-worker-memory/results/negative-control.json`
- `experiments/M172-worker-memory/results/float-witness.json`
- `experiments/M172-worker-memory/results/negative-control-summary.json`
- `experiments/M172-worker-memory/negative_control.py`
- `experiments/M172-worker-memory/float_witness.py`
- `experiments/M172-worker-memory/float-witness.patch`
- `experiments/M172-worker-memory/verify_negative_control.py`

TIFFs, build trees, caches, and binaries remain under ignored `out/` and are
not committed.
