# Independent build and generated-screen review

2026-10-27. VERIFIED receipt/source/artifact audit; reported image numbers are MEASURED by the frozen test, not recomputed by this reviewer. No RAW, operator, image fitting or Cargo job was run for this review. The screen is mechanically valid and fails its quality guards. Root's previously declared diagnostic full-photograph policy still applies; this is not photographic admission.

## Identity and completeness

The actual build command was `cargo test --locked --offline --release -p strehl-cli --lib --no-run --features native-direct-planes,native-correction-variance,native-gpu-gather --jobs 4 --message-format=json-render-diagnostics`. Build1 records fresh `Compiling strehl-cli`, exit0 and238.422s. Frozen executable SHA256 is `339efc0ac1652501b2a834ab9305cc7c6ede792316c42d20f7dfdbc32d32714d` (42,051,072bytes).

The actual screen command was:

```powershell
& 'C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-27\native-restoration-build-1\cli-tests.exe' merge_cmd::native_restoration::generated_controls --ignored --exact --nocapture --test-threads=1
```

Invocation records four Rayon/pyramid workers, fixed Malvar and the bound config. Screen1 ran exactly one test, exit0, .859s wrapper wall time,7,815,168bytes peak committed job memory, no cleanup error or residual active process. The screen's120s/4GiB bounds were not approached. These figures are job observations, not a competitive full-workflow benchmark.

Independently streaming-rehashed all1,407 build-bound sources and101 unique executable/report/dependency/generated-artifact bindings; none changed. The eight standalone case reports equal their copies in `screen.json`; `commission.json` equals its embedded copy. All43 complete128x128 RGB float masters/PPMs (five arms per case plus three destroyers) and eight original generated u16 CFA files have the recorded byte counts/hashes. Baseline and off payload hashes agree in every case. No camera RAW is read by the producing path.

## Outcomes and actual risk

`all_cases_completed=true`, `hard_valid=true`, `quality_pass=false`, `admission=false`, `photographic_admission=false`. Unequal-phase DC, signed bypass, nonfinite rejection, input preservation, exact MHC bypass and independent local-range checks pass. The false-green, erased-coarse and wrong-range destroyers are detected. The unbounded actual-CFA step foil produces the exact500DN excursion on a4000DN step (12.5%), changes actual MHC output and fails the live error guard. The bounded sharp step is bit-identical to baseline. It also retains baseline MHC errors, so this is an added-artifact null, not a clean-edge claim.

Seven of eight cases fail quality protection. The risks are more specific than a generic sharpening/noise tradeoff:

| Fixed case | Baseline → bounded observation | Consequence |
| --- | --- | --- |
| Neutral/colored noisy flats | Chroma RMSE17.95→20.76 /18.52→21.48DN | Range preservation does not prevent amplification of colored noise. This synthetic source-noise draw does not identify actual merged covariance. |
| Blurred close lines | RGB203.04→192.92 but chroma24.18→30.50DN | Lower aggregate RGB error can coexist with worse color around genuine structures. |
| Glints | Green41.44→61.67 and RGB56.18→74.25DN | Highlights and their neighborhoods are a concrete high-risk photographic witness. |
| Independent color | Known-template amplitudes.720/.772→.809/.876, but green137.16→157.47DN | More recovered component contrast does not establish clean color; weak green is not independently amplitude-qualified. |
| Fine/coarse superposition | Fine.840→1.123; coarse1.002→1.013; RGB52.72→64.21DN | Fine contrast overshoots truth despite every CFA value remaining inside its local range. The component guard fails rather than treating higher contrast as success. |
| Asymmetric mismatch | RGB173.23→168.16 but chroma65.67→73.74DN | A modest aggregate gain again conceals color harm. |

These fixed failures stay attached to the candidate. They do not require cancelling the separately authorized finite whole-weevil/flat observation, nor support promoting the recipe. Actual full-photo review should specifically check dark-field color texture, bright-scale/glint contours, independent blue/red scale boundaries and overemphasized fine structure. No statement here establishes recovered resolution, absence of occlusion halos, or improvement on a photograph.
