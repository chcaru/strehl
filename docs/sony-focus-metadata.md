# Sony focus metadata inspection

Strehl can inspect the A7C II's hidden RAW focus records without decoding the photograph. The native reader supports the observed ILCE-7CM2 firmware 2.00 and 2.01 layout. Actual RAW witnesses currently cover firmware 2.00; the supplied 2.01 firmware provides the serializer evidence. Other models, versions, and layouts are reported explicitly.

## Explore inside Strehl

Select a capture on the desktop timeline and open **Camera metadata**. The native
panel reads the imported bracket once, then follows the current capture from its
cache. Its AF grid exposes exact cell bits and flags; focus position, scalar A,
scalar B and a selected AF cell can be plotted through capture order. Clicking a
chart point selects the corresponding capture. Missing or incompatible metadata
breaks the line instead of borrowing another frame's values.

Optical curves retain all 16 shading, 16 distortion and 32 color-fringing samples,
with stored sample index and raw value axes. **Full capture details** stays inside
Strehl; **Refresh bracket metadata** rereads source identities and metadata. The
fixed signed AF color scale is -32768 to 32767. This two's-complement i16 display
interpretation does not establish producer arithmetic, depth, physical focus
steps, complete flag meanings or exposure-time freshness. Neither optical curves
nor settings enable a correction.

## Inspect a bracket

```powershell
./target/release/strehl.exe focus inspect "path/to/bracket" --records --out "focus.json"
```

For an optional standalone browser report, add `--html "focus.html"`. The HTML export is self-contained and works offline. It provides the stored 33 by 23 field, exact cell bits and flags, and scalar progression. `--html` includes all grid records; JSON alone includes summaries unless `--records` is supplied. A single ARW path and `--limit N` are also accepted. Output paths must be new files with existing parent directories.

The report preserves filename order and distinguishes present, absent, unsupported, malformed, and unreadable metadata. Comparisons break at changes in camera model, firmware, lens, focal length, aperture, or grid geometry, and at missing metadata. It reports repeated values, direction changes, raw sequence changes, and unusually large differences relative to that segment's median. These observations can reveal an unexpected capture progression; they do not by themselves prove a missing exposure or a physical focus gap.

`probe` now includes a concise focus metadata summary. Both normal stack backends print a nonfatal bracket summary before decoding images. Set `$env:STREHL_SONY_FOCUS_AUDIT = "0"` to disable that optional stack scan; remove the variable to restore it. This setting does not disable the explicit inspector.

## Optical settings and tables

Add `--optical` to the inspector to include exact optical header facts:

```powershell
./target/release/strehl.exe focus inspect "path/to/bracket" --optical --records --out "optical.json"
```

Each frame has a separate optical status, so optical metadata can be inspected even when the hidden focus field is absent or unsupported. The offline viewer shows the selected frame's optical facts. JSON retains signed shading, chromatic-aberration and distortion samples, their prefixes, setting integers, original bytes, tag identifiers, TIFF types, counts and offsets. MakerNote settings remain separate from RAW-directory settings. Unknown setting codes and a nonzero table beside a zero setting are preserved.

The native `strehl_raw::sony_optical::{read, read_from_reader}` API reads these optional facts without decoding pixels. It preserves exposure rationals, identity fields, header geometry and header levels without interpreting them as calibrated correction laws or replacing the decoder's working values. The optical reader does not require the hidden focus payload. Its fixed conformance population covers 598 files; this establishes exact representation on those files, not optical calibration or improved stacked photographs. See the [public conformance summary](research/metadata-continuation-2026-10-25.md#metadata-reader).

`--optical` adds an optional per-frame `optical` object with its own versioned schema to the existing focus-audit JSON. Without the flag, the existing report fields and automatic stack preflight are unchanged. No table is activated as a correction by this command.

## What the data means

**VERIFIED format:** hidden tag `0x2045` contains an 8192-byte substituted payload. Its decoded sections carry image/crop geometry, 759 four-byte value/flag records, three sequence fields, and finer scalar fields. The reader preserves original payload bytes and unknown tail bytes; JSON exports SHA-256 fingerprints and file size/mtime for provenance.

