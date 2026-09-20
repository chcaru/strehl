# Independent complete-photograph review

2026-09-19. **Reject this fixed candidate for promotion.** The complete render
succeeds mechanically, but the observed highlight tradeoff is adverse. Some
thin rays contract while broader coloured smears and patches appear. This is
not a clean solution to the target defect and does not close the gap to the
retained Helicon B result. Original generated admission remains false.

## Integrity and scope

VERIFIED from root's bound receipts: seventy sources,6920x4612 RGB16 output,
held crop[28,19,3460,2306],4096-square twelve-level candidate, eight threads and
one operator worker. The historical baseline decoded-pixel guard passes at
`2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda`;
root also records exact array equality. Inputs, map and source metadata are
unchanged. The successful job took1253.844 wall seconds and2365 CPU seconds,
peaking at7,812,116,480 bytes committed memory. This is one bounded execution,
not a timing benchmark.

Reviewed the complete baseline/candidate overviews, retained Helicon B whole
preview, all five frozen384-native boards and all three nearest-replicated
detail boards. Flat background was inspected first. The full PNGs retain all
pixels; their display conversion is rounded RGB16 division by257 with held
ICC and no tone change. Native boards do not resample source pixels. Helicon
uses the previously held map only to choose integer crop origins, retaining
its approximately1.0107 scale difference. Accordingly, its fine alignment is
not pixel truth. Whole resized views establish overall appearance; the native
views support the local defect descriptions. No new score or RAW read was
performed by this reviewer.

## Observations

- **Flat first:** pale-background grain looks broadly similar, perhaps slightly
  smoother in the candidate. No gross flat-field instability is apparent.
  Small soft marks remain; this is not evidence of recovered structure.
- **Whole photograph:** the general subject and blue rendering remain intact,
  with no obvious large rectangular seam or catastrophic boundary at overview
  scale. Several bright spots become more bloomed/patchy. I see no compensating
  improvement in the dense fine-crystal field across the full scene.
- **Dark inclusion, both branches:** the baseline's long downward left tail
  becomes a broader multicolour smear. The candidate adds conspicuous green
  and magenta bands above the bright edge, intruding into the dark core. The
  right glint remains expanded with coloured spokes. This is a decisive local
  regression even though one narrow tail is less distinct. Helicon B keeps
  substantially cleaner, more compact boundaries in the same region.
- **Facet:** the left-going thin rays are shorter, but cyan/green spread and
  broader patchy material surround the bright core. The crystal outline still
  exists; it has not been globally erased. The improvement cannot be described
  as artifact removal without the replacement smear. Helicon B remains the
  cleaner compact-core reference here.
- **Genuine structure and colour:** the competing-depth diagonal and nearby
  edges remain recognizable, with no clear increase in recoverable detail.
  Fine-crystal highlights look more mottled/coloured in the candidate; the
  bright-facet region supplies no convincing new structure and some small
  marks appear softer. Without scene truth I do not label every colour fleck
  false, but stronger flecks or local contrast cannot count as quality.

The evidence closes this exact full operator as a quality candidate for this
scene. It preserves useful numerical/parallel-execution work, but neither
validates a general wavelet failure nor identifies which coefficient, weight,
phase interaction or input highlight caused the new colour patches. Those
would require a distinct diagnostic. Do not transfer or promote this recipe
on the strength of shortened rays, smoother background or successful runtime.

| Binding | SHA256 |
| --- | --- |
| full-1/output/candidate.tiff | 0b3e50438b3215513234713862716a4bd4c50cc6a4ca6c9428f2b17a5edab9d6 |
| full-1/output/receipt.json | 6a31739c39fb290b4bc65ded4fb290131f2c4b3b125b1d7ebab9940dc629c8d1 |
| full-1/completion.json | 77d8222408aca7a57b6aed4fcba9b65cd3bc56a001c5c6cd37ede4e0675543cd |
| full-1/process.json | d48fc1a602f1535baac909868908854ff9f2b43853e72ea055f54b62fc09bcf0 |
| full-1/photo-comparison-1/coordinate-receipt.json | f447f8910581c66b6ba75522a2d9aefeb2cfd8ce80a70b82d7c7a65f70bc6a84 |
| photo-compare.py | 290c2e4bf494a34d79a77ab7cecd15545bc7af72d6f7d916daf835535584a6ca |
| ../helicon-current/vitamin-c-b-2/whole-stack.tiff | f08335d17083789fa2bd60ee17ecbaba921bbc7aa20c9fdfdfa0cf0e1ca1d2d8 |
