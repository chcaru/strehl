# Independent photograph review: one coarsest-AC mean

**OBSERVED: reject this fixed treatment as a useful image-quality improvement.**
The complete-image views and all fourteen preselected native panels do not show
a useful reduction of the slide's broad gray spread. Printed detail is mostly
retained, but that alone does not make this a successful repair.

I inspected both complete-image overviews, then every baseline/candidate pair
at its unresampled 384 x 384 size, starting with the pale control. Coordinates
are the seven fixed entries in `coarse-1/completion.json`; none was recentered
or selected from the candidate.

| Fixed region | Independent visible assessment |
| --- | --- |
| Pale control | The faint points and fine granularity look very similar. No conspicuous new structure or visible gain. This is not a measured noise-equivalence result. |
| QR upper | The broad polygonal gray surrounds remain around the isolated white squares and in the dark corners beside the connected white shape. Around the upper isolated square, the candidate's gray surround looks more filled rather than removed. White edges remain recognizable; no useful cleanup. |
| QR lower | The gray band under the broad white rule and the rounded spread beside the lower vertical white bars remain. The subtle tonal redistribution does not recover the cleaner dark gaps visible in the fixed gathered source witnesses. |
| Siemens contact | The central junction and wedge edges remain, but conspicuous broad gray fans still fill the dark wedges, especially to the right and downward. The candidate does not produce the cleaner dark wedges of the selected gathered sources. |
| Medium bars | The upper triple bars, vertical bars, number column and smaller central groups remain. Broad low-frequency shading is somewhat more apparent across the upper background; no extra resolved printed feature is established. |
| Fine bars | The central short groups and diagonal leaders retain their positions and separations. No specific missing or doubled feature appears, but no clear detail gain is visible either. |
| Lettering | The rounded counter, multi-stem characters and lower thin rule remain essentially the same. No meaningful improvement. |

The source comparison is limited to the already reviewed nominees in
`photographic-review.md`. Those actual gathered images show cleaner dark gaps
at these three large boundary sites. They are not all-focus truth or evidence
that every one of the 299 sources is clean. The candidate's failure to approach
those cleaner gaps is a useful negative for this one intervention.

**VERIFIED from saved execution receipts:** the root-run command was
`python -I -B -X faulthandler experiments/slide2-bright-boundary/coarse-ablation.py --out experiments/slide2-bright-boundary/coarse-1`.
The full 299-source job exited 0 in 92.969 seconds, with zero active processes
at termination. The retained baseline TIFF SHA256 is
`24c66183ae94df908eb4a8662fc4b032532b7721655dfcc867e9a7d59b4f655b`;
the candidate is
`a514f8aaa47e47d97696f0c0e4cac8610f8c3be36e001b1a07e0c0431a1a9928`.
Different output samples establish liveness only. The completion records
unchanged original metadata and bound files. Four additional input hashes were
captured during the run and all matched the post-terminal check; this is the
explicit scope of `supplemental-inputs-postcheck.json`, not a claim that those
four bindings were captured before execution.

The fixed `mean_coarse=1` path averages only AC level 6. AC levels 0 through 5
and terminal Mean retain their prior policies; final synthesis and the input
hull can couple the visible result. No coefficient-hash identity is claimed.
This negative therefore does not identify terminal Mean as the cause, exclude
other AC contributions, or authorize a sweep of additional levels. It closes
this one treatment without promotion or a broader alignment/glare verdict.
