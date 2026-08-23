# M23 — metacalibrated short alignment edges

Tests review item **R4**: import weak lensing's response calibration
("metacalibration") to fix the short-baseline magnification shrinkage that
bounds deep-stack alignment at 6.758 plane px.

**Result: negative.** The per-edge response `R` is not a well-defined per-edge
quantity, and the deficit it measures is the *plant's own bilinear resampler*,
not the defocus asymmetry it was supposed to correct. See
`docs/research/M23-metacalibrated-edges-measured.md`.

## Layout

| path | what |
|---|---|
| `PREREGISTRATION.md` | the contract, committed as `f1be27f` **before** any number in `out/` existed |
| `src/*.rs` | verbatim copy of `experiments/m12-shrinkage/src/*.rs` (itself a verbatim copy of M10's) **plus** the `metacal` mode in `main.rs` |
| `m23_lib.py` | verbatim copy of M10's `m10_lib.py` — transform algebra, solvers, metrics |
| `m23_mc.py` | new: reads the metacal CSV, forms `R`, applies the correction and its nulls |
| `m23_response.py` | the response tables, δ-dependence criterion, positive control, gate (b), N3, per-edge noise |
| `m23_controls.py` | the control arms — self-pair, pedestal, resampler-free field |
| `m23_conserve.py` | gate (a) conservation, nulls N1/N2, every-window sweep, local telescoping |
| `m23_heldout.py` | gate (c), reusing M10's `train_sets` / `strategies` / `score` **unmodified** |
| `m23_cost.py` | wall-clock cost, alternated sweep, per-setting minimum (rule 16) |
| `run-m23.ps1` | re-runs everything end to end |
| `data/` | committed CSVs, including the two edge CSVs copied from M10/M12 |
| `out/` | committed text output of every script |

## The added Rust mode

```
m23-metacal metacal <dir-of-ARW> <out-prefix> --case NAME [--cfgs m10]
    [--spans 1,2] [--deltas 1e-4,...] [--self] [--pedestal P] [--field REPS]
    [--noise E] [--stride 1] [--limit N]
```

Per pair `(i, j)` and per `δ`: fit the base, then plant `+δ` and `−δ` on the
moving frame with **one** bilinear pass each (the pedestal is composed into that
same pass, never applied on top of another warp), refit, form the increment
`I_± = F_± ∘ F_0^{-1}` in the `(a, b)` algebra, and emit

```
R = (log|a(I_+)| − log|a(I_−)|) / (log(1+δ) − log(1−δ))
```

`log|a_0|` cancels algebraically in that difference, so the two-sided `R` does
not contain the base fit.

- `--self` measures frame `k` against **itself**: real content, zero defocus
  difference, identical resampler and plant.
- `--pedestal P` composes a large pre-existing scale `P` into the same single
  warp, so the pair carries a real differential displacement (`P = 4e-3` is
  ≈ 4.8 plane px) and no tile sits in the sub-pixel locking zone.
- `--field REPS` renders the reference and both plants as point samples of one
  continuous band-limited synthetic field at the composed transforms, so **no
  interpolator appears anywhere in the path**.

## Data provenance

`data/m10-coffee-bean-edges.csv` and `data/m12-stack-112-edges.csv` are copies,
verified by MD5 against the originals:

| file | MD5 |
|---|---|
| `m10-coffee-bean-edges.csv` | `5FAFAF327256EB974F974AEF2989E1B0` |
| `m12-stack-112-edges.csv` | `7B22151496CA3CEEB53FA5BBECC4D05B` |

`m23_conserve.py` re-derives `log|a|` for every span-1 edge from this
milestone's own runs and compares against those CSVs: max deviation
**5.3e-10** on both stacks.

## Gotchas that cost time

- `cargo` is not on `PATH`: `$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"`.
- **`Tee-Object -FilePath X | Select-Object -First N` truncates the tee'd file.**
  Use a plain `>` redirect. `-Last N` is safe. (Inherited M12 gotcha; it bit
  this milestone too.)
- `Get-ChildItem -Force` is mandatory for the read-only audit or the corpus
  under-reports by 1081 files.
- PowerShell has no heredoc. `@'...'@ | Out-File -Encoding utf8`.
- Decoding `coffee-bean` takes ~2.3 s for 105 frames to 3516×2344 green planes;
  each arm re-decodes.

## Reuse is a consistency check, not evidence

`m23_heldout.py` imports `train_sets`, `strategies` and `score` directly from
`experiments/m10-deep-align/m10_measure.py`, and the solvers from `m10_lib.py`,
unmodified. It reproduces M10's 6.758 px baseline **exactly**. That proves the
plumbing, not the physics (discipline 34).
