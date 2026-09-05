# M135 slide commissioning amendment 13

Status: **DETERMINISTIC-SERIALIZATION REPAIR BEFORE COMMIT**

Two identical final commissioning invocations both passed all 55 checks but
produced different file hashes:

- before: `a08898d507b4778bcaab7547b03963bc57d6e5d1ca1ff56dcca1231441dab469`;
- after: `8e0334d3512671f01254a271150771f43dbb1dec8cda0edb7de312e748b4872e`.

The pair is preserved as
`commission-run4-nondeterministic-{before,after}.json`.  The only differences
were `3.9e-11` to `7.8e-11` in OpenCV quadrilateral diagnostic scores; the
selected corners and every predicate were identical.

OpenCV-derived diagnostic geometry is now serialized at ten decimal places,
and the commissioning plant-detail envelope applies the same diagnostic-only
rounding after all checks have run.  No value used to choose a quadrilateral,
fit registration, estimate a peak, or decide a bar is rounded before its
decision.
