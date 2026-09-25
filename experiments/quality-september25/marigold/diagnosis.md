# New marigold output diagnosis, 2026-09-25

Scope: independent bounded diagnosis, not a quality improvement or a full audit. Originals and delivered images were read only. No production source, global alignment, GPU job, or full stack was run. Complete output overviews were examined before six new native crops; a total of 22 distinct stack-4 originals were then decoded for three bounded source ROIs. No global or per-pixel argmax was used to choose a witness.

## Provenance and complete views

VERIFIED from retained invocation, input order, alignment sidecar, render log and final TIFFs: four stacks have 292, 433, 339, 488 sources. The delivered TIFFs are the -0.5 EV variants of the seven-band production soft-selection merge with terminal mean. They are 6228x4152, 6212x4140, 6268x4176, 6268x4176 RGB16 with sRGB ICC profiles. Executable binding in the invocation is `2fd0a1615989e262fbba61e0a1587a9b8f20ff4913d3969510e967ce9d9219d7`. All frames placed does not establish placement accuracy. The previous review sampled 20 locations and explicitly did not establish source-detail retention.

`overview-receipt.json` binds every delivered master. Stack 4 master SHA256 is `7df00e469bb392a5c045613815dbcd885eb470e9f10f630c9add6fda1bb179a0`. Its retained map is reference 244, with common native output origin (382,256), equivalent to CFA-plane origin (191,128), and original CFA-plane geometry 3516x2344. The map's 4.0590-plane-pixel held-out number is not independent per-frame truth.

Whole-image previews: [stack 1](stack-1-overview.png), [stack 2](stack-2-overview.png), [stack 3](stack-3-overview.png), [stack 4](stack-4-overview.png). These are complete images, max 1617 pixels, with rounded u16/257 conversion and original ICC, no tone or exposure changes. Native crops in `regions.json` were not resampled.

## Concrete observations and source trace

1. **Stack 4 fan/hair region**, native output rectangle `(3230,3000,600,600)`: the merged image has sharp near hair tips together with faint, transparent-looking longer hair lines, over broad yellow haze. These lines are not all inventions of the merge. In the held map's coordinates, originals 104/120/128 show different portions of this hair cluster coming into focus; 136/152/168 show recognizable fine hairs through broad foreground defocus. The changing visibility of real structures makes a simple remove-the-faint-lines criterion unsafe. The output's broad haze is real as an appearance observation; its exact excess over a physically correct all-focus image is not measured.
2. **Stack 4 left rim**, `(1170,1380,650,600)`: hanging hairs cross a bright petal and have a soft, translucent-looking base in the output. Original 80 shows the hanging hairs against a defocused bright background, while later originals focus other parts of the edge. This is a useful protected hair-retention region, not a proven duplicate-contour defect.
3. **Stack 4 central throat**, `(2350,2310,700,500)`: faint hair/vein-like traces run through a broad low-contrast region. Broad temporal sampling shows little sharp source structure at most sampled indices; some lines begin to appear near 240/256. Therefore absence from a few sampled sources does not prove fabricated detail, nor does this establish the best focused witness. Treat this as a suspicious site requiring retained-source checks, not a proven hallucination.
4. **Stack 1 left petal over rear bud**, `(640,1480,600,600)`: a sharp hairy petal overlaps a visibly soft rear bud with a broad transition. No source witnesses were traced for stack 1, so this location alone cannot separate incomplete focus coverage, occlusion, registration or merge contamination.

The source ladders are in `broad/`, `refined/`, and `adjacent/`. Direct green CFA samples, copied while RawPy owns the buffer, avoid any demosaicer creating the traced hair lines. Only the three bounded ROIs are resampled into the existing reference gauge. The display is fixed square-root grayscale; it is **not tone-matched to the output**, so brightness/contrast differences between witness and output are inadmissible as quality evidence. Two-native-pixel sampling and linear interpolation are also insufficient to certify native fine-detail retention.

