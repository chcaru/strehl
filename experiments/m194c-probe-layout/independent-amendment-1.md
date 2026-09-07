# Additive component power check after the retained first failure

2026-09-07, after independent-run-1 and before the second independent execution.
This is a prospective addition, not a claim that the original fixture passed.

Both gather modes passed the sampler, actual Probe and actual writer tests.
The separate direct BandMerge check failed at the finite-floor power assertion:
the original sinusoid at variance800 produced exactly the same output for the
white fallback and beta1e6. Its None/empty/NaN equalities therefore have no
demonstrated branch power. Both raw failed logs and source hashes are retained.
The original assertion remains as an explicit expected-failure regression with
its named reason. It will fail the suite if the known-inert case changes.

Mechanism (ARGUED before the new run): the original field's angular frequencies
(.69,.41) rad/sample are attenuated by the pyramid's Laplacian operation, so the
chosen raw amplitude does not establish energy above the variance800 floor.
Increasing an already inactive floor need not change an average. No camera
calibration, product traversal defect, or fallback implementation defect follows.

Separate fixed choice: use the same72x54 dimensions, amplitudes12/110/34,
pedestal3000, bands3, gate2 and variance800, but replace the sinusoidal field by
an exactly alternating checkerboard with all frames in phase. The binomial
reduction kernel annihilates that spectral support in the interior, leaving
band0 signal energy110²=12100 in the largest-amplitude frame. The ordinary
white floor is about2*.8894*800=1423; beta1e6 puts the floor far above it.
No gate/noise threshold or parameter sweep is introduced. This is a deliberately
chosen component signal, not a physical scene or a new scored quality sample.

Falsifiers: None/empty/NaN outputs must match; the huge finite floor and separately
variance80000 must change the output. The forced mean must agree within.02DN at
two interior sites with the independently known arithmetic mean3000±52, and
ordinary-floor amplitude there must exceed60DN, proving actual non-mean output.
If this additive fixture is inert or violates that mean, retain the result and
stop commissioning this unchanged fallback consumer. The primary layout repair
and40-output quality comparison remain separate.

The final test source may be rustfmt'd before rebuilding, with hash/compile
bindings renewed. No producer, product constant, or scored input changes.
