# Opal103: the omitted fixed display-headroom comparison

Status: implementation ready; no new RAW decoding, rendering, or quality result
has been executed by this author. Root owns execution and independent review.

The mineral diagnosis explicitly nominated complete opal103 for the unchanged
merged-radiance shoulder comparison. The completed highlight factorial receipts
cover garnet104, ore100, and marigold4. Their null/damaging results remain closed;
opal103 is the omitted comparison, not permission to sweep another parameter.

The three previously sampled opal originals have active maxima 4356/4992/4987
DN and no samples at nominal white. This is evidence of headroom in those three
originals only. It says nothing about the other 152 originals or about the RAW
values actually contributing to each finished highlight.

Use all 155 ordered originals in
`D:/personal/macro/minerals/rainbow-opal-cabochon/103MSDCF`, the retained
`outputs/minerals-september24/103msdcf/alignment.txt`, reference77, crop
[60,40,3396,2264] in CFA-plane coordinates, and exposure -0.3 EV. First produce
a new complete baseline through `scripts/render-native.py` with the current
checked arithmetic. The current native configuration is unchanged: rounded GPU
gather, the green probe, matching optical profile, as-shot WB, seven bands,
soft weights, gate2, exponent2, ramp1.4, mean base and automatic tone.

No new Rust adapter or colour pipeline is needed. The existing
`full_stack_source_prior::complete_pair`, mode=current, accepts this new
production baseline as its expected image. It supplies the full actual native
cache with per-original active/gather/guide/variance/energy/floor/weight hashes
and the canonical chunk plan. The old pre-repair opal image is not an equality
target. The cache replay must match every RGB16 sample and the ICC of the NEW
production image before any candidate arm can run. Instrumented/current
observer on/off complete TIFF files must also be byte-identical. A disagreement
stops the experiment; do not relax the identity requirement.

Run precisely the existing four rendering arms: current, sensor-rolloff-off,
the fixed shoulder at .75, and both. The actual writer's resolved tone,
exposure, matrix and ceiling bits must be identical across arms. The existing
four independent controls commission that writer under the exact test binary.
Below-knee nulls, neutral/coloured ramps and pinned-highlight protection remain
binding. No parameter, exposure, crop, WB or source ranking is retuned.

## Photographic refusal and protection targets

Frozen before candidates from the existing opal witnesses:

| Target | Native output rectangle | Required observation |
| --- | --- | --- |
| Reflection | [3628,1658,384,384] | Additional distinct bright bands/gradation must be visible; retain fine slanted marks, cyan surroundings and the physical reflection. |
| Colour control | [2128,2228,384,384] | Preserve blue/pink variation, fine irregular texture and small dark marks; it is textured, not a flat-noise ROI. |
| Complete image | Entire6792x4528 output | Preserve the spatial blue/green/pink colour play, boundaries and bright reflection structure. An overview is orientation only. |

The author inspected the old complete overview and both384px native witnesses
to freeze these targets. No candidate output has been seen at registration.
Root independently reviews all four complete outputs and the two native pairs.
Actual restored local gradation earns consideration. Merely fewer white pixels,
lower average brightness, greyer highlights, flattened texture or hue shifts
fails. A positive result remains a display-only finding; it cannot establish
RAW clipping recovery, registration repair, or removal of an occlusion halo.
If no arm gives a clear useful gain, close this comparison without a sweep.

No sharpness metric or flat-noise improvement is claimed. Pixel/hash checks
test identity, not quality: unchanged images pass identity but cannot pass the
photographic improvement decision. The existing generated ramps have distinct
above-knee steps and the fixed destructive alternatives in the commissioning
tests, so a renderer that clips or neutralizes valid colour can fail.

The cache run is bounded at900s wall,6000s CPU and12GiB job commitment; prior
complete183/207/488-source runs on this same adapter establish resource scale,
not a speed claim. Replay keeps the existing240s/1200CPU/8GiB bounds and opens
no RAW sources. No aligned frame volume is stored. Original corpus bytes remain
read-only. Complete RGB16 masters, full views and all receipts are retained.
