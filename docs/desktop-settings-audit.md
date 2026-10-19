# Desktop stacking settings audit

Source audit: `crates/strehl-cli/src/lib.rs`, `Command::Stack`, its backend
compatibility checks, and `merge_cmd.rs` dispatch. The desktop invokes the
shipping **pyramid** backend. The CLI also exposes an alternative estimator and
research/control arms; those are not silently treated as pyramid settings.

The desktop therefore does **not** expose every CLI flag. It exposes the
photographic pyramid controls below, preserves their values in each saved run,
and leaves deliberately excluded options documented here. Defaults are the
engine defaults, full-resolution sRGB, supported automatic optical correction,
and the machine's available CPU capacity. A larger numerical setting does not
mean better image quality.

## Available in the desktop

| CLI control | Desktop location and behavior |
| --- | --- |
| Source `dir` | Project/stack source bracket |
| `--out` | Fresh private render folder, staged and validated TIFF publication |
| `--limit` | Capture range & evidence → First captures; filename-order prefix; All restores the complete bracket |
| `--pyramid-bands` | Merge → Scale controls → Scales; 1–12 |
| `--pyramid-gate` | Merge → Noise gate; default remains engine-controlled |
| `--pyramid-exponent` | Merge → Scale controls → Coarse power |
| `--pyramid-sharpen` | Merge → Scale controls → Fine-scale ramp |
| `--exposure` | Develop → Exposure; −12 to +12 EV |
| `--auto-exposure` | Develop → Automatic exposure; mutually exclusive with manual exposure |
| `--srgb` | Always used for photographic output; as-shot white balance and the engine's sRGB development path |
| `--demosaic` / `--binned` | Geometry → Half-size TIFF; full-resolution demosaic is the engine's default with `--srgb` |
| `--fix-ca off` / normal automatic gear guard | Develop → Correct colour fringing; unsupported gear is not forced through a profile |
| `--resampler` | Geometry → Sampling; all six CLI interpolators available |
| `--cover scale` / `--cover crop` | Geometry → Shared coverage crop; unchecked uses the engine's scale policy |
| `--confidence-map` | Capture range & evidence → Save confidence map; extra decode/warp pass; writes `confidence.tiff` beside the photograph |
| Execution pool limits | Execution → CPU thread limit; both `RAYON_NUM_THREADS` and `STREHL_PYRAMID_WORKERS` set together |

The optional confidence map is shown as **Observation balance** beside the
finished photograph and in its regional hover probe. Its 16-bit grayscale
values are **0–1000**, computed from the balance of observations strictly below
the output versus at or above it; **65535** marks no observation. Ties belong
to the latter side, so an all-identical set also reads zero. This is neither
an image-quality score nor a defect detector. The analysis-plane map is linked
only to a certified owned output, with exact cursor readings and a zoom-refined
overlay. New stacks enable the extra engine pass by default; an explicitly saved off setting remains respected. The preview always exposes its confidence-map status and offers a direct balance overlay when the map exists.

Regional source charts report sampled gate admission at each detail size,
separately from fallback averaging. They are not normalized source weights.
New stacks record up to 128 by 96 observations per band; older runs retain
their original grids. The density control changes display thinning, and zoom
reveals retained observations without inventing values between them. Linked
camera previews share the final image's normalized crop but are marked
approximate: their embedded JPEG crop does not certify a sensor warp.

## Deliberate exclusions

| CLI control | Why it remains CLI-only |
| --- | --- |
| `--merge estimator` | A different merge operator with a different diagnostic model, rather than a quality preset for the current process workspace |
| `--gate`, `--focus`, `--target-n-eff`, `--index-map`, `--n-eff-map` | Estimator-only; explicitly refused by the pyramid backend. In particular, estimator gate values cannot be transferred to the pyramid gate |
| `--photometric` | **Not implemented on pyramid** and explicitly refused there. The estimator's help describing it as default-on does not mean the desktop applies it |
| `--flat-roi`, `--detail-roi`, `--stats`, `--stats-placebo`, `--confidence-tail` | Estimator measurement/statistics paths, not controls for the shipped photographic pyramid run |
| `--pyramid-select hard-max` | A documented control arm that the CLI help explicitly says not to ship; desktop keeps soft weighting |
| `--pyramid-base weighted` | Retained comparison arm for reproducibility; desktop keeps the measured mean tone base |
| `--linear-srgb`, output without `--srgb` | Measurement encodings, not photographic viewing presets; the process photograph is sRGB |
| Forced named `--fix-ca PROFILE` | Bypasses the normal gear guard; desktop permits automatic matching or off, not arbitrary correction on incompatible gear |
| `--help`, `--version`, environment research switches | CLI introspection/research controls. Inherited `STREHL_*` overrides are stripped from desktop renders so hidden environment state cannot change a saved run |

The audit checked the complete `Stack` field list, not just flags mentioned in
its short help. No focus-operator, photometric, posterior-confidence, or
per-pixel source-ownership behavior is implied for pyramid by the UI.

## Review and continuity

The Review pane reads the run's emitted evidence: placed/refused counts,
covered field of view or exact crop rectangle, held-out alignment diagnostics,
and fraction of band coefficients averaged below the gate. Its diagrams link
back to capture, coverage, alignment, and blend inspection. Unknown counts stay
unknown; partial placement cannot turn into a success bar. An alignment error
is not a per-pixel sharpness score, and a band average is not an RGB ownership
percentage. Suggestions request inspection or a saved comparison at the same
image position; they do not diagnose a need to retake from an unvalidated score.

New settings have serde defaults so v18 saved runs reopen with their original
behavior. Auto exposure and explicit exposure cannot both be submitted. A
zero capture limit is rejected before output creation. Requested confidence
evidence is validated and published in the owned run folder before the final
photograph is published.

## Verification

Targeted regressions cover legacy JSON, full settings round trips, actual
command arguments (including paths containing spaces), automatic/manual
exposure conflicts, invalid capture limits, non-overwriting artifact
publication, unknown/partial placement, and off-center coverage geometry.
Run with `cargo test -p strehl-ui` and confirm a fresh `Compiling strehl-ui`
line. Read the delivery's command logs and paired output hashes for executed
validation; this source audit alone is not an image-quality or performance
claim.