**DERIVED from firmware:** the field is associated with Sony's defocus processing. A static coordinate table enumerates 33 columns by 23 rows in row-major order, with sample coordinates `(32 + 18*column, 16 + 18*row)` on a 640 by 428 reference plane. Firmware scales its origin and extent into the stored image dimensions. Sony specifies a maximum of 759 phase-detection AF points for stills. The count and native defocus path support identifying this as the sparse AF defocus field.

**VERIFIED partial status packing, firmware 2.01:** decoded flag pair `(0,0)` matches a strict camera-side status check. `(2,128)` combines source states that another camera-side check treats differently; `(3,129)` fails both inspected checks. The RAW records also omit auxiliary fields used when the camera accepts measurements. The stored values and flags therefore cannot reproduce its full acceptance decision. These status semantics have not been verified in the firmware 2.00 used by the captured RAWs.

**UNVERIFIED:** calibrated distance units, complete flag meanings, exact correspondence between each sample and image content, and exposure-time freshness. The firmware can independently fall back to earlier AF and lens buffers. All three sequence fields are copied from the requested capture key, including on those fallback paths; they do not identify the selected source buffers. Matching sequence fields or a changed payload cannot establish that every record was freshly measured for that exposure. Signed 16-bit values in the viewer are an explicit display interpretation. The field must not be treated as a dense metric depth map.

Firmware arithmetic associates scalar B with current lens state and scalar A with a focus-error-corrected estimate. The Q16 conversion is verified; interpreting the unit as meters remains a derivation requiring independent distance calibration. These fields are not motor counters.

The finer scalar B distinguishes all 299 frames in each of two tested brackets, where the coarse focus code distinguishes only 9 and 5. It is useful for progression diagnostics. Tests against independent ruler focus measurements do not establish a transferable physical focus axis or an image-quality improvement over a fitted frame-index axis.

**MEASURED, conditional grid test:** requiring `(0,0)` at every contributing interpolation corner left local focus estimates at only 8 of 72 sites across two retained scenes, including 7 of 34 held-out sites. These sparse estimates were close to an independently fitted image-plane model, but one slide site disagreed sharply with both direct image-response references. Without the status condition, stable but badly misplaced focus estimates occurred. Neither experiment establishes a general focus window, metric depth, or an image-quality improvement; applying the 2.01 status interpretation to the 2.00 captures remains unverified.

**MEASURED, scattered-cell continuation:** using individual strict readings at their actual aligned positions recovered focus-related scene structure without requiring four simultaneous corners. On the two retained 299-frame targets, the metadata front differed from the image-only front by 2.709/1.337 frames at held sites; temporal shuffles were far worse. The slide passed the fixed metadata-consistency screen and the chip failed it. Against both direct image-response references, neither metadata front improved on the existing image-only fit. Most held sites were outside the metadata calibration hull. This establishes conditional focus information, not a better merge or reliable exposure timing.

## Native API

`strehl_raw::sony_focus::read(path)` and `read_from_reader(reader)` return optional metadata or a classified I/O, unsupported-format, or malformed-data error. The bounded reader is independent of RAW pixel decoding, caps directory sizes and total reads, resolves stored offsets, and checks the declared geometry against independent TIFF geometry when available. It preserves the original flag bytes and sequence disagreements for the caller to inspect; it does not apply an automatic reliability mask.

The automatic stack consumer only reports metadata. It does not reorder frames, discard samples, change geometry, or change the noise model. An image consumer needs a controlled comparison against the current image-only method and direct output evidence. Unknown version-specific status semantics, freshness, spatial correspondence, and calibration must remain explicit limits; an empirical benefit on tested captures would not establish a universal depth contract.

## Evidence

The [public research status](research/metadata-continuation-2026-10-25.md)
separates reader conformance from the unsuccessful AF, optical-table and ordinary
coordinate photographic trials. No metadata-driven improvement to the core
stacked photograph has been demonstrated by those trials.

- [Metadata interpretation and consumer limits](research/metadata-continuation-2026-10-25.md#metadata-reader)
- [Sony ILCE-7CM2 specifications](https://www.sony.com/electronics/support/e-mount-body-ilce-7cm2/specifications)
