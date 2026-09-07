# M194d independent source-counter commissioning

Before any independent control execution, source review identified the new
per-frame read counters as a test-source observer. The committed independent
design already requires an active on/off/placebo byte proof for a new observer;
the first include implemented only the on arm. Add that missing commissioning
before running it. No scene, floor, exponent, tolerance, seed, product source or
benchmark arm changes.

Curie's first core/CLI build was already running when this was identified.
The independent sources remained unchanged until that build completed. Its
logs and edited-source snapshot are preserved in `author-run-1`; author tests
passed and no independent tests executed from that first build.

For both existing full/cropped geometries and both gather paths, compare the
same actual candidate output with the test-source counter off, counting each
index, and a placebo incrementing an unrelated total counter. The on arm must
record one read per supplied frame; off records zero; placebo records five
total increments while the per-index counters stay zero. All TIFF bytes and
decoded pixels must agree. The branches are therefore demonstrated to run;
the inert prepared-Pyramid stats flags are unused.

This adds two small TIFFs per geometry, bringing independent actual-consumer
output to twenty TIFFs per gather process. These are software controls outside
the root-owned fixed comparison. Counter totals and output hashes are retained.
No performance inference follows from the observer or its placebo.
