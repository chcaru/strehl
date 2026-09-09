# Current native RAW pipeline costs

MEASURED,2026-09-09. The per-frame synthetic noise probe consumes51.7-52.0% of completed render wall time on the fixed first eight112MSDCF RAWs at native7032x4688 output. Real gather is22.4-23.3%; pyramid addition is7.1%. These costs select a small exact parallel probe-fill implementation next. No speedup or photographic-quality claim is made by this profile.

All five off/on/placebo/on/off full TIFFs and decoded RGB16 pixel payloads are byte-identical. Four tiny generated consumers also preserve exact CFA/TIFF bytes, place a requested75ms delay in decode, and reject independent overlapping/misattributed saved intervals. The placebo visits actual phases without clock durations.

Actual commands, all successful:

- Python312 -I -B experiments/native-pyramid-profile/build.py: release compile, including a real Compiling strehl-cli line; source6f425cc3.
- Python312 -I -B experiments/native-pyramid-profile/run-controls.py: four tiny consumers, six pairs of actual equal outputs; source33c1a03f.
- Python312 -I -S -B experiments/native-pyramid-profile/independent-controls.py --output ABS/independent-controls-1.json: independent saved controls and two rejecting faults.
- Python312 -I -B experiments/native-pyramid-profile/run-native.py: one direct alignment and five completed native renders; source90fbbb3b. Exact executable arguments/environment are retained in native/*-invocation.json.

Completed render times in order:9.859,9.453,9.281,9.359,9.312 seconds. Standalone alignment:1.297seconds, separate from cached-map render cost. This warmed eight-frame development prefix does not establish deep-stack speed, alignment quality, a competitive baseline or SOTA. The combined probe includes fill, synthetic gather and other work; fill cost alone was not measured. See native-interpretation.md for the independent choice-point analysis and full phase/residual table. Original capture files were read only.

Retained large native TIFFs and executables are bound by recorded SHA256 and remain local; compact logs, receipts, tiny payloads, source and commands are versioned. No SYNTHESIS facts are folded.