LibRaw declares 7028 visible columns while the renderer declares 7032. We copy the explicit renderer domain `[0:4688,0:7032]` from the decoded buffer; all ROIs lie well inside the common domain. The receipt records this mismatch, source file hashes, pattern, black/white values, and active little-endian u16 hashes so another decoder can check it. **Independent decoder agreement on these new files has not been established.** The first run's shape assertion caught the metadata mismatch; it did not silently reshape or pad the image.

## Rejected gross-placement hypothesis

The broad ladder initially looked as if one sharp cluster moved tens of pixels. A closer temporal sample showed that this was different hair segments entering focus. The initial visual attribution was withdrawn before treating it as a registration defect.

MEASURED by `correspondence-check.py`: a fixed original-112 hair template, applied to held-map original indices 104,108,112,116,120, gives integer residual shifts in **CFA-plane pixels in reference-244 map gauge**:

| Region | 104 | 108 | 112 | 116 | 120 | NCC range |
|---|---|---|---|---|---|---|
| Fan | (0,-1) | (0,-1) | (0,0) | (0,1) | (0,2) | 0.723-1.000 |
| Rim | (1,0) | (0,0) | (0,0) | (0,0) | (0,0) | 0.781-1.000 |

This matcher can be fooled by blur, visibility change, shape change or matching a different hair. It does **not** establish true placement or rule out a few native pixels of residual error. The limited result is that the supposed tens-of-pixels displacement is not supported at these corresponding sites. A forced (6,-4)-plane-pixel translation is recovered exactly; a constant flat input is rejected before matching; identity reads zero; an independently applied Gaussian blur of sigma 1.5 plane pixels reads zero shift at both templates. Those controls can fail, but Gaussian blur is not the complete physical defocus model.

## Two bounded next interventions

1. **Prioritize one complete marigold-4 comparison of the existing, frozen cross-scale source-prior recipe**, with identical input order/map/crop/tone and an exact baseline replay. This tests a concrete cross-scale contamination mechanism on an opaque hairy subject; it is not a new parameter search or evidence the prior's known synthetic thin/glint failures disappeared. Predeclare the fan, rim, throat and existing inner-bud controls. Reject if haze reduction erases the separately witnessed real hairs, blunts near tips, or worsens other complete-image regions. A complete-image visual difference without preserved structure is not an improvement.
2. **If that is null, a diagnostic-only temporal-support intervention can test distant-defocus loading**: in the same actual full-context consumer, compare the ordinary coarse contributions at the fan with coarse contributions restricted to the independently viewed source interval 80-168, retaining finest coefficients, all normal geometry and the original baseline. This interval is a manually supported diagnostic for that region, not an automatic selector or a whole-image production recipe. Run a wrong interval (320-400) as a destroyer. It would support a temporal-support direction only if the supported interval restores source-compatible boundaries while the wrong interval fails. It cannot license restricting the whole image, whose rear buds focus elsewhere. Do not turn this into an interval sweep or claim whole-stack quality from the local counterfactual.

The first trial is the direct user-visible priority; the second only has value if a single bounded causal question remains. No new occlusion-halo algorithm is justified solely by these observations, and this diagnosis does not claim the current outputs are acceptable.

## Commands run

Interpreter: `C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe`, with `-I -B -X faulthandler`.

```
python -I -B -X faulthandler experiments/quality-september25/marigold/inspect-outputs.py
python -I -B -X faulthandler experiments/quality-september25/marigold/source-check.py --indices 0,64,128,192,244,320,400,487 --tag broad
python -I -B -X faulthandler experiments/quality-september25/marigold/source-check.py --indices 48,80,104,120,136,152,168,208,224,240,256 --tag refined
python -I -B -X faulthandler experiments/quality-september25/marigold/source-check.py --indices 104,108,112,116,120 --tag adjacent
python -I -B -X faulthandler experiments/quality-september25/marigold/correspondence-check.py
```

No performance comparison is claimed. These small source checks took seconds, not a full-stack render. The scripts/receipts are retained for review; NPY and PNG artifacts are local inspection data, not proposed code commits. This report's choices and interpretations have not yet had an independent second review.
