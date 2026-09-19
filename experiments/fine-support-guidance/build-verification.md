# Build and default-feature verification

Root executed the two fresh release builds and both independent control runs
recorded in `results.md`. The second release log contains both `Compiling
strehl-core` and `Compiling strehl-cli`. Independent source review found no
critical weight-hook or integration defect; independent numerical review
rejects the quality change.

Root additionally ran the ordinary core feature configuration after the hook
edit, to exercise compilation with the diagnostic feature absent:

```
cargo test -p strehl-core --lib pyramid:: --locked --offline
```

Actual terminal result: fresh `Compiling strehl-core`, compilation8.32s,
61passed/0failed/0ignored,501filtered, tests8.35s. These include reconstruction,
shared-plane selection, noise averaging, disabled-significance identity, hulls,
worker/chunk controls and the existing admission controls. This does not
reclassify the rejected experimental mode as a quality gain. No product
default changes, and no additional RAW image was rendered for that mode.
