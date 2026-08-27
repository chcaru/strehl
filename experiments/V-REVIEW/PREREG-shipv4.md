# Pre-registration: do the four noise cells hold on the SHIP-V4 pin?

Written and committed **before any SHIP-V4 render exists**. Nothing below was
chosen after seeing a result.

## What is being tested

The four published cells were measured with the strehl arm rendered by
`740e7056`, the SHIP-V3 pin. The owner's 26 masters come from `9b05d0b7`, the
SHIP-V4 pin. Only the strehl arm is re-rendered. The comparator outputs and the
tile census are held fixed, because our pin cannot affect them and re-running
them would add variance to a comparison that has none to spare.

## The published SHIP-V3 cells, restated here so they cannot drift

| cell | channel | point | 95% interval |
|---|---|---:|---|
| vs `enfuse` | luma | 1.618 | 1.511 to 1.709 |
| vs `enfuse` | B-Y | 1.606 | 1.525 to 1.702 |
| vs `enfuse` | R-Y | 1.813 | 1.717 to 1.966 |
| vs `focus-stack` | luma | 1.475 | 1.400 to 1.514 |
| vs `focus-stack` | B-Y | 1.640 | 1.550 to 1.710 |
| vs `focus-stack` | R-Y | 1.661 | 1.592 to 1.755 |

## Decision rule, fixed in advance

The rule is stated on the **six per-channel ratios**, not the four rounded
README cells, because a rounded cell hides movement.

- **HOLD.** Every SHIP-V4 point estimate falls **inside** the published SHIP-V3
  interval for its channel, **and** every SHIP-V4 interval has a lower bound
  above 1.000. Action: strike the scope line, publish nothing new.
- **RESTATE DIGITS.** All points inside their intervals and all clear of
  parity, but at least one README cell changes when rounded to two decimals.
  Action: replace the digits with the SHIP-V4 figures, claim unchanged.
- **RESTATE THE CLAIM.** Either at least one SHIP-V4 point falls **outside**
  its published interval, **or** any channel's lower bound reaches 1.000 or
  below. Action: the table is restated tonight and the SOTA sentence is
  revisited.

The interval is the threshold because this project forbids comparing two
numbers closer together than the printed spread. A point inside the interval is
not distinguishable from the published one by the instrument that produced it.

**Direction is reported either way.** If the SHIP-V4 figures favour strehl more
than the published ones, that is reported as a movement requiring restatement
on exactly the same terms as a movement against.

## Commissioning, fixed in advance

The failure this is most likely to produce is a render made with the wrong
binary, which yields "no change" -- the same answer as a genuine null.

- **DIFFERENCE REQUIRED.** The SHIP-V4 render must differ from the SHIP-V3
  render byte-wise. A byte-identical result is a **red flag to diagnose**, not
  a clean null.
- If the two arms do come back byte-identical, that must be established
  **positively** -- by showing the two binaries produce identical output on this
  subject through some route other than my own single run -- before it is
  reported as a null.
- **PIN VERIFIED BY HASH.** Already done: the pin hashes
  `44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490`, which
  equals the SHIP-V4 corpus seal. Four builds on this machine share size
  9,568,768, so size and path prove nothing.
- **SWITCH STATE MATCHED.** The RULE 47 block in
  `experiments/V-HEADTOHEAD2/render_linear.ps1` is followed exactly: `stack
  --merge pyramid --pyramid-gate 4.5 --linear-srgb --demosaic`, with
  `STREHL_FULLRES_GATHER=1`, the pinned per-half warpmap, and the same eleven
  `STREHL_*` variables cleared by name. Verified before rendering: no `STREHL_*`
  variable is set in the calling process, so none can leak in.
- **ESTIMATOR UNCHANGED.** Same container-matched shift-corrected gauge, same
  110 tiles, same 2000-resample bootstrap, same code.

## Declared in advance as a non-result

If the pinned warpmap's digest is rejected by the SHIP-V4 binary, the switch
state cannot be matched and the comparison is **not performed**. That is
reported as unmeasurable rather than forced by dropping the warpmap, because
dropping it would change the geometry and compare two rasters instead of two
merges.
