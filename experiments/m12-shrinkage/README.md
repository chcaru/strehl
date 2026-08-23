# M12 — short-baseline shrinkage: is it calibratable?

Research milestone. Report: [`docs/research/M12-shrinkage-measured.md`](../../docs/research/M12-shrinkage-measured.md).
Binding pre-registration: [`PREREGISTRATION.md`](PREREGISTRATION.md), committed as `8326564`
**before** any result was computed.

**Answer: no.** The shrinkage is a per-scene property, reproducible within a scene to 0.15 σ and
transferring to **0 of 18** cross-scene pairs. It does not replicate at all on the two new stacks
(`1/S_W(1)` = 1.048 / 1.027 against `coffee-bean`'s 3.260) at matched displacement and matched
drift. Even an oracle in-sample correction leaves `coffee-bean`'s chain at 13.92 px, twice the
6.76 px M10's global solve already reaches without one.

## Provenance

The Rust crate is a **verbatim copy** of M10's at `experiments/m10-deep-align/`, renamed
`m12-shrinkage`. `experiments/m10-deep-align/` was **not modified**. Two deliberate deltas:

- `main.rs` carries a header doc comment recording the copy;
- `run_synth` gained `--g-total` and `--curve`, so C3's synthetic null can be planted at the same
  total magnification drift as the real stack it is controlling for.

`m12_lib.py` is a copy of `m10_lib.py` (docstring retitled only).

`data/m10-*.csv` are byte-identical copies of M10's committed edge sets, so this experiment is
self-contained and M10's published numbers are checkable against M12's re-implementation without
reaching into another milestone's directory. Verify with:

```powershell
Get-FileHash data\m10-coffee-bean-edges.csv -Algorithm MD5   # 5FAFAF327256EB974F974AEF2989E1B0
Get-FileHash data\m10-shallow-119-edges.csv -Algorithm MD5   # 6E8E8DF5B993D7061349B5A16F919637
Get-FileHash data\m10-shallow-109-edges.csv -Algorithm MD5   # 1C60294E0F9BB7AE501007267463899A
```

## The statistic

M10's ladder rescaled partial coverage by `(n−1)/coverage`, which mixes extrapolation error into a
comparison meant to isolate the baseline. M12 fixes the endpoints instead. For window `0..W` and
span `s` dividing `W`:

- `T_W(s) = Σ_{k=0,s,…,W−s} log|a_{k,k+s}|` — telescoped total, must be independent of `s`;
- `A_W = log|a_{0,W}|` — the single direct anchor edge;
- **`1/S_W(1) = A_W / T_W(1)`** — the headline shrinkage ratio.

`s = W` rows are excluded by construction (there `T_W(W) ≡ A_W`, the same measurement twice —
SYNTHESIS §5 item 20), and `divisor_spans()` refuses spans that do not tile the window exactly.
An anchor-free variant `T_W(1)/T_W(s*)` reproduces the result to ≤1.2% on all five stacks.

## Layout

| file | what |
|---|---|
| `PREREGISTRATION.md` | the contract: statistic, threshold, refutation criteria, controls C1–C9 |
| `PREREGISTRATION-focus.md` | the M12-F contract: focus-index hypotheses, threshold, controls F1–F5 |
| `src/` | copied Rust harness (`edges`, `synthetic`, `synth`, `increment`, `floor`, `lock`) plus M12's own `focus` and `pairfit` modes |
| `m12_lib.py` | copy of M10's transform algebra and CSV reader |
| `m12_ladder.py` | the windowed conservation ladder |
| `m12_conserve.py` | C2 reproduction gate + all-stack ladders |
| `m12_premise.py` | fact 49's identical-sweep premise, tested by magnification |
| `m12_meta.py` | capture metadata; the 3-tick `FocusPosition2` finding |
| `m12_ruling.py` | sections A–I, the registered ruling applied mechanically |
| `m12_controls.py` | C3 null, C4 positive, `wide64` robustness arm |
| `m12_diagnose.py` | decorrelation profile and candidate predictors |
| `m12_repair.py` | the C4 repair and the anchor-free shrinkage |
| `m12_verify.py` | recomputes every derived ratio quoted in the report |
| `m12_focus.py` | M12-F: focus-index regression, controls F1–F5, corroborations U0/U1 |
| `data/` | edge CSVs, increment CSVs, EXIF dumps, `focus-peaks.csv` (the distilled M12-F measurement) |
| `out/` | committed console output for every script above |

## Running it

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cargo build --release

$SPANS = "1,2,3,4,5,6,8,10,12,16,20,24,32,40,48"
.\target\release\m12-shrinkage.exe edges D:\personal\macro\112MSDCF stack-112 `
    --cfg m10,wide64 --spans $SPANS --direct0
.\target\release\m12-shrinkage.exe edges D:\personal\macro\113MSDCF stack-113 `
    --cfg m10,wide64 --spans $SPANS --direct0

python m12_conserve.py > out\conservation.txt
python m12_premise.py  > out\premise.txt
python m12_ruling.py   > out\ruling.txt
python m12_controls.py > out\controls.txt
python m12_diagnose.py > out\diagnose.txt
python m12_repair.py   > out\repair.txt
python m12_verify.py   > out\verify.txt
```

Edge measurement is ~24 s (112) and ~18 s (113) on 32 cores. Every Rust mode prepends `data/` to
the output prefix itself.

### M12-F — measuring the focus band from the pixels

Per-frame focus position is **not** in EXIF (`FocusPosition2` has 3 distinct values across a
79-frame sweep), so it is measured instead. `focus` mode reports, per scene tile, the
parabola-interpolated frame index at which a mean-normalised sharpness measure peaks.

```powershell
$F = ".\target\release\m12-shrinkage.exe"

# primary arms  (tile 96, stride 96, 160 px frame margin are the defaults)
& $F focus D:\personal\macro\112MSDCF focus-112 --case f112
& $F focus D:\personal\macro\113MSDCF focus-113 --case f113

# F1 null: planted magnification, no focus change  -> expect ~0% tiles accepted
& $F focus D:\personal\macro\112MSDCF focus-null --case fnull --synth-scale 3.7448e-2 --synth-n 79

# F2 known-answer arms, built by decimating 112 against itself
& $F focus D:\personal\macro\112MSDCF focus-112-even --case f112ev --step 2 --phase 0
& $F focus D:\personal\macro\112MSDCF focus-112-odd  --case f112od --step 2 --phase 1

# F5 frozen tile grid (no (0,j) warp at all)
& $F focus D:\personal\macro\112MSDCF focus-112-frozen --case f112fz --frozen
& $F focus D:\personal\macro\113MSDCF focus-113-frozen --case f113fz --frozen

# F3 cross-stack frame-0 registration, for the independent offset check
& $F pairfit D:\personal\macro\112MSDCF D:\personal\macro\113MSDCF

python m12_focus.py > out\focus.txt
```

Focus extraction is ~4 s per 79-frame arm on top of a ~1.7 s decode. No resampler is involved:
mapped tile centres are rounded to integer pixels, which keeps M10 fact 45's resampler question out
of the measurement. The 160 px frame margin leaves 33 × 21 = 693 tiles; every arm uses the same
grid so tiles are comparable across arms by index.

The raw `data/focus-*-focus.csv` profiles are ~18 MB and are **git-ignored**. What is committed is
`data/focus-peaks.csv` (266 KB) — the distilled per-tile peak and acceptance reason for all nine
arms. `m12_focus.py` writes it when the raw profiles are present and falls back to it when they are
not, so `python m12_focus.py` reproduces every number in §4.1a of the report on a fresh clone with
no access to the ARWs. Verified: the cache-only run is line-for-line identical to the raw run.

`D:\personal\macro` is read-only and was not written to; `out/readonly-audit-{before,after}.txt`
record identical counts and byte totals under the identical enumeration method.

## Gotchas that cost time here

- PowerShell `Tee-Object … | Select-Object -First N` **truncates the tee'd file**. Use plain `>`.
- A read-only audit must use the *same* enumeration both times: `-Force` includes `.git` and
  changes the count by 1081 files on `C:\dev\macro` with nothing having changed.
- `cargo` is not on `PATH` in a fresh shell.
