# M-PHASE0-PIPE — fold scaling and bounded decode handoff (MEASURED)

**Verdict: D13 is FALSE, and the queue is a measured negative result.** On two
real 64-frame stacks, the pyramid fold's first doubling below 1.10x is 8→16:
**1.082x** on `112MSDCF` and **1.078x** on `bee-3-cpl`. Decode saturates at
16 threads; fold saturates one doubling earlier, at eight workers. A bounded
decode→fold rendezvous was implemented and proved byte-identical, but its
best-of-five wall time was **1.3% slower** and **2.1% slower** on the two
stacks. It therefore failed the preregistered 1.05x retention bar and was
removed rather than shipped behind a flag.

## 1. What D13 says

The proposal's assertion is not simply “fold scales usefully past eight.” It
is:

> Pyramid folding continues scaling beyond eight workers on an idle 16-core
> machine sufficiently to justify worker-count-independent reduction and
> memory redesign.

The proposal supplies no numerical D13 threshold. D15 owns the later
≤0.15 s/frame, ≤6 GiB, byte-invariance, and no-staircase end-state bars. Before
measurement, this lane operationalised “sufficiently” as at least 1.20x from
8→16 on **both** stacks and saturation as the first doubling below 1.10x on
both. Those choices, the load rejection rule, and the queue retention rule
were frozen in `experiments/M-PHASE0-PIPE/PREREGISTRATION.md` at `867c6041`.

## 2. Provenance and controls

| item | value |
|---|---|
| host | Ryzen 9 9950X3D, 16C/32T; Windows 11 build 26200; 61.6 GiB RAM |
| baseline | build id `a4b2ba8fdde6`; SHA-256 `C6C2FDB62F36A6E2E978F94524B397F5F672A4A9E1B954EADB0FF29C235E69EB` |
| queue candidate | build id `1da5e87b`; SHA-256 `F123B5DFBAB04812DAD38CADC85871AB93DCF78145BFB0BBF913B09C1BF0D04B` |
| harness | `experiments/M-PHASE0-PIPE/measure.py`, commits `a4b2ba8f`, `1ce83ddc` |
| inputs | first 64 name-sorted ARWs from `112MSDCF` and `bee-3-cpl`, with fixed lane-owned warp sidecars |
| timing | whole-process QPC wall time plus the binary's fold `Instant`; ascending and descending worker sweeps |
| load gate | ≤15% five-second pre-load and ≤10% during-run external busy after subtracting child CPU |

The untracked pre-commit scratch tree at `out/source-prototype` is **not**
provenance evidence. It omitted `decode_queue.rs` and its `merge_cmd.rs`
resolved that module through an absolute path into the live working tree.
That generator/checker cancellation makes the snapshot inadmissible under
rule 35; no result in this report relies on it. The candidate is identified
instead by the committed source at `1da5e87b`, its embedded build id, and the
executable hash above.

The accepted commissioning pair measured 1.298 s normally and 3.326 s with an
independently requested 2,000 ms sleep: **+2.028 s**, inside the registered
1.750–2.500 s interval. Both rendered the same nonzero TIFF, SHA-256
`1EF94527CF39AA7A35D134D6C1AC63DE7F560AE5FB490EB9DCDFD403841F2487`;
external load was 5.3% and 6.9%. Thus the wall timer detected a known slowdown.

Every accepted render was fully hashed and independently decoded as a nonempty
`2344×3516×3` `uint16` TIFF with nonzero pixels and sum. Before/after
`Get-ChildItem -Force` manifests were identical:

* `112MSDCF`: 79 ARWs, 2,959,888,384 bytes, `68A5344D...006538A`.
* `bee-3-cpl`: 299 ARWs, 11,308,236,800 bytes, `55BDDCF8...87604A`.

The capture trees remained read-only.

## 3. D13 curve

Chosen is the smaller **valid** fold time per rule 16. External load and peak
working set belong to that same run.

