# Independent control completion review

2026-09-19. Read-only review of root receipts and the separate completion helper;
no rerun or RAW read. **GO for the separately scoped source35 cost checkpoint
only. Original generated quality admission remains false.**

Root's fresh build1 completed in136.328 seconds. The bound executable ran
`merge_cmd::parallel_cfa_wavelet:: --nocapture --test-threads=1`: four tests
passed, none failed, the full RAW test remained ignored. Rust time5.41 seconds;
owned-job wall5.734 seconds. The log explicitly names both unchanged boundary
tests, the new numerical test and the adapted full mechanical test.

The unchanged driver then failed only because its final assertion expected the
old full-control marker. `complete-controls.py` does not bypass a failing test:
it requires successful process exit/cleanup, verifies bound sources/executable
and the recorded log hash, requires the actual unique numerical/full records,
and repeats all frozen twelve-case continuity checks. The actual command and
test names agree with this scope. Its separate completion receipt is a valid
record of the already completed controls, not a rerun or changed algorithm.

MEASURED numerical evidence:

- Parallel forward/inverse coefficients equal the serial oracle bit for bit
  at one/four threads, including reflected odd input and twelve-level axes.
- The finite exp80/DN adversary overflows the legacy product but stays finite
  with scaling. Maximum normalized error is .008929 on components as large as
  392571; seventy-source mixed-sign/order stress reaches .000793 absolute
  component error. These are arithmetic errors, not reconstructed pixel error.
- The actual generated old/new comparison has exact baseline, variance,
  weights and fallback. Maximum candidate discrepancy is .000976563 DN in CFA
  and1.192093e-7 in normalized RGB. Observer on/off is bit-identical within the
  new operator. Existing CA/headroom/developer controls pass.
- Across all twelve cases, the largest candidate score change is2.406400e-7
  (limit2e-6); RGB-ratio change6.347787e-7 (limit2e-4). Baseline and evidence are
  exact except probe timing; all quality decisions remain unchanged.

This establishes the bounded execution/numerical repair on commissioned inputs.
It does not establish full4096² runtime, memory, successful full-size inversion
or photographic improvement. The source35 cost run must still satisfy original
one-source output equality and the fixed resource gate before any full pair.

| Binding | SHA256 |
| --- | --- |
| complete-controls.py | a2a092226ba5afb93603fdf154bae3eff8be634828344ae788f78fdbe41e4e0d |
| controls-1/completion.json | a155dcc7374219699c0f0ceb30a7587f22fa9b09d63ff7ab65283aa9669c4971 |
| controls-1/output/screen.json | e1cfd11b745ce4a2aa28a1f5c26e7c9832dd80df74944d17db9214ac5e8dec7f |
| controls-1/process.json | bf298d98f2ae1e1510cd09282bfab2548f9f9e90756be5cbab9d09003fe857fa |
| controls-1/bindings.json | 8615c19d696064399ae90a46bc1383f4f5868690d3835748bb17334bd1e43fce |
