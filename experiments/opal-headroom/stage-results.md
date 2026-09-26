# Opal writer attribution: pin and rolloff branches are inactive

Root executed the independently reviewed observer under the fresh shared
`real-source-contributions/build-1` binary. **MEASURED: no pixel in the complete
30,754,176-pixel opal image activates pin protection, changes under its clip,
or changes under sensor chroma rolloff.** Those mechanisms do not explain this
delivered opal. The pin-bypass/provenance branch is closed for this observation.

The three generated controls passed, including the independently chosen
ceiling-equality versus changed-pixel distinction and unequal-ceiling CFA
phase cases. The actual MHC fixture demonstrates that interpolation-created
pinning is possible; the real image demonstrates that it does not occur here.
Do not turn a positive synthetic possibility into a photographic attribution.

VERIFIED: observer-on/off complete TIFF bytes are identical. Every observed
Current and Shoulder RGB16 value, hashed over the whole image, matches its
previously executed full factorial master. Both frozen target arrays also
match. Resolved development and cached merged planes are unchanged. Thus this
is the actual writer's activity, not a separately normalized proxy. The run
reads no RAW files and takes6.547s as one instrumented job, not a speed benchmark.

MEASURED: after tone/exposure,102,015 pixels have a channel above1, and310
have luminance at least1. The existing gamut map turns310 pixels exactly white.
In the fixed384x384 reflection target,5,945 pixels have a channel above1 and71
become exactly white. These are display-stage losses; they are not sensor
saturation counts. The fixed shoulder eliminates those exact-white results,
yet the independent whole/native photographic comparison in
`factorial-results.md` found no useful recovery of reflection gradation.
This is the registered counterexample to treating fewer white pixels as
improved image quality. No shoulder tuning follows.

The colour-control target has no pins, clipping or rolloff changes and no
shoulder changes. Its521 above-one channel values and seven negative-component
pixels are mapped by the current gamut stage. This establishes activity, not
damage or a reason to alter colour rendering. Neither natural target is a
calibrated noise control.

Commands run with Python312, `-I -B -X faulthandler`:

```text
experiments/real-source-contributions/run.py build --out experiments/real-source-contributions/build-1
experiments/opal-headroom/stage-run.py controls --build experiments/real-source-contributions/build-1 --out experiments/opal-headroom/stage-controls-1
experiments/opal-headroom/stage-run.py run --build experiments/real-source-contributions/build-1 --controls experiments/opal-headroom/stage-controls-1 --cache-run experiments/opal-headroom/cache-1 --factorial experiments/opal-headroom/replay-1 --out experiments/opal-headroom/stage-1
```

The fresh compilation includes strehl-core and strehl-cli. Exact source,
executable, invocation and input bindings plus all target f32 stages remain
in the named directories. No default or photograph is changed by the observer.
This result does not establish original-source clipping across155 captures,
physical reflectance, or that all broad spill was captured rather than merged.
It removes two specific renderer mechanisms from the next implementation queue.
