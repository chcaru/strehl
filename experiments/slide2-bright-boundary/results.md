# Broad printed-boundary spread: actual-source attribution

2026-09-26. **VISUALLY REVIEWED by root and independently:** the focused
original and gathered witnesses retain substantially cleaner black gaps and
dark wedges at all three fixed QR/Siemens sites. The complete merge adds
conspicuous broad gray polygonal surrounds and fans. Narrow colored fringes
and some defocus already exist in the sources; those are distinct from the
broad pattern. Both nominated neighbors support the observation.

This establishes a concrete reconstruction target after the previous small
bar/lettering sites failed to expose a lost feature. It does not identify
terminal Mean, a particular AC band, or placement of other sources as the
cause. It does not prove that every one of the299 inputs lacks defocus spill
or explain mineral reflections. See `photographic-review.md` for the
independent stage comparison and limits.

Root executed, using installed Python3.12 with `-I -B -X faulthandler`:

```
experiments/slide2-bright-boundary/locate.py --out experiments/slide2-bright-boundary/locate-1
experiments/slide2-bright-boundary/render.py --locator experiments/slide2-bright-boundary/locate-1 --out experiments/slide2-bright-boundary/render-1
```

The all299 locator completed in108.235s, nominating QR-upper83/85,
QR-lower92/94 and Siemens58/60, with pale149 retained. All seven selected
original-u16 patches agree with the second decoder. The unchanged pale149
golden alone was reused; no old bar golden was claimed for a new coordinate.
The noisy-flat control demonstrates that the scalar nomination score is
not an image-quality measure. Source copying stays inside the RAW lifetime.

The complete observer-on render completed in112.391s with375.296875 summed
CPU seconds and3184046080 peak Job committed bytes. These are operational
observations, not a full-workflow benchmark. It reused the exact earlier
observer-off master, avoiding a second baseline run. Every output RGB16
sample and TIFF byte matches that baseline, and all seven actual raw-CFA
observer patches match the locator's independently decoded originals after
the literal f32 normalization, at the same sensor coordinates and CFA phase.
All merged slices and wrong-origin controls pass. Input metadata and
nominated original content are unchanged; no fresh all299 content audit.

The complete6476x4316 master is `render-1/on/output/replay.tiff`, SHA256
`24c66183ae94df908eb4a8662fc4b032532b7721655dfcc867e9a7d59b4f655b`.
The complete PNG is `render-1/matched-full.png`;21 unresampled384px native
panels accompany it. There is no improved candidate in this attribution run.

The next fixed ablation is written separately in `coarse-ablation-plan.md`:
average AC6 only with the existing `STREHL_PYRAMID_MEAN_COARSE=1` path, hold
the terminal Mean and finer AC path, and compare the complete output plus
all seven problem/protection regions. No multi-level sweep or default change
is implied. Its output must be reviewed before any quality conclusion.

## Completed coarsest-band ablation

Root executed `coarse-ablation.py --out experiments/slide2-bright-boundary/coarse-1`
with the same Python invocation above. The original session90682 returned
terminal exit0 and `COARSE_ABLATION_COMPLETE`; it was not restarted after
the goal-text interruption. The native process took92.969s and346.234375 CPU
seconds, with3217543168 peak Job committed bytes. This is an operational
observation, not a comparative performance claim.

The candidate is live:50311363 RGB16 channel samples change. Its full TIFF
SHA256 is `a514f8aaa47e47d97696f0c0e4cac8610f8c3be36e001b1a07e0c0431a1a9928`.
Both complete images and all seven fixed native pairs were inspected by root.
The broad gray QR surrounds and Siemens fans remain conspicuous; this does
not fix the measured defect. Small changes in the fine-bar background do not
establish a photographic gain. The independent review in
`coarse-photographic-review.md` also rejects the fixed treatment after both
whole images and all fourteen native panels, retaining the same scope limits.
No default or production code changed and no further mean-coarse sweep follows.

All original pre-run bound files remain unchanged. Four ancillary inputs
omitted from that list were captured in `supplemental-inputs-during-run.json`
while the job was live, explicitly not before it. The generated configuration
matched the frozen construction, and the two historical site inputs matched
their committed39b72e41 bytes. `supplemental-inputs-postcheck.json`, recorded
after terminal completion, confirms all four supplemental hashes unchanged.
This records the binding limitation rather than retroactively claiming a
pre-run check. The executed controller is preserved without modification.
