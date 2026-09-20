# Fixed source-consistency result

This is a native RAW counterfactual with externally supplied regions and source
indices, not an automatic selector or a SOTA result. The complete70-frame
vitamin-C triplet is retained at `full-1/output/`. Each image is6920x4612 RGB16.
The charter fixed all masks, source indices, blend law and photographic failure
conditions before execution. No photographic parameter was adjusted afterward.

## Executed commands and operator checks

All commands ran from the repository root with Python3.12, using `-I -B`.
`run.py` records child commands, input/source bindings and bounded process cost.

```
python -I -B experiments/donor-consistency/run.py build --out experiments/donor-consistency/build-1
python -I -B experiments/donor-consistency/run.py controls --build experiments/donor-consistency/build-1 --out experiments/donor-consistency/controls-1
python -I -B experiments/donor-consistency/lean-controls.py --out experiments/donor-consistency/lean-1
python -I -B experiments/donor-consistency/run.py build --out experiments/donor-consistency/build-2
python -I -B experiments/donor-consistency/run.py controls --build experiments/donor-consistency/build-2 --out experiments/donor-consistency/controls-2
python -I -B -X faulthandler experiments/donor-consistency/run.py full --build experiments/donor-consistency/build-2 --screen experiments/donor-consistency/controls-2 --out experiments/donor-consistency/full-1
python -I -B experiments/donor-consistency/photo-compare.py --run-dir experiments/donor-consistency/full-1
python -I -B experiments/donor-consistency/change-extent.py
```

MEASURED: first fresh build148.515s; first controls failed. The independent
fixture reused a memoized source pyramid without advancing FrameWorkspace.
Production already performs that advance. `failure-diagnosis.md` preserves the
failure, same-core isolation and correction; `controls-review.md` independently
accepts the lifecycle repair without relaxing the original limits. The added
independent three-source mean-base assertion rejects the cache omission.

MEASURED: corrected lean compile3.782s, tests0.125s. Final fresh core/CLI build
148.922s, actual CLI controls0.312s, two tests passed. These are individual job
receipts, not an alternating speed comparison. The final controls establish:

- Exact three-source terminal mean, zero/off and observer-baseline equality.
- Actual live range-clamp excursions on all four planes, including a second
  explicit pin fixture; original all-ones returned-image discrepancy0DN.
- Mask reduction/normalization discrepancy0; largest coefficient difference
  0.00003052DN and returned-image difference0.00024414DN against independent
  calculations, both below the unchanged0.003DN tolerance.
- Same-mask wrong-source control changes25,984 samples; source hashes remain
  unchanged. These counts establish participation, not photographic quality.

## Complete RAW replay

MEASURED: full job37.109s wall,118.609375s user+kernel CPU, peak job committed
memory4,216,139,776bytes. This includes one native baseline merge, streaming
capture of four source pyramids' masked contributions and three developed
outputs. It is not three independent stack timings or a competitive speed
benchmark. The held warp map was already available; alignment is excluded.

VERIFIED: baseline RGB16 sample hash is exactly
`2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda`,
matching the historical complete output. TIFF files differ because Software
truthfully identifies the new build. Source active-u16 hashes and metadata,
map identity, four original gathered donor planes, output extent and fixed
development remain bound in the retained receipts. Originals were read only.

| Complete TIFF | SHA256 |
| --- | --- |
| baseline | f0eab596dd0e37e80084588629d592a6c261c97eb9a1655b20e39ef430e23535 |
| candidate | ba57bb889a0dbe883e3fd889dffb831bbf7296d8f32730337ecde7f6123f2b48 |
| late69 | 6635aee9c56f350e906b9add33453d1aab7e55b3f7e1ae03e80b4ba3b0b3fb6d |

Complete ICC-tagged PNGs and overview JPEGs are in
`full-1/photo-comparison-1/`, together with five frozen384-native windows per
arm. Conversion is rounded division by257, with no new tone/colour adjustment.
Native windows use the same exact output coordinates in all three arms.

MEASURED change extent, explicitly not a quality score: candidate differs in
523,457 RGB pixels at any channel bit (1.64016% of the complete image);24,148
pixels differ by more than257 RGB16 DN (0.07566%). Its nonzero bounding rectangle
is[2199,1677,1477,1648]. Broad low-amplitude changes arise from reduced masks in
coarse bands; the intervention is not strictly bounded by its finest capsules.
All pixels in the three remote frozen windows are identical. A zero change
cannot establish improved flat noise; it establishes unchanged output there.

## Photographic decision

Independent photographic review in `results-review.md` rejects the exact recipe
as an incomplete repair. The facet's compact core survives and two long tails
shrink, but a prominent cyan/pink tail remains at the dark inclusion. The nearby
source25 structure survives; no gross hard seam appears, though diffuse residual
beside the facet remains visible. Late69 visibly worsens both target areas.
Root inspected the independent centred boards and agrees: local contraction is
not a joint pass. The implementation author did not judge photographic quality.

The complete images occupy the same scene, but the intentional change is local.
Success can license one automatic source-assignment discriminator only. It
cannot establish improved whole-image quality, transfer to another stack,
calibrated colour, automatic operation, or superiority to Helicon B.

DECISION: close this exact recipe, with no donor/radius/feather/band-count sweep.
Keep automatic-design.md conditional. First explain the remaining consumer
loss with a read-only decomposition of actual source coefficients. The added
command `python -I -B experiments/donor-consistency/mask-membership.py` uses the
same bound core and frozen masks: at the dark-fan point a constant AC field's
expanded mask response is1,1,0.995975,0.784719,0.405718,0.153182,0.052245 across
the seven detail levels. This algebraic operator response establishes incomplete
coarse-scale donor membership; it is not an effective image-pixel donor weight
or an attribution of the visible tail. Actual varying coefficients do not
factor through mask expansion. The new observer will preserve the recipe and
account separately for retained baseline, donor contribution and final clamp.
