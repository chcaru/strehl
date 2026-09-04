# M167 blinded candidate admission — preregistration

Status: **FROZEN BEFORE THE ARM-IDENTITY CANARY IS EXECUTED**

This document closes the provenance and arm-identity bypass left open by the
original M167 battery.  It changes none of P1--P6.  It governs how a future
candidate may obtain the observations whose results are submitted to those
predicates.

M167 remains the judge.  The deliberately dishonest program used below is a
battery sabotage control, permanently marked `INELIGIBLE_CHEATING_CANARY`; it
is not a proposed detail instrument.

## 1. Threat and boundary

The bypass is an out-of-band identity channel.  A program that receives
`flat`, `improved`, the blur rung, a stable call index, or a fixture filename
can emit the answer the checker wants without measuring resolution.

Candidate-visible image content is not an out-of-band channel.  A useful
instrument must respond to its declared observation.  No protocol can forbid
content-dependent branching while allowing image measurement.  The admission
rule therefore removes labels, order, state, filenames, construction metadata,
and known fixture bytes; freezes and audits the submitted artifact; and
requires capability isolation for arbitrary code.

The source audit is evidence, not the security boundary.  Python AST checks
cannot exclude reflection, native-code access, or a sandbox escape.  A real
candidate is inadmissible unless an evaluator-controlled disposable sandbox
attests the runtime restrictions in section 4.  If that facility is absent,
the result is `REFUSED_SANDBOX_UNAVAILABLE`, never a pass.

## 2. Freeze must precede the hidden challenge

Before any challenge nonce is generated:

1. the complete candidate artifact, its declared input mode and score
   orientation are committed and SHA-256 pinned;
2. the evaluator-owned challenge builder, packet worker and admission runner
   are committed and SHA-256 pinned;
3. an independent source audit records every candidate file and dependency;
4. all those owned paths are clean relative to the recorded Git commit; and
5. neither author nor candidate has seen a challenge packet, opaque token,
   permutation, score, or gate result.

Changing any pinned byte discards the challenge.  The revised artifact must be
frozen first and receives a newly generated nonce.  A disclosed nonce may be
reused only to reproduce the already sealed run, never to admit a revised
candidate.

The M167 canary sequence is fixed:

1. commit this preregistration;
2. author and commit the runner and canary without executing the canary;
3. commit a manifest pinning their hashes;
4. generate the hidden nonce and run; and
5. commit the sealed transcript and unblinded verdict.

## 3. Hidden challenge family

Admission uses **three** independently derived challenge instances.  A
256-bit nonce is drawn only after the freeze.  SHA-256 domain-separated
derivations from that nonce and the instance number replace the public latent,
fixed-pattern and downstream-noise seeds in the frozen M167 fixture recipe.
Array side, oversampling, optical sigmas, noise amplitudes, blur ladder and USM
plant remain exactly those in the original preregistration.

Each instance contains these private semantic observations:

`flat_detail`, `flat`, `base`, `improved`, `degraded`, `blur_0`,
`blur_0p5`, `blur_1`, `blur_1p5`, `usm`, `nonfinite`, and `wrong_shape`.

It also contains fresh byte-for-byte copies of `flat_detail`, `base`, and
`improved` as duplicate-consistency controls.  The fifteen packets are
permuted from the nonce.  Their public handles are random opaque 128-bit
tokens.  Tokens and their semantic mapping exist only in the evaluator; no
token is supplied to the candidate.

This hidden-seed family prevents a pre-frozen artifact from memorising the
public M167 arrays.  It does not make semantic response to newly observed
pixels illegal.

## 4. Candidate-visible packet and runtime

The candidate declares exactly one mode before the challenge:

- `single_image`: one NumPy array;
- `repeat_pair`: two NumPy arrays; or
- a separately preregistered reference-bearing schema.

The evaluator strips undeclared fields.  M167's canary declares
`single_image`.  Its child receives one `.npy` byte stream on standard input
and emits one result-contract JSON object on standard output.

Every packet runs from the same clean snapshot in a **fresh process and fresh
disposable sandbox**.  The candidate sees:

- the frozen candidate artifact and declared numerical runtime;
- one observation byte stream;
- a constant command line, working-directory shape and normalized
  environment; and
- standard output/error.

