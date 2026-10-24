# Application recordings

Recorded from the released **Strehl 0.1.0-alpha.6** Windows application on
2026-10-23 using FFmpeg's Windows Graphics Capture input. These are recordings
of the actual rendered window, driven through Strehl's local control interface.
They are not screenshot slideshows or mockups. No animation frames were
generated or interpolated.

The photographs belong to the repository owner:

- **Insect:** the 299-frame Sony ARW beetle bracket used in the previous
  application recordings.
- **Garnet:** a 183-frame Sony ARW mineral bracket, showing linked exploration
  on a second subject.

The private RAW brackets and uncut capture masters are not distributed.

## Recordings

The three full-workspace GIFs and all MP4s are **1600 × 1000**. The garnet GIF
uses a **1160 × 420** crop around the preview area, without upscaling; its MP4
shows the full workspace. GIFs run at **25 fps** with uniform 40 ms frames;
the accompanying **30 fps MP4s** retain more photographic color detail and
animation frames. Every segment plays at its original recorded speed.

| Recording | GIF | MP4 | Content |
| --- | --- | --- | --- |
| Stacking | [24.92 s · 623 frames](stacking.gif) | [30 fps](stacking.mp4) | Active registration, first detail bands, accumulating contributions, reconstruction, and the finished color photograph. |
| Timeline exploration | [15.24 s · 381 frames](timeline-scrubbing.gif) | [30 fps](timeline-scrubbing.mp4) | Source/final comparison, changing admitted regions, linked zoom, and return to the completed photograph. |
| Regional editing | [11.64 s · 291 frames](editing.gif) | [30 fps](editing.mp4) | An elliptical region, local light and color, undo/redo, Natural Adaptive, zoom, and a saved edit version. |
| Garnet exploration | [12.72 s · 318 frames](mineral-exploration.gif) | [30 fps](mineral-exploration.mp4) | Contribution regions on source and final images, panning and zooming, and inspecting another part of the focus sweep. |

**Stacking is condensed:** its five excerpts retain source-time windows
12–18 s, 43–47 s, 85–89 s, 129–132 s, and 156–164 s from a 195.233-second
capture. Cuts omit waits and repetitive processing; motion within each excerpt
is unchanged. The three exploration/editing recordings are continuous, with
only 0.2 seconds removed from their beginnings.

These clips are SDR documentation media. They do not reproduce HDR display
headroom and are not benchmarks of processing speed, interaction latency, or
photographic accuracy.

## Capture and encoding

The application was built from source commit
`4b818b63b713e4c5c14c1e65d4a5a9c9662ff7bb`.
The official Windows executable's SHA-256 is
`f502a787f9c1e5645753a390e311fc2b53bd87dfde4595a2b026dc4d30c20ac8`.

Capture masters use 30 fps H.264 with 4:4:4 chroma. GIF encoding uses a shared
palette per recording, ordered dithering, and partial-frame updates. The MP4s
use H.264, CRF 15, browser-compatible 4:2:0 chroma, and explicit color tags.
There is no artificial frame interpolation or playback acceleration.

Decoded frame cadence, changing image content, and contact sheets were checked
for every recording. The GIFs contain respectively 570, 341, 223, and 279
distinct decoded frames; brief stationary moments are retained. No black-image
flash candidates were found in the central preview region.
