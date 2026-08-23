# M9 — focus-measure / merge-regulariser coupling

Harness for SYNTHESIS §10 open question 9: *is the coupling between the focus
measure and the merge regulariser severe enough that it must appear on the
public plugin interface?* — i.e. does plugin-review item **B3**'s proposed
`support_px()` method earn its place?

Report: [`docs/research/M9-support-coupling-measured.md`](../../docs/research/M9-support-coupling-measured.md).
Pre-registration: [`PREREGISTRATION.md`](PREREGISTRATION.md) — committed in
`f29e4db`, **before** any cross-measure number existed. The ordering is
checkable from `git log`.

**Ruling: B3 dies.** Knowing `support_px()` is worth **+0.0000** (109MSDCF) and
**+0.0009** (119MSDCF) ratio units of worst-case regret, against a
pre-registered severity floor of 0.02. The real driver of the noise the merge
has to regularise away is the operator's **centre-tap sensitivity fraction φ**
(Spearman ρ = +0.92 / +0.89), not its spatial support (ρ = −0.21 / −0.24).

## Everything is already committed

`data/` holds every raw measurement as CSV/text. The analysis reproduces with
just `m9_analyse.py`; you only need the RAW corpus to re-measure.

## Prerequisites

- `cargo` is not on PATH in a fresh shell. **Every** command below assumes:
  ```powershell
  $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
  ```
- Python 3 (stdlib only — `m9_analyse.py` and `m9_acf.py` import no packages).
- Read-only RAW corpora at `C:\dev\macro\test\109MSDCF` and
  `C:\dev\macro\test\119MSDCF`. **Never written to by anything here.**
- Run everything from `experiments/m9-support/`.

```powershell
cd experiments\m9-support
cargo build --release
```

Runtime for the whole chain is ≈ 50 min on 32 logical cores, almost all of it
in the three sweeps.

## The commands, in order

`run-m9.ps1` runs all of this end to end. The stages are listed separately so
any one can be re-run alone.

### 1. Self-test — the statistic before the data

```powershell
cargo run --release -- selftest
```

102 assertions in seven groups. Group D is the one that matters: it exercises
the knee statistic `W90` against **planted** curves (known-good and known-bad)
before it is ever pointed at a sensor, per project rule "a gate written from a
model of the system tests the model".

### 2. Reproduce M2's headline

```powershell
cargo run --release -- xcheck C:\dev\macro\test\109MSDCF `
    --roi 2272,1344,256,256 > data\xcheck-109MSDCF.txt
```

Also cross-checks the tile path against the shipped CLI on the full plane and
proves margin-independence. Expect `1.2527x` at width 1 (M2 published 1.253x).

### 3. Choose ROIs by structure, not by hand

```powershell
# 109MSDCF was run at the default margin (105); its ROIs were then verified to
# fit the sweep's larger margin. 119MSDCF had to be re-run at 169 -- see below.
cargo run --release -- rois C:\dev\macro\test\109MSDCF --top 6 `
    --rank 2272,1344,256,256 > data\rois-109MSDCF.txt
cargo run --release -- rois C:\dev\macro\test\119MSDCF --margin 169 --top 6 > data\rois-119MSDCF.txt
```

Ranks every 256×256 block on a 16 px stride by scene structure (flat) and by
full-resolution mean gradient (detail), with non-overlap suppression so that
eight shifts of one patch are not reported as eight ROIs. `--rank X,Y,W,H`
re-ranks a named ROI; that is how M2's `2272,1344,256,256` is placed at "51 of
22538 grid blocks are flatter".

> **`--margin` must be ≥ the sweep's own margin.** Pick ROIs at a smaller margin
> and the sweep may reject them for not fitting. This bit once, on 119MSDCF,
> whose flattest blocks sit near the frame edge. 109MSDCF's default-margin
> choices happen to fit and were kept, so the committed file reproduces from the
> command above exactly.

### 4. The sweeps — 26 measures × 5 ROIs × 19 widths

The four flat ROIs and one detail ROI come from step 3. On 109MSDCF the
top-ranked flat block (`2361,1417`) is **replaced by M2's `2272,1344`**, which
ranks 51st of 22,538 and overlaps the same flat region, so that M2's exact
measurement appears as a row of the sweep. The other three flat ROIs and the
detail ROI are the top-ranked non-overlapping blocks as reported.

```powershell
# coupled: select and evaluate on the same field (the real configuration)
cargo run --release -- sweep C:\dev\macro\test\109MSDCF `
    --roi 2272,1344,256,256 --roi 2505,441,256,256 --roi 2665,1513,256,256 `
    --roi 329,1353,256,256  --roi 2089,1065,256,256 `
    --roi-kind flat --roi-kind flat --roi-kind flat --roi-kind flat --roi-kind detail `
    --out data\sweep-109MSDCF-coupled.csv

# placebo / whole-sweep null: elect on G1, evaluate on G2. Independent read
# noise, so no noise-election defect can exist to regularise away.
cargo run --release -- sweep C:\dev\macro\test\109MSDCF `
    --roi 2272,1344,256,256 --roi 2505,441,256,256 --roi 2665,1513,256,256 `
    --roi 329,1353,256,256  --roi 2089,1065,256,256 `
    --roi-kind flat --roi-kind flat --roi-kind flat --roi-kind flat --roi-kind detail `
    --placebo --out data\sweep-109MSDCF-placebo.csv

# replication on a second stack (33 frames, ISO 50)
cargo run --release -- sweep C:\dev\macro\test\119MSDCF `
    --roi 3065,425,256,256  --roi 2713,1673,256,256 --roi 3065,1577,256,256 `
    --roi 649,1433,256,256  --roi 2025,1161,256,256 `
    --roi-kind flat --roi-kind flat --roi-kind flat --roi-kind flat --roi-kind detail `
    --out data\sweep-119MSDCF-coupled.csv
```

