# Native observation scope amendment 3

2026-09-09. SOURCE PREPARATION ONLY. This narrows two concrete interfaces before
the producer patch is applied or any scientific input is read.

## Actual resolved channel map

The existing effective t_site is available only after Optics::compose inside
align_cmd::warp_frame_in_place_fullres. Permit one test-and-feature-gated
read-only callback at that location. It records the already-resolved transform,
site offset, working gain and actual capture/profile context, four sites per
real warp and four per probe warp. It must not perform another profile lookup,
change a transform or arithmetic, add a per-pixel callback, or alter the existing
default full-resolution gather. The hook is inert without an active observer.
This explicitly extends amendment 1's unapplied source scope to align_cmd.rs.

## Native output witness

The charter's native writer witness remains required. For each of the fixed
nine paired invocations, retain both finished route outputs as four-plane
little-endian f32 payloads AND call the existing write_merged with those same
finished planes. There are eighteen f32 payloads and eighteen native TIFFs,
with no additional input decode, probe, merge fold or alternate writer.

Use camera-native linear output, demosaic=true, Exposure::None, restore=None,
and the actual recorded levels and white balance. Record the exact enum,
writer/environment/configuration values and output dimensions before execution.
No display judgement or photographic metric is derived from these files.

Require exact f32 and whole-TIFF byte identity for the fixed paper-five and
dark-prefix-two off/on/placebo and feature-off witnesses. The f32 check remains
necessary because output quantization could conceal a changed merge value.
No no-map-versus-placed equality requirement is introduced, and no whole
twenty-two-dark output-neutrality claim follows from the two-frame witness.

The producer must update its concrete call table, output identities, retained
byte ceiling and existing-writer ownership flow. The independent protocol and
checker design must agree. This amendment grants source preparation only:
application, build, controls, decoding and execution still require root's finite
reviewed release. The eighteen writer calls are additional bounded work and
must be priced rather than charged as zero.
