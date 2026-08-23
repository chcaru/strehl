# M11 — the focus-measure bake-off

Measures the **Pareto front between focus selectivity and argmax noise excess** across 47
focus operators on real RAW stacks, and rules on what `strehl`'s default focus measure
should be. Closes SYNTHESIS risk 2.

Read in this order:

1. [`PREREGISTRATION.md`](PREREGISTRATION.md) — the design, thresholds, full outcome grid
   and decision rule, committed **before** any measurement ran (`git log` proves it), plus
   §8 amendments A1–A5.
2. [`data/analysis.txt`](data/analysis.txt) — the resolved analysis, controls first.
3. [`../../docs/research/M11-focus-bakeoff-measured.md`](../../docs/research/M11-focus-bakeoff-measured.md)
   — the report.

Nothing here writes outside this directory. `crates/` is untouched: every operator lives in
[`src/measures.rs`](src/measures.rs), following M9's precedent.

## The two axes

| axis | symbol | what it is | where |
| --- | --- | --- | --- |
| cost | `N` | flat-ROI **spatial** sd of the argmax-stacked result / same for one frame | `noise` mode |
| cost, corrected | `Ncorr` | `N(select G2, eval G2) / N(select G1, eval G2)` — divides out frame preference | `noise --coupled-g2` / `--placebo` |
| benefit | `S` | fraction of pixels where argmax elects the **planted** in-focus frame | `planted` mode |
| benefit, corroborator | `kappa` | winner-map agreement across an independent noise realisation | `stability` mode |
| structure | `phi` | centre-tap sensitivity fraction, by finite difference | `phi` mode |

`N` and `Ncorr` are spatial-vs-spatial and `kappa` is index-vs-index. **Rule 10 is not
violated anywhere**: no spatial sd is ever compared to a temporal sigma.

## Reproducing

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd experiments\m11-focus-bakeoff
.\run-m11.ps1            # ~25 min; writes every CSV in data\
python m11_analyse.py --out data\analysis.txt
```

`run-m11.ps1` is the exact chain that produced the committed CSVs. It is read-only with
respect to `C:\dev\macro` and `D:\macro-dark-frames`.

Two gates must pass before any result is believed, and the script runs them first:

- `selftest` — 104 assertions on synthetic data, no RAW file touched.
- `xcheck` — must reproduce M2's `1.2527x` at width 1 and `1.0737x` at width 17.

## Modes

| mode | what it does |
| --- | --- |
| `selftest` | 7 groups, 104 assertions: operator algebra, `phi` analytics, plant recovery, tie behaviour |
| `rois` | picks ROIs **by measured structure**, so the flat/detail split is not eyeballed |
| `xcheck` | reproduces M2's headline argmax noise ratio through this harness's code path |
| `noise` | the `N` axis. `--placebo` and `--coupled-g2` give the matched pair behind `Ncorr` |
| `phi` | centre-tap sensitivity fraction by finite difference, several deltas |
| `planted` | the `S` axis. `--tilt`, `--alpha`, `--noise-scales`, `--null`, `--synthetic`, `--flat-base` |
| `stability` | `kappa`. `--planes` uses G1 vs G2 photosites as two genuinely independent realisations |
| `cost` | single-threaded ms/frame/Mpx |

## Data manifest

| file | what it holds |
| --- | --- |
| `audit-before.txt`, `audit-after.txt` | read-only-corpus file counts and byte totals, before and after |
| `selftest.txt` | the 104 assertions, all passing |
| `xcheck-109MSDCF.txt` | the M2 reproduction gate |
| `rois-109MSDCF.txt`, `rois-119MSDCF.txt` | the structure-selected ROIs, with their measured statistics |
| `noise-<stack>.csv` | `N` per operator x ROI x width |
| `noise-<stack>-placebo.csv` | select on G1, evaluate on G2 — the M2-style placebo |
| `noise-<stack>-coupledg2.csv` | select on G2, evaluate on G2 — the matched coupled arm |
| `phi-<stack>.csv` | measured `phi` per operator, at four probe deltas |
| `planted-109MSDCF-p1.csv` | the registered selectivity run (real base, planted ladder) |
| `planted-119MSDCF-p1.csv` | the same on the second stack (corroborator, see amendment A5) |
| `planted-109MSDCF-p0.csv` | P0 positive control — noiseless synthetic broadband texture |
| `planted-109MSDCF-p2null.csv` | P2 null control — `alpha = 0`, no focus planted |
| `planted-109MSDCF-flatbase.csv` | the A5 constant-base null — the rule-9 pairing of record |
| `planted-109MSDCF-alpha.csv` | depth-discrimination sweep, `alpha` = 0.15 … 1.4 px/frame |
| `planted-109MSDCF-noisescale.csv` | injected-noise sweep, x0 … x4 |
| `planted-109MSDCF-tilt{0,4,16,32}.csv` | depth-ramp sweep; tilt 16 and 32 turn the width axis over |
| `*-frames.csv` | per-frame realised statistics of each planted ladder |
| `stability-<stack>-inject.csv` | `kappa` under an injected independent noise realisation |
| `stability-<stack>-planes.csv` | `kappa` across the G1/G2 photosite planes |
| `cost-109MSDCF.csv` | single-threaded cost |
| `analysis.txt` | everything above, resolved against the registered rule |

## Rules this experiment is bound by

- **Rule 7** — statistics are computed inside explicit ROIs of the CFA-quad plane
  (`3516x2344`), never over `rawler`'s zero-padded `7168x5120` buffer. `src/tile.rs` is the
  only place the geometry is resolved.
- **Rule 8** — every claim in the report carries a label and a command.
- **Rule 9** — the sharpness axis is paired with a flat-ROI control. The registered pairing
  **failed**; amendment A5 diagnoses why and supplies the constant-base null that passes.
  Both are reported.
- **Rule 10** — see the axis table above.
- **Rule 11** — null (`ctl-random`, P2), positive (P0), placebo (`--placebo`), and an
  instrument floor (`ctl-const`).
- **Rule 12** — this experiment does not verify itself. The CSVs are committed so that it
  can be re-verified against them.
