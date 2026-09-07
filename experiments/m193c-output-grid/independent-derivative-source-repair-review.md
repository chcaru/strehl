# M193c derivative — narrow source-repair review

2026-09-07. **SOURCE ONLY / UNEXECUTED.** This addendum preserves the initial
`independent-derivative-source-review.md` and its two findings. No Rust build,
helper/control call, TIFF operation or RAW read/decode occurred here.

| Repaired file | Bytes | SHA256 |
| --- | ---: | --- |
| registration-derivative.rs | 39489 | db2a4d0c36d3f0778481e8a9837feef1c2651258865799bbd143b6bb0840eecd |
| derivative-controls-preregister.md | 14799 | 7c9f359a100d3b1f7c0522e8635f9178e0147756e61bcbc1373fd37324fbe5dc |

The preregistration now distinguishes the same bounded JSON bytes used for
plan hashing/parsing from RAW snapshot hashing before and after the separate
path-based owned decode. It explicitly declines a same-buffer RAW decode or
atomic lock/handle guarantee. The parent still owns the stable fresh snapshot
and all-original provenance. This resolves the initial scope overstatement;
it does not implement a stronger snapshot-access mechanism.

The existing `late-publication-revokes` control now constructs the known
initial pretty-JSON bytes including their newline. Its actual finalizer
callback reopens the provisional file and requires those exact bytes before
raising `private late-finalization source fault`. The post-call assertion
requires that exact returned cause, `REFUSED` status, the same persisted
error, and a finalization array containing that one cause only. It reopens
the retained first receipt and requires equality with the known initial
bytes and the bytes observed by the callback. Actual expected/observed hashes
and the retained FileRef are recorded.

An unrelated callback read error cannot satisfy the exact returned-cause
predicate. Missing or altered first bytes cannot pass merely because a
`.first.json` file exists. A replaced original cause or additional unexpected
finalization error now fails the existing control. This closes the initial
power gap without a new ID or writer invocation. The source still requires
32 controls, followed by exactly two private TIFF writer calls. No image
arithmetic, fixture values, scalar allowance, schema or native population
changed in these repairs.

**Disposition:** both initial findings are discharged at source level by
the reviewed pins. No additional blocking defect was found in this narrow
reread. These sources are ready for the parent's exact include/build and
later private-control release; compilation and actual controls remain
unverified. Native RAW release still depends on the separate independent
active-payload/TIFF reader and encompassing campaign, as the initial review
states.