Other flags: `--widths 1,3,5,…` overrides the 19-entry default grid (even
widths are rejected — a centred box is `2r+1`); `--measures ring-1-3,ring-2-6`
restricts the design but still sizes the tile from the **whole** design's
maximum support, so a filtered run is byte-identical to the full run.

### 5. Centre-tap sensitivity φ — measured on real frames

```powershell
cargo run --release -- sensitivity C:\dev\macro\test\109MSDCF --out data\sensitivity-109MSDCF.csv
cargo run --release -- sensitivity C:\dev\macro\test\119MSDCF --out data\sensitivity-119MSDCF.csv
```

Sparse-lattice finite difference at spacing `4·reach + 2` = 166 px, wider than
twice the largest support, so the whole kernel comes back in one pass without
cross-contamination. Run on real sensor data at the real noise level — project
rule: never null on synthetic noise. `--deltas` sweeps the probe size (default
`1,8,32`) to show φ is stable in it.

### 6. Focus-field autocorrelation (supplementary)

```powershell
cargo run --release -- acf C:\dev\macro\test\109MSDCF `
    --roi 2272,1344,256,256 --out data\acf-109MSDCF.csv
```

### 7. Analysis

```powershell
python m9_analyse.py data\sweep-109MSDCF-coupled.csv  > data\analysis-109MSDCF-coupled.txt
python m9_analyse.py data\sweep-109MSDCF-placebo.csv  > data\analysis-109MSDCF-placebo.txt
python m9_analyse.py data\sweep-119MSDCF-coupled.csv  > data\analysis-119MSDCF-coupled.txt
python m9_acf.py     data\acf-109MSDCF.csv            > data\analysis-acf-109MSDCF.txt
```

Controls print **before** treatments, by construction.

### 8. The regression test and its negative control

```powershell
cd ..\..
cargo test -p strehl-core focus::tests::centre
powershell -NoProfile -ExecutionPolicy Bypass -File experiments\m9-support\negative-control.ps1
```

`negative-control.ps1` plants two independent regressions in
`crates/strehl-core/src/focus.rs` (`INNER_RADIUS 1→2`, `OUTER_RADIUS 3→5`),
proves the test goes red for each, then restores from a byte copy and bumps
`LastWriteTime` — `Copy-Item` preserves the source mtime and cargo would
otherwise silently skip the rebuild. It never uses `git checkout --`. Captured
output: [`data/negative-control.txt`](data/negative-control.txt).

## Things that will bite you

| | |
| --- | --- |
| `cargo` missing | Prefix every shell with the `$env:PATH` line above. |
| `rois --margin` too small | Must be ≥ 169 or the chosen ROIs will not fit the sweep. |
| Shipped CLI needs `--out` | `strehl stack` requires `--out` even for a pure `--flat-roi` run. |
| Sweep argmin at the grid edge | Real, not a bug — the objective is monotone-then-flat and has no interior optimum. See the report, §"What I could not establish". |
| `--measures` filter | Uses the *whole design's* max support for the tile margin, so a filtered run is byte-identical to the full run. Verified. |
| Experiment crate is out of the workspace | It carries its own `[workspace]` key; `cargo test --workspace` at the repo root does not build it. Run its self-test explicitly. |

## Data manifest

| File | What it is |
| --- | --- |
| `data/xcheck-109MSDCF.txt` | M2 reproduction, shipped-CLI full-plane cross-check, margin-independence proof |
| `data/rois-{109,119}MSDCF.txt` | ROI selection with flatness/gradient rankings |
| `data/sweep-109MSDCF-coupled.csv` | 2,470 rows — 26 measures × 5 ROIs × 19 widths, primary stack |
| `data/sweep-109MSDCF-placebo.csv` | same shape, G1-select / G2-evaluate — the whole-sweep null |
| `data/sweep-119MSDCF-coupled.csv` | same shape, replication stack (33 frames) |
| `data/sensitivity-{109,119}MSDCF.csv` | φ, centre and total \|∂r\|, tap counts per measure |
| `data/acf-109MSDCF.csv` | focus-field autocorrelation, lags 0–63 |
| `data/analysis-*.txt` | captured analysis output — what the report cites |
| `data/pilot-shape.csv`, `data/pilot-placebo.csv` | the pilot that fixed the *form* of the statistic, disclosed in PREREGISTRATION §0 |
| `data/negative-control.txt` | proof the regression test fires when the code is regressed |

## Design

`src/measures.rs` defines 26 measures:

- **16 treatments** — a crossed 4 × 4 design, families `{ring, tenengrad, sml,
  dsml}` × support radii `{1, 3, 6, 12}`. The crossing is the whole point: a
  sweep over support alone cannot separate "the optimum tracks support" from
  "the optimum tracks whatever else changed with it".
- **5 null controls** `nullctl-d*` — all literally `ring(1,3)`; only the
  *declared* `support_px()` varies. Any statistic that moves here is reading the
  declaration, not the operator.
- **5 positive controls** `posctl-e*` — `ring(1,3)` plus extra smoothing, so
  support genuinely varies (3/7/13/23/41 px) with the family fixed. A statistic
  that cannot move here cannot be trusted to report absence.

`src/tile.rs` keeps every read inside the active area via `Frame::quad_rows`
(project rule 7 — never compute statistics over the full decoded buffer; the
A7C II decodes 7168×5120 but fills only 7032×4688) and carries a verbatim copy
of the shipped tie-break so the tile path is bit-comparable with the CLI.
