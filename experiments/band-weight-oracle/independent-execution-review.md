# Independent execution review

VERIFIED from saved artifacts on 2026-09-26. The admitted diagnostic used the
fixed consumer and final optimizer iterate. No execution blocker remains. This
review checks execution and admission, not photographic quality or the global
optimum. No optimizer, reconstruction, RAW job or scoring job was rerun.

The recorded commands and bounded process receipts are in each job's
`invocation.json` and `process.json`:

| Job | Child command | Wall seconds | Exit | Outcome |
| --- | --- | ---: | ---: | --- |
| commission-1 | solve.py commission | 27.328 | 0 | Two prescribed targets fitted |
| commission-check-1 | independent-check.py check-commission | 2.906 | 1 | Original analytic truth port refused |
| commission-check-2 | independent-check.py check-commission | 3.250 | 0 | Corrected checker admitted the original fit |
| solve-1 | solve.py solve | 27.640 | 0 | Seven truth-assisted fits completed |
| check-1 | independent-check.py check | 3.156 | 0 | Final saved-weight replay and readout completed |

All five processes have terminal job accounting and empty cleanup errors. Caps
remained 240 wall seconds, 1,800 CPU seconds and 8 GiB committed job memory.
The largest saved peak is 3,587,432,448 bytes. These are process records, not
stacking speed measurements.

The original checker failure is retained with its traceback and no successful
completion receipt. Its seven scalar Gaussian blur taps used NumPy f32 exp,
which did not reproduce the native scalar rounding. The checker-only repair
uses `f32(math.exp(f32(argument)))`; the unchanged 2e-7 truth-parity gate then
passed. The plan records the independent scalar expf comparison and the
one-ULP tap differences. No target, source array, optimizer, fitted weight or
scientific threshold changed, and the commission solver was not repeated.
The first two historical input snapshots differ from today's files only at
`independent-check.py` and `independent-plan.md`. They are historical bindings,
not claims that the original checker equals its corrected version. All 189,
177 and 177 bindings in corrected check2, solve1 and final check1 respectively
still match.

Source inspection and receipt checks agree on the following constraints:

- The reconstruction helper is the unchanged learned-guide consumer committed
  at `f852db6145cfb6758a50cc5045704ff41f349738`, SHA256
  `b5455f488a92ed75c2a8ae8d9dcfb31b054237805b7ded22893459ef4ea9b987`.
  The dataset SHA256 is
  `0c8e7c457f971cc387fa06e7f5261e2b9ef15014c6591b6d7950ce0acdda9e19`.
  Both are checked before use and matched by the retained successful native
  consumer commission. The source coefficients, terminal Mean, InputRange
  bounds, WB/range and MHC were not optimized or replaced.
- Only per-source, per-band logits are optimizer parameters. One weight serves
  all four original CFA planes. Grouping N5 and N9 cases weights each group loss
  by its case count divided by the total; equal image dimensions therefore give
  equal full-image RGB-MSE weight to every case, not every source or group.
- Both fits bind solver SHA256
  `cde46d1d725044373282eb594970e5765ae8cc00255f81b247968359b4f6e73d`.
  They start at uniform zero logits and execute exactly 1,024 Adam updates at
  learning rate .03 and epsilon 1e-15. The final result is used without
  checkpoint selection. History labels explicitly describe pre-update losses;
  final errors are evaluated after the last update. The fixed 180-second fit
  cap was respected: 24.143 and 24.371 seconds, respectively.
- The solve's accepted commission is precisely
  `commission-check-2/output/commission.json`; its hash binds the original
  commissioning fit and the same solver, consumer and dataset. The runner
  requires its qualification argument to resolve to that same receipt.
  The checker also validates completed phase, optimizer settings, fit/prediction
  linkage and exact ordered case identities.

The known-feasible commissioning cases reduced final/initial MSE to
8.2365922e-7 (Flat N5) and 1.8273182e-4 (Curved N9), below the unchanged .10 bar.
Directional finite differences agreed with autodiff to relative errors
6.3766e-6 and 9.7860e-6, with the required opposite-direction increase. These
results commission achievable targets and the gradient path; they do not prove
global convergence on the later truth targets.

I independently rehashed all 45 prediction arrays across the two commission
cases and seven oracle cases, checked their shapes/finite values and matched
their case and prediction manifest hashes. Final oracle weights range from
1.7503216e-5 to 1; every source-normalized maximum is exactly 1. The smallest
saved denominator mass is 1.0008873. Thus the saved output has neither a zero
mass fallback nor nonfinite weights. The checker reports exactly zero complete
CFA and RGB replay difference for all nine cases, including borders. All 183
inputs recorded by the final checker remain hash-identical.

The readout retains the original seven cases and fixed decisions. Known truth
passes, and erased-near, erased-far, added-noise and erased-image destroyers
fail. The saved conjunction is correct: the near-fine/far-coarse positive
passes its preservation and improvement guards, while curved occlusion and
unclipped glint fail preservation. Therefore `all_fixed_screen_guards_pass`,
`candidate_nominated` and `photographic_replay_admitted` remain false. This is
decision-logic verification, not a new quality judgment. Scientific
interpretation belongs to the separate independent results report.

Final screen SHA256:
`c60e4d2399157a16f392a002589e041b6f6fd80ff9d0ca4cb07ff41e48ab0fe5`.
These seven targets were fitted to known truth and are no longer held-out
validation. The result supplies feasible weight witnesses where successful;
failure does not establish a representation ceiling, and neither result grants
another model fit or complete photographic run.
