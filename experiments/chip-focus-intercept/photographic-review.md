# Independent complete native intercept review

VISUALLY REVIEWED, 2026-09-25: **reject the fixed quadratic candidate as an
overall improvement over current production.** It retains the preceding
Gaussian candidate's substantial reduction of broad coloured spread. The
quadratic step restores a little definition relative to that rejected Gaussian
reference, but it does not recover the protected fine structures visible in
current production. The failure is residual softening/detail loss, rather than
an asserted new ringing or noise defect. This closes the unchanged intercept
observation; no width/degree/front adjustment or production promotion follows.

I inspected both complete overviews, all 25 fixed native pairs (50 PNGs), and
then three already registered Gaussian-reference tiles. There was no new crop
search, recentering or display adjustment. All coordinates below are saved
delivered-native top-lefts. The rail pair is 384 square; other pairs are 256
square. These seven rows account for every one of the 25 inspected pairs.

| Region and inspected coordinates | Finding against current production |
| --- | --- |
| Rail crossing: (1098,958) | Yellow interiors have less pale/coloured spread and long rails remain strong. Alternating horizontal crossbar divisions and fine interior marks remain less distinct. Cleaner colour does not establish retained crossing detail. |
| Upper colour: (1036,196), (1292,196), (1036,452), (1292,452) | Main rectangles and text remain recognizable, but dotted contact interiors and narrow horizontal subdivisions soften. The two lower tiles reduce bright spill while compressing closely spaced lines. This fails the internal-detail protection. |
| Central stipple: (2976,1306), (3232,1306), (2976,1562), (3232,1562) | Compartment surrounds are quieter, but narrow stripes and triangular lined facets lose definition; the lower-left stipple remains smeared. Lower-right repeated bars remain while their internal fine texture is weaker. |
| Lower array: (566,2796), (822,2796), (566,3052), (822,3052) | Cell locations and gaps survive, with cleaner orange/yellow surrounding areas. Thin cyan boundaries are broader and dark-cell texture is less resolved. This is a mixed cleanup/detail tradeoff, not a demonstrated gain in native separation. |
| Lower colour: (4666,3016), (4922,3016), (4666,3272), (4922,3272) | Broad green spread retreats strongly in the first tile. The other three lose fine horizontal contact texture, dotted structure and triangular stripe definition. The quiet surround does not compensate for those losses. |
| Surface scratches: (4856,1256), (5112,1256), (4856,1512), (5112,1512) | Main long scratches remain, but fine branches, small marks and local edge structure remain suppressed. The smoother olive surface is not a valid sensor-noise measurement because these windows contain real structure. |
| Upper-left contact grid: (48,336), (304,336), (48,592), (304,592) | Strong white/yellow/green spread between contacts is much reduced and the whole view is cleaner. Tiny connectors, internal texture and contact boundaries remain softer in the border controls, so the extrapolated field does not pass detail retention. |

The extra Gaussian comparisons were upper-colour (1292,196), central-stipple
(2976,1562), and surface-scratches (5112,1512), using the exact previously
retained native tiles. The intercept shows modest additional definition in
the stipple and small scratch structure, but the larger losses against current
production persist. Improvement against an already rejected reference is not
overall acceptance. No conspicuous new patch transitions or dominant ringing
were the deciding issue in these fixed views; that is a bounded visual finding,
not a proof of absence throughout the original radiance field.

MEASURED validity: all 299 sources completed in reference149 with the unchanged
crop [133,89,3250,2166] and 6500x4332 output. Every actual active-source and
gathered-plane hash matches the preceding Gaussian observation. Its actual
development also matches. Current production RGB16/ICC and the pinned baseline
rewrite pass. The fixed all-site support/noise policy passes: condition maximum
8.937810, minimum left/right mass fractions 0.461535/0.425163, maximum unit-noise
gain 0.0760454, and maximum Gaussian-relative gain 1.732285. CFA hashes before
and after the constraint summary are identical. These geometric gains are not
measured camera-noise ratios and do not establish native quality.

The source model, width and reconstruction remain fixed. Tone settings are
held, but changed radiance/DC can change per-pixel tone/gamut response. Neither
this image nor the prior Gaussian pair identifies front error, blur-model
inadequacy, local depth variation or actual placement/gather error as the cause
of the remaining softness. The generated single-surface improvement did not
transfer strongly enough to satisfy the actual complete-image protections.
The original proxy and general intercept screen remain failed; the separately
authorized exploratory exception has now received its photographic rejection.

Root commands and saved process receipts:

```text
python experiments/chip-focus-intercept/reconciled-run.py full --controls experiments/chip-focus-intercept/native-controls-2 --out experiments/chip-focus-intercept/native-full-1
python experiments/chip-focus-intercept/native-run.py views --run experiments/chip-focus-intercept/native-full-1 --out experiments/chip-focus-intercept/native-views-1
```

The full job took 134.015 s (receipt internal 133.842 s), including both output
arms and checks. It is not an isolated estimator-speed or SOTA benchmark.
Complete masters are `native-full-1/output/{baseline,candidate}.tiff`; complete
6500x4332 JPEGs are `native-views-1/{baseline,candidate}-full.jpg`. Show these
complete outputs if discussing the visible cleanup with the owner; favorable
sections alone would conceal the failed detail protections.

The full invocation used the separate reconciliation wrapper after the native
build's overbroad source guard refused an unrelated standalone harness change.
The original refusal is retained. `native-results.md` and
`reconciliation-review.md` describe the compiled-input audit, preserved original
bindings and subsequently bound dependencies; no retrospective build-start
identity is claimed for those previously unbound inputs. This command record
corrects an earlier reconstructed `native-run.py full` line. The actual retained
executable, native-controls-2 result, photograph and verdict did not change.

Receipt SHA256:
`993ef60b57057ddb954476f543d374966e7b52f2d41fd27456c3b5237ae93074`.
Views-manifest SHA256:
`3f86c8c606d028d78a83da328b858ed7af9dcae6a7153b09dbe6d051a0897166`.
Candidate RGB16 SHA256:
`984c61f70c3f05ca5d7150cbf7a3737ff85e4f8d5a8dddae2f54c88995a73440`.
Current baseline RGB16 SHA256:
`fbeeda70e45be91086e5d6400b642054df908a87ae4021815ad493940960298c`.
