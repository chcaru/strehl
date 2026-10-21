# REA and Adobe Adaptive: local investigation

Reviewed 2026-10-21. **VERIFIED** below means observed metadata or a command
actually run; it does not mean that Adobe's rendering was reproduced.

## What the installed tools expose

REA's [license](https://github.com/morluto/rea/blob/main/LICENSE) is MIT.
`rea-agents@6.7.0` was installed with scripts disabled under ignored
`outputs/rea-review/tool`, using a cache in the same investigation directory.
No agent registration, global configuration, Lightroom launch, catalog access,
or target modification was performed.

**VERIFIED:** the published CLI ran `inspect-pe-resources` and
`inspect-managed-artifact` against the installed Lightroom executable. It is
Lightroom 9.3.1, a native x64 PE with no CLR directory. Resource inspection
reported 509 examined entries and 248 resources; this inventories resources,
not rendering behavior. `providers` reported no configured native analysis
provider: Ghidra, IDA, and Kuna were unavailable; Hopper does not support this
Windows host.

The repository's current
[desktop](https://github.com/morluto/rea/blob/main/docs/desktop-applications.md)
and [model](https://github.com/morluto/rea/blob/main/docs/model-artifacts.md)
guides describe `inspect-desktop-application` and `inspect-model-artifact`.
**VERIFIED:** both return `COMMAND_NOT_FOUND` in the installed 6.7.0 package.
The model guide's advertised formats are GGUF and safetensors, not arbitrary
vendor model payloads. Documentation alone therefore does not establish a
working Adobe model-inspection route.

## Installation metadata relevant to Adaptive

**VERIFIED:** Lightroom's shipped Adaptive Color profile declares
`SupportsSceneReferred=True`, `SupportsOutputReferred=False`, and support for
both normal and high dynamic range. It enables `ProfileGainTableMap` and
`RGBTables`. A rendered SDR TIFF is not interchangeable with a scene-linear
input for this installed profile.

The adjacent `Resources/ModelZoo/ai_look/winml/manifest.json` declares:

| Item | Declared float tensor |
| --- | --- |
| Input | 1 × 5 × 384 × 512 |
| Tone output, separately for SDR and HDR | 196,608 elements |
| Three color outputs, separately for SDR and HDR | 98,304 elements each |
| Exposure, separately for SDR and HDR | One element |

The component is named `secured_file`, with a 5,895,920-byte
`adobelook.data` payload. Only its file identity/header and the surrounding
metadata were examined; no weights or implementation were extracted, executed,
or copied into Strehl. The tensor lengths are **DERIVED** to fit
128 × 96 × 16 tone samples and 32³ × 3 color samples. Their actual arrangement,
five input-channel meanings, preprocessing, and execution contract remain
**UNVERIFIED**.

## The useful next experiment

Adobe's [public explanation](https://blog.adobe.com/en/publish/2024/10/14/the-adobe-adaptive-profile)
describes spatial tone curves, global/subject/sky color tables, separate SDR/HDR
looks, and saving the resulting tables in DNG. The
[DNG 1.7.1 specification](https://helpx.adobe.com/content/dam/help/en/camera-raw/digital-negative/jcr_content/root/content/flex/items/position/position-par/download_section_733958301/download-1/DNG_Spec_1_7_1_0.pdf)
documents LinearRaw, `ProfileGainTableMap`/`ProfileGainTableMap2`, `RGBTables`,
semantic masks, interpolation, and color-space/application requirements.
These are interoperable data formats; they do not provide the model that
predicts the tables.

**ARGUED:** the smallest useful behavioral experiment is to apply Adaptive in
Adobe to an owned copy of a scene-referred DNG, export a separate DNG, and
inspect its tables and masks with a parser written from the public standard.
Keep a default-profile export of the same input and separate SDR/HDR renders.
Compare complete photographs and independently selected edge/flat regions;
hold crop, white balance, exposure, and other controls fixed. Inspect both TIFF
tags and XMP references rather than assuming one storage location. Presence of
a profile name is insufficient evidence that a generated table was saved.

A Strehl float master could be a candidate for a correctly color-described
LinearRaw DNG bridge, but this investigation has **not** implemented or tested
Adobe acceptance of such a bridge. A renamed TIFF is not that bridge. Adobe's
[documented DNG Converter CLI](https://helpx.adobe.com/content/dam/help/en/camera-raw/digital-negative/jcr_content/root/content/flex/items/position/position-par/download_section/download-1/dng_converter_commandline.pdf)
does not document an Adaptive-profile rendering command. No headless Adaptive
API was established here.

Local receipts and reproducible inspection commands are retained under ignored
`outputs/rea-review`: `local-metadata.json`, `lightroom-pe.json`,
`lightroom-managed.json`, `providers.json`, `desktop-command.json`, and
`model-command.json`. This investigation supports a controlled comparison and
possible standards-based interoperability; it does not justify Adobe
equivalence or redistributing Adobe's model/profile assets.
