# m10-deep-align — deep-stack global alignment

Harness for milestone **M10**, which attacks SYNTHESIS **risk 11**: neither of the
project's two alignment strategies survives a 100+ frame stack. Chaining accumulates
bias; a single fixed reference runs out of shared in-focus content.

The report is [`docs/research/M10-deep-alignment-measured.md`](../../docs/research/M10-deep-alignment-measured.md).
The registered design is [`PREREGISTRATION.md`](PREREGISTRATION.md) and it was written
before any solver ran.

Nothing here modifies `crates/`. Following M9's precedent, every aligner variant lives
inside this crate.

## Shape of the experiment

The Rust binary only ever measures **direct pairwise fits between two real decoded
frames**. It never composes, never resamples a frame into another frame's grid, and
never writes an aligned image. Its whole output is a CSV of edges:

```
i, j, span, ok, used, rms, a_re, a_im, b_re, b_im, lever, ...
```

Every strategy — chaining, keyframe ladders, bundle adjustment, parametric curves — is
then a different *estimator over that same edge set*, implemented in Python. That
separation is deliberate: all strategies see identical measurements, so any difference
between them is the strategy and not the estimator.

## Layout

| Path | What it is |
| --- | --- |
| `src/plane.rs` | CFA-quad green plane (3516x2344), decimation, bilinear sampling, corner radius. |
| `src/align.rs` | The ported similarity estimator. `AlignCfg::m3()` matches M3's configuration (margin 10); `m10()`, `wide()`, `wide64()` are the M10 variants. |
| `src/synth.rs` | Synthetic stacks with planted ground truth (P1, P4). |
| `src/field.rs` | Resampler-free band-limited field: two frames are independent point samples of one continuous function, so no interpolation kernel touches either (P6). |
| `src/main.rs` | Modes `synthetic`, `floor`, `edges`, `synth`, `lock`, `increment`. |
| `m10_lib.py` | Similarity algebra, edge reader, weighting, all solvers, all metrics. |
| `m10_*.py` | One script per registered measurement. |
| `data/` | Raw CSVs. Committed, per project rule 12 — the orchestrator re-verifies against these, not against the prose. |
| `out/` | Console logs of every run quoted in the report. |

## Reproducing

`cargo` is not on `PATH` in a fresh shell:

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd experiments\m10-deep-align
cargo build --release
```

Measure the edge sets (the only expensive step; ~68 s for coffee-bean across both
configs, including decode):

```powershell
$SPANS_DEEP = "1,2,3,4,5,6,8,10,12,16,20,24,32,40,48,56,64,72,80,88,96"

.\target\release\m10-deep-align.exe edges C:\dev\macro\test\coffee-bean coffee-bean `
    --case coffee-bean --cfg m10,wide64 --spans $SPANS_DEEP --direct0
.\target\release\m10-deep-align.exe edges C:\dev\macro\test\109MSDCF shallow-109 `
    --case shallow-109 --cfg m10,wide64 --spans 1,2,3,4,6,8,12,16 --direct0
.\target\release\m10-deep-align.exe edges C:\dev\macro\test\119MSDCF shallow-119 `
    --case shallow-119 --cfg m10,wide64 --spans 1,2,3,4,6,8,12,16,24 --direct0
```

`--direct0` adds every frame-0 pair on top of the span ladder, so the fixed-reference
strategy and the sparse-graph strategies are scored on **the same measurements**. Note
the flag is `--cfg` (not `--cfgs`) in this mode, and the prefix is bare: every mode
prepends `data/` itself.

The controls and the synthetic end-to-end run:

```powershell
# P1  - four hand-picked planted warps, the M3 (S)0 cross-check     -> out\p1-estimator-control.txt
.\target\release\m10-deep-align.exe synthetic C:\dev\macro\test\coffee-bean

# P1b - the estimator corner-error floor as a 432-warp distribution -> data\coffee-bean-floor.csv
.\target\release\m10-deep-align.exe floor C:\dev\macro\test\coffee-bean coffee-bean `
    --cfgs m10,wide,wide64 --margins 10,96 --frames 0,40,80 --n 24

# P6  - resampler-free field arm + bilinear-resample arm            -> data\lock-lock.csv   (~380 s)
.\target\release\m10-deep-align.exe lock lock --resample-from C:\dev\macro\test\coffee-bean

# P7  - a known magnification increment planted on real frame pairs -> data\coffee-bean-increment.csv
.\target\release\m10-deep-align.exe increment C:\dev\macro\test\coffee-bean coffee-bean `
    --cfgs m10 --spans 1,2,4 --frames 10,20,30,40,50,60,70 `
    --mags 0.0001,-0.0001,0.0002,-0.0002,0.0004,-0.0004,0.0008,-0.0008,0.0016,-0.0016,0.004,-0.004

# P4  - a 105-frame synthetic stack with a planted path             -> data\p4-warp-{edges,truth}.csv
.\target\release\m10-deep-align.exe synth C:\dev\macro\test\coffee-bean p4-warp `
    --case p4-warp --n 105 --flavour warp --spans 1,2,4,8,16,32,48,64 --direct0 --cfg m10
```

Then the analyses, in the order the report presents them:

```powershell
python m10_selftest.py  > out\controls.txt          # P0/P2/P3/P5 - gates everything below
python m10_edges.py     > out\edge-quality.txt      # M6 cross-check + edge yield
python m10_shrink.py    > out\scale-rate-ladder.txt # the ladder
python m10_conserve.py  > out\conservation.txt      # the telescoping identity
python m10_measure.py   > out\headline.txt          # the headline held-out metric
python m10_ruling.py    > out\ruling.txt            # PREREGISTRATION section 6, applied mechanically
python m10_centre.py    > out\scale-centre.txt      # scale centre + registered falsifier 3
python m10_floor.py     > out\p1b-floor-summary.txt
python m10_lock.py      > out\p6-lock-summary.txt
python m10_increment.py > out\p7-increment-summary.txt
python m10_mechanism.py > out\p6-p7-mechanism.txt   # P6 vs P7 at matched differential displacement
python m10_p4.py        > out\p4-warp.txt           # end-to-end scoring against planted truth
python m10_p4_conserve.py > out\p4-conservation.txt # the same telescoping identity, on synthetic frames
```

`m10_selftest.py` must print `ALL CONTROLS PASS`. Per PREREGISTRATION §5 no result in
this experiment is believed if it does not.

Every Rust mode is bit-reproducible from these arguments; the `increment` run above was
re-run after the final lint pass and hashed **identical** to the committed CSV.

## Two things to know before reading any number

**Plane pixels, not sensor pixels.** Everything here is in the CFA-quad plane, which is
half resolution in each axis. M3's headline "25 px chaining error at 60 frames" is a
*sensor* figure and is **12.5 plane px**. M6's halo figures are already plane px. One
plane px is two sensor px. The corner radius is rho = 2112.93 plane px.

**A bundle adjustment over a tree is chaining.** If the training graph has cycle rank 0
then S3 and S1 are the same algorithm and any comparison between them is vacuous.
`graph_stats()` reports `cycle_rank`, `components` and `is_tree` for every training
subset, the tables print `TREE` when it happens, and those rows are excluded from the
ruling. This is the registered non-degeneracy guard.

## Read-only data

`C:\dev\macro` and `D:\macro-dark-frames` are irreplaceable capture data and are opened
read-only. The harness decodes; it never writes into those trees.
