# Explicit-track geometry implementation

Base: c149e52834fc1c86c2af0fe022713c39fa25f33c. Allocation:
multi-stack-2026-10-28-geometry-core. Source prepared; root schedules execution.
This note makes no numerical or photographic claim.

## APIs

- `solve_global_in_tracks(edges, n, options, reference, tracks)` validates a
  complete nonoverlapping partition into ordered tracks and solves only the
  reference's measured component. The numerical gauge stays the smallest
  admitted index, matching the existing API; callers explicitly rebase.
- `refine_pair_observed(reference, moving, spots, config, seed, observer)`
  delegates existing fine-stage iteration and tracing. Invalid external seeds
  are refused. No coarse pyramid is required.
- `lift_box_decimated_similarity(transform, reference_geometry,
  moving_geometry, factor)` includes box-centroid/truncated-size offsets.

The ordinary solver constructs adjacent triples in its previous order. Both
row assembly and prior IRLS use the same explicit triple list. No preferred-pass
fusion policy is embedded in geometry.

## Controls prepared

Eight tests in `crates/strehl-core/src/multi-track-tests.rs` cover one-track bit
equality; malformed partitions; disconnected and gapped tracks; reversed pass
boundary jumps; curved-track robust-IRLS invariance under global reindexing;
guide-lift coordinate chains and a wrong-lift control; analytic direct-pair
recovery with nonperturbing observation; and wrong/invalid-seed/flat refusals.
Curvature plants carry a 46.1-plane-pixel midpoint departure from their chord.
These commission algebra/operators, not capture calibration or quality.

Formatting completed successfully:

```powershell
rustfmt --edition 2024 --config skip_children=true crates/strehl-core/src/align.rs crates/strehl-core/src/multi-track-tests.rs
```

Root must run scheduled focused tests, existing core suite and clippy before
claiming verification. The implementation lane ran no Cargo commands.
