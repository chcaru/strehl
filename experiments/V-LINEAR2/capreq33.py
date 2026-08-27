"""Rewrite docs/captures-needed.md sec.33 from a source file, not from a
`python -c` string.

The first attempt at sec.33 was written through `python -c "..."` inside
PowerShell, whose double-quoted strings eat backticks as an escape character.
Four markdown code spans arrived as control bytes (ESC, FF) with their closing
backtick silently deleted; corpus_lint's S7 check caught all four.  fixctl.py
can repair the control bytes but not the deleted closing backticks, so the
section is regenerated wholesale from this file instead.

Truncates docs/captures-needed.md at the line "## 33." and re-appends.
Idempotent.  Run with --apply to write.
"""
import io
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "docs", "captures-needed.md")

SECTION = """
## 33. A subject with real contrast above 0.25 cyc/px -- REQUESTED 2026-08-27, one subject and one stack, and it is what would let a resolution claim reach past a quarter of Nyquist

### Why you are being asked

Every fine-scale comparison this project has attempted has been decided, in the
end, by whether the *corpus* carries signal at the frequency being argued about.
On 113MSDCF it mostly does not. `experiments/V-LINEAR2/bandsignal.py` measures
in-focus band power against defocused band power, per tile, on the linear
develops, and the answer is a cliff:

| band, cyc/px | 0.10-0.20 | 0.20-0.25 | 0.25-0.30 | 0.30-0.40 | 0.40-0.48 |
|---|---:|---:|---:|---:|---:|
| in-focus / defocused | 6.28 | **2.42** | 1.39 | 1.15 | 1.10 |
| verdict | PASS | **PASS** | MARGINAL | FAIL | FAIL |

A ratio near 1.0 means focusing the lens does not change the power in that band,
which means the band is not showing you the subject. Above 0.25 cyc/px this
corpus is showing you sensor noise. **No stacker can be shown to resolve better
than another in a band where the subject contributes nothing**, and no amount of
better code or better statistics fixes that -- it is a property of the photons.

That is why the comparison in `docs/research/V-LINEAR2.md` is reported at
0.20-0.25 cyc/px and nowhere finer, and it is why the answer there is *level*
with the best of the open-source field rather than a number with a margin. At
0.20-0.25 the in-focus/defocused ratio is 2.42; two good stackers separated by
5% cannot be told apart at that ratio without far more regions than one subject
provides.

### What to shoot

A subject with **genuine, high-contrast structure at a period of 2-4 output
pixels** -- which at this magnification means structure a few micrometres
across. Candidates, cheapest first:

- **Diatom test slide** (8-form or 20-form). These exist precisely because they
  are a resolution standard, the finest forms are well below a micrometre, and
  they cost less than a filter.
- **Insect wing scales** -- butterfly or moth. Ridge spacing is around a
  micrometre and the contrast is high.
- **A cleaved silicon wafer or a grating of known pitch**, if you have one --
  the pitch is then known independently and doubles as a scale check.

Shoot it the same way as 113MSDCF otherwise: same step, same lens, same constant
exposure, RAW, enough frames to cover the depth.

### The acceptance test, so this does not have to be argued about afterwards

Run it before anything else is claimed:

```
python experiments/V-LINEAR2/bandsignal.py 5 6 20
```

**A band is usable if in-focus/defocused power is at least 2.0 with the lower
end of its 95% CI at or above 1.5.** That threshold was fixed in
`experiments/V-LINEAR2/PREREGISTRATION.md` and committed before any comparator
output existed, so it is not a number chosen to suit an answer. If the new
subject passes at 0.30-0.40 cyc/px, the resolution question can finally be asked
at a frequency where the differences between stackers are large. If it fails
there too, that is worth knowing as well -- it would say the limit is the optics
and the sensor, not the software, and the project should stop framing fine-scale
resolution as a differentiator at all.

### What it unblocks

- **A resolution verdict with a margin instead of a tie.**
  `docs/research/V-LINEAR2.md` puts strehl level with `enfuse` (0.977, CI
  [0.810, 1.181]) and ahead of `focus-stack` (1.326, CI [1.089, 1.625]) in
  coherent fine-scale structure at 0.20-0.25. Those intervals are wide because
  the band is only 2.4x above noise.
- **The 0.25-0.48 bands, which are currently unusable.** Four of the seven bands
  this project measures carry no verdict at all on the present corpus.
- **Sections 30 and 32.** A slanted edge answers a different question -- whether
  fine-scale power is real detail or sharpening overshoot -- and the two
  together would close the fine-scale question completely. Neither closes it
  alone.

### Related

- `docs/research/V-LINEAR2.md` -- the measurement this would strengthen, and the
  reason its comparison band is 0.20-0.25.
- `docs/research/V-LINEAR.md` section 5.3 -- the earlier and *too pessimistic*
  reading that 0.20-0.48 was all noise. It is 0.25-0.48 that is noise; 0.20-0.25
  does carry signal when best focus is chosen per tile.
- Section 30 (slanted edge) -- orthogonal, still wanted, and no substitute for
  this.
"""


def main():
    s = io.open(P, encoding="utf-8", newline="").read()
    i = s.find("\n## 33.")
    if i < 0:
        print("no sec.33 present -- appending fresh")
        head = s.rstrip("\n")
    else:
        head = s[:i].rstrip("\n")
        print(f"truncating existing sec.33 at byte {i} "
              f"({len(s) - i} bytes removed)")
    new = head + "\n" + SECTION
    bad = [hex(ord(c)) for c in new if ord(c) < 32 and c != "\n"]
    if bad:
        print(f"REFUSING TO WRITE: control bytes in payload {set(bad)}")
        return 2
    print(f"  payload clean; {len(new.splitlines())} lines total")
    if "--apply" in sys.argv:
        io.open(P, "w", encoding="utf-8", newline="\n").write(new)
        print("  WRITTEN")
    else:
        print("  dry run -- pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
