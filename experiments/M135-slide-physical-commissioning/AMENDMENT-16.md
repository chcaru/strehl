# M135 slide commissioning amendment 16

Status: **PRE-DATA REPAIR AFTER INDEPENDENT SEND BACK**

An independent review sent commit `a71f6a2645b1f251f11fa16251e8bae11164e836`
back before authorization for any M135 data access.  No path under `D:\` was
accessed to make this amendment.  `PREREGISTRATION.md` is unchanged, and none
of its frozen bars is relaxed.

The SEND BACK identified three load-bearing defects.

1. **The freeze did not cover the executable's local dependency closure.**
   The freeze now derives the resolved local packages with
   `cargo metadata --locked --format-version 1`, hashes every selected
   manifest, build script, Rust source and `src/` input in that closure, and
   also binds the repository and lane locks, root workspace manifest,
   `rust-toolchain` and repository Cargo config when present.  It records the
   Cargo/rustc binaries, versions, metadata/build commands and relevant build
   environment.  The MSVC link uses `/Brepro`, making clean builds
   byte-identical across Cargo target directories.  The exact release
   crosscheck executable bytes are frozen; Stage B refuses a supplied
   executable whose byte count or SHA-256 differs.
   The Python record now uses compact distribution-wide semantic-file
   aggregates plus explicit native-file records for the Python runtime,
   NumPy core/FFT, SciPy FFT/ndimage/optimize, rawpy and the loaded OpenCV
   binary.  A temporary repository-layout copy mutates
   `crates/strehl-raw/src/lib.rs::Frame::active_row` and must make
   `freeze.py check` red; a wrong executable must be refused before Stage B
   decodes a frame.

2. **The role gate trusted declarations instead of physical-site evidence.**
   `target.same_physical_sites` is now a load-bearing predicate.  An
   identifiable ledger must bind by path and SHA-256 a
   `m135-physical-site-manifest-v1` containing at least 64 unique site
   identities and unique normalized slide coordinates.  Every site must carry
   the exact same identity and coordinate for
   `R1`, `R2`, `sw4_Y1`, `sw4_Y2`, `sw10_Y1` and `sw10_Y2`, and the manifest's
   role bindings must match the inventoried capture units and RAW hashes.
   A scalar `site_count` is only a consistency field and is never evidence by
   itself.  Controls now reject a false same-site declaration, a bare scalar,
   duplicate identities, duplicate coordinates, fewer than 64 sites,
   per-role coordinate mismatch, role-binding mismatch and a wrong manifest
   hash.  The existing refusals for sw4-as-truth, odd/even lineage,
   all-axis-as-repeat, shared calibration/source files and checker/source
   oracles remain explicit.

3. **The flat repeatability statistic discarded alternating structure.**
   The decision statistic is now the maximum over the six temporal-split pairs
   of the mean across carriers of the absolute site-averaged complex
   cross-power.  The same maximum statistic is calibrated against the frozen
   255-draw independent site/carrier phase-scramble null.  The reported
   threshold is its fixed higher-method `q99`, and the existing
   `alpha = 0.01` decision rule is unchanged.  The previous positive-clipped
   signed median remains report-only for disclosure.  Commissioning must keep
   independent flat noise quiet and reject constant, `+/-` alternating,
   rotating-sign and one-pair-only structured plants; the amplitude-100
   alternating plant has mean split power `10000`.

All runs described here are **author commissioning, not independent
verification**.  They do not establish that the lane is safe for data access;
that decision remains with a later independent verifier.
