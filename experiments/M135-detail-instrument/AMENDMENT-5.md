# M135 commissioning amendment 5

Status: **FROZEN BEFORE SUCCESSFUL FLAT-NULL OUTCOME GENERATION**

The first amendment-4 execution stopped before gate evaluation or artifact
write. The potency record emitted one gain per registered cell (`16` values),
while the checker correctly expected one value per registered frequency (`4`
values), causing a shape error.

This amendment changes no data, transform, statistic, threshold, or gate. The
noise plant still applies the same gain to all four orientations at each
frequency. Only the potency record is de-duplicated to the four frequency
values frozen in amendment 4. No challenge outcome was printed or inspected
before this correction.
