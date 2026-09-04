# `focus-stack` depthmap-off full-control preregistration

Frozen before the first full-size execution of this configuration. No subject
run is authorized here.

## Why this is a separate arm

The selected binary's default `--depthmap-chain=auto` path crashed the mandatory
full `N=92`, `3392x2262` byte-identical witness. Source audit shows that
`--depthmap-chain=off` still writes a merged output, but it does **not** merely
suppress a depth-map file. It restores the pre-Phase-12.5 compose path and
therefore disables confidence-map consumers used by the selected default
merge.

Accordingly this is a newly named, non-default controlled-merge arm:

```text
focus-stack-depthmap-chain-off
```

It cannot rehabilitate or replace the failed default arm. Any later admissible
subject result would describe this exact arm only. This remains a controlled
merge audit, not a default-settings product benchmark.

## Prior diagnostic used only to justify this attempt

The preregistered small `I08-S` diagnostic completed with return code zero and
wrote an output when the sole extra option was:

```text
--depthmap-chain=off
```

That reduced diagnostic is not admission evidence. It only establishes that a
full-control attempt is technically meaningful.

## Frozen executable and external preset

```text
binary:
  C:\dev\macro\focus-stack\dist\focus-stack.exe
SHA-256:
  0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D
reported version:
  focus-stack unknown, built May 17 2026 03:01:23
OpenCV:
  4.13.0
auto noise preset:
  C:\dev\macro\presets\noise_profile.json
preset SHA-256:
  860A57DB745776E0C50E3FC190320142FDE2D79AF0F85848A659719C7D2AAC1E
control runner:
  controls_depthmap_off.py
runner SHA-256:
  8D6240483948E6B0CAE2733FD292FDE0A28F9A336180E69DB2CF9ADD382963B5
```

The executable embeds no Git revision and `dist/` is ignored. The source audit
therefore cannot cryptographically bind the executable to a commit. Source
evidence is corroborative; this full executable control remains load-bearing.

## Sole invocation delta

The invocation remains exactly the one in `PREREGISTRATION.md`, with one option
appended before `--output`:

```text
--depthmap-chain=off
```

No other merge, denoise, compose, colour, geometry, thread, or output option is
changed. The runner must reject any drift in the original option list, binary
hash, or auto-noise preset hash.

## Mandatory control and predicates

Run the unchanged full witness from `controls.py`:

* `N=92`;
* `3392x2262x3`, uint16;
* 92 byte-identical hard links;
* the same aperiodic coordinate code, border codes, asymmetric markers, and
  constant RGB patches;
* exact identity-map verification only;
* marker, border, and patch tolerance `4 DN`;
* at least `0.999` of output coordinates within `4 DN`;
* exact dimensions, Orientation `1`, and frozen linear-Rec.2020 ICC after
  metadata-only canonicalization;
* every registered geometry/domain RED plant rejects;
* restored identity passes;
* unchanged M8 adapter null, two-sided plant, and improvement all pass.

Do not change the input, source count, dimensions, or thresholds. A successful
reduced run cannot substitute.

## Host gate and stop rule

Immediately before the comparator process, measure five one-second total-CPU
samples. Run only if:

```text
mean CPU <= 35%
available physical memory >= 24 GiB
measurement age <= 10 minutes
threads = 6
```

If the comparator fails, writes no output, or any unchanged admission predicate
fails, stop at `UNMEASURED`. Do not decode or run `tilted-sw10-cpl`.

Even a PASS would admit only a future run of this separate non-default arm. It
would not be a detail-quality result and would not license opening a holdout.
