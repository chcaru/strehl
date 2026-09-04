# `focus-stack` identity-crop full-control preregistration

Frozen before executing this configuration. No subject run is authorized.

## Prior configuration failure

The preregistered `focus-stack-depthmap-chain-off` full witness wrote a
`3584x2560` output from `3392x2262` inputs and was rejected before any pixel
correspondence test. It remains `UNMEASURED`.

This was not a fitted transform. Source and the executable's help define
`--nocrop` as saving the full internal image, including reflected/extrapolated
border data. The loader pads each input for wavelet decomposition and records
the centered original rectangle as `valid_area`; the ordinary save path crops
back to that exact source-derived rectangle when `--nocrop` is absent.

No output pixels were searched for a matching rectangle. The next expected
extent is registered from input dimensions and source control flow:

```text
3392x2262
```

## Separate configuration

This is another explicitly named controlled-merge arm:

```text
focus-stack-identity-crop-depthmap-chain-off
```

Relative to the original frozen invocation:

1. omit `--nocrop`, selecting the comparator's documented normal final crop to
   its propagated `valid_area`;
2. append `--depthmap-chain=off`, selecting the already-declared non-default
   pre-Phase-12.5 merge path.

The configuration neither estimates nor compensates an observed translation,
scale, rotation, or crop. Under source-proven `--no-align`, every input's
`valid_area` is the centered rectangle set by the loader, and the final crop is
that same rectangle.

This cannot rehabilitate either earlier failed configuration and cannot be
described as the current default product. It remains a controlled merge audit.

## Frozen implementation and provenance

```text
binary SHA-256:
  0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D
reported version:
  focus-stack unknown, built May 17 2026 03:01:23
OpenCV:
  4.13.0
auto-noise preset SHA-256:
  860A57DB745776E0C50E3FC190320142FDE2D79AF0F85848A659719C7D2AAC1E
runner:
  controls_identity_crop_depthmap_off.py
runner SHA-256:
  9060C98002F0AFA736C58632F999ABE80CF33F5B79E4E8470D12DEDBA12E4044
```

The binary-to-source Git binding remains incomplete because the executable
reports revision `unknown` and its build directory is unavailable. The
full-size executable control is therefore load-bearing.

## Frozen command options

```text
--no-align
--no-transform
--no-whitebalance
--no-contrast
--input-colorspace=linear-rec2020
--internal-colorspace=linear
--output-colorspace=linear-rec2020
--output-bitdepth=16
--hdr-preserve=off
--threads=6
--depthmap-chain=off
```

Then pass `--output=<fresh-path>` and all 92 byte-identical witness inputs in
registered order. No other option or default is changed.

## Unchanged full-control predicates

Run exactly the `controls.py` witness and verifier:

* `N=92`, `3392x2262x3`, uint16;
* exact registered identity map only;
* output `3392x2262x3`, uint16, Orientation `1`;
* marker, border, and constant-patch error at most `4 DN`;
* at least `0.999` of coordinates within `4 DN`;
* frozen linear-Rec.2020 ICC after metadata-only canonicalization;
* all registered geometry/domain RED plants reject;
* restored identity passes;
* unchanged M8 adapter GREEN/RED/improvement sequence passes.

No threshold, source count, dimension, marker, expected rectangle, or transform
may be adjusted after execution.

## Host gate and stop rule

Immediately before the comparator process require:

```text
five one-second CPU samples
mean CPU <= 35%
available physical memory >= 24 GiB
measurement age <= 10 minutes
threads = 6
```

Any comparator or predicate failure is `UNMEASURED`. Do not decode or run the
registered subject. A PASS would be control admission only, not a quality
result.
