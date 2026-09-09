# Next integer common-RGB consumer: source audit

2026-09-08. SOURCE-READ / DERIVED / ARGUED planning only. No sampler,
fixture, TIFF, image, metric, compiler, process-control or product execution.
No current dimensions outcome was read. This note neither releases another
experiment nor changes the program, defaults, numerical gates or SYNTHESIS.

The smallest useful next implementation remains the one already selected in
`experiments/sampler-boundary/next-consumer-audit.md`: supplied integer
translations and an explicit common input crop, after the dimensions consumer
passes its independently verified software contract. The present source read
makes that recommendation more precise; it does not discover an unasked
alignment problem or justify another general matcher campaign.

## Consumer and source seam

The consumer is the three-plane `BandMerge::add_frame_with_gain` call in
`crates/strehl-cli/src/bin/common-stack/mod.rs:308`. It consumes each frame's
RGB samples, selection proxy and injected variance on one named output grid.
Correct endpoint placement, a plausible final image or a low fitted residual
cannot substitute for those actual per-frame values. M103's revised summary
and section16 explicitly withdraw its endpoint-based acceptance interpretation.

The current common-TIFF loop authenticates an encoded buffer, decodes
`CommonTiffFrame.pixels: Vec<u16>`, obtains current-frame f32 planes using
`merge_planes`, forms `(R+2G+B)/4`, folds once and drops the frame buffers.
`BandMerge` takes contiguous current-frame slices and builds its pyramids from
them. Preserve this lifetime and existing reusable workspace. A direct indexed
conversion from decoded u16 to the output-sized current-frame planes is the
narrow seam. Do not convert the whole source into f32 first and then create a
second mapped copy; do not retain mapped frames across the stack. This is
current-frame preparation required by this consumer, not an aligned-stack cache.

Relevant existing APIs settle direction and refusal, but are not a drop-in
implementation for the proposed crop:

- `warpmap::gather_checked` maps destination/reference coordinates to source
  coordinates, with no inversion. It refuses unequal source and destination
  geometries, takes an f32 `PlaneRef`, and writes NaN/false outside support.
  `gather_frame` additionally refuses an unplaced frame. Reuse those meanings;
  do not substitute an unknown placement with identity.
- `align::gather_into` is documented for controls/examples and calls unchecked
  sampling. It is not the masked production interface. Routing a crop through
  it would neither establish support nor preserve the intended storage seam.
- The native sidecar is a general floating-point Similarity contract. Its
  filename/size stack identity is not a replacement for the common consumer's
  ordered whole-file/pixel/profile bindings. An integer-only common-RGB request
  need not acquire a real fitted sidecar or modify that format.

ARGUED implementation choice: a narrow checked integer source view in the
common-RGB preparation path, filling the already required current-frame
buffers. Keep samplers, native CFA geometry and the merge algorithm unchanged.
It should share no CFA half-grid conversion: these are full-resolution common
RGB pixel centers with one identical address used for all three channels.
The existing same-geometry masked API remains available for its present users.

## Smallest prospective geometry contract

Retain current bounded input count, input dimensions, exact profile, RGB16
units, noise declarations, merge settings and legacy versions. Add a separately
versioned request with one explicit output rectangle and one supplied signed
integer translation for each exact ordered input. Initially keep a shared
input shape; heterogeneous inputs, scale, rotation and arbitrary integer maps
would be separate scope.

Write the convention without implied recentering:

    output local pixel (x,y) has common coordinate q=(origin_x+x,origin_y+y)
    input k is read at (q.x+tx[k], q.y+ty[k])

The origin and each translation are actual serialized integers, with checked
signed arithmetic and declared finite bounds. The rectangle must lie wholly
inside every translated input domain; validate the complete required source
address range before folding that frame. Refuse absent/unknown maps, overflow
and unsupported source coverage. There is no wrapping, clamping, edge fill,
nearest rounding or partial-frame admission in this first mode. A full-cover
requirement avoids passing fabricated zeros or NaNs into the existing dense
pyramid consumer. Actual input shape/hash failures still retain the successfully
consumed prefix and refuse final admission.

