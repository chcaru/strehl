# Strehl's native extended-linear surface patch

This directory contains **egui-wgpu 0.33.3**, from the crates.io package published
by [emilk/egui](https://github.com/emilk/egui), upstream Git revision
`44cdd653e2317d300fb8a6c9c36b03f23991e803`. The original upstream
`MIT OR Apache-2.0` licensing is unchanged. Both license texts are included here.
Strehl's modifications use the same dual license.

The root Cargo patch selects this exact local package. This avoids a broad
egui/wgpu upgrade for one surface-format capability. `strehl.patch` records the
source difference from the published 0.33.3 package.

## Changes

- An opt-in `WgpuConfiguration::extended_linear_surface` allows `Rgba16Float`
  only on DX12 or Metal, when the surface advertises it and the adapter reports
  render-attachment and blending support. The default remains the upstream
  SDR behavior.
- Before handing the initial render state to the app, the native painter checks
  configuring the float surface under validation/internal error scopes. A
  rejected configuration selects the original SDR renderer. Device loss or
  out-of-memory errors remain ordinary application startup failures.
- The float-target UI shader decodes premultiplied gamma colors correctly:
  unpremultiply, decode sRGB, multiply by alpha and the configured SDR white.
  The existing SDR shaders remain unchanged.
- Native float screenshots read eight bytes per pixel, decode the OS scanout
  values to f32, and produce an explicitly SDR, hue-preserving highlight proxy.
  This is a viewable screenshot, not an HDR image export.
  When HDR is inactive, float screenshots preserve the SDR transfer and all
  opaque 8-bit sRGB codes without a highlight shoulder.
- The normalized package's license include paths point to the included local
  license files.

The application's dedicated photograph callback, Windows monitor query, and
macOS EDR setup live in `crates/strehl-ui/src/hdr-display*`. The photo working
texture is **RGBA32Float**; only the platform's final scanout surface is
RGBA16Float. No f16 image or intermediate processing buffer is introduced.

## Platform contracts

Windows DX12 float swapchains use linear scRGB, where 1.0 represents 80 nits.
The app queries the window's actual output and enables HDR photographs only when
DXGI reports the active PQ/BT.2020 HDR output and usable SDR-white/luminance
information. On macOS the app sets its own CAMetalLayer to extended-linear sRGB
and uses AppKit's current EDR headroom, relative to SDR white. Moving displays
or changing OS HDR state is polled outside the Windows paint path.

Other backends retain SDR: a float texture format alone is not evidence of a
negotiated HDR color space. No system display setting is changed.

Primary platform references:

- [Microsoft: High dynamic range](https://learn.microsoft.com/en-us/windows/win32/direct3darticles/high-dynamic-range)
- [Apple: Performing your own tone mapping](https://developer.apple.com/documentation/metal/performing-your-own-tone-mapping)
- [Apple: Extended dynamic range layer content](https://developer.apple.com/documentation/quartzcore/cametallayer/wantsextendeddynamicrangecontent)

## Verification

The application includes an opt-in GPU readback control:

```text
cargo test -p strehl-ui native_float_pixels_ui_white_and_sdr_negative_control -- --ignored --nocapture
```

It exercises the production photograph shader, the patched egui renderer,
colored above-white values, the clipping of an SDR target, SDR-white scaling,
and premultiplied translucent UI over a known background. Independent review
uses different colors, white levels, and alpha values. Passing these controls
establishes framebuffer arithmetic; it does not substitute for inspecting an
actual HDR monitor.

Release source and relinking kits must include this directory and both licenses.
