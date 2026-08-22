# experiments/

Measurement harnesses. Each is a standalone crate with its own `[workspace]`
key, so the parent workspace ignores it and a root `cargo build` never
compiles it.

These are not products and are not held to the standard of `crates/`. They
exist so that the numbers in `docs/research/M*.md` can be reproduced rather
than taken on trust, which is project rule 8.

| Crate | Produces |
| --- | --- |
| `m2-fpn` | `docs/research/M4-fpn-measured.md` |
| `m3-drift` | `docs/research/M3-alignment-measured.md` |

## m2-fpn

```
cd experiments/m2-fpn
cargo run --release -- --synthetic                # estimator control, run this first
cargo run --release -- <root> --map               # folder -> ISO/exposure from EXIF
cargo run --release -- <root> [folder ...]        # the measurement
```

`<root>` is a directory of subdirectories of dark ARW files, one subdirectory
per capture setting. The first 2 frames of each are discarded as stabilisation
shots. ISO and exposure are discovered from EXIF, never assumed, and a folder
whose frames disagree is reported rather than averaged.

`--synthetic` plants known `sigma_FPN` and `sigma_temporal` into generated
frames and checks that the bias-corrected estimator recovers them — including
the case where the planted FPN is **zero**, where the uncorrected estimator
reports a fictitious floor of 1.79 DN. **Run it before believing any number the
other mode prints.**

The measurement runs a sanity gate (is this really a dark frame?), then per CFA
plane and over the active area only: the sigma-vs-N curve with disjoint
subsets, the same curve with a disjoint master bias subtracted, sigma_temporal
and bias-corrected sigma_FPN separately, split-half bias subtraction, a hot
pixel census at both robust and absolute thresholds, and black level and read
noise against ISO.

The crate keeps *spatial* and *temporal* sigma separately named throughout. A
prior claim in this project was retracted for confusing the two.

## m3-drift

```
cd experiments/m3-drift
cargo run --release -- --synthetic <dir-of-ARW>   # estimator control, run this first
cargo run --release -- <dir-of-ARW> [limit]       # the measurement
```

`--synthetic` warps one real frame by four known similarity transforms and
re-estimates them. It is the negative control: it bounds what the estimator can
resolve, and every effect claimed in M3 is larger than that bound. It also
checks `compose()` against a closed form. **Run it before believing any number
the other mode prints.**

The measurement aligns every frame independently against frame 0, reports the
fitted similarity per frame, compares 4-, 6- and 12-parameter motion models on
the same tiles, tests whether drift is linear or quadratic in frame index,
locates the scale centre, and composes the adjacent-pair chain to measure what
chaining costs.