The crop is applied before pyramid construction by gathering only that source
rectangle. It is not a claim of equivalence to merging full images and cropping
afterward: pyramid boundary extension and InputRange can make those operations
different. Keep the output origin, shape, map direction and per-frame support
rectangle in the bound plan and final output association so downstream users
know what each output pixel denotes. A crop chosen solely from supplied map
support is acceptable; a content-selected crop would add a selection question.

Strictly, a translation is a bijection on the integer lattice and restricts to
a bijection between the output rectangle and one source crop. It is not a
bijection onto the entire larger source frame. That distinction rules out
mistaking repeated boundary pixels for lossless sampling.

## Noise boundary: what this does and does not preserve

DERIVED, conditional on the existing simulation law: unique integer reindexing
preserves each source sample exactly, introduces no mixing between sites and
preserves the law of spatially independent input noise. Applying the same map
to RGB preserves the specified within-pixel covariance. Independence between
frames remains an input assumption; filenames and mapping do not create it.
Consequently the existing noiseless or independently generated per-channel
Rademacher law can retain its injected proxy variance and white operator gains
on the new output lattice. No local noise fit or gain recalibration is proposed.
The source `pyramid.rs` documents why its white `BandGain` is an operator model,
and why a per-frame `frame_beta` override must describe the actual warp.

An arbitrary map that repeats source indices does not have this property.
Fractional interpolation generally changes marginal variance through squared
weights and creates covariance between neighboring outputs that share source
samples. A marginal variance array alone does not specify that covariance;
passing the identity white band gains would not discharge the contract.
Clamped cubic also makes the effective operation content-dependent. General
fractional geometry therefore needs an independently specified propagation or
operator-transfer contract before admission. This is a reason to retain the
small integer step, not a claim that fractional resampling is impossible.

These arguments apply to the synthetic law, not arbitrary developed RGB.
M165's current verdict remains PROPHOTO_DISPROVED for its required retained
consumer semantics, with the real competitive package unmeasured. Exact ICC
bytes and lossless TIFF handling do not prove physical noise, scene geometry,
real calibration or agreement with a comparator. No new real capture or
physical-alignment bar follows from this software extension.

## Useful acceptance choices for a future finite brief

This is not a new registered case population. Before a separately authorized
implementation/run, fix a small independent literal fixture and the following
same-path failure operands; reuse admitted TIFF/profile/process interfaces.

| Choice | Needed observation; failure input |
|---|---|
| Actual consumer values | Hash the exact gathered planes and proxy supplied to each fold against independently indexed u16 truth. Include asymmetric row/column/channel data and distinct contributors. Wrong map sign, forgotten output origin, wrong row stride or one duplicated source index must fail before a final image could conceal it. |
| Support and crop | Known positive and negative translations with a nonzero output origin and a valid common rectangle. Changes only outside every sampled crop must leave gathered values and output unchanged. One shift that moves the rectangle outside the last frame must refuse; no border replacement is accepted. |
| Complete contribution | Literal contributor means and actual ordered fold identities must both match. Keep the current discipline of proving that the selected omission/duplication faults survive output rounding; matching InputRange alone is insufficient. |
| Noise use | Compare actual gathered proxy/variance/gain inputs with the declared law. Include mixed flat/textured content to exercise the intended aggregate gate behavior. Changing injected variance or duplicating source indices must not be described as a white-noise-preserving map. No spatial-SD-as-temporal-sigma claim. |
| Diagnostic neutrality | If new map/support diagnostics inspect merge data, exercise their actual off/on/placebo path and require whole-TIFF and pixel equality. An output pixel mutation must fail the same saved comparison. This does not require rerunning unrelated completed controls. |

