# BUILD-GATE — provenance and reproducibility after the scratch purge

Written at wind-down, after `C:\dev\strehl-out\BUILD-GATE` and
`D:\strehl-out\BUILD-GATE` were deleted under the orchestrator's disk
directive. Its purpose is to record what survives the deletion and, more
importantly, what does not — so that no number in `docs/research/BUILD-GATE-4.md`
is read as more reproducible than it is.

## What was deleted

| path | GB | what it was |
| --- | ---: | --- |
| `C:\dev\strehl-out\BUILD-GATE\sweep\` | 6.45 | 7 gate arms x 5 subjects, full-bracket masters |
| `C:\dev\strehl-out\BUILD-GATE\head\ab\G200\` | 0.92 | the section 15 NULL baseline masters |
| `C:\dev\strehl-out\BUILD-GATE\pin\strehl.exe` | 0.01 | the pinned binary every sweep arm was rendered by |
| `C:\dev\strehl-out\BUILD-GATE\blotch_rows_*.json` | small | per-subject blotch rows, intermediate |
| `D:\strehl-out\BUILD-GATE\109-noauto.tiff` | 0.18 | the unclipped exposure comparison render |

## What survives, and where

- **Every number** is in the committed tables of `docs/research/BUILD-GATE-4.md`
  and in `experiments/BUILD-GATE/gen/`. The deleted JSON was intermediate: its
  values were already reduced into those tables.
- **The method** is `experiments/BUILD-GATE/src/sweep_render.ps1`, committed. It
  names all seven arms, their `--pyramid-gate` values, the `STREHL_GATE_FLOOR`
  setting for `WHITE200`, and the exact invocation
  (`stack <subject> --out <out> --srgb --auto-exposure --merge pyramid
  --pyramid-gate <k>`). Source frames are under `D:\personal\macro`, untouched.
- **Cost to re-render**: about 27.5 s per master, measured from the render log,
  so roughly 16 minutes for 7 arms x 5 subjects.

## What does NOT survive — read this before quoting section 13

**The pinned binary is gone and its identity was recorded truncated.**
`BUILD-GATE-4.md:57` records it as SHA256 `8E397B01` followed by an ellipsis —
eight hex characters. That string appears nowhere else in the tree, and the
binary itself has been deleted, so the full digest is unrecoverable.

The consequence, stated plainly:

- Section 13's sweep is **methodologically** reproducible. Anyone can re-run
  `sweep_render.ps1` and repeat the experiment.
- It is **not** bit-reproducible, and a re-render **cannot be checked** against
  the original, because the recorded hash is too short to verify a rebuild.

This is the defect that `crates/strehl-cli/tests/byte-freezes.tsv` warns about
in its own header: a hash must never be truncated, because the corpus already
carries one recorded as eight characters and an ellipsis, which no machine can
check. This lane committed the same error and is recording it rather than
leaving it to be discovered.

**Section 15 does not have this problem.** Its binary is banked in full at
`BUILD-GATE-4.md:1369`: SHA256
`5915316B95E21446A85A1F50EC4D459E1E52F19DAE4487981E0342622740AFF9`, version
`strehl 0.0.0 (5e914c5f4fa2)`. Commit `5e914c5f` is in git, so that binary can
be rebuilt and the rebuild can be verified against the recorded digest.

## Consequence for the gates

`verify_blotch.py` re-derives section 13's 60 checks from the sweep **pixels**,
not from `gen/`. With `sweep/` deleted it now fails:

```
FileNotFoundError: [Errno 2] No such file or directory:
  'C:\dev\strehl-out\BUILD-GATE\sweep\WHITE200\bee-1-cpl.tiff'
verify_blotch.py  rc=1
```

That was measured before the deletion, by moving the tree aside and re-running.
To restore the gate, run `sweep_render.ps1` with the five subjects, repointing
`$PIN` at a rebuilt binary. `verify_s14.py` (42 checks) and `verify_s15.py`
(86 checks) do not read pixels and are unaffected.

## The generalisation

Regenerability is a property of the **chain**, not of the artifact type. This
lane's section 15 chain reads `gen/` only, which was proven by moving its
masters aside and re-running `s15_tables.py --check`. Its section 13 chain
re-derives from pixels. Same lane, renders that look identical, opposite
answers. Deleting by category label rather than by measurement would have
destroyed one and not the other.
