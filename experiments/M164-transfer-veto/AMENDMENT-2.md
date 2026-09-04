# M164 preregistration amendment 2 — clipping repair and threshold refinement

Status: frozen after commissioning run 1 and before the measurements below.
Run 1 is preserved byte-for-byte as
`commissioning-run1-pre-clipping-control.json`.

## Why a repair is required

Run 1 exposed a stimulus defect, not a gate failure. The original source
mapping to `[0.10,0.90]` left insufficient headroom for USM amounts `0.50` and
`1.00`. Quantization clipped some crops, so those arms were no longer a common
linear transfer. The frozen veto correctly refused several of them; counting
that as failure to detect USM would test clipping plus USM rather than the
registered contract.

No instrument family, statistic, or threshold changes.

## Added clipping-free sharpening battery

For sharpening only, derive

```text
A_headroom = quantize(0.5 + 0.2 * (A - 0.5))
B          = quantize(A_headroom
                      + amount * (A_headroom - G_1.0(A_headroom)))
```

Run the original amount ladder and require zero pre-quantization samples
outside `[0,1]`. The original run remains reported, including every clipped
failure.

## Outcome-informed threshold localization

Run 1 bracketed, but did not tightly locate, four transition points. Freeze one
additional ladder for each before reading it:

- Gaussian sigma: `0.26, 0.27, 0.28, 0.29 px`;
- clipping-free USM amount: `0.0025, 0.0030, 0.0035, 0.0040, 0.0045`;
- scalar gain delta: `0.00012, 0.00014, 0.00016, 0.00018`;
- bilinear round-trip displacement:
  `0.001, 0.002, 0.005, 0.010, 0.020, 0.030, 0.040 px`.

The reported threshold remains the weakest strength firing on 12/12 crops
with every stronger strength in the combined original-plus-refinement ladder
also firing on 12/12. These additions refine resolution only; they do not
alter a pass/fail bar after seeing it.
