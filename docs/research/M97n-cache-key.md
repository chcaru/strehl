# M97n — the warp cache key did not cover its own inputs

**Status: SHIPPED.** The shared warp-map cache was keyed on the capture path
alone, so two solves of one bracket with different configurations occupied a
single entry. Four bars, all passing, the null planted.

Owner: M97, lane granted. Files: `crates/strehl-cli/src/align_cmd.rs` only.

---

## 1. The defect

`sidecar_path(dir)` hashed the canonical capture path. `check_stack` compares
the **frame set**. Neither covers *how* the solve was configured. So a sidecar
produced by one configuration was silently served to a merge expecting another,
and `strehl stack` reported `alignment: ON (sidecar)` with no indication that
the registration was not the one it would have computed.

MEASURED before the fix: `strehl align --reference 40`, then an **identical**
`strehl stack` command line, rendered `DB43E708…` or `ADF81E01…` depending only
on whether the align had run first.

**Why this was worth doing before anything else.** Every A/B comparison in the
project reads this cache. An unkeyed solve input is therefore not one
milestone's problem — it is a validity problem under every sharpness, halo and
merge measurement being taken concurrently. It also lands squarely on
`resampler`, the field M95 attributes 59% of high-band loss to. It is the same
class as a byte-freeze that cannot distinguish "verified nothing" from
"verified everything": the instrument reports success either way.

**A second, one-hour-old instance.** `solve_map` calls `apply_smooth_env`, so
M110's new `STREHL_SMOOTH` and `STREHL_SMOOTH_HUBER` change the solved warps.
They were recorded nowhere and keyed nothing. That is how an unkeyed input gets
in: not carelessly, but by adding a knob to the solve without touching the
cache. The fix keys them, and `SOLVE_ENV` carries a comment saying that
extending `apply_smooth_env` without extending it reopens this.

## 2. The fix

Two layers, because they fail differently.

- **`solve_config_key(reference, spans, resampler)`** digests every input to
  `solve_map` that can change its warps, environment included, and is mixed
  into the cache filename. Different configurations now get different entries,
  so they cannot collide **and cannot thrash** — both stay cached.
- **A provenance guard in `load_or_solve`.** The merge compares the loaded
  map's `reference` and `resampler` against the configuration it would have
  solved with, and re-solves loudly on a mismatch. With the key in place this
  is unreachable in normal operation; it exists for a stale, hand-edited or
  hash-colliding file, where using the entry would silently render a
  registration nobody asked for.

`merge_config(n)` returns the merge's reference, spans and resampler as one
value, so the cache lookup and the solve cannot drift apart — the drift that
created the defect.

## 3. Bars (MEASURED)

`experiments/M97-warped-merge/src/poison2.ps1`, `109MSDCF`, `--limit 22
--gate 4.0`, hermetic `STREHL_CACHE_DIR` so the seven live agents' shared cache
is untouched.

| bar | claim | result |
|---|---|---|
| C1 | a poisoning `align` does not move the render | PASS — `07C067E4…` both |
| C4a | a no-flag `align` resolves to the merge's own config, 1 entry | PASS |
| C4b | `--reference 3` gets its **own** entry, 1 -> 2 | PASS |
| C2 | **PLANT** — disabling alignment *does* move it | PASS — `48DFB69C…` |
| C5 | no thrash: the second `stack` reads `sidecar`, not `solved` | PASS |
| C3 | the byte-freeze still reproduces | PASS — `the_frozen_renders_still_produce_their_recorded_bytes` |

C1 is a null and a null is worthless unattended, so C2 is the plant: the same
hash comparison that reports "unchanged" for the poisoning sequence reports
"changed" when alignment is switched off. C5 matters separately — a guard alone
would have made the poisoning loud but left the merge re-solving on every run.

Unit: `different_solve_configurations_get_different_cache_entries` crosses
reference, resampler and spans; `the_solve_environment_keys_the_cache` crosses
both `SOLVE_ENV` variables and asserts the key returns to its unset value.

### 3.1 Rule 47 invocation record

```
strehl stack D:\personal\macro\109MSDCF --limit 22 --gate 4.0 --out P0.tiff
  STREHL_ALIGN unset (ON)   STREHL_WARPMAP unset   STREHL_FIX_HALO unset
  STREHL_DUMP_ELECTION unset   STREHL_SMOOTH unset  STREHL_SMOOTH_HUBER unset
  STREHL_CACHE_DIR=C:\dev\strehl-out\M97\poison2\cache  (hermetic)
  32 logical processors; alignment ON, reference 11, 22 placed / 0 refused
  SHA-256/16 07C067E438F74D77
  the PLANT arm differs only by STREHL_ALIGN=0 -> 48DFB69C00F0107F
```

## 4. Two things I got wrong, and how they were caught

**A bar failed on a wrong premise, not a wrong fix.** I pre-registered C4 as
"a plain `align` lands on its own cache entry, 1 -> 2 entries" and it FAILED at
1. The fix was not at fault: `align`'s reference resolves to the **middle**
frame when unspecified, which is exactly what the merge uses, so sharing one
entry is correct. I split it into C4a (the no-flag case shares, correctly) and
C4b (an explicit `--reference 3` separates). **The harness was right and the
prediction was wrong**; the temptation to relax the bar until it went green is
precisely the failure this project's culture exists to prevent.

**The wrong premise came from a stale binary.** I read `[default: 0]` out of
`strehl align --help` and built the prediction on it. That help text came from
a binary compiled before the middle-frame default landed; the current binary
prints "Defaults to the **middle** frame". This is my own fact P17 — 10 of 13
builds in this tree predate the fix they are being used to test — biting me from
the direction I was not watching. **I nearly reported a documentation defect
that does not exist.** Re-reading `--help` from a freshly built binary is what
stopped it.

## 5. Facts

- **S1 (MEASURED).** The warp cache was keyed on the capture path alone, so a
  differently-configured solve of the *same frames* passed `check_stack` and was
  served silently: identical `stack` command lines gave `DB43E708…` or
  `ADF81E01…` according to whether an `align --reference 40` had run first.
- **S2 (MEASURED).** With the configuration in the key, the same poisoning
  sequence leaves the render at `07C067E438F74D77`, and the poisoning solve
  occupies a second cache entry rather than overwriting the first.
- **S3 (MEASURED).** The merge still gets a cache **hit** afterwards
  (`alignment: ON (sidecar)`), so the fix removes the silent substitution
  without introducing a re-solve on every run.
- **S4 (MEASURED).** `STREHL_SMOOTH` / `STREHL_SMOOTH_HUBER`, added to the solve
  roughly an hour before this work, changed the warps while keying nothing. Now
  keyed, with a named constant and a comment binding future knobs to it.
- **S5 (DERIVED, from C1+C2+C3).** No frozen render moves: the change alters
  which cache entry is consulted, never the arithmetic applied to pixels.
- **S6 (MEASURED, method).** A pre-registered bar that fails may indict the
  prediction rather than the subject. C4 failed because `align`'s unspecified
  reference resolves to the middle; the premise came from a **stale binary's**
  `--help`, not from the source.
