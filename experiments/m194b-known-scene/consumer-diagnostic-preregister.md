# M194b padding sensitivity isolation preregistration

2026-09-07, after independent consumer controls found a live layout sensitivity,
before the diagnostic extension and its runs. The initial result is preserved in
`independent-consumer.json`: identical active CFA samples with a changed storage
origin/stride yielded different TIFF samples. This falsifies the initially
expected whole-render padding identity; it is not reclassified as a passing null.

Source inspection proposes a specific mediator: `gatefloor::Probe::run` clones
the full decoded storage and fills its linear slots with deterministic noise.
Changing the storage layout changes the probe samples at active photosites.
The two existing logs also show different consumed measured-floor summaries.
Neither observation alone isolates the effect from a gather addressing error.

The only new control is an explicit test-local `--diagnostic-white-floor` switch.
It requires both a test-local diagnostic marker and the existing production
`STREHL_GATE_FLOOR=white` setting, records this in the plan/environment/config,
and still passes through the same prepared production consumer. Both planning
and rendering must select it; an ordinary measured-floor plan cannot be reused.
No production arithmetic or registered baseline setting changes.

The independent verifier will render the same original and alternate storage
layouts with the white floor. Prediction: their TIFF pixels and bytes become
identical. Any surviving difference falsifies gate-floor probing as the complete
explanation. The existing measured-floor layout difference remains the live
positive control. Additional refusal controls omit either member of the paired
diagnostic environment or reuse a measured-floor plan and must fail. The original
measured-floor configuration remains the sole admitted 40-TIFF benchmark.
