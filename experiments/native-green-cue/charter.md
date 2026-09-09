# Native green cue — one candidate, 2026-09-09

Status: source preparation; no quality benefit measured.

Purpose: use the original spatial locations of the two green CFA samples to
inform finest-band selection before demosaic/early green averaging. C12's real
optical energy existence check passed, but its through-focus and nuisance gates
were not completed. This allocation supplies one small consumer falsifier; it
does not mark C12 cleared or authorize a whole RAW ladder.

Implementation: one explicitly selected, off-default cue with the noise model
injected from the caller. Original frame storage remains u16, image arithmetic
f32, current reconstruction/accumulation and coarse bands remain unchanged.
No aligned-frame stack, super-resolution, new camera calibration or new package.
The designer defines the fixed operator and transport in design.md. Independent
controls must price constant green imbalance and gradients as potential scene
content; G1 minus G2 alone is not a noise measurement.

Consumer: the actual PyramidMerge finest-band weight followed by actual collapse.
A continuous high-frequency known-scene witness must survive to the consumer's
output grid. A single strong noiseless sinusoid cannot establish a benefit if
both operators produce the same relative defocus weights. Include a live flat
noise control first, and known signal plus destroyers so amplitude, alias or
noise manufacture cannot pass as preserved detail. Existing M194b fixtures may
reject regressions but lack this witness's intended high-frequency content.

Allocation: one fixed synthetic witness/control set. Root freezes source before
numerical execution; a different agent owns controls and interpretation. Up to
120 aggregate numerical CPU seconds, 2 GiB process commit, 256 MiB artifacts,
120 seconds per child; two worker threads. Compile uses the existing bounded
builder, at most 600 wall seconds/1800 CPU seconds/4 GiB per build. Compile
repairs may correct source defects, never change numerical bars after results.
No automatic repeats, parameter sweep, fresh original RAW reads or photo render.
Report source and executable bindings and retain failures. A passed result may
justify one separately specified next step; a failed candidate is not SOTA.

Root owns charter, build/run dispatch and decision. Designer owns the compact
fixed design. Implementer owns candidate/minimal production hooks and does not
execute numerical tests. Verifier owns independent controls/review. No SYNTHESIS
fold or numbered fact allocation. Preserve unrelated working-tree changes.

Primary background read (no source code copied): Eric Dubois's
[frequency-domain analysis of the Bayer structure](https://www.site.uottawa.ca/~edubois/SingleSensorImaging/Bayer_structure/)
describes the sampling geometry and luma/chroma overlap. It supports the need
for color/alias controls, not a claim that this focus cue improves stacking.