It does **not** see an arm name, opaque token, packet index, permutation,
challenge nonce, semantic manifest, fixture/challenge source, checker,
repository, parent memory, prior/future packet, persistent storage, network,
host clock, or differing path.  No host directory is mounted.  Writable
scratch is empty and destroyed after that one call.  Numerical thread settings
are constant.  There is no wall-clock acceptance predicate.

The local M167 commissioning harness can prove the packet/API and fresh-process
properties against the canary, but ordinary Windows subprocesses do not supply
the filesystem, network, clock and parent-memory capability boundary above.
It must therefore record `sandbox_attested=false` and is ineligible to admit a
real candidate.  The governing rule remains fail-closed until a local
disposable VM/sandbox supplies and independently audits those controls.

## 5. Seal before unblinding

Candidate execution ends while semantic identities remain private.  The runner
then writes a canonical sealed transcript containing, for every opaque token:

- candidate artifact hash;
- challenge-instance commitment;
- candidate-visible packet hash;
- canonical result record; and
- child return/parse status.

The transcript contains no nonce or token-to-semantic mapping.  It is written
and read back, and its SHA-256 is fixed, before any record is mapped to an M167
arm.  Unblinding may only consume the exact sealed bytes.  The final record
reveals the nonce, mapping and transcript hash so an independent verifier can
rebuild every array, packet hash, permutation, P1--P6 record and P7 comparison.

## 6. Admission gates

P1--P6 retain their original definitions and are evaluated separately on all
three hidden challenge instances.

**P7, exact duplicate consistency:** within each instance, the canonical
result records for each of the three declared duplicate pairs must be
byte-identical.  Approximate equality, stochastic intervals, a process failure
on only one copy, or different refusal reasons fail.  A stochastic instrument
is inadmissible; it must internalize and freeze any sampling so the same input
has the same result.

The non-score admission gates are:

- **A1 artifact freeze:** all hashes and the pre-nonce Git state match;
- **A2 source provenance:** the audit finds no arm vocabulary, extra identity
  argument, environment/path/order/reflection channel, undeclared dependency,
  dynamic import/evaluation, filesystem/process/network/clock access, or
  persistent state;
- **A3 packet blinding:** child argv, environment, cwd shape and stdin schema
  are invariant across packets and contain no private identity;
- **A4 process isolation:** every packet starts from a clean process/snapshot
  with no cross-call state;
- **A5 seal ordering:** the transcript hash is fixed before semantic mapping;
  and
- **A6 capability sandbox:** the evaluator independently attests every denial
  in section 4.

`ADMITTED_BY_BLINDED_BATTERY` requires P1--P7 on every instance and A1--A6.
One false/missing gate rejects.  No average, majority vote or later explanation
can compensate.

## 7. Pre-registered cheating-canary commissioning

The canary will explicitly try, in order, to obtain an arm identity from:

1. a direct identity argument;
2. recognized arm words in environment variables;
3. recognized arm words in argv or the current path; and
4. a process-local invocation counter.

When it finds a label, it emits canned values that satisfy P1--P6.  When it
does not, every finite two-dimensional image receives the same point score;
non-finite and wrong-shape inputs receive typed failures.

The fixed predictions are:

1. **Legacy labeled control:** supplying the direct private arm identity makes
   the canary pass P1, P2, P3, P4, P5 and P6.  Failure means the canary is not
   a valid bypass control and commissioning stops.
2. **Source audit:** the identity argument, arm vocabulary, environment/path
   probes and state counter are all detected, so A2 is false.
3. **Blinded API:** no identity is recovered.  All valid observations return
   the same point.  Therefore P1, P2, P3, P4 and P5 are false, P6 is true, and
   P7 is true on every instance.
4. **Disposition:** the canary is
   `REJECTED_BY_BLINDED_ADMISSION`.  If it is admitted, if a child sees a
   private label/token/index, or if the sealed and independently rebuilt
   results differ, the admission protocol is `NOT_COMMISSIONED`.

P7 is not expected to catch this particular constant fallback; P1--P5 do.
P7 guards the separate order/state strategy.  The fresh-process reset makes
the canary's process-local counter identical on every blinded call.

The canary's legacy pass is not a positive instrument control.  The original
construction-truth oracle remains the only positive control and remains
permanently ineligible as a candidate.
