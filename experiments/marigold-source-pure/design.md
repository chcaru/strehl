# Fixed three-source marigold counterfactual

Status: implementation prepared, UNVERIFIED until independent review and root execution.
This is a manual diagnostic of source-purity headroom, not an automatic ownership
model, released merge change, image-quality result, or SOTA qualification.

The observed marigold fan contains real fine hairs that sharpen at different
focus distances. Earlier coarse-source-prior and rendering experiments did not
convincingly repair the haze. This asks one narrower question: does substituting
one *complete gathered RAW source* clean a contact boundary while retaining the
two real hair groups? Unlike the earlier donor-consistency AC replacement, it
retains neither current coarse AC nor a mean base in the full-weight core.

Inputs are configurable root-selected complete marigold4 cache, full receipt,
recipe, and TIFF. Prefer the corrected numerical baseline after its independent
qualification; no old cache or tone hash is hardcoded. Cache phase must be full,
488 sources, reference 244, quad crop [191,128,3134,2088]. Receipt binds cache
and complete ordered source evidence. Recipe serialization binds exact input
order, and map file/hash/identity/reference/crop are checked. Exactly source
indices 112, 152 and 320 are decoded once each. Their original file SHA-256,
actual active-u16 hash and four actual BandWorker gathered-plane hashes must
match the complete receipt. The full count 488 goes into the worker, maintaining
the probe policy. No alignment fitting, source search or all-stack RAW job.

The fixed native core is [3230,3000,384,384], with a 32-pixel smoothstep ring
and total support [3198,2968,448,448]. The mask uses quad centres and is shared
across four planes. Core replacement is a literal donor copy; ring replacement
is a convex combination of signed final CFA values. No sharpening, hull clamp,
PSF fit, hidden AC term or preserved mean base is added. Donor 112 addresses
the near hairs, 152 the farther line; 320 is a deliberately defocused destroyer.
No donor or mask sweep follows a failure.

The unchanged full cache is first passed to actual write_merged with its current
automatic tone. Its complete RGB16 and ICC must match the selected baseline.
The existing Current writer observer records exact resolved Tone/Develop bits.
Pinned replay copies only the restore=None writer normalization/interleave
expressions and calls the real image_out::write_demosaiced with those exact
anchors. This diagnostic duplication is explicitly limited to this held
configuration. A zero mask with a contrasting synthetic donor must preserve all
CFA bits, complete RGB16 pixels, and ICC before any original is decoded. Every
donor uses identical recorded development bits; no auto-tone is re-estimated.
Literal TIFF hashes are also recorded, while identity admission uses pixels
and ICC to avoid conflating descriptive TIFF metadata with image arithmetic.

Every CFA value outside the mask must remain bit-identical. Every complete RGB
pixel outside [3196,2966,452,452] must match; that rectangle is the mask expanded
by the actual current Malvar-He-Cutler support radius of two native pixels.
Directional demosaicing and competing overrides are rejected. The zero-mask
test has a distinct donor so an accidental nonzero mask can fail. Generated
controls require core, ring, outside and inject an outside-RGB destroyer to
prove the support checker can reject it. These are arithmetic/interface gates,
not image-quality evidence.

Resource ceiling: one bounded Windows job, 8 GiB committed memory, 120 seconds
wall time, 900 CPU seconds, eight worker threads. Complete source frames are
never materialized as an aligned volume. Only one current worker is retained;
three small four-plane donor patches survive its disposal. The baseline and
one candidate final cache exist during a write. Resource limits include the
five whole TIFF writes. The driver fails closed on timeout; an overrun is not
an excuse to admit an incomplete or subset full-stack result.

Independent review must choose whether visible hair loss, color discontinuity,
noise, or ring seams outweigh a cleaner boundary. Success requires cleaner
contact structure **and both real hair groups** without these failures. A
merely darker region, erased faint hairs, or beating only the deliberately
blurred source is failure. If haze remains in pure sources, mixing is not a
sufficient explanation. If it disappears only by deleting the other depth's
hairs, ownership conflict remains unsolved. No scalar sharpness metric is used.

Root adds a cfg(test) merge_cmd::marigold_source_pure include of oracle.rs,
using the same native-direct-planes/native-correction-variance/native-gpu-gather
feature conjunction as full_stack_source_prior. No shared source is edited by
this author. Root build must snapshot run.bindings(), record fresh Compiling
strehl-cli, and retain cli-tests.exe plus sources.json/executables.json/process.log.

Commands, for root execution after independent review (not run by author):

```powershell
python -I -B -X faulthandler experiments/marigold-source-pure/run.py controls --build <frozen-build> --out experiments/marigold-source-pure/controls-1
python -I -B -X faulthandler experiments/marigold-source-pure/run.py run --build <frozen-build> --controls experiments/marigold-source-pure/controls-1 --recipe <marigold-recipe.json> --cache <corrected-candidate-cache.json> --full-receipt <corrected-full-receipt.json> --baseline <corrected-candidate.tiff> --out experiments/marigold-source-pure/run-1
python -I -B -X faulthandler experiments/marigold-source-pure/run.py views --run experiments/marigold-source-pure/run-1 --out experiments/marigold-source-pure/views-1
```

Whole baseline and all three donor outputs accompany any later visual report,
with ICC-preserving <=1617 overviews and unresampled 384-native core/ring/control
tiles. Whole overviews establish orientation; native tiles support fine claims.
Source diagnosis/proposal is experiments/quality-september25/marigold/source-pure-oracle-proposal.md.
