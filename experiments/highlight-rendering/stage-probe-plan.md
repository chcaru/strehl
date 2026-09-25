# Frozen garnet writer-stage trace

SOURCE REVIEW / prospective diagnostic, not executed by its author. No rendering
treatment or quality claim. The frozen native output region is
`[4668,1858,384,384]` in the full `6524x4348` garnet Current output. Its matching
full-active-sensor origin is `[4922,2028]` because the CFA-plane crop is
`[127,85,3262,2174]`. The small original inspection tile starts at output-native
`[4720,1930]`; it is inside this region, not a different gauge.

`stage-probe.rs` must be included as `image_out::stage_probe`. The observer takes
the actual full `Mosaic` and resolved `Develop` inside `write_demosaiced`.
Normalization, WB, exposure, clipping of negative merged values, mosaic assembly,
crop and auto-tone are owned by the existing writer. None is reconstructed from
rounded logs. Each inspected row uses actual full-context MHC; no isolated-crop
demosaic or remeasured regional tone is allowed.

## Integration after the active source freeze

Root applies these three small changes together, then makes a fresh bound build:

1. Include `stage-probe.rs` in a new `pub(crate) mod stage_probe` beside the
   highlight module in `image_out.rs`, under the same test/native-direct-planes/
   native-correction-variance/native-gpu-gather guard.
2. Under that same guard call `stage_probe::observe_mosaic(&m, dev)?;` in
   `write_demosaiced`, after `resolve_tone` and existing resolved metadata capture,
   before the output loop.
3. Change only visibility of the existing
   `full_stack_source_prior::write_current` helper from `fn` to `pub(crate) fn`.
   Its body remains unchanged. This avoids duplicating the preparation path.

No bound source has been edited by the probe author. The ignored test is:

```text
image_out::stage_probe::garnet_cached_stage_trace
```

Run the fresh CLI test executable with that exact filter, `--exact --ignored
--nocapture --test-threads=1`. `STREHL_HIGHLIGHT_STAGE_CONFIG` points to a JSON
object with `schema:1`, absolute `cache`, `cache_sha256`, absolute
`expected_current_tiff`, `expected_current_file_sha256`, and fresh absolute
`out_dir` beneath `experiments`. Bind all sources/executables/config/inputs with
the usual root runner. Use the full baseline garnet cache: phase `full`, arm
`baseline`, 183 original sources, reference 91. Candidate/cost caches are refused.
Default MHC and sensor knee are required; unrelated pinned tone is refused.

## What the diagnostic proves, and what could make it fail

First write Current through the actual existing cache writer with stage observer
off. Require complete RGB16 pixels and ICC to equal the retained user master.
Then enable the observer, write Current again and require whole-file SHA256
identity. Actual development metadata must also match. A perturbing observer,
wrong normalization, crop, tone, cache or input image fails these checks.

The observer records row-major per-pixel f32 little-endian arrays for the exact
normalized mosaic, MHC camera RGB, actual post-`clip_highlights` camera RGB,
actual post-`Render::develop` linear sRGB, post-tone linear sRGB, and post-gamut
linear sRGB. Post-tone uses the actual private `Tone::gain`; post-gamut uses
the actual private `gamut_map`. It records the final output by calling actual
`develop_pixel` with Current and requires every ROI RGB16 value to equal the
written master. A saved native RGB16 ROI with original ICC is reread and checked.

`pin-channels.u8` contains the three ceiling comparisons as bits R=1/G=2/B=4.
`pin-mask.tiff` is 65535 where any comparison is true, zero otherwise.
`clip-changed-mask.tiff` separately states where actual `clip_highlights` changes
the RGB bits. A pinned pixel need not change, so these are not interchangeable.
All float files declare their spaces/shapes in the receipt; no stretch or
normalization is applied to the diagnostic mask or final ROI. The existing cache
already retains the four pre-writer collapsed CFA planes.

This records no new RAW reads and repeats no merge. It checks all in-memory
planes and cache binary/metadata/retained-master hashes after the writes. It
exports no new quality score and has no required nonzero pin count: an empty
pin mask is a useful refusal of the specific clipping-trigger explanation.

Compare the fixed rectangle boundaries across successive stages. If a boundary
is already in cached planes/MHC RGB, the writer did not originate that upstream
structure. If an abrupt change first appears at post-clip and coincides with
the predicate transition, that motivates a separately authorized causal bypass
test; coincidence alone does not prove it. If the pin mask is absent/inert,
stop pursuing this branch. A post-merge predicate is not an original RAW clipping
census. This observer diagnoses geometry; it does not claim to repair glare,
spatial ghosting, or the photograph.
