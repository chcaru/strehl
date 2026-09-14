# Native source review — printer, 14 September

**No newly manufactured output defect is established by the allocated middle-frame comparison.** The baseline visibly has cyan/magenta fringes around small bright points and soft fine surfaces. The original middle frame already shows coloured structure around corresponding bright points; it is out of focus at several of the baseline regions. Those observations constrain the next intervention rather than justify an alignment, demosaic, or optics diagnosis.

## What was inspected

Baseline: `baseline-1/views/{junction,letter-edge,fibre,surface}.png`, each 384×384 native output pixels, inspected with `view_image`. Reference: `D:/personal/macro/requests/misc-diagnostic/3d-printer-piece-cpl/DSC00053.ARW`, frame 52, whose stored warp is identity. The logged output origin is plane `(48,32)`, hence native `(96,64)`; source crop origins add that native offset to the baseline crop origins.

Command run:

```text
python -X faulthandler experiments/quality-september14/source-review.py
```

**VERIFIED:** The existing independent `m61-decode-check.exe` and rawpy/LibRaw agree byte for byte over the union containing all four patches. `source-review-1/receipt.json` records the source, coordinates, display, and zero differing sensels. The rawpy buffer was copied while its owner remained open. There were two RAW decodes total, both of the same original. The original size and modification time were unchanged; no original was written.

Source green displays preserve one output pixel per same-colour sensor sample, with two native pixels between samples. Every source display uses fixed gain 2.809 and power 1/2.2. The additional LibRaw AHD colour crops use camera WB and no automatic brightness. No crop was spatially resampled. LibRaw and the baseline use different rendering paths and tone; colour comparisons are qualitative only. Decoder metadata also differs in white level (LibRaw 16383, rawler 15360), so these displays cannot establish a colour or exposure error quantitatively.

## Visual findings

- **VISUALLY OBSERVED:** The baseline junction's bottom bright edge has cyan/magenta micro-fringes. The source colour crop shows cyan/magenta structure at corresponding bright points before stacking. Raw G1 and G2 both show the underlying bright objects. This supports a source-dependent bright-point problem; it does not isolate clipping, chromatic aberration, demosaic, or additional merge amplification. In particular, the observation does not justify assigning these fringes to axial chromatic aberration.
- **VISUALLY OBSERVED:** The baseline fibre has a more resolved thin winding outline than this source frame. The middle source is visibly defocused there, and also over much of the letter-edge and surface crops. It therefore cannot falsify or quantify best-focus detail loss. Calling the baseline softness merge damage from these inputs would be unsupported.
- **UNVERIFIED:** Whether the baseline makes the source's point colour worse, or sacrifices recoverable edge detail. No sharpness score was run: the permitted reference does not supply an independent in-focus target for those claims.

## Two bounded next actions

1. Use the in-focus portion of the junction's bottom edge for a source-versus-merge comparison through the same colour/tone routine, with settings frozen to the baseline. A surviving fringe before fusion would reject the explanation that fusion alone created it. The current LibRaw comparison is only the cheap preliminary falsifier, because its rendering differs.
2. If testing a colour reconstruction change, reuse the same fused data and inspect that point edge beside nearby low-chroma texture and a real coloured-detail control. Fail the candidate if the point colours vanish by erasing genuine colour/detail, or if the flat control gains texture. Do not judge it by gradient energy or infer a best-focus gain from this single source frame.

This is a compact review, not a milestone or a SOTA claim; no SYNTHESIS facts were folded.
