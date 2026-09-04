# M164 real-pair audit — amendment 2

Status: **FROZEN AFTER RUN 2 FAILED, BEFORE RUN 3**

Run 2 preserved every original scientific gate and evaluated all three
authorized pairs. All three failed the predeclared minimum of eight eligible
sites:

- `cb`: `4/12`;
- `113`: `7/12`;
- `113-sharp`: `6/12`.

The persistent artifact is `out/realpair-run2-failed.json`, SHA-256
`DB89D5BADD10799D6A71550D550D327581D78CABD7F729EC051014A7D5AC4713`.
No pair-level transfer verdict was observed.

This amendment is based only on eligibility counts/reasons, not transfer-veto
outcomes:

1. replace the sparse 3-by-4 site lattice with a fixed, non-overlapping
   5-by-8 lattice (`40` sites) determined from the common image dimensions;
2. evaluate every site in that lattice, with no result-dependent selection;
3. retain the absolute minimum of `8` eligible sites and every rail,
   registration, adapter and transfer threshold unchanged;
4. if fewer than eight sites survive, preserve their site-level transfer
   diagnostics but return `PAIR_INVALID`, never `NOT_VETOED`; and
5. return aggregate `NOT_DETERMINED` if every pair is invalid, `PARTIAL` if
   only some are invalid, and a categorical answer only if all three satisfy
   their preconditions.

The wider lattice repairs sampling coverage, not the gate. It is a transparent
post-failure development amendment on already-burned pairs.

