# Direct CFA sampler design

2026-10-26. ARGUED implementation design; no numerical or photographic result. Root owns module registration, CLI hookup and builds/runs. API: ActiveCfa::new(data,stride,active_x,active_y,width,height) -> Option<Self>; sample_checked(channel,x,y) -> Option<f32>. Channels0/1/2 RGB, coordinates active-native pixels, output raw DN with no black/WB/clamp. Immutable borrowed u16 source, f32 arithmetic, f64 coordinates.

Catmull-Rom uses the same coefficient polynomials as the existing resampler. R/B use actual phase offsets. Green uses u=(x+y-1)/2,v=(x-y-1)/2 and x=u+v+1,y=u-v. Every nonzero tap must map to the active rectangle. Exact-zero taps are skipped to preserve measured edge samples under identity without border extension. Constructor checks bounds/overflow once and keeps signed headroom. No small-image bilinear fallback changes the operator.

Root must preserve original frame while phase sinks write output; one original u16 clone is enough and is not an aligned volume. Real gathering and GREEN_ONLY synthetic probe must use this route. Root adapter applies (sample-black)*gain before unchanged inverse-WB/quantization sink. R/B bandwidth, green mixing, negative lobes and changed coverage are substantive risks. No private noise model.

Separate-green imbalance is a calibration caveat: the injected model distinguishes G1/G2, while combined-lattice taps mix both. Do not invent equalization or infer a new correction from output. Actual synthetic probe must transport supplied noise through both phases. Fixed bias/gain differences need explicit diagnosis. Independent controls should include unequal phase levels and independently drawn noise.

Local unit checks cover identity at padded/odd active extents, separate-channel affine fields, support refusal and invalid geometry. These are mechanics only. Reviewer owns independent spectral/noise/color checks. Oblique neutral high-frequency detail and independent color texture are adverse cases. Complete photographs and transfer decide usefulness; no default promotion is implied.