Final TIFF identity is useful but insufficient by itself: the hull can hide a
wrong prepared contributor. Conversely changed whole-TIFF bytes caused solely
by a newly truthful origin/geometry description must be distinguished from
changed pixels when comparing a mapped request with a separately represented
identity oracle. Off/on/placebo within the same request still demands whole-file
identity. Freeze that comparison choice before execution.

Stop promotion if dimensions admission is incomplete, any per-frame address or
noise association fails, required support is missing, a destroyer is not
exercised, or output/observer checks disagree. Preserve the failed prefix. Do
not respond by tuning alignment, shrinking a content-selected crop, weakening
exact sample checks or adding a wider image campaign. A pass would establish
known-map common-RGB software consumption only. Supplied maps carry literal
truth; they do not show that any real estimator can produce those maps.

## Prior art and alternatives

The mandatory current query returned V-GATHER, BUILD-DEMOSAIC,
V-HEADTOHEAD2 and BUILD-GATE as headline matches. These are citations to prior
work, not reports re-executed or individually re-audited here. Their relevant
conclusions were already summarized in the preceding consumer audit: warped
noise is not generally white, chroma-power changes are not independently
physical error, and comparator agreement cannot establish registration truth.
The current source `frame_beta` contract directly corroborates the noise seam.
No global absence claim is made from a ranked query.

The earlier output-adapter proposal has already supplied the three-frame
consumer that it recommended. Repeating it would add little. The current
count/dimensions work must finish its held cases; this note does not infer its
success from a source draft or build. The prior audit already chose integer
translation/crop next. The present audit retains that sequence and rules out
unnecessary general-sampler/sidecar changes. Fractional affine ingestion,
estimated real placement, scorecard captures, alternate calibration, rotation
or arbitrary permutations each add a different missing contract; none is needed
to expose wrong output-to-source addressing in this next narrow consumer.

## Read/search record and finite scope

Original root bound: query output plus12 detailed reports/source files,
16MiB aggregate source reads,1MiB retained note,20CPU/40active-wall tool allowance.
Before running the mandatory search I inspected its7322-byte source: it reads
all top-level research Markdown except SYNTHESIS and all non-target crate Rust.
A metadata census found394 reports/16,395,141B and96 Rust files/4,302,901B,
total20,698,042B. I reported that this exceeded16MiB and did not execute it at
that cap. Root prospectively amended aggregate source reads to48MiB for this
specific query plus targeted reads. Root separately admitted `warpmap.rs` as
exactly the13th detailed file to settle the actual masked-consumer interface.
Other limits stayed fixed. No additional dependency expansion occurred.

Commands actually used (PowerShell, repository root; read-only unless the final
UTF-8 note publication). Searches produced bounded displayed output; selected
sections were read with `Get-Content` line slices. The source pins below were
read once with per-file3MiB caps; their aggregate whole-file read was2,923,118B.
No complete CPU or end-to-end wall measurement is claimed for this planning job;
its full authorized reservation remains the20CPU/40active-wall scope.

```text
rg --files docs/proposals docs/research experiments crates/strehl-core/src crates/strehl-raw/src
  | rg '(next-consumer|common-tiff|common-input|mapped|gather|resampl|SYNTHESIS|2026-09-sota-program|M165)'
  | Select-Object -First150
rg -n -i --max-count12 'integer|biject|permutation|mapped|gather|covariance|common.rgb|common.input'
  [M165,M95,M104,M118,M124,common-tiff-stack-integration,current-program,prior-audits,charter]
rg -n 'prior.art|before.*new|Before.*new' AGENTS.md
rg -n 'pub fn gather|struct Gather|fn gather' crates/strehl-core/src
rg -n [headings and named API symbols] [the detailed files below]
Get-ChildItem docs/research -Filter '*.md' -File [except SYNTHESIS] | Measure-Object Length -Sum
Get-ChildItem crates -Filter '*.rs' -File -Recurse [except target] | Measure-Object Length -Sum
C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe -I -S -B
  experiments/ORCH-drift-check/prior_art.py 'integer translation' 'known map' 'common RGB' 'gather' 'resampling noise'
```

