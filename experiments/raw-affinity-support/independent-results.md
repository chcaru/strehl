# Independent result decision

MEASURED by root; independently reviewed from the frozen source, completed
receipts and all 13 result cases. Reject this exact RAW-affinity support rule;
no photographic replay is admitted. The instrument completed successfully,
which is distinct from its recorded `photographic_replay_admitted=false`.
There were three passing cases (both flats and ISO100 radial), eleven exercised
cases, and two unexercised ISO400 glint cases. No rerun or parameter change was
made by this reviewer.

The independently useful comparison is not simply fan against core. At ISO100
without brightening, fan/core/interior RGB error ratios are respectively
1.02225/1.07016/1.09468. Core template recoveries remain above truth: baseline
[1.0431,1.0334,1.0523] becomes [1.0392,1.0305,1.0469]. Thus the core failure is
higher actual RGB error despite slightly less overcontrast, not loss of its
in-phase amplitude. Its chroma error improves to 0.84780. A colour-difference
metric or a retained-amplitude observation alone would misread this result.

The no-glint twin establishes an independent failure without fan contamination.
At ISO100, stable illumination gives boundary/interior ratios 1.05035/1.09560;
the corresponding ISO400 ratios are 1.09440/1.11616. With brightening the
interior ratios become 1.27704 and 1.43290. The thin-ridge component remains
protected in these twins, but boundary/interior error still fails. Therefore
neither the synthetic fan nor the added lighting nuisance is necessary for
rejection.

Common brightening makes all 18,420 nonself affinities positive in the ISO100
glint case, with weight sum 18,365.97. Affinity fan/ridge RGB ratios become
2.71554/3.13026, close to the cue-free AllAffinity placebo's 2.89564/3.43673.
The cue changes the result and is slightly less damaging here; it does not
preserve depth identity. The ridge's baseline components
[1.0264,0.9944,1.0454] fall to [0.8314,0.8029,0.8382], a genuine loss under the
truth-capped guard, while core recovery and error pass. The independently
commissioned two-block nuisance raises unrelated-profile affinity from zero
to 0.999142. This is a demonstrated ambiguity, not a noise-significance result.

The frozen FAN window also crosses the near half-plane beginning at native
x=164 and includes part of the ridge near y=138. Its RGB ratio measures a
composite region; it does **not** measure a 2.7-fold increase in ray strength.
The separate ridge, boundary and no-glint comparisons carry the rejection
without that interpretation. Moving the crop one quad keeps this failure:
fan/ridge ratios become 2.74726/3.34548. That is a physical block-phase stress,
not an assertion that the operator should be shift invariant or proof of a
particular visible seam.

The positive results remain real and bounded. Flat RGB ratios are
0.87855/0.87764 at ISO100/400, with chroma ratios 0.88908/0.88732 and finest
averaged fraction becoming exactly one. ISO100 true radial RGB/chroma improve
to 0.91640/0.83666 with retained components. At ISO400, radial RGB worsens to
1.06304 even though chroma improves to 0.95542 and red/blue recovery rises.
This independently reinforces why amplitude and chroma cannot replace RGB
truth error. It is not blanket deletion of radial detail.

The ISO400 glint positive is unexercised: its clean late-source fan RMS is
0.00347112, below twice the matched flat baseline RMS
(2 x 0.00222078 = 0.00444157). The ISO100 positive exceeds its corresponding
0.00221978 requirement. ISO400 glint measurements are retained but cannot be
called a successful replication of that positive fixture. All mandatory
baseline components are live; their qualification is not the source of these
two refusals.

The mechanical evidence is exercised. Off reproduces completed CFA planes and
RGB exactly. All 65 case/source records preserve original-input and replay
hashes, including actual gathered known4, guide, variance, beta and descriptors;
all 13 cases retain nonfinest accumulators exactly. AllAffinity changes 54,131
CFA samples, and forced source4 changes 72,104. The forced arm reduces core
recovery to [0.4023,0.3931,0.3683] and increases its RGB RMS to 0.046069 versus
baseline 0.013595, so the wrong-donor guard is demonstrably rejecting a live
error. Literal affinity and pooled-field maximum errors are respectively
1.19e-7 and 5.81e-6. Source reversal is only the fixed-descriptor arithmetic
control, not a second image run.

Evidence: `build-1/process.log` contains fresh `Compiling strehl-cli` and a
successful release build; root's operator and actual-screen commands and logs
are recorded in `controls-1/operator/process.json` and `controls-1/process.json`.
Their wall times are 0.266 and 2.719 seconds, operational receipts rather than
speed benchmarks. The reviewed `controls-1/output/screen.json` SHA256 is
`c36ea2504d1a93c221553ada1d7632b9d903d3e810f06c149ee37a1dd36b9d65`.

Close the frozen rule. Positive through-focus association has not justified
source ownership, and these results do not justify rescuing its radius, block
size, cosine or global-brightness treatment. This generated result makes no
camera-calibration, real-image quality or SOTA claim.
