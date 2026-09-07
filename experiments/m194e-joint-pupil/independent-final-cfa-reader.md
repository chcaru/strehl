# M194e final CFA reader commissioning

2026-09-07. Prepared under the previously approved
[emission design](independent-emission-design.md). **The reader is commissioned
on private controls; no genuine CFA commission exists.** The full optical run
`float-run-1` remains `UNCOMMISSIONED_NUMERICS`. No file from that incomplete
population was emitted or admitted by this lane.

This report preserves the amendment1 reader revision. The subsequently
released source pins and repeated controls are recorded separately in the
[amendment2 refresh](independent-amendment2-refresh.md); use that record's current
reader/control hashes for the forthcoming genuine invocation.

## Interface and trust boundary

`independent-verify-cfa.py` accepts externally supplied SHA-256 bindings for the
real emitted manifest and the real independent float commission. The entry point
also requires the exact final-reader control record and its supplied hash. It
does not fetch a gate hash from the candidate manifest and call that authority.
The final CLI has no fixture-mode option. Its private Python test entry point
uses distinct `FIXTURE_ONLY_*` predecessor statuses and returns only
`PASS_FIXTURE_READER_ONLY`; it cannot write a CFA commission.

The driver reuses the unchanged commissioned scalar oracle and the
`actual_output` lineage function from the independent API driver. It adds typed
emitted geometry/model comparisons, strict parsing of the actual bound JSON
documents, source/terminal/authority checks, and a before/after ledger of the
files it consumes. No producer, emitter, Rust or numerical-method source changed
for this work. The driver requires the fixed genuine reference result digest
`8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc`
and `PASS_FLOAT_MODEL` from the externally bound mathematical comparison.

For all five actual emitted frames it checks:

- every CFA u16 sample and every expected-CFA electron sample against the
  independently implemented conversion of the exact admitted scalar values;
- scalar, indicator and numerical receipt bytes preserved under the original
  relative hierarchy, and source/noise/units/geometry consistency through the
  terminal emission receipt and external float gate;
- complete primary/refined mathematical comparison populations and their
  admitted references, followed by an actual primary-scalar comparison with
  each refined independent reference array;
- unchanged input and relevant source bytes through completion.

The scalar/reference maximum `.004e` and RMS `.0008e` are the already registered
discrepancy bars. They are not inferred from quantized CFA agreement. The reader
reports separate reference-code differences, per-channel distance to half-DN
ties and `.004 * .25 * channel_factor` DN allowances. Codes that differ only
because an approximate reference crosses a rounding tie are not mislabeled as
failed exact conversion. Quantization's half-DN allowance is separate again.
An eight-ulp arithmetic guard is used only when classifying the tie boundary;
it does not enlarge the scalar maximum or RMS bar.

## Private controls and first failure

The control package is explicitly synthetic: five nonconstant48×64 scalar
arrays, private float gates and fake comparison/reference records whose statuses
say `FIXTURE_ONLY_*`. The genuine135-check author component record is copied
unchanged from `author-controls-6`. That component provenance does not confer
optical authority on invented scalar arrays.

The private reference is offset by `.0002e` from the admitted private scalar.
This deliberately produces **192 actual rounded-reference code differences per
frame**, all within the recorded allowance, while exact emitted-scalar
conversion still matches all15,360 samples. A zero-difference-only fixture could
not test the distinction. Shifted references at `.005e` and `.001e` separately
trigger the maximum and RMS bars; a `.0002e` companion passes.

First run:

```powershell
python -B -X faulthandler -X pycache_prefix=experiments/m194e-joint-pupil/work/independent-final-cfa-cache-1 experiments/m194e-joint-pupil/independent-final-cfa-controls.py --output experiments/m194e-joint-pupil/independent-final-cfa-controls-1 *> experiments/m194e-joint-pupil/independent-final-cfa-controls-1.log
```

Exit1, **23/24** expectations passed. The new reader accepted JSON`false` as
emitted frame index0 through its reused equality-only lineage function. This
was a defect in this lane's new reader, not in the emitter. The exact first
source, accepted mutant, result and log remain under that run directory.
Result SHA-256:
`324186e8844660e624c48d24de4fea7dd95a548a8bb1e90fe6aa37daca251137`.

The repair compares typed emitted geometry, fixed model/sensor values and
producer records against the admitted originals, and also compares completion
frames with typed values. Two extra direct cases check `noise:0` in place of
`false`, and floating64.0 in place of integer width64. This is closed-type
enforcement, not a changed numerical tolerance or scientific admission rule.

Final component command used the same command with cache/output/log suffixes`2`.
Exit0, **26/26** passed; source and original private fixture tree unchanged.
The controls include genuine-mode refusal of private gates, wrong external
digests, nonterminal/refused receipts, source and authority mismatches, unknown
keys, missing files/fields/frames, incorrect units/noise/types and actual
rehash-consistent CFA/electron corruptions. The unchanged complete companion
passes both before and after them.

| Artifact | SHA-256 |
| --- | --- |
| `independent-verify-cfa.py` | `9e79bb62ad9fcfc3cae71770d4d1bdda35bffcb5a71f27c50e82f63c6ae6e229` |
| `independent-final-cfa-controls.py` | `b14c0124bcbcfd1c487838b01157fe95763ba170fe52bc4cb926e82f47167776` |
| `independent-final-cfa-controls-2/result.json` | `fd3a741cae39d0d084a748603ad616fed756abf951f4beb562945e84b1385e5e` |
| `independent-final-cfa-controls-2.log` | `3c96ff98ae2e5326c669d1b103f10b64529db58e4a79b119691529c587327472` |

## Real CLI refusal and future invocation

The genuine CLI was also run against the complete private fixture using its
actual manifest/gate hashes and the passing final-reader control hash. It
exited1 with `UNCOMMISSIONED_CFA`, specifically because the `author_api`
predecessor had a fixture-only status. The result records the exact invocation:
[independent-final-cfa-genuine-refusal-1/result.json](independent-final-cfa-genuine-refusal-1/result.json),
SHA-256 `7be73d4669aa8d610dad2ba11c71859e24bc487e3dadbfdecdc00ef7864f74dd`.
No `cfa-commission.json` was written. This is an actual CLI authority refusal,
not a successful scientific CFA verification.

After a genuine independently admitted float package and actual emission exist,
the invocation shape is:

```text
python -B -X faulthandler -X pycache_prefix=<new isolated prefix> experiments/m194e-joint-pupil/independent-verify-cfa.py --manifest <actual manifest> --manifest-sha256 <externally supplied digest> --float-commission <genuine gate> --float-commission-sha256 <externally supplied digest> --reader-controls experiments/m194e-joint-pupil/independent-final-cfa-controls-2/result.json --reader-controls-sha256 fd3a741cae39d0d084a748603ad616fed756abf951f4beb562945e84b1385e5e --output <new independent verification directory>
```

This template was **not run on genuine CFA files**. The current reader and its
controls are pinned to numerical amendment1 and corrected schema
`0bcc546634a748ee31fbd5095b6aae3a1eab18899a557dbed8aeeb8af102a82c`.
Any numerical amendment2 source/contract change requires an explicit relevant
dependency-pin and control refresh before use. A source mismatch is a refusal,
not permission to silently project new evidence into the old schema.

No full-array mathematical PASS, physical calibration, actual production merge,
noise-performance improvement or SOTA bar is supplied by these private controls.
