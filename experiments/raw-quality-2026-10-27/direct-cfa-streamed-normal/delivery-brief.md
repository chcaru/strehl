# Final reference-cell RGB delivery preparation

2026-10-27. Source preparation only. Root owns compilation, commissioning and
execution. Cfa-residual owns `delivery.py`, `delivery-notes.md` and the new
`crates/strehl-cli/examples/direct-rgb-develop.rs`; do not edit Cargo.toml or
any existing production/experiment source. Native band/normal/solver sources
are frozen while root runs their controls.

The eventual full observation needs actual reference-cell-integrated RGB, not
a crop of latent interpolation coefficients and not a remosaic/MHC round trip.
Prepare `delivery.py` to consume a saved contiguous f32 global camera-RGB latent
field plus its declared integer reference origin and retained metadata. Use the
unchanged frozen integrated measurement kernel on the complete native delivery
crop(68,46,6896,4596), map identity minus the global reference origin. Three
explicit output-channel selectors(allR/allG/allB) can call the existing
diagnostic_channel_map API for this final RGB consumer; record that meaning
honestly. It is not original sensor phase selection at this stage. Stream
bounded rectangles, never per-source RGB images. Save complete signed f32
camera-DN RGB with shape/units/hash; no black pedestal is added. Independently
commission small output against the frozen CPU `integrate_reference` before
using it for a photograph. Retain the unit-square sensor-response assumption.

Prepare a small native renderer example for that final RGB file. Reuse
`image_out::develop_pixel` and `write_rgb16_described` from the actual product
module, following the existing weevil-batch-develop example's module inclusion
and `make_dev`, but never call its MHC writer. Input is signed black-subtracted
camera RGB DN; apply the exact frozen as-shot WB and white-minus-black scale,
then the existing camera matrix/highlight handling, pinned tone, gamut and
sRGB path. Preserve negative fitted values until the existing development
operations handle them; do not add a new pre-matrix clamp. Use receipt bit
patterns for WB/XYZ/tone and fixed exposure1, with no image-dependent retone.
Write a full RGB16+ICC TIFF master, source/metadata/output hashes and an explicit
no-demosaic/no-remosaic receipt. Keep the signed f32 reconstruction as a separate
research master, not mislabeled sRGB. A later viewer worker can make the complete
JPEG and fixed384-pixel witnesses from this master using the established ICC.

Require fresh outputs, exact input byte count, finite values, dimensions and
supported schema. Do not perform a build, RAW decode, fit, delivery or image
render. Root read the native `image_out.rs` functions and the existing exporter:
the intended bridge reuses that actual display transform rather than ports its
color/highlight/gamut arithmetic to an uncommissioned Python approximation.
This preparation does not release a full fit or claim better photographic quality.
