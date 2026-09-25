# Bounded source provenance of garnet color islands

Root requested this followup after independently confirming the native384 image. Re-decoded only three already-sampled originals: zero-based91/120/137, filesDSC00118/00147/00164.ARW. Command:

```text
python -I -B -X faulthandler experiments/quality-september25/minerals/garnet-islands.py
```

`garnet-islands.json` binds source files, plane counts and hashes. Small `.npy` crops retain actual u16 samples. Output region[4720,1930,256,256] includes both conspicuous rectangular colored patches. Its source coordinates use the retained reference91 sidecar and current crop origin, rounded to nearest original CFA quad. Each source plane is128x128 samples; there is no color interpolation, CA, tone, selection or merge. Grayscale preview uses the same fixed black512/container16383 mapping for all planes and sources.

VISUAL OBSERVATION, native viewer sizes<=256: `104-islands-native256.png` clearly contains both rectangular magenta/cyan patterned islands. Inspected original R planes91/120/137 plus G1 and B planes137 contain the physical reflection/facet with changing blur but no corresponding hard rectangular patch boundary. This excludes the simple explanation that those inspected original patches already contain those rectangles. It does not exclude another source frame, a gather/merge failure, a display/development discontinuity, or an interaction between stages. No quantitative artifact-width claim or complete-stack source census follows.

A current four-plane merged cache of the complete183-source garnet is therefore particularly useful next: inspect the same region before the color developer, then run the rendering factorial on exactly those values. The current evidence supports that stage separation; it does not yet identify the guilty stage. No original files were modified.