| stack | workers | fold s | wall s | external busy | peak GiB | output SHA-256 prefix |
|---|---:|---:|---:|---:|---:|---|
| 112 | 1 | 55.8 | 56.353 | 7.1% | 2.10 | `0E81CC157542FA37` |
| 112 | 2 | 35.0 | 35.572 | 7.9% | 4.17 | `AD6CBA97500E6DFF` |
| 112 | 4 | 24.7 | 25.266 | 9.9% | 8.20 | `5280249AF021AC0D` |
| 112 | 8 | 21.0 | 21.529 | 9.5% | 16.38 | `79302FBDCFFFA3A9` |
| 112 | 16 | 19.4 | 19.992 | 7.0% | 31.46 | `CFE0993F5225A435` |
| 112 | 32 | **53.3*** | 53.847 | **14.7%*** | 52.17 | `05FAF5FC86CF8AC0` |
| bee | 1 | 54.7 | 55.225 | 5.4% | 2.10 | `34F8D00FAE4AC99D` |
| bee | 2 | 40.3 | 40.852 | 8.2% | 4.17 | `6FA002885BC7988B` |
| bee | 4 | 27.0 | 27.614 | 7.2% | 8.32 | `43A2AB9B1BC91D60` |
| bee | 8 | 22.2 | 22.752 | 8.8% | 16.43 | `03DE923040A93810` |
| bee | 16 | 20.6 | 21.203 | 10.0% | 32.05 | `23DE6F8B460BE6D3` |
| bee | 32 | **64.7*** | 65.378 | **18.2%*** | 48.90 | `3FB1ED77273A3C57` |

\* W=32 is reported because it was run, but is **rejected**, not part of the
valid curve. Eight 112 attempts had 14.7–26.7% external load and 53.3–72.5 s
fold times; four bee attempts had 14.7–24.0% external load and 57.9–81.6 s
fold times. Peak RSS reached 45.6–53.7 GiB. Repeating with 60–120 s cooldowns
did not produce a valid SMT arm, so no idle W=32 claim is made.

Valid doubling speedups:

| stack | 1→2 | 2→4 | 4→8 | 8→16 |
|---|---:|---:|---:|---:|
| 112 | 1.594x | 1.417x | 1.176x | **1.082x** |
| bee | 1.357x | 1.493x | 1.216x | **1.078x** |

Both 8→16 results miss 1.20x, and both are below 1.10x. **D13 is FALSE;
fold saturation is eight workers.** Decode's measured saturation is 16
threads, so the two stages do not saturate together—but the difference runs
opposite the queue-starvation hypothesis: fold stops scaling first.

The registered N=29..36, W=4 fine ladder measured
`3.5, 3.6, 3.8, 3.7, 3.9, 4.2, 4.2, 4.2 s`. N=33 is 5.4% above N=32, but
32→33 is not the largest adjacent increment; the registered staircase test is
therefore false. This descriptive arm used alignment off because a warpmap's
stack identity changes with N.

## 4. The Rust candidate

Commit `1da5e87b` implemented `STREHL_DECODE_FOLD_QUEUE=on`; unset, blank, and
`off` retained the serial path and unknown values failed. It added:

* a zero-capacity `sync_channel` per existing contiguous fold chunk;
* one scoped decode producer and one fold consumer per active chunk;
* unchanged worker count, chunk boundaries, within-chunk frame order, part
  order, and `BandMerge::absorb` order;
* a printed bound of at most one extra producer-held decoded frame per chunk,
  independent of stack depth;
* order, exactly-once, overlap, one-frame-ahead, and both error-direction tests;
* byte-freeze environment isolation.

The consumer used the same refactored registration/deinterleave/fold function
as serial execution. Fold consumers used scoped OS threads rather than parking
Rayon workers needed by decode.

