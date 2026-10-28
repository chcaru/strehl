# Full geometry measurement cost checkpoint

2026-10-27. Root releases source preparation only; execution is conditional on
the unchanged independent measurement controls passing. This is the separately
scoped cost checkpoint anticipated in brief.md. No RAW decode or inverse fit.

Photo-review owns cost.py and cost-notes.md. Use the frozen MeasurementGpu API
to measure one forward and one adjoint over the complete native7032x4688
original sensor for source149, then source0, each once. Stream bounded source
rectangles, never a node cube or sparse matrix. Time each whole pass after a
CUDA synchronization and retain per-rectangle timing/accounting. A and its
transpose consume deterministic generated signed, independent-channel f32
fields, with their generating equations recorded. This is not an image or a
noise/control test. Do not read any ARW or developed TIFF.

Use the held299 literal-f64 similarity map and the original source order
identified in input-bridge-audit.md. Construct one global latent domain that
covers the union of inverse-mapped corners of all299 unit source-cell
footprints plus sufficient Lanczos3 support; retain the integer reference
origin and derived full affine maps. Do not use delivery crop as the domain.
Keep original integer RGGB phase and the historical coordinate gauge. Do not
replace reference149's recorded near-identity transform with identity.

Run constants/structured short rectangles only as a warmup; exclude compile
and initialization from the pass times but report both. Use four Torch CPU
workers, f32 data/arithmetic, f64 geometry, TF32/autocast off,8GiB allocation
cap. Record actual dimensions, point counts, memory peaks, finite summaries,
rectangular coverage, source/PTX/runtime hashes and wall/CPU/host-load evidence.
No output field needs disk export: retain deterministic summaries and checksums
of fixed small field samples, with no claim of photographic evidence.

Root will bind cost.py, notes, measurement producer and imported loader, frozen
CPU/reference and map/order. Root owns a fresh output directory and one bounded
job:300s wall,1200CPU-seconds,8GiB host,16MiB log. If the budget prevents all
scheduled passes, preserve that measured failure rather than resize/subset a
pass or extend the deadline. Derived64-step299-source cost must be labeled an
extrapolation excluding Haar/noise/projection/solver and I/O overhead; it is not
a complete-workflow measurement. No64-step execution or cache export is
authorized by this checkpoint. An impractical result closes this exact global
iterative route before another large cache is created.

Before any cost execution, root sets the practicality decision: if both measured
source geometries project beyond3600 seconds for the inherited64-step solve,
stop a naive full299 port of that solver. This is already much slower than the
retained native/vendor workflows and excludes other real work. It is a planning
ceiling, not a measured full-workflow limit or a theorem about all geometries.
Passing it would not release reconstruction automatically. Independent source
review counted132 forward and133 adjoint whole-stack calls for the inherited
nonconverged64-step deflated solver, so use299*(132*A+133*At), not one pair per
iteration. Use synchronized operator-call sums for that planning decision,
excluding generated residuals, diagnostic reductions and journal writes;
report the complete loop projection separately. Both remain extrapolations,
not a measured solver or a strict lower bound. Retain the known synthetic
failures in either outcome.
