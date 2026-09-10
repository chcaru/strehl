# Native GPU gather: exact output, no reliable elapsed-time gain yet

MEASURED with committed Parallel256 source cbbb2bfa68dbd0444d7d74e48c685fa420560bbd.
The strict f32 shader and CPU f64 coordinate path preserve every tested output.
GPU remains default-off and experimental. This is a preservation and execution-cost
result, not a photographic-quality or SOTA result.

Commands actually run from the repository root:

~~~powershell
python -I -B experiments/native-pyramid-profile/build.py --gpu-gather --output-dir experiments/native-gpu-gather/build-native-2
python -I -B experiments/native-gpu-gather/run.py
python -I -B experiments/native-gpu-gather/run-native.py
python -I -B experiments/native-gpu-gather/run-native.py --timing-109
~~~

The held runner revision is cbbb2bfa; subsequent source-only device-coordinate
work is separate. Full absolute commands, environment, original-input plan,
executable/source hashes, terminal Job accounting and costs are in each
invocation/process receipt. The release compile printed Compiling strehl-cli
and took 133.312 wall / 263.703125 child CPU seconds; no timing includes this
build. CLI SHA256 f3ac79f4b97f7b29f590b368bf2d0d29dd414a3fd29addc795d4ba971fd079c4.

## Controls and native preservation

Run-4 visits and passes all 18 fixed controls under Parallel256. Quantizer and
live descriptor destroyers pass; the separately reported undecorated SPIR-V
diagnostic reproduces the original one-code failure. Thus NoContraction
restrictions fix the demonstrated input on this hardware/binary; the experiment
does not identify a particular machine instruction or prove FMA alone caused it.
Run-4 costs 0.703 wall / 0.3125 child CPU seconds; its report SHA256 is
3980091736a3131d3b5b2f4386b4f89837d9236bb91161e2cae534ece1e523f9.

All 13 native TIFFs across native-112-1 (6), native-112-2 (3), native-109-1 (4)
match their independently held corpus-specific whole-file and decoded RGB16
hashes. They are distinct render executions of two fixed stack prefixes,
not 13 independent scenes. Each output contains 98,898,048 RGB16 values.
Both remosaic and rounded-direct consumers and initial numeric-log
off/on/placebo are covered. The scheduling revision adds a log label; the
earlier log identity is evidence for the same observer behavior, not a claim
that its source text is unchanged. Optimized native height 4688 exercises
multiple 256-row batches and the final 80-row strip.

| Corpus | Whole TIFF SHA256 | Decoded RGB16 SHA256 |
| --- | --- | --- |
| 112, eight RAWs | ba96c63dd56f2729ba2ed25fedc19b291a4a78f9992f6823ce501a1df2a8bdc6 | d5fd6969b77fc94334995dea771e434f65f2b3cf782e1d683ca2872639595a1a |
| 109, 22 RAWs | 84f24ff6cdeae80f612ec6a2048dc888715eb8a2e632be29efcb9eefcdc61851 | 1bd230a17e40030159540be6f75a958a839cd422b29d78afcd524f3cfe4c53e1 |

The native-112-2 pilot reads 4.907 s CPU, 8.594 s GPU/Serial32, 4.796 s
GPU/Parallel256. This is not an alternating benchmark; do not derive a
production speedup from the pilot.

## Complete process cost on 109

Same executable, same 22 original RAWs, same saved alignment, rounded-direct
consumer, eight workers, log off; chronological CPU/GPU/GPU/CPU:

| Arm | Wall seconds | Child CPU seconds | Peak Job committed bytes |
| --- | ---: | ---: | ---: |
| CPU 1 | 11.703 | 68.515625 | 2998943744 |
| GPU 2 | 11.218 | 44.046875 | 3578957824 |
| GPU 3 | 11.234 | 41.593750 | 3580096512 |
| CPU 4 | 11.156 | 67.781250 | 2997882880 |

GPU logs establish 22 RGB and 22 green-only completions per GPU render;
CPU arms contain neither. There is no eligible-call CPU fallback.

DERIVED: per-setting minima are 11.218 s GPU and 11.156 s CPU, a 0.56%
GPU slowdown. Forward comparison suggests 4.14% faster and reverse suggests
0.70% slower; the CPU order change alone is 4.67%. Treat elapsed time as
near-flat within this observed drift, not a precise speed difference.
There is no reliable elapsed-time gain and no default promotion.
Child CPU work does fall, but this is not a measurement of GPU work or energy.
Peak Job committed memory grows from about 3.00 GB to 3.58 GB; this does
not include a separate GPU-local memory high-water measurement.

Timing includes startup, device initialization, host preparation, transfers,
synchronization, RAW decode, merge and TIFF writing. The alignment solve is
excluded through a saved map. It is not a fair full-workflow competitor ranking.

## Next bounded mechanism

MEASURED in the verbose optimized 112 arm: descriptor upload still dominates
transfer volume, about 528 MB per frame. Parallelism repairs CPU preparation
but still uploads one 16-byte plan per native pixel. Next source-only candidate
moves only f64 coordinate planning to a separate device kernel. The existing
f32 image arithmetic, injected noise, merge, quantizer and defaults stay fixed.
It must preserve exact support/base/fraction decisions before any native run,
and must pass a further same-binary alternating pipeline comparison before
being called a speed improvement. No broader alignment or quality conclusion
follows from these preservation tests.

Only the selected original-input size/mtime checks and saved-map hashes were
checked before and after runs. No global corpus audit is claimed.
