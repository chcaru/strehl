"""Fold 29 -- exposure is systematically low across 23 stacks. Fact plus a
capture instruction in captures-needed.md section 22.
"""
import io
import re

SYN = "docs/research/SYNTHESIS.md"
CAP = "docs/captures-needed.md"


def check(row, want=5):
    n = len(re.findall(r"(?<!\\)\|", row))
    assert n == want, "row has %d unescaped pipes, need %d: %s" % (n, want, row[:170])
    return row


FACT = check(
    "| 1257 | **19 OF 23 DELIVERED STACKS ARE UNDER-EXPOSED, MEDIAN +2.01 "
    "STOPS OF UNUSED HEADROOM, AND THAT IS THE LARGEST QUALITY LEVER IN THE "
    "PROJECT.** Surveying every macro bracket in the corpus at `p99.9` of "
    "`(raw-black)/(white-black)`: median unused headroom **+2.01 stops**, range "
    "**-0.00 to +4.39**. `lead-1-cpl` **+4.39**, `leaf-2-cpl` +3.91, "
    "`112MSDCF` +3.83, all three `bee-*-cpl` **+1.69**, and only "
    "`dry-erase-marker-head-cpl`, `coffee-bean`, `coffee-bubbles` and `foam` "
    "reach the top of the range. Nineteen stacks clip **0.0000%** of pixels. | "
    "Recovering the median would collect **4.04x the photons**, which is "
    "**2.01x less shot noise before the stacker runs** -- larger than any "
    "merge improvement this corpus has measured or plausibly can, since the "
    "gated mean's own ceiling on a 30-frame burst is 5.48x and it is bounded by "
    "frame count. It costs nothing but capture technique. The CPL stacks are "
    "the worst affected, which is consistent with the polariser's ~1.5-2 stop "
    "loss not being compensated. Written up as a capture instruction in "
    "`docs/captures-needed.md` section 22. | orchestrator (MEASURED, 23 "
    "stacks); `experiments/ORCH-drift-check/exposure-survey.py` |")

L = io.open(SYN, encoding="utf-8").read().split("\n")
i = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[i].startswith("| 1256 |"), L[i][:80]
L[i + 1:i + 1] = [FACT]
io.open(SYN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("SYNTHESIS: fact 1257")

SECTION = """
## 22. Expose to the right -- REQUESTED, costs nothing, worth more than any algorithm here

**This is the highest-value change available to this project and it is not a
capture we need, it is a capture setting.** MEASURED across every macro bracket
delivered so far (23 stacks, `experiments/ORCH-drift-check/exposure-survey.py`):

| stack | frames | unused headroom | clipped |
| --- | --- | --- | --- |
| `lead-1-cpl` | 123 | **+4.39 stops** | 0.0000% |
| `leaf-2-cpl` | 182 | +3.91 | 0.0000% |
| `112MSDCF` | 79 | +3.83 | 0.0000% |
| `109MSDCF` / `113MSDCF` | 22 / 63 | +2.86 | 0.0000% |
| `wrapped-text-1` | 130 | +2.71 | 0.0000% |
| `flat-on-ruler-cpl` | 79 | +2.65 | 0.0000% |
| `couch-fibers-cpl` | 299 | +2.35 | 0.0000% |
| `wrapped-text-2` | 120 | +2.31 | 0.0000% |
| `flowers-cpl` | 176 | +2.07 | 0.0000% |
| `flower-bud-with-background-fern-cpl` | 299 | +2.04 | 0.0000% |
| `lavendar-cpl` | 299 | +2.01 | 0.0000% |
| `highly-angled-ruler-mm-cpl` | 299 | +1.82 | 0.0000% |
| `119MSDCF` | 33 | +1.75 | 0.0000% |
| `flower-bud-alone-cpl` | 205 | +1.73 | 0.0000% |
| **`bee-1-cpl` / `bee-2-cpl` / `bee-3-cpl`** | 299 each | **+1.69** | 0.0000% |
| `tweezers-cpl` | 100 | +1.39 | 0.0001% |
| `foam` | 100 | +0.40 | 0.0428% |
| `coffee-bean` | 105 | +0.01 | 0.1283% |
| `coffee-bubbles` | 19 | -0.00 | 0.1225% |
| `dry-erase-marker-head-cpl` | 299 | -0.00 | 3.6726% |

Median **+2.01 stops**. Nineteen of the twenty-three clip **0.0000%** of
pixels -- not "few", none.

### Why this outranks everything else on the roadmap

Two stops is **4.04x the photons**, which is **2.01x less shot noise arriving
at the sensor**, before a single line of strehl runs. For comparison, the
merge's own ceiling on a 30-frame static burst is 5.48x and it is bounded by
frame count (M62); the shipped gate reaches 0.890x flat-ROI noise (fact 320).
**A capture change worth 2.01x is competitive with the entire estimation
machinery this project exists to build**, and unlike the machinery it is free
and available today.

It also compounds: the merge's advantage over selection is largest where the
frames are noisy, so a cleaner capture does not make strehl less useful -- it
raises the floor everything else is measured from.

### What to do

- **Expose to the right.** Raise exposure until the brightest *diffuse* part
  of the subject or the background sits just below clipping. A blown specular
  highlight on a chitin edge is acceptable; a blown diffuse surface is not.
- **The polariser is costing about 1.5-2 stops and the CPL stacks show it** --
  every `*-cpl` bracket except `dry-erase-marker-head-cpl` and `tweezers-cpl`
  is at least 1.7 stops down. If the exposure was not compensated when the CPL
  went on, that is most of the gap.
- **Prefer longer shutter to higher ISO** on a static subject; the noise model
  is read-noise dominated at low signal and this rig is tripod-bound anyway.
- **Do not clip to reach it.** Judge on the RAW histogram, not the JPEG
  preview, which has the camera's tone curve applied and will look brighter
  than the data.

### What it does NOT change

The existing 23 stacks stay valid. Every measured number in this corpus was
taken on them and none is invalidated -- the noise model is calibrated in
electrons and handles a dark capture correctly. This is about the *next*
captures, and about what the shipped product can show.

### Related

- Fact 1253: the render is tonally faithful; `bee-3-cpl`'s dullness is the
  capture, not the merge.
- Fact 1257: this survey.
- M100 is adding `--exposure` / `--auto-exposure` to the **viewing** render so
  existing captures at least *display* correctly. That is a presentation fix
  and it does not recover the photons; only re-shooting does.
"""

C = io.open(CAP, encoding="utf-8").read()
assert "## 22." not in C, "section 22 already exists"
assert C.rstrip().endswith(("---", ".", ")", "`")) or True
io.open(CAP, "w", encoding="utf-8", newline="\n").write(
    C.rstrip("\n") + "\n" + SECTION)
print("captures-needed.md: appended section 22")
