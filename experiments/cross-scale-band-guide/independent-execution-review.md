# Independent execution audit of development revision 1

VERIFIED from saved source and receipts on 2026-09-26. No stage-1 execution or
reporting mismatch was found. This audit covers the model author's five jobs;
it does not judge image quality or verify this reviewer's newer fixture/export
work. No job was repeated and no fresh validation pixels or candidate scores
were read.

The five recorded processes all exited0 with no process error, terminal job
accounting, empty cleanup errors and successful root completion receipts:
commission1 6.906s, independent commission-check1 3.812s, train1 108.937s,
infer1 3.859s and check1 3.953s. Each preserves its actual command in
`invocation.json`. These match `development-results.md`; they are individual
process readings, not production speed comparisons.

Every historical input binding still matches except the root's subsequently
extended `run.py`. Its recorded stage-1 hash is
`33969c05589100f583dc285afd645484df59bce5c5bcf6914963496bcff80f11`.
That later wrapper evolution does not alter the saved child commands or the
unchanged model, checker, consumer and dataset. All471 inputs read by the final
independent checker remain hash-identical.

The training source is unchanged at
`03ddcab38c492557244638d93694b66473a749aaac6f7785fb129be98dfce96f`.
It reads precisely the pinned old19 cases; the original seven test cases are
explicitly development data here. Every checkpoint has those same19 distinct
case hashes. The source opens truth only during training; inference records
`truth_read=false`. Neither this training/inference path nor its fixed manifest
contains the new training or fresh validation export. Input separation is
supported by this source path and the saved case bindings, not an OS file-access
trace.

Both commissioning receipts are present in the training job's input snapshot.
`training.json` binds the author commission (`18344386...36a8e`), while the root
also gates on the independent commission (`6e7a508a...37dabe`), which in turn
binds that exact author receipt. The distinction is intentional. The independent
gradient check retained descent and ascent controls and relative finite-
difference error0.000712672. All19 uniform/prescribed complete CFA and RGB
comparisons were exact, with113 exercised hull-clamp events.

I checked all65 checkpoint hashes (step0, then every32 through2048) and their
case coverage. Every recorded checkpoint score is exactly the arithmetic mean
of its19 recorded per-case losses. The declared minimum, with earlier-step
tie breaking, is step1536: score1.1333851016627849e-5 versus initial
0.00018959067681347924. The ratio0.059780634824032924 and105.631466-second fit
time match the report. `model.json` is byte-identical to that selected
checkpoint. Selection is development-objective optimization, not independent
validation.

All19 inference records and95 output-array hashes match. The independent final
checker reports exact selected-model-to-weight and weight-to-complete-CFA/RGB
replay for every case, including borders. All saved source weights and
denominators are positive; their reported minima are1.8715247e-13 and
9.3576232e-13. The model hash carried through training, inference and final check
is `b3a22d0c0ab2418bc7f1ddbba0bff193b46a25e446afb1e1f20da3be7c459cb8`.

The final screen is bound by
`b97da529a28124a7018813c589fbeced5a1c7b494215ff8b04a9e5f1a38d19c7`.
It preserves the development failures and sets independent validation,
candidate nomination and photographic admission false. Scientific interpretation
remains in `independent-development-review.md`; this audit grants no new
training revision or photograph.
