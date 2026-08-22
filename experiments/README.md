# experiments/

Measurement harnesses. Each is a standalone crate with its own `[workspace]`
key, so the parent workspace ignores it and a root `cargo build` never
compiles it.

These are not products and are not held to the standard of `crates/`. They
exist so that the numbers in `docs/research/M*.md` can be reproduced rather
than taken on trust, which is project rule 8.

| Crate | Produces |
| --- | --- |
| `m3-drift` | `docs/research/M3-alignment-measured.md` |

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
