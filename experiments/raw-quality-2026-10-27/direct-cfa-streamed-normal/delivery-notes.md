# Final reference-cell RGB and native development

2026-10-27. **SOURCE-PREPARED; not yet commissioned by the author.** This is the
final-output bridge for a possible complete original-CFA reconstruction. It
does not establish reconstruction quality or change the retained flat/noise
failure. No solver, RAW reader, bound measurement or normal source was changed.

## Reference-cell integration

`delivery.py` imports the frozen `measurement-gpu.py`, SHA256
`8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84`.
Its public small-control interface is:

```python
integrate_rgb(torch, latent_cuda_f32_HWC, reference_origin_xy, output_xywh,
              device_limit_bytes=8 << 30)  # returns CUDA f32 HWC
```

`ReferenceDelivery(torch,field_hw,reference_origin_xy,device_limit_bytes)`
exposes `.integrate(latent,output_xywh)` and `.metadata()` for retained runtime
evidence. The source-to-latent map is identity minus the declared integer
global reference origin. Three explicit selectors `(R,R,R,R)`, `(G,G,G,G)` and
`(B,B,B,B)` evaluate every final RGB channel at every reference pixel cell.
They intentionally replace Bayer channel selection **only at final delivery**;
they do not construct RGB for any source photograph. The frozen9-node uniform
unit-square sensor footprint and normalized Lanczos3 row remain unchanged.

The CLI enforces the complete weevil delivery crop `(68,46,6896,4596)` and
streams at most1,048,576 reference cells per rectangle. No second crop, remosaic,
MHC or black pedestal is introduced. Signed values and headroom remain in
`camera-rgb-dn.f32le`, interleaved row-major R,G,B. The full final image is a
permitted single output field, not an aligned-source volume.

The independent small reference can use global origin `(-8,-8)` and output
`(0,0,w,h)`, matching CPU `integrate_reference` centers offset by8. Its CPU
delivery helper builds GL weights from f32 axis weights and a f32 outer product;
the frozen GPU measurement builds double products then casts to f32. Combined
with sparse/coalescing/sine/reduction differences this requires numerical
commissioning, not a bit-identity claim. The kernel/geometry itself is frozen.

Run contract (root only):

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/direct-cfa-streamed-normal/delivery.py --config <config.json>
```

The strict configuration contains only `schema:1`, `latent`, `latent_metadata`
and `out_dir`. Both inputs are exact `{path,sha256,bytes}` bindings. Latent
metadata has schema `strehl-direct-cfa-latent-v1`, `field_hw`, integer
`reference_origin_xy`, `channels:["R","G","B"]`,
`units:"black-subtracted-camera-DN"`, `dtype:"<f4"`, and matching `latent_sha256`.
Additional retained provenance/numerical-status fields are preserved. Exact
byte count, finiteness, fresh output and source/input hashes/metadata before and
after are required. The CLI sets four workers, f32/no autocast/TF32 and8GiB
Torch budget; root supplies the process bound. The completion receipt is
`COMPLETE_REFERENCE_CELL_CAMERA_RGB`, with full shape/units/hash, all rectangles,
runtime bindings, signed ranges and explicit no-quality/no-admission fields.

## Native viewing master

New auto-discovered example:
`crates/strehl-cli/examples/direct-rgb-develop.rs`. No Cargo.toml or existing
native source was changed. It includes actual `image_out.rs` as the prior
exporter does, then calls only `develop_pixel` and `write_rgb16_described`.

The signed camera-DN triple is multiplied by exact as-shot WB and divided by
`white-black` in f32, without a new `max(0)` or black subtraction. The native
`camera_to_srgb(...).with_saturation(levels,WB,1)` performs the existing
highlight handling and camera matrix; the pinned tone, gamut, sRGB transfer
and final quantization follow in `develop_pixel`. Exposure is exactly1. No
output-dependent tone measurement is called. The existing writer supplies its
ordinary sRGB ICC, description and print-resolution tags. Its Software field
honestly names this diagnostic example.

Root build/invocation contract:

```text
cargo build --locked --release -p strehl-cli --example direct-rgb-develop
<frozen-direct-rgb-develop.exe> <renderer-config.json>
```

The strict renderer configuration has `schema:1`, `camera_rgb`,
`delivery_receipt`, `development_receipt`, `out_dir`, and
`expected_executable_sha256`. Every file binding is `{path,sha256,bytes}`.
The development receipt has exactly:

```text
schema: 1
levels_bits: [black_u32_bits, white_u32_bits]
wb_bits: [R_u32_bits, G_u32_bits, B_u32_bits]
xyz_to_cam_bits: [[u32_bits;3];3]
tone_bits: [black_u32_bits, white_u32_bits, contrast_u32_bits]
exposure_bits: 1065353216
source_bindings: [{path,sha256,bytes}, ...]
```

Root must derive these from the held native sensor metadata and exact held
linear-master DisplayBaseline, not the old rounded comparator tone. The source
binding list must be nonempty and all its hashes/metadata are checked before
and after. The supplied WB must be positive finite and green-normalized to
exactly1; matrix/tone/levels must be finite and valid. The renderer validates
the delivery receipt's quantity/channel order, extent, zero demosaic/remosaic
counts and file binding. Small complete commissioning panels are permitted;
it records their actual dimensions without calling them a weevil photograph.

Outputs are `rgb16-master.tiff` and `receipt.json`, status
`COMPLETE_DIRECT_RGB_NATIVE_DEVELOPMENT`. The TIFF is decoded back and its
RGB16 pixels must exactly equal the native producing buffer; ICC is required.
Full file/pixel/ICC hashes, exact development metadata and negative input count
are recorded. The signed input is retained as the separate camera-linear
research master and is not mislabeled sRGB. This bridge does not add a second
scene-linear sRGB master or silently treat latent coefficients as integrated
camera RGB.

## Source verification and current limit

Frozen `delivery.py` SHA256:
`c59c7f6a5f218f8809de43e4315ff88f5c5cd7a124826d016da3b75563b83b3b`.
Frozen new Rust example SHA256:
`c528ffec8b0eb2fb27b9070da95cacee8ab822a33c7ab81ea2e39f57ab98635e`.

Author performed standard-library AST parsing and Rust formatting/parser with
`--config skip_children=true`; the latter did not touch included native files.
No build, GPU integration, image rendering, RAW decoding or numerical
commissioning was executed by the author. Root and independent controls must
commission small integration and actual native development before complete
photographic use. No result here is an image-quality claim.
