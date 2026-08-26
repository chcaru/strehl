"""Append section 11 (V-RIM's answer key, run on both arms) to the report."""
import io

DOC = "docs/research/BUILD-BLEND.md"
MARK = "11. Scored against V-RIM's answer key"

NOTE = """
### 11. Scored against V-RIM's answer key, with V-RIM's own instrument

ORCH forwarded V-RIM's finding -- single frames have flat backdrops, the merge
manufactures the darkening, the election can leave the hull of its inputs -- and
asked me to score against the in-focus frame rather than a pre-registered number.
Done, using `C:\\dev\\strehl-out\\V-RIM\\framerings.py` (V-RIM's code, not mine,
argv-capable) against V-RIM's own single-frame linear TIFFs.

**First, which backend V-RIM measured.** Their merge input is
`ORCH-rim\\fb-1cacb61-lin.tif`, and the banner captured in their own log reads
`strehl stack -- regularised winner + noise-gated average (THE DEFAULT PATH, an
estimator)`. **V-RIM measured the estimator -- the old default.** None of the
quoted -18.94% / -13.61% figures describe the merge that ships today.

**Commissioning before use.** Running their instrument on my *estimator* arm
first reproduces their ground truth: frame 110 far field **19058 DN**, against
ORCH's quoted "~19100 DN". An instrument that had not reproduced that number
would not have been trusted for the row below it.

`flower-bud-alone-cpl`, smooth backdrop, STRAIGHTEST QUARTILE / ALL RAYS:

| metric | estimator | **pyramid** | FRAME110 = truth |
|---|---|---|---|
| far field DN | 17150 / 16761 | **19467 / 19470** | 19058 / 19070 |
| inner DN | 3803 / 3699 | **2655 / 2720** | 2729 / 3070 |
| 10-90 edge px | 242.6 / 239.2 | **27.7 / 35.4** | 43.9 / 81.6 |
| ring % | +2.68 / +3.32 | **+0.11 / +0.06** | +0.19 / +0.10 |

The estimator's backdrop sags **10.0%** below the frame that actually saw it.
The pyramid arm lands **+2.1% above** it -- no sag -- and its ring, **+0.11%**,
is at or below the ground-truth frame's own **+0.19%**, a **24x** reduction. Edge
width is tighter than the in-focus single frame. On this subject the merge is
already at the answer key.

**ORCH's falsifiable prediction (3), tested and CONFIRMED.** The prediction was
that the cure should help most on a smooth backdrop and least on a textured one,
because texture gives the focus measure real signal to elect on. `coffee-bean`
is the textured case (paper fibres):

| ring % | estimator | **pyramid** | FRAME58 = truth |
|---|---|---|---|
| flower-bud (smooth) | +2.68 / +3.32 | **+0.11 / +0.06** | +0.19 / +0.10 |
| coffee-bean (textured) | +4.15 / +7.02 | **+3.54 / +3.62** | +0.16 / +0.18 |

Smooth: cured, 96% of the ring removed, ground truth reached. Textured: only
15% / 48% removed and **+3.54% of ring remains against a +0.16% truth**. The
prediction holds in the direction and the magnitude stated, from an instrument
neither ORCH nor I wrote. The mechanism is confirmed.

**What this changes about priority.** ORCH asked for the base-band fix as the
highest-value item. The base band is *already* the plain mean -- runtime-confirmed
in section 10 -- and the flower-bud row shows that is already delivering the cure
where the mechanism predicts it should. **The residual is on `coffee-bean`, and it
cannot be a base-band problem**: a textured backdrop gives the focus measure real
signal, so the bad election happens in the *detail* bands, which the base band
does not touch. Changing the base band cannot move a ring that lives at fine
scales. The remaining work is in detail-band election on textured backdrops --
a different fix from the one prescribed, and the answer key now localises it.

**Reported against my own interest.** Two residuals in my arm, neither spun:
`coffee-bean` inner is **8512 DN against the frame's 9563**, 11% dark, and I
cannot tell from this measurement whether that is veil correctly removed or the
subject over-darkened. And `flower-bud` far field overshoots truth by +409 DN
(+2.1%). Both want a diagnosis before either is called good.
"""

src = io.open(DOC, encoding="utf-8").read()
if MARK in src:
    raise SystemExit("section already present -- refusing to duplicate")
io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
print("appended section 11;", len(io.open(DOC, encoding="utf-8").read().splitlines()), "lines")
