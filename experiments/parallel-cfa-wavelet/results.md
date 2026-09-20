# Parallel complete-CFA replay: execution record

2026-09-19. This record separates execution repair from photographic quality.
The previous generated admission remains **false**. No default is promoted.

Root commands actually run (Python3.12, repository root):

```
python -I -B experiments/parallel-cfa-wavelet/run.py build --out experiments/parallel-cfa-wavelet/build-1
python -I -B -X faulthandler experiments/parallel-cfa-wavelet/run.py controls --build experiments/parallel-cfa-wavelet/build-1 --out experiments/parallel-cfa-wavelet/controls-1
python -I -B experiments/parallel-cfa-wavelet/complete-controls.py --controls experiments/parallel-cfa-wavelet/controls-1
python -I -B -X faulthandler experiments/parallel-cfa-wavelet/full-run.py cost --build experiments/parallel-cfa-wavelet/build-1 --screen experiments/parallel-cfa-wavelet/controls-1 --out experiments/parallel-cfa-wavelet/cost-1
python -I -B experiments/parallel-cfa-wavelet/cost-decision.py --cost experiments/parallel-cfa-wavelet/cost-1
```

MEASURED: fresh build1 compiled both crates in136.328s. All four control tests
passed (5.734s job). The driver then failed its final log-marker assertion:
it expected the previous full-control marker, while the copied test emits
`PARALLEL_CFA_FULL_MECHANICAL`. This mismatch was identified during the build;
no bound source was changed. The separate completion helper checks successful
process/cleanup, the bound log, unchanged sources/executable, actual unique
numeric/full records and quality preservation. Its receipt records the wrapper
failure explicitly. Independent review accepts that completion; no tests were
rerun or skipped to repair the marker.

VERIFIED on the independent fixtures: serial/parallel forward and inverse
coefficients are bit-identical at one/four threads, including reflected and
12-level one-axis domains. The finite exp80 weight times large coefficient
overflows the legacy product; scaled accumulation remains finite and agrees
with the independent f64 oracle. The70-source/order stress maximum component
error is0.000793 coefficient units. These controls do not prove arbitrary
unbounded f32 sums safe.

MEASURED: the actual generated preservation witness changes CFA by at most
0.0009765625DN and linear RGB by1.1920929e-7. Across the original twelve cases,
maximum candidate score movement is2.4064004e-7 and RGB-ratio movement is
6.3477867e-7. Baseline, variance/evidence and original quality decisions are
unchanged (probe timing excluded). The old weak-red90% and benefit failures
remain failures. Observer on/off remains exact. See the independent control
review; numerical continuity is not a new quality result.

MEASURED: source35 cost1 finishes successfully in21.016s job wall and43.15625s
job CPU. Source phase is18.3408052s and finish2.1419226s; peak job committed
memory is7,171,502,080 bytes. The complete4096-square/12-level inverse is finite
and the one-source hull returns actual gathered CFA exactly. Baseline/candidate
RGB16 are identical, pixel hash
`8adedb6d54417f5b51adfcf0ac952541fce8e3f3f7af2b0da572b3e591fe1323`.
This is one source, **not a complete stack or a photograph improvement**.

DERIVED under the frozen rule:70*source_phase+finish+120=1405.9982866s,
below1500s; memory is below12GiB. The feasibility decision is true. Multiplying
the entire one-source job CPU by70 gives3020.9375s, below the3600s job cap;
neither extrapolation measures the full run. Do not quote an implementation
speedup from this unpaired one-source timing.

The complete70-source observation has now finished. Commands actually run:

```
python -I -B -X faulthandler experiments/parallel-cfa-wavelet/full-run.py full --build experiments/parallel-cfa-wavelet/build-1 --screen experiments/parallel-cfa-wavelet/controls-1 --cost experiments/parallel-cfa-wavelet/cost-1 --out experiments/parallel-cfa-wavelet/full-1
python -I -B experiments/parallel-cfa-wavelet/photo-compare.py --run-dir experiments/parallel-cfa-wavelet/full-1
```

MEASURED: full job1253.844s wall (20.90min),2365s CPU, peak job committed
memory7,812,116,480 bytes. Both6920x4612 RGB16 masters exist. Source phase
1251.2119537s; finish2.0805804s. Original metadata/map remain unchanged, and
the complete baseline pixels match the historical baseline exactly. Source35
within this run also matches its separate cost checkpoint in original u16,
all four gathered planes, guide/variance, all coefficient variances and16 seeds.
The job is within its resource caps; this timing does not establish competitive
speed and excludes solving the already-held alignment map.

Candidate TIFF SHA256:
`0b3e50438b3215513234713862716a4bd4c50cc6a4ca6c9428f2b17a5edab9d6`.
Full masters are `full-1/output/{baseline,candidate}.tiff`; whole views and eight
native comparison boards are under `full-1/photo-comparison-1`. The conversion
uses the same ICC profile and fixed RGB16-to-RGB8 mapping, with no new tone or
registration fit. Helicon B retains its known different native scale and
development/alignment limitations; it is a comparator, not pixel truth.

**Independent photographic decision: REJECT.** Root inspected both complete
overviews and all eight native boards, and the independent reviewer agrees.
The pale background is broadly similar/slightly smoother, while bright
structures become more mottled. Shorter facet rays trade into cyan/green spread;
the dark inclusion gains conspicuous green/magenta patches above the bright
edge, and its long tail becomes a broader multicolour smear. The competing
structure remains recognizable, but there is no convincing extra real detail
or compensating whole-image gain. Helicon B has substantially cleaner compact
boundaries in these views. See `photographic-review.md` for the independent
assessment and its limits.

These are qualitative observations, not calibrated colour accuracy, sensor
noise measurements, or a causal decomposition of the artifact. They do not
identify wavelets generally as the cause. They decisively reject advancement
of this exact full operator. No second-scene run, parameter sweep, further
speed optimization or product-default promotion is justified for it.

The owner was shown both **complete** stack overviews and both full-resolution
master links, explicitly labelled as a rejected candidate. Numerical stability
and parallel arithmetic remain reusable work, not an image-quality victory.
