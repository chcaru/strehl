# Multi-stack Windows tryout

This is a development build of the multi-stack branch, not a public release.
Keep its `source` folder, source ZIP and license/rebuild notices with the binaries.
Open `Strehl.exe`; Python is not needed to use the desktop.

1. Import one of your source stacks normally.
2. In Projects or Adjust, choose **Create multi-stack session**.
3. Add another separately acquired sweep as an **independent pass**. Use
   **continuation folder** only for another folder belonging to the same sweep.
4. Choose a result mode. **Interleaved focus** combines complementary focus
   positions; **Repeated captures** averages supported repeated observations;
   **Aligned layers** preserves different aperture/lighting/appearance choices;
   **Independent views** retains separately stacked viewpoints.
5. For simple fusion, optionally select a **Primary** pass or leave Automatic.
   Primary anchors framing and supplies a preference when supported observations
   disagree. Mosaic and Independent views have no primary.
6. Choose a destination with free disk space outside the source folders. Start
   with the default 16 GiB session RAM budget; increase it if the reservation
   reports that more is required. Adjust CPU threads to suit other running work.
7. Stack, inspect the saved photograph, then use the layer/view selector where
   applicable. Develop/export the retained native photograph or linear master.

For a first trial, use a small related pair and leave optional diagnostics and
reconstruction off. Add contribution/focus evidence later to inspect support;
these maps can occupy substantial space. The separate decoded-CFA cache is shared
between session revisions and can also be large. Originals remain read-only.

**Experimental limits:** Wider mosaic does not yet have an acceptable demonstrated
real extended-field output. Original-CFA reconstruction has working support and
fallback machinery but no demonstrated recognizable-detail improvement. Exposure
range handles compatible shutter changes/clipping; simultaneous highlight/shadow
superiority over both singles remains unproved. These controls should be treated
as experiments. Broader repeat matching remains a hidden research option and is
not automatically enabled in this build. Existing ordinary stacking uses its
existing pipeline.

The [full feature guide](multi-stack.md) describes settings, eligibility and
limitations. The repository's `docs/multi-stack-handoff.md` records all completed
and pending development for the next agent.
