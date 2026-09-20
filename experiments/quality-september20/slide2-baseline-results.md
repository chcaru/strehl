# Complete second calibration slide baseline

**MEASURED baseline, no improvement claim.** Root executed
`python -I -B -X faulthandler experiments/quality-september20/slide2-baseline.py`.
The retained renderer placed and consumed all 299 original RAW captures and
wrote a complete 6476 x 4316 RGB16 image. The common crop begins at native
(278,186); reference index is149. Original file contents and metadata matched
before and after. The executable is the held historical build, not a claim
about the currently edited source tree.

Alignment and rendering child wall times were74.359 and91.640 seconds, with
eight configured threads/workers. Job committed peaks were10,196,553,728 and
3,219,275,776 bytes. Both exited cleanly. These single-run costs exclude parent
input hashing and PNG conversion and are not comparative speed benchmarks.
The alignment's endpoint/cycle diagnostics do not measure per-frame truth.

Root inspected the complete overview. Fine lettering, bars, dots and radial
targets provide useful witnesses; source detail retention and absolute colour
accuracy remain unestablished. The next source comparison uses matched product
development before assigning a loss to the stacker.

[Complete RGB16 master](slide2-baseline-1/slide2.tiff),
[full native PNG](slide2-baseline-1/slide2-full.png), and
[complete-field overview](slide2-baseline-1/slide2-overview-only.png).
The overview was shown to the owner as a baseline only.

Decoded RGB16 pixel SHA256:
`e899a56b58bc928b0905a15271b01d684ada6842ddeedef4f18422a39a2f329c`.
Exact executable, map, source bindings, command, output hashes and limits are
retained in `slide2-baseline-1/invocation.json` and `completion.json`.