Unset/off/on on aligned `112MSDCF` were byte-for-byte identical:
`5280249AF021AC0D29E2403E5349FAC91D53FB37A0539F34E875EE100F8D7513`.
Off/on on aligned `bee-3-cpl` were identical:
`43A2AB9B1BC91D6049F42A35D5804922BFED25973B2F83AB74A2BC18F3286690`.

An independent holdout used 16 `coffee-bean` frames, W=8, alignment off. It
confirmed distinct SERIAL/BOUNDED banners, nonzero identical decoded TIFFs,
and byte equality at
`5E4B5E6C4FADDEAFE930BB2D3D9B2973BCFE8A6F5AB3BFC6DA8D4B05177A6C27`.

## 5. Queue speed and decision

These are wall seconds from five accepted samples per mode at the unchanged
default four-worker plan. The fifth bee sample uses complementary valid halves
from consecutive replacement attempts; four pairs were wholly valid. That
weakens pairwise drift cancellation, but cannot change the decision because
the fully paired 112 result alone fails the hard best-of-five bar, and using
all valid bee arms makes its result slightly worse.

| stack | serial wall s | queued wall s | best speedup | median change | external busy | peak GiB off/on |
|---|---|---|---:|---:|---:|---:|
| 112 | 25.766, 24.980, 26.103, 26.666, 25.069 | 25.293, 26.470, 25.945, 26.147, 26.392 | **0.9876x** | **+1.48%** | 4.8–9.9% | 8.33 / 8.60 |
| bee | 24.893, 26.471, 25.112, 26.041, 25.195 | 25.427, 26.652, 26.119, 25.921, 26.605 | **0.9790x** | **+3.67%** | 6.3–9.5% | 8.32 / 8.61 |

The required result was ≥1.05x on both stacks, with queued median no more than
2% slower. Both best results are below even the preregistered 1.03x
negative-result floor, and bee also fails the median guard. The extra
concurrency raises RSS by about 0.28 GiB and CPU work without reducing wall
time. **It does not earn its complexity.**

Commit `a35691d3` therefore removed the flag and all queue Rust. The candidate
and withdrawal net to no shipping Rust diff. This is deliberate: a reversible
experiment was built, measured, and rejected rather than left as an attractive
unproven switch.

## 6. Verification and limits

Commands that passed:

* `cargo build --release -p strehl-cli` from a fresh lane target.
* `cargo test --release --workspace --all-targets --no-fail-fast --quiet`:
  all tests passed; one pre-existing ignored test; all three byte-freezes
  reproduced twice.
* Candidate queue's four focused tests and flag-resolver test.
* Independent final `cargo check -p strehl-cli` and holdout render/hash check.

Clippy with `-D warnings` is not green because of pre-existing warnings in
`build.rs` and `strehl-core`; `cargo clippy -p strehl-cli --bin strehl
--no-deps` completed and introduced no queue warning. Repository-wide
`cargo fmt --check` is likewise already red outside this lane.

Not verified: an idle W=32 curve, a fifth wholly valid bee pair, another camera
or compression ratio, or performance on another machine. Background work
could only slow a run, but correlated variation can move a ratio either way;
that is why every >10% arm remains recorded and excluded. A rejected loaded
pair misleadingly made the queue look about 8% faster, while the accepted
campaign made it slower—the load gate changed the conclusion, not merely the
error bars.

## 7. Final close-out and M11 handoff

### 7.1 Evidence ledger

Only these results survived the registered load and output-validity gates:

