# V-HEADTOHEAD3 — central-sensitivity count-gate correction

**Frozen after independent verification of schema 1, before its replacement
run.**

The independent verifier confirmed every reported profile, hash, geometry,
unit conversion, clearance, retained count and final disposition.  It also
found a protocol defect: schema 1 called `cover_core.map_site`, which computes
per-site spectral components, before applying the frozen 12-detail / 6-flat
count gate.  No bootstrap, aggregate, or numeric result was emitted, but 250
licensed-Q25 components were touched before the failed gate.  The statement
that no filtered statistic was computed was therefore too broad.

Schema 1 is withdrawn as an execution-order record.  Its geometry-only facts
and `BORDER_UNRESOLVED_INSUFFICIENT_CENTRAL_SITES` disposition are not
numerically affected.

The corrected run freezes this order:

1. independently fit each render geometry exactly as before;
2. map, register, rail-check and measure border clearance without calling
   `rank_energy`;
3. apply the exact 1280-Scale / 640-Crop output-pixel clearance gates;
4. count frozen detail/flat labels;
5. if either 12/6 minimum fails, stop with no spectral call;
6. only if counts pass, revisit those same retained sites and compute the
   licensed 0.10–0.20 aggregate.

The runner must count every `rank_energy` invocation before the count
decision and fail closed unless it is exactly zero.  That guard is
commissioned against a planted one-call leak, which must go RED, plus a
zero-call null.  No site, threshold, geometry fit, profile value, or verdict
rule changes.