The final mandatory query ran once, exit0; tool-reported command wait2.788775s.
It reported headline scores74/66/63/50 for the four reports above, plus
BUILD-SHARP,M107b-lateral-correction,ORCH-veiling,M95-resample,M86-alignment,
M95-cdiff. Those are retrieval ranks, not scientific evidence. No `--commission`
self-test was run. Two harmless inspection issues are retained here: a
PowerShell custom-object formatting attempt was refused by constrained language
mode; an initial common-stack source path omitted `bin` and was corrected after
filename discovery. Neither ran candidate code or changed a file.

Detailed files (selected sections, not a claim to have reread every line), with
whole-file SHA256 at this audit's source pin:

| File / section | Bytes | SHA256 |
|---|---:|---|
| docs/proposals/2026-09-sota-program.md, final consumer/sampler/dimensions updates |41986|2eeb204cfefbfdcfb3f3645ada376cc64cbe357820244436445fd0445e53bdb4|
| docs/research/SYNTHESIS.md,3.1-3.2 |2213785|e0448cc278635067dccd004cd8e469a73ad2a2df7bd1232b80a3cf4ccde9e6b0|
| experiments/common-tiff-dimensions/charter.md |6150|4f3605c505ae9adce0ff9c7d6f8e6246fab0a379efaa9b6a928be2fee1c6f69c|
| experiments/sampler-boundary/next-consumer-audit.md |10597|d13cbb4dbbab432e55c457f5f9f4f65a908cf846f9522370da49fad027e7b150|
| experiments/review-output-adapter/next-consumer-proposal.md |8759|5b8203a8c7c325db5fa3b2bfae8cbff7521fd4660029162ab1f835c4f934a68c|
| experiments/ORCH-drift-check/prior_art.py |7322|c4765d84d89f8cbc8d4f0cc9342c6068d85dc695c0ae7dcf47146d80c19faba5|
| crates/strehl-raw/src/common_tiff.rs,frame/parse/merge_planes |33071|bac1d18f036b8960a8e82d01b610ae945d00d259d4cc3fe7eb9106e8a8077f42|
| crates/strehl-core/src/align.rs,Similarity/PlaneRef/checked sampling/gather_into |148796|e5003cf05a2805a0a6a72b6f59f2724bcc8873ebbcc8bbb95a69120bda7a24a1|
| crates/strehl-cli/src/bin/common-stack/mod.rs,actual input loop/fold |18095|fc55cdaca929b5540901dc246c4294df6fa6c9f3a4407b16799c0de2ecd91452|
| crates/strehl-core/src/pyramid.rs,BandGain/add_frame_with_gain |208956|ea0a490d299b156c449b3de8c5633fcaeda2190d1c92d1d9c5356e6a9a92c02e|
| docs/research/M165-common-input.md,verdict/residual doubt |54367|ace362ba1a5412c49028876cea7cc47cddf50fcd34d60139d2ca73dbbc54d45c|
| docs/research/M103-halfdrift.md,revised summary/16.2-16.7 |116405|04dffd42c5f9e5ec3c3cb937af36ac16e4c11937c2848037fbc6e3a9e486fcd9|
| crates/strehl-core/src/warpmap.rs,types/direction/gather_checked/gather_frame |54829|9d2198eeab5e8a941e297cf8fcd8a217d2454390220433ae19cc6b07e6fd721b|

Only repository-owned source and reports were read. No external repository,
GPL/LGPL source, native image payload, model, current result metrics or new
capture was accessed. Query hits outside the13 detailed files were treated only
as discovery evidence. The conclusion is an implementation recommendation for
review after current admission, not an experiment grant or a numerical result.
