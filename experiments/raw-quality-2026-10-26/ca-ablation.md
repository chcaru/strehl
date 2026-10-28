# Weevil lateral-CA causal comparison

2026-10-26/27. Active photographic ablation, not a profile change or quality result.

The independent source149 split observes stronger orange/blue separation on several upper-leg hair edges after the actual full-resolution gather. Both green CFA phases are exactly unchanged in that witness; R/B change. This nominates the applied chromatic geometry for a causal comparison. The complete source itself is not all in focus, so this observation does not establish whole-stack detail loss.

Prior: `optics.rs` documents the current radial-only profile, prior red overshoot and its later coefficient correction. M113-ca rejects calibration gains measured after demosaic and color conversion; M113-spectral confirms scene-dependent measured coefficients but rejects its proposed spectral explanation. Those results do not authorize a new coefficient from displayed fringe width, or attributing this weevil result to its colors, focus distance or illumination. The prior profile fitted other insect/corpus material; disabling it globally is not presently justified.

Searches executed: `python scripts/research.py search CA weevil --limit 5`; `python experiments/ORCH-drift-check/prior_art.py lateral chromatic insect`. Read actual profile documentation, M113-ca, M113-spectral and M114-ca-verify before interpreting the controlled result.

## Fixed intervention

Complete299 originals in the same order, frozen baseline executable SHA256 `89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388`, same Catmull-Rom map bytes/reference149/crop, four workers, same RAW/noise/focus/merge/development options. The map is copied to its own read-only comparison path. Only STREHL_FIX_CA=off changes. The runner binds the full environment and original hashes before/after; outputs stay outside the corpus.

```text
python -X faulthandler experiments/raw-quality-2026-10-26/render-ca-off.py --input D:/personal/macro/insects/bug-3/107MSDCF --out outputs/raw-quality-2026-10-26/weevil-107-ca-off --exe outputs/raw-quality-2026-10-26/baseline-strehl.exe --sha256 89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388 --warp-map outputs/raw-quality-2026-10-26/weevil-107-ca-off-alignment.txt
```

The original `render-cpu.py` remains frozen; this separate runner records the changed setting. Check logged tone values before claiming a matched display. Both linear masters are retained, permitting one identical display if automatic tone changes. Green pulls and focus inputs should be identical, but final MHC couples channel values; raw-green equality is not a proof of final RGB-green equality.

The supplemental source149 CA-off capture goes through the same production kernel and exact tiny reference-gauge roundoff. It is a distinct ignored test preserving the completed CA-on capture source. It isolates the existing profile's action at one source; it cannot establish a better scene-wide calibration.

## Metadata applicability observation

After the complete bug2 transfer worsened with CA disabled, root compares its original149 native optical metadata with the already inspected weevil149 record. This is a bounded read-only observation using the same frozen executable, not a coefficient fit or a new correction. It asks whether the capture state and embedded Sony correction tables differ, without assuming their units, application status or causal role. Record exact source identity and unchanged bytes; do not infer a profile switch from two photographs. Prior M113 scene variability and the October25 optical-metadata continuation's uncalibrated-coordinate limits still apply. Root ran unified research search for CA table and mechanical prior-art search for Sony/CA/metadata before this observation. The existing CA-ablation allocation owns the added record; no new RAW rendering or product mutation is authorized by it.

## Acceptance and scope

Independent review starts with the complete photograph, then all ten preselected native384 witnesses and the dark-background control under identical display. Inspect colored outlines, real hairs at different depths, scale gaps, glints, noise and any new color displacement. A local hair-fringe reduction with other field regressions is a tradeoff, not a general improvement. Do not estimate physical CA from developed sRGB. A promising whole-image result must transfer to another insect and non-insect adverse stacks before changing profile applicability or defaults.

Full output/master are required for any presented improvement. Operational render time can overlap builds and is not an isolated speed claim. Current complete Helicon B/C serve as workflow references, with their premerge tone, geometry and CA differences explicitly retained.