| result | admitted evidence |
|---|---|
| timer commissioning | One control pair: 1.298 s baseline, 3.326 s with a planted 2,000 ms delay, delta +2.028 s; 5.3%/6.9% external load; identical nonzero output hash |
| D13 scaling | Two real stacks at W=1/2/4/8/16; selected fold curves `55.8/35.0/24.7/21.0/19.4 s` and `54.7/40.3/27.0/22.2/20.6 s`; 5.4–10.0% external load |
| fine-N diagnostic | N=29–36 at W=4, 15 accepted alternating-direction arms across eight settings; selected fold times `3.5/3.6/3.8/3.7/3.9/4.2/4.2/4.2 s`; 5.5–9.7% external load; registered staircase test FALSE |
| queue throughput | Five accepted samples per mode on each stack; best speedups `0.9876x` and `0.9790x`; queued medians +1.48% and +3.67%; 4.8–9.9% external load |
| queue transparency | Fixed-worker off/on renders matched byte-for-byte on two aligned stacks and one independent holdout; this was experimental evidence, not a permanent automated freeze |

The following are **invalidated**, not weak evidence:

* W=32: all 12 completed arms failed the external-load gate—eight 112 arms at
  14.7–26.7% and four bee arms at 14.7–24.0%. They establish no idle-SMT
  timing.
* Queue timing: 22 additional arms exceeded 10% external load and were
  excluded. The originally circulated `0.948029x` best / `0.958487x` median
  came from 19.6–38.8% external load and is not the queue verdict.
* The fifth bee throughput sample per mode came from consecutive replacement
  retries; only four bee pairs were wholly valid. The five fully paired 112
  samples independently fail the retention bar.

Candidate `1da5e87b` was withdrawn by `a35691d3`. `decode_queue.rs`, its module
wiring, flag/parser, and byte-freeze environment entry all left the tree.
`cargo build --release -p strehl-cli` and
`cargo test --release --workspace --all-targets --no-fail-fast --quiet` both
exited 0 without them.

### 7.2 Can M11 be measured here?

**Not currently, and no finite quiet-window duration fixes that.** Scorecard
v1.7 classifies M11 as blocked on `(a)(b)(d)`: no admissible detail/quality
qualifier, unresolved native-scale geometry, and no quality-qualified
common-input comparator output. Native decode or fold timing is diagnostic;
it cannot populate the end-to-end product/comparator axis. The required idle
window length is therefore **NOT MEASURED**, and scheduling one now would
consume the program's single clean window without making M11 measurable.

Once those scientific prerequisites exist, the frozen execution is one
warm-up followed by six alternating-order scored sweeps per setting. It times
process start through closed, flushed, hashed TIFF and manifest, including the
whole process tree, registration, merge, colour, and write. Every hard bar
must pass:

* warm common-input throughput at least `2.00x` the fastest quality-qualified
  comparator;
* candidate/default warm-wall ratio at most `2.00`;
* native-RAW CPU at 16 workers at most `0.15 s/frame`;
* hybrid at most `0.06 s/frame`;
* cold no more than warm plus 20 s;
* readable 100-frame live master within 10 s of the last shutter.

Before reserving a host, commission every complete arm and measure one
non-scored dry-run campaign; that measured duration, including the documented
reboot or equivalent cache reset required by the cold arm, must define the
window. Do not estimate it from this lane's 64-frame fold-only timings.

### 7.3 Timing gate to inherit

1. Sample whole-host busy time for five seconds before each arm; start only at
   `<=15%`.
2. During the arm, subtract **whole-process-tree** CPU from system busy CPU and
   require external busy `<=10%` of wall time times 32 logical processors.
   Anything above that is invalid and must not enter a minimum, median, or
   ratio.
3. Alternate arm/sweep order. Retry a rejected paired position as a pair;
   never splice a favourable loaded half into a clean comparison.
4. Record executable and input provenance, QPC wall time, process-tree CPU,
   system/external busy, peak memory, bytes read/written, stage banners, full
   output hash, and a nonzero decoded-output witness.
5. Before results, require the M11 controls: a planted one-second sleep adds
   `1.00±0.05 s`, an asynchronous child writer remains inside the timer, and a
   cold arm follows a documented machine-wide cache reset.

Contention biases absolute time upward, against an absolute speed pass;
correlation with arm order can move a ratio either way. A pre-run idle sample
does not license a run whose measured external load later crosses the gate.
